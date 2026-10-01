"""Public CPU standing-retry controls over immutable failure evidence."""
import copy
import json
import sys
import shutil
from contextlib import contextmanager
import tempfile
import unittest
from contextlib import ExitStack
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark import s1_recovery as recovery, s1_retry as retry
import test_vipe_benchmark_s1_recovery as fixtures
from vipe_benchmark.config import ROOT, load
from vipe_benchmark.files import file_record, read_json, write_json

SUBTEST_CASES = {
    'test_vipe_benchmark_s1_standing_retry.S1StandingRetryTests.test_policy_scope_and_chain_guards': [
        {'kind': 'authority'}, {'kind': 'policy'}, {'kind': 'total_cap'}, {'kind': 'identity_skip'},
        {'kind': 'seconds'}, {'kind': 'reconstruction'}, {'kind': 'correction'}, {'kind': 'stale_qualification'}],
    'test_vipe_benchmark_s1_standing_retry.S1StandingRetryTests.test_success_active_cleanup_and_budgets_block_retry': [
        {'kind': 'success'}, {'kind': 'unclean'}, {'kind': 'survivor'}, {'kind': 'active'},
        {'kind': 'gpu_budget'}, {'kind': 'cpu_budget'}, {'kind': 'setup_budget'}]
}


class S1StandingRetryTests(unittest.TestCase):
    def prepared(self):
        historical = fixtures.S1NinthReviewTests('runTest')
        historical.setUp()
        self.addCleanup(historical.doCleanups)
        snapshot = ROOT / 'docs/research/vipe-alternatives/plan031-execution/s1-recovery-009/outcome/ledger-after.jsonl'
        historical.fixture_raw = snapshot.read_bytes()
        historical.before = historical.fixture_raw
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.object(recovery, 'ROOT', historical.main))
        for name, suffix in [('PROCESS_FILE_AMENDMENT', 'issue3-preparation/s1-process-file-amendment-001.json'),
                ('PROCESS_FILE_AMENDMENT_2', 'plan031-execution/s1-process-file-amendment-002.json'),
                ('PROCESS_FILE_AMENDMENT_3', 'plan031-execution/s1-process-file-amendment-003.json')]:
            stack.enter_context(patch.object(recovery, name, historical.main / 'docs/research/vipe-alternatives' / suffix))
        from vipe_benchmark import s1_validation_contract as contract
        current = self.root / 'current-source'
        for source in contract.source_paths():
            target = current / source.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        stack.enter_context(patch.object(contract, 'ROOT', current))
        stack.enter_context(patch.object(fixtures, 'ROOT', current))
        stack.enter_context(patch.object(contract, 'ARGV', [sys.executable, '-B', '-']))
        self.current = current
        self.stack = stack
        previous_record = file_record(historical.main / 'docs/research/vipe-alternatives/plan031-execution/s1-recovery-009/do.json')
        previous = read_json(previous_record['path'])
        graph = fixtures.ReceiptFixture(self.root / 'qualification',
            {key: previous[key] for key in ('semantic_amendment', 'configuration', 'baseline', 'baseline_correction', 'plan')})
        review = self.root / 'independent-review.md'
        review.write_text('Synthetic CPU fixture: reviewed ninth alias failure and relevant current source changes.')
        diagnosis = file_record(ROOT / 'docs/research/vipe-alternatives/plan031-execution/s1-recovery-009/acceptance-symlink-diagnosis.md')
        events = [json.loads(line) for line in historical.fixture_raw.splitlines()]
        correction = retry.build_correction(events[-1], previous_record, diagnosis, graph.record,
            file_record(review), file_record(snapshot))
        write_json(self.root / 'correction.json', correction)
        proposal = retry.build_review_proposal(historical.local, load(), graph.record, file_record(review),
            '2026-09-30', correction=file_record(self.root / 'correction.json'))
        write_json(self.root / 'review.json', proposal)
        do = retry.approve_review(file_record(self.root / 'review.json'))
        write_json(self.root / 'do.json', do)
        return historical, events, graph, proposal, do

    def disposable_ledger(self, historical, events):
        from vipe_benchmark.ledger import Ledger
        from vipe_benchmark.files import canonical
        ledger = Ledger(historical.local / 'ledger.jsonl', load())
        sink = self.root / 'ledger-sink.jsonl'
        sink.write_bytes(historical.fixture_raw)
        @contextmanager
        def locked():
            with sink.open('r+') as stream:
                try:
                    yield stream, events
                finally:
                    historical.fixture_raw = ''.join(canonical(event) + '\n' for event in events).encode()
        self.stack.enter_context(patch.object(ledger, 'locked', locked))
        return ledger

    def register_and_reserve(self, historical, events, do):
        from vipe_benchmark import s1_progress as progress
        from vipe_benchmark.execution import component_recovery_request
        ledger = self.disposable_ledger(historical, events)
        authorization = file_record(self.root / 'do.json')
        evidence = dict(do, s1_recovery_authorization=authorization, implementation_validation=do['repair_validation'])
        write_json(self.root / 'admission.json', dict(status='admitted', evidence=evidence))
        admission = ledger.note('admission', evidence=file_record(self.root / 'admission.json'))
        registration = ledger.authorize_component_recovery(authorization)
        request = dict(component_recovery_request(historical.local, load(), do['job_id']), configuration=do['configuration'])
        physical = self.root / 'request.json'
        write_json(physical, request)
        virtual = historical.local / 'requests' / (do['job_id'] + '.json')
        request_record = dict(file_record(physical), path=str(virtual))
        original_bytes = progress.read_bytes
        original_stat = Path.stat
        def mapped_bytes(path, limit, *args, **kwargs):
            if Path(path) == virtual:
                raw = physical.read_bytes()
                self.assertLessEqual(len(raw), limit)
                return raw
            return original_bytes(path, limit, *args, **kwargs)
        def mapped_stat(path, *args, **kwargs):
            if path == virtual:
                return original_stat(physical, *args, **kwargs)
            return original_stat(path, *args, **kwargs)
        self.stack.enter_context(patch.object(progress, 'read_bytes', mapped_bytes))
        self.stack.enter_context(patch.object(Path, 'stat', mapped_stat))
        bound = dict(request=request_record, worker=file_record(historical.main / 'scripts/basketball_vipe_worker.py'),
            authorization=authorization, admission=admission['evidence'], authorization_event=recovery.event_ref(registration),
            **{key: do[key] for key in recovery.BINDINGS if key != 'original_request_sha256'})
        command = recovery.canonical_dispatch(do, authorization, bound)
        reservation = ledger.reserve(do['job_id'], command, bound)
        return ledger, authorization, request, reservation

    def test_registration_reservation_clock_and_consumed_identity(self):
        historical, events, graph, proposal, do = self.prepared()
        ledger, authorization, request, reservation = self.register_and_reserve(historical, events, do)
        clock = recovery.captured_clock(historical.local, load(), reservation, reservation['command'])
        self.assertEqual(clock.job_id, 'S1-calibration-recovery-010')
        self.assertEqual(clock.effective_seconds, 3600)
        self.assertEqual(clock.mapping()['request'], reservation['evidence']['request'])
        with self.assertRaises(ValueError):
            ledger.reserve(do['job_id'], reservation['command'], reservation['evidence'])
        with self.assertRaises(ValueError):
            ledger.authorize_component_recovery(authorization)
        self.assertTrue((self.root / 'ledger-sink.jsonl').read_bytes().startswith(historical.before))

    def variant(self, proposal, name, **changes):
        review = dict(copy.deepcopy(proposal), **changes)
        review_path = self.root / (name + '-review.json')
        write_json(review_path, review)
        do = dict(review, additional_attempt_approved=True,
            authorization_context=dict(review['authorization_context'], stage='DO'), review_proposal=file_record(review_path))
        do_path = self.root / (name + '-do.json')
        write_json(do_path, do)
        return file_record(do_path)

    def test_policy_scope_and_chain_guards(self):
        historical, events, graph, proposal, do = self.prepared()
        prefix = historical.fixture_raw
        for case in SUBTEST_CASES[f'{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}']:
            with self.subTest(**case):
                kind = case['kind']
                changes = {}
                if kind in ('authority', 'policy'):
                    value = copy.deepcopy(proposal['standing_retry_authority'])
                    value['approval' if kind == 'authority' else 'policy_amendment']['sha256'] = '0' * 64
                    changes['standing_retry_authority'] = value
                elif kind == 'total_cap': changes['total_attempts_limit'] = 10
                elif kind == 'identity_skip': changes['job_id'] = 'S1-calibration-recovery-012'
                elif kind == 'seconds': changes['seconds_limit'] = 3601
                elif kind == 'reconstruction': changes['branch'] = 'reconstruction'
                elif kind == 'correction':
                    value = read_json(proposal['retry_correction']['path'])
                    value['changes'] = []
                    path = self.root / 'unchanged-correction.json'
                    write_json(path, value)
                    changes['retry_correction'] = file_record(path)
                elif kind == 'stale_qualification':
                    target = self.current / 'scripts/vipe_benchmark/s1_retry.py'
                    original = target.read_bytes()
                    target.write_bytes(original + b'\n# changed disposable qualification source\n')
                try:
                    with self.assertRaises(ValueError):
                        recovery.validate_binding(historical.local, load(), self.variant(proposal, kind, **changes), events=events)
                finally:
                    if kind == 'stale_qualification': target.write_bytes(original)
                self.assertEqual(historical.fixture_raw, prefix)

    def test_success_active_cleanup_and_budgets_block_retry(self):
        historical, events, graph, proposal, do = self.prepared()
        from vipe_benchmark.files import canonical, object_hash
        before = historical.fixture_raw
        for case in SUBTEST_CASES[f'{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}']:
            with self.subTest(**case):
                kind = case['kind']
                changed = copy.deepcopy(events)
                if kind in ('success', 'unclean', 'survivor'):
                    if kind == 'success': changed[-1]['status'] = 'complete'
                    elif kind == 'unclean': changed[-1]['cleanup_uncertain'] = True
                    else: changed[-1]['surviving_pids'] = [12345]
                    changed[-1]['event_sha256'] = object_hash({key: value for key, value in changed[-1].items() if key != 'event_sha256'})
                else:
                    resource = kind.split('_')[0] if kind != 'active' else 'gpu'
                    extra = dict(event='reserve' if kind == 'active' else 'finish', job_id='fixture-charge',
                        resource=resource, sequence=len(changed), previous_sha256=changed[-1]['event_sha256'],
                        seconds=1, elapsed_seconds=93600 if resource == 'gpu' else 57600)
                    extra['event_sha256'] = object_hash(extra)
                    changed.append(extra)
                historical.fixture_raw = ''.join(canonical(event) + '\n' for event in changed).encode()
                with self.assertRaises(ValueError):
                    retry.build_review_proposal(historical.local, load(), graph.record, proposal['implementation_review'],
                        '2026-09-30', correction=proposal['retry_correction'])
                historical.fixture_raw = before

    def test_validated_correction_allows_next_fresh_identity_after_failed_tenth(self):
        historical, events, graph, proposal, do = self.prepared()
        ledger, authorization, request, reservation = self.register_and_reserve(historical, events, do)
        failed = ledger.finish(do['job_id'], 'failed', .125, cleanup_confirmed=True,
            cleanup_uncertain=False, surviving_pids=[], reservation=recovery.event_ref(reservation),
            result=None, acceptance=None, stop_required=True, terminal_receipt=None,
            terminal_publication_status='unavailable', terminal_publication_block_reason='synthetic corrected failure')
        snapshot = self.root / 'failed-tenth-ledger.jsonl'
        snapshot.write_bytes(historical.fixture_raw)
        diagnosis = self.root / 'tenth-diagnosis.md'
        diagnosis.write_text('Synthetic CPU failed tenth requires a relevant source correction.')
        with self.assertRaisesRegex(ValueError, 'unchanged failed execution'):
            retry.build_correction(failed, authorization, file_record(diagnosis), graph.record,
                proposal['implementation_review'], file_record(snapshot))
        fix = self.current / 'scripts/vipe_benchmark/disposable-retry-correction.py'
        fix.write_text('"""Synthetic source correction; no model execution."""\n')
        after = fixtures.ReceiptFixture(self.root / 'corrected-qualification',
            {key: do[key] for key in ('semantic_amendment', 'configuration', 'baseline', 'baseline_correction', 'plan')})
        correction = retry.build_correction(failed, authorization, file_record(diagnosis), after.record,
            proposal['implementation_review'], file_record(snapshot))
        self.assertEqual(correction['changes'], [dict(before=None, after=file_record(fix))])
        write_json(self.root / 'tenth-correction.json', correction)
        next_proposal = retry.build_review_proposal(historical.local, load(), after.record, proposal['implementation_review'],
            '2026-09-30', correction=file_record(self.root / 'tenth-correction.json'))
        self.assertEqual(next_proposal['job_id'], 'S1-calibration-recovery-011')
        self.assertIsNone(next_proposal['total_attempts_limit'])
        self.assertEqual(next_proposal['previous_recovery_failure'], failed)
        write_json(self.root / 'eleventh-review.json', next_proposal)
        next_do = retry.approve_review(file_record(self.root / 'eleventh-review.json'))
        write_json(self.root / 'eleventh-do.json', next_do)
        bound, canonical_request = recovery.validate_binding(historical.local, load(), file_record(self.root / 'eleventh-do.json'), events=events)
        self.assertEqual(bound['job_id'], 'S1-calibration-recovery-011')
        self.assertEqual(canonical_request['job_id'], 'S1-calibration')
        self.assertEqual(events[578]['event_sha256'], retry.NINTH_FINISH['event_sha256'])

    def test_standing_review_and_do_preserve_failed_ninth_without_allocation(self):
        historical, events, graph, proposal, do = self.prepared()
        self.assertEqual(proposal['job_id'], 'S1-calibration-recovery-010')
        self.assertIsNone(proposal['total_attempts_limit'])
        self.assertEqual(proposal['attempts_limit'], 1)
        self.assertFalse(proposal['approval_required'])
        self.assertEqual(proposal['previous_recovery_failure'], events[-1])
        self.assertEqual(proposal['previous_recovery_failure']['sequence'], 578)
        self.assertTrue(proposal['previous_recovery_failure']['stop_required'])
        self.assertIsNone(proposal['previous_recovery_failure']['terminal_receipt'])
        bound, request = recovery.validate_binding(historical.local, load(), file_record(self.root / 'do.json'), events=events)
        self.assertEqual(bound['job_id'], 'S1-calibration-recovery-010')
        self.assertEqual(request['job_id'], 'S1-calibration')
        self.assertEqual((historical.local / 'ledger.jsonl').read_bytes(), historical.before)
        with self.assertRaises(ValueError):
            recovery.validate_binding(historical.local, load(), file_record(self.root / 'review.json'), events=events)

    def test_fresh_standing_identity_requires_its_policy_contract(self):
        original = read_json(Path(__file__).resolve().parents[1] /
            'docs/research/vipe-alternatives/plan031-execution/s1-recovery-009/do.json')
        document = dict(original, schema='vipe-benchmark-s1-standing-calibration-recovery/v1',
            job_id='S1-calibration-recovery-010', total_attempts_limit=None)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_json(root / 'do.json', document)
            from vipe_benchmark.config import load
            with self.assertRaisesRegex(ValueError, 'standing retry authority'):
                recovery.validate_binding(root, load(), file_record(root / 'do.json'), events=[])


if __name__ == '__main__':
    unittest.main()
