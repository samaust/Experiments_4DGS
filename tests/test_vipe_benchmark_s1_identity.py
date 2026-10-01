"""Pure S1 retry identity and immutable clock boundaries; no GPU dispatch."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.s1_identity import is_recovery_job, is_standing_retry_job, job_from_attempt, prior_job


class IdentityTests(unittest.TestCase):
    def test_canonical_fresh_identities_continue_beyond_three_digits(self):
        for attempt, job, previous in (
            (1, 'S1-calibration-recovery-001', None),
            (9, 'S1-calibration-recovery-009', 'S1-calibration-recovery-008'),
            (10, 'S1-calibration-recovery-010', 'S1-calibration-recovery-009'),
            (1000, 'S1-calibration-recovery-1000', 'S1-calibration-recovery-999'),
        ):
            with self.subTest(job=job):
                self.assertEqual(job_from_attempt(attempt), job)
                self.assertTrue(is_recovery_job(job))
                self.assertEqual(is_standing_retry_job(job), attempt >= 10)
                self.assertEqual(prior_job(job), previous)
        for job in (None, 10, '', 'S1-calibration-recovery-000', 'S1-calibration-recovery-10',
                    'S1-calibration-recovery-0010', 'S1-calibration-recovery-010\n',
                    'S1-reconstruction-recovery-010', 'S1-calibration-recovery-+10'):
            with self.subTest(invalid=job):
                self.assertFalse(is_recovery_job(job))
                self.assertFalse(is_standing_retry_job(job))
                with self.assertRaises(ValueError):prior_job(job)
        for attempt in (True, False, 0, -1, 10., '10'):
            with self.assertRaises(ValueError):job_from_attempt(attempt)


if __name__ == '__main__':unittest.main()
