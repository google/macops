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

///
///  Retrieves a mutable array from the kPreferencePath plist on disk.
///  If the file doesn't exist or is unreadable, returns an empty mutable array.
///
NSMutableArray *GetUsers() {
  NSMutableArray *currentUsers = [NSMutableArray arrayWithContentsOfFile:kPreferencePath];
  return (currentUsers ? currentUsers : [NSMutableArray array]);
}

///
///  Writes out the provided array as a plist to disk.
///
void SetUsers(NSMutableArray *usersArray) {
  if (!usersArray) return;
  [usersArray writeToFile:kPreferencePath atomically:YES];
}

///
///  Validates that the provided password is the current user's login password.
///
BOOL ValidateLoginPassword(NSString *newPassword) {
  AuthorizationItem authRightsItems[1];
  authRightsItems[0].name = "com.google.keychain-minder.validate-new-password";
  authRightsItems[0].value = NULL;
  authRightsItems[0].valueLength = 0;
  authRightsItems[0].flags = 0;
  AuthorizationRights authRights;
  authRights.count = sizeof(authRightsItems) / sizeof(authRightsItems[0]);
  authRights.items = authRightsItems;

  AuthorizationItem authEnvItems[2];
  authEnvItems[0].name = kAuthorizationEnvironmentUsername;
  authEnvItems[0].valueLength = NSUserName().length;
  authEnvItems[0].value = (void *)[NSUserName() UTF8String];
  authEnvItems[0].flags = 0;
  authEnvItems[1].name = kAuthorizationEnvironmentPassword;
  authEnvItems[1].valueLength = newPassword.length;
  authEnvItems[1].value = (void *)[newPassword UTF8String];
  authEnvItems[1].flags = 0;
  AuthorizationEnvironment authEnv;
  authEnv.count = sizeof(authEnvItems) / sizeof(authEnvItems[0]);
  authEnv.items = authEnvItems;

  AuthorizationFlags authFlags = (kAuthorizationFlagDefaults |
                                  kAuthorizationFlagExtendRights);

  AuthorizationRef authRef = NULL;

  // Create an authorization reference, retrieve rights and then release.
  // CopyRights is where the authorization actually takes place and the result lets us know
  // whether auth was successful.
  AuthorizationCreate(&authRights, &authEnv, authFlags, &authRef);
  OSStatus authStatus = AuthorizationCopyRights(authRef, &authRights, &authEnv, authFlags, NULL);
  AuthorizationFree(authRef, kAuthorizationFlagDestroyRights);

  return (authStatus == errAuthorizationSuccess);
}

///
///  Validates that the provided password matches the password for the current user's
///  default keychain.
///
///  To attempt to avoid issues with the "Local Items" keychain, it makes a hardlink
///  to the keychain file with the date appended, opens that 'new' keychain file, attempts
///  to unlock it and then removes the hardlink. Attempting to unlock an unlocked keychain
///  will always succeed and locking the login keychain also locks the Local Items keychain
///  and so should be avoided.
///
///  Returns YES if password matches the keychain.
///
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