"""An approved second map attempt follows only a clean no-output worker failure."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vipe_benchmark import depth_map_retry as retry
from vipe_benchmark.files import file_record, object_hash, read_json, write_json

FIRST, SECOND = 'plan069-D8-maps-001', 'plan069-D8-maps-002'


class MapRetryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.proposal = dict(candidate='D8', allocation=dict(gpu_seconds=3600))
        self.failure = self.root / 'jobs' / FIRST / 'failure.json'
        write_json(self.failure, dict(schema='plan069-depth-single-maps-failure/v1', status='failed',
                                      candidate='D8', job_id=FIRST, completed_map_rows=0))
        self.grant = dict(event='depth_attempt_authorized', candidate='D8', seconds=3600, sequence=1,
                          review=dict(path='review'), authorization=dict(path='do'))
        self.finish = dict(event='finish', job_id=FIRST, status='failed', resource='gpu',
                           failure_kind='worker_failure', elapsed_seconds=19.4, cleanup_confirmed=True,
                           cleanup_uncertain=False, surviving_pids=[], deadline_exceeded=False,
                           sequence=3, event_sha256='f' * 64)
        self.events = [dict(event='cpu_preparation_charge', sequence=0), self.grant,
                       dict(event='reserve', job_id=FIRST, resource='gpu', sequence=2), self.finish]
        self.approval_path = self.root / 'approval.json'
        self.approve()
        patcher = patch.dict(retry.RETRIES, D8=dict(failed_job=FIRST, job=SECOND, approval=self.approval_path))
        patcher.start()
        self.addCleanup(patcher.stop)

    def approve(self, **changes):
        if self.approval_path.exists():
            self.approval_path.unlink()
        write_json(self.approval_path, dict(dict(
            schema=retry.SCHEMA, status='DO', candidate='D8', failed_job=FIRST, job=SECOND,
            failed_finish_event_sha256='f' * 64, failure=file_record(self.failure),
            proposal_sha256=object_hash(self.proposal), gpu_seconds=3580, max_attempts=1,
            review=dict(path='review'), authorization=dict(path='do'), device_ceiling_unchanged=True,
            approved_by='operator'), **changes))

    def test_first_attempt_is_the_map_job_until_it_finishes(self):
        self.assertEqual(retry.map_job('D8', self.events[:3]), FIRST)
        self.assertEqual(retry.map_job('D8', self.events), SECOND)
        completed = self.events[:3] + [dict(self.finish, status='complete')]
        self.assertEqual(retry.map_job('D8', completed), FIRST)
        self.assertEqual(retry.map_job('D5', self.events), 'plan069-D5-maps-001')

    def test_clean_no_output_failure_grants_the_remaining_gpu_seconds(self):
        granted = retry.validate_retry('D8', self.proposal, self.events, self.root)
        self.assertEqual((granted['job'], granted['seconds']), (SECOND, 3600 - 20))
        self.assertEqual(granted['approval'], file_record(self.approval_path))
        self.assertEqual(granted['failed_finish_event_sha256'], 'f' * 64)

    def test_unclean_or_productive_first_attempts_are_never_retried(self):
        for change in (dict(status='complete'), dict(failure_kind='deadline'), dict(cleanup_confirmed=False),
                       dict(cleanup_uncertain=True), dict(surviving_pids=[7]), dict(deadline_exceeded=True)):
            with self.subTest(change=change):
                events = self.events[:3] + [dict(self.finish, **change)]
                with self.assertRaises(ValueError):
                    retry.validate_retry('D8', self.proposal, events, self.root)
        write_json(self.failure.with_name('result.json'), dict(status='complete'))
        with self.assertRaisesRegex(ValueError, 'no map output'):
            retry.validate_retry('D8', self.proposal, self.events, self.root)

    def test_failure_with_written_rows_is_never_retried(self):
        self.failure.unlink()
        write_json(self.failure, dict(schema='plan069-depth-single-maps-failure/v1', status='failed',
                                      candidate='D8', job_id=FIRST, completed_map_rows=4))
        with self.assertRaisesRegex(ValueError, 'no map output'):
            retry.validate_retry('D8', self.proposal, self.events, self.root)

    def test_approval_must_bind_the_exact_failure_proposal_and_seconds(self):
        for change in (dict(status='REVIEW'), dict(failed_finish_event_sha256='0' * 64),
                       dict(gpu_seconds=3600), dict(proposal_sha256='0' * 64), dict(max_attempts=2),
                       dict(job='plan069-D8-maps-003'), dict(failure=dict(path='x', sha256='0', bytes=1)),
                       dict(review=dict(path='other')), dict(authorization=dict(path='other')),
                       dict(device_ceiling_unchanged=False)):
            with self.subTest(change=change):
                self.approve(**change)
                with self.assertRaises(ValueError):
                    retry.validate_retry('D8', self.proposal, self.events, self.root)

    def test_candidates_without_an_approved_retry_keep_one_attempt(self):
        events = [dict(row, candidate='D5', job_id='plan069-D5-maps-001') if 'job_id' in row or
                  row['event'] == 'depth_attempt_authorized' else row for row in self.events]
        with self.assertRaisesRegex(ValueError, 'no approved map retry'):
            retry.validate_retry('D5', dict(self.proposal, candidate='D5'), events, self.root)

    def test_current_allocation_is_the_retry_grant_only_after_the_first(self):
        second = dict(self.grant, job_id=SECOND, sequence=4)
        self.assertIs(retry.current_allocation('D8', self.events), self.grant)
        self.assertIs(retry.current_allocation('D8', self.events + [second]), second)
        self.assertIsNone(retry.current_allocation('D8', self.events + [second, dict(second, sequence=5)]))
        self.assertIsNone(retry.current_allocation('D8', [self.events[0]]))
        self.assertIsNone(retry.current_allocation('D5', [dict(self.grant, candidate='D5'),
                                                          dict(self.grant, candidate='D5')]))
        self.assertTrue(retry.is_map_job(SECOND) and retry.is_map_job('plan069-D5-maps-001'))
        self.assertFalse(retry.is_map_job('plan069-D5-maps-002'))


class WorkerIdentityTests(unittest.TestCase):
    def gate(self, job, events):
        from vipe_benchmark import depth_single_run

        class Ledger:
            def __init__(self, path, config):
                pass

            def events(self):
                return events

            def states(self, _events=None):
                return {}
        with tempfile.TemporaryDirectory() as temp, patch.object(depth_single_run, 'Ledger', Ledger):
            request = dict(candidate='D8', job_id=job, ledger_path=str(Path(temp) / 'ledger.jsonl'))
            output = Path(temp) / 'jobs' / job
            depth_single_run._actual_gate(request, Path(temp) / 'request.json', output)

    def test_worker_accepts_only_the_current_map_job(self):
        finished = [dict(event='finish', job_id=FIRST, status='failed')]
        with self.assertRaisesRegex(ValueError, 'GPU reservation required'):
            self.gate(FIRST, [dict(finished[0], status='complete')])
        with self.assertRaisesRegex(ValueError, 'exact map identity'):
            self.gate(FIRST, finished)
        with self.assertRaisesRegex(ValueError, 'exact map identity'):
            self.gate(SECOND, [])
        with self.assertRaisesRegex(ValueError, 'GPU reservation required'):
            self.gate(SECOND, finished)

if __name__ == '__main__':
    unittest.main()


class PinnedRetryApprovalTests(unittest.TestCase):
    def test_each_pinned_retry_approval_names_its_own_candidate_and_jobs(self):
        from vipe_benchmark.depth_map_retry import RETRIES, SCHEMA
        for candidate, retry in RETRIES.items():
            with self.subTest(candidate=candidate):
                approval = read_json(retry['approval'])
                self.assertEqual((approval['schema'], approval['status'], approval['candidate'],
                                  approval['failed_job'], approval['job'], approval['max_attempts']),
                                 (SCHEMA, 'DO', candidate, f'plan069-{candidate}-maps-001',
                                  f'plan069-{candidate}-maps-002', 1))
