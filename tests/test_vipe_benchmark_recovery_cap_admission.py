"""Recovered D9 map admission inherits protected caps without changing its DO."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from vipe_benchmark.config import ROOT, load
from vipe_benchmark.files import file_record, object_hash, read_json, write_json
from vipe_benchmark.ledger import Ledger


class RecoveryCapAllocationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        original = ROOT / 'docs/research/vipe-alternatives/plan031-execution/depth-approval-001.json'
        self.original = file_record(original)
        self.cap = read_json(original)['cap_approval']
        proposal = dict(candidate='D9', max_attempts=1, schema='plan069-depth-execution-proposal/v1',
            allocation=dict(download_bytes=100, artifact_bytes=2**20, gpu_seconds=120,
                cpu_seconds=100, setup_seconds=100, device_bytes=2**20))
        self.proposal = proposal
        def doc(name,value):
            path = self.root / name
            write_json(path, value)
            return file_record(path)
        self.review = doc('review.json', dict(schema='plan069-depth-execution-review/v1',
            status='REVIEW', proposals=[proposal]))
        # Truthful distinct recovery DO has no repeated cap keys.
        self.authorization = doc('authorization.json', dict(schema='plan069-depth-user-authorization/v1',
            status='DO', review=self.review, setup_recovery_approval=dict(status='approved'),
            candidate_approvals=[dict(candidate='D9',status='approved',max_attempts=1,
                proposal_sha256=object_hash(proposal))]))
        self.worker = file_record(ROOT / 'scripts/basketball_vipe_video_actual.py')
        self.source = doc('source.json', dict(local_sources=[self.worker]))
        self.setup = doc('jobs/plan069-D9-setup-recovery-002/result.json',dict(status='complete'))
        self.ledger = Ledger(self.root/'ledger.jsonl',dict(load(),new_download_gib_limit=110,new_artifact_disk_gib_limit=210))
        with self.ledger.locked() as (stream,events):
            self.original_grant = self.ledger._append(stream,events,dict(event='depth_setup_authorized',
                candidate='D9',authorization=self.original,resource_snapshot=dict(download_bytes=0,artifact_bytes=0)))
        self.accepted = dict(map_proposal=proposal,authorization=self.authorization,
            lineage=dict(grant=self.original_grant))
        self.stage = dict(allocation=proposal['allocation'],credited_assets_bytes=0,setup=self.setup,
            setup_finish_event_sha256='fixture-complete-setup')
        self.admission = doc('admission.json',dict(schema='plan069-depth-admission-result/v1',status='passed',candidate='D9',
            proposal_sha256=object_hash(proposal),review=self.review,authorization=self.authorization,
            source_review=self.source,completed_setup=self.setup,commercial={},assets=[],runtime={},
            live=dict(ledger_head_sha256=self.ledger.events()[-1]['event_sha256'])))
        request = doc('requests/plan069-D9-maps-001.json',dict(candidate='D9',job_id='plan069-D9-maps-001',
            record_kind='actual',review=self.review,authorization=self.authorization,
            source_review=self.source,admission=self.admission,setup=self.setup))
        self.binding = dict(request=request,worker=self.worker,executable=file_record(sys.executable),
            command=[sys.executable,self.worker['path'],'--request',request['path'],'--output',str(self.root/'jobs/plan069-D9-maps-001')])

    def allocate(self):
        def qualified(*args,**kwargs):
            return [] if kwargs['cap_approval']==self.cap else ['approved versioned cap amendment required']
        # Fake runtime qualification/host resource boundaries. The actual public
        # allocator, file bindings, lock, single-use rules and inherited records run.
        with patch('vipe_benchmark.depth_admission.review',side_effect=qualified), \
             patch('vipe_benchmark.execution.resources',return_value=dict(gpu_pids=[],download_bytes=0,artifact_bytes=32768,device_bytes=0)), \
             patch('vipe_benchmark.depth_recovery_lineage.accepted_setup_lineage',return_value=self.accepted), \
             patch('vipe_benchmark.depth_map_allowance.remaining_map_allocation',return_value=self.stage):
            return self.ledger.authorize_depth_attempt('D9',self.review,self.authorization,self.source,self.admission,**self.binding)

    def test_truthful_recovery_do_allocates_original_map_slot_once(self):
        grant=self.allocate()
        self.assertEqual(grant['event'],'depth_attempt_authorized')
        self.assertEqual(grant['authorization'],self.authorization)
        self.assertNotIn('cap_approval',read_json(self.authorization['path']))
        with self.assertRaisesRegex(ValueError,'already authorized or consumed'):self.allocate()

    def test_wrong_recovery_map_authority_stops_before_allocation(self):
        before=self.ledger.events()
        self.accepted['authorization']=self.original
        with self.assertRaisesRegex(ValueError,'exact map approval'):self.allocate()
        self.assertEqual(self.ledger.events(),before)

    def test_changed_recovery_proposal_stops_before_allocation(self):
        before=self.ledger.events()
        self.accepted['map_proposal']=dict(self.proposal,max_attempts=2)
        with self.assertRaisesRegex(ValueError,'exact map approval'):self.allocate()
        self.assertEqual(self.ledger.events(),before)

    def test_missing_original_cap_authority_is_not_fabricated(self):
        path=self.root/'missing-cap-do.json'
        write_json(path,dict(status='DO'))
        self.accepted['lineage']['grant']=dict(self.original_grant,authorization=file_record(path))
        before=self.ledger.events()
        with self.assertRaisesRegex(ValueError,'original approved cap authority missing'):self.allocate()
        self.assertEqual(self.ledger.events(),before)
