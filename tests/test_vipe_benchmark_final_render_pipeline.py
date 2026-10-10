"""Disposable CPU worker-result contracts; no native dispatch or human evidence."""
import importlib
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from vipe_benchmark.files import object_hash


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.fixture=importlib.import_module('test_vipe_benchmark_extended_final_render_contract').AdmissionTests()
        self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.request=self.fixture.request;self.record=self.fixture.record
        self.build_records()

    def build_records(self):
        endpoint=self.request['iterations']
        self.checkpoint=self.record('fixture-checkpoint-'+str(endpoint),{'fixture':'not a native checkpoint'})
        self.image=self.record('fixture-image-'+str(endpoint),{'fixture':'not actual rendered media'})
        self.records={};parent=None
        for phase in ('geometry','initializer','train','render'):
            result=dict(schema='plan069-final-render-worker-result/v1',record_kind='fixture',status='complete',
                arm='QF-B',phase=phase,composition=self.request['compositions']['QF-B'],
                request_sha256=object_hash(self.request),allocation_id=self.request['id']+'/QF-B/'+phase,
                parent_result=parent,elapsed_seconds=.25,peak_device_bytes=0,artifact_bytes=0,
                cpu_workers_used=1,
                execution_authorized=False,native_adapter_qualified=False,artifacts=[self.image])
            if phase=='train':
                result.update(completed_iterations=endpoint,checkpoint=self.checkpoint,artifacts=[self.checkpoint])
            if phase=='render':
                reload=self.record('fixture-reload-'+str(endpoint),dict(schema='plan069-final-render-fixture-reload/v1',
                    record_kind='fixture',status='passed',checkpoint=self.checkpoint,iteration=endpoint,
                    request_sha256=object_hash(self.request),arm='QF-B'))
                result.update(checkpoint=self.checkpoint,reload_validation=reload,iteration=endpoint,
                    render_settings=self.request['render'],artifacts=[self.image,reload],
                    rendered_frames=[dict(camera=c,frame=f,rgb=self.image) for c in (0,10,20,30) for f in range(50)])
            result['artifact_bytes']=sum(record['bytes'] for record in result['artifacts'])
            parent=self.record('fixture-'+phase+'-'+str(endpoint),result);self.records[phase]=parent

    def use_endpoint(self,iterations):
        from vipe_benchmark.final_render_contract import allocation_specs
        self.request.update(iterations=iterations,allocations=allocation_specs(self.request['id'],iterations))
        self.fixture.rebind_proposal()
        self.build_records()

    def test_fixture_pipeline_binds_checkpoint_reload_and_all_heldout_frames(self):
        from vipe_benchmark.final_render_pipeline import validate_pipeline
        result=validate_pipeline(self.request,'QF-B',self.records)
        self.assertEqual(result['status'],'complete')
        self.assertEqual(result['rendered_frames'],200)
        self.assertEqual(result['records'],self.records)
        self.assertEqual(result['composition']['depth'],'D5')
        self.assertFalse(result['execution_authorized'])
        self.assertFalse(result['native_adapter_qualified'])
        self.assertFalse(result['actual_final_renders'])

    def test_worker_cpu_limit_is_checked_before_accepting_fixture_results(self):
        from vipe_benchmark.files import read_json
        from vipe_benchmark.final_render_pipeline import validate_worker_result
        result=read_json(self.records['geometry']['path']);result['cpu_workers_used']=9
        with self.assertRaisesRegex(ValueError,'cpu_workers_used'):
            validate_worker_result(self.request,'QF-B','geometry',result)

    def test_fixture_result_cannot_smuggle_an_actual_media_claim(self):
        from vipe_benchmark.files import read_json
        from vipe_benchmark.final_render_pipeline import validate_worker_result
        result=read_json(self.records['geometry']['path']);result['actual_final_renders']=True
        with self.assertRaisesRegex(ValueError,'exact worker result fields'):
            validate_worker_result(self.request,'QF-B','geometry',result)

    def test_failed_training_preserves_partial_artifacts_and_stops_render(self):
        from vipe_benchmark.files import read_json
        from vipe_benchmark.final_render_pipeline import validate_pipeline
        result=read_json(self.records['train']['path'])
        result.update(status='failed',reason='fixture training stopped before the endpoint')
        result.pop('checkpoint');result.pop('completed_iterations')
        records=dict(self.records,train=self.record('failed-train',result))
        with self.assertRaisesRegex(ValueError,'continued after'):
            validate_pipeline(self.request,'QF-B',records)
        records.pop('render')
        report=validate_pipeline(self.request,'QF-B',records)
        self.assertEqual(report['status'],'failed')
        self.assertEqual(report['reason'],'fixture training stopped before the endpoint')
        self.assertEqual(report['records']['train'],records['train'])
        self.assertEqual(result['artifacts'],[self.checkpoint])
        self.assertEqual(report['rendered_frames'],0)

    def test_missing_phase_is_blocked_and_skipped_or_substituted_predecessor_rejected(self):
        from vipe_benchmark.files import read_json
        from vipe_benchmark.final_render_pipeline import validate_pipeline
        partial={'geometry':self.records['geometry']}
        self.assertEqual(validate_pipeline(self.request,'QF-B',partial)['reason'],'missing initializer result')
        with self.assertRaisesRegex(ValueError,'skipped'):
            validate_pipeline(self.request,'QF-B',{'train':self.records['train']})
        initializer=read_json(self.records['initializer']['path'])
        initializer['parent_result']=self.record('copied-geometry',read_json(self.records['geometry']['path']))
        with self.assertRaisesRegex(ValueError,'substituted predecessor'):
            validate_pipeline(self.request,'QF-B',dict(self.records,initializer=self.record('changed-initializer',initializer)))

    def test_endpoint_reload_coverage_resource_and_identity_mutations_are_rejected(self):
        from vipe_benchmark.files import read_json
        from vipe_benchmark.final_render_pipeline import validate_worker_result
        cases=[('train','completed_iterations',4999),('render','iteration',True),
            ('render','checkpoint',self.image),('render','rendered_frames',[]),
            ('geometry','elapsed_seconds',float('inf')),('geometry','elapsed_seconds',True),
            ('geometry','elapsed_seconds',5401),('geometry','artifact_bytes',0),
            ('geometry','peak_device_bytes',23*2**30),('geometry','cpu_workers_used',True),
            ('geometry','allocation_id','foreign/QF-B/geometry'),('geometry','native_adapter_qualified',True)]
        for phase,field,value in cases:
            result=read_json(self.records[phase]['path']);result[field]=value
            with self.subTest(phase=phase,field=field),self.assertRaises(ValueError):
                validate_worker_result(self.request,'QF-B',phase,result)
        result=read_json(self.records['render']['path']);result['rendered_frames'][-1]=result['rendered_frames'][0]
        with self.assertRaisesRegex(ValueError,'coverage'):
            validate_worker_result(self.request,'QF-B','render',result)

    def test_altered_artifact_and_actual_mode_are_rejected(self):
        from vipe_benchmark.final_render_pipeline import validate_pipeline
        actual=dict(self.request,record_kind='actual')
        with self.assertRaisesRegex(ValueError,'fixture-only'):
            validate_pipeline(actual,'QF-B',self.records)
        Path(self.checkpoint['path']).write_text('changed checkpoint bytes')
        with self.assertRaises(ValueError):
            validate_pipeline(self.request,'QF-B',self.records)

    def test_standalone_render_rehashes_the_consumed_training_checkpoint(self):
        from vipe_benchmark.files import read_json
        from vipe_benchmark.final_render_pipeline import validate_worker_result
        result=read_json(self.records['render']['path'])
        Path(self.checkpoint['path']).write_text('changed checkpoint bytes')
        with self.assertRaises(ValueError):
            validate_worker_result(self.request,'QF-B','render',result)

    def test_five_fixture_pipelines_share_depth_and_keep_separate_arm_results(self):
        from vipe_benchmark.files import read_json
        from vipe_benchmark.final_render_pipeline import validate_pipeline
        for arm in ('QF-B','QF-M1','QF-M2','QF-N1','QF-N2'):
            records={};parent=None
            for phase,original in self.records.items():
                result=read_json(original['path'])
                result.update(arm=arm,composition=self.request['compositions'][arm],
                    allocation_id=self.request['id']+'/'+arm+'/'+phase,parent_result=parent)
                if phase=='render':
                    reload=read_json(result['reload_validation']['path']);reload['arm']=arm
                    result['reload_validation']=self.record('reload-'+arm,reload)
                    result['artifacts']=[self.image,result['reload_validation']]
                    result['artifact_bytes']=sum(record['bytes'] for record in result['artifacts'])
                parent=self.record(arm+'-'+phase,result);records[phase]=parent
            with self.subTest(arm=arm):
                report=validate_pipeline(self.request,arm,records)
                self.assertEqual(report['rendered_frames'],200)
                self.assertEqual(report['composition']['depth'],'D5')
                self.assertEqual(report['arm'],arm)

    def test_missing_parent_field_is_rejected_as_a_contract_error(self):
        from vipe_benchmark.files import read_json
        from vipe_benchmark.final_render_pipeline import validate_worker_result
        result=read_json(self.records['geometry']['path']);result.pop('parent_result')
        with self.assertRaisesRegex(ValueError,'exact worker result fields'):
            validate_worker_result(self.request,'QF-B','geometry',result)


if __name__=='__main__':
    unittest.main()
