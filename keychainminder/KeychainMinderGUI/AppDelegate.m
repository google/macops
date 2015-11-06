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

#import "AppDelegate.h"

#import "PasswordKnownView.h"
#import "PasswordNotKnownView.h"
#import "KeychainMinderAgentProtocol.h"

@import QuartzCore;

@interface AppDelegate ()
@property (weak) IBOutlet NSWindow *window;
@property (weak) IBOutlet NSView *viewArea;

@property (weak) IBOutlet NSImageView *imageView;

@property (weak) IBOutlet PasswordKnownView *knownView;
@property (weak) IBOutlet PasswordNotKnownView *notKnownView;

@property NSXPCConnection *connectionToService;
@property id remoteObject;
@end

@implementation AppDelegate

- (void)applicationWillFinishLaunching:(NSNotification *)notification {
  [self.window setLevel:NSScreenSaverWindowLevel];
  [self.window setMovable:NO];
  [self.window setCanBecomeVisibleWithoutLogin:YES];
  [self.window setCanHide:NO];
  
  self.connectionToService = [[NSXPCConnection alloc]
                              initWithMachServiceName:kKeychainMinderAgentMachServiceName
                                              options:NSXPCConnectionPrivileged];
  self.connectionToService.remoteObjectInterface = [NSXPCInterface interfaceWithProtocol:
                                                    @protocol(KeychainMinderAgentProtocol)];
  [self.connectionToService resume];
  self.remoteObject = [self.connectionToService
                       remoteObjectProxyWithErrorHandler:^(NSError *error) {
    NSLog(@"%@", [error description]);
  }];

  [self.window makeFirstResponder:nil];
  [NSApp activateIgnoringOtherApps:YES];

  NSLog(@"KeychainMinder launched for %@", NSUserName());
}

- (BOOL)applicationShouldTerminateAfterLastWindowClosed:(NSApplication *)sender {
  return YES;
}

- (void)updateIcon {
  [self.imageView setImage:[NSImage imageNamed:@"Keychain_Unlocked"]];
}

- (IBAction)passwordKnown:(id)sender {
  [self updateIcon];
  [[self.viewArea subviews] makeObjectsPerformSelector:@selector(removeFromSuperview)];
  [[self.viewArea animator] addSubview:self.knownView.view];
  [self.remoteObject getPasswordWithReply:^(NSString *inPassword) {
    if (inPassword) {
      [self.knownView updatePassword:inPassword];
    }
  }];
}

- (IBAction)passwordUnknown:(id)sender {
  [self updateIcon];
  [[self.viewArea subviews] makeObjectsPerformSelector:@selector(removeFromSuperview)];
  [[self.viewArea animator] addSubview:self.notKnownView.view];
  [self.remoteObject getPasswordWithReply:^(NSString *inPassword) {
    if (inPassword) {
      [self.notKnownView updatePassword:inPassword];
    }
  }];
}

-(void)applicationWillTerminate:(NSNotification *)notification {
  [self.remoteObject clearPassword];
  [self.connectionToService invalidate];
}

@end
