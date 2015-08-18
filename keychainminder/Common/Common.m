/// Copyright 2015 Google Inc. All rights reserved.
///
/// Licensed under the Apache License, Version 2.0 (the "License");
/// you may not use this file except in compliance with the License.
/// You may obtain a copy of the License at
///
///    http://www.apache.org/licenses/LICENSE-2.0
///
///    Unless required by applicable law or agreed to in writing, software
///    distributed under the License is distributed on an "AS IS" BASIS,
///    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
///    See the License for the specific language governing permissions and
///    limitations under the License.

#import "Common.h"

static NSString * const kPreferencePath =
    @"/Library/Preferences/com.google.corp.keychainminder.plist";


NSMutableArray *GetUsers() {
  NSMutableArray *currentUsers = [NSMutableArray arrayWithContentsOfFile:kPreferencePath];
  return (currentUsers ? currentUsers : [NSMutableArray array]);
}

void SetUsers(NSMutableArray *usersArray) {
  if (!usersArray) return;
  [usersArray writeToFile:kPreferencePath atomically:YES];
}

BOOL ValidateLoginPassword(NSString *newPassword) {
  NSError *err = nil;

  ODSession *mySession = [ODSession defaultSession];

  ODNode *myNode = [ODNode nodeWithSession:mySession type:kODNodeTypeAuthentication error:&err];
  if (err) {
    NSLog(@"Unable to get node: %@", err);
    return NO;
  }

  ODRecord *myRecord = [myNode recordWithRecordType:kODRecordTypeUsers
                                               name:NSUserName()
                                         attributes:nil
                                              error:&err];
  if (err) {
    NSLog(@"Unable to get %@'s record: %@", NSUserName(), err);
  }

  return [myRecord verifyPassword:newPassword error:nil];
}

BOOL ValidateLoginKeychainPassword(NSString *oldPassword) {
  // Get default keychain path
  SecKeychainRef defaultKeychain;
  SecKeychainCopyDefault(&defaultKeychain);
  UInt32 maxPathLen = MAXPATHLEN;
  char keychainPath[MAXPATHLEN];
  SecKeychainGetPath(defaultKeychain, &maxPathLen, keychainPath);
  CFRelease(defaultKeychain);

  // Duplicate the default keychain file to a new location.
  NSString *path = @(keychainPath);
  NSString *newPath = [path stringByAppendingFormat:@".%d",
                       (int)[[NSDate date] timeIntervalSince1970]];
  if (link(path.UTF8String, newPath.UTF8String) != 0) {
    return NO;
  }

  // Open and unlock this new keychain file.
  SecKeychainRef keychainRef;
  SecKeychainOpen(newPath.UTF8String, &keychainRef);
  OSStatus err = SecKeychainUnlock(keychainRef, (UInt32)oldPassword.length,
                                   oldPassword.UTF8String, YES);
  CFRelease(keychainRef);

  // Delete the temporary keychain file.
  unlink(newPath.UTF8String);

  return (err == errSecSuccess);
}