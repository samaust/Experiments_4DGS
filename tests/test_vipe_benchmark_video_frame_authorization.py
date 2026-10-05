"""D10 frame amendment needs exact prior scope, unstarted proof and D9 gate."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from vipe_benchmark.config import ROOT
from vipe_benchmark.files import file_record, read_json, object_hash
from vipe_benchmark.depth_authorization import execution_authorization
from vipe_benchmark.depth_admission import VIDEO_FRAME_PROFILES, local_source_records
from vipe_benchmark.video_environment import FRAME_RECIPE

def write_json(path, value):
    # Deliberately mutable isolated CPU fixture; production records remain immutable.
    Path(path).write_text(json.dumps(value)+'\n')


class FrameAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        # The public seam consumes the committed predecessor's exact bytes.
        prior_source=ROOT/'docs/research/vipe-alternatives/plan031-execution/depth-approval-003.json'
        self.prior_path=self.root/'docs/research/vipe-alternatives/plan031-execution/depth-approval-003.json'
        self.prior_path.parent.mkdir(parents=True);self.prior_path.write_bytes(prior_source.read_bytes())
        prior=read_json(self.prior_path);baseline=read_json(prior['review']['path'])
        self.proposal=copy.deepcopy(next(row for row in baseline['proposals'] if row['candidate']=='D10'))
        self.proposal.update(runtime_recipe=file_record(FRAME_RECIPE),profile_inventory=file_record(VIDEO_FRAME_PROFILES),profile=read_json(VIDEO_FRAME_PROFILES)['profiles']['D10'])
        self.prefix_path=self.root/'prefix.jsonl'
        self.row=dict(event='fixture',sequence=0,previous_sha256=None)
        self.row['event_sha256']=object_hash(self.row)
        self.prefix_path.write_text(json.dumps(self.row)+'\n')
        self.qual_path=self.root/'D9-qualified.json'
        from vipe_benchmark.depth_extension import CONFIG
        config=read_json(CONFIG)['candidates']['D9']; profile=read_json(VIDEO_FRAME_PROFILES)['profiles']['D9']
        stub=self.root/'fixture-bytes';stub.write_bytes(b'CPU fixture only; no model executed')
        shared=dict(candidate='D9',record_kind='actual',status='passed',source_revision=config['code']['revision'],
            source_archive=file_record(stub),source_files=[file_record(stub)],profile=profile,local_sources=local_source_records('D9'),python=file_record(stub),python_executable=str(stub))
        runtime_path=self.root/'runtime.json';write_json(runtime_path,dict(schema='plan069-depth-environment-result/v1',record_kind='actual',status='complete',candidate='D9',python=file_record(stub),python_executable=str(stub),requirement_sources=[file_record(FRAME_RECIPE)]))
        shared['runtime_environment']=file_record(runtime_path)
        setup_path=self.root/'setup.json';write_json(setup_path,dict(shared,status='complete',schema='plan069-video-setup-result/v1',weight_revision=config['weights']['revision'],runtime_recipe=file_record(FRAME_RECIPE),runtime_profile=profile['runtime_profile']))
        shared['setup']=file_record(setup_path)
        versions=dict(pin.split('==') for pin in read_json(FRAME_RECIPE)['constraints']);versions.update(decord=None,xformers=None)
        dependency_path=self.root/'dependencies.json'
        write_json(dependency_path,dict(schema='plan069-depth-installed-dependencies/v1',candidate='D9',source_revision=config['code']['revision'],setup=shared['setup'],runtime_environment=shared['runtime_environment'],runtime_recipe=file_record(FRAME_RECIPE),files=[file_record(stub)],versions=versions,
            runtime_observation=dict(schema='plan069-video-runtime-observation/v1',record_kind='actual',torch_version='2.14.1+cu130',torchvision_version='0.29.1+cu130',cuda_version='13.0')))
        shared['dependency_manifest']=file_record(dependency_path)
        source_path=self.root/'source-review.json';write_json(source_path,dict(shared,schema='plan069-depth-source-review/v1',reviewer='CPU fixture reviewer',profile_inventory=file_record(VIDEO_FRAME_PROFILES)))
        native_path=self.root/'native.json';write_json(native_path,dict(shared,schema='plan069-video-native-cpu-qualification/v1',strict_cpu_loads=2,inference=False,cuda_initialized=False))
        capture_path=self.root/'capture.json';write_json(capture_path,dict(schema='plan069-video-cpu-capture/v1',candidate='D9',status='passed',cleanup_confirmed=True,native_cpu=file_record(native_path)))
        write_json(self.qual_path,dict(shared,schema='plan069-depth-runtime-qualification/v1',source_review=file_record(source_path),native_cpu=file_record(native_path),capture=file_record(capture_path)))
        self.review=dict(schema='plan069-depth-execution-review/v1',status='REVIEW',asset_inventory=baseline['asset_inventory'],proposals=[self.proposal],unstarted_ledger_prefix=file_record(self.prefix_path))
        self.approved=dict(schema='plan069-depth-user-authorization/v1',status='DO',previous_authorization=file_record(self.prior_path),reset_previous_consumption=False,
            **{key:prior[key] for key in ('cap_amendment','cap_approval','video_amendment')})
        self.amendment=dict(schema='plan069-video-frame-amendment-approval/v1',status='approved',candidate='D10',optional_decoder_omission_approved=True,runtime_recipe=file_record(FRAME_RECIPE),profile_inventory=file_record(VIDEO_FRAME_PROFILES),unstarted_ledger_prefix=file_record(self.prefix_path),D9_runtime_qualification=file_record(self.qual_path))
    def authorization(self):
        review_path=self.root/'review.json';write_json(review_path,self.review)
        approved=dict(self.approved,review=file_record(review_path),video_frame_amendment=self.amendment,candidate_approvals=[dict(schema='plan069-depth-execution-approval/v1',status='approved',candidate='D10',proposal_sha256=object_hash(self.proposal),max_attempts=1)])
        path=self.root/'DO.json';write_json(path,approved);return path
    def test_exact_unstarted_amendment(self):
        _,_,proposal,_=execution_authorization('D10',root=self.root,authorization_path=self.authorization())
        self.assertEqual(proposal['allocation']['setup_seconds'],2400)
        self.assertEqual(proposal['runtime_recipe'],file_record(FRAME_RECIPE))
    def test_no_scientific_budget_or_attempt_expansion(self):
        for key in ('setup_seconds','cpu_seconds','gpu_seconds','artifact_bytes','download_bytes'):
            with self.subTest(key=key):
                old=self.proposal['allocation'][key];self.proposal['allocation'][key]+=1
                with self.assertRaisesRegex(ValueError,'science, caps'):
                    execution_authorization('D10',root=self.root,authorization_path=self.authorization())
                self.proposal['allocation'][key]=old
    def test_prior_d10_grant_rejected(self):
        for event in ('depth_setup_authorized','depth_attempt_authorized','reserve'):
            with self.subTest(event=event):
                row=dict(event=event,candidate='D10',resource='setup',sequence=0,previous_sha256=None)
                row['event_sha256']=object_hash(row);self.prefix_path.write_text(json.dumps(row)+'\n')
                record=file_record(self.prefix_path);self.review['unstarted_ledger_prefix']=record;self.amendment['unstarted_ledger_prefix']=record
                with self.assertRaisesRegex(ValueError,'already started'):
                    execution_authorization('D10',root=self.root,authorization_path=self.authorization())
    def test_qualification_required_and_exact(self):
        for field,value in (('status','failed'),('candidate','D10'),('local_sources',[]),('record_kind','fixture'),('record_kind',None)):
            with self.subTest(field=field):
                old=read_json(self.qual_path);changed=dict(old,**{field:value});write_json(self.qual_path,changed);self.amendment['D9_runtime_qualification']=file_record(self.qual_path)
                with self.assertRaisesRegex(ValueError,'passed actual D9'):
                    execution_authorization('D10',root=self.root,authorization_path=self.authorization())
                write_json(self.qual_path,old)
    def test_explicit_exception_and_scope_required(self):
        self.amendment['optional_decoder_omission_approved']=False
        with self.assertRaisesRegex(ValueError,'exact D10 frame'):
            execution_authorization('D10',root=self.root,authorization_path=self.authorization())
        self.amendment['optional_decoder_omission_approved']=True
        with self.assertRaisesRegex(ValueError,'D10-only'):
            execution_authorization('D9',root=self.root,authorization_path=self.authorization())
    def test_no_reset_or_altered_predecessor(self):
        self.approved['reset_previous_consumption']=True
        with self.assertRaisesRegex(ValueError,'budget or lineage'):
            execution_authorization('D10',root=self.root,authorization_path=self.authorization())
        self.approved['reset_previous_consumption']=False
        self.prior_path.write_text('{}\n')
        with self.assertRaises((ValueError,KeyError)):
            execution_authorization('D10',root=self.root,authorization_path=self.authorization())

    def test_cpu_preparation_is_not_a_consumed_attempt(self):
        row=dict(event='cpu_preparation_charge',candidate='D10',sequence=0,previous_sha256=None)
        row['event_sha256']=object_hash(row);self.prefix_path.write_text(json.dumps(row)+'\n')
        record=file_record(self.prefix_path);self.review['unstarted_ledger_prefix']=record;self.amendment['unstarted_ledger_prefix']=record
        execution_authorization('D10',root=self.root,authorization_path=self.authorization())

    def test_missing_observation_or_present_decoder_rejected(self):
        qualified=read_json(self.qual_path);dependency_path=Path(qualified['dependency_manifest']['path']);original=read_json(dependency_path)
        for mutation in ('observation','decord'):
            with self.subTest(mutation=mutation):
                dependency=copy.deepcopy(original)
                if mutation=='observation':dependency.pop('runtime_observation')
                else:dependency['versions']['decord']='0.6.0'
                write_json(dependency_path,dependency);qualified['dependency_manifest']=file_record(dependency_path);write_json(self.qual_path,qualified);self.amendment['D9_runtime_qualification']=file_record(self.qual_path)
                with self.assertRaises(ValueError):
                    execution_authorization('D10',root=self.root,authorization_path=self.authorization())
    def test_d10_v4_preserved_large_allowance_reaches_provisioning(self):
        from unittest.mock import patch
        import test_vipe_benchmark_video_setup as fixtures
        from vipe_benchmark.video_setup import run_video_setup
        from vipe_benchmark.video_environment import environment_request
        f=fixtures.VideoSetupTests();f.setUp();self.addCleanup(f.tearDown)
        tiny_inventory=f.root/'D10-assets.json'
        import hashlib
        write_json(tiny_inventory,dict(candidates={'D10':dict(files=[dict(repository='vdame',path='metric_video_depth_anything_vits.pth',bytes=len(f.weights),lfs_sha256=hashlib.sha256(f.weights).hexdigest())])}))
        proposal=copy.deepcopy(self.proposal);proposal['required_assets']=file_record(tiny_inventory)
        review=f.root/'D10-review.json';write_json(review,dict(schema='plan069-depth-execution-review/v1',status='REVIEW',proposals=[proposal]))
        auth=f.root/'D10-authority.json';grant=dict(candidate='D10',status='approved',proposal_sha256=object_hash(proposal))
        write_json(auth,dict(review=file_record(review),candidate_approvals=[grant]))
        original=f.runtime_request()
        runtime=environment_request('D10',f.root,seed_executable=original['python_seed_executable'],uv_executable=original['uv']['path'],record_kind='fixture',recipe_path=FRAME_RECIPE)
        request=dict(f.request,candidate='D10',job_id='plan069-D10-setup-001',review=file_record(review),authorization=file_record(auth),runtime_environment=runtime)
        # Real authority acceptance is covered above; this fixture uses tiny assets
        # and an explicit provisioner sentinel to exercise the setup budget branch.
        with patch.object(fixtures,'REQUIRED_SOURCE',fixtures.REQUIRED_SOURCE+('utils/dc_utils.py',)), \
                patch('vipe_benchmark.depth_authorization.execution_authorization',return_value=(request['review'],request['authorization'],proposal,grant)), \
                patch('vipe_benchmark.depth_environment.provision_depth_environment',side_effect=RuntimeError('CPU fixture reached provisioner')) as provision:
            with self.assertRaisesRegex(RuntimeError,'reached provisioner'):
                run_video_setup(request,f.root/request['job_id'],acquire=f.acquire)
        self.assertEqual(provision.call_count,1)
        self.assertEqual(provision.call_args.args[0]['recipe'],file_record(FRAME_RECIPE))
    def recovery_prerequisite_fixture(self, *, repair=False):
        """Rebind tiny qualification receipts to a recovery-shaped private setup."""
        qualified=read_json(self.qual_path)
        old_setup=read_json(qualified['setup']['path'])
        job=self.root/('jobs/plan069-D9-setup-recovery-002' if repair else 'jobs/plan069-D9-setup-recovery-001');job.mkdir(parents=True)
        setup_path=job/'result.json'
        write_json(setup_path,dict(old_setup,schema='plan069-video-setup-recovery-result/v2' if repair else 'plan069-video-setup-recovery-result/v1',job_id=job.name))
        setup_record=file_record(setup_path);qualified['setup']=setup_record
        dependency_path=Path(qualified['dependency_manifest']['path']);dependencies=read_json(dependency_path)
        dependencies['setup']=setup_record;write_json(dependency_path,dependencies);qualified['dependency_manifest']=file_record(dependency_path)
        native_path=Path(qualified['native_cpu']['path']);native=read_json(native_path)
        native.update(setup=setup_record,dependency_manifest=qualified['dependency_manifest']);write_json(native_path,native);qualified['native_cpu']=file_record(native_path)
        capture_path=Path(qualified['capture']['path']);capture=read_json(capture_path)
        capture['native_cpu']=qualified['native_cpu'];write_json(capture_path,capture);qualified['capture']=file_record(capture_path)
        write_json(self.qual_path,qualified);qualification_record=file_record(self.qual_path)
        rows=[]
        for data in (dict(event='finish',job_id=job.name,status='complete'),
                     dict(event='cpu_preparation_charge',resource='cpu',evidence=qualification_record,elapsed_seconds=.001)):
            row=dict(data,sequence=len(rows),previous_sha256=rows[-1]['event_sha256'] if rows else None)
            row['event_sha256']=object_hash(row);rows.append(row)
        ledger=self.root/'ledger.jsonl';ledger.write_text(''.join(json.dumps(row)+'\n' for row in rows))
        prefix=self.root/'qualification-prefix.jsonl';prefix.write_bytes(ledger.read_bytes())
        return qualification_record,file_record(prefix),rows
    def test_recovery_requires_checked_protected_ancestry_not_schema(self):
        from vipe_benchmark.depth_video_frame_authorization import validate_D9_prerequisite
        record,prefix,_=self.recovery_prerequisite_fixture()
        with self.assertRaisesRegex(ValueError,'unique accepted recovery'):
            validate_D9_prerequisite(record,ledger_prefix=prefix)
    def test_accepted_recovery_delegates_to_strict_no_active_lineage(self):
        from unittest.mock import patch
        from vipe_benchmark.depth_video_frame_authorization import validate_D9_prerequisite
        record,prefix,rows=self.recovery_prerequisite_fixture()
        # Accepted lineage itself has independent full producer fixtures. This
        # seam test verifies the prerequisite delegates with exact checked rows.
        with patch('vipe_benchmark.depth_recovery_lineage.accepted_setup_lineage',return_value=dict(finish=rows[0])) as accept:
            validate_D9_prerequisite(record,ledger_prefix=prefix)
        self.assertEqual(accept.call_args.args[0],read_json(self.qual_path)['setup'])
        self.assertEqual(accept.call_args.args[1],rows)
        self.assertEqual(accept.call_args.kwargs,{})
    def test_accepted_repair_delegates_to_strict_no_active_lineage(self):
        from unittest.mock import patch
        from vipe_benchmark.depth_video_frame_authorization import validate_D9_prerequisite
        record,prefix,rows=self.recovery_prerequisite_fixture(repair=True)
        # Accepted lineage itself has independent full producer fixtures. This
        # seam test verifies the prerequisite delegates with exact checked rows.
        with patch('vipe_benchmark.depth_recovery_lineage.accepted_setup_lineage',return_value=dict(finish=rows[0])) as accept:
            validate_D9_prerequisite(record,ledger_prefix=prefix)
        self.assertEqual(accept.call_args.args[0],read_json(self.qual_path)['setup'])
        self.assertEqual(accept.call_args.args[1],rows)
        self.assertEqual(accept.call_args.kwargs,{})
    def test_missing_charge_or_changed_live_prefix_rejected(self):
        from unittest.mock import patch
        from vipe_benchmark.depth_video_frame_authorization import validate_D9_prerequisite
        record,prefix,rows=self.recovery_prerequisite_fixture()
        with patch('vipe_benchmark.depth_recovery_lineage.accepted_setup_lineage',return_value=dict(finish=rows[0])):
            short=self.root/'no-charge.jsonl';short.write_text(json.dumps(rows[0])+'\n')
            with self.assertRaisesRegex(ValueError,'finalization charge'):
                validate_D9_prerequisite(record,ledger_prefix=file_record(short))
            (self.root/'ledger.jsonl').write_text(json.dumps(rows[0])+'\n')
            with self.assertRaisesRegex(ValueError,'differs from protected'):
                validate_D9_prerequisite(record,ledger_prefix=prefix)
    def test_unrelated_active_or_faked_locked_events_rejected(self):
        from unittest.mock import patch
        from vipe_benchmark.depth_video_frame_authorization import validate_D9_prerequisite
        record,prefix,rows=self.recovery_prerequisite_fixture()
        active=dict(event='reserve',job_id='foreign-gpu',resource='gpu',sequence=2,previous_sha256=rows[-1]['event_sha256'])
        active['event_sha256']=object_hash(active);ledger=self.root/'ledger.jsonl'
        ledger.write_text(ledger.read_text()+json.dumps(active)+'\n')
        with patch('vipe_benchmark.depth_recovery_lineage.accepted_setup_lineage',return_value=dict(finish=rows[0])):
            with self.assertRaisesRegex(ValueError,'active attempt'):
                validate_D9_prerequisite(record,ledger_prefix=prefix,allow_owned_active=False)
            with self.assertRaisesRegex(ValueError,'locked current'):
                validate_D9_prerequisite(record,ledger_prefix=prefix,current_events=rows)
    def test_only_exact_protected_own_d10_reservation_can_revalidate(self):
        from unittest.mock import patch
        from vipe_benchmark.depth_video_frame_authorization import validate_D9_prerequisite
        record,prefix,rows=self.recovery_prerequisite_fixture()
        review_path=self.root/'active-D10-review.json';write_json(review_path,dict(proposals=[self.proposal]))
        approved=dict(schema='plan069-depth-user-authorization/v1',status='DO',review=file_record(review_path))
        authority_path=self.root/'active-D10-DO.json';write_json(authority_path,approved)
        authority=file_record(authority_path);source_review=read_json(self.qual_path)['source_review']
        grant=dict(event='depth_setup_authorized',candidate='D10',authorization=authority,review=approved['review'],source_review=source_review,proposal_sha256=object_hash(self.proposal))
        reserve=dict(event='reserve',job_id='plan069-D10-setup-001',resource='setup',evidence=dict(authorization=authority,review=approved['review'],source_review=source_review))
        for data in (grant,reserve):
            row=dict(data,sequence=len(rows),previous_sha256=rows[-1]['event_sha256']);row['event_sha256']=object_hash(row);rows.append(row)
        ledger=self.root/'ledger.jsonl';ledger.write_text(''.join(json.dumps(row)+'\n' for row in rows))
        with patch('vipe_benchmark.depth_recovery_lineage.accepted_setup_lineage',return_value=dict(finish=rows[0])):
            validate_D9_prerequisite(record,ledger_prefix=prefix,approved=approved)
            with self.assertRaisesRegex(ValueError,'active attempt'):
                validate_D9_prerequisite(record,ledger_prefix=prefix,approved=approved,current_events=rows,allow_owned_active=False)
            wrong=dict(approved,status='REVIEW')
            with self.assertRaisesRegex(ValueError,'differs from protected exact'):
                validate_D9_prerequisite(record,ledger_prefix=prefix,approved=wrong)

    def stale_bound_with_successor(self, *, successor_changes=None):
        """DO-bound record from older D9 sources plus a later protected successor."""
        _,_,rows=self.recovery_prerequisite_fixture(repair=True)
        current=read_json(self.qual_path)
        bound_path=self.root/'prepare/plan069-D9-native-qualification-002/runtime-qualification.json'
        bound_path.parent.mkdir(parents=True)
        write_json(bound_path,dict(current,local_sources=current['local_sources'][:-1]))
        successor_path=self.root/'prepare/plan069-D9-native-qualification-003/runtime-qualification.json'
        successor_path.parent.mkdir(parents=True)
        write_json(successor_path,dict(current,**(successor_changes or {})))
        bound,successor=file_record(bound_path),file_record(successor_path)
        rows=rows[:1]
        ledger=self.root/'ledger.jsonl'
        for evidence,prefix in ((bound,bound_path.parent/'finalization-ledger-prefix.jsonl'),
                                (successor,successor_path.parent/'finalization-ledger-prefix.jsonl')):
            row=dict(event='cpu_preparation_charge',resource='cpu',evidence=evidence,elapsed_seconds=.001,
                     sequence=len(rows),previous_sha256=rows[-1]['event_sha256'])
            row['event_sha256']=object_hash(row);rows.append(row)
            ledger.write_text(''.join(json.dumps(row)+'\n' for row in rows))
            prefix.write_bytes(ledger.read_bytes())
        return bound,file_record(bound_path.parent/'finalization-ledger-prefix.jsonl'),successor,rows
    def test_stale_bound_qualification_uses_protected_successor(self):
        from unittest.mock import patch
        from vipe_benchmark.depth_video_frame_authorization import validate_D9_prerequisite
        bound,prefix,successor,rows=self.stale_bound_with_successor()
        with patch('vipe_benchmark.depth_recovery_lineage.accepted_setup_lineage',return_value=dict(finish=rows[0])) as accept:
            validate_D9_prerequisite(bound,ledger_prefix=prefix)
        self.assertEqual(accept.call_args.args[1],rows)
    def test_successor_is_the_qualification_whose_lineage_is_checked(self):
        from unittest.mock import patch
        import vipe_benchmark.depth_video_frame_authorization as frame
        bound,prefix,successor,rows=self.stale_bound_with_successor()
        with patch.object(frame,'validate_recovery_qualification_lineage') as lineage:
            frame.validate_D9_prerequisite(bound,ledger_prefix=prefix)
        self.assertEqual(lineage.call_args.kwargs['qualification_record'],successor)
        self.assertEqual(lineage.call_args.args[1]['path'],str(Path(successor['path']).parent/'finalization-ledger-prefix.jsonl'))
    def test_successor_under_caller_owned_exclusive_lock_does_not_deadlock(self):
        import fcntl, threading
        from unittest.mock import patch
        from vipe_benchmark.depth_video_frame_authorization import validate_D9_prerequisite
        bound,prefix,_,rows=self.stale_bound_with_successor()
        outcome=[]
        def check():
            try:
                validate_D9_prerequisite(bound,ledger_prefix=prefix,current_events=rows,allow_owned_active=False)
                outcome.append('passed')
            except Exception as error:
                outcome.append(error)
        with (self.root/'ledger.jsonl').open('rb') as held, \
                patch('vipe_benchmark.depth_recovery_lineage.accepted_setup_lineage',return_value=dict(finish=rows[0])):
            fcntl.flock(held,fcntl.LOCK_EX)
            worker=threading.Thread(target=check,daemon=True);worker.start();worker.join(5)
            while_locked=list(outcome)
            fcntl.flock(held,fcntl.LOCK_UN)
            worker.join(5)
        self.assertEqual(while_locked,['passed'])
    def test_malformed_charge_rows_are_ignored_not_crashing(self):
        from unittest.mock import patch
        from vipe_benchmark.depth_video_frame_authorization import validate_D9_prerequisite
        bound,prefix,successor,rows=self.stale_bound_with_successor()
        odd=dict(event='cpu_preparation_charge',resource='cpu',evidence=None,elapsed_seconds=.001,sequence=len(rows),previous_sha256=rows[-1]['event_sha256'])
        odd['event_sha256']=object_hash(odd);rows=rows+[odd]
        (self.root/'ledger.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))
        with patch('vipe_benchmark.depth_recovery_lineage.accepted_setup_lineage',return_value=dict(finish=rows[0])):
            validate_D9_prerequisite(bound,ledger_prefix=prefix)
    def test_successor_outside_run_prepare_or_missing_prefix_rejected(self):
        from unittest.mock import patch
        from vipe_benchmark.depth_video_frame_authorization import validate_D9_prerequisite
        bound,prefix,successor,rows=self.stale_bound_with_successor()
        (Path(successor['path']).parent/'finalization-ledger-prefix.jsonl').unlink()
        with patch('vipe_benchmark.depth_recovery_lineage.accepted_setup_lineage',return_value=dict(finish=rows[0])):
            with self.assertRaisesRegex(ValueError,'successor'):
                validate_D9_prerequisite(bound,ledger_prefix=prefix)
        # A correctly named qualification outside the run's prepare directory is never selected.
        outside=self.root/'elsewhere/plan069-D9-native-qualification-009/runtime-qualification.json'
        outside.parent.mkdir(parents=True);outside.write_bytes(Path(successor['path']).read_bytes())
        rows=rows[:2]
        row=dict(event='cpu_preparation_charge',resource='cpu',evidence=file_record(outside),elapsed_seconds=.001,sequence=2,previous_sha256=rows[1]['event_sha256'])
        row['event_sha256']=object_hash(row);rows.append(row)
        (self.root/'ledger.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
        with patch('vipe_benchmark.depth_recovery_lineage.accepted_setup_lineage',return_value=dict(finish=rows[0])):
            with self.assertRaisesRegex(ValueError,'passed actual D9'):
                validate_D9_prerequisite(bound,ledger_prefix=prefix)
    def test_successor_with_changed_installed_runtime_rejected(self):
        from unittest.mock import patch
        from vipe_benchmark.depth_video_frame_authorization import validate_D9_prerequisite
        other=self.root/'other-dependencies.json';other.write_text('{"different": true}\n')
        bound,prefix,_,rows=self.stale_bound_with_successor(successor_changes=dict(dependency_manifest=file_record(other)))
        with patch('vipe_benchmark.depth_recovery_lineage.accepted_setup_lineage',return_value=dict(finish=rows[0])):
            with self.assertRaisesRegex(ValueError,'successor'):
                validate_D9_prerequisite(bound,ledger_prefix=prefix)
    def test_stale_bound_qualification_without_successor_rejected(self):
        from unittest.mock import patch
        from vipe_benchmark.depth_video_frame_authorization import validate_D9_prerequisite
        bound,prefix,_,rows=self.stale_bound_with_successor()
        ledger=self.root/'ledger.jsonl';ledger.write_text(''.join(json.dumps(row)+'\n' for row in rows[:2]))
        with patch('vipe_benchmark.depth_recovery_lineage.accepted_setup_lineage',return_value=dict(finish=rows[0])):
            with self.assertRaisesRegex(ValueError,'passed actual D9'):
                validate_D9_prerequisite(bound,ledger_prefix=prefix)

    def test_unrelated_resumed_checkpoint_remains_active(self):
        from unittest.mock import patch
        from vipe_benchmark.depth_video_frame_authorization import validate_D9_prerequisite
        record,prefix,rows=self.recovery_prerequisite_fixture()
        for event in ('reserve','checkpoint','checkpoint_resume'):
            row=dict(event=event,job_id='foreign-aggregate',resource='cpu',sequence=len(rows),previous_sha256=rows[-1]['event_sha256'])
            row['event_sha256']=object_hash(row);rows.append(row)
        (self.root/'ledger.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))
        with patch('vipe_benchmark.depth_recovery_lineage.accepted_setup_lineage',return_value=dict(finish=rows[0])):
            with self.assertRaisesRegex(ValueError,'unrelated active'):
                validate_D9_prerequisite(record,ledger_prefix=prefix,approved={})
