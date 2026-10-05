"""Candidate-agnostic setup-recovery ancestry over synthetic ledger rows."""
import unittest
from unittest.mock import patch

from vipe_benchmark.files import object_hash


def ledger(*rows):
    events: list[dict] = []
    previous = None
    for data in rows:
        row = dict(data, sequence=len(events), previous_sha256=previous)
        row['event_sha256'] = object_hash(row)
        events.append(row)
        previous = row['event_sha256']
    return events


CLEAN = dict(cleanup_confirmed=True, cleanup_uncertain=False, surviving_pids=[], deadline_exceeded=False)
FIXTURE = dict(original_job='plan069-DX-setup-001', jobs=('plan069-DX-setup-recovery-001',),
               result_schemas={'plan069-DX-setup-recovery-001': 'plan069-DX-recovery-result/v1'})


class SetupRecoveryCoreTests(unittest.TestCase):
    def setUp(self):
        from vipe_benchmark import setup_recovery_core as core
        self.core = core
        adapter = patch.dict(core.RECOVERY_CANDIDATES, {'DX': FIXTURE})
        adapter.start()
        self.addCleanup(adapter.stop)

    def failed_original(self, **finish):
        return ledger(dict(event='depth_setup_authorized', candidate='DX'),
                      dict(event='reserve', job_id='plan069-DX-setup-001', resource='setup'),
                      dict(event='finish', job_id='plan069-DX-setup-001', resource='setup',
                           **{**CLEAN, 'status': 'failed', **finish}))

    def test_d9_identities_are_unchanged(self):
        self.assertEqual(self.core.RECOVERY_CANDIDATES['D9'], dict(
            original_job='plan069-D9-setup-001',
            jobs=('plan069-D9-setup-recovery-001', 'plan069-D9-setup-recovery-002'),
            result_schemas={'plan069-D9-setup-recovery-001': 'plan069-video-setup-recovery-result/v1',
                            'plan069-D9-setup-recovery-002': 'plan069-video-setup-recovery-result/v2'}))

    def test_jobs_route_to_their_candidate_only(self):
        self.assertEqual(self.core.candidate_for_job('plan069-DX-setup-recovery-001'), 'DX')
        self.assertEqual(self.core.candidate_for_job('plan069-D9-setup-recovery-002'), 'D9')
        self.assertIsNone(self.core.candidate_for_job('plan069-DX-setup-001'))
        self.assertIsNone(self.core.candidate_for_job('plan069-D8-maps-001'))

    def test_exact_clean_failed_original_is_accepted(self):
        events = self.failed_original()
        lineage = self.core.failed_setup_ancestry(
            'DX', 'plan069-DX-setup-001', events,
            dict(grant_event_sha256=events[0]['event_sha256'],
                 failed_finish_event_sha256=events[2]['event_sha256']))
        self.assertEqual((lineage['grant'], lineage['reserve'], lineage['finish']), tuple(events))

    def test_completed_unclean_or_unbound_original_is_rejected(self):
        for finish in (dict(status='complete'), dict(cleanup_confirmed=False),
                       dict(surviving_pids=[7]), dict(deadline_exceeded=True)):
            with self.subTest(finish=finish):
                events = self.failed_original(**finish)
                with self.assertRaises(ValueError):
                    self.core.failed_setup_ancestry('DX', 'plan069-DX-setup-001', events, dict(
                        grant_event_sha256=events[0]['event_sha256'],
                        failed_finish_event_sha256=events[2]['event_sha256']))
        events = self.failed_original()
        with self.assertRaises(ValueError):
            self.core.failed_setup_ancestry('DX', 'plan069-DX-setup-001', events,
                dict(grant_event_sha256='0' * 64, failed_finish_event_sha256=events[2]['event_sha256']))

    def test_clean_completed_recovery_is_accepted_and_failed_one_rejected(self):
        record = dict(path='/run/jobs/plan069-DX-setup-recovery-001/result.json', sha256='a' * 64, bytes=1)
        job = 'plan069-DX-setup-recovery-001'
        rows = [dict(event='depth_setup_recovery_authorized', candidate='DX', job_id=job),
                dict(event='reserve', job_id=job, resource='setup')]
        events = ledger(*rows, dict(event='finish', job_id=job, resource='setup', status='complete',
                                    result=record, **CLEAN))
        completed = self.core.completed_recovery('DX', job, record, events)
        self.assertEqual(completed['finish'], events[2])
        failed = ledger(*rows, dict(event='finish', job_id=job, resource='setup', status='failed',
                                    result=record, **CLEAN))
        with self.assertRaises(ValueError):
            self.core.completed_recovery('DX', job, record, failed)
        with self.assertRaises(ValueError):
            self.core.completed_recovery('D9', job, record, events)


if __name__ == '__main__':
    unittest.main()
