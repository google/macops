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

#import "PasswordNotKnownView.h"

#import "Common.h"

@import QuartzCore;

/// From Security.framework
extern OSStatus SecKeychainResetLogin(UInt32 passwordLength,
                                      const void* password,
                                      Boolean resetSearchList);

@interface PasswordNotKnownView ()
@property IBOutlet NSTextField *password;
@property IBOutlet NSButton *okButton;
@property IBOutlet NSProgressIndicator *spinner;
@end

@implementation PasswordNotKnownView

- (void)updatePassword:(NSString *)inPassword {
  dispatch_async(dispatch_get_main_queue(), ^{
    [self.password setStringValue:inPassword];
    [self.password setEnabled:NO];
  });
}

- (NSArray *)textFields {
  return @[ self.password ];
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

  if (!ValidateLoginPassword(self.password.stringValue)) {
    [self badPasswordField:self.password];
    return;
  }

  dispatch_async(dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_BACKGROUND, 0), ^{
    OSStatus ret = [self resetKeychainWithPassword:self.password.stringValue];
    NSLog(@"KeychainMinder Reset: %d", ret);
    [NSApp terminate:sender];
  });
}

- (OSStatus)resetKeychainWithPassword:(NSString *)password {
  return SecKeychainResetLogin((UInt32)password.length, [password UTF8String], YES);
}


@end
