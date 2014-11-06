/*

 Plan B
 PBURLBuilder.m

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

#import "PBConnectionDelegate.h"
#import "PBLogging.h"
#import "PBURLBuilder.h"

const static short kSupportedMajorVersion = 10;
const static short kSupportedMinorVersion = 10;
const static char *kMachineInfo = "/Library/Preferences/com.megacorp.machineinfo.plist";
const static char *kSystemInfo = "/System/Library/CoreServices/SystemVersion.plist";

@implementation URLBuilder

+ (NSString *)configurationTrack {
  static dispatch_once_t onceToken;
  static NSString *track;

  dispatch_once(&onceToken, ^{
      NSDictionary *machineInfoDictionary =
          [NSDictionary dictionaryWithContentsOfFile:@(kMachineInfo)];
      track = [machineInfoDictionary objectForKey:@"ConfigurationTrack"];
  });

  return track;
}

+ (NSURL *)URLForTrackWithPkg:(NSString *)pkg {
  NSString *track = [[self configurationTrack] lowercaseString];

  if (!track) {
    NSDictionary *systemVersionDictionary =
        [NSDictionary dictionaryWithContentsOfFile:@(kSystemInfo)];
    NSString *systemVersion = [systemVersionDictionary objectForKey:@"ProductVersion"];
    NSArray *systemVersionComps = [systemVersion componentsSeparatedByString:@"."];

    int majorVersion = [systemVersionComps[0] intValue];
    int minorVersion = [systemVersionComps[1] intValue];

    if (majorVersion == kSupportedMajorVersion && minorVersion <= kSupportedMinorVersion) {
      track = @"stable";
    } else {
      track = @"unstable";
    }
  }

  NSURLComponents *resultURLString = [[NSURLComponents alloc] init];
  resultURLString.scheme = @(kConnectionDelegateScheme);
  resultURLString.host = kConnectionDelegateHost;
  resultURLString.path = [NSString stringWithFormat:@"/%s/%@-%@.dmg",
                          kConnectionDelegatePackageBase, pkg, track];

  return [resultURLString URL];
}

@end

