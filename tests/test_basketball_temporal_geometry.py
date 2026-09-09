import unittest
from pathlib import Path
import sys
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from basketball_temporal_geometry import crop_to_image, geometry_gate, project, triangulate, velocity_from_support, track_lk


class GeometryTests(unittest.TestCase):
    def setUp(self):
        self.centers = np.array([[-1., 0, 0], [0., 0, 0], [1., 0, 0]])
        K = np.array([[800., 0, 480], [0, 800, 270], [0, 0, 1]])
        self.P = np.array([K @ np.column_stack((np.eye(3), -c)) for c in self.centers])
        self.points = np.array([[0., 0, 10.], [0, 1, 10.]])

    def test_crop_pixel_center_and_roundtrip(self):
        uv = np.array([[.5, .5], [99.5, 49.5]])
        np.testing.assert_allclose(crop_to_image(uv, (10, 20, 210, 120), (100, 50)), [[11, 21], [209, 119]])
        observed = np.array([project(self.points, p)[0] for p in self.P])
        result = triangulate(observed, self.P)
        np.testing.assert_allclose(result, self.points, atol=1e-10)
        self.assertTrue(geometry_gate(result, observed, self.P, self.centers)[0].all())
        observed[2, 0, 1] += 20
        self.assertFalse(geometry_gate(result, observed, self.P, self.centers)[0][0])

    def test_measured_motion_units_missing_occluded_and_wrong_support(self):
        end = self.points + [0.02, 0, 0]
        uv = np.array([project(end, p)[0] for p in self.P])
        valid = np.ones((3, 2), bool)
        transform = np.diag([3., 3., 3., 1.])
        velocity, measured = velocity_from_support(self.points, uv, self.P, self.centers, valid, [1, 2, 3], transform)
        np.testing.assert_allclose(velocity, [[3, 0, 0], [3, 0, 0]], atol=1e-10)
        self.assertTrue(measured.all())
        valid[2, 0] = False  # Occlusion or rejected temporal instance.
        uv[2, 1, 1] += 30  # Incorrect correspondence/identity switch.
        velocity, measured = velocity_from_support(self.points, uv, self.P, self.centers, valid, [1, 2, 3], transform)
        self.assertFalse(measured.any())
        self.assertFalse(velocity.any())
        with self.assertRaises(ValueError):
            velocity_from_support(self.points, uv, self.P, self.centers, valid, [1, 2, 2], transform)

    def test_negative_depth_and_nonfinite(self):
        points = np.array([[0., 0, -10.], [np.nan, 0, 10.]])
        uv = np.array([project(points, p)[0] for p in self.P])
        self.assertFalse(geometry_gate(points, uv, self.P, self.centers)[0].any())

    def test_lk_translation_rejects_temporal_instance_switch(self):
        import cv2
        rng = np.random.default_rng(42)
        first = rng.integers(0, 256, (512, 512, 3), dtype=np.uint8)
        second = cv2.warpAffine(first, np.float32([[1, 0, 2], [0, 1, 1]]), (512, 512))
        labels = np.ones((512, 512), np.uint8)
        points = np.array([[200.5, 200.5], [300.5, 300.5]])
        end, valid = track_lk(first, second, points, labels, labels)
        self.assertTrue(valid.all())
        np.testing.assert_allclose(end, points+[2, 1], atol=.1)
        _, valid = track_lk(first, second, points, labels, labels*2)
        self.assertFalse(valid.any())


if __name__ == '__main__':
    unittest.main()
