"""Exercise explicit cleanup time through the public process supervisor."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest

from vipe_benchmark.config import load
from vipe_benchmark.ledger import Ledger
from vipe_benchmark.supervisor import supervise, SupervisionFailure


class CleanupReservationTests(unittest.TestCase):
    def test_reserved_cleanup_shortens_worker_time(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = copy.deepcopy(load())
            config['cpu_prepare_score_report_seconds_limit'] = .8
            ledger = Ledger(root / 'ledger.jsonl', config)
            with self.assertRaises(SupervisionFailure):
                supervise(ledger, 'prepare', [sys.executable, '-c', 'import time; time.sleep(5)'],
                    root / 'output', evidence={'kind': 'disposable cleanup fixture'},
                    poll_seconds=.01, cleanup_reserve_seconds=.5)
            finish = ledger.states()['prepare']
            self.assertTrue(finish['cleanup_confirmed'])
            self.assertGreaterEqual(finish['elapsed_seconds'], .2)
            self.assertLess(finish['elapsed_seconds'], .55)

    def test_invalid_cleanup_rejected_before_output_or_attempt(self):
        for reserve in (True, 0, -1, float('nan'), float('inf'), .8, 1):
            with self.subTest(reserve=reserve), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                config = copy.deepcopy(load())
                config['cpu_prepare_score_report_seconds_limit'] = .8
                ledger = Ledger(root / 'ledger.jsonl', config)
                output = root / 'new-parent' / 'output'
                with self.assertRaises(ValueError):
                    supervise(ledger, 'prepare', ['unused'], output,
                        evidence={}, cleanup_reserve_seconds=reserve)
                self.assertFalse(output.parent.exists())
                self.assertEqual(ledger.events(), [])
