"""Various system configuration related functions.

Largely copied from
http://code.google.com/p/pymacadmin/source/browse/lib/PyMacAdmin/SCUtilities/SCPreferences.py
and
http://code.google.com/p/pymacadmin/source/browse/examples/crankd/socks-proxy/ProxyManager.py
"""

import logging
import os
import struct

# pylint: disable=g-import-not-at-top
from . import gmacpyutil
from . import defaults
try:
  from Foundation import NSMutableDictionary
  from Foundation import NSString
  from SystemConfiguration import SCDynamicStoreAddValue
  from SystemConfiguration import SCDynamicStoreCopyValue
  from SystemConfiguration import SCDynamicStoreCreate
  from SystemConfiguration import SCDynamicStoreSetValue
  from SystemConfiguration import SCPreferencesApplyChanges
  from SystemConfiguration import SCPreferencesCommitChanges
  from SystemConfiguration import SCPreferencesCreate
  from SystemConfiguration import SCPreferencesPathGetValue
  from SystemConfiguration import SCPreferencesPathSetValue
except ImportError:
  if os.uname()[0] == 'Linux':
    logging.debug('Skipping Mac imports for later mock purposes.')
    # pylint: disable=g-bad-name
    NSMutableDictionary = NSString = None
    SCDynamicStoreAddValue = SCDynamicStoreCopyValue = None
    SCDynamicStoreCreate = SCDynamicStoreSetValue = None
    SCPreferencesApplyChanges = SCPreferencesCommitChanges = None
    SCPreferencesCreate = None
    SCPreferencesPathGetValue = SCPreferencesPathSetValue = None
    # pylint: enable=g-bad-name
  else:
    raise
# pylint: enable=g-import-not-at-top


CORP_PROXY = defaults.CORP_PROXY
NI_PLIST = '/Library/Preferences/SystemConfiguration/NetworkInterfaces.plist'


class SysconfigError(Exception):
  """Module specific exception class."""


class SystemProfilerError(Exception):
  """Error retrieving results from system_profiler."""


class InterfaceError(Exception):
  """Error reading network interface data."""


class SCDynamicPreferences(object):
  """Utility Class for working with the SystemConfiguration Dynamic store."""
  store = None

  def __init__(self):
    super(SCDynamicPreferences, self).__init__()
    self.store = SCDynamicStoreCreate(None, 'gmacpyutil', None, None)

  def ReadProxySettings(self):
    """Read proxy setting from SCDynamicStore."""
    return SCDynamicStoreCopyValue(self.store, 'State:/Network/Global/Proxies')

  def SetProxy(self, enable=True, pac=CORP_PROXY):
    """Set proxy autoconfig."""

    proxies = NSMutableDictionary.dictionaryWithDictionary_(
        self.ReadProxySettings())
    logging.debug('initial proxy settings: %s', proxies)
    proxies['ProxyAutoConfigURLString'] = pac
    if enable:
      proxies['ProxyAutoConfigEnable'] = 1
    else:
      proxies['ProxyAutoConfigEnable'] = 0
    logging.debug('Setting ProxyAutoConfigURLString to %s and '
                  'ProxyAutoConfigEnable to %s', pac, enable)
    result = SCDynamicStoreSetValue(self.store,
                                    'State:/Network/Global/Proxies',
                                    proxies)
    logging.debug('final proxy settings: %s', self.ReadProxySettings())
    return result

  def SetCorpSetupKey(self, key, value):
    """Set key-value pair under the CORP_SETUP tree.

    Args:
      key: String, key to add
      value: string/integer if single value, dict if multiple values.

    Returns:
      Boolean, True if successful.

    Raises:
      SysconfigError: On failure (SCDynamicStore* does return False
      on failure, we don't get any better errors).
    """
    long_key = '%s%s' % (CORP_SETUP, key)
    if SCDynamicStoreCopyValue(self.store, long_key) is not None:
      key_set = SCDynamicStoreSetValue(self.store, long_key, value)
      if key_set:
        logging.debug('Setting %s to value %s', long_key, value)
        return True
      else:
        raise SysconfigError('Failed setting %s with value %s' % (
            long_key, value))

    else:
      add = SCDynamicStoreAddValue(self.store, long_key, value)
      if add:
        logging.debug('Adding %s with value %s', long_key, value)
        return True
      else:
        raise SysconfigError('Failed adding %s with value %s' % (
            long_key, value))

  def GetCorpSetupKey(self, key):
    """Get key-value pair from the CORP_SETUP tree.

    Args:
      key: String, key to look up

    Returns:
      value: String if single value, dictionary if plist.

    Raises:
      SysconfigError: On failure (see above).
    """
    long_key = '%s%s' % (CORP_SETUP, key)
    key = SCDynamicStoreCopyValue(self.store, long_key)
    if key is not None:
      return key
    else:
      logging.debug('Failed retrieving %s', long_key)
      raise SysconfigError('Failed retrieving %s' % long_key)


class SCPreferences(object):
  """Utility class for working with the SystemConfiguration framework."""
  session = None

  def __init__(self):
    super(SCPreferences, self).__init__()
    self.session = SCPreferencesCreate(None, 'gmacpyutil', None)

  def Save(self):
    """Commits changes to permanent store, applies to running config."""
    if not self.session:
      return
    if not SCPreferencesCommitChanges(self.session):
      raise SysconfigError('Unable to save SystemConfiguration changes.')
    if not SCPreferencesApplyChanges(self.session):
      raise SysconfigError('Unable to apply SystemConfiguration changes.')

  def GetPathValue(self, path):
    """Gets the preferences path value for a given path."""
    base = os.path.basename(path)
    tree = os.path.dirname(path)
    settings = SCPreferencesPathGetValue(self.session, tree)
    if not settings:
      # SCPreferencesPathGetValue returns a dict or None if the path doesn't
      # exist. Just pass along None in the second case.
      return None
    if base is '':
      # If base is '', the path is '/' so we just return the whole tree
      return settings
    if base in settings:
      return settings[base]
    else:
      return None

  def SetPathValue(self, path, value):
    """Sets the path value for a given path."""
    base = os.path.basename(path)
    if not base:
      raise SysconfigError('Updating %s not permitted.' % path)
    tree = os.path.dirname(path)
    settings = SCPreferencesPathGetValue(self.session, tree)
    if not settings:
      settings = NSMutableDictionary.alloc().init()
    settings[base] = value
    SCPreferencesPathSetValue(self.session, tree, settings)

  def SetProxy(self, enable=True, pac=CORP_PROXY):
    """Sets the proxy autoconfiguration URL and enables or disables it."""
    interfaces = self.GetPathValue(u'/NetworkServices')
    for interface in interfaces:
      # Some interfaces, (e.g. some 3G modem dummy interfaces) don't
      # always have a proxy key, so we simply ignore them.
      if 'Proxies' not in interfaces[interface]:
        continue
      if enable:
        interfaces[interface]['Proxies']['ProxyAutoConfigEnable'] = 1
        interfaces[interface]['Proxies']['ProxyAutoConfigURLString'] = pac
      else:
        interfaces[interface]['Proxies']['ProxyAutoConfigEnable'] = 0

    self.SetPathValue(u'/NetworkServices', interfaces)

  def GetComputerName(self):
    """Gets the current ComputerName."""
    return self.GetPathValue(u'/System/System/ComputerName')

  def GetLocalName(self):
    """Gets the current LocalName."""
    return self.GetPathValue(u'/System/Network/HostNames/LocalHostName')

  def GetHostName(self):
    """Gets the current HostName."""
    return self.GetPathValue(u'/System/System/HostName')

  def SetComputerName(self, computername):
    """Sets the Local name for the machine."""
    current_computername = self.GetPathValue(u'/System/System/ComputerName')
    if current_computername != computername:
      self.SetPathValue(u'/System/System/ComputerName', computername)

  def SetLocalName(self, localname):
    """Sets the Computer name for the machine."""
    current_localname = self.GetPathValue(
        u'/System/Network/HostNames/LocalHostName')
    if current_localname != localname:
      self.SetPathValue(u'/System/Network/HostNames/LocalHostName', localname)

  def SetHostName(self, hostname):
    """Sets the Hostname for the machine."""
    current_hostname = self.GetPathValue(u'/System/System/HostName')
    if current_hostname != hostname:
      self.SetPathValue(u'/System/System/HostName', hostname)


class SystemProfiler(object):
  """Utility Class for parsing system_profiler data."""
  _cache = {}

  def _GetSystemProfilerOutput(self, sp_type):
    logging.debug('Getting system_profiler output for %s', sp_type)
    argv = ['/usr/sbin/system_profiler', '-XML', sp_type]
    stdout, unused_stderr, returncode = gmacpyutil.RunProcess(argv)
    if returncode is not 0:
      raise SystemProfilerError('Could not run %s' % argv)
    else:
      return stdout

  def _GetSystemProfile(self, sp_type):
    # pylint: disable=global-statement
    if sp_type not in self._cache:
      logging.debug('%s not cached', sp_type)
      sp_xml = self._GetSystemProfilerOutput(sp_type)
      self._cache[sp_type] = NSString.stringWithString_(sp_xml).propertyList()
    return self._cache[sp_type]

  def GetMBSerialNumber(self):
    """Retrieves the Mainboard serial number.

    Returns:
      string of serial number
    """
    sp_type = 'SPHardwareDataType'
    for data in self._GetSystemProfile(sp_type):
      if data.get('_dataType', None) == sp_type:
        for item in data['_items']:
          if 'serial_number' in item:
            logging.debug('serial_number: %s', item['serial_number'])
            return item['serial_number']
    return None

  def GetMBModelNumber(self):
    """Retrieves the Mainboard machine model.

    Returns:
      string of model number
    """
    sp_type = 'SPHardwareDataType'
    for data in self._GetSystemProfile(sp_type):
      if data.get('_dataType', None) == sp_type:
        for item in data['_items']:
          if 'machine_model' in item:
            logging.debug('machine_model: %s', item['machine_model'])
            return item['machine_model']
    return None

  def GetHWUUID(self):
    """Retrieves the Hardware UUID.

    Returns:
      string of UUID
    """
    sp_type = 'SPHardwareDataType'
    for data in self._GetSystemProfile(sp_type):
      if data.get('_dataType', None) == sp_type:
        for item in data['_items']:
          if 'platform_UUID' in item:
            logging.debug('platform_UUID: %s', item['platform_UUID'])
            return item['platform_UUID']
    return None

  def GetDiskSerialNumber(self):
    """Retrieves the primary disk serial number.

    Returns:
      string of serial number

    Raises:
      SystemProfilerError: when disk0 is not found on SATA bus.
    """
    # the order is important so we prefer SATA then RAID finally PATA
    sp_types = ['SPSerialATADataType', 'SPHardwareRAIDDataType',
                'SPParallelATADataType']
    for sp_type in sp_types:
      for data in self._GetSystemProfile(sp_type):
        if data.get('_dataType', None) == sp_type:
          for controller in data['_items']:
            for device in controller.get('_items', []):
              if device.get('bsd_name', '').find('disk0') > -1:
                logging.debug('device_serial: %s', device['device_serial'])
                return device['device_serial']
    raise SystemProfilerError('Could not find disk0')


def GetMacAddresses():
  """Retrieves the MAC addresses of all *built-in* interfaces.

  Returns:
    List of: uppercase string of MAC address without ':'
  """
  mac_addresses = []
  for interface in GetDot1xInterfaces():
    cur_mac = interface['mac']
    if cur_mac:
      mac_addresses.append(cur_mac.replace(':', '').upper())
  return mac_addresses


def _GetMACFromData(data):
  """Unpacks and formats MAC address data.

  Args:
    data: buffer, usually an NSCFData object
  Returns:
    string containing the MAC address
  Raises:
    InterfaceError: if data can't be unpacked
  """
  try:
    unpacked = struct.unpack_from('BBBBBB', data)
  except struct.error as e:
    logging.error('Could not unpack MAC address data: %s', e)
    raise InterfaceError(e)
  return ':'.join(['{:02x}'.format(i) for i in unpacked])


def GetNetworkInterfaces():
  """Retrieves attributes of all network interfaces.

  Returns:
    Array of dict or empty array
  """
  interfaces = []
  ni_data = gmacpyutil.GetPlist(NI_PLIST)
  for cur_int in ni_data['Interfaces']:
    interface = {}
    interface['type'] = unicode(cur_int['SCNetworkInterfaceType'])
    interface['mac'] = _GetMACFromData(cur_int['IOMACAddress'])
    interface['name'] = unicode(
        cur_int['SCNetworkInterfaceInfo']['UserDefinedName'])
    interface['dev'] = unicode(cur_int['BSD Name'])
    interface['bus'] = unicode(cur_int['IOPathMatch'])
    interface['builtin'] = cur_int['IOBuiltin']
    interfaces.append(interface)
  return interfaces


def GetDot1xInterfaces():
  """Retrieves attributes of all dot1x compatible interfaces.

  Returns:
    Array of dict or empty array
  """
  interfaces = []
  for interface in GetNetworkInterfaces():
    if interface['type'] == 'IEEE80211' or interface['type'] == 'Ethernet':
      if (interface['builtin'] and
          'AppleThunderboltIPPort' not in interface['bus']):
        interfaces.append(interface)
  return interfaces


def ConfigureSystemProxy(proxy=CORP_PROXY, enable=True):
  """Sets the system proxy to the specified value."""
  scd_prefs = SCDynamicPreferences()
  if not scd_prefs.SetProxy(enable=enable, pac=proxy):
    logging.error('Could not change proxy settings.')


def GetLocalHostname():
  """Gets the .local hostname.

  Returns:
    string with local hostname, 'noname' if none is set.
  """
  session = SCPreferencesCreate(None, 'gmacpyutil', None)
  try:
    hostname = SCPreferencesPathGetValue(
        session,
        '/System/Network/HostNames/')['LocalHostName']
  except TypeError:
    # LocalHostName (scutil --get LocalHostName) is not set.
    hostname = None
  if hostname:
    return hostname
  else:
    return 'noname'


def GetLocalName():
  """Get the local name."""
  sc_prefs = SCPreferences()
  return sc_prefs.GetLocalName()


def GetComputerName():
  """Get the computer name."""
  sc_prefs = SCPreferences()
  return sc_prefs.GetComputerName()


def GetHostName():
  """Get the hostname."""
  sc_prefs = SCPreferences()
  return sc_prefs.GetHostName()


def ConfigureLocalName(localname):
  """Sets the local name to the specified value."""
  sc_prefs = SCPreferences()
  sc_prefs.SetLocalName(localname)
  sc_prefs.Save()


def ConfigureComputerName(computername):
  """Sets the computer name to the specified value."""
  sc_prefs = SCPreferences()
  sc_prefs.SetComputerName(computername)
  sc_prefs.Save()


def ConfigureHostName(hostname):
  """Sets the hostname to a specified value."""
  sc_prefs = SCPreferences()
  sc_prefs.SetHostName(hostname)
  sc_prefs.Save()
