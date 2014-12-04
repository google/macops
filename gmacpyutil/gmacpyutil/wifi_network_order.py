"""Manage preferred wireless network order."""

import os

from . import gmacpyutil
from . import defaults
from . import systemconfig

_NETWORK_SETUP = '/usr/sbin/networksetup'
_SYSTEM_PROFILER = '/usr/sbin/system_profiler'
_SECURITY_TYPES = ('OPEN', 'WPA', 'WPAE', 'WPA2', 'WPA2E', 'WEP', '8021XWEP')
_SSIDS = defaults.SSIDS


class Error(Exception):
  """Base exception for module."""


class BadSecurityTypeError(Error):
  """Security type specified is not allowed."""


class PreferenceRemovalError(Error):
  """Unable to remove preferred wireless network."""


class PreferenceAdditionError(Error):
  """Unable to add preferred wireless network."""


class NotRunningAsRootError(Error):
  """Not running as root."""


def GetWifiInterface():
  """Gets the first Wi-Fi interface name.

  Returns:
    interface: str, the first Wi-Fi interface name (e.g. en0) or None if no
      interface exists.
  """
  interfaces = systemconfig.GetNetworkInterfaces()
  for interface in interfaces:
    if interface['type'] == 'IEEE80211':
      return interface['dev']
  return None


def SplitNetworkNameSecurity(network):
  """Splits a network name from it's security type.

  Splits strings of the form NetworkName$NetworkSecurity into a tuple of
  NetworkName, NetworkSecurity. Verifies that security matches one of the
  allowed options in _SECURITY_TYPES; if the security type is missing or is not
  in the allowed types, it is assumed to be OPEN.

  Args:
    network: str, the network name to split

  Returns:
    name: str, the network name.
    security: str, the network security type.
  """
  try:
    name, security = network.split('$')
    security = security.upper()
    if security not in _SECURITY_TYPES:
      security = 'OPEN'
  except ValueError:
    name = network
    security = 'OPEN'
  return name, security


def GetPreferredNetworks():
  """Returns a list of preferred wireless networks.

  The list is created by getting the user's preferred networks from the
  machineinfo file and appending this to the _SSIDS defined above

  Returns:
    networks: The list of networks
  """
  networks = []
  plistdata = gmacpyutil.MachineInfoForKey('PreferredNetworks')
  if plistdata:
    # Backwards compatible with single string PreferredNetworks
    if isinstance(plistdata, basestring):
      networks = [plistdata]
    else:
      networks = list(plistdata)

  networks = _SSIDS + networks
  return networks


def GetSSIDS():
  """Returns a list of internal SSIDs.

  Returns:
    list of strings containing network ssids.
  """
  return _SSIDS




def RemovePreferredNetwork(interface, ssid, sudo_password=None):
  """Removes |ssid| from the list of preferred networks on |interface|.

  If Python is not running as root and sudo_password is not supplied an
  authorization dialog will appear.

  Args:
    interface: the interface to remove the preference from.
    ssid: the SSID of the network.
    sudo_password: optional password to get sudo access.

  Raises:
    PreferenceRemovalError: preference could not be removed. Exception message
      is the stderr.
  """
  args = (_NETWORK_SETUP, '-removepreferredwirelessnetwork', interface, ssid)
  _, stderr, rc = gmacpyutil.RunProcess(args, sudo=bool(sudo_password),
                                        sudo_password=sudo_password)
  if rc:
    raise PreferenceRemovalError(stderr)


def AddPreferredNetwork(interface, ssid, security, index=-1, password=None,
                        sudo_password=None):
  """Adds |ssid| to the list of preferred networks on |interface|.

  If Python is not running as root and sudo_password is not supplied an
  authorization dialog will appear.

  Args:
    interface: the interface to add the preference to.
    ssid: the SSID of the network.
    security: the security type of the network, must be in _SECURITY_TYPES.
    index: optional, the index in the network list to store the network.
      Defaults to -1, which is the end of the list.
    password: an optional password for the network to store in the keychain.
    sudo_password: optional password to get sudo access.

  Raises:
    PreferenceAdditionError: preference could not be added. Exception message
      is the stderr.
    BadSecurityTypeError: specified security type is not valid.
  """
  security = security.upper()
  if security not in _SECURITY_TYPES:
    raise BadSecurityTypeError

  args = [_NETWORK_SETUP, '-addpreferredwirelessnetworkatindex', interface,
          ssid, str(index), security]
  if password:
    args.append(password)

  _, stderr, rc = gmacpyutil.RunProcess(args, sudo=bool(sudo_password),
                                        sudo_password=sudo_password)
  if rc:
    raise PreferenceAdditionError(stderr)


def ResetPreferredNetworks(interface, networks, sudo_password=None):
  """Adds |networks| as preferred networks to |interface| from position 0.

  Each network should be specified as the SSID and associated
  encryption type, seperated by a $ sign (which is not legal in SSIDs).
  Allowed encryption types are specified in _SECURITY_TYPES.

  The network list is inserted at position 0, so any existing networks which
  are not specified by |networks| will be moved below. As the passed in network
  list is assumed to be in order, the list is reversed before beginning

  If no interface is passed the method returns immediately.

  Note: Because this could potentially cause _lots_ of password dialogs, a sudo
  password must be supplied or the Python process must be running as root.

  Args:
    interface: the interface ID (e.g. en0).
    networks: the list of networks.
    sudo_password: password to get sudo access. required if not running as root.

  Raises:
    NotRunningAsRootError: not running as root and no sudo_password supplied.
  """
  if not interface:
    return

  if os.geteuid() and not sudo_password:
    raise NotRunningAsRootError('ResetPreferredNetworks requires root access')

  for nw in reversed(networks):
    nw_name, nw_security = SplitNetworkNameSecurity(nw)
    RemovePreferredNetwork(interface, nw_name, sudo_password=sudo_password)
    AddPreferredNetwork(interface, nw_name, nw_security, index=0,
                        sudo_password=sudo_password)
