"""CPU-only exact qualification gate tests for the tracked execution producer."""
import importlib.util
from pathlib import Path
import unittest
from vipe_benchmark.config import ROOT

PATH=ROOT/'docs/research/vipe-alternatives/plan069-D9-recovery-dispatch-001/prepare_recovery.py'
spec=importlib.util.spec_from_file_location('recovery_producer',PATH)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class RecoveryProducerTests(unittest.TestCase):
    def setUp(self):
        self.record=dict(path='/fixture/source.py',sha256='a'*64,bytes=10)
        self.receipt=dict(schema='plan069-delta-cpu-test-capture/v1',record_kind='actual',passed=True,
            within_wall_limit=True,source_bytes_unchanged=True,checkout=str(ROOT),
            sources_before=[self.record],sources_after=[self.record],commands=[dict(returncode=0,timed_out=False,
            cleanup=dict(confirmed_no_surviving_observed_processes=True,surviving_observed_owned_processes=[]))])

    def test_exact_qualified_sources_accepted_without_head_equality(self):
        self.receipt.update(head='old',head_after='new')
        module.validate_qualification(self.receipt,[self.record],ROOT)

    def test_missing_changed_or_relocated_source_rejected(self):
        for record in (dict(self.record,sha256='b'*64),dict(self.record,path='/different/source.py')):
            with self.subTest(record=record):
                with self.assertRaisesRegex(ValueError,'not covered'):
                    module.validate_qualification(self.receipt,[record],ROOT)

    def test_failed_unclean_or_fixture_capture_rejected(self):
        for key,value in [('record_kind','fixture'),('passed',False),('within_wall_limit',False),
                          ('source_bytes_unchanged',False),('sources_after',[])]:
            with self.subTest(key=key):
                prior=self.receipt[key];self.receipt[key]=value
                with self.assertRaises(ValueError):module.validate_qualification(self.receipt,[self.record],ROOT)
                self.receipt[key]=prior
        command=self.receipt['commands'][0]
        for key,value in [('returncode',1),('timed_out',True),('cleanup',{})]:
            prior=command[key];command[key]=value
            with self.assertRaises(ValueError):module.validate_qualification(self.receipt,[self.record],ROOT)
            command[key]=prior

    def test_original_setup_grant_has_candidate_without_job_id(self):
        import tempfile
        from unittest.mock import patch
        from vipe_benchmark.files import file_record,object_hash,write_json
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);old=root/'jobs'/module.OLD;old.mkdir(parents=True)
            (old/'runtime').mkdir();(root/'transfers').mkdir()
            for name in ('source.tar.gz','model.pth','runtime/failure.json','runtime/requirements.lock'):
                (old/name).write_text('fixture')
            asset_record=root/'assets.json';write_json(asset_record,dict(candidates={'D9':dict(files=[dict(
                path='model.pth',bytes=7,lfs_sha256='a'*64)])}))
            maps=dict(candidate='D9',required_assets=file_record(asset_record))
            review=root/'review.json';write_json(review,dict(proposals=[maps]))
            request=root/'request.json';write_json(request,{})
            info=(old/'model.pth').stat();write_json(root/'transfers/transfer-fixture.json',dict(
                output=str(old/'model.pth'),output_identity=dict(device=info.st_dev,inode=info.st_ino,
                size=info.st_size,mtime_ns=info.st_mtime_ns),error=None,bytes_received=7))
            events=[dict(event='depth_setup_authorized',candidate='D9',sequence=761,event_sha256='grant',
                review=file_record(review),proposal_sha256=object_hash(maps),byte_checkpoint={}),
                dict(event='reserve',job_id=module.OLD,sequence=762,evidence=dict(request=file_record(request))),
                dict(event='finish',job_id=module.OLD,sequence=765,event_sha256='finish',status='failed',
                cleanup_confirmed=True,cleanup_uncertain=False,surviving_pids=[],deadline_exceeded=False)]
            with patch('vipe_benchmark.video_native.native_source_records',return_value=[]):
                original,*_=module.retained_original(root,events)
            self.assertEqual(original['grant_event_sha256'],'grant')

    def test_reservation_evidence_includes_every_checked_grant_binding(self):
        fields=('request','review','authorization','source_review','worker','executable')
        records=[dict(path=field,sha256='a'*64,bytes=1) for field in fields]
        self.assertEqual(module.reservation_evidence(*records),dict(zip(fields,records)))

    def test_identical_unconsumed_request_can_resume_without_rewrite(self):
        import tempfile
        from vipe_benchmark.files import write_json
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path=root/'request.json';output=root/'output';request={'fixture':True}
            write_json(path,request);before=path.stat().st_mtime_ns
            module.publish_request(request,path,output,[])
            self.assertEqual(path.stat().st_mtime_ns,before)
            with self.assertRaisesRegex(ValueError,'differs'):module.publish_request({'changed':True},path,output,[])
            for event in ('depth_setup_recovery_authorized','reserve','finish'):
                with self.assertRaisesRegex(ValueError,'already'):
                    module.publish_request(request,path,output,[dict(event=event,job_id=module.JOB)])

    def test_canonical_approval_schema_and_additional_fields_are_accepted(self):
        from vipe_benchmark.files import object_hash
        proposal={'fixture_recovery':True};maps={'fixture_maps':True}
        approval=dict(schema='plan069-depth-user-authorization/v1',status='DO',review=self.record,
            setup_recovery_approval=dict(candidate='D9',job_id=module.JOB,status='approved',max_attempts=1,
                proposal_sha256=object_hash(proposal)),candidate_approvals=[dict(
                schema='plan069-depth-execution-approval/v1',candidate='D9',status='approved',max_attempts=1,
                proposal_sha256=object_hash(maps),explanation='additional review evidence')])
        module.validate_approval(approval,self.record,proposal,maps)
        for key in ('setup_recovery_approval','candidate_approvals'):
            prior=approval[key];approval[key]=None if key=='setup_recovery_approval' else []
            with self.assertRaises(ValueError):module.validate_approval(approval,self.record,proposal,maps)
            approval[key]=prior
