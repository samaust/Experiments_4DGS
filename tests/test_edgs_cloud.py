import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from freetimegs_initialization import digest, load_dense_cloud


class DenseCloudTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        keys = [(f'{i:04d}', 4150) for i in range(24) if i != 15]
        self.scene = SimpleNamespace(sha256='manifest', training_keys=lambda frame: keys,
            frames={key: dict(sha256='image', normalized_time=.5) for key in keys})
        self.archive = self.directory / 'cloud.npz'
        np.savez(self.archive, positions=np.zeros((4, 3), dtype=np.float32),
                 colors=np.ones((4, 3), dtype=np.float32))
        self.report = dict(schema='edgs-selfcap-cloud/v1', status='prepared', frame_id=4150,
            manifest_sha256='manifest', points=4, archive_sha256=digest(self.archive),
            inputs=[dict(camera_id=c, frame_id=f, sha256='image') for c, f in keys])

    def load(self):
        (self.directory / 'result.json').write_text(json.dumps(self.report))
        return load_dense_cloud(self.directory, self.scene, 4150)

    def test_valid_cloud_and_time(self):
        points, colors, evidence = self.load()
        self.assertEqual(points.shape, (4, 3))
        self.assertEqual(colors.dtype, np.float32)
        self.assertEqual(evidence['normalized_time'], .5)

    def test_heldout_and_duplicate_inputs_rejected(self):
        self.report['inputs'][0]['camera_id'] = '0015'
        with self.assertRaisesRegex(ValueError, 'training split'):
            self.load()
        self.report['inputs'][0] = self.report['inputs'][1]
        with self.assertRaisesRegex(ValueError, 'training split'):
            self.load()

    def test_wrong_frame_and_image_digest_rejected(self):
        self.report['frame_id'] = 4151
        with self.assertRaisesRegex(ValueError, 'frame or status'):
            self.load()
        self.report['frame_id'] = 4150
        self.report['inputs'][0]['sha256'] = 'changed'
        with self.assertRaisesRegex(ValueError, 'image digest'):
            self.load()

    def test_archive_digest_and_nonfinite_data_rejected(self):
        np.savez(self.archive, positions=np.full((4, 3), np.nan, dtype=np.float32),
                 colors=np.ones((4, 3), dtype=np.float32))
        with self.assertRaisesRegex(ValueError, 'archive digest'):
            self.load()
        self.report['archive_sha256'] = digest(self.archive)
        with self.assertRaisesRegex(ValueError, 'invalid dense cloud'):
            self.load()
