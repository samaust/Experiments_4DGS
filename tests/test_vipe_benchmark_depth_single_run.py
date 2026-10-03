"""Single-image map workload and failed-fit inference boundary on CPU."""
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.config import load, training_cameras
from vipe_benchmark.files import file_record, read_json, write_json
from vipe_benchmark.depth_single_run import run_maps, validate_result


class Plane:
    component = 'D5'

    def __init__(self, fail_fit=False):
        self.calls = 0
        self.fail_fit = fail_fit

    def predict(self, rgb, K, image_valid):
        self.calls += 1
        valid = image_valid.copy()
        if self.fail_fit and self.calls <= 30:
            valid[:] = False
        depth = np.full(valid.shape, 6., np.float32)
        depth[~valid] = np.nan
        points = np.repeat(depth[..., None], 3, axis=-1)
        return SimpleNamespace(domain='camera_z_metres', values=depth,
            valid=valid, raw_values=depth.copy(), native_points=points,
            metadata=dict(native_depth_type='camera-z metres', conversion_count=0))


class SingleMapsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cameras = training_cameras(load())
        self.K = [[800., 0., 480.], [0., 800., 270.], [0., 0., 1.]]
        self.valid = np.ones((540, 960), bool)
        np.save(self.root / 'valid.npy', self.valid)
        Image.new('RGB', (960, 540), (20, 30, 40)).save(self.root / 'rgb.png')
        self.rgb = file_record(self.root / 'rgb.png')
        Image.new('RGB', (960, 540), (21, 30, 40)).save(self.root / 'decoded.png')
        decoded = file_record(self.root / 'decoded.png')
        (self.root / 'video.bin').write_bytes(b'accepted source video')
        video = file_record(self.root / 'video.bin')
        np.save(self.root / 'context-valid.npy', self.valid)
        valid = file_record(self.root / 'valid.npy')
        y, x = np.meshgrid(np.linspace(20, 520, 10), np.linspace(10, 940, 12), indexing='ij')
        uv = np.column_stack((x.ravel(), y.ravel()))
        np.savez(self.root / 'samples.npz', uv=uv, K=self.K,
                 camera_z=np.full(len(uv), 2.), valid=self.valid.astype(np.uint8))
        samples = file_record(self.root / 'samples.npz')
        depth_rows = [dict(identity=dict(branch='depth', camera=c, frame=f),
            rgb=self.rgb, valid=valid, samples=samples, K=self.K,
            grid='scale-opencv-integer') for c in self.cameras for f in (100, 175)]
        write_json(self.root / 'inputs.json', dict(schema='vipe-benchmark-inputs/v1',
                   status='prepared', depth=depth_rows, rgb=[dict(
                       identity=dict(branch='calibration', camera=c, frame=f),
                       rgb=decoded, source_video=video) for c in self.cameras for f in range(50, 200)]))
        self.inputs = file_record(self.root / 'inputs.json')
        self.context_rows = [dict(camera=c, frame=f, role='fit' if f < 150 else 'check',
            timestamp=f / 25, source_rgb=self.rgb if f in (100, 175) else decoded,
            source_rgb_grid='scale-opencv-integer' if f in (100, 175) else 'distorted-opencv-integer',
            decoded_source_rgb=decoded, source_video=video, accepted_anchor=f in (100, 175), K=self.K, valid=file_record(self.root / 'context-valid.npy'),
            grid='scale-opencv-integer') for c in self.cameras for f in range(50, 200)]
        anchors = [dict(camera=c, frame=f, source_rgb=decoded,
            accepted_rgb=self.rgb, decoded_remapped_sha256='different-from-accepted',
            decoded_drift=dict(matches_accepted_bytes=False))
            for c in self.cameras for f in (100, 175)]
        write_json(self.root / 'context.json', dict(schema='plan069-depth-context/v1',
            inputs=self.inputs, rows=self.context_rows, anchors=anchors))
        self.request = dict(schema='plan069-depth-single-maps-request/v1',
            record_kind='fixture', candidate='D5', job_id='plan069-D5-maps-fixture-001',
            inputs=self.inputs, context=file_record(self.root / 'context.json'))

    def test_failed_fit_stops_before_any_check_inference_without_admission(self):
        backend = Plane(fail_fit=True)
        with patch('vipe_benchmark.depth_single_run.materialize_role', self.materialize), self.assertRaisesRegex(ValueError, 'qualitative-only admission'):
            run_maps(self.request, self.root / self.request['job_id'], backend=backend)
        self.assertEqual(backend.calls, 30)
        fit = read_json(self.root / self.request['job_id'] / 'scale-fit.json')
        self.assertEqual(fit['status'], 'blocked')
        self.assertFalse((self.root / self.request['job_id'] / 'scale-check.json').exists())

    def materialize(self, context_record, camera, role):
        rows = [r for r in self.context_rows if r['camera'] == camera and r['role'] == role]
        frames = np.broadcast_to(np.zeros((540, 960, 3), np.uint8), (50, 540, 960, 3))
        return frames, self.valid, rows

    def test_all_candidates_publish_exact_workload_and_freeze_fit(self):
        for candidate in ('D5', 'D6', 'D8'):
            with self.subTest(candidate=candidate):
                request = dict(self.request, candidate=candidate,
                               job_id=f'plan069-{candidate}-maps-fixture-001')
                backend = Plane()
                backend.component = candidate
                with patch('vipe_benchmark.depth_single_run.materialize_role', self.materialize):
                    result = run_maps(request, self.root / request['job_id'], backend=backend)
                self.assertEqual(backend.calls, 256)
                validate_result(result, request)
                altered = dict(result, rows=result['rows'][:-1])
                with self.assertRaisesRegex(ValueError, 'result membership'):
                    validate_result(altered, request)
                keys = {(r['camera'], r['frame']) for r in result['rows']}
                expected = {(c, f) for c in self.cameras for f in (100, 175)} | {
                    (c, f) for c in (1, 11, 21, 31) for f in range(150, 200)}
                self.assertEqual(keys, expected)
                self.assertEqual(sum(r['kind'] == 'anchor' for r in result['rows']), 60)
                self.assertEqual(result['engineering_eligibility'], 'passed')
                fit = read_json(result['scales']['fit']['path'])
                check = read_json(result['scales']['check']['path'])
                self.assertAlmostEqual(fit['scale'], 3.)
                self.assertAlmostEqual(check['scale'], 3.)
                self.assertEqual(check['frozen_fit'], result['scales']['fit'])
                with np.load(result['rows'][0]['prediction']['path']) as data:
                    self.assertIn('native_points', data.files)

    def test_admitted_failed_fit_publishes_support_without_refitting(self):
        path = self.root / 'qualitative.json'
        write_json(path, dict(schema='plan069-depth-qualitative-admission/v1',
            record_kind='fixture', component='D5', inputs=self.inputs,
            purpose='qualitative-only', status='admitted'))
        request = dict(self.request, qualitative_admission=file_record(path))
        backend = Plane(fail_fit=True)
        with patch('vipe_benchmark.depth_single_run.materialize_role', self.materialize):
            result = run_maps(request, self.root / request['job_id'], backend=backend)
        self.assertEqual(backend.calls, 256)
        self.assertEqual(result['engineering_eligibility'], 'blocked')
        validate_result(result, request)
        check = read_json(result['scales']['check']['path'])
        self.assertIsNone(check['scale'])
        self.assertEqual(len(check['cameras']), 30)
        self.assertEqual(check['cameras'][0]['sampled_valid_points'], 120)

    def test_unreserved_actual_request_never_loads_native_model(self):
        job = 'plan069-D5-maps-001'
        request = dict(self.request, record_kind='actual', job_id=job,
            ledger_path=str(self.root / 'ledger.jsonl'))
        request_path = self.root / 'request.json'
        write_json(request_path, request)
        with patch('vipe_benchmark.moge_native.load_adapter') as constructor:
            with self.assertRaisesRegex(ValueError, 'active exact single-image GPU reservation'):
                run_maps(request, self.root / 'jobs' / job, request_path=request_path)
            constructor.assert_not_called()
        self.assertFalse((self.root / 'jobs' / job).exists())

    def test_substituted_context_frame_is_rejected_before_native_loading(self):
        context = read_json(self.request['context']['path'])
        next(row for row in context['rows'] if row['camera'] == 1 and row['frame'] == 150)[
            'source_rgb'] = self.rgb
        altered = self.root / 'altered-context.json'
        write_json(altered, context)
        request = dict(self.request, record_kind='actual', job_id='plan069-D5-maps-001',
                       context=file_record(altered))
        with patch('vipe_benchmark.moge_native.load_adapter') as constructor:
            with self.assertRaisesRegex(ValueError, 'RGB source lineage changed'):
                run_maps(request, self.root / request['job_id'])
            constructor.assert_not_called()
        self.assertFalse((self.root / request['job_id']).exists())

    def test_substituted_nonclip_anchor_provenance_is_rejected_before_loading(self):
        context = read_json(self.request['context']['path'])
        row = next(r for r in context['rows'] if r['camera'] == 2 and r['frame'] == 100)
        row['source_rgb'] = row['decoded_source_rgb']
        altered = self.root / 'altered-anchor-context.json'
        write_json(altered, context)
        request = dict(self.request, record_kind='actual', job_id='plan069-D5-maps-001',
                       context=file_record(altered))
        with patch('vipe_benchmark.moge_native.load_adapter') as constructor:
            with self.assertRaisesRegex(ValueError, 'RGB source lineage changed'):
                run_maps(request, self.root / request['job_id'])
            constructor.assert_not_called()
        self.assertFalse((self.root / request['job_id']).exists())
