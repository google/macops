#!/usr/bin/python2.7

"""One-stop image creation script.

This script generates a catalog based on what is currently on the package
source and compares it with the current catalog. If they differ,
a new image is created with the latest packages available.
"""



import datetime
import hashlib
from optparse import OptionParser
import os
import re
import shutil
import subprocess
import sys
import urllib2


BUILD = 'build/can_haz_image'
TMPDIR = '/tmp/pkgs'
TMPINDEX = os.path.join(TMPDIR, 'tmp_index.html')
FREE_SPACE = 30000


def RunProcess(cmd, stream_out=False):
  """Runs a command and returns a tuple of stdout, stderr, returncode."""
  if stream_out:
    task = subprocess.Popen(cmd)
  else:
    task = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
  (stdout, stderr) = task.communicate()
  return stdout, stderr, task.returncode


class CanHazImage(object):
  """Object creating a new image."""

  def __init__(self, location, webserver, pkgsource):
    self.cwd = os.getcwd()
    self.missing = []
    self.pkgsource = pkgsource
    self.webserver = webserver
    self.catalog = ''
    self.thirdparty = ''
    self.changes = False
    self.thirdparty_location = location
    self.image_creation_time = datetime.datetime.now().strftime('%Y%m%d%H%M')
    self.os_version = RunProcess(['sw_vers'])[0].split('\t')[2][:4]
    self.installer_choices = '%s_InstallerChoices.xml' % self.os_version
    self.newimagepath = ''

  def CreateCatalogNames(self, catalog_name):
    """Generates catalog names."""
    self.new_catalogfile = '%s%s_new.catalog' % (catalog_name, self.os_version)
    self.old_catalogfile = '%s%s_old.catalog' % (catalog_name, self.os_version)

  def NewCatalog(self, catalog_name):
    """Generates a new catalog with the latest packages."""
    self.CreateCatalogNames(catalog_name)
    print ('Generating new %s catalog - this may take a while. (up to 10 mins)'
           % catalog_name)
    self.newcatalog = []
    if catalog_name == 'base':
      pkgsrc = os.path.join(self.pkgsource, self.os_version, 'base')
    elif catalog_name == 'thirdparty':
      if self.thirdparty_location == '':  # pylint: disable-msg=C6403
        pkgsrc = os.path.join(self.pkgsource, self.os_version)
        self.thirdparty_location = pkgsrc
      else:
        pkgsrc = self.thirdparty_location
    else:
      print 'Unknown catalog name: %s' % catalog_name
      raise SystemExit

    linegen = LineGenerator(pkgsrc)
    print 'Generating catalog for %s' % pkgsrc
    print 'Generating catalog checksums and lines...'
    linegen.GenAllLines()

    for line in linegen.catalog_lines:
      last_pkg = line.split()[1]

    old_pkg = ''
    old_line = ''
    pkgname = ''

    for line in linegen.catalog_lines:
      pkg = line.split()[1]
      try:
        date = re.findall('-([0-9]+).dmg', pkg)
        if date:
          if len(date[0]) == 8 or len(date[0]) == 12:
            pkgname = os.path.basename(line.split(date[0])[0])
        if old_pkg != pkgname:
          self.newcatalog.append(old_line)
        if pkg == last_pkg:
          # Add last line
          self.newcatalog.append(line)
        old_pkg = pkgname
      except AttributeError:
        pass
      if catalog_name == 'base' and pkg != last_pkg:
        self.newcatalog.append(line)
      old_line = line

    self.RenameCatalog(catalog_name)
    self.WriteCatalog()

  def RenameCatalog(self, catalog_name):
    """Renames existing generated catalog files."""
    new_catalog = '%s%s_new.catalog' % (catalog_name, self.os_version)
    old_catalog = '%s%s_old.catalog' % (catalog_name, self.os_version)
    if os.path.exists(new_catalog):
      try:
        os.rename(new_catalog, old_catalog)
        print '%s renamed' % new_catalog
      except OSError, e:
        print ('Could not rename catalog! Check file permissions in your '
               'build directory!')
        print 'Error: %s' % e
        raise SystemExit

  def WriteCatalog(self):
    """Writes the catalog file to disk."""
    try:
      f = open(self.new_catalogfile, 'w')
      print 'Writing %s to disk...' % self.new_catalogfile
      for line in self.newcatalog:
        if line:
          f.write('%s\n' % line)
      f.close()
    except IOError, e:
      print ('Writing new catalog failed! Check file permissions in your '
             'build directory!')
      print 'Error: %s' % e
      raise SystemExit

  def CompareCatalogs(self):
    """Checks if there were changes between the new and existing catalogs."""
    try:
      if self.GetFileChecksum(self.new_catalogfile) != self.GetFileChecksum(
          self.old_catalogfile):
        self.changes = True
    except IOError:
      self.changes = True

  def GetFileChecksum(self, filepath):
    """Generates checksum of given file.

    Args:
      filepath: String of filepath.

    Returns:
      f_hash: SHA1 hash for the file provided in filepath.
    """
    f_content = open(filepath, 'r').read()
    f_hash = hashlib.sha1(f_content).hexdigest()
    return f_hash

  def CheckRequirements(self):
    """Checks prerequisites for image building."""
    supported_versions = ['10.6', '10.7', '10.8', '10.9']
    if self.os_version not in supported_versions:
      print 'You\'re running an unsupported version of OS X.'
      sys.exit()
    if not os.path.exists(os.path.join(self.cwd, self.installer_choices)):
      print ('Could not find %s - please reinstall can_haz_image!' %
             self.installer_choices)
      sys.exit()

  def GetBaseImage(self, baseimage=None):
    """Downloads the base installer dmg."""
    baseos_path = os.path.join(self.cwd, BUILD,
                               'BaseOS')
    baseos_dmg = os.path.join(self.cwd, BUILD,
                              'BaseOS/Mac OS X Install DVD.dmg')
    try:
      os.mkdir(baseos_path)
    except OSError:
      pass
    if not os.path.exists(baseos_dmg):
      print 'Base image not found, getting latest one.'
      if not baseimage:
        src = os.path.join(self.webserver, 'osx_base',
                           '%s-default-base.dmg' % self.os_version)
      else:
        src = baseimage
      tgt = os.path.join(self.cwd, BUILD, 'BaseOS/Mac OS X Install DVD.dmg')

      self.DownloadFile(src, tgt)

  def GetBuildPackages(self):
    """Downloads the packages to be installed."""
    package_path = os.path.join(self.cwd, BUILD, 'Packages/')
    try:
      os.mkdir(package_path)
    except OSError:
      pass
    catalogs = [os.path.join(self.cwd, 'base%s_new.catalog' % self.os_version),
                os.path.join(self.cwd,
                             'thirdparty%s_new.catalog' % self.os_version)]

    for catalog in catalogs:
      f = open(catalog, 'r')
      packages = f.readlines()
      for line in packages:
        shutil.copy(os.path.join(TMPDIR, line.split()[0]),
                    os.path.join(package_path, line.split()[0]))

  def DownloadFile(self, fileurl, dlfile):
    """Download a file."""
    try:
      file_to_dl = urllib2.urlopen(fileurl)
      tmpfile = open(dlfile, 'wb')
      shutil.copyfileobj(file_to_dl, tmpfile)
    except urllib2.URLError, e:
      print 'Download of %s failed with error %s' % (fileurl, e)
      sys.exit()
    except IOError, e:
      print 'Could not write %s to disk; check disk permissions!' % dlfile
      print 'Error: %s' % e
      sys.exit()

  def CreateSparseBundle(self):
    """Creates the sparsebundle to install OS X into."""
    sparsebundle_path = os.path.join(self.cwd, BUILD, 'new.sparsebundle')
    if os.path.exists(sparsebundle_path):
      shutil.rmtree(sparsebundle_path)
    cmd = ['hdiutil', 'create', sparsebundle_path, '-size', '20G', '-volname',
           'MacintoshHD', '-layout', 'GPTSPUD', '-fs', 'JHFS+', '-mode',
           '775', '-uid', '0', '-gid', '80']
    (unused_stdout, stderr, unused_rc) = RunProcess(cmd)
    if stderr:
      print 'Failed to create sparsebundle at %s: %s' % (sparsebundle_path,
                                                         stderr)
      raise SystemExit
    else:
      return sparsebundle_path

  def InstallOSX(self, mounted_sparsebundle, mounted_image):
    """Installs OS X into sparsebundle."""
    install_choices = os.path.join(self.cwd, self.installer_choices)
    print 'InstallerChoices.xml: %s' % install_choices
    cmd = ['installer', '-pkg', '%s/Packages/OSInstall.mpkg' %  mounted_image,
           '-target', mounted_sparsebundle, '-applyChoiceChangesXML',
           install_choices]
    print 'Installing OS X into %s...' % mounted_sparsebundle
    (unused_stdout, unused_stderr, unused_rc) = RunProcess(cmd, stream_out=True)
    cmd = ['hdiutil', 'detach', mounted_image]
    (unused_stdout, stderr, unused_rc) = RunProcess(cmd)
    if stderr:
      print 'Failed to unmount: %s' % stderr

  def MountOSXInstallESD(self):
    """Mounts OS X installer disk."""
    baseimage_path = os.path.join(self.cwd, BUILD,
                                  'BaseOS/Mac OS X Install DVD.dmg')
    cmd = ['hdiutil', 'attach', baseimage_path]
    print 'Mounting installer disk %s' % baseimage_path
    (stdout, stderr, unused_rc) = RunProcess(cmd)
    if stderr:
      print 'Unable to mount %s: %s' % (baseimage_path, stderr)
      raise SystemExit
    else:
      return stdout.split('\n')[-2].split('\t')[-1]

  def MountSparseBundle(self, sb):
    """Mounts sparsebundle for installation."""
    cmd = ['hdiutil', 'attach', '-owners', 'on', sb]
    print 'Mounting sparsebundle %s' % sb
    (stdout, stderr, unused_rc) = RunProcess(cmd)
    if stderr:
      print 'Unable to mount sparsebundle %s: %s' % (sb, stderr)
    else:
      return stdout.split('\n')[-2].split('\t')[-1]

  def InstallPackages(self, pkgpath, mounted_sparsebundle):
    """Installs all packages in pkgpath into sparsebundle."""
    package_report = []
    for (path, unused_dirs, files) in os.walk(pkgpath):
      for f in files:
        print 'Installing %s into %s' % (f, mounted_sparsebundle)
        cmd = ['hdiutil', 'attach', os.path.join(path, f)]
        (stdout, stderr, unused_rc) = RunProcess(cmd)
        if stderr:
          package_report.append('Failure mounting %s: %s' % (f, stderr))
        else:
          mountpoint = stdout.split('\n')[-2].split('\t')[-1]
          # If there's any folder in that dmg that looks like a valid app
          # we'll copy it to /Applications
          apps_to_install = []
          for item in os.listdir(mountpoint):
            app_path = os.path.join(mountpoint, item)
            if not os.path.islink(app_path) and app_path.endswith('.app'):
              apps_to_install.append(item)

          if apps_to_install:
            # If we go this route, this is an bundled app
            for app in apps_to_install:
              cmd = ['cp', '-pR', os.path.join(mountpoint, app),
                     os.path.join(mounted_sparsebundle, 'Applications')]
              (stdout, stderr, rc) = RunProcess(cmd)
              if rc == 0:
                print('Successfully copied %s to %s' %
                      (app, mounted_sparsebundle))
                package_report.append('Successfully copied %s to %s' %
                                      (app, mounted_sparsebundle))
              else:
                print('Failed to copy %s to %s due to %s' %
                      (app, mounted_sparsebundle, stderr))
                package_report.append('Failed to copy %s to %s due to %s' %
                                      (app, mounted_sparsebundle, stderr))
                return package_report
          else:
            # This route is for .pkgs
            package = '%s.pkg' % mountpoint.split('/')[-1]
            if not os.path.exists(os.path.join(mountpoint, package)):
              for (unused_packagepath, dirs, content) in os.walk(mountpoint):
                for filename in content:
                  if filename.endswith('.pkg') or filename.endswith('.mpkg'):
                    package = filename
                    print 'Nonstandard package: %s/%s' % (mountpoint, package)
                for dirname in dirs:
                  if dirname.endswith('.pkg') or dirname.endswith('.mpkg'):
                    package = dirname
                    print 'Nonstandard package: %s/%s' % (mountpoint, package)
            cmd = ['installer', '-pkg', os.path.join(mountpoint, package),
                   '-target', mounted_sparsebundle, '-verboseR']
            (stdout, stderr, unused_rc) = RunProcess(cmd)
            if stderr:
              package_report.append('Failure installing %s: %s' % (package,
                                                                   stderr))
            else:
              package_report.append('Success installing %s' % package)
        cmd = ['hdiutil', 'detach', mountpoint]
        (unused_stdout, stderr, unused_rc) = RunProcess(cmd)
        if stderr:
          print 'Failed to unmount dmg: %s' % f

    return package_report

  def WriteImageInfo(self, mounted_sparsebundle, package_report):
    """Writes information about the image to a plist file in the image."""
    imageinfo = ('%s/etc/imageinfo.plist' % mounted_sparsebundle)

    cmd = ['defaults', 'write', imageinfo, 'ImageVersion',
           '-string', self.image_creation_time]
    (unused_stdout, stderr, rc) = RunProcess(cmd)
    if rc:
      print 'Failed to write ImageVersion: %s' % stderr

    cmd = ['defaults', 'write', imageinfo, 'ImageMethod',
           '-string', 'can_haz_image']
    (unused_stdout, stderr, rc) = RunProcess(cmd)
    if rc:
      print 'Failed to write ImageMethod: %s' % stderr

    for package in package_report:
      cmd = ['defaults', 'write', imageinfo, 'ImagePackages',
             '-array-add', package]
      (unused_stdout, stderr, rc) = RunProcess(cmd)
      if rc:
        print 'Failed to write ImagePackages: %s' % stderr

    # chmod to 0644, chown to root:wheel
    os.chmod(imageinfo, 0644)
    os.chown(imageinfo, 0, 0)

  def ConvertSparseBundle(self, mounted_sparsebundle, sb):
    """Detaches the sparsebundle and converts to installable disk image."""
    print 'Detaching sparsebundle %s' % mounted_sparsebundle
    cmd = ['hdiutil', 'detach', '-force', mounted_sparsebundle]
    (unused_stdout, stderr, unused_rc) = RunProcess(cmd)
    if stderr:
      print 'Unable to detach sparsebundle %s: %s' % (mounted_sparsebundle, sb)
    else:
      if self.thirdparty_location.endswith('/'):
        from_location = os.path.basename(self.thirdparty_location[:-1])
      else:
        from_location = os.path.basename(self.thirdparty_location)
      image_name = '%s_%s.dmg' % (from_location, self.image_creation_time)
      image_file = os.path.join(self.cwd, BUILD, image_name)
      cmd = ['hdiutil', 'convert', sb, '-format', 'UDZO', '-o', image_file]
      (unused_stdout, stderr, unused_rc) = RunProcess(cmd)
      if stderr:
        print 'Image conversion went wrong: %s' % stderr
      else:
        print 'ASR imagescanning the new image'
        cmd = ['asr', 'imagescan', '-source', image_file]
        RunProcess(cmd)
        return image_file

  def BuildImage(self, baseimage=None):
    """Actually build the image."""
    sb = self.CreateSparseBundle()
    mounted_sparsebundle = self.MountSparseBundle(sb)
    self.GetBaseImage(baseimage)
    mounted_image = self.MountOSXInstallESD()
    self.InstallOSX(mounted_sparsebundle, mounted_image)
    self.GetBuildPackages()
    pkgs = os.path.join(self.cwd, BUILD, 'Packages/')
    pkgreport = self.InstallPackages(pkgs, mounted_sparsebundle)
    self.WriteImageInfo(mounted_sparsebundle, pkgreport)
    image_file = self.ConvertSparseBundle(mounted_sparsebundle, sb)
    self.CleanUp(sb, image_file)
    self.PrintReport(pkgreport)
    self.newimagepath = image_file
    print ('Created new image: %s' % os.path.join(BUILD,
                                                  os.path.basename(image_file)))
    if os.path.exists(os.path.join(self.cwd, 'lastimage')):
      os.unlink(os.path.join(self.cwd, 'lastimage'))
    f = open(os.path.join(self.cwd, 'lastimage'), 'w')
    f.write('/Users/Shared/can_haz_image/%s' % os.path.basename(image_file))
    f.close()

  def CleanUp(self, sb, image_file):
    try:
      shutil.rmtree(sb)
    except OSError, e:
      print 'Could not remove sparsebundle %s: %s' % (sb, e)
    for (path, dirs, files) in os.walk(os.path.join(self.cwd, BUILD)):
      for f in files:
        if f != os.path.basename(image_file):
          try:
            os.unlink(os.path.join(path, f))
          except OSError, e:
            print 'Could not remove file %s: %s' % (f, e)
      for d in dirs:
        if not (d == 'BaseOS' or d == 'Packages'):
          try:
            os.rmdir(os.path.join(path, d))
          except OSError, e:
            print 'Could not remove directory %s: %s' % (d, e)

  def PrintReport(self, pkgreport):
    """Prints a report of installed packages."""
    print 'Packages installed:\n'
    for item in pkgreport:
      print '%s' % item


class ChiConfig(object):
  """Storage of configuration parameters."""

  def __init__(self):
    self.webserver = ''
    self.pkgsource = ''
    self.config_info = {}
    self.configured_settings = []

  def ReadConfig(self):
    """Reads configuration parameters from file."""
    f = open(os.path.join(os.getcwd(), 'chi.config'), 'r')
    config = f.readlines()
    for line in config:
      self.config_info[line.split('=')[0]] = line.split('=')[1].strip()
    f.close()

  def SetupConfig(self):
    """Creates/Alters configuration file."""
    if os.path.exists(os.path.join(os.getcwd(), 'chi.config')):
      self.ReadConfig()
      (webserver, pkgsource) = self.ConfigQuestionnaire()
    else:
      (webserver, pkgsource) = self.ConfigQuestionnaire()
      f = open(os.path.join(os.getcwd(), 'chi.config'), 'w')
      content = 'webserver=%s\npkgsource=%s' % (webserver, pkgsource)
      f.write(content)
      f.close()

  def ConfigQuestionnaire(self):
    """Gets user input for configuration parameters."""
    for item in self.config_info:
      self.configured_settings.append(item)
    if 'webserver' in self.configured_settings:
      webserver = self.config_info['webserver']
    else:
      webserver = 'example: http://www.yourserver.com'
    question = ('Please provide the URL for the server you store your'
                ' images and packages on.\nCurrent setting: %s' % webserver)
    prompt = 'Server URL: '
    unanswered = True
    while unanswered:
      try:
        userinput = self.GetUserInput(question, prompt)
      except KeyboardInterrupt:
        print 'Ctrl+C pressed; aborting configuration setup.'
        sys.exit()
      # pylint: disable-msg=C6403
      if userinput != '' and not userinput.startswith('example:'):
      # pylint: enable-msg=C6403
        webserver = userinput
        unanswered = False
      elif userinput == '' or userinput.startswith('example:'):
        question = 'You did not provide a URL - please try again.'

    if 'pkgbase' in self.configured_settings:
      pkgbase = self.config_info['pkgbase']
    else:
      pkgbase = 'example: http://www.yourserver.com/packages'
    question = ('Please provide the URL for the server containing the'
                ' packages you wish to install in your images.\n'
                'Current setting: %s' % pkgbase)
    prompt = 'Server URL: '
    unanswered = True
    while unanswered:
      try:
        userinput = self.GetUserInput(question, prompt)
      except KeyboardInterrupt:
        print 'Ctrl+C pressed; aborting configuration setup.'
        sys.exit()
      # pylint: disable-msg=C6403
      if userinput != '' and not userinput.startswith('example:'):
      # pylint: enable-msg=C6403
        pkgbase = userinput
        unanswered = False
      elif userinput != '' and userinput.startswith('example:'):
        question = 'You did not provide a URL - please try again.'

    return (webserver, pkgbase)

  def GetUserInput(self, question, prompt):
    """Asks user for input."""
    print question
    return raw_input('%s' % prompt)

  def SetupBuildFolder(self):
    buildpath = os.path.join(os.getcwd(), BUILD)
    try:
      os.mkdir(buildpath)
    except OSError:
      try:
        os.mkdir(os.path.dirname(buildpath))
        os.mkdir(buildpath)
      except OSError:
        print 'Unable to create build folder %s' % buildpath

  def CheckDiskSpace(self):
    stat = os.statvfs('/Users')
    free_space_mb = (stat.f_bavail * stat.f_frsize) / 1048576
    if free_space_mb < FREE_SPACE:
      print ('You have less than 30GB of free disk space.\n'
             ' Depending on what you\'re installing into the image, '
             'that may not be enough.')
      sys.exit()


class LineGenerator(object):
  """Collection of functions for generating catalog lines."""

  def __init__(self, pkgsrc):
    if not os.path.isdir(TMPDIR):
      os.mkdir(TMPDIR)
    self.source = pkgsrc
    self.pkgs = []
    self.catalog_lines = []

  def DownloadFile(self, fileurl, dlfile):
    """Downloads a given file to a given path/filename.

    Args:
      fileurl: String with URL of file to download.
      dlfile: String with path of file to be written to.
    Raises:
      OSError: If file cannot be opened/written to, function raises OSError.
      URLError: If URL cannot be opened, fucntion raises URLError.
    """
    if not os.path.isfile(dlfile) or dlfile == TMPINDEX:
      print 'Downloading %s ...' % fileurl
      file_to_dl = urllib2.urlopen(fileurl)
      tmpfile = open(dlfile, 'wb')
      shutil.copyfileobj(file_to_dl, tmpfile)
    else:
      print '%s exists' % dlfile

  def GetPackages(self):
    for pkg in self.pkgs:
      self.DownloadFile(os.path.join(self.source, pkg),
                        os.path.join(TMPDIR, pkg))

  def GetIndex(self):
    self.DownloadFile(self.source, TMPINDEX)

  def ParseIndex(self):
    """Finds pkg names on lines containing one."""
    f = open(TMPINDEX, 'r')
    index = f.read().splitlines()

    for line in index:
      if line.rfind('href') != -1:
        pkg = line.split('href=')[1].split('\"')[1]
        if pkg.endswith('dmg'):
          self.pkgs.append(pkg)

  def GetFileChecksum(self, filepath):
    """Generates checksum of given file.

    Args:
      filepath: String of filepath.

    Returns:
      f_hash: SHA1 hash for the file provided in filepath.
    """
    statinfo = os.stat(filepath)
    if statinfo.st_size/1048576 < 200:
      f_content = open(filepath, 'r').read()
      f_hash = hashlib.sha1(f_content).hexdigest()
      return f_hash
    else:
      cmd = ['shasum', filepath]
      (stdout, unused_sterr, unused_rc) = RunProcess(cmd)
      return stdout.split()[0]

  def GenerateLines(self):
    for pkg in self.pkgs:
      checksum = self.GetFileChecksum(os.path.join(TMPDIR, pkg))
      catalog_line = '\t%s\t%s\tsha1:%s' % (pkg, os.path.join(self.source, pkg),
                                            checksum)
      self.catalog_lines.append(catalog_line)

  def PrintLines(self):
    for line in self.catalog_lines:
      print line

  def GenAllLines(self):
    self.GetIndex()
    self.ParseIndex()
    self.GetPackages()
    self.GenerateLines()


def main():
  parser = OptionParser(usage='Usage: sudo %prog [options]')
  parser.add_option('-c', '--catalog', dest='filename',
                    help='Specify custom package location (URL)')
  parser.add_option('-t', '--test', dest='test', action='store_true',
                    help='Don\'t build image, just build new catalogs')
  parser.add_option('-b', '--baseimage', dest='baseimage',
                    help='Specify a custom base image (URL)')
  parser.add_option('-f', '--force', dest='force', action='store_true',
                    help='Build new image even if catalogs are unchanged')
  parser.add_option('-C', '--configure', dest='configure', action='store_true',
                    help='Set up configuration for build environment')
  (options, unused_args) = parser.parse_args()

  if not os.path.exists(os.path.join(os.getcwd(), 'chi.config')):
    options.configure = True
  if os.getuid() != 0:
    print 'Must be run as root!'
    parser.print_help()
    sys.exit(1)
  if options.filename:
    catalog_location = options.filename
  else:
    catalog_location = ''
  chiconfig = ChiConfig()
  if not os.path.exists(os.path.join(os.getcwd(), BUILD)):
    chiconfig.SetupBuildFolder()
  if options.configure:
    if os.path.exists(os.path.join(os.getcwd(), 'chi.config')):
      os.unlink(os.path.join(os.getcwd(), 'chi.config'))
    chiconfig.SetupConfig()
  chiconfig.ReadConfig()
  chi = CanHazImage(catalog_location, chiconfig.config_info['webserver'],
                    chiconfig.config_info['pkgsource'])
  chi.CheckRequirements()
  chi.NewCatalog('base')
  if not options.force:
    chi.CompareCatalogs()
  else:
    chi.changes = True
  chi.NewCatalog('thirdparty')
  if not options.force:
    chi.CompareCatalogs()
  if chi.changes:
    if options.test:
      print 'Running in test mode, skipping build phase.'
    else:
      chi.BuildImage(options.baseimage)
  else:
    print 'No changes, not building new image.'

if __name__ == '__main__':
  main()
