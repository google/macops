"""Module to manipulate certificates in an OS X Keychain, and related functions.

Importing this will run LoginKeychain(), which tries to determine the importing
user's login keychain and sets the global variable login_keychain accordingly.
"""

import datetime
import logging
import operator
import os
import re
import shutil
import tempfile
from . import gmacpyutil
from . import getauth


CMD_OPENSSL = '/usr/bin/openssl'
CMD_SECURITY = '/usr/bin/security'
PEM_HEADER = '-----BEGIN CERTIFICATE-----'
PEM_FOOTER = '-----END CERTIFICATE-----'
OPENSSL_DATETIME_FORMAT = '%b %d %H:%M:%S %Y %Z'
SYSTEM_KEYCHAIN = '/Library/Keychains/System.keychain'
login_keychain = None


class Error(Exception):
  """Base error class."""


class CertError(Error):
  """Module specific exception class."""


class KeychainError(Error):
  """Module specific exception class."""


class Certificate(object):
  """Basic certificate object.

  The Certificate constructor accepts a string of PEM-encoded data. The object
  will populate with attributes decoded from the PEM.

  Certificate objects will have these read-only attributes:
  certhash        hash of the certificate's subject name
  subject         string representation of the certificate's full subject
  subject_cn      the CN of the subject
  serial          string representation of the certificate's serial number
  issuer          string representation of the certificate's full issuer
  issuer_cn       the CN of the issuer
  startdate       list, the notBefore date and a datettime object of the same
  enddate         list, the notAfter date and a datettime object of the same
  fingerprint     digest of the DER encoded version of the whole certificate
  osx_fingerprint fingerprint with the ':' removed

  .. and may have this read-only attribute:
  email           email addresses

  Attributes:
    pem: str, PEM-encoded data
  """

  def __init__(self, pem):
    self.pem = pem
    self._ParsePEMCertificate(pem)

  def get(self, key):  # pylint: disable=g-bad-name
    return self.__dict__.get(key, None)


  def _ParsePEMCertificate(self, pem):
    """Reads data from PEM encoded certificate.

    This method take a PEM-encoded certificate and parses it with openssl x509.
    It adds attributes to the object from the parsed output. We feed the PEM
    data though openssl x509 once, with a given order of requested attributes,
    and then parse the output to retrieve the attributes.

    For issuer and subject, the output is "<attribute>= <value>", and we set the
    attribute to <value>.
    For issuer_cn and subject_cn, we get "<attribute>= /X=ZZ/CN=VALUE" and
    set <attribute>_cn VALUE. If the CN is not where we expect, don't set the
    attribute.
    For fingerprint, the output is "SHA1 Fingerprint=fi:ng:er:pr:in:tt", and we
    set fingerprint to "fi:ng:er:pr:in:tt" and osx_fingerprint to
    "fingerprintt".
    For startdate and enddate, we get "notAfter=Apr 29 18:09:17 2036 GMT" and
    make a list. Index 0 has the full date string, index 1 is a datetime object
    parsed from the string. If the string is in an unknown format, index 1 will
    be None.
    For hash, no parsing is needed as the output is just the hash.
    For email, we join up all the remaining lines of output and add them.

    Args:
      pem: str, PEM-encoded data

    Raises:
      CertError: unable to get certificate data
    """
    command = [CMD_OPENSSL, 'x509', '-sha1', '-nameopt', 'compat', '-noout']
    attrs = ['hash', 'subject', 'issuer', 'startdate', 'enddate', 'fingerprint',
             'serial', 'email']

    for attr in attrs:
      command.extend(['-%s' % attr])
    (stdout, stderr, returncode) = gmacpyutil.RunProcess(command, pem)
    if returncode:
      raise CertError('Unable to retrieve data for certificates: %s' % stderr)
    output = stdout.splitlines()
    for index, attr in enumerate(attrs):
      if attr in ('issuer', 'subject'):
        name = output[index].split(' ', 1)[1]
        self.__dict__[attr] = name
        try:
          self.__dict__[''.join([attr, '_cn'])] = (
              name.split('/')[-1].split('=')[1])
        except IndexError:
          pass
      elif attr == 'fingerprint':
        self.__dict__['fingerprint'] = output[index].split('=', 1)[1]
        self.__dict__['osx_fingerprint'] = (
            re.sub(':', '', output[index].split('=', 1)[1]))
      elif attr in ('enddate', 'startdate'):
        datestring = output[index].split('=')[1]
        try:
          dateobject = datetime.datetime.strptime(datestring,
                                                  OPENSSL_DATETIME_FORMAT)
        except ValueError:
          dateobject = None
        self.__dict__[attr] = [datestring, dateobject]
      elif attr == 'hash':
        self.__dict__['certhash'] = output[index]
      elif attr == 'serial':
        self.__dict__[attr] = output[index].split('=')[1]
      elif attr == 'email':
        self.__dict__[attr] = ''.join(output[index:])


def LoginKeychain():
  """Gets the current user's login keychain and updates login_keychain."""
  global login_keychain  # pylint: disable=global-statement
  if os.uname()[0] == 'Linux':
    return
  if os.getuid() == 0:
    logging.debug('Root has no access to login keychain.')
    return
  stdout, stderr, rc = gmacpyutil.RunProcess([CMD_SECURITY, 'login-keychain'])
  if rc == 0:
    login_keychain = stdout.strip(' \n"')
  else:
    logging.error('Unable to determine login keychain: %s', stderr)
    login_keychain = None


def _GetCertificates(keychain=None):
  """Gets all certificates in a given keychain.

  On a newly-created keychain, searching for all certs gives a
  CSSMERR_DL_INVALID_RECORDTYPE error and sets the returncode to 9. Just
  assume there are no certs in this case.

  Args:
    keychain: str, keychain to look in

  Yields:
    Certificate objects

  Raises:
    CertError: could not search for certficates
    StopIteration: no more matching certs
  """
  cmd = [CMD_SECURITY, 'find-certificate', '-a', '-p']

  if keychain is not None:
    cmd.extend([keychain])

  (stdout, stderr, returncode) = gmacpyutil.RunProcess(cmd)
  if returncode == 0:
    allcerts = stdout.split(PEM_FOOTER)
    allcerts.pop()
    for cert in allcerts:
      pem = '%s\n%s\n%s' % (PEM_HEADER, '\n'.join(cert.split()[2:]), PEM_FOOTER)
      try:
        yield Certificate(pem)
      except CertError, e:
        logging.info('Encountered an unparseable certificate, continuing.')
        logging.debug(str(e))
        continue
  elif returncode == 9:
    raise StopIteration
  else:
    raise CertError('Unable to get all certificates. Exit code: %s, '
                    'Output: %s' % (returncode, stderr))


def DeleteCert(osx_fingerprint, keychain=None, gui=False,
               password=None):
  """Deletes a certificate by SHA1 hash.

  Args:
    osx_fingerprint: str, SHA-1 hash (uppercase, no colons)
    keychain: str, keychain to delete from; if unset the default keychain is
              used (normally the login keychain)
    gui: True if running in a gui context
    password: The user's password if already known.

  Raises:
    CertError: unable to delete certificate
  """
  sudo, sudo_pass = _GetSudoContext(keychain,
                                    gui=gui,
                                    password=password)
  cmd = [CMD_SECURITY, 'delete-certificate', '-Z', osx_fingerprint]
  if keychain:
    cmd.append(keychain)
  (unused_stdout, stderr, returncode) = (
      gmacpyutil.RunProcess(cmd, sudo=sudo, sudo_password=sudo_pass))

  if returncode:
    raise CertError('Unable to delete certificate: %s' % stderr)


def FindCertificates(subject=None, subject_cn=None, issuer=None, issuer_cn=None,
                     startdate=None, enddate=None, certhash=None,
                     fingerprint=None, email=None, keychain=None):
                     # pylint: disable=unused-argument
  """Finds certificates by attribute.

  Multiple attributes are ANDed together.

  To do this, we get a list of all matching certs with a list comprehension,
  then run a reduce multiplying all results. Since bools multiply as ints, a
  False means multiply by 0 so any False match makes the whole thing False.

  Args:
    subject: str, find certificate by full subject
    subject_cn: str, find certificate by subject CN
    issuer: str, find certificate by issuer
    issuer_cn: str, find certificate by issuer CN
    startdate: str, find certificate by notBefore date
    enddate: str, find certificate by notAfter date
    certhash: str, find certificate by SHA-1 hash of suject name
    fingerprint: str, find certificate by fingerprint
    email: str, find certificates by email address
    keychain: str, which keychain to look in
  Returns:
    List of matching Certificate objects
  Raises:
    CertError: could not search for certificates
  """

  attrs = vars().keys()[:]
  attrs.remove('keychain')
  allcerts = _GetCertificates(keychain=keychain)
  matchedcerts = []

  for cert in allcerts:
    if reduce(operator.mul,  # pylint: disable=bad-builtin
              [(cert.get(k) == eval(k))  # pylint: disable=eval-used
               for k in attrs
               if eval(k)],  # pylint: disable=eval-used
              True):
      matchedcerts.append(cert)
  return matchedcerts


def CertificateExpired(cert, expires=0):
  """Checks a given certificate for expiry.

  Args:
    cert: Certificate object
    expires: int, the number of seconds to check for expiry. 0 means now
  Returns:
    boolean, whether the certificate will expire in expires seconds
  Raises:
    CertError: cert is a mandatory argument
    CertError: cert is not a PEM encoded x509 cert
  """
  expiry = datetime.datetime.today() + datetime.timedelta(seconds=expires)
  # enddate is a list of [str, (datetime|None)], we want the datetime object
  cert_end = cert.enddate[1]
  if cert_end:
    return expiry > cert_end
  else:
    raise CertError('Certificate has a malformed enddate.')




def VerifyIdentityPreference(subject_cn, service):
  """Verify a TLS identity preference exists for a given cert.

  Args:
    subject_cn: str, subject CN of cert to verify matches preference
    service: str, Service for which identity should be verified

  Returns:
    Bool: true if identity exists and matches subject_cn
  """
  cmd = [CMD_SECURITY, 'get-identity-preference', '-s', service, '-c']
  (stdout, unused_stderr, rc) = gmacpyutil.RunProcess(cmd)

  if rc:
    return False

  search_string = '"labl"<blob>="%s"' % subject_cn
  return search_string in stdout


def ClearIdentityPreferences(sudo_password=None):
  """Deletes existing TLS identity preferences.

  There's no way to list all identity preferences without knowing the full name
  so it's necessary to dump all keychains and search for the desired
  preferences.  All of the desired preferences have a line in the output like
  the following:

      "svce"<blob>="com.apple.network.eap.user.identity.wlan.ssid.<SSID>"

      or

      "svce"<blob>="com.apple.network.eap.system.identity.profileid.B7392191"

  Args:
    sudo_password: str, optional, for removing from system keychain
  """
  service_re = re.compile(r'\s*"svce"<blob>="(com\.apple\.network\.eap\..*)"')

  cmd = [CMD_SECURITY, 'dump-keychain']
  (keychain_content, _, _) = gmacpyutil.RunProcess(cmd)

  for line in keychain_content.splitlines():
    matches = service_re.match(line)
    if matches:
      cmd = [CMD_SECURITY, 'set-identity-preference',
             '-n', '-s', matches.group(1)]
      logging.debug('Removing identity preference: %s', cmd)
      gmacpyutil.RunProcess(cmd, sudo=bool(sudo_password),
                            sudo_password=sudo_password)


def CreateIdentityPreference(issuer_cn, service, keychain=login_keychain):
  """Create a TLS Identity preference for a given cert.

  Args:
    issuer_cn: str, CN of issuer of cert to create preference for
    service: str, Service for which identity should be preferred
    keychain: str, keychain to create the preference entry in

  Raises:
    CertError: if there is more than one matching cert
    CertError: if the preference can't be created
  """
  logging.debug('Creating TLS identity preference for %s in keychain %s',
                service, keychain)

  existing_certs = FindCertificates(issuer_cn=issuer_cn, keychain=keychain)
  if len(existing_certs) != 1:
    raise CertError('More or less than one matching certificate '
                    'in the keychain.')

  command = [CMD_SECURITY, 'set-identity-preference', '-Z',
             existing_certs[0].osx_fingerprint, '-s', service, keychain]
  logging.debug('Command: %s', command)
  (stdout, stderr, status) = gmacpyutil.RunProcess(command)
  logging.debug('Identity preference creation output: %s', stdout)
  if status:
    raise CertError(stdout, stderr)


def _GetSudoContext(keychain, gui=False, password=None):
  """Determine if we need sudo and get a sudo password if necessary.

  TODO(user): handle shadow admin

  Args:
    keychain: path to keychain
    gui: True if we are running from the gui
    password: The user's password.

  Returns:
    sudo: True if this is the system keychain and we will need sudo
    sudo_pass: sudo password if necessary, or None if not necessary or not
               available.
  """

  sudo_pass = None
  if keychain == SYSTEM_KEYCHAIN:

    # If we're given a password we should test if it works for sudo.
    if password:
      (unused_stdout, unused_stderr, return_code) = gmacpyutil.RunProcess(
          ['-v'], sudo=True, sudo_password=password)
      if return_code == 0:
        return keychain == SYSTEM_KEYCHAIN, password

    if gui:
      # If we arrive here it means the password doesn't work for sudo, if this
      # is a gui context, try and get a passwd, otherwise let sudo do the
      # prompting in the terminal
      try:
        sudo_pass = getauth.GetPassword(gui=gui)
      except (EOFError, KeyboardInterrupt):
        logging.exception('Could not get sudo password from GUI prompt')
        raise
  return keychain == SYSTEM_KEYCHAIN, sudo_pass


def InstallPrivateKeyInKeychain(private_key, keychain=login_keychain,
                                trusted_app_path=None, passphrase=None,
                                gui=False, password=None):
  """Install the private key into the keychain.

  Args:
    private_key: str, private key in PEM format
    keychain: str, keychain to install cert and key into
    trusted_app_path: list of strings, optional applications that can
                      access private key.  If None, trust is set Open
    passphrase: str, optional passphrase the private key is encrypted with
    gui: True if running in a gui context
    password: The user's password if already known.

  Raises:
    KeychainError: if there are any errors installing
  """
  sudo, sudo_pass = _GetSudoContext(keychain,
                                    gui=gui,
                                    password=password)

  temp_dir = tempfile.mkdtemp(prefix='cert_pkey_install')
  key_file = '%s/private.key' % temp_dir

  try:
    key_handle = open(key_file, 'w')
    key_handle.write(private_key)
    key_handle.close()

    logging.info('Installing downloaded key into the %s keychain', keychain)

    command = [CMD_SECURITY, 'import', key_file, '-x', '-k', keychain]
    if passphrase:
      command.extend(['-P', passphrase])
    if trusted_app_path:
      for trusted_app in trusted_app_path:
        if os.path.exists(trusted_app):
          command.extend(['-T', trusted_app])
    else:
      command.extend(['-A'])
    logging.debug('Command: %s', command)
    (stdout, stderr, status) = gmacpyutil.RunProcess(command, sudo=sudo,
                                                     sudo_password=sudo_pass)
    logging.debug('Private key installation output: %s', stdout)
    if status:
      raise KeychainError(stdout, stderr)
  except IOError:
    raise KeychainError('Could not write to temp files in %s' % temp_dir)
  finally:
    shutil.rmtree(temp_dir)


def InstallCertInKeychain(pem, private_key, keychain=login_keychain,
                          trusted_app_path=None, passphrase=None, gui=False,
                          password=None):
  """Install the certificate and private key into the keychain.

  Args:
    pem: str, the certificate in PEM format
    private_key: str, private key in PEM format
    keychain: str, keychain to install cert and key into
    trusted_app_path: list of strings, optional applications that can
                      access private key; a single string can be used for
                      backwards compatibility.  If None, trust is set Open
    passphrase: str, optional passphrase the private key is encrypted with
    gui: True if running in a gui context
    password: The user's password if already known.

  Raises:
    KeychainError: if there are any errors installing
  """
  sudo, sudo_pass = _GetSudoContext(keychain,
                                    gui=gui,
                                    password=password)

  if type(trusted_app_path) == str:
    # Convert bare strings to a list for backwards compatibility
    trusted_app_path = [trusted_app_path]

  # TODO(user): Make this function just install the certificate and not handle
  # any key installation at all.
  InstallPrivateKeyInKeychain(private_key, keychain=keychain,
                              trusted_app_path=trusted_app_path,
                              passphrase=passphrase, gui=gui,
                              password=sudo_pass)

  temp_dir = tempfile.mkdtemp(prefix='cert_install')
  cert_file = '%s/certificate.cer' % temp_dir

  try:
    cert_handle = open(cert_file, 'w')
    cert_handle.write(pem)
    cert_handle.close()

    logging.info('Installing downloaded certificate into the %s keychain',
                 keychain)

    command = [CMD_SECURITY, 'import', cert_file, '-x', '-k', keychain]
    logging.debug('Command: %s', command)
    (stdout, stderr, status) = gmacpyutil.RunProcess(command, sudo=sudo,
                                                     sudo_password=sudo_pass)
    logging.debug('Certificate installation output: %s', stdout)
    if status:
      raise KeychainError(stdout, stderr)
  except IOError:
    raise KeychainError('Could not write to temp files in %s' % temp_dir)
  finally:
    shutil.rmtree(temp_dir)


def RemoveIssuerCertsFromKeychain(issuer_cn, keychain=login_keychain, gui=False,
                                  password=None):
  """Removes all certificates issued from a given CN from the keychain.

  DeleteCert tries to raise privileges to allow deletions from the System
  keychain, so we try and log if it fails.

  Args:
    issuer_cn: str, the certificate's issuer's CN
    keychain: str, the path to the keychain to remove from
    gui: True if running in a gui context
    password: The user's password if already known.

  Raises:
    KeychainError: if there are any errors removing

  Returns:
    Array of deleted serial numbers
  """
  if keychain is None:
    return []

  existing_certs = FindCertificates(issuer_cn=issuer_cn, keychain=keychain)
  deleted_certs = []
  for cert in existing_certs:
    try:
      logging.debug('Removing cert with fingerprint %s from %s',
                    cert.osx_fingerprint, keychain)
      DeleteCert(cert.osx_fingerprint, keychain=keychain, gui=gui,
                 password=password)
      deleted_certs.append(cert.serial)
    except CertError, e:
      logging.error('Cannot delete old certificate: %s', str(e))
  return deleted_certs


def GenerateCSR(subject, rsa_bits=2048, passphrase=None):
  """Generate a Certificate Signing Request.

  Args:
    subject: str, subject for csr
    rsa_bits: int, optional number of bits
    passphrase: str, optional passphrase to encrypt private key with

  Returns:
    tuple, cert and private key in PEM format and passphrase

  Raises:
    CertError: Error generating a CSR.
  """
  command = [CMD_OPENSSL, 'genrsa']
  env = {}
  if passphrase:
    command.extend(['-des3', '-passout', 'env:PASSPHRASE'])
    env['PASSPHRASE'] = passphrase
  command.extend([str(rsa_bits)])

  logging.debug('command: %s', command)
  logging.debug('environment: %s', env.keys())
  (stdout, stderr, status) = gmacpyutil.RunProcess(command, env=env)
  logging.debug('Private key generation output: %s', stdout)
  if status:
    raise CertError('Error creating private key: %s' % stderr)
  private_key = stdout

  command = [CMD_OPENSSL, 'req', '-new', '-subj', subject, '-key',
             '/dev/stdin']
  if passphrase:
    command.extend(['-passin', 'env:PASSPHRASE'])
    env['PASSPHRASE'] = passphrase

  logging.debug('command: %s', command)
  logging.debug('environment: %s', env.keys())
  logging.debug('stdinput: %s', private_key)
  (csr, stderr, status) = gmacpyutil.RunProcess(command, private_key, env=env)
  logging.debug('CSR generation output: %s', csr)
  if status:
    raise CertError('Error creating CSR: %s' % stderr)

  return (csr, private_key, passphrase)


LoginKeychain()
