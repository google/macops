"""Tests for experiments module."""

import mock
from google.apputils import basetest
import experiments


EXP_NAME = 'experiment_name'
TEST_UUID = 'test_uuid'

SAMPLE_0_EXPERIMENT = {EXP_NAME: {'owner': 'owner', 'percent': 0,
                                  'description': '0 percent'}}
SAMPLE_P1_EXPERIMENT = {EXP_NAME: {'owner': 'owner', 'percent': 0.1,
                                   'description': '0.1 percent'}}
SAMPLE_50_EXPERIMENT = {EXP_NAME: {'owner': 'owner', 'percent': 50,
                                   'description': '50 percent'}}
SAMPLE_100_EXPERIMENT = {EXP_NAME: {'owner': 'owner', 'percent': 100,
                                    'description': '100 percent'}}
SAMPLE_UNSTABLE_EXPERIMENT = {EXP_NAME: {'owner': 'owner', 'percent': 0,
                                         'description': 'unstable',
                                         'enable_unstable': True}}
SAMPLE_TESTING_EXPERIMENT = {EXP_NAME: {'owner': 'owner', 'percent': 0,
                                        'description': 'testing',
                                        'enable_testing': True}}
SAMPLE_INVALID_EXPERIMENT = {EXP_NAME: {'owner': 'owner', 'percent': 'string',
                                        'description': '100 percent'}}
TWO_SAMPLE_EXPERIMENTS = {'100': {'owner': 'owner', 'percent': 100,
                                  'description': '100 percent'},
                          '0': {'owner': 'owner', 'percent': 0,
                                'description': '0 percent'}}


class ExperimentListFetcherTest(basetest.TestCase):
  """Test experiments ExperimentListFetcher class functions."""

  @mock.patch('__builtin__.open')
  def testFetch(self, mock_open):
    fh = mock.MagicMock()
    mock_open.return_value = fh
    fh.read.return_value = 'data'
    elf = experiments.ExperimentListFetcher('file')
    elf._Fetch()
    mock_open.assert_called_with('file', 'rb')
    self.assertEqual('data', elf.data.data)

  @mock.patch('__builtin__.open')
  @mock.patch.object(experiments, 'logging')
  def testFetchWithIOError(self, _, mock_open):
    fh = mock.MagicMock()
    mock_open.return_value = fh
    fh.read.side_effect = IOError('error')
    elf = experiments.ExperimentListFetcher('file')
    self.assertRaises(experiments.ExperimentsError, elf._Fetch)
    mock_open.assert_called_with('file', 'rb')
    self.assertIsNone(elf.data)

  @mock.patch.object(experiments.yaml, 'safe_load')
  @mock.patch.object(experiments, 'logging')
  def testParse(self, _, mock_yaml_sl):
    exp_dict = {'serial': 42, 'experiments': 'experiments'}
    mock_yaml_sl.return_value = exp_dict
    elf = experiments.ExperimentListFetcher('file')
    elf.data = type('obj', (object,), dict(data='data'))
    elf._Parse()
    mock_yaml_sl.assert_called_with('data')
    self.assertDictEqual(exp_dict, elf.data.parsed)
    self.assertTrue(elf.data.valid)
    self.assertEqual('experiments', elf.data.experiments)

  @mock.patch.object(experiments, 'logging')
  def testParseWithNoData(self, mock_logging):
    elf = experiments.ExperimentListFetcher('file')
    # elf.data = type('obj', (object,), dict(data='data'))
    elf._Parse()
    self.assertTrue(mock_logging.error.called)
    self.assertIsNone(elf.data)

  @mock.patch.object(experiments.yaml, 'safe_load')
  @mock.patch.object(experiments, 'logging')
  def testParseWithYamlError(self, _, mock_yaml_sl):
    mock_yaml_sl.side_effect = experiments.yaml.YAMLError
    elf = experiments.ExperimentListFetcher('file')
    elf.data = type('obj', (object,), dict(data='data'))
    elf._Parse()
    mock_yaml_sl.assert_called_with('data')
    self.assertIsNone(elf.data.parsed)
    self.assertFalse(elf.data.valid)

  @mock.patch.object(experiments.yaml, 'safe_load')
  @mock.patch.object(experiments, 'logging')
  def testParseWithMissingExperimentsField(self, _, mock_yaml_sl):
    mock_yaml_sl.return_value = {'serial': 42}
    elf = experiments.ExperimentListFetcher('file')
    elf.data = type('obj', (object,), dict(data='data'))
    elf._Parse()
    mock_yaml_sl.assert_called_with('data')
    self.assertEqual({'serial': 42}, elf.data.parsed)
    self.assertTrue(elf.data.valid)
    self.assertEqual({}, elf.data.experiments)

  @mock.patch.object(experiments.ExperimentListFetcher, '_Fetch')
  @mock.patch.object(experiments.ExperimentListFetcher, '_Parse')
  def testGetData(self, mock_parse, mock_fetch):
    def FetchSE():
      elf.data = type('obj', (object,), {'valid': False, 'parsed': None,
                                         'data': 'data'})
    mock_fetch.side_effect = FetchSE

    def ParseSE():
      elf.data.valid = True
      elf.data.parsed = 'parsed'
      elf.data.serial = 1
    mock_parse.side_effect = ParseSE

    elf = experiments.ExperimentListFetcher('file')
    elf.GetData()
    self.assertTrue(elf.data.valid)

  @mock.patch.object(experiments, 'logging')
  @mock.patch.object(experiments.ExperimentListFetcher, '_Fetch')
  @mock.patch.object(experiments.ExperimentListFetcher, '_Parse')
  def testGetDataWithInvalidData(self, mock_parse, mock_fetch, _):
    def FetchSE():
      elf.data = type('obj', (object,), {'valid': False, 'parsed': None})
    mock_fetch.side_effect = FetchSE

    def ParseSE():
      elf.data.valid = False
    mock_parse.side_effect = ParseSE

    elf = experiments.ExperimentListFetcher('file')
    self.assertRaises(experiments.InvalidData, elf.GetData)
    self.assertFalse(elf.data.valid)

  @mock.patch.object(experiments, 'logging')
  @mock.patch.object(experiments.ExperimentListFetcher, '_Fetch')
  def testGetDataRaisesErrorWithNoYaml(self, mock_fetch, _):
    mock_fetch.side_effect = experiments.ExperimentsError
    elf = experiments.ExperimentListFetcher('file')
    self.assertRaises(experiments.InvalidData, elf.GetData)
    self.assertIsNone(elf.data)


class KnobsTest(basetest.TestCase):
  """Test experiments Knobs class functions."""

  @mock.patch.object(experiments.gmacpyutil, 'MachineInfoForKey')
  def testKnobsManualKnobReturnsList(self, mock_mifk):
    def MifkSE(key):
      if key == experiments.MANUAL_ON_KNOB:
        return 'foo,bar,baz'
      else:
        return ''
    mock_mifk.side_effect = MifkSE
    k = experiments.Knobs()
    knobs = k._GetKnobs()
    self.assertSameElements(['foo', 'baz', 'bar'],
                            knobs[experiments.MANUAL_ON_KNOB])

  @mock.patch.object(experiments.gmacpyutil, 'MachineInfoForKey')
  def testKnobsExperimentsKnobIsNotSplit(self, mock_mifk):
    def MifkSE(key):
      if key == experiments.EXPERIMENTS_KNOB:
        return 'foo,bar,baz'
      else:
        return ''
    mock_mifk.side_effect = MifkSE
    k = experiments.Knobs()
    knobs = k._GetKnobs()
    self.assertEqual('foo,bar,baz', knobs[experiments.EXPERIMENTS_KNOB])

  def testKnobsInit(self):
    knobs_list = ['foo', 'bar']
    k = experiments.Knobs(knobs_list=knobs_list)
    self.assertEqual(k._knobs_list, knobs_list)
    self.assertFalse(k._valid)
    self.assertEqual({}, k._knobs)

  @mock.patch.object(experiments.Knobs, '_GetKnobs')
  def testKnobsCachingWorks(self, mock_getknobs):
    knobs_data = {'foo': 'bar'}
    mock_getknobs.return_value = knobs_data
    knobs_list = ['foo']
    k = experiments.Knobs(knobs_list=knobs_list)
    k.Knobs()
    k.Knobs()
    self.assertEqual(knobs_data, k._knobs)
    self.assertEqual(1, mock_getknobs.call_count)


class ExperimentsModuleTest(basetest.TestCase):
  """Test experiments top-level functions."""

  def testOutput(self):
    """Just to be thorough."""
    experiments.Output('message')

  @mock.patch.object(experiments.gmacpyutil, 'MachineInfoForKey')
  def testFetchUUIDWithGoodUUID(self, mock_mifk):
    good_uuid = 'AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE'
    mock_mifk.return_value = good_uuid
    self.assertEqual(good_uuid, experiments.FetchUUID())

  @mock.patch.object(experiments.gmacpyutil, 'MachineInfoForKey')
  def testFetchUUIDWithBadUUID(self, mock_mifk):
    bad_uuid = 'bad'
    mock_mifk.return_value = bad_uuid
    self.assertRaises(experiments.ExperimentsError, experiments.FetchUUID)

  @mock.patch.object(experiments.gmacpyutil, 'MachineInfoForKey')
  def testFetchUUIDWithNonStringUUID(self, mock_mifk):
    bad_uuid = 123
    mock_mifk.return_value = bad_uuid
    self.assertRaises(experiments.ExperimentsError, experiments.FetchUUID)

  @mock.patch.object(experiments, 'systemconfig')
  @mock.patch.object(experiments.gmacpyutil, 'MachineInfoForKey')
  def testFetchUUIDWithMissingMachineUUID(self, mock_mifk, mock_sc):
    good_uuid = 'AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE'
    mock_mifk.return_value = None
    mock_sc.SystemProfiler().GetHWUUID.return_value = good_uuid
    self.assertEqual(good_uuid, experiments.FetchUUID())

  @mock.patch.object(experiments, 'systemconfig')
  @mock.patch.object(experiments.gmacpyutil, 'MachineInfoForKey')
  def testFetchUUIDWithMissingUUID(self, mock_mifk, mock_sc):
    mock_mifk.return_value = None
    mock_sc.SystemProfiler().GetHWUUID.return_value = None
    with self.assertRaises(experiments.ExperimentsError):
      experiments.FetchUUID()

  @mock.patch.object(experiments, 'ExperimentListFetcher')
  def testGetExperiments(self, mock_elf):
    mc = mock_elf.return_value
    mc.GetData.return_value = type('obj', (object,),
                                   dict(experiments='experiments'))
    mock_elf.GetData().experiments = 'experiments'
    self.assertEqual('experiments', experiments.GetExperiments())

  @mock.patch.object(experiments, 'ExperimentListFetcher')
  def testGetExperimentsWithBadData(self, mock_elf):
    mc = mock_elf.return_value
    mc.GetData.side_effect = experiments.InvalidData
    self.assertIsNone(experiments.GetExperiments())

  @mock.patch.object(experiments, 'Output')
  def testMainWithoutOptionsEmptyExperiments(self, mock_output):
    experiments.GetExperiments = mock.MagicMock(return_value={})
    experiments.main([])
    mock_output.assert_called_with('No experiments are currently running.')

  @mock.patch.object(experiments, 'Output')
  @mock.patch.object(experiments.gmacpyutil, 'ConfigureLogging')
  def testMainWithDebugEmptyExperiments(self, mock_confl, mock_output):
    experiments.GetExperiments = mock.MagicMock(return_value={})
    experiments.main(['', '--debug'])
    mock_confl.assert_called_with(debug_level=experiments.logging.DEBUG,
                                  stderr=True)
    mock_output.assert_called_with('No experiments are currently running.')

  @mock.patch.object(experiments, 'Output')
  @mock.patch.object(experiments, 'GetExperiments')
  def testMainWithoutOptions(self, mock_getexp, mock_output):
    experiments.InExperiment = mock.MagicMock(
        side_effect=[(True, ''), (False, '')])
    mock_getexp.return_value = TWO_SAMPLE_EXPERIMENTS
    experiments.main([])
    self.assertTrue(mock_getexp.called)
    self.assertEqual(2, mock_output.call_count)

  @mock.patch.object(experiments, 'InExperiment', return_value=(False, 'auto'))
  @mock.patch.object(experiments, 'Output')
  @mock.patch.object(experiments, 'GetExperiments')
  def testMainWithFormatting(self, mock_getexp, mock_output, mock_inexp):
    mock_getexp.return_value = SAMPLE_50_EXPERIMENT
    experiments.main(['', '-F'])
    self.assertTrue(mock_getexp.called)
    self.assertTrue(mock_inexp.called)
    mock_output.assert_called_with('%s,false' % EXP_NAME)

  def testMainWithConflictingOptions(self):
    self.assertRaisesRegexp(SystemExit, r'^1$',
                            experiments.main, ['', '-F', '-e', 'foo'])

  def testMainEnableDisableRequiresRoot(self):
    experiments.os.geteuid = mock.MagicMock(return_value=14313)
    self.assertRaisesRegexp(SystemExit, r'^2$',
                            experiments.main, ['', '-e', 'foo'])

  @mock.patch.object(experiments, 'ModifyManualList')
  def testMainEnable(self, mock_mml):
    experiments.os.geteuid = mock.MagicMock(return_value=0)
    experiments.main(['', '-e', 'foo'])
    mock_mml.assert_has_calls([
        mock.call('add', mock.ANY, 'foo'),
        mock.call('remove', mock.ANY, 'foo'),
        mock.call('add', mock.ANY, None),
        mock.call('remove', mock.ANY, None),
        mock.call('remove', mock.ANY, None)])

  @mock.patch.object(experiments, 'ModifyManualList')
  def testMainDisable(self, mock_mml):
    experiments.os.geteuid = mock.MagicMock(return_value=0)
    experiments.main(['', '-d', 'foo'])
    mock_mml.assert_has_calls([
        mock.call('add', mock.ANY, None),
        mock.call('remove', mock.ANY, None),
        mock.call('add', mock.ANY, 'foo'),
        mock.call('remove', mock.ANY, 'foo'),
        mock.call('remove', mock.ANY, None)])

  @mock.patch.object(experiments, 'ModifyManualList')
  def testMainRecommended(self, mock_mml):
    experiments.os.geteuid = mock.MagicMock(return_value=0)
    experiments.main(['', '-r', 'foo'])
    mock_mml.assert_has_calls([
        mock.call('add', mock.ANY, None),
        mock.call('remove', mock.ANY, None),
        mock.call('add', mock.ANY, None),
        mock.call('remove', mock.ANY, None),
        mock.call('remove', mock.ANY, 'foo')])

  @mock.patch.object(experiments, 'ModifyManualList')
  def testMainHandlePlistError(self, mock_mml):
    mock_mml.side_effect = experiments.PlistError
    experiments.os.geteuid = mock.MagicMock(return_value=0)
    self.assertRaisesRegexp(SystemExit, r'^3$', experiments.main,
                            ['', '-e', 'foo'])

  @mock.patch.object(experiments, 'GetExperimentStatus')
  @mock.patch.object(experiments.KNOBS, 'Knobs', return_value={})
  @mock.patch.object(experiments.gmacpyutil, 'GetTrack')
  def testInExperiment(self, unused_gettrack, unused_knobs, mock_ges):
    exp_status = mock.Mock()
    exp_status.status, exp_status.source, exp_status.rollout_percent = (
        experiments.ENABLED, experiments.AUTO, 100)
    mock_ges.return_value = exp_status
    self.assertTrue(
        experiments.InExperiment('exp', SAMPLE_100_EXPERIMENT))

  @mock.patch.object(experiments.KNOBS, 'Knobs', return_value={})
  @mock.patch.object(experiments.gmacpyutil, 'GetTrack')
  def testInExperimentEmptyExperiments(self, unused_gettrack, unused_knobs):
    self.assertFalse(
        experiments.InExperiment('exp', {})[0])

  @mock.patch.object(experiments.hashlib, 'sha256')
  def testExperimentIsBucketTinyPercentEnabled(self, mock_sha):
    """Ensure that we can turn experiments on for small percentages."""
    mock_hash = mock.MagicMock()
    mock_sha.return_value = mock_hash
    mock_hash.hexdigest.return_value = '1'
    ret = experiments.ExperimentIsBucket(EXP_NAME, SAMPLE_P1_EXPERIMENT,
                                         TEST_UUID)
    self.assertEqual(ret.status, experiments.ENABLED)
    self.assertEqual(ret.source, experiments.AUTO)

  @mock.patch.object(experiments.hashlib, 'sha256')
  def testExperimentIsBucketZeroPercentIsDisabled(self, mock_sha):
    """Ensure that a 0 percent experiment is disabled."""
    mock_hash = mock.MagicMock()
    mock_sha.return_value = mock_hash
    mock_hash.hexdigest.return_value = '0'
    ret = experiments.ExperimentIsBucket(EXP_NAME, SAMPLE_0_EXPERIMENT,
                                         TEST_UUID)
    self.assertEqual(ret.status, experiments.DISABLED)
    self.assertEqual(ret.source, experiments.AUTO)

  @mock.patch.object(experiments.hashlib, 'sha256')
  def testExperimentIsBucketHundredPercentEnabled(self, mock_sha):
    """Ensure that a 100 percent experiment is enabled."""
    mock_hash = mock.MagicMock()
    mock_sha.return_value = mock_hash
    mock_hash.hexdigest.return_value = '100'
    ret = experiments.ExperimentIsBucket(EXP_NAME, SAMPLE_100_EXPERIMENT,
                                         TEST_UUID)
    self.assertEqual(ret.status, experiments.ENABLED)
    self.assertEqual(ret.source, experiments.AUTO)

  @mock.patch.object(experiments, 'logging')
  @mock.patch.object(experiments.hashlib, 'sha256')
  def testExperimentIsBucketHashlibReturnsNonInt(self, mock_sha, _):
    """Ensure that we fail if hashlib goes bad."""
    mock_hash = mock.MagicMock()
    mock_sha.return_value = mock_hash
    mock_hash.hexdigest.return_value = 'not a number'
    self.assertRaises(experiments.ExperimentsError,
                      experiments.ExperimentIsBucket,
                      EXP_NAME,
                      SAMPLE_100_EXPERIMENT,
                      TEST_UUID)

  def testExperimentIsBucketInvalidExperiment(self):
    """Ensure that an invalid experiment raises an exception."""
    self.assertRaises(
        experiments.InvalidExperiment,
        experiments.ExperimentIsBucket,
        'invalid',
        SAMPLE_100_EXPERIMENT,
        TEST_UUID)

  @mock.patch.object(experiments, 'logging')
  @mock.patch.object(experiments.hashlib, 'sha256')
  def testExperimentIsBucketInvalidPercent(self, mock_sha, _):
    """Ensure that an invalid percent experiment is disabled."""
    mock_hash = mock.MagicMock()
    mock_sha.return_value = mock_hash
    mock_hash.hexdigest.return_value = '100'
    ret = experiments.ExperimentIsBucket(EXP_NAME, SAMPLE_INVALID_EXPERIMENT,
                                         TEST_UUID)
    self.assertEqual(ret.rollout_percent, 0)
    self.assertEqual(ret.status, experiments.DISABLED)
    self.assertEqual(ret.source, experiments.AUTO)

  def testGetExperimentStatusAlwaysEnabled(self):
    knobs = {experiments.EXPERIMENTS_KNOB: experiments.ALWAYS}
    ret = experiments.GetExperimentStatus(EXP_NAME, knobs, SAMPLE_50_EXPERIMENT)
    self.assertEqual(ret.status, experiments.ENABLED)
    self.assertEqual(ret.source, experiments.ALWAYS)

  def testGetExperimentStatusAlwaysDisabled(self):
    knobs = {experiments.EXPERIMENTS_KNOB: experiments.NEVER}
    ret = experiments.GetExperimentStatus(EXP_NAME, knobs, SAMPLE_50_EXPERIMENT)
    self.assertEqual(ret.status, experiments.DISABLED)
    self.assertEqual(ret.source, experiments.ALWAYS)

  def testGetExperimentStatusEnabledViaUnstableTrackWhenUnstable(self):
    knobs = {}
    ret = experiments.GetExperimentStatus(
        EXP_NAME, knobs, SAMPLE_UNSTABLE_EXPERIMENT, 'unstable')
    self.assertEqual(ret.status, experiments.ENABLED)
    self.assertEqual(ret.source, experiments.ALWAYS)

  @mock.patch.object(experiments, 'FetchUUID', return_value=TEST_UUID)
  def testGetExperimentStatusDisabledViaUnstableTrackWhenTesting(self, _):
    knobs = {}
    ret = experiments.GetExperimentStatus(
        EXP_NAME, knobs, SAMPLE_UNSTABLE_EXPERIMENT, 'testing')
    self.assertEqual(ret.status, experiments.DISABLED)
    self.assertEqual(ret.source, experiments.AUTO)

  def testGetExperimentStatusEnabledViaTestingTrackWhenUnstable(self):
    knobs = {}
    ret = experiments.GetExperimentStatus(
        EXP_NAME, knobs, SAMPLE_TESTING_EXPERIMENT, 'unstable')
    self.assertEqual(ret.status, experiments.ENABLED)
    self.assertEqual(ret.source, experiments.ALWAYS)

  def testGetExperimentStatusEnabledViaTestingTrackWhenTesting(self):
    knobs = {}
    ret = experiments.GetExperimentStatus(
        EXP_NAME, knobs, SAMPLE_TESTING_EXPERIMENT, 'testing')
    self.assertEqual(ret.status, experiments.ENABLED)
    self.assertEqual(ret.source, experiments.ALWAYS)

  @mock.patch.object(experiments, 'FetchUUID', return_value=TEST_UUID)
  def testGetExperimentStatusDisabledViaUnstableTrackWhenStable(self, _):
    knobs = {}
    ret = experiments.GetExperimentStatus(
        EXP_NAME, knobs, SAMPLE_UNSTABLE_EXPERIMENT, 'stable')
    self.assertEqual(ret.status, experiments.DISABLED)
    self.assertEqual(ret.source, experiments.AUTO)

  def testGetExperimentStatusManuallyEnable(self):
    knobs = {experiments.MANUAL_ON_KNOB: [EXP_NAME]}
    ret = experiments.GetExperimentStatus(EXP_NAME, knobs, SAMPLE_50_EXPERIMENT)
    self.assertEqual(ret.status, experiments.ENABLED)
    self.assertEqual(ret.source, experiments.MANUAL)

  def testGetExperimentStatusManuallyDisable(self):
    knobs = {experiments.MANUAL_OFF_KNOB: [EXP_NAME]}
    ret = experiments.GetExperimentStatus(EXP_NAME, knobs, SAMPLE_50_EXPERIMENT)
    self.assertEqual(ret.status, experiments.DISABLED)
    self.assertEqual(ret.source, experiments.MANUAL)

  def testGetExperimentStatusManuallyEnableMultipleEnttries(self):
    knobs = {experiments.MANUAL_ON_KNOB: [EXP_NAME, 'random']}
    ret = experiments.GetExperimentStatus(EXP_NAME, knobs, SAMPLE_50_EXPERIMENT)
    self.assertEqual(ret.status, experiments.ENABLED)
    self.assertEqual(ret.source, experiments.MANUAL)
    ret = experiments.GetExperimentStatus('random', knobs, SAMPLE_50_EXPERIMENT)
    self.assertEqual(ret.status, experiments.ENABLED)
    self.assertEqual(ret.source, experiments.MANUAL)

  def testGetExperimentStatusManuallyDisableWhenTrackEnabled(self):
    knobs = {experiments.MANUAL_OFF_KNOB: [EXP_NAME]}
    ret = experiments.GetExperimentStatus(
        EXP_NAME, knobs, SAMPLE_UNSTABLE_EXPERIMENT, 'unstable')
    self.assertEqual(ret.status, experiments.DISABLED)
    self.assertEqual(ret.source, experiments.MANUAL)

  @mock.patch.object(experiments, 'FetchUUID', return_value=TEST_UUID)
  @mock.patch.object(experiments, 'ExperimentIsBucket')
  def testGetExperimentStatusBucketOn(self, mock_eib, _):
    knobs = {experiments.EXPERIMENTS_KNOB: experiments.AUTO}
    eib_ret = mock.MagicMock()
    eib_ret.source, eib_ret.status = experiments.AUTO, experiments.ENABLED
    mock_eib.return_value = eib_ret
    ret = experiments.GetExperimentStatus(EXP_NAME, knobs, SAMPLE_50_EXPERIMENT)
    self.assertEqual(ret.status, experiments.ENABLED)
    self.assertEqual(ret.source, experiments.AUTO)

  @mock.patch.object(experiments, 'FetchUUID', return_value=TEST_UUID)
  @mock.patch.object(experiments, 'ExperimentIsBucket')
  def testGetExperimentStatusBucketOff(self, mock_eib, _):
    knobs = {experiments.EXPERIMENTS_KNOB: experiments.AUTO}
    eib_ret = mock.MagicMock()
    eib_ret.source, eib_ret.status = experiments.AUTO, experiments.DISABLED
    mock_eib.return_value = eib_ret
    ret = experiments.GetExperimentStatus(EXP_NAME, knobs, SAMPLE_50_EXPERIMENT)
    self.assertEqual(ret.status, experiments.DISABLED)
    self.assertEqual(ret.source, experiments.AUTO)

  @mock.patch.object(experiments, 'FetchUUID', return_value=TEST_UUID)
  @mock.patch.object(experiments, 'ExperimentIsBucket')
  def testGetExperimentStatusBucketError(self, mock_eib, _):
    knobs = {experiments.EXPERIMENTS_KNOB: experiments.AUTO}
    mock_eib.side_effect = experiments.ExperimentsError
    self.assertRaises(
        experiments.ExperimentsError,
        experiments.GetExperimentStatus,
        EXP_NAME,
        knobs,
        SAMPLE_50_EXPERIMENT)

  def testGetExperimentStatusHundrePercentIsAlwaysEnabled(self):
    knobs = {experiments.MANUAL_OFF_KNOB: [EXP_NAME]}
    ret = experiments.GetExperimentStatus(EXP_NAME, knobs,
                                          SAMPLE_100_EXPERIMENT)
    self.assertEqual(ret.status, experiments.ENABLED)
    self.assertEqual(ret.source, experiments.ALWAYS)

  def testConvertListToCSVString(self):
    self.assertEqual('a,b,c',
                     experiments.ConvertListToCSVString(['a', 'b', 'c']))
    self.assertEqual('', experiments.ConvertListToCSVString([]))

  def testConvertCSVStringToList(self):
    self.assertEqual(['a', 'b', 'c'],
                     experiments.ConvertCSVStringToList('a,b,c'))
    self.assertEqual([], experiments.ConvertCSVStringToList(''))

  @mock.patch.object(experiments, 'AddExperimentToManualList')
  def testModifyManualListAdd(self, mock_add):
    experiments.ModifyManualList('add', ['knob'], 'foo,bar')
    mock_add.assert_any_call('foo', 'knob')
    mock_add.assert_any_call('bar', 'knob')
    self.assertEqual(2, mock_add.call_count)

  @mock.patch.object(experiments, 'RemoveExperimentFromManualList')
  def testModifyManualListRemove(self, mock_remove):
    experiments.ModifyManualList('remove', ['knob'], 'foo,bar')
    mock_remove.assert_any_call('foo', 'knob')
    mock_remove.assert_any_call('bar', 'knob')
    self.assertEqual(2, mock_remove.call_count)

  def testModifyManualListInvalidAction(self):
    self.assertRaises(ValueError, experiments.ModifyManualList, 'munchkin',
                      ['knob'], 'freeblebit')

  @mock.patch.object(experiments.gmacpyutil, 'SetMachineInfoForKey')
  @mock.patch.object(experiments, 'Output')
  def testAddExperimentToManualListEmptyKnobsList(self, mock_output,
                                                  mock_smifk):
    mock_smifk.return_value = True
    experiments.KNOBS.Knobs = mock.MagicMock(return_value={})
    experiments.AddExperimentToManualList('foo', 'knob')
    self.assertRegexpMatches(mock_output.call_args[0][0], r'^New value of.*')

  @mock.patch.object(experiments.gmacpyutil, 'SetMachineInfoForKey')
  @mock.patch.object(experiments, 'Output')
  def testAddExperimentToManualListAlreadyAdded(self, mock_output, mock_smifk):
    mock_smifk.return_value = True
    experiments.KNOBS.Knobs = mock.MagicMock(
        return_value={'knob': ['bar', 'foo', 'baz']})
    experiments.AddExperimentToManualList('foo', 'knob')
    self.assertRegexpMatches(mock_output.call_args[0][0],
                             r'^foo is already in.*')

  @mock.patch.object(experiments.gmacpyutil, 'SetMachineInfoForKey')
  def testAddExperimentToManualListPlistError(self, mock_smifk):
    mock_smifk.return_value = False
    experiments.KNOBS.Knobs = mock.MagicMock(return_value={})
    self.assertRaises(
        experiments.PlistError, experiments.AddExperimentToManualList, 'foo',
        'knob')

  @mock.patch.object(experiments.gmacpyutil, 'SetMachineInfoForKey')
  @mock.patch.object(experiments, 'Output')
  def testRemoveExperimentFromManualListEmptyKnobsList(self, mock_output,
                                                       mock_smifk):
    mock_smifk.return_value = True
    experiments.KNOBS.Knobs = mock.MagicMock(return_value={})
    experiments.RemoveExperimentFromManualList('foo', 'knob')
    self.assertRegexpMatches(mock_output.call_args[0][0],
                             r'nothing to remove.$')

  @mock.patch.object(experiments.gmacpyutil, 'SetMachineInfoForKey')
  @mock.patch.object(experiments, 'Output')
  def testRemoveExperimentFromManualListAlreadyAdded(self, mock_output,
                                                     mock_smifk):
    mock_smifk.return_value = True
    experiments.KNOBS.Knobs = mock.MagicMock(
        return_value={'knob': ['bar', 'baz']})
    experiments.RemoveExperimentFromManualList('foo', 'knob')
    self.assertRegexpMatches(mock_output.call_args[0][0], r'^foo is not in.*')

  @mock.patch.object(experiments.gmacpyutil, 'SetMachineInfoForKey')
  def testRemoveExperimentFromManualListPlistError(self, mock_smifk):
    mock_smifk.return_value = False
    experiments.KNOBS.Knobs = mock.MagicMock(
        return_value={'knob': ['bar', 'foo']})
    self.assertRaises(experiments.PlistError,
                      experiments.RemoveExperimentFromManualList, 'foo', 'knob')


def main(unused_argv):
  basetest.main()

if __name__ == '__main__':
  basetest.main()
