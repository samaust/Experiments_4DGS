"""Admission seam credits only retained assets from an accepted setup stage."""
import copy
import unittest
from pathlib import Path
from unittest.mock import patch
from vipe_benchmark.files import file_record, object_hash, read_json, write_json
from vipe_benchmark.depth_map_allowance import remaining_map_allocation
import test_vipe_benchmark_depth_admission as fixtures

class MapAllowanceTests(unittest.TestCase):
    setUp = fixtures.DepthAdmissionTests.setUp
    tearDown = fixtures.DepthAdmissionTests.tearDown
    decide = fixtures.DepthAdmissionTests.decide

    def prepare_completed_setup(self):
        self.setup_root = self.root / 'jobs/plan069-D5-setup-001'
        self.setup_root.mkdir(parents=True)
        self.asset.rename(self.setup_root / 'model.bin')
        self.asset = self.setup_root / 'model.bin'
        self.assets[0]['record'] = file_record(self.asset)
        write_json(self.root / 'execution-review.json', dict(schema='plan069-depth-execution-review/v1',
            status='REVIEW', proposals=[self.proposal]))
        self.review = file_record(self.root / 'execution-review.json')
        self.approval['max_attempts'] = 1
        write_json(self.root / 'authorization.json', dict(schema='plan069-depth-user-authorization/v1',
            status='DO', review=self.review, candidate_approvals=[self.approval]))
        self.authorization = file_record(self.root / 'authorization.json')
        request = self.root / 'requests/plan069-D5-setup-001.json'
        write_json(request, dict(schema='plan069-depth-setup-request/v1', record_kind='actual',
            candidate='D5', job_id='plan069-D5-setup-001', review=self.review,
            authorization=self.authorization, ledger_path=str(self.root / 'ledger.jsonl')))
        self.setup = self.setup_root / 'result.json'
        write_json(self.setup, dict(schema='plan069-depth-setup-result/v1', record_kind='actual',
            candidate='D5', job_id='plan069-D5-setup-001', status='complete',
            review=self.review, authorization=self.authorization, assets=self.assets,
            source_revision=self.proposal['candidate_config']['code']['revision'],
            weight_revision=self.proposal['candidate_config']['weights']['revision'],
            bytes_received=self.asset.stat().st_size))
        self.events = [dict(event='depth_setup_authorized', candidate='D5',
            review=self.review, authorization=self.authorization,
            proposal_sha256=object_hash(self.proposal)),
            dict(event='reserve', job_id='plan069-D5-setup-001', resource='setup',
                evidence=dict(request=file_record(request), review=self.review, authorization=self.authorization)),
            dict(event='finish', job_id='plan069-D5-setup-001', resource='setup',
                status='complete', result=file_record(self.setup), cleanup_confirmed=True,
                cleanup_uncertain=False, surviving_pids=[], deadline_exceeded=False, event_sha256='b'*64)]
        receipt = Path(self.runtime['receipt']['path'])
        document = read_json(receipt)
        document.update(assets=self.assets, setup=file_record(self.setup))
        receipt.unlink()
        write_json(receipt, document)
        self.runtime['receipt'] = file_record(receipt)

    def test_allowance_helper_is_bound_in_every_candidate_source_closure(self):
        from vipe_benchmark.depth_admission import LOCAL_ADAPTERS, local_source_records
        for candidate in LOCAL_ADAPTERS:
            with self.subTest(candidate=candidate):
                self.assertIn("depth_map_allowance.py",
                    [Path(row["path"]).name for row in local_source_records(candidate)])

    def test_completed_retained_assets_are_not_reserved_twice_at_admission(self):
        self.prepare_completed_setup()
        for key, cap in [('download_bytes','new_download_gib_limit'), ('artifact_bytes','new_artifact_disk_gib_limit')]:
            self.live['used'][key] = self.config[cap] * 2**30 - self.proposal['allocation'][key] + 1
        self.assertIn('download_bytes allocation exceeds current cap or lacks accounting', self.decide())
        self.assertEqual(self.decide(completed_setup=file_record(self.setup), setup_events=self.events,
            run_root=self.root), [])
        remaining = remaining_map_allocation(self.proposal, file_record(self.setup), self.events,
            self.root, self.assets)
        self.assertEqual(remaining['allocation']['download_bytes'], 20-self.asset.stat().st_size)
        self.assertEqual(remaining['allocation']['artifact_bytes'], 100-self.asset.stat().st_size)
        self.assertEqual(remaining['allocation']['gpu_seconds'],100)
        self.assertEqual(remaining['setup_finish_event_sha256'], 'b'*64)

    def test_setup_credit_does_not_reset_used_totals_or_allow_excess_growth(self):
        self.prepare_completed_setup()
        credit = self.asset.stat().st_size
        cap = self.config['new_artifact_disk_gib_limit'] * 2**30
        self.live['used']['artifact_bytes'] = cap - (100-credit) + 1
        self.live['used']['download_bytes'] = credit
        before = copy.deepcopy(self.live)
        blockers = self.decide(completed_setup=file_record(self.setup), setup_events=self.events,
            run_root=self.root)
        self.assertIn('artifact_bytes allocation exceeds current cap or lacks accounting', blockers)
        self.assertEqual(self.live, before)
        self.live['used']['artifact_bytes'] = 0
        self.assertIn('setup asset credit is absent from live used totals',
            self.decide(completed_setup=file_record(self.setup), setup_events=self.events, run_root=self.root))

    def test_failed_unclean_or_wrong_ledger_setup_receipts_cannot_credit(self):
        self.prepare_completed_setup()
        for changes in ({'status':'failed'}, {'cleanup_confirmed':False},
                        {'cleanup_uncertain':True}, {'surviving_pids':[123]},
                        {'deadline_exceeded':True}, {'result':self.assets[0]['record']}):
            events = copy.deepcopy(self.events)
            events[-1].update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                remaining_map_allocation(self.proposal, file_record(self.setup), events, self.root,self.assets)
        with self.assertRaises(ValueError):
            remaining_map_allocation(self.proposal, file_record(self.setup), self.events[:-1], self.root,self.assets)
        with self.assertRaises(ValueError):
            remaining_map_allocation(self.proposal, file_record(self.setup), self.events, self.root/'foreign',self.assets)

    def test_completed_setup_keeps_its_old_source_proof_with_current_map_review(self):
        self.prepare_completed_setup()
        self.events[0]['source_review'] = dict(path='historical-source-review',sha256='a'*64,bytes=1)
        self.live['used'].update(download_bytes=12, artifact_bytes=12)
        self.assertEqual(self.decide(completed_setup=file_record(self.setup), setup_events=self.events,
            run_root=self.root), [])

    def test_foreign_request_ledger_cannot_receive_credit(self):
        self.prepare_completed_setup()
        request = Path(self.events[1]['evidence']['request']['path'])
        document = read_json(request)
        document['ledger_path'] = str(self.root / 'other-ledger.jsonl')
        request.unlink()
        write_json(request, document)
        self.events[1]['evidence']['request'] = file_record(request)
        with self.assertRaisesRegex(ValueError,'clean exact setup'):
            remaining_map_allocation(self.proposal,file_record(self.setup),self.events,self.root,self.assets)

    def test_changed_deleted_or_foreign_assets_cannot_receive_credit(self):
        self.prepare_completed_setup()
        self.asset.write_bytes(b'changed model')
        with self.assertRaises(ValueError):
            remaining_map_allocation(self.proposal, file_record(self.setup), self.events,self.root,self.assets)
        self.asset.unlink()
        with self.assertRaises(FileNotFoundError):
            remaining_map_allocation(self.proposal, file_record(self.setup), self.events,self.root,self.assets)

    def test_wrong_source_or_review_proposal_cannot_receive_credit(self):
        self.prepare_completed_setup()
        proposal = copy.deepcopy(self.proposal)
        proposal['candidate_config']['code']['revision'] = 'wrong-source'
        with self.assertRaisesRegex(ValueError,'source and model'):
            remaining_map_allocation(proposal,file_record(self.setup),self.events,self.root,self.assets)
        events = copy.deepcopy(self.events)
        events[0]['proposal_sha256'] = 'wrong-review'
        with self.assertRaisesRegex(ValueError,'approval lineage'):
            remaining_map_allocation(self.proposal,file_record(self.setup),events,self.root,self.assets)

    def test_locked_allocator_recomputes_remaining_bounds_from_its_own_ledger(self):
        import sys
        import time
        from vipe_benchmark.config import ROOT
        from vipe_benchmark.ledger import Ledger
        self.prepare_completed_setup()
        ledger = Ledger(self.root / 'ledger.jsonl', self.config)
        initial = dict(gpu_pids=[], download_bytes=self.config['new_download_gib_limit']*2**30-20,
                       artifact_bytes=self.config['new_artifact_disk_gib_limit']*2**30-100,device_bytes=0)
        with patch('vipe_benchmark.execution.resources', return_value=initial):
            ledger.authorize_depth_setup('D5',self.review,self.authorization,self.source_review)
            ledger.reserve('plan069-D5-setup-001',['bounded-fixture-setup'],self.events[1]['evidence'])
            ledger.finish('plan069-D5-setup-001','complete',1.,result=file_record(self.setup),
                cleanup_confirmed=True,cleanup_uncertain=False,surviving_pids=[])
        events = ledger.events()
        self.live.update(sampled_unix=time.time(),ledger_head_sha256=events[-1]['event_sha256'])
        for key,cap in [('download_bytes','new_download_gib_limit'),('artifact_bytes','new_artifact_disk_gib_limit')]:
            self.live['used'][key] = self.config[cap]*2**30-self.proposal['allocation'][key]+1
        admission_path = self.root / 'map-admission.json'
        write_json(admission_path,dict(schema='plan069-depth-admission-result/v1',status='passed',candidate='D5',
            proposal_sha256=object_hash(self.proposal),review=self.review,authorization=self.authorization,
            source_review=self.source_review,commercial=self.commercial,assets=self.assets,runtime=self.runtime,
            live=self.live,completed_setup=file_record(self.setup)))
        admission = file_record(admission_path)
        request_path = self.root / 'requests/plan069-D5-maps-001.json'
        write_json(request_path,dict(candidate='D5',job_id='plan069-D5-maps-001',record_kind='actual',
            review=self.review,authorization=self.authorization,source_review=self.source_review,
            admission=admission,setup=file_record(self.setup)))
        worker = file_record(ROOT / 'scripts/basketball_vipe_depth_single_maps.py')
        command = [sys.executable,worker['path'],'--request',str(request_path),'--output',
            str(self.root/'jobs/plan069-D5-maps-001')]
        reading = dict(initial,**{key:self.live['used'][key] for key in ['download_bytes','artifact_bytes']})
        excess = dict(reading, artifact_bytes=self.config['new_artifact_disk_gib_limit']*2**30-88+1)
        with patch('vipe_benchmark.depth_map_allowance.owned_slot_bytes',return_value=12), \
                patch('vipe_benchmark.execution.resources',return_value=excess), \
                self.assertRaisesRegex(ValueError,'artifact_bytes depth allocation exceeds live cap'):
            ledger.authorize_depth_attempt('D5',self.review,self.authorization,self.source_review,
                admission,command=command,request=file_record(request_path),worker=worker,
                executable=file_record(sys.executable))
        self.assertEqual(ledger.events(), events)
        with patch('vipe_benchmark.depth_map_allowance.owned_slot_bytes',return_value=12), \
                patch('vipe_benchmark.execution.resources',return_value=reading):
            event = ledger.authorize_depth_attempt('D5',self.review,self.authorization,self.source_review,
                admission,command=command,request=file_record(request_path),worker=worker,
                executable=file_record(sys.executable))
        self.assertEqual(event['map_stage_allowance']['credited_assets_bytes'],12)
        self.assertEqual(event['map_stage_allowance']['allocation']['artifact_bytes'],88)
        self.assertEqual(event['resource_snapshot']['artifact_bytes'],reading['artifact_bytes'])
        self.assertEqual(event['map_stage_allowance']['setup_finish_event_sha256'],events[-1]['event_sha256'])


class WholeSlotBudgetTests(unittest.TestCase):
    def test_setup_runtime_and_source_costs_leave_no_second_full_allocation(self):
        from vipe_benchmark.depth_map_allowance import bind_slot_byte_budget, check_slot_byte_budget
        proposal = dict(candidate='D11',allocation=dict(download_bytes=100,artifact_bytes=200))
        stage = dict(setup=dict(path='accepted-result'), setup_finish_event_sha256='f'*64)
        events = [dict(event='depth_setup_authorized',candidate='D11',
                       resource_snapshot=dict(download_bytes=1000,artifact_bytes=2000))]
        with patch('vipe_benchmark.depth_map_allowance.owned_slot_bytes',return_value=140):
            budget = bind_slot_byte_budget(proposal,stage,events,'/tmp',
                dict(download_bytes=1090,artifact_bytes=2180))
            self.assertEqual(budget['shared_setup_artifact_bytes'],40)
            check_slot_byte_budget(proposal,budget,'/tmp',dict(download_bytes=1100,artifact_bytes=2200))
            for reading in (dict(download_bytes=1101,artifact_bytes=2200),
                            dict(download_bytes=1100,artifact_bytes=2201)):
                with self.subTest(reading=reading), self.assertRaisesRegex(ValueError,'whole-slot'):
                    check_slot_byte_budget(proposal,budget,'/tmp',reading)
        with patch('vipe_benchmark.depth_map_allowance.owned_slot_bytes',return_value=161), \
                self.assertRaisesRegex(ValueError,'retained candidate'):
            check_slot_byte_budget(proposal,budget,'/tmp',dict(download_bytes=1100,artifact_bytes=2200))
        with patch('vipe_benchmark.depth_map_allowance.owned_slot_bytes',return_value=140):
            check_slot_byte_budget(proposal,budget,'/tmp',
                dict(download_bytes=999999,artifact_bytes=999999),historical=True)

    def test_owned_scope_counts_preserved_revisions_and_excludes_other_candidates(self):
        import tempfile
        from vipe_benchmark.budgets import directory_bytes
        from vipe_benchmark.depth_map_allowance import owned_slot_bytes
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('setup-001','maps-001','clips-001','anchor-previews-001','anchor-previews-002'):
                folder = root/'jobs'/('plan069-D11-'+name)
                folder.mkdir(parents=True)
                (folder/'retained.bin').write_bytes(b'preserved')
            other = root/'jobs/plan069-D5-maps-001'
            other.mkdir()
            (other/'other.bin').write_bytes(b'other slot')
            self.assertEqual(owned_slot_bytes(root,'D11'),
                sum(directory_bytes(path) for path in (root/'jobs').glob('plan069-D11-*')))
            self.assertLess(owned_slot_bytes(root,'D11'),directory_bytes(root/'jobs'))


    def test_late_cpu_diagnostics_reject_new_downloads_without_charging_other_jobs(self):
        import tempfile
        from types import SimpleNamespace
        from vipe_benchmark.depth_map_allowance import historical_slot_byte_guard
        proposal = dict(candidate='D11',allocation=dict(download_bytes=100,artifact_bytes=200))
        budget = dict(schema='plan069-depth-slot-byte-budget/v1',candidate='D11',
            proposal_sha256=object_hash(proposal),shared_setup_artifact_bytes=40,
            setup_baseline=dict(download_bytes=1000,artifact_bytes=2000),
            absolute_limits=dict(download_bytes=1100,artifact_bytes=2200))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_json(root/'review.json',dict(proposals=[proposal]))
            ledger = SimpleNamespace(path=root/'ledger.jsonl',events=lambda:[dict(
                event='depth_attempt_authorized',candidate='D11',slot_byte_budget=budget,
                review=file_record(root/'review.json'))])
            reading = dict(download_bytes=999999,artifact_bytes=999999)
            with patch('vipe_benchmark.depth_map_allowance.owned_slot_bytes',return_value=140), \
                    patch('vipe_benchmark.budgets.budget_snapshot',return_value=reading):
                guard = historical_slot_byte_guard(ledger,'D11')
                guard()
                reading['download_bytes'] += 1
                with self.assertRaisesRegex(ValueError,'must not acquire'):
                    guard()
