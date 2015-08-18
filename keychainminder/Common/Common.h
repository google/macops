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

@import Foundation;
@import OpenDirectory;

///
///  Retrieves a mutable array from the plist on disk.
///  If the file doesn't exist or is unreadable, returns an empty mutable array.
///
NSMutableArray *GetUsers();

///
///  Writes out the provided array as a plist to disk.
///
void SetUsers(NSMutableArray *usersArray);

///
///  Validates that the provided password is the current user's login password.
///
BOOL ValidateLoginPassword(NSString *newPassword);

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
BOOL ValidateLoginKeychainPassword(NSString *OldPassword);