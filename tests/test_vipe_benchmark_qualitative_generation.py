"""CPU generation requests preserve source identities and accounting."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.files import file_record, write_json, read_json
from vipe_benchmark.qualitative_generation import generate, validate_actual_package, publish_generation


class GenerationTests(unittest.TestCase):
    def setUp(self):
        from PIL import Image
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        rgb = self.root / 'rgb.png'; Image.new('RGB', (16, 12), 'white').save(rgb)
        self.identity = dict(branch='reconstruction', camera=1, frame=0, pair_start=0)
        self.input = dict(identity=self.identity, rgb=file_record(rgb), K=[], grid='fixture')
        depth=dict(self.input,identity=dict(branch='depth',camera=1,frame=175,pair_start=None))
        inputs = self.root / 'inputs.json'; write_json(inputs, dict(rgb=[self.input], depth=[depth]))
        authority = self.root / 'authority.json'; write_json(authority, {'scope':'fixture'})
        self.request = dict(schema='plan067-qualitative-generation/v1', id='fixture', record_kind='fixture',
            local=str(self.root), max_seconds=60, cameras=[1], reconstruction_frames=[0], depth_frames=[175],
            depth_range_metres=[0,20], bindings={k:file_record(authority) for k in ('config','amendment','approval')})
        self.request['bindings']['inputs'] = file_record(inputs)
        class Ledger:
            config={'cpu_prepare_score_report_seconds_limit':100}
            def events(s): return []
            def states(s, events): return {}
            def totals(s, events): return {'cpu': {'elapsed_seconds':0}}
            def charge_cpu_preparation(s, seconds, evidence):
                s.charge=(seconds,evidence)
                return {'event':'cpu_preparation_charge'}
        self.ledger = Ledger()
    def tearDown(self): self.temp.cleanup()
    def test_missing_results_are_inventory_and_charge_once(self):
        with patch('vipe_benchmark.qualitative_generation.result_record', return_value=None):
            result = generate(self.request, self.root/'out', ledger=self.ledger)
        self.assertEqual(result['status'],'complete')
        group=read_json(result['manifests']['segmentation']['path'])
        self.assertEqual(group['candidates'][1]['status'],'missing')
        self.assertEqual(group['candidates'][0]['output_type'],'reference')
        self.assertGreaterEqual(self.ledger.charge[0],0)
        with self.assertRaises(FileExistsError): generate(self.request,self.root/'out',ledger=self.ledger)
    def test_deadline_failure_is_immutable_and_charged(self):
        with patch('vipe_benchmark.qualitative_generation.result_record', side_effect=ValueError('corrupt source')):
            with self.assertRaisesRegex(ValueError,'corrupt source'):
                generate(self.request,self.root/'out',ledger=self.ledger)
        self.assertEqual(read_json(self.root/'out/result.json')['status'],'failed')
        self.assertTrue(hasattr(self.ledger,'charge'))
    def test_selection_freezes_and_budget_checked_before_publication(self):
        self.request['reconstruction_frames']=[0,0]
        with self.assertRaises(ValueError): generate(self.request,self.root/'out',ledger=self.ledger)
        self.assertFalse((self.root/'out').exists())
        self.request['reconstruction_frames']=[0]; self.request['max_seconds']=101
        with self.assertRaisesRegex(ValueError,'CPU'): generate(self.request,self.root/'out',ledger=self.ledger)
    def test_output_is_bound_to_completed_result_and_matching_rgb(self):
        from PIL import Image
        mask=self.root/'mask.png'; Image.new('L',(16,12),255).save(mask)
        row=dict(self.input,source_rgb_sha256=self.input['rgb']['sha256'],semantic_static=file_record(mask))
        source=self.root/'source.json';write_json(source,dict(status='complete',component='S2',rows=[row]))
        event=dict(event='finish',status='complete',result=file_record(source))
        self.ledger.events=lambda:[event]
        with patch('vipe_benchmark.qualitative_generation.result_record',side_effect=lambda local,job:file_record(source) if job=='S2-reconstruction' else None):
            result=generate(self.request,self.root/'out',ledger=self.ledger)
        group=read_json(result['manifests']['segmentation']['path'])
        candidate=next(c for c in group['candidates'] if c['id']=='S2')
        self.assertEqual(candidate['status'],'available')
        self.assertEqual(candidate['media'][0]['source_input'],self.input['rgb'])
        self.assertEqual(candidate['provenance']['source_result'],file_record(source))
    def test_changed_input_geometry_fails_and_charges_without_available_package(self):
        source=self.root/'source.json'
        row=dict(self.input,source_rgb_sha256='0'*64)
        write_json(source,dict(status='complete',component='S2',rows=[row]))
        self.ledger.events=lambda:[dict(event='finish',status='complete',result=file_record(source))]
        with patch('vipe_benchmark.qualitative_generation.result_record',side_effect=lambda local,job:file_record(source) if job=='S2-reconstruction' else None):
            with self.assertRaisesRegex(ValueError,'lineage'):
                generate(self.request,self.root/'out',ledger=self.ledger)
        self.assertTrue(hasattr(self.ledger,'charge'))
        self.assertFalse((self.root/'out/segmentation/manifest.json').exists())
    def test_real_deadline_and_active_allocation_rejected(self):
        self.ledger.states=lambda events:{'model':dict(event='reserve')}
        with self.assertRaisesRegex(ValueError,'active'):
            generate(self.request,self.root/'active',ledger=self.ledger)
        self.ledger.states=lambda events:{}
        with patch('vipe_benchmark.qualitative_generation._check',side_effect=TimeoutError('deadline')):
            with self.assertRaises(TimeoutError):generate(self.request,self.root/'timeout',ledger=self.ledger)
        self.assertEqual(read_json(self.root/'timeout/result.json')['status'],'failed')
        self.assertTrue(hasattr(self.ledger,'charge'))
    def test_sparse_sequence_and_consecutive_clip_preserve_original_times(self):
        inputs=read_json(self.request['bindings']['inputs']['path'])
        for frame in (1,5,6):
            inputs['rgb'].append(dict(self.input,identity=dict(self.identity,frame=frame,pair_start=0 if frame==1 else 5)))
        path=self.root/'extended-inputs.json';write_json(path,inputs)
        self.request['bindings']['inputs']=file_record(path)
        self.request['reconstruction_frames']=[0,1,5,6]
        with patch('vipe_benchmark.qualitative_generation.result_record',return_value=None):
            result=generate(self.request,self.root/'out',ledger=self.ledger)
        manifest=read_json(result['manifests']['motion']['path'])
        videos=[m for m in manifest['candidates'][0]['media'] if m['kind']!='frame']
        self.assertEqual([(m['kind'],m['frame_ids']) for m in videos],[('sequence',[0,1,5,6]),('clip',[0,1])])
        self.assertEqual(videos[0]['timestamps'],[0,.04,.2,.24])
    def test_actual_graph_checks_charged_receipt_and_deterministic_png(self):
        from PIL import Image
        config=self.root/'config.json';write_json(config,self.ledger.config)
        inputs=self.root/'prepare/inputs.json';write_json(inputs,read_json(self.request['bindings']['inputs']['path']))
        self.request['record_kind']='actual'
        self.request['bindings']['config']=file_record(config)
        self.request['bindings']['inputs']=file_record(inputs)
        mask=self.root/'mask.png';Image.new('L',(16,12),0).save(mask)
        worker=self.root/'worker.json';write_json(worker,dict(component='S2',configuration=file_record(config),inputs=file_record(inputs)))
        row=dict(self.input,source_rgb_sha256=self.input['rgb']['sha256'],semantic_static=file_record(mask))
        source=self.root/'source.json';write_json(source,dict(status='complete',component='S2',configuration=file_record(worker),rows=[row]))
        events=[dict(event='finish',status='complete',result=file_record(source))]
        self.ledger.events=lambda:events[:]
        self.ledger.charge_cpu_preparation=lambda seconds,evidence:events.append(dict(event='cpu_preparation_charge',evidence=evidence))
        with patch('vipe_benchmark.qualitative_generation.result_record',side_effect=lambda local,job:file_record(source) if job=='S2-reconstruction' else None):
            result=generate(self.request,self.root/'out',ledger=self.ledger)
        manifest_record=result['manifests']['segmentation']
        manifest=read_json(manifest_record['path'])
        manifest['bindings'].update(generation_manifest=manifest_record,generation_result=file_record(self.root/'out/result.json'))
        with patch('vipe_benchmark.qualitative_generation.Ledger',return_value=self.ledger):
            self.assertEqual(validate_actual_package(manifest)['actual_lineage'],'verified')
            events.pop()
            with self.assertRaisesRegex(ValueError,'charge'):validate_actual_package(manifest)
    def test_publication_validation_failure_is_charged_and_not_replayed(self):
        with patch('vipe_benchmark.qualitative_generation.result_record',return_value=None):
            result=generate(self.request,self.root/'out',ledger=self.ledger)
        def failure(manifest,output):raise ValueError('lineage failed')
        output=self.root/'package'
        with self.assertRaisesRegex(ValueError,'lineage failed'):
            publish_generation(result['manifests']['segmentation'],output,ledger=self.ledger,publisher=failure)
        self.assertEqual(read_json(self.root/'package-cpu-receipt.json')['status'],'failed')
        self.assertTrue(hasattr(self.ledger,'charge'))
        with self.assertRaises(FileExistsError):
            publish_generation(result['manifests']['segmentation'],output,ledger=self.ledger,publisher=failure)
