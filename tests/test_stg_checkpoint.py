"""CPU synthetic optimizer tests; no experiment training budget is consumed."""
from argparse import Namespace
import importlib.util
from pathlib import Path
import random
import tempfile
import unittest

import numpy as np
import torch

spec = importlib.util.spec_from_file_location('stg_checkpoint',
    Path(__file__).resolve().parents[1]/'scripts/stg_checkpoint.py')
checkpoint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checkpoint)


class Model:
    def __init__(self, full):
        self.names = checkpoint.PARAMETERS + (('_features_t',) if full else ())
        for name in self.names:
            setattr(self, name, torch.nn.Parameter(torch.randn(5, 3)))
        for name in checkpoint.BUFFERS:
            setattr(self, name, torch.rand(5, 1))
        self.rgbdecoder = torch.nn.Linear(3, 3) if full else None
        self.spatial_lr_scale = 2.0
        self.training_setup(Namespace(lr=0.003))

    def training_setup(self, args):
        groups = [{'params': [getattr(self, n)], 'name': n} for n in self.names]
        if self.rgbdecoder is not None:
            groups.append({'params': list(self.rgbdecoder.parameters()), 'name': 'decoder'})
        self.optimizer = torch.optim.Adam(groups, lr=args.lr)
        # Upstream resets these during setup; restoration must undo that.
        for name in checkpoint.BUFFERS:
            setattr(self, name, torch.zeros(5, 1))

    def step(self):
        value = sum((getattr(self, n)*torch.randn(5, 3)).square().sum() for n in self.names)
        if self.rgbdecoder is not None:
            value = value + self.rgbdecoder(torch.randn(5, 3)).square().sum()
        value.backward()
        self.optimizer.step()
        self.optimizer.zero_grad(set_to_none=True)
        return value.detach()


class CheckpointTests(unittest.TestCase):
    def test_next_step_exact_after_restore(self):
        for variant in ('lite', 'full'):
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as directory:
                model = Model(variant == 'full')
                model.step()
                model.optimizer.param_groups[0]['lr'] = np.float64(0.001)
                model.denom.fill_(7)
                path = Path(directory)/'state.pt'
                provenance = {'manifest_sha256': 'synthetic', 'source': 'test'}
                checkpoint.save_checkpoint(path, model, variant=variant,
                    training_args=Namespace(lr=0.003), iteration=1,
                    loop_state={'remaining_views': [2, 7]}, provenance=provenance)
                expected_random = (random.random(), np.random.random())
                expected_loss = model.step()
                restored = Model(variant == 'full')
                iteration, loop, _ = checkpoint.restore_checkpoint(path, restored,
                    variant=variant, provenance=provenance, device='cpu')
                self.assertEqual(iteration, 1)
                self.assertEqual(loop, {'remaining_views': [2, 7]})
                self.assertEqual(expected_random, (random.random(), np.random.random()))
                self.assertTrue(torch.equal(model.denom, restored.denom))
                self.assertTrue(torch.equal(expected_loss, restored.step()))
                for name in model.names:
                    self.assertTrue(torch.equal(getattr(model, name), getattr(restored, name)))
                if model.rgbdecoder is not None:
                    for a, b in zip(model.rgbdecoder.parameters(), restored.rgbdecoder.parameters()):
                        self.assertTrue(torch.equal(a, b))
                with self.assertRaisesRegex(ValueError, 'provenance mismatch'):
                    checkpoint.restore_checkpoint(path, restored, variant=variant,
                        provenance={}, device='cpu')
                state = torch.load(path, weights_only=True)
                del state['parameters']['_motion']
                torch.save(state, path)
                with self.assertRaisesRegex(ValueError, 'missing or unexpected'):
                    checkpoint.restore_checkpoint(path, restored, variant=variant,
                        provenance=provenance, device='cpu')

    def test_uncleared_gradients_rejected(self):
        model = Model(False)
        model._xyz.sum().backward()
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'cleared gradients'):
                checkpoint.save_checkpoint(Path(directory)/'state.pt', model, variant='lite',
                    training_args=Namespace(lr=.003), iteration=0, loop_state={}, provenance={})
