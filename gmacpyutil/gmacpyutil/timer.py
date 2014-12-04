"""Timestamp storage, parsing utility.

Use this to keep state between application executions.  Often we want to
throttle how often we run something, or check last time an event happened.

Example usage

In [1]: lastrun = timer.TimeFile('/var/run/myapp.plist')
In [2]: lastrun.IsOlderThan(datetime.timedelta(hours=10))
Out[2]: False
"""

import datetime
import os.path

from . import gmacpyutil


PLIST_TIMESTAMP_KEY = 'timestamp'


class Error(Exception):
  """Base error class."""


class ErrorReadingPlist(Error):
  """Couldn't read timeplist plist."""


class ErrorWritingPlist(Error):
  """Couldn't write timeplist plist."""


class TimeFile(object):
  """Record a timestamp in a plist and provide query utilities."""

  def __init__(self, path):
    self.timeplist = path

  def ReadTimeFile(self):
    """Read timestamp from self.timeplist.

    Returns:
      datetime.datetime object from timestamp in self.timeplist
    Raises:
      ErrorReadingPlist: getplistkey failed
      ValueError: bad value from plist that doesn't match strptime
    """
    time_str = gmacpyutil.GetPlistKey(self.timeplist, PLIST_TIMESTAMP_KEY)

    if not time_str:
      raise ErrorReadingPlist('Could not read %s from %s' %
                              (PLIST_TIMESTAMP_KEY, self.timeplist))

    self.stored_time = datetime.datetime.strptime(time_str,
                                                  '%Y-%m-%d %H:%M:%S %Z')

    return self.stored_time

  def WriteTimeFile(self, timestamp=None):
    """Write UTC timestamp to a plist.

    If no timestamp is supplied, write current UTC time to self.timeplist plist.
    If plist exists, update the PLIST_TIMESTAMP_KEY.

    Args:
      timestamp: UTC datetime object
    Returns:
      datetime object stored
    Raises:
      ErrorWritingPlist: SetPlistKey fails
      OSError: if more >1 parent directory is missing from self.timeplist path
    """
    if timestamp:
      self.stored_time = timestamp
    else:
      self.stored_time = datetime.datetime.utcnow()

    # This will only handle one missing parent dir
    # os.mkdirs not available in version of python we run
    if not os.path.exists(os.path.dirname(self.timeplist)):
      os.mkdir(os.path.dirname(self.timeplist))

    timestr = self.stored_time.strftime('%Y-%m-%d %H:%M:%S UTC')
    if not gmacpyutil.SetPlistKey(self.timeplist, PLIST_TIMESTAMP_KEY, timestr):
      raise ErrorWritingPlist('Could not write to %s in %s'
                              % (PLIST_TIMESTAMP_KEY, self.timeplist))
    return self.stored_time

  def GetOrCreateTimestamp(self):
    """Get a timestamp from self.timeplist, create if doesn't exist.

    Returns:
      datetime.datetime object
    Raises:
      ErrorWritingPlist: SetPlistKey fails
      OSError: if more >1 parent directory is missing from self.timeplist path
    """
    try:
      return self.ReadTimeFile()
    except (ErrorReadingPlist, ValueError):
      # Got a bad file, try writing a new one
      return self.WriteTimeFile()

  def IsOlderThan(self, interval):
    """Is the stored timestamp older than interval.

    Args:
      interval: datetime.interval object
    Returns:
      bool true if interval time has passed since timestamp
    Raises:
      ErrorWritingPlist: SetPlistKey fails
      OSError: if more >1 parent directory is missing from self.timeplist path
    """
    return datetime.datetime.utcnow() > (self.GetOrCreateTimestamp() + interval)
