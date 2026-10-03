"""CPU rendering contracts; fake ledgers never authorize real execution."""
from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.config import load
from vipe_benchmark.depth_anchor_previews import aggregate_request, render
from vipe_benchmark.depth_aggregate import CANDIDATES, DOMAINS
from vipe_benchmark.files import file_record, read_json, write_json


class FakeLedger:
    def __init__(self, root, config):
        self.path = root / 'ledger.jsonl'
        self.config = dict(config, new_download_gib_limit=110, new_artifact_disk_gib_limit=210)
        self.charges = []

    def events(self):
        return []

    def states(self):
        return {}

    def totals(self):
        return dict(cpu=dict(elapsed_seconds=0))

    def charge_cpu_preparation(self, elapsed, evidence):
        self.charges.append((elapsed, evidence))


class AnchorPreviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.cameras = [camera for camera in range(1, 34) if camera not in (10, 20, 30)]
        self.camera_patch = patch('vipe_benchmark.depth_anchor_previews.training_cameras', return_value=self.cameras)
        self.camera_patch.start()
        rgb = self.root / 'rgb.png'
        Image.new('RGB', (960, 540), (10, 20, 30)).save(rgb)
        self.rgb = file_record(rgb)
        values = np.full((540, 960), 3, np.float32)
        valid = np.ones(values.shape, np.bool_)
        valid[0, 0] = False
        values[0, 0] = np.nan
        values[0, 1] = 21
        values[0, 2] = 20
        values[0, 3] = 19
        self.raw_path = self.root / 'depth.npz'
        np.savez_compressed(self.raw_path, depth=values, valid=valid)
        self.raw = file_record(self.raw_path)
        self.inputs = self.record('inputs', dict(synthetic=True))
        self.config = self.record('config', load())
        self.context = self.record('context', dict(schema='plan069-depth-context/v1', inputs=self.inputs,
            anchors=[dict(camera=camera, frame=frame, accepted_rgb=self.rgb)
                     for camera in self.cameras for frame in (100, 175)]))

    def tearDown(self):
        self.camera_patch.stop()
        self.temp.cleanup()

    def record(self, name, value):
        path = self.root / (name + '.json')
        write_json(path, value)
        return file_record(path)

    def request(self, candidate='D7', kind='fixture'):
        if DOMAINS[candidate] != 'camera_z_metres':
            with np.load(self.raw_path) as data:
                values, valid = data['depth'], data['valid']
            relative = self.root / (candidate + '-relative.npz')
            np.savez_compressed(relative, relative=values, valid=valid)
            self.raw = file_record(relative)
        rows = [dict(camera=camera, frame=frame, prediction=self.raw, source_rgb=self.rgb,
                     domain=DOMAINS[candidate])
                for camera in self.cameras for frame in (100, 175)]
        native = self.record(candidate + '-native', dict(rows=rows))
        package = self.record(candidate + '-package', dict(synthetic=True))
        clips = self.record(candidate + '-clips', dict(package=package))
        slot = dict(status='available', reason='', clips=clips, evidence={},
                    provenance=dict(source_result=native, ledger_outcome=self.inputs, configuration=self.config))
        return dict(schema='plan069-depth-anchor-preview-request/v1', record_kind=kind,
                    candidate=candidate, preview_revision='002', config=self.config, context=self.context, inputs=self.inputs,
                    slot=slot, max_seconds=30, max_artifact_bytes=32 * 2**20)

    def test_sixty_metric_previews_preserve_raw_maps_and_source_frames(self):
        request = self.request()
        result = render(request, self.root / 'previews')
        self.assertEqual(result['rendered_frames'], 60)
        self.assertEqual(len(result['source_rgb']), 60)
        self.assertEqual({(row['camera'], row['frame']) for row in result['anchors']},
                         {(camera, frame) for camera in self.cameras for frame in (100, 175)})
        self.assertTrue(all(row['prediction'] == self.raw and row['source_rgb'] == self.rgb
                            for row in result['anchors']))
        with Image.open(result['anchors'][0]['record']['path']) as image:
            self.assertEqual(image.size, (960, 540))
            self.assertEqual(image.getpixel((0, 0)), (255, 0, 255))
            self.assertEqual(image.getpixel((1, 0)), (255, 0, 0))
            self.assertEqual(image.getpixel((2, 0)), (255, 255, 255))
            self.assertEqual(image.getpixel((3, 0)), (242, 242, 242))
        self.assertEqual(result['anchors'][0]['display']['range_metres'], [0, 20])
        self.assertEqual(result['anchors'][0]['display']['above_20_metres_color'], 'red')
        self.assertEqual(result['anchors'][0]['display']['invalid_color'], 'magenta')
        self.assertEqual(file_record(self.raw_path), self.raw)
        with self.assertRaisesRegex(ValueError, 'immutable'):
            render(request, self.root / 'previews')

    def test_relative_previews_declare_frame_scope_and_preserve_native_values(self):
        request = self.request('D11')
        result = render(request, self.root / 'relative')
        self.assertEqual(file_record(self.raw['path']), self.raw)
        display = result['anchors'][0]['display']
        self.assertEqual(display['normalization_scope'], 'one frozen anchor frame')
        self.assertEqual(display['units'], 'relative arbitrary values')
        self.assertNotIn('range_metres', display)
        self.assertEqual(result['physical_accuracy'], 'unverified')
        self.assertEqual(result['human_review'], 'pending')

    def test_actual_revision_001_cannot_be_overwritten_or_reused(self):
        request = self.request()
        request['preview_revision'] = '001'
        output = self.root / 'old-preview'
        with self.assertRaisesRegex(ValueError, 'revision 002'):
            render(request, output)
        self.assertFalse(output.exists())

    def test_video_relative_npz_uses_native_key(self):
        request = self.request('D9')
        result = render(request, self.root / 'video-relative')
        self.assertEqual(result['anchors'][0]['display']['domain'], 'relative_inverse')
        self.assertEqual(result['anchors'][0]['display']['direction'], 'larger means nearer')
        self.assertEqual(file_record(self.raw['path']), self.raw)

    def test_proof_verification_counts_toward_deadline_before_writes(self):
        request = self.request(kind='actual')
        ledger = FakeLedger(self.root, load())
        output = self.root / 'jobs/plan069-D7-anchor-previews-002'
        clock = [100.0]
        def slow_proof(*args):
            clock[0] += 31
            return None, None, None
        with patch('vipe_benchmark.depth_anchor_previews.time.monotonic', side_effect=lambda: clock[0]), \
             patch('vipe_benchmark.depth_anchor_previews._native_result', side_effect=slow_proof), \
             patch('vipe_benchmark.depth_anchor_previews._clips'), \
             patch('vipe_benchmark.budgets.budget_snapshot', return_value=dict(artifact_bytes=0)):
            with self.assertRaisesRegex(ValueError, 'deadline during proof') as caught:
                render(request, output, ledger=ledger)
        self.assertEqual(caught.exception.anchor_preview_elapsed_seconds, 31)
        self.assertFalse(output.exists())
        self.assertEqual(ledger.charges, [])

    def test_output_creation_failure_exposes_measured_cpu_for_caller(self):
        request = self.request()
        clock = [100.0]
        from vipe_benchmark.depth_anchor_previews import _prepare
        def slow_proof(*args):
            prepared = _prepare(*args)
            clock[0] += 5
            return prepared
        with patch('vipe_benchmark.depth_anchor_previews.time.monotonic', side_effect=lambda: clock[0]), \
             patch('vipe_benchmark.depth_anchor_previews._prepare', side_effect=slow_proof), \
             patch('pathlib.Path.mkdir', side_effect=PermissionError('read only')):
            with self.assertRaisesRegex(PermissionError, 'read only') as caught:
                render(request, self.root / 'unwritable')
        self.assertEqual(caught.exception.anchor_preview_elapsed_seconds, 5)
        self.assertFalse((self.root / 'unwritable').exists())

    def test_failed_render_preserves_failure_and_respects_artifact_bound(self):
        request = self.request()
        request['max_artifact_bytes'] = 1
        with self.assertRaisesRegex(ValueError, 'CPU/disk bound'):
            render(request, self.root / 'too-small')
        self.assertEqual(read_json(self.root / 'too-small/cpu-failure.json')['status'], 'failed')

    def test_actual_shaped_cpu_render_charges_success_and_failure_to_fake_ledger(self):
        ledger = FakeLedger(self.root, load())
        output = self.root / 'jobs/plan069-D7-anchor-previews-002'
        request = self.request(kind='actual')
        clock = [100.0]
        def slow_proof(*args):
            clock[0] += 5
            return None, None, None
        with patch('vipe_benchmark.depth_anchor_previews.time.monotonic', side_effect=lambda: clock[0]), \
             patch('vipe_benchmark.depth_anchor_previews._native_result', side_effect=slow_proof), \
             patch('vipe_benchmark.depth_anchor_previews._clips'), \
             patch('vipe_benchmark.budgets.budget_snapshot', return_value=dict(artifact_bytes=0)):
            result = render(request, output, ledger=ledger)
        self.assertEqual(len(ledger.charges), 1)
        self.assertEqual(ledger.charges[0][0], 5)
        self.assertEqual(result['elapsed_seconds'], 5)
        accounting = read_json(ledger.charges[0][1]['path'])
        self.assertEqual(accounting['result'], file_record(output / 'result.json'))
        template = dict(schema='plan069-depth-aggregate-request/v1', record_kind='actual',
                        bindings=dict(context=self.context, inputs=self.inputs),
                        candidates={candidate: dict(status='missing', reason='Pending', evidence={})
                                    for candidate in CANDIDATES})
        template['candidates']['D7'] = deepcopy(request['slot'])
        aggregate = aggregate_request(template, dict(D7=file_record(output / 'result.json')))
        self.assertEqual(len(aggregate['candidates']['D7']['anchors']), 60)
        self.assertEqual(aggregate['candidates']['D11']['status'], 'missing')
        self.assertEqual(template['candidates']['D7'], request['slot'])
        failed_root = self.root / 'failed'
        failed_ledger = FakeLedger(failed_root, load())
        request['max_artifact_bytes'] = 1
        with patch('vipe_benchmark.depth_anchor_previews._native_result', return_value=(None, None, None)), \
             patch('vipe_benchmark.depth_anchor_previews._clips'), \
             patch('vipe_benchmark.budgets.budget_snapshot', return_value=dict(artifact_bytes=0)):
            with self.assertRaisesRegex(ValueError, 'CPU/disk bound'):
                render(request, failed_root / 'jobs/plan069-D7-anchor-previews-002', ledger=failed_ledger)
        self.assertEqual(len(failed_ledger.charges), 1)
        self.assertEqual(read_json(failed_ledger.charges[0][1]['path'])['status'], 'failed')

    def test_actual_native_previews_require_whole_slot_proof_before_output(self):
        for candidate in ('D11', 'D9', 'D10'):
            with self.subTest(candidate=candidate):
                request = self.request(candidate, kind='actual')
                ledger = FakeLedger(self.root, load())
                output = self.root / f'jobs/plan069-{candidate}-anchor-previews-002'
                with patch('vipe_benchmark.depth_anchor_previews._native_result', return_value=(None, None, None)), \
                     patch('vipe_benchmark.depth_anchor_previews._clips'), \
                     patch('vipe_benchmark.budgets.budget_snapshot', return_value=dict(artifact_bytes=0)):
                    with self.assertRaisesRegex(ValueError, 'native depth diagnostics require whole-slot byte proof'):
                        render(request, output, ledger=ledger)
                self.assertFalse(output.exists())
                self.assertEqual(ledger.charges, [])

    def test_preview_slot_guards_stop_overcap_and_stage_downloads(self):
        request = self.request('D9', kind='actual')
        for mode in ('before-output', 'after-png', 'download'):
            with self.subTest(mode=mode):
                root = self.root / mode
                ledger = FakeLedger(root, load())
                output = root / 'jobs/plan069-D9-anchor-previews-002'
                def factory(*args):
                    if mode == 'before-output':
                        raise ValueError('retained candidate artifacts exceed whole-slot allocation')
                    def full():
                        if mode == 'download':
                            raise ValueError('CPU diagnostics must not acquire new downloads')
                    def fast(additional_bytes=0):
                        if mode == 'after-png' and list(output.glob('*.png')):
                            raise ValueError('next map output exceeds remaining whole-slot artifact headroom')
                    return full, fast
                with patch('vipe_benchmark.depth_anchor_previews._native_result', return_value=(None, None, None)), \
                     patch('vipe_benchmark.depth_anchor_previews._clips'), \
                     patch('vipe_benchmark.depth_anchor_previews._publication_guards', side_effect=factory), \
                     patch('vipe_benchmark.budgets.budget_snapshot', return_value=dict(artifact_bytes=0)):
                    with self.assertRaises(ValueError):
                        render(request, output, ledger=ledger)
                if mode == 'before-output':
                    self.assertFalse(output.exists())
                    self.assertEqual(ledger.charges, [])
                else:
                    self.assertFalse((output / 'cpu-accounting.json').exists())
                    self.assertEqual(len(ledger.charges), 1)
                    self.assertEqual(read_json(output / 'cpu-failure.json')['status'], 'failed')
                    self.assertEqual(len(list(output.glob('*.png'))), 1 if mode == 'after-png' else 60)

    def test_fixture_previews_cannot_be_used_as_actual_aggregate_evidence(self):
        request = self.request()
        output = self.root / 'fixture'
        render(request, output)
        template = dict(schema='plan069-depth-aggregate-request/v1', record_kind='actual',
            bindings=dict(context=self.context, inputs=self.inputs), candidates={
                candidate: dict(status='missing', reason='Pending', evidence={}) for candidate in CANDIDATES})
        template['candidates']['D7'] = request['slot']
        with self.assertRaisesRegex(ValueError, 'actual anchor preview receipt'):
            aggregate_request(template, dict(D7=file_record(output / 'result.json')))

    def test_unadmitted_native_evidence_stops_before_actual_rendering(self):
        request = self.request(kind='actual')
        ledger = FakeLedger(self.root, load())
        output = self.root / 'jobs/plan069-D7-anchor-previews-002'
        with patch('vipe_benchmark.budgets.budget_snapshot', return_value=dict(artifact_bytes=0)):
            with self.assertRaisesRegex(ValueError, 'generation/ledger provenance'):
                render(request, output, ledger=ledger)
        self.assertFalse(output.exists())
        self.assertEqual(ledger.charges, [])

    def test_legacy_anchors_render_only_the_frozen_fit_and_check_maps(self):
        request = self.request('D0')
        for role, frame in (('fit', 100), ('check', 175)):
            historical = self.record('legacy-' + role, dict(component='D0', status='complete',
                configuration=self.record('legacy-config-' + role, dict(role=role)),
                rows=[dict(identity=dict(camera=camera, frame=frame), depth=self.raw,
                           grid='scale-opencv-integer', source_rgb_sha256=self.rgb['sha256'])
                      for camera in self.cameras]))
            request['slot']['evidence']['historical_' + role] = historical
        result = render(request, self.root / 'historical-previews')
        self.assertEqual(len(result['anchors']), 60)
        self.assertTrue(all(row['prediction'] == self.raw for row in result['anchors']))


if __name__ == '__main__':
    unittest.main()
