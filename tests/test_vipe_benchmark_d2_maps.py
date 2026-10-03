import json
from types import SimpleNamespace
import numpy as np
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from vipe_benchmark.d2_maps import run, build_request
from vipe_benchmark.files import file_record, object_hash, write_json
from basketball_vipe_d2_maps import active_reservation


class D2MapsTest(unittest.TestCase):
    def test_cli_guard_rejects_unreserved_gpu_work(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request_path = root / 'request.json'
            request_path.write_text('{}')
            output = root / 'jobs/plan069-D2-maps-001'
            request = dict(record_kind='actual', job_id=output.name,
                ledger_path=str(root / 'ledger.jsonl'),
                runtime=dict(python='/missing/qualified/python'))
            self.assertFalse(active_reservation(request, request_path, output))
            self.assertFalse(output.exists())

    def test_cli_rejects_hashed_failed_or_wrong_candidate_admission(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request_path = root / 'request.json'
            output = root / 'jobs/plan069-D2-maps-001'
            for status, candidate in (('failed', 'D2'), ('passed', 'D7')):
                admission = root / f'admission-{candidate}-{status}.json'
                write_json(admission, dict(schema='plan069-depth-admission-result/v1',
                    status=status, candidate=candidate))
                request = dict(record_kind='actual', job_id=output.name,
                    ledger_path=str(root / 'ledger.jsonl'), admission=file_record(admission),
                    runtime=dict(python='/missing/qualified/python'))
                request_path.write_text(json.dumps(request))
                self.assertFalse(active_reservation(request, request_path, output))
            self.assertFalse(output.exists())

    def test_builder_binds_native_runtime_component_and_source_roots(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            proposal = dict(candidate='D2')
            assets = dict(path='/frozen/assets.json', sha256='a' * 64, bytes=1)
            runtime = dict(python='/qualified/environment/bin/python')
            preflight = root / 'preflight.json'
            context = root / 'context.json'
            write_json(preflight, dict(candidate='D2', proposal_sha256=object_hash(proposal),
                assets=assets, runtime=runtime))
            write_json(context, dict(inputs={'path': '/accepted/inputs.json'}))
            with patch('vipe_benchmark.d2_maps.local_source_records', return_value=['sources']):
                request = build_request(proposal=proposal, preflight=file_record(preflight),
                    historical_check={}, context=file_record(context), admission={},
                    ledger_path=root / 'ledger.jsonl', forbidden_vipe_roots=['/forbidden/vipe'])
            self.assertEqual(request['component'], 'D2')
            self.assertEqual(request['runtime'], runtime)
            self.assertEqual(request['assets_record'], assets)
            self.assertEqual(request['local_sources'], ['sources'])
            self.assertEqual(request['forbidden_vipe_roots'], ['/forbidden/vipe'])

    def test_cli_binds_qualification_worker_runtime_before_ledger(self):
        import basketball_vipe_d2_maps as cli
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / 'jobs/plan069-D2-maps-001'
            proposal = dict(candidate='D2')
            request = dict(record_kind='actual', component='D2', job_id=output.name,
                ledger_path=str(root / 'ledger.jsonl'), proposal=proposal,
                proposal_sha256=object_hash(proposal), local_sources=['sources'],
                admission=dict(path='admission'), preflight=dict(path='preflight'),
                assets_record=dict(path='assets'), runtime=dict(python='/wrong/python'))
            documents = dict(admission=dict(schema='plan069-depth-admission-result/v1',
                status='passed', candidate='D2', proposal_sha256=object_hash(proposal),
                review=dict(path='review'), source_review=dict(path='source'),
                qualification=dict(path='qualification'), runtime={}),
                review=dict(proposals=[proposal]), source=dict(local_sources=['sources']),
                qualification=dict(schema='plan069-depth-D2-qualification/v1', candidate='D2',
                    worker_runtime=dict(python='/qualified/python'), runtime={},
                    preflight=request['preflight'], assets_record=request['assets_record']))
            with patch.object(cli, 'verify_record', side_effect=lambda record: record), \
                 patch.object(cli, 'read_json', side_effect=lambda path: documents[path]), \
                 patch.object(cli, 'local_source_records', return_value=['sources']), \
                 patch.object(cli, 'Ledger') as ledger:
                self.assertFalse(active_reservation(request, root / 'request.json', output))
                ledger.assert_not_called()

    def test_complete_fixture_preserves_four_anchors_and_native_metadata(self):
        from vipe_benchmark import d2_maps
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def record(name, payload):
                path = root / name
                write_json(path, payload)
                return file_record(path)
            rgb = root / 'rgb.bin'
            rgb.write_bytes(b'frozen RGB')
            anchor_path = root / 'anchor.npz'
            anchor_path.write_bytes(b'unchanged frozen anchor')
            anchor_record = file_record(anchor_path)
            inputs = record('inputs.json', {})
            assets = dict(da3_snapshot=dict(files=[file_record(rgb)]))
            assets_record = record('assets.json', assets)
            runtime = {}
            settings = json.loads(d2_maps.HISTORICAL.read_text())['settings']['D2']
            K = np.eye(3).tolist()
            metadata = dict(component='D2', settings=settings, settings_sha256=object_hash(settings),
                assets_sha256=object_hash(assets), native_processed_K=K)
            frozen = record('frozen.json', dict(component='D2', role='check',
                configuration=file_record(d2_maps.BENCHMARK), assets=assets,
                runtime=runtime, inputs=inputs, forbidden_vipe_roots=['/forbidden/vipe']))
            historical = record('historical.json', dict(status='complete', component='D2',
                component_sha256=object_hash(dict(component='D2', assets=assets, runtime=runtime)),
                configuration=frozen, rows=[dict(identity=dict(camera=c, frame=175),
                    depth=anchor_record, source_rgb_sha256=file_record(rgb)['sha256'],
                    K=K, grid='scale-opencv-integer', metadata=metadata)
                    for c in range(1, 34) if c not in (0, 10, 20, 30)]))
            rows = [dict(camera=c, frame=f, role='check', grid='scale-opencv-integer',
                K=K, source_rgb=file_record(rgb))
                for c in range(1, 34) if c not in (10, 20, 30) for f in range(50, 200)]
            context = record('context.json', dict(schema=d2_maps.SCHEMA, inputs=inputs, rows=rows))
            preflight = record('preflight.json', dict(schema=d2_maps.PREFLIGHT_SCHEMA,
                status='cpu_preflight_passed', candidate='D2', proposal_sha256='p',
                assets=assets_record, runtime=runtime, checkpoint=file_record(rgb)))
            request = dict(schema=d2_maps.REQUEST_SCHEMA, job_id='plan069-D2-maps-001',
                candidate='D2', record_kind='fixture', max_seconds=3600,
                preflight=preflight, proposal_sha256='p', assets_record=assets_record,
                runtime=runtime, historical_check=historical, context=context,
                inputs=inputs, forbidden_vipe_roots=['/forbidden/vipe'])
            valid = np.ones((540, 960), bool)
            estimate = SimpleNamespace(depth=np.ones((540, 960), np.float32), valid=valid,
                raw_depth=np.ones((4, 4), np.float32), metadata=metadata, confidence=None)
            calls = []
            class Backend:
                component = 'D2'
                def predict(self, *_args):
                    calls.append(1)
                    return estimate
            def load_role(_record, camera, _role):
                images = np.broadcast_to(np.zeros((1, 1, 1, 3), np.uint8), (50, 540, 960, 3))
                return images, valid, [r for r in rows if r['camera']==camera and 150<=r['frame']<200]
            with patch.object(d2_maps, 'AssetBundle', return_value=SimpleNamespace(records=assets)), \
                 patch.object(d2_maps, 'verify_runtime'):
                with self.assertRaisesRegex(ValueError, 'historical component configuration'):
                    run(dict(request, inputs={}), root / request['job_id'],
                        backend=Backend(), load_role=load_role)
                self.assertFalse((root / request['job_id']).exists())
                result = run(request, root / request['job_id'], backend=Backend(), load_role=load_role)
            self.assertEqual(len(calls), 196)
            self.assertEqual(len(result['rows']), 200)
            anchors = [r for r in result['rows'] if r['reused_anchor']]
            self.assertEqual(len(anchors), 4)
            self.assertTrue(all(r['prediction']==anchor_record for r in anchors))
            self.assertTrue(all(r['metadata']['native_processed_K']==K for r in result['rows']))

    def test_actual_worker_requires_reserved_supervision_before_model_work(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'plan069-D2-maps-001'
            request = dict(schema='plan069-d2-maps-request/v1',
                job_id=output.name, candidate='D2', record_kind='actual',
                max_seconds=3600)
            class Backend:
                def predict(self, *_args):
                    self.fail('model must not run')
            with self.assertRaisesRegex(ValueError, 'active exact supervision'):
                run(request, output, backend=Backend())
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
