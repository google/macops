//
//  DNLockedWindow.m
//  DeprecationNotifier
//

#import "DNLockedWindow.h"

@implementation DNLockedWindow

- (id)initWithContentRect:(NSRect)contentRect
                styleMask:(NSUInteger)windowStyle
                  backing:(NSBackingStoreType)bufferingType
                    defer:(BOOL)deferCreation {

  self = [super initWithContentRect:contentRect
                          styleMask:NSBorderlessWindowMask
                            backing:bufferingType
                              defer:deferCreation];

  if (self) {
    [self setLevel: NSScreenSaverWindowLevel];
    [self setAlphaValue:0.80];
    [self setBackgroundColor: [NSColor blackColor]];
    [self setHasShadow:YES];
    [self setReleasedWhenClosed:YES];
    [self setCanHide:NO];
    [self setHidesOnDeactivate:NO];
    [self setCollectionBehavior:NSWindowCollectionBehaviorCanJoinAllSpaces];
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
