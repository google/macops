/*

 Plan B
 PBConnectionDelegate.m

 Copyright 2014 Google Inc.

 Licensed under the Apache License, Version 2.0 (the "License"); you may not
 use this file except in compliance with the License.  You may obtain a copy
 of the License at

 http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
 License for the specific language governing permissions and limitations under
 the License.

*/

// This file is auto-generated during every build from roots.pem.
#include "roots.pem.h"

#import "PBCertificate.h"
#import "PBConnectionDelegate.h"
#import "PBDERDecoder.h"
#import "PBLogging.h"

NSString *const kConnectionDelegateHost = @"mac.internal.megacorp.com";
const char *kConnectionDelegatePackageBase = "pkgs";
const char *kConnectionDelegateScheme = "https";

@implementation PBConnectionDelegate {
  SecIdentityRef _foundIdentity;
  ConnectionDelegateFinishedHandler _downloadFinishedHandler;
}

// Designated initializer, pass in finishedHandler block when initializing this delegate.
- (instancetype)initWithDownloadDir:(NSString *)downloadDir
                    finishedHandler:(ConnectionDelegateFinishedHandler)handler {
  self = [super init];

  if (self) {
    _downloadDir = [downloadDir copy];
    _downloadFinishedHandler = [handler copy];

    if (![_downloadDir length] || !_downloadFinishedHandler) {
      return nil;
    }
  }

  return self;
}

- (void)connection:(NSURLConnection *)connection
    willSendRequestForAuthenticationChallenge:(NSURLAuthenticationChallenge *)challenge {

  NSURLProtectionSpace *protectionSpace = challenge.protectionSpace;

  if (![protectionSpace.protocol isEqual:NSURLProtectionSpaceHTTPS]) {
    PBLog(@"Error: %@ is not a secure protocol", protectionSpace.protocol);
    [challenge.sender cancelAuthenticationChallenge:challenge];
    return;
  }

  if (![protectionSpace.host isEqual:kConnectionDelegateHost]) {
    PBLog(@"Error: %@ does not match expected host", protectionSpace.host);
    [challenge.sender cancelAuthenticationChallenge:challenge];
    return;
  }

  if (!protectionSpace.receivesCredentialSecurely) {
    PBLog(@"Error: secure authentication or protocol cannot be established");
    [challenge.sender cancelAuthenticationChallenge:challenge];
    return;
  }

  NSString *authMethod = [protectionSpace authenticationMethod];
  NSURLCredential *cred;

  if (authMethod == NSURLAuthenticationMethodServerTrust) {
    PBLog(@"Connection requires server trust authentication");
    cred = [self serverCredentialForProtectionSpace:protectionSpace];
    if (cred) {
      [challenge.sender useCredential:cred forAuthenticationChallenge:challenge];
      return;
    } else {
      [challenge.sender cancelAuthenticationChallenge:challenge];
      return;
    }
  } else if (authMethod == NSURLAuthenticationMethodClientCertificate) {
    PBLog(@"Connection requires client certificate authentication");
    cred = [self clientCredentialForProtectionSpace:protectionSpace];
    if (cred) {
      [challenge.sender useCredential:cred forAuthenticationChallenge:challenge];
      return;
    } else {
      [challenge.sender cancelAuthenticationChallenge:challenge];
      return;
    }
  } else {
    [challenge.sender cancelAuthenticationChallenge:challenge];
    return;
  }
}

- (void)connection:(NSURLConnection *)connection didFailWithError:(NSError *)error {
  PBLog(@"Error: connection failed: %@", [error localizedDescription]);

  if (_fileHandle) {
    NSError *fmError = nil;

    if (![[NSFileManager defaultManager] removeItemAtPath:_path
                                                    error:&fmError]) {
      PBLog(@"Error: could not delete temporary file: %@", fmError);
    }
  }

  _path = nil;
  [self connectionFinished];
}

- (void)connectionDidFinishLoading:(NSURLConnection *)connection {
  [self connectionFinished];
}

- (void)connectionFinished {
  // Close the file handle.
  [_fileHandle closeFile];
  _fileHandle = nil;

  // Save copy of the finished handler.
  ConnectionDelegateFinishedHandler handler = _downloadFinishedHandler;

  // Delete the finished handler and file path.
  _downloadFinishedHandler = nil;
  handler(_path);
  _path = nil;
}

- (void)connection:(NSURLConnection *)connection didReceiveResponse:(NSURLResponse *)response {
  long responseCode = [(NSHTTPURLResponse *)response statusCode];

  if (responseCode != 200) {
    PBLog(@"Error: unexpected response from server: %ld", responseCode);
    return;
  }

  if (_fileHandle) {
    // Reset any accumulated file data, in case this delegate method has been called again.
    [_fileHandle seekToFileOffset:0];
  } else {
    _path = [_downloadDir stringByAppendingPathComponent:[response suggestedFilename]];
    PBLog(@"Saving disk image to %@", _path);
    NSError *err;

    BOOL succeeded = [[NSData data] writeToFile:_path
                                        options:0
                                          error:&err];
    if (!succeeded) {
      PBLog(@"Error: could not save disk image: %@", err);
    } else {
      NSDictionary *fileAttributes = @{ NSFilePosixPermissions : @(0644),
                                        NSFileOwnerAccountName : @"root",
                                        NSFileGroupOwnerAccountName : @"wheel" };

      if (![[NSFileManager defaultManager] setAttributes:fileAttributes
                                            ofItemAtPath:_path
                                                   error:&err]) {
        PBLog(@"Error: could not set %@ file attributes: %@", _path, err);
        return;
      }

      _fileHandle = [NSFileHandle fileHandleForWritingAtPath:_path];
    }
  }

}

- (void)connection:(NSURLConnection *)connection didReceiveData:(NSData *)data {
  if (!_fileHandle) {
    PBLog(@"No file handle!");
    return;
  }

  [_fileHandle writeData:data];
}

#pragma mark Private Helpers for connection:willSendRequestForAuthenticationChallenge:

- (NSURLCredential *)clientCredentialForProtectionSpace:(NSURLProtectionSpace *)protectionSpace {
  // SecItemCopyMatching ignores kSecMatchIssuers on OS X so this actually ends up returning all
  // issuers. We still ask SecItemCopyMatching to filter the issuers in case a future version of
  // OS X filters the list correctly, in which case our manual filtering will have less work to
  // do.
  CFArrayRef cfIdentities = NULL;
  __block OSStatus err = noErr;

  err = SecItemCopyMatching((__bridge CFDictionaryRef) @{
      (__bridge id)kSecClass:        (__bridge id)kSecClassIdentity,
      (__bridge id)kSecMatchLimit:   (__bridge id)kSecMatchLimitAll,
      (__bridge id)kSecMatchIssuers: protectionSpace.distinguishedNames,
      (__bridge id)kSecReturnRef:  @YES,
  }, (CFTypeRef *)&cfIdentities);

  NSArray *identities = CFBridgingRelease(cfIdentities);

  if (err != errSecSuccess) {
    PBLog(@"Failed to load identities, SecItemCopyMatching returned: %d", (int)err);
    return nil;
  }

  // Manually iterate through available identities to find one with an allowed issuer.
  [identities enumerateObjectsUsingBlock:^(id obj, NSUInteger idx, BOOL *stop) {
      SecIdentityRef identityRef = (__bridge SecIdentityRef)obj;

      SecCertificateRef certificate = NULL;
      err = SecIdentityCopyCertificate(identityRef, &certificate);
      if (err != errSecSuccess) {
        PBLog(@"Failed to read certificate data: %d. Skipping identity", (int)err);
        return;
      }

      // Due to another bug in OS X, we can't just compare the kSecIssuer attribute with
      // the distinguished names provided by NSURLProtectionSpace as the distinguished names
      // of the issuer in the keychain have had their case changed. Instead, use PBCertificate
      // to parse the cert into readable fields, use PBDERDecoder to parse the distinguished
      // names array and compare the two.
      PBCertificate *clientCert = [[PBCertificate alloc] initWithSecCertificateRef:certificate];
      CFRelease(certificate);

      for (NSData *allowedIssuer in protectionSpace.distinguishedNames) {
        PBDERDecoder *decoder = [[PBDERDecoder alloc] initWithData:allowedIssuer];
        if (!decoder) continue;
        if ([clientCert.issuerCommonName isEqual:decoder.commonName] &&
            [clientCert.issuerCountryName isEqual:decoder.countryName] &&
            [clientCert.issuerOrgName isEqual:decoder.organizationName] &&
            [clientCert.issuerOrgUnit isEqual:decoder.organizationalUnit]) {
          PBLog(@"Found accepted client identity: %@", clientCert);
          _foundIdentity = identityRef;
          CFRetain(_foundIdentity);
          *stop = YES;
          return;
        }
      }
  }];

  if (_foundIdentity == NULL) {
    PBLog(@"Error: Failed to find valid client identity");
    return nil;
  }

  NSURLCredential *cred =
      [NSURLCredential credentialWithIdentity:_foundIdentity
                                 certificates:nil
                                  persistence:NSURLCredentialPersistenceForSession];
  return cred;
}

- (NSURLCredential *)serverCredentialForProtectionSpace:(NSURLProtectionSpace *)protectionSpace {
  SecTrustRef serverTrust = protectionSpace.serverTrust;
  if (serverTrust == NULL) {
    PBLog(@"Error: no trust information available");
    return nil;
  }

  // Read the embedded roots.pem into an NSString without copying an initialize an
  // array of PBCertificate objects from that pem.
  NSString *pem = [[NSString alloc] initWithBytesNoCopy:ROOTS_PEM
                                                 length:ROOTS_PEM_len
                                               encoding:NSASCIIStringEncoding
                                           freeWhenDone:NO];
  NSArray *certs = [PBCertificate certificatesFromPEM:pem];

  // Make a new array of the SecCertificateRef's from the PBCertificate's.
  NSMutableArray *certRefs = [[NSMutableArray alloc] initWithCapacity:certs.count];
  for (PBCertificate *cert in certs) {
    [certRefs addObject:(id)cert.certRef];
  }

  OSStatus err = noErr;
  // Set this array of certs as the anchors to trust.
  err = SecTrustSetAnchorCertificates(serverTrust, (__bridge CFArrayRef)certRefs);
  if (err != errSecSuccess) {
    PBLog(@"Error: could not set anchor certificates.");
    return nil;
  }

  // Evaluate the server's cert chain.
  SecTrustResultType result = kSecTrustResultInvalid;
  err = SecTrustEvaluate(protectionSpace.serverTrust, &result);
  if (err != errSecSuccess) {
    PBLog(@"Error: could not evaluate trust.");
    return nil;
  }

  // Print details about the server's leaf certificate.
  SecCertificateRef firstCert = SecTrustGetCertificateAtIndex(protectionSpace.serverTrust, 0);
  if (firstCert) {
    PBCertificate *cert = [[PBCertificate alloc] initWithSecCertificateRef:firstCert];
    PBLog(@"Server certificate details: CN: %@, Org: %@, OU: %@, ValidFrom: %@, ValidUntil: %@, "
          @"SHA1: %@, Issuer CN: %@",
          cert.commonName, cert.orgName, cert.orgUnit, cert.validFrom,
          cert.validUntil, cert.SHA1, cert.issuerCommonName);
  }

  // Having a trust level "unspecified" by the user is the usual result, described at
  //   https://developer.apple.com/library/mac/qa/qa1360
  if (result != kSecTrustResultProceed && result != kSecTrustResultUnspecified) {
    PBLog(@"Error: server isn't trusted. SecTrustResultType: %d", result);
    return nil;
  }

  NSURLCredential *cred = [NSURLCredential credentialForTrust:[protectionSpace serverTrust]];
  return cred;
}

@end

