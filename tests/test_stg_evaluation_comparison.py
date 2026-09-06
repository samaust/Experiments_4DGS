import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


class EvaluationComparisonTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('compare_evaluations',
            Path(__file__).resolve().parents[1]/'scripts/compare-stg-evaluations.py')
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.a, self.b = [Path(self.temp.name)/n for n in ('a', 'b')]
        for directory, model, psnr in [(self.a, 'lite', 20), (self.b, 'full', 22)]:
            (directory/'reload-a').mkdir(parents=True)
            metrics = dict(psnr=psnr, ssim=.8, lpips_alex=.3)
            report = dict(status='completed', model=model, iteration=5000,
                checkpoint_sha256=model+'-hash', manifest_sha256='manifest-hash',
                incomplete_training=True, checkpoint_bytes=100, benchmark=None, metrics=metrics)
            self.write(directory/'evaluation.json', report)
            self.write(directory/'metrics.json', dict(protocol={'ssim': 'shared'}, count=1,
                aggregate=metrics, per_frame=[dict(frame='004120', **metrics)]))
            self.write(directory/'reload-a/render.json', dict(**report,
                frames=[dict(camera='0015', frame_id=4120, normalized_time=.1)], sweep={'poses': 20}))

    def write(self, path, value):
        path.write_text(json.dumps(value))

    def change(self, path, key, value):
        data = json.loads(path.read_text())
        data[key] = value
        self.write(path, data)

    def test_valid_deltas_and_incomplete_label(self):
        report = self.module.compare(self.a, self.b)
        self.assertEqual(report['delta_second_minus_first']['psnr'], 2)
        self.assertTrue(report['first']['incomplete_training'])
        self.assertTrue(report['equal_iterations'])
        self.assertEqual(report['per_frame'][0]['delta_second_minus_first']['psnr'], 2)

    def test_incompatible_protocol_rejected(self):
        self.change(self.b/'metrics.json', 'protocol', {'ssim': 'different'})
        with self.assertRaisesRegex(ValueError, 'protocol'):
            self.module.compare(self.a, self.b)

    def test_changed_manifest_rejected(self):
        for path in [self.b/'evaluation.json', self.b/'reload-a/render.json']:
            self.change(path, 'manifest_sha256', 'other')
        with self.assertRaisesRegex(ValueError, 'manifests'):
            self.module.compare(self.a, self.b)

    def test_missing_frame_and_duplicate_rejected(self):
        path = self.b/'metrics.json'
        data = json.loads(path.read_text())
        original = data['per_frame'][0]
        for rows in ([], [original, original]):
            data['per_frame'] = rows
            self.write(path, data)
            with self.assertRaisesRegex(ValueError, 'frames'):
                self.module.compare(self.a, self.b)

    def test_metadata_mismatch_rejected(self):
        self.change(self.b/'evaluation.json', 'iteration', 2000)
        with self.assertRaisesRegex(ValueError, 'metadata mismatch'):
            self.module.compare(self.a, self.b)

    def test_unequal_iterations_are_labeled(self):
        for path in (self.b/'evaluation.json', self.b/'reload-a/render.json'):
            self.change(path, 'iteration', 2000)
        self.assertFalse(self.module.compare(self.a, self.b)['equal_iterations'])

    def test_duplicate_render_frames_rejected(self):
        path = self.b/'reload-a/render.json'
        data = json.loads(path.read_text())
        data['frames'] *= 2
        self.write(path, data)
        with self.assertRaisesRegex(ValueError, 'duplicates'):
            self.module.compare(self.a, self.b)

    def test_time_mismatch_rejected(self):
        path = self.b/'reload-a/render.json'
        data = json.loads(path.read_text())
        data['frames'][0]['normalized_time'] = .2
        self.write(path, data)
        with self.assertRaisesRegex(ValueError, 'camera/time'):
            self.module.compare(self.a, self.b)

    def test_infinite_psnr_delta_is_explicit_null(self):
        a = dict(psnr='Infinity', ssim=1, lpips_alex=0)
        self.assertIsNone(self.module.difference(a, a)['psnr'])

    def test_atgs_bundle_comparison_and_runtime_mismatch(self):
        self.check_bundle_comparison('atgs')

    def test_freetimegs_bundle_comparison_and_runtime_mismatch(self):
        self.check_bundle_comparison('freetimegs')

    def check_bundle_comparison(self, model):
        for path in (self.b/'evaluation.json', self.b/'reload-a/render.json'):
            report = json.loads(path.read_text())
            report.pop('checkpoint_sha256')
            report.update(model=model, bundle={'schema': model+'-bundle/v1'}, runtime={'extensions': {}})
            self.write(path, report)
        result = self.module.compare(self.a, self.b)
        self.assertEqual(result['second']['model'], model)
        self.assertIsNone(result['second']['checkpoint_sha256'])
        self.assertEqual(result['delta_second_minus_first']['psnr'], 2)
        self.change(self.b/'evaluation.json', 'runtime', {'changed': True})
        with self.assertRaisesRegex(ValueError, 'runtime'):
            self.module.compare(self.a, self.b)
