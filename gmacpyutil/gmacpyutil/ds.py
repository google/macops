"""Module to read and configure directoryservice related data."""

import filecmp
from optparse import OptionParser
import os
import plistlib
import shutil

# pylint: disable=g-import-not-at-top
try:
  from Foundation import NSString
except ImportError:
  if os.uname()[0] == 'Linux':
    import sys
    print >>sys.stderr, 'Skipping Mac imports for later mock purposes.'
    del sys
  else:
    raise

from . import gmacpyutil
# pylint: enable=g-import-not-at-top

_DSCL = '/usr/bin/dscl'
_DSCACHEUTIL = '/usr/bin/dscacheutil'
_DSEDITGROUP = '/usr/sbin/dseditgroup'
_EDITGROUPACTIONS = {'add': '-a', 'delete': '-d'}


class DSException(Exception):
  """Module specific error class."""
  pass


def FlushCache():
  """Flushes the DirectoryService cache."""
  command = [_DSCACHEUTIL, '-flushcache']
  gmacpyutil.RunProcess(command)


def _GetCSPSearchPathForPath(path):
  """Returns list of search nodes for a given path.

  Args:
    path: One of '/Search' or '/Search/Contacts' only.
  Returns:
    nodes: list of search nodes for given path.
  Raises:
    DSException: Unable to retrieve search nodes in path.
  """

  command = [_DSCL, '-plist', path, '-read', '/', 'CSPSearchPath']
  (stdout, stderr, unused_returncode) = gmacpyutil.RunProcess(command)
  result = plistlib.readPlistFromString(stdout)
  if 'dsAttrTypeStandard:CSPSearchPath' in result:
    search_nodes = result['dsAttrTypeStandard:CSPSearchPath']
    return search_nodes
  else:
    raise DSException('Unable to retrieve search nodes: %s' % stderr)


def _ModifyCSPSearchPathForPath(action, node, path):
  """Modifies the search nodes for a given path.

  Args:
    action: one of (["append", "delete"]) only.
    node: the node to append or delete.
    path: the DS path to modify.
  Returns:
    True on success
  Raises:
    DSException: Could not modify nodes for path.
  """

  command = [_DSCL, path, '-%s' % action, '/', 'CSPSearchPath', node]
  (unused_stdout, stderr, returncode) = gmacpyutil.RunProcess(command)
  if returncode:
    raise DSException('Unable to perform %s on CSPSearchPath '
                      'for node: %s on path: %s '
                      'Error: %s '% (action, node, path, stderr))
  return True


def GetSearchNodes():
  """Returns search nodes for DS /Search path."""
  return _GetCSPSearchPathForPath('/Search')


def GetContactsNodes():
  """Returns search nodes for DS /Search/Contacts path."""
  return _GetCSPSearchPathForPath('/Search/Contacts')


def AddNodeToSearchPath(node):
  """Adds a given DS node to the /Search path."""
  _ModifyCSPSearchPathForPath('append', node, '/Search')


def AddNodeToContactsPath(node):
  """Adds a given DS node to the /Search/Contacts path."""
  _ModifyCSPSearchPathForPath('append', node, '/Search/Contacts')


def DeleteNodeFromSearchPath(node):
  """Deletes a given DS node from the /Search path."""
  _ModifyCSPSearchPathForPath('delete', node, '/Search')


def DeleteNodeFromContactsPath(node):
  """Deletes a given DS node from the /Search/Contacts path."""
  _ModifyCSPSearchPathForPath('delete', node, '/Search/Contacts')


def EnsureSearchNodePresent(node):
  """Ensures a given DS node is present in the /Search path."""
  if node not in GetSearchNodes():
    AddNodeToSearchPath(node)


def EnsureSearchNodeAbsent(node):
  """Ensures a given DS node is absent from the /Search path."""
  if node in GetSearchNodes():
    DeleteNodeFromSearchPath(node)


def EnsureContactsNodePresent(node):
  """Ensures a given DS node is present in the /Search/Contacts path."""
  if node not in GetContactsNodes():
    AddNodeToContactsPath(node)


def EnsureContactsNodeAbsent(node):
  """Ensures a given DS node is absent from the /Search path."""
  if node in GetContactsNodes():
    DeleteNodeFromContactsPath(node)


def DSQuery(dstype, objectname, attribute=None):
  """DirectoryServices query.

  Args:
    dstype: The type of objects to query. user, group.
    objectname: the object to query.
    attribute: the optional attribute to query.
  Returns:
    If an attribute is specified, the value of the attribute. Otherwise, the
    entire plist.
  Raises:
    DSException: Cannot query DirectoryServices.
  """
  ds_path = '/%ss/%s' % (dstype.capitalize(), objectname)
  cmd = [_DSCL, '-plist', '.', '-read', ds_path]
  if attribute:
    cmd.append(attribute)
  (stdout, stderr, returncode) = gmacpyutil.RunProcess(cmd)
  if returncode:
    raise DSException('Cannot query %s for %s: %s' % (ds_path,
                                                      attribute,
                                                      stderr))
  plist = NSString.stringWithString_(stdout).propertyList()
  if attribute:
    value = None
    if 'dsAttrTypeStandard:%s' % attribute in plist:
      value = plist['dsAttrTypeStandard:%s' % attribute]
    elif attribute in plist:
      value = plist[attribute]
    try:
      # We're copying to a new list to convert from NSCFArray
      return value[:]
    except TypeError:
      # ... unless we can't
      return value
  else:
    return plist


def DSSearch(path, key, value, node='.'):
  cmd = [_DSCL, node, '-search', path, key, value]
  (stdout, stderr, returncode) = gmacpyutil.RunProcess(cmd)
  if returncode:
    raise DSException('Cannot search %s for %s:%s. %s' % (path,
                                                          key,
                                                          value,
                                                          stderr))
  return NSString.stringWithString_(stdout)


def DSList(dstype, objectname=None):
  """List a directory from DS.

  dscl -plist . -list returns text, not a plist, so no -plist here.

  Args:
    dstype: The type of objects to list. user, group.
    objectname: the object to query.
  Returns:
    a list of users
  Raises:
    ds.DSException: Cannot query DirectoryServices
  """
  ds_path = '/%ss' % dstype.capitalize()
  if objectname:
    ds_path = ds_path + '/' + objectname
  cmd = [_DSCL, '.', '-list', ds_path]
  stdout, stderr, rc = gmacpyutil.RunProcess(cmd)
  if rc:
    raise DSException('Cannot list %s: %s' % (ds_path, stderr))
  if stdout:
    return stdout.rstrip('\n').split('\n')
  return []


def DSGetRecordNameFromUUID(dstype, uuid, node='.'):
  search_result = DSSearch('/%ss' % (dstype.capitalize()), 'GeneratedUID', uuid,
                           node=node)
  if search_result:
    return search_result.split('\t')[0]
  else:
    return None


def DSSet(dstype, objectname, attribute=None, value=None):
  """DirectoryServices attribute set.

  This uses dscl create, which overwrites any existing objects or attributes.

  Args:
    dstype: The type of objects to query. user, group.
    objectname: the object to set.
    attribute: the optional attribute to set.
    value: the optional value to set, only handles strings and simple lists
  Raises:
    DSException: Cannot modify DirectoryServices.
  """
  ds_path = '/%ss/%s' % (dstype.capitalize(), objectname)
  cmd = [_DSCL, '.', '-create', ds_path]
  if attribute:
    cmd.append(attribute)
    if value:
      if type(value) == type(list()):
        cmd.extend(value)
      else:
        cmd.append(value)
  (unused_stdout, stderr, returncode) = gmacpyutil.RunProcess(cmd)
  if returncode:
    raise DSException('Cannot set %s for %s: %s' % (attribute,
                                                    ds_path,
                                                    stderr))


def DSAppend(dstype, objectname, attribute, value):
  """DirectoryServices attribute append.

  This uses dscl append, which appends one or more values to a property in a
  given record. The property is created if it does not exist.

  Args:
    dstype: The type of objects to query. user, group.
    objectname: the object to append under.
    attribute: the attribute to append a value to.
    value: the value to append, only handles strings and simple lists
  Raises:
    DSException: Cannot modify DirectoryServices.
  """
  ds_path = '/%ss/%s' % (dstype.capitalize(), objectname)
  cmd = [_DSCL, '.', '-append', ds_path, attribute]
  if type(value) == type(list()):
    cmd.extend(value)
  else:
    cmd.append(value)
  (unused_stdout, stderr, returncode) = gmacpyutil.RunProcess(cmd)
  if returncode:
    raise DSException('Cannot append %s for %s: %s' % (attribute,
                                                       ds_path,
                                                       stderr))


def DSDelete(dstype, objectname, attribute=None, value=None):
  """DirectoryServices attribute delete.

  Args:
    dstype: The type of objects to delete. user, group.
    objectname: the object to delete.
    attribute: the attribute to delete.
    value: the value to delete
  Raises:
    DSException: Cannot modify DirectoryServices.
  """
  ds_path = '/%ss/%s' % (dstype.capitalize(), objectname)
  cmd = [_DSCL, '.', '-delete', ds_path]
  if attribute:
    cmd.append(attribute)
    if value:
      cmd.extend([value])
  (unused_stdout, stderr, returncode) = gmacpyutil.RunProcess(cmd)
  if returncode:
    raise DSException('Cannot delete %s for %s: %s' % (attribute,
                                                       ds_path,
                                                       stderr))


def UserAttribute(username, attribute):
  """Returns the requested DirectoryService attribute for this user.

  Args:
    username: the user to retrieve a value for.
    attribute: the attribute to retrieve.
  Returns:
    the value of the attribute.
  """
  return DSQuery('user', username, attribute)


def GroupAttribute(groupname, attribute):
  """Returns the requested DirectoryService attribute for this group.

  Args:
    groupname: the group to retrieve a value for.
    attribute: the attribute to retrieve.
  Returns:
    the value of the attribute.
  """
  return DSQuery('group', groupname, attribute)


def EditLocalGroup(action, recordtype, account, group):
  """Edit a local DirectoryService group.

  Args:
    action: dsedit group action parameter -a, -d
    recordtype: group, user
    account: username or groupname to be added/deleted
    group: target group to be modified
  Returns:
    Nothing
  Raises:
    DSException: Can't perform group edit
  """
  if action in _EDITGROUPACTIONS:
    operation = _EDITGROUPACTIONS[action]
  else:
    raise DSException('Unsupported dseditgroup action %s' % action)

  cmd = [_DSEDITGROUP, '-o', 'edit', '-n', '.',
         operation, account, '-t', recordtype, group]
  (stdout, stderr, rc) = gmacpyutil.RunProcess(cmd)
  if rc is not 0:
    raise DSException('Error modifying group %s with %s %s -t %s,'
                      'returned %s\n%s' %
                      (group, operation, account, recordtype, stdout, stderr))


def AddUserToLocalGroup(username, group):
  """Adds user to a local group, uses dseditgroup to deal with GUIDs.

  Args:
    username: user to add
    group: local group to add user to
  Returns:
    Nothing
  Raises:
    DSException: Can't add user to group
  """
  EditLocalGroup('add', 'user', username, group)


def RemoveUserFromLocalGroup(username, group):
  """Removes user from a local group, uses dseditgroup to deal with GUIDs.

  Args:
    username: user to remove
    group: local group to remove user from
  Returns:
    Nothing
  Raises:
    DSException: Can't remove user from group
  """
  EditLocalGroup('delete', 'user', username, group)


def AddGroupToLocalGroup(newgroup, group):
  """Adds newgroup to a local group, uses dseditgroup.

  Args:
    newgroup: group to add
    group: local group to add newgroup to
  Returns:
    Nothing
  Raises:
    DSException: Can't add newgroup to group
  """
  EditLocalGroup('add', 'group', newgroup, group)


def RemoveGroupFromLocalGroup(delgroup, group):
  """Removes delgroup from a local group, uses dseditgroup to deal with GUIDs.

  Args:
    delgroup: group to remove
    group: local group to remove delgroup from
  Returns:
    Nothing
  Raises:
    DSException: Can't remove delgroup from group
  """
  EditLocalGroup('delete', 'group', delgroup, group)


def CreateShadowAccount(username, shadow_name):
  """Creates a shadow user account."""
  shadow_account = {'PrimaryGID': '80', 'UniqueID': '497',
                    'RealName': '%s Admin' % username,
                    'AuthenticationAuthority': ';ShadowHash;',
                    'NFSHomeDirectory': '/var/empty', 'UserShell': '/bin/bash'}

  DSSet('user', shadow_name)

  for key in shadow_account:
    DSSet('user', shadow_name, key, shadow_account[key])

  AddUserToLocalGroup(shadow_name, 'admin')
  AddUserToLocalGroup(shadow_name, '_appserveradm')
  AddUserToLocalGroup(shadow_name, '_lpadmin')


def SyncShadowHash(username, shadow_name):
  """Sync the password hash for the shadow admin account with the user's."""
  shadow_guid = UserAttribute(shadow_name, 'GeneratedUID')
  user_hash = '/var/db/shadow/hash/%s' % username
  if not os.path.exists(user_hash):
    user_guid = UserAttribute(username, 'GeneratedUID')[0]
    user_hash = '/var/db/shadow/hash/%s' % user_guid
  shadow_hash = '/var/db/shadow/hash/%s' % shadow_guid[0]

  try:
    if (os.path.exists(shadow_hash)
        and os.path.isfile(shadow_hash)
        and filecmp.cmp(user_hash, shadow_hash, shallow=False)):
      # everything is as should be
      pass
    else:
      shutil.copy2(user_hash, shadow_hash)
  except (IOError, OSError), err:
    raise DSException('Error creating the shadow admin hash for '
                      '%s-admin: %s' % (username, err))


def _GetNameFromGroupUID(groupuid, ldap_server=None):
  """Get a human readable name from a groupuid, try ldap_server if provided.

  Try resolving the uid locally, then with ldap if a server is specified.

  Args:
    groupuid: UID to resolve
    ldap_server: use ldap_server if defined
  Returns:
    human-readable name or None if it couldn't be resolved
  """
  name = None
  try:
    name = DSGetRecordNameFromUUID('group', groupuid)
    if not name and ldap_server:
      name = DSGetRecordNameFromUUID('group',
                                     groupuid,
                                     node='/LDAPv3/%s' % ldap_server)
  except DSException:
    pass
  return name


def GetGroupMembership(groupname, ldap_server=None):
  """Get membership of a group.

  Args:
    groupname: name of the group to query
    ldap_server: use this LDAP server to try to convert nested group UUIDs to
                 human-readable form.

  Returns:
    (membership, groups)
    membership: group members array, 'UNKNOWN' on error
    groups: array of human readable nested group names, 'UNKNOWN' on error
  """
  try:
    membership = DSQuery('group', groupname, attribute='GroupMembership')
  except DSException:
    membership = 'UNKNOWN'

  try:
    nested_groups = DSQuery('group', groupname, attribute='NestedGroups')
    if nested_groups:
      groups = []
      for groupuid in nested_groups:
        groupname = _GetNameFromGroupUID(groupuid,
                                         ldap_server=ldap_server)
        if not groupname:
          groupname = groupuid

        groups.append(groupname)
    else:
      groups = None
  except DSException:
    groups = 'UNKNOWN'

  return membership, groups


# Provide a basic main so we can call this from a puppet fact
def main():
  parser = OptionParser()
  parser.add_option('-e', '--expandgroup', dest='groupname',
                    help='Get group membership')
  parser.add_option('-l', '--ldapserver', dest='ldap_server',
                    help='LDAP server to query for nested groups',
                    default=None)
  (options, unused_args) = parser.parse_args()
  if options.groupname:
    print GetGroupMembership(options.groupname, ldap_server=options.ldap_server)
  else:
    parser.print_help()

if __name__ == '__main__':
  main()
