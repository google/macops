//
//  main.m
//  KeychainMinderAgent
//
//  Created by Burgin, Thomas (NIH/CIT) [C] on 10/27/15.
//  Copyright (c) 2015 Google Inc. All rights reserved.
//

#import <Foundation/Foundation.h>
#import "KeychainMinderAgent.h"

int main(int argc, char **argv) {
#pragma unused(argc)
#pragma unused(argv)
    
    @autoreleasepool {
        KeychainMinderAgent *keychainMinderAgent;
        if (!keychainMinderAgent) {
            keychainMinderAgent = [[KeychainMinderAgent alloc] init];
        }
        [keychainMinderAgent run];
    }
    
    return EXIT_FAILURE;
}

