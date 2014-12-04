"""Module to run Applescript internally with Foundation class."""

import logging
import platform
try:
  import Foundation  # pylint: disable=import-error,g-import-not-at-top
except ImportError:
  # hack to make unit tests work
  if not platform.platform().startswith('Linux-'):
    raise


class Error(Exception):
  """Base error."""


class AppleScriptError(Error):
  """AppleScript error."""


class AppleScriptTimeoutError(Error):
  """AppleScript dialog timed out before user action."""


class AppleScriptRunner(object):
  """Run AppleScript without shelling out to osascript."""

  # TODO(user): add a timeout for all of these dialogs

  GENERIC_DIALOG = (
      'tell application "Finder"\n'
      '  activate\n'
      '  set myResult to (display dialog "%s" %s )\n'
      '  set myReplyText to text returned of myResult\n'
      '  set myGaveUpState to False\n'
      '  set myReply to {myReplyText, myGaveUpState}\n'
      'end tell\n'
  )

  GENERIC_TIMEOUT_DIALOG = (
      'tell application "Finder"\n'
      '  activate\n'
      '  set myResult to (display dialog "%s" %s )\n'
      '  set myReplyText to text returned of myResult\n'
      '  set myGaveUpState to gave up of myResult as string\n'
      '  set myReply to {myReplyText, myGaveUpState}\n'
      'end tell\n'
  )

  BUTTON_DIALOG = (
      'tell application "Finder"\n'
      '  activate\n'
      '  set myResult to (display dialog "%s" %s )\n'
      '  set myReplyText to button returned of myResult as string\n'
      '  set myGaveUpState to False\n'
      '  set myReply to {myReplyText, myGaveUpState}\n'
      'end tell\n'
  )

  BUTTON_TIMEOUT_DIALOG = (
      'tell application "Finder"\n'
      '  activate\n'
      '  set myResult to (display dialog "%s" %s )\n'
      '  set myReplyText to button returned of myResult as string\n'
      '  set myGaveUpState to gave up of myResult as string\n'
      '  set myReply to {myReplyText, myGaveUpState}\n'
      'end tell\n'
  )

  def _EscapeScriptValue(self, v):
    """Returns an script safe version of v if v is a str, or returns v."""
    if type(v) in [unicode, str]:
      return v.replace('\\', '\\\\').replace('"', '\\"')
    else:
      return v

  def _IsNSAppleEventDescriptor(self, x):
    """Returns true if x is NSAppleEventDescriptor instance."""
    try:
      if x.__class__.__name__ == 'NSAppleEventDescriptor':
        return True
    except AttributeError:
      pass

    return False

  def Execute(self, osa_script, *args):
    """Execute script with optional arguments.

    Parsing the return value yourself may not be necessary, see
    ExecuteAndUnpack.

    Be careful to put user-supplied values into args, not osa_script, or
    code injection attacks could occur.

    Args:
      osa_script: str, the script to run
      *args: array of arguments to pass in
    Returns:
      NSAppleEventDescriptor instance
    Raises:
      AppleScriptError: if an error occured at the AppleScript layer
    """
    if args:
      safe_args = tuple([self._EscapeScriptValue(x) for x in args])
      osa_script %= safe_args

    logging.debug('AppleScript: %s', osa_script)

    script = Foundation.NSAppleScript.initWithSource_(
        Foundation.NSAppleScript.alloc(),
        osa_script)

    ret, err = script.executeAndReturnError_(None)

    logging.debug('AppleScript return: %s, %s', ret, err)

    if err:
      raise AppleScriptError(err)

    if not self._IsNSAppleEventDescriptor(ret):
      raise AppleScriptError('expecting NSAppleEventDescriptor return')

    return ret

  def ExecuteAndUnpack(self, osa_script, unpack_fmt, *args):
    """Execute script with optional arguments and unpack the return values.

    Be careful to put user-supplied values into args, not osa_script, or
    code injection attacks could occur.

    The unpack_fmt string is a str of single characters which defines each
    expected return value from AppleScript.  Each character can be one of:

      's': unicode string
      'b': boolean
      'i': int

    e.g. a string of 'sb' indicates that AppleScript will be returning 2
    values, first a unicode string, and then a boolean.  You will receive
    native Python types containing the values.

    Args:
      osa_script: str, the script to run
      unpack_fmt: str, format string to use when parsing the return values
      *args: array of arguments to pass in
    Returns:
      list of values as parsed by format string
    Raises:
      AppleScriptError: if an error occured at the AppleScript layer
      Error: if unpack_fmt has invalid format characters
    """
    ret = self.Execute(osa_script, *args)

    noi = ret.numberOfItems()
    lf = len(unpack_fmt)
    if noi != lf:
      raise AppleScriptError(
          'numberOfItems %d != unpack_fmt len %d' % (noi, lf))

    values = []
    idx = 1

    for f in unpack_fmt:
      d = ret.descriptorAtIndex_(idx)
      if f == 's':  # unicode string
        values.append(unicode(d.stringValue()))
      elif f == 'b':  # bool
        values.append(d.booleanValue())
      elif f == 'i':  # int32
        values.append(d.int32Value())
      else:
        raise Error('unknown unpack_fmt char %s', f)
      idx += 1

    return values

  def DialogGetString(
      self, prompt, timeout=None, hidden=False, default=None, args=()):
    """Prompt the user for a string input via a GUI dialog.

    Do not put user-supplied data into the prompt value. Use string formatting
    and put the values into args.

    Args:
      prompt: str, the prompt to supply to the user
      timeout: int, optional, number of seconds to wait before giving up
      hidden: bool, optional, if true the input field is obfuscated
      default: str, optional, default value to place into input field
      args: list, optional, arguments to supply to Execute().
    Returns:
      str
    Raises:
      AppleScriptTimeoutError: dialog timed out before user action
    """
    opts = []

    if timeout is not None:
      opts.append('giving up after %d' % timeout)
      base_script = self.GENERIC_TIMEOUT_DIALOG
    else:
      base_script = self.GENERIC_DIALOG

    if hidden:
      opts.append('with hidden answer')

    if default is not None:
      opts.append('default answer "%s"' % self._EscapeScriptValue(default))
    else:
      opts.append('default answer ""')

    osa_script = base_script % (self._EscapeScriptValue(prompt), ' '.join(opts))

    # The GENERIC_*DIALOG scripts return 2 values, the button text
    # and a boolean for whether timeout occured or not.
    ret = self.ExecuteAndUnpack(osa_script, 'sb', *args)

    if ret[1]:
      raise AppleScriptTimeoutError(ret[0])

    return ret[0]

  def DialogDisplay(self, prompt, timeout=None, args=(), buttons=None):
    """Show the user a dialog with OK button.

    Do not put user-supplied data into the prompt value. Use string formatting
    and put the values into args.

    Args:
      prompt: str, the prompt to supply to the user
      timeout: int, optional, number of seconds to wait before giving up
      args: list, optional, arguments to supply to Execute().
      buttons: list of strs, optional, default "OK", buttons to display
    Returns:
      str, the name of the button pressed, in this case "OK"
    Raises:
      AppleScriptTimeoutError: dialog timed out before user action
    """
    if buttons is None:
      buttons = ['OK']
    opts = [
        'buttons {"'
        + '","'.join([self._EscapeScriptValue(b) for b in buttons])
        + '"}',
    ]
    if timeout is not None:
      opts.append('giving up after %d' % timeout)
      base_script = self.BUTTON_TIMEOUT_DIALOG
    else:
      base_script = self.BUTTON_DIALOG

    osa_script = base_script % (self._EscapeScriptValue(prompt), ' '.join(opts))
    ret = self.ExecuteAndUnpack(osa_script, 'sb', *args)

    # The BUTTON_*DIALOG scripts return 2 values, the button text
    # and a boolean for whether timeout occured or not.
    if ret[1]:
      raise AppleScriptTimeoutError(ret[0])

    return ret[0]

# Provide module-global shortcuts for these commonly called methods.
_SINGLETON = AppleScriptRunner()


def DialogDisplay(*args, **kwargs):
  return _SINGLETON.DialogDisplay(*args, **kwargs)


def DialogGetString(*args, **kwargs):
  return _SINGLETON.DialogGetString(*args, **kwargs)
