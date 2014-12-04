"""Unit tests for systemconfig module."""

import struct


import mock

from google.apputils import basetest
import systemconfig


class SysconfigModuleTest(basetest.TestCase):
  """Test systemconfig module-level functions."""

  @mock.patch.object(systemconfig, 'SCDynamicPreferences', autospec=True)
  @mock.patch.object(systemconfig, 'logging')
  def testConfigureSystemProxy(self, mock_logging, mock_scdp):
    """Test ConfigureSystemProxy success."""
    proxy = 'proxy'
    enable = True
    mock_scdp().SetProxy.return_value = True
    self.assertEqual(None, systemconfig.ConfigureSystemProxy(proxy, enable))
    self.assertFalse(mock_logging.error.called)

  @mock.patch.object(systemconfig, 'SCDynamicPreferences', autospec=True)
  @mock.patch.object(systemconfig, 'logging')
  def testConfigureSystemProxyFailure(self, mock_logging, mock_scdp):
    """Test ConfigureSystemProxy failure."""
    proxy = 'proxy'
    enable = True
    mock_scdp().SetProxy.return_value = False
    self.assertEqual(None, systemconfig.ConfigureSystemProxy(proxy, enable))
    self.assertTrue(mock_logging.error.called)

  @mock.patch.object(systemconfig, 'SCPreferences', autospec=True)
  def testGetLocalName(self, mock_scp):
    """Test GetLocalName."""
    mock_scp().GetLocalName.return_value = 'localname'
    self.assertEqual('localname', systemconfig.GetLocalName())

  @mock.patch.object(systemconfig, 'SCPreferences', autospec=True)
  def testGetComputerName(self, mock_scp):
    """Test GetComputerName."""
    mock_scp().GetComputerName.return_value = 'computername'
    self.assertEqual('computername', systemconfig.GetComputerName())

  @mock.patch.object(systemconfig, 'SCPreferences', autospec=True)
  def testConfigureLocalName(self, _):
    """Test ConfigureLocalName."""
    self.assertEqual(None, systemconfig.ConfigureLocalName('localname'))

  @mock.patch.object(systemconfig, 'SCPreferences', autospec=True)
  def testConfigureComputerName(self, _):
    """Test ConfigureComputerName."""
    self.assertEqual(None, systemconfig.ConfigureComputerName('computername'))

  @mock.patch.object(systemconfig, '_GetMACFromData')
  @mock.patch.object(systemconfig, 'gmacpyutil', autospec=True)
  def testGetNetworkInterfaces(self, mock_gc, mock_gmfd):
    """Test GetNetworkInterfaces."""
    ni_data = {'Interfaces': [
        {'SCNetworkInterfaceType': 'Ethernet',
         'IOMACAddress': 'raw mac data',
         'SCNetworkInterfaceInfo': {
             'UserDefinedName': 'Airport'
         },
         'BSD Name': 'en0',
         'IOPathMatch': 'path',
         'IOBuiltin': True
        }
    ]}
    mock_gc.GetPlist.return_value = ni_data
    mock_gmfd.return_value = 'a:b'
    self.assertEqual([{'type': 'Ethernet',
                       'mac': 'a:b',
                       'name': 'Airport',
                       'dev': 'en0',
                       'bus': 'path',
                       'builtin': True}],
                     systemconfig.GetNetworkInterfaces())

  @mock.patch.object(systemconfig, 'GetNetworkInterfaces')
  def testGetDot1xInterfaces(self, mock_gni):
    """Test GetDot1xInterfaces."""
    builtin = {'type': 'Ethernet', 'mac': 'a:b', 'name': 'Airport',
               'dev': 'en0', 'bus': 'path', 'builtin': True}
    external = {'type': 'Ethernet', 'mac': 'a:b', 'name': 'BogusNIC',
                'dev': 'en1', 'bus': 'path', 'builtin': False}
    mock_gni.return_value = [builtin, external]
    self.assertEqual([builtin],
                     systemconfig.GetDot1xInterfaces())

  @mock.patch.object(systemconfig, 'GetDot1xInterfaces')
  def testGetMacAddressesWhenOneFound(self, mock_gd1i):
    """Test GetMacAddresses when one is found."""
    mock_gd1i.return_value = [{'mac': 'ab:cd:ef:gh'}]
    self.assertEqual(['ABCDEFGH'], systemconfig.GetMacAddresses())

  @mock.patch.object(systemconfig, 'GetDot1xInterfaces')
  def testGetMacAddressesWhenMultipleAreFound(self, mock_gd1i):
    """Test GetMacAddresses when multiple are found."""
    mock_gd1i.return_value = [{'mac': 'ab:cd:ef:gh'},
                              {'mac': 'ij:kl:mn:op'}]
    self.assertEqual(['ABCDEFGH', 'IJKLMNOP'], systemconfig.GetMacAddresses())

  @mock.patch.object(systemconfig, 'GetDot1xInterfaces')
  def testGetMacAddressesWhenNoneFound(self, mock_gd1i):
    """Test GetMacAddresses with none found."""
    mock_gd1i.return_value = []
    self.assertEqual([], systemconfig.GetMacAddresses())

  def testGetMACFromData(self):
    """Test _GetMACFromData."""
    mac_data = (0, 62, 225, 190, 73, 13)
    mac_str = '00:3e:e1:be:49:0d'
    buf = struct.pack('6B', *mac_data)
    self.assertEqual(mac_str, systemconfig._GetMACFromData(buf))

  def testGetMACFromDataWithBadData(self):
    mac_data = (0, 62)
    buf = struct.pack('2B', *mac_data)
    with self.assertRaises(systemconfig.InterfaceError):
      systemconfig._GetMACFromData(buf)


class SCDynamicPreferencesTest(basetest.TestCase):
  """Test systemconfig.SCDynamicPreferences class."""

  @mock.patch.object(systemconfig, 'SCDynamicStoreCreate')
  def testInit(self, mock_scdsc):
    """Test SCDynamicPreferences init."""
    mock_scdsc.return_value = 999
    scdp = systemconfig.SCDynamicPreferences()
    self.assertEqual(scdp.store, 999)

  @mock.patch.object(systemconfig, 'SCDynamicStoreCreate')
  @mock.patch.object(systemconfig, 'SCDynamicStoreCopyValue')
  def testReadProxySettings(self, mock_scdscv, mock_scdsc):
    """Test SCDynamicPreferences ReadProxySettings."""
    proxies = {'ExceptionsList': ('*.local', '169.254/16'),
               'FTPPassive': 1, 'ProxyAutoConfigEnable': 1,
               'ProxyAutoConfigURLString':
               'https://proxyconfig.megacorp.com/proxy.pac'
              }
    mock_scdsc.return_value = 'store'
    mock_scdscv.return_value = proxies
    scdp = systemconfig.SCDynamicPreferences()
    self.assertEqual(scdp.ReadProxySettings(), proxies)

  @mock.patch.multiple(
      systemconfig, SCDynamicStoreCreate=mock.DEFAULT,
      NSMutableDictionary=mock.DEFAULT, SCDynamicStoreSetValue=mock.DEFAULT)
  @mock.patch.object(systemconfig.SCDynamicPreferences, 'ReadProxySettings')
  def testSetProxyEnable(self, mock_rps, **mocks):
    """Test SCDynamicPreferences SetProxy, enable proxy."""
    enable = True
    pac = 'pac'
    proxy = 'proxy settings'
    mocks['SCDynamicStoreCreate'].return_value = 'store'
    mock_rps.return_value = proxy
    proxies = {'ProxyAutoConfigURLString': pac, 'ProxyAutoConfigEnable': 1}
    mocks['NSMutableDictionary'].dictionaryWithDictionary_.return_value = proxies  # pylint: disable=line-too-long
    mocks['SCDynamicStoreSetValue'].return_value = 'foo'
    scdp = systemconfig.SCDynamicPreferences()
    self.assertEqual(scdp.SetProxy(enable, pac), 'foo')

  @mock.patch.multiple(
      systemconfig, SCDynamicStoreCreate=mock.DEFAULT,
      NSMutableDictionary=mock.DEFAULT, SCDynamicStoreSetValue=mock.DEFAULT)
  @mock.patch.object(systemconfig.SCDynamicPreferences, 'ReadProxySettings')
  def testSetProxyDisable(self, mock_rps, **mocks):
    """Test SCDynamicPreferences SetProxy, disable proxy."""
    enable = False
    pac = 'pac'
    mocks['SCDynamicStoreCreate'].return_value = 'store'
    proxy = 'proxy settings'
    mock_rps.return_value = proxy
    proxies = {'ProxyAutoConfigURLString': pac, 'ProxyAutoConfigEnable': 0}
    mocks['NSMutableDictionary'].return_value = proxies
    mocks['SCDynamicStoreSetValue'].return_value = 'foo'
    scdp = systemconfig.SCDynamicPreferences()
    self.assertEqual(scdp.SetProxy(enable, pac), 'foo')


class SCPreferencesTest(basetest.TestCase):
  """Test systemconfig.SCPreferences class."""

  @mock.patch.object(systemconfig, 'SCPreferencesCreate')
  def testInit(self, mock_scpc):
    """Test SCPreferences init."""
    mock_scpc.return_value = 999
    scp = systemconfig.SCPreferences()
    self.assertEqual(scp.session, 999)

  @mock.patch.multiple(
      systemconfig, SCPreferencesCreate=mock.DEFAULT,
      SCPreferencesCommitChanges=mock.DEFAULT,
      SCPreferencesApplyChanges=mock.DEFAULT)
  def testSave(self, **mocks):
    """Test SCPreferences Save success."""
    mocks['SCPreferencesCreate'].return_value = 'session'
    mocks['SCPreferencesCommitChanges'].return_value = True
    mocks['SCPreferencesApplyChanges'].return_value = True
    scp = systemconfig.SCPreferences()
    self.assertEqual(None, scp.Save())

  @mock.patch.object(systemconfig, 'SCPreferencesCreate')
  def testSaveNoSession(self, mock_scpc):
    """Test SCPreferences Save, no session."""
    mock_scpc.return_value = None
    scp = systemconfig.SCPreferences()
    self.assertEqual(None, scp.Save())

  @mock.patch.multiple(
      systemconfig, SCPreferencesCreate=mock.DEFAULT,
      SCPreferencesCommitChanges=mock.DEFAULT)
  def testSaveCommitFailed(self, **mocks):
    """Test SCPreferences Save, commit failed."""
    mocks['SCPreferencesCreate'].return_value = 'session'
    mocks['SCPreferencesCommitChanges'].return_value = False
    scp = systemconfig.SCPreferences()
    self.assertRaises(systemconfig.SysconfigError, scp.Save)

  @mock.patch.multiple(
      systemconfig, SCPreferencesCreate=mock.DEFAULT,
      SCPreferencesCommitChanges=mock.DEFAULT,
      SCPreferencesApplyChanges=mock.DEFAULT)
  def testSaveApplyFailed(self, **mocks):
    """Test SCPreferences Save, apply failed."""
    mocks['SCPreferencesCreate'].return_value = 'session'
    mocks['SCPreferencesCommitChanges'].return_value = True
    mocks['SCPreferencesApplyChanges'].return_value = False
    scp = systemconfig.SCPreferences()
    self.assertRaises(systemconfig.SysconfigError, scp.Save)

  @mock.patch.multiple(
      systemconfig, SCPreferencesCreate=mock.DEFAULT,
      SCPreferencesPathGetValue=mock.DEFAULT)
  @mock.patch.object(systemconfig.os, 'path', autospec=True)
  def testGetPathValue(self, mock_osp, **mocks):
    """Test SCPreferences GetPathValue."""
    mocks['SCPreferencesCreate'].return_value = 'session'
    mock_osp.basename.return_value = 'path'
    mock_osp.dirname.return_value = '/some'
    mocks['SCPreferencesPathGetValue'].return_value = {'path': 'value'}
    scp = systemconfig.SCPreferences()
    self.assertEqual('value', scp.GetPathValue('/some/path'))

  @mock.patch.multiple(systemconfig,
                       SCPreferencesCreate=mock.DEFAULT,
                       SCPreferencesPathGetValue=mock.DEFAULT)
  def testGetPathValueNoMatchingValue(self, **mocks):
    """Test SCPreferences GetPathValue, no matching value."""
    mocks['SCPreferencesCreate'].return_value = 'session'
    mocks['SCPreferencesPathGetValue'].return_value = {'not_it': 'value'}
    scp = systemconfig.SCPreferences()
    self.assertEqual(None, scp.GetPathValue('/some/path'))

  @mock.patch.multiple(systemconfig,
                       SCPreferencesCreate=mock.DEFAULT,
                       SCPreferencesPathGetValue=mock.DEFAULT)
  def testGetPathValueWholeTree(self, **mocks):
    """Test SCPreferences GetPathValue, get whole tree."""
    mocks['SCPreferencesCreate'].return_value = 'session'
    mocks['SCPreferencesPathGetValue'].return_value = 'whole tree'
    scp = systemconfig.SCPreferences()
    self.assertEqual('whole tree', scp.GetPathValue('/'))

  @mock.patch.multiple(systemconfig,
                       SCPreferencesCreate=mock.DEFAULT,
                       SCPreferencesPathGetValue=mock.DEFAULT)
  def testGetPathValueNoMatchingPath(self, **mocks):
    """Test SCPreferences GetPathValue, no matching path."""
    mocks['SCPreferencesCreate'].return_value = 'session'
    mocks['SCPreferencesPathGetValue'].return_value = None
    scp = systemconfig.SCPreferences()
    self.assertEqual(None, scp.GetPathValue('/some/path'))

  @mock.patch.multiple(systemconfig,
                       SCPreferencesCreate=mock.DEFAULT,
                       SCPreferencesPathGetValue=mock.DEFAULT,
                       SCPreferencesPathSetValue=mock.DEFAULT)
  def testSetPathValue(self, **mocks):
    """Test SCPreferences SetPathValue."""
    mocks['SCPreferencesCreate'].return_value = 'session'
    mocks['SCPreferencesPathGetValue'].return_value = {'path': 'value'}
    scp = systemconfig.SCPreferences()
    self.assertEqual(None, scp.SetPathValue('/some/path', 'newval'))

  @mock.patch.multiple(systemconfig,
                       SCPreferencesCreate=mock.DEFAULT,
                       SCPreferencesPathGetValue=mock.DEFAULT,
                       SCPreferencesPathSetValue=mock.DEFAULT,
                       NSMutableDictionary=mock.DEFAULT)
  def testSetPathValueNewPath(self, **mocks):
    """Test SCPreferences SetPathValue, new path created."""
    mocks['SCPreferencesCreate'].return_value = 'session'
    mocks['SCPreferencesPathGetValue'].return_value = None
    mocks['NSMutableDictionary'].alloc().init.return_value = {}
    scp = systemconfig.SCPreferences()
    self.assertEqual(None, scp.SetPathValue('/some/path', 'newval'))

  @mock.patch.multiple(systemconfig.SCPreferences,
                       GetPathValue=mock.DEFAULT, SetPathValue=mock.DEFAULT)
  @mock.patch.multiple(systemconfig, SCPreferencesCreate=mock.DEFAULT)
  def testSetProxy(self, **mocks):
    """Test SCPreferences SetProxy, enabled, default proxy."""
    interfaces = {'interface':
                  {'Proxies':
                   {'ProxyAutoConfigEnable': 0,
                    'ProxyAutoConfigURLString': 'url'}}}
    mocks['GetPathValue'].return_value = interfaces
    interfaces['interface']['ProxyAutoConfigEnable'] = 1
    interfaces['interface']['ProxyAutoConfigURLString'] = (
        systemconfig.CORP_PROXY)
    scp = systemconfig.SCPreferences()
    self.assertEqual(None, scp.SetProxy())
    self.assertEqual(
        1, interfaces['interface']['Proxies']['ProxyAutoConfigEnable'])
    self.assertEqual(
        systemconfig.CORP_PROXY,
        interfaces['interface']['Proxies']['ProxyAutoConfigURLString'])

  @mock.patch.multiple(systemconfig.SCPreferences,
                       GetPathValue=mock.DEFAULT, SetPathValue=mock.DEFAULT)
  @mock.patch.multiple(systemconfig, SCPreferencesCreate=mock.DEFAULT)
  def testSetProxyNoInterfacesWithProxySupport(self, **mocks):
    """Test SCPreferences SetProxy, no interfaces that support proxies found."""
    interfaces = {'interface': {'nope': 0}}
    mocks['GetPathValue'].return_value = interfaces
    scp = systemconfig.SCPreferences()
    self.assertEqual(None, scp.SetProxy())

  @mock.patch.multiple(systemconfig.SCPreferences,
                       GetPathValue=mock.DEFAULT, SetPathValue=mock.DEFAULT)
  @mock.patch.multiple(systemconfig, SCPreferencesCreate=mock.DEFAULT)
  def testSetProxyDisableProxy(self, **mocks):
    """Test SCPreferences SetProxy, disabled, default proxy."""
    interfaces = {'interface':
                  {'Proxies':
                   {'ProxyAutoConfigEnable': 1,
                    'ProxyAutoConfigURLString': 'url'}}}
    mocks['GetPathValue'].return_value = interfaces
    scp = systemconfig.SCPreferences()
    self.assertEqual(None, scp.SetProxy(enable=False))
    self.assertEqual(
        0,
        interfaces['interface']['Proxies']['ProxyAutoConfigEnable'])

  @mock.patch.multiple(systemconfig.SCPreferences, GetPathValue=mock.DEFAULT)
  @mock.patch.multiple(systemconfig, SCPreferencesCreate=mock.DEFAULT)
  def testGetComputerName(self, **mocks):
    """Test SCPreferences GetComputerName."""
    mocks['GetPathValue'].return_value = 'computer'
    scp = systemconfig.SCPreferences()
    self.assertEqual('computer', scp.GetComputerName())

  @mock.patch.multiple(systemconfig.SCPreferences, GetPathValue=mock.DEFAULT)
  @mock.patch.multiple(systemconfig, SCPreferencesCreate=mock.DEFAULT)
  def testGetLocalName(self, **mocks):
    """Test SCPreferences GetLocalName."""
    mocks['GetPathValue'].return_value = 'localname'
    scp = systemconfig.SCPreferences()
    self.assertEqual('localname', scp.GetComputerName())

  @mock.patch.multiple(systemconfig.SCPreferences, GetPathValue=mock.DEFAULT)
  @mock.patch.multiple(systemconfig, SCPreferencesCreate=mock.DEFAULT)
  def testGetHostName(self, **mocks):
    """Test SCPreferences GetHostName."""
    mocks['GetPathValue'].return_value = 'hostname'
    scp = systemconfig.SCPreferences()
    self.assertEqual('hostname', scp.GetComputerName())

  @mock.patch.multiple(systemconfig.SCPreferences, GetPathValue=mock.DEFAULT,
                       SetPathValue=mock.DEFAULT)
  @mock.patch.multiple(systemconfig, SCPreferencesCreate=mock.DEFAULT)
  def testSetComputerName(self, **mocks):
    """Test SCPreferences SetComputerName."""
    mocks['GetPathValue'].return_value = 'computername'
    scp = systemconfig.SCPreferences()
    self.assertEqual(None, scp.SetComputerName('newname'))
    self.assertEqual(None, scp.SetComputerName('computername'))
    # Only called once from 'newname'
    self.assertEqual(1, mocks['SetPathValue'].call_count)

  @mock.patch.multiple(systemconfig.SCPreferences, GetPathValue=mock.DEFAULT,
                       SetPathValue=mock.DEFAULT)
  @mock.patch.multiple(systemconfig, SCPreferencesCreate=mock.DEFAULT)
  def testSetLocalName(self, **mocks):
    """Test SCPreferences SetLocalName."""
    mocks['GetPathValue'].return_value = 'localname'
    scp = systemconfig.SCPreferences()
    self.assertEqual(None, scp.SetComputerName('newname'))
    self.assertEqual(None, scp.SetComputerName('localname'))
    # Only called once from 'newname'
    self.assertEqual(1, mocks['SetPathValue'].call_count)

  @mock.patch.multiple(systemconfig.SCPreferences, GetPathValue=mock.DEFAULT,
                       SetPathValue=mock.DEFAULT)
  @mock.patch.multiple(systemconfig, SCPreferencesCreate=mock.DEFAULT)
  def testSetHostName(self, **mocks):
    """Test SCPreferences SetHostName."""
    mocks['GetPathValue'].return_value = 'hostname'
    scp = systemconfig.SCPreferences()
    self.assertEqual(None, scp.SetComputerName('newname'))
    self.assertEqual(None, scp.SetComputerName('hostname'))
    # Only called once from 'newname'
    self.assertEqual(1, mocks['SetPathValue'].call_count)


class SystemProfilerTest(basetest.TestCase):
  """Test class for SystemProfiler."""

  @mock.patch.object(systemconfig.gmacpyutil, 'RunProcess')
  def testGetSystemProfilerOutput(self, mock_rp):
    """Test _GetSystemProfilerOutput()."""
    mock_rp.return_value = ['output', None, 0]
    sp = systemconfig.SystemProfiler()
    self.assertEqual('output', sp._GetSystemProfilerOutput('sp_type'))

  @mock.patch.object(systemconfig.SystemProfiler, '_GetSystemProfilerOutput')
  @mock.patch.object(systemconfig, 'NSString')
  def testGetSystemProfile(self, mock_nss, mock_gspo):
    """Test _GetSystemProfile()."""
    sp_xml = 'foo'
    sp_type = 'bar'
    mock_gspo.return_value = sp_xml
    mock_nss.stringWithString_().propertyList.return_value = 'contents'
    sp = systemconfig.SystemProfiler()
    self.assertEqual(sp._GetSystemProfile(sp_type), 'contents')
    self.assertEqual(sp._cache, {'bar': 'contents'})


def main(unused_argv):
  basetest.main()

if __name__ == '__main__':
  basetest.main()
