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

#import "MOLCertificate.h"

#import <CommonCrypto/CommonDigest.h>
#import <Security/Security.h>

@interface MOLCertificate ()
///  A container for cached property values
@property NSMutableDictionary *memoizedData;
@end

@implementation MOLCertificate

static NSString *const kCertDataKey = @"certData";

#pragma mark Init/Dealloc

- (instancetype)initWithSecCertificateRef:(SecCertificateRef)certRef {
  self = [super init];
  if (self) {
    _certRef = certRef;
    CFRetain(_certRef);
  }
  return self;
}

- (instancetype)initWithCertificateDataDER:(NSData *)certData {
  SecCertificateRef cert = SecCertificateCreateWithData(NULL, (__bridge CFDataRef)certData);

  if (cert) {
    // Despite the header file claiming that SecCertificateCreateWithData will return NULL if
    // @c certData doesn't contain a valid DER-encoded X509 cert, this isn't always true.
    // radar://problem/16124651
    // To workaround, check that the certificate serial number can be retrieved. According to
    // RFC5280, the serial number field is required.
    NSData *ser = CFBridgingRelease(SecCertificateCopySerialNumber(cert, NULL));
    if (ser) {
      self = [self initWithSecCertificateRef:cert];
    } else {
      self = nil;
    }
    CFRelease(cert);  // was retained in initWithSecCertificateRef
  } else {
    self = nil;
  }

  return self;
}

- (instancetype)initWithCertificateDataPEM:(NSString *)certData {
  // Find the PEM and extract the Base64-encoded DER data from within
  NSScanner *scanner = [NSScanner scannerWithString:certData];
  NSString *base64der;

  // Locate and parse DER data into base64der
  [scanner scanUpToString:@"-----BEGIN CERTIFICATE-----" intoString:NULL];
  if (!([scanner scanString:@"-----BEGIN CERTIFICATE-----" intoString:NULL] &&
        [scanner scanUpToString:@"-----END CERTIFICATE-----" intoString:&base64der] &&
        [scanner scanString:@"-----END CERTIFICATE-----" intoString:NULL])) {
    return nil;
  }

  // Base64-decode the DER
  SecTransformRef transform = SecDecodeTransformCreate(kSecBase64Encoding, NULL);
  if (!transform) return nil;
  NSData *input = [base64der dataUsingEncoding:NSUTF8StringEncoding];
  NSData *output = nil;

  if (SecTransformSetAttribute(transform,
                               kSecTransformInputAttributeName,
                               (__bridge CFDataRef)input,
                               NULL)) {
    output = CFBridgingRelease(SecTransformExecute(transform, NULL));
  }
  if (transform) CFRelease(transform);

  return [self initWithCertificateDataDER:output];
}

+ (NSArray *)certificatesFromPEM:(NSString *)pemData {
  NSScanner *scanner = [NSScanner scannerWithString:pemData];
  NSMutableArray *certs = [[NSMutableArray alloc] init];

  while (YES) {
    NSString *curCert;

    [scanner scanUpToString:@"-----BEGIN CERTIFICATE-----" intoString:NULL];
    [scanner scanUpToString:@"-----END CERTIFICATE-----" intoString:&curCert];

    if (!curCert) break;

    curCert = [curCert stringByAppendingString:@"-----END CERTIFICATE-----"];
    MOLCertificate *cert = [[MOLCertificate alloc] initWithCertificateDataPEM:curCert];

    if (!cert) continue;

    [certs addObject:cert];
  }

  return certs;
}

- (instancetype)init {
  [self doesNotRecognizeSelector:_cmd];
  return nil;
}

- (void)dealloc {
  if (_certRef) CFRelease(_certRef);
}

#pragma mark Equality & description

- (BOOL)isEqual:(id)other {
  if (self == other) return YES;
  if (![other isKindOfClass:[MOLCertificate class]]) return NO;

  MOLCertificate *o = other;
  return [self.certData isEqual:o.certData];
}

- (NSUInteger)hash {
  return [self.certData hash];
}

- (NSString *)description {
  return
      [NSString stringWithFormat:@"/O=%@/OU=%@/CN=%@", self.orgName, self.orgUnit, self.commonName];
}

#pragma mark NSSecureCoding

+ (BOOL)supportsSecureCoding {
  return YES;
}

- (void)encodeWithCoder:(NSCoder *)coder {
  [coder encodeObject:self.certData forKey:kCertDataKey];
}

- (instancetype)initWithCoder:(NSCoder *)decoder {
  NSData *certData = [decoder decodeObjectOfClass:[NSData class] forKey:kCertDataKey];
  if ([certData length] == 0) return nil;
  SecCertificateRef cert = SecCertificateCreateWithData(NULL, (__bridge CFDataRef)certData);
  self = [self initWithSecCertificateRef:cert];
  if (cert) CFRelease(cert);
  return self;
}

#pragma mark Private Accessors

/**
  For a given selector, caches the value that selector would return on subsequent invocations,
  using the provided block to get the value on the first invocation.

  Assumes the selector's value will never change.
*/
- (id)memoizedSelector:(SEL)selector forBlock:(id (^)(void))block {
  NSString *selName = NSStringFromSelector(selector);

  if (!self.memoizedData) {
    self.memoizedData = [NSMutableDictionary dictionary];
  }

  if (!self.memoizedData[selName]) {
    id val = block();
    if (val) {
      self.memoizedData[selName] = val;
    } else {
      self.memoizedData[selName] = [NSNull null];
    }
  }

  // Return the value if there is one, or nil if the value is NSNull
  return self.memoizedData[selName] != [NSNull null] ? self.memoizedData[selName] : nil;
}

- (NSDictionary *)allCertificateValues {
  return [self memoizedSelector:_cmd forBlock:^id{
      return CFBridgingRelease(SecCertificateCopyValues(self.certRef, NULL, NULL));
  }];
}

- (NSDictionary *)x509SubjectName {
  return [self memoizedSelector:_cmd forBlock:^id{
      return [self allCertificateValues][(__bridge NSString *)kSecOIDX509V1SubjectName];
  }];
}

- (NSDictionary *)x509IssuerName {
  return [self memoizedSelector:_cmd forBlock:^id{
      return [self allCertificateValues][(__bridge NSString *)kSecOIDX509V1IssuerName];
  }];
}

- (NSDictionary *)x509SubjectAltName {
    return [self memoizedSelector:_cmd forBlock:^id{
        return [self allCertificateValues][(__bridge NSString *)kSecOIDSubjectAltName];
    }];
}

/**
  Retrieve the value with the specified label from the X509 dictionary provided

  @param desiredLabel The label you want, e.g: kSecOIDOrganizationName.
  @param dict The dictionary to look in (Subject, Issuer or SAN)
  @return An `NSString`, the value for the specified label.
*/
- (NSString *)x509ValueForLabel:(NSString *)desiredLabel fromDictionary:(NSDictionary *)dict {
  @try {
    NSArray *valArray = dict[(__bridge NSString *)kSecPropertyKeyValue];

    for (NSDictionary *curCertVal in valArray) {
      NSString *valueLabel = curCertVal[(__bridge NSString *)kSecPropertyKeyLabel];
      if ([valueLabel isEqual:desiredLabel]) {
        return curCertVal[(__bridge NSString *)kSecPropertyKeyValue];
      }
    }
    return nil;
  }
  @catch (NSException *e) {
    return nil;
  }
}

/**
  Retrieve the list with the specified label from the X509 dictionary provided

  @param desiredLabel The label you want, e.g: DNS Name.
  @param dict The dictionary to look in (SAN)
  @return An `NSString`, the value for the specified label.
*/
- (NSArray *)x509ListForLabel:(NSString *)desiredLabel fromDictionary:(NSDictionary *)dict {
  @try {
    NSArray *valArray = dict[(__bridge NSString *)kSecPropertyKeyValue];
    NSMutableArray *retArray = [[NSMutableArray alloc] init];
    
    for (NSDictionary *curCertVal in valArray) {
      NSString *valueLabel = curCertVal[(__bridge NSString *)kSecPropertyKeyLabel];
      if ([valueLabel isEqual:desiredLabel]) {
        [retArray addObject:curCertVal[(__bridge NSString *)kSecPropertyKeyValue]];
      }
    }
    return (retArray.count == 0) ? nil : (NSArray *)retArray;
  }
  @catch (NSException *e) {
    return nil;
  }
}

/**
  Retrieve the specified date from the certificate's values and convert from a reference date
  to an NSDate object.

  @param key The identifier for the date: e.g. `kSecOIDX509V1ValiditityNotBefore`
  @return An `NSDate` representing the date and time the certificate is valid from or expires.
*/
- (NSDate *)dateForX509Key:(NSString *)key {
  NSDictionary *curCertVal = [self allCertificateValues][key];
  NSNumber *value = curCertVal[(__bridge NSString *)kSecPropertyKeyValue];

  NSTimeInterval interval = [value doubleValue];
  if (interval) {
    return [NSDate dateWithTimeIntervalSinceReferenceDate:interval];
  }

  return nil;
}

#pragma mark Public Accessors

- (NSString *)SHA1 {
  return [self memoizedSelector:_cmd forBlock:^id{
      NSMutableData *SHA1Buffer = [[NSMutableData alloc] initWithCapacity:CC_SHA1_DIGEST_LENGTH];

      CC_SHA1([self.certData bytes], (CC_LONG)[self.certData length], [SHA1Buffer mutableBytes]);

    const unsigned char *bytes = (const unsigned char *)[SHA1Buffer bytes];
    NSMutableString *hexDigest = [NSMutableString stringWithCapacity:CC_SHA1_DIGEST_LENGTH * 2];
    for (int i = 0; i < CC_SHA1_DIGEST_LENGTH; i++) {
      [hexDigest appendFormat:@"%02x", bytes[i]];
    }

    return hexDigest;
  }];
}

- (NSString *)SHA256 {
  return [self memoizedSelector:_cmd forBlock:^id{
    NSMutableData *SHA256Buffer = [[NSMutableData alloc] initWithCapacity:CC_SHA256_DIGEST_LENGTH];

    CC_SHA256([self.certData bytes], (CC_LONG)[self.certData length], [SHA256Buffer mutableBytes]);

    const unsigned char *bytes = (const unsigned char *)[SHA256Buffer bytes];
    NSMutableString *hexDigest = [NSMutableString stringWithCapacity:CC_SHA256_DIGEST_LENGTH * 2];
    for (int i = 0; i < CC_SHA256_DIGEST_LENGTH; i++) {
      [hexDigest appendFormat:@"%02x", bytes[i]];
    }

    return hexDigest;
  }];
}

- (NSData *)certData {
  return CFBridgingRelease(SecCertificateCopyData(self.certRef));
}

- (NSString *)commonName {
  return [self memoizedSelector:_cmd forBlock:^id{
    CFStringRef commonName = NULL;
    SecCertificateCopyCommonName(self.certRef, &commonName);
    return CFBridgingRelease(commonName);
  }];
}

- (NSString *)countryName {
  return [self memoizedSelector:_cmd forBlock:^id{
    return [self x509ValueForLabel:(__bridge NSString *)kSecOIDCountryName
                    fromDictionary:[self x509SubjectName]];
  }];
}

- (NSString *)orgName {
  return [self memoizedSelector:_cmd forBlock:^id{
    return [self x509ValueForLabel:(__bridge NSString *)kSecOIDOrganizationName
                    fromDictionary:[self x509SubjectName]];
  }];
}

- (NSString *)orgUnit {
  return [self memoizedSelector:_cmd forBlock:^id{
    return [[self orgUnits] firstObject];
  }];
}

- (NSString *)orgUnits {
  return [self memoizedSelector:_cmd forBlock:^id{
    return [self x509ListForLabel:(__bridge NSString *)kSecOIDOrganizationalUnitName
                   fromDictionary:[self x509SubjectName]];
  }];
}

- (NSDate *)validFrom {
  return [self memoizedSelector:_cmd forBlock:^id{
    return [self dateForX509Key:(__bridge NSString *)kSecOIDX509V1ValidityNotBefore];
  }];
}

- (NSDate *)validUntil {
  return [self memoizedSelector:_cmd forBlock:^id{
    return [self dateForX509Key:(__bridge NSString *)kSecOIDX509V1ValidityNotAfter];
  }];
}

- (NSString *)issuerCommonName {
  return [self memoizedSelector:_cmd forBlock:^id{
    return [self x509ValueForLabel:(__bridge NSString *)kSecOIDCommonName
                    fromDictionary:[self x509IssuerName]];
  }];
}

- (NSString *)issuerCountryName {
  return [self memoizedSelector:_cmd forBlock:^id{
    return [self x509ValueForLabel:(__bridge NSString *)kSecOIDCountryName
                    fromDictionary:[self x509IssuerName]];
  }];
}

- (NSString *)issuerOrgName {
  return [self memoizedSelector:_cmd forBlock:^id{
    return [self x509ValueForLabel:(__bridge NSString *)kSecOIDOrganizationName
                    fromDictionary:[self x509IssuerName]];
  }];
}

- (NSString *)issuerOrgUnit {
  return [self memoizedSelector:_cmd forBlock:^id{
    return [[self issuerOrgUnits] firstObject];
  }];
}

- (NSArray *)issuerOrgUnits {
  return [self memoizedSelector:_cmd forBlock:^id{
    return [self x509ListForLabel:(__bridge NSString *)kSecOIDOrganizationalUnitName
                   fromDictionary:[self x509IssuerName]];
  }];
}

- (BOOL)isCA {
  return [[self memoizedSelector:_cmd forBlock:^id{
    NSDictionary *dict = [self allCertificateValues][(__bridge NSString *)kSecOIDBasicConstraints];
    return [self x509ValueForLabel:@"Certificate Authority" fromDictionary:dict];
  }] isEqual:@"Yes"];
}

- (NSString *)serialNumber {
  return [self memoizedSelector:_cmd forBlock:^id{
    NSDictionary *dict = [self allCertificateValues][(__bridge NSString *)kSecOIDX509V1SerialNumber];
    return dict[(__bridge NSString *)kSecPropertyKeyValue];
  }];
}

- (NSString *)ntPrincipalName {
  return [self memoizedSelector:_cmd forBlock:^id{
    return [self x509ValueForLabel:(__bridge NSString *)kSecOIDMS_NTPrincipalName
                    fromDictionary:[self x509SubjectAltName]];
  }];
}

- (NSString *)dnsName {
  return [self memoizedSelector:_cmd forBlock:^id{
    return [[self dnsNames] firstObject];
  }];
}

- (NSArray *)dnsNames {
  return [self memoizedSelector:_cmd forBlock:^id{
    return [self x509ListForLabel:@"DNS Name" fromDictionary:[self x509SubjectAltName]];
  }];
}

@end
