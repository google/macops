"""Unit tests for macdisk module."""


import mox
import stubout

from google.apputils import app
from google.apputils import basetest

import macdisk


class MacdiskModuleTest(mox.MoxTestBase):
  """Test macdisk module-level functions."""

  def setUp(self):
    mox.MoxTestBase.setUp(self)
    self.stubs = stubout.StubOutForTesting()

  def tearDown(self):
    self.mox.UnsetStubs()
    self.stubs.UnsetAll()

  def testAttachedImages(self):
    """Test AttachedImages."""
    self.mox.StubOutWithMock(macdisk, 'Disk')
    self.mox.StubOutWithMock(macdisk, 'Image')
    self.mox.StubOutWithMock(macdisk, '_DictFromHdiutilInfo')
    mock_hdiutilinfodict = {
        'images': [
            {'system-entities': [
                {'dev-entry': '/dev/disk1'}, {'dev-entry': '/dev/disk1s1'},
                {'mount-point': '/Volumes/Some-Image',
                 'dev-entry': '/dev/disk1s2'}
                ],
             'image-path': '/tmp/Some-Image.dmg'}]}
    macdisk._DictFromHdiutilInfo().AndReturn(mock_hdiutilinfodict)
    macdisk.Image('/tmp/Some-Image.dmg').AndReturn('image')
    macdisk.Disk('/dev/disk1').AndReturn('/dev/disk1')
    macdisk.Disk('/dev/disk1s1').AndReturn('/dev/disk1s1')
    macdisk.Disk('/dev/disk1s2').AndReturn('/dev/disk1s2')

    self.mox.ReplayAll()
    ai = macdisk.AttachedImages()
    self.assertTrue(isinstance(ai, list))
    self.assertEqual(len(ai), 1)
    self.assertTrue(isinstance(ai[0], dict))
    self.assertTrue('image' in ai[0])
    self.assertTrue('disks' in ai[0])
    self.assertEqual(ai[0]['image'], 'image')
    self.assertTrue(isinstance(ai[0]['disks'], list))
    self.assertEqual(ai[0]['disks'][0], '/dev/disk1')
    self.assertEqual(ai[0]['disks'][1], '/dev/disk1s1')
    self.assertEqual(ai[0]['disks'][2], '/dev/disk1s2')
    self.mox.VerifyAll()

  def testUnmountAllDiskImagesDetachTrue(self):
    """Test UnmountAllDiskImages."""
    detach = True
    force = False
    self.mox.StubOutWithMock(macdisk, 'AttachedImages')
    mock_image = self.mox.CreateMockAnything()
    mock_image.Detach(force=force).AndReturn(None)
    mock_disk = self.mox.CreateMockAnything()
    macdisk.AttachedImages().AndReturn([{'image': mock_image,
                                         'disks': [mock_disk]}])
    self.mox.ReplayAll()
    self.assertEqual(macdisk.UnmountAllDiskImages(detach=detach, force=force),
                     None)
    self.mox.VerifyAll()

  def testUnmountAllDiskImagesDetachFalse(self):
    """Test UnmountAllDiskImages."""
    detach = False
    force = False
    self.mox.StubOutWithMock(macdisk, 'AttachedImages')
    mock_image = self.mox.CreateMockAnything()
    mock_disk = self.mox.CreateMockAnything()
    macdisk.AttachedImages().AndReturn([{'image': mock_image,
                                         'disks': [mock_disk]}])
    mock_disk.Mounted().AndReturn(True)
    mock_disk.Unmount(force=force).AndReturn(None)
    self.mox.ReplayAll()
    self.assertEqual(macdisk.UnmountAllDiskImages(detach=detach, force=force),
                     None)
    self.mox.VerifyAll()


class ImageTest(mox.MoxTestBase):
  """Test macdisk.Image class."""

  def setUp(self):
    mox.MoxTestBase.setUp(self)
    self.stubs = stubout.StubOutForTesting()

  def tearDown(self):
    self.mox.UnsetStubs()
    self.stubs.UnsetAll()

  def testImageScanSuccess(self):
    """Test successful ImageScan."""
    self.mox.StubOutWithMock(macdisk.Image, 'Refresh')
    self.mox.StubOutWithMock(macdisk.gmacpyutil, 'RunProcess')
    command = ['asr', 'imagescan', '--source', 'imagepath']
    stdout = 'stdout'
    stderr = 'stderr'
    returncode = 0
    macdisk.gmacpyutil.RunProcess(command).AndReturn(
        (stdout, stderr, returncode))
    macdisk.Image.Refresh().AndReturn(None)
    self.mox.ReplayAll()
    img = macdisk.Image('imagepath')
    self.assertEqual(img.ImageScan(), 'stdout')
    self.mox.VerifyAll()

  def testImageScanFailure(self):
    """Test failed ImageScan."""
    self.mox.StubOutWithMock(macdisk.Image, 'Refresh')
    self.mox.StubOutWithMock(macdisk.gmacpyutil, 'RunProcess')
    command = ['asr', 'imagescan', '--source', 'imagepath']
    stdout = 'stdout'
    stderr = 'stderr'
    returncode = 1
    macdisk.gmacpyutil.RunProcess(command).AndReturn(
        (stdout, stderr, returncode))
    macdisk.Image.Refresh().AndReturn(None)
    self.mox.ReplayAll()
    img = macdisk.Image('imagepath')
    self.assertRaises(macdisk.MacDiskError, img.ImageScan)
    self.mox.VerifyAll()

  def testAttach(self):
    """Test for default Attach."""
    password = None
    verify = True
    browse = True
    self.mox.StubOutWithMock(macdisk, '_DictFromSubprocess')
    self.mox.StubOutWithMock(macdisk.Image, 'Refresh')
    self.mox.StubOutWithMock(macdisk, 'Disk')

    command = ['hdiutil', 'attach', '-plist', 'imagepath']
    plist = {'system-entities': [{'dev-entry': '/dev/disk1s2'},
                                 {'dev-entry': '/dev/disk1s1'},
                                 {'dev-entry': '/dev/disk1'}]}

    macdisk._DictFromSubprocess(command, stdin=password).AndReturn(plist)
    macdisk.Disk('disk1s2').AndReturn('disk1s2')
    macdisk.Disk('disk1s1').AndReturn('disk1s1')
    macdisk.Disk('disk1').AndReturn('disk1')
    macdisk.Image.Refresh().AndReturn(None)

    self.mox.ReplayAll()
    img = macdisk.Image('imagepath')
    disks = img.Attach(password=password, verify=verify, browse=browse)
    self.assertEqual(set(disks), set(['disk1', 'disk1s1', 'disk1s2']))
    self.mox.VerifyAll()

  def testDetach(self):
    """Test Detach."""
    force = False
    self.mox.StubOutWithMock(macdisk.gmacpyutil, 'RunProcess')
    self.mox.StubOutWithMock(macdisk, 'AttachedImages')
    self.mox.StubOutWithMock(macdisk.Image, 'Refresh')

    class MockDisk(object):

      def __init__(self, deviceid):
        self.deviceid = deviceid

    class MockImage(object):

      def __init__(self, imagepath):
        self.imagepath = imagepath

    attachedimages = [{'image': MockImage('matched_path'),
                       'disks': [MockDisk('matched_deviceid')]},
                      {'image': MockImage('unmatched_path'),
                       'disks': [MockDisk('unmatched_deviceid')]}]
    macdisk.Image.Refresh().AndReturn(None)
    macdisk.AttachedImages().AndReturn(attachedimages)
    macdisk.gmacpyutil.RunProcess(['hdiutil', 'detach',
                                   'matched_deviceid']).AndReturn(None)

    self.mox.ReplayAll()
    img = macdisk.Image('matched_path')
    self.assertEqual(None, img.Detach(force=force))
    self.mox.VerifyAll()


def main(unused_argv):
  basetest.main()


if __name__ == '__main__':
  app.run()
