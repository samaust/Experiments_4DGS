"""D7 publication accepts only an accounted native GPU result."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.depth_d7_publish import publish_d7_after_gpu
from vipe_benchmark.files import file_record, write_json


class D7PublishTests(unittest.TestCase):
    def test_unaccounted_map_result_cannot_be_published(self):
        with tempfile.TemporaryDirectory() as directory:
            local = Path(directory)
            result = local / 'jobs/plan069-D7-maps-001/result.json'
            write_json(result, dict(schema='plan069-D7-maps-result/v1',
                                    status='complete', candidate='D7'))
            with self.assertRaisesRegex(ValueError, 'supervised D7 GPU result'):
                publish_d7_after_gpu(file_record(result),
                    local / 'jobs/plan069-D7-clips-001')
            self.assertFalse((local / 'jobs/plan069-D7-clips-001').exists())


if __name__ == '__main__':
    unittest.main()
