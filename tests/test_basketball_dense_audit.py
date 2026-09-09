"""Reject overlapping, unclosed, and unpaired Plan 027 GPU jobs."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from basketball_dense_audit import ledger_audit


class LedgerTests(unittest.TestCase):
    def test_failed_attempt_remains_charged(self):
        events=[dict(event='start',output='a'),dict(event='finish',output='a',stage='training',charged_seconds=2,exit_code=1),
            dict(event='start',output='b'),dict(event='finish',output='b',stage='training',charged_seconds=3,exit_code=0)]
        result=ledger_audit(events)
        self.assertEqual(result['charged_gpu_job_wall_seconds'],{'training':5})
        self.assertEqual(len(result['failures']),1)
        self.assertEqual(result['peak_concurrency'],1)

    def test_overlap_and_unclosed_rejected(self):
        for events in ([dict(event='start',output='a')],
                [dict(event='start',output='a'),dict(event='start',output='b')],
                [dict(event='finish',output='a')],
                [dict(event='cleanup-failed',container='a')]):
            with self.assertRaises(ValueError):ledger_audit(events)


if __name__=='__main__':unittest.main()
