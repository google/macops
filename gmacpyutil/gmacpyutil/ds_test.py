"""Tests for ds module."""

import os

import mox
import stubout

from google.apputils import basetest

import ds


class DsTest(mox.MoxTestBase):

  def setUp(self):
    self.mox = mox.Mox()
    self.mox.StubOutWithMock(ds.gmacpyutil, 'RunProcess')
    if os.uname()[0] == 'Linux':
      self.InitMockFoundation()
    elif os.uname()[0] == 'Darwin':
      self.StubFoundation()

  def tearDown(self):
    self.mox.UnsetStubs()
    self.mox.ResetAll()

  def InitMockFoundation(self):
    mock_nsstring = self.mox.CreateMockAnything()
    ds.NSString = mock_nsstring

  def StubFoundation(self):
    self.mox.StubOutWithMock(ds, 'NSString')

  def _DScmd(self):
    self.path = '/Groups'
    self.key = 'GeneratedUID'
    self.value = 'dummy-uid-blah'
    return [ds._DSCL, '.', '-search', self.path, self.key, self.value]

  def testDSSearchNotFound(self):
    ds.gmacpyutil.RunProcess(self._DScmd()).AndReturn((None, None, None))
    ds.NSString.stringWithString_(mox.IgnoreArg()).AndReturn(None)

    self.mox.ReplayAll()
    result = ds.DSSearch(self.path, self.key, self.value)
    self.mox.VerifyAll()
    self.assertEqual(result, None)

  def testDSSearchError(self):
    ds.gmacpyutil.RunProcess(self._DScmd()).AndReturn(('blah', 'someerror', 5))

    self.mox.ReplayAll()
    self.assertRaises(ds.DSException, ds.DSSearch,
                      self.path, self.key, self.value)
    self.mox.VerifyAll()

  def testDSSearch(self):
    result = 'groupname\t\tblah'
    ds.gmacpyutil.RunProcess(self._DScmd()).AndReturn((result,
                                                       None, 0))

    ds.NSString.stringWithString_(result).AndReturn(result)
    self.mox.ReplayAll()
    res = ds.DSSearch(self.path, self.key, self.value)
    self.mox.VerifyAll()
    self.assertEqual(result, res)

  def testDSGetRecordNameFromUUID(self):
    self.mox.StubOutWithMock(ds, 'DSSearch')
    ds.DSSearch('/Groups',
                'GeneratedUID',
                'dummy-uid',
                node='.').AndReturn('groupname\t\tblah')

    self.mox.ReplayAll()
    group = ds.DSGetRecordNameFromUUID('group', 'dummy-uid')
    self.mox.VerifyAll()
    self.assertEqual(group, 'groupname')

  def testDSGetRecordNameFromUUIDNone(self):
    self.mox.StubOutWithMock(ds, 'DSSearch')
    ds.DSSearch('/Groups',
                'GeneratedUID',
                'dummy-uid',
                node='.').AndReturn(None)

    self.mox.ReplayAll()
    group = ds.DSGetRecordNameFromUUID('group', 'dummy-uid')
    self.mox.VerifyAll()
    self.assertEqual(group, None)

  def testEditLocalGroupBadAction(self):
    self.mox.ReplayAll()
    self.assertRaises(ds.DSException, ds.EditLocalGroup,
                      'badaction', 'group', 'sub', 'parent')
    self.mox.VerifyAll()

  def testEditLocalGroupReturnCode(self):
    action = 'add'
    account = 'someuser'
    recordtype = 'user'
    group = 'somegroup'

    cmd = [ds._DSEDITGROUP, '-o', 'edit', '-n', '.',
           ds._EDITGROUPACTIONS[action], account, '-t', recordtype, group]

    ds.gmacpyutil.RunProcess(cmd).AndReturn(('out', 'errtext', 1))
    self.mox.ReplayAll()
    self.assertRaises(ds.DSException, ds.EditLocalGroup,
                      action, recordtype, account, group)
    self.mox.VerifyAll()

  def testGetNameFromGroupUIDNone(self):
    groupuid = '0000-000'
    self.mox.StubOutWithMock(ds, 'DSGetRecordNameFromUUID')
    ds.DSGetRecordNameFromUUID('group', groupuid).AndReturn(None)
    self.mox.ReplayAll()
    self.assertEqual(ds._GetNameFromGroupUID(groupuid), None)
    self.mox.VerifyAll()

  def testGetNameFromGroupUIDError(self):
    groupuid = '0000-000'
    self.mox.StubOutWithMock(ds, 'DSGetRecordNameFromUUID')
    ds.DSGetRecordNameFromUUID('group', groupuid).AndReturn(None)
    ds.DSGetRecordNameFromUUID('group',
                               groupuid,
                               node='/LDAPv3/blah').AndRaise(
                                   ds.DSException('something'))
    self.mox.ReplayAll()
    self.assertEqual(ds._GetNameFromGroupUID(groupuid,
                                             ldap_server='blah'), None)
    self.mox.VerifyAll()

  def testGetGroupMembership(self):
    groupname = 'somegroup'
    members = [u'asdf', u'asdfaaa']
    guids = [u'000-111-aaa', u'121123-aaaa']
    ldap = 'ldap.corp'
    self.mox.StubOutWithMock(ds, '_GetNameFromGroupUID')
    self.mox.StubOutWithMock(ds, 'DSQuery')

    ds.DSQuery('group', groupname,
               attribute='GroupMembership').AndReturn(members)
    ds.DSQuery('group', groupname,
               attribute='NestedGroups').AndReturn(guids)

    ds._GetNameFromGroupUID(guids[0], ldap_server=ldap).AndReturn(None)
    ds._GetNameFromGroupUID(guids[1],
                            ldap_server=ldap).AndReturn('humanreadable')
    self.mox.ReplayAll()
    result = ds.GetGroupMembership(groupname, ldap_server=ldap)
    self.assertEqual(result, (members, [guids[0], 'humanreadable']))
    self.mox.VerifyAll()

  def testGetGroupMembershipError(self):
    groupname = 'somegroup'
    ldap = 'ldap.corp'
    self.mox.StubOutWithMock(ds, 'DSQuery')

    ds.DSQuery('group', groupname,
               attribute='GroupMembership').AndRaise(ds.DSException)
    ds.DSQuery('group', groupname,
               attribute='NestedGroups').AndRaise(ds.DSException)

    self.mox.ReplayAll()
    result = ds.GetGroupMembership(groupname, ldap_server=ldap)
    self.assertEqual(result, ('UNKNOWN', 'UNKNOWN'))
    self.mox.VerifyAll()

  def testGetGroupMembershipEmptyGroup(self):
    groupname = 'somegroup'
    ldap = 'ldap.corp'
    self.mox.StubOutWithMock(ds, 'DSQuery')

    ds.DSQuery('group', groupname,
               attribute='GroupMembership').AndReturn(None)
    ds.DSQuery('group', groupname,
               attribute='NestedGroups').AndReturn(None)

    self.mox.ReplayAll()
    result = ds.GetGroupMembership(groupname, ldap_server=ldap)
    self.assertEqual(result, (None, None))
    self.mox.VerifyAll()

  def testDSList(self):
    dscl_list_output = ('_www\n'
                        '_xcsbuildagent\n'
                        '_xcscredserver\n'
                        'daemon\n'
                        'yes\n'
                        'nobody\n'
                        'puppet\n'
                        'root\n')
    cmd = [ds._DSCL, '.', '-list', '/Users']
    ds.gmacpyutil.RunProcess(cmd).AndReturn(
        (dscl_list_output, '', 0))
    self.mox.ReplayAll()
    result = ds.DSList('user')
    self.assertEqual(result, dscl_list_output.rstrip('\n').split('\n'))
    self.mox.VerifyAll()

if __name__ == '__main__':
  basetest.main()
