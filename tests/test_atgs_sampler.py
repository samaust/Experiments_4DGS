import io
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from atgs_sampler import ManifestBalancedSampler


def scene():
    keys = [('0000', i) for i in range(5)]
    return SimpleNamespace(sha256='manifest', cameras={'0000': {'split': 'train'}},
        training_keys=lambda: keys,
        frames={k: {'normalized_time': t} for k, t in zip(keys, [.1, .2, .49, .51, .9])})


class ATGSSamplerTests(unittest.TestCase):
    def test_mid_batch_and_epoch_boundary_resume(self):
        for consumed in (0, 1, 5, 6, 7):
            a = ManifestBalancedSampler(scene(), 2, seed=17)
            for _ in range(consumed):
                next(a)
            state = a.state_dict()
            stream = io.BytesIO()
            torch.save(state, stream)
            expected = [next(a) for _ in range(30)]
            stream.seek(0)
            b = ManifestBalancedSampler(scene(), 2, seed=999)
            b.load_state_dict(torch.load(stream, weights_only=True))
            self.assertEqual(expected, [next(b) for _ in range(30)])

    def test_corrected_time_balance_and_global_rng_isolation(self):
        s = scene()
        rng = torch.get_rng_state().clone()
        sampler = ManifestBalancedSampler(s, 2)
        self.assertEqual(sampler.buckets, [[0, 1, 2], [3, 4]])
        for _ in range(10):
            batch = [next(sampler), next(sampler)]
            self.assertEqual({int(s.frames[k]['normalized_time'] * 2) for k in batch}, {0, 1})
        self.assertTrue(torch.equal(rng, torch.get_rng_state()))

    def test_bad_membership_and_saved_state(self):
        s = scene()
        s.cameras['0000']['split'] = 'test'
        with self.assertRaisesRegex(ValueError, 'held-out'):
            ManifestBalancedSampler(s, 2)
        with self.assertRaisesRegex(ValueError, 'empty encoder'):
            ManifestBalancedSampler(scene(), 20)
        sampler = ManifestBalancedSampler(scene(), 2)
        next(sampler)
        state = sampler.state_dict()
        state['cursor'] = 100
        with self.assertRaisesRegex(ValueError, 'cursor'):
            sampler.load_state_dict(state)
        state = sampler.state_dict()
        state['identity'] = 'different'
        with self.assertRaisesRegex(ValueError, 'identity'):
            sampler.load_state_dict(state)
        state = sampler.state_dict()
        state['order'][1] = state['order'][0]
        with self.assertRaisesRegex(ValueError, 'unbalanced'):
            sampler.load_state_dict(state)
