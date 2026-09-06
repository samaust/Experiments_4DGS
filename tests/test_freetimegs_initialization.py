from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from freetimegs_source import load_initializer

CHECKOUT = Path(__file__).resolve().parents[1] / '.local/FreeTimeGsVanilla'
try:
    import sklearn
except ImportError:
    sklearn = None


@unittest.skipUnless(CHECKOUT.is_dir() and sklearn is not None,
                     'requires reproduction checkout and scikit-learn')
class NativeInitializationTests(unittest.TestCase):
    def test_native_parameter_groups_scales_colors_and_adam(self):
        initialize, digest = load_initializer(CHECKOUT)
        cfg = SimpleNamespace(init_scale=.03, init_opacity=.5, init_duration=.2,
            sh_degree=3, batch_size=1, position_lr=.00016, scales_lr=.005,
            quats_lr=.001, opacities_lr=.05, sh0_lr=.0025, shN_lr=.000125,
            times_lr=.001, durations_lr=.001, velocity_lr_start=.005)
        positions = torch.tensor([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.], [0., 0., 1.]])
        data = dict(positions=positions, velocities=torch.zeros((4, 3)),
                    colors=torch.full((4, 3), .5), times=torch.full((4, 1), .5),
                    durations=torch.full((4, 1), .1))
        torch.manual_seed(0)
        splats, optimizers = initialize(cfg, data, scene_scale=2., device='cpu')
        self.assertEqual(len(digest), 64)
        self.assertEqual(set(splats), {'means', 'scales', 'quats', 'opacities',
                                      'sh0', 'shN', 'times', 'durations', 'velocities'})
        self.assertEqual(set(splats), set(optimizers))
        self.assertEqual(splats['shN'].shape, (4, 15, 3))
        torch.testing.assert_close(splats['sh0'], torch.zeros((4, 1, 3)))
        torch.testing.assert_close(splats['durations'].exp(), torch.full((4, 1), .2))
        distances = torch.cdist(positions, positions).square()
        distances.fill_diagonal_(float('inf'))
        expected = distances.topk(3, largest=False).values.mean(1).sqrt() * .03
        torch.testing.assert_close(splats['scales'].exp(), expected[:, None].expand(4, 3))
        self.assertEqual(optimizers['means'].param_groups[0]['lr'], cfg.position_lr * 2.)
        sum(p.square().sum() for p in splats.values()).backward()
        for name, optimizer in optimizers.items():
            self.assertIs(type(optimizer), torch.optim.Adam)
            self.assertIs(optimizer.param_groups[0]['params'][0], splats[name])
            optimizer.step()
            self.assertEqual(optimizer.state[splats[name]]['step'].item(), 1)
            self.assertTrue(torch.isfinite(splats[name]).all())
