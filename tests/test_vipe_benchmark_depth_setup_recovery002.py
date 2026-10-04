"""A fresh002 grant preserves both consumed attempts and their paid ancestry."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import test_vipe_benchmark_depth_setup_recovery as existing
from vipe_benchmark.files import file_record,object_hash,read_json,write_json
from vipe_benchmark.budgets import budget_snapshot
from vipe_benchmark.depth_setup_recovery import REPAIR_JOB,validate_recovery_request


class Recovery002Tests(unittest.TestCase):
    def setUp(self):
        self.fixture=existing.RecoveryRequestTests();self.fixture.setUp();self.addCleanup(self.fixture.tearDown)
        f=self.fixture;self.root=f.root;self.ledger=f.ledger
        grant=f.authorize()
        with patch('vipe_benchmark.execution.resources',return_value=dict(budget_snapshot(f.root),gpu_pids=[],device_bytes=0)):
            self.ledger.reserve(existing.JOB,f.command,f.evidence)
        failure_path=f.root/'jobs'/existing.JOB/'failure.json';write_json(failure_path,dict(schema='plan069-video-setup-recovery-failure/v1',record_kind='actual',status='failed',job_id=existing.JOB,error='ValueError: runtime profile mismatch',elapsed_seconds=.1,original_setup=f.original,automatic_retries=0,gpu_operations=False))
        finish=self.ledger.finish(existing.JOB,'failed',8.383504559,cleanup_confirmed=True,cleanup_uncertain=False,surviving_pids=[])
        self.failed=dict(job_id=existing.JOB,grant_event_sha256=grant['event_sha256'],failed_finish_event_sha256=finish['event_sha256'],request=f.request_record,failure=file_record(failure_path))
        proposal=dict(f.recovery,schema='plan069-video-setup-recovery-proposal/v2',job_id=REPAIR_JOB,failed_recoveries=[self.failed])
        review=dict(schema='plan069-depth-execution-review/v1',status='REVIEW',proposals=[f.map_proposal],setup_recovery_proposal=proposal)
        review_path=f.root/'review002.json';write_json(review_path,review)
        self.review=file_record(review_path)
        approval=dict(schema='plan069-depth-user-authorization/v1',status='DO',review=self.review,setup_recovery_approval=dict(candidate='D9',job_id=REPAIR_JOB,status='approved',max_attempts=1,proposal_sha256=object_hash(proposal)),candidate_approvals=[dict(candidate='D9',status='approved',max_attempts=1,proposal_sha256=object_hash(f.map_proposal))])
        approval_path=f.root/'DO002.json';write_json(approval_path,approval)
        source=read_json(f.source_review['path']);source['setup_recovery_proposal_sha256']=object_hash(proposal)
        source_path=f.root/'source002.json';write_json(source_path,source)
        self.request=dict(f.request,schema='plan069-video-setup-recovery-request/v2',job_id=REPAIR_JOB,failed_recoveries=[self.failed],review=self.review,authorization=file_record(approval_path),source_review=file_record(source_path))
        self.path=f.root/'requests'/(REPAIR_JOB+'.json');write_json(self.path,self.request);self.record=file_record(self.path)
        self.command=[f.command[0],f.command[1],'--request',str(self.path),'--output',str(f.root/'jobs'/REPAIR_JOB)]
        self.evidence=dict(f.evidence,request=self.record,review=self.review,authorization=self.request['authorization'],source_review=self.request['source_review'])

    def authorize(self):
        f=self.fixture
        with patch('vipe_benchmark.execution.resources',return_value=dict(budget_snapshot(f.root),gpu_pids=[],device_bytes=0)):
            return self.ledger.authorize_depth_setup_recovery(self.record,command=self.command,worker=f.worker,executable=f.executable)

    def test_new002_one_use_preserves_original_and_failed001(self):
        grant=self.authorize()
        self.assertEqual(grant['job_id'],REPAIR_JOB)
        self.assertEqual(self.ledger.states()[existing.JOB]['status'],'failed')
        self.assertEqual(self.ledger.states()['plan069-D9-setup-001']['status'],'failed')
        with patch('vipe_benchmark.execution.resources',return_value=dict(budget_snapshot(self.root),gpu_pids=[],device_bytes=0)):
            reserve=self.ledger.reserve(REPAIR_JOB,self.command,self.evidence)
        self.assertEqual(reserve['seconds'],1200)
        self.assertNotIn('plan069-D9-maps-001',self.ledger.states())

    def refresh(self):
        proposal=read_json(self.review['path'])['setup_recovery_proposal']
        proposal['failed_recoveries']=self.request['failed_recoveries']
        review=read_json(self.review['path']);review['setup_recovery_proposal']=proposal
        Path(self.review['path']).write_text(json.dumps(review));self.review=file_record(self.review['path'])
        approval=read_json(self.request['authorization']['path']);approval.update(review=self.review,setup_recovery_approval=dict(candidate='D9',job_id=REPAIR_JOB,status='approved',max_attempts=1,proposal_sha256=object_hash(proposal)))
        Path(self.request['authorization']['path']).write_text(json.dumps(approval));self.request['authorization']=file_record(self.request['authorization']['path'])
        source=read_json(self.request['source_review']['path']);source['setup_recovery_proposal_sha256']=object_hash(proposal)
        Path(self.request['source_review']['path']).write_text(json.dumps(source));self.request['source_review']=file_record(self.request['source_review']['path'])
        self.request['review']=self.review;self.path.write_text(json.dumps(self.request));self.record=file_record(self.path)
        self.evidence.update(request=self.record,review=self.review,authorization=self.request['authorization'],source_review=self.request['source_review'])

    def test_second_review_cannot_reuse_first_DO(self):
        self.request['authorization']=self.fixture.authorization;self.path.write_text(json.dumps(self.request));self.record=file_record(self.path)
        before=self.ledger.path.read_bytes()
        with self.assertRaisesRegex(ValueError,'separately approved'):
            self.authorize()
        self.assertEqual(self.ledger.path.read_bytes(),before)

    def test_missing_wrong_or_changed_failed_chain_denies_without_append(self):
        for chain in ([],[dict(self.failed,job_id='plan069-D9-setup-recovery-003')],[dict(self.failed,failed_finish_event_sha256='0'*64)]):
            with self.subTest(chain=chain):
                self.request['failed_recoveries']=chain;self.refresh();before=self.ledger.path.read_bytes()
                with self.assertRaisesRegex(ValueError,'failed recovery001|confirmed cleanup'):
                    self.authorize()
                self.assertEqual(self.ledger.path.read_bytes(),before)

    def test_old_consumption_and_global_setup_time_are_not_reset(self):
        from vipe_benchmark.ledger import Ledger
        original_append=Ledger._append
        child=Recovery002Tests(methodName='runTest')
        def append(instance,stream,events,row):
            # Seed a longer protected original attempt in this CPU history fixture.
            if row.get('event')=='finish' and row.get('job_id')=='plan069-D9-setup-001':
                row=dict(row,elapsed_seconds=595.)
            return original_append(instance,stream,events,row)
        try:
            with patch.object(Ledger,'_append',new=append):child.setUp()
            before=child.ledger.path.read_bytes()
            # 595+1200 fits1800; adding the consumed recovery001 pushes it over1800.
            with self.assertRaisesRegex(ValueError,'remaining candidate'):
                child.authorize()
            self.assertEqual(child.ledger.path.read_bytes(),before)
        finally:child.doCleanups()

    def test_second_recovery_requires_exact1200_seconds_before_append(self):
        for seconds in (1000,1201):
            with self.subTest(seconds=seconds):
                review=read_json(self.review['path']);review['setup_recovery_proposal']['recovery_seconds']=seconds
                Path(self.review['path']).write_text(json.dumps(review));self.refresh()
                before=self.ledger.path.read_bytes()
                with self.assertRaisesRegex(ValueError,'1200'):
                    self.authorize()
                self.assertEqual(self.ledger.path.read_bytes(),before)

    def test_completed_or_uncertain_first_recovery_cannot_be_retried(self):
        from vipe_benchmark.ledger import Ledger
        original_finish=Ledger.finish
        for fields in (dict(status='complete'),dict(cleanup_uncertain=True),dict(surviving_pids=[123])):
            with self.subTest(fields=fields):
                child=Recovery002Tests(methodName='runTest')
                def finish(instance,job,status,*args,**kwargs):
                    if job==existing.JOB:
                        kwargs.update({key:value for key,value in fields.items() if key!='status'});status=fields.get('status',status)
                    return original_finish(instance,job,status,*args,**kwargs)
                try:
                    with patch.object(Ledger,'finish',new=finish):child.setUp()
                    before=child.ledger.path.read_bytes()
                    with self.assertRaisesRegex(ValueError,'confirmed cleanup'):
                        child.authorize()
                    self.assertEqual(child.ledger.path.read_bytes(),before)
                finally:child.doCleanups()

    def test_second_grant_consumption_and_command_are_exact(self):
        self.authorize();before=self.ledger.path.read_bytes()
        with self.assertRaisesRegex(ValueError,'already authorized or consumed'):self.authorize()
        self.assertEqual(self.ledger.path.read_bytes(),before)
        with self.assertRaisesRegex(ValueError,'reservation differs'):
            self.ledger.reserve(REPAIR_JOB,self.command+['unapproved'],self.evidence)
        self.assertNotIn(REPAIR_JOB,self.ledger.states())


if __name__=='__main__':unittest.main()
