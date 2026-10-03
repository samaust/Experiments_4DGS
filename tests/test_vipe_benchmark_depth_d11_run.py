"""D11's admitted map workload preserves native relative-log values on CPU."""

from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.depth_d11_run import run_maps, validate_result
from vipe_benchmark.files import file_record, read_json, write_json
from vipe_benchmark.marigold_relative import PROFILE
import test_vipe_benchmark_depth_single_run as single_fixture


class RelativePlane:
    component = 'D11'

    def __init__(self):
        self.calls = 0

    def predict(self, rgb, K, image_valid):
        self.calls += 1
        values = np.full(image_valid.shape, -2.5, np.float32)
        values[~image_valid] = np.nan
        return SimpleNamespace(domain='relative_log', values=values, valid=image_valid.copy(),
            raw_values=np.full(image_valid.shape, -2.5, np.float32), metadata=dict(profile=PROFILE))


class D11MapsTests(unittest.TestCase):
    def setUp(self):
        self.fixture = single_fixture.SingleMapsTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.request = dict(self.fixture.request, schema='plan069-D11-maps-request/v1',
                            candidate='D11', job_id='plan069-D11-maps-fixture-001')

    def test_exact_workload_retains_negative_log_depth_without_scale_fitting(self):
        backend = RelativePlane()
        with patch('vipe_benchmark.depth_d11_run.materialize_role', self.fixture.materialize):
            result = run_maps(self.request, self.root / self.request['job_id'], backend=backend)
        self.assertEqual(backend.calls, 256)
        self.assertEqual(sum(row['kind'] == 'anchor' for row in result['rows']), 60)
        self.assertEqual(sum(row['kind'] == 'clip-extra' for row in result['rows']), 196)
        self.assertEqual(result['engineering_eligibility'], 'not_applicable')
        self.assertNotIn('scales', result)
        self.assertFalse((self.root / self.request['job_id'] / 'scale-fit.json').exists())
        with np.load(result['rows'][0]['prediction']['path']) as data:
            self.assertEqual(set(data.files), {'relative', 'valid', 'raw_values'})
            self.assertEqual(float(data['relative'][0, 0]), -2.5)
            self.assertEqual(float(data['raw_values'][0, 0]), -2.5)
        validate_result(result, self.request)
        changed = self.root / 'changed-native-map.npz'
        with np.load(result['rows'][0]['prediction']['path']) as data:
            np.savez_compressed(changed, relative=data['relative'], valid=data['valid'],
                                raw_values=data['raw_values'] + np.float32(1))
        altered = dict(result, rows=[dict(result['rows'][0], prediction=file_record(changed))] + result['rows'][1:])
        with self.assertRaisesRegex(ValueError, 'saved native relative-log array'):
            validate_result(altered, self.request)
        with self.assertRaisesRegex(ValueError, 'nonmetric D11 result'):
            validate_result(dict(result, scales={'fit': 'pseudo-metric'}), self.request)
        with self.assertRaisesRegex(ValueError, 'row source'):
            altered = dict(result, rows=[dict(result['rows'][0], source_rgb_grid='distorted-opencv-integer')] + result['rows'][1:])
            validate_result(altered, self.request)

    def test_actual_worker_invokes_one_native_folder_in_deterministic_order(self):
        import hashlib
        request = dict(self.request, record_kind='actual', job_id='plan069-D11-maps-001')
        setup = dict(native_source=dict(test='synthetic'), source_manifest=dict(test='synthetic'),
                     runtime=dict(native_qualification=dict(test='synthetic')))
        path = self.root / 'setup.json'
        write_json(path, setup)
        request['setup'] = file_record(path)
        calls = []
        def native(setup, frames, output, **options):
            calls.append([name for name, _ in frames])
            output.mkdir()
            prediction = output / 'native.npy'
            np.save(prediction, np.full((540, 960), -2.5, np.float32))
            rows = [dict(id=name, rgb_sha256=hashlib.sha256(rgb.tobytes()).hexdigest(),
                         prediction=file_record(prediction)) for name, rgb in frames]
            write_json(output / 'result.json', dict(schema='plan069-D11-native-folder-result/v1',
                status='complete', profile=PROFILE, setup_source=setup['native_source'],
                source_manifest=setup['source_manifest'],
                native_qualification=setup['runtime']['native_qualification'], predictions=rows))
            return rows
        with patch('vipe_benchmark.depth_d11_run._actual_output_guard') as output_guard, patch('vipe_benchmark.depth_d11_run._check_actual_slot') as slot_guard, patch('vipe_benchmark.depth_d11_run._actual_gate', return_value=(__import__('time').monotonic()+120, setup)), patch(
                'vipe_benchmark.depth_d11_run.materialize_role', self.fixture.materialize), patch(
                'vipe_benchmark.depth_d11_run.run_folder', native):
            result = run_maps(request, self.root / request['job_id'], request_path=self.root / 'request.json')
        self.assertEqual(slot_guard.call_count,1)
        self.assertEqual(output_guard.return_value.call_count,512)
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(calls[0]), 256)
        self.assertEqual(calls[0], sorted(calls[0]))
        self.assertEqual(calls[0].count('camera01-frame175'), 1)
        validate_result(result, request)

    def test_unreserved_actual_work_never_launches_native_cli(self):
        request = dict(self.request, record_kind='actual', job_id='plan069-D11-maps-001',
                       ledger_path=str(self.root / 'ledger.jsonl'))
        path = self.root / 'request.json'
        write_json(path, request)
        with patch('vipe_benchmark.depth_d11_run.run_folder') as native:
            with self.assertRaisesRegex(ValueError, 'active exact single-image GPU reservation'):
                run_maps(request, self.root / 'jobs' / request['job_id'], request_path=path)
            native.assert_not_called()

    def test_changed_context_pixels_fail_before_any_native_attempt(self):
        context = read_json(self.request['context']['path'])
        next(row for row in context['rows'] if row['camera'] == 1 and row['frame'] == 150)['source_rgb'] = self.fixture.rgb
        path = self.root / 'changed-context.json'
        write_json(path, context)
        backend = RelativePlane()
        with self.assertRaisesRegex(ValueError, 'RGB source lineage'):
            run_maps(dict(self.request, context=file_record(path)),
                     self.root / self.request['job_id'], backend=backend)
        self.assertEqual(backend.calls, 0)


if __name__ == '__main__':
    unittest.main()
