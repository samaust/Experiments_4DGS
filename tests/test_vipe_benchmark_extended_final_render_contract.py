"""Prospective extended depth choice at the public downstream REVIEW seam."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.extended_final_render_contract import compositions


class ExtendedContractTests(unittest.TestCase):
    def test_metric_depth_choice_is_fixed_across_five_isolated_arms(self):
        expected = {
            'QF-B': {'segmentation': 'S2', 'depth': 'D5', 'motion': 'M0', 'neighbors': 'N0'},
            'QF-M1': {'segmentation': 'S2', 'depth': 'D5', 'motion': 'M1', 'neighbors': 'N0'},
            'QF-M2': {'segmentation': 'S2', 'depth': 'D5', 'motion': 'M2', 'neighbors': 'N0'},
            'QF-N1': {'segmentation': 'S2', 'depth': 'D5', 'motion': 'M0', 'neighbors': 'N1'},
            'QF-N2': {'segmentation': 'S2', 'depth': 'D5', 'motion': 'M0', 'neighbors': 'N2'},
        }
        self.assertEqual(compositions('D5'), expected)
        for candidate in ('D4', 'D9', 'D11'):
            with self.assertRaises(ValueError):
                compositions(candidate)

    def test_do_cannot_be_requested_by_a_review_contract(self):
        from vipe_benchmark.extended_final_render_contract import parse_request
        with self.assertRaisesRegex(ValueError, 'REVIEW'):
            parse_request({'schema': 'plan069-final-render-request/v1', 'mode': 'DO', 'record_kind': 'fixture'})


class AdmissionTests(unittest.TestCase):
    def setUp(self):
        import copy
        import importlib
        from vipe_benchmark.files import file_record, read_json, object_hash
        from vipe_benchmark.final_render_contract import allocation_specs
        from vipe_benchmark import depth_review
        self.base = importlib.import_module('test_vipe_benchmark_final_render_contract').ContractTests()
        self.base.setUp()
        self.addCleanup(self.base.tearDown)
        self.review = importlib.import_module('test_vipe_benchmark_depth_review').DepthReviewTests()
        self.review.setUp()
        self.addCleanup(self.review.doCleanups)
        self.record = self.base.record
        self.read = lambda record: read_json(record['path'])
        self.request = copy.deepcopy(self.base.request)
        self.request.update(schema='plan069-final-render-request/v1', depth_candidate='D5',
                            compositions=compositions('D5'), id='extended-001', allocations=allocation_specs('extended-001'))
        self.request['initializer_contract'].update(schema='plan069-final-render-initializer/v1',
            normalization=dict(transform=[[0,-2,0,1],[2,0,0,2],[0,0,2,3],[0,0,0,1]]))
        bindings = self.request['bindings']
        inputs = self.read(bindings['inputs'])
        normalization = dict(self.request['initializer_contract']['normalization'],scene_scale=10.)
        for row in inputs['rgb']:
            row['K'] = [[2,0,1],[0,2,1],[0,0,1]]
        for name in ('S2','M0','M1','M2'):
            native = self.read(bindings[name])
            for row in native['rows']:
                row['K'] = [[2,0,1],[0,2,1],[0,0,1]]
            bindings[name] = self.record(name+'-calibrated',native)
            self.base.events.append(dict(event='finish',job_id=name+'-calibrated',status='complete',result=bindings[name]))
        inputs.update(reference_geometry=dict(scale=1.7,normalization=normalization,
            freeze=self.record('historical-freeze',dict(scale=1.7)),
            normalization_source=self.record('historical-normalization',dict(normalization=normalization))),
            map=self.record('accepted-map',{}))
        bindings['inputs'] = self.record('extended-inputs',inputs)
        self.review.inputs = bindings['inputs']
        context = self.review.record(dict(inputs=bindings['inputs']))
        for candidate, slot in self.review.slots.items():
            generation = self.read(slot['evidence']['generation'])
            fit = dict(self.read(generation['scales']['fit']), scale=1.7,
                provenance=dict(inputs=bindings['inputs'],component=candidate,component_sha256='1'*64),
                estimator_sha256='2'*64,scale_protocol_sha256='3'*64)
            fit_record = self.review.record(fit)
            check_record = self.review.record(dict(fit,role='selection',frozen_fit=fit_record))
            generation.update(context=context,inputs=bindings['inputs'],scales=dict(fit=fit_record,check=check_record))
            slot['evidence'].update(generation=self.review.record(generation),scale=check_record)
            if candidate == 'D2':
                slot['evidence'].update(historical_fit=self.review.record({'scale':fit_record}),
                    historical_check=self.review.record({'scale':check_record}))
        package = self.read(self.review.package)
        package['bindings'].update(inputs=bindings['inputs'],context=context,
            depth_aggregate_request=self.review.record(dict(candidates=self.review.slots)))
        self.review.package = self.review.record(package)
        self.review.form['package'] = self.review.package
        self.review.freeze()
        bindings['depth_decision'] = file_record(self.review.root/'decision.json')
        selected = self.read(self.review.slots['D5']['evidence']['generation'])['scales']
        bindings['D_fit'],bindings['D_check'] = selected['fit'],selected['check']
        del bindings['D4_fit'],bindings['D4_check']
        for name in ('N0','N1','N2'):
            bindings[name] = self.record(name+'-extended',dict(self.read(bindings[name]),inputs=bindings['inputs']))
            self.base.events.append(dict(event='finish',job_id=name+'-extended',status='complete',result=bindings[name]))
        self.build_scene(inputs)
        self.rebind_proposal()
        self.ledger,self.storage = self.base.ledger,self.base.storage

    def build_scene(self, inputs):
        from sync_timing import common_training_keys
        from vipe_benchmark.final_render_contract import TRAINING_CAMERAS
        ids = [str(c) for c in range(34)]
        timing = dict(schema='camera-timing/v1',units='seconds',
            convention='corrected_timestamp_seconds = source_timestamp_seconds - offset_seconds',
            camera_ids=ids,reference_camera='1',offset_seconds={c:0. for c in ids},
            uncertainty_seconds={c:0. for c in ids},source_support_seconds={c:[0.,2.] for c in ids},
            coverage=dict(camera_ids=ids),source_window_seconds=[0.,2.],normalization=dict(origin_seconds=0.,duration_seconds=2.),
            kind='operational-assumption',provenance=dict(fixture=True))
        keys,excluded = common_training_keys([(c,f,f/25) for c in ids for f in range(50)],[timing],['0','10','20','30'])
        cameras = [dict(id=c,split='train' if int(c) in TRAINING_CAMERAS else 'test',width=960,height=540,
            K=[[2,0,1.5],[0,2,1.5],[0,0,1]],world_to_camera_R=[[1,0,0],[0,1,0],[0,0,1]],
            world_to_camera_T=[0,0,0],center=[0,0,0],
            frames=[dict(frame_id=f,normalized_time=f/50,sha256=f'{c}-{f}') for f in range(50)]) for c in ids]
        manifest = dict(schema='basketball-processed/v1',status='prepared',source_fps=25,timing=timing,
            comparison_timings=[timing],time=timing['normalization'],heldout_camera_ids=['0','10','20','30'],
            temporal_holdout_seconds=[.8,1.],training_keys=[list(k) for k in keys],training_exclusions=excluded,cameras=cameras,
            freeze_sha256=inputs['reference_geometry']['freeze']['sha256'])
        self.request['bindings']['scene_manifest'] = self.record('extended-manifest',manifest)
        scene = dict(schema='plan069-final-render-scene/v1',status='complete',depth_component='D5',scale=1.7,
            scale_evidence=dict(fit=self.request['bindings']['D_fit'],check=self.request['bindings']['D_check']),
            normalization=self.request['initializer_contract']['normalization']['transform'],
            historical_reference=inputs['reference_geometry'],map=inputs['map'],
            units=dict(normalized_time_seconds=2.,frame_seconds=.04,velocity='metres/second -> normalization linear map * 2 seconds'),
            cameras={str(c):dict(K=[[2,0,1],[0,2,1],[0,0,1]],R=[[1,0,0],[0,1,0],[0,0,1]],t=[0,0,0],center=[0,0,0]) for c in TRAINING_CAMERAS})
        self.request['bindings']['scene_freeze'] = self.record('extended-scene',scene)

    def rebind_proposal(self):
        from vipe_benchmark.files import object_hash
        bindings = self.request['bindings']
        proposal = dict(schema='plan069-final-render-review-proposal/v1',record_kind='fixture',mode='REVIEW',depth_candidate=self.request['depth_candidate'],
            bindings={k:v for k,v in bindings.items() if k!='proposal'},
            settings_sha256=object_hash({k:v for k,v in self.request.items() if k!='bindings'}))
        self.request['bindings']['proposal'] = self.record('proposal-'+str(len(list(self.base.root.glob('proposal-*')))),proposal)

    def test_imported_choice_admits_only_a_prospective_review(self):
        from vipe_benchmark.extended_final_render_contract import admit_review
        before = self.ledger.events()
        result = admit_review(self.request,self.ledger,self.storage)
        self.assertEqual(result.coverage_edges_per_arm,810)
        self.assertEqual((result.gpu_seconds,result.cpu_seconds),(49500,5400))
        self.assertFalse(result.execution_authorized)
        self.assertEqual(self.ledger.events(),before)

    def test_rejects_mixed_depth_historical_choice_and_unequal_endpoint(self):
        import copy
        from vipe_benchmark.extended_final_render_contract import admit_review
        for change in (
            lambda r:r['compositions']['QF-M1'].update(depth='D6'),
            lambda r:r.update(depth_candidate='D4',compositions={a:dict(c,depth='D4') for a,c in r['compositions'].items()}),
            lambda r:r.update(iterations=4999),
            lambda r:r['render'].update(frames=list(range(49))),
            lambda r:r.update(mode='DO'),
        ):
            with self.subTest(change=change):
                request = copy.deepcopy(self.request)
                change(request)
                with self.assertRaises(ValueError):
                    admit_review(request,self.ledger,self.storage)

    def test_rebinding_proposal_cannot_substitute_decision_inputs_or_fit(self):
        import copy
        from vipe_benchmark.extended_final_render_contract import admit_review
        original = copy.deepcopy(self.request)
        for name in ('inputs','D_fit','D_check'):
            self.request = copy.deepcopy(original)
            value = self.read(self.request['bindings'][name])
            # Even identical content at a new path is a different bound record.
            self.request['bindings'][name] = self.record('substituted-'+name,value)
            self.rebind_proposal()
            with self.assertRaisesRegex(ValueError,'manifest substitution'):
                admit_review(self.request,self.ledger,self.storage)

    def test_rejects_missing_native_coverage_and_substituted_component(self):
        from vipe_benchmark.extended_final_render_contract import admit_review
        missing = dict(self.read(self.request['bindings']['M1']))
        missing['rows'] = missing['rows'][:-1]
        self.request['bindings']['M1'] = self.record('missing-motion',missing)
        self.base.events.append(dict(event='finish',job_id='missing-motion',status='complete',result=self.request['bindings']['M1']))
        self.rebind_proposal()
        with self.assertRaisesRegex(ValueError,'coverage'):
            admit_review(self.request,self.ledger,self.storage)
        self.request['bindings']['M1'] = self.request['bindings']['M0']
        self.rebind_proposal()
        with self.assertRaisesRegex(ValueError,'M1'):
            admit_review(self.request,self.ledger,self.storage)

    def test_rejects_changed_camera_time_transform_and_union(self):
        import copy
        from vipe_benchmark.extended_final_render_contract import admit_review
        original = copy.deepcopy(self.request)
        for name, mutation in (
            ('scene_freeze',lambda s:s['cameras']['1']['center'].__setitem__(0,1)),
            ('scene_freeze',lambda s:s['units'].update(normalized_time_seconds=3)),
            ('scene_freeze',lambda s:s['normalization'][0].__setitem__(3,9)),
            ('scene_manifest',lambda s:s['training_keys'].pop()),
        ):
            self.request = copy.deepcopy(original)
            scene = self.read(self.request['bindings'][name])
            mutation(scene)
            self.request['bindings'][name] = self.record('changed-scene-'+str(len(list(self.base.root.glob('changed-scene-*')))),scene)
            self.rebind_proposal()
            with self.assertRaises(ValueError):
                admit_review(self.request,self.ledger,self.storage)

    def test_rejects_changed_qualification_and_absent_evidence(self):
        from vipe_benchmark.extended_final_render_contract import admit_review
        self.request['bindings']['qualification'] = self.record('failed-qualification',dict(status='failed',record_kind='fixture'))
        self.rebind_proposal()
        with self.assertRaisesRegex(ValueError,'qualification'):
            admit_review(self.request,self.ledger,self.storage)
        del self.request['bindings']['runtime']
        with self.assertRaisesRegex(ValueError,'bindings'):
            admit_review(self.request,self.ledger,self.storage)

    def test_rejects_active_consumed_and_exhausted_allocations(self):
        from vipe_benchmark.extended_final_render_contract import admit_review
        self.base.events.append(dict(event='reserve',job_id='another',status='reserved'))
        with self.assertRaisesRegex(ValueError,'active'):
            admit_review(self.request,self.ledger,self.storage)
        self.base.events.pop()
        self.base.events.append(dict(event='account',job_id=self.request['allocations'][0]['id'],status='blocked'))
        with self.assertRaisesRegex(ValueError,'consumed'):
            admit_review(self.request,self.ledger,self.storage)
        self.base.events.pop()
        self.ledger.totals=lambda events:{r:dict(elapsed_seconds=90000 if r=='gpu' else 0,reserved_seconds=0) for r in ('gpu','cpu','setup')}
        with self.assertRaisesRegex(ValueError,'GPU'):
            admit_review(self.request,self.ledger,self.storage)

    def test_fixture_cannot_become_actual_human_authority(self):
        import copy
        from vipe_benchmark.extended_final_render_contract import admit_review
        actual = dict(copy.deepcopy(self.request),record_kind='actual')
        with self.assertRaises(ValueError):
            admit_review(actual,self.ledger,self.storage)

    def test_initializer_keeps_selected_depth_provenance_and_arrays(self):
        import numpy as np
        from vipe_benchmark.extended_final_render_contract import validate_initializer
        from vipe_benchmark.final_render_contract import initializer_arrays_hash
        arrays=dict(positions=np.array([[1.,2.,3.]],np.float32),colors=np.zeros((1,3),np.float32),
            velocities=np.zeros((1,3),np.float32),times=np.zeros((1,1),np.float32),durations=np.full((1,1),.2,np.float32),
            region=np.zeros(1,np.int32),velocity_valid=np.zeros(1,np.bool_))
        names=('S2','D_fit','D_check','depth_decision','M0','N0')
        receipt=dict(self.request['initializer_contract'],arm='QF-B',composition=self.request['compositions']['QF-B'],
            arrays_sha256=initializer_arrays_hash(arrays),scene_manifest=self.request['bindings']['scene_manifest'],
            prerequisites={name:self.request['bindings'][name] for name in names})
        checked=validate_initializer(self.request,'QF-B',receipt,arrays)
        self.assertEqual(checked['point_count'],1)
        self.assertFalse(checked['native_adapter_qualified'])
        self.assertFalse(checked['execution_authorized'])
        with self.assertRaisesRegex(ValueError,'isolation'):
            validate_initializer(self.request,'QF-M1',receipt,arrays)
        arrays['positions'][0,0]=9
        with self.assertRaisesRegex(ValueError,'arrays changed'):
            validate_initializer(self.request,'QF-B',receipt,arrays)

    def test_unclear_real_imported_decision_does_not_admit_a_fallback(self):
        import copy
        from vipe_benchmark import depth_review
        from vipe_benchmark.files import file_record
        from vipe_benchmark.extended_final_render_contract import admit_review
        form = copy.deepcopy(self.review.form)
        form['metric_choice'] = dict(outcome='unclear',candidate_ids=[],reason='Need additional judgment.',examples=[])
        imported=depth_review.import_review(self.review.package,self.review.record(form),self.review.root/'unclear-review.json',actual=False)
        depth_review.freeze_decision(imported,self.review.root/'unclear-decision.json',actual=False)
        self.request['bindings']['depth_decision']=file_record(self.review.root/'unclear-decision.json')
        self.rebind_proposal()
        with self.assertRaisesRegex(ValueError,'ready'):
            admit_review(self.request,self.ledger,self.storage)

    def test_hot_path_parse_trusts_pinned_decision_but_admission_rederives_it(self):
        from vipe_benchmark.extended_final_render_contract import admit_review, parse_request
        from vipe_benchmark.files import file_record, write_json
        forged = dict(self.read(self.request['bindings']['depth_decision']), forged=True)
        write_json(self.review.root/'forged-decision.json', forged)
        self.request['bindings']['depth_decision'] = file_record(self.review.root/'forged-decision.json')
        self.rebind_proposal()
        self.assertEqual(parse_request(self.request)['id'], self.request['id'])
        with self.assertRaisesRegex(ValueError, 'decision contents changed'):
            admit_review(self.request,self.ledger,self.storage)

    def test_scene_camera_must_match_native_accepted_input_calibration(self):
        from vipe_benchmark.extended_final_render_contract import admit_review
        inputs=self.read(self.request['bindings']['inputs'])
        inputs['rgb'][0]['K']=[[1]]
        # Modify content in place to keep the decision identity stale: public
        # validation must reject the bound hash rather than accept replacement.
        from pathlib import Path
        import json
        Path(self.request['bindings']['inputs']['path']).write_text(json.dumps(inputs))
        with self.assertRaises(ValueError):
            admit_review(self.request,self.ledger,self.storage)

    def test_manifest_frame_substitution_cannot_change_native_accepted_rgb(self):
        from vipe_benchmark.extended_final_render_contract import admit_review
        manifest=self.read(self.request['bindings']['scene_manifest'])
        manifest['cameras'][1]['frames'][0]['sha256']='other-rgb'
        self.request['bindings']['scene_manifest']=self.record('changed-manifest-rgb',manifest)
        self.rebind_proposal()
        with self.assertRaisesRegex(ValueError,'input geometry'):
            admit_review(self.request,self.ledger,self.storage)

    def test_all_six_eligible_metric_candidates_use_the_real_import_seam(self):
        import copy
        from vipe_benchmark import depth_review
        from vipe_benchmark.files import file_record
        from vipe_benchmark.extended_final_render_contract import admit_review
        for candidate in ('D2','D5','D6','D7','D8','D10'):
            with self.subTest(candidate=candidate):
                form=copy.deepcopy(self.review.form)
                form['metric_choice']=dict(outcome='selected',candidate_ids=[candidate],
                    reason='Independent CPU fixture selection.',examples=[self.review.example(candidate)])
                imported=depth_review.import_review(self.review.package,self.review.record(form),self.review.root/(candidate+'-review.json'),actual=False)
                depth_review.freeze_decision(imported,self.review.root/(candidate+'-decision.json'),actual=False)
                scales=self.read(self.review.slots[candidate]['evidence']['generation'])['scales']
                self.request.update(depth_candidate=candidate,compositions=compositions(candidate))
                self.request['bindings'].update(depth_decision=file_record(self.review.root/(candidate+'-decision.json')),
                    D_fit=scales['fit'],D_check=scales['check'])
                scene=self.read(self.request['bindings']['scene_freeze'])
                scene.update(depth_component=candidate,scale_evidence=dict(fit=scales['fit'],check=scales['check']))
                self.request['bindings']['scene_freeze']=self.record(candidate+'-scene',scene)
                self.rebind_proposal()
                result=admit_review(self.request,self.ledger,self.storage)
                self.assertEqual(result.coverage_edges_per_arm,810)
                self.assertFalse(result.execution_authorized)

    def authorize_amended_budget(self):
        from vipe_benchmark.files import object_hash
        baseline=self.request['bindings']['config']
        amendment=self.record('budget-amendment',dict(schema='plan069-depth-cap-amendment/v1',status='REVIEW',
            historical_configuration={key:baseline[key] for key in ('sha256','bytes')},
            new_download_gib_limit=110,new_artifact_disk_gib_limit=210))
        authorization=self.record('budget-authorization',dict(schema='plan069-depth-user-authorization/v1',status='DO',
            record_kind='fixture',cap_amendment=amendment,
            cap_approval=dict(schema='plan069-depth-cap-approval/v1',status='approved',amendment_sha256=object_hash(self.read(amendment)))))
        self.request['budget_amendment']=dict(amendment=amendment,authorization=authorization)
        self.ledger.config=dict(self.ledger.config,new_download_gib_limit=110,new_artifact_disk_gib_limit=210)
        self.rebind_proposal()

    def test_approved_budget_amendment_preserves_original_prerequisite_configuration(self):
        from vipe_benchmark.extended_final_render_contract import admit_review
        original=self.request['bindings']['config']
        self.authorize_amended_budget()
        self.storage.update(artifact_bytes=151*2**30,download_bytes=70*2**30)
        result=admit_review(self.request,self.ledger,self.storage)
        self.assertFalse(result.execution_authorized)
        self.assertEqual(self.request['bindings']['config'],original)
        self.assertEqual(self.read(original)['new_artifact_disk_gib_limit'],150)

    def test_amended_ledger_requires_authorization_and_rejects_other_configuration_drift(self):
        from vipe_benchmark.extended_final_render_contract import admit_review
        self.ledger.config=dict(self.ledger.config,new_download_gib_limit=110,new_artifact_disk_gib_limit=210)
        with self.assertRaisesRegex(ValueError,'amendment required'):
            admit_review(self.request,self.ledger,self.storage)
        self.authorize_amended_budget()
        self.ledger.config['gpu_total_seconds_limit'] += 1
        with self.assertRaisesRegex(ValueError,'outside exact'):
            admit_review(self.request,self.ledger,self.storage)
        self.ledger.config['gpu_total_seconds_limit'] -= 1
        del self.request['budget_amendment']['authorization']
        self.rebind_proposal()
        with self.assertRaisesRegex(ValueError,'authorization records'):
            admit_review(self.request,self.ledger,self.storage)

    def test_changed_budget_amendment_and_approval_are_rejected(self):
        import copy
        from vipe_benchmark.extended_final_render_contract import admit_review
        self.authorize_amended_budget()
        original=copy.deepcopy(self.request)
        for name, change in (
            ('amendment',lambda a:a.update(new_download_gib_limit=111)),
            ('amendment',lambda a:a['historical_configuration'].update(bytes=1)),
            ('authorization',lambda a:a.update(status='REVIEW')),
            ('authorization',lambda a:a['cap_approval'].update(amendment_sha256='0'*64)),
            ('authorization',lambda a:a.update(record_kind='human')),
        ):
            self.request=copy.deepcopy(original)
            document=self.read(self.request['budget_amendment'][name])
            change(document)
            self.request['budget_amendment'][name]=self.record('altered-budget-'+str(len(list(self.base.root.glob('altered-budget-*')))),document)
            self.rebind_proposal()
            with self.assertRaises(ValueError):
                admit_review(self.request,self.ledger,self.storage)

    def extend_artifact_cap(self, **changes):
        from vipe_benchmark.files import object_hash
        self.authorize_amended_budget()
        bound=self.request['budget_amendment']
        amendment=dict(schema='plan069-final-render-cap-amendment/v1',status='REVIEW',base_amendment=bound['amendment'],
            new_download_gib_limit=110,new_artifact_disk_gib_limit=260)
        amendment.update(changes)
        record=self.record('artifact-extension-'+str(len(list(self.base.root.glob('artifact-extension-*')))),amendment)
        authorization=self.record('artifact-extension-authorization-'+str(len(list(self.base.root.glob('artifact-extension-authorization-*')))),
            dict(schema='plan069-final-render-cap-authorization/v1',status='DO',record_kind='fixture',amendment=record,
                 approval=dict(status='approved',amendment_sha256=object_hash(amendment))))
        bound['artifact_extension']=dict(amendment=record,authorization=authorization)
        self.ledger.config=dict(self.ledger.config,new_artifact_disk_gib_limit=260)
        self.rebind_proposal()

    def test_approved_artifact_extension_admits_against_the_260_gib_cap(self):
        from vipe_benchmark.extended_final_render_contract import admit_review
        self.extend_artifact_cap()
        storage=dict(self.storage,artifact_bytes=200*2**30)
        self.assertFalse(admit_review(self.request,self.ledger,storage).execution_authorized)
        with self.assertRaisesRegex(ValueError,'artifact cumulative ceiling exhausted'):
            admit_review(self.request,self.ledger,dict(self.storage,artifact_bytes=215*2**30))

    def test_artifact_extension_must_chain_the_exact_base_amendment_and_cap(self):
        from vipe_benchmark.extended_final_render_contract import admit_review
        for changes in (dict(new_artifact_disk_gib_limit=300),dict(new_download_gib_limit=120),dict(base_amendment=None)):
            with self.subTest(changes=changes):
                self.setUp()
                self.extend_artifact_cap(**changes)
                with self.assertRaisesRegex(ValueError,'artifact extension'):
                    admit_review(self.request,self.ledger,self.storage)
        self.setUp()
        self.authorize_amended_budget()
        self.ledger.config=dict(self.ledger.config,new_artifact_disk_gib_limit=260)
        with self.assertRaisesRegex(ValueError,'approved budget caps'):
            admit_review(self.request,self.ledger,self.storage)

    def test_actual_artifact_extension_requires_the_recorded_user_authorization(self):
        from vipe_benchmark import extended_final_render_contract as contract
        self.extend_artifact_cap()
        actual=dict(self.request,record_kind='actual')
        with self.assertRaisesRegex(ValueError,'artifact extension is not the recorded user authorization'):
            contract._artifact_extension(actual,actual['budget_amendment'])

    def test_actual_budget_seam_accepts_only_the_recorded_user_cap_authorization(self):
        from vipe_benchmark.extended_final_render_contract import validate_budget_configuration
        from vipe_benchmark.depth_admission import BENCHMARK
        from vipe_benchmark.files import file_record
        authorization=file_record(Path(__file__).resolve().parents[1]/'docs/research/vipe-alternatives/plan031-execution/depth-approval-001.json')
        amendment=self.read(authorization)['cap_amendment']
        baseline=file_record(BENCHMARK)
        value=dict(record_kind='actual',bindings={'config':baseline},budget_amendment=dict(amendment=amendment,authorization=authorization))
        amended=dict(self.read(baseline),new_download_gib_limit=110,new_artifact_disk_gib_limit=210)
        validate_budget_configuration(value,amended)
        document=self.read(authorization)
        document['authorization_basis']='CPU fixture cannot forge actual user authorization'
        value['budget_amendment']['authorization']=self.record('forged-user-authorization',document)
        with self.assertRaisesRegex(ValueError,'recorded user'):
            validate_budget_configuration(value,amended)

    def extend_long_training(self, gpu=252000, **changes):
        from vipe_benchmark.files import object_hash
        self.extend_artifact_cap()
        bound=self.request['budget_amendment']
        previous=bound['artifact_extension']
        amendment=dict(schema='plan069-final-render-cap-amendment/v2',status='REVIEW',base_amendment=bound['amendment'],
            previous_extension=previous,new_download_gib_limit=110,new_artifact_disk_gib_limit=380,
            new_gpu_total_seconds_limit=gpu)
        amendment.update(changes)
        record=self.record('long-extension-'+str(len(list(self.base.root.glob('long-extension-*')))),amendment)
        authorization=self.record('long-authorization-'+str(len(list(self.base.root.glob('long-authorization-*')))),
            dict(schema='plan069-final-render-cap-authorization/v1',status='DO',record_kind='fixture',amendment=record,
                 approval=dict(status='approved',amendment_sha256=object_hash(amendment))))
        bound['artifact_extension']=dict(amendment=record,authorization=authorization)
        self.ledger.config=dict(self.ledger.config,new_artifact_disk_gib_limit=380,gpu_total_seconds_limit=gpu)
        self.rebind_proposal()

    def long_endpoint(self):
        from vipe_benchmark.final_render_contract import allocation_specs
        self.request.update(iterations=70000,allocations=allocation_specs(self.request['id'],70000))
        self.rebind_proposal()

    def test_long_training_extension_raises_artifact_and_gpu_caps_over_the_v1_chain(self):
        from vipe_benchmark.extended_final_render_contract import admit_review, amended_configuration
        self.extend_long_training();self.long_endpoint()
        self.assertEqual(amended_configuration(self.request),self.ledger.config)
        self.assertFalse(admit_review(self.request,self.ledger,dict(self.storage,artifact_bytes=320*2**30)).execution_authorized)
        with self.assertRaisesRegex(ValueError,'artifact cumulative ceiling exhausted'):
            admit_review(self.request,self.ledger,dict(self.storage,artifact_bytes=340*2**30))

    def test_long_training_extension_rejects_other_caps_unbounded_gpu_and_a_broken_chain(self):
        from vipe_benchmark.extended_final_render_contract import admit_review
        for gpu, changes, message in (
                (252000,dict(new_artifact_disk_gib_limit=400),'artifact extension'),
                (93600,{},'GPU limit raise'),
                (10**6,{},'GPU limit raise'),
                (252000,dict(previous_extension=None),'chain the exact v1')):
            with self.subTest(changes=changes,gpu=gpu):
                self.setUp()
                self.extend_long_training(gpu,**changes);self.long_endpoint()
                with self.assertRaisesRegex(ValueError,message):
                    admit_review(self.request,self.ledger,self.storage)
        self.setUp()
        self.extend_long_training();self.long_endpoint()
        self.ledger.config=dict(self.ledger.config,gpu_total_seconds_limit=252001)
        with self.assertRaisesRegex(ValueError,'outside exact approved budget caps'):
            admit_review(self.request,self.ledger,self.storage)

    def test_long_training_extension_covers_only_the_70k_endpoint(self):
        from vipe_benchmark.extended_final_render_contract import admit_review
        self.extend_long_training()
        with self.assertRaisesRegex(ValueError,'only the 70k'):
            admit_review(self.request,self.ledger,self.storage)

    def test_actual_long_training_extension_requires_its_pinned_user_authorization(self):
        from vipe_benchmark import extended_final_render_contract as contract
        self.extend_long_training();self.long_endpoint()
        actual=dict(self.request,record_kind='actual')
        with self.assertRaisesRegex(ValueError,'not the recorded user authorization'):
            contract._artifact_extension(actual,actual['budget_amendment'])

    def test_seventy_thousand_step_endpoint_scales_only_the_train_ceiling(self):
        from vipe_benchmark.extended_final_render_contract import admit_review
        from vipe_benchmark.final_render_contract import allocation_specs
        self.extend_long_training();self.long_endpoint()
        result=admit_review(self.request,self.ledger,self.storage)
        self.assertEqual((result.gpu_seconds,result.cpu_seconds),(5*(5400+14400+900),5400))
        trains={a['seconds'] for a in self.request['allocations'] if a['phase']=='train'}
        self.assertEqual(trains,{14400})
        for iterations, allocations in ((70000,allocation_specs('extended-001')),(20000,allocation_specs('extended-001'))):
            with self.subTest(iterations=iterations):
                self.request.update(iterations=iterations,allocations=allocations)
                self.rebind_proposal()
                with self.assertRaises(ValueError):
                    admit_review(self.request,self.ledger,self.storage)

    def test_actual_recorded_long_training_authorization_yields_the_approved_caps(self):
        from vipe_benchmark.extended_final_render_contract import amended_configuration
        from vipe_benchmark.depth_admission import BENCHMARK
        from vipe_benchmark.files import file_record
        root=Path(__file__).resolve().parents[1]
        base=self.read(file_record(root/'docs/research/vipe-alternatives/plan031-execution/depth-approval-001.json'))['cap_amendment']
        value=dict(record_kind='actual',iterations=70000,bindings={'config':file_record(BENCHMARK)},budget_amendment=dict(
            amendment=base,authorization=file_record(root/'docs/research/vipe-alternatives/plan031-execution/depth-approval-001.json'),
            artifact_extension=dict(
                amendment=file_record(root/'docs/specs/plan031-execution/final-render-cap-amendment-review-004.json'),
                authorization=file_record(root/'docs/research/vipe-alternatives/plan031-execution/final-render-cap-approval-004.json'))))
        config=amended_configuration(value)
        self.assertEqual((config['new_artifact_disk_gib_limit'],config['gpu_total_seconds_limit'],config['new_download_gib_limit'],config['cpu_prepare_score_report_seconds_limit']),(380,288000,110,66000))

    def test_training_and_lifetime_policies_are_explicit_pairs(self):
        from vipe_benchmark.extended_final_render_contract import admit_review, parse_request
        self.assertNotIn('training_policy', parse_request(self.request))
        self.request.update(training_policy='all-times', lifetime_policy='repaired')
        self.rebind_proposal()
        self.assertFalse(admit_review(self.request,self.ledger,self.storage).execution_authorized)
        for change in (dict(training_policy='holdout',lifetime_policy='repaired'),
                       dict(training_policy='all-times',lifetime_policy='original'),
                       dict(training_policy='everything',lifetime_policy='repaired')):
            with self.subTest(change=change):
                request = dict(self.request,**change)
                with self.assertRaisesRegex(ValueError,'policy'):
                    parse_request(request)
        partial = {k:v for k,v in self.request.items() if k != 'lifetime_policy'}
        with self.assertRaisesRegex(ValueError,'policy'):
            parse_request(partial)

    def test_long_training_extension_may_raise_the_cpu_limit_within_bounds(self):
        from vipe_benchmark.extended_final_render_contract import admit_review, amended_configuration
        self.extend_long_training(288000,new_cpu_prepare_score_report_seconds_limit=66000);self.long_endpoint()
        self.ledger.config=dict(self.ledger.config,cpu_prepare_score_report_seconds_limit=66000)
        self.assertEqual(amended_configuration(self.request)['cpu_prepare_score_report_seconds_limit'],66000)
        self.assertFalse(admit_review(self.request,self.ledger,self.storage).execution_authorized)
        for cpu in (57600,10**6):
            with self.subTest(cpu=cpu):
                self.setUp()
                self.extend_long_training(288000,new_cpu_prepare_score_report_seconds_limit=cpu);self.long_endpoint()
                with self.assertRaisesRegex(ValueError,'CPU limit raise'):
                    admit_review(self.request,self.ledger,self.storage)
