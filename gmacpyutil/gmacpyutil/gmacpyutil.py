"""Modules and methods for managing OS X."""

import contextlib
import ctypes
import fcntl
import logging
import logging.handlers
import os
import pwd
import re
import select
import signal
import socket
import subprocess
import sys
import time
from . import defaults
from distutils import version as distutils_version

if os.uname()[0] == 'Linux':
  pass
else:
  try:
    import objc
  except ImportError:
    print >>sys.stderr, ('Can\'t import Mac-specific objc library! '
                         'Some functionality may be broken.')
    objc = None
  try:
    from Foundation import NSDictionary
    from Foundation import NSMutableDictionary
  except ImportError:
    print >>sys.stderr, ('Can\'t import Mac-specific Foundation libraries! '
                         'Some functionality may be broken.')
    NSDictionary = None
    NSMutableDictionary = None
  try:
    from CoreFoundation import CFStringCreateWithCString
    from CoreFoundation import kCFStringEncodingASCII
  except ImportError:
    print >>sys.stderr, ('Can\'t import Mac-specific CoreFoundation libraries! '
                         'Some functionality may be broken.')
    CFStringCreateWithCString = None
    kCFStringEncodingASCII = None

MACHINEINFO = defaults.MACHINEINFO
IMAGEINFO = defaults.IMAGEINFO
# Security.Framework/Headers/AuthSession.h
SESSIONHASGRAPHICACCESS = 0x0010  # pylint: disable=g-bad-name

# These need to be handled differently to avoid duplicating information and to
# ensure correct senders are stored in asl for launchdaemons.
LOG_FORMAT_SYSLOG = '%(pathname)s[%(process)d]:%(message)s'
LOG_FORMAT_STDERR_LEVEL = '%(levelname)s: %(message)s'
LOG_FORMAT_STDERR = '%(message)s'

# Maximum supported version of OS X.
MAX_SUPPORTED_VERS = '10.10'


class GmacpyutilException(Exception):
  """Module specific error class."""


class LogConfigurationError(GmacpyutilException):
  """Bad logging configuration."""




class MissingImportsError(GmacpyutilException):
  """Missing Mac-specific imports."""


class MultilineSysLogHandler(logging.handlers.SysLogHandler):
  """SysLogHandler subclass which splits very long messages gracefully.

  Messages over 2000 characters will be split either (in order of preference):
    1) On the nearest newline between 1000-2000 characters.
    2) On the nearest space between 1000-2000 characters.
    3) On the 2000 character mark.
  """

  def emit(self, record):
    msg = self.format(record)

    if len(msg) > 2000:
      break_loc_pre = 0
      for break_char in ['\n', ' ', '\t']:
        break_loc_pre = msg.rfind(break_char, 1000, 2000)
        break_loc_post = break_loc_pre + 1
        if break_loc_pre > 0:
          break

      if break_loc_pre < 1:
        break_loc_pre = 2000
        break_loc_post = 2000

      r1msg = msg[:break_loc_pre]
      r2msg = 'CONTINUED: %s' % msg[break_loc_post:]

      r1 = logging.LogRecord(
          record.name, record.levelno, record.pathname, record.lineno,
          r1msg, None, None, func=record.funcName)
      r2 = logging.LogRecord(
          record.name, record.levelno, record.pathname, None, r2msg, None, None)

      logging.handlers.SysLogHandler.emit(self, r1)
      self.emit(r2)
    else:
      logging.handlers.SysLogHandler.emit(self, record)


def _ConfigureHandler(handler, logger, formatstr, debug_level):
  """Configure handler and add it to logger.

  Args:
    handler: logging handler to be configured
    logger: logger to add handler to
    formatstr: log format string
    debug_level: logging level to set
  """
  handler.setFormatter(logging.Formatter(formatstr))
  handler.setLevel(debug_level)
  logger.addHandler(handler)


def ConfigureLogging(debug_level=logging.INFO,
                     show_level=True,
                     stderr=True,
                     syslog=True,
                     facility=None):
  """Sets up logging defaults for the root logger.

  LaunchDaemons should use syslog and disable stderr (or send it to /dev/null in
  the launchd plist). This ensures that multi-line logs (such as those from
  logging.exception) are not split and we don't get dups.

  Other programs should use both stderr and syslog (the default).

  Possible syslog facility names come from
  logging.handlers.SysLogHandler.facility_names.keys():
  ['ftp', 'daemon', 'uucp', 'security', 'local7', 'local4', 'lpr', 'auth',
   'local0', 'cron', 'syslog', 'user', 'mail', 'local5', 'kern', 'news',
   'local6', 'local1', 'authpriv', 'local3', 'local2']

  Args:
    debug_level: python logging level
    show_level: show the logging level in the message for stderr
    stderr: If true, log to stderr
    syslog: If true log to syslog
    facility: string, syslog facility to use
  Raises:
    LogConfigurationError: if no handers are set
  """
  if not stderr and not syslog:
    raise LogConfigurationError('Neither syslog nor stdout handlers set.')

  if facility and not syslog:
    raise LogConfigurationError('facility can only be used with syslog.')

  logger = logging.getLogger()

  # Clear any existing handlers
  logger.handlers = []

  logger.setLevel(debug_level)
  if syslog:
    # Get the default syslog facility
    facility_id = logging.handlers.SysLogHandler.LOG_USER
    if facility:
      try:
        facility_id = logging.handlers.SysLogHandler.facility_names[facility]
      except KeyError:
        logging.error('%s is an invalid facility, using default.', facility)
    try:
      syslog_handler = MultilineSysLogHandler(facility=facility_id)
      _ConfigureHandler(syslog_handler, logger, LOG_FORMAT_SYSLOG, debug_level)
    except socket.error:
      print >>sys.stderr, 'Warning: Could not configure syslog based logging.'
      stderr = True

  if stderr:
    stderr_handler = logging.StreamHandler()
    if show_level:
      _ConfigureHandler(stderr_handler, logger, LOG_FORMAT_STDERR_LEVEL,
                        debug_level)
    else:
      _ConfigureHandler(stderr_handler, logger, LOG_FORMAT_STDERR, debug_level)

  logging.debug('Logging enabled at level %s', debug_level)


def SetFileNonBlocking(f, non_blocking=True):
  """Set non-blocking flag on a file object.

  Args:
    f: file
    non_blocking: bool, default True, non-blocking mode or not
  """
  flags = fcntl.fcntl(f.fileno(), fcntl.F_GETFL)
  if bool(flags & os.O_NONBLOCK) != non_blocking:
    flags ^= os.O_NONBLOCK
  fcntl.fcntl(f.fileno(), fcntl.F_SETFL, flags)


def _RunProcess(cmd, stdinput=None, env=None, cwd=None, sudo=False,
                sudo_password=None, background=False, stream_output=False,
                timeout=0, waitfor=0):
  """Executes cmd using suprocess.

  Args:
    cmd: An array of strings as the command to run
    stdinput: An optional sting as stdin
    env: An optional dictionary as the environment
    cwd: An optional string as the current working directory
    sudo: An optional boolean on whether to do the command via sudo
    sudo_password: An optional string of the password to use for sudo
    background: Launch command in background mode
    stream_output: An optional boolean on whether to send output to the screen
    timeout: An optional int or float; if >0, Exec() will stop waiting for
      output after timeout seconds and kill the process it started. Return code
      might be undefined, or -SIGTERM, use waitfor to make sure to obtain it.
      values <1 will be crudely rounded off because of select() sleep time.
    waitfor: An optional int or float, if >0, Exec() will wait waitfor seconds
      before asking for the process exit status one more time.
  Returns:
    Tuple: two strings and an integer: (stdout, stderr, returncode);
    stdout/stderr may also be None. If the process is set to launch in
    background mode, a tuple of (<subprocess.Popen object>, None, None) is
    returned, in order to be able to read from its pipes *and* use poll() to
    check when it is finished
  Raises:
    GmacpyutilException: If both stdinput and sudo_password are specified
    GmacpyutilException: If both sudo and background are specified
    GmacpyutilException: If both timeout and background, stream_output, sudo, or
      sudo_password, or stdinput are specified
    GmacpyutilException: If timeout is less than 0
    GmacpyutilException: If subprocess raises an OSError
  """
  if timeout and (background or stream_output or sudo or sudo_password or
                  stdinput):
    raise GmacpyutilException('timeout is not compatible with background, '
                              'stream_output, sudo, sudo_password, or '
                              'stdinput.')
  if waitfor and not timeout:
    raise GmacpyutilException('waitfor only valid with timeout.')
  if timeout < 0:
    raise GmacpyutilException('timeout must be greater than 0.')
  if stream_output:
    stdoutput = None
    stderror = None
  else:
    stdoutput = subprocess.PIPE
    stderror = subprocess.PIPE
  if sudo and not background:
    sudo_cmd = ['sudo']
    if sudo_password and not stdinput:
      # Set sudo to get password from stdin
      sudo_cmd.extend(['-S'])
      stdinput = sudo_password + '\n'
    elif sudo_password and stdinput:
      raise GmacpyutilException('stdinput and sudo_password are mutually '
                                'exclusive')
    else:
      sudo_cmd.extend(['-p', "%u's password is required for admin access: "])
    sudo_cmd.extend(cmd)
    cmd = sudo_cmd
  elif sudo and background:
    raise GmacpyutilException('sudo is not compatible with background.')
  environment = os.environ.copy()
  if env is not None:
    environment.update(env)
  try:
    task = subprocess.Popen(cmd, stdout=stdoutput, stderr=stderror,
                            stdin=subprocess.PIPE, env=environment, cwd=cwd)
  except OSError, e:
    raise GmacpyutilException('Could not execute: %s' % e.strerror)
  if timeout == 0:
    # communicate() will wait until the process is finished, so if we are in
    # background mode, just send the input and take the pipe objects as output.
    if not background:
      (stdout, stderr) = task.communicate(input=stdinput)
      return (stdout, stderr, task.returncode)
    else:
      if stdinput:
        task.stdin.write(stdinput)
      return task
  else:
    # TODO(user): See if it's possible to pass stdinput when using a timeout
    inactive = 0
    stdoutput = []
    stderror = []
    SetFileNonBlocking(task.stdout)
    SetFileNonBlocking(task.stderr)
    returncode = None
    while returncode is None:
      rlist, _, _ = select.select([task.stdout, task.stderr], [], [], 1.0)
      if not rlist:
        inactive += 1
        if inactive >= timeout:
          logging.error('cmd has timed out: %s', cmd)
          logging.error('Sending SIGTERM to PID=%s', task.pid)
          os.kill(task.pid, signal.SIGTERM)
          break  # note: this is a hard timeout, we don't read() again
      else:
        inactive = 0
        for fd in rlist:
          if fd is task.stdout:
            stdoutput.append(fd.read())
          elif fd is task.stderr:
            stderror.append(fd.read())

      returncode = task.poll()

    # if the process was just killed, wait for waitfor seconds.
    if inactive >= timeout and waitfor > 0:
      time.sleep(waitfor)
    # attempt to obtain returncode one last chance
    returncode = task.poll()
    stdoutput = ''.join(stdoutput)
    stderror = ''.join(stderror)
    return (stdoutput, stderror, task.returncode)


def RunProcess(*args, **kwargs):
  if kwargs.get('background'):
    raise GmacpyutilException('Use RunProcessInBackground() instead.')
  # We're collecting the return value and re-returning it to ensure it's always
  # a tuple
  # pylint: disable=unpacking-non-sequence
  out, err, rc = _RunProcess(*args, **kwargs)
  # pylint: enable=unpacking-non-sequence
  return (out, err, rc)


def RunProcessInBackground(*args, **kwargs):
  kwargs['background'] = True
  return _RunProcess(*args, **kwargs)


def GetConsoleUser():
  """Returns current console user."""
  stat_info = os.stat('/dev/console')
  console_user = pwd.getpwuid(stat_info.st_uid)[0]
  return console_user




def GetAirportInfo(include_nearby_networks=False):
  """Returns information about current AirPort connection.

  Args:
    include_nearby_networks: bool, if True a nearby_networks key will be in
      the returned dict with a list of detected SSIDs nearby.

  Returns:
    dict: key value pairs from CWInterface data. If an error occurs or there is
      no Wi-Fi interface: the dict will be empty.
  """
  airport_info = {}
  try:
    objc.loadBundle('CoreWLAN', globals(),
                    bundle_path='/System/Library/Frameworks/CoreWLAN.framework')
  except ImportError:
    logging.error('Could not load CoreWLAN framework.')
    return airport_info

  cw_interface_state = {0: u'Inactive',
                        1: u'Scanning',
                        2: u'Authenticating',
                        3: u'Associating',
                        4: u'Running'}

  cw_security = {-1: u'Unknown',
                 0: u'None',
                 1: u'WEP',
                 2: u'WPA Personal',
                 3: u'WPA Personal Mixed',
                 4: u'WPA2 Personal',
                 6: u'Dynamic WEP',
                 7: u'WPA Enterprise',
                 8: u'WPA Enterprise Mixed',
                 9: u'WPA2 Enterprise'}

  cw_phy_mode = {0: u'None',
                 1: u'802.11a',
                 2: u'802.11b',
                 3: u'802.11g',
                 4: u'802.11n'}

  cw_channel_band = {0: u'Unknown',
                     1: u'2 GHz',
                     2: u'5 GHz'}

  iface = CWInterface.interface()  # pylint: disable=undefined-variable
  if not iface:
    return airport_info

  airport_info['name'] = iface.interfaceName()
  airport_info['hw_address'] = iface.hardwareAddress()
  airport_info['service_active'] = bool(iface.serviceActive())
  airport_info['country_code'] = iface.countryCode()
  airport_info['power'] = bool(iface.powerOn())
  airport_info['SSID'] = iface.ssid()
  airport_info['BSSID'] = iface.bssid()
  airport_info['noise_measurement'] = iface.noiseMeasurement()
  airport_info['phy_mode'] = iface.activePHYMode()
  airport_info['phy_mode_name'] = cw_phy_mode[iface.activePHYMode()]
  airport_info['rssi'] = iface.rssiValue()
  airport_info['state'] = iface.interfaceState()
  airport_info['state_name'] = cw_interface_state[iface.interfaceState()]
  airport_info['transmit_power'] = iface.transmitPower()
  airport_info['transmit_rate'] = iface.transmitRate()

  # Get channel information
  cw_channel = iface.wlanChannel()
  if cw_channel:
    airport_info['channel_number'] = cw_channel.channelNumber()
    airport_info['channel_band'] = cw_channel_band[cw_channel.channelBand()]

  # Get security information
  # If the security setting is unknown iface.security() returns NSIntegerMax
  # which is a very large number and annoying to test for in calling scripts.
  # Change any value larger than 100 (the enum currently ends at 10) to -1.
  security = iface.security()
  if security > 100:
    security = -1
  airport_info['security'] = security
  airport_info['security_name'] = cw_security[security]

  # Get nearby network information, if requested
  if include_nearby_networks:
    nearby_networks = []
    try:
      for nw in iface.scanForNetworksWithName_error_(None, None):
        ssid = nw.ssid()
        if ssid not in nearby_networks:
          nearby_networks.append(ssid)
    except TypeError:
      pass
    airport_info['nearby_networks'] = nearby_networks

  return airport_info


def GetPowerState():
  """Returns information about the current power state.

  This method is used to determine the machine's current power source,
  battery life percentage and time remaining. Intended for use with power
  assertions to ensure we're creating them at an opportune time. This is done
  by using the command 'pmset -g ps' which returns something like:

  Currently drawing from 'Battery Power'
   -InternalBattery-0 100%; discharging; 3:46 remaining

  or

  Currently drawing from 'AC Power'
   -InternalBattery-0 100%; charged; 0:00 remaining

  or (Mac Pro desktop):

  Currently drawing from 'AC Power'

  Returns:
    power_info: dict, information about the power state:
        {'ac_power': bool, (True if on AC power)
         'battery_percent': int, (percentage of battery life left)
         'battery_state': string (unknown, charging, discharging, or charged),
         'minutes_remaining': int (time left until fully charged or discharged)}
        Note: If regular expression matching does not identify power_info
        values, they will be defaulted to '-1'.

  Raises:
    GmacpyutilException: command failed to execute.
  """
  power_info = {}
  power_info['ac_power'] = '-1'
  power_info['battery_percent'] = '-1'
  power_info['battery_state'] = '-1'
  power_info['minutes_remaining'] = '-1'

  cmd = ['/usr/bin/pmset', '-g', 'ps']
  # pylint: disable=unpacking-non-sequence
  stdout, stderr, returncode = RunProcess(cmd)
  # pylint: enable=unpacking-non-sequence

  lines = stdout.splitlines()
  # ["Currently drawing from 'AC Power'",
  # '-InternalBattery-0\t100%; charged; 0:00 remaining']

  if returncode or not lines:
    raise GmacpyutilException(
        'pmset error (exit %d): %s' % (returncode, stderr))

  power_source = re.match(
      r'Currently drawing from \'(?P<power_source>\w+)', lines[0])

  if power_source:
    if power_source.group('power_source') == 'AC':
      power_info['ac_power'] = True

    if power_source.group('power_source') == 'Battery':
      power_info['ac_power'] = False

  if len(lines) > 1:  # sanity check for machine without batteries
    battery_info = re.match(
        r'.*\t'
        r'(?P<percent>\d+)%; '
        r'(?P<state>\w+); '
        r'(?P<hours>\d+):(?P<mins>\d+) remaining', lines[1])
    if battery_info:  # ensure named parameters matched
      power_info['battery_percent'] = int(battery_info.group('percent'))
      power_info['battery_state'] = battery_info.group('state')
      power_info['minutes_remaining'] = (
          60 * int(
              battery_info.group('hours')) + int(battery_info.group('mins')))
  return power_info


def ConfigureIOKit():
  """Sets up IOKit.

  We use ctypes to call functions in shared libraries to create, access and
  manipulate C data types in Python. For more information about ctypes, see:

  http://python.net/crew/theller/ctypes/
  http://code.rancidbacon.com/LearningAboutMacOSXNativePythonProgramming

  Returns:
    io_lib: IOKit library
  """
  io_lib = ctypes.cdll.LoadLibrary(
      '/System/Library/Frameworks/IOKit.framework/IOKit')
  io_lib.IOPMAssertionCreateWithName.argtypes = [
      ctypes.c_void_p,
      ctypes.c_uint32,
      ctypes.c_void_p,
      ctypes.POINTER(ctypes.c_uint32)]
  io_lib.IOPMAssertionRelease.argtypes = [ctypes.c_uint32]
  return io_lib


def StrToCFString(string):
  """Creates a CFString from a Python string.

  Inspired by Michael Lynn's power management wrapper:
  https://github.com/pudquick/pypmset/blob/master/pypmset.py

  Args:
    string: str, a regular Python string
  Returns:
    CFStringRef for CreatePowerAssertion()
  Raises:
    MissingImportsError: if CFStringCreateWithCString is missing
  """
  if CFStringCreateWithCString and kCFStringEncodingASCII:
    return objc.pyobjc_id(CFStringCreateWithCString(
        None, string, kCFStringEncodingASCII).nsstring())
  else:
    raise MissingImportsError(
        'CFStringCreateWithCString or kCFStringEncodingASCII '
        'not imported successfully.')


def CreatePowerAssertion(io_lib, assertion_type,
                         assertion_level, assertion_reason):
  """Creates a power assertion.

  IOPMAssertionCreate allows a process to assert a 'power assertion' to
  prevent display or system sleep while the assertion is active.

  The command-line equivalent for power assertions is '/usr/bin/pmset'.
  NB: it is not possible to create an assertion which prevents a forced
  system sleep, such as a lid close, low battery sleep, thermal sleep, etc.

  For more information on IOPMLib calls, see Apple's IOPMLib.h Reference:
  https://developer.apple.com/library/mac/#documentation/IOKit
      /Reference/IOPMLib_header_reference

  Args:
    io_lib: IOKit library from ConfigureIOKit()
    assertion_type: str, IOPMAssertionType:
        PreventUserIdleSystemSleep
        PreventUserIdleDisplaySleep
        PreventSystemSleep
        NoIdleSleepAssertion - preferred assertion, enforces screen lock
        NoDisplaySleepAssertion
    assertion_level: int, 0-255
    assertion_reason: str, reason for assertion, which will be displayed to the
        user when 'pmset -g assertions' is invoked

  Returns:
    assertion_error: 0 if successful, stderr otherwise
    assertion_id: c_uint, assertion identification number
  """
  assertion_id = ctypes.c_uint32(0)
  assertion_type = StrToCFString(assertion_type)
  assertion_reason = StrToCFString(assertion_reason)
  assertion_error = io_lib.IOPMAssertionCreateWithName(
      assertion_type,
      assertion_level,
      assertion_reason,
      ctypes.byref(assertion_id))
  return assertion_error, assertion_id


def ReleasePowerAssertion(io_lib, assertion_id):
  """Releases a power assertion.

  Assertions are released with IOPMAssertionRelease, however if they are not,
  assertions are automatically released when the process exits, dies or
  crashes, i.e. a crashed process will not prevent idle sleep indefinitely.

  Args:
    io_lib: IOKit library from ConfigureIOKit()
    assertion_id: c_uint, assertion identification number from
        CreatePowerAssertion()

  Returns:
    0 if successful, stderr otherwise.
  """
  try:
    return io_lib.IOPMAssertionRelease(assertion_id)
  except AttributeError:
    return 'IOKit library returned an error.'


@contextlib.contextmanager
def NoIdleAssertion(reason):
  """Context manager for creating and releasing a NoIdleAssertion.

  https://docs.python.org/2/library/contextlib.html#contextlib.contextmanager

  Usage:
  with NoIdleAssertion():
    # Some stuff

  Args:
    reason: string, tag for the power assertion
  Yields:
    None
  """
  assertion_type = 'NoIdleSleepAssertion'
  io_lib = ConfigureIOKit()
  returncode, assertion_id = CreatePowerAssertion(
      io_lib, assertion_type, 255, reason)
  if returncode:
    logging.error('Could not create assertion: %s', returncode)
  else:
    logging.debug('Created %s', assertion_type)

  try:
    yield
  finally:
    returncode = ReleasePowerAssertion(io_lib, assertion_id)
    if returncode:
      logging.error('Could not release assertion: %s', returncode)
    else:
      logging.debug('Released %s', assertion_type)


def GetPlist(plist):
  """Returns a dictionary from a given plist.

  Args:
    plist: plist to operate on
  Returns:
    Contents of the plist as a dict-like object.
  Raises:
    MissingImportsError: if NSDictionary is missing
  """
  if NSDictionary:
    return NSDictionary.dictionaryWithContentsOfFile_(plist)
  else:
    raise MissingImportsError('NSDictionary not imported successfully.')


def GetPlistKey(plist, key):
  """Returns the value for a given key in a plist.

  Args:
    plist: plist to operate on
    key: key to target
  Returns:
    The key value, or None on error or if the key is not present.
  """
  mach_info = GetPlist(plist)
  if mach_info:
    if key in mach_info:
      return mach_info[key]
  else:
    return None


def MachineInfoForKey(key):
  """Returns the value for a given key in the machineinfo plist.

  Args:
    key: key to target
  Returns:
    The key value, or None on error or if the key is not present.
  """
  return GetPlistKey(MACHINEINFO, key)


def ImageInfoForKey(key):
  """Returns the value for a given key in the imageinfo plist.

  Args:
    key: key to target
  Returns:
    The key value, or None on error or if the key is not present.
  """
  return GetPlistKey(IMAGEINFO, key)


def SetPlistKey(plist, key, value):
  """Sets the value for a given key in a plist.

  Args:
    plist: plist to operate on
    key: key to change
    value: value to set
  Returns:
    boolean: success
  Raises:
    MissingImportsError: if NSMutableDictionary is missing
  """
  if NSMutableDictionary:
    mach_info = NSMutableDictionary.dictionaryWithContentsOfFile_(plist)
    if not mach_info:
      mach_info = NSMutableDictionary.alloc().init()
    mach_info[key] = value
    return mach_info.writeToFile_atomically_(plist, True)
  else:
    raise MissingImportsError('NSMutableDictionary not imported successfully.')


def SetMachineInfoForKey(key, value):
  """Sets the value for a given key in the machineinfo plist."""
  return SetPlistKey(MACHINEINFO, key, value)


def SetImageInfoForKey(key, value):
  """Sets the value for a given key in the imageinfo plist."""
  return SetPlistKey(IMAGEINFO, key, value)


def Facts():
  """All facts for the current machine.

  Returns:
    A dictionary of all facts, with values as strings.
  Raises:
    GmacpyutilException: command failed to execute.
  """
  cmd = ['/usr/bin/puppet', 'config', '--config', '/etc/puppet/puppet.conf',
         'print', 'factpath']
  # pylint: disable=unpacking-non-sequence
  (stdout, stderr, returncode) = RunProcess(cmd)
  if returncode:
    raise GmacpyutilException('Puppetd Error: %s' % stderr)
  factpath = stdout.strip()  # pylint: disable=maybe-no-member
  all_facts = {}
  cmd = ['/usr/bin/facter', '-p']
  env = {'RUBYLIB': factpath}
  (stdout, stderr, returncode) = RunProcess(cmd, env=env)
  # pylint: enable=unpacking-non-sequence
  if returncode:
    raise GmacpyutilException('Facter Error: %s' % stderr)
  for line in stdout.split('\n'):  # pylint: disable=maybe-no-member
    fact_value = [i.strip() for i in line.split('=>')]
    if len(fact_value) != 2:
      continue
    fact = fact_value[0]
    value = str(fact_value[1])
    all_facts[fact] = value
  return all_facts


def FactValue(fact):
  """Retrieves a given facter value.

  With the current version of facter we need to retrieve all facts so that
  facts that are dependent upon other facts are correctly retrieved. This is
  unfortunately slow, but the best we can do at the moment.

  Args:
      fact: The fact to retrieve the value for.
  Returns:
      The value of the specified fact or None if non-existent.
  """
  facts = Facts()
  if fact in facts:
    return facts[fact]
  return None




def GetOSVersion():
  """Retrieve the current OS version from machine.

  Returns:
    os_version: string, like '10.9.5' or '10.10'.
  Raises:
    GmacpyutilException: command failed to execute.
    GmacpyutilException: os_version does not match expected formatting.
  """
  cmd = ['sw_vers', '-productVersion']
  out, err, rc = RunProcess(cmd)  # pylint: disable=unpacking-non-sequence
  if rc != 0:
    raise GmacpyutilException('Unable to retrieve OS version - Error: %s.', err)
  os_version = out.strip()
  match = re.match(r'([0-9]+\.)', os_version)
  if not match:
    raise GmacpyutilException('Unexpected OS version returned.')
  return os_version


def GetMajorOSVersion():
  """Retrieve the current Major OS version from machine.

  Returns:
    major_os_version: string, like '10.9' or '10.10',
      or False if OS version cannot be determined.
  """
  try:
    os_version = GetOSVersion()
  except GmacpyutilException:
    return False
  version_list = os_version.split('.')
  major_os_version = '.'.join(version_list[:2])
  return major_os_version


def GetTrack():
  """Retrieve the currently set track.

  Returns:
    track: As defined in Track key, stable if undefined, or unstable
        if Major OS version does not match currently supported version.
  """
  major_os_version = GetMajorOSVersion()
  if not major_os_version:
    track = 'stable'
  else:
    track = MachineInfoForKey('Track')
    if distutils_version.LooseVersion(
        major_os_version) > distutils_version.LooseVersion(MAX_SUPPORTED_VERS):
      track = 'unstable'
    elif track not in ['stable', 'testing', 'unstable']:
      track = 'stable'
  return track


def IsTextConsole():
  """Checks if console is test only or GUI.

  Returns:
    True if the console is text-only, False if GUI is available
  """
  try:
    # see TN2083
    security_lib = ctypes.cdll.LoadLibrary(
        '/System/Library/Frameworks/Security.framework/Security')

    # Security.Framework/Headers/AuthSession.h
    session = -1
    session_id = ctypes.c_int(0)
    attributes = ctypes.c_int(0)

    ret = security_lib.SessionGetInfo(
        session, ctypes.byref(session_id), ctypes.byref(attributes))

    if ret != 0:
      return True

    return not attributes.value & SESSIONHASGRAPHICACCESS
  except OSError:
    return True


def InteractiveConsole():
  """Launch an interactive python shell."""
  # pylint: disable=g-import-not-at-top,unused-variable
  import code
  import readline
  # pylint: enable=g-import-not-at-top,unused-variable
  console = code.InteractiveConsole(dict(globals(), **locals()))
  console.interact('Interactive shell for %s' %
                   os.path.basename(sys.argv[0]))
