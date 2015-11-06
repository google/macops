//
//  KeychainMinderAgent.h
//  KeychainMinderAgent
//
//  Created by Burgin, Thomas (NIH/CIT) [C] on 10/27/15.
//  Copyright (c) 2015 Google Inc. All rights reserved.
//

#import <Foundation/Foundation.h>
#import "KeychainMinderAgentProtocol.h"

@interface KeychainMinderAgent : NSObject <NSXPCListenerDelegate, KeychainMinderAgentProtocol>

@property (atomic, strong, readwrite) NSXPCListener *listener;
@property (nonatomic, strong) NSString *password;

- (void)setPassword:(NSString *)inPassword withReply:(void (^)(BOOL))reply;
- (void)getPasswordWithReply:(void (^)(NSString *))reply;
- (void)clearPassword;
- (id)init;
- (void)run;

@end
