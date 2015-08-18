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

#include "Common.h"

#import <Foundation/Foundation.h>
#import <Security/AuthorizationPlugin.h>

#include <pwd.h>

#pragma mark Data Types

enum {
  kMechanismMagic = 'Mchn',
  kPluginMagic = 'PlgN',
};

typedef struct {
  OSType magic;
  const AuthorizationCallbacks *callbacks;
} PluginRecord;

typedef struct {
  OSType magic;
  AuthorizationEngineRef engineRef;
  const PluginRecord *pluginRecord;
} MechanismRecord;

#pragma mark Utility Functions

NSString *GetStringFromContext(MechanismRecord *mechanism, AuthorizationString key) {
  const AuthorizationValue *value;
  AuthorizationContextFlags flags;
  OSStatus err = mechanism->pluginRecord->callbacks->GetContextValue(
      mechanism->engineRef, key, &flags, &value);
  if (err == errSecSuccess && value->length > 0) {
    NSString *s = [[NSString alloc] initWithBytes:value->data
                                           length:value->length
                                         encoding:NSUTF8StringEncoding];
    return [s stringByReplacingOccurrencesOfString:@"\0" withString:@""];
  }
  return nil;
}

#pragma mark Mechanism Functions

OSStatus MechanismCreate(
    AuthorizationPluginRef inPlugin,
    AuthorizationEngineRef inEngine,
    AuthorizationMechanismId mechanismId,
    AuthorizationMechanismRef *outMechanism) {
  MechanismRecord *mechanism = (MechanismRecord *)malloc(sizeof(MechanismRecord));
  if (mechanism == NULL) return errSecMemoryError;
  mechanism->magic = kMechanismMagic;
  mechanism->engineRef = inEngine;
  mechanism->pluginRecord = (PluginRecord *)inPlugin;
  *outMechanism = mechanism;
  return errSecSuccess;
}

OSStatus MechanismDestroy(AuthorizationMechanismRef inMechanism) {
  free(inMechanism);
  return errSecSuccess;
}

OSStatus MechanismInvoke(AuthorizationMechanismRef inMechanism) {
  MechanismRecord *mechanism = (MechanismRecord *)inMechanism;
  @autoreleasepool {
    NSString *username = GetStringFromContext(mechanism, kAuthorizationEnvironmentUsername);
    NSString *password = GetStringFromContext(mechanism, kAuthorizationEnvironmentPassword);

    if (username && password) {
      // Get current UID/GID for later
      uid_t originalUid = geteuid();
      gid_t originalGid = getegid();

      // Get the user's UID/GID from their username
      struct passwd *pw = getpwnam([username UTF8String]);
      uid_t uid = pw->pw_uid;
      uid_t gid = pw->pw_gid;
      endpwent();

      // Switch EUID/EGID to the target user so SecKeychain* knows who to affect, validate
      // the login keychain password, then switch back to the previous user.
      seteuid(uid);
      setegid(gid);
      SecKeychainSetUserInteractionAllowed(NO);
      BOOL passwordValid = ValidateLoginKeychainPassword(password);
      seteuid(originalUid);
      setegid(originalGid);

      // Remove the current user, so they aren't duplicated in a second if
      // the password wasn't valid.
      NSMutableArray *users = GetUsers();
      [users removeObject:username];

      if (!passwordValid) {
        [users addObject:username];
      }
      SetUsers(users);
    }
  }

  return mechanism->pluginRecord->callbacks->SetResult(mechanism->engineRef,
                                                       kAuthorizationResultAllow);
}

OSStatus MechanismDeactivate(AuthorizationMechanismRef inMechanism) {
  MechanismRecord *mechanism = (MechanismRecord *)inMechanism;
  return mechanism->pluginRecord->callbacks->DidDeactivate(mechanism->engineRef);
}

#pragma mark Plugin Functions

OSStatus PluginDestroy(AuthorizationPluginRef inPlugin) {
  free(inPlugin);
  return errSecSuccess;
}

OSStatus AuthorizationPluginCreate(
    const AuthorizationCallbacks *callbacks,
    AuthorizationPluginRef *outPlugin,
    const AuthorizationPluginInterface **outPluginInterface) {
  PluginRecord *plugin = (PluginRecord *)malloc(sizeof(PluginRecord));
  if (plugin == NULL) return errSecMemoryError;
  plugin->magic = kPluginMagic;
  plugin->callbacks = callbacks;
  *outPlugin = plugin;

  static AuthorizationPluginInterface pluginInterface = {
    kAuthorizationPluginInterfaceVersion,
    &PluginDestroy,
    &MechanismCreate,
    &MechanismInvoke,
    &MechanismDeactivate,
    &MechanismDestroy
  };
  *outPluginInterface = &pluginInterface;

  return errSecSuccess;
}
