"""Plan 069 depth extension through its worker and package boundary."""
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.access import Identity
from vipe_benchmark.config import ROOT, load, training_cameras
from vipe_benchmark.files import file_record, read_json, write_json
from vipe_benchmark.ledger import Ledger
from vipe_benchmark.dav2_metric import DAV2MetricSmallAdapter
from vipe_benchmark.moge_metric import (MoGe2Adapter, MoGe3Adapter,
    MetricAnythingPointMapAdapter, POINTMAP_PIN)
from vipe_benchmark.marigold_relative import MarigoldLogStage2Adapter, PROFILE
from vipe_benchmark.stages import run as run_worker


def run(request, output, config, *, backend, ledger):
    return run_worker(request, output, config, depth_backend=backend, depth_ledger=ledger)


class KnownPlane:
    def predict(self, rgb, K, image_valid):
        depth = np.full(image_valid.shape, 6., np.float32)
        depth[~image_valid] = np.nan
        return SimpleNamespace(domain='camera_z_metres', values=depth,
            valid=image_valid.copy(), raw_values=depth.copy(),
            metadata={'native_depth_type': 'camera-z metres'})


class RelativeInverse:
    def predict(self, rgb, K, image_valid):
        profile = np.linspace(.2, .8, image_valid.shape[1], dtype=np.float32)
        values = np.broadcast_to(profile, image_valid.shape).copy()
        values[~image_valid] = np.nan
        return SimpleNamespace(domain='relative_inverse', values=values,
            valid=image_valid.copy(), raw_values=values.copy(),
            metadata={'native_depth_type': 'relative inverse depth'})


class ConstantRelative(RelativeInverse):
    def predict(self, rgb, K, image_valid):
        result = super().predict(rgb, K, image_valid)
        result.values[image_valid] = .5
        return result


class ZeroRelative(RelativeInverse):
    def predict(self, rgb, K, image_valid):
        result = super().predict(rgb, K, image_valid)
        result.values[image_valid] = 0
        return result


class NoValidPixels(KnownPlane):
    def predict(self, rgb, K, image_valid):
        result = super().predict(rgb, K, image_valid)
        result.valid[:] = False
        result.values[:] = np.nan
        return result


class WrongDomain:
    def predict(self, rgb, K, image_valid):
        return KnownPlane().predict(rgb, K, image_valid)


class NativeMoGeFixture:
    def infer(self, image, **options):
        import torch
        height, width = image.shape[-2:]
        points = torch.zeros((height, width, 3), dtype=torch.float32)
        points[..., 0] = 2
        points[..., 2] = 6
        return dict(points=points, depth=points[..., 2].clone(),
                    mask=torch.ones((height, width), dtype=torch.bool))


class NativeMoGe3Fixture(NativeMoGeFixture):
    def infer(self, image, **options):
        import torch
        output = super().infer(image, **options)
        output['intrinsics'] = torch.tensor([[800 / 960, 0, .5],
            [0, 800 / 540, .5], [0, 0, 1]], dtype=torch.float32)
        return output


class NativeDAV2Fixture:
    encoder = 'vits'
    max_depth = 20.
    training = False

    def infer_image(self, bgr, input_size=518):
        return np.full(bgr.shape[:2], 6., np.float32)


class NativeMarigoldFixture:
    profile = PROFILE
    training = False

    def __init__(self):
        self.calls = []

    def infer_image(self, rgb, *, seed):
        self.calls.append((rgb.shape, seed))
        return np.broadcast_to(np.linspace(-.8, .6, rgb.shape[1], dtype=np.float32),
                               rgb.shape[:2]).copy()


class OneFailedCamera:
    def __init__(self):
        self.calls = 0

    def predict(self, rgb, K, image_valid):
        self.calls += 1
        result = KnownPlane().predict(rgb, K, image_valid)
        if self.calls == 2:
            result.valid[:] = False
            result.values[:] = np.nan
        return result


class DepthExtensionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.config = load()
        self.K = np.array([[800., 0., 480.], [0., 800., 270.], [0., 0., 1.]])
        Image.new('RGB', (960, 540), (80, 90, 100)).save(self.root / 'rgb.png')
        valid = np.ones((540, 960), bool)
        np.save(self.root / 'valid.npy', valid)
        y, x = np.meshgrid(np.linspace(20, 520, 10), np.linspace(10, 940, 12), indexing='ij')
        uv = np.column_stack((x.ravel(), y.ravel()))
        np.savez(self.root / 'samples.npz', point_ids=np.arange(len(uv)), xyz=np.zeros((len(uv), 3)),
            uv=uv, K=self.K, camera_z=np.full(len(uv), 2.), valid=valid.astype(np.uint8))
        rgb = file_record(self.root / 'rgb.png')
        footprint = file_record(self.root / 'valid.npy')
        samples = file_record(self.root / 'samples.npz')
        rows = [dict(identity=Identity('depth', camera, frame).record(), rgb=rgb,
            valid=footprint, samples=samples, K=self.K.tolist(), grid='accepted-scale-grid')
            for frame in (100, 175) for camera in training_cameras(self.config)]
        write_json(self.root / 'inputs.json', dict(schema='vipe-benchmark-inputs/v1', depth=rows))
        self.ledger = Ledger(self.root / 'ledger.jsonl', self.config)
        self.request = dict(schema='plan069-depth-extension-request/v1', record_kind='fixture',
            id='D5-fit-fixture-001', component='D5', role='fit',
            inputs=file_record(self.root / 'inputs.json'),
            configuration=file_record(ROOT / 'configs/vipe-alternatives/benchmark-v1.json'),
            extension_configuration=file_record(ROOT / 'configs/vipe-alternatives/depth-extension-v1.json'),
            max_seconds=60)

    def tearDown(self):
        self.temporary.cleanup()

    def test_metric_fit_is_scale_bound_and_reviewable(self):
        receipt = run(self.request, self.root / 'D5-fit-fixture-001', self.config,
            backend=KnownPlane(), ledger=self.ledger)
        self.assertEqual(receipt['status'], 'complete')
        worker = read_json(receipt['worker']['path'])
        self.assertEqual(worker['schema'], 'plan069-depth-extension-result/v1')
        self.assertEqual(len(worker['rows']), 30)
        self.assertEqual(worker['eligibility'], dict(commercial='unverified',
            runtime='fixture-only', metric_scale='passed', downstream='blocked'))
        self.assertEqual(worker['rows'][0]['context'], dict(
            camera=1, role='fit', source_frames=[100], input_manifest=self.request['inputs']))
        scale = read_json(worker['scale']['path'])
        self.assertEqual(scale['status'], 'passed')
        self.assertAlmostEqual(scale['scale'], 3.)
        self.assertEqual(scale['provenance']['inputs'], self.request['inputs'])
        package = read_json(receipt['package']['path'])
        self.assertEqual(package['record_kind'], 'fixture')
        self.assertEqual([c['id'] for c in package['candidates']], ['source-rgb', 'D5'])
        self.assertEqual(package['candidates'][1]['status'], 'available')
        outcome = read_json(package['candidates'][1]['provenance']['ledger_outcome']['path'])
        self.assertEqual(outcome['event'], 'cpu_preparation_charge')
        self.assertEqual(outcome['evidence'], file_record(self.root / self.request['id'] / 'result.json'))
        self.assertIn(outcome, self.ledger.events())

    def test_check_reuses_exact_fit_and_rejects_changed_inputs(self):
        fit = run(self.request, self.root / 'D5-fit-fixture-001', self.config,
            backend=KnownPlane(), ledger=self.ledger)
        fitted = read_json(fit['worker']['path'])['scale']
        check_request = dict(self.request, id='D5-check-fixture-001',
            role='check', frozen_fit=fitted)
        check = run(check_request, self.root / 'D5-check-fixture-001',
            self.config, backend=KnownPlane(), ledger=self.ledger)
        selected = read_json(read_json(check['worker']['path'])['scale']['path'])
        self.assertEqual(selected['status'], 'passed')
        self.assertAlmostEqual(selected['scale'], 3.)
        self.assertEqual(selected['frozen_fit'], fitted)
        write_json(self.root / 'substituted-inputs.json', dict(
            read_json(self.request['inputs']['path']), substituted=True))
        replaced = dict(check_request, inputs=file_record(self.root / 'substituted-inputs.json'))
        with self.assertRaisesRegex(ValueError, 'frozen fit candidate/input'):
            run(replaced, self.root / 'changed' / 'D5-check-fixture-001',
                self.config, backend=KnownPlane(), ledger=Ledger(
                    self.root / 'changed-ledger.jsonl', self.config))

    def test_d5_native_adapter_crosses_worker_scale_and_package_boundary(self):
        receipt = run(self.request, self.root / self.request['id'], self.config,
            backend=MoGe2Adapter(NativeMoGeFixture()), ledger=self.ledger)
        worker = read_json(receipt['worker']['path'])
        self.assertEqual(worker['eligibility']['metric_scale'], 'passed')
        self.assertAlmostEqual(worker['rows'][0]['metadata']['fov_x_degrees'],
            2 * np.degrees(np.arctan(960 / 1600)))
        with np.load(worker['rows'][0]['depth']['path']) as stored:
            self.assertEqual(stored['native_points'].shape, (540, 960, 3))
            self.assertEqual(stored['raw_values'][270, 480], 6.)
            self.assertEqual(stored['depth'][270, 480], 6.)
        package = read_json(receipt['package']['path'])
        self.assertEqual(package['candidates'][1]['status'], 'available')

    def test_d6_three_step_adapter_uses_same_worker_scale_and_package_path(self):
        request = dict(self.request, id='D6-fit-fixture-001', component='D6')
        with self.assertRaisesRegex(ValueError, 'adapter candidate'):
            run(request, self.root / request['id'], self.config,
                backend=MoGe2Adapter(NativeMoGeFixture()), ledger=self.ledger)
        receipt = run(request, self.root / request['id'], self.config,
            backend=MoGe3Adapter(NativeMoGe3Fixture()), ledger=self.ledger)
        worker = read_json(receipt['worker']['path'])
        self.assertEqual(worker['eligibility']['metric_scale'], 'passed')
        self.assertEqual(worker['rows'][0]['metadata']['native_refine_steps'], 3)
        self.assertEqual(read_json(receipt['package']['path'])['candidates'][1]['id'], 'D6')

    def test_d7_native_518_metric_output_reaches_scale_and_package(self):
        request = dict(self.request, id='D7-fit-fixture-001', component='D7')
        receipt = run(request, self.root / request['id'], self.config,
            backend=DAV2MetricSmallAdapter(NativeDAV2Fixture()), ledger=self.ledger)
        worker = read_json(receipt['worker']['path'])
        self.assertEqual(worker['eligibility']['metric_scale'], 'passed')
        self.assertEqual(worker['rows'][0]['metadata']['native_processed_size'], [924, 518])
        self.assertEqual(read_json(receipt['package']['path'])['candidates'][1]['id'], 'D7')

    def test_d8_pointmap_student_reuses_frozen_fit_at_check(self):
        fit_request = dict(self.request, id='D8-fit-fixture-001', component='D8')
        fit = run(fit_request, self.root / fit_request['id'], self.config,
            backend=MetricAnythingPointMapAdapter(NativeMoGe3Fixture(), POINTMAP_PIN),
            ledger=self.ledger)
        fit_scale = read_json(fit['worker']['path'])['scale']
        self.assertEqual(read_json(fit_scale['path'])['status'], 'passed')
        check_request = dict(fit_request, id='D8-check-fixture-001', role='check',
            frozen_fit=fit_scale)
        check = run(check_request, self.root / check_request['id'], self.config,
            backend=MetricAnythingPointMapAdapter(NativeMoGe3Fixture(), POINTMAP_PIN),
            ledger=self.ledger)
        check_worker = read_json(check['worker']['path'])
        self.assertEqual(read_json(check_worker['scale']['path'])['status'], 'passed')
        self.assertEqual(check_worker['rows'][0]['metadata']['checkpoint_identity'], POINTMAP_PIN)
        self.assertEqual(read_json(check['package']['path'])['candidates'][1]['id'], 'D8')

    def test_relative_depth_keeps_its_domain_out_of_metric_scale(self):
        request = dict(self.request, id='D9-fit-fixture-001', component='D9')
        receipt = run(request, self.root / request['id'], self.config,
            backend=RelativeInverse(), ledger=self.ledger)
        worker = read_json(receipt['worker']['path'])
        self.assertEqual(worker['scale_status'], 'not_metric')
        self.assertNotIn('scale', worker)
        self.assertEqual(worker['eligibility']['metric_scale'], 'not_applicable')
        with np.load(worker['rows'][0]['depth']['path']) as stored:
            self.assertIn('relative', stored.files)
            self.assertNotIn('depth', stored.files)
        package = read_json(receipt['package']['path'])
        self.assertEqual(package['settings']['depth_display']['domain'], 'relative_inverse')
        self.assertEqual(package['settings']['depth_display']['direction'], 'larger means nearer')

    def test_d11_pinned_log_adapter_crosses_worker_and_review_boundary(self):
        request = dict(self.request, id='D11-fit-fixture-001', component='D11')
        native = NativeMarigoldFixture()
        receipt = run(request, self.root / request['id'], self.config,
            backend=MarigoldLogStage2Adapter(native), ledger=self.ledger)
        worker = read_json(receipt['worker']['path'])
        self.assertEqual(len(native.calls), 30)
        self.assertTrue(all(shape == (540, 960, 3) and seed == 2025
                            for shape, seed in native.calls))
        self.assertEqual(worker['scale_status'], 'not_metric')
        self.assertEqual(worker['eligibility']['downstream'], 'blocked')
        self.assertEqual(worker['rows'][0]['metadata']['profile'], PROFILE)
        with np.load(worker['rows'][0]['depth']['path']) as stored:
            self.assertIn('relative', stored.files)
            self.assertNotIn('depth', stored.files)
            self.assertAlmostEqual(float(stored['raw_values'][0, 0]), -.8)
            self.assertEqual(stored['relative'].shape, (540, 960))
        package = read_json(receipt['package']['path'])
        self.assertEqual(package['settings']['depth_display']['domain'], 'relative_log')
        self.assertEqual(package['settings']['depth_display']['direction'], 'larger means farther')
        self.assertEqual(package['candidates'][1]['id'], 'D11')

    def test_d11_rejects_unapproved_runtime_substitution(self):
        native = NativeMarigoldFixture()
        native.profile = dict(PROFILE, transformer_quantization='8bit')
        with self.assertRaisesRegex(ValueError, 'pinned Log-stage2'):
            MarigoldLogStage2Adapter(native)
        native.profile = PROFILE
        native.infer_image = lambda rgb, seed: np.ones((270, 480), np.float32)
        with self.assertRaisesRegex(ValueError, 'accepted grid'):
            MarigoldLogStage2Adapter(native).predict(
                np.zeros((540, 960, 3), np.uint8), self.K,
                np.ones((540, 960), np.bool_))

    def test_constant_relative_map_has_a_neutral_labeled_display(self):
        request = dict(self.request, id='D9-fit-fixture-001', component='D9')
        receipt = run(request, self.root / request['id'], self.config,
            backend=ConstantRelative(), ledger=self.ledger)
        package = read_json(receipt['package']['path'])
        self.assertEqual(package['settings']['depth_display']['raw_range'], [.5, .5])
        self.assertEqual(package['settings']['depth_display']['constant_value'], .5)

    def test_native_relu_zero_remains_valid_relative_output(self):
        request = dict(self.request, id='D9-fit-fixture-001', component='D9')
        receipt = run(request, self.root / request['id'], self.config,
            backend=ZeroRelative(), ledger=self.ledger)
        worker = read_json(receipt['worker']['path'])
        self.assertEqual(worker['scale_status'], 'not_metric')
        self.assertEqual(read_json(receipt['package']['path'])['settings']
                         ['depth_display']['constant_value'], 0)

    def test_d10_anchor_only_worker_cannot_bypass_video_context(self):
        request = dict(self.request, id='D10-fit-fixture-001', component='D10')
        with self.assertRaisesRegex(ValueError, 'offline sequence path'):
            run(request, self.root / request['id'], self.config,
                backend=KnownPlane(), ledger=self.ledger)

    def test_wrong_domain_preserves_failure_and_cpu_charge(self):
        request = dict(self.request, id='D9-fit-fixture-001', component='D9')
        with self.assertRaisesRegex(ValueError, 'domain'):
            run(request, self.root / request['id'], self.config,
                backend=WrongDomain(), ledger=self.ledger)
        failure = read_json(self.root / request['id'] / 'failure.json')
        self.assertEqual(failure['status'], 'failed')
        charged = [event for event in self.ledger.events()
            if event['event'] == 'cpu_preparation_charge']
        self.assertEqual(len(charged), 1)
        self.assertEqual(charged[0]['evidence'], file_record(self.root / request['id'] / 'failure.json'))

    def test_blocked_fit_requires_its_own_bound_qualitative_scope(self):
        write_json(self.root / 'foreign-fit.json', dict(status='blocked', role='fit',
            component='D5', provenance=dict(inputs=dict(path='other', sha256='foreign', bytes=1))))
        write_json(self.root / 'qualitative-admission.json',
            dict(schema='plan069-depth-qualitative-admission/v1', record_kind='fixture',
                 component='D5', inputs=self.request['inputs'],
                 purpose='qualitative-only', status='admitted'))
        check = dict(self.request, id='D5-check-fixture-001', role='check',
            frozen_fit=file_record(self.root / 'foreign-fit.json'),
            qualitative_admission=file_record(self.root / 'qualitative-admission.json'))
        with self.assertRaisesRegex(ValueError, 'frozen fit candidate/input'):
            run(check, self.root / check['id'], self.config,
                backend=KnownPlane(), ledger=self.ledger)

    def test_failed_camera_stays_visible_during_qualitative_only_check(self):
        fitted = run(self.request, self.root / self.request['id'], self.config,
            backend=OneFailedCamera(), ledger=self.ledger)
        failed_fit = read_json(read_json(fitted['worker']['path'])['scale']['path'])
        self.assertEqual(failed_fit['status'], 'blocked')
        self.assertEqual(len(failed_fit['cameras']), 30)
        self.assertEqual(failed_fit['cameras'][1]['points'], 0)
        write_json(self.root / 'qualitative-admission.json',
            dict(schema='plan069-depth-qualitative-admission/v1', record_kind='fixture',
                 component='D5', inputs=self.request['inputs'],
                 purpose='qualitative-only', status='admitted'))
        check = dict(self.request, id='D5-check-fixture-001', role='check',
            frozen_fit=read_json(fitted['worker']['path'])['scale'],
            qualitative_admission=file_record(self.root / 'qualitative-admission.json'))
        receipt = run(check, self.root / check['id'], self.config,
            backend=KnownPlane(), ledger=self.ledger)
        selected = read_json(read_json(receipt['worker']['path'])['scale']['path'])
        self.assertEqual(selected['status'], 'blocked')
        self.assertIsNone(selected['scale'])
        self.assertEqual(selected['fit_cameras'], failed_fit['cameras'])
        self.assertEqual(selected['cameras'][1]['points'], 120)
        package = read_json(receipt['package']['path'])
        self.assertEqual(package['candidates'][1]['status'], 'available')

    def test_qualitative_check_with_no_valid_map_is_unavailable(self):
        fitted = run(self.request, self.root / self.request['id'], self.config,
            backend=NoValidPixels(), ledger=self.ledger)
        write_json(self.root / 'qualitative-admission.json',
            dict(schema='plan069-depth-qualitative-admission/v1', record_kind='fixture',
                 component='D5', inputs=self.request['inputs'],
                 purpose='qualitative-only', status='admitted'))
        check = dict(self.request, id='D5-check-fixture-001', role='check',
            frozen_fit=read_json(fitted['worker']['path'])['scale'],
            qualitative_admission=file_record(self.root / 'qualitative-admission.json'))
        receipt = run(check, self.root / check['id'], self.config,
            backend=NoValidPixels(), ledger=self.ledger)
        package = read_json(receipt['package']['path'])
        self.assertEqual(package['candidates'][1]['status'], 'unavailable')
        self.assertEqual(package['candidates'][1]['media'], [])

    def test_reused_identity_is_rejected_by_ledger_even_in_a_new_directory(self):
        run(self.request, self.root / self.request['id'], self.config,
            backend=KnownPlane(), ledger=self.ledger)
        with self.assertRaisesRegex(ValueError, 'already consumed'):
            run(self.request, self.root / 'another' / self.request['id'], self.config,
                backend=KnownPlane(), ledger=self.ledger)


if __name__ == '__main__':
    unittest.main()
