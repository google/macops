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


"""Tracks application launches and exits.

This is designed to be triggered upon
NSWorkspaceWillLaunchApplicationNotification and
NSWorkspaceDidTerminateApplicationNotification NSWorkspace notifications by
crankd. It is useless without the user_info dictionary that such notifications
provide.

"""

import logging
from Foundation import NSDictionary
import os
import sqlite3
import sys
import time


# SQLite table to store application usage data
APPLICATION_USAGE_DB = '/var/db/application_usage.sqlite'
# SQL to detect existance of application usage table
APPLICATION_USAGE_TABLE_DETECT = 'SELECT * FROM application_usage LIMIT 1'
# This table creates ~64 bytes of disk data per event.
APPLICATION_USAGE_TABLE_CREATE = (
    'CREATE TABLE application_usage ('
    'event TEXT,'
    'bundle_id TEXT,'
    'app_version TEXT,'
    'app_path TEXT,'
    'last_time INTEGER DEFAULT 0,'
    'number_times INTEGER DEFAULT 0,'
    'PRIMARY KEY (event, bundle_id)'
    ')')

APPLICATION_USAGE_TABLE_INSERT = (
    'INSERT INTO application_usage VALUES ('
    '?, '  # event
    '?, '  # bundle_id
    '?, '  # app_version
    '?, '  # app_path
    '?, '  # last_time
    '? '   # number_times
    ')'
    )

# keep same order of columns as APPLICATION_USAGE_TABLE_INSERT
APPLICATION_USAGE_TABLE_SELECT = (
    'SELECT '
    'event, bundle_id, app_version, app_path, last_time, number_times '
    'FROM application_usage'
    )

APPLICATION_USAGE_TABLE_UPDATE = (
    'UPDATE application_usage SET '
    'app_version=?,'
    'app_path=?,'
    'last_time=?,'
    'number_times=number_times+1 '
    'WHERE event=? and bundle_id=?'
    )


class Error(Exception):
  """Base error."""


class ApplicationUsage(object):
  """Tracks application launches and exits. Unusable outside of crankd."""

  def _Connect(self, database_name=None):
    """Connect to database.

    Args:
      database_name: str, default APPLICATION_USAGE_DB
    Returns:
      sqlite3.Connection instance
    """
    if database_name is None:
      database_name = APPLICATION_USAGE_DB

    conn = sqlite3.connect(database_name)

    return conn

  def _Close(self, conn):
    """Close database.

    Args:
      conn: sqlite3.Connection instance
    """
    conn.close()

  def GetAppInfo(self, user_info):
    """Grabs the application info from the user_info dictionary.

    Args:
      user_info: dictionary of application info

    Returns:
      tuple of bundle_id, app_version, app_path
    """
    bundle_id, app_version, app_path = None, None, None
    try:
      bundle_id = user_info['NSApplicationBundleIdentifier']
    except KeyError:
      # Malformed applications may not have NSApplicationBundleIdentifier
      # Return NSApplicationName instead
      logging.error('Error reading bundle identifier: %s', user_info)
      bundle_id = user_info['NSApplicationName']
    try:
      app_path = user_info['NSApplicationPath']
    except KeyError:
      # Malformed applications may not have NSApplicationPath
      logging.error('Error reading application path: %s', user_info)
    if app_path:
      try:
        app_info_plist = NSDictionary.dictionaryWithContentsOfFile_(
            '%s/Contents/Info.plist' % app_path)
        if app_info_plist:
          app_version = app_info_plist['CFBundleVersion']
      except KeyError:
        logging.error('Error reading application version from %s', app_path)

    return bundle_id, app_version, app_path

  def _DetectApplicationUsageTable(self, conn):
    """Detect whether the application usage table exists.

    Args:
      conn: sqlite3.Connection object
    Returns:
      True if the table exists, False if not.
    Raises:
      sqlite3.Error: if error occurs
    """
    try:
      conn.execute(APPLICATION_USAGE_TABLE_DETECT)
      exists = True
    except sqlite3.OperationalError, e:
      if e.args[0].startswith('no such table'):
        exists = False
      else:
        raise
    return exists

  def _CreateApplicationUsageTable(self, conn):
    """Create application usage table when it does not exist.

    Args:
      conn: sqlite3.Connection object
    Raises:
      sqlite3.Error: if error occurs
    """
    conn.execute(APPLICATION_USAGE_TABLE_CREATE)

  def _InsertApplicationUsage(
      self, conn, event, bundle_id, app_version, app_path, now):
    """Insert usage data into application usage table.

    Args:
      conn: sqlite3.Connection object
      event: str
      bundle_id: str
      app_version: str
      app_path: str
      now: int
    """
    # this looks weird, but it's the simplest way to do an update or insert
    # operation in sqlite, and atomically update number_times, that I could
    # figure out.  plus we avoid using transactions and multiple SQL
    # statements in most cases.

    v = (app_version, app_path, now, event, bundle_id)
    q = conn.execute(APPLICATION_USAGE_TABLE_UPDATE, v)
    if q.rowcount == 0:
      number_times = 1
      v = (event, bundle_id, app_version, app_path, now, number_times)
      conn.execute(APPLICATION_USAGE_TABLE_INSERT, v)

  def _RecreateDatabase(self):
    """Recreate a database.

    Returns:
      int number of rows that were recovered from old database
      and written into new one
    """
    recovered = 0

    try:
      conn = self._Connect()
      table = []
      q = conn.execute(APPLICATION_USAGE_TABLE_SELECT)
      try:
        while 1:
          row = q.fetchone()
          if not row:
            break
          table.append(row)
      except sqlite3.Error:
        pass
        # ok, done, hit an error
      conn.close()
    except sqlite3.Error, e:
      logging.error('Unhandled error reading existing db: %s', str(e))
      return recovered

    usage_db_tmp = '%s.tmp.%d' % (APPLICATION_USAGE_DB, os.getpid())

    try:
      conn = self._Connect(usage_db_tmp)
      self._CreateApplicationUsageTable(conn)
      recovered = 0
      for row in table:
        if row[1:3] == ['', '', '']:
          continue
        try:
          conn.execute(APPLICATION_USAGE_TABLE_INSERT, row)
          conn.commit()
          recovered += 1
        except sqlite3.IntegrityError, e:
          logging.error('Ignored error: %s: %s', str(e), str(row))
      self._Close(conn)
      os.unlink(APPLICATION_USAGE_DB)
      os.rename(usage_db_tmp, APPLICATION_USAGE_DB)
    except sqlite3.Error, e:
      logging.error('Unhandled error: %s', str(e))
      recovered = 0

    return recovered

  def VerifyDatabase(self, fix=False):
    """Verify database integrity."""
    conn = self._Connect()
    try:
      q = conn.execute(APPLICATION_USAGE_TABLE_SELECT)
      unused_rows = q.fetchall()
      ok = True
    except sqlite3.Error:
      ok = False

    if not ok:
      if fix:
        print 'Recreating database.'
        print 'Recovered %d rows.' % self._RecreateDatabase()
      else:
        print 'Database is malformed.  Run with --fix to attempt repair.'
    else:
      print 'Database is OK.'

  def LogApplicationUsage(self, event, bundle_id, app_version, app_path):
    """Log application usage.

    Args:
      event: str, like "launch" or "quit"
      bundle_id: str
      app_version: str
      app_path: str
    """
    if bundle_id is None and app_version is None and app_path is None:
      return

    try:
      now = int(time.time())
      conn = self._Connect()
      if not self._DetectApplicationUsageTable(conn):
        self._CreateApplicationUsageTable(conn)
      self._InsertApplicationUsage(
          conn,
          event, bundle_id, app_version, app_path, now)
      conn.commit()
    except sqlite3.OperationalError, e:
      logging.error('Error writing %s event to database: %s', event, e)
      self._Close(conn)
    except sqlite3.DatabaseError, e:
      if e.args[0] == 'database disk image is malformed':
        self._RecreateDatabase()
      logging.error('Database error: %s', e)
      self._Close(conn)
    self._Close(conn)

  def OnApplicationLaunch(self, *unused_args, **kwargs):
    """The main entry point for launches."""
    appinfo = self.GetAppInfo(kwargs['user_info'])
    self.LogApplicationUsage('launch', *appinfo)
    logging.info('Application Launched: bundle_id: %s version: %s path: %s',
        *appinfo)

  def OnApplicationQuit(self, *unused_args, **kwargs):
    """The main entry point for quits."""
    appinfo = self.GetAppInfo(kwargs['user_info'])
    self.LogApplicationUsage('quit', *appinfo)
    logging.info('Application Quit: bundle_id: %s version: %s path: %s',
        *appinfo)


if __name__ == '__main__':
  au = ApplicationUsage()
  au.VerifyDatabase('--fix' in sys.argv)
