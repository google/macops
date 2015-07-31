#!/usr/bin/env python
# Copyright 2015 Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

"""
Python module for installing/removing the KeychainMinder mechanism
from the authorization database. Only designed for 10.8+.

This can either be used as a standalone script or imported and used
in another Python script.
"""

import argparse
import plistlib
import os
import subprocess
import sys


# Default mechanism.
AUTHENTICATE_RIGHT = 'authenticate'
KEYCHAIN_MINDER_MECHANISM = 'KeychainMinder:check,privileged'

SCREENSAVER_RIGHT = 'system.login.screensaver'
SCREENSAVER_RULE = 'authenticate-session-owner-or-admin'


def _GetRightData(right):
  """Get the current configuration for the requested right as a dict."""
  output = subprocess.check_output(
      ["/usr/bin/security", "authorizationdb", "read", right],
      stderr=subprocess.PIPE)
  data = plistlib.readPlistFromString(output)
  return data


def _SetRightData(right, data):
  """Update the configuration for the requested right."""
  data = plistlib.writePlistToString(data)
  p = subprocess.Popen(
      ["/usr/bin/security", "authorizationdb", "write", right],
      stdin=subprocess.PIPE,
      stderr=subprocess.PIPE)
  p.communicate(input=data)


def InstallPlugin():
  data = _GetRightData(AUTHENTICATE_RIGHT)
  if not data.get('mechanisms').count(KEYCHAIN_MINDER_MECHANISM):
    mechanisms = data.get('mechanisms')
    mechanisms.append(KEYCHAIN_MINDER_MECHANISM)
    data['mechanisms'] = mechanisms
    _SetRightData(AUTHENTICATE_RIGHT, data)
    print 'Mechanism installed.'
  else:
    print 'Mechanism already installed.'

  data = _GetRightData(SCREENSAVER_RIGHT)
  if data.get('rules') != [SCREENSAVER_RULE]:
    data['rules'] = [SCREENSAVER_RULE]
    _SetRightData(SCREENSAVER_RIGHT, data)
    print 'Screensaver rule updated.'
  else:
    print 'Screensaver rule already correct.'

def RemovePlugin():
  data = _GetRightData(AUTHENTICATE_RIGHT)
  if not data.get('mechanisms').count(KEYCHAIN_MINDER_MECHANISM):
    mechanisms = data.get('mechanisms')
    mechanisms.append(KEYCHAIN_MINDER_MECHANISM)
    data['mechanisms'] = mechanisms
    _SetRightData(AUTHENTICATE_RIGHT, data)
    print 'Mechanism removed.'
  else:
    print 'Mechanism already removed.'

  # Note: Don't revert the screensaver rule. It wouldn't be difficult to
  # revert to 'use-login-window-ui' but this isn't valid on all OS versions.


def CheckForRoot():
  if not os.geteuid() == 0:
    sys.exit('This script requires root privileges')

def ParseOptions():
  parser = argparse.ArgumentParser()
  group = parser.add_mutually_exclusive_group(required=True)
  group.add_argument("--install", action="store_true", dest="install", help="Install plugin")
  group.add_argument("--remove", action="store_true", dest="remove", help="Remove plugin")
  return parser.parse_args()

def main(argv):
  CheckForRoot()
  options = ParseOptions()
  if options.install:
    InstallPlugin()
  elif options.remove:
    RemovePlugin()

if __name__ == '__main__':
  main(sys.argv)
