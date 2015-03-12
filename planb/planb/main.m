/*

 Plan B
 main.m

 Installs management software on a managed Mac.

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

#import "PBConnectionDelegate.h"
#import "PBLogging.h"
#import "PBPackageInstaller.h"
#import "PBURLBuilder.h"

static NSString *CreateTmpDownloadDirectory() {
  char tmpdir[22];
  strncpy(tmpdir, "/tmp/planb-dmg.XXXXXX", sizeof tmpdir);

  if (!mkdtemp(tmpdir)) {
    PBLog(@"Error: Could not create temporary download directory %s.", tmpdir);
    return NULL;
  }

  return [[NSFileManager defaultManager] stringWithFileSystemRepresentation:tmpdir
                                                                     length:strlen(tmpdir)];
}

int main(int argc, const char * argv[]) {
  @autoreleasepool {

    if (getuid() != 0) {
      PBLog(@"%s must be run as root!", argv[0]);
      exit(99);
    }

    PBLog(@"Starting planb");

    __block BOOL installComplete = NO;

    NSArray *packages = @[
      @[ @"pkg1/package1", @"com.megacorp.package1" ],
      @[ @"pkg2/package2", @"com.megacorp.package2" ],
      @[ @"pkg3/package3", @"com.megacorp.package3" ],
    ];

    for (NSArray *packageTuple in packages) {
      NSString *item = [packageTuple objectAtIndex:0];
      NSString *receiptName = [packageTuple objectAtIndex:1];

      PBConnectionDelegate *connDel =
          [[PBConnectionDelegate alloc] initWithDownloadDir:CreateTmpDownloadDirectory()
                                            finishedHandler:^(NSString *path) {

          installComplete = YES;
          if (!path) {
            // Fast fail if the connection cannot be established.
            return;
          }

          PBPackageInstaller *pkg = [[PBPackageInstaller alloc] initWithReceiptName:receiptName
                                                                    packagePath:path
                                                                   targetVolume:@"/"];
          [pkg installApplication];

          PBLog(@"Finished with %@", item);
      }];

      NSURL *url = [URLBuilder URLForTrackWithPkg:item];
      PBLog(@"Requesting %@", url);

      // Disable disk and memory caching of downloads.
      [NSURLCache setSharedURLCache:[[NSURLCache alloc] initWithMemoryCapacity:0
                                                                  diskCapacity:0
                                                                      diskPath:nil]];

      // Also instruct NSURLRequest to ignore local and remote caches; download only from source.
      NSURLRequest *urlReq = [NSURLRequest requestWithURL:url
                                              cachePolicy:NSURLRequestReloadIgnoringLocalAndRemoteCacheData
                                          timeoutInterval:30];

      NSURLConnection *urlConn = [[NSURLConnection alloc] initWithRequest:urlReq
                                                                 delegate:connDel];

      installComplete = NO;
      [urlConn start];

      while (!installComplete) {
        [[NSRunLoop mainRunLoop] runUntilDate:[NSDate dateWithTimeIntervalSinceNow:0.5]];
      }

      // Clean up temporary download directory.
      if (connDel.downloadDir) {
        NSError *err;
        if ([connDel.downloadDir hasPrefix:@"/tmp/planb-dmg"]) {
          if (![[NSFileManager defaultManager] removeItemAtPath:connDel.downloadDir
                                                          error:&err]) {
            PBLog(@"Error: could not delete download directory %@: %@", connDel.downloadDir, err);
          }
        }
      }
    }
  }

  return 0;
}

