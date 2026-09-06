import io
from pathlib import Path
import random
import sys
import unittest

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from training_rng import capture_rng, restore_rng


class TrainingRNGTests(unittest.TestCase):
    def setUp(self):
        self.previous = capture_rng(include_cuda=False)

    def tearDown(self):
        restore_rng(self.previous, include_cuda=False)

    def test_weights_only_roundtrip_reproduces_all_cpu_streams(self):
        random.seed(7)
        np.random.seed(8)
        torch.manual_seed(9)
        np.random.normal()  # Exercise NumPy's cached Gaussian state.
        state = capture_rng(include_cuda=False)
        stream = io.BytesIO()
        torch.save(state, stream)
        expected = ([random.random() for _ in range(5)], np.random.normal(size=5), torch.rand(5))
        stream.seek(0)
        restore_rng(torch.load(stream, weights_only=True), include_cuda=False)
        self.assertEqual(expected[0], [random.random() for _ in range(5)])
        np.testing.assert_array_equal(expected[1], np.random.normal(size=5))
        torch.testing.assert_close(expected[2], torch.rand(5), rtol=0, atol=0)

    def test_reject_saved_cuda_state_in_cpu_mode(self):
        state = capture_rng(include_cuda=False)
        state['torch_cuda'] = [torch.zeros(1, dtype=torch.uint8)]
        with self.assertRaisesRegex(ValueError, 'discard'):
            restore_rng(state, include_cuda=False)

    def test_invalid_schema_and_keys_rejected(self):
        with self.assertRaisesRegex(ValueError, 'schema'):
            restore_rng({}, include_cuda=False)
        state = capture_rng(include_cuda=False)
        state['numpy']['keys'][0] = -1
        with self.assertRaisesRegex(ValueError, 'keys'):
            restore_rng(state, include_cuda=False)
