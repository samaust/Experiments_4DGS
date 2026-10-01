"""D5's supplied-FoV metric geometry through an independent fake native runtime."""
from pathlib import Path
import math
import sys
import unittest

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.moge_metric import MoGe2Adapter, supplied_horizontal_fov, restore_pointmap


class FakeMoGe2:
    def __init__(self, *, radial=False):
        self.radial = radial
        self.calls = []

    def infer(self, image, **options):
        self.calls.append((image, options))
        height, width = image.shape[-2:]
        points = torch.zeros((height, width, 3), dtype=torch.float32)
        points[..., 0] = 3
        points[..., 2] = 4
        depth = torch.full((height, width), 5. if self.radial else 4.)
        mask = torch.ones((height, width), dtype=torch.bool)
        mask[0, 0] = False
        points[0, 0] = torch.inf
        depth[0, 0] = torch.inf
        return dict(points=points, depth=depth, mask=mask,
                    intrinsics=torch.eye(3))


class MoGe2Tests(unittest.TestCase):
    def setUp(self):
        self.image = np.full((540, 960, 3), 127, np.uint8)
        self.K = np.array([[800., 0., 480.], [0., 800., 270.], [0., 0., 1.]])
        self.valid = np.ones((540, 960), bool)

    def test_known_z_off_axis_points_are_not_radial_or_focal_scaled(self):
        runtime = FakeMoGe2()
        result = MoGe2Adapter(runtime).predict(self.image, self.K, self.valid)
        self.assertEqual(result.domain, 'camera_z_metres')
        self.assertAlmostEqual(result.metadata['fov_x_degrees'],
            2 * math.degrees(math.atan(960 / 1600)))
        self.assertEqual(runtime.calls[0][1]['fov_x'], result.metadata['fov_x_degrees'])
        self.assertEqual(runtime.calls[0][1]['resolution_level'], 9)
        self.assertFalse(result.valid[0, 0])
        self.assertTrue(np.isnan(result.values[0, 0]))
        self.assertEqual(result.values[270, 480], 4.)
        self.assertEqual(result.native_points[270, 480, 0], 3.)
        self.assertEqual(result.metadata['conversion_count'], 0)

    def test_geometry_and_depth_mismatch_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'point-map camera-z'):
            MoGe2Adapter(FakeMoGe2(radial=True)).predict(self.image, self.K, self.valid)
        shifted = self.K.copy()
        shifted[0, 2] = 479
        with self.assertRaisesRegex(ValueError, 'centered pinhole'):
            supplied_horizontal_fov(shifted, 960, 540)

    def test_resize_rejects_invalid_interpolation_contributors(self):
        points = np.ones((2, 2, 3), np.float32)
        points[..., 2] = 4
        depth = np.full((2, 2), 4., np.float32)
        valid = np.ones((2, 2), bool)
        valid[0, 0] = False
        points[0, 0] = np.inf
        depth[0, 0] = np.inf
        restored = restore_pointmap(points, depth, valid, (4, 4),
                                    np.ones((4, 4), bool))
        self.assertFalse(restored.valid[0, 0])
        self.assertFalse(restored.valid[1, 1])
        self.assertTrue(restored.valid[3, 3])
        self.assertEqual(restored.values[3, 3], 4.)


if __name__ == '__main__':
    unittest.main()
