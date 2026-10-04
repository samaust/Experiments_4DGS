"""Recovery-only slot accounting and native entry with private CPU fixtures."""
from copy import deepcopy
import os
from pathlib import Path
from unittest.mock import patch

import test_vipe_benchmark_depth_recovery_lineage as lineage_fixtures
from vipe_benchmark.budgets import budget_snapshot, directory_bytes
from vipe_benchmark.config import load
from vipe_benchmark.depth_map_allowance import (remaining_map_allocation, bind_slot_byte_budget,
    check_slot_byte_budget, owned_slot_bytes, historical_slot_byte_guard)
from vipe_benchmark.files import file_record, object_hash, read_json, write_json
from vipe_benchmark.ledger import Ledger
from vipe_benchmark.video_depth import video_slot_guard, admitted_video_request


class RecoveryMapIntegrationTests(lineage_fixtures.RecoveryLineageTests):
    request: dict
    events: list

    def prepare_maps(self, *, active=False):
        self.maps['allocation'].update(artifact_bytes=2**20, gpu_seconds=120)
        # The independent authority validator is isolated by the parent fixture;
        # this integration exercises real ledger records and retained inodes.
        review_path = Path(self.authority['review']['path']); review_path.unlink()
        self.authority['review'] = self.document(review_path, dict(proposals=[self.maps]))
        self.normalized.update(self.authority)
        self.grant.update(self.authority)
        self.reserve['evidence'].update(self.authority)
        request_path = Path(self.request['path']); request_path.unlink()
        self.request = self.document(request_path, dict(self.authority, original_setup=self.original))
        self.normalized['request'] = self.request
        self.grant['request'] = self.request
        self.reserve['evidence']['request'] = self.request
        self.result.update(self.authority, request=self.request); self.publish()
        self.ledger = Ledger(self.root / 'ledger.jsonl', load())
        with self.ledger.locked() as (stream, events):
            original_grant = self.ledger._append(stream, events, dict(event='depth_setup_authorized',
                candidate='D9', resource_snapshot=dict(download_bytes=0, artifact_bytes=0)))
            for row in self.events:
                self.ledger._append(stream, events, {k: v for k, v in row.items()
                    if k not in ('sequence', 'event_sha256')})
        self.events = self.ledger.events()
        self.normalized['lineage']['grant'] = original_grant
        self.stage = remaining_map_allocation(self.maps, self.setup, self.events, self.root, self.assets())
        self.budget = bind_slot_byte_budget(self.maps, self.stage, self.events, self.root, budget_snapshot(self.root))
        self.qualification = self.document(self.root / 'qualification.json', dict(status='passed'))
        self.admission = self.document(self.root / 'admission.json', dict(
            schema='plan069-depth-admission-result/v1', status='passed', candidate='D9',
            completed_setup=self.setup, assets=self.assets(), qualification=self.qualification,
            source_review=self.authority['source_review'], runtime=dict(receipt=self.qualification)))
        with self.ledger.locked() as (stream, events):
            self.map_grant = self.ledger._append(stream, events, dict(event='depth_attempt_authorized',
                candidate='D9', admission=self.admission, proposal_sha256=object_hash(self.maps),
                map_stage_allowance=self.stage, slot_byte_budget=self.budget, **self.authority))
            if active:
                self.ledger._append(stream, events, dict(event='reserve', job_id='plan069-D9-maps-001',
                    resource='gpu', seconds=120, evidence=dict(admission=self.admission, **self.authority)))
        self.video_request = dict(component='D9', candidate='D9', setup=self.setup,
            admission=self.admission, max_seconds=120, **self.authority)

    def test_recovery_maps_dispatch_preserves_failed_original_and_paid_model_stage(self):
        self.prepare_maps()
        self.assertEqual(self.stage['setup'], self.setup)
        self.assertEqual(self.stage['original_setup'], self.original)
        self.assertEqual(self.stage['allocation']['download_bytes'], 56)
        self.assertEqual(self.budget['absolute_limits']['artifact_bytes'], 2**20)
        check_slot_byte_budget(self.maps, self.budget, self.root, budget_snapshot(self.root))

    def test_only_accepted_recovery_pair_gets_inode_union(self):
        self.prepare_maps()
        plain = owned_slot_bytes(self.root, 'D9')
        union = owned_slot_bytes(self.root, 'D9', recovery_lineage=self.stage['recovery_lineage'])
        # directory_bytes expects a tree; the model's allocation is inferred by
        # removing its one duplicate alias from the pair's otherwise equal scans.
        info = (self.job / 'model.bin').stat()
        self.assertEqual(plain - union, max(info.st_size, info.st_blocks * 512))
        other = self.root / 'jobs/plan069-D9-setup-other-001'; other.mkdir()
        os.link(self.old_checkpoint['path'], other / 'model.bin')
        self.assertEqual(owned_slot_bytes(self.root, 'D9', recovery_lineage=self.stage['recovery_lineage']),
                         union + max(info.st_size, info.st_blocks * 512))

    def test_active_exact_native_maps_admission_allows_clean_recovery_lineage(self):
        self.prepare_maps(active=True)
        guard = video_slot_guard(self.video_request, self.ledger)
        guard()
        historical_slot_byte_guard(self.ledger, 'D9')()

    def test_foreign_active_or_unbound_map_admission_cannot_use_recovery(self):
        self.prepare_maps(active=True)
        with self.ledger.locked() as (stream, events):
            self.ledger._append(stream, events, dict(event='reserve', job_id='foreign', resource='gpu'))
        with self.assertRaisesRegex(ValueError, 'active attempt'):
            video_slot_guard(self.video_request, self.ledger)

    def test_missing_protected_marker_or_changed_clean_finish_rejected(self):
        self.prepare_maps()
        altered = deepcopy(self.budget)
        altered['recovery_lineage']['finish_event_sha256'] = 'foreign'
        with self.assertRaisesRegex(ValueError, 'protected accepted recovery'):
            check_slot_byte_budget(self.maps, altered, self.root, budget_snapshot(self.root))
        self.map_grant['slot_byte_budget'].pop('recovery_lineage')
        # Supply the altered grant via the public native boundary; receipt bytes
        # and accepted lineage still exist, but marker omission cannot broaden it.
        events = self.ledger.events(); events[-1]['slot_byte_budget'].pop('recovery_lineage')
        with patch.object(self.ledger, 'events', return_value=events):
            with self.assertRaisesRegex(ValueError, 'whole-slot setup lineage'):
                video_slot_guard(self.video_request, self.ledger)

    def test_original_failed_setup_receipt_never_routes_to_recovery_credit(self):
        self.prepare_maps()
        old_result = self.document(self.old / 'result.json', dict(schema='plan069-video-setup-result/v1',
            status='failed', record_kind='actual', candidate='D9'))
        with self.assertRaises(ValueError):
            remaining_map_allocation(self.maps, old_result, self.ledger.events(), self.root, self.assets())

    def test_default_recovery_gate_remains_closed_during_maps(self):
        self.prepare_maps(active=True)
        with self.assertRaisesRegex(ValueError, 'active attempt'):
            remaining_map_allocation(self.maps, self.setup, self.ledger.events(), self.root, self.assets())

    def test_native_entry_accepts_clean_recovery_without_promoting_old_failed_job(self):
        self.prepare_maps(active=True)
        request = dict(self.video_request, schema='plan069-video-depth-request/v1', record_kind='actual',
            id='plan069-D9-maps-001', job_id='plan069-D9-maps-001', ledger_path=str(self.ledger.path),
            qualification=self.qualification)
        # Process-registration and interpreter qualification are independently
        # covered by existing native entry tests; this isolates setup routing.
        with patch('vipe_benchmark.depth_setup._active_reservation', return_value=(self.root, self.ledger.config)), \
             patch('vipe_benchmark.video_depth.validate_runtime_interpreter'):
            accepted = admitted_video_request(request, self.root / 'jobs/plan069-D9-maps-001',
                self.ledger.config, ledger=self.ledger, request_path=self.root / 'request.json')
        self.assertEqual(accepted['job_id'], 'plan069-D9-setup-recovery-001')

    def test_active_map_exception_requires_exact_protected_authority(self):
        self.prepare_maps(active=True)
        events = self.ledger.events()
        events[-2]['source_review'] = self.qualification
        with self.assertRaisesRegex(ValueError, 'active recovery map authority'):
            remaining_map_allocation(self.maps, self.setup, events, self.root, self.assets(),
                                     active_map_admission=self.admission)
