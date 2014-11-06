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

#import <Foundation/Foundation.h>

/// Download a file securely with server trust verification and client certificate authentication.
@interface PBConnectionDelegate : NSObject<NSURLConnectionDelegate>

/// Hostname of server, e.g. 'mac.internal.megacorp.com'
extern NSString *const kConnectionDelegateHost;

/// Folder on server to look in for packages, e.g. 'pkgbase'.
extern const char *kConnectionDelegatePackageBase;

/// URI scheme to use for connection, e.g. 'https'.
extern const char *kConnectionDelegateScheme;

/// File handle of downloaded temporary dmg file.
@property NSFileHandle *fileHandle;

/// Path to temporary directory to save dmg file to.
@property NSString *downloadDir;

/// Path to temporary dmg file, e.g. '/tmp/planb-dmg.mB3dpL/package-stable.dmg'.
@property(readonly) NSString *path;

/// If download was successful, path will be the file, otherwise nil.
typedef void (^ConnectionDelegateFinishedHandler)(NSString *downloadedFilePath);

/// Designated initializer.
- (instancetype)initWithDownloadDir:(NSString *)downloadDir
                    finishedHandler:(ConnectionDelegateFinishedHandler)handler;

@end

