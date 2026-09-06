from pathlib import Path
import sys
import unittest

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from edgs_source import calibrated_projection, load_geometry

CHECKOUT = Path(__file__).resolve().parents[1] / '.local/EDGS'


class ProjectionTests(unittest.TestCase):
    def test_input_validation(self):
        with self.assertRaisesRegex(ValueError, '3x3'):
            calibrated_projection(torch.eye(4), torch.eye(4))
        bad = torch.eye(3)
        bad[0, 0] = float('nan')
        with self.assertRaisesRegex(ValueError, 'non-finite'):
            calibrated_projection(bad, torch.eye(4))
        with self.assertRaisesRegex(ValueError, 'floating-point'):
            calibrated_projection(torch.eye(3).long(), torch.eye(4))


@unittest.skipUnless(CHECKOUT.is_dir(), 'EDGS checkout unavailable')
class ReleasedGeometryTests(unittest.TestCase):
    def setUp(self):
        self.native, self.evidence = load_geometry(CHECKOUT)

    def test_calibrated_triangulation_nonidentity_pose(self):
        K = torch.tensor([[870., 0., 471.], [0., 910., 263.], [0., 0., 1.]])
        camera_a = torch.tensor([[.8, 0., .6, .2], [0., 1., 0., -.1],
                                 [-.6, 0., .8, .5], [0., 0., 0., 1.]])
        camera_b = camera_a.clone()
        camera_b[0, 3] -= .7
        points = torch.tensor([[.2, .1, 4., 1.], [-.3, .4, 6., 1.],
                               [.7, -.2, 3., 1.]])
        projections = [calibrated_projection(K, c) for c in (camera_a, camera_b)]
        pixels = []
        for camera, projection in zip((camera_a, camera_b), projections):
            independently_projected = (K @ (camera @ points.T)[:3]).T
            uv = independently_projected[:, :2] / independently_projected[:, 2:3]
            packed = points @ projection
            torch.testing.assert_close(packed[:, :2] / packed[:, 3:4], uv)
            pixels.append(uv)
        X, error_a, error_b = self.native['triangulate_points'](
            *projections, pixels[0][:, 0], pixels[0][:, 1],
            pixels[1][:, 0], pixels[1][:, 1], device='cpu')
        torch.testing.assert_close(X, points, atol=2e-5, rtol=2e-5)
        # Native error calculation adds 1e-4 to depth even for perfect matches.
        self.assertLess(float(max(error_a.max(), error_b.max())), .1)
        self.assertTrue(all(len(value) == 64 for value in self.evidence.values()))

    def test_native_neighbor_selection_excludes_self(self):
        vectors = torch.tensor([[0., 0.], [1., 0.], [5., 0.]])
        nearest = self.native['k_closest_vectors'](vectors, 1)
        torch.testing.assert_close(nearest, torch.tensor([[1], [0], [1]]))
