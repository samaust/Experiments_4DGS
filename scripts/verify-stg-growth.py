#!/usr/bin/env python3
"""Exercise native EMS, splitting, pruning and resume on synthetic CUDA points.

This is not scene training and does not consume a contender's training budget.
Report failures before asserting so both representations retain diagnostic data.
"""
import argparse
import json
from pathlib import Path
import sys
import tempfile

import numpy as np
import torch
from stg_checkpoint import save_checkpoint, restore_checkpoint
from stg_scene import make_camera


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkout', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--require-valid', action='store_true')
    a = parser.parse_args()
    if a.output.exists():
        parser.error('choose a new report path')
    root = a.checkout.resolve()
    sys.path[:0] = [str(root), str(root/'thirdparty/gaussian_splatting')]
    from arguments import OptimizationParams
    from helper_train import getrenderpip, trbfunction
    from thirdparty.gaussian_splatting.scene.ourslite import GaussianModel as Lite
    from thirdparty.gaussian_splatting.scene.oursfull import GaussianModel as Full
    from utils.graphics_utils import BasicPointCloud
    opt_parser = argparse.ArgumentParser()
    group = OptimizationParams(opt_parser)
    opt = group.extract(opt_parser.parse_args([]))
    results = {}
    for variant, cls in [('lite', Lite), ('full', Full)]:
        torch.manual_seed(0)
        np.random.seed(0)
        full = variant == 'full'
        camera = make_camera(dict(width=80, height=60,
            K=[[70, 0, 33], [0, 65, 30], [0, 0, 1]],
            world_to_camera_R=np.eye(3), world_to_camera_T=np.zeros(3)),
            .5, device='cuda', full=full)
        points = np.random.uniform([-.5, -.4, 2], [.5, .4, 3], (32, 3)).astype(np.float32)
        model = cls(3, 'sandwich') if full else cls(3)
        model.trbfslinit = 0.
        model.create_from_pcd(BasicPointCloud(points, np.full_like(points, .5),
            np.zeros_like(points), np.full((32, 1), .3, dtype=np.float32)), 1.)
        if full:
            model.rgbdecoder.cuda()
        model.training_setup(opt)
        # Populate Adam's state before changing tensor sizes.
        sum(p.square().sum() for g in model.optimizer.param_groups for p in g['params']).backward()
        model.optimizer.step()
        model.optimizer.zero_grad(set_to_none=True)
        render, settings, rasterizer = getrenderpip('train_ours_'+variant)
        background = torch.zeros(9 if full else 3, device='cuda')
        def forward(target):
            return render(camera, target, None, background, basicfunction=trbfunction,
                          GRsetting=settings, GRzer=rasterizer)['render']
        with torch.no_grad():
            original_count = len(model._xyz)
            added = model.addgaussians(torch.tensor([[20, 20], [30, 30], [40, 40]], device='cuda'),
                camera, torch.full((1, 60, 80), 2.5, device='cuda'),
                torch.rand((3, 60, 80), device='cuda'), numperay=2, ratioend=1.1,
                depthmax=2.5, shuffle=False)
            quaternion_norms = model._rotation[-added:].norm(dim=1)
            valid_quaternions = bool(torch.allclose(quaternion_norms, torch.ones_like(quaternion_norms)))
            # Exercise anisotropic rotation and splitting, not only spherical splats.
            model._scaling[-added:] = torch.tensor([-3., -4., -5.], device='cuda')
        pixels = forward(model)
        pixels.square().mean().backward()
        pre_split_finite = bool(torch.isfinite(pixels).all() and torch.isfinite(model._rotation.grad).all())
        model.optimizer.zero_grad(set_to_none=True)
        with torch.no_grad():
            gradients = torch.zeros((len(model._xyz), 1), device='cuda')
            gradients[-added:] = 1
            model.densify_and_splitv2(gradients, .5, 1., N=2)
            split_count = len(model._xyz)
            finite_xyz = bool(torch.isfinite(model._xyz).all())
            prune = torch.zeros(split_count, dtype=torch.bool, device='cuda')
            prune[0] = True
            model.prune_points(prune)
        optimizer_shapes = all(
            state['exp_avg'].shape == parameter.shape and state['exp_avg_sq'].shape == parameter.shape
            for parameter, state in model.optimizer.state.items())
        record = dict(original_points=original_count, ems_added=added,
            ems_unit_quaternions=valid_quaternions, pre_split_finite=pre_split_finite,
            after_split_points=split_count, after_prune_points=len(model._xyz),
            finite_split_positions=finite_xyz, optimizer_shapes_match=optimizer_shapes)
        if finite_xyz and valid_quaternions:
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory)/'checkpoint.pt'
                save_checkpoint(path, model, variant=variant, training_args=opt, iteration=1,
                                loop_state={'growth_test': True}, provenance={'synthetic': True})
                restored = cls(3, 'sandwich') if full else cls(3)
                restore_checkpoint(path, restored, variant=variant,
                                   provenance={'synthetic': True}, device='cuda')
                with torch.no_grad():
                    first, second = forward(model), forward(restored)
                    record['reload_pixel_max_difference'] = float((first-second).abs().max())
                output = forward(restored)
                output.square().mean().backward()
                record['restored_backward_finite'] = all(
                    p.grad is not None and bool(torch.isfinite(p.grad).all())
                    for g in restored.optimizer.param_groups for p in g['params'])
                del restored, output, first, second
        record['passed'] = (valid_quaternions and finite_xyz and optimizer_shapes and
                            record.get('restored_backward_finite', False) and
                            record.get('reload_pixel_max_difference') == 0)
        results[variant] = record
        del model, camera, pixels
        torch.cuda.empty_cache()
    report = dict(gpu=torch.cuda.get_device_name(), results=results)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    if a.require_valid and not all(r['passed'] for r in results.values()):
        raise SystemExit('growth validation failed; see report')


if __name__ == '__main__':
    main()
