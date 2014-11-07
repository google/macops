//
//  DNAppDelegate.m
//  DeprecationNotifier
//

#import "DNAppDelegate.h"

@interface DNAppDelegate () {
  float _countdownTime;
  NSTimer *_countdownTimer;
  NSTimer *_reopenTimer;
  NSUserDefaults *_defaults;
  NSMutableArray *_windows;
  NSMutableString *_enteredKeys;
}

@property NSString *timeRemaining;
@property NSString *deprecationMessage;
@property NSWindow *window;
@property IBOutlet NSView *contentView;

@end

@implementation DNAppDelegate

- (void)applicationDidFinishLaunching:(NSNotification *)aNotification {
  NSString *expectedVersion = NSLocalizedString(@"expectedVersion", @"");
  NSDictionary *systemVersionDictionary = [NSDictionary dictionaryWithContentsOfFile:
                                              @"/System/Library/CoreServices/SystemVersion.plist"];
  NSString *systemVersion = systemVersionDictionary[@"ProductVersion"];

  NSArray *systemVersionArray = [systemVersion componentsSeparatedByString:@"."];
  NSArray *expectedVersionArray = [expectedVersion componentsSeparatedByString:@"."];

  if (systemVersionArray.count < 2 || expectedVersionArray.count < 2) {
    NSLog(@"Exiting: Error, unable to properly determine system version or expected version");
    [NSApp terminate:nil];
  } else if (([expectedVersionArray[0] intValue] <= [systemVersionArray[0] intValue]) &&
             ([expectedVersionArray[1] intValue] <= [systemVersionArray[1] intValue])) {
    NSLog(@"Exiting: OS is already %@ or greater", expectedVersion);
    [NSApp terminate:nil];
  }

  _defaults = [NSUserDefaults standardUserDefaults];
  [_defaults synchronize];
  [_defaults registerDefaults:[NSDictionary dictionaryWithObjectsAndKeys:
                                  INITIAL_TIMEOUT, KEY_TIMEOUT,
                                  INITIAL_MAXTIMEOUT, KEY_MAXTIMEOUT,
                                  INITIAL_TIMEOUTMULT, KEY_TIMEOUTMULT,
                                  INITIAL_RENOTIFY, KEY_RENOTIFY,
                                  nil]];

  // Get this message from the .strings file for easier changing in the future
  self.deprecationMessage = NSLocalizedString(@"deprecationMsg", @"");

  _windows = [[NSMutableArray alloc] init];

  // Create a window on every screen
  for (NSScreen *thisScreen in [[NSScreen screens] reverseObjectEnumerator]) {
    NSWindow *window = [DNLockedWindow windowWithFrame:[thisScreen frame]];
    [_windows addObject:window];

    [window setContentView:self.contentView];

    [window makeKeyAndOrderFront:self];
    [window setNextResponder:(NSResponder *)self];
  }

  [self openCountdownWindow];
}

- (void)applicationWillTerminate:(NSNotification *)notification {
  [_defaults synchronize];
}

- (void)countDown {
  // Keep stealing focus..
  [NSApp activateIgnoringOtherApps:YES];

  _countdownTime -= 0.1;

  // Update time remaining message
  self.timeRemaining = [NSString stringWithFormat:@"%i:%02i",
                        (int)_countdownTime / 60,
                        (int)_countdownTime % 60];

  if (_countdownTime < 1) {
    self.timeRemaining = @"Click to close";
  }
}

- (void)hideCountdownWindowReopen:(BOOL)reopen {
  // Stop the countdown timer
  [_countdownTimer invalidate];

  // Hide window
  for (NSWindow *window in _windows) {
    [window orderOut:nil];
  }

  // Synchronize defaults in case Puppet has made changes
  [_defaults synchronize];

  // Update countdown
  float newTimeOut = [_defaults floatForKey:KEY_TIMEOUT] * [_defaults floatForKey:KEY_TIMEOUTMULT];

  if (newTimeOut > [_defaults integerForKey:KEY_MAXTIMEOUT]) {
    [_defaults setFloat:[_defaults integerForKey:KEY_MAXTIMEOUT] forKey:KEY_TIMEOUT];
  } else {
    [_defaults setFloat:newTimeOut forKey:KEY_TIMEOUT];
  }
  [_defaults synchronize];

  if (reopen) {
    // Start reopen timer
    long reopen_time = [_defaults integerForKey:KEY_RENOTIFY];
    NSLog(@"Will re-open in %ld seconds", reopen_time);
    _reopenTimer = [NSTimer scheduledTimerWithTimeInterval:reopen_time
                                                    target:self
                                                  selector:@selector(openCountdownWindow)
                                                  userInfo:nil
                                                   repeats:NO];
  }
}

- (void)openCountdownWindow {
  // Show the instructions URL to the user
  NSURL *instURL = [NSURL URLWithString:NSLocalizedString(@"instructionURL", @"")];
  [[NSWorkspace sharedWorkspace] openURL:instURL];

  // Set the countdown time from the plist, plus 1 (as it'll be decremented in the countDown method)
  _countdownTime = [_defaults integerForKey:KEY_TIMEOUT] + 1;
  [self countDown];

  // Start the countdown timer, once per 0.1 seconds
  _countdownTimer = [NSTimer scheduledTimerWithTimeInterval:0.1
                                                     target:self
                                                   selector:@selector(countDown)
                                                   userInfo:nil
                                                    repeats:YES];
  // Show the windows on every screen
  for (NSWindow *window in _windows) {
    [window makeKeyAndOrderFront:nil];
  }
}

- (void)mouseDown:(NSEvent *)event {
  if (_countdownTime < 1) {
    [self hideCountdownWindowReopen:YES];
  }
}

@end
