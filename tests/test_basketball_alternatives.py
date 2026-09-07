import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from basketball_alternatives_protocol import (
    CAMERAS, TRAINING, HELD_OUT, SNAPSHOT_PAIRS, check_inputs,
    manifest, rank_complete, screening_matrix,
)


class AlternativesProtocolTests(unittest.TestCase):
    def test_restored_physical_ids_and_disjoint_roles(self):
        self.assertEqual(CAMERAS, tuple(range(34)))
        self.assertEqual(len(TRAINING), 30)
        self.assertEqual(HELD_OUT, (0,10,20,30))
        self.assertIn(5, TRAINING)
        self.assertIn(19, TRAINING)
        roles = manifest()
        keys = ('fit_frames','selection_frames','validation_frames','downstream_frames')
        self.assertEqual(sum(len(roles[k]) for k in keys), 250)
        self.assertEqual(len(set().union(*(roles[k] for k in keys))), 250)
        self.assertIsNone(roles['calibration_gpu_limit_seconds'])
        self.assertEqual(len(screening_matrix()), 48)

    def test_incomplete_duplicate_held_out_and_leaked_frames_rejected(self):
        check_inputs(TRAINING, [50,99])
        for ids in (TRAINING[:-1], TRAINING[:-1]+(TRAINING[0],), TRAINING+(0,)):
            with self.assertRaises(ValueError):
                check_inputs(ids, [50])
        for frames in ([49], [150], [200], [50,50], []):
            with self.assertRaises(ValueError):
                check_inputs(TRAINING, frames)

    def test_ranking_rejects_omission_and_nonfinite_metrics(self):
        rows = [dict(method='global', frames=pair, complete=True, cameras=list(TRAINING),
                     max_rotation_degrees=.4, max_center_fraction=.009,
                     wall_seconds=2.) for pair in SNAPSHOT_PAIRS]
        self.assertAlmostEqual(rank_complete(rows)[0]['score'], .9)
        self.assertEqual(rank_complete(rows[:-1]), [])
        rows[0]['cameras'] = list(TRAINING[:-1])
        self.assertEqual(rank_complete(rows), [])
        rows[0]['cameras'] = list(TRAINING)
        rows[0]['max_rotation_degrees'] = float('nan')
        self.assertEqual(rank_complete(rows), [])


if __name__ == '__main__':
    unittest.main()
