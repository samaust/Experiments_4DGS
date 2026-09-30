"""Disposable CPU acceptance fixtures; no native model or live ledger access."""
import copy
import hashlib
import os
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import test_vipe_benchmark_s1_recovery as fixtures
from vipe_benchmark import s1_recovery as recovery
from vipe_benchmark.access import output_identities
from vipe_benchmark.files import file_record, read_json, write_json
from vipe_benchmark.s1_evidence import first_record, qualify_row


SUBTEST_CASES = {}


class S1AssetAcceptanceTests(unittest.TestCase):
    def admitted_result(self):
        from vipe_benchmark import s1_validation_contract as contract
        # The disposable worktree uses the explicitly selected root CPU interpreter.
        interpreter = Path(sys.executable)
        launcher = patch.object(contract, 'ARGV', [str(interpreter), '-B', '-'])
        launcher.start()
        self.addCleanup(launcher.stop)
        synthetic = fixtures.synthetic_assets
        def with_snapshot(root, put):
            assets, runtime, observed = synthetic(root, put)
            cache = root / 'models--fixture'
            snapshot = cache / 'snapshots' / ('a' * 40)
            snapshot.mkdir(parents=True)
            blob = cache / 'blobs' / hashlib.sha256(b'admitted CPU model fixture').hexdigest()
            blob.parent.mkdir()
            blob.write_bytes(b'admitted CPU model fixture')
            alias = snapshot / 'model.safetensors'
            alias.symlink_to('../../blobs/' + blob.name)
            record = dict(file_record(blob), path=str(alias))
            config_blob = cache / 'blobs' / ('b' * 40)
            config_blob.write_bytes(b'CPU config with Git blob name')
            config_alias = snapshot / 'config.json'
            config_alias.symlink_to('../../blobs/' + config_blob.name)
            config_record = dict(file_record(config_blob), path=str(config_alias))
            assets['bert_snapshot'] = dict(path=str(snapshot), revision='a' * 40, files=[record, config_record])
            self.config_alias, self.config_blob, self.config_record = config_alias, config_blob, config_record
            self.alias, self.blob, self.asset_record = alias, blob, record
            from vipe_benchmark.backends import SNAPSHOT_PINS
            depth = root / 'models--depth-fixture'
            depth_snapshot = depth / 'snapshots' / SNAPSHOT_PINS['unidepth_snapshot']
            depth_snapshot.mkdir(parents=True)
            depth_blob = depth / 'blobs' / hashlib.sha256(b'CPU depth fixture').hexdigest()
            depth_blob.parent.mkdir()
            depth_blob.write_bytes(b'CPU depth fixture')
            depth_alias = depth_snapshot / 'model.safetensors'
            depth_alias.symlink_to('../../blobs/' + depth_blob.name)
            depth_record = dict(file_record(depth_blob), path=str(depth_alias))
            assets['unidepth_snapshot'] = dict(path=str(depth_snapshot),
                revision=SNAPSHOT_PINS['unidepth_snapshot'], files=[depth_record])
            self.expected_aliases = [dict(asset=name, snapshot=str(link.parent), alias=rec,
                symlink_target='../../blobs/' + target.name, target=file_record(target))
                for name, link, target, rec in [('bert_snapshot', alias, blob, record),
                    ('bert_snapshot', config_alias, config_blob, config_record),
                    ('unidepth_snapshot', depth_alias, depth_blob, depth_record)]]
            self.expected_aliases.sort(key=lambda item: item['alias']['path'])
            return assets, runtime, observed
        fixture = fixtures.S1RecoveryTests('runTest')
        with patch.object(fixtures, 'synthetic_assets', with_snapshot):
            fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        _, request, evidence = fixture.register()
        reservation = fixture.ledger.reserve(recovery.JOB, fixture.command(evidence), evidence)
        clock = recovery.captured_clock(fixture.root, fixture.config, reservation, reservation['command'])
        output = fixture.root / 'jobs' / recovery.JOB
        write_json(output / 'config.json', request)
        row, _ = fixtures.synthetic_row(fixture.root / 'numeric', request)
        rows = [dict(row, identity=i.record()) for i in output_identities(fixture.config, 'calibration')]
        first = first_record(request, output, 'passed', clock=clock, rows=rows[:1],
            runtime=fixture.observed, checks=qualify_row(row, request, first=True), raw=[row['diagnostics']])
        result = dict(status='complete', job_id=recovery.JOB, component='S1', branch='calibration',
            rows=rows, runtime=fixture.observed, native_wall_seconds=63.75,
            peak_allocated_bytes=1024, peak_reserved_bytes=2048,
            configuration=file_record(output / 'config.json'), first_result=first, reservation_clock=clock.mapping())
        write_json(output / 'result.json', result)
        return fixture, request, reservation, output, result

    def test_acceptance_preserves_admitted_snapshot_alias_and_target(self):
        fixture, request, reservation, output, result = self.admitted_result()
        prefix = fixture.ledger.path.read_bytes()
        unchanged = {path: path.read_bytes() for path in
            (output / 'result.json', output / 'config.json', Path(reservation['evidence']['request']['path']))}
        accepted = recovery.accept_result(fixture.root, fixture.config, request, result, output, reservation=reservation)
        document = read_json(accepted['path'])
        self.assertEqual(document['status'], 'passed')
        self.assertEqual(document['count'], 510)
        self.assertNotIn(self.asset_record, document['records'])
        for binding in self.expected_aliases:
            info = Path(binding['alias']['path']).lstat()
            binding['alias_identity'] = dict(device=info.st_dev, inode=info.st_ino, size=info.st_size,
                mtime_ns=info.st_mtime_ns, ctime_ns=info.st_ctime_ns)
        self.assertEqual(document['asset_aliases'], self.expected_aliases)
        self.assertIn(file_record(self.blob), document['records'])
        self.assertEqual({path: path.read_bytes() for path in unchanged}, unchanged)
        self.assertEqual(fixture.ledger.path.read_bytes(), prefix)

    def test_acceptance_rejects_escaped_target_even_with_admitted_payload(self):
        fixture, request, reservation, output, result = self.admitted_result()
        outside = fixture.root / 'same-payload-outside-cache'
        outside.write_bytes(self.blob.read_bytes())
        self.alias.unlink()
        self.alias.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'relative sibling blob'):
            recovery.accept_result(fixture.root, fixture.config, request, result, output, reservation=reservation)
        self.alias.unlink()
        self.alias.symlink_to('../../../same-payload-outside-cache')
        with self.assertRaisesRegex(ValueError, 'escaped sibling blobs'):
            recovery.accept_result(fixture.root, fixture.config, request, result, output, reservation=reservation)
        self.assertFalse((output / 'acceptance.json').exists())

    def test_acceptance_rejects_broken_cyclic_and_changed_payload_targets(self):
        fixture, request, reservation, output, result = self.admitted_result()
        original = self.blob.read_bytes()
        prefix = fixture.ledger.path.read_bytes()
        self.blob.unlink()
        with self.assertRaises(FileNotFoundError):
            recovery.accept_result(fixture.root, fixture.config, request, result, output, reservation=reservation)
        self.blob.symlink_to(self.alias)
        with self.assertRaises(OSError):
            recovery.accept_result(fixture.root, fixture.config, request, result, output, reservation=reservation)
        self.blob.unlink()
        self.blob.write_bytes(original.replace(b'admitted', b'altered!'))
        with self.assertRaisesRegex(ValueError, 'changed file'):
            recovery.accept_result(fixture.root, fixture.config, request, result, output, reservation=reservation)
        self.assertFalse((output / 'acceptance.json').exists())
        self.assertEqual(fixture.ledger.path.read_bytes(), prefix)

    def test_acceptance_rejects_blob_directory_alias_with_identical_payload(self):
        fixture, request, reservation, output, result = self.admitted_result()
        blobs = self.blob.parent
        moved = blobs.parent / 'moved-blobs'
        blobs.rename(moved)
        blobs.symlink_to(moved, target_is_directory=True)
        with self.assertRaises(OSError):
            recovery.accept_result(fixture.root, fixture.config, request, result, output, reservation=reservation)
        self.assertFalse((output / 'acceptance.json').exists())

    def test_acceptance_rejects_blob_alias_with_identical_payload(self):
        fixture, request, reservation, output, result = self.admitted_result()
        replacement = fixture.root / 'outside-identical-payload'
        replacement.write_bytes(self.blob.read_bytes())
        self.blob.unlink()
        self.blob.symlink_to(replacement)
        with self.assertRaises(OSError):
            recovery.accept_result(fixture.root, fixture.config, request, result, output, reservation=reservation)
        self.assertFalse((output / 'acceptance.json').exists())

    def test_result_alias_does_not_receive_asset_exception(self):
        fixture, request, reservation, output, result = self.admitted_result()
        forged = copy.deepcopy(result)
        forged['ordinary_evidence'] = dict(self.asset_record)
        (output / 'result.json').unlink()
        write_json(output / 'result.json', forged)
        # Result qualification accepts additional evidence; the ordinary byte
        # collector must still reject its alias instead of granting asset trust.
        with self.assertRaises(OSError):
            recovery.accept_result(fixture.root, fixture.config, request, forged, output, reservation=reservation)
        self.assertFalse((output / 'acceptance.json').exists())

    def test_acceptance_rejects_alias_parent_replaced_after_target_read(self):
        from vipe_benchmark import s1_progress as progress
        fixture, request, reservation, output, result = self.admitted_result()
        original_operation = progress.operation
        replaced = []
        def replace_parent(function, *args, **kwargs):
            value = original_operation(function, *args, **kwargs)
            if function is os.stat and args and args[0] == self.blob.name and not replaced:
                # The strict target reader just checked its anchored named blob.
                replaced.append(True)
                raw = os.readlink(self.alias)
                parent = self.alias.parent
                parent.rename(parent.with_name(parent.name + '-retained'))
                parent.mkdir()
                self.alias.symlink_to(raw)
            return value
        with patch.object(progress, 'operation', replace_parent):
            with self.assertRaisesRegex(ValueError, 'alias parent changed during verification'):
                recovery.accept_result(fixture.root, fixture.config, request, result, output, reservation=reservation)
        self.assertEqual(replaced, [True])
        self.assertFalse((output / 'acceptance.json').exists())

    def test_shared_request_asset_object_in_result_remains_ordinary_evidence(self):
        fixture, request, reservation, output, result = self.admitted_result()
        result['ordinary_evidence'] = request['assets']['bert_snapshot']['files'][0]
        (output / 'result.json').unlink()
        write_json(output / 'result.json', result)
        with self.assertRaises(OSError):
            recovery.accept_result(fixture.root, fixture.config, request, result, output, reservation=reservation)
        self.assertFalse((output / 'acceptance.json').exists())

    def test_historical_resolution_rejects_recreated_identical_alias(self):
        fixture, request, reservation, output, result = self.admitted_result()
        # Retain the old inode before acceptance, avoiding immediate inode reuse.
        os.link(self.alias, self.alias.parent / 'retained-old-alias', follow_symlinks=False)
        accepted = recovery.accept_result(fixture.root, fixture.config, request, result, output, reservation=reservation)
        result_record = file_record(output / 'result.json')
        receipt = fixture.put('synthetic-terminal.json', dict(status='complete', acceptance=accepted,
            outcome=dict(result=result_record)))
        finish = dict(job_id=recovery.JOB, status='complete', cleanup_confirmed=True,
            surviving_pids=[], deadline_exceeded=False, stop_required=False, result=result_record,
            acceptance=accepted, terminal_receipt=receipt,
            elapsed_seconds=time.monotonic() - reservation['monotonic_start'],
            peak=dict(device_bytes=0, artifact_bytes=0, download_bytes=0))
        events = fixture.ledger.events()
        self.assertEqual(recovery.resolved_result(fixture.root, fixture.config, events, finish), result_record)
        original = self.alias.lstat()
        raw = os.readlink(self.alias)
        self.alias.unlink()
        self.alias.symlink_to(raw)
        self.assertNotEqual(self.alias.lstat().st_ino, original.st_ino)
        self.assertEqual(os.readlink(self.alias), raw)
        self.assertEqual(dict(file_record(self.alias), path=str(self.alias)), self.asset_record)
        with self.assertRaisesRegex(ValueError, 'accepted referenced bytes changed'):
            recovery.resolved_result(fixture.root, fixture.config, events, finish)

    def test_historical_resolution_rejects_alias_retargeted_to_same_bytes(self):
        fixture, request, reservation, output, result = self.admitted_result()
        accepted = recovery.accept_result(fixture.root, fixture.config, request, result, output, reservation=reservation)
        result_record = file_record(output / 'result.json')
        receipt = fixture.put('synthetic-terminal.json', dict(status='complete', acceptance=accepted,
            outcome=dict(result=result_record)))
        finish = dict(job_id=recovery.JOB, status='complete', cleanup_confirmed=True,
            surviving_pids=[], deadline_exceeded=False, stop_required=False, result=result_record,
            acceptance=accepted, terminal_receipt=receipt,
            elapsed_seconds=time.monotonic() - reservation['monotonic_start'],
            peak=dict(device_bytes=0, artifact_bytes=0, download_bytes=0))
        events = fixture.ledger.events()
        prefix = fixture.ledger.path.read_bytes()
        self.assertEqual(recovery.resolved_result(fixture.root, fixture.config, events, finish), result_record)
        replacement = self.blob.parent / ('c' * 40)
        replacement.write_bytes(self.blob.read_bytes())
        self.alias.unlink()
        self.alias.symlink_to('../../blobs/' + replacement.name)
        with self.assertRaisesRegex(ValueError, 'accepted referenced bytes changed'):
            recovery.resolved_result(fixture.root, fixture.config, events, finish)
        self.assertEqual(fixture.ledger.path.read_bytes(), prefix)


if __name__ == '__main__':
    unittest.main()
