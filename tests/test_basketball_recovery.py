import unittest
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from basketball_recovery import native_options, search_manifest, check_fixed, window_intrinsics, POLICIES
from basketball_protocol import TRAINING
from basketball_vipe_pilot import intrinsic_stability


class RecoveryTests(unittest.TestCase):
    def test_native_policy_covers_registration_and_adjustment(self):
        import pycolmap
        for policy in POLICIES:
            mapper, ba, absolute = native_options(pycolmap, policy)
            free = policy == 'fixed-principal'
            self.assertEqual(mapper.mapper.abs_pose_refine_focal_length, free)
            self.assertEqual(mapper.ba_refine_focal_length, free)
            self.assertEqual(ba.refine_focal_length, free)
            self.assertEqual(absolute.refine_focal_length, free)
            self.assertFalse(mapper.ba_refine_principal_point)
            self.assertFalse(ba.refine_principal_point)
            self.assertFalse(mapper.mapper.abs_pose_refine_extra_params)
            with self.assertRaises(ValueError):
                native_options(pycolmap, policy, [5, 12])

    def test_drift_detection(self):
        prior = np.array([1000., 1000., 480., 270.])
        changed = prior.copy(); changed[0] += 100
        check_fixed(prior, changed, 'fixed-principal')
        with self.assertRaises(ValueError): check_fixed(prior, changed, 'fixed-intrinsics')
        changed = prior.copy(); changed[2] += .01
        with self.assertRaises(ValueError): check_fixed(prior, changed, 'fixed-principal')

    def test_independent_window_and_camera_priors(self):
        entries = [dict(camera_id=c, source_frame_id=f,
                        K_960x540=[[c+f+800., 0, 480.], [0, c+f+800., 270.], [0, 0, 1]])
                   for c in TRAINING for f in [50, 75, 125, 149]]
        early = window_intrinsics(dict(observations=entries), [50, 75])
        late = window_intrinsics(dict(observations=entries), [125, 149])
        self.assertNotEqual(early[1][0, 0], late[1][0, 0])
        self.assertNotEqual(early[1][0, 0], early[2][0, 0])
        self.assertEqual(early[1][0, 2], 480.5)
        with self.assertRaises(ValueError): window_intrinsics(dict(observations=entries), [0, 50])
        with self.assertRaises(ValueError): window_intrinsics(dict(observations=entries + [entries[0]]), [50, 75])

    def test_finite_search(self):
        manifest = search_manifest()
        self.assertEqual([len(v) for v in manifest['stages'].values()], [4, 8, 4])
        self.assertEqual(sum(map(len, manifest['stages'].values())) * 2, manifest['max_independent_runs'])
        self.assertFalse(set(manifest['early_frames']) & set(manifest['late_frames']))

    def test_expanded_prior_gate(self):
        self.assertTrue(intrinsic_stability([1000.] * 10, expected_count=10)['passed'])
        self.assertFalse(intrinsic_stability([1000.] * 9 + [1260.], expected_count=10)['passed'])
        self.assertFalse(intrinsic_stability([1000.] * 9, expected_count=10)['passed'])


if __name__ == '__main__':
    unittest.main()
