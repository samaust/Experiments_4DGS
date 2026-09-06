#!/usr/bin/env python3
"""Check ATGS imports and its scatter-max CUDA dependency, without training."""
import argparse
import hashlib
import importlib
import json
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkout', type=Path, default=Path('.local/ATGS'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    checkout = args.checkout.resolve()
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable; GPU validation stopped, no CPU fallback')
    import torch_scatter
    assert torch_scatter.__version__ == '2.1.2'
    # ATGS expands group indices along the feature dimension and uses values.
    # Include negative features, repeated groups, and an empty output group.
    src = torch.tensor([[-2., 1.], [-1., 3.], [-4., -2.], [5., 0.]],
                       device='cuda', requires_grad=True)
    groups = torch.tensor([0, 0, 2, 2], device='cuda')
    index = groups[:, None].expand_as(src)
    values, argmax = torch_scatter.scatter_max(src, index, dim=0, dim_size=3)
    expected = torch.tensor([[-1., 3.], [0., 0.], [5., 0.]], device='cuda')
    torch.testing.assert_close(values, expected, rtol=0, atol=0)
    values.sum().backward()
    expected_gradient = torch.tensor([[0., 0.], [1., 1.], [0., 0.], [1., 1.]], device='cuda')
    torch.testing.assert_close(src.grad, expected_gradient, rtol=0, atol=0)
    torch.cuda.synchronize()

    sys.path.insert(0, str(checkout))
    # train_long constructs LPIPS-VGG at import time and may download weights.
    # Its execution/metric lifecycle is a separate adapter gate.
    names = ('scene.gaussian_model', 'gaussian_renderer', 'render')
    modules = {}
    for name in names:
        module = importlib.import_module(name)
        path = Path(module.__file__).resolve()
        if not path.is_relative_to(checkout):
            raise RuntimeError(f'{name} resolved outside checkout: {path}')
        modules[name] = dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    from arguments.atgs_cfg import cfg
    assert cfg.hash and cfg.primitive_type == '3dgs'
    report = dict(status='passed', scope='ATGS module imports and synthetic scatter-max only',
                  device=torch.cuda.get_device_name(), torch_version=torch.__version__,
                  scatter_version=torch_scatter.__version__, values=values.tolist(), argmax=argmax.tolist(),
                  checkout_revision=subprocess.check_output(['git', '-C', str(checkout), 'rev-parse', 'HEAD'], text=True).strip(),
                  modules=modules)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
