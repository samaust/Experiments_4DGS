from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.metrics import (boundary_counts, boundary_score, conditional_domain, instance_matching,
    paired_bootstrap, pixel_counts, pixel_scores, role_precision_bounds, temporal_counts, temporal_groups)
from vipe_benchmark.neighbors import rank
from vipe_benchmark.selection import combined, select


class MetricsTests(unittest.TestCase):
    def test_hand_computed_pixel_counts_and_empty_cases(self):
        truth = np.array([[1, 1], [0, 0]], bool)
        prediction = np.array([[1, 0], [1, 0]], bool)
        scores = pixel_scores(pixel_counts(prediction, truth, np.ones_like(truth)))
        self.assertEqual(scores, dict(precision=.5, recall=.5, iou=1/3, dice=.5))
        empty = np.zeros_like(truth)
        self.assertIsNone(pixel_scores(pixel_counts(empty, empty, ~empty))['iou'])
        self.assertEqual(pixel_counts(prediction, empty, ~empty)['negative_false_positive_pixels'], 2)

    def test_two_pixel_boundary(self):
        a, b = np.zeros((20, 20), bool), np.zeros((20, 20), bool)
        a[5:10, 5:10], b[5:10, 7:12] = True, True
        self.assertEqual(boundary_score(boundary_counts(a, b, np.ones_like(a))), 1.)

    def test_hungarian_eligible_count_and_stable_tie(self):
        truth = np.array([[1, 1, 2, 2]])
        pred = np.array([[8, 8, 8, 8]])
        result = instance_matching(pred, truth, [8], [2, 1], np.ones_like(pred, bool))
        self.assertEqual(result['matches'], [dict(truth_id=1, prediction_id=8, iou=.5)])
        self.assertEqual((result['tp'], result['fp'], result['fn']), (1, 0, 1))

    def test_role_domains_keep_background_and_ignore_uncertain(self):
        labels = np.array([[1, 2, 3, 0]])
        meta = {str(i): {'class': 'person', 'role': r} for i, r in [(1, 'player'), (2, 'other-person'), (3, 'uncertain')]}
        domain = conditional_domain(np.ones_like(labels, bool), labels, meta, 'player')
        np.testing.assert_array_equal(domain, [[1, 0, 0, 1]])
        self.assertEqual(role_precision_bounds(2, 3), [.4, 1.])
        self.assertIsNone(role_precision_bounds(0, 3))

    def test_temporal_switch_and_missed_keyframe_remain_counted(self):
        truth0 = np.array([[1, 1, 0, 0]])
        truth1 = np.array([[1, 1, 2, 2]])
        p0 = np.array([[7, 7, 0, 0]])
        p1 = np.array([[8, 8, 0, 0]])
        domain = np.ones_like(p0, bool)
        m0 = instance_matching(p0, truth0, [7], [1], domain)
        m1 = instance_matching(p1, truth1, [8], [1, 2], domain)
        rows = [dict(first_id=1, second_id=1), dict(first_id=None, second_id=2)]
        result = temporal_counts(p0, p1, truth0, truth1, m0, m1, rows, domain, domain)
        self.assertEqual((result['id_switches'], result['visible_successors'], result['matched_successors']), (1, 2, 1))
        self.assertEqual(result['area_change_errors'], [0.])

    def test_groups_preserve_overlapping_pairs(self):
        frames = [0, 1, 5, 6, 20, 21, 22, 23, 24, 25, 26, 45, 46]
        self.assertEqual(temporal_groups(frames), [[0, 1], [5, 6], [20, 21, 22, 23, 24, 25, 26], [45, 46]])

    def test_bootstrap_pools_within_camera_then_equal_camera(self):
        # Camera 1 has many more pixels; pooling cameras would give .991 rather
        # than the required equal-camera .55 for A.
        a = {(1, 0): dict(tp=90, fp=0, fn=0), (2, 0): dict(tp=1, fp=0, fn=9)}
        b = {(1, 0): dict(tp=90, fp=0, fn=0), (2, 0): dict(tp=5, fp=0, fn=5)}
        r = paired_bootstrap({'A': a, 'B': b}, lambda counts: pixel_scores(counts)['recall'])
        self.assertAlmostEqual(r['estimates']['A'], .55)
        self.assertAlmostEqual(r['differences']['B-A']['estimate'], .2)
        self.assertEqual(r['differences']['B-A']['interval_95'], [0., .4])
        self.assertEqual(r['differences']['B-A']['conclusion'], 'inconclusive')
        with self.assertRaises(ValueError):
            paired_bootstrap({'A': a, 'B': {(1, 0): b[1, 0]}}, lambda c: 1)


class NeighborAndSelectionTests(unittest.TestCase):
    def test_raw_count_and_jaccard_are_different_and_positive_only(self):
        tracks = {1: {1, 2, 3, 4}, 2: set(range(1, 101)), 3: {1, 2}, 4: {1}, 5: set()}
        self.assertEqual(rank('N0', 1, tracks, training=list(tracks))['neighbors'], [2, 3, 4])
        self.assertEqual(rank('N1', 1, tracks, training=list(tracks))['neighbors'], [3, 4, 2])
        tracks[4] = set()
        result = rank('N0', 1, tracks, training=list(tracks))
        self.assertEqual(result['status'], 'blocked')
        self.assertEqual(result['neighbors'], [])
        with self.assertRaises(ValueError):
            rank('N0', 1, tracks, training=[1, 2, 3, 4])

    def test_n2_greedy_coverage_tuple_with_independent_geometry(self):
        K = np.array([[100., 0, 480], [0, 100., 270], [0, 0, 1]])
        cameras = {i: dict(K=K, R=np.eye(3), t=np.array([-offset, 0., 0.]),
                          center=np.array([offset, 0., 0.])) for i, offset in [(1, 0), (2, 1), (3, -1), (4, 2), (5, 0)]}
        points = {1: [-12., -8., 5.], 2: [2., 2., 5.], 3: [13., 9., 5.], 4: [-2., -2., 5.]}
        tracks = {1: set(points), 2: {1, 2}, 3: {2, 3}, 4: {4}, 5: set(points)}
        masks = {i: np.ones((540, 960), bool) for i in cameras}
        result = rank('N2', 1, tracks, training=list(tracks), points=points, cameras=cameras, footprints=masks)
        self.assertEqual(result['status'], 'complete')
        self.assertNotIn(5, result['neighbors'])  # coincident cameras fail 1°
        self.assertEqual(set(result['neighbors']), {2, 3, 4})
        for row in result['rounds'][0]:
            self.assertEqual(len(row['score']), 7)
        self.assertEqual(result['covered_point_ids'], [1, 2, 3, 4])

    def test_finalist_ranking_and_only_prespecified_default(self):
        rows = {f'S{i}': dict(status='complete', person_dice=.9, ball_dice=.5,
                leakage=.2, retained_static_features=.7, boundary_f1=.8) for i in range(1, 5)}
        self.assertEqual(select('S', rows)['selected'], 'S1')
        rows['S3']['ball_dice'] = .6
        self.assertEqual(select('S', rows)['selected'], 'S3')
        rows['S2']['ball_dice'] = .6 + 1e-14
        self.assertEqual(select('S', rows)['selected'], 'S2')
        self.assertEqual(select('S', {}, missing_semantic_class=True)['status'], 'unverified')
        blocked = {f'M{i}': dict(status='blocked', reason='missing source') for i in range(3)}
        self.assertIsNone(select('M', blocked)['selected'])

    def test_combined_depth_gate_and_license_blocks_no_replacement(self):
        finalists = {k: dict(selected=v) for k, v in [('S', 'S2'), ('M', 'M1'), ('N', 'N2')]}
        result = combined(finalists, {'D3': dict(fit='passed', check='passed')}, {})
        self.assertEqual(result['C1']['components'][1], 'D1')
        self.assertEqual(result['C2']['components'][1], 'D2')
        self.assertTrue(all(r['status'] == 'blocked' for r in result.values()))


if __name__ == '__main__':
    unittest.main()
