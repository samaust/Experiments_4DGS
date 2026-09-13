"""CPU-only acquisition accounting fixtures; no network or inference."""
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest import mock

from scripts.vipe_benchmark import budgets
from scripts.vipe_benchmark.files import write_json


class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()

    def payload(self, relative, size):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'x' * size)
        return path

    def document(self, relative, value):
        path = self.root / relative
        write_json(path, value)
        return path

    def identity(self, path):
        info = path.stat()
        return dict(device=info.st_dev, inode=info.st_ino, size=info.st_size, mtime_ns=info.st_mtime_ns)

    def intent(self, identifier, output):
        return self.document(f'transfers/active-{identifier}.json', dict(transfer_id=identifier,
            output=str(output), partial=str(output.with_suffix(output.suffix + '.partial'))))

    def receipt(self, identifier, output, received, **extra):
        return self.document(f'transfers/transfer-{identifier}.json', dict(transfer_id=identifier,
            output=str(output), bytes_received=received, **extra))

    def charge(self):
        return budgets.budget_snapshot(self.root)['download_bytes']

    def test_failed_and_successful_receipts_retain_all_received_bytes(self):
        output = self.payload('job/archive.tar', 7)
        self.receipt('success', output, 7)
        self.receipt('failed-no-file', self.root / 'job/missing', 11, error='write failed')
        self.document('assets/teacher.pth.transfer-001.json', dict(
            output=str(self.root / 'assets/teacher.pth'), bytes_received=13, error='timeout'))
        self.document('transfers/transfer-count-only.json', dict(bytes_received=17, error='no file'))
        self.assertEqual(self.charge(), 48)

    def test_intent_bridges_partial_rename_and_receipt_publication_once(self):
        output = self.root / 'job/archive.tar'
        partial = self.payload('job/archive.tar.partial', 19)
        self.intent('one', output)
        self.assertEqual(self.charge(), 19)
        identity = self.identity(partial)
        partial.rename(output)
        self.assertEqual(self.charge(), 19)
        self.receipt('one', output, 19, partial_identity=identity)
        self.assertEqual(self.charge(), 19)

    def test_retained_failed_partial_is_not_counted_twice(self):
        output = self.root / 'job/failure.bin'
        partial = self.payload('job/failure.bin.partial', 7)
        self.intent('failure', output)
        self.receipt('failure', output, 11, partial_identity=self.identity(partial), error='write failed')
        self.assertEqual(self.charge(), 11)

    def test_new_attempt_on_same_path_adds_bytes_to_historical_failure(self):
        output = self.root / 'job/retry.bin'
        partial = self.payload('job/retry.bin.partial', 7)
        self.intent('old', output)
        self.receipt('old', output, 11, partial_identity=self.identity(partial), error='failed')
        partial.rename(partial.with_suffix('.failed-retained'))
        self.payload('job/retry.bin.partial', 5)
        self.intent('new', output)
        self.assertEqual(self.charge(), 16)
        self.receipt('new', output, 5, partial_identity=self.identity(partial), error='failed again')
        self.assertEqual(self.charge(), 16)

    def test_legacy_teacher_partial_covered_but_later_growth_charged(self):
        partial = self.payload('assets/teacher.pth.partial', 7)
        old_ns = 1_000_000_000
        os.utime(partial, ns=(old_ns, old_ns))
        receipt = self.document('assets/teacher.pth.transfer-001.json', dict(
            output=str(self.root / 'assets/teacher.pth'), bytes_received=11, error='failed'))
        self.assertEqual(self.charge(), 11)
        partial.write_bytes(b'x' * 5)
        newer = receipt.stat().st_mtime_ns + 1_000_000
        os.utime(partial, ns=(newer, newer))
        self.assertEqual(self.charge(), 16)

    def test_unreceipted_teacher_output_is_counted_during_publication_gap(self):
        self.payload('assets/teacher.pth', 23)
        self.assertEqual(self.charge(), 23)
        self.document('assets/teacher.pth.transfer-001.json', dict(
            output=str(self.root / 'assets/teacher.pth'), bytes_received=23))
        self.assertEqual(self.charge(), 23)

    def test_orphan_partial_is_charged(self):
        self.payload('job/lost.bin.partial', 29)
        self.assertEqual(self.charge(), 29)

    def test_uv_uses_larger_wire_or_retained_package_scope(self):
        self.payload('setup-cache/wheel/extracted.py', 19)
        self.payload('managed-python/python/bin/python', 11)
        self.document('uv-transfers/active-a.json', dict(transfer_id='a', bytes_received=17, reserved_bytes=0))
        self.document('uv-transfers/transfer-a.json', dict(transfer_id='a', bytes_received=17, reserved_bytes=0))
        self.assertEqual(self.charge(), 30)
        self.document('uv-transfers/transfer-b.json', dict(transfer_id='b', bytes_received=23, reserved_bytes=5))
        self.assertEqual(self.charge(), 45)

    def test_direct_file_inside_cache_is_not_also_a_package_proxy(self):
        output = self.payload('setup-cache/archive.whl', 13)
        self.receipt('direct', output, 13)
        self.payload('managed-python/python', 7)
        self.assertEqual(self.charge(), 20)

    def test_package_orphan_partial_uses_retained_cache_scope_once(self):
        self.payload('setup-cache/download.partial', 19)
        self.assertEqual(self.charge(), 19)

    def test_artifact_hardlinks_count_once_with_allocated_blocks(self):
        path = self.payload('setup-cache/small-wheel', 1)
        target = self.root / 'environment/package.py'
        target.parent.mkdir()
        os.link(path, target)
        info = path.stat()
        physical = max(info.st_size, info.st_blocks * 512)
        result = budgets.budget_snapshot(self.root)
        self.assertEqual(result['artifact_bytes'], physical)
        self.assertEqual(result['logical_artifact_bytes'], 2)
        self.assertEqual(budgets.directory_bytes(self.root), physical)

    def test_symlinks_and_prompts_directories_are_not_traversed(self):
        path = self.payload('visible', 1)
        forbidden = self.root / 'prompts'
        forbidden.mkdir()
        (self.root / 'external-link').symlink_to('/etc')
        scan = budgets.os.scandir
        seen = []
        def guarded(base):
            self.assertNotEqual(Path(base).name, 'prompts')
            seen.append(Path(base))
            return scan(base)
        with mock.patch.object(budgets.os, 'scandir', side_effect=guarded):
            result = budgets.budget_snapshot(self.root)
        self.assertEqual(result['logical_artifact_bytes'], 1)
        self.assertEqual(seen, [self.root])
        with self.assertRaisesRegex(ValueError, 'prompts'):
            budgets.directory_bytes(forbidden)

    def test_concurrent_rename_is_rescanned_instead_of_losing_storage(self):
        partial = self.payload('payload.partial', 31)
        expected = max(partial.stat().st_size, partial.stat().st_blocks * 512)
        scan = budgets.os.scandir
        renamed = []
        class RacingScan:
            def __init__(self, base):
                self.entries = scan(base)
            def __enter__(self):
                self.entries.__enter__()
                return self
            def __exit__(self, *args):
                return self.entries.__exit__(*args)
            def __iter__(self):
                for entry in self.entries:
                    if entry.name == partial.name and not renamed:
                        partial.rename(partial.with_suffix(''))
                        renamed.append(True)
                    yield entry
        with mock.patch.object(budgets.os, 'scandir', side_effect=RacingScan):
            self.assertEqual(budgets.directory_bytes(self.root), expected)
        self.assertEqual(renamed, [True])

    def test_incomplete_receipts_fail_closed(self):
        path = self.root / 'transfers/transfer-broken.json'
        path.parent.mkdir()
        path.write_text('{"bytes_received":')
        with self.assertRaisesRegex(budgets.BudgetAccountingError, 'incomplete JSON'):
            self.charge()

    def test_duplicate_identity_and_negative_counts_fail_closed(self):
        output = self.root / 'job/data'
        self.receipt('a', output, 1)
        self.document('transfers/transfer-b.json', dict(transfer_id='a', output=str(output), bytes_received=1))
        with self.assertRaisesRegex(budgets.BudgetAccountingError, 'duplicate'):
            self.charge()

    def test_negative_count_is_not_silently_ignored(self):
        self.document('transfers/transfer-bad.json', dict(bytes_received=-1))
        with self.assertRaisesRegex(budgets.BudgetAccountingError, 'nonnegative'):
            self.charge()

    def test_counted_output_cannot_escape_the_run(self):
        self.document('transfers/transfer-bad.json', dict(output='/tmp/outside-budget-fixture', bytes_received=1))
        with self.assertRaisesRegex(budgets.BudgetAccountingError, 'outside'):
            self.charge()

    def test_received_but_unwritten_bytes_reduce_next_read(self):
        output = self.root / 'job/data'
        self.intent('current', output)
        self.payload('job/data.partial', 3)
        self.assertEqual(budgets.download_remaining(self.root, 10, active_output=output, bytes_received=7), 3)
        self.assertEqual(budgets.download_remaining(self.root, 10, active_output=output, bytes_received=11), 0)

    def test_direct_reservation_survives_failure_receipt_with_fewer_known_bytes(self):
        output = self.root / 'job/data'
        self.intent('current', output)
        with budgets.download_lock(self.root):
            budgets.record_download_progress(self.root, 'current', output, 5, 13)
        self.assertEqual(self.charge(), 18)
        self.receipt('current', output, 5, error='read failed before returning a block')
        self.assertEqual(self.charge(), 18)

    def test_successful_direct_flush_replaces_reservation_with_actual_bytes_once(self):
        output = self.root / 'job/data'
        self.intent('current', output)
        with budgets.download_lock(self.root):
            budgets.record_download_progress(self.root, 'current', output, 0, 10)
            self.assertEqual(self.charge(), 10)
            partial = self.payload('job/data.partial', 7)
            budgets.record_download_progress(self.root, 'current', output, 7, 0)
            self.assertEqual(self.charge(), 7)
            self.receipt('current', output, 7, partial_identity=self.identity(partial))
            self.assertEqual(self.charge(), 7)

    def test_progress_without_final_receipt_or_payload_keeps_crash_charge(self):
        output = self.root / 'job/data'
        with budgets.download_lock(self.root):
            budgets.record_download_progress(self.root, 'lost', output, 11, 7)
        self.assertEqual(self.charge(), 18)

    def test_direct_progress_baseline_does_not_double_charge_own_flushed_chunk(self):
        output = self.root / 'job/data'
        self.intent('current', output)
        self.payload('job/data.partial', 3)
        with budgets.download_lock(self.root), mock.patch.object(budgets.time, 'monotonic', return_value=10.):
            budgets.record_download_progress(self.root, 'current', output, 3, 0)
            self.assertEqual(budgets.download_remaining(self.root, 10, active_output=output, bytes_received=3), 7)
            budgets.record_download_progress(self.root, 'current', output, 3, 7)
            self.payload('job/data.partial', 6)
            budgets.record_download_progress(self.root, 'current', output, 6, 0)
            self.assertEqual(budgets.download_remaining(self.root, 10, active_output=output, bytes_received=6), 4)

    def test_historical_reservation_does_not_mask_new_attempt_local_bytes(self):
        output = self.root / 'job/data'
        self.intent('old', output)
        with budgets.download_lock(self.root):
            budgets.record_download_progress(self.root, 'old', output, 0, 10)
        self.receipt('old', output, 5, error='failed')
        self.intent('new', output)
        self.payload('job/data.partial', 2)
        with budgets.download_lock(self.root):
            budgets.record_download_progress(self.root, 'new', output, 2, 0)
            self.assertEqual(self.charge(), 12)
            self.assertEqual(budgets.download_remaining(self.root, 20, active_output=output, bytes_received=3), 7)

    def test_direct_actual_counter_cannot_decrease_or_change_output(self):
        output = self.root / 'job/data'
        with budgets.download_lock(self.root):
            budgets.record_download_progress(self.root, 'one', output, 7, 0)
            with self.assertRaisesRegex(budgets.BudgetAccountingError, 'decrease'):
                budgets.record_download_progress(self.root, 'one', output, 6, 0)
            with self.assertRaisesRegex(budgets.BudgetAccountingError, 'output changed'):
                budgets.record_download_progress(self.root, 'one', self.root / 'other', 7, 0)

    def test_exact_sixty_gib_cap_requires_no_large_fixture(self):
        cap = 60 * 2**30
        self.document('transfers/transfer-prior.json', dict(bytes_received=cap - 3))
        output = self.root / 'job/data'
        self.intent('current', output)
        self.assertEqual(budgets.download_remaining(self.root, cap, active_output=output, bytes_received=0), 3)
        self.assertEqual(budgets.download_remaining(self.root, cap, active_output=output, bytes_received=3), 0)

    def test_artifact_allowance_limits_next_read(self):
        output = self.root / 'job/data'
        self.intent('current', output)
        artifact = budgets.budget_snapshot(self.root)['artifact_bytes']
        self.assertEqual(budgets.download_remaining(self.root, 100, active_output=output,
                         bytes_received=2, artifact_limit=artifact + 5), 3)

    def test_lock_caches_scan_but_charges_every_intervening_read(self):
        output = self.root / 'job/data'
        self.intent('current', output)
        with budgets.download_lock(self.root), mock.patch.object(budgets, '_snapshot', wraps=budgets._snapshot) as scan:
            with mock.patch.object(budgets.time, 'monotonic', return_value=10.):
                self.assertEqual(budgets.download_remaining(self.root, 10, active_output=output), 10)
                self.assertEqual(budgets.download_remaining(self.root, 10, active_output=output, bytes_received=3), 7)
                self.assertEqual(budgets.download_remaining(self.root, 10, active_output=output, bytes_received=7), 3)
                self.assertEqual(scan.call_count, 1)
            self.payload('job/data.partial', 7)
            with mock.patch.object(budgets.time, 'monotonic', return_value=11.1):
                self.assertEqual(budgets.download_remaining(self.root, 10, active_output=output, bytes_received=8), 2)
                self.assertEqual(scan.call_count, 2)

    def test_uv_local_growth_obeys_max_without_double_charging_cache(self):
        self.payload('setup-cache/package', 30)
        self.document('uv-transfers/active-a.json', dict(transfer_id='a', bytes_received=5, reserved_bytes=0))
        with budgets.download_lock(self.root):
            self.assertEqual(budgets.download_remaining(self.root, 40, uv_transfer_id='a', bytes_received=15), 10)
            self.assertEqual(budgets.download_remaining(self.root, 40, uv_transfer_id='a', bytes_received=33), 7)

    def test_two_transfer_threads_cannot_spend_the_same_remaining_bytes(self):
        barrier = threading.Barrier(2)
        received, errors = [], []
        def transfer(identifier):
            try:
                barrier.wait(timeout=2)
                with budgets.download_lock(self.root):
                    count = min(7, budgets.download_remaining(self.root, 10))
                    self.document(f'transfers/transfer-{identifier}.json', dict(bytes_received=count))
                    received.append(count)
            except BaseException as exc:
                errors.append(exc)
        threads = [threading.Thread(target=transfer, args=(i,)) for i in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(3)
        self.assertFalse(any(t.is_alive() for t in threads))
        self.assertEqual(errors, [])
        self.assertEqual(sorted(received), [3, 7])
        self.assertEqual(self.charge(), 10)

    def test_cancelled_waiting_lock_does_not_enter_download_scope(self):
        cancelled = threading.Event()
        started = threading.Event()
        errors = []
        def wait_for_lock():
            started.set()
            try:
                with budgets.download_lock(self.root, cancel_event=cancelled):
                    errors.append('unexpected acquisition')
            except budgets.BudgetAccountingError:
                errors.append('cancelled')
        with budgets.download_lock(self.root):
            thread = threading.Thread(target=wait_for_lock)
            thread.start()
            self.assertTrue(started.wait(1))
            cancelled.set()
            thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, ['cancelled'])


if __name__ == '__main__':
    unittest.main()
