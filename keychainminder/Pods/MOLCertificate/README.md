# MOLCertificate
Objective-C wrapper around SecCertificateRef with caching accessors.

Requires ARC. Tested on OS X 10.9+.

## Usage

```objc

#import <MOLCertificate/MOLCertificate.h>

- (MOLCertificate *)certificateFromFile:(NSString *)filePath {
  NSData *fileData = [NSData dataWithContentsOfFile:filePath];
  return [[MOLCertificate alloc] initWithCertificateDataPEM:fileData];
}

- (BOOL)validateCertificate:(MOLCertificate *)cert {
  if ([cert.validFrom compare:[NSDate date]) == NSOrderedDescending) {
    NSLog(@"Certificate has expired");
    return NO;
  }

  if (! [cert.commonName isEqual:@"My Certificate"]) {
    NSLog(@"Certificate is not named the way I expected");
    return YES;
  }

  if (! [cert.countryName isEqual:@"US"]) {
    NSLog(@"This certificate is very un-American.");
  }
}
```

## Installation

Install using CocoaPods.

```
pod 'MOLCertificate'
```

You can also import the project manually but this isn't tested.

## Documentation

Reference documentation is at CocoaDocs.org:

http://cocoadocs.org/docsets/MOLCertificate

## Contributing

Patches to this library are very much welcome.
Please see the [CONTRIBUTING](https://github.com/google/macops-molcertificate/blob/master/CONTRIBUTING.md) file.
