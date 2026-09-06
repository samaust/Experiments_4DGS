from pathlib import Path
import sys
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from freetimegs_initialization import assemble_initialization, load_velocity_helper, load_cloud

CHECKOUT = Path(__file__).resolve().parents[1] / '.local/FreeTimeGsVanilla'


@unittest.skipUnless(CHECKOUT.is_dir(), 'reproduction checkout unavailable')
class TemporalInitializationTests(unittest.TestCase):
    def test_native_displacements_and_invalid_matches(self):
        velocity, digest = load_velocity_helper(CHECKOUT)
        a = np.array([[0., 0., 0.], [10., 0., 0.]], dtype=np.float32)
        b = np.array([[.1, 0., 0.]], dtype=np.float32)
        displacement, valid = velocity(a, b, n_workers=1)
        np.testing.assert_allclose(displacement, [[.1, 0, 0], [0, 0, 0]])
        np.testing.assert_array_equal(valid, [True, False])
        self.assertEqual(len(digest), 64)

    def test_corrected_time_velocity_units_and_duration(self):
        scene = SimpleNamespace(sha256='manifest', manifest=dict(source_fps=60,
            time=dict(duration_seconds=1.02)))
        frames = {f for k in range(4120, 4180, 5) for f in (k, k + 1)}
        clouds = {f: Path(str(f)) for f in frames}
        dt = 1 / 61.2

        def fake_cloud(directory, actual_scene, frame):
            self.assertIs(actual_scene, scene)
            offset = .1 if (frame - 4120) % 5 == 1 else 0.
            return (np.array([[offset, 0., 0.]], dtype=np.float32),
                    np.ones((1, 3), dtype=np.float32),
                    dict(normalized_time=.001 + (frame - 4120) * dt))

        with patch('freetimegs_initialization.load_cloud', side_effect=fake_cloud):
            arrays, evidence = assemble_initialization(CHECKOUT, scene, clouds)
        self.assertEqual(arrays['positions'].shape, (12, 3))
        np.testing.assert_allclose(arrays['velocities'][:, 0], .1 / dt)
        np.testing.assert_allclose(arrays['durations'], 15 * dt)
        np.testing.assert_allclose(arrays['times'][:, 0], .001 + np.arange(12) * 5 * dt)
        self.assertEqual(evidence['valid_velocity_points'], 12)
        self.assertEqual(evidence['duration_gap_multiplier'], 3)

    def test_missing_successor_rejected_before_loading(self):
        with self.assertRaisesRegex(ValueError, 'exactly all'):
            assemble_initialization(CHECKOUT, None, {4120: Path('cloud')})

    def test_cloud_provenance_rejects_wrong_frame_and_held_out(self):
        keys = [(f'{i:04d}', 4120) for i in range(24) if i != 15]
        scene = SimpleNamespace(sha256='manifest', training_keys=lambda frame: keys,
                                frames={key: dict(sha256='image', normalized_time=.01) for key in keys})
        evidence = dict(status='triangulated', manifest_sha256='manifest', source_frame=4121,
                        inputs=[dict(camera_id=c, frame_id=f, sha256='image') for c, f in keys])
        with patch('pathlib.Path.read_text', return_value=json.dumps(evidence)):
            with self.assertRaisesRegex(ValueError, 'frame or status'):
                load_cloud('unused', scene, 4120)
        evidence['source_frame'] = 4120
        evidence['inputs'][0]['camera_id'] = '0015'
        with patch('pathlib.Path.read_text', return_value=json.dumps(evidence)):
            with self.assertRaisesRegex(ValueError, 'training split'):
                load_cloud('unused', scene, 4120)
