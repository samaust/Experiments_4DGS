import copy
from pathlib import Path
import runpy
import unittest


compare = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'scripts/verify-atgs-accumulation.py'))['compare_continuation']


class ContinuationTests(unittest.TestCase):
    def test_json_keys_and_loss_drift(self):
        reference = dict(records=[dict(key=['synthetic', 0], target=.25, loss=.5)],
                         warmup=.1, loop=dict(iteration=6, micro_steps=0, encoder_visits={},
                                             update_count=4, last_update_iteration=6))
        resumed = copy.deepcopy(reference)
        resumed['records'][0].update(key=('synthetic', 0), loss=.625)
        self.assertEqual(compare(reference, resumed), [.125])

    def test_reject_changed_sequence_or_counters(self):
        reference = dict(records=[dict(key=['synthetic', 0], target=.25, loss=.5)],
                         warmup=.1, loop=dict(iteration=6, micro_steps=0, encoder_visits={},
                                             update_count=4, last_update_iteration=6))
        for field in ('key', 'target'):
            resumed = copy.deepcopy(reference)
            resumed['records'][0][field] = None
            with self.assertRaisesRegex(ValueError, 'sequence mismatch'):
                compare(reference, resumed)
        resumed = copy.deepcopy(reference)
        resumed['loop']['update_count'] = 5
        with self.assertRaisesRegex(ValueError, 'loop update_count'):
            compare(reference, resumed)
