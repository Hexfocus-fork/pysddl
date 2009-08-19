#!C:\Python24\python.exe


"""A module for translating and manipulating SDDL strings.


  SDDL strings are used by Microsoft to describe ACLs as described in
  http://msdn.microsoft.com/en-us/library/aa379567.aspx.

  Example: D:(A;;CCLCSWLOCRRC;;;AU)(A;;CCLCSWRPLOCRRC;;;PU)
  """

__author__ = 'tojo2000@tojo2000.com (Tim Johnson)'
__version__ = '0.1'
__updated__ = '2008-07-14'

import re
import wmi # Tim Golden's wmi module
           # at http://tgolden.sc.sabren.com/python/wmi.html

re_valid_string = re.compile('^[ADO][ADLU]?\:\(.*\)$')
re_perms = re.compile('\(([^\(\)]+)\)')
re_type = re.compile('^[DOGS]')
re_owner = re.compile('^O:[^:()]+(?=[DGS]:)')
re_group = re.compile('G:[^:()]+(?=[DOS]:)')
re_acl = re.compile('[DS]:.+$')
re_const = re.compile('(\w\w)')
re_non_acl = re.compile('[^:()]+$')

SDDL_TYPE = {'O': 'Owner',
             'G': 'Group',
             'D': 'DACL',
             'S': 'SACL'}

ACCESS = {# ACE Types
          'A' : 'ACCESS_ALLOWED',
          'D' : 'ACCESS_DENIED',
          'OA': 'ACCESS_ALLOWED_OBJECT',
          'OD': 'ACCESS_DENIED_OBJECT',
          'AU': 'SYSTEM_AUDIT',
          'AL': 'SYSTEM_ALARM',
          'OU': 'SYSTEM_AUDIT_OBJECT',
          'OL': 'SYSTEM_ALARM_OBJECT',

          # ACE Flags
          'CI': 'CONTAINER_INHERIT',
          'OI': 'OBJECT_INHERIT',
          'NP': 'NO_PROPAGATE_INHERIT',
          'IO': 'INHERIT_ONLY',
          'ID': 'INHERITED',
          'SA': 'SUCCESSFUL_ACCESS',
          'FA': 'FAILED_ACCESS',

          # Generic Access Rights
          'GA': 'GENERIC_ALL',
          'GR': 'GENERIC_READ',
          'GW': 'GENERIC_WRITE',
          'GX': 'GENERIC_EXECUTE',

          # Standard Access Rights
          'RC': 'READ_CONTROL',
          'SD': 'DELETE',
          'WD': 'WRITE_DAC',
          'WO': 'WRITE_OWNER',

          # Directory Service Object Access Rights
          'RP': 'DS_READ_PROP',
          'WP': 'DS_WRITE_PROP',
          'CC': 'DS_CREATE_CHILD',
          'DC': 'DS_DELETE_CHILD',
          'LC': 'DS_LIST',
          'SW': 'DS_SELF',
          'LO': 'DS_LIST_OBJECT',
          'DT': 'DS_DELETE_TREE',

          # File Access Rights
          'FA': 'FILE_ALL_ACCESS',
          'FR': 'FILE_GENERIC_READ',
          'FW': 'FILE_GENERIC_WRITE',
          'FX': 'FILE_GENERIC_EXECUTE',

          # Registry Access Rights
          'KA': 'KEY_ALL_ACCESS',
          'KR': 'KEY_READ',
          'KW': 'KEY_WRITE',
          'KE': 'KEY_EXECUTE'}


TRUSTEE = {'AO': 'Account Operators',
           'RU': 'Pre-Win2k Compatibility Access',
           'AN': 'Anonymous',
           'AU': 'Authenticated Users',
           'BA': 'Administrators',
           'BG': 'Guests',
           'BO': 'Backup Operators',
           'BU': 'Users',
           'CA': 'Certificate Publishers',
           'CD': 'Certificate Services DCOM Access',
           'CG': 'Creator Group',
           'CO': 'Creator Owner',
           'DA': 'Domain Admins',
           'DC': 'Domain Computers',
           'DD': 'Domain Controllers',
           'DG': 'Domain Guests',
           'DU': 'Domain Users',
           'EA': 'Enterprise Admins',
           'ED': 'Enterprise Domain Controllers',
           'RO': 'Enterprise Read-Only Domain Controllers',
           'WD': 'Everyone',
           'PA': 'Group Policy Admins',
           'IU': 'Interactive Users',
           'LA': 'Local Administrator',
           'LG': 'Local Guest',
           'LS': 'Local Service',
           'SY': 'Local System',
           'NU': 'Network',
           'LW': 'Low Integrity',
           'ME': 'Medium Integrity',
           'HI': 'High Integrity',
           'SI': 'System Integrity',
           'NO': 'Network Configuration Operators',
           'NS': 'Network Service',
           'PO': 'Printer Operators',
           'PS': 'Self',
           'PU': 'Power Users',
           'RS': 'RAS Servers',
           'RD': 'Remote Desktop Users',
           'RE': 'Replicator',
           'RC': 'Restricted Code',
           'SA': 'Schema Administrators',
           'SO': 'Server Operators',
           'SU': 'Service'
           }


class Error(Exception):
  """Generic Error class."""


class InvalidSddlStringError(Error):
  """The input string provided was not a valid SDDL string."""


class InvalidSddlTypeError(Error):
  """The type sepcified must be O, G, D, or S."""


class InvalidAceStringError(Error):
  """The ACE string provided was invalid."""


def TranslateSid(sid_string):
  """Translate a SID string to an account name.

  Args:
    sid_string: a SID in string form

  Returns:
    A string with the account name if the name resolves.
    None if the name is not found.
  """
  account = wmi.WMI().Get('Win32_SID.SID="' + sid_string + '"')

  if account:
    return account.ReferencedDomainName + '\\' + account.AccountName


def SortAceByTrustee(x, y):
  """Custom sorting function to sort SDDL.ACE objects by trustee.

  Args:
    x: first object being compared
    y: second object being compared

  Returns:
    The results of a cmp() between the objects.
  """
  return cmp(x.trustee, y.trustee)


class ACE(object):
  """Represents an access control entry."""

  def __init__(self, ace_string, access_constants):
    """Initializes the SDDL::ACE object.

    Args:
      ace_string: a string representing a single access control entry
      access_constants: a dictionary of access constants for translation

    Raises:
      InvalidAceStringError: If the ace string provided doesn't appear to be
        valid.
    """
    self.ace_string = ace_string
    LOCAL_ACCESS = access_constants
    self.flags = []
    self.perms = []
    fields = ace_string.split(';')

    if len(fields) != 6:
      raise InvalidAceStringError

    if (LOCAL_ACCESS[fields[0]]):
      self.ace_type = LOCAL_ACCESS[fields[0]]
    else:
      self.ace_type = fields[0]

    for flag in re.findall(re_const, fields[1]):
      if LOCAL_ACCESS[flag]:
        self.flags.append(LOCAL_ACCESS[flag])
      else:
        self.flags.append(flag)

    for perm in re.findall(re_const, fields[2]):
      if LOCAL_ACCESS[perm]:
        self.perms.append(LOCAL_ACCESS[perm])
      else:
        self.perms.append(perm)

    self.perms.sort()
    self.object_type = fields[3]
    self.inherited_type = fields[4]
    self.trustee = None

    if TRUSTEE[fields[5]]:
      self.trustee = TRUSTEE[fields[5]]

    if not self.trustee:
      self.trustee = TranslateSid(fields[5])

    if not self.trustee:
      self.trustee = 'Unknown or invalid SID.'


class SDDL(object):
  """Represents an SDDL string."""

  def __init__(self, sddl_string, target=None):
    """Initializes the SDDL object.

    Args:
      input_string: The SDDL string representation of the ACL
      target: Some values of the SDDL string change their meaning depending
        on the type of object they describe.
        Note:  The only supported type right now is 'service'

    Raises:
      SDDLInvalidStringError: if the string doesn't appear to be valid
    """
    self.target = target
    self.sddl_string = sddl_string
    self.sddl_type = None
    self.acl = []
    sddl_owner_part = re.search(re_owner, sddl_string)
    sddl_group_part = re.search(re_group, sddl_string)
    sddl_acl_part = re.search(re_acl, sddl_string)
    self.ACCESS = ACCESS
    self.group_sid = None
    self.group_account = None
    self.owner_sid = None
    self.owner_account = None

    if self.target == 'service':
      self.ACCESS['CC'] = 'Query Configuration'
      self.ACCESS['DC'] = 'Change Configuration'
      self.ACCESS['LC'] = 'Query State'
      self.ACCESS['SW'] = 'Enumerate Dependencies'
      self.ACCESS['RP'] = 'Start'
      self.ACCESS['WP'] = 'Stop'
      self.ACCESS['DT'] = 'Pause'
      self.ACCESS['LO'] = 'Interrogate'
      self.ACCESS['CR'] = 'User Defined'
      self.ACCESS['SD'] = 'Delete'
      self.ACCESS['RC'] = 'Read the Security Descriptor'
      self.ACCESS['WD'] = 'Change Permissions'
      self.ACCESS['WO'] = 'Change Owner'

    for match in (sddl_owner_part, sddl_group_part, sddl_acl_part):
      if not match:
        continue

      part = match.group()
      sddl_prefix = re.match(re_type, part).group()

      if sddl_prefix in ('D', 'S'):
        if sddl_prefix in SDDL_TYPE:
          self.sddl_type = SDDL_TYPE[sddl_prefix]
        else:
          raise InvalidSddlTypeError

        for perms in re.findall(re_perms, part):
          self.acl.append(ACE(perms, self.ACCESS))

      elif (sddl_prefix == 'G'):
        self.group_sid = re.search(re_non_acl, part).group()

        if self.group_sid in TRUSTEE:
          self.group_account = TRUSTEE[self.group_sid]
        else:
          self.group_account = TranslateSid(self.group_sid)

        if not self.group_account:
          self.group_account = 'Unknown'

      elif (sddl_prefix == 'O'):
        self.owner_sid = re.search(re_non_acl, part).group()

        if self.owner_sid in TRUSTEE:
          self.owner_account = TRUSTEE[self.owner_sid]
        else:
          self.owner_account = TranslateSid(self.owner_sid)

        if not self.owner_account:
          self.owner_account = 'Unknown'

      else:
        raise InvalidSddlStringError

