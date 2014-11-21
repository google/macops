#!/usr/bin/env python
#
# Copyright 2010 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Handles NSWorkspace notifications from crankd."""

__author__ = 'crc@google.com (Clay Caviness)'

from ApplicationUsage import ApplicationUsage
# from FirefoxPreferenceManager import FirefoxPreferenceManager


class NSWorkspaceHandler(object):
  """Handles NSWorkspace events from crankd. Unusable outside of crankd."""

  def __init__(self):
    self.au = ApplicationUsage()
    # self.fpm = FirefoxPreferenceManager()

  def OnApplicationLaunch(self, *args, **kwargs):
    """The main entry point for launches."""
    self.au.OnApplicationLaunch(*args, **kwargs)
    # self.fpm.OnWillLaunchApplication(*args, **kwargs)

  def OnApplicationQuit(self, *args, **kwargs):
    """The main entry point for quits."""
    self.au.OnApplicationQuit(*args, **kwargs)
