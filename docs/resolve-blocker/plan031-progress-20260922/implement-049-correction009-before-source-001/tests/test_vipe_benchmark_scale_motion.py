from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.access import Identity
from vipe_benchmark.config import load, training_cameras
from vipe_benchmark.files import file_record, write_json
from vipe_benchmark.motion import RoleMOG2, changing, pair_union
from vipe_benchmark.scale import evaluate


class ScaleAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.config = load()
        self.K = np.array([[800., 0, 480], [0, 800., 270], [0, 0, 1.]])
        y, x = np.meshgrid(np.linspace(20, 520, 10), np.linspace(10, 940, 12), indexing='ij')
        uv = np.column_stack((x.ravel(), y.ravel()))
        np.savez(self.root / 'samples.npz', point_ids=np.arange(len(uv)), xyz=np.zeros((len(uv), 3)),
                 uv=uv, K=self.K, camera_z=np.ones(len(uv)) * 2, valid=np.ones((540, 960), np.uint8))
        np.savez_compressed(self.root / 'depth.npz', depth=np.full((540, 960), 6., np.float32), valid=np.ones((540, 960), bool))
        self.rows = [dict(identity=Identity('depth', c, 100).record(), K=self.K.tolist(),
                          samples=file_record(self.root / 'samples.npz')) for c in training_cameras(self.config)]
        self.predictions = {c: file_record(self.root / 'depth.npz') for c in training_cameras(self.config)}
        self.provenance = dict(component_sha256='synthetic-test-component', sample_manifest_sha256='fixture')

    def tearDown(self):
        self.tmp.cleanup()

    def test_known_fit_and_frozen_check_do_not_refit(self):
        fit = evaluate(self.rows, self.predictions, self.config, provenance=self.provenance)
        self.assertEqual(fit['status'], 'passed')
        self.assertAlmostEqual(fit['scale'], 3.)
        write_json(self.root / 'fit.json', fit)
        for row in self.rows:
            row['identity']['frame'] = 175
        check = evaluate(self.rows, self.predictions, self.config, provenance=self.provenance,
                         frozen_fit=file_record(self.root / 'fit.json'))
        self.assertEqual(check['status'], 'passed')
        self.assertEqual(check['scale'], fit['scale'])

    def test_zero_support_camera_is_retained_as_failure(self):
        np.savez_compressed(self.root / 'invalid.npz', depth=np.full((540, 960), np.nan, np.float32),
                            valid=np.zeros((540, 960), bool))
        self.predictions[1] = file_record(self.root / 'invalid.npz')
        result = evaluate(self.rows, self.predictions, self.config, provenance=self.provenance)
        self.assertEqual(result['status'], 'blocked')
        self.assertIsNone(result['scale'])
        self.assertEqual(len(result['cameras']), 30)
        self.assertEqual(result['cameras'][0]['points'], 0)

    def test_missing_camera_and_changed_fit_candidate_rejected(self):
        with self.assertRaises(ValueError):
            evaluate(self.rows[:-1], self.predictions, self.config, provenance=self.provenance)
        fit = evaluate(self.rows, self.predictions, self.config, provenance=self.provenance)
        write_json(self.root / 'fit.json', fit)
        for row in self.rows:
            row['identity']['frame'] = 175
        with self.assertRaisesRegex(ValueError, 'another candidate'):
            evaluate(self.rows, self.predictions, self.config, provenance=dict(component_sha256='changed'),
                     frozen_fit=file_record(self.root / 'fit.json'))


class MotionTests(unittest.TestCase):
    def test_m0_threshold_dilation_pair_identity_and_m1_window(self):
        class Loader:
            config = load()
            def load(self, identity):
                image = np.zeros((20, 20, 3), np.uint8)
                if identity.frame == 21:
                    image[10, 10] = 21
                return image
            def row(self, identity):
                return dict(rgb=dict(sha256=f'fixture-frame-{identity.frame}'))
        loader = Loader()
        first, a = changing(Identity('reconstruction', 1, 20, 20), 'M0', loader)
        second, b = changing(Identity('reconstruction', 1, 21, 20), 'M0', loader)
        np.testing.assert_array_equal(first, second)
        self.assertEqual(int(first.sum()), 81)
        self.assertEqual(a, b)
        median, state = changing(Identity('reconstruction', 1, 21, 21), 'M1', loader)
        self.assertEqual(int(median.sum()), 81)
        self.assertEqual(state['context_frames'], list(range(17, 26)))

    def test_mog2_cold_start_chronology_and_role_reset(self):
        with self.assertRaises(ValueError):
            RoleMOG2('calibration', 1, 175)
        model = RoleMOG2('calibration', 1, 150)
        identity = Identity('calibration', 1, 150)
        image = np.zeros((20, 20, 3), np.uint8)
        mask, native, state = model.advance(identity, image, 'synthetic')
        self.assertTrue(mask.all())
        self.assertTrue((native == 255).all())
        self.assertEqual(state['context_frames'], [150])
        with self.assertRaises(ValueError):
            model.advance(identity, image, 'synthetic')
        with self.assertRaises(ValueError):
            model.advance(Identity('calibration', 2, 151), image, 'synthetic')

    def test_pair_static_uses_union(self):
        np.testing.assert_array_equal(pair_union(np.array([[0, 1]], bool), np.array([[1, 0]], bool)), [[1, 1]])


if __name__ == '__main__':
    unittest.main()
