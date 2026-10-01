"""D6 must use supplied camera geometry and exactly three native refinements."""
from pathlib import Path
import sys
import unittest

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.moge_metric import MoGe3Adapter


class FakeMoGe3:
    def __init__(self, *, predicted_camera=False, invalid_metric=False, wrong_grid=False):
        self.predicted_camera = predicted_camera
        self.invalid_metric = invalid_metric
        self.wrong_grid = wrong_grid
        self.options = None

    def infer(self, image, **options):
        self.options = options
        height, width = image.shape[-2:]
        if self.wrong_grid:
            height -= 1
        points = torch.zeros((height, width, 3), dtype=torch.float32)
        points[..., 0] = 3
        points[..., 2] = -1 if self.invalid_metric else 4
        intrinsics = torch.tensor([[.7 if self.predicted_camera else 800 / 960, 0, .5],
            [0, 800 / 540, .5], [0, 0, 1]], dtype=torch.float32)
        return dict(points=points, depth=points[..., 2].clone(),
            mask=torch.ones((height, width), dtype=torch.bool), intrinsics=intrinsics)


class MoGe3Tests(unittest.TestCase):
    def setUp(self):
        self.image = np.zeros((540, 960, 3), np.uint8)
        self.K = np.array([[800., 0., 480.], [0., 800., 270.], [0., 0., 1.]])
        self.valid = np.ones((540, 960), bool)

    def test_three_step_supplied_fov_produces_z_without_reconversion(self):
        native = FakeMoGe3()
        output = MoGe3Adapter(native).predict(self.image, self.K, self.valid)
        self.assertEqual(native.options['refine_steps'], 3)
        self.assertFalse(native.options['return_per_step'])
        self.assertFalse(native.options['use_fp16'])
        self.assertGreater(native.options['fov_x'], 0)
        self.assertEqual(output.values[270, 480], 4.)
        self.assertEqual(output.native_points[270, 480, 0], 3.)
        self.assertEqual(output.metadata['native_refine_steps'], 3)

    def test_predicted_camera_wrong_grid_and_invalid_depth_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'supplied camera'):
            MoGe3Adapter(FakeMoGe3(predicted_camera=True)).predict(
                self.image, self.K, self.valid)
        with self.assertRaisesRegex(ValueError, 'input grid'):
            MoGe3Adapter(FakeMoGe3(wrong_grid=True)).predict(
                self.image, self.K, self.valid)
        with self.assertRaisesRegex(ValueError, 'valid metric'):
            MoGe3Adapter(FakeMoGe3(invalid_metric=True)).predict(
                self.image, self.K, self.valid)


if __name__ == '__main__':
    unittest.main()
