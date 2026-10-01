"""D7's pinned native metric inference contract, with no GPU runtime."""
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.dav2_metric import DAV2MetricSmallAdapter


class FakeDAV2:
    encoder = 'vits'
    max_depth = 20.
    training = False

    def __init__(self, *, shape=(540, 960), value=6.):
        self.shape = shape
        self.value = value
        self.calls = []

    def infer_image(self, bgr, input_size=518):
        self.calls.append((bgr.copy(), input_size))
        return np.full(self.shape, self.value, np.float32)


class DAV2MetricTests(unittest.TestCase):
    def setUp(self):
        self.rgb = np.full((540, 960, 3), [10, 20, 30], np.uint8)
        self.K = np.array([[800., 0, 480], [0, 800, 270], [0, 0, 1]])
        self.valid = np.ones((540, 960), bool)
        self.valid[0, 0] = False

    def test_native_518_path_returns_camera_z_on_accepted_grid(self):
        runtime = FakeDAV2()
        output = DAV2MetricSmallAdapter(runtime).predict(self.rgb, self.K, self.valid)
        self.assertEqual(runtime.calls[0][1], 518)
        self.assertEqual(runtime.calls[0][0][270, 480].tolist(), [30, 20, 10])
        self.assertEqual(output.metadata['native_processed_size'], [924, 518])
        self.assertEqual(output.metadata['max_depth_metres'], 20)
        self.assertEqual(output.values[270, 480], 6.)
        self.assertTrue(np.isnan(output.values[0, 0]))
        self.assertEqual(output.metadata['conversion_count'], 0)

    def test_wrong_grid_nonfinite_range_and_checkpoint_mode_are_rejected(self):
        for runtime, message in ((FakeDAV2(shape=(518, 924)), 'output grid'),
                                 (FakeDAV2(value=np.nan), 'nonfinite'),
                                 (FakeDAV2(value=21.), 'native 20 m')):
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                DAV2MetricSmallAdapter(runtime).predict(self.rgb, self.K, self.valid)
        bad = FakeDAV2()
        bad.encoder = 'vitl'
        with self.assertRaisesRegex(ValueError, 'Hypersim Small'):
            DAV2MetricSmallAdapter(bad)


if __name__ == '__main__':
    unittest.main()
