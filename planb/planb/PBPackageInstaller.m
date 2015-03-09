/*

 Plan B
 PBPackageInstaller.m

 Copyright 2014 Google Inc.

 Licensed under the Apache License, Version 2.0 (the "License"); you may not
 use this file except in compliance with the License.  You may obtain a copy
 of the License at

 http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
 License for the specific language governing permissions and limitations under
 the License.

 */

#import <CommonCrypto/CommonDigest.h>

#import "PBLogging.h"
#import "PBPackageInstaller.h"

@implementation PBPackageInstaller

+ (NSString *)SHA1ForFileAtPath:(NSString *)path {
  unsigned char sha1[CC_SHA1_DIGEST_LENGTH];
  NSData *fileData = [NSData dataWithContentsOfFile:path
                                            options:NSDataReadingMappedIfSafe
                                              error:nil];

  CC_SHA1([fileData bytes], (unsigned int)[fileData length], sha1);
  NSMutableString *buf = [[NSMutableString alloc] initWithCapacity:CC_SHA1_DIGEST_LENGTH * 2];

  for (int i = 0; i < CC_SHA1_DIGEST_LENGTH; i++) {
    [buf appendFormat:@"%02x", (unsigned char)sha1[i]];
  }

  return buf;
}

- (instancetype)initWithReceiptName:(NSString *)receiptName
                        packagePath:(NSString *)packagePath
                       targetVolume:(NSString *)targetVolume {
  self = [super init];

  if (self) {
    _receiptName = receiptName;
    _packagePath = packagePath;
    _targetVolume = targetVolume;

    if (![_receiptName length] || ![_packagePath length] || ![_targetVolume length]) {
      return nil;
    }
  }

  return self;
}

- (NSString *)firstPackageOnImage {
  NSFileManager *fm = [NSFileManager defaultManager];
  NSError *fmError = nil;
  NSArray *dirContents = [fm contentsOfDirectoryAtPath:_mountPoint
                                                 error:&fmError];
  if (fmError) {
    PBLog(@"Error: could not determine package path: %@", fmError);
    return nil;
  }

  NSPredicate *filterPKGs = [NSPredicate predicateWithFormat:@"self ENDSWITH '.pkg'"];
  NSArray *onlyPKGs = [dirContents filteredArrayUsingPredicate:filterPKGs];
  return [onlyPKGs firstObject];
}

- (void)installApplication {
  char tmpdir[22];
  strncpy(tmpdir, "/tmp/planb-pkg.XXXXXX", sizeof tmpdir);

  if (!mkdtemp(tmpdir)) {
    PBLog(@"Error: Could not create temporary installation directory %s.", tmpdir);
    return;
  }

  _mountPoint = [[NSFileManager defaultManager] stringWithFileSystemRepresentation:tmpdir
                                                                            length:strlen(tmpdir)];

  if ([self runDiskUtilityWithLocation:_packagePath
                             operation:@"attach"]) {
    PBLog(@"Mounted %@ (SHA1: %@) to %@",
          _packagePath,
          [PBPackageInstaller SHA1ForFileAtPath:_packagePath],
          _mountPoint);

    [self forgetPackageWithName:_receiptName];
    [self installPackageFromLocation:[self firstPackageOnImage]
                            toVolume:_targetVolume];
  }

  [self runDiskUtilityWithLocation:_packagePath
                         operation:@"detach"];

  NSError *err;
  [[NSFileManager defaultManager] removeItemAtPath:_mountPoint
                                             error:&err];
  if (err) {
    PBLog(@"Error: could not delete temporary mount point %@: %@",
          _mountPoint, err.localizedDescription);
  }
}

- (BOOL)runDiskUtilityWithLocation:(NSString *)location
                         operation:(NSString *)operation {
  NSArray *args;

  if ([operation isEqual:@"attach"]) {
    args = @[ operation, location, @"-nobrowse", @"-readonly", @"-mountpoint", _mountPoint ];
  } else if ([operation isEqual:@"detach"]) {
    args = @[ operation, @"-force", _mountPoint ];
  } else {
    return NO;
  }

  NSTask *hdiutil = [[NSTask alloc] init];
  NSPipe *pipe = [NSPipe pipe];

  [hdiutil setLaunchPath:@"/usr/bin/hdiutil"];
  [hdiutil setArguments:args];
  [hdiutil setStandardOutput:pipe];
  [hdiutil setStandardError:pipe];
  [hdiutil setStandardInput:[NSPipe pipe]];
  @try {
    [hdiutil launch];
  }
  @catch (NSException *exception) {
    PBLog(@"Exception: hdiutil failed to launch.");
    return NO;
  }

  NSMutableData *stdBuff = [self runTask:hdiutil outputPipe:pipe timeout:30];

  if (stdBuff && [hdiutil terminationStatus] == 0) {
    return YES;
  } else {
    NSString *pipeOut = [[NSString alloc] initWithData:stdBuff
                                              encoding:NSUTF8StringEncoding];
    PBLog(@"Error: failed to %@ %@: %@", operation, _packagePath, pipeOut);
    return NO;
  }
}

- (BOOL)installPackageFromLocation:(NSString *)location
                          toVolume:(NSString *)volume {
  if ([[location pathComponents] count] != 1) {
    PBLog(@"Error: %@ is not a direct subpath.", location);
    return NO;
  }

  NSString *packageLocation = [_mountPoint stringByAppendingPathComponent:location];
  NSArray *args = @[ @"-pkg", packageLocation, @"-tgt", volume ];
  NSTask *installer = [[NSTask alloc] init];
  NSPipe *pipe = [NSPipe pipe];

  PBLog(@"Attempting to install %@ to %@", packageLocation, volume);

  [installer setLaunchPath:@"/usr/sbin/installer"];
  [installer setArguments:args];
  [installer setStandardOutput:pipe];
  [installer setStandardError:pipe];
  [installer setStandardInput:[NSPipe pipe]];
  @try {
    [installer launch];
  }
  @catch (NSException *exception) {
    PBLog(@"Exception: installer failed to launch.");
    return NO;
  }

  // some packages may take several minutes to install, especially if they have postlight scripts.
  NSMutableData *stdBuff = [self runTask:installer outputPipe:pipe timeout:60 * 5];

  if (stdBuff && [installer terminationStatus] == 0) {
    // DMG may be ejected before installer is done, so sleep for a few seconds first.
    sleep(3);
    PBLog(@"Installed %@", location);
    return YES;
  } else {
    NSString *pipeOut = [[NSString alloc] initWithData:stdBuff
                                              encoding:NSUTF8StringEncoding];
    PBLog(@"Error: failed to install %@: %@", location, pipeOut);
    return NO;
  }
}

- (BOOL)forgetPackageWithName:(NSString *)packageReceipt {
  NSArray *args = @[ @"--forget", packageReceipt ];
  NSTask *pkgutil = [[NSTask alloc] init];
  NSPipe *pipe = [NSPipe pipe];
  NSPipe *stdin_pipe = [NSPipe pipe];

  [pkgutil setLaunchPath:@"/usr/sbin/pkgutil"];
  [pkgutil setArguments:args];
  [pkgutil setStandardOutput:pipe];
  [pkgutil setStandardError:pipe];
  [pkgutil setStandardInput:[NSPipe pipe]];
  @try {
    [pkgutil launch];
  }
  @catch (NSException *exception) {
    PBLog(@"Exception: pkgutil failed to launch.");
    return NO;
  }

  NSMutableData *stdBuff = [self runTask:pkgutil outputPipe:pipe timeout:3];

  if (stdBuff && [pkgutil terminationStatus] == 0) {
    PBLog(@"Forgot %@", _receiptName);
    return YES;
  } else {
    NSString *pipeOut = [[NSString alloc] initWithData:stdBuff
                                              encoding:NSUTF8StringEncoding];
    PBLog(@"Error: cannot forget %@: %@", _receiptName, pipeOut);
    return NO;
  }
}

- (NSMutableData *)runTask:(NSTask *)task
                outputPipe:(NSPipe *)pipe
                   timeout:(NSTimeInterval)timeout {
  NSDate *startDate = [NSDate date];
  NSMutableData *stdBuff = [[NSMutableData alloc] init];

  do {
    [[NSRunLoop currentRunLoop] runUntilDate:[NSDate dateWithTimeIntervalSinceNow:1]];

    NSData *availableData = [[pipe fileHandleForReading] availableData];

    if ([availableData length]) {
      [stdBuff appendData:availableData];
    }
  } while ([task isRunning] && -[startDate timeIntervalSinceNow] < timeout);

  // If task has exceeded its timeout, kill it.
  if ([task isRunning]) {
    kill([task processIdentifier], SIGKILL);
  }

  return stdBuff;
}

@end

