"""applescript module tests."""


import mox
import stubout

from google.apputils import app
from google.apputils import basetest

import applescript


class AppleScriptRunnerTest(mox.MoxTestBase):

  def setUp(self):
    mox.MoxTestBase.setUp(self)
    self.stubs = stubout.StubOutForTesting()
    self._SetupFoundation()
    self.asr = applescript.AppleScriptRunner()

  def tearDown(self):
    self.mox.UnsetStubs()
    self.stubs.UnsetAll()

  def _SetupFoundation(self):
    """Setup a fake Foundation module."""
    applescript.Foundation = self.mox.CreateMockAnything()
    applescript.Foundation.NSAppleScript = self.mox.CreateMockAnything()

  def testVariables(self):
    """Test variables of Opener class."""
    self.assertTrue(hasattr(self.asr, 'GENERIC_DIALOG'))
    self.assertTrue(hasattr(self.asr, 'GENERIC_TIMEOUT_DIALOG'))
    self.assertTrue(hasattr(self.asr, 'BUTTON_DIALOG'))
    self.assertTrue(hasattr(self.asr, 'BUTTON_TIMEOUT_DIALOG'))

  def testEscapeScriptValue(self):
    """Test _EscapeScript()."""
    tests = (
        (None, None),
        (1, 1),
        ('clean', 'clean'),
        ('"; haxor -p', '\\"; haxor -p'),
        (
            'trying to escape the escape \\"; haxor -p',
            'trying to escape the escape \\\\\\"; haxor -p'
        ),
    )
    for i, o in tests:
      self.assertEqual(self.asr._EscapeScriptValue(i), o)

  def testIsNSAppleEventDescriptor(self):
    """Test _IsNSAppleEventDescriptor()."""

    class NSAppleEventDescriptor(object):
      pass

    x1 = NSAppleEventDescriptor()
    x2 = self

    self.assertTrue(self.asr._IsNSAppleEventDescriptor(x1))
    self.assertFalse(self.asr._IsNSAppleEventDescriptor(x2))

  def testExecute(self):
    """Test Execute()."""
    self.mox.StubOutWithMock(self.asr, '_IsNSAppleEventDescriptor')

    mock_nsa = self.mox.CreateMockAnything()
    mock_script = self.mox.CreateMockAnything()
    ret = self.mox.CreateMockAnything()

    err = None
    osa_script = 'hot value "%s"'
    value = 'hello'

    applescript.Foundation.NSAppleScript.alloc().AndReturn(mock_nsa)
    applescript.Foundation.NSAppleScript.initWithSource_(
        mock_nsa, osa_script % value).AndReturn(mock_script)
    mock_script.executeAndReturnError_(None).AndReturn((ret, err))
    self.asr._IsNSAppleEventDescriptor(ret).AndReturn(True)

    self.mox.ReplayAll()
    self.assertEqual(ret, self.asr.Execute(osa_script, value))
    self.mox.VerifyAll()

  def testExecuteWhenUnknownReturn(self):
    """Test Execute()."""
    self.mox.StubOutWithMock(self.asr, '_IsNSAppleEventDescriptor')

    mock_nsa = self.mox.CreateMockAnything()
    mock_script = self.mox.CreateMockAnything()

    ret = {}
    err = None
    osa_script = 'some script %s'

    applescript.Foundation.NSAppleScript.alloc().AndReturn(mock_nsa)
    applescript.Foundation.NSAppleScript.initWithSource_(
        mock_nsa, osa_script).AndReturn(mock_script)
    mock_script.executeAndReturnError_(None).AndReturn((ret, err))
    self.asr._IsNSAppleEventDescriptor(ret).AndReturn(False)

    self.mox.ReplayAll()
    self.assertRaises(
        applescript.AppleScriptError, self.asr.Execute, osa_script)
    self.mox.VerifyAll()

  def testExecuteWhenError(self):
    """Test Execute()."""
    mock_nsa = self.mox.CreateMockAnything()
    mock_script = self.mox.CreateMockAnything()
    ret = None
    err = 'error'
    osa_script = 'some script %s'

    applescript.Foundation.NSAppleScript.alloc().AndReturn(mock_nsa)
    applescript.Foundation.NSAppleScript.initWithSource_(
        mock_nsa, osa_script).AndReturn(mock_script)
    mock_script.executeAndReturnError_(None).AndReturn((ret, err))

    self.mox.ReplayAll()
    self.assertRaises(
        applescript.AppleScriptError,
        self.asr.Execute, osa_script)
    self.mox.VerifyAll()

  def testExecuteAndUnpack(self):
    """Test ExecuteAndUnpack()."""
    self.mox.StubOutWithMock(self.asr, 'Execute')

    mock_ret = self.mox.CreateMockAnything()
    mock_item = self.mox.CreateMockAnything()
    mock_ret = self.mox.CreateMockAnything()

    unpack_fmt = 'sbi'
    args = ['some value']
    osa_script = 'some script %s'

    self.asr.Execute(osa_script, args).AndReturn(mock_ret)
    mock_ret.numberOfItems().AndReturn(len(unpack_fmt))
    mock_ret.descriptorAtIndex_(1).AndReturn(mock_item)
    mock_item.stringValue().AndReturn(u'hello')
    mock_ret.descriptorAtIndex_(2).AndReturn(mock_item)
    mock_item.booleanValue().AndReturn(True)
    mock_ret.descriptorAtIndex_(3).AndReturn(mock_item)
    mock_item.int32Value().AndReturn(54321)

    self.mox.ReplayAll()
    self.assertEqual(
        [u'hello', True, 54321],
        self.asr.ExecuteAndUnpack(osa_script, unpack_fmt, args))
    self.mox.VerifyAll()

  def testExecuteAndUnpackWhenError(self):
    """Test ExecuteAndUnpack()."""
    self.mox.StubOutWithMock(self.asr, 'Execute')

    mock_ret = self.mox.CreateMockAnything()
    mock_item = self.mox.CreateMockAnything()
    mock_ret = self.mox.CreateMockAnything()

    unpack_fmt = 'sbi'
    args = ['some value']
    osa_script = 'some script %s'

    self.asr.Execute(osa_script, args).AndReturn(mock_ret)
    mock_ret.numberOfItems().AndReturn(len(unpack_fmt) + 1)
    self.asr.Execute(osa_script, args).AndReturn(mock_ret)
    mock_ret.numberOfItems().AndReturn(len(unpack_fmt) + 1)
    mock_ret.descriptorAtIndex_(1).AndReturn(mock_item)

    self.mox.ReplayAll()
    self.assertRaises(
        applescript.Error,
        self.asr.ExecuteAndUnpack, osa_script, unpack_fmt, args)
    unpack_fmt = 'xsbi'
    self.assertRaises(
        applescript.Error,
        self.asr.ExecuteAndUnpack, osa_script, unpack_fmt, args)
    self.mox.VerifyAll()

  def testDialogGetString(self):
    """Test DialogGetString()."""
    self.mox.StubOutWithMock(self.asr, 'ExecuteAndUnpack')

    ret = ('hello', False)

    self.asr.ExecuteAndUnpack(
        self.asr.GENERIC_DIALOG % ('prompt', 'default answer ""'),
        'sb', 1).AndReturn(ret)

    self.mox.ReplayAll()
    self.assertEqual('hello', self.asr.DialogGetString('prompt', args=[1]))
    self.mox.VerifyAll()

  def testDialogGetStringWithSpecialCharacters(self):
    """Test DialogGetString() with special characters in the prompt."""
    self.mox.StubOutWithMock(self.asr, 'ExecuteAndUnpack')

    ret = ('hello', False)

    prompt = 'prompt "quoted"'
    prompt_escaped = r'prompt \"quoted\"'

    self.asr.ExecuteAndUnpack(
        self.asr.GENERIC_DIALOG % (prompt_escaped, 'default answer ""'),
        'sb', 1).AndReturn(ret)

    self.mox.ReplayAll()
    self.assertEqual(
        'hello', self.asr.DialogGetString(prompt, args=[1]))
    self.mox.VerifyAll()

  def testDialogGetStringWhenDefault(self):
    """Test DialogGetString()."""
    self.mox.StubOutWithMock(self.asr, 'ExecuteAndUnpack')

    ret = ('hello', False)

    self.asr.ExecuteAndUnpack(
        self.asr.GENERIC_DIALOG % ('prompt', 'default answer "default"'),
        'sb', 1).AndReturn(ret)

    self.mox.ReplayAll()
    self.assertEqual(
        'hello',
        self.asr.DialogGetString('prompt', args=[1], default='default'))
    self.mox.VerifyAll()

  def testDialogGetStringWhenTimeout(self):
    """Test DialogGetString()."""
    self.mox.StubOutWithMock(self.asr, 'ExecuteAndUnpack')

    ret = ('hello', True)

    self.asr.ExecuteAndUnpack(
        self.asr.GENERIC_TIMEOUT_DIALOG % (
            'prompt', 'giving up after 5 default answer ""'),
        'sb', 1).AndReturn(ret)

    self.mox.ReplayAll()
    self.assertRaises(
        applescript.AppleScriptTimeoutError,
        self.asr.DialogGetString, 'prompt', timeout=5, args=[1])
    self.mox.VerifyAll()

  def testDialogGetStringHidden(self):
    """Test DialogGetString()."""
    self.mox.StubOutWithMock(self.asr, 'ExecuteAndUnpack')

    ret = ('hello', False)

    self.asr.ExecuteAndUnpack(
        self.asr.GENERIC_DIALOG % (
            'prompt', 'with hidden answer default answer ""'),
        'sb', 1).AndReturn(ret)

    self.mox.ReplayAll()
    self.assertEqual(
        'hello',
        self.asr.DialogGetString('prompt', hidden=True, args=[1]))
    self.mox.VerifyAll()

  def testDialogDisplay(self):
    """Test DialogDisplay()."""
    self.mox.StubOutWithMock(self.asr, 'ExecuteAndUnpack')

    ret = ('OK', False)

    self.asr.ExecuteAndUnpack(
        self.asr.BUTTON_DIALOG % ('prompt', 'buttons {"OK"}'),
        'sb', 1).AndReturn(ret)

    self.mox.ReplayAll()
    self.assertEqual('OK', self.asr.DialogDisplay('prompt', args=[1]))
    self.mox.VerifyAll()

  def testDialogDisplayWhenTimeout(self):
    """Test DialogDisplay()."""
    self.mox.StubOutWithMock(self.asr, 'ExecuteAndUnpack')

    ret = ('OK', True)

    self.asr.ExecuteAndUnpack(
        self.asr.BUTTON_TIMEOUT_DIALOG % (
            'prompt', 'buttons {"OK"} giving up after 5'),
        'sb', 1).AndReturn(ret)

    self.mox.ReplayAll()
    self.assertRaises(
        applescript.AppleScriptTimeoutError,
        self.asr.DialogDisplay, 'prompt', args=[1], timeout=5)
    self.mox.VerifyAll()

  def testDialogDisplayWithButtons(self):
    """Test DialogDisplay() with buttons arg."""
    self.mox.StubOutWithMock(self.asr, 'ExecuteAndUnpack')

    ret = ('OK', False)

    self.asr.ExecuteAndUnpack(
        self.asr.BUTTON_DIALOG % ('prompt', 'buttons {"OK","Other"}'),
        'sb', 1).AndReturn(ret)

    self.mox.ReplayAll()
    self.assertEqual('OK', self.asr.DialogDisplay(
        'prompt', args=[1], buttons=['OK', 'Other']))
    self.mox.VerifyAll()


def main(unused_argv):
  basetest.main()


if __name__ == '__main__':
  app.run()
