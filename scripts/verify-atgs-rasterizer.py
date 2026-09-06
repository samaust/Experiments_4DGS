#!/usr/bin/env python3
"""Synthetic recovered-rasterizer/KNN CUDA gate; not an ATGS training result."""
import argparse
import json
import subprocess
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    import torch

    if not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable; GPU validation stopped, no CPU fallback')
    from diff_gaussian_rasterization import GaussianRasterizationSettings, GaussianRasterizer
    from simple_knn._C import distCUDA2

    start = time.monotonic()
    torch.manual_seed(0)
    xyz = torch.tensor([[-.2, -.1, 2.], [.2, -.1, 2.2], [0., .2, 2.4], [.1, 0., 3.]], device='cuda', requires_grad=True)
    screen = torch.zeros_like(xyz, requires_grad=True)
    scale = torch.full_like(xyz, .1, requires_grad=True)
    rotation = torch.tensor([[1., 0., 0., 0.]] * 4, device='cuda', requires_grad=True)
    opacity = torch.full((4, 1), .5, device='cuda', requires_grad=True)
    color = torch.rand((4, 3), device='cuda', requires_grad=True)
    projection = torch.zeros((4, 4), device='cuda')
    projection[0, 0] = projection[1, 1] = 1.
    projection[2, 2] = 100. / 99.9
    projection[2, 3] = -10. / 99.9
    projection[3, 2] = 1.
    settings = GaussianRasterizationSettings(
        image_height=64, image_width=64, tanfovx=1., tanfovy=1.,
        bg=torch.zeros(3, device='cuda'), scale_modifier=1.,
        viewmatrix=torch.eye(4, device='cuda'), projmatrix=projection.T.contiguous(),
        sh_degree=0, campos=torch.zeros(3, device='cuda'), prefiltered=False, debug=False,
    )
    rasterizer = GaussianRasterizer(settings)
    image, radii = rasterizer(xyz, screen, opacity, colors_precomp=color, scales=scale, rotations=rotation)
    assert image.shape == (3, 64, 64) and torch.isfinite(image).all()
    assert (radii > 0).all() and image.max() > 0
    image.square().mean().backward()
    for parameter in (xyz, screen, scale, rotation, opacity, color):
        assert parameter.grad is not None and torch.isfinite(parameter.grad).all()
    assert color.grad.abs().sum() > 0 and xyz.grad.abs().sum() > 0
    filtered = rasterizer.visible_filter(xyz.detach(), scales=scale.detach(), rotations=rotation.detach())
    torch.testing.assert_close(filtered, radii)
    # This kernel returns mean squared distance to the three nearest neighbours.
    actual = distCUDA2(xyz.detach())
    distances = torch.cdist(xyz.detach(), xyz.detach()).square()
    distances.fill_diagonal_(float('inf'))
    expected = distances.topk(3, largest=False).values.mean(dim=1)
    torch.testing.assert_close(actual, expected, rtol=1e-5, atol=1e-6)
    torch.cuda.synchronize()
    root = Path(__file__).resolve().parents[1]
    revision = subprocess.check_output(['git', '-C', str(root / '.local/LocalDyGS'), 'rev-parse', 'HEAD'], text=True).strip()
    report = dict(status='passed', scope='synthetic rasterizer forward/backward, visibility and KNN only',
                  source_revision=revision, torch_version=torch.__version__, device=torch.cuda.get_device_name(),
                  radii=radii.tolist(), knn_max_abs_difference=(actual - expected).abs().max().item(),
                  wall_seconds=time.monotonic() - start)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
