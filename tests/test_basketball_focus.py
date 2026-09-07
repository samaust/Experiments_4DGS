import sys
import unittest
from pathlib import Path
import cv2
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from basketball_focus import sharpness_maps, best_observations, support_radius, sustained


class FocusTests(unittest.TestCase):
    def test_blur_lowers_local_priority(self):
        rng = np.random.default_rng(0)
        image = rng.integers(0, 256, (100, 100), dtype=np.uint8)
        blurred = cv2.GaussianBlur(image, (9, 9), 2.)
        original_score, _ = sharpness_maps(image)
        blurred_score, _ = sharpness_maps(blurred)
        self.assertLess(float(np.median(blurred_score)), float(np.median(original_score)))
        _, flat_variance = sharpness_maps(np.full((100, 100), 127, np.uint8))
        self.assertTrue(np.all(flat_variance < 1e-4))

    def test_highest_score_wins_not_first_timestamp(self):
        candidates = [dict(score=s, frame=f, index=i, uv=[20.5, 40.5])
                      for s, f, i in [(1., 50, 0), (3., 75, 2), (3., 62, 1)]]
        self.assertEqual(best_observations(candidates)[0]['frame'], 62)
        self.assertEqual(best_observations(candidates[::-1]), best_observations(candidates))

    def test_affine_support_accounts_for_rotation_and_anisotropy(self):
        self.assertAlmostEqual(support_radius([0, 0, 0, -3, 2, 0]), 18.)
        self.assertAlmostEqual(support_radius([0, 0, 1, 0]), 8.)

    def test_sustained_and_inconclusive(self):
        self.assertFalse(sustained([1., .5, None, .5, .5], .3))
        self.assertTrue(sustained([1., .5, .5, .5], .3))
        self.assertFalse(sustained([1., 1.001, 1.002], .01))


if __name__ == '__main__': unittest.main()
