"""Module for controlling a Wi-Fi interface using CoreWLAN.

https://developer.apple.com/library/mac/documentation/Networking/Reference/CoreWLANFrameworkRef/_index.html
"""

import logging
import os
import time
from . import cocoadialog
from . import defaults

# pylint: disable=g-import-not-at-top
try:
  import objc
  objc.loadBundle('CoreWLAN', globals(),
                  bundle_path='/System/Library/Frameworks/CoreWLAN.framework')

  def R(selector, error_arg_num):
    """Register metadata for CWInterface selectors that return NSError values.

    This tells the Objective-C bridge that the requested selector would normally
    take a reference to an NSError as an argument and should instead return any
    errors alongside the normal return values. This causes the method to return
    a tuple of [Return value, Error or None].

    Args:
      selector: The selector as it's known in Objective-C
      error_arg_num: Which numbered argument would the NSError be passed in
    """
    objc.registerMetaDataForSelector(
        'CWInterface', selector,
        {'arguments': {error_arg_num + 1: {'type_modifier': 'o'}}})
  R('scanForNetworksWithName:error:', 2)
  R('setPower:error:', 2)
  R('associateToNetwork:password:forceBSSID:remember:error:', 5)
  del R
except ImportError:
  if os.uname()[0] == 'Linux':
    logging.debug('Skipping Mac imports for later mock purposes.')
  else:
    raise
# pylint: enable=g-import-not-at-top

GUEST_NETWORKS = defaults.GUEST_NETWORKS
GUEST_PSKS = defaults.GUEST_PSKS


def GetDefaultInterface():
  """Returns the default Wi-Fi interface."""
  return CWInterface.interface()  # pylint:disable=undefined-variable


def GetInterfacePower(interface=None):
  """Determines if the interface is powered on.

  Args:
    interface: the CWInterface to operate on.

  Returns:
    bool: True if interface is on, False otherwise
  """
  if not interface:
    interface = GetDefaultInterface()
    if not interface:
      return False

  return interface.power()


def SetInterfacePower(state, interface=None):
  """Sets an interfaces power state.

  Args:
    state: bool, True is on, False is off.
    interface: the CWInterface to operate on.

  Returns:
    bool: whether setting the state was successful.
  """
  if not interface:
    interface = GetDefaultInterface()
    if not interface:
      return False

  if bool(interface.powerOn()) != state:
    _, error = interface.setPower_error_(state, None)
    if error:
      logging.debug('Failed to set interface power. Error: %s', error)
      return False
    if state:
      while interface.interfaceState() == 0:
        # After powering on the interface, it takes a while before it's ready.
        logging.debug('Waiting for interface to wake up')
        time.sleep(5)
      return True


def Disassociate(interface=None):
  """Disassociate from the current network.

  Args:
    interface: the CWInterface to operate on.
  """
  if not interface:
    interface = GetDefaultInterface()
    if not interface:
      return

  interface.disassociate()


def AssociateToNetwork(network, password=None, remember=False, interface=None):
  """Associate to a given CWNetwork.

  Blocks until the association is complete.

  Args:
    network: the CWNetwork to connect to.
    password: optional, a password to use for connecting.
    remember: whether to remember the network.
    interface: the CWInterface to operate on.

  Returns:
    bool: whether associating was successful or not.
  """
  if not interface:
    interface = GetDefaultInterface()
    if not interface:
      return False

  SetInterfacePower(True, interface=interface)

  _, error = interface.associateToNetwork_password_forceBSSID_remember_error_(
      network, password, False, remember, None)

  if error:
    logging.debug('Failed to connect. Error: %s', error)
    return False

  # Wait until connection is actually established
  while interface.ssid() != network.ssid():
    time.sleep(5)

  return True


def AssociateToSSID(ssid, password=None, remember=False, interface=None):
  """Associate to a given SSID.

  Blocks until the association is complete.

  If the first attempt to connect fails, a second attempt will be made before
  returning as CoreWLAN often mysteriously fails on the first attempt.

  Args:
    ssid: the SSID of the network to connect to.
    password: optional, a password to use for connecting.
    remember: whether to remember the network.
    interface: the CWInterface to operate on.

  Returns:
    bool: whether associating was successful or not.
  """
  if not interface:
    interface = GetDefaultInterface()
    if not interface:
      return False

  SetInterfacePower(True, interface=interface)

  networks = ScanForNetworks(ssid, interface=interface)
  if not networks:
    return False
  network = networks[ssid]

  return AssociateToNetwork(network, password=password,
                            interface=interface, remember=remember)


def ScanForNetworks(ssid, interface=None):
  """Scan for networks nearby.

  Blocks until the association is complete.

  The call to scanForNetworksWithName_error_ will return a list of networks
  including many duplicates, so this function uses the rssiValue to pick
  the CWNetwork object with the strongest signal for a given SSID. The RSSI
  value goes from 0 to -100 with 0 being the best signal.

  Args:
    ssid: optional, an SSID to search for.
    interface: the CWInterface to operate on.

  Returns:
    dict: CWNetwork objects keyed by the SSIDs.
  """
  if not interface:
    interface = GetDefaultInterface()
    if not interface:
      return None

  SetInterfacePower(True, interface=interface)

  nw = {}

  networks, error = interface.scanForNetworksWithName_error_(ssid, None)

  if not networks:
    logging.debug('Failed to get networks. Error: %s', error)
    return nw

  for network in networks:
    network_ssid = network.ssid()
    if network_ssid not in nw:
      nw[network_ssid] = network
    else:
      if network.rssiValue() > nw[network_ssid].rssiValue():
        nw[network_ssid] = network

  return nw


def _FindGuestNetwork(guest_networks, available_networks):
  """Returns the first guest network found in available networks.

  Args:
    guest_networks: list of string SSIDs used as guest networks.
    available_networks: dict of networks to look through.
  Returns:
    SSID string of network found or None.
  """
  for net in guest_networks:
    if net in available_networks:
      return net


def ConnectToNetwork(withcancelbutton):
  """Attempt to connect to a network.

  If one of |GUEST_NETWORKS| is available nearby, will connect to that.
  Otherwise, will offer a list of networks to connect to.
  Args:
    withcancelbutton: True to add a Cancel button to the Wi-Fi picker dialog.
  Returns:
    True if network connected, False if not or user canceled.
  """
  logging.info('Searching for network to connect to, please wait')
  networks = ScanForNetworks(None)
  logging.info('Found these networks: %s', networks.keys())

  guest_net = _FindGuestNetwork(GUEST_NETWORKS, networks)
  if guest_net:
    network = guest_net
  else:
    action = 'Refresh'
    while action != 'OK':
      dialog = cocoadialog.DropDown()
      dialog.SetTitle('Select Wireless Network')
      items = networks.keys()
      items.sort()
      dialog.SetItems(items)
      dialog.SetButton1('OK')
      dialog.SetButton2('Refresh')
      if withcancelbutton:
        dialog.SetButton3('Cancel')
      action, network, _ = dialog.Show().split('\n')
      if action == 'Refresh':
        networks = ScanForNetworks(None)
      elif action == 'Cancel':
        return False
  logging.info('Connecting to %s', network)

  # Does network need a password?
  password = None
  if networks[network].securityMode():
    if network in GUEST_NETWORKS:
      for psk in GUEST_PSKS:
        result = AssociateToNetwork(networks[network], password=psk)
        logging.info('Attempted to connect to %s. Success: %s', network, result)
        if result:
          return True
      logging.error('Password protected guest network detected, but known '
                    'passwords are not accepted.')
    dialog = cocoadialog.Standard_InputBox()
    dialog.SetPasswordBox()
    dialog.SetTitle('Password Required')
    dialog.SetInformativeText('The requested network (%s) requires a '
                              'password:' % network)
    (_, password, _) = dialog.Show().split('\n')
  result = AssociateToNetwork(networks[network], password=password)
  logging.info('Attempted to connect to %s. Success: %s', network, result)
  return result
