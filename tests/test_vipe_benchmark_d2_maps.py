from pathlib import Path
import tempfile
import unittest

from vipe_benchmark.d2_maps import run
from basketball_vipe_d2_maps import active_reservation


class D2MapsTest(unittest.TestCase):
    def test_cli_guard_rejects_unreserved_gpu_work(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request_path = root / 'request.json'
            request_path.write_text('{}')
            output = root / 'jobs/plan069-D2-maps-001'
            request = dict(record_kind='actual', job_id=output.name,
                ledger_path=str(root / 'ledger.jsonl'),
                runtime=dict(python='/missing/qualified/python'))
            self.assertFalse(active_reservation(request, request_path, output))
            self.assertFalse(output.exists())

    def test_actual_worker_requires_reserved_supervision_before_model_work(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'plan069-D2-maps-001'
            request = dict(schema='plan069-d2-maps-request/v1',
                job_id=output.name, candidate='D2', record_kind='actual',
                max_seconds=3600)
            class Backend:
                def predict(self, *_args):
                    self.fail('model must not run')
            with self.assertRaisesRegex(ValueError, 'active exact supervision'):
                run(request, output, backend=Backend())
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
