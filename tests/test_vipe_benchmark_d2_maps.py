from pathlib import Path
import tempfile
import unittest

from vipe_benchmark.d2_maps import run


class D2MapsTest(unittest.TestCase):
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
