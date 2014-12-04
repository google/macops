"""Tests for airport module."""

import mock
from google.apputils import basetest
import airport


class AirportModuleTest(basetest.TestCase):
  """Test Airport module functions."""

  def setUp(self):
    self.mock_getintf_patcher = mock.patch.object(airport,
                                                  'GetDefaultInterface')
    self.mock_getintf = self.mock_getintf_patcher.start()
    self.mock_intf = mock.MagicMock()
    self.mock_getintf.return_value = self.mock_intf

    self.mock_sleep_patcher = mock.patch.object(airport.time, 'sleep')
    self.mock_sleep = self.mock_sleep_patcher.start()

  def tearDown(self):
    self.mock_getintf.stop()
    self.mock_sleep.stop()

  def testSetInterfacePowerOff(self):
    self.mock_intf.setPower_error_.return_value = (0, None)
    airport.SetInterfacePower(False)
    self.mock_intf.setPower_error_.assert_called_once_with(False, None)

  def testDisassociate(self):
    airport.Disassociate()
    self.mock_intf.disassociate.assert_called_once_with()

  # pylint: disable=g-line-too-long

  def testAssociateToNetworkNoPassword(self):
    mock_network = mock.MagicMock()
    self.mock_intf.associateToNetwork_password_forceBSSID_remember_error_.return_value = [True, None]
    mock_network.ssid.return_value = 'SSID'
    self.mock_intf.ssid.return_value = 'SSID'

    airport.AssociateToNetwork(mock_network)

    self.mock_intf.associateToNetwork_password_forceBSSID_remember_error_.assert_called_once_with(
        mock_network, None, False, False, None)

  def testAssociateToNetworkPassword(self):
    mock_network = mock.MagicMock()
    self.mock_intf.associateToNetwork_password_forceBSSID_remember_error_.return_value = [True, None]
    mock_network.ssid.return_value = 'SSID'
    self.mock_intf.ssid.return_value = 'SSID'

    airport.AssociateToNetwork(mock_network, 'hunter2')

    self.mock_intf.associateToNetwork_password_forceBSSID_remember_error_.assert_called_once_with(
        mock_network, 'hunter2', False, False, None)

  @mock.patch.object(airport, 'ScanForNetworks')
  def testAssociateToSSIDNoPassword(self, mock_sfn):
    mock_network = mock.MagicMock()
    mock_sfn.return_value = {'GuestSSID': mock_network}
    self.mock_intf.associateToNetwork_password_forceBSSID_remember_error_.return_value = [True, None]
    mock_network.ssid.return_value = 'GuestSSID'
    self.mock_intf.ssid.return_value = 'GuestSSID'

    airport.AssociateToSSID('GuestSSID')

    mock_sfn.assert_called_once_with('GuestSSID', interface=self.mock_intf)
    self.mock_intf.associateToNetwork_password_forceBSSID_remember_error_.assert_called_once_with(
        mock_network, None, False, False, None)

  @mock.patch.object(airport, 'ScanForNetworks')
  def testAssociateToSSIDPassword(self, mock_sfn):
    mock_network = mock.MagicMock()
    mock_sfn.return_value = {'GuestSSID': mock_network}
    self.mock_intf.associateToNetwork_password_forceBSSID_remember_error_.return_value = [True, None]
    mock_network.ssid.return_value = 'GuestSSID'
    self.mock_intf.ssid.return_value = 'GuestSSID'

    airport.AssociateToSSID('GuestSSID', password='hunter2')

    mock_sfn.assert_called_once_with('GuestSSID', interface=self.mock_intf)
    self.mock_intf.associateToNetwork_password_forceBSSID_remember_error_.assert_called_once_with(
        mock_network, 'hunter2', False, False, None)

  # pylint: enable=g-line-too-long

  def testScanForNetworksNoSSID(self):
    mock_network = mock.MagicMock()
    mock_network.ssid.return_value = 'GuestSSID'
    mock_network.rssiValue.return_value = -78

    mock_network2 = mock.MagicMock()
    mock_network2.ssid.return_value = 'GuestSSID'
    mock_network2.rssiValue.return_value = -62

    mock_network3 = mock.MagicMock()
    mock_network3.ssid.return_value = 'SSID'
    mock_network3.rssiValue.return_value = -25

    networks = [mock_network, mock_network2, mock_network3]

    self.mock_intf.scanForNetworksWithName_error_.return_value = [
        networks, None]
    retval = airport.ScanForNetworks(None)

    self.mock_intf.scanForNetworksWithName_error_.assert_called_once_with(None,
                                                                          None)
    self.assertEqual(retval, {'GuestSSID': mock_network2,
                              'SSID': mock_network3})


def main(unused_argv):
  basetest.main()


if __name__ == '__main__':
  basetest.main()
