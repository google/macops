//
//  KeychainMinderAgent.m
//  KeychainMinderAgent
//
//  Created by Burgin, Thomas (NIH/CIT) [C] on 10/27/15.
//  Copyright (c) 2015 Google Inc. All rights reserved.
//

#import "KeychainMinderAgent.h"
#import <MOLCertificate/MOLCertificate.h>
#import <MOLCodesignChecker/MOLCodesignChecker.h>

@implementation KeychainMinderAgent

- (id)init {
  self = [super init];
  if (self != nil) {
    // Set up our XPC listener to handle requests on our Mach service.
    self->_listener = [[NSXPCListener alloc] initWithMachServiceName:
                       kKeychainMinderAgentMachServiceName];
    self->_listener.delegate = self;
  }
  return self;
}

- (void)run
{
  // Tell the XPC listener to start processing requests.
  [self.listener resume];
  
  // Run the run loop forever.
  [[NSRunLoop currentRunLoop] run];
}

- (BOOL)listener:(NSXPCListener *)listener shouldAcceptNewConnection:(NSXPCConnection *)newConnection {
  assert(listener == self.listener);
  #pragma unused(listener)
  assert(newConnection != nil);
  
  pid_t pid = newConnection.processIdentifier;
  
  MOLCodesignChecker *selfCS = [[MOLCodesignChecker alloc] initWithSelf];
  MOLCodesignChecker *otherCS = [[MOLCodesignChecker alloc] initWithPID:pid];
  
  // Add an exemption for Apple Signed Security.framework items
  MOLCodesignChecker *appleCS = [[MOLCodesignChecker alloc] initWithBinaryPath:@"/System/Library/Frameworks/Security.framework"];
  
  if ([otherCS signingInformationMatches:selfCS] || [otherCS signingInformationMatches:appleCS]) {
  
    newConnection.exportedInterface = [NSXPCInterface interfaceWithProtocol:
                                       @protocol(KeychainMinderAgentProtocol)];
    newConnection.exportedObject = self;
    [newConnection resume];
    return YES;
  }
  return NO;
}

- (void)setPassword:(NSString *)inPassword withReply:(void (^)(BOOL))reply {
  _password = [[NSString alloc] initWithString:inPassword];
  reply(_password != nil);
}

- (void)getPasswordWithReply:(void (^)(NSString *))reply {
  reply(_password);
}

- (void)clearPassword {
  _password = nil;
}

@end
