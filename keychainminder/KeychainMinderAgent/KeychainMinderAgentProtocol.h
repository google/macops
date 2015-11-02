//
//  KeychainMinderAgentProtocol.h
//  KeychainMinderAgent
//
//  Created by Burgin, Thomas (NIH/CIT) [C] on 10/27/15.
//  Copyright (c) 2015 Google Inc. All rights reserved.
//

#import <Foundation/Foundation.h>
#define kKeychainMinderAgentMachServiceName @"com.google.corp.KeychainMinderAgent"

@protocol KeychainMinderAgentProtocol

- (void)getPasswordWithReply:(void (^)(NSString *))reply;
- (void)setPassword:(NSString *)inPassword withReply:(void (^)(BOOL))reply;
- (void)clearPassword;

@end

