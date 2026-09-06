from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from atgs_update import load_update_helpers

CHECKOUT = Path(__file__).resolve().parents[1] / '.local/ATGS'


@unittest.skipUnless((CHECKOUT / 'train_long.py').is_file(), 'ATGS checkout unavailable')
class ATGSUpdateTests(unittest.TestCase):
    def test_native_averaging_warmup_and_gradient_clear(self):
        helpers, digest = load_update_helpers(CHECKOUT)
        self.assertEqual(len(digest), 64)
        static = torch.nn.Parameter(torch.tensor([1.]))
        dynamic = torch.nn.Module()
        dynamic.enc_models = torch.nn.ModuleList([torch.nn.Linear(1, 1, bias=False)])
        parameter = next(dynamic.parameters())
        initial = parameter.detach().clone()
        static.grad = torch.tensor([6.])
        parameter.grad = torch.tensor([[8.]])
        model = SimpleNamespace(optimizer=torch.optim.SGD([static], lr=.1),
                                dy_optimizer=torch.optim.SGD(dynamic.parameters(), lr=.2),
                                dynamic_module=dynamic)
        opt = SimpleNamespace(gradient_clip_norm=0., lr_warmup_updates=10, lr_warmup_start_factor=.1)
        counter = {'count': 0, 'iteration': 3}
        _, factor = helpers['step_accumulated_gradients'](model, opt, 3, {0: 2}, counter)
        self.assertAlmostEqual(factor, .19)
        torch.testing.assert_close(static, torch.tensor([1 - .1 * 2 * .19]))
        torch.testing.assert_close(parameter, initial - .2 * 4 * .19)
        self.assertEqual(counter['count'], 1)
        self.assertEqual(model.optimizer.param_groups[0]['lr'], .1)
        self.assertEqual(model.dy_optimizer.param_groups[0]['lr'], .2)
        self.assertIsNone(static.grad)
        self.assertIsNone(parameter.grad)
