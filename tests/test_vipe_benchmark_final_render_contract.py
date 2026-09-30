"""Prospective QF request, initializer and ledger admission seams (CPU fixtures)."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from vipe_benchmark.files import file_record,object_hash,write_json
from vipe_benchmark.final_render_contract import COMPOSITIONS,TRAINING_CAMERAS,KEYFRAMES,allocation_specs,admit_review,initializer_arrays_hash,validate_initializer,validate_worker_result
from vipe_benchmark.config import ROOT


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.events=[]
        def record(name,value):
            path=self.root/(name+'.json');write_json(path,value);return file_record(path)
        self.record=record
        config=dict(gpu_total_seconds_limit=93600,cpu_prepare_score_report_seconds_limit=57600,
            setup_wall_seconds_limit=57600,new_artifact_disk_gib_limit=150,new_download_gib_limit=60,
            cpu_max_workers=8,gpu_peak_device_gib_limit=22)
        class Ledger:
            def events(s):return self.events[:]
            def states(s,events):return {e['job_id']:e for e in events if e['event'] in ('reserve','finish','account')}
            def totals(s,events):return {r:dict(elapsed_seconds=0,reserved_seconds=0) for r in ('gpu','cpu','setup')}
        self.ledger=Ledger();self.ledger.config=config
        bindings={name:record(name,{}) for name in ('proposal','source','preset','runtime')}
        bindings['config']=record('config',config)
        bindings['qualification']=record('qualification',dict(status='passed',record_kind='fixture'))
        bindings['scene_manifest']=record('scene',dict(schema='dynamic-gaussian-scene/v1',
            evaluation=dict(training_cameras=[str(c) for c in TRAINING_CAMERAS],held_out_cameras=['0','10','20','30']),
            frames=dict(ids=list(range(50)),count=50,normalized_time=dict(formula='frame_offset / count')),
            source=dict(frame_rate=25)))
        for kind,candidate in [('segmentation','S2'),('depth','D4')]:
            bindings[kind+'_decision']=record(kind+'_decision',dict(schema='plan067-qualitative-decision/v1',
                status='ready',actual_human_review=False,selected_candidate_ids=[candidate],record_kind='fixture'))
        self.identity=lambda camera,frame,pair:dict(branch='reconstruction',camera=camera,frame=frame,pair_start=pair)
        rows=[dict(identity=self.identity(camera,frame,pair),source_rgb_sha256=f'{camera}-{frame}',K=[[1]],grid='fixture')
            for camera in TRAINING_CAMERAS for pair in KEYFRAMES for frame in (pair,pair+1)]
        input_rows=[dict(identity=dict(row['identity'],pair_start=None),rgb=dict(sha256=row['source_rgb_sha256']),K=row['K'],grid=row['grid']) for row in rows]
        bindings['inputs']=record('inputs',dict(rgb=input_rows,depth=[]))
        for component in ('S2','M0','M1','M2'):
            result=record(component,dict(status='complete',component=component,branch='reconstruction',rows=rows))
            bindings[component]=result;self.events.append(dict(event='finish',job_id=component,status='complete',result=result))
        for component in ('N0','N1','N2'):
            neighbor_rows=[dict(reference=c,status='complete',neighbors=[other for other in TRAINING_CAMERAS if other!=c][:3]) for c in TRAINING_CAMERAS]
            result=record(component,dict(status='complete',component=component,records=neighbor_rows,inputs=bindings['inputs']))
            bindings[component]=result;self.events.append(dict(event='finish',job_id=component,status='complete',result=result))
        scale=record('scale',dict(status='passed',scale=1.7))
        for phase,frame in [('fit',100),('check',175)]:
            result=record('D4-'+phase,dict(status='complete',component='D4',scale=scale,
                rows=[dict(identity=dict(branch='depth',camera=c,frame=frame,pair_start=None)) for c in TRAINING_CAMERAS]))
            bindings['D4_'+phase]=result;self.events.append(dict(event='finish',job_id='D4-'+phase,status='complete',result=result))
        self.request=dict(schema='plan067-final-render-request/v1',record_kind='fixture',mode='REVIEW',id='qf-001',bindings=bindings,
            compositions=copy.deepcopy(COMPOSITIONS),seed=0,iterations=5000,preset='default_keyframe',
            preset_source_sha256='fc3e4320da73a470d0a16bcb5803f84d1bda5bdeafb000fcc39e022fbcfaaeb4',
            geometry=dict(keyframes=list(KEYFRAMES),samples_per_edge=5000,neighbors_per_reference=3),
            render=dict(cameras=[0,10,20,30],frames=list(range(50)),fps=25,resolution=[960,540]),
            artifact_bytes_limit=50*2**30,device_bytes_limit=22*2**30,cpu_workers_limit=8,
            initializer_contract=dict(schema='plan067-final-render-initializer/v1',velocity_units='normalized-scene/normalized-time',
                time_formula='frame/50',normalization=dict(translate=[0,0,0],radius=1.0)),
            allocations=allocation_specs('qf-001'))
        self.storage=dict(artifact_bytes=0,download_bytes=0,free_disk_bytes=100*2**30)
    def tearDown(self):self.temp.cleanup()
    def test_review_admission_is_usable_but_never_claims_execution_viable(self):
        result=admit_review(self.request,self.ledger,self.storage)
        self.assertFalse(result.execution_authorized)
        self.assertEqual(result.coverage_edges_per_arm,810)
        self.assertEqual(result.gpu_seconds,49500)
        self.assertEqual(result.cpu_seconds,5400)
        self.assertIn('adapter',result.blockers[0])
    def test_fresh_identity_isolation_fixed_composition_and_equal_endpoint(self):
        for change in (
            lambda r:r['compositions']['QF-M1'].update(depth='D1'),
            lambda r:r.update(iterations=4999),
            lambda r:r['allocations'][1].update(id=r['allocations'][0]['id']),
            lambda r:r['render'].update(frames=list(range(49))),
            lambda r:r.update(mode='DO'),
        ):
            request=copy.deepcopy(self.request);change(request)
            with self.assertRaises(ValueError):admit_review(request,self.ledger,self.storage)
        self.events.append(dict(event='account',job_id=self.request['allocations'][0]['id'],status='blocked'))
        with self.assertRaisesRegex(ValueError,'consumed'):admit_review(self.request,self.ledger,self.storage)
    def test_missing_coverage_and_changed_native_geometry_rejected(self):
        rows=[dict(identity=self.identity(TRAINING_CAMERAS[0],0,0),source_rgb_sha256='other',K=[[1]],grid='fixture')]
        missing=self.record('missing-S2',dict(status='complete',component='S2',rows=rows))
        self.request['bindings']['S2']=missing;self.events.append(dict(event='finish',job_id='S2',status='complete',result=missing))
        with self.assertRaisesRegex(ValueError,'coverage|input'):admit_review(self.request,self.ledger,self.storage)
    def test_budget_and_active_job_gates_reject(self):
        self.ledger.totals=lambda events:{r:dict(elapsed_seconds=90000 if r=='gpu' else 0,reserved_seconds=0) for r in ('gpu','cpu','setup')}
        with self.assertRaisesRegex(ValueError,'GPU'):admit_review(self.request,self.ledger,self.storage)
        self.ledger.totals=lambda events:{r:dict(elapsed_seconds=0,reserved_seconds=0) for r in ('gpu','cpu','setup')}
        self.events.append(dict(event='reserve',job_id='other'))
        with self.assertRaisesRegex(ValueError,'active'):admit_review(self.request,self.ledger,self.storage)
    def test_arrays_reuse_native_validation_and_bind_arm_units_normalization(self):
        import numpy as np
        arrays=dict(positions=np.zeros((2,3),np.float32),colors=np.zeros((2,3),np.float32),
            velocities=np.zeros((2,3),np.float32),times=np.zeros((2,1),np.float32),durations=np.full((2,1),.2,np.float32),
            region=np.zeros(2,np.int32),velocity_valid=np.zeros(2,np.bool_))
        receipt=dict(self.request['initializer_contract'],arm='QF-B',composition=self.request['compositions']['QF-B'],
            arrays_sha256=initializer_arrays_hash(arrays),scene_manifest=self.request['bindings']['scene_manifest'],
            prerequisites={name:self.request['bindings'][name] for name in ('S2','D4_fit','D4_check','M0','N0')})
        self.assertEqual(validate_initializer(self.request,'QF-B',receipt,arrays)['point_count'],2)
        arrays['positions'][0,0]=np.nan
        with self.assertRaises(ValueError):validate_initializer(self.request,'QF-B',receipt,arrays)
        arrays['positions']=np.zeros((3,3),np.float32)
        with self.assertRaises(ValueError):validate_initializer(self.request,'QF-B',receipt,arrays)
    def test_initializer_array_hash_and_isolation_reject_substitution(self):
        import numpy as np
        arrays=dict(positions=np.zeros((2,3),np.float32),colors=np.zeros((2,3),np.float32),
            velocities=np.zeros((2,3),np.float32),times=np.zeros((2,1),np.float32),durations=np.full((2,1),.2,np.float32),
            region=np.zeros(2,np.int32),velocity_valid=np.zeros(2,np.bool_))
        receipt=dict(self.request['initializer_contract'],arm='QF-B',composition=self.request['compositions']['QF-B'],
            arrays_sha256=initializer_arrays_hash(arrays),scene_manifest=self.request['bindings']['scene_manifest'],
            prerequisites={name:self.request['bindings'][name] for name in ('S2','D4_fit','D4_check','M0','N0')})
        arrays['positions'][0,0]=1
        with self.assertRaisesRegex(ValueError,'arrays differ'):validate_initializer(self.request,'QF-B',receipt,arrays)
        with self.assertRaisesRegex(ValueError,'isolation'):validate_initializer(self.request,'QF-M1',receipt,arrays)
    def test_neighbor_membership_and_component_substitution_reject(self):
        neighbors=self.record('bad-N1',dict(status='complete',component='N1',inputs=self.request['bindings']['inputs'],
            records=[dict(reference=c,status='complete',neighbors=[0,2,3]) for c in TRAINING_CAMERAS]))
        self.request['bindings']['N1']=neighbors;self.events.append(dict(event='finish',job_id='N1',status='complete',result=neighbors))
        with self.assertRaisesRegex(ValueError,'neighbor membership'):admit_review(self.request,self.ledger,self.storage)
        self.request['bindings']['N1']=self.request['bindings']['N0']
        # A substituted N0 result cannot become N1 just by relabeling the binding.
        with self.assertRaisesRegex(ValueError,'N1 prerequisite'):admit_review(self.request,self.ledger,self.storage)
    def test_storage_resource_limits_and_nonfinite_worker_deadline_reject(self):
        self.storage['artifact_bytes']=101*2**30
        with self.assertRaisesRegex(ValueError,'artifact cumulative'):admit_review(self.request,self.ledger,self.storage)
        self.storage['artifact_bytes']=0;self.storage['free_disk_bytes']=49*2**30
        with self.assertRaisesRegex(ValueError,'free disk'):admit_review(self.request,self.ledger,self.storage)
        self.storage['free_disk_bytes']=100*2**30;self.request['device_bytes_limit']=23*2**30
        with self.assertRaisesRegex(ValueError,'device_bytes'):admit_review(self.request,self.ledger,self.storage)
        self.request['device_bytes_limit']=22*2**30
        result=dict(schema='plan067-final-render-worker-result/v1',record_kind='fixture',status='blocked',arm='QF-B',
            phase='train',allocation_id='qf-001/QF-B/train',elapsed_seconds=float('inf'),
            request_sha256=object_hash(self.request),reason='fixture')
        with self.assertRaisesRegex(ValueError,'finite deadline'):validate_worker_result(self.request,'QF-B','train',result)
    def test_actual_scope_rejects_rewritten_choice_eligibility_and_proposal_before_admission(self):
        from vipe_benchmark.final_render_contract import validate_scope_bindings
        bindings=dict(self.request['bindings'])
        names={
            'proposal':'docs/specs/plan031-execution/qualitative-final-render-review-proposal-001.md',
            'segmentation_decision':'docs/research/vipe-alternatives/plan067-execution/human-review-001/segmentation-decision.json',
            'depth_decision':'docs/research/vipe-alternatives/plan067-execution/human-depth-review-001/depth-decision.json',
        }
        for name,path in names.items():bindings[name]=file_record(ROOT/path)
        self.assertEqual(validate_scope_bindings(bindings)['scope'],'proposal-001')
        # These copies are explicit mutation fixtures. They never stand in for
        # performed human review or actual coverage/qualification.
        from vipe_benchmark.files import read_json
        for name,mutation in (
            ('segmentation_decision',lambda value:value.update(human_choice={'candidate_ids':['S2'],'reason':'rewritten'})),
            ('depth_decision',lambda value:value['engineering_eligibility']['D4'].update(reason='rewritten eligibility')),
        ):
            altered=read_json(bindings[name]['path']);mutation(altered)
            changed=dict(bindings);changed[name]=self.record('altered-'+name,altered)
            with self.assertRaisesRegex(ValueError,'frozen proposal-001'):validate_scope_bindings(changed)
            actual=dict(self.request,record_kind='actual',bindings=changed)
            with self.assertRaisesRegex(ValueError,'frozen proposal-001'):admit_review(actual,self.ledger,self.storage)
        changed=dict(bindings);path=self.root/'changed-proposal.md';path.write_text('Changed proposal scope')
        changed['proposal']=file_record(path)
        with self.assertRaisesRegex(ValueError,'frozen proposal-001'):validate_scope_bindings(changed)
        with self.assertRaisesRegex(ValueError,'frozen proposal-001'):
            admit_review(dict(self.request,record_kind='actual',bindings=changed),self.ledger,self.storage)
        # Identical bytes at another path also cannot replace the frozen scope.
        path=self.root/'relocated-proposal.md';path.write_bytes(Path(bindings['proposal']['path']).read_bytes())
        changed['proposal']=file_record(path)
        with self.assertRaisesRegex(ValueError,'frozen proposal-001'):validate_scope_bindings(changed)
    def test_actual_result_cannot_be_claimed_and_training_iterations_must_match(self):
        result=dict(schema='plan067-final-render-worker-result/v1',record_kind='fixture',status='complete',arm='QF-B',
            phase='train',allocation_id='qf-001/QF-B/train',elapsed_seconds=1,completed_iterations=5000,
            request_sha256=object_hash(self.request),artifacts=[self.request['bindings']['source']])
        self.assertEqual(validate_worker_result(self.request,'QF-B','train',result)['status'],'complete')
        result['completed_iterations']=4999
        with self.assertRaisesRegex(ValueError,'iterations'):validate_worker_result(self.request,'QF-B','train',result)
        result['completed_iterations']=5000;result['record_kind']='actual'
        with self.assertRaisesRegex(ValueError,'adapter'):validate_worker_result(self.request,'QF-B','train',result)
