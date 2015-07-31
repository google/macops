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

#include "Common.h"

@import Cocoa;

int main(int argc, const char * argv[]) {
#ifdef DEBUG
  NSLog(@"DEBUG: Launching regardless of user's plist contents");
#else
  NSArray *users = GetUsers();
  if (![users containsObject:NSUserName()]) exit(0);
#endif
  return NSApplicationMain(argc, argv);
}
