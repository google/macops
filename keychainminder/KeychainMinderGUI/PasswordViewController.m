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

#import "PasswordViewController.h"

@import QuartzCore;

@implementation PasswordViewController

- (instancetype)init {
  return [super initWithNibName:NSStringFromClass([self class]) bundle:nil];
}

- (void)viewDidAppear {
  NSTextField *firstField = [[self textFields] firstObject];
  if ([firstField isKindOfClass:[NSTextField class]]) {
    [self.view.window makeFirstResponder:firstField];
  }
}

- (NSArray *)textFields {
  [self doesNotRecognizeSelector:_cmd];
  return nil;
}

- (void)beginProcessing {
  for (NSTextField *textField in [self textFields]) {
    if (![textField isKindOfClass:[NSTextField class]]) continue;
    textField.focusRingType = NSFocusRingTypeNone;
  }
}

- (void)endProcessing {
  for (NSTextField *textField in [self textFields]) {
    if (![textField isKindOfClass:[NSTextField class]]) continue;
    textField.focusRingType = NSFocusRingTypeDefault;
  }
}

- (CAAnimation *)makeShakeAnimation {
  CAKeyframeAnimation *animation = [CAKeyframeAnimation animation];
  animation.keyPath = @"position.x";
  animation.values = @[ @0, @10, @-10, @10, @-10, @10, @0 ];
  animation.keyTimes = @[ @0, @(1 / 6.0), @(2 / 6.0), @(3 / 6.0), @(4 / 6.0), @(5 / 6.0), @1 ];
  animation.duration = 0.6;
  animation.additive = YES;
  return animation;
}

- (void)badPasswordField:(NSTextField *)textField {
  [CATransaction begin];
  [CATransaction setCompletionBlock:^{
    [textField setStringValue:@""];
    [self endProcessing];
    [self.view.window makeFirstResponder:textField];
  }];
  [textField.layer addAnimation:[self makeShakeAnimation] forKey:@"shake"];
  [CATransaction commit];
}

@end
