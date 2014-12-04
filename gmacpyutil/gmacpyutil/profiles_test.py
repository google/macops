"""Tests for profiles module."""


import mock
from google.apputils import basetest

import profiles


class ProfilesModuleTest(basetest.TestCase):

  def testGenerateUUID(self):
    self.assertIsInstance(profiles.GenerateUUID('a'), str)
    self.assertTrue(profiles.GenerateUUID('a').isupper())
    self.assertEqual(profiles.GenerateUUID('a'),
                     profiles.GenerateUUID('a'))

  def testValidatePayload(self):
    payload = {}

    with self.assertRaises(profiles.PayloadValidationError):
      profiles.ValidatePayload(payload)

    payload.update({profiles.PAYLOADKEYS_IDENTIFIER: 'a',
                    profiles.PAYLOADKEYS_DISPLAYNAME: 'a',
                    profiles.PAYLOADKEYS_TYPE: 'com.apple.welcome.to.1984'})

    profiles.ValidatePayload(payload)

    self.assertEqual(payload.get(profiles.PAYLOADKEYS_UUID),
                     profiles.GenerateUUID('a'))
    self.assertEqual(payload.get(profiles.PAYLOADKEYS_ENABLED), True)
    self.assertEqual(payload.get(profiles.PAYLOADKEYS_VERSION), 1)


class ProfileClassTest(basetest.TestCase):
  """Tests for the Profile class."""

  def _GetValidProfile(self, include_payload=True):
    profile = profiles.Profile()
    profile.Set(profiles.PAYLOADKEYS_DISPLAYNAME, 'Acme Corp Config Profile')
    profile.Set(profiles.PAYLOADKEYS_IDENTIFIER, 'com.acme.configprofile')
    profile.Set(profiles.PAYLOADKEYS_ORG, 'Acme Corp')
    profile.Set(profiles.PAYLOADKEYS_SCOPE, ['System', 'User'])
    profile.Set(profiles.PAYLOADKEYS_TYPE, 'Configuration')
    if include_payload:
      profile.AddPayload(self._GetValidPayload())
    return profile

  def _GetValidPayload(self):
    test_payload = {profiles.PAYLOADKEYS_IDENTIFIER: 'com.test.payload',
                    profiles.PAYLOADKEYS_DISPLAYNAME: 'Test Payload',
                    profiles.PAYLOADKEYS_TYPE: 'com.apple.welcome.to.1984'}
    return test_payload

  def testInit(self):
    """Test the __init__ method."""
    profile = profiles.Profile()
    self.assertIsNotNone(profile._profile)
    self.assertEqual(profile._profile[profiles.PAYLOADKEYS_CONTENT], [])

  def testGet(self):
    profile = profiles.Profile()
    profile._profile['TestKey'] = 'TestValue'

    self.assertEqual(profile.Get(profiles.PAYLOADKEYS_CONTENT), [])
    self.assertEqual(profile.Get('TestKey'), 'TestValue')

  def testSet(self):
    profile = profiles.Profile()
    profile.Set('TestKey', 'TestValue')
    profile.Set('OtherKey', 'OtherValue')

    self.assertEqual(profile._profile['TestKey'], 'TestValue')
    self.assertEqual(profile._profile['OtherKey'], 'OtherValue')

  def testStr(self):
    profile = self._GetValidProfile()
    self.assertEqual(profile.__str__(), 'Acme Corp Config Profile')

  def testAddPayload(self):
    profile = self._GetValidProfile(include_payload=False)
    test_payload = self._GetValidPayload()

    with self.assertRaises(profiles.PayloadValidationError):
      profile.AddPayload('Payloads should be dicts')

    profile.AddPayload(test_payload)
    self.assertEqual(profile.Get(profiles.PAYLOADKEYS_CONTENT), [test_payload])

  def testValidateProfile(self):
    profile = profiles.Profile()

    with self.assertRaises(profiles.ProfileValidationError):
      profile._ValidateProfile()

    profile = self._GetValidProfile(include_payload=False)

    with self.assertRaises(profiles.ProfileValidationError):
      profile._ValidateProfile()

    profile.AddPayload(self._GetValidPayload())
    profile._ValidateProfile()

    self.assertIsNotNone(profile.Get(profiles.PAYLOADKEYS_UUID))
    self.assertIsNotNone(profile.Get(profiles.PAYLOADKEYS_VERSION))

  @mock.patch.object(profiles.plistlib, 'writePlist')
  def testSaveSuccess(self, mock_writeplist):
    profile = self._GetValidProfile()
    profile.Save('/tmp/hello')
    mock_writeplist.assert_called_once_with(profile._profile, '/tmp/hello')

  @mock.patch.object(profiles.plistlib, 'writePlist')
  def testSaveIOError(self, mock_writeplist):
    profile = self._GetValidProfile()
    mock_writeplist.side_effect = IOError

    with self.assertRaises(profiles.ProfileSaveError):
      profile.Save('/tmp/hello')

    mock_writeplist.assert_called_once_with(profile._profile, '/tmp/hello')

  @mock.patch.object(profiles.gmacpyutil, 'RunProcess')
  @mock.patch.object(profiles.Profile, 'Save')
  def testInstallSuccess(self, mock_save, mock_runprocess):
    profile = self._GetValidProfile()
    mock_runprocess.return_value = ['Output', None, 0]

    profile.Install()

    mock_save.assert_called_once_with(mock.ANY)
    mock_runprocess.assert_called_once_with(
        [profiles.CMD_PROFILES, '-I', '-F', mock.ANY],
        sudo=None, sudo_password=None)

  @mock.patch.object(profiles.gmacpyutil, 'RunProcess')
  @mock.patch.object(profiles.Profile, 'Save')
  def testInstallSudoPassword(self, mock_save, mock_runprocess):
    profile = self._GetValidProfile()
    mock_runprocess.return_value = ['Output', None, 0]

    profile.Install(sudo_password='ladygagaeatssocks')

    mock_save.assert_called_once_with(mock.ANY)
    mock_runprocess.assert_called_once_with(
        [profiles.CMD_PROFILES, '-I', '-F', mock.ANY],
        sudo='ladygagaeatssocks', sudo_password='ladygagaeatssocks')

  @mock.patch.object(profiles.gmacpyutil, 'RunProcess')
  @mock.patch.object(profiles.Profile, 'Save')
  def testInstallCommandFail(self, mock_save, mock_runprocess):
    profile = self._GetValidProfile()
    mock_runprocess.return_value = ['Output', 'Errors', 42]

    with self.assertRaisesRegexp(profiles.ProfileInstallationError,
                                 'Profile installation failed!\n'
                                 'Output, Errors, 42'):
      profile.Install(sudo_password='ladygagaeatssocks')

    mock_save.assert_called_once_with(mock.ANY)
    mock_runprocess.assert_called_once_with(
        [profiles.CMD_PROFILES, '-I', '-F', mock.ANY],
        sudo='ladygagaeatssocks', sudo_password='ladygagaeatssocks')

  @mock.patch.object(profiles.gmacpyutil, 'RunProcess')
  @mock.patch.object(profiles.Profile, 'Save')
  def testInstallCommandException(self, mock_save, mock_runprocess):
    profile = self._GetValidProfile()
    mock_runprocess.side_effect = profiles.gmacpyutil.GmacpyutilException

    with self.assertRaisesRegexp(profiles.ProfileInstallationError,
                                 'Profile installation failed!\n'):
      profile.Install(sudo_password='ladygagaeatssocks')

    mock_save.assert_called_once_with(mock.ANY)
    mock_runprocess.assert_called_once_with(
        [profiles.CMD_PROFILES, '-I', '-F', mock.ANY],
        sudo='ladygagaeatssocks', sudo_password='ladygagaeatssocks')


class NetworkProfileClassTest(basetest.TestCase):
  """Tests for the NetworkProfile class."""

  def testInit(self):
    profile = profiles.NetworkProfile('testuser')

    self.assertEqual(profile.Get(profiles.PAYLOADKEYS_DISPLAYNAME),
                     'Network Profile (testuser)')
    self.assertEqual(profile.Get(profiles.PAYLOADKEYS_DESCRIPTION),
                     'Network authentication settings')
    self.assertEqual(profile.Get(profiles.PAYLOADKEYS_IDENTIFIER),
                     'com.megacorp.networkprofile')
    self.assertEqual(profile.Get(profiles.PAYLOADKEYS_SCOPE),
                     ['System', 'User'])
    self.assertEqual(profile.Get(profiles.PAYLOADKEYS_TYPE), 'Configuration')
    self.assertEqual(profile.Get(profiles.PAYLOADKEYS_CONTENT), [])

  def testGenerateID(self):
    profile = profiles.NetworkProfile('testuser')

    self.assertEqual(profile._GenerateID('test_suffix'),
                     'com.megacorp.networkprofile.test_suffix')
    self.assertEqual(profile._GenerateID('another_suffix'),
                     'com.megacorp.networkprofile.another_suffix')

  @mock.patch.object(profiles.NetworkProfile, 'AddPayload')
  @mock.patch.object(profiles.crypto, 'load_privatekey')
  @mock.patch.object(profiles.crypto, 'load_certificate')
  @mock.patch.object(profiles.crypto, 'PKCS12Type')
  @mock.patch.object(profiles.certs, 'Certificate')
  def testAddMachineCertificateSuccess(self, mock_certificate, mock_pkcs12,
                                       mock_loadcert, mock_loadkey,
                                       mock_addpayload):
    mock_certobj = mock.MagicMock()
    mock_certobj.subject_cn = 'My Cert Subject'
    mock_certobj.osx_fingerprint = '0011223344556677889900'
    mock_certificate.return_value = mock_certobj

    mock_pkcs12obj = mock.MagicMock()
    mock_pkcs12obj.export.return_value = '-----PKCS12 Data-----'
    mock_pkcs12.return_value = mock_pkcs12obj

    mock_loadcert.return_value = 'certobj'
    mock_loadkey.return_value = 'keyobj'

    profile = profiles.NetworkProfile('testuser')
    profile.AddMachineCertificate('fakecert', 'fakekey')

    mock_pkcs12.assert_called_once_with()
    mock_pkcs12obj.set_certificate.assert_called_once_with('certobj')
    mock_pkcs12obj.set_privatekey.assert_called_once_with('keyobj')
    mock_pkcs12obj.export.assert_called_once_with('0011223344556677889900')
    mock_loadcert.assert_called_once_with(1, 'fakecert')
    mock_loadkey.assert_called_once_with(1, 'fakekey')

    mock_addpayload.assert_called_once_with(
        {profiles.PAYLOADKEYS_IDENTIFIER:
             'com.megacorp.networkprofile.machine_cert',
         profiles.PAYLOADKEYS_TYPE: 'com.apple.security.pkcs12',
         profiles.PAYLOADKEYS_DISPLAYNAME: 'My Cert Subject',
         profiles.PAYLOADKEYS_ENABLED: True,
         profiles.PAYLOADKEYS_VERSION: 1,
         profiles.PAYLOADKEYS_CONTENT: profiles.plistlib.Data(
             '-----PKCS12 Data-----'),
         profiles.PAYLOADKEYS_UUID: mock.ANY,
         'Password': '0011223344556677889900'})

  @mock.patch.object(profiles.crypto, 'load_privatekey')
  @mock.patch.object(profiles.crypto, 'load_certificate')
  @mock.patch.object(profiles.crypto, 'PKCS12Type')
  @mock.patch.object(profiles.certs, 'Certificate')
  def testAddMachineCertificateInvalidKey(self, mock_certificate, mock_pkcs12,
                                          mock_loadcert, mock_loadkey):
    mock_certobj = mock.MagicMock()
    mock_certobj.subject_cn = 'My Cert Subject'
    mock_certobj.osx_fingerprint = '0011223344556677889900'
    mock_certificate.return_value = mock_certobj

    mock_pkcs12obj = mock.MagicMock()
    mock_pkcs12obj.export.side_effect = profiles.crypto.Error
    mock_pkcs12.return_value = mock_pkcs12obj

    mock_loadcert.return_value = 'certobj'
    mock_loadkey.return_value = 'keyobj_from_different_cert'

    profile = profiles.NetworkProfile('testuser')
    with self.assertRaises(profiles.CertificateError):
      profile.AddMachineCertificate('fakecert', 'otherfakekey')

  @mock.patch.object(profiles.certs, 'Certificate')
  def testAddMachineCertificateBadCert(self, mock_certificate):
    mock_certificate.side_effect = profiles.certs.CertError

    profile = profiles.NetworkProfile('testuser')

    with self.assertRaises(profiles.CertificateError):
      profile.AddMachineCertificate('fakecert', 'fakekey')

  @mock.patch.object(profiles.NetworkProfile, 'AddPayload')
  @mock.patch.object(profiles.certs, 'Certificate')
  def testAddAnchorCertificateSuccess(self, mock_certificate, mock_addpayload):
    mock_certobj = mock.MagicMock()
    mock_certobj.subject_cn = 'My Cert Subject'
    mock_certobj.osx_fingerprint = '0011223344556677889900'
    mock_certificate.return_value = mock_certobj

    profile = profiles.NetworkProfile('testuser')
    profile.AddAnchorCertificate('my_cert')

    mock_certificate.assert_called_once_with('my_cert')
    mock_addpayload.assert_called_once_with(
        {profiles.PAYLOADKEYS_IDENTIFIER:
             'com.megacorp.networkprofile.0011223344556677889900',
         profiles.PAYLOADKEYS_TYPE: 'com.apple.security.pkcs1',
         profiles.PAYLOADKEYS_DISPLAYNAME: 'My Cert Subject',
         profiles.PAYLOADKEYS_CONTENT: profiles.plistlib.Data('my_cert'),
         profiles.PAYLOADKEYS_ENABLED: True,
         profiles.PAYLOADKEYS_VERSION: 1,
         profiles.PAYLOADKEYS_UUID: mock.ANY})

  @mock.patch.object(profiles.certs, 'Certificate')
  def testAddAnchorCertificateBadCert(self, mock_certificate):
    mock_certificate.side_effect = profiles.certs.CertError

    profile = profiles.NetworkProfile('testuser')
    with self.assertRaises(profiles.CertificateError):
      profile.AddAnchorCertificate('test_cert')

  @mock.patch.object(profiles.NetworkProfile, 'AddPayload')
  def testAddNetworkPayloadSSID(self, mock_addpayload):
    profile = profiles.NetworkProfile('test_user')

    profile._auth_cert = '00000000-AUTH-CERT-UUID-00000000'
    profile._anchor_certs = ['00000000-ANCH-ORCE-RTUU-ID000000']

    profile.AddTrustedServer('radius.company.com')
    profile.AddNetworkPayload('SSID')

    eap_client_data = {'AcceptEAPTypes': [13],
                       'PayloadCertificateAnchorUUID':
                           ['00000000-ANCH-ORCE-RTUU-ID000000'],
                       'TLSTrustedServerNames':
                           ['radius.company.com'],
                       'TLSAllowTrustExceptions': False}

    mock_addpayload.assert_called_once_with(
        {'AutoJoin': True,
         'SetupModes': ['System', 'User'],
         'PayloadCertificateUUID': '00000000-AUTH-CERT-UUID-00000000',
         'EncryptionType': 'WPA',
         'Interface': 'BuiltInWireless',
         profiles.PAYLOADKEYS_DISPLAYNAME: 'SSID',
         profiles.PAYLOADKEYS_IDENTIFIER:
             'com.megacorp.networkprofile.ssid.SSID',
         profiles.PAYLOADKEYS_TYPE: 'com.apple.wifi.managed',
         'SSID_STR': 'SSID',
         'EAPClientConfiguration': eap_client_data})

  @mock.patch.object(profiles.NetworkProfile, 'AddPayload')
  def testAddNetworkPayloadWired(self, mock_addpayload):
    profile = profiles.NetworkProfile('test_user')

    profile._auth_cert = '00000000-AUTH-CERT-UUID-00000000'
    profile._anchor_certs = ['00000000-ANCH-ORCE-RTUU-ID000000']

    profile.AddTrustedServer('radius.company.com')
    profile.AddNetworkPayload('wired')

    eap_client_data = {'AcceptEAPTypes': [13],
                       'PayloadCertificateAnchorUUID':
                           ['00000000-ANCH-ORCE-RTUU-ID000000'],
                       'TLSTrustedServerNames':
                           ['radius.company.com'],
                       'TLSAllowTrustExceptions': False}

    mock_addpayload.assert_called_once_with(
        {'AutoJoin': True,
         'SetupModes': ['System', 'User'],
         'PayloadCertificateUUID': '00000000-AUTH-CERT-UUID-00000000',
         'EncryptionType': 'Any',
         'Interface': 'FirstActiveEthernet',
         profiles.PAYLOADKEYS_DISPLAYNAME: 'Wired',
         profiles.PAYLOADKEYS_IDENTIFIER:
             'com.megacorp.networkprofile.wired',
         profiles.PAYLOADKEYS_TYPE: 'com.apple.firstactiveethernet.managed',
         'EAPClientConfiguration': eap_client_data})


if __name__ == '__main__':
  basetest.main()
