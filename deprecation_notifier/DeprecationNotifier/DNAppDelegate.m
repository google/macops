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

#import "DNAppDelegate.h"

@interface DNAppDelegate ()

@property NSTimer *countdownTimer;
@property NSTimer *reopenTimer;

@property NSMutableArray *windows;

@property float countdownTime;
@property NSString *timeRemaining;
@property NSString *deprecationMessage;
@property NSWindow *window;

@end

@implementation DNAppDelegate

// These are the names of the keys in the configuration plist
static NSString * const kWindowTimeoutKey = @"WindowTimeOut";
static NSString * const kMaxWindowTimeoutKey = @"MaxWindowTimeOut";
static NSString * const kTimeoutMultiplierKey = @"TimeOutMultiplier";
static NSString * const kRenotifyPeriodKey = @"RenotifyPeriod";


- (void)applicationDidFinishLaunching:(NSNotification *)aNotification {
  NSString *expectedVersion = NSLocalizedString(@"expectedVersion", @"");
  NSString *expectedBuildsStr = NSLocalizedString(@"expectedBuilds", @"");
  NSString *buildsKey = @"expectedBuilds";
  NSString *builds = NSLocalizedString(buildsKey, @"");
  NSSet *expectedBuilds = [NSSet setWithArray:[builds componentsSeparatedByString:@","]];
  if (!expectedBuilds.count || [expectedBuilds containsObject:buildsKey]) expectedBuilds = nil;

  NSDictionary *systemVersionDictionary = [NSDictionary dictionaryWithContentsOfFile:
                                              @"/System/Library/CoreServices/SystemVersion.plist"];
  NSString *systemVersion = systemVersionDictionary[@"ProductVersion"];
  NSString *systemBuild = systemVersionDictionary[@"ProductBuildVersion"];

  NSArray *systemVersionArray = [systemVersion componentsSeparatedByString:@"."];
  if (systemVersionArray.count == 2) {
      systemVersionArray = [systemVersionArray arrayByAddingObject:@"0"];
    }

  NSArray *expectedVersionArray = [expectedVersion componentsSeparatedByString:@"."];
  if (expectedVersionArray.count == 2) {
      expectedVersionArray = [expectedVersionArray arrayByAddingObject:@"0"];
  }

  NSLog(@"Info: System version: %@ %@", systemVersion, systemBuild);
  NSLog(@"Info: Expected version: %@ %@", expectedVersion, expectedBuildsStr);
  if ([expectedVersionArray isEqualToArray:systemVersionArray]) {
    NSLog(@"Checking: running OS is equal to %@, checking build version", expectedVersion);
    if (!expectedBuilds.count) {
      NSLog(@"Exiting: No preferred build, so considered equal");
      [NSApp terminate:nil];
    }
    if ([expectedBuilds containsObject:systemBuild]) {
      NSLog(@"Exiting: OS build is one of the expected builds %@", expectedBuilds);
      [NSApp terminate:nil];
    }
    NSLog(@"Checking: OS build not found in expected builds %@", expectedBuilds);
  } else if ([systemVersionArray[0] intValue] < [expectedVersionArray[0] intValue] ||
            [systemVersionArray[1] intValue] < [expectedVersionArray[1] intValue] ||
            [systemVersionArray[2] intValue] < [expectedVersionArray[2] intValue]) {
    NSLog(@"Checking: OS build is lower than required");
  } else {
    NSLog(@"Exiting: OS build is greater than required");
    [NSApp terminate:nil];
  }

  [[NSUserDefaults standardUserDefaults] synchronize];
  [[NSUserDefaults standardUserDefaults] registerDefaults:@{
      kWindowTimeoutKey: @([NSLocalizedString(@"initialTimeout", @"") intValue]),
      kMaxWindowTimeoutKey: @([NSLocalizedString(@"maxWindowTimeout", @"") intValue]),
      kTimeoutMultiplierKey: @([NSLocalizedString(@"timeoutMultiplier", @"") floatValue]),
      kRenotifyPeriodKey: @([NSLocalizedString(@"renotifyPeriod", @"") intValue]),
  }];

  // Get this message from the .strings file for easier changing in the future
  self.deprecationMessage = NSLocalizedString(@"deprecationMsg", @"");

  self.windows = [[NSMutableArray alloc] init];

  // Create a window on every screen
  for (NSScreen *thisScreen in [[NSScreen screens] reverseObjectEnumerator]) {
    NSWindow *window = [DNLockedWindow windowWithFrame:[thisScreen frame]];
    [self.windows addObject:window];

    // Make view and add to window. View is now full size of window.
    NSView *customView = [[NSView alloc] initWithFrame:NSMakeRect(0, 0, 0, 0)];
    [window setContentView:customView];

    NSBox *box = [[NSBox alloc] initWithFrame:NSMakeRect(
        (NSWidth(customView.frame) - 700) / 2, (NSHeight(customView.frame) - 450) / 2, 700, 450)];
    box.boxType = NSBoxCustom;
    box.transparent = YES;
    [customView addSubview:box];

    // Add countdown timer label
    NSTextField *countdownLabel = [[NSTextField alloc] initWithFrame:NSMakeRect(15, 300, 670, 120)];
    [countdownLabel bind:@"value"
                toObject:self
             withKeyPath:@"timeRemaining"
                 options:@{NSConditionallySetsEditableBindingOption: @NO}];
    [countdownLabel bind:@"accessibilityLabel"
                toObject:self
             withKeyPath:@"timeRemaining"
                 options:@{NSConditionallySetsEditableBindingOption: @NO}];
    countdownLabel.bezeled = NO;
    countdownLabel.drawsBackground = NO;
    countdownLabel.selectable = NO;
    countdownLabel.font = [NSFont fontWithName:@"HelveticaNeue-Bold" size:100.0];
    countdownLabel.textColor = [NSColor highlightColor];
    countdownLabel.alignment = NSTextAlignmentCenter;
    countdownLabel.accessibilityElement = YES;
    [box addSubview:countdownLabel];

    // Add message label
    NSTextField *userMsgLabel = [[NSTextField alloc] initWithFrame:NSMakeRect(15, 40, 670, 220)];
    userMsgLabel.stringValue = self.deprecationMessage;
    userMsgLabel.bezeled = NO;
    userMsgLabel.drawsBackground = NO;
    userMsgLabel.selectable = NO;
    userMsgLabel.font = [NSFont fontWithName:@"HelveticaNeue-Light" size:22.0];
    userMsgLabel.textColor = [NSColor highlightColor];
    userMsgLabel.alignment = NSTextAlignmentCenter;
    userMsgLabel.accessibilityElement = YES;
    userMsgLabel.accessibilityLabel = userMsgLabel.stringValue;
    [box addSubview:userMsgLabel];

    // Now bring window to front and make this class the next responder in the chain
    [window makeKeyAndOrderFront:self];
    [window setNextResponder:(NSResponder *)self];
  }

  [self openCountdownWindow];
}

- (void)applicationWillTerminate:(NSNotification *)notification {
  [[NSUserDefaults standardUserDefaults] synchronize];
}

- (void)countDown {
  // Keep stealing focus..
  [NSApp activateIgnoringOtherApps:YES];

  self.countdownTime -= 0.1;

  // Update time remaining message
  self.timeRemaining = [NSString stringWithFormat:@"%i:%02i",
                           (int)self.countdownTime / 60, (int)self.countdownTime % 60];

  if (self.countdownTime < 1) {
    self.timeRemaining = @"Click to close";
    [self.countdownTimer invalidate];
  }
}

- (void)hideCountdownWindowReopen:(BOOL)reopen {
  // Stop the countdown timer
  [self.countdownTimer invalidate];

  // Hide window
  for (NSWindow *window in self.windows) {
    [window orderOut:nil];
  }

  // Show the instructions URL to the user
  NSURL *instURL = [NSURL URLWithString:NSLocalizedString(@"instructionURL", @"")];
  [[NSWorkspace sharedWorkspace] openURL:instURL];

  // Synchronize defaults in case Puppet has made changes
  NSUserDefaults *userDefaults = [NSUserDefaults standardUserDefaults];
  [userDefaults synchronize];

  // Update countdown
  float newTimeout = ([userDefaults floatForKey:kWindowTimeoutKey] *
                      [userDefaults floatForKey:kTimeoutMultiplierKey]);

  // Ensure timeout is not above max
  NSInteger maxTimeout = [userDefaults integerForKey:kMaxWindowTimeoutKey];
  if (newTimeout > maxTimeout) newTimeout = maxTimeout;

  [userDefaults setFloat:newTimeout forKey:kWindowTimeoutKey];
  [userDefaults synchronize];

  if (reopen) {
    // Start reopen timer
    long reopenTime = [userDefaults integerForKey:kRenotifyPeriodKey];
    NSLog(@"Will re-open in %ld seconds", reopenTime);
    self.reopenTimer = [NSTimer scheduledTimerWithTimeInterval:reopenTime
                                                        target:self
                                                      selector:@selector(openCountdownWindow)
                                                      userInfo:nil
                                                       repeats:NO];
  }
}

- (void)openCountdownWindow {
  // Start Kiosk Mode to disallow Expose and other such features
  @try {
      int kioskOptions = [NSLocalizedString(@"kioskModeSettings", @"") intValue];
      NSApplicationPresentationOptions options = kioskOptions;
      [NSApp setPresentationOptions:options];
  } @catch (NSException *exception) {
      NSLog(@"Error: Invalid combination of Kiosk Mode options.");
  }

  // Set the countdown time from the plist
  self.countdownTime = [[NSUserDefaults standardUserDefaults] floatForKey:kWindowTimeoutKey];

  // Start the countdown timer, once per 0.1 seconds
  self.countdownTimer = [NSTimer scheduledTimerWithTimeInterval:0.1
                                                         target:self
                                                       selector:@selector(countDown)
                                                       userInfo:nil
                                                        repeats:YES];
  // Show the windows on every screen
  for (NSWindow *window in self.windows) {
    [window makeKeyAndOrderFront:self];
  }
}

- (void)mouseDown:(NSEvent *)event {
  if (self.countdownTime < 1) {
    [self hideCountdownWindowReopen:YES];
  }
}

@end
