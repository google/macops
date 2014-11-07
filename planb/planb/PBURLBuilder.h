/*

 Plan B
 PBURLBuilder.h

 Create URL for a resource to download, by combining:
   * uri scheme: in this case, https.
   * host: server hostname.
   * path: top-level folder containing the resources required by this program.
   * package: name of folder and package, joined by '/'.
   * track: machine's configuration track: unstable, testing, or stable.
            Default 'stable' for machines on a supported OS release, 'unstable' otherwise.
   * suffix: '.dmg' file type.

 For example, https://mac.internal.megacorp.com/pkgbase/pkg1/sample-stable.dmg
 is constructed for the 'sample' package, which is stored in the 'pkg1' folder of
 'mac.internal.megacorp.com', for a machine on the 'stable' configuration track.

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

/// Create NSURL for a resource to download.
@interface URLBuilder : NSObject

/// Configuration track: @c unstable, @c testing, or @c stable.
+ (NSString *)configurationTrack;

/// URL of package to download for corresponding track.
/// @param pkg package name, e.g. 'pkg1/sample'.
/// @return NSURL of the package to download.
+ (NSURL *)URLForTrackWithPkg:(NSString *)pkg;

@end

