"""Plan 027 fusion invariants and corruption rejection."""
import sys
from pathlib import Path
import unittest
import tempfile
import json
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from basketball_dense_fusion import fuse, validate, voxel_width, freeze, load_frozen
from basketball_study import KEYFRAMES, digest, write_new
from basketball_dense_training import ARMS


class FusionTests(unittest.TestCase):
    def test_width_uses_unique_positive_distances(self):
        self.assertEqual(voxel_width([[0,0,0], [0,0,0], [2,0,0], [4,0,0]]), 1)

    def test_medians_mapping_and_order_independence(self):
        xyz = np.array([[.1,0,0], [.9,0,0], [-.1,0,0], [2,0,0]], np.float32)
        rgb = np.array([[0,0,0], [1,1,1], [.2,.2,.2], [.4,.4,.4]], np.float32)
        p, c, mapping, voxels = fuse(xyz, rgb, 1)
        np.testing.assert_array_equal(mapping, [1,1,0,2])
        np.testing.assert_allclose(p[1], [.5,0,0])
        np.testing.assert_allclose(c[1], [.5,.5,.5])
        q, d, inverse, cells = fuse(xyz[::-1], rgb[::-1], 1)
        np.testing.assert_array_equal(p, q)
        np.testing.assert_array_equal(c, d)
        np.testing.assert_array_equal(mapping, inverse[::-1])
        np.testing.assert_array_equal(voxels, cells)

    def test_empty_static_is_permitted(self):
        p, c, m, v = fuse(np.empty((0,3)), np.empty((0,3)), 1)
        self.assertEqual(p.shape, (0,3))
        self.assertEqual(len(m), 0)

    def test_invalid_values_rejected(self):
        for width in (0, -1, float('nan')):
            with self.assertRaises(ValueError):
                fuse(np.ones((1,3)), np.ones((1,3)), width)

    def test_freeze_keeps_foreground_times_and_static_contributors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cloud = root/'cloud'
            cloud.mkdir()
            norm = {'test_normalization': 1}
            write_new(root/'width.json', dict(width=1., normalization=norm, files={}))
            write_new(cloud/'config.json', dict(mode='coarse', frames=list(KEYFRAMES), normalization=norm))
            records = []
            for frame in KEYFRAMES:
                path = cloud/f'{frame}.npz'
                np.savez(path, positions=np.array([[.1,0,0],[.2,0,0]],np.float32),
                    colors=np.ones((2,3),np.float32), velocities=np.zeros((2,3),np.float32),
                    times=np.full((2,1),frame/50,np.float32), durations=np.full((2,1),.2,np.float32),
                    region=np.array([0,1]), velocity_valid=np.array([False,False]), camera_ids=np.array([1,2,3]))
                records.append(dict(reference=1, frame=frame, path=path.name, sha256=digest(path)))
            write_new(cloud/'result.json', dict(status='geometry-generated-not-accepted',
                config_sha256=digest(cloud/'config.json'), records=records))
            freeze(cloud,root/'width.json',root/'frozen',ARMS[0])
            arrays,record = load_frozen(root/'frozen',ARMS[0],norm)
            self.assertFalse(record['visual_acceptance'])
            self.assertEqual(record['physical_static_points'],1)
            self.assertEqual(record['temporal_static_copies'],9)
            self.assertEqual(record['foreground_observations'],9)
            np.testing.assert_array_equal(arrays['foreground_observation_id'][9:],np.arange(1,18,2))
            np.testing.assert_array_equal(arrays['times'][9:,0],np.array(KEYFRAMES,np.float32)/50)
            with np.load(root/'frozen/observation-mapping.npz') as mapping:
                np.testing.assert_array_equal(mapping['static_observation_id'],np.arange(0,18,2))
                np.testing.assert_array_equal(mapping['static_physical_id'],np.zeros(9))
            with self.assertRaisesRegex(ValueError,'recipe'):
                load_frozen(root/'frozen',ARMS[1],norm)
            (root/'frozen/initialization.npz').write_bytes(b'corruption')
            with self.assertRaisesRegex(ValueError,'hash mismatch'):
                load_frozen(root/'frozen',ARMS[0],norm)

    def test_native_validity(self):
        a = dict(positions=np.ones((2,3),np.float32), colors=np.ones((2,3),np.float32),
            velocities=np.zeros((2,3),np.float32), times=np.array([[0],[.5]],np.float32),
            durations=np.full((2,1),.2,np.float32), region=np.array([0,1]), velocity_valid=np.array([False,False]))
        validate(a)
        a['velocities'][1,0] = 1
        with self.assertRaisesRegex(ValueError, 'velocity'):
            validate(a)
        a['velocities'][:] = 0
        a['times'][1] = .4
        with self.assertRaisesRegex(ValueError, 'held-out'):
            validate(a)


if __name__ == '__main__':
    unittest.main()
