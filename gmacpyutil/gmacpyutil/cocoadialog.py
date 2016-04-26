"""cocoadialog - a wrapper around CocoaDialog to be a bit more OO.

Note that this is by no means complete. The setters all need more validation,
and we're still missing some attributes that could be employed.

Validation should be broken out into generic int/bool/string validation
methods.
"""

from . import gmacpyutil
from . import defaults


_CD_APP = defaults.COCOADIALOG_PATH
_CD = '%s/Contents/MacOS/CocoaDialog' % _CD_APP


class DialogException(Exception):
  """Module specific exception class."""
  pass


class Dialog(object):
  """base dialog class."""

  def __init__(self, title=None, cocoadialog=None):
    self._title = title
    self._debug = False
    self._timeout = 0
    self._width = None
    self._height = None
    self._password_box = False
    if cocoadialog:
      self._cocoadialog = cocoadialog
    else:
      self._cocoadialog = _CD

  def __str__(self):
    return 'CocoaDialog[%s] -- title: [%s]' % (self.__class__.__name__,
                                               self._title)

  def GetTitle(self):
    return self._title

  def SetTitle(self, value):
    self._title = str(value)

  def GetDebug(self):
    return self._debug

  def SetDebug(self, value):
    # checking boolean via an int is simpler
    try:
      value = int(value)
    except ValueError:
      raise DialogException('%s has no boolean equivalent.' % value)
    # but we want to keep it as a boolean.
    self._debug = bool(value)

  def GetWidth(self):
    return self._width

  def SetWidth(self, value):
    self._width = value

  def GetHeight(self):
    return self._height

  def SetHeight(self, value):
    self._height = value

  def GetTimeout(self):
    return self._timeout

  def SetTimeout(self, value):
    try:
      value = int(value)
    except ValueError:
      raise DialogException('Timeout value %s is not an integer.' % value)
    self._timeout = int(value)

  title = property(GetTitle, SetTitle)
  debug = property(GetDebug, SetDebug)
  timeout = property(GetTimeout, SetTimeout)
  width = property(GetWidth, SetWidth)
  height = property(GetHeight, SetHeight)

  def GenerateCommand(self):
    """Generate the actual commands to execute.

    Some special casing is needed here per-class type because of the original
    design of CocoaDialog itself being inconsistent unfortunately.

    SubClasses will normally call super and extend the array with their own
    parameters.

    Returns:
      an array of commands.
    """
    cmds = [self._cocoadialog]
    # Cocoa Dialog uses "-" in run modes, Python classes can't use this char.
    runmode = self.__class__.__name__.lower().replace('_', '-')
    cmds.append(runmode)
    cmds.append('--string-output')
    if self.title:
      cmds.extend(['--title', self._title])
    if self.debug:
      cmds.append('--debug')
    if not self._timeout:
      if runmode == 'bubble':
        cmds.append('--no-timeout')  # only bubble supports this option.
    else:
      cmds.extend(['--timeout', self._timeout])
    if self._width:
      cmds.extend(['--width', self._width])
    if self._height:
      cmds.extend(['--height', self._height])
    return cmds

  def Show(self):
    """Displays the dialog."""
    cmd = [unicode(i) for i in self.GenerateCommand()]
    (stdout, unused_stderr, unused_returncode) = gmacpyutil.RunProcess(cmd)
    return stdout


class TweakDialog(Dialog):
  """This class is one that can be tweaked with icons, text-color etc."""

  def __init__(self, title=None):
    self._text = None
    self._icon = None
    self._icon_file = None
    super(TweakDialog, self).__init__(title)

  def GetText(self):
    return self._text

  def SetText(self, value):
    self._text = value

  def GetIcon(self):
    return self._icon

  def SetIcon(self, value):
    self._icon = value

  def GetIconFile(self):
    return self._icon_file

  def SetIconFile(self, value):
    self._icon_file = value

  text = property(GetText, SetText)
  icon = property(GetIcon, SetIcon)
  icon_file = property(GetIconFile, SetIconFile)

  def GenerateCommand(self):
    """class specific additions."""
    super_cmds = super(TweakDialog, self).GenerateCommand()
    cmds = []
    if self._text:
      cmds.extend(['--text', self._text])
    if self._icon:
      cmds.extend(['--icon', self._icon])
    if self._icon_file:
      cmds.extend(['--icon-file', self._icon_file])
    super_cmds.extend(cmds)
    return super_cmds


class Bubble(TweakDialog):
  """Bubble dialog."""

  xplacement_vals = ['left', 'right', 'center']
  yplacement_vals = ['top', 'bottom', 'center']

  def __init__(self, title=None):
    self._alpha = 0.95
    self._xplacement = 'right'
    self._yplacement = 'top'
    self._text_color = None
    self._border_color = None
    self._background_top = None
    self._background_bottom = None
    super(Bubble, self).__init__(title)

  def GetAlpha(self):
    return self._alpha

  def SetAlpha(self, value):
    try:
      value = float(value)
    except ValueError:
      raise DialogException('Alpha value %s is not a float.' % value)
    if value < 0 or value > 1.0:
      raise DialogException('Alpha value %s is not between 0 and 1' % value)
    self._alpha = value

  def GetXPlacement(self):
    return self._xplacement

  def SetXPlacement(self, value):
    if value.lower() not in self.xplacement_vals:
      raise DialogException('value %s not one of %s' % (value,
                                                        self.xplacement_vals))
    self._xplacement = value.lower()

  def GetYPlacement(self):
    return self._yplacement

  def SetYPlacement(self, value):
    if value.lower() not in self.yplacement_vals:
      raise DialogException('value %s not one of %s' % (value,
                                                        self.yplacement_vals))
    self._yplacement = value.lower()

  def GetTextColor(self):
    return self._text_color

  def SetTextColor(self, value):
    self._text_color = value

  def GetBorderColor(self):
    return self._border_color

  def SetBorderColor(self, value):
    self._border_color = value

  def GetBackgroundTop(self):
    return self._background_top

  def SetBackgroundTop(self, value):
    self._background_top = value

  def GetBackgroundBottom(self):
    return self._background_bottom

  def SetBackgroundBottom(self, value):
    self._background_bottom = value

  alpha = property(GetAlpha, SetAlpha)
  xplacement = property(GetXPlacement, SetXPlacement)
  yplacement = property(GetYPlacement, SetYPlacement)
  text_color = property(GetTextColor, SetTextColor)
  border_color = property(GetBorderColor, SetBorderColor)
  background_top = property(GetBackgroundTop, SetBackgroundTop)
  background_bottom = property(GetBackgroundBottom, SetBackgroundBottom)

  def GenerateCommand(self):
    """Class specific additions."""
    super_cmds = super(Bubble, self).GenerateCommand()
    cmds = []
    super_cmds.extend(cmds)
    return super_cmds


class MsgBox(TweakDialog):
  """msgbox base class."""

  def __init__(self, title=None):
    self._informative_text = None
    self._float = True
    self._button1 = 'OK'
    self._button2 = None
    self._button3 = None
    super(MsgBox, self).__init__(title)

  def GetInformativeText(self):
    return self._informative_text

  def SetInformativeText(self, value):
    value = value.replace('\n', chr(13))
    self._informative_text = value

  def GetFloat(self):
    return self._float

  def SetFloat(self, value):
    self._float = value

  def GetButton1(self):
    return self._button1

  def SetButton1(self, value):
    self._button1 = value

  def GetButton2(self):
    return self._button2

  def SetButton2(self, value):
    self._button2 = value

  def GetButton3(self):
    return self._button3

  def SetButton3(self, value):
    self._button3 = value

  informative_text = property(GetInformativeText, SetInformativeText)
  float = property(GetFloat, SetFloat)
  button1 = property(GetButton1, SetButton1)
  button2 = property(GetButton2, SetButton2)
  button3 = property(GetButton3, SetButton3)

  def GenerateCommand(self):
    super_cmds = super(MsgBox, self).GenerateCommand()
    cmds = []
    cmds.extend(['--button1', self._button1])
    if self._button2:
      cmds.extend(['--button2', self._button2])
    if self._button3:
      cmds.extend(['--button3', self._button3])
    if self._informative_text:
      cmds.extend(['--informative-text', self._informative_text])
    if self._float:
      cmds.append('--float')
    super_cmds.extend(cmds)
    return super_cmds


class OK_MsgBox(MsgBox):
  """ok-msgbox base class."""

  # Disable buttons - not supported by this cocoadialog run mode.
  GetButton1 = None
  SetButton1 = None
  GetButton2 = None
  SetButton2 = None
  GetButton3 = None
  SetButton3 = None

  def __init__(self, title=None):
    self._no_cancel = False
    super(OK_MsgBox, self).__init__(title)

  def GetNoCancel(self):
    return self._no_cancel

  def SetNoCancel(self, cancel=True):
    self._no_cancel = cancel

  no_cancel = property(GetNoCancel, SetNoCancel)

  def GenerateCommand(self):
    super_cmds = super(OK_MsgBox, self).GenerateCommand()
    cmds = []
    if self._no_cancel:
      cmds.append('--no-cancel')
    super_cmds.extend(cmds)
    return super_cmds


class YesNo_MsgBox(MsgBox):
  """yesno-msgbox base class."""

  # Disable buttons - not supported by this cocoadialog run mode.
  GetButton1 = None
  SetButton1 = None
  GetButton2 = None
  SetButton2 = None
  GetButton3 = None
  SetButton3 = None

  def __init__(self, title=None):
    self._no_cancel = False
    super(YesNo_MsgBox, self).__init__(title)

  def GetNoCancel(self):
    return self._no_cancel

  def SetNoCancel(self, cancel=True):
    self._no_cancel = cancel

  no_cancel = property(GetNoCancel, SetNoCancel)

  def GenerateCommand(self):
    super_cmds = super(YesNo_MsgBox, self).GenerateCommand()
    cmds = []
    if self._no_cancel:
      cmds.append('--no-cancel')
    super_cmds.extend(cmds)
    return super_cmds


class Standard_InputBox(Dialog):  # pylint: disable=invalid-name
  """Create a basic inputbox with Cancel and OK buttons."""

  def __init__(self, title=None):
    self._informative_text = None
    self._text = None
    self._no_cancel = False
    super(Standard_InputBox, self).__init__(title)

  def GetInformativeText(self):
    return self._informative_text

  def SetInformativeText(self, value):
    self._informative_text = value

  def GetText(self):
    return self._text

  def SetText(self, value):
    self._text = value

  def GetPasswordBox(self):
    return self._password_box

  def SetPasswordBox(self):
    self._password_box = True

  def GetNoCancel(self):
    return self._no_cancel

  def SetNoCancel(self, cancel=True):
    self._no_cancel = cancel

  informative_text = property(GetInformativeText, SetInformativeText)
  text = property(GetText, SetText)
  password_box = property(GetPasswordBox, SetPasswordBox)
  no_cancel = property(GetNoCancel, SetNoCancel)

  def GenerateCommand(self):
    """Class specific additions."""
    super_cmds = super(Standard_InputBox, self).GenerateCommand()
    cmds = []
    if self._informative_text:
      cmds.extend(['--informative-text', self._informative_text])
    if self._text:
      cmds.extend(['--text', self._text])
    if self._password_box:
      cmds.extend(['--no-show'])
    if self._no_cancel:
      cmds.extend(['--no-cancel'])
    super_cmds.extend(cmds)
    return super_cmds


class DropDown(MsgBox):
  """Generate a basic dropdown with customizable buttons."""

  def __init__(self, title=None, cocoadialog=None):
    self._items = []
    if cocoadialog:
      self._cocoadialog = cocoadialog
    else:
      self._cocoadialog = _CD
    self._title = title
    self._debug = None
    super(DropDown, self).__init__(title)

  def __str__(self):
    return 'CocoaDialog[%s] -- title: [%s]' % (self.__class__.__name__,
                                               self._title)

  def GetItems(self):
    return self._items

  def SetItems(self, list_of_items):
    self._items = list_of_items

  items = property(GetItems, SetItems)

  def GenerateCommand(self):
    """Class specific additions."""
    super_cmds = super(DropDown, self).GenerateCommand()
    cmds = []
    if self._items:
      dropdown_items = ['--items']
      for item in self._items:
        dropdown_items.append(item)
      cmds.extend(dropdown_items)
    super_cmds.extend(cmds)
    return super_cmds


class Standard_DropDown(MsgBox):  # pylint: disable=invalid-name
  """Generate a basic dropdown with Cancel and OK buttons."""

  # Disable buttons - not supported by this cocoadialog run mode.
  GetButton1 = None
  SetButton1 = None
  GetButton2 = None
  SetButton2 = None
  GetButton3 = None
  SetButton3 = None

  def __init__(self, title=None, cocoadialog=None):
    self._items = []
    if cocoadialog:
      self._cocoadialog = cocoadialog
    else:
      self._cocoadialog = _CD
    self._title = title
    self._no_cancel = False
    self._debug = None
    super(Standard_DropDown, self).__init__(title)

  def __str__(self):
    return 'CocoaDialog[%s] -- title: [%s]' % (self.__class__.__name__,
                                               self._title)

  def GetItems(self):
    return self._items

  def SetItems(self, list_of_items):
    self._items = list_of_items

  def GetNoCancel(self):
    return self._no_cancel

  def SetNoCancel(self, cancel=True):
    self._no_cancel = cancel

  items = property(GetItems, SetItems)
  no_cancel = property(GetNoCancel, SetNoCancel)

  def GenerateCommand(self):
    """Class specific additions."""
    super_cmds = super(Standard_DropDown, self).GenerateCommand()
    cmds = []
    if self._items:
      dropdown_items = ['--items']
      for item in self._items:
        dropdown_items.append(item)
      cmds.extend(dropdown_items)
    if self._no_cancel:
      cmds.append('--no-cancel')
    super_cmds.extend(cmds)
    return super_cmds
