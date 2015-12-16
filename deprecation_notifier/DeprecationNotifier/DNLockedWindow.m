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

#import "DNLockedWindow.h"

@implementation DNLockedWindow

- (id)initWithContentRect:(NSRect)contentRect
                styleMask:(NSUInteger)windowStyle
                  backing:(NSBackingStoreType)bufferingType
                    defer:(BOOL)deferCreation {
  self = [super initWithContentRect:contentRect
                          styleMask:windowStyle
                            backing:bufferingType
                              defer:deferCreation];
  if (self) {
    [self setAlphaValue:0.80];
    [self setBackgroundColor:[NSColor blackColor]];
    [self setCanHide:NO];
    [self setCollectionBehavior:NSWindowCollectionBehaviorDefault];
    [self setHasShadow:YES];
    [self setHidesOnDeactivate:NO];
    [self setLevel:NSScreenSaverWindowLevel];
    [self setReleasedWhenClosed:NO];
  }
  return self;
}

- (BOOL)canBecomeKeyWindow { return YES; }
- (BOOL)canBecomeMainWindow { return YES; }

+ (DNLockedWindow *)windowWithFrame:(NSRect)frame {
  return [[self alloc] initWithContentRect:frame
                                 styleMask:NSBorderlessWindowMask
                                   backing:NSBackingStoreBuffered
                                     defer:NO];
}

@end
