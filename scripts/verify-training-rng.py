#!/usr/bin/env python3
"""Validate serialized Python/NumPy/Torch CPU and CUDA RNG continuation."""
import argparse
import io
import json
from pathlib import Path
import random

import numpy as np
import torch

from training_rng import capture_rng, restore_rng


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable; RNG validation stopped, no CPU fallback')
    random.seed(0)
    np.random.seed(0)
    torch.manual_seed(0)
    torch.cuda.manual_seed_all(0)
    np.random.normal()  # Include a cached Gaussian in the checkpoint.
    state = capture_rng(include_cuda=True)
    stream = io.BytesIO()
    torch.save(state, stream)

    def draw():
        return dict(python=[random.random() for _ in range(32)], numpy=np.random.normal(size=32),
                    cpu=torch.rand(32), cuda=[torch.rand(32, device=f'cuda:{i}')
                                             for i in range(torch.cuda.device_count())])

    expected = draw()
    draw()  # Advance every stream beyond the expected sample.
    stream.seek(0)
    restore_rng(torch.load(stream, weights_only=True), include_cuda=True)
    actual = draw()
    assert expected['python'] == actual['python']
    np.testing.assert_array_equal(expected['numpy'], actual['numpy'])
    torch.testing.assert_close(expected['cpu'], actual['cpu'], rtol=0, atol=0)
    for a, b in zip(expected['cuda'], actual['cuda']):
        torch.testing.assert_close(a, b, rtol=0, atol=0)
    report = dict(status='passed', exact=True, scope='serialized RNG continuation only; no training loop',
                  devices=[torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())],
                  streams=['python', 'numpy_with_cached_gaussian', 'torch_cpu', 'all_visible_torch_cuda'],
                  torch_version=torch.__version__, numpy_version=np.__version__)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as output:
        json.dump(report, output, indent=2)
        output.write('\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
