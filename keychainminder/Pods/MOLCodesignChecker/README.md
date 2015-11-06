# MOLCodesignChecker

Provides an easy way to do code signature validation in Objective-C

## Usage

```objc
#import <MOLCertificate/MOLCertificate.h>
#import <MOLCodesignChecker/MOLCodesignChecker.h>

- (BOOL)validateMySignature {
  MOLCodesignChecker *csInfo = [[MOLCodesignChecker alloc] initWithSelf];
  if (csInfo) {
    // I'm signed! Check the certificate
    NSLog(@"%@, %@", csInfo.leafCertificate, csInfo.leafCertificate.SHA256);
    return YES;
  }
  return NO;
}

- (BOOL)validateFile:(NSString *)filePath {
  MOLCodesignChecker *csInfo = [[MOLCodesignChecker alloc] initWithBinaryPath:filePath];
  if (csInfo) {
    // I'm signed! Check the certificate
    NSLog(@"%@, %@", csInfo.leafCertificate, csInfo.leafCertificate.SHA256);
    return YES;
  }
  return NO;
}
```

## Installation

Install using CocoaPods.

```
pod 'MOLCodesignChecker'
```

You can also import the project manually but this isn't tested.

## Documentation

Reference documentation is at CocoaDocs.org:

http://cocoadocs.org/docsets/MOLCodesignChecker

## Contributing

Patches to this library are very much welcome. Please see the
[CONTRIBUTING](https://github.com/google/macops-molcodesignchecker/blob/master/CONTRIBUTING.md)
file.
