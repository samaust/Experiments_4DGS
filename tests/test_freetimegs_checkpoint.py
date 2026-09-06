from dataclasses import dataclass
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from freetimegs_checkpoint import PARAMETERS, restore_checkpoint, save_checkpoint


@dataclass
class Config:
    max_steps: int = 70000
    sh_degree: int = 3


def model():
    shapes = dict(means=(4, 3), scales=(4, 3), quats=(4, 4), opacities=(4,),
                  sh0=(4, 1, 3), shN=(4, 15, 3), times=(4, 1), durations=(4, 1), velocities=(4, 3))
    splats = torch.nn.ParameterDict({name: torch.nn.Parameter(torch.ones(shapes[name]))
                                     for name in sorted(PARAMETERS)})
    optimizers = {name: torch.optim.Adam([value], lr=.01) for name, value in splats.items()}
    scheduler = torch.optim.lr_scheduler.ExponentialLR(optimizers['means'], gamma=.99)
    return SimpleNamespace(splats=splats, optimizers=optimizers, schedulers=[scheduler],
        cfg=Config(), device='cpu', grad_accum=torch.arange(4).float(), grad_count=7,
        strategy_state={'grad2d': torch.ones(4), 'scene_scale': 1.}, source_digests={'test': 'pin'})


def step(value):
    loss = sum((parameter * torch.rand_like(parameter)).sum() for parameter in value.splats.values())
    loss.backward()
    for optimizer in value.optimizers.values():
        optimizer.step()
        optimizer.zero_grad(set_to_none=True)
    value.schedulers[0].step()


class FreeTimeCheckpointTests(unittest.TestCase):
    def test_exact_next_update_and_relocation_state(self):
        original = model()
        step(original)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'checkpoint.pt'
            save_checkpoint(path, original, iteration=1, loop_state={'cursor': 3}, provenance={'manifest': 'a'})
            step(original)
            restored = model()
            iteration, loop = restore_checkpoint(path, restored, provenance={'manifest': 'a'})
            self.assertEqual((iteration, loop), (1, {'cursor': 3}))
            step(restored)
            for name in PARAMETERS:
                torch.testing.assert_close(original.splats[name], restored.splats[name], rtol=0, atol=0)
                self.assertEqual(original.optimizers[name].param_groups[0]['lr'],
                                 restored.optimizers[name].param_groups[0]['lr'])
            torch.testing.assert_close(restored.grad_accum, original.grad_accum)
            self.assertEqual(restored.grad_count, 7)
            torch.testing.assert_close(restored.strategy_state['grad2d'], torch.ones(4))

    def test_unfinished_update_and_wrong_provenance_rejected(self):
        value = model()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'checkpoint.pt'
            value.splats['means'].sum().backward()
            with self.assertRaisesRegex(ValueError, 'gradient clearing'):
                save_checkpoint(path, value, iteration=0, loop_state={}, provenance={})
            value.optimizers['means'].zero_grad(set_to_none=True)
            save_checkpoint(path, value, iteration=0, loop_state={}, provenance={})
            with self.assertRaisesRegex(ValueError, 'provenance'):
                restore_checkpoint(path, model(), provenance={'changed': True})
            with self.assertRaises(FileExistsError):
                save_checkpoint(path, value, iteration=0, loop_state={}, provenance={})
