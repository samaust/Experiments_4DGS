import copy
import io
from pathlib import Path
import random
import sys
from types import SimpleNamespace
import unittest

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from atgs_loop_state import capture_loop_state, restore_loop_state
from atgs_sampler import ManifestBalancedSampler
from training_rng import capture_rng, restore_rng


def make():
    a, b = torch.nn.Parameter(torch.tensor([.2])), torch.nn.Parameter(torch.tensor([.3]))
    model = SimpleNamespace(optimizer=torch.optim.Adam([a], lr=.01),
                            dy_optimizer=torch.optim.Adam([b], lr=.02))
    keys = [('train', 0), ('train', 1)]
    scene = SimpleNamespace(sha256='fixture', training_keys=lambda: keys,
                            cameras={'train': {'split': 'train'}},
                            frames={keys[0]: {'normalized_time': .1}, keys[1]: {'normalized_time': .9}})
    return model, ManifestBalancedSampler(scene, 2), a, b


class LoopStateTests(unittest.TestCase):
    def setUp(self):
        self.rng = capture_rng(include_cuda=False)

    def tearDown(self):
        restore_rng(self.rng, include_cuda=False)

    def test_partial_accumulation_resumes_next_update_exactly(self):
        model, sampler, a, b = make()
        first = next(sampler)
        (a + b).square().sum().backward()
        loop = dict(iteration=1, micro_steps=1, encoder_visits={first[1]: 1},
                    update_count=0, last_update_iteration=0, ema_loss=.25)
        state = capture_loop_state(model, sampler, loop, include_cuda=False)
        stream = io.BytesIO()
        torch.save(state, stream)

        def finish(m, s, x, y):
            key = next(s)
            target = random.random() + float(np.random.normal()) + torch.rand(1)
            (x + y - target).square().sum().backward()
            for optimizer in (m.optimizer, m.dy_optimizer):
                for group in optimizer.param_groups:
                    for p in group['params']:
                        p.grad.div_(2)
                optimizer.step()
            return key, target

        expected_key, expected_target = finish(model, sampler, a, b)
        restored, rs, ra, rb = make()
        stream.seek(0)
        loaded = torch.load(stream, weights_only=True)
        self.assertEqual(restore_loop_state(restored, rs, loaded, include_cuda=False), loop)
        key, target = finish(restored, rs, ra, rb)
        self.assertEqual(expected_key, key)
        torch.testing.assert_close(expected_target, target, rtol=0, atol=0)
        torch.testing.assert_close(a, ra, rtol=0, atol=0)
        torch.testing.assert_close(b, rb, rtol=0, atol=0)

    def test_bad_counts_topology_and_boundary_gradients(self):
        model, sampler, a, b = make()
        loop = dict(iteration=0, micro_steps=0, encoder_visits={}, update_count=0,
                    last_update_iteration=0, ema_loss=0.)
        state = capture_loop_state(model, sampler, loop, include_cuda=False)
        changed = copy.deepcopy(state)
        changed['loop']['encoder_visits'] = {0: 1}
        with self.assertRaisesRegex(ValueError, 'sum'):
            restore_loop_state(model, sampler, changed, include_cuda=False)
        changed = copy.deepcopy(state)
        next(iter(changed['parameters'].values()))['shape'] = [99]
        with self.assertRaisesRegex(ValueError, 'topology'):
            restore_loop_state(model, sampler, changed, include_cuda=False)
        a.sum().backward()
        with self.assertRaisesRegex(ValueError, 'cleared'):
            capture_loop_state(model, sampler, loop, include_cuda=False)
