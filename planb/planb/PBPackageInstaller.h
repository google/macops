/*

 Plan B
 PBPackageInstaller.h

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

/// Mount dmg disk image to install first pkg in payload, then unmount and remove dmg.
@interface PBPackageInstaller : NSObject

/// Path to mounted disk image, e.g. '/tmp/planb-pkg.duc3eP'.
@property(nonatomic, copy) NSString *mountPoint;

/// Path to temporary dmg file, e.g. '/tmp/planb-dmg.ihI1UV/pkg-stable.dmg'.
@property(nonatomic, copy) NSString *packagePath;

/// Package receipt name, e.g. 'com.megacorp.corp.pkg'.
@property(nonatomic, copy) NSString *receiptName;

/// Target volume for installation, e.g. '/'.
@property(nonatomic, copy) NSString *targetVolume;

/// Designated initializer.
/// @param receiptName pkgutil receipt name to forget before installation, like 'com.megacorp.pkg'.
/// @param packagePath path to package to mount , like '/tmp/planb-dmg.ihI1UV/pkg-stable.dmg'
/// @param targetVolume target disk volume to install package to.
- (instancetype)initWithReceiptName:(NSString *)receiptName
                        packagePath:(NSString *)packagePath
                       targetVolume:(NSString *)targetVolume;

/// Returns the SHA1 hash of a file at a given path.
+ (NSString *)SHA1ForFileAtPath:(NSString *)path;

/// Mount disk image and install package.
- (void)installApplication;

@end

