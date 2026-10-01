"""D8's bundled PointMap student uses supplied rather than predicted camera."""
from pathlib import Path
import sys
import unittest

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.moge_metric import MetricAnythingPointMapAdapter


PIN = ('yjh001/metricanything_student_pointmap@'
       '8f1f08c53c683d4e19864601dfaf78515f29a63b')


class StudentRuntime:
    def __init__(self, *, predicted_camera=False, wrong_grid=False):
        self.predicted_camera = predicted_camera
        self.wrong_grid = wrong_grid
        self.options = None

    def infer(self, image, **options):
        self.options = options
        height, width = image.shape[-2:]
        if self.wrong_grid:
            width -= 1
        points = torch.zeros((height, width, 3), dtype=torch.float32)
        points[..., 0] = 3
        points[..., 2] = 4
        return dict(points=points, depth=points[..., 2].clone(),
            mask=torch.ones((height, width), dtype=torch.bool),
            intrinsics=torch.tensor([[.7 if self.predicted_camera else 800 / 960, 0, .5],
                [0, 800 / 540, .5], [0, 0, 1]], dtype=torch.float32))


class MetricAnythingTests(unittest.TestCase):
    def setUp(self):
        self.rgb = np.zeros((540, 960, 3), np.uint8)
        self.K = np.array([[800., 0., 480.], [0., 800., 270.], [0., 0., 1.]])
        self.valid = np.ones((540, 960), bool)

    def test_student_pointmap_uses_exact_asset_and_supplied_fov(self):
        native = StudentRuntime()
        result = MetricAnythingPointMapAdapter(native, PIN).predict(
            self.rgb, self.K, self.valid)
        self.assertGreater(native.options['fov_x'], 0)
        self.assertEqual(result.values[270, 480], 4.)
        self.assertEqual(result.native_points[270, 480, 0], 3.)
        self.assertEqual(result.metadata['checkpoint_identity'], PIN)
        self.assertEqual(result.metadata['component'], 'D8')

    def test_other_checkpoint_predicted_camera_and_wrong_grid_fail(self):
        with self.assertRaisesRegex(ValueError, 'PointMap checkpoint'):
            MetricAnythingPointMapAdapter(StudentRuntime(), 'depthmap')
        with self.assertRaisesRegex(ValueError, 'supplied camera'):
            MetricAnythingPointMapAdapter(StudentRuntime(predicted_camera=True), PIN).predict(
                self.rgb, self.K, self.valid)
        with self.assertRaisesRegex(ValueError, 'input grid'):
            MetricAnythingPointMapAdapter(StudentRuntime(wrong_grid=True), PIN).predict(
                self.rgb, self.K, self.valid)


if __name__ == '__main__':
    unittest.main()
