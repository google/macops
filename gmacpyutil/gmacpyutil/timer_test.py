"""Tests for timer module."""

import datetime
import os


import mox

from google.apputils import app
from google.apputils import basetest

import timer


class TimeFileTest(mox.MoxTestBase):

  def setUp(self):
    self.mox = mox.Mox()
    self.mox.StubOutWithMock(timer.gmacpyutil, 'SetPlistKey')
    self.mox.StubOutWithMock(timer.gmacpyutil, 'GetPlistKey')

    self.timeplist = '/tmp/blah/myapp.plist'
    self.interval = datetime.timedelta(hours=23)
    self.tf = timer.TimeFile(self.timeplist)

  def tearDown(self):
    self.mox.UnsetStubs()
    self.mox.ResetAll()

  def testNotExpired(self):
    self.mox.StubOutWithMock(self.tf, 'GetOrCreateTimestamp')
    almost_expired = self.interval - datetime.timedelta(minutes=1)
    timestamp = datetime.datetime.utcnow() - almost_expired

    self.tf.GetOrCreateTimestamp().AndReturn(timestamp)
    self.mox.ReplayAll()
    self.assertFalse(self.tf.IsOlderThan(self.interval))
    self.mox.VerifyAll()

  def testExpired(self):
    self.mox.StubOutWithMock(self.tf, 'GetOrCreateTimestamp')
    expired = self.interval + datetime.timedelta(minutes=1)
    timestamp = datetime.datetime.utcnow() - expired

    self.tf.GetOrCreateTimestamp().AndReturn(timestamp)
    self.mox.ReplayAll()
    self.assertTrue(self.tf.IsOlderThan(self.interval))
    self.mox.VerifyAll()

  def testReadTimeFile(self):
    now = datetime.datetime.now()
    timer.gmacpyutil.GetPlistKey(
        self.timeplist, timer.PLIST_TIMESTAMP_KEY).AndReturn(
            now.strftime('%Y-%m-%d %H:%M:%S UTC'))

    self.mox.ReplayAll()
    result = self.tf.ReadTimeFile()
    # We lose precision in the string conversion
    self.assertEqual(now.minute, result.minute)
    self.assertEqual(now.second, result.second)
    self.mox.VerifyAll()

  def testReadTimeFileError(self):
    timer.gmacpyutil.GetPlistKey(
        self.timeplist, timer.PLIST_TIMESTAMP_KEY).AndReturn(None)

    self.mox.ReplayAll()
    self.assertRaises(timer.ErrorReadingPlist, self.tf.ReadTimeFile)
    self.mox.VerifyAll()

  def testReadTimeFileErrorTimestamp(self):
    timer.gmacpyutil.GetPlistKey(
        self.timeplist, timer.PLIST_TIMESTAMP_KEY).AndReturn('broken')

    self.mox.ReplayAll()
    self.assertRaises(ValueError, self.tf.ReadTimeFile)
    self.mox.VerifyAll()

  def testWriteTimeFile(self):
    self.mox.StubOutWithMock(timer.os.path, 'exists')
    now = datetime.datetime.now()

    timer.os.path.exists(os.path.dirname(self.timeplist)).AndReturn(True)
    timer.gmacpyutil.SetPlistKey(self.timeplist,
                                 timer.PLIST_TIMESTAMP_KEY,
                                 mox.IgnoreArg()).AndReturn(True)
    self.mox.ReplayAll()
    self.assertEqual(self.tf.WriteTimeFile(timestamp=now), now)
    self.mox.VerifyAll()

  def testWriteFileErrorWriting(self):
    self.mox.StubOutWithMock(timer.os.path, 'exists')
    now = datetime.datetime.now()

    timer.os.path.exists(os.path.dirname(self.timeplist)).AndReturn(True)
    timer.gmacpyutil.SetPlistKey(self.timeplist,
                                 timer.PLIST_TIMESTAMP_KEY,
                                 mox.IgnoreArg()).AndReturn(None)
    self.mox.ReplayAll()
    self.assertRaises(timer.ErrorWritingPlist,
                      self.tf.WriteTimeFile, timestamp=now)
    self.mox.VerifyAll()


def main(unused_argv):
  basetest.main()


if __name__ == '__main__':
  app.run()
