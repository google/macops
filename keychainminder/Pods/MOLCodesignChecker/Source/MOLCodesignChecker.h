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

@class MOLCertificate;

#import <Foundation/Foundation.h>

/**
  `MOLCodesignChecker` validates a binary (either on-disk or in memory) has been signed
  and if so allows for pulling out the certificates that were used to sign it.

  @warning When checking bundles this class will ignore non-code resources inside the bundle for
  validation purposes. This very dramatically speeds up validation but means that it is possible
  to tamper with resource files without this class noticing.
*/
@interface MOLCodesignChecker : NSObject

/**  The `SecStaticCodeRef` that this `MOLCodesignChecker` is wrapping. */
@property(readonly) SecStaticCodeRef codeRef;

/**
  A dictionary of raw signing information provided by the Security framework.
*/
@property(readonly) NSDictionary *signingInformation;

/**
  An array of `MOLCertificate` objects representing the chain that signed this binary.

  @see [MOLCertificate](http://cocoadocs.org/docsets/MOLCertificate)
*/
@property(readonly) NSArray *certificates;

/**
  The leaf certificate that this binary was signed with.

  @see [MOLCertificate](http://cocoadocs.org/docsets/MOLCertificate)
*/
@property(readonly, nonatomic) MOLCertificate *leafCertificate;

/** The on-disk path of this binary. */
@property(readonly, nonatomic) NSString *binaryPath;

/**
  Designated initializer

  @note Takes ownership of `codeRef`.

  @param codeRef A `SecStaticCodeRef` or `SecCodeRef` representing a binary.
  @return An initialized `MOLCodesignChecker` if the binary is validly signed, `nil` otherwise.
*/
- (instancetype)initWithSecStaticCodeRef:(SecStaticCodeRef)codeRef;

/**
  Initialize with a binary on disk.

  @note While the method name mentions binary path, it is possible to initialize with a bundle
  instead by passing the path to the root of the bundle.

  @param binaryPath Path to a binary file on disk.
  @return An initialized `MOLCodesignChecker` if file is signed binary, `nil` otherwise.
*/
- (instancetype)initWithBinaryPath:(NSString *)binaryPath;

/**
  Initialize with a running binary using its process ID.

  @param PID PID of a running process.
  @return An initialized `MOLCodesignChecker` if binary is signed, `nil` otherwise.
*/
- (instancetype)initWithPID:(pid_t)PID;

/**
  Initialize with the currently running process.

  @return An initialized `MOLCodesignChecker` if current binary is signed, `nil` otherwise.
*/
- (instancetype)initWithSelf;

/**
  Compares the signatures of the binaries represented by this `MOLCodesignChecker` and
  `otherChecker` to see if both are correctly signed and the leaf signatures are identical.

  @return YES if both binaries are signed with the same leaf certificate.
*/
- (BOOL)signingInformationMatches:(MOLCodesignChecker *)otherChecker;

@end
