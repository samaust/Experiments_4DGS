#!/usr/bin/env python3
"""Synthetic ATGS integration gate; optional Adam steps are not scene training."""
import argparse
import json
import sys
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkout', type=Path, default=Path('.local/ATGS'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--native-checkpoint', type=Path,
                        help='new directory for an optional native save/reload probe')
    parser.add_argument('--restore-auxiliary', action='store_true',
                        help='also save/restore supplemental tensors and rebuild optimizers')
    parser.add_argument('--populate-optimizer-state', action='store_true',
                        help='take three synthetic Adam updates before checkpoint validation')
    args = parser.parse_args()
    if args.restore_auxiliary and args.native_checkpoint is None:
        parser.error('--restore-auxiliary requires --native-checkpoint')
    if args.populate_optimizer_state and not args.restore_auxiliary:
        parser.error('--populate-optimizer-state requires --restore-auxiliary')
    if args.output.exists():
        raise FileExistsError(args.output)
    if args.native_checkpoint is not None and args.native_checkpoint.exists():
        raise FileExistsError(args.native_checkpoint)
    import numpy as np
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable; GPU validation stopped, no CPU fallback')
    sys.path.insert(0, str(args.checkout.resolve()))
    from atgs_config import load_config
    from atgs_scene import make_camera
    from scene.gaussian_model import GaussianModel
    from utils.graphics_utils import BasicPointCloud
    from gaussian_renderer import prefilter_voxel, render

    merged, (dataset, hidden, opt, pipe), cfg = load_config(args.checkout)
    torch.manual_seed(0)
    np.random.seed(0)
    start = time.monotonic()
    model = GaussianModel(hidden, opt, dataset.feat_dim, 10, dataset.voxel_size,
                          dataset.update_depth, dataset.update_init_factor,
                          dataset.update_hierachy_factor, dataset.use_feat_bank,
                          dataset.appearance_dim, dataset.ratio, dataset.add_opacity_dist,
                          dataset.add_cov_dist, dataset.add_color_dist)
    xyz = np.random.uniform(-.3, .3, (64, 3)).astype(np.float32)
    xyz[:, 2] += 2.
    lifetimes = np.zeros((64, 60), dtype=bool)
    lifetimes[:, 0] = True  # Exercise upstream's always-active initial anchors.
    cloud = BasicPointCloud(xyz, np.full_like(xyz, .5), np.zeros_like(xyz),
                            None, lifetimes, None)
    model.create_from_pcd(cloud, 1., 1., [0, 60])
    model.training_setup(opt, None, '')
    calibration = dict(width=64, height=64, K=[[60, 0, 29], [0, 60, 30], [0, 0, 1]],
                       world_to_camera_R=np.eye(3).tolist(), world_to_camera_T=[0, 0, 0])
    records = []
    for step, timestamp in enumerate((.1, .5, .9), start=1):
        model.optimizer.zero_grad(set_to_none=True)
        model.dy_optimizer.zero_grad(set_to_none=True)
        camera = make_camera(calibration, timestamp, device='cuda')
        background = torch.zeros(3, device='cuda')
        visible = prefilter_voxel(camera, model, pipe, background)
        assert visible.any(), 'no visible anchors'
        output = render(camera, model, pipe, background, iteration=1,
                        retain_grad=True, visible_mask=visible)
        image = output['render']
        assert image.shape == (3, 64, 64) and torch.isfinite(image).all()
        loss = (image - .25).square().mean()
        loss.backward()
        gradients = [p.grad for optimizer in (model.optimizer, model.dy_optimizer)
                     for group in optimizer.param_groups for p in group['params'] if p.grad is not None]
        assert gradients and all(torch.isfinite(g).all() for g in gradients)
        active = model.dynamic_module.routing_encoder_id(timestamp)
        encoder_gradients = [p.grad for p in model.dynamic_module.enc_models[active].parameters()
                             if p.grad is not None]
        assert encoder_gradients and any(g.abs().sum() > 0 for g in encoder_gradients)
        model.mlp_color.eval()
        with torch.no_grad():
            inference = render(camera, model, pipe, background, iteration=1, visible_mask=visible)
        model.mlp_color.train()
        torch.testing.assert_close(inference['render'], image.detach(), rtol=0, atol=0)
        assert 'neural_opacity' not in inference
        records.append(dict(time=timestamp, encoder=active, loss=loss.item(),
                            visible_anchors=int(visible.sum()), gradient_tensors=len(gradients),
                            inference_max_abs_difference=(inference['render'] - image.detach()).abs().max().item()))
        if args.populate_optimizer_state:
            model.update_learning_rate(step, opt, timestamp)
            for optimizer in (model.optimizer, model.dy_optimizer):
                parameters = [p for group in optimizer.param_groups for p in group['params']]
                torch.nn.utils.clip_grad_norm_(parameters, opt.gradient_clip_norm, error_if_nonfinite=True)
                optimizer.step()
                assert all(torch.isfinite(p).all() for p in parameters)
    if args.populate_optimizer_state:
        assert model.optimizer.state and model.dy_optimizer.state
    reload_result = None
    if args.native_checkpoint is not None:
        from atgs_checkpoint import probe_native_reload
        def factory():
            return GaussianModel(hidden, opt, dataset.feat_dim, 10, dataset.voxel_size,
                                 dataset.update_depth, dataset.update_init_factor,
                                 dataset.update_hierachy_factor, dataset.use_feat_bank,
                                 dataset.appearance_dim, dataset.ratio, dataset.add_opacity_dist,
                                 dataset.add_cov_dist, dataset.add_color_dist)
        reload_result = probe_native_reload(model, factory, cloud, args.native_checkpoint,
                                            camera=camera, pipe=pipe, background=background,
                                            restore_auxiliary=args.restore_auxiliary, opt=opt)
    torch.cuda.synchronize()
    report = dict(status='passed', scope='synthetic full model integration; not scene training',
                  synthetic_optimizer_updates=3 if args.populate_optimizer_state else 0,
                  device=torch.cuda.get_device_name(), levels=cfg.levels,
                  feat_dim=dataset.feat_dim, voxel_resolution=model.voxel_grid_resolution,
                  records=records, wall_seconds=time.monotonic() - start,
                  native_reload=reload_result,
                  peak_allocated_bytes=torch.cuda.max_memory_allocated())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
