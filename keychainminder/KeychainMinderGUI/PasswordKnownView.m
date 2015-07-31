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

#import "PasswordKnownView.h"

#import "Common.h"

@import QuartzCore;

/// From Security.framework
extern OSStatus SecKeychainChangePassword(SecKeychainRef keychainRef,
                                          UInt32 oldPasswordLength,
                                          const void* oldPassword,
                                          UInt32 newPasswordLength,
                                          const void* newPassword);

@interface PasswordKnownView ()
@property IBOutlet NSTextField *previousPassword;
@property IBOutlet NSTextField *currentPassword;
@property IBOutlet NSButton *okButton;
@property IBOutlet NSProgressIndicator *spinner;
@end

@implementation PasswordKnownView

- (NSArray *)textFields {
  return @[ self.previousPassword, self.currentPassword ];
}

- (void)beginProcessing {
  [super beginProcessing];
  self.okButton.enabled = NO;
  [self.spinner startAnimation:self];
}

- (void)endProcessing {
  [super endProcessing];
  self.okButton.enabled = YES;
  [self.spinner stopAnimation:self];
}

- (IBAction)readyToContinue:(id)sender {
  [self beginProcessing];

  if (!ValidateLoginKeychainPassword(self.previousPassword.stringValue)) {
    [self badPasswordField:self.previousPassword];
    return;
  }

  if (!ValidateLoginPassword(self.currentPassword.stringValue)) {
    [self badPasswordField:self.currentPassword];
    return;
  }

  dispatch_async(dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_BACKGROUND, 0), ^{
    OSStatus ret = [self changeKeychainPasswordOldPassword:self.previousPassword.stringValue
                                               newPassword:self.currentPassword.stringValue];
    NSLog(@"KeychainMinder Change: %d", ret);
    [NSApp terminate:sender];
  });
}

- (OSStatus)changeKeychainPasswordOldPassword:(NSString *)oldPw newPassword:(NSString *)newPw {
  OSStatus ret = SecKeychainChangePassword(
      NULL, (UInt32)oldPw.length, [oldPw UTF8String], (UInt32)newPw.length, [newPw UTF8String]);
  return ret;
}

@end
