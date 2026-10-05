"""D8 setup-recovery dispatch: authorize, reserve and supervise the reviewed request."""
import sys
import unittest
from unittest.mock import patch

import basketball_vipe_depth_setup_other_dispatch as dispatcher
from test_vipe_benchmark_depth_native_setup_recovery import JOB, WHEELS, NativeSetupRecoveryFixture
from vipe_benchmark.files import file_record, read_json


class NativeSetupRecoveryDispatchTests(NativeSetupRecoveryFixture):
    def dispatch(self, supervise):
        inputs = self.request_inputs()
        (self.run_root / 'requests' / (JOB + '.json')).unlink()  # The dispatcher writes it.
        with patch.object(dispatcher, 'supervise', side_effect=supervise), \
                patch.object(dispatcher, 'recipe', return_value=self.environment), \
                patch('vipe_benchmark.execution.resources',
                      return_value=dict(download_bytes=10, artifact_bytes=20, gpu_pids=[])):
            return dispatcher.dispatch_recovery(self.run_root, inputs)

    def request_inputs(self):
        request = read_json(self.request['path'])
        return dict(review=request['review'], authorization=request['authorization'],
                    source_review=request['source_review'])

    def test_reviewed_request_is_authorized_once_and_supervised_with_its_exact_bounds(self):
        seen: dict = {}

        def supervise(ledger, job_id, command, output, **kwargs):
            seen.update(job_id=job_id, command=command, output=output, **kwargs)
            return dict(status='complete')
        outcome = self.dispatch(supervise)
        self.assertEqual(outcome, dict(status='complete'))
        request_path = self.run_root / 'requests' / (JOB + '.json')
        request = read_json(request_path)
        self.assertEqual((request['schema'], request['job_id'], request['acquisitions']),
                         ('plan069-depth-setup-recovery-request/v1', JOB, WHEELS))
        self.assertEqual(seen['job_id'], JOB)
        self.assertEqual(seen['command'], [sys.executable, self.worker['path'], '--request', str(request_path),
                                           '--output', str(self.run_root / 'jobs' / JOB)])
        self.assertEqual(seen['seconds_limit'], 1200)
        self.assertEqual(seen['evidence']['request'], file_record(request_path))
        events = [line for line in (self.run_root / 'ledger.jsonl').read_text().splitlines()
                  if 'depth_setup_recovery_authorized' in line]
        self.assertEqual(len(events), 1)

    def test_existing_recovery_request_is_never_overwritten(self):
        before = (self.run_root / 'ledger.jsonl').read_bytes()
        with patch.object(dispatcher, 'supervise') as supervise:
            with self.assertRaisesRegex(ValueError, 'already prepared'):
                dispatcher.dispatch_recovery(self.run_root, self.request_inputs())
            supervise.assert_not_called()
        self.assertEqual((self.run_root / 'ledger.jsonl').read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
