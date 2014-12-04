#!/usr/bin/env python
"""List, determine, and modify experiment status.

This can be used either as a module or standalone.
"""

import csv
import hashlib
import logging
import optparse
import os
import re
import sys

from . import gmacpyutil
from . import defaults
from . import systemconfig
import yaml


# knobs for experiments
MANUAL_ON_KNOB = 'ManuallyEnabledExperiments'
MANUAL_OFF_KNOB = 'ManuallyDisabledExperiments'
EXPERIMENTS_KNOB = 'EnableExperiments'
DEFAULT_USEFUL_KNOBS = (EXPERIMENTS_KNOB,
                        MANUAL_ON_KNOB,
                        MANUAL_OFF_KNOB)


EXPERIMENT_KEY = 'experiments'
PERCENT_KEY = 'percent'
START_KEY = 'begin_date'
OBSOLETE_KEY = 'obsolete_after'
OWNER_KEY = 'owner'
DESCRIPTION_KEY = 'description'
ENABLE_UNSTABLE = 'enable_unstable'
ENABLE_TESTING = 'enable_testing'
REQUIRED_FIELDS = (OWNER_KEY, PERCENT_KEY, START_KEY)
OPTIONAL_FIELDS = (OBSOLETE_KEY, DESCRIPTION_KEY, ENABLE_UNSTABLE,
                   ENABLE_TESTING)
ALL_FIELDS = REQUIRED_FIELDS + OPTIONAL_FIELDS


# Where we store experiments
EXP_FILENAME = defaults.EXPERIMENTS_YAML

# Experiment status values
ENABLED, DISABLED = ('enabled', 'disabled')

# Experiment source values (or why a given experiment has a given status.
ALWAYS, NEVER, MANUAL, AUTO = 'always', 'never', 'manually', 'automatically'

# Experiment source values continued:
RECOMMENDED = 'recommended'

# How many pieces do we want to divide the fleet into?
MOD_VALUE = 10000  # seems to work for now (gives us .01% granularity)


class ExperimentsError(Exception):
  pass


class InvalidData(ExperimentsError):
  pass


class InvalidExperiment(ExperimentsError):
  pass


class MissingUUID(ExperimentsError):
  pass


class PlistError(ExperimentsError):
  pass


class ExperimentListFetcher(object):
  """Wrapper around fetching experiment data.

  Generally errors will not be obvious until the GetData phase in which case an
  InvaldData exception will be raised.

  data.valid == True implies that data.parsed exists.
  data.valid == False implies that the data is bad and you should not use it.
  """

  def __init__(self, path):
    self.data = None
    self.path = path

  def _Fetch(self):
    self.data = type('obj', (object,), dict(valid=False, parsed=None))
    try:
      self.data.data = open(self.path, 'rb').read()
    except IOError, e:
      logging.debug('Failed to read experiment file: %s', self.path)
      self.data = None
      raise ExperimentsError(e.message)

  def _Parse(self):
    """Ensure the class data is valid."""
    if self.data is not None:
      try:
        logging.debug('yaml.safe_load(...)')
        self.data.parsed = yaml.safe_load(self.data.data)
      except yaml.YAMLError:
        logging.warning('Error parsing YAML.')
        self.data.parsed = None

      if self.data.parsed is not None:
        try:
          self.data.serial = self.data.parsed.get('serial', None)
          self.data.experiments = self.data.parsed.get('experiments', {})
        except (AttributeError, ExperimentsError):
          logging.warning('Caught exception while parsing self.data.')
          self.data.valid = False
          return

        logging.debug('Parsed YAML data is valid')
        self.data.valid = True
      else:
        logging.debug('Problem parsing YAML data')
        self.data.valid = False
    else:
      logging.error('No data to parse!')

  def GetData(self):
    """Return parsed and valid experiments data."""
    try:
      logging.debug('Fetching data from YAML')
      self._Fetch()
    except ExperimentsError, e:
      raise InvalidData(e.message)
    logging.debug('Parsing data')
    self._Parse()
    if not self.data or not self.data.valid:
      logging.error('Data not valid after parsing')
      raise InvalidData
    return self.data


class Knobs(object):
  """Caching class for reading knobs.

  Usage:
    k = Knobs()
    k.Knobs()
  """

  def __init__(self, knobs_list=DEFAULT_USEFUL_KNOBS):
    self._knobs_list = knobs_list
    self._knobs = {}
    self._valid = False

  def Knobs(self):
    """Get knobs from plist if they haven't been fetched already.

    Returns:
      a dictionary containing the knobs data.
    """
    if not self._valid:
      logging.debug('Getting knobs')
      self._knobs = self._GetKnobs()
      self._valid = True
    return self._knobs

  def _GetKnobs(self):
    """Gets values of specific knobs.

    Returns:
      a dict of knobs.
    """
    knobs = {}
    for knob in self._knobs_list:
      data = gmacpyutil.MachineInfoForKey(knob)
      if data:
        if knob in (MANUAL_ON_KNOB, MANUAL_OFF_KNOB):
          knobs[knob] = ConvertCSVStringToList(data)
        else:
          knobs[knob] = data
    return knobs


# Global instance of Knobs class
KNOBS = Knobs(DEFAULT_USEFUL_KNOBS)


def ExperimentIsBucket(experiment, exp_data, mach_uuid):
  """Determine if a given experiment is enabled for a certname.

  Args:
    experiment: a string identifier for the experiment.
    exp_data: a dict containing experiment data (yaml.load(...))
    mach_uuid: A machine UUID provided by sendsysinfo.

  Returns:
    an instance with three attributes, status, source, and rollout_percent
  Raises:
    InvalidExperiment: an invalid experiment
    ExperimentsError: couldn't coerce hash to integer
  """

  ret = type('obj', (object,), dict(status=None, source=AUTO))
  data = exp_data.get(experiment)
  if not data:
    raise InvalidExperiment('%s is not in %s.' % (experiment, exp_data))

  try:
    rollout_percent = float(data.get(PERCENT_KEY, 0))
    logging.debug('Got rollout_percent: %s.', rollout_percent)
  except ValueError:
    logging.warning('Could not parse rollout_percent, using 0.')
    rollout_percent = 0

  ret.rollout_percent = rollout_percent

  try:
    exp_hash = int(hashlib.sha256(experiment + mach_uuid).hexdigest(), 16)
  except ValueError:
    logging.warning('Could not coerce hash to integer.')
    raise ExperimentsError('Could not determine bucket for host.')

  bucket = exp_hash % MOD_VALUE
  logging.debug('Bucket is %s, rollout_percent is %s.', bucket, rollout_percent)
  if bucket * 100 / float(MOD_VALUE) < rollout_percent:
    ret.status = ENABLED
  else:
    ret.status = DISABLED
  return ret


def GetExperimentStatus(experiment, knobs, exp_data, track='stable'):
  """Determine the status and source of a given experiment.

  Take into account all ways that a given experiment may be enabled and allow
  the client to determine why a given experiment has a particular status.

  Experiments at 100% are always on.
  If the machine is set to ignore experiments, it will ignore any experiments
  not at 100%.
  If the machine is set to always apply experiments, the experiment will be on.
  If the machine is in an explicitly enabled track, the experiment will be on.
  If the machine is manually opted in or out, that option is applied.
  Otherwise the bucket algorithm is applied.

  Args:
    experiment: a string identifier for a given experiment.
    knobs: knobs for a host (in dict form)
    exp_data: a dict containing experiment data (yaml.load(...))
    track: a string of the machine's release track
  Returns:
    an object with three attributes, status, source, and rollout_percent
  """
  ReturnEarly = lambda ret: ret.source is not None  # pylint: disable=g-bad-name

  ret = type('obj', (object,), {})
  ret.status = DISABLED
  ret.source = None
  ret.rollout_percent = float(exp_data.get(experiment, {}).get(PERCENT_KEY, -1))

  if ret.rollout_percent == 100:
    logging.debug('Experiment %s is at 100%%, enabling', experiment)
    ret.status = ENABLED
    ret.source = ALWAYS
    return ret

  auto_knob = knobs.get(EXPERIMENTS_KNOB, 'recommended')
  if auto_knob == ALWAYS:
    ret.status = ENABLED
    ret.source = ALWAYS
  elif auto_knob == NEVER:
    ret.status = DISABLED
    ret.source = ALWAYS
  if ReturnEarly(ret): return ret

  manual_on_knob = knobs.get(MANUAL_ON_KNOB, [])
  manual_off_knob = knobs.get(MANUAL_OFF_KNOB, [])
  if experiment in manual_on_knob:
    ret.status = ENABLED
    ret.source = MANUAL
  elif experiment in manual_off_knob:
    ret.status = DISABLED
    ret.source = MANUAL
  if ReturnEarly(ret): return ret

  enable_unstable = exp_data.get(experiment, {}).get(ENABLE_UNSTABLE, False)
  enable_testing = exp_data.get(experiment, {}).get(ENABLE_TESTING, False)
  if ((track == 'testing' and enable_testing) or
      (track == 'unstable' and (enable_unstable or enable_testing))):
    ret.status = ENABLED
    ret.source = ALWAYS
  if ReturnEarly(ret): return ret

  try:
    mach_uuid = FetchUUID()
  except ExperimentsError, e:
    raise MissingUUID(e)
  logging.debug('Found uuid %s', mach_uuid)
  return ExperimentIsBucket(experiment, exp_data, mach_uuid)


def InExperiment(exp_name, experiments):
  """Check if we are in a given experiment.

  Args:
    exp_name: str, name of experiment
    experiments: dict, dictionary of experiments
  Returns:
    tuple of bool, if host in exp_name, and str, source of experiment status
  """
  in_experiment = False
  source = 'unknown'
  knobs = KNOBS.Knobs()
  track = gmacpyutil.GetTrack()

  if experiments:
    try:
      retval = GetExperimentStatus(exp_name, knobs, experiments, track=track)
      if retval.status == ENABLED:
        in_experiment = True
      source = retval.source
    except (InvalidExperiment, MissingUUID):
      pass
  return in_experiment, source


def GetExperiments():
  """Try to fetch a new set of experiment data. Perform verification.

  Returns:
    An object containing experiments or None.
  """
  fetcher = ExperimentListFetcher(EXP_FILENAME)
  try:
    return fetcher.GetData().experiments
  except InvalidData:
    return None


def FetchUUID():
  """Return our UUID.

  Returns:
    a string UUID
  Raises:
    ExperimentsError: machine UUID is malformed
  """
  uuid_regex = r'^[A-F0-9]{8}-([A-F0-9]{4}-){3}[A-F0-9]{12}$'
  uuid = gmacpyutil.MachineInfoForKey('MachineUUID')
  if not uuid:
    logging.info('No MachineUUID found, trying platform UUID')
    sp = systemconfig.SystemProfiler()
    uuid = sp.GetHWUUID()
  if isinstance(uuid, basestring) and re.match(uuid_regex, uuid):
    return uuid
  else:
    raise ExperimentsError('Malformed UUID: %s' % uuid)


def AddExperimentToManualList(experiment, knob):
  """Adds an experiment to the ManuallyEnabledExperiments knob.

  Args:
    experiment: str, the experiment name to add.
    knob: str, the manual knob to modify
  Raises:
    PlistError: if the plist can't be modified.
  """
  knobs = KNOBS.Knobs()
  current_value = knobs.get(knob, [])
  if knob in knobs and experiment in current_value:
    Output('%s is already in %s.' % (experiment, knob))
  else:
    current_value.append(experiment)
    Output('New value of %s is %s' % (knob, ','.join(current_value)))
    if not gmacpyutil.SetMachineInfoForKey(knob, ','.join(current_value)):
      raise PlistError('Problem writing to plist.')


def RemoveExperimentFromManualList(experiment, knob):
  """Removes an experiment from the ManuallyDisabledExperiments knob.

  Args:
    experiment: str, the experiment name to remove.
    knob: str, the manual knob to modify
  Raises:
    PlistError: if the plist can't be modified.
  """
  knobs = KNOBS.Knobs()
  if knob not in knobs:
    Output('%s list is empty, nothing to remove.' % knob)
  else:
    current_value = knobs.get(knob, [])
    if experiment in current_value:
      current_value.remove(experiment)
      Output('New value of %s is %s' % (knob, ','.join(current_value)))
      if not gmacpyutil.SetMachineInfoForKey(knob, ','.join(current_value)):
        raise PlistError('Problem writing to plist.')
    else:
      Output('%s is not in %s.' % (experiment, knob))


def ConvertCSVStringToList(csv_string):
  """Helper to convert a csv string to a list."""
  reader = csv.reader([csv_string])
  return list(reader)[0]


def ConvertListToCSVString(csv_list):
  """Helper to convert a list to a csv string."""
  return ','.join(str(s) for s in csv_list)


def ModifyManualList(action, knob_list, experiments):
  """Modify the manually enabled/disabled lists.

  Args:
    action: string, action to take, either add or remove.
    knob_list: list of manual setting knobs to modify
    experiments: string, comma-delimited string of experiments to add or remove
  Raises:
    ValueError: an invalid action was requested.
  """
  experiments = '' if experiments is None else experiments
  exp_list = ConvertCSVStringToList(experiments)
  for experiment in exp_list:
    for knob in knob_list:
      if action == 'add':
        AddExperimentToManualList(experiment, knob)
      elif action == 'remove':
        RemoveExperimentFromManualList(experiment, knob)
      else:
        raise ValueError('%s is not a valid action.')


def ParseOptions(argv):
  """Parse command-line options."""
  parser = optparse.OptionParser(usage='%prog [options]')
  parser.add_option('-D', '--debug', action='store_true', default=False)
  parser.add_option('-F', '--formatted', action='store_true', default=False,
                    help=('Output experiments as one "experiment,status" '
                          'per line'))
  parser.add_option(
      '-e', '--enable', action='store', dest='manually_enable',
      help='Comma-delimited list of experiments to manually enable.')
  parser.add_option(
      '-d', '--disable', action='store', dest='manually_disable',
      help='Comma-delimited list of experiments to manually enable.')
  parser.add_option(
      '-r', '--recommended', action='store', dest='recommended',
      help='Comma-delimited list of experiments to no longer manually manage.')
  opts, args = parser.parse_args(argv)
  return opts, args


def Output(text):
  """Wrap print so it's mockable for testing."""
  print text


def main(argv):
  opts, _ = ParseOptions(argv)
  if opts.debug:
    gmacpyutil.ConfigureLogging(debug_level=logging.DEBUG, stderr=opts.debug)
  else:
    gmacpyutil.ConfigureLogging()
  if opts.formatted and (
      opts.manually_enable or opts.manually_disable or opts.recommended):
    Output('--formatted and --enable/--disable cannot be used together.')
    raise SystemExit(1)

  if opts.manually_enable or opts.manually_disable or opts.recommended:
    if os.geteuid() != 0:
      Output('Need to be root to change knobs, try again with sudo')
      raise SystemExit(2)
    try:
      # Manually enabled experiments should be added to MANUAL_ON_KNOB and
      # removed from MANUAL_OFF_KNOB
      ModifyManualList('add', [MANUAL_ON_KNOB], opts.manually_enable)
      ModifyManualList('remove', [MANUAL_OFF_KNOB], opts.manually_enable)
      # Manually disabled experiments should be added to MANUAL_OFF_KNOB and
      # removed from MANUAL_ON_KNOB
      ModifyManualList('add', [MANUAL_OFF_KNOB], opts.manually_disable)
      ModifyManualList('remove', [MANUAL_ON_KNOB], opts.manually_disable)
      # Experiments reset to recommended should be removed from both
      # MANUAL_ON_KNOB and MANUAL_OFF_KNOB
      ModifyManualList('remove', [MANUAL_ON_KNOB, MANUAL_OFF_KNOB],
                       opts.recommended)
    except PlistError, e:
      Output(e.message)
      raise SystemExit(3)
  else:
    experiments = GetExperiments()
    if experiments:
      for experiment in experiments:
        status, source = InExperiment(experiment, experiments)
        if opts.formatted:
          Output('%s,%s' % (experiment,
                            str(status).lower()))
        else:
          percent = experiments[experiment]['percent']
          description = experiments[experiment].get('description',
                                                    'No description')
          status_string = 'enabled' if status else 'disabled'
          Output('%s: %s, at %.1f%% rollout, %s on this host %s'  % (
              experiment, description, percent, status_string, source))
    else:
      if not opts.formatted:
        Output('No experiments are currently running.')


if __name__ == '__main__':
  sys.exit(main(sys.argv))
