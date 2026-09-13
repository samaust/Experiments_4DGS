import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.config import load
from vipe_benchmark.files import file_record, write_json
from vipe_benchmark.ledger import Ledger
from vipe_benchmark.execution import result_record, component_recovery_request


class ComponentRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.config = load()
        self.ledger = Ledger(self.root / 'ledger.jsonl', self.config)
        self.ledger.reserve('S2-reconstruction', [], {})
        self.failure = self.ledger.finish('S2-reconstruction', 'failed', 328., cleanup_confirmed=True)
        write_json(self.root / 'validation.json', dict(status='passed', sources=[file_record(__file__)]))

    def tearDown(self):
        self.temp.cleanup()

    def authorization(self, **changes):
        doc = dict(schema='vipe-benchmark-component-recovery/v1',
            job_id='S2-reconstruction-recovery-001', original_job_id='S2-reconstruction',
            attempts_limit=1, seconds_limit=5400, reset_previous_consumption=False,
            gpu_total_seconds_limit=93600, changes_to_prescribed_configuration=False,
            unrelated_attempts_reopened=False, authorization='Synthetic explicit retry approval',
            original_failure_event_sha256=self.failure['event_sha256'],
            repair_validation=file_record(self.root / 'validation.json'))
        doc.update(changes)
        path = self.root / f'authorization-{len(list(self.root.glob("authorization-*.json")))}.json'
        write_json(path, doc)
        return file_record(path)

    def test_successful_recovery_preserves_failure_and_requires_registered_valid_result(self):
        auth = self.authorization()
        history = self.ledger.path.read_bytes()
        self.ledger.authorize_component_recovery(auth)
        self.assertTrue(self.ledger.path.read_bytes().startswith(history))
        with self.assertRaisesRegex(ValueError, 'already allocated'):
            self.ledger.authorize_component_recovery(auth)
        job = 'S2-reconstruction-recovery-001'
        path = self.root / 'jobs' / job / 'result.json'
        write_json(path, dict(status='complete', component='S2', branch='reconstruction', rows=[{}]*840))
        self.assertIsNone(result_record(self.root, 'S2-reconstruction'))
        self.ledger.reserve(job, [], {})
        self.ledger.finish(job, 'complete', 20., cleanup_confirmed=True, result=file_record(path))
        self.assertEqual(result_record(self.root, 'S2-reconstruction'), file_record(path))
        self.assertEqual(self.ledger.states()['S2-reconstruction'], self.failure)
        self.assertEqual(self.ledger.totals()['gpu']['elapsed_seconds'], 348.)
        with self.assertRaisesRegex(ValueError, 'already consumed'):
            self.ledger.reserve(job, [], {})
        with self.assertRaisesRegex(ValueError, 'previous cleaned-up'):
            self.ledger.authorize_component_recovery(self.authorization(job_id='S2-reconstruction-recovery-002'))

    def test_scope_validation_and_cumulative_cap_are_not_relaxed(self):
        for changes in (dict(attempts_limit=2), dict(seconds_limit=5401),
                        dict(reset_previous_consumption=True), dict(changes_to_prescribed_configuration=True)):
            with self.subTest(changes=changes), self.assertRaisesRegex(ValueError, 'exact explicit'):
                self.ledger.authorize_component_recovery(self.authorization(**changes))
        with self.assertRaisesRegex(ValueError, 'original cleaned-up'):
            self.ledger.authorize_component_recovery(self.authorization(original_failure_event_sha256='0'*64))
        self.config['gpu_total_seconds_limit'] = 328.
        with self.assertRaisesRegex(ValueError, 'cumulative GPU'):
            self.ledger.authorize_component_recovery(self.authorization(gpu_total_seconds_limit=328.))

    def test_recipe_is_derived_from_original_and_missing_prerequisites_block(self):
        auth = self.authorization()
        self.ledger.authorize_component_recovery(auth)
        with patch('vipe_benchmark.execution.make_request', return_value=({'job_id':'S2-reconstruction', 'fixed':42}, [])) as make:
            request = component_recovery_request(self.root, self.config, 'S2-reconstruction-recovery-001')
        make.assert_called_once_with(self.root, 'S2-reconstruction', self.config)
        self.assertEqual(request, dict(job_id='S2-reconstruction-recovery-001', fixed=42))
        with patch('vipe_benchmark.execution.make_request', return_value=(None,['runtime missing'])):
            with self.assertRaisesRegex(ValueError, 'runtime missing'):
                component_recovery_request(self.root, self.config, 'S2-reconstruction-recovery-001')


if __name__ == '__main__':
    unittest.main()
