//
//  DNAppDelegate.h
//  DeprecationNotifier
//

#import "DNLockedWindow.h"

#define KEY_TIMEOUT         @"WindowTimeOut"
#define INITIAL_TIMEOUT     [NSNumber numberWithInt:10]
#define KEY_MAXTIMEOUT      @"MaxWindowTimeOut"
#define INITIAL_MAXTIMEOUT  [NSNumber numberWithInt:300]
#define KEY_TIMEOUTMULT     @"TimeOutMultiplier"
#define INITIAL_TIMEOUTMULT [NSNumber numberWithFloat:1.1]
#define KEY_RENOTIFY        @"RenotifyPeriod"
#define INITIAL_RENOTIFY    [NSNumber numberWithInt:3600]


@interface DNAppDelegate : NSResponder <NSApplicationDelegate>
@end
