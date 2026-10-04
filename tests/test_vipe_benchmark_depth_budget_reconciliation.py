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
                     finish_changes=None, installed_spelling=None, duplicate_installed=False):
        self.proposal['allocation'].update(download_bytes=2**20, artifact_bytes=2**20, cpu_seconds=1000)
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
        installed_record = file_record(installed)
        if installed_spelling is not None:
            installed_record['path'] = str(installed_spelling(installed))
        write_json(inventory, dict(inventory_only=True, model_imports=False, gpu_operations=False,
            packages=[dict(name='fixture-library', files=[installed_record, file_record(installed)] if duplicate_installed else [installed_record])]))
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
                **dict(dict(result=file_record(self.setup), elapsed_seconds=1.), **(finish_changes or {}))))
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

    def cpu_admission(self, *, remaining=1000, seconds=120):
        from vipe_benchmark.depth_admission import local_source_records
        source = self.root / 'cpu-source-review.json'
        write_json(source, dict(status='passed', candidate='D5', local_sources=local_source_records('D5')))
        config = self.root / 'cpu-effective-config.json'
        write_json(config, self.ledger.config)
        events = self.ledger.events()
        elapsed = self.ledger.totals(events)['cpu']['elapsed_seconds']
        admission = self.root / 'cpu-admission.json'
        write_json(admission, dict(schema='plan069-root-cpu-fixture-admission/v1',candidate='D5',
            cpu_accounting_owner='D5', ledger_head_sequence=events[-1]['sequence'],
            ledger_head_sha256=events[-1]['event_sha256'],ledger_event_count=len(events),
            candidate_cpu_allocation_seconds=1000,candidate_cpu_elapsed_seconds=1000-remaining,
            candidate_cpu_remaining_seconds=remaining, global_cpu_elapsed_seconds=elapsed,
            global_cpu_remaining_seconds=self.ledger.config['cpu_prepare_score_report_seconds_limit']-elapsed,
            seconds=seconds,effective_configuration=file_record(config),source_review=file_record(source)))
        return file_record(admission), self.root / 'prepare/plan069-D5-setup-byte-reconciliation-001'

    def test_bounded_cpu_producer_charges_once_with_receipt_and_preserves_future_headroom(self):
        from vipe_benchmark.depth_budget_reconciliation import run_reconciliation
        self.build_causal(reconcile=False)
        admission, output = self.cpu_admission()
        result = run_reconciliation(self.ledger, 'D5', admission, output)
        self.assertEqual(result['status'], 'complete')
        self.assertTrue(result['cleanup_confirmed'])
        self.assertEqual(result['surviving_pids'], [])
        self.assertFalse(result['gpu_operations'])
        charges = [row for row in self.ledger.events() if row['event'] == 'cpu_preparation_charge']
        self.assertEqual(len(charges), 1)
        self.assertEqual(charges[0]['evidence'], file_record(output / 'receipt.json'))
        self.assertEqual(charges[0]['elapsed_seconds'], result['elapsed_seconds'])
        with self.assertRaisesRegex(ValueError, 'fresh named CPU'):
            run_reconciliation(self.ledger, 'D5', admission, output)
        self.assertEqual(len([row for row in self.ledger.events() if row['event'] == 'cpu_preparation_charge']), 1)

    def test_cpu_producer_rejects_insufficient_future_headroom_before_writes(self):
        from vipe_benchmark.depth_budget_reconciliation import run_reconciliation
        self.build_causal(reconcile=False)
        admission, output = self.cpu_admission(remaining=459)
        before = self.ledger.path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'preserve qualification and maps headroom'):
            run_reconciliation(self.ledger, 'D5', admission, output)
        self.assertEqual(self.ledger.path.read_bytes(), before)
        self.assertFalse(output.exists())

    def test_cpu_timeout_preserves_failed_receipt_and_actual_charge_without_credit(self):
        from vipe_benchmark.depth_budget_reconciliation import run_reconciliation
        self.build_causal(reconcile=False)
        admission, output = self.cpu_admission()
        from unittest.mock import patch
        from vipe_benchmark.depth_budget_reconciliation import _timed_verify
        def timed(record, deadline):
            if record['path'] == str(self.asset):
                raise TimeoutError('fixture streaming deadline')
            return _timed_verify(record, deadline)
        with patch('vipe_benchmark.depth_budget_reconciliation._timed_verify', side_effect=timed):
            with self.assertRaisesRegex(TimeoutError, 'streaming deadline'):
                run_reconciliation(self.ledger, 'D5', admission, output)
        receipt = read_json(output / 'receipt.json')
        self.assertEqual(receipt['status'], 'failed')
        self.assertTrue(receipt['cleanup_confirmed'])
        events = self.ledger.events()
        self.assertFalse(any(row['event'] == 'depth_setup_bytes_reconciled' for row in events))
        self.assertEqual(events[-1]['event'], 'cpu_preparation_charge')
        self.assertEqual(events[-1]['evidence'], file_record(output / 'receipt.json'))

    def test_streamed_hash_enforces_deadline_between_blocks(self):
        from vipe_benchmark.depth_budget_reconciliation import _timed_verify
        from unittest.mock import patch
        self.build_causal(reconcile=False)
        path = self.root / 'large-fixture.bin'
        path.write_bytes(b'X' * (2**20 + 1))
        record = file_record(path)
        with patch('vipe_benchmark.depth_budget_reconciliation.time.monotonic',side_effect=[0., 2.]):
            with self.assertRaisesRegex(TimeoutError, 'CPU deadline'):
                _timed_verify(record, 1.)

    def test_final_scan_deadline_cannot_leave_protected_credit(self):
        from vipe_benchmark.depth_budget_reconciliation import run_reconciliation, _files
        from unittest.mock import patch
        self.build_causal(reconcile=False)
        admission, output = self.cpu_admission()
        calls = []
        def inventory(root, deadline=None):
            calls.append(root)
            result = _files(root, deadline)
            if len(calls) == 2:
                raise TimeoutError('fixture final inventory deadline')
            return result
        with patch('vipe_benchmark.depth_budget_reconciliation._files', side_effect=inventory):
            with self.assertRaisesRegex(TimeoutError, 'final inventory deadline'):
                run_reconciliation(self.ledger, 'D5', admission, output)
        events = self.ledger.events()
        self.assertFalse(any(row['event'] == 'depth_setup_bytes_reconciled' for row in events))
        self.assertEqual(events[-1]['event'], 'cpu_preparation_charge')
        self.assertEqual(read_json(output / 'receipt.json')['status'], 'failed')

    def test_source_preflight_failure_is_preserved_and_charged_after_fresh_admission(self):
        from vipe_benchmark.depth_budget_reconciliation import run_reconciliation
        self.build_causal(reconcile=False)
        admission, output = self.cpu_admission()
        document = read_json(admission['path'])
        Path(document['source_review']['path']).write_text('{}\n')
        with self.assertRaisesRegex(ValueError, 'changed file'):
            run_reconciliation(self.ledger, 'D5', admission, output)
        receipt = read_json(output / 'receipt.json')
        self.assertEqual(receipt['status'], 'failed')
        self.assertEqual(self.ledger.events()[-1]['evidence'], file_record(output / 'receipt.json'))


import test_vipe_benchmark_depth_recovery_lineage as recovery_fixtures
from vipe_benchmark.depth_budget_reconciliation import prepare_reconciliation, causal_credits


class RecoveryCausalTests(recovery_fixtures.RecoveryLineageTests):
    """Exercise retained inode accounting through the producer's public boundary."""
    def build_recovery(self, *, preexisting=False):
        from vipe_benchmark.depth_budget_reconciliation import _files
        # The authority seam is independently covered by checked-ledger tests.
        # Its normalized ancestor binds the same real before inventory here.
        before_files = _files(self.root) if preexisting else {}
        snapshot = budget_snapshot(self.root)
        baseline = dict(snapshot)
        baseline.update(download_bytes=0, artifact_bytes=0, direct_download_bytes=0,
                        uv_metered_bytes=0, retained_package_bytes=0)
        self.maps['allocation'].update(download_bytes=2**20, artifact_bytes=2**20)
        checkpoint = self.document(self.root / 'prepare/plan069-D9-setup-byte-checkpoint.json',
            dict(schema='plan069-depth-setup-byte-checkpoint/v1', candidate='D9',
                 resource_snapshot=baseline, files=before_files, uv_progress=[]))
        original_grant = dict(event='depth_setup_authorized', candidate='D9', sequence=2,
            event_sha256='original-grant', resource_snapshot=baseline, byte_checkpoint=checkpoint)
        failed = dict(event='finish', job_id='plan069-D9-setup-001', sequence=3,
            event_sha256='failed', status='failed', cleanup_confirmed=True,
            cleanup_uncertain=False, surviving_pids=[], deadline_exceeded=False)
        failure = self.document(self.old / 'runtime/failure.json', dict(command_receipts=[]))
        self.original.update(grant_event_sha256='original-grant', failed_finish_event_sha256='failed',
            byte_checkpoint=checkpoint, runtime_failure=failure)
        self.normalized['lineage'].update(grant=original_grant, finish=failed,
            checkpoint=read_json(checkpoint['path']))
        self.proposal['original_setup'] = self.original
        self.grant['proposal_sha256'] = object_hash(self.proposal)
        Path(self.request['path']).unlink()
        self.request = self.document(Path(self.request['path']), dict(self.authority,
            schema='plan069-video-setup-recovery-request/v1', original_setup=self.original))
        self.normalized['request'] = self.request
        self.grant.update(request=self.request, original_setup=self.original)
        self.reserve['evidence']['request'] = self.request
        self.result.update(request=self.request, original_setup=self.original)
        # An expanded package is retained both in cache and the new environment.
        cache = self.root / 'setup-cache/package.so'; cache.parent.mkdir()
        cache.write_bytes(b'x' * 16384)
        installed = self.job / 'runtime/environment/lib/package.so'
        installed.parent.mkdir(); os.link(cache, installed)
        inventory_path = Path(self.result['inventory']['path']); inventory_path.unlink()
        self.result['inventory'] = self.document(inventory_path, dict(inventory_only=True,
            model_imports=False, gpu_operations=False, executable=self.result['python_executable'],
            packages=[dict(name='fixture-package', files=[file_record(installed)])]))
        runtime_path = Path(self.result['runtime_environment']['path'])
        runtime = read_json(runtime_path); runtime_path.unlink()
        runtime['inventory'] = self.result['inventory']; runtime['command_receipts'] = []
        self.result['runtime_environment'] = self.document(runtime_path, runtime)
        self.publish()
        self.events = [original_grant, failed, self.grant, self.reserve, self.finish]
        self.subject = dict(candidate='D6', sequence=1, event_sha256='subject')

    def protect_proof(self):
        proof = prepare_reconciliation(self.root, 'D9', self.events)
        self.events.append(dict(event='depth_setup_bytes_reconciled', candidate='D9',
            sequence=7, event_sha256='reconciled', proof=proof))
        return read_json(proof['path'])

    def test_repair_causal_proof_binds_failed_first_recovery(self):
        self.build_recovery()
        original_events = self.events[:2]
        descriptor = self.repair()
        self.events = original_events + self.events
        proof_record = prepare_reconciliation(self.root, 'D9', self.events)
        proof = read_json(proof_record['path'])
        self.assertEqual(proof['recovery_lineage']['job_id'], self.job.name)
        self.assertEqual(proof['recovery_lineage']['failed_recoveries'], [descriptor])
        self.events.append(dict(event='depth_setup_bytes_reconciled', candidate='D9', sequence=10,
            event_sha256='reconciled', proof=proof_record))
        self.assertEqual(causal_credits(self.root, self.subject, self.events)['download_bytes'], 16388)
        self.events[4]['cleanup_uncertain'] = True
        with self.assertRaisesRegex(ValueError, 'clean failed recovery'):
            causal_credits(self.root, self.subject, self.events)

    def test_recovery_reconciles_expanded_new_cache_using_original_checkpoint(self):
        self.build_recovery()
        proof = self.protect_proof()
        self.assertEqual(proof['checkpoint'], self.original['byte_checkpoint'])
        self.assertEqual(proof['recovery_lineage']['failed_finish_event_sha256'], 'failed')
        credit = causal_credits(self.root, self.subject, self.events)
        self.assertEqual(credit['download_bytes'], 16388)
        # A recovery model hardlink is credited once, even though both paths own it.
        self.assertEqual(len({(row['device'], row['inode']) for row in proof['owned_files'].values()}),
                         len(proof['owned_files']) - 1)

    def test_recovery_keeps_preexisting_model_and_source_inodes_uncredited(self):
        self.build_recovery(preexisting=True)
        # A paid receipt for an inode in the protected before snapshot must fail.
        with self.assertRaisesRegex(ValueError, 'newly retained accepted setup data'):
            prepare_reconciliation(self.root, 'D9', self.events)

    def test_failed_recovery_cannot_publish_attribution(self):
        self.build_recovery(); self.finish['status'] = 'failed'
        with self.assertRaisesRegex(ValueError, 'authorized recovery completion'):
            prepare_reconciliation(self.root, 'D9', self.events)
        self.assertFalse((self.root / 'prepare/plan069-D9-setup-byte-reconciliation.json').exists())

    def test_original_successful_uv_receipt_credits_expanded_recovery_cache_once(self):
        self.build_recovery()
        identifier = 'c' * 32
        receipt = self.document(self.root / 'uv-transfers' / ('transfer-' + identifier + '.json'),
            dict(transfer_id=identifier, bytes_received=1024, reserved_bytes=0,
                 complete=True, error=None))
        command = self.document(self.old / 'runtime/commands/01-install.json',
            dict(record_kind='actual', error=None, package_transfer_proxy=True,
                 uv_transfer_receipt=receipt))
        failure_path = Path(self.original['runtime_failure']['path']); failure_path.unlink()
        self.original['runtime_failure'] = self.document(failure_path,
            dict(command_receipts=[command]))
        self.grant['proposal_sha256'] = object_hash(self.proposal)
        request_path = Path(self.request['path']); request_path.unlink()
        self.request = self.document(request_path, dict(self.authority,
            schema='plan069-video-setup-recovery-request/v1', original_setup=self.original))
        self.normalized['request'] = self.request
        self.grant.update(request=self.request, original_setup=self.original)
        self.reserve['evidence']['request'] = self.request
        self.result.update(request=self.request, original_setup=self.original)
        self.publish()
        proof = self.protect_proof()
        self.assertEqual(proof['uv_transfers'], [dict(command=command, receipt=receipt)])
        self.assertEqual(causal_credits(self.root, self.subject, self.events)['download_bytes'], 16388)

    def test_recovery_causal_credit_requires_protected_original_failed_binding(self):
        self.build_recovery(); self.protect_proof()
        self.events[1]['event_sha256'] = 'changed'
        with self.assertRaisesRegex(ValueError, 'unique protected recovery causal event'):
            causal_credits(self.root, self.subject, self.events)


class InstalledDeclaredPathTests(unittest.TestCase):
    setUp = RetainedCausalTests.setUp
    tearDown = RetainedCausalTests.tearDown
    prepare_completed_setup = RetainedCausalTests.prepare_completed_setup
    build_causal = RetainedCausalTests.build_causal
    def test_lexical_parent_console_path_matches_owned_file_and_bounded_hash(self):
        from vipe_benchmark.depth_budget_reconciliation import prepare_reconciliation
        import time
        def spelling(path):
            nested=path.parent/'nested';nested.mkdir()
            return nested/'..'/path.name
        cache,installed=self.build_causal(reconcile=False,installed_spelling=spelling)
        before=read_json(self.setup)['inventory']
        proof=prepare_reconciliation(self.root,'D5',self.ledger.events(),deadline=time.monotonic()+30)
        proof=read_json(proof['path'])
        relative=str(installed.relative_to(self.root))
        self.assertIn(relative,proof['owned_files'])
        self.assertIn(str(cache.relative_to(self.root)),proof['retained_cache_files'])
        self.assertEqual(read_json(self.setup)['inventory'],before)

    def test_bounded_verifier_preserves_literal_record_with_parent_segments(self):
        from vipe_benchmark.depth_budget_reconciliation import _timed_verify
        import time
        path=self.root/'owned/value';path.parent.mkdir();path.write_bytes(b'fixture')
        nested=path.parent/'nested';nested.mkdir()
        literal=dict(file_record(path),path=str(nested/'..'/path.name))
        self.assertNotEqual(literal['path'],str(path))
        self.assertEqual(_timed_verify(literal,time.monotonic()+1),literal)
        with self.assertRaises(TimeoutError):_timed_verify(literal,time.monotonic()-1)

    def test_lexical_parent_escape_does_not_produce_owned_credit(self):
        def spelling(path):
            outside=self.root/'outside.bin';outside.write_bytes(path.read_bytes())
            return path.parent/'..'/'..'/'..'/'..'/'..'/outside.name
        self.build_causal(reconcile=False,installed_spelling=spelling)
        with self.assertRaisesRegex(ValueError,'outside approved owned lineage'):
            prepare_reconciliation(self.root,'D5',self.ledger.events())

    def test_parent_symlink_inside_owned_job_is_rejected(self):
        def spelling(path):
            alias=path.parent/'alias';alias.symlink_to(path.parent,target_is_directory=True)
            return alias/path.name
        self.build_causal(reconcile=False,installed_spelling=spelling)
        with self.assertRaisesRegex(ValueError,'symlink'):
            prepare_reconciliation(self.root,'D5',self.ledger.events())

    def test_forbidden_lexical_prompt_component_is_rejected(self):
        def spelling(path):return path.parent/'prompts'/'..'/path.name
        self.build_causal(reconcile=False,installed_spelling=spelling)
        with self.assertRaisesRegex(ValueError,'prompts'):
            prepare_reconciliation(self.root,'D5',self.ledger.events())

    def test_canonical_and_lexical_aliases_credit_one_owned_inode(self):
        def spelling(path):
            nested=path.parent/'nested';nested.mkdir()
            return nested/'..'/path.name
        cache,installed=self.build_causal(reconcile=False,installed_spelling=spelling,duplicate_installed=True)
        proof=read_json(prepare_reconciliation(self.root,'D5',self.ledger.events())['path'])
        identity=(installed.stat().st_dev,installed.stat().st_ino)
        matching=[row for row in proof['owned_files'].values() if (row['device'],row['inode'])==identity]
        self.assertEqual(len(matching),1)
        self.assertEqual(len(proof['retained_cache_files']),1)

    def test_bounded_verifier_rejects_changed_hash_or_byte_count(self):
        from vipe_benchmark.depth_budget_reconciliation import _timed_verify
        import time
        path=self.root/'owned-value';path.write_bytes(b'fixture');record=file_record(path)
        for changed in [dict(record,sha256='0'*64),dict(record,bytes=record['bytes']+1)]:
            with self.subTest(record=changed),self.assertRaisesRegex(ValueError,'changed file'):
                _timed_verify(changed,time.monotonic()+1)

    def test_generic_evidence_verifier_rejects_symlink_and_relative_aliases(self):
        from vipe_benchmark.depth_budget_reconciliation import _timed_verify
        import time
        target=self.root/'evidence';target.write_bytes(b'fixture')
        alias=self.root/'evidence-alias';alias.symlink_to(target)
        record=file_record(target)
        for path in [str(alias),'relative-evidence']:
            for deadline in [None,time.monotonic()+1]:
                with self.subTest(path=path,deadline=deadline),self.assertRaisesRegex(ValueError,'symlink or relative'):
                    _timed_verify(dict(record,path=path),deadline)
