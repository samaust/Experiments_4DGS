import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('training_budget',
    Path(__file__).resolve().parents[1]/'scripts/training_budget.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class BudgetTests(unittest.TestCase):
    def test_bounded_plan_reservation_preserves_later_seeds(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'budget.json'
            now = [0.]
            with module.TrainingBudget(path, method='stg-full', scene='vru-basketball-dg',
                                       clock=lambda: now[0]) as b:
                with self.assertRaises(ValueError):
                    b.start(command=[], provenance={}, seconds=7201)
                b.start(command=['seed0'], provenance={}, seconds=1200)
                self.assertEqual(b.remaining_seconds(),1200)
                # An unfinalized bounded run consumes its complete reservation.
            with module.TrainingBudget(path, method='stg-full', scene='vru-basketball-dg') as b:
                self.assertEqual(b.available,6000)

    def test_failed_attempt_counts_and_crash_reservation_persists(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'budget.json'
            now = [100.]
            def budget():
                return module.TrainingBudget(path, method='stg-lite', scene='selfcap-dance1',
                                             clock=lambda: now[0])
            with self.assertRaisesRegex(ValueError, 'synthetic failure'):
                with budget() as b:
                    b.start(command=['synthetic'], provenance={})
                    now[0] += 17
                    raise ValueError('synthetic failure')
            with budget() as b:
                self.assertEqual(b.available, 7183)
                b.start(command=['synthetic-retry'], provenance={})
                now[0] += 5
                self.assertEqual(b.remaining_seconds(), 7178)
                # Model an unfinalized attempt; reservation must not be refunded.
            with self.assertRaisesRegex(RuntimeError, 'exhausted'):
                with budget():
                    pass
            self.assertEqual(sum(a['charged_seconds'] for a in json.loads(path.read_text())['attempts']), 7200)

    def test_moe_total_and_no_stage_redistribution(self):
        stages = [f'expert-{i}' for i in range(4)]+['router']
        self.assertEqual(sum(module.allocation('moe-gs', 'selfcap-dance1', s) for s in stages), 7200)
        self.assertEqual(sum(7200 for _ in module.METHODS for _ in module.SCENES), 24*3600)
        with self.assertRaises(ValueError):
            module.allocation('moe-gs', 'selfcap-dance1', 'train')

    def test_clean_finish_refunds_unused_time_and_serializes_attempts(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'budget.json'
            now = [0.]
            def budget():
                return module.TrainingBudget(path, method='stg-full', scene='selfcap-dance1',
                                             clock=lambda: now[0])
            with budget() as b:
                with self.assertRaises(BlockingIOError):
                    with budget():
                        pass
                b.start(command=['synthetic'], provenance={})
                now[0] = 120
                b.finish('completed')
            with budget() as b:
                self.assertEqual(b.available, 7080)

    def test_overrun_is_visible_not_silently_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'budget.json'
            now = [0.]
            with module.TrainingBudget(path, method='atgs', scene='vru-basketball-dg',
                                       clock=lambda: now[0]) as b:
                b.start(command=['synthetic'], provenance={})
                now[0] = 7201
                with self.assertRaisesRegex(RuntimeError, 'exceeded'):
                    b.finish('deadline')
            self.assertEqual(json.loads(path.read_text())['attempts'][0]['overrun_seconds'], 1)
