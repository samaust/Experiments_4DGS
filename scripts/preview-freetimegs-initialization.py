#!/usr/bin/env python3
"""Render untrained sparse or dense initialization; not quantitative evaluation."""
import argparse
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from PIL import Image
import torch

from freetimegs_initialization import digest
from freetimegs_model import NativeFreeTimeModel
from freetimegs_scene import FreeTimeSelfCapScene


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--initialization', type=Path, required=True)
    parser.add_argument('--checkout', type=Path, default=Path('.local/FreeTimeGsVanilla'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('choose a new output directory')
    scene = FreeTimeSelfCapScene(args.manifest)
    evidence = json.loads((args.initialization / 'result.json').read_text())
    archive = args.initialization / 'initialization.npz'
    if (evidence.get('status') != 'prepared' or evidence.get('manifest_sha256') != scene.sha256
            or evidence.get('archive_sha256') != digest(archive)):
        raise ValueError('initialization provenance mismatch')
    with np.load(archive, allow_pickle=False) as arrays:
        data = {name: torch.from_numpy(arrays[name].copy()) for name in
                ('positions', 'colors', 'velocities', 'times', 'durations')}
    count = evidence['points']
    for name, tensor in data.items():
        width = 3 if name in ('positions', 'colors', 'velocities') else 1
        if tensor.shape != (count, width) or tensor.dtype != torch.float32 or not torch.isfinite(tensor).all():
            raise ValueError(f'invalid initialization tensor: {name}')
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable; no CPU fallback')
    from gsplat.strategy import DefaultStrategy
    import gsplat.csrc as native
    torch.manual_seed(0)
    centers = np.array([c['center'] for c in scene.cameras.values() if c['split'] == 'train'])
    extent = float(np.linalg.norm(centers - centers.mean(0), axis=1).max() * 1.1)
    # Construction-only settings: keyframe preset scale/opacity, no training loop.
    cfg = SimpleNamespace(init_scale=.03, init_opacity=.5,
        init_duration=10 * evidence['normalized_frame_interval'], sh_degree=3,
        batch_size=1, position_lr=.00016, scales_lr=.005, quats_lr=.001,
        opacities_lr=.05, sh0_lr=.0025, shN_lr=.000125, times_lr=.001,
        durations_lr=.005, velocity_lr_start=.005, use_velocity=True,
        antialiased=False, packed=True, near_plane=.01, far_plane=1e10,
        strategy=DefaultStrategy())
    model = NativeFreeTimeModel(args.checkout, cfg, data, scene_scale=extent, device='cuda')
    args.output.mkdir(parents=True)
    records = []
    with torch.no_grad():
        for frame in (4120, 4150, 4179):
            camera = scene.camera(('0015', frame), device='cuda')
            rgb, alpha, _ = model.render(camera, sh_degree=0)
            if rgb.shape != (1, camera.height, camera.width, 3) or not torch.isfinite(rgb).all():
                raise ValueError('invalid rendered initialization')
            path = args.output / f'{frame:06d}.png'
            pixels = (rgb[0].clamp(0, 1) * 255).round().byte().cpu().numpy()
            Image.fromarray(pixels).save(path)
            records.append(dict(frame_id=frame, time=camera.t, image_sha256=digest(path),
                                mean_alpha=alpha.mean().item(), width=camera.width, height=camera.height))
    torch.cuda.synchronize()
    report = dict(status='rendered', scope='untrained initialization coverage only', seed=0,
        manifest_sha256=scene.sha256, initialization_sha256=digest(archive),
        source_digests=model.source_digests, renderer_sha256=digest(native.__file__),
        points=count, device=torch.cuda.get_device_name(), records=records,
        peak_allocated_bytes=torch.cuda.max_memory_allocated(), scene_extent=extent,
        config={k: v for k, v in vars(cfg).items() if k != 'strategy'})
    (args.output / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
