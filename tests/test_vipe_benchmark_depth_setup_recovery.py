"""Checked recovery cannot reset consumed setup authority or whole-slot caps."""
import tempfile
import unittest
from pathlib import Path
from vipe_benchmark.config import load
from vipe_benchmark.ledger import Ledger


class RecoveryAuthorityTests(unittest.TestCase):
    def test_video_source_closure_includes_the_executed_network_guard(self):
        from vipe_benchmark.config import ROOT
        from vipe_benchmark.depth_admission import local_source_records
        from vipe_benchmark.files import file_record
        for candidate in ('D9','D10'):
            self.assertIn(file_record(ROOT/'scripts/offline-python.py'),local_source_records(candidate))

    def test_recovery_source_closure_includes_checked_execution_selection(self):
        from vipe_benchmark.config import ROOT
        from vipe_benchmark.depth_admission import local_source_records
        from vipe_benchmark.files import file_record
        records=local_source_records('D9')
        for name in ('depth_authorization.py','depth_recovery_authorization.py'):
            self.assertIn(file_record(ROOT/'scripts/vipe_benchmark'/name),records)

    def test_ordinary_note_cannot_mint_recovery_authority(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger=Ledger(Path(directory)/'ledger.jsonl',load())
            ledger.note('fixture_observation',value='unchanged')
            before=ledger.path.read_bytes()
            with self.assertRaisesRegex(ValueError,'checked ledger transition'):
                ledger.note('depth_setup_recovery_authorized',job_id='plan069-D9-setup-recovery-001')
            self.assertEqual(ledger.path.read_bytes(),before)

import copy
import os
import sys
from unittest.mock import patch
from vipe_benchmark.budgets import budget_snapshot
from vipe_benchmark.config import ROOT
from vipe_benchmark.files import file_record, object_hash, read_json, write_json
from vipe_benchmark.depth_setup_recovery import JOB, validate_recovery_request


class RecoveryRequestTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.root=Path(self.temporary.name)
        self.config=dict(load(),new_download_gib_limit=110,new_artifact_disk_gib_limit=210)
        self.ledger=Ledger(self.root/'ledger.jsonl',self.config)
        from vipe_benchmark.depth_admission import VIDEO_PYPI_PROFILES, VIDEO_FRAME_PROFILES, local_source_records
        from vipe_benchmark.video_environment import PYPI_RECIPE, FRAME_RECIPE
        self.model=self.root/'jobs/plan069-D9-setup-001/model.bin'
        asset_hash=__import__('hashlib').sha256(b'model-data').hexdigest()
        inventory=self.root/'required-assets.json'
        write_json(inventory,dict(candidates=dict(D9=dict(files=[dict(repository='fixture/model',path='model.bin',bytes=10,lfs_sha256=asset_hash)]))))
        self.original_proposal=dict(candidate='D9',candidate_config=dict(code=dict(revision='a'*40),weights=dict(revision='b'*40)),
            allocation=dict(download_bytes=6*2**30,artifact_bytes=9*2**30,setup_seconds=1800,cpu_seconds=3600,gpu_seconds=1200),
            max_attempts=1,required_assets=file_record(inventory),profile_inventory=file_record(VIDEO_PYPI_PROFILES),
            runtime_recipe=file_record(PYPI_RECIPE),profile=read_json(VIDEO_PYPI_PROFILES)['profiles']['D9'])
        old_review=self.root/'old-review.json';write_json(old_review,dict(schema='plan069-depth-execution-review/v1',status='REVIEW',proposals=[self.original_proposal]))
        self.old_review=file_record(old_review)
        old_do=self.root/'old-do.json';write_json(old_do,dict(status='DO',review=self.old_review,candidate_approvals=[dict(candidate='D9',status='approved',max_attempts=1,proposal_sha256=object_hash(self.original_proposal))]))
        self.old_do=file_record(old_do)
        old_source=self.root/'old-source.json';write_json(old_source,dict(status='passed'));self.old_source=file_record(old_source)
        old_request=self.root/'requests/plan069-D9-setup-001.json'
        write_json(old_request,dict(schema='plan069-depth-setup-request/v1',record_kind='actual',candidate='D9',job_id='plan069-D9-setup-001',ledger_path=str(self.ledger.path),review=self.old_review,authorization=self.old_do))
        from vipe_benchmark.depth_budget_reconciliation import capture_checkpoint
        reading=budget_snapshot(self.root);checkpoint=capture_checkpoint(self.root,'D9',reading)
        with self.ledger.locked() as (stream,events):
            self.original_grant=self.ledger._append(stream,events,dict(event='depth_setup_authorized',candidate='D9',seconds=1800,
                review=self.old_review,authorization=self.old_do,source_review=self.old_source,proposal_sha256=object_hash(self.original_proposal),resource_snapshot=reading,byte_checkpoint=checkpoint))
            self.ledger._append(stream,events,dict(event='reserve',job_id='plan069-D9-setup-001',resource='setup',seconds=1800,evidence=dict(request=file_record(old_request))))
        self.model.parent.mkdir(parents=True);self.model.write_bytes(b'model-data')
        archive=self.model.parent/'source.tar.gz';archive.write_bytes(b'archive')
        source=self.model.parent/'source/video_depth.py';source.parent.mkdir();source.write_text('# fixture source\n')
        lock=self.model.parent/'runtime/requirements.lock';lock.parent.mkdir();lock.write_text('torch==2.14.1\n')
        failure=self.model.parent/'runtime/failure.json';write_json(failure,dict(schema='plan069-depth-environment-failure/v1',status='failed',candidate='D9',command_receipts=[]))
        with self.ledger.locked() as (stream,events):
            self.failed_finish=self.ledger._append(stream,events,dict(event='finish',job_id='plan069-D9-setup-001',resource='setup',status='failed',elapsed_seconds=203.775189598,cleanup_confirmed=True,cleanup_uncertain=False,surviving_pids=[],deadline_exceeded=False))
        self.original=dict(grant_event_sha256=self.original_grant['event_sha256'],failed_finish_event_sha256=self.failed_finish['event_sha256'],byte_checkpoint=checkpoint,
            request=file_record(old_request),source_archive=file_record(archive),source_files=[file_record(source)],checkpoint=file_record(self.model),runtime_failure=file_record(failure),dependency_lock=file_record(lock))
        self.map_proposal=copy.deepcopy(self.original_proposal)
        self.map_proposal.update(runtime_recipe=file_record(FRAME_RECIPE),profile_inventory=file_record(VIDEO_FRAME_PROFILES),profile=read_json(VIDEO_FRAME_PROFILES)['profiles']['D9'])
        self.recovery=dict(schema='plan069-video-setup-recovery-proposal/v1',candidate='D9',job_id=JOB,max_attempts=1,
            recovery_seconds=1200,original_setup=self.original,map_proposal_sha256=object_hash(self.map_proposal),runtime_recipe=file_record(FRAME_RECIPE),profile_inventory=file_record(VIDEO_FRAME_PROFILES))
        review=self.root/'recovery-review.json';write_json(review,dict(schema='plan069-depth-execution-review/v1',status='REVIEW',proposals=[self.map_proposal],setup_recovery_proposal=self.recovery));self.review=file_record(review)
        authorization=self.root/'recovery-do.json';write_json(authorization,dict(schema='plan069-depth-user-authorization/v1',status='DO',review=self.review,
            setup_recovery_approval=dict(candidate='D9',job_id=JOB,status='approved',max_attempts=1,proposal_sha256=object_hash(self.recovery)),
            candidate_approvals=[dict(candidate='D9',status='approved',max_attempts=1,proposal_sha256=object_hash(self.map_proposal))]));self.authorization=file_record(authorization)
        source_review=self.root/'recovery-source.json';write_json(source_review,dict(schema='plan069-depth-source-review/v1',status='passed',candidate='D9',proposal_sha256=object_hash(self.map_proposal),setup_recovery_proposal_sha256=object_hash(self.recovery),local_sources=local_source_records('D9')));self.source_review=file_record(source_review)
        self.request=dict(schema='plan069-video-setup-recovery-request/v1',record_kind='actual',candidate='D9',job_id=JOB,ledger_path=str(self.ledger.path),
            review=self.review,authorization=self.authorization,source_review=self.source_review,original_setup=self.original,
            runtime_environment=dict(recipe=file_record(FRAME_RECIPE),runtime_profile=self.map_proposal['profile']['runtime_profile'],candidate='D9',record_kind='actual'))
        self.request_path=self.root/'requests'/(JOB+'.json');write_json(self.request_path,self.request);self.request_record=file_record(self.request_path)
        self.worker=file_record(ROOT/'scripts/basketball_vipe_video_setup_recovery.py');self.executable=file_record(sys.executable)
        self.command=[sys.executable,self.worker['path'],'--request',str(self.request_path),'--output',str(self.root/'jobs'/JOB)]
        self.evidence=dict(request=self.request_record,review=self.review,authorization=self.authorization,source_review=self.source_review,worker=self.worker,executable=self.executable)

    def tearDown(self):
        self.temporary.cleanup()

    def authorize(self):
        reading=dict(budget_snapshot(self.root),gpu_pids=[],device_bytes=0)
        with patch('vipe_benchmark.execution.resources',return_value=reading):
            return self.ledger.authorize_depth_setup_recovery(self.request_record,command=self.command,worker=self.worker,executable=self.executable)

    def test_new_do_recovery_preserves_failed_consumption_and_original_byte_limits(self):
        before=self.ledger.path.read_bytes()
        normalized=validate_recovery_request(self.request_record,self.ledger.events(),self.root)
        self.assertEqual(normalized['allocation']['setup_seconds'],1200)
        self.assertEqual(normalized['byte_limits']['artifact_bytes'],self.original_grant['resource_snapshot']['artifact_bytes']+9*2**30)
        self.assertEqual(self.ledger.path.read_bytes(),before)
        grant=self.authorize()
        self.assertEqual(grant['seconds'],1200)
        self.assertEqual(self.ledger.states()['plan069-D9-setup-001']['status'],'failed')
        with self.assertRaisesRegex(ValueError,'already authorized or consumed'):
            self.authorize()

    def test_current_do_cannot_authorize_recovery_by_reusing_original_approval(self):
        self.request['authorization']=self.old_do
        self.request_path.unlink();write_json(self.request_path,self.request)
        before=self.ledger.path.read_bytes()
        with self.assertRaisesRegex(ValueError,'separately approved'):
            validate_recovery_request(file_record(self.request_path),self.ledger.events(),self.root)
        self.assertEqual(self.ledger.path.read_bytes(),before)

    def test_missing_or_mutated_network_guard_source_record_blocks_authority(self):
        original_source=read_json(self.source_review['path'])
        for missing in (True,False):
            with self.subTest(missing=missing):
                source=copy.deepcopy(original_source)
                guard=next(row for row in source['local_sources'] if Path(row['path']).name=='offline-python.py')
                if missing:source['local_sources'].remove(guard)
                else:guard['sha256']='0'*64
                path=Path(self.source_review['path']);path.unlink();write_json(path,source)
                self.request['source_review']=file_record(path)
                self.request_path.unlink();write_json(self.request_path,self.request)
                before=self.ledger.path.read_bytes()
                with self.assertRaisesRegex(ValueError,'source closure'):
                    validate_recovery_request(file_record(self.request_path),self.ledger.events(),self.root)
                self.assertEqual(self.ledger.path.read_bytes(),before)

    def test_active_request_requires_checked_new_reservation(self):
        with self.assertRaisesRegex(ValueError,'checked recovery grant'):
            validate_recovery_request(self.request_record,self.ledger.events(),self.root,require_reservation=True)
        self.authorize()
        reading=dict(budget_snapshot(self.root),gpu_pids=[],device_bytes=0)
        with patch('vipe_benchmark.execution.resources',return_value=reading):
            self.ledger.reserve(JOB,self.command,self.evidence)
        result=validate_recovery_request(self.request_record,self.ledger.events(),self.root,require_reservation=True)
        self.assertEqual(result['resource_snapshot']['gpu_pids'],[])
        self.ledger.finish(JOB,'failed',1.,cleanup_confirmed=True,cleanup_uncertain=False,surviving_pids=[])
        with self.assertRaisesRegex(ValueError,'live exact recovery'):
            validate_recovery_request(self.request_record,self.ledger.events(),self.root,require_reservation=True)

    def test_changed_original_failed_inputs_cannot_be_reused(self):
        self.model.write_bytes(b'other-data')
        with self.assertRaisesRegex(ValueError,'changed file'):
            self.authorize()
        self.assertFalse(any(row['event']=='depth_setup_recovery_authorized' for row in self.ledger.events()))

    def test_mutated_worker_command_cannot_be_reserved(self):
        self.authorize()
        with self.assertRaisesRegex(ValueError,'reservation differs'):
            self.ledger.reserve(JOB,self.command+['--unapproved'],self.evidence)
        self.assertNotIn(JOB,self.ledger.states())
