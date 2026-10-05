"""Method 002 binds the accepted recovered D8 setup (CPU fixtures; no model load)."""
import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from test_vipe_benchmark_depth_native_setup_recovery import JOB, ORIGINAL
from test_vipe_benchmark_depth_native_setup_recovery_maps import RecoveredSetupMapsTests
from vipe_benchmark.files import file_record, read_json

spec = importlib.util.spec_from_file_location('d8_method_002', Path(__file__).with_name('producer.py'))
method = importlib.util.module_from_spec(spec)
spec.loader.exec_module(method)


class BindAcceptedSetupTests(RecoveredSetupMapsTests):
    def bind(self, setup, request, dispatch=None):
        args = SimpleNamespace(setup=str(setup), setup_request=str(request), setup_dispatch=dispatch)
        record, read, _ = method.helpers(str(self.run_root))
        proposal = dict(self.maps, candidate_config=dict(self.maps['candidate_config'],
                        code=dict(self.maps['candidate_config']['code'], revision='0' * 40)))
        with patch('vipe_benchmark.native_d8.SOURCE_REVISION', '0' * 40):
            return method.bind_accepted_setup(args, file_record, read_json, self.run_root, None, None, proposal)

    def test_recovered_setup_binds_its_own_request_and_runtime(self):
        self.completed_recovery()
        runtime = self.run_root / 'jobs' / JOB / 'runtime'
        runtime.mkdir(parents=True, exist_ok=True)
        (runtime / 'request.json').write_text('{"marker": "recovered runtime"}\n')
        setup, request, dispatch, runtime_request = self.bind(self.run_root / 'jobs' / JOB / 'result.json',
                                                              self.run_root / 'requests' / (JOB + '.json'))
        self.assertEqual((setup['job_id'], dispatch, runtime_request), (JOB, None, {'marker': 'recovered runtime'}))
        self.assertEqual(request, file_record(self.run_root / 'requests' / (JOB + '.json')))

    def test_failed_original_setup_never_binds(self):
        self.completed_recovery()
        with self.assertRaises(ValueError):
            self.bind(self.run_root / 'jobs' / ORIGINAL / 'failure.json',
                      self.run_root / 'requests' / (ORIGINAL + '.json'))

    def test_recovery_with_a_dispatch_record_or_other_request_is_refused(self):
        self.completed_recovery()
        with self.assertRaises(ValueError):
            self.bind(self.run_root / 'jobs' / JOB / 'result.json', self.run_root / 'requests' / (JOB + '.json'),
                      dispatch=str(self.run_root / 'requests' / (JOB + '.json')))


for name in [n for n in vars(RecoveredSetupMapsTests) if n.startswith('test_')]:
    setattr(BindAcceptedSetupTests, name, None)

if __name__ == '__main__':
    unittest.main()
