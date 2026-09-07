import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from basketball_audit import frame_roles, validate_probe
from basketball_vipe_pilot import fitting_frame, intrinsic_stability


class AuditTests(unittest.TestCase):
    def probe(self):
        return {'streams': [{'width': 1920, 'height': 1080, 'nb_read_frames': '250',
                             'r_frame_rate': '25/1', 'avg_frame_rate': '25/1'}],
                'frames': [{'width': 1920, 'height': 1080,
                            'best_effort_timestamp_time': f'{i/25:.6f}'} for i in range(250)]}

    def test_complete_constant_timing(self):
        times = validate_probe(self.probe())
        self.assertEqual(len(times), 250)
        self.assertEqual(times[-1], 9.96)

    def test_missing_frame(self):
        probe = self.probe()
        del probe['frames'][80]
        with self.assertRaisesRegex(ValueError, 'missing frames'):
            validate_probe(probe)

    def test_irregular_or_duplicate_timestamp(self):
        for replacement in ['3.160000', '3.210000']:
            probe = self.probe()
            probe['frames'][80]['best_effort_timestamp_time'] = replacement
            with self.assertRaisesRegex(ValueError, 'timestamps'):
                validate_probe(probe)

    def test_dimensions_and_rate(self):
        for field, value in [('width', 960), ('avg_frame_rate', '24/1')]:
            probe = self.probe()
            probe['streams'][0][field] = value
            with self.assertRaises(ValueError):
                validate_probe(probe)

    def test_frozen_intrinsic_gate(self):
        self.assertTrue(intrinsic_stability([900, 900, 900, 787.5, 1012.5])['passed'])
        self.assertFalse(intrinsic_stability([900, 900, 900, 787.5, 1013.5])['passed'])
        for values in [[float('nan')]*5, [float('inf')]*5, [-1]*5, []]:
            self.assertFalse(intrinsic_stability(values)['passed'])

    def test_all_priors_allow_held_out_only_in_fitting_window(self):
        self.assertEqual(fitting_frame(0, 50, all_priors=True), 0)
        for camera, frame in [(0, 49), (0, 150), (34, 50), (5, 100)]:
            with self.assertRaises(ValueError):
                fitting_frame(camera, frame, all_priors=True)

    def test_frame_roles_partition(self):
        roles = frame_roles()
        groups = [set(roles[key]) for key in ['experiment', 'fit', 'selection', 'validation']]
        self.assertEqual(set.union(*groups), set(range(250)))
        self.assertEqual(sum(map(len, groups)), 250)
        self.assertEqual(len(roles['training_cameras']), 30)
        self.assertFalse(set(roles['training_cameras']) & set(roles['held_out_cameras']))

    def test_fit_cannot_access_experiment_selection_validation_or_held_out(self):
        for camera, frame in [(4, 49), (4, 150), (4, 200), (0, 50), (10, 100), (34, 100)]:
            with self.assertRaises(ValueError):
                fitting_frame(camera, frame)
        self.assertEqual(fitting_frame(4, 50), 0)
        self.assertEqual(fitting_frame(29, 149), 99)


if __name__ == '__main__':
    unittest.main()
