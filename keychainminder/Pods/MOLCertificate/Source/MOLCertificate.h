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

#import <Foundation/Foundation.h>

/** An Objective-C wrapper around `SecCertificateRef` objects provided by the Security framework.

  Accessors are read-only properties and access to each property is cached for future use.
 
  `MOLCertificate` objects can be passed over an XPC connection freely, though the receiving
  end will not benefit from any previously cached properties and the underlying SecCertificateRef
  may be different.
*/
@interface MOLCertificate : NSObject <NSSecureCoding>

/**
  Initialize a `MOLCertificate` object with a valid `SecCertificateRef`.
 
  Designated initializer.

  @param certRef A valid `SecCertificateRef`, which will be retained.
*/
- (instancetype)initWithSecCertificateRef:(SecCertificateRef)certRef;

/**
  Initialize a `MOLCertificate` object with certificate data in DER format.

  @param certData DER-encoded certificate data.
  @return An initialized `MOLCertificate` or `nil` if the input is not a DER-encoded certificate.
*/
- (instancetype)initWithCertificateDataDER:(NSData *)certData;

/**
  Initialize a `MOLCertificate` object with certificate data in PEM format.
  If multiple PEM certificates exist within the string, the first is used.

  @param certData PEM-encoded certificate data.
  @return An initialized `MOLCertifcate` or `nil` if the input is not a PEM-encoded certificate.
*/
- (instancetype)initWithCertificateDataPEM:(NSString *)certData;

/**
  Returns an array of `MOLCertificate's` for all of the certificates in `pemData`.

  @param pemData PEM-encoded certificates.
  @return An array of `MOLCertificate` objects for each valid PEM in `pemData`.
*/
+ (NSArray *)certificatesFromPEM:(NSString *)pemData;

/**
  Access the underlying certificate ref.
 
  If you're planning on using the ref for a long time, you should
  CFRetain() it and CFRelease() it when you're finished.
*/
@property(readonly, nonatomic) SecCertificateRef certRef;

/**  SHA-1 hash of the certificate data. */
@property(readonly, nonatomic) NSString *SHA1;

/**  SHA-256 hash of the certificate data. */
@property(readonly, nonatomic) NSString *SHA256;

/**  Certificate data in DER format. */
@property(readonly, nonatomic) NSData *certData;

/**  Common Name e.g: "Software Signing" */
@property(readonly, nonatomic) NSString *commonName;

/**  Country Name e.g: "US" */
@property(readonly, nonatomic) NSString *countryName;

/**  Organization Name e.g: "Apple Inc." */
@property(readonly, nonatomic) NSString *orgName;

/**  Organizational Unit Name. Returns the first OU e.g: "Apple Software". */
@property(readonly, nonatomic) NSString *orgUnit;

/**  Organizational Unit Names. Returns an array of all OUs e.g: ("Apple Software", "Apple"). */
@property(readonly, nonatomic) NSArray *orgUnits;

/**  Is this cert able to issue certs? */
@property(readonly, nonatomic) BOOL isCA;

/**  The cert serial number. */
@property(readonly, nonatomic) NSString *serialNumber;

/**  Issuer common name. */
@property(readonly, nonatomic) NSString *issuerCommonName;

/**  Issuer country name. */
@property(readonly, nonatomic) NSString *issuerCountryName;

/**  Issuer organization name. */
@property(readonly, nonatomic) NSString *issuerOrgName;

/**  Issuer organizational unit. Returns the first issuer OU. */
@property(readonly, nonatomic) NSString *issuerOrgUnit;

/**  Issuer organizational units. Returns an array of all issuer OUs. */
@property(readonly, nonatomic) NSArray *issuerOrgUnits;

/**  Validity not before / valid from date. */
@property(readonly, nonatomic) NSDate *validFrom;

/**  Validity not after / valid until date. */
@property(readonly, nonatomic) NSDate *validUntil;

/**  NT Principal Name */
@property(readonly, nonatomic) NSString *ntPrincipalName;

/**  DNS Name. Returns the first DNS Name from the SAN */
@property(readonly, nonatomic) NSString *dnsName;

/**  DNS Names. Returns an array of all DNS Names from the SAN */
@property(readonly, nonatomic) NSArray *dnsNames;

@end
