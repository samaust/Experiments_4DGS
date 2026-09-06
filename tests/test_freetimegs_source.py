from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from freetimegs_source import load_temporal_methods

CHECKOUT = Path(__file__).resolve().parents[1] / '.local/FreeTimeGsVanilla'


@unittest.skipUnless(CHECKOUT.is_dir(), 'FreeTimeGS reproduction checkout unavailable')
class FreeTimeSourceTests(unittest.TestCase):
    def setUp(self):
        self.methods, self.digest = load_temporal_methods(CHECKOUT)
        self.model = SimpleNamespace(cfg=SimpleNamespace(use_velocity=True), splats={
            'means': torch.tensor([[1., 2., 3.]], requires_grad=True),
            'velocities': torch.tensor([[2., 0., -2.]], requires_grad=True),
            'times': torch.tensor([[.5]], requires_grad=True),
            'durations': torch.tensor([[.1]]).log().requires_grad_(),
            'opacities': torch.tensor([0.], requires_grad=True),
        })

    def test_motion_and_temporal_opacity(self):
        self.assertEqual(len(self.digest), 64)
        position = self.methods['compute_positions_at_time'](self.model, .75)
        torch.testing.assert_close(position, torch.tensor([[1.5, 2., 2.5]]))
        at_center = self.methods['compute_temporal_opacity'](self.model, .5)
        torch.testing.assert_close(at_center, torch.ones(1))
        away = self.methods['compute_temporal_opacity'](self.model, .6)
        torch.testing.assert_close(away, torch.tensor([-.5]).exp())
        (position.sum() + away.sum()).backward()
        for name in ('means', 'velocities', 'times', 'durations'):
            self.assertTrue(torch.isfinite(self.model.splats[name].grad).all())
        self.model.cfg.use_velocity = False
        self.assertIs(self.methods['compute_positions_at_time'](self.model, .9),
                      self.model.splats['means'])

    def test_regularization_stops_temporal_gradient(self):
        temporal = self.methods['compute_temporal_opacity'](self.model, .6)
        regularization = self.methods['compute_4d_regularization'](self.model, temporal)
        torch.testing.assert_close(regularization, temporal.detach().mean() * .5)
        regularization.backward()
        self.assertGreater(self.model.splats['opacities'].grad.item(), 0)
        self.assertIsNone(self.model.splats['times'].grad)
        self.assertIsNone(self.model.splats['durations'].grad)
