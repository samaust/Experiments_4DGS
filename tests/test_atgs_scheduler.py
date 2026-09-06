"""CPU checks against the optional pinned ATGS checkout's patched scheduler."""
import ast
import io
from pathlib import Path
import unittest

import numpy as np
import torch


SOURCE = Path(__file__).resolve().parents[1] / '.local/ATGS/utils/general_utils.py'


@unittest.skipUnless(SOURCE.is_file(), 'pinned ATGS checkout not available')
class ATGSSchedulerTests(unittest.TestCase):
    def scheduler(self, original=False):
        text = SOURCE.read_text()
        if original:
            text = text.replace('return float(delay_rate * log_lerp)', 'return delay_rate * log_lerp')
        function = next(n for n in ast.parse(text).body
                        if isinstance(n, ast.FunctionDef) and n.name == 'get_expon_lr_func')
        namespace = {'np': np}
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(SOURCE), 'exec'), namespace)
        return namespace['get_expon_lr_func']

    def test_values_unchanged_and_builtin_float(self):
        for delay in (0, 100):
            options = dict(lr_init=.0002, lr_final=.000002, lr_delay_steps=delay,
                           lr_delay_mult=.01, max_steps=200000)
            patched, original = self.scheduler()(**options), self.scheduler(True)(**options)
            for step in (-1, 0, 1, 99, 100, 5000, 200000, 250000):
                self.assertIs(type(patched(step)), float)
                self.assertEqual(patched(step), original(step))

    def test_optimizer_checkpoint_weights_only_roundtrip(self):
        parameter = torch.nn.Parameter(torch.ones(2))
        optimizer = torch.optim.Adam([parameter], lr=self.scheduler()(.01, .001)(1))
        parameter.sum().backward()
        optimizer.step()
        stream = io.BytesIO()
        torch.save(optimizer.state_dict(), stream)
        stream.seek(0)
        loaded = torch.load(stream, weights_only=True)
        torch.testing.assert_close(loaded['state'][0]['exp_avg'], optimizer.state[parameter]['exp_avg'])
        self.assertIs(type(loaded['param_groups'][0]['lr']), float)
