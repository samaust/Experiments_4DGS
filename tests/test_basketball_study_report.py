from pathlib import Path
import sys
import unittest
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from basketball_study_report import matched_table


class MatchedStudyTests(unittest.TestCase):
    def test_blocks_not_pixels_and_matched_duration_difference(self):
        runs = [dict(seed=s, frames=[dict(split='heldout-camera', frame_id=f,
                full={'psnr': float(s+f//5)}) for f in range(10)]) for s in range(3)]
        blocks, values = matched_table(runs, 'heldout-camera', 'full/psnr')
        self.assertEqual(blocks, [0, 1])
        np.testing.assert_array_equal(values, [[0, 1], [1, 2], [2, 3]])
        for run in runs:
            for row in run['frames']:
                row['full']['psnr'] += 2
        _, longer = matched_table(runs, 'heldout-camera', 'full/psnr')
        np.testing.assert_array_equal(longer-values, np.full((3, 2), 2))

    def test_incomplete_seed_or_block_is_rejected(self):
        runs = [dict(seed=s, frames=[dict(split='temporal-interpolation', frame_id=22,
                temporal_difference_mae=.1)]) for s in range(3)]
        with self.assertRaises(ValueError):
            matched_table(runs[:2], 'temporal-interpolation', 'temporal_difference_mae')
        runs[-1]['frames'][0]['frame_id'] = 27
        with self.assertRaises(ValueError):
            matched_table(runs, 'temporal-interpolation', 'temporal_difference_mae')


if __name__ == '__main__':
    unittest.main()
