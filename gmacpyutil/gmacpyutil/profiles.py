"""Module for manipulating and installing Configuration Profiles."""

import plistlib
import tempfile
import uuid
from OpenSSL import crypto
from . import gmacpyutil
from . import certs
from . import defaults

CMD_PROFILES = '/usr/bin/profiles'

PAYLOADKEYS_IDENTIFIER = 'PayloadIdentifier'
PAYLOADKEYS_DISPLAYNAME = 'PayloadDisplayName'
PAYLOADKEYS_TYPE = 'PayloadType'
PAYLOADKEYS_DESCRIPTION = 'PayloadDescription'
PAYLOADKEYS_ORG = 'PayloadOrganization'
PAYLOADKEYS_SCOPE = 'PayloadScope'
PAYLOADKEYS_CONTENT = 'PayloadContent'
PAYLOADKEYS_UUID = 'PayloadUUID'
PAYLOADKEYS_ENABLED = 'PayloadEnabled'
PAYLOADKEYS_VERSION = 'PayloadVersion'

NETWORK_PROFILE_ID = defaults.NETWORK_PROFILE_ID
ORGANIZATION_NAME = defaults.ORGANIZATION_NAME


class Error(Exception):
  """Base error class."""


class ProfileSaveError(Error):
  """Error saving configuration profile."""


class ProfileInstallationError(Error):
  """Error installing configuration profile."""


class ProfileValidationError(Error):
  """Error validating configuration profile."""


class PayloadValidationError(Error):
  """Error validating payload."""


class CertificateError(Error):
  """Error adding a certificate to a network configuration profile."""


def GenerateUUID(payload_id):
  """Generates a UUID for a given PayloadIdentifier.

  This function will always generate the same UUID for a given identifier.

  Args:
    payload_id: str, a payload identifier string (reverse-dns style).

  Returns:
    uuid: str, a valid UUID based on the payload ID.
  """
  return str(uuid.uuid5(uuid.NAMESPACE_DNS, payload_id)).upper()


def ValidatePayload(payload):
  """Validate the payload includes all required keys.

  Will automatically add the following keys if they do not already exist:
    PayloadUUID, PayloadEnabled, PayloadVersion

  Args:
    payload: dict, the payload to validate.

  Raises:
    PayloadValidationError: the payload is missing a required key.
  """
  required_keys = [PAYLOADKEYS_IDENTIFIER,
                   PAYLOADKEYS_DISPLAYNAME,
                   PAYLOADKEYS_TYPE]

  for key in required_keys:
    if key not in payload:
      raise PayloadValidationError('Required key (%s) missing.' % key)

  if PAYLOADKEYS_UUID not in payload:
    payload[PAYLOADKEYS_UUID] = GenerateUUID(payload[PAYLOADKEYS_IDENTIFIER])

  if PAYLOADKEYS_ENABLED not in payload:
    payload[PAYLOADKEYS_ENABLED] = True

  if PAYLOADKEYS_VERSION not in payload:
    payload[PAYLOADKEYS_VERSION] = 1


class Profile(object):
  """Represents a configuration profile which can be installed."""

  def __init__(self):
    self._profile = plistlib.Plist()
    self.Set(PAYLOADKEYS_CONTENT, [])

  def __str__(self):
    return self.Get(PAYLOADKEYS_DISPLAYNAME)

  def Get(self, key):
    return self._profile.get(key)

  def Set(self, key, value):
    self._profile[key] = value

  def _ValidateProfile(self):
    """Validate the profile and all payloads are valid.

    Raises:
      ProfileValidationError: the profile data was not valid.
    """
    required_keys = [PAYLOADKEYS_DISPLAYNAME,
                     PAYLOADKEYS_IDENTIFIER,
                     PAYLOADKEYS_ORG,
                     PAYLOADKEYS_SCOPE,
                     PAYLOADKEYS_TYPE]
    for key in required_keys:
      if not self.Get(key):
        raise ProfileValidationError('Required key (%s) missing.' % key)

    if not self.Get(PAYLOADKEYS_UUID):
      self.Set(PAYLOADKEYS_UUID, GenerateUUID(self.Get(PAYLOADKEYS_IDENTIFIER)))

    if not self.Get(PAYLOADKEYS_VERSION):
      self.Set(PAYLOADKEYS_VERSION, 1)

    if len(self.Get(PAYLOADKEYS_CONTENT)) < 1:
      raise ProfileValidationError('Profile has no payloads.')

  def AddPayload(self, payload):
    """Adds a new payload to the PayloadContent dict.

    Args:
      payload: dict, dictionary of payload data.

    Raises:
      PayloadValidationError: payload could not be validated.
    """
    ValidatePayload(payload)
    self.Get(PAYLOADKEYS_CONTENT).append(payload)

  def Save(self, path):
    """Save the profile to disk.

    Args:
      path: str, the path to save the profile to.

    Raises:
      ProfileValidationError: profile data was not valid.
      ProfileSaveError: profile could not be saved.
    """
    self._ValidateProfile()
    try:
      plistlib.writePlist(self._profile, path)
    except (IOError, TypeError) as e:
      raise ProfileSaveError('The profile could not be saved: %s' % e)

  def Install(self, sudo_password=None):
    """Install the profile.

    Args:
      sudo_password: str, the password to use for installing the profile.

    Raises:
      ProfileInstallationError: profile failed to install.
      ProfileValidationError: profile data was not valid.
      ProfileSaveError: profile could not be saved.
    """
    self._ValidateProfile()

    with tempfile.NamedTemporaryFile(suffix='.mobileconfig',
                                     prefix='profile_') as f:
      temp_file = f.name

      self.Save(temp_file)
      command = [CMD_PROFILES, '-I', '-F', temp_file]

      try:
        (stdout, stderr, status) = gmacpyutil.RunProcess(
            command, sudo=sudo_password, sudo_password=sudo_password)
      except gmacpyutil.GmacpyutilException as e:
        raise ProfileInstallationError('Profile installation failed!\n%s' % e)

      if status:
        raise ProfileInstallationError('Profile installation failed!\n'
                                       '%s, %s, %s' % (stdout, stderr, status))


class NetworkProfile(Profile):
  """Represents a configuration profile containing network settings."""

  def __init__(self, username):
    """Initializes a network configuration profile with no payloads.

    Args:
      username: str, the username associated with this profile.
    """
    super(NetworkProfile, self).__init__()

    self._username = username
    self._auth_cert = None
    self._anchor_certs = []
    self._trusted_servers = []

    self.Set(PAYLOADKEYS_DISPLAYNAME, 'Network Profile (%s)' % self._username)
    self.Set(PAYLOADKEYS_DESCRIPTION, 'Network authentication settings')
    self.Set(PAYLOADKEYS_IDENTIFIER, NETWORK_PROFILE_ID)
    self.Set(PAYLOADKEYS_ORG, ORGANIZATION_NAME)
    self.Set(PAYLOADKEYS_SCOPE, ['System', 'User'])
    self.Set(PAYLOADKEYS_TYPE, 'Configuration')
    self.Set(PAYLOADKEYS_CONTENT, [])

  def _GenerateID(self, suffix):
    """Generates a unique PayloadIdentifier for a given suffix."""
    return '%s.%s' % (self.Get(PAYLOADKEYS_IDENTIFIER), suffix)

  def AddMachineCertificate(self, certificate, private_key):
    """Adds a machine certificate payload to the profile.

    Args:
      certificate: str, PEM-formatted certificate.
      private_key: str, PEM-formatted private key.

    Raises:
      CertificateError: there was an error processing the certificate/key
    """
    try:
      cert = certs.Certificate(certificate)

      pkcs12 = crypto.PKCS12Type()
      pkcs12.set_certificate(crypto.load_certificate(
          crypto.FILETYPE_PEM, certificate))
      pkcs12.set_privatekey(crypto.load_privatekey(
          crypto.FILETYPE_PEM, private_key))
    except (certs.CertError, crypto.Error) as e:
      raise CertificateError(e)

    payload = {PAYLOADKEYS_IDENTIFIER: self._GenerateID('machine_cert'),
               PAYLOADKEYS_TYPE: 'com.apple.security.pkcs12',
               PAYLOADKEYS_DISPLAYNAME: cert.subject_cn,
               'Password': cert.osx_fingerprint}

    try:
      payload[PAYLOADKEYS_CONTENT] = plistlib.Data(
          pkcs12.export(cert.osx_fingerprint))
    except crypto.Error as e:
      raise CertificateError(e)

    # Validate payload to generate its UUID
    ValidatePayload(payload)
    self._auth_cert = payload.get(PAYLOADKEYS_UUID)
    self.AddPayload(payload)

  def AddAnchorCertificate(self, certificate):
    """Adds a certificate payload to the profile for server identification.

    Args:
      certificate: str, PEM-formatted certificate.

    Raises:
      CertificateError: there was an error processing the certificate
    """
    try:
      cert = certs.Certificate(certificate)
    except certs.CertError as e:
      raise CertificateError(e)

    payload = {PAYLOADKEYS_IDENTIFIER: self._GenerateID(cert.osx_fingerprint),
               PAYLOADKEYS_TYPE: 'com.apple.security.pkcs1',
               PAYLOADKEYS_DISPLAYNAME: cert.subject_cn,
               PAYLOADKEYS_CONTENT: plistlib.Data(certificate)}

    # Validate payload to generate its UUID
    ValidatePayload(payload)
    self._anchor_certs.append(payload.get(PAYLOADKEYS_UUID))
    self.AddPayload(payload)

  def AddTrustedServer(self, server_dn):
    """Adds a server to the trusted servers list.

    Args:
      server_dn: str, a server's DNS name.
    """
    self._trusted_servers.append(server_dn)

  def AddNetworkPayload(self, ssid):
    """Adds a network payload to the profile.

    If the SSID specified is 'wired' a wired payload will be created.

    NOTE: If you intend to use |AddMachineCertifcate|, |AddAnchorCertifcate| or
    |AddTrustedServer| then you must call them before this method or they won't
    take effect.

    Args:
      ssid: str, the SSID to create a payload for.
    """
    payload = {'AutoJoin': True,
               'SetupModes': ['System', 'User'],
               'PayloadCertificateUUID': self._auth_cert}

    if ssid == 'wired':
      payload[PAYLOADKEYS_DISPLAYNAME] = 'Wired'
      payload[PAYLOADKEYS_IDENTIFIER] = self._GenerateID('wired')
      payload[PAYLOADKEYS_TYPE] = 'com.apple.firstactiveethernet.managed'
      payload['EncryptionType'] = 'Any'
      payload['Interface'] = 'FirstActiveEthernet'
    else:
      payload[PAYLOADKEYS_DISPLAYNAME] = ssid
      payload[PAYLOADKEYS_IDENTIFIER] = self._GenerateID('ssid.%s' % ssid)
      payload[PAYLOADKEYS_TYPE] = 'com.apple.wifi.managed'
      payload['EncryptionType'] = 'WPA'
      payload['Interface'] = 'BuiltInWireless'
      payload['SSID_STR'] = ssid

    eap_client_config = {}
    eap_client_config['AcceptEAPTypes'] = [13,]
    eap_client_config['PayloadCertificateAnchorUUID'] = self._anchor_certs
    eap_client_config['TLSTrustedServerNames'] = self._trusted_servers
    eap_client_config['TLSAllowTrustExceptions'] = False
    payload['EAPClientConfiguration'] = eap_client_config

    self.AddPayload(payload)
