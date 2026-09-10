import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from basketball_dense_crossing_audit import (ADJACENT, CAMERAS, EXPECTED, GAP,
    checked_json, digest, validate_metrics, window_summary)


def row(camera, frame):
    return dict(camera=camera, frame_id=frame, normalized_time=frame/50,
        split='heldout-camera' if camera in CAMERAS else 'temporal-interpolation',
        full=dict(psnr=30.), dynamic=dict(psnr=25., lpips_alex=.1),
        motion_pixels=dict(mae=.3 if frame in GAP else .1))


class CrossingAuditTests(unittest.TestCase):
    def setUp(self):
        self.record = dict(seed=0, iteration=50000, render_sha256='frozen')
        self.metrics = dict(complete=True, **self.record,
                            frames=[row(c, f) for c, f in sorted(EXPECTED)])

    def test_frozen_split_and_unique_coverage(self):
        self.assertEqual(len(validate_metrics(self.record, self.metrics)), 350)
        duplicate = copy.deepcopy(self.metrics)
        duplicate['frames'][-1] = duplicate['frames'][0]
        with self.assertRaisesRegex(ValueError, 'coverage'):
            validate_metrics(self.record, duplicate)

    def test_rejects_misaligned_seed_time_and_source(self):
        for field, replacement in (('seed', 2), ('iteration', 5000), ('render_sha256', 'different')):
            metrics = copy.deepcopy(self.metrics)
            metrics[field] = replacement
            with self.assertRaisesRegex(ValueError, 'provenance'):
                validate_metrics(self.record, metrics)
        metrics = copy.deepcopy(self.metrics)
        metrics['frames'][0]['normalized_time'] += .02
        with self.assertRaisesRegex(ValueError, 'split/time'):
            validate_metrics(self.record, metrics)

    def test_window_uses_only_declared_frames(self):
        rows = [row('0', f) for f in range(50)]
        rows[0]['motion_pixels']['mae'] = .9
        summary = window_summary(rows)
        self.assertAlmostEqual(summary['motion_pixels/mae']['gap'], .3)
        self.assertAlmostEqual(summary['motion_pixels/mae']['adjacent'], .1)
        self.assertAlmostEqual(summary['motion_pixels/mae']['gap_over_adjacent'], 3.)
        self.assertEqual(summary['motion_mae_peak_frames'], [0])
        self.assertTrue(set(ADJACENT).isdisjoint(GAP))
        with self.assertRaisesRegex(ValueError, 'fifty frames'):
            window_summary(rows[1:])

    def test_corrupted_source_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'metrics.json'
            path.write_text(json.dumps({'test': True}))
            sha = digest(path)
            self.assertTrue(checked_json(path, sha, {})['test'])
            path.write_text(json.dumps({'test': False}))
            with self.assertRaisesRegex(ValueError, 'changed source'):
                checked_json(path, sha, {})


if __name__ == '__main__':
    unittest.main()
