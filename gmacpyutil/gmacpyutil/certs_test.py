"""Unit tests for certs module."""

import __builtin__
import datetime


import mox
import stubout

from google.apputils import app
from google.apputils import basetest

import certs


class CertificateTest(mox.MoxTestBase):
  """Test Certificate object functions."""

  def setUp(self):
    mox.MoxTestBase.setUp(self)
    self.stubs = stubout.StubOutForTesting()

  def tearDown(self):
    self.mox.UnsetStubs()
    self.stubs.UnsetAll()

  def StubSetup(self):
    """Set up stubs."""
    self.mox.StubOutWithMock(certs.gmacpyutil, 'RunProcess')

  def testget(self):  # pylint: disable=g-bad-name
    """Test get."""
    self.StubSetup()
    self.mox.StubOutWithMock(certs.Certificate, '_ParsePEMCertificate')

    certs.Certificate._ParsePEMCertificate('pem').AndReturn(None)

    self.mox.ReplayAll()
    c = certs.Certificate('pem')
    c.key = 'key'
    self.assertEqual('key', c.get('key'))
    self.assertEqual(None, c.get('missing'))
    self.mox.VerifyAll()

  def testParsePEMCertificateFails(self):
    """Test _ParsePEMCertificate."""
    self.StubSetup()
    pem = 'pem'
    cmd = [certs.CMD_OPENSSL, 'x509', '-sha1', '-nameopt', 'compat', '-noout',
           '-hash', '-subject', '-issuer', '-startdate', '-enddate',
           '-fingerprint', '-serial', '-email']
    certs.gmacpyutil.RunProcess(cmd, pem).AndReturn(('', '', 1))
    self.mox.ReplayAll()
    self.assertRaises(certs.CertError, certs.Certificate, pem)
    self.mox.VerifyAll()

  def testParsePEMCertificateWithoutEmail(self):
    """Test _ParsePEMCertificate."""
    self.StubSetup()
    pem = 'pem'
    date = 'Oct 31 12:34:56 1971 GMT'
    dt_date = datetime.datetime(1971, 10, 31, 12, 34, 56)
    parsed = {'subject': 'subject', 'issuer': 'issuer', 'certhash': 'hash',
              'startdate': [date, dt_date], 'enddate': [date, dt_date],
              'fingerprint': 'fing:er:print', 'osx_fingerprint': 'fingerprint',
              'email': '', 'serial': '87654321', 'pem': pem}
    cmd = [certs.CMD_OPENSSL, 'x509', '-sha1', '-nameopt', 'compat', '-noout',
           '-hash', '-subject', '-issuer', '-startdate', '-enddate',
           '-fingerprint', '-serial', '-email']
    output = ('hash\nsubject= subject\nissuer= issuer\nnotBefore=%s\n'
              'notAfter=%s\nSHA1 Fingerprint=fing:er:print\nserial=87654321\n'
              % (date, date))
    certs.gmacpyutil.RunProcess(cmd, pem).AndReturn((output, '', 0))

    self.mox.ReplayAll()
    c = certs.Certificate(pem)
    self.assertEqual(parsed, c.__dict__)
    self.mox.VerifyAll()

  def testParsePEMCertificateWithEmail(self):
    """Test _ParsePEMCertificate."""
    self.StubSetup()
    pem = 'pem'
    date = 'Oct 31 12:34:56 1971 GMT'
    dt_date = datetime.datetime(1971, 10, 31, 12, 34, 56)
    parsed = {'subject': 'subject', 'issuer': 'issuer', 'certhash': 'hash',
              'startdate': [date, dt_date], 'enddate': [date, dt_date],
              'fingerprint': 'fing:er:print', 'osx_fingerprint': 'fingerprint',
              'serial': '87654321', 'email': 'user@company.com', 'pem': pem}
    cmd = [certs.CMD_OPENSSL, 'x509', '-sha1', '-nameopt', 'compat', '-noout',
           '-hash', '-subject', '-issuer', '-startdate', '-enddate',
           '-fingerprint', '-serial', '-email']
    output_with_email = ('hash\nsubject= subject\nissuer= issuer\nnotBefore=%s'
                         '\nnotAfter=%s\nSHA1 Fingerprint=fing:er:print\n'
                         'serial=87654321\nuser@company.com\n' % (date, date))
    certs.gmacpyutil.RunProcess(cmd, pem).AndReturn((output_with_email, '', 0))

    self.mox.ReplayAll()
    c = certs.Certificate(pem)
    self.assertEqual(parsed, c.__dict__)
    self.mox.VerifyAll()

  def testParsePEMCertificateWithMalformedDate(self):
    """Test _ParsePEMCertificate."""
    self.StubSetup()
    pem = 'pem'
    parsed = {'subject': 'subject', 'issuer': 'issuer', 'certhash': 'hash',
              'startdate': ['bad date', None], 'enddate': ['bad date', None],
              'fingerprint': 'fing:er:print', 'osx_fingerprint': 'fingerprint',
              'email': '', 'serial': '87654321', 'pem': pem}
    cmd = [certs.CMD_OPENSSL, 'x509', '-sha1', '-nameopt', 'compat', '-noout',
           '-hash', '-subject', '-issuer', '-startdate', '-enddate',
           '-fingerprint', '-serial', '-email']
    output_bad_date = ('hash\nsubject= subject\nissuer= issuer\nnotBefore=bad '
                       'date\nnotAfter=bad date\nSHA1 Fingerprint='
                       'fing:er:print\nserial=87654321\n')
    certs.gmacpyutil.RunProcess(cmd, pem).AndReturn((output_bad_date, '', 0))

    self.mox.ReplayAll()
    c = certs.Certificate(pem)
    self.assertEqual(parsed, c.__dict__)
    self.mox.VerifyAll()


class CertsModuleTest(mox.MoxTestBase):
  """Test certs module-level functions."""

  def setUp(self):
    mox.MoxTestBase.setUp(self)
    self.stubs = stubout.StubOutForTesting()

  def tearDown(self):
    self.mox.UnsetStubs()
    self.stubs.UnsetAll()

  def StubSetup(self):
    """Set up stubs."""
    self.mox.StubOutWithMock(certs.gmacpyutil, 'RunProcess')
    self.mox.StubOutWithMock(certs.logging, 'info')
    self.mox.StubOutWithMock(certs.logging, 'debug')
    self.mox.StubOutWithMock(certs.logging, 'error')
    self.mox.StubOutWithMock(certs.os, 'getuid')
    self.mox.StubOutWithMock(certs.os, 'uname')
    self.mox.StubOutWithMock(certs.os.path, 'exists')
    self.mox.StubOutWithMock(certs.shutil, 'rmtree')
    self.mox.StubOutWithMock(certs.tempfile, 'mkdtemp')
    self.mox.StubOutWithMock(__builtin__, 'open')
    certs.login_keychain = None

  def testLoginKeychainAsRoot(self):
    """Test LoginKeychainAsRoot."""
    self.StubSetup()
    certs.os.uname().AndReturn(('Darwin'))
    certs.os.getuid().AndReturn(0)
    certs.logging.debug('Root has no access to login keychain.')
    self.mox.ReplayAll()
    # running as root
    certs.LoginKeychain()
    self.assertEqual(None, certs.login_keychain)
    self.mox.VerifyAll()

  def testLoginKeychain(self):
    """Test LoginKeychain."""
    self.StubSetup()
    command = [certs.CMD_SECURITY, 'login-keychain']
    # security returns successfully
    certs.os.uname().AndReturn(('Darwin'))
    certs.os.getuid().AndReturn(1337)
    certs.gmacpyutil.RunProcess(command).AndReturn(('out\n', 'err\n', 0))
    # security fails
    certs.os.uname().AndReturn(('Darwin'))
    certs.os.getuid().AndReturn(1337)
    certs.gmacpyutil.RunProcess(command).AndReturn(('out\n', 'err\n', 1))
    certs.logging.error(
        'Unable to determine login keychain: %s', 'err\n').AndReturn(None)

    self.mox.ReplayAll()
    # security returns successfully
    certs.LoginKeychain()
    self.assertEqual('out', certs.login_keychain)
    # security fails
    certs.LoginKeychain()
    self.assertEqual(None, certs.login_keychain)
    self.mox.VerifyAll()

  def testGetCertificatesNoKeychainSuccess(self):
    """Test _GetCertificates no keychain specified, successful search."""
    self.StubSetup()
    self.mox.StubOutWithMock(certs, 'Certificate')
    command = [certs.CMD_SECURITY, 'find-certificate', '-a', '-p']
    cert = '%s\n%s\n%s\n' % (certs.PEM_HEADER, 'cert_body', certs.PEM_FOOTER)
    output = cert * 2
    certs.gmacpyutil.RunProcess(command).AndReturn((output, '', 0))
    certs.Certificate(cert.strip()).AndReturn('parsed cert')
    certs.Certificate(cert.strip()).AndReturn('parsed cert')

    self.mox.ReplayAll()
    self.assertEqual(['parsed cert', 'parsed cert'],
                     list(certs._GetCertificates()))
    self.mox.VerifyAll()

  def testGetCertificatesNoKeychainCertError(self):
    """Test _GetCertificates with CertError from Certificate class."""
    self.StubSetup()
    self.mox.StubOutWithMock(certs, 'Certificate')
    command = [certs.CMD_SECURITY, 'find-certificate', '-a', '-p']
    cert = '%s\n%s\n%s\n' % (certs.PEM_HEADER, 'cert_body', certs.PEM_FOOTER)
    output = cert * 2
    certs.gmacpyutil.RunProcess(command).AndReturn((output, '', 0))
    certs.Certificate(cert.strip()).AndRaise(certs.CertError('err'))
    certs.logging.info('Encountered an unparseable certificate, continuing.')
    certs.logging.debug('err')
    certs.Certificate(cert.strip()).AndReturn('parsed cert')

    self.mox.ReplayAll()
    self.assertEqual(['parsed cert'], list(certs._GetCertificates()))
    self.mox.VerifyAll()

  def testGetCertificatesNewKeychain(self):
    """Test _GetCertificates with a newly-created keychain."""
    self.StubSetup()
    self.mox.StubOutWithMock(certs, 'Certificate')
    command = [certs.CMD_SECURITY, 'find-certificate', '-a', '-p']
    certs.gmacpyutil.RunProcess(command).AndReturn(('', '', 9))

    self.mox.ReplayAll()
    self.assertEqual([], list(certs._GetCertificates()))
    self.mox.VerifyAll()

  def testGetCertificatesNoKeychainSearchFailed(self):
    """Test _GetCertificates, no keychain, search failed."""
    self.StubSetup()
    self.mox.StubOutWithMock(certs, 'Certificate')
    command = [certs.CMD_SECURITY, 'find-certificate', '-a', '-p']
    certs.gmacpyutil.RunProcess(command).AndReturn(('', '', 1))

    self.mox.ReplayAll()
    c = certs._GetCertificates()
    self.assertRaises(certs.CertError, c.next)
    self.mox.VerifyAll()

  def testGetCertificatesKeychainSpecifiedSuccess(self):
    """Test _GetCertificates with keychain specified."""
    self.StubSetup()
    self.mox.StubOutWithMock(certs, 'Certificate')
    command = [certs.CMD_SECURITY, 'find-certificate', '-a', '-p']
    cert = '%s\n%s\n%s\n' % (certs.PEM_HEADER, 'cert_body', certs.PEM_FOOTER)
    output = cert * 2
    command = [certs.CMD_SECURITY, 'find-certificate', '-a', '-p', 'keychain']
    certs.gmacpyutil.RunProcess(command).AndReturn((output, '', 0))
    certs.Certificate(cert.strip()).AndReturn('parsed cert')
    certs.Certificate(cert.strip()).AndReturn('parsed cert')

    self.mox.ReplayAll()
    self.assertEqual(['parsed cert', 'parsed cert'],
                     list(certs._GetCertificates(keychain='keychain')))
    self.mox.VerifyAll()

  def testDeleteCert(self):
    """Test DeleteCert."""
    self.StubSetup()
    command = [certs.CMD_SECURITY, 'delete-certificate', '-Z', 'f']
    # Successful deletion
    certs.gmacpyutil.RunProcess(command,
                                sudo=False,
                                sudo_password=None).AndReturn(('out', 'err', 0))
    # Unsuccessful deletion
    certs.gmacpyutil.RunProcess(command,
                                sudo=False,
                                sudo_password=None).AndReturn(('out', 'err', 1))
    # Successful deletion, custom keychain
    certs.gmacpyutil.RunProcess(command + ['k'],
                                sudo=False,
                                sudo_password=None).AndReturn(('out', 'err', 0))
    # Successful deletion, system keychain
    certs.gmacpyutil.RunProcess(command + [certs.SYSTEM_KEYCHAIN],
                                sudo=True,
                                sudo_password=None).AndReturn(('out', 'err', 0))

    self.mox.ReplayAll()
    self.assertEqual(None, certs.DeleteCert('f'))
    self.assertRaises(certs.CertError, certs.DeleteCert, 'f')
    self.assertEqual(None, certs.DeleteCert('f', keychain='k'))
    self.assertEqual(None,
                     certs.DeleteCert('f', keychain=certs.SYSTEM_KEYCHAIN))
    self.mox.VerifyAll()

  def testFindCertificates(self):
    """Test FindCertificates."""
    self.StubSetup()
    self.mox.StubOutWithMock(certs, '_GetCertificates')
    allcerts = [{'subject': 's1', 'issuer': 'i1', 'fingerprint': 'f1'},
                {'subject': 's2', 'issuer': 'i1', 'fingerprint': 'f2'},
                {'subject': 's3', 'issuer': 'i2', 'fingerprint': 'f3'}]
    certs._GetCertificates(keychain=None).AndReturn(allcerts)
    certs._GetCertificates(keychain=None).AndReturn(allcerts)
    certs._GetCertificates(keychain=None).AndReturn(allcerts)
    certs._GetCertificates(keychain=None).AndReturn(allcerts)
    certs._GetCertificates(keychain=None).AndReturn(allcerts)
    self.mox.ReplayAll()
    self.assertEqual(allcerts, certs.FindCertificates())
    self.assertEqual(allcerts[0:1], certs.FindCertificates(subject='s1'))
    self.assertEqual(allcerts[0:2], certs.FindCertificates(issuer='i1'))
    self.assertEqual([], certs.FindCertificates(issuer='i3'))
    self.assertEqual([], certs.FindCertificates(subject='s1', issuer='i2'))
    self.mox.VerifyAll()

  def testCertificateExpired(self):
    """Test CertificateExpired."""
    c = self.mox.CreateMockAnything()
    self.mox.ReplayAll()
    expired = datetime.datetime.today() - datetime.timedelta(days=1)
    c.enddate = [None, expired]
    self.assertTrue(certs.CertificateExpired(c))
    unexpired = datetime.datetime.today() + datetime.timedelta(days=1)
    c.enddate = [None, unexpired]
    self.assertFalse(certs.CertificateExpired(c))
    self.mox.VerifyAll()


  def testVerifyIdentityPreference(self):
    """Test VerifyIdentityPreference."""
    self.StubSetup()

    svc = 'com.apple.eap.identity.preference.test'
    sstr = '"labl"<blob>="A820662822C2 20C9D09417C7 :4E6DB011"'
    scn_true = 'A820662822C2 20C9D09417C7 :4E6DB011'
    scn_false = 'B85065212212 F52D6268A281 :6C09A091'

    cmd = [certs.CMD_SECURITY, 'get-identity-preference', '-s', svc, '-c']
    certs.gmacpyutil.RunProcess(cmd).AndReturn((sstr, 'stderr', 0))
    certs.gmacpyutil.RunProcess(cmd).AndReturn((sstr, 'stderr', 0))

    self.mox.ReplayAll()
    self.assertTrue(certs.VerifyIdentityPreference(scn_true, svc))
    self.assertFalse(certs.VerifyIdentityPreference(scn_false, svc))
    self.mox.VerifyAll()

  def testClearIdentityPreferences(self):
    """Test ClearIdentityPreferences."""
    self.StubSetup()

    dump = ('keychain: "/Users/gneagle/Library/Keychains/login.keychain"\n'
            'class: "genp"\n'
            'attributes:\n'
            '    0x00000007 <blob>="com.apple.network.eap.user.identity.wlan"\n'
            '    0x00000008 <blob>=<NULL>\n'
            '    "acct"<blob>="20C9D043F6CF :2EE73EF2 "\n'
            '    "cdat"<timedate>=0x32303133303932353230333031375A00\n'
            '    "crtr"<uint32>="aapl"\n'
            '    "cusi"<sint32>=<NULL>\n'
            '    "desc"<blob>=<NULL>\n'
            '    "gena"<blob>=0x737375690000002087191CA30FC911D4849A000\n'
            '    "icmt"<blob>=<NULL>\n'
            '    "invi"<sint32>=<NULL>\n'
            '    "mdat"<timedate>=0x32303133313030373231303833375A00\n'
            '    "nega"<sint32>=<NULL>\n'
            '    "prot"<blob>=<NULL>\n'
            '    "scrp"<sint32>=0x00000000\n'
            '    "svce"<blob>="com.apple.network.eap.user.identity.wlan.ssid"\n'
            '    "type"<uint32>="iprf"\n'
            'keychain: "/Users/gneagle/Library/Keychains/login.keychain"\n'
            'class: "genp\n"'
            'attributes:\n'
            '    0x00000007 <blob>="com.apple.assistant"\n'
            '    0x00000008 <blob>=<NULL>\n'
            '    "acct"<blob>="675588EC-C24F-4068-88FC-B7BEE228B93C"\n'
            '    "cdat"<timedate>=0x32303133303431313135333335335A00\n'
            '    "crtr"<uint32>=<NULL>\n'
            '    "cusi"<sint32>=<NULL>\n'
            '    "desc"<blob>=<NULL>\n'
            '    "gena"<blob>=<NULL>\n'
            '    "icmt"<blob>=<NULL>\n'
            '    "invi"<sint32>=<NULL>\n'
            '    "mdat"<timedate>=0x32303133313030383134323233325A00\n'
            '    "nega"<sint32>=<NULL>\n'
            '    "prot"<blob>=<NULL>\n'
            '    "scrp"<sint32>=<NULL>\n'
            '    "svce"<blob>="com.apple.assistant"\n'
            '    "type"<uint32>=<NULL>\n')

    cmd = [certs.CMD_SECURITY, 'dump-keychain']
    certs.gmacpyutil.RunProcess(cmd).AndReturn((dump, None, 0))

    cmd = [certs.CMD_SECURITY, 'set-identity-preference', '-n', '-s',
           'com.apple.network.eap.user.identity.wlan.ssid']
    certs.logging.debug('Removing identity preference: %s', cmd)
    certs.gmacpyutil.RunProcess(
        cmd, sudo=False, sudo_password=None).AndReturn((None, None, 0))

    self.mox.ReplayAll()
    certs.ClearIdentityPreferences()
    self.mox.VerifyAll()

  def testCreateIdentityPreference(self):
    """Test CreateIdentityPreference."""
    self.StubSetup()
    self.mox.StubOutWithMock(certs, 'FindCertificates')
    c = self.mox.CreateMockAnything()
    c.osx_fingerprint = 'f'

    # No matching certs found
    certs.logging.debug('Creating TLS identity preference for %s '
                        'in keychain %s', 's', 'k')
    certs.FindCertificates(issuer_cn='i', keychain='k').AndReturn([])
    # Successful ID pref creation
    certs.logging.debug('Creating TLS identity preference for %s '
                        'in keychain %s', 's', 'k')
    certs.FindCertificates(issuer_cn='i', keychain='k').AndReturn([c])
    command = [certs.CMD_SECURITY, 'set-identity-preference', '-Z', 'f',
               '-s', 's', 'k']
    certs.logging.debug('Command: %s', command)
    certs.gmacpyutil.RunProcess(command).AndReturn(('out', 'err', 0))
    certs.logging.debug('Identity preference creation output: %s', 'out')
    # Error creating ID pref
    certs.logging.debug('Creating TLS identity preference for %s '
                        'in keychain %s', 's', 'k')
    certs.FindCertificates(issuer_cn='i', keychain='k').AndReturn([c])
    command = [certs.CMD_SECURITY, 'set-identity-preference', '-Z', 'f',
               '-s', 's', 'k']
    certs.logging.debug('Command: %s', command)
    certs.gmacpyutil.RunProcess(command).AndReturn(('out', 'err', 1))
    certs.logging.debug('Identity preference creation output: %s', 'out')

    self.mox.ReplayAll()
    # No matching certs found
    self.assertRaises(certs.CertError,
                      certs.CreateIdentityPreference, 'i', 's', keychain='k')
    # Successful ID pref creation
    self.assertEquals(None,
                      certs.CreateIdentityPreference('i', 's', keychain='k'))
    # Error creating ID pref
    self.assertRaises(certs.CertError,
                      certs.CreateIdentityPreference, 'i', 's', keychain='k')
    self.mox.VerifyAll()

  def testInstallCertInKeychainFailIOError(self):
    self.StubSetup()

    certs.tempfile.mkdtemp(prefix=mox.IgnoreArg()).AndReturn('tempdir')
    open_file = self.mox.CreateMockAnything()
    open('tempdir/private.key', 'w').AndReturn(open_file)
    open_file.write('key').AndRaise(IOError)
    certs.shutil.rmtree('tempdir').AndReturn(None)

    self.mox.ReplayAll()
    self.assertRaises(certs.KeychainError, certs.InstallCertInKeychain,
                      'cert', 'key', keychain='k')
    self.mox.VerifyAll()

  def WriteFiles(self):
    """Mocks the writing of tempfiles for InstallCertInKeychain."""
    key = self.mox.CreateMockAnything()
    open('tempdir/private.key', 'w').AndReturn(key)
    key.write('key').AndReturn(None)
    key.close().AndReturn(None)
    cert = self.mox.CreateMockAnything()
    open('tempdir/certificate.cer', 'w').AndReturn(cert)
    cert.write('cert').AndReturn(None)
    cert.close().AndReturn(None)

  def testInstallCertInKeychainSuccessNoPassNoApp(self):
    """Test InstallCertInKeychain success, no passphrase or trusted app."""
    self.StubSetup()
    certs.logging.info('Installing downloaded key into the %s keychain',
                       'k').AndReturn(None)
    certs.tempfile.mkdtemp(prefix=mox.IgnoreArg()).AndReturn('tempdir')
    self.WriteFiles()
    command = [certs.CMD_SECURITY, 'import', 'tempdir/private.key', '-x',
               '-k', 'k', '-A']
    certs.logging.debug('Command: %s', command).AndReturn(None)
    certs.gmacpyutil.RunProcess(command,
                                sudo=False,
                                sudo_password=None).AndReturn(('out', 'err', 0))
    certs.logging.debug('Private key installation output: %s',
                        'out').AndReturn(None)
    certs.shutil.rmtree('tempdir').AndReturn(None)
    certs.tempfile.mkdtemp(prefix=mox.IgnoreArg()).AndReturn('tempdir')
    certs.logging.info('Installing downloaded certificate into the %s keychain',
                       'k').AndReturn(None)
    command = [certs.CMD_SECURITY, 'import', 'tempdir/certificate.cer', '-x',
               '-k', 'k']
    certs.logging.debug('Command: %s', command).AndReturn(None)
    certs.gmacpyutil.RunProcess(command,
                                sudo=False,
                                sudo_password=None).AndReturn(('out', 'err', 0))
    certs.logging.debug('Certificate installation output: %s',
                        'out').AndReturn(None)
    certs.shutil.rmtree('tempdir').AndReturn(None)

    self.mox.ReplayAll()
    certs.InstallCertInKeychain('cert', 'key', keychain='k')
    self.mox.VerifyAll()

  def testInstallCertInKeychainSuccessSystemKeychain(self):
    """Test InstallCertInKeychain success, system keychain."""
    self.StubSetup()
    certs.logging.info('Installing downloaded key into the %s keychain',
                       certs.SYSTEM_KEYCHAIN).AndReturn(None)
    certs.tempfile.mkdtemp(prefix=mox.IgnoreArg()).AndReturn('tempdir')
    self.WriteFiles()
    command = [certs.CMD_SECURITY, 'import', 'tempdir/private.key', '-x', '-k',
               certs.SYSTEM_KEYCHAIN, '-A']
    certs.logging.debug('Command: %s', command).AndReturn(None)
    certs.gmacpyutil.RunProcess(command,
                                sudo=True,
                                sudo_password=None).AndReturn(('out', 'err', 0))
    certs.logging.debug('Private key installation output: %s',
                        'out').AndReturn(None)
    certs.shutil.rmtree('tempdir').AndReturn(None)
    certs.tempfile.mkdtemp(prefix=mox.IgnoreArg()).AndReturn('tempdir')
    certs.logging.info('Installing downloaded certificate into the %s keychain',
                       certs.SYSTEM_KEYCHAIN).AndReturn(None)
    command = [certs.CMD_SECURITY, 'import', 'tempdir/certificate.cer', '-x',
               '-k', certs.SYSTEM_KEYCHAIN]
    certs.logging.debug('Command: %s', command).AndReturn(None)
    certs.gmacpyutil.RunProcess(command,
                                sudo=True,
                                sudo_password=None).AndReturn(('out', 'err', 0))
    certs.logging.debug('Certificate installation output: %s',
                        'out').AndReturn(None)
    certs.shutil.rmtree('tempdir').AndReturn(None)

    self.mox.ReplayAll()
    certs.InstallCertInKeychain('cert', 'key', keychain=certs.SYSTEM_KEYCHAIN)
    self.mox.VerifyAll()

  def testInstallCertInKeychainSuccessWithPassNoApp(self):
    """Test InstallCertInKeychain success, with passphrase, no trusted app."""
    self.StubSetup()
    certs.logging.info('Installing downloaded key into the %s keychain',
                       'k').AndReturn(None)
    certs.tempfile.mkdtemp(prefix=mox.IgnoreArg()).AndReturn('tempdir')
    self.WriteFiles()
    command = [certs.CMD_SECURITY, 'import', 'tempdir/private.key', '-x',
               '-k', 'k', '-P', 'passphrase', '-A']
    certs.logging.debug('Command: %s', command).AndReturn(None)
    certs.gmacpyutil.RunProcess(command,
                                sudo=False,
                                sudo_password=None).AndReturn(('out', 'err', 0))
    certs.logging.debug('Private key installation output: %s',
                        'out').AndReturn(None)
    certs.shutil.rmtree('tempdir').AndReturn(None)
    certs.tempfile.mkdtemp(prefix=mox.IgnoreArg()).AndReturn('tempdir')
    certs.logging.info('Installing downloaded certificate into the %s keychain',
                       'k').AndReturn(None)
    command = [certs.CMD_SECURITY, 'import', 'tempdir/certificate.cer', '-x',
               '-k', 'k']
    certs.logging.debug('Command: %s', command).AndReturn(None)
    certs.gmacpyutil.RunProcess(command,
                                sudo=False,
                                sudo_password=None).AndReturn(('out', 'err', 0))
    certs.logging.debug('Certificate installation output: %s',
                        'out').AndReturn(None)
    certs.shutil.rmtree('tempdir').AndReturn(None)

    self.mox.ReplayAll()
    certs.InstallCertInKeychain('cert', 'key', keychain='k',
                                passphrase='passphrase')
    self.mox.VerifyAll()

  def testInstallCertInKeychainSuccessWithPassWithApp(self):
    """Test InstallCertInKeychain success, with passphrase and trusted app."""
    self.StubSetup()
    certs.logging.info('Installing downloaded key into the %s keychain',
                       'k').AndReturn(None)
    certs.tempfile.mkdtemp(prefix=mox.IgnoreArg()).AndReturn('tempdir')
    self.WriteFiles()
    command = [certs.CMD_SECURITY, 'import', 'tempdir/private.key', '-x',
               '-k', 'k', '-P', 'passphrase', '-T', 'trusted_app_path']
    certs.os.path.exists('trusted_app_path').AndReturn(True)
    certs.logging.debug('Command: %s', command).AndReturn(None)
    certs.gmacpyutil.RunProcess(command,
                                sudo=False,
                                sudo_password=None).AndReturn(('out', 'err', 0))
    certs.logging.debug('Private key installation output: %s',
                        'out').AndReturn(None)
    certs.shutil.rmtree('tempdir').AndReturn(None)
    certs.tempfile.mkdtemp(prefix=mox.IgnoreArg()).AndReturn('tempdir')
    certs.logging.info('Installing downloaded certificate into the %s keychain',
                       'k').AndReturn(None)
    command = [certs.CMD_SECURITY, 'import', 'tempdir/certificate.cer', '-x',
               '-k', 'k']
    certs.logging.debug('Command: %s', command).AndReturn(None)
    certs.gmacpyutil.RunProcess(command,
                                sudo=False,
                                sudo_password=None).AndReturn(('out', 'err', 0))
    certs.logging.debug('Certificate installation output: %s',
                        'out').AndReturn(None)
    certs.shutil.rmtree('tempdir').AndReturn(None)

    self.mox.ReplayAll()
    certs.InstallCertInKeychain('cert', 'key', keychain='k',
                                passphrase='passphrase',
                                trusted_app_path='trusted_app_path')
    self.mox.VerifyAll()

  def testInstallCertInKeychainSuccessWithMultipleApps(self):
    """Test InstallCertInKeychain success, with multiple trusted apps."""
    self.StubSetup()
    certs.logging.info('Installing downloaded key into the %s keychain',
                       'k').AndReturn(None)
    certs.tempfile.mkdtemp(prefix=mox.IgnoreArg()).AndReturn('tempdir')
    self.WriteFiles()
    command = [certs.CMD_SECURITY, 'import', 'tempdir/private.key', '-x',
               '-k', 'k', '-P', 'passphrase', '-T', 'app1', '-T', 'app2']
    certs.os.path.exists('app1').AndReturn(True)
    certs.os.path.exists('app2').AndReturn(True)
    certs.logging.debug('Command: %s', command).AndReturn(None)
    certs.gmacpyutil.RunProcess(command,
                                sudo=False,
                                sudo_password=None).AndReturn(('out', 'err', 0))
    certs.logging.debug('Private key installation output: %s',
                        'out').AndReturn(None)
    certs.shutil.rmtree('tempdir').AndReturn(None)
    certs.tempfile.mkdtemp(prefix=mox.IgnoreArg()).AndReturn('tempdir')
    certs.logging.info('Installing downloaded certificate into the %s keychain',
                       'k').AndReturn(None)
    command = [certs.CMD_SECURITY, 'import', 'tempdir/certificate.cer', '-x',
               '-k', 'k']
    certs.logging.debug('Command: %s', command).AndReturn(None)
    certs.gmacpyutil.RunProcess(command,
                                sudo=False,
                                sudo_password=None).AndReturn(('out', 'err', 0))
    certs.logging.debug('Certificate installation output: %s',
                        'out').AndReturn(None)
    certs.shutil.rmtree('tempdir').AndReturn(None)

    self.mox.ReplayAll()
    certs.InstallCertInKeychain('cert', 'key', keychain='k',
                                passphrase='passphrase',
                                trusted_app_path=['app1', 'app2'])
    self.mox.VerifyAll()

  def testInstallCertInKeychainPrivateFailNoPassNoApp(self):
    """Test InstallCertInKeychain private key failure, no pass or app."""
    self.StubSetup()
    certs.tempfile.mkdtemp(prefix=mox.IgnoreArg()).AndReturn('tempdir')
    mock_file = self.mox.CreateMockAnything()
    open('tempdir/private.key', 'w').AndReturn(mock_file)
    mock_file.write('key').AndReturn(None)
    mock_file.close().AndReturn(None)
    certs.logging.info('Installing downloaded key into the %s keychain',
                       'k').AndReturn(None)
    command = [certs.CMD_SECURITY, 'import', 'tempdir/private.key', '-x',
               '-k', 'k', '-A']
    certs.logging.debug('Command: %s', command).AndReturn(None)
    certs.gmacpyutil.RunProcess(command,
                                sudo=False,
                                sudo_password=None).AndReturn(('out', 'err', 1))
    certs.logging.debug('Private key installation output: %s',
                        'out').AndReturn(None)
    certs.shutil.rmtree('tempdir').AndReturn(None)

    self.mox.ReplayAll()
    self.assertRaises(certs.KeychainError, certs.InstallCertInKeychain, 'cert',
                      'key', keychain='k')
    self.mox.VerifyAll()

  def testInstallCertInKeychainCertFailNoPassNoApp(self):
    """Test InstallCertInKeychain cert failure, no passphrase."""
    self.StubSetup()
    certs.logging.info('Installing downloaded key into the %s keychain',
                       'k').AndReturn(None)
    certs.tempfile.mkdtemp(prefix=mox.IgnoreArg()).AndReturn('tempdir')
    self.WriteFiles()
    command = [certs.CMD_SECURITY, 'import', 'tempdir/private.key', '-x',
               '-k', 'k', '-A']
    certs.logging.debug('Command: %s', command).AndReturn(None)
    certs.gmacpyutil.RunProcess(command,
                                sudo=False,
                                sudo_password=None).AndReturn(('out', 'err', 0))
    certs.logging.debug('Private key installation output: %s',
                        'out').AndReturn(None)
    certs.shutil.rmtree('tempdir').AndReturn(None)
    certs.tempfile.mkdtemp(prefix=mox.IgnoreArg()).AndReturn('tempdir')
    certs.logging.info('Installing downloaded certificate into the %s keychain',
                       'k').AndReturn(None)
    command = [certs.CMD_SECURITY, 'import', 'tempdir/certificate.cer', '-x',
               '-k', 'k']
    certs.logging.debug('Command: %s', command).AndReturn(None)
    certs.gmacpyutil.RunProcess(command,
                                sudo=False,
                                sudo_password=None).AndReturn(('out', 'err', 1))
    certs.logging.debug('Certificate installation output: %s',
                        'out').AndReturn(None)
    certs.shutil.rmtree('tempdir').AndReturn(None)

    self.mox.ReplayAll()
    self.assertRaises(certs.KeychainError, certs.InstallCertInKeychain, 'cert',
                      'key', keychain='k')
    self.mox.VerifyAll()

  def testRemoveIssuerCertsFromKeycahin(self):
    """Test RemoveIssuerCertsFromKeychain."""
    self.StubSetup()
    self.mox.StubOutWithMock(certs, 'DeleteCert')
    self.mox.StubOutWithMock(certs, 'FindCertificates')
    c = self.mox.CreateMockAnything()
    c.osx_fingerprint = 'f'

    # Remove is successful
    certs.FindCertificates(issuer_cn='i', keychain='k').AndReturn([c])
    certs.logging.debug(
        'Removing cert with fingerprint %s from %s', 'f', 'k').AndReturn(None)
    certs.DeleteCert('f', password=None,
                     gui=False, keychain='k').AndReturn(None)
    # Remove fails
    certs.FindCertificates(issuer_cn='i', keychain='k').AndReturn([c])
    certs.logging.debug(
        'Removing cert with fingerprint %s from %s', 'f', 'k').AndReturn(None)
    certs.DeleteCert('f', password=None,
                     gui=False, keychain='k').AndRaise(certs.CertError('err'))
    certs.logging.error('Cannot delete old certificate: %s', 'err')

    self.mox.ReplayAll()
    # Remove is sucessful
    certs.RemoveIssuerCertsFromKeychain('i', keychain='k')
    # Remove fails
    certs.RemoveIssuerCertsFromKeychain('i', keychain='k')
    self.mox.VerifyAll()

  def testGenerateCSRNoPassphrase(self):
    """Test GenerateCSR success with no passphrase."""
    self.StubSetup()
    command = [certs.CMD_OPENSSL, 'genrsa', '2048']
    certs.logging.debug('command: %s', command).AndReturn(None)
    certs.logging.debug('environment: %s', []).AndReturn(None)
    certs.gmacpyutil.RunProcess(command, env={}).AndReturn(('key', 'err', 0))
    certs.logging.debug('Private key generation output: %s',
                        'key').AndReturn(None)
    command = [certs.CMD_OPENSSL, 'req', '-new', '-subj', 'subject', '-key',
               '/dev/stdin']
    certs.logging.debug('command: %s', command)
    certs.logging.debug('environment: %s', [])
    certs.logging.debug('stdinput: %s', 'key')
    certs.gmacpyutil.RunProcess(command, 'key',
                                env={}).AndReturn(('csr', 'err', 0))
    certs.logging.debug('CSR generation output: %s', 'csr').AndReturn(None)

    self.mox.ReplayAll()
    self.assertEqual(('csr', 'key', None), certs.GenerateCSR(subject='subject'))
    self.mox.VerifyAll()

  def testGenerateCSRWithPassphrase(self):
    """Test GenerateCSR success with a passphrase."""
    self.StubSetup()
    command = [certs.CMD_OPENSSL, 'genrsa', '-des3', '-passout',
               'env:PASSPHRASE', '2048']
    certs.logging.debug('command: %s', command).AndReturn(None)
    certs.logging.debug('environment: %s', ['PASSPHRASE']).AndReturn(None)
    certs.gmacpyutil.RunProcess(command, env={'PASSPHRASE': 'pass'}).AndReturn(
        ('key', 'err', 0))
    certs.logging.debug('Private key generation output: %s',
                        'key').AndReturn(None)
    command = [certs.CMD_OPENSSL, 'req', '-new', '-subj', 'subject', '-key',
               '/dev/stdin', '-passin', 'env:PASSPHRASE']
    certs.logging.debug('command: %s', command)
    certs.logging.debug('environment: %s', ['PASSPHRASE'])
    certs.logging.debug('stdinput: %s', 'key')
    certs.gmacpyutil.RunProcess(command, 'key',
                                env={'PASSPHRASE': 'pass'}).AndReturn(
                                    ('csr', 'err', 0))
    certs.logging.debug('CSR generation output: %s', 'csr').AndReturn(None)

    self.mox.ReplayAll()
    self.assertEqual(('csr', 'key', 'pass'),
                     certs.GenerateCSR(subject='subject', passphrase='pass'))
    self.mox.VerifyAll()

  def testGenerateCSRPrivateKeyFailed(self):
    """Test GenerateCSR when generating a private key fails."""
    self.StubSetup()
    # Private key generation failed
    command = [certs.CMD_OPENSSL, 'genrsa', '2048']
    certs.logging.debug('command: %s', command).AndReturn(None)
    certs.logging.debug('environment: %s', []).AndReturn(None)
    certs.gmacpyutil.RunProcess(command, env={}).AndReturn(('key', 'err', 1))
    certs.logging.debug('Private key generation output: %s',
                        'key').AndReturn(None)
    self.mox.ReplayAll()
    self.assertRaises(certs.CertError, certs.GenerateCSR, subject='subject')
    self.mox.VerifyAll()

  def testGenerateCSRFailed(self):
    """Test GenerateCSR when generating the CSR fails."""
    self.StubSetup()
    command = [certs.CMD_OPENSSL, 'genrsa', '2048']
    certs.logging.debug('command: %s', command).AndReturn(None)
    certs.logging.debug('environment: %s', []).AndReturn(None)
    certs.gmacpyutil.RunProcess(command, env={}).AndReturn(('key', 'err', 0))
    certs.logging.debug('Private key generation output: %s',
                        'key').AndReturn(None)
    command = [certs.CMD_OPENSSL, 'req', '-new', '-subj', 'subject', '-key',
               '/dev/stdin']
    certs.logging.debug('command: %s', command)
    certs.logging.debug('environment: %s', [])
    certs.logging.debug('stdinput: %s', 'key')
    certs.gmacpyutil.RunProcess(command, 'key',
                                env={}).AndReturn(('csr', 'err', 1))
    certs.logging.debug('CSR generation output: %s', 'csr').AndReturn(None)

    self.mox.ReplayAll()
    self.assertRaises(certs.CertError, certs.GenerateCSR, subject='subject')
    self.mox.VerifyAll()

  def _SudoContextHelper(self):
    self.password = 'hunter2'
    self.keychain = certs.SYSTEM_KEYCHAIN

  def testGetSudoContextWithCertHandler(self):
    self._SudoContextHelper()

    self.mox.StubOutWithMock(certs.gmacpyutil, 'RunProcess')
    certs.gmacpyutil.RunProcess(
        ['-v'], sudo=True,
        sudo_password=self.password).AndReturn(['', '', 0])
    self.mox.ReplayAll()
    sudo, sudo_pass = certs._GetSudoContext(self.keychain,
                                            gui=True,
                                            password=self.password)
    self.mox.VerifyAll()
    self.assertTrue(sudo)
    self.assertEqual(sudo_pass, 'hunter2')

  def testGetSudoContextWithoutCertHandlerGUIError(self):
    self._SudoContextHelper()

    self.mox.StubOutWithMock(certs.logging, 'exception')
    self.mox.StubOutWithMock(certs.getauth, 'GetPassword')
    certs.getauth.GetPassword(gui=True).AndRaise(EOFError)
    certs.logging.exception(
        'Could not get sudo password from GUI prompt').AndReturn(None)
    self.mox.ReplayAll()
    self.assertRaises(EOFError, certs._GetSudoContext, self.keychain, gui=True)
    self.mox.VerifyAll()

  def testGetSudoContextWithoutCertHandler(self):
    self._SudoContextHelper()

    self.mox.StubOutWithMock(certs.getauth, 'GetPassword')
    certs.getauth.GetPassword(gui=True).AndReturn('pass')
    self.mox.ReplayAll()
    sudo, sudo_pass = certs._GetSudoContext(self.keychain, gui=True)
    self.mox.VerifyAll()
    self.assertTrue(sudo)
    self.assertEqual(sudo_pass, 'pass')

  def testGetSudoContextNoSudo(self):
    self._SudoContextHelper()

    self.mox.ReplayAll()
    sudo, sudo_pass = certs._GetSudoContext('notsystemkeychain')
    self.mox.VerifyAll()
    self.assertFalse(sudo)
    self.assertEqual(sudo_pass, None)


def main(unused_argv):
  basetest.main()


if __name__ == '__main__':
  app.run()
