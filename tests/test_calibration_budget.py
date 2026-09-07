import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import calibration_budget as budget


class BudgetTests(unittest.TestCase):
    def test_failed_attempt_counts_separately(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / 'ledger.json'
            def worker(*args, **kwargs):
                reserved = json.loads(ledger.read_text())['attempts'][0]
                self.assertEqual(reserved['charged_seconds'], 60)
                self.assertEqual(reserved['status'], 'reserved')
                return dict(exit_code=1, stop_requested=False, forced_kill=False)
            with patch.object(budget, 'supervise', side_effect=worker), patch.object(budget.time, 'monotonic', side_effect=[10, 17]):
                self.assertEqual(budget.run(ledger, ['worker'], seconds=60, log_path=Path(tmp)/'log'), 1)
            value = json.loads(ledger.read_text())
            self.assertEqual(value['schema'], 'basketball-calibration-budget/v1')
            self.assertEqual(value['attempts'][0]['charged_seconds'], 7)
            self.assertEqual(value['attempts'][0]['status'], 'failed')

    def test_crash_retains_reservation(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / 'ledger.json'
            with patch.object(budget, 'supervise', side_effect=RuntimeError('crash')):
                with self.assertRaisesRegex(RuntimeError, 'crash'):
                    budget.run(ledger, ['worker'], seconds=28800, log_path=Path(tmp)/'log')
            with self.assertRaisesRegex(ValueError, 'remain'):
                budget.run(ledger, ['worker'], seconds=60, log_path=Path(tmp)/'log2')

    def test_reject_training_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / 'ledger.json'
            ledger.write_text(json.dumps({'schema': 'plan-004-training-budget/v1', 'attempts': []}))
            with self.assertRaisesRegex(ValueError, 'invalid calibration ledger'):
                budget.run(ledger, ['worker'], seconds=60, log_path=Path(tmp)/'log')


if __name__ == '__main__':
    unittest.main()
