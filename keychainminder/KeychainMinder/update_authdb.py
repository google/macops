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
KEYCHAIN_MINDER_MECHANISM = "KeychainMinder:check,privileged"

def _GetMechanismsContainsUs(mechanisms, mechanism=KEYCHAIN_MINDER_MECHANISM):
  """Check if |mechanisms| contains |mechanism|."""
  for m in mechanisms:
    if m == mechanism:
      return True
  return False

def _GetAuthenticateData():
  """Get the current configuration for the 'authenticate' right as a dict."""
  output = subprocess.check_output(
      ["/usr/bin/security", "authorizationdb", "read", "authenticate"],
      stderr=subprocess.PIPE)
  data = plistlib.readPlistFromString(output)
  return data

def _SetAuthenticateData(input):
  """Update the configuration for the 'authenticate' right."""
  data = plistlib.writePlistToString(input)
  p = subprocess.Popen(
      ["/usr/bin/security", "authorizationdb", "write", "authenticate"],
      stdin=subprocess.PIPE,
      stderr=subprocess.PIPE)
  p.communicate(input=data)

def _UpdateMechanisms(data, install=True, mechanism=KEYCHAIN_MINDER_MECHANISM):
  """Install/remove the requested mechanism in the right configuration."""
  mechanisms = data.get('mechanisms')
  if not mechanisms:
    sys.exit("Unable to parse mechanisms from authenticate right")

  if install != _GetMechanismsContainsUs(mechanisms):
    if install:
      mechanisms.append(mechanism)
    else:
      mechanisms.remove(mechanism)
    data['mechanisms'] = mechanisms
    _SetAuthenticateData(data)
  else:
    if install:
      sys.exit("Mechanism is already installed")
    else:
      sys.exit("Mechanism is not installed")

def InstallPlugin():
  _UpdateMechanisms(_GetAuthenticateData())
  print 'Mechanism installed.'

def RemovePlugin():
  _UpdateMechanisms(_GetAuthenticateData(), install=False)
  print 'Mechanism removed.'

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
