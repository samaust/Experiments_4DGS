import sys
import unittest
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from atgs_scene import make_camera


class ATGSCameraTests(unittest.TestCase):
    def calibration(self):
        return dict(width=80, height=60, K=[[70, 0, 33], [0, 65, 28], [0, 0, 1]],
                    world_to_camera_R=[[0, 0, 1], [0, 1, 0], [-1, 0, 0]],
                    world_to_camera_T=[1, 2, 3])

    def test_offcenter_world_projection_and_depth(self):
        c = self.calibration()
        view = make_camera(c, .234, device='cpu')
        points = np.array([[.1, .2, 2], [-.3, .4, 3], [0, 0, 1]])
        world = (points - c['world_to_camera_T']) @ np.array(c['world_to_camera_R'])
        clip = torch.tensor(np.c_[world, np.ones(3)], dtype=torch.float32) @ view.full_proj_transform
        ndc = (clip[:, :2] / clip[:, 3:]).numpy()
        pixels = ((ndc + 1) * [80, 60] - 1) / 2
        projected = points @ np.array(c['K']).T
        np.testing.assert_allclose(pixels, projected[:, :2] / projected[:, 2:] - .5, atol=2e-5)
        depth = (clip[:, 2] / clip[:, 3]).numpy()
        expected = view.zfar / (view.zfar - view.znear) * (1 - view.znear / points[:, 2])
        np.testing.assert_allclose(depth, expected, atol=1e-6)
        self.assertEqual(view.time, .234)
        self.assertEqual(view.timestamp, view.time)
        self.assertIsNone(view.mask)
        self.assertIsNone(view.image_path)

    def test_reject_invalid_time_and_calibration(self):
        for time in (-.01, 1., float('nan')):
            with self.assertRaises(ValueError):
                make_camera(self.calibration(), time, device='cpu')
        calibration = self.calibration()
        calibration['K'][0][1] = 1
        with self.assertRaises(ValueError):
            make_camera(calibration, .5, device='cpu')
