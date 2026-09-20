from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.access import Identity, guard, motion_context, output_identities, validate_grid, validate_membership
from vipe_benchmark.config import counts, execution_order, jobs, load
from vipe_benchmark.contracts import (bilinear_valid, depth, instances, merge_logits, metric_depth,
                                     ray_range_to_z, renderer_K, sample_depth, static_mask, transform_K)
from vipe_benchmark.files import file_record, safe_path, verify_record, write_json
from vipe_benchmark.geometry import scale_scene


class AccessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = load()

    def test_exact_protocol_counts_and_order(self):
        c = counts(self.config)
        self.assertEqual((c['annotation_images'], c['reconstruction_rgb'], c['primary_mask_rows']), (232, 690, 6750))
        self.assertEqual((c['gpu_jobs'], c['gpu_seconds'], c['motion_rgb']), (36, 93600, 6600))
        self.assertEqual((c['isolated_matches'], c['combined_matches'], c['max_person_crops']), (1728, 768, 195840))
        self.assertEqual(len(execution_order()), len(set(execution_order())))
        order = execution_order()
        for repeat, source in [('R-S', 'S1-reconstruction'), ('R-D', 'D1-fit'), ('R-G', 'G-S0')]:
            self.assertEqual(order.index(repeat), order.index(source) + 1)
        self.assertEqual(sum(r['seconds'] for r in jobs(self.config).values() if r['resource'] == 'gpu'), 93600)

    def test_pair_contexts_are_distinct_without_weakening_historical_guard(self):
        from basketball_study import training_key
        a, b = Identity('reconstruction', 1, 21, 20), Identity('reconstruction', 1, 21, 21)
        self.assertNotEqual(a.key(), b.key())
        self.assertEqual(guard(a, self.config), 'reconstruction')
        with self.assertRaises(ValueError):
            training_key(1, 21)

    def test_heldout_final_window_wrong_branch_and_pair_rejected(self):
        for case in SUBTEST_CASES[f"{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}"]:
            item = Identity(**case)
            with self.subTest(**case), self.assertRaises(ValueError):
                guard(item, self.config)

    def test_motion_context_roles_and_ends(self):
        for frame, expected in [(50, range(50, 59)), (149, range(141, 150)),
                                (150, range(150, 159)), (199, range(191, 200))]:
            identity = Identity('calibration', 1, frame)
            self.assertEqual(motion_context(identity, 'M1', self.config), list(expected))
        self.assertEqual(motion_context(Identity('calibration', 1, 199), 'M0', self.config), [199, 198])
        self.assertEqual(motion_context(Identity('reconstruction', 1, 21, 20), 'M0', self.config), [20, 21])
        self.assertEqual(motion_context(Identity('calibration', 1, 150), 'M2', self.config), [150])

    def test_duplicate_missing_and_wrong_grid(self):
        expected = output_identities(self.config, 'reconstruction')
        rows = [dict(identity=i.record()) for i in expected]
        validate_membership(rows, expected)
        for bad in (rows[:-1], rows + rows[:1]):
            with self.assertRaises(ValueError):
                validate_membership(bad, expected)
        K = np.array([[800., 0, 479.5], [0, 810, 269.5], [0, 0, 1]])
        with self.assertRaises(ValueError):
            validate_grid(dict(K=renderer_K(K), grid='scale'), K, 'reconstruction')

    def test_hash_change_and_exclusive_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            p = Path(temporary) / 'result.json'
            write_json(p, dict(status='incomplete'))
            record = file_record(p)
            verify_record(record)
            with self.assertRaises(FileExistsError):
                write_json(p, dict(status='complete'))
            p.write_text('changed')
            with self.assertRaises(ValueError):
                verify_record(record)

    def test_prohibited_spelling_and_symlink_rejected_without_reading(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'alias').symlink_to(root / 'prompts')
            for p in (root / 'prompts/a', root / 'alias/a'):
                with self.assertRaises(ValueError):
                    safe_path(p)


class ArrayTests(unittest.TestCase):
    def test_static_polarity_semantics_invalid_and_capacity(self):
        valid = np.ones((3, 4), bool)
        valid[0, 0] = False
        labels = np.zeros(valid.shape, np.int32)
        labels[0, 0], labels[1, 1] = -1, 1
        meta = {'1': dict(class_='person', native_class='person', score=.9)}
        meta['1']['class'] = meta['1'].pop('class_')
        changing = np.zeros_like(valid)
        changing[2, 2] = True
        mask = static_mask(labels, meta, changing, valid, valid.shape)
        self.assertEqual(mask[0, 1], 255)
        self.assertEqual(int(mask[~valid].sum() + mask[1, 1] + mask[2, 2]), 0)
        with self.assertRaises(ValueError):
            instances(labels, {}, valid, valid.shape)
        labels[1, 1] = 256
        with self.assertRaises(ValueError):
            instances(labels, {'256': meta['1']}, valid, valid.shape)

    def test_overlap_greatest_logit_then_score_then_index(self):
        logits = np.array([[[2., 1., -1.]], [[2., 2., -2.]]], np.float32)
        detections = [dict(id=1, index=0, score=.8, native_class='person', **{'class': 'person'}),
                      dict(id=2, index=1, score=.9, native_class='sports ball', **{'class': 'basketball'})]
        labels, meta, overlap = merge_logits(logits, detections, np.ones((1, 3), bool))
        np.testing.assert_array_equal(labels, [[2, 2, 0]])
        self.assertEqual(overlap[0]['pixels'], 2)
        detections[1]['score'] = .8
        labels, _, _ = merge_logits(logits, detections, np.ones((1, 3), bool))
        np.testing.assert_array_equal(labels, [[1, 2, 0]])

    def test_invalid_depth_nan_contract(self):
        z = np.ones((2, 3), np.float32)
        footprint = np.ones(z.shape, bool)
        valid = footprint.copy()
        valid[0, 0] = False
        with self.assertRaises(ValueError):
            depth(z, valid, footprint, shape=z.shape)
        z[0, 0] = np.nan
        depth(z, valid, footprint, shape=z.shape)

    def test_sparse_cv_quantized_support_including_borders(self):
        import cv2
        z = np.arange(1, 10, dtype=np.float32).reshape(3, 3)
        valid = np.ones_like(z, bool)
        uv = np.array([[0, 0], [.5, .5], [1.25, 1.5], [2, 2], [2.25, 2]])
        sampled, good = sample_depth(z, valid, uv)
        np.testing.assert_allclose(sampled[:4], [1., 3., 6.75, 9.])
        self.assertFalse(good[-1])
        # A truly zero-weight invalid neighbor must not invalidate exact centers.
        valid[0, 1] = False
        sampled, good = sample_depth(z, valid, np.array([[0., 0.], [.001, 0.], [.5, 0.], [-.25, 0.]]))
        self.assertTrue(good[0])
        self.assertFalse(good[2])
        self.assertFalse(good[3])
        # The exact native kernel decides whether .001 is rounded to a zero
        # weight; IPP and the generic OpenCV table can differ here.
        native_weight = cv2.remap((~valid).astype(np.float32), np.array([[.001]], np.float32),
                                  np.array([[0]], np.float32), cv2.INTER_LINEAR)[0, 0]
        self.assertEqual(bool(good[1]), bool(native_weight == 0))
        uv = np.array([[.37, .61], [1.1, 1.3]])
        expected = cv2.remap(z, uv[:, :1].astype(np.float32), uv[:, 1:].astype(np.float32), cv2.INTER_LINEAR).ravel()
        actual, _ = sample_depth(z, np.ones_like(valid), uv)
        np.testing.assert_array_equal(actual, expected)

    def test_nonuniform_crop_pad_and_half_pixel_analytic(self):
        K = np.array([[700., 0, 317.25], [0, 900., 189.75], [0, 0, 1.]])
        points = np.array([[1., 2., 5.], [-1., .3, 4.], [.2, -.1, 1.]])
        before = points @ K.T
        uv = before[:, :2] / before[:, 2:3]
        changed, A = transform_K(K, (.7, 1.3), (13, 7), (9, 11))
        q = points @ changed.T
        expected = (uv + .5) * [.7, 1.3] - .5 - [13, 7] + [9, 11]
        np.testing.assert_allclose(q[:, :2] / q[:, 2:3], expected, atol=1e-6, rtol=0)
        restored = np.column_stack((expected, np.ones(len(expected)))) @ np.linalg.inv(A).T
        np.testing.assert_allclose(restored[:, :2], uv, atol=1e-6, rtol=0)
        np.testing.assert_allclose(renderer_K(K)[:2, 2], K[:2, 2] + .5, atol=0, rtol=0)

    def test_radial_remap_against_independent_formula(self):
        import cv2
        K = np.array([[820., 0., 479.5], [0., 820., 269.5], [0, 0, 1.]])
        target = K.copy()
        target[:2, 2] += .5
        k = -.12
        mx, my = cv2.initUndistortRectifyMap(K, np.array([k, 0, 0, 0]), None, target, (960, 540), cv2.CV_32FC1)
        xy = np.array([[30, 27], [400, 200], [900, 500]])
        rays = np.column_stack((xy, np.ones(3))) @ np.linalg.inv(target).T
        radial = 1 + k * (rays[:, :2] ** 2).sum(1)
        expected = rays[:, :2] * radial[:, None] * [820, 820] + K[:2, 2]
        np.testing.assert_allclose(np.column_stack((mx[xy[:, 1], xy[:, 0]], my[xy[:, 1], xy[:, 0]])), expected, atol=1e-3, rtol=0)

    def test_camera_z_range_and_exactly_one_metric_conversion(self):
        K = np.array([[2., 0., 1], [0., 3., 1], [0, 0, 1.]])
        y, x = np.indices((3, 4))
        distance = 5 * np.sqrt(((x - 1) / 2) ** 2 + ((y - 1) / 3) ** 2 + 1)
        np.testing.assert_allclose(ray_range_to_z(distance, K), 5., atol=1e-6, rtol=0)
        processed_K = np.diag([600., 900., 1.])
        for method, expected in [('D2', 5.), ('D3', 1.2)]:
            result, _, record = metric_depth(np.ones((2, 2)) * 2, method, processed_K=processed_K)
            np.testing.assert_allclose(result, expected)
            self.assertEqual(record['focal_conversion_count'], 1)
            with self.assertRaises(ValueError):
                metric_depth(result, method, processed_K=processed_K, already_metric=True)

    def test_scaled_camera_projection_and_normalization(self):
        xyz = np.array([[1., 2, 5], [-2, -1, 3]])
        camera = dict(R=np.eye(3).tolist(), t=[-.5, 0, 0], center=[.5, 0, 0], K=np.eye(3).tolist())
        normalization = np.eye(4)
        normalization[:3, :3] *= .3
        normalization[:3, 3] = [1, 2, 3]
        scaled, cameras, transform, _ = scale_scene(xyz, {1: camera}, normalization, 2, 6)
        before, after = xyz + camera['t'], scaled + cameras[1]['t']
        np.testing.assert_allclose(before[:, :2] / before[:, 2:], after[:, :2] / after[:, 2:], atol=1e-6)
        np.testing.assert_allclose(xyz @ normalization[:3, :3].T + normalization[:3, 3],
                                   scaled @ transform[:3, :3].T + transform[:3, 3], atol=1e-10)





# Literal ordered callback contract consumed without importing this module.
SUBTEST_CASES = {
    'test_vipe_benchmark_contracts.AccessTests.test_heldout_final_window_wrong_branch_and_pair_rejected': [
        {'branch': 'reconstruction', 'camera': 0, 'frame': 0, 'pair_start': 0},
        {'branch': 'calibration', 'camera': 1, 'frame': 200, 'pair_start': None},
        {'branch': 'depth', 'camera': 0, 'frame': 100, 'pair_start': None},
        {'branch': 'depth', 'camera': 1, 'frame': 176, 'pair_start': None},
        {'branch': 'reconstruction', 'camera': 1, 'frame': 21, 'pair_start': None},
        {'branch': 'reconstruction', 'camera': 1, 'frame': 22, 'pair_start': 20},
        {'branch': 'calibration', 'camera': 1, 'frame': 21, 'pair_start': None},
        {'branch': 'calibration', 'camera': True, 'frame': 100, 'pair_start': None},
    ],
}


if __name__ == '__main__':
    unittest.main()
