"""Prospective unrelated setup bytes need protected, retained ownership proof."""
import os
from pathlib import Path
import tempfile
import unittest

from vipe_benchmark.budgets import budget_snapshot
from vipe_benchmark.config import load
from vipe_benchmark.files import read_json, write_json
from vipe_benchmark.ledger import Ledger


class CheckpointTests(unittest.TestCase):
    def test_reconciliation_helper_is_bound_in_every_candidate_source_closure(self):
        from vipe_benchmark.depth_admission import LOCAL_ADAPTERS, local_source_records
        for candidate in LOCAL_ADAPTERS:
            self.assertIn('depth_budget_reconciliation.py',
                [Path(row['path']).name for row in local_source_records(candidate)])

    def test_generic_notes_cannot_manufacture_reconciled_credit(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory) / 'ledger.jsonl', load())
            before = ledger.path.read_bytes() if ledger.path.exists() else b''
            with self.assertRaisesRegex(ValueError, 'checked ledger transition'):
                ledger.note('depth_setup_bytes_reconciled', candidate='D9', artifact_bytes=10**12)
            self.assertEqual(ledger.path.read_bytes() if ledger.path.exists() else b'', before)

    def test_prospective_checkpoint_preserves_shared_inode_identity(self):
        from vipe_benchmark.depth_budget_reconciliation import capture_checkpoint
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = root / 'setup-cache/old'
            old.parent.mkdir(); old.write_bytes(b'old')
            alias = root / 'old-job'
            os.link(old, alias)
            before = budget_snapshot(root)
            record = capture_checkpoint(root, 'D9', before)
            proof = read_json(record['path'])
            self.assertEqual(proof['resource_snapshot'], before)
            self.assertEqual(proof['files']['setup-cache/old']['inode'], proof['files']['old-job']['inode'])
            self.assertEqual(proof['files']['setup-cache/old']['logical_bytes'], 3)

    def test_expanded_cache_and_uv_are_reconciled_with_max_not_sum(self):
        from vipe_benchmark.depth_budget_reconciliation import acquisition_credit
        self.assertEqual(acquisition_credit(7, 30, 60, 20, 40), 47)
        self.assertEqual(acquisition_credit(7, 90, 60, 20, 40), 27)
        self.assertEqual(acquisition_credit(7, 30, 60, 0, 0), 7)

    def test_acquisition_credit_rejects_invented_or_negative_components(self):
        from vipe_benchmark.depth_budget_reconciliation import acquisition_credit
        for values in ((0, 10, 10, 11, 0), (0, 10, 10, 0, 11), (-1, 0, 0, 0, 0)):
            with self.subTest(values=values), self.assertRaises(ValueError):
                acquisition_credit(*values)


import test_vipe_benchmark_depth_map_allowance as fixtures
from vipe_benchmark.files import file_record, object_hash
from vipe_benchmark.depth_map_allowance import bind_slot_byte_budget, check_slot_byte_budget


class RetainedCausalTests(unittest.TestCase):
    setUp = fixtures.MapAllowanceTests.setUp
    tearDown = fixtures.MapAllowanceTests.tearDown
    prepare_completed_setup = fixtures.MapAllowanceTests.prepare_completed_setup
    """Use the existing accepted setup boundary, with real temp ledger/inodes."""
    def build_causal(self, *, baseline_cache=False, extra_unowned=False, reconcile=True,
                     finish_changes=None):
        self.proposal['allocation'].update(download_bytes=2**20, artifact_bytes=2**20)
        self.approval['proposal_sha256'] = object_hash(self.proposal)
        self.prepare_completed_setup()
        self.ledger = Ledger(self.root / 'ledger.jsonl', load())
        cache = self.root / 'setup-cache/accepted-library'
        cache.parent.mkdir()
        if baseline_cache:
            cache.write_bytes(b'x' * 131072)
        subject_reading = budget_snapshot(self.root)
        with self.ledger.locked() as (stream, events):
            self.subject = self.ledger._append(stream, events, dict(
                event='depth_setup_authorized', candidate='D6', resource_snapshot=subject_reading))
        from vipe_benchmark.depth_budget_reconciliation import capture_checkpoint
        reading = budget_snapshot(self.root)
        checkpoint = capture_checkpoint(self.root, 'D5', reading)
        with self.ledger.locked() as (stream, events):
            self.grant = self.ledger._append(stream, events,
                dict(self.events[0], resource_snapshot=reading, byte_checkpoint=checkpoint))
            self.ledger._append(stream, events, self.events[1])
        if not baseline_cache:
            cache.write_bytes(b'x' * 131072)
        installed = self.setup_root / 'runtime/environment/lib/library.so'
        installed.parent.mkdir(parents=True)
        os.link(cache, installed)
        inventory = self.setup_root / 'runtime/inventory.json'
        write_json(inventory, dict(inventory_only=True, model_imports=False, gpu_operations=False,
            packages=[dict(name='fixture-library', files=[file_record(installed)])]))
        identifier = 'a' * 32
        transfer = self.root / 'uv-transfers' / ('transfer-' + identifier + '.json')
        write_json(transfer, dict(transfer_id=identifier, bytes_received=131084 if baseline_cache else 8192,
                                 reserved_bytes=0, complete=True, error=None))
        command = self.setup_root / 'runtime/commands/00-install.json'
        write_json(command, dict(record_kind='actual', error=None, package_transfer_proxy=True,
                                uv_transfer_receipt=file_record(transfer)))
        runtime = self.setup_root / 'runtime/result.json'
        write_json(runtime, dict(schema='plan069-depth-environment-result/v1',
            status='complete', record_kind='actual', candidate='D5', inventory=file_record(inventory),
            command_receipts=[file_record(command)]))
        result = read_json(self.setup); self.setup.unlink()
        result.update(runtime_environment=file_record(runtime), inventory=file_record(inventory),
                      bytes_received=budget_snapshot(self.root)['download_bytes'] - reading['download_bytes'])
        write_json(self.setup, result)
        with self.ledger.locked() as (stream, events):
            self.ledger._append(stream, events, dict({k:v for k,v in self.events[2].items() if k != 'event_sha256'},
                **dict(dict(result=file_record(self.setup)), **(finish_changes or {}))))
        if extra_unowned:
            (self.root / 'unowned.bin').write_bytes(b'z' * 131072)
        if reconcile:
            self.ledger.reconcile_depth_setup_bytes('D5')
        self.subject_proposal = dict(candidate='D6', allocation=dict(download_bytes=65536,
            artifact_bytes=65536))
        self.stage = dict(setup=file_record(self.setup), setup_finish_event_sha256='fixture-subject-finish')
        return cache, installed

    def test_later_accepted_expanded_cache_permits_original_slot_without_raising_caps(self):
        self.build_causal()
        reading = budget_snapshot(self.root)
        baseline = self.subject['resource_snapshot']
        self.assertGreater(reading['artifact_bytes'], baseline['artifact_bytes'] + 65536)
        self.assertGreater(reading['download_bytes'], baseline['download_bytes'] + 65536)
        budget = bind_slot_byte_budget(self.subject_proposal, self.stage,
                                      self.ledger.events(), self.root, reading)
        self.assertEqual(budget['schema'], 'plan069-depth-slot-byte-budget/v2')
        self.assertEqual(budget['absolute_limits']['artifact_bytes'], baseline['artifact_bytes'] + 65536)
        check_slot_byte_budget(self.subject_proposal, budget, self.root, budget_snapshot(self.root))
        from vipe_benchmark.depth_budget_reconciliation import causal_credits
        credit = causal_credits(self.root, self.subject, self.ledger.events())
        self.assertEqual(credit['artifact_bytes'], 131072)
        self.assertEqual(credit['download_bytes'], 131072)
        self.assertEqual(budget_snapshot(self.root), reading)

    def test_new_alias_of_baseline_inode_has_no_artifact_or_cache_credit(self):
        self.build_causal(baseline_cache=True)
        from vipe_benchmark.depth_budget_reconciliation import causal_credits
        credit = causal_credits(self.root, self.subject, self.ledger.events())
        self.assertEqual(credit['artifact_bytes'], 0)
        self.assertEqual(credit['download_bytes'], 12)

    def test_unowned_later_growth_still_exceeds_unchanged_candidate_limit(self):
        self.build_causal(extra_unowned=True)
        with self.assertRaisesRegex(ValueError, 'whole-slot allocation exceeded'):
            bind_slot_byte_budget(self.subject_proposal, self.stage,
                                 self.ledger.events(), self.root, budget_snapshot(self.root))

    def test_retained_inode_change_revokes_credit(self):
        _, installed = self.build_causal()
        installed.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'retained inode changed'):
            bind_slot_byte_budget(self.subject_proposal, self.stage,
                                 self.ledger.events(), self.root, budget_snapshot(self.root))

    def test_fake_checkpoint_reconciliation_is_rejected_without_event_append(self):
        self.build_causal()
        before = self.ledger.path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'already protected'):
            self.ledger.reconcile_depth_setup_bytes('D5')
        self.assertEqual(self.ledger.path.read_bytes(), before)

    def test_legacy_v1_without_checkpoint_receives_no_new_credit(self):
        self.build_causal()
        events = [row for row in self.ledger.events() if row['event'] != 'depth_setup_bytes_reconciled']
        with self.assertRaisesRegex(ValueError, 'whole-slot allocation exceeded'):
            bind_slot_byte_budget(self.subject_proposal, self.stage,
                                 events, self.root, budget_snapshot(self.root))

    def test_own_reconciliation_does_not_exclude_own_setup_charge_or_block_maps(self):
        self.build_causal()
        events = self.ledger.events()
        stage = dict(setup=file_record(self.setup), setup_finish_event_sha256=
                     next(row['event_sha256'] for row in events if row['event'] == 'finish'))
        budget = bind_slot_byte_budget(self.proposal, stage, events, self.root, budget_snapshot(self.root))
        self.assertEqual(budget['schema'], 'plan069-depth-slot-byte-budget/v1')
        check_slot_byte_budget(self.proposal, budget, self.root, budget_snapshot(self.root))

    def test_same_size_mutation_before_reconciliation_cannot_mint_credit(self):
        _, installed = self.build_causal(reconcile=False)
        installed.write_bytes(b'y' * installed.stat().st_size)
        before = self.ledger.path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'changed file'):
            self.ledger.reconcile_depth_setup_bytes('D5')
        self.assertEqual(self.ledger.path.read_bytes(), before)

    def test_changed_acceptance_inventory_revokes_live_credit(self):
        self.build_causal()
        inventory = self.setup_root / 'runtime/inventory.json'
        inventory.write_text('{}\n')
        with self.assertRaisesRegex(ValueError, 'changed file'):
            bind_slot_byte_budget(self.subject_proposal, self.stage,
                                 self.ledger.events(), self.root, budget_snapshot(self.root))

    def test_missing_or_modified_checkpoint_cannot_mint_credit(self):
        self.build_causal(reconcile=False)
        checkpoint = Path(self.grant['byte_checkpoint']['path'])
        checkpoint.write_text('{}\n')
        before = self.ledger.path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'changed file'):
            self.ledger.reconcile_depth_setup_bytes('D5')
        self.assertEqual(self.ledger.path.read_bytes(), before)

    def test_active_attempt_blocks_reconciliation_without_new_proof(self):
        self.build_causal(reconcile=False)
        with self.ledger.locked() as (stream, events):
            self.ledger._append(stream, events, dict(event='reserve', job_id='fixture-active',resource='cpu'))
        before = self.ledger.path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'active attempt'):
            self.ledger.reconcile_depth_setup_bytes('D5')
        self.assertEqual(self.ledger.path.read_bytes(), before)
        self.assertFalse((self.root / 'prepare/plan069-D5-setup-byte-reconciliation.json').exists())

    def test_unclean_or_failed_finish_cannot_mint_credit(self):
        for changes in (dict(status='failed'), dict(cleanup_confirmed=False),
                        dict(cleanup_uncertain=True), dict(surviving_pids=[123]),
                        dict(deadline_exceeded=True)):
            with self.subTest(changes=changes):
                self.build_causal(reconcile=False, finish_changes=changes)
                before = self.ledger.path.read_bytes()
                with self.assertRaisesRegex(ValueError, 'clean exact setup'):
                    self.ledger.reconcile_depth_setup_bytes('D5')
                self.assertEqual(self.ledger.path.read_bytes(), before)
            self.tearDown(); self.setUp()

    def test_global_cap_overflow_blocks_reconciliation_without_changing_totals(self):
        self.build_causal(reconcile=False)
        self.ledger.config = dict(self.ledger.config, new_artifact_disk_gib_limit=0)
        before = self.ledger.path.read_bytes()
        reading = budget_snapshot(self.root)
        with self.assertRaisesRegex(ValueError, 'global cap'):
            self.ledger.reconcile_depth_setup_bytes('D5')
        self.assertEqual(self.ledger.path.read_bytes(), before)
        self.assertEqual(budget_snapshot(self.root), reading)
