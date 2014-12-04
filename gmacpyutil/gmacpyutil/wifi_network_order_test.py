"""Unit tests for wifi_network_order module."""


import mox
import stubout

from google.apputils import app
from google.apputils import basetest

import wifi_network_order


class WifiNetworkOrderModuleTest(mox.MoxTestBase):
  """Test wifi_network_order module-level functions."""

  def setUp(self):
    mox.MoxTestBase.setUp(self)
    self.stubs = stubout.StubOutForTesting()

  def tearDown(self):
    self.mox.UnsetStubs()
    self.stubs.UnsetAll()

  def testGetWifiInterfaceNoInterfaces(self):
    """Test GetWifiInterface with no Wi-Fi interfaces."""
    self.mox.StubOutWithMock(wifi_network_order.systemconfig,
                             'GetNetworkInterfaces')
    interfaces = ({'type': 'Ethernet', 'dev': 'en0'},
                  {'type': 'Bluetooth', 'dev': 'Bluetooth-Modem'})
    wifi_network_order.systemconfig.GetNetworkInterfaces().AndReturn(
        interfaces)
    self.mox.ReplayAll()
    self.assertEqual(None, wifi_network_order.GetWifiInterface())
    self.mox.VerifyAll()

  def testGetWifiInterfaceOneInterface(self):
    """Test GetWifiInterface with a single Wi-Fi interface."""
    self.mox.StubOutWithMock(wifi_network_order.systemconfig,
                             'GetNetworkInterfaces')
    interfaces = ({'type': 'Ethernet', 'dev': 'en0'},
                  {'type': 'Bluetooth', 'dev': 'Bluetooth-Modem'},
                  {'type': 'IEEE80211', 'dev': 'en1'})
    wifi_network_order.systemconfig.GetNetworkInterfaces().AndReturn(
        interfaces)
    self.mox.ReplayAll()
    self.assertEqual('en1', wifi_network_order.GetWifiInterface())
    self.mox.VerifyAll()

  def testSplitNetworkNameSecurityValid(self):
    """Test SplitNetworkNameSecurity, valid argument."""
    network = 'TestNetwork$WPA2E'
    name, security = wifi_network_order.SplitNetworkNameSecurity(network)
    self.assertEqual(name, 'TestNetwork')
    self.assertEqual(security, 'WPA2E')

  def testSplitNetworkNameSecurityMissingSecurity(self):
    """Test SplitNetworkNameSecurity, missing security type."""
    network = 'TestNetwork'
    name, security = wifi_network_order.SplitNetworkNameSecurity(network)
    self.assertEqual(name, 'TestNetwork')
    self.assertEqual(security, 'OPEN')

  def testSplitNetworkNameSecurityInvalidSecurity(self):
    """Test SplitNetworkNameSecurity, invalid security type."""
    network = 'TestNetwork$INVA'
    name, security = wifi_network_order.SplitNetworkNameSecurity(network)
    self.assertEqual(name, 'TestNetwork')
    self.assertEqual(security, 'OPEN')

  def testGetPreferredNetworksNoUserNetworks(self):
    """Test GetPreferredNetworks with no user defined networks."""
    self.mox.StubOutWithMock(wifi_network_order.gmacpyutil, 'MachineInfoForKey')
    wifi_network_order.gmacpyutil.MachineInfoForKey(
        'PreferredNetworks').AndReturn(None)
    self.mox.ReplayAll()
    self.assertEqual(wifi_network_order._SSIDS,
                     wifi_network_order.GetPreferredNetworks())
    self.mox.VerifyAll()

  def testGetPreferredNetworksTwoUserNetworksWithSecurity(self):
    """Test GetPreferredNetworks with two user networks with security."""
    user_networks = ['Network1$WPA2E', 'Network2$OPEN']
    expected_result = wifi_network_order._SSIDS + user_networks
    self.mox.StubOutWithMock(wifi_network_order.gmacpyutil, 'MachineInfoForKey')
    wifi_network_order.gmacpyutil.MachineInfoForKey(
        'PreferredNetworks').AndReturn(user_networks)
    self.mox.ReplayAll()
    self.assertEqual(expected_result, wifi_network_order.GetPreferredNetworks())
    self.mox.VerifyAll()

  def testGetPreferredNetworksOneUserNetworksWithoutSecurity(self):
    """Test GetPreferredNetworks with one user network without security."""
    user_network = 'Network1'
    expected_result = wifi_network_order._SSIDS + [user_network]
    self.mox.StubOutWithMock(wifi_network_order.gmacpyutil, 'MachineInfoForKey')
    wifi_network_order.gmacpyutil.MachineInfoForKey(
        'PreferredNetworks').AndReturn(user_network)
    self.mox.ReplayAll()
    self.assertEqual(expected_result, wifi_network_order.GetPreferredNetworks())
    self.mox.VerifyAll()

  def testRemovePreferredNetworkSuccess(self):
    """Test RemovePreferredNetwork with valid arguments."""
    interface = 'en0'
    ssid = 'GuestNetwork'
    args = (wifi_network_order._NETWORK_SETUP,
            '-removepreferredwirelessnetwork', interface, ssid)
    self.mox.StubOutWithMock(wifi_network_order.gmacpyutil, 'RunProcess')
    wifi_network_order.gmacpyutil.RunProcess(args, sudo=False,
                                             sudo_password=None).AndReturn(
                                                 ('\n', '\n', 0))
    self.mox.ReplayAll()
    wifi_network_order.RemovePreferredNetwork(interface, ssid)
    self.mox.VerifyAll()

  def testRemovePreferredNetworkFailure(self):
    """Test RemovePreferredNetwork with a bad interface and network."""
    interface = 'enX'
    ssid = 'NetworkThatDoesntExist'
    args = (wifi_network_order._NETWORK_SETUP,
            '-removepreferredwirelessnetwork', interface, ssid)
    self.mox.StubOutWithMock(wifi_network_order.gmacpyutil, 'RunProcess')
    wifi_network_order.gmacpyutil.RunProcess(
        args, sudo=False, sudo_password=None).AndReturn(
            ('enX does not exist\n', 'An error occurred\n', 1))
    self.mox.ReplayAll()
    with self.assertRaises(wifi_network_order.PreferenceRemovalError):
      wifi_network_order.RemovePreferredNetwork(interface, ssid)

    self.mox.VerifyAll()

  def testAddPreferredNetworkNoOptionalSuccess(self):
    """Test AddPreferredNetwork, no optional parameters, reporting success."""
    interface = 'en0'
    ssid = 'GuestNetwork'
    security = 'OPEN'
    args = [wifi_network_order._NETWORK_SETUP,
            '-addpreferredwirelessnetworkatindex', interface, ssid, '-1',
            security]
    self.mox.StubOutWithMock(wifi_network_order.gmacpyutil, 'RunProcess')
    wifi_network_order.gmacpyutil.RunProcess(
        args, sudo=False, sudo_password=None).AndReturn(('\n', '\n', 0))
    self.mox.ReplayAll()
    wifi_network_order.AddPreferredNetwork(interface, ssid, security)
    self.mox.VerifyAll()

  def testAddPreferredNetworkBothOptionalSuccess(self):
    """Test AddPreferredNetwork, both optional parameters, reporting success."""
    interface = 'en0'
    ssid = 'GuestNetwork'
    security = 'open'
    index = 0
    password = 'MyFirstWifiNetworkPasswordWhatIWrote'
    args = [wifi_network_order._NETWORK_SETUP,
            '-addpreferredwirelessnetworkatindex', interface, ssid, str(index),
            security.upper(), password]
    self.mox.StubOutWithMock(wifi_network_order.gmacpyutil, 'RunProcess')
    wifi_network_order.gmacpyutil.RunProcess(
        args, sudo=False, sudo_password=None).AndReturn(('\n', '\n', 0))
    self.mox.ReplayAll()
    wifi_network_order.AddPreferredNetwork(interface, ssid, security, index,
                                           password)
    self.mox.VerifyAll()

  def testAddPreferredNetworkBadSecurityType(self):
    """Test AddPreferredNetwork, bad security type."""
    interface = 'en0'
    ssid = 'GuestNetwork'
    security = 'INVA'
    with self.assertRaises(wifi_network_order.BadSecurityTypeError):
      wifi_network_order.AddPreferredNetwork(interface, ssid, security)

  def testAddPreferredNetworkBadInterface(self):
    """Test AddPreferredNetwork, bad interface name."""
    interface = 'enX'
    ssid = 'GuestNetwork'
    security = 'OPEN'
    args = [wifi_network_order._NETWORK_SETUP,
            '-addpreferredwirelessnetworkatindex', interface, ssid, '-1',
            security]
    self.mox.StubOutWithMock(wifi_network_order.gmacpyutil, 'RunProcess')
    wifi_network_order.gmacpyutil.RunProcess(
        args, sudo=False, sudo_password=None).AndReturn(
            ('\n', 'Bad interface name!\n', 1))
    self.mox.ReplayAll()
    with self.assertRaises(wifi_network_order.PreferenceAdditionError):
      wifi_network_order.AddPreferredNetwork(interface, ssid, security)

    self.mox.VerifyAll()

  def testResetPreferredNetworksNoInterface(self):
    networks = ['GuestNetwork$OPEN']
    self.mox.ReplayAll()
    self.assertIsNone(wifi_network_order.ResetPreferredNetworks(None, networks))
    self.mox.VerifyAll()

  def testResetPreferredNetworksRootRequired(self):
    """Test ResetPreferredNetworks, not running as root."""
    interface = 'en0'
    networks = ['GuestNetwork$OPEN']
    self.mox.StubOutWithMock(wifi_network_order.os, 'geteuid')
    wifi_network_order.os.geteuid().AndReturn(501)
    self.mox.ReplayAll()
    with self.assertRaises(wifi_network_order.NotRunningAsRootError):
      wifi_network_order.ResetPreferredNetworks(interface, networks)

    self.mox.VerifyAll()

  def testResetPreferredNetworksSudoPassword(self):
    """Test ResetPreferredNetworks with a sudo password supplied."""
    interface = 'en0'
    networks = ['GuestNetwork$OPEN']
    sudo_password = 'test'
    self.mox.StubOutWithMock(wifi_network_order.os, 'geteuid')
    self.mox.StubOutWithMock(wifi_network_order, 'RemovePreferredNetwork')
    self.mox.StubOutWithMock(wifi_network_order, 'AddPreferredNetwork')
    wifi_network_order.os.geteuid().AndReturn(501)
    wifi_network_order.RemovePreferredNetwork(interface, 'GuestNetwork',
                                              sudo_password=sudo_password)
    wifi_network_order.AddPreferredNetwork(interface, 'GuestNetwork', 'OPEN',
                                           index=0, sudo_password=sudo_password)
    self.mox.ReplayAll()
    wifi_network_order.ResetPreferredNetworks(interface, networks,
                                              sudo_password=sudo_password)
    self.mox.VerifyAll()

  def testResetPreferredNetworksReversesNetworks(self):
    """Test ResetPreferredNetworks reverses the network list."""
    interface = 'en0'
    networks = ['NetworkOne$OPEN', 'NetworkTwo$WPA2']
    self.mox.StubOutWithMock(wifi_network_order.os, 'geteuid')
    self.mox.StubOutWithMock(wifi_network_order, 'RemovePreferredNetwork')
    self.mox.StubOutWithMock(wifi_network_order, 'AddPreferredNetwork')
    wifi_network_order.os.geteuid().AndReturn(0)
    wifi_network_order.RemovePreferredNetwork(interface, 'NetworkTwo',
                                              sudo_password=None)
    wifi_network_order.AddPreferredNetwork(interface, 'NetworkTwo', 'WPA2',
                                           index=0, sudo_password=None)
    wifi_network_order.RemovePreferredNetwork(interface, 'NetworkOne',
                                              sudo_password=None)
    wifi_network_order.AddPreferredNetwork(interface, 'NetworkOne', 'OPEN',
                                           index=0, sudo_password=None)
    self.mox.ReplayAll()
    wifi_network_order.ResetPreferredNetworks(interface, networks)
    self.mox.VerifyAll()


def main(unused_argv):
  basetest.main()


if __name__ == '__main__':
  app.run()
