#!/usr/bin/env python3
"""Synthetic gsplat/fused-SSIM CUDA gate, not a FreeTimeGS scene result."""
import argparse
import hashlib
import json
import time
from pathlib import Path
from types import SimpleNamespace


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable; GPU validation stopped, no CPU fallback')
    import gsplat.csrc as native
    import fused_ssim_cuda as ssim_native
    from gsplat.rendering import rasterization
    from gsplat.optimizers import SelectiveAdam
    from fused_ssim import fused_ssim

    start = time.monotonic()
    torch.manual_seed(0)
    means = torch.tensor([[-.2, -.1, 2.], [.2, -.1, 2.2], [0., .2, 2.4]],
                         device='cuda', requires_grad=True)
    quats = torch.tensor([[1., 0., 0., 0.]] * 3, device='cuda', requires_grad=True)
    scales = torch.full((3, 3), .15, device='cuda', requires_grad=True)
    opacities = torch.full((3,), .7, device='cuda', requires_grad=True)
    colors = torch.rand((3, 3), device='cuda', requires_grad=True)
    camera = torch.eye(4, device='cuda')[None]
    intrinsic = torch.tensor([[[50., 0., 32.], [0., 50., 32.], [0., 0., 1.]]], device='cuda')
    results = []
    for packed in (False, True):
        image, alpha, _ = rasterization(
            means=means, quats=quats, scales=scales, opacities=opacities,
            colors=colors, viewmats=camera, Ks=intrinsic, width=64, height=64,
            packed=packed, sh_degree=None, rasterize_mode='classic')
        assert image.shape == (1, 64, 64, 3) and alpha.shape == (1, 64, 64, 1)
        assert torch.isfinite(image).all() and image.max() > 0
        image.square().mean().backward()
        for parameter in (means, quats, scales, opacities, colors):
            assert parameter.grad is not None and torch.isfinite(parameter.grad).all()
        assert means.grad.abs().sum() > 0 and colors.grad.abs().sum() > 0
        results.append(image.detach())
        for parameter in (means, quats, scales, opacities, colors):
            parameter.grad = None
    torch.testing.assert_close(results[0], results[1], rtol=1e-5, atol=1e-6)

    target = torch.rand((1, 3, 64, 64), device='cuda')
    identical = fused_ssim(target, target, train=False)
    torch.testing.assert_close(identical, torch.ones_like(identical), rtol=1e-5, atol=1e-5)
    perturbed = (target * .8).detach().requires_grad_()
    score = fused_ssim(perturbed, target)
    assert torch.isfinite(score) and score < identical
    (1. - score).backward()
    assert torch.isfinite(perturbed.grad).all() and perturbed.grad.abs().sum() > 0

    parameter = torch.nn.Parameter(torch.ones((3, 3), device='cuda'))
    optimizer = SelectiveAdam([{'params': [parameter], 'lr': .01}], eps=1e-15, betas=(.9, .999))
    parameter.square().sum().backward()
    optimizer.step(visibility=torch.tensor([True, False, True], device='cuda'))
    assert (parameter[[0, 2]] < 1).all() and (parameter[1] == 1).all()

    from freetimegs_model import NativeFreeTimeModel
    from gsplat.strategy import DefaultStrategy
    cfg = SimpleNamespace(init_scale=.3, init_opacity=.5, init_duration=.2,
        sh_degree=3, batch_size=1, position_lr=.00016, scales_lr=.005,
        quats_lr=.001, opacities_lr=.05, sh0_lr=.0025, shN_lr=.000125,
        times_lr=.001, durations_lr=.005, velocity_lr_start=.005,
        use_velocity=True, antialiased=False, packed=True, near_plane=.01,
        far_plane=1e10, strategy=DefaultStrategy())
    init_data = dict(positions=torch.tensor([[-.2, -.1, 2.], [.2, -.1, 2.2],
                                            [0., .2, 2.4], [.1, .1, 2.8]]),
        colors=torch.rand((4, 3)), times=torch.full((4, 1), .5),
        durations=torch.full((4, 1), .2), velocities=torch.tensor([[.3, 0., 0.]] * 4))
    model = NativeFreeTimeModel(Path(__file__).resolve().parents[1] / '.local/FreeTimeGsVanilla',
                               cfg, init_data, scene_scale=1., device='cuda')
    model_camera = SimpleNamespace(camtoworlds=camera, Ks=intrinsic,
                                   width=64, height=64, t=.4)
    temporal_images = []
    for timestamp in (.4, .6):
        model_camera.t = timestamp
        rendered, _, info = model.render(model_camera, sh_degree=3)
        assert rendered.shape == (1, 64, 64, 3) and torch.isfinite(rendered).all()
        temporal_images.append(rendered.detach())
        loss = rendered.square().mean() + .001 * model.compute_4d_regularization(info['temporal_opacity'])
        loss.backward()
    assert not torch.equal(*temporal_images)
    for name, optimizer in model.optimizers.items():
        gradient = model.splats[name].grad
        assert gradient is not None and torch.isfinite(gradient).all(), name
        optimizer.step()
        optimizer.zero_grad(set_to_none=True)
    torch.cuda.synchronize()

    report = dict(status='passed', scope='synthetic native kernels only; no scene training',
                  torch_version=torch.__version__, device=torch.cuda.get_device_name(),
                  packed_max_abs_difference=(results[0] - results[1]).abs().max().item(),
                  ssim_identical=identical.item(), ssim_perturbed=score.item(),
                  native_model=dict(parameter_groups=sorted(model.splats),
                                    source_digests=model.source_digests,
                                    diagnostic_init_scale=cfg.init_scale,
                                    temporal_images_differ=True,
                                    optimizer_steps=1),
                  wall_seconds=time.monotonic() - start,
                  native_sha256={name: hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
                                 for name, module in [('gsplat', native), ('fused_ssim', ssim_native)]})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
