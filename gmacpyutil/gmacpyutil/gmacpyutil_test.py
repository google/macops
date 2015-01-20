"""Unit tests for top-level module."""

import os


import mock
import mox
import stubout

from google.apputils import app
from google.apputils import basetest

import gmacpyutil


def InitMockFoundation(self):
  mock_nsdict = self.mox.CreateMockAnything()
  mock_nsmutdict = self.mox.CreateMockAnything()
  gmacpyutil.NSDictionary = mock_nsdict
  gmacpyutil.NSMutableDictionary = mock_nsmutdict


def StubFoundation(self):
  self.mox.StubOutWithMock(gmacpyutil, 'NSDictionary')
  self.mox.StubOutWithMock(gmacpyutil, 'NSMutableDictionary')


class GmacpytutilModuleTest(mox.MoxTestBase):

  def setUp(self):
    mox.MoxTestBase.setUp(self)
    self.stubs = stubout.StubOutForTesting()

  def tearDown(self):
    self.mox.UnsetStubs()
    self.stubs.UnsetAll()

  def StubSetup(self):
    self.mox.StubOutWithMock(gmacpyutil, 'logging')
    self.mox.StubOutWithMock(gmacpyutil.logging, 'handlers')
    self.mox.StubOutWithMock(gmacpyutil.logging, 'Formatter')
    self.mox.StubOutWithMock(gmacpyutil.logging, 'getLogger')
    self.mox.StubOutWithMock(gmacpyutil, 'os')
    self.mox.StubOutWithMock(gmacpyutil, 'subprocess')
    self.mox.StubOutWithMock(gmacpyutil.subprocess, 'Popen')
    if os.uname()[0] == 'Linux':
      InitMockFoundation(self)
    elif os.uname()[0] == 'Darwin':
      StubFoundation(self)

  @mock.patch('logging.handlers.SysLogHandler.emit')
  def testMultilineSysLogHandlerEmit(self, mock_syslogemit):
    record = gmacpyutil.logging.LogRecord(None, None, None, None,
                                          '%s\n%s', ('x' * 1900, 'y' * 1000),
                                          None)

    # Test newline split
    mlslh = gmacpyutil.MultilineSysLogHandler()
    mlslh.emit(record)
    self.assertEqual(mock_syslogemit.call_count, 2)
    self.assertEqual(mock_syslogemit.call_args_list[0][0][1].msg,
                     'x' * 1900)
    self.assertEqual(mock_syslogemit.call_args_list[1][0][1].msg,
                     'CONTINUED: %s' % ('y' * 1000))
    mock_syslogemit.reset_mock()

    # Test space split
    record.msg = '%s %s'
    record.args = ('x' * 1999, 'y' * 150)
    mlslh.emit(record)
    self.assertEqual(mock_syslogemit.call_count, 2)
    self.assertEqual(mock_syslogemit.call_args_list[0][0][1].msg,
                     'x' * 1999)
    self.assertEqual(mock_syslogemit.call_args_list[1][0][1].msg,
                     'CONTINUED: %s' % ('y' * 150))
    mock_syslogemit.reset_mock()

    # Test character split
    record.msg = '%s%s'
    record.args = ('x' * 1999, 'y' * 150)
    mlslh.emit(record)
    self.assertEqual(mock_syslogemit.call_count, 2)
    self.assertEqual(mock_syslogemit.call_args_list[0][0][1].msg,
                     '%s%s' % ('x' * 1999, 'y'))
    self.assertEqual(mock_syslogemit.call_args_list[1][0][1].msg,
                     'CONTINUED: %s' % ('y' * 149))
    mock_syslogemit.reset_mock()

  def testMultilineSysLogHandlerException(self):
    gmacpyutil.ConfigureLogging(stderr=False, syslog=True)

    try:
      raise Exception('\n'.join(['error ' * 100] * 10))
    except Exception:  # pylint: disable=broad-except
      gmacpyutil.logging.exception('something is busticated')

  def testMultilineSysLogHandlerFormattedString(self):
    fs = '%s' +  'a' * 2500
    gmacpyutil.ConfigureLogging(stderr=False, syslog=True)
    gmacpyutil.logging.error(fs, 'foo')

  def testConfigureLogging(self):
    """Test ConfigureLogging, syslog and stderr, debug log level."""
    self.StubSetup()
    self.mox.StubOutWithMock(gmacpyutil, '_ConfigureHandler')
    self.mox.StubOutWithMock(gmacpyutil, 'MultilineSysLogHandler')
    self.mox.StubOutWithMock(gmacpyutil.logging.handlers, 'SysLogHandler')
    gmacpyutil.logging.handlers.SysLogHandler.LOG_USER = 1

    level = gmacpyutil.logging.DEBUG
    mock_syslog = self.mox.CreateMockAnything()
    mock_logger = self.mox.CreateMockAnything()

    stream_handler = self.mox.CreateMock(gmacpyutil.logging.StreamHandler)
    stream_handler2 = self.mox.CreateMock(gmacpyutil.logging.StreamHandler)
    mock_logger.handlers = [stream_handler, stream_handler2]

    gmacpyutil.logging.getLogger().AndReturn(mock_logger)
    mock_logger.setLevel(level)

    gmacpyutil.MultilineSysLogHandler(facility=1).AndReturn(mock_syslog)
    gmacpyutil._ConfigureHandler(mock_syslog, mock_logger,
                                 gmacpyutil.LOG_FORMAT_SYSLOG, level)

    gmacpyutil.logging.StreamHandler().AndReturn(stream_handler)
    gmacpyutil._ConfigureHandler(stream_handler, mock_logger,
                                 gmacpyutil.LOG_FORMAT_STDERR, level)

    gmacpyutil.logging.debug('Logging enabled at level %s', level)
    self.mox.ReplayAll()
    self.assertEqual(None, gmacpyutil.ConfigureLogging(debug_level=level,
                                                       show_level=False))
    self.mox.VerifyAll()

  def testConfigureLoggingWithCustomFacility(self):
    """Test ConfigureLogging custom syslog facility."""
    self.StubSetup()
    self.mox.StubOutWithMock(gmacpyutil, '_ConfigureHandler')
    self.mox.StubOutWithMock(gmacpyutil, 'MultilineSysLogHandler')
    self.mox.StubOutWithMock(gmacpyutil.logging.handlers, 'SysLogHandler')
    gmacpyutil.logging.handlers.SysLogHandler.LOG_USER = 1
    gmacpyutil.logging.handlers.SysLogHandler.facility_names = {'local1': 999}

    mock_syslog = self.mox.CreateMockAnything()
    mock_logger = self.mox.CreateMockAnything()

    stream_handler = self.mox.CreateMock(gmacpyutil.logging.StreamHandler)
    mock_logger.handlers = [stream_handler]

    gmacpyutil.logging.getLogger().AndReturn(mock_logger)
    mock_logger.setLevel(mox.IgnoreArg())

    gmacpyutil.MultilineSysLogHandler(facility=999).AndReturn(mock_syslog)
    gmacpyutil._ConfigureHandler(mock_syslog, mock_logger,
                                 gmacpyutil.LOG_FORMAT_SYSLOG, mox.IgnoreArg())

    gmacpyutil.logging.StreamHandler().AndReturn(stream_handler)
    gmacpyutil._ConfigureHandler(stream_handler, mock_logger,
                                 mox.IgnoreArg(), mox.IgnoreArg())

    gmacpyutil.logging.debug(mox.IgnoreArg(), mox.IgnoreArg())

    self.mox.ReplayAll()
    self.assertEqual(None, gmacpyutil.ConfigureLogging(facility='local1'))
    self.mox.VerifyAll()

  def testConfigureLoggingWithUnknownCustomFacility(self):
    """Test ConfigureLogging custom syslog facility."""
    self.StubSetup()
    self.mox.StubOutWithMock(gmacpyutil, '_ConfigureHandler')
    self.mox.StubOutWithMock(gmacpyutil, 'MultilineSysLogHandler')
    self.mox.StubOutWithMock(gmacpyutil.logging.handlers, 'SysLogHandler')
    gmacpyutil.logging.handlers.SysLogHandler.LOG_USER = 1
    gmacpyutil.logging.handlers.SysLogHandler.facility_names = {'known': 999}

    mock_syslog = self.mox.CreateMockAnything()
    mock_logger = self.mox.CreateMockAnything()

    stream_handler = self.mox.CreateMock(gmacpyutil.logging.StreamHandler)
    mock_logger.handlers = [stream_handler]

    gmacpyutil.logging.getLogger().AndReturn(mock_logger)
    mock_logger.setLevel(mox.IgnoreArg())

    gmacpyutil.logging.error(mox.IgnoreArg(), mox.IgnoreArg())
    gmacpyutil.MultilineSysLogHandler(facility=1).AndReturn(mock_syslog)
    gmacpyutil._ConfigureHandler(mock_syslog, mock_logger,
                                 gmacpyutil.LOG_FORMAT_SYSLOG, mox.IgnoreArg())

    gmacpyutil.logging.StreamHandler().AndReturn(stream_handler)
    gmacpyutil._ConfigureHandler(stream_handler, mock_logger,
                                 mox.IgnoreArg(), mox.IgnoreArg())

    gmacpyutil.logging.debug(mox.IgnoreArg(), mox.IgnoreArg())

    self.mox.ReplayAll()
    self.assertEqual(None, gmacpyutil.ConfigureLogging(facility='unknown'))
    self.mox.VerifyAll()

  def testConfigureLoggingStderrNoExisting(self):
    self.StubSetup()
    self.mox.StubOutWithMock(gmacpyutil, '_ConfigureHandler')

    level = gmacpyutil.logging.DEBUG
    mock_logger = self.mox.CreateMockAnything()

    stream_handler = self.mox.CreateMock(gmacpyutil.logging.StreamHandler)
    mock_logger.handlers = []

    gmacpyutil.logging.getLogger().AndReturn(mock_logger)
    mock_logger.setLevel(level)

    gmacpyutil.logging.StreamHandler().AndReturn(stream_handler)
    gmacpyutil._ConfigureHandler(stream_handler, mock_logger,
                                 gmacpyutil.LOG_FORMAT_STDERR_LEVEL, level)

    gmacpyutil.logging.debug('Logging enabled at level %s', level)
    self.mox.ReplayAll()
    self.assertEqual(None, gmacpyutil.ConfigureLogging(debug_level=level,
                                                       stderr=True,
                                                       syslog=False))
    self.mox.VerifyAll()

  def testConfigureLoggingBadConfig(self):
    self.StubSetup()
    self.mox.ReplayAll()
    self.assertRaises(gmacpyutil.LogConfigurationError,
                      gmacpyutil.ConfigureLogging,
                      stderr=False, syslog=False)
    self.mox.VerifyAll()

  def testConfigureHandler(self):
    formatter = self.mox.CreateMock(gmacpyutil.logging.Formatter)
    self.StubSetup()
    debug_level = gmacpyutil.logging.INFO

    logger = self.mox.CreateMockAnything()
    handler = self.mox.CreateMockAnything()

    gmacpyutil.logging.Formatter(
        gmacpyutil.LOG_FORMAT_SYSLOG).AndReturn(formatter)
    handler.setFormatter(formatter)
    handler.setLevel(debug_level)
    logger.addHandler(handler)

    self.mox.ReplayAll()
    gmacpyutil._ConfigureHandler(handler, logger,
                                 gmacpyutil.LOG_FORMAT_SYSLOG, debug_level)
    self.mox.VerifyAll()

  def testPrivateRunProcess(self):
    """Test _RunProcess, simple command, default args."""
    self.StubSetup()
    mock_env = self.mox.CreateMockAnything()
    gmacpyutil.os.environ = mock_env
    gmacpyutil.subprocess.PIPE = 'pipe'
    mock_task = self.mox.CreateMockAnything()
    mock_env.copy().AndReturn(mock_env)
    gmacpyutil.subprocess.Popen(
        ['cmd'], stdout='pipe', stderr='pipe', stdin='pipe', env=mock_env,
        cwd=None).AndReturn(mock_task)
    mock_task.communicate(input=None).AndReturn(('out', 'err'))
    mock_task.returncode = 0
    self.mox.ReplayAll()
    self.assertEqual(('out', 'err', 0), gmacpyutil._RunProcess(['cmd']))
    self.mox.VerifyAll()

  def testPrivateRunProcessWithEnv(self):
    """Test _RunProcess, simple command, with env."""
    self.StubSetup()
    mock_env = self.mox.CreateMockAnything()
    env_copy = {'foo': 'bar'}
    new_env = {'new': True}
    used_env = env_copy.copy()
    used_env.update(new_env)

    gmacpyutil.os.environ = mock_env
    gmacpyutil.subprocess.PIPE = 'pipe'
    mock_task = self.mox.CreateMockAnything()
    mock_env.copy().AndReturn(env_copy)
    gmacpyutil.subprocess.Popen(
        ['cmd'], stdout='pipe', stderr='pipe', stdin='pipe', env=used_env,
        cwd=None).AndReturn(mock_task)
    mock_task.communicate(input=None).AndReturn(('out', 'err'))
    mock_task.returncode = 0
    self.mox.ReplayAll()
    self.assertEqual(
        ('out', 'err', 0), gmacpyutil._RunProcess(['cmd'], env={'new': True}))
    self.mox.VerifyAll()

  def testPrivateRunProcessWithEnvNoClobber(self):
    """Test _RunProcess, simple cmd, with env, doesn't clobber os.environ."""
    environment = os.environ.copy()
    self.mox.ReplayAll()
    gmacpyutil.RunProcess(['/bin/echo'], env={'added_to_env': 'added_to_env'})
    self.assertEqual(environment, os.environ)
    self.mox.VerifyAll()

  def testPrivateRunProcessErrorSudoAndBackground(self):
    """Test _RunProcess fails with sudo and background set."""
    self.mox.ReplayAll()
    with self.assertRaises(gmacpyutil.GmacpyutilException):
      gmacpyutil._RunProcess(['cmd'], background=True, sudo=True)
    self.mox.VerifyAll()

  def testPrivateRunProcessErrorSudoPasswordAndStdinput(self):
    """Test _RunProcess fail with sudo and stdinput set."""
    self.mox.ReplayAll()
    with self.assertRaises(gmacpyutil.GmacpyutilException):
      gmacpyutil._RunProcess(['cmd'], stdinput='input', sudo=True,
                             sudo_password='password')
    self.mox.VerifyAll()

  def testPrivateRunProcessErrorTimeoutAndBackground(self):
    """Test _RunProcess fails with timeout and background set."""
    self.mox.ReplayAll()
    with self.assertRaises(gmacpyutil.GmacpyutilException):
      gmacpyutil._RunProcess(['cmd'], background=True, timeout=1)
    self.mox.VerifyAll()

  def testPrivateRunProcessErrorTimeoutAndStreamOutput(self):
    """Test _RunProcess fails with timeout and stream_output set."""
    self.mox.ReplayAll()
    with self.assertRaises(gmacpyutil.GmacpyutilException):
      gmacpyutil._RunProcess(['cmd'], stream_output=True, timeout=1)
    self.mox.VerifyAll()

  def testPrivateRunProcessErrorTimeoutIsNegative(self):
    """Test _RunProcess fails if timeout is negative."""
    self.mox.ReplayAll()
    with self.assertRaises(gmacpyutil.GmacpyutilException):
      gmacpyutil._RunProcess(['cmd'], timeout=-1)
    self.mox.VerifyAll()

  def testPrivateRunProcessErrorWaitforWithoutTimeout(self):
    """Test _RunProcess fails if waitfor is set without timeout."""
    self.mox.ReplayAll()
    with self.assertRaises(gmacpyutil.GmacpyutilException):
      gmacpyutil._RunProcess(['cmd'], waitfor=1)
    self.mox.VerifyAll()

  def testPrivateRunProcessWithSudo(self):
    """Test _RunProcess, simple command, with sudo."""
    self.StubSetup()
    mock_env = self.mox.CreateMockAnything()
    gmacpyutil.os.environ = mock_env
    gmacpyutil.subprocess.PIPE = 'pipe'
    mock_task = self.mox.CreateMockAnything()
    mock_env.copy().AndReturn(mock_env)
    gmacpyutil.subprocess.Popen(
        ['sudo', '-p', "%u's password is required for admin access: ", 'cmd'],
        stdout='pipe', stderr='pipe', stdin='pipe', env=mock_env,
        cwd=None).AndReturn(mock_task)
    mock_task.communicate(input=None).AndReturn(('out', 'err'))
    mock_task.returncode = 0
    self.mox.ReplayAll()
    self.assertEqual(('out', 'err', 0), gmacpyutil._RunProcess(
        ['cmd'], sudo=True))
    self.mox.VerifyAll()

  def testPrivateRunProcessWithSudoAndSudoPassword(self):
    """Test _RunProcess, simple command, with sudo and sudo_password."""
    self.StubSetup()
    mock_env = self.mox.CreateMockAnything()
    gmacpyutil.os.environ = mock_env
    gmacpyutil.subprocess.PIPE = 'pipe'
    mock_task = self.mox.CreateMockAnything()
    mock_env.copy().AndReturn(mock_env)
    gmacpyutil.subprocess.Popen(
        ['sudo', '-S', 'cmd'], stdout='pipe', stderr='pipe', stdin='pipe',
        env=mock_env, cwd=None).AndReturn(mock_task)
    mock_task.communicate(input='password\n').AndReturn(('out', 'err'))
    mock_task.returncode = 0
    self.mox.ReplayAll()
    self.assertEqual(('out', 'err', 0), gmacpyutil._RunProcess(
        ['cmd'], sudo=True, sudo_password='password'))
    self.mox.VerifyAll()

  def testPrivateRunProcessBackground(self):
    """Test _RunProcess, simple command, default args, in background."""
    self.StubSetup()
    mock_env = self.mox.CreateMockAnything()
    gmacpyutil.os.environ = mock_env
    gmacpyutil.subprocess.PIPE = 'pipe'
    mock_task = self.mox.CreateMockAnything()
    mock_env.copy().AndReturn(mock_env)
    gmacpyutil.subprocess.Popen(
        ['cmd'], stdout='pipe', stderr='pipe', stdin='pipe', env=mock_env,
        cwd=None).AndReturn(mock_task)
    self.mox.ReplayAll()
    self.assertEqual(mock_task,
                     gmacpyutil._RunProcess(['cmd'], background=True))
    self.mox.VerifyAll()

  def testPrivateRunProcessBackgroundWithInput(self):
    """Test _RunProcess, simple command, in background, with input."""
    self.StubSetup()
    mock_env = self.mox.CreateMockAnything()
    gmacpyutil.os.environ = mock_env
    gmacpyutil.subprocess.PIPE = 'pipe'
    mock_task = self.mox.CreateMockAnything()
    mock_write = self.mox.CreateMockAnything()
    mock_env.copy().AndReturn(mock_env)
    gmacpyutil.subprocess.Popen(
        ['cmd'], stdout='pipe', stderr='pipe', stdin='pipe', env=mock_env,
        cwd=None).AndReturn(mock_task)
    mock_task.stdin = mock_write
    mock_write.write('input').AndReturn(None)
    self.mox.ReplayAll()
    self.assertEqual(mock_task,
                     gmacpyutil._RunProcess(
                         ['cmd'], background=True, stdinput='input'))
    self.mox.VerifyAll()

  def testPrivateRunProcessStreamOutput(self):
    """Test _RunProcess, simple command, stream output."""
    self.StubSetup()
    mock_env = self.mox.CreateMockAnything()
    gmacpyutil.os.environ = mock_env
    gmacpyutil.subprocess.PIPE = 'pipe'
    mock_task = self.mox.CreateMockAnything()
    mock_env.copy().AndReturn(mock_env)
    gmacpyutil.subprocess.Popen(
        ['cmd'], stdout=None, stderr=None, stdin='pipe', env=mock_env,
        cwd=None).AndReturn(mock_task)
    mock_task.communicate(input=None).AndReturn((None, None))
    mock_task.returncode = 0
    self.mox.ReplayAll()
    self.assertEqual((None, None, 0),
                     gmacpyutil._RunProcess(['cmd'], stream_output=True))
    self.mox.VerifyAll()

  def testPrivateRunProcessWithTimeout(self):
    """Test _RunProcess with a timeout."""
    self.StubSetup()
    self.mox.StubOutWithMock(gmacpyutil, 'SetFileNonBlocking')
    self.mox.StubOutWithMock(gmacpyutil.select, 'select')
    mock_env = self.mox.CreateMockAnything()
    mock_stderr = self.mox.CreateMockAnything()
    mock_stdout = self.mox.CreateMockAnything()
    gmacpyutil.os.environ = mock_env
    gmacpyutil.subprocess.PIPE = 'pipe'
    mock_task = self.mox.CreateMockAnything()
    mock_task.stdout = mock_stdout
    mock_task.stderr = mock_stderr
    mock_task.returncode = 0
    mock_env.copy().AndReturn(mock_env)
    gmacpyutil.subprocess.Popen(
        ['cmd'], stdout='pipe', stderr='pipe', stdin='pipe', env=mock_env,
        cwd=None).AndReturn(mock_task)
    gmacpyutil.SetFileNonBlocking(mock_task.stdout).AndReturn(None)
    gmacpyutil.SetFileNonBlocking(mock_task.stderr).AndReturn(None)
    gmacpyutil.select.select(
        [mock_task.stdout, mock_task.stderr], [], [], 1.0).AndReturn(
            ([mock_task.stdout, mock_task.stderr], None, None))
    mock_task.poll().AndReturn(0)
    mock_task.poll().AndReturn(0)
    mock_stdout.read().AndReturn('out')
    mock_stderr.read().AndReturn('err')
    self.mox.ReplayAll()
    self.assertEqual(('out', 'err', 0), gmacpyutil._RunProcess(
        ['cmd'], timeout=2))
    self.mox.VerifyAll()

  def testPrivateRunProcessWithTimeoutTimingOut(self):
    """Test _RunProcess with a timeout that times out."""
    self.StubSetup()
    self.mox.StubOutWithMock(gmacpyutil, 'SetFileNonBlocking')
    self.mox.StubOutWithMock(gmacpyutil.os, 'kill')
    self.mox.StubOutWithMock(gmacpyutil.select, 'select')
    mock_env = self.mox.CreateMockAnything()
    mock_stderr = self.mox.CreateMockAnything()
    mock_stdout = self.mox.CreateMockAnything()
    gmacpyutil.os.environ = mock_env
    gmacpyutil.subprocess.PIPE = 'pipe'
    mock_task = self.mox.CreateMockAnything()
    mock_task.stdout = mock_stdout
    mock_task.stderr = mock_stderr
    mock_task.returncode = None
    mock_task.pid = 123
    mock_env.copy().AndReturn(mock_env)
    gmacpyutil.subprocess.Popen(
        ['cmd'], stdout='pipe', stderr='pipe', stdin='pipe', env=mock_env,
        cwd=None).AndReturn(mock_task)
    gmacpyutil.SetFileNonBlocking(mock_task.stdout).AndReturn(None)
    gmacpyutil.SetFileNonBlocking(mock_task.stderr).AndReturn(None)
    gmacpyutil.select.select(
        [mock_task.stdout, mock_task.stderr], [], [], 1.0).AndReturn(
            (None, None, None))
    gmacpyutil.select.select(
        [mock_task.stdout, mock_task.stderr], [], [], 1.0).AndReturn(
            (None, None, None))
    mock_task.poll().AndReturn(None)
    mock_task.poll().AndReturn(None)
    gmacpyutil.logging.error(mox.IgnoreArg(), mox.IgnoreArg()).AndReturn(None)
    gmacpyutil.logging.error(mox.IgnoreArg(), mox.IgnoreArg()).AndReturn(None)
    gmacpyutil.os.kill(mock_task.pid, gmacpyutil.signal.SIGTERM)
    self.mox.ReplayAll()
    self.assertEqual(('', '', None), gmacpyutil._RunProcess(['cmd'], timeout=2))
    self.mox.VerifyAll()

  def testPrivateRunProcessWithTimeoutAndWaitforWhenTimingOut(self):
    """Test _RunProcess with a timeout and waitfor that times out."""
    self.StubSetup()
    self.mox.StubOutWithMock(gmacpyutil, 'SetFileNonBlocking')
    self.mox.StubOutWithMock(gmacpyutil.os, 'kill')
    self.mox.StubOutWithMock(gmacpyutil.select, 'select')
    self.mox.StubOutWithMock(gmacpyutil.time, 'sleep')
    mock_env = self.mox.CreateMockAnything()
    mock_stderr = self.mox.CreateMockAnything()
    mock_stdout = self.mox.CreateMockAnything()
    gmacpyutil.os.environ = mock_env
    gmacpyutil.subprocess.PIPE = 'pipe'
    mock_task = self.mox.CreateMockAnything()
    mock_task.stdout = mock_stdout
    mock_task.stderr = mock_stderr
    mock_task.returncode = None
    mock_task.pid = 123
    mock_env.copy().AndReturn(mock_env)
    gmacpyutil.subprocess.Popen(
        ['cmd'], stdout='pipe', stderr='pipe', stdin='pipe', env=mock_env,
        cwd=None).AndReturn(mock_task)
    gmacpyutil.SetFileNonBlocking(mock_task.stdout).AndReturn(None)
    gmacpyutil.SetFileNonBlocking(mock_task.stderr).AndReturn(None)
    gmacpyutil.select.select(
        [mock_task.stdout, mock_task.stderr], [], [], 1.0).AndReturn(
            (None, None, None))
    gmacpyutil.select.select(
        [mock_task.stdout, mock_task.stderr], [], [], 1.0).AndReturn(
            (None, None, None))
    mock_task.poll().AndReturn(None)
    mock_task.poll().AndReturn(None)
    gmacpyutil.logging.error(mox.IgnoreArg(), mox.IgnoreArg()).AndReturn(None)
    gmacpyutil.logging.error(mox.IgnoreArg(), mox.IgnoreArg()).AndReturn(None)
    gmacpyutil.os.kill(mock_task.pid, gmacpyutil.signal.SIGTERM)
    gmacpyutil.time.sleep(1).AndReturn(None)
    self.mox.ReplayAll()
    self.assertEqual(('', '', None), gmacpyutil._RunProcess(
        ['cmd'], timeout=2, waitfor=1))
    self.mox.VerifyAll()

  def testPrivateRunProcessWithOSError(self):
    """Test _RunProcess when subprocess returns an exception."""
    gmacpyutil.os.environ = mock.MagicMock()
    gmacpyutil.subprocess.Popen = mock.MagicMock()
    gmacpyutil.subprocess.Popen.side_effect = OSError('oops')
    with self.assertRaises(gmacpyutil.GmacpyutilException):
      gmacpyutil._RunProcess(['cmd'])

  def testRunProcessReturnsATuple(self):
    """Test RunProcess returns a 3-tuple."""
    self.mox.StubOutWithMock(gmacpyutil, '_RunProcess')
    gmacpyutil._RunProcess(['cmd']).AndReturn(('out', 'err', 1))
    self.mox.ReplayAll()
    self.assertEqual(3, len(gmacpyutil.RunProcess(['cmd'])))
    self.mox.VerifyAll()

  def testRunProcessFailsWithBackground(self):
    """Test RunProcess fails when called with background=True."""
    self.mox.ReplayAll()
    with self.assertRaises(gmacpyutil.GmacpyutilException):
      gmacpyutil.RunProcess(['foo'], background=True)
    self.mox.VerifyAll()

  def testRunProcessInBackground(self):
    self.mox.StubOutWithMock(gmacpyutil, '_RunProcess')
    gmacpyutil._RunProcess(['cmd'], background=True)
    self.mox.ReplayAll()
    gmacpyutil.RunProcessInBackground(['cmd'])
    self.mox.VerifyAll()

  def testGetPlistKey(self):
    """Test GetPlistKey."""
    self.StubSetup()
    gmacpyutil.NSDictionary.dictionaryWithContentsOfFile_(
        gmacpyutil.MACHINEINFO).AndReturn({'key': 'value'})
    self.mox.ReplayAll()
    self.assertEqual('value',
                     gmacpyutil.GetPlistKey(gmacpyutil.MACHINEINFO, 'key'))
    self.mox.VerifyAll()

  def testGetPlistKeyWhenKeyNotFound(self):
    """Test GetPlistKey when the key's not found."""
    self.StubSetup()
    gmacpyutil.NSDictionary.dictionaryWithContentsOfFile_(
        gmacpyutil.MACHINEINFO).AndReturn({'key': 'value'})
    self.mox.ReplayAll()
    self.assertEqual(None,
                     gmacpyutil.GetPlistKey(gmacpyutil.MACHINEINFO, 'missing'))
    self.mox.VerifyAll()

  def testGetPlistKeyWhenPlistNotFound(self):
    """Test GetPlistKey when the machineinfo plist's not found."""
    self.StubSetup()
    gmacpyutil.NSDictionary.dictionaryWithContentsOfFile_(
        gmacpyutil.MACHINEINFO).AndReturn(None)
    self.mox.ReplayAll()
    self.assertEqual(None,
                     gmacpyutil.GetPlistKey(gmacpyutil.MACHINEINFO,
                                            'something'))
    self.mox.VerifyAll()

  def testGetPlistKeyRaisesExceptionWhenMissingNSDictionary(self):
    """Test GetPlistKey raises and exception when NSDictionary is missing."""
    gmacpyutil.NSDictionary = None
    self.mox.ReplayAll()
    with self.assertRaises(gmacpyutil.MissingImportsError):
      gmacpyutil.GetPlistKey('a path', 'a key')
    self.mox.VerifyAll()

  def testSetPlistKey(self):
    """Test SetPlistKey."""
    self.StubSetup()
    mock_mach_info = self.mox.CreateMockAnything()
    gmacpyutil.NSMutableDictionary.dictionaryWithContentsOfFile_(
        gmacpyutil.MACHINEINFO).AndReturn(mock_mach_info)
    mock_mach_info.__setitem__('missing', 'value').AndReturn(None)
    mock_mach_info.writeToFile_atomically_(
        gmacpyutil.MACHINEINFO, True).AndReturn(True)
    self.mox.ReplayAll()
    self.assertTrue(gmacpyutil.SetPlistKey(gmacpyutil.MACHINEINFO, 'missing',
                                           'value'))
    self.mox.VerifyAll()

  def testSetPlistKeyWhenPlistNotThere(self):
    """Test SetPlistKey when the plist doesn't exist."""
    self.StubSetup()
    mock_mach_info = self.mox.CreateMockAnything()
    mock_dict = self.mox.CreateMockAnything()
    gmacpyutil.NSMutableDictionary.dictionaryWithContentsOfFile_(
        gmacpyutil.MACHINEINFO).AndReturn(None)
    gmacpyutil.NSMutableDictionary.alloc().AndReturn(mock_dict)
    mock_dict.init().AndReturn(mock_mach_info)
    mock_mach_info.__setitem__('missing', 'value').AndReturn(None)
    mock_mach_info.writeToFile_atomically_(
        gmacpyutil.MACHINEINFO, True).AndReturn(True)
    self.mox.ReplayAll()
    self.assertTrue(gmacpyutil.SetPlistKey(gmacpyutil.MACHINEINFO, 'missing',
                                           'value'))
    self.mox.VerifyAll()

  def testSetPlistKeyRaisesExceptionWhenMissingNSMutableDictionary(self):
    """Test SetPlistKey raises exception when NSMutableDictionary is missing."""
    gmacpyutil.NSMutableDictionary = None
    self.mox.ReplayAll()
    with self.assertRaises(gmacpyutil.MissingImportsError):
      gmacpyutil.SetPlistKey('a path', 'a key', 'a value')
    self.mox.VerifyAll()

  def testFacts(self):
    """Test Facts."""
    self.mox.StubOutWithMock(gmacpyutil, 'RunProcess')
    puppet_cmd = ['/usr/bin/puppet', 'config', '--config',
                  '/etc/puppet/puppet.conf', 'print', 'factpath']
    facter_cmd = ['/usr/bin/facter', '-p']
    facter_out = 'fact1 => 1\nfact2 => value2\nfact3 => value 3'
    facts = {'fact1': '1', 'fact2': 'value2', 'fact3': 'value 3'}
    env = {'RUBYLIB': 'factpath'}
    gmacpyutil.RunProcess(puppet_cmd).AndReturn(('factpath\n', 'err\n', 0))
    gmacpyutil.RunProcess(facter_cmd, env=env).AndReturn(
        (facter_out, 'err\n', 0))
    self.mox.ReplayAll()
    self.assertEqual(facts, gmacpyutil.Facts())
    self.mox.VerifyAll()

  def testFactsWithMalformedOutput(self):
    """Test Facts with malformed output."""
    self.mox.StubOutWithMock(gmacpyutil, 'RunProcess')
    puppet_cmd = ['/usr/bin/puppet', 'config', '--config',
                  '/etc/puppet/puppet.conf', 'print', 'factpath']
    facter_cmd = ['/usr/bin/facter', '-p']
    facter_out = 'fact1 => 1\nfact2 => value2\n\nfact3 =>\nfact4\n'
    facts = {'fact1': '1', 'fact2': 'value2', 'fact3': ''}
    env = {'RUBYLIB': 'factpath'}
    gmacpyutil.RunProcess(puppet_cmd).AndReturn(('factpath\n', 'err\n', 0))
    gmacpyutil.RunProcess(facter_cmd, env=env).AndReturn(
        (facter_out, 'err\n', 0))
    self.mox.ReplayAll()
    self.assertEqual(facts, gmacpyutil.Facts())
    self.mox.VerifyAll()

  def testFactsPuppetError(self):
    """Test Facts when puppet fails."""
    self.mox.StubOutWithMock(gmacpyutil, 'RunProcess')
    puppet_cmd = ['/usr/bin/puppet', 'config', '--config',
                  '/etc/puppet/puppet.conf', 'print', 'factpath']
    gmacpyutil.RunProcess(puppet_cmd).AndReturn(('out\n', 'err\n', 1))
    self.mox.ReplayAll()
    self.assertRaises(gmacpyutil.GmacpyutilException, gmacpyutil.Facts)
    self.mox.VerifyAll()

  def testFactsFacterError(self):
    """Test Facts when facter fails."""
    self.mox.StubOutWithMock(gmacpyutil, 'RunProcess')
    puppet_cmd = ['/usr/bin/puppet', 'config', '--config',
                  '/etc/puppet/puppet.conf', 'print', 'factpath']
    facter_cmd = ['/usr/bin/facter', '-p']
    env = {'RUBYLIB': 'factpath'}
    gmacpyutil.RunProcess(puppet_cmd).AndReturn(('factpath\n', 'err\n', 0))
    gmacpyutil.RunProcess(facter_cmd, env=env).AndReturn(('out\n', 'err\n', 1))
    self.mox.ReplayAll()
    self.assertRaises(gmacpyutil.GmacpyutilException, gmacpyutil.Facts)
    self.mox.VerifyAll()

  def testFactValue(self):
    """Test FactValue."""
    self.mox.StubOutWithMock(gmacpyutil, 'Facts')
    gmacpyutil.Facts().AndReturn({'fact': 'value'})
    self.mox.ReplayAll()
    self.assertEqual('value', gmacpyutil.FactValue('fact'))
    self.mox.VerifyAll()

  def testFactValueNoMatch(self):
    """Test FactValue, no matching Fact."""
    self.mox.StubOutWithMock(gmacpyutil, 'Facts')
    gmacpyutil.Facts().AndReturn({'nope': 'value'})
    self.mox.ReplayAll()
    self.assertEqual(None, gmacpyutil.FactValue('fact'))
    self.mox.VerifyAll()


  def testIsTextConsole(self):
    """Test IsTextConsole()."""
    self.mox.StubOutWithMock(gmacpyutil.ctypes.cdll, 'LoadLibrary')
    self.mox.StubOutWithMock(gmacpyutil.ctypes, 'c_int')
    self.mox.StubOutWithMock(gmacpyutil.ctypes, 'byref')

    session_id = 1
    attributes = self.mox.CreateMockAnything()
    attributes.value = 1234 | gmacpyutil.SESSIONHASGRAPHICACCESS
    ret = 0

    mock_security = self.mox.CreateMockAnything()

    gmacpyutil.ctypes.cdll.LoadLibrary(
        '/System/Library/Frameworks/Security.framework/Security').AndReturn(
            mock_security)

    gmacpyutil.ctypes.c_int(0).AndReturn(session_id)
    gmacpyutil.ctypes.c_int(0).AndReturn(attributes)
    gmacpyutil.ctypes.byref(session_id).AndReturn(session_id)
    gmacpyutil.ctypes.byref(attributes).AndReturn(attributes)

    mock_security.SessionGetInfo(-1, session_id, attributes).AndReturn(ret)

    self.mox.ReplayAll()
    self.assertFalse(gmacpyutil.IsTextConsole())
    self.mox.VerifyAll()

  def testIsTextConsoleWhenText(self):
    """Test IsTextConsole() when text."""
    self.mox.StubOutWithMock(gmacpyutil.ctypes.cdll, 'LoadLibrary')
    self.mox.StubOutWithMock(gmacpyutil.ctypes, 'c_int')
    self.mox.StubOutWithMock(gmacpyutil.ctypes, 'byref')

    session_id = 1
    attributes = self.mox.CreateMockAnything()
    attributes.value = 0
    ret = 0

    mock_security = self.mox.CreateMockAnything()

    gmacpyutil.ctypes.cdll.LoadLibrary(
        '/System/Library/Frameworks/Security.framework/Security').AndReturn(
            mock_security)

    gmacpyutil.ctypes.c_int(0).AndReturn(session_id)
    gmacpyutil.ctypes.c_int(0).AndReturn(attributes)
    gmacpyutil.ctypes.byref(session_id).AndReturn(session_id)
    gmacpyutil.ctypes.byref(attributes).AndReturn(attributes)

    mock_security.SessionGetInfo(-1, session_id, attributes).AndReturn(ret)

    self.mox.ReplayAll()
    self.assertTrue(gmacpyutil.IsTextConsole())
    self.mox.VerifyAll()

  def testIsTextConsoleWhenSessionGetInfoError(self):
    """Test IsTextConsole() when session getinfo errors."""
    self.mox.StubOutWithMock(gmacpyutil.ctypes.cdll, 'LoadLibrary')
    self.mox.StubOutWithMock(gmacpyutil.ctypes, 'c_int')
    self.mox.StubOutWithMock(gmacpyutil.ctypes, 'byref')

    session_id = 1
    attributes = self.mox.CreateMockAnything()
    attributes.value = 0
    ret = 1

    mock_security = self.mox.CreateMockAnything()

    gmacpyutil.ctypes.cdll.LoadLibrary(
        '/System/Library/Frameworks/Security.framework/Security').AndReturn(
            mock_security)

    gmacpyutil.ctypes.c_int(0).AndReturn(session_id)
    gmacpyutil.ctypes.c_int(0).AndReturn(attributes)
    gmacpyutil.ctypes.byref(session_id).AndReturn(session_id)
    gmacpyutil.ctypes.byref(attributes).AndReturn(attributes)

    mock_security.SessionGetInfo(-1, session_id, attributes).AndReturn(ret)

    self.mox.ReplayAll()
    self.assertTrue(gmacpyutil.IsTextConsole())
    self.mox.VerifyAll()

  def testIsTextConsoleWhenCtypesException(self):
    """Test IsTextConsole() when ctypes raises an exception."""
    self.mox.StubOutWithMock(gmacpyutil.ctypes.cdll, 'LoadLibrary')

    gmacpyutil.ctypes.cdll.LoadLibrary(
        '/System/Library/Frameworks/Security.framework/Security').AndRaise(
            OSError)

    self.mox.ReplayAll()
    self.assertTrue(gmacpyutil.IsTextConsole())
    self.mox.VerifyAll()


  def testGetConsoleUser(self):
    """Test GetConsoleUser."""
    self.mox.StubOutWithMock(gmacpyutil.os, 'stat')
    self.mox.StubOutWithMock(gmacpyutil.pwd, 'getpwuid')

    console_user = 'macadmin'
    stat_info = self.mox.CreateMockAnything()
    stat_info.st_uid = 501
    gmacpyutil.os.stat('/dev/console').AndReturn(stat_info)
    gmacpyutil.pwd.getpwuid(501).AndReturn((console_user, 501))

    self.mox.ReplayAll()
    self.assertEqual(console_user, gmacpyutil.GetConsoleUser())
    self.mox.VerifyAll()

  def testGetAirportInfoOn(self):
    """Test GetAirportInfo when WiFi is on and connected."""
    gmacpyutil.objc = self.mox.CreateMockAnything()
    gmacpyutil.CWInterface = self.mox.CreateMockAnything()
    mock_cwinterface = self.mox.CreateMockAnything()

    gmacpyutil.objc.loadBundle(mox.IgnoreArg(), mox.IgnoreArg(),
                               bundle_path=mox.IgnoreArg())
    gmacpyutil.CWInterface.interface().AndReturn(mock_cwinterface)
    mock_cwinterface.interfaceName().AndReturn(u'en1')
    mock_cwinterface.hardwareAddress().AndReturn(u'20:c9:d0:94:17:c7')
    mock_cwinterface.serviceActive().AndReturn(1)
    mock_cwinterface.countryCode().AndReturn(u'US')
    mock_cwinterface.powerOn().AndReturn(1)
    mock_cwinterface.ssid().AndReturn(u'SSID')
    mock_cwinterface.bssid().AndReturn(u'd8:c7:c8:b5:ae:50')
    mock_cwinterface.noiseMeasurement().AndReturn(-90)
    mock_cwinterface.activePHYMode().AndReturn(4)
    mock_cwinterface.activePHYMode().AndReturn(4)
    mock_cwinterface.rssiValue().AndReturn(-71)
    mock_cwinterface.interfaceState().AndReturn(4)
    mock_cwinterface.interfaceState().AndReturn(4)
    mock_cwinterface.transmitPower().AndReturn(1496)
    mock_cwinterface.transmitRate().AndReturn(216.0)

    mock_channel = self.mox.CreateMockAnything()
    mock_cwinterface.wlanChannel().AndReturn(mock_channel)
    mock_channel.channelNumber().AndReturn(153)
    mock_channel.channelBand().AndReturn(2)

    mock_cwinterface.security().AndReturn(9)

    airport_info_results = {'name': u'en1',
                            'power': True,
                            'channel_number': 153,
                            'state_name': u'Running',
                            'BSSID': u'd8:c7:c8:b5:ae:50',
                            'service_active': True,
                            'security_name': u'WPA2 Enterprise',
                            'transmit_rate': 216.0,
                            'hw_address': u'20:c9:d0:94:17:c7',
                            'phy_mode': 4,
                            'state': 4,
                            'noise_measurement': -90,
                            'channel_band': u'5 GHz',
                            'country_code': u'US',
                            'rssi': -71,
                            'phy_mode_name': u'802.11n',
                            'security': 9,
                            'transmit_power': 1496,
                            'SSID': u'SSID'}

    self.mox.ReplayAll()
    self.assertEqual(airport_info_results, gmacpyutil.GetAirportInfo())
    self.mox.VerifyAll()

  def testGetAirportInfoOff(self):
    """Test GetAirportInfo when WiFi is off."""
    gmacpyutil.objc = self.mox.CreateMockAnything()
    gmacpyutil.CWInterface = self.mox.CreateMockAnything()
    mock_cwinterface = self.mox.CreateMockAnything()

    gmacpyutil.objc.loadBundle(mox.IgnoreArg(), mox.IgnoreArg(),
                               bundle_path=mox.IgnoreArg())
    gmacpyutil.CWInterface.interface().AndReturn(mock_cwinterface)
    mock_cwinterface.interfaceName().AndReturn(u'en1')
    mock_cwinterface.hardwareAddress().AndReturn(u'20:c9:d0:94:17:c7')
    mock_cwinterface.serviceActive().AndReturn(1)
    mock_cwinterface.countryCode().AndReturn(u'US')
    mock_cwinterface.powerOn().AndReturn(0)
    mock_cwinterface.ssid().AndReturn(None)
    mock_cwinterface.bssid().AndReturn(None)
    mock_cwinterface.noiseMeasurement().AndReturn(0)
    mock_cwinterface.activePHYMode().AndReturn(0)
    mock_cwinterface.activePHYMode().AndReturn(0)
    mock_cwinterface.rssiValue().AndReturn(0)
    mock_cwinterface.interfaceState().AndReturn(0)
    mock_cwinterface.interfaceState().AndReturn(0)
    mock_cwinterface.transmitPower().AndReturn(1496)
    mock_cwinterface.transmitRate().AndReturn(0.0)

    mock_cwinterface.wlanChannel().AndReturn(None)

    mock_cwinterface.security().AndReturn(90122091824908)

    airport_info_results = {'name': u'en1',
                            'power': False,
                            'state_name': u'Inactive',
                            'BSSID': None,
                            'service_active': True,
                            'security_name': u'Unknown',
                            'transmit_rate': 0.0,
                            'hw_address': u'20:c9:d0:94:17:c7',
                            'phy_mode': 0,
                            'state': 0,
                            'noise_measurement': 0,
                            'country_code': u'US',
                            'rssi': 0,
                            'phy_mode_name': u'None',
                            'security': -1,
                            'transmit_power': 1496,
                            'SSID': None}

    self.mox.ReplayAll()
    self.assertEqual(airport_info_results, gmacpyutil.GetAirportInfo())
    self.mox.VerifyAll()

  def testGetAirportInfoNoInterface(self):
    """Test GetAirportInfo when there is no Wi-Fi interface."""
    gmacpyutil.objc = self.mox.CreateMockAnything()
    gmacpyutil.CWInterface = self.mox.CreateMockAnything()
    gmacpyutil.objc.loadBundle(mox.IgnoreArg(), mox.IgnoreArg(),
                               bundle_path=mox.IgnoreArg())
    gmacpyutil.CWInterface.interface().AndReturn(None)

    self.mox.ReplayAll()
    self.assertEqual({}, gmacpyutil.GetAirportInfo())
    self.mox.VerifyAll()

  def testGetPowerStateOnACNoBattery(self):
    """Test GetPowerState when on AC power and no battery."""
    self.mox.StubOutWithMock(gmacpyutil, 'RunProcess')
    cmd = ['/usr/bin/pmset', '-g', 'ps']
    stdout = "Currently drawing from 'AC Power'\n"
    mock_power_info = {'ac_power': True,
                       'battery_percent': '-1',
                       'battery_state': '-1',
                       'minutes_remaining': '-1'}

    gmacpyutil.RunProcess(cmd).AndReturn((stdout, None, 0))

    self.mox.ReplayAll()
    self.assertEqual(mock_power_info, gmacpyutil.GetPowerState())
    self.mox.VerifyAll()

  def testGetPowerStateOnACFull(self):
    """Test GetPowerState when on AC power and battery is full."""
    self.mox.StubOutWithMock(gmacpyutil, 'RunProcess')
    cmd = ['/usr/bin/pmset', '-g', 'ps']
    stdout = ("Currently drawing from 'AC Power'\n "
              "-InternalBattery-0\t100%; charged; 0:00 remaining\n")
    mock_power_info = {'ac_power': True,
                       'battery_percent': 100,
                       'battery_state': 'charged',
                       'minutes_remaining': 0}

    gmacpyutil.RunProcess(cmd).AndReturn((stdout, None, 0))

    self.mox.ReplayAll()
    self.assertEqual(mock_power_info, gmacpyutil.GetPowerState())
    self.mox.VerifyAll()

  def testGetPowerStateDischarging(self):
    """Test GetPowerState when battery is discharging."""
    self.mox.StubOutWithMock(gmacpyutil, 'RunProcess')
    cmd = ['/usr/bin/pmset', '-g', 'ps']
    stdout = ("Currently drawing from 'Battery Power'\n "
              "-InternalBattery-0\t50%; discharging; 3:42 remaining\n")
    mock_power_info = {'ac_power': False,
                       'battery_percent': 50,
                       'battery_state': 'discharging',
                       'minutes_remaining': 222}

    gmacpyutil.RunProcess(cmd).AndReturn((stdout, None, 0))

    self.mox.ReplayAll()
    self.assertEqual(mock_power_info, gmacpyutil.GetPowerState())
    self.mox.VerifyAll()

  def testGetPowerStateBatteryRegexFail(self):
    """Test GetPowerState when regular expression matching fails."""
    self.mox.StubOutWithMock(gmacpyutil, 'RunProcess')
    cmd = ['/usr/bin/pmset', '-g', 'ps']
    stdout = ("Currently drawing from 'Battery Power'\n "
              "-InternalBattery-0\t99%; discharging; (no estimate)\n")
    mock_power_info = {'ac_power': False,
                       'battery_percent': '-1',
                       'battery_state': '-1',
                       'minutes_remaining': '-1'}

    gmacpyutil.RunProcess(cmd).AndReturn((stdout, None, 0))

    self.mox.ReplayAll()
    self.assertEqual(mock_power_info, gmacpyutil.GetPowerState())
    self.mox.VerifyAll()

  def testGetPowerStateBothRegexFail(self):
    """Test GetPowerState when regular expression matching fails."""
    self.mox.StubOutWithMock(gmacpyutil, 'RunProcess')
    cmd = ['/usr/bin/pmset', '-g', 'ps']
    stdout = ('foo')
    mock_power_info = {'ac_power': '-1',
                       'battery_percent': '-1',
                       'battery_state': '-1',
                       'minutes_remaining': '-1'}

    gmacpyutil.RunProcess(cmd).AndReturn((stdout, None, 0))

    self.mox.ReplayAll()
    self.assertEqual(mock_power_info, gmacpyutil.GetPowerState())
    self.mox.VerifyAll()

  def testGetTrackEqualsTesting(self):
    self.mox.StubOutWithMock(gmacpyutil, 'GetMajorOSVersion')
    self.mox.StubOutWithMock(gmacpyutil, 'MachineInfoForKey')

    gmacpyutil.GetMajorOSVersion().AndReturn('10.8')
    gmacpyutil.MachineInfoForKey('Track').AndReturn('testing')

    self.mox.ReplayAll()
    track = gmacpyutil.GetTrack()
    self.assertEqual(track, 'testing')
    self.mox.VerifyAll()

  def testGetTrackEqualsNone(self):
    self.mox.StubOutWithMock(gmacpyutil, 'GetMajorOSVersion')
    self.mox.StubOutWithMock(gmacpyutil, 'MachineInfoForKey')

    gmacpyutil.GetMajorOSVersion().AndReturn('10.8')
    gmacpyutil.MachineInfoForKey('Track').AndReturn(None)

    self.mox.ReplayAll()
    track = gmacpyutil.GetTrack()
    self.assertEqual(track, 'stable')
    self.mox.VerifyAll()

  def testGetTrackReturnsUnexpected(self):
    self.mox.StubOutWithMock(gmacpyutil, 'GetMajorOSVersion')
    self.mox.StubOutWithMock(gmacpyutil, 'MachineInfoForKey')

    gmacpyutil.GetMajorOSVersion().AndReturn('10.8')
    gmacpyutil.MachineInfoForKey('Track').AndReturn('foobar')

    self.mox.ReplayAll()
    track = gmacpyutil.GetTrack()
    self.assertEqual(track, 'stable')
    self.mox.VerifyAll()

  def testGetTrackUnsupportedOS(self):
    self.mox.StubOutWithMock(gmacpyutil, 'GetMajorOSVersion')
    self.mox.StubOutWithMock(gmacpyutil, 'MachineInfoForKey')

    gmacpyutil.GetMajorOSVersion().AndReturn('11.0')
    gmacpyutil.MachineInfoForKey('Track').AndReturn('stable')

    self.mox.ReplayAll()
    track = gmacpyutil.GetTrack()
    self.assertEqual(track, 'unstable')
    self.mox.VerifyAll()

  def testGetOSVersion(self):
    self.mox.StubOutWithMock(gmacpyutil, 'RunProcess')
    cmd = ['sw_vers', '-productVersion']
    gmacpyutil.RunProcess(cmd).AndReturn(('10.8.4', '', 0))

    self.mox.ReplayAll()
    os_version = gmacpyutil.GetOSVersion()
    self.assertEqual(os_version, '10.8.4')
    self.mox.VerifyAll()

  def testGetOSVersionFails(self):
    self.mox.StubOutWithMock(gmacpyutil, 'RunProcess')
    cmd = ['sw_vers', '-productVersion']
    gmacpyutil.RunProcess(cmd).AndReturn(('', '', 1))

    self.mox.ReplayAll()
    self.assertRaises(gmacpyutil.GmacpyutilException,
                      gmacpyutil.GetOSVersion)
    self.mox.VerifyAll()

  def testGetOSVersionMatchFails(self):
    self.mox.StubOutWithMock(gmacpyutil, 'RunProcess')
    cmd = ['sw_vers', '-productVersion']
    gmacpyutil.RunProcess(cmd).AndReturn(('foobar', '', 0))

    self.mox.ReplayAll()
    self.assertRaises(gmacpyutil.GmacpyutilException,
                      gmacpyutil.GetOSVersion)
    self.mox.VerifyAll()

  def testGetMajorOSVersion(self):
    self.mox.StubOutWithMock(gmacpyutil, 'GetOSVersion')
    gmacpyutil.GetOSVersion().AndReturn('10.8.4')

    self.mox.ReplayAll()
    major_os_version = gmacpyutil.GetMajorOSVersion()
    self.assertEqual(major_os_version, '10.8')
    self.mox.VerifyAll()

  def testGetMajorOSVersionFails(self):
    self.mox.StubOutWithMock(gmacpyutil, 'GetMajorOSVersion')
    gmacpyutil.GetMajorOSVersion().AndReturn(False)

    self.mox.ReplayAll()
    track = gmacpyutil.GetTrack()
    self.assertEqual(track, 'stable')
    self.mox.VerifyAll()

  def testGetMajorOSVersionInitialRelease(self):
    self.mox.StubOutWithMock(gmacpyutil, 'GetOSVersion')
    gmacpyutil.GetOSVersion().AndReturn('10.9')

    self.mox.ReplayAll()
    major_os_version = gmacpyutil.GetMajorOSVersion()
    self.assertEqual(major_os_version, '10.9')
    self.mox.VerifyAll()

  def testGetMajorOSVersion10_10(self):
    self.mox.StubOutWithMock(gmacpyutil, 'GetOSVersion')
    gmacpyutil.GetOSVersion().AndReturn('10.10.1')

    self.mox.ReplayAll()
    major_os_version = gmacpyutil.GetMajorOSVersion()
    self.assertEqual(major_os_version, '10.10')
    self.mox.VerifyAll()


def main(unused_argv):
  basetest.main()


if __name__ == '__main__':
  app.run()
