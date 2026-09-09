"""Exercise the production cropped matcher mapping with a known correspondence."""
from pathlib import Path
import sys
import unittest
import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from basketball_temporal_cloud import person_crop_warp


def grid(size):
    y, x = np.meshgrid((np.arange(size)+.5)*2/size-1, (np.arange(size)+.5)*2/size-1, indexing='ij')
    return np.stack((x, y), -1).astype(np.float32)


class CropTests(unittest.TestCase):
    def test_local_ids_do_not_define_cross_camera_identity(self):
        class Matcher:
            def match(self, a, b, device):
                self.sizes = (a.size, b.size)
                g = grid(32)
                return torch.from_numpy(np.concatenate((g, g), -1)), torch.ones((32, 32))
        matcher = Matcher()
        g = grid(32)
        offset = np.array([20/480, 30/270], np.float32)
        warp = np.concatenate((g, g+offset), -1)
        confidence = np.ones((32, 32), np.float32)
        labels0 = np.zeros((540, 960), np.uint8)
        labels1 = labels0.copy()
        labels0[100:300, 100:300] = 3
        labels1[130:330, 120:320] = 7
        rgb = np.zeros((540, 960, 3), np.uint8)
        refined, _, records = person_crop_warp(matcher, warp.copy(), confidence, rgb, rgb,
            labels0, labels1, {'3': 'person'}, {'7': 'person'})
        self.assertEqual(records[0]['target_instance'], 7)
        self.assertEqual(records[0]['source_instance'], 3)
        self.assertEqual(matcher.sizes, ((240, 240), (240, 240)))
        # OpenCV interpolation quantizes weights to 1/32 of one matcher pixel.
        np.testing.assert_allclose(refined, warp, atol=.0006)


if __name__ == '__main__':
    unittest.main()
