from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from freetimegs_normalization import load_normalization, normalize_camera

CHECKOUT = Path(__file__).resolve().parents[1] / '.local/FreeTimeGsVanilla'


@unittest.skipUnless(CHECKOUT.is_dir(), 'native normalization source unavailable')
class NativeNormalizationTests(unittest.TestCase):
    def test_projection_and_motion_invariance(self):
        helpers, evidence = load_normalization(CHECKOUT)
        transform = np.array([[0., -2., 0., 1.], [2., 0., 0., -1.],
                              [0., 0., 2., .5], [0., 0., 0., 1.]], dtype=np.float32)
        K = torch.tensor([[[800., 0., 471.], [0., 900., 267.], [0., 0., 1.]]])
        c2w = torch.eye(4)[None]
        c2w[0, :3, 3] = torch.tensor([.2, -.1, .3])
        camera = SimpleNamespace(camtoworlds=c2w.clone(), Ks=K)
        converted = normalize_camera(camera, transform, helpers['transform_cameras'])
        torch.testing.assert_close(converted.Ks, K, rtol=0, atol=0)
        R = converted.camtoworlds[0, :3, :3]
        torch.testing.assert_close(R.T @ R, torch.eye(3))
        position = np.array([[.5, .7, 4.]], dtype=np.float32)
        velocity = np.array([[.1, -.2, .05]], dtype=np.float32)
        transformed_position = helpers['transform_points'](transform, position)
        transformed_velocity = velocity @ transform[:3, :3].T
        for t in (-.2, 0., .3):
            original = torch.from_numpy(position+t*velocity)
            changed = torch.from_numpy(transformed_position+t*transformed_velocity)
            def project(points, view):
                homogeneous = torch.cat((points, torch.ones((len(points), 1))), dim=1)
                pixels = (K[0] @ (view @ homogeneous.T)[:3]).T
                return pixels[:, :2]/pixels[:, 2:3]
            torch.testing.assert_close(project(original, torch.linalg.inv(c2w[0])),
                                       project(changed, converted.viewmats[0]), rtol=1e-5, atol=1e-4)
        self.assertEqual(len(evidence['normalization_ast_sha256']), 64)
