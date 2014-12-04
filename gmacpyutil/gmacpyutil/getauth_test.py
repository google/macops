"""Unit tests for getauth module."""

import re

import mox
import stubout

from google.apputils import app
from google.apputils import basetest

import getauth


class GetauthModuleTest(mox.MoxTestBase):
  """Test common module-level functions."""

  def setUp(self):
    mox.MoxTestBase.setUp(self)
    self.stubs = stubout.StubOutForTesting()

  def tearDown(self):
    self.mox.UnsetStubs()
    self.stubs.UnsetAll()

  def StubSetup(self):
    self.mox.StubOutWithMock(getauth, 'getpass')
    self.mox.StubOutWithMock(getauth, 'cocoadialog')
    self.mox.StubOutWithMock(getauth.getpass, 'getpass')

  def testGetAuthToken(self):
    """Test successful GetAuthToken with defaults."""
    self.StubSetup()
    getauth.getpass.getpass('Password: ').AndReturn('password')
    self.mox.ReplayAll()
    self.assertEqual('password', getauth.GetAuthToken())
    self.mox.VerifyAll()

  def testGetAuthTokenGUI(self):
    """Test successful GetAuthToken with GUI."""
    mock_cocoainput = self.mox.CreateMockAnything()
    self.StubSetup()
    getauth.cocoadialog.Standard_InputBox().AndReturn(mock_cocoainput)
    mock_cocoainput.SetPasswordBox().AndReturn(None)
    mock_cocoainput.Show().AndReturn('button\npassword\n')
    self.mox.ReplayAll()
    self.assertEqual('password', getauth.GetAuthToken(gui=True))
    self.mox.VerifyAll()

  def testGetAuthTokenGUIEmptyData(self):
    """Test successful GetAuthToken with GUI with no data."""
    mock_cocoainput = self.mox.CreateMockAnything()
    self.StubSetup()
    getauth.cocoadialog.Standard_InputBox().AndReturn(mock_cocoainput)
    mock_cocoainput.SetPasswordBox().AndReturn(None)
    mock_cocoainput.Show().AndReturn('button\n\n')
    self.mox.ReplayAll()
    self.assertEqual('', getauth.GetAuthToken(gui=True))
    self.mox.VerifyAll()

  def testGetPasswordInteractivelyVisible(self):
    """Test successful _GetPasswordInteractively with visible password."""
    input_fn = self.mox.CreateMock(raw_input)
    self.StubSetup()
    input_fn('Password: ').AndReturn('password')
    self.mox.ReplayAll()
    self.assertEqual('password',
                     getauth._GetPasswordInteractively(hidden=False,
                                                       input_fn=input_fn))
    self.mox.VerifyAll()

  def testGetAuthTokenWithValidation(self):
    """Test successful GetAuthToken with a validator."""
    validator = re.compile(r'\d{6}')
    self.StubSetup()
    getauth.getpass.getpass('Password: ').AndReturn('123456')
    self.mox.ReplayAll()
    self.assertEqual('123456',
                     getauth.GetAuthToken(validator=validator))
    self.mox.VerifyAll()

  def testGetAuthTokenGUIWithValidation(self):
    """Test successful GetAuthToken with GUI with a validator."""
    validator = re.compile(r'\d{6}')
    mock_cocoainput = self.mox.CreateMockAnything()
    self.StubSetup()
    getauth.cocoadialog.Standard_InputBox().AndReturn(mock_cocoainput)
    mock_cocoainput.SetPasswordBox().AndReturn(None)
    mock_cocoainput.Show().AndReturn('button\npassword\n')
    getauth.cocoadialog.Standard_InputBox().AndReturn(mock_cocoainput)
    mock_cocoainput.SetPasswordBox().AndReturn(None)
    mock_cocoainput.Show().AndReturn('button\n123456\n')
    self.mox.ReplayAll()
    self.assertEqual('123456',
                     getauth.GetAuthToken(gui=True, validator=validator))
    self.mox.VerifyAll()

  def testGetAuthTokenWithValidationOneFailure(self):
    """Test successful GetAuthToken with validator and one failure."""
    validator = re.compile(r'\d{6}')
    self.StubSetup()
    getauth.getpass.getpass('Password: ').AndReturn('password')
    getauth.getpass.getpass('Password: ').AndReturn('123456')
    self.mox.ReplayAll()
    self.assertEqual('123456',
                     getauth.GetAuthToken(validator=validator))
    self.mox.VerifyAll()


def main(unused_argv):
  basetest.main()


if __name__ == '__main__':
  app.run()
