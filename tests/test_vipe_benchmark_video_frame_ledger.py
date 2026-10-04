"""D10 allocations recheck the sealed D9 prerequisite under the current lock."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import test_vipe_benchmark_video_frame_authorization as fixtures
from vipe_benchmark.config import load
from vipe_benchmark.depth_admission import local_source_records
from vipe_benchmark.files import file_record, object_hash, read_json, write_json
from vipe_benchmark.ledger import Ledger


class FrameLedgerTests(unittest.TestCase):
    recovery_prerequisite_fixture=fixtures.FrameAuthorityTests.recovery_prerequisite_fixture
    authorization=fixtures.FrameAuthorityTests.authorization

    def setUp(self):
        fixtures.FrameAuthorityTests.setUp(self)
        record,prefix,rows=self.recovery_prerequisite_fixture()
        rows[0].update(resource='setup',elapsed_seconds=0)
        self.rows=rows
        self.publish_rows()
        self.amendment.update(D9_runtime_qualification=record,
            D9_qualification_ledger_prefix=file_record(self.root/'qualification-prefix.jsonl'))
        self.ledger=Ledger(self.root/'ledger.jsonl',load())
        self.source_path=self.root/'D10-source.json'
        write_json(self.source_path,dict(schema='plan069-depth-source-review/v1',status='passed',
            candidate='D10',source_revision=self.proposal['candidate_config']['code']['revision'],
            profile_inventory=self.proposal['profile_inventory'],local_sources=local_source_records('D10'),
            reviewer='CPU fixture reviewer'))
        self.source=file_record(self.source_path)
        self.lineage=patch('vipe_benchmark.depth_recovery_lineage.accepted_setup_lineage',
            return_value=dict(finish=dict(sequence=0)))
        self.lineage.start();self.addCleanup(self.lineage.stop)

    def publish_rows(self):
        previous=None
        for index,row in enumerate(self.rows):
            row.update(sequence=index,previous_sha256=previous)
            row.pop('event_sha256',None);row['event_sha256']=object_hash(row)
            previous=row['event_sha256']
        raw=''.join(json.dumps(row)+'\n' for row in self.rows)
        (self.root/'ledger.jsonl').write_text(raw)
        (self.root/'qualification-prefix.jsonl').write_text(raw)

    def records(self):
        auth=file_record(self.authorization());return read_json(auth['path'])['review'],auth

    def setup(self):
        review,auth=self.records()
        with patch('vipe_benchmark.execution.resources',return_value=dict(download_bytes=0,artifact_bytes=0)):
            return self.ledger.authorize_depth_setup('D10',review,auth,self.source)

    def attempt(self):
        review,auth=self.records()
        evidence=self.root/'admission.json'
        write_json(evidence,dict(schema='plan069-depth-admission-result/v1',status='passed',candidate='D10',
            proposal_sha256=object_hash(self.proposal),review=review,authorization=auth,source_review=self.source))
        with patch.object(self.ledger,'_depth_command'):
            return self.ledger.authorize_depth_attempt('D10',review,auth,self.source,file_record(evidence),
                request={},worker={},executable={},command=[])

    def test_setup_checks_actual_prefix_under_lock_and_preserves_no_active_gate(self):
        from vipe_benchmark.depth_video_frame_authorization import validate_D9_prerequisite
        with patch('vipe_benchmark.depth_video_frame_authorization.validate_D9_prerequisite',
                   wraps=validate_D9_prerequisite) as checked:
            grant=self.setup()
        self.assertEqual(grant['event'],'depth_setup_authorized')
        self.assertEqual(checked.call_args.kwargs['current_events'][:-1],self.rows)
        self.assertIs(checked.call_args.kwargs['allow_owned_active'],False)

    def test_both_allocations_reject_missing_protected_qualification_charge(self):
        for method in (self.setup,self.attempt):
            with self.subTest(method=method.__name__):
                self.rows=self.rows[:1];self.publish_rows()
                self.amendment['D9_qualification_ledger_prefix']=file_record(self.root/'qualification-prefix.jsonl')
                before=self.ledger.path.read_bytes()
                with self.assertRaisesRegex(ValueError,'finalization charge required'):
                    method()
                self.assertEqual(self.ledger.path.read_bytes(),before)

    def test_changed_qualification_prefix_rejects_fresh_setup_without_append(self):
        path=self.root/'qualification-prefix.jsonl'
        row=dict(event='fixture',sequence=0,previous_sha256=None);row['event_sha256']=object_hash(row)
        path.write_text(json.dumps(row)+'\n')
        self.amendment['D9_qualification_ledger_prefix']=file_record(path)
        before=self.ledger.path.read_bytes()
        with self.assertRaisesRegex(ValueError,'prefix differs'):
            self.setup()
        self.assertEqual(self.ledger.path.read_bytes(),before)

    def test_active_attempt_rejects_fresh_allocation_before_prerequisite(self):
        self.rows.append(dict(event='reserve',job_id='foreign',resource='cpu',seconds=10))
        self.publish_rows()
        before=self.ledger.path.read_bytes()
        with patch('vipe_benchmark.depth_video_frame_authorization.validate_D9_prerequisite') as checked:
            for method in (self.setup,self.attempt):
                with self.subTest(method=method.__name__),self.assertRaisesRegex(ValueError,'active attempt'):
                    method()
        checked.assert_not_called();self.assertEqual(self.ledger.path.read_bytes(),before)
