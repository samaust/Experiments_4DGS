#!/usr/bin/env python3
"""Verify native STG optimizer resume on synthetic CUDA tensors, not scene training."""
import argparse
import json
from pathlib import Path
import sys
import tempfile

import torch
from stg_checkpoint import save_checkpoint, restore_checkpoint


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkout', type=Path, required=True)
    args = parser.parse_args()
    root = args.checkout.resolve()
    sys.path[:0] = [str(root), str(root/'thirdparty/gaussian_splatting')]
    from arguments import OptimizationParams
    from thirdparty.gaussian_splatting.scene.ourslite import GaussianModel as Lite
    from thirdparty.gaussian_splatting.scene.oursfull import GaussianModel as Full
    options_parser = argparse.ArgumentParser()
    options_group = OptimizationParams(options_parser)
    options = options_group.extract(options_parser.parse_args([]))
    results = {}
    for variant, cls in [('lite', Lite), ('full', Full)]:
        model = cls(3, 'sandwich') if variant == 'full' else cls(3)
        shapes = dict(_xyz=3, _features_dc=6 if variant == 'full' else 3,
                      _scaling=3, _rotation=4, _opacity=1, _motion=9,
                      _omega=4, _trbf_center=1, _trbf_scale=1)
        if variant == 'full':
            shapes['_features_t'] = 3
            model.rgbdecoder.cuda()
        for name, width in shapes.items():
            setattr(model, name, torch.nn.Parameter(torch.randn(8, width, device='cuda')))
        model.spatial_lr_scale = 1.0
        model.max_radii2D = torch.rand(8, device='cuda')
        model.training_setup(options)

        def step(target):
            loss = sum((p * torch.randn_like(p)).square().sum()
                       for group in target.optimizer.param_groups for p in group['params'])
            loss.backward()
            target.optimizer.step()
            target.optimizer.zero_grad(set_to_none=True)
            return loss.detach().clone()

        step(model)
        model.update_learning_rate(1)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'state.pt'
            save_checkpoint(path, model, variant=variant, training_args=options,
                            iteration=1, loop_state={}, provenance={'test': 'synthetic-native'})
            expected_loss = step(model)
            restored = cls(3, 'sandwich') if variant == 'full' else cls(3)
            restore_checkpoint(path, restored, variant=variant,
                               provenance={'test': 'synthetic-native'}, device='cuda')
            actual_loss = step(restored)
            equal = torch.equal(expected_loss, actual_loss) and all(
                torch.equal(a, b)
                for ga, gb in zip(model.optimizer.param_groups, restored.optimizer.param_groups)
                for a, b in zip(ga['params'], gb['params']))
            assert equal, f'{variant}: next optimization step differs'
            results[variant] = dict(next_step_exact=True, checkpoint_bytes=path.stat().st_size)
    print(json.dumps(dict(gpu=torch.cuda.get_device_name(), results=results,
                         scope='synthetic native optimizer; not rasterizer/backprop validation'), indent=2))


if __name__ == '__main__':
    main()
