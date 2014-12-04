"""Mac OS X Disk Module.

This is basically a convenience wrapper around hdiutil, diskutil and asr to
unify the three tools so you can easily refer to objects.
"""

import plistlib
import re
import subprocess
import xml.parsers.expat
from . import gmacpyutil


class MacDiskError(Exception):
  """Module specific exception class."""
  pass


class Disk(object):
  """Represents a disk object.

  Note that this also is used for currently mounted disk images as they
  really are just 'disks'. Mostly. Can take device ids of the form "disk1" or
  of the form "/dev/disk1".
  """

  def __init__(self, deviceid):
    if deviceid.startswith("/dev/"):
      deviceid = deviceid.replace("/dev/", "", 1)
    self.deviceid = deviceid
    self.Refresh()

  def Refresh(self):
    """convenience attrs for direct querying really."""

    self._attributes = _DictFromDiskutilInfo(self.deviceid)
    # We iterate over all known keys, yes this includes DeviceIdentifier
    # even though we"re using deviceid internally for init.
    # This is why the rest of the code has gratuitous use of
    # disable-msg=E1101 due to constructing the attributes this way.
    keys = ["Content", "Internal", "CanBeMadeBootableRequiresDestroy",
            "MountPoint", "DeviceNode", "SystemImage", "CanBeMadeBootable",
            "SupportsGlobalPermissionsDisable", "VolumeName",
            "DeviceTreePath", "DeviceIdentifier", "VolumeUUID", "Bootable",
            "BusProtocol", "Ejectable", "MediaType", "RAIDSlice",
            "FilesystemName", "RAIDMaster", "WholeDisk", "FreeSpace",
            "TotalSize", "GlobalPermissionsEnabled", "SMARTStatus",
            "Writable", "ParentWholeDisk", "MediaName"]

    for key in keys:
      try:
        attribute = key.lower().replace(" ", "")
        setattr(self, attribute, self._attributes[key])
      # pylint: disable=pointless-except
      except KeyError:  # not all objects have all these attributes
        pass

    if self.busprotocol == "Disk Image":  # pylint: disable=no-member
      self.diskimage = True
    else:
      self.diskimage = False

  def Mounted(self):
    """Is it mounted."""
    try:
      if self.mountpoint:  # pylint: disable=no-member
        return True
      else:
        return False
    except KeyError:
      return False

  def Partitions(self):
    """Child partitions of a whole disk."""
    if not self.wholedisk:  # pylint: disable=no-member
      raise MacDiskError("%s is not a whole disk" % self.deviceid)
    else:
      partitions = []
      for p in PartitionDeviceIds():
        if re.compile("^%ss" % self.deviceid).search(p):
          partitions.append(Disk(p))
      return partitions

  def Info(self):
    """info."""
    return self._attributes

  def Mount(self):
    """Mounts single volumes for partitions, all volumes for whole disks."""
    if self.Mounted():
      raise MacDiskError("%s is already mounted" % self.deviceid)
    else:
      command = ["diskutil", "mount", self.deviceid]
      if self.wholedisk:  # pylint: disable=no-member
        command[1] = "mountDisk"
      rc = gmacpyutil.RunProcess(command)[2]
      if rc == 0:
        self.Refresh()
        return True

  def EnsureMountedWithRefresh(self):
    """Mounts single volumes for partitions, all volumes for whole disks.

    Convenience method so you don't have to test if it's mounted already.

    Returns:
      boolean for success.
    """
    if self.Mounted():
      self.Refresh()
      return True
    else:
      command = ["diskutil", "mount", self.deviceid]
      if self.wholedisk:  # pylint: disable=no-member
        command[1] = "mountDisk"
      rc = gmacpyutil.RunProcess(command)[2]
      if rc == 0:
        self.Refresh()
        return True

  def Unmount(self, force=False):
    """Unounts single volumes for partitions, all volumes for whole disks."""
    if not self.Mounted():
      raise MacDiskError("%s is not mounted" % self.deviceid)
    else:
      command = ["diskutil", "unmount", self.deviceid]
      if force:
        command.insert(2, "force")
      if self.wholedisk:  # pylint: disable=no-member
        command[1] = "unmountDisk"
      rc = gmacpyutil.RunProcess(command)[2]
      if rc == 0:
        self.Refresh()
        return True

  def Rename(self, newname):
    """Renames a single volume."""
    if self.wholedisk:  # pylint: disable=no-member
      raise MacDiskError("Cannot rename whole disk %s" % self.deviceid)
    else:
      command = ["diskutil", "renameVolume", self.deviceid, newname]
      rc = gmacpyutil.RunProcess(command)[2]
      if rc == 0:
        self.Refresh()
        return True

  def EnableJournal(self):
    """enables journalling."""
    if self.wholedisk:  # pylint: disable=no-member
      raise MacDiskError("Cannot enable journal on whole disk: %s" %
                         self.deviceid)
    if self.journalsize:  # pylint: disable=no-member
      raise MacDiskError("%s already has a journal." % self.deviceid)
    else:
      command = ["diskutil", "enableJournal", self.deviceid]
      rc = gmacpyutil.RunProcess(command)[2]
      if rc == 0:
        self.Refresh()
        return True

  def DisableJournal(self):
    """enables journalling."""
    if self.wholedisk:  # pylint: disable=no-member
      raise MacDiskError("Cannot enable journal on whole disk: %s" %
                         self.deviceid)
    if not self.journalsize:  # pylint: disable=no-member
      raise MacDiskError("%s already has no journal." % self.deviceid)
    else:
      command = ["diskutil", "disableJournal", self.deviceid]
      rc = gmacpyutil.RunProcess(command)[2]
      if rc == 0:
        self.Refresh()
        return True

  def SetStartupDisk(self):
    """Sets this disk to be the startup disk."""
    self.Refresh()
    # pylint: disable=no-member
    if not self.Mounted():
      command = ["/usr/sbin/bless", "--device", self.deviceidentifier,
                 "--setBoot"]
    else:
      command = ["/usr/sbin/bless", "--mount", self.mountpoint, "--setBoot"]
    rc = gmacpyutil.RunProcess(command)[2]
    if rc == 0:
      return True

  # TODO(user): methods for: verifyVolume, verifyDisk, repairVolume,
  # repairDisk, verifyPermissions, repairPermissions,
  # repairOS9Permissions (really?), eraseDisk, eraseVolume, reformat,
  # eraseOptical, zeroDisk, randomDisk, secureErase, partitionDisk,
  # resizeVolume, splitPartition, mergePartitions


class Image(object):
  """Represents an unmounted image object."""

  def __init__(self, imagepath, password=None):
    self.imagepath = imagepath
    self.attached = False
    # encrypted images can't refresh without a password
    if isinstance(self, EncryptedImage):
      if password:
        self.Refresh(password)
    else:
      self.Refresh()

  def Refresh(self, password=None):
    """convenience attrs for direct querying really."""

    if isinstance(self, EncryptedImage) and not password:
      raise MacDiskError("Encrypted Images cannot Refresh without a password")

    self._attributes = _DictFromHdiutilImageInfo(self.imagepath, password)
    # We iterate over all known keys
    keys = ["Class Name", "Checksum Type", "Format", "Partition Information",
            "Segments", "Size Information", "Properties",
            "Backing Store Information", "udif-ordered-chunks",
            "Checksum Value", "Format Description", "partitions"]

    for key in keys:
      try:
        attribute = key.lower().replace(" ", "")
        setattr(self, attribute, self._attributes[key])
      # pylint: disable=pointless-except
      except KeyError:  # not all objects have all these attributes
        pass

  def ImageScan(self):
    """ASR image scanning."""
    command = ["asr", "imagescan", "--source", self.imagepath]
    stdout, stderr, returncode = gmacpyutil.RunProcess(command)
    if returncode is not 0:
      raise MacDiskError("Cannot imagescan %s, %s" % (self.imagepath,
                                                      stderr))
    else:
      return stdout

  def Attach(self, password=None, verify=True, browse=True):
    """Attaches a disk image, returns list of Disk objects."""

    if isinstance(self, EncryptedImage) and not password:
      raise MacDiskError("Encrypted Images cannot Attach without a password")

    command = ["hdiutil", "attach", "-plist"]

    if isinstance(self, EncryptedImage):
      command.append("-stdinpass")

    if not verify:
      command.append("-noverify")

    if not browse:
      command.append("-nobrowse")

    command.append(self.imagepath)

    plist = _DictFromSubprocess(command, stdin=password)
    attached_disks = []
    for entity in plist["system-entities"]:
      # strip off /dev from start
      deviceid = entity["dev-entry"].replace("/dev/", "")
      disk = Disk(deviceid)
      attached_disks.append(disk)
    self.attached = True
    self.attached_disks = attached_disks  # for later detaches.
    return attached_disks

  def Detach(self, force=False):
    """Detaches a disk image."""
    images = AttachedImages()
    for image in images:
      if image["image"].imagepath == self.imagepath:
        command = ["hdiutil", "detach"]
        command.append(image["disks"][0].deviceid)
        if force:
          command.append("-force")
        gmacpyutil.RunProcess(command)

  # TODO(user): how much of hdiutil do we really need? convert, burn etc
  # How are we going to cope with a detach that requires the mountpoint?


class EncryptedImage(Image):
  """Represents an unmounted encrypted image object. Password is optional."""

  def AttachWithRecover(self, keychain_path, verify=True):
    """Attaches a disk image with keychain recovery option.

    Args:
      keychain_path: the path to the recovery keychain
      verify: whether to verify the attach.
    Returns:
      disks: a list of Disk objects.
    """
    command = ["hdiutil", "attach", "-plist", "-recover", keychain_path]
    if not verify:
      command.append("-noverify")
    command.append(self.imagepath)
    plist = _DictFromSubprocess(command)
    attached_disks = []
    for entity in plist["system-entities"]:
      # strip off /dev from start
      deviceid = entity["dev-entry"].replace("/dev/", "")
      disk = Disk(deviceid)
      attached_disks.append(disk)
    self.attached = True
    return attached_disks


def _DictFromSubprocess(command, stdin=None):
  """returns a dict based upon a subprocess call with a -plist argument.

  Args:
    command: the command to be executed as a list
    stdin: any standard input required.
  Returns:
    dict: dictionary from command output
  Raises:
    MacDiskError: Error running command
    MacDiskError: Error creating plist from standard output
  """

  task = {}

  if stdin:
    (task["stdout"],
     task["stderr"],
     task["returncode"]) = gmacpyutil.RunProcess(command, stdin)
  else:
    (task["stdout"],
     task["stderr"],
     task["returncode"]) = gmacpyutil.RunProcess(command)

  if task["returncode"] is not 0:
    raise MacDiskError("Error running command: %s, stderr: %s" %
                       (command, task["stderr"]))
  else:
    try:
      return plistlib.readPlistFromString(task["stdout"])
    except xml.parsers.expat.ExpatError:
      raise MacDiskError("Error creating plist from output: %s" %
                         task["stdout"])


def _DictFromDiskutilInfo(deviceid):
  """calls diskutil info for a specific device id.

  Args:
    deviceid: a given device id for a disk like object
  Returns:
    info: dictionary from resulting plist output
  Raises:
    MacDiskError: deviceid is invalid
  """
  # Do we want to do this? can trigger optical drive noises...
  if deviceid not in PartitionDeviceIds():
    raise MacDiskError("%s is not a valid disk id" % deviceid)
  else:
    command = ["/usr/sbin/diskutil", "info", "-plist", deviceid]
    return _DictFromSubprocess(command)


def _DictFromDiskutilList():
  """calls diskutil list -plist and returns as dict."""

  command = ["/usr/sbin/diskutil", "list", "-plist"]
  return _DictFromSubprocess(command)


def _DictFromHdiutilInfo():
  """calls hdiutil info -plist and returns as dict."""

  command = ["/usr/bin/hdiutil", "info", "-plist"]
  return _DictFromSubprocess(command)


def _DictFromHdiutilImageInfo(imagepath, password=None):
  """calls hdiutil imageinfo -plist and returns as dict."""

  if not password:
    command = ["/usr/bin/hdiutil", "imageinfo", "-plist", imagepath]
  else:
    command = ["/usr/bin/hdiutil", "imageinfo", "-encryption", "-stdinpass",
               "-plist", imagepath]

  return _DictFromSubprocess(command, stdin=password)


# Class methods
def PartitionDeviceIds():
  """Returns a list of all device ids that are partitions."""
  try:
    return _DictFromDiskutilList()["AllDisks"]
  except KeyError:
    # TODO(user): fix errors to actually provide info...
    raise MacDiskError("Unable to list all partitions.")


def Partitions():
  """Returns a list of all disk objects that are partitions."""
  partitions = []
  for deviceid in PartitionDeviceIds():
    partitions.append(Disk(deviceid))
  return partitions


def WholeDiskDeviceIds():
  """Returns a list of device ids for all whole disks."""
  try:
    return _DictFromDiskutilList()["WholeDisks"]
  except KeyError:
    # TODO(user): fix errors to actually provide info...
    raise MacDiskError("Unable to list all partitions.")


def WholeDisks():
  """Returns a list of all disk objects that are whole disks."""
  wholedisks = []
  for deviceid in WholeDiskDeviceIds():
    wholedisks.append(Disk(deviceid))
  return wholedisks


def MountedVolumeNames():
  """Get names of all currently attached volumes.

  Returns:
    list of volume names
  Raises:
    MacDiskError: unable to list all volume names
  """
  try:
    return _DictFromDiskutilList()["VolumesFromDisks"]
  except KeyError:
    raise MacDiskError("Unable to list all volumes names.")


def MountedVolumes():
  """Returns a list of all Disk objects that are mounted volumes."""
  volumes = []
  volumenames = MountedVolumeNames()
  for partition in Partitions():
    if partition.volumename in volumenames:
      volumes.append(partition)
  return volumes


def AttachedImages():
  """info about attached images.

  Returns:
    attached_images: a list of dictionaries of attached Image objects and
                     corresponding Disk objects.
  """
  attached_images = []
  images = _DictFromHdiutilInfo()["images"]
  for image in images:
    attached_image = {}
    attached_image["image"] = Image(image["image-path"])
    attached_image["disks"] = []
    for entity in image["system-entities"]:
      if "dev-entry" in entity:
        attached_image["disks"].append(Disk(entity["dev-entry"]))
    attached_images.append(attached_image)
  return attached_images


def UnmountAllDiskImages(detach=True, force=False):
  """Unmounts all currently attached disk images with optional force param.

  Args:
    detach: whether to detach
    force: whether to force the unmount
  """
  for image in AttachedImages():
    if detach:
      image["image"].Detach(force=force)
    else:
      try:
        for disk in image["disks"]:
          if disk.Mounted():
            disk.Unmount(force=force)
      except KeyError:
        pass


def InitalizeVDSB():
  """Initializes/updates the Volume Status Database.

  Returns:
    boolean: whether the operation succeeded.
  """
  command = ["vsdbutil", "-i"]
  rc = gmacpyutil.RunProcess(command)[2]
  if rc == 0:
    return True
  else:
    return False


def Clone(source, target, erase=True, verify=True, show_activity=False):
  """A wrapper around 'asr' to clone one disk object onto another.

  We run with --puppetstrings so that we get non-buffered output that we can
  actually read when show_activity=True.

  Args:
    source: A Disk or Image object.
    target: A Disk object (including a Disk from a mounted Image)
    erase:  Whether to erase the target. Defaults to True.
    verify: Whether to verify the clone operation. Defaults to True.
    show_activity: whether to print the progress to the screen.
  Returns:
    boolean: whether the operation succeeded.
  Raises:
    MacDiskError: source is not a Disk or Image object
    MacDiskError: target is not a Disk object
  """

  if isinstance(source, Image):
    # even attached dmgs can be a restore source as path to the dmg
    source_ref = source.imagepath
  elif isinstance(source, Disk):
    source_ref = "/dev/%s" % source.deviceidentifier
  else:
    raise MacDiskError("source is not a Disk or Image object")

  if isinstance(target, Disk):
    target_ref = "/dev/%s" % target.deviceidentifier
  else:
    raise MacDiskError("target is not a Disk object")

  command = ["/usr/sbin/asr", "restore", "--source", source_ref, "--target",
             target_ref, "--noprompt", "--puppetstrings"]

  if erase:
    # check we can unmount the target... may as well fail here than later.
    if target.Mounted():
      target.Unmount()
    command.append("--erase")

  if not verify:
    command.append("--noverify")

  task = subprocess.Popen(command, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)
  returncode = task.poll()
  if show_activity:
    while returncode < 0:
      print task.stdout.readline().strip()
      returncode = task.poll()

  (unused_stdout, stderr) = task.communicate()

  if task.returncode:
    raise MacDiskError("Cloning Error: %s" % stderr)

  return True

