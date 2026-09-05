#!/usr/bin/env python3
"""Qualitative STG lite preview using released cameras and the native renderer.

No dataset, COLMAP, training, or evaluation metrics are involved. Timestamps
are normalized model time, not recovered physical capture timestamps.
"""
import argparse
import json
import math
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkout', type=Path, required=True)
    parser.add_argument('--ply', type=Path, required=True)
    parser.add_argument('--cameras', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--camera-index', type=int, default=0)
    parser.add_argument('--resolution', type=int, default=2)
    parser.add_argument('--times', type=float, nargs='+', default=[0, 0.5, 0.98])
    args = parser.parse_args()
    if args.resolution < 1 or any(not 0 <= t <= 1 for t in args.times):
        parser.error('resolution must be positive and times must be in [0, 1]')
    cameras = json.loads(args.cameras.read_text())
    if not 0 <= args.camera_index < len(cameras):
        parser.error('camera index is out of range')
    if args.output.exists():
        parser.error('choose a new output directory to preserve previous runs')
    checkout = args.checkout.resolve()
    sys.path[:0] = [str(checkout), str(checkout / 'thirdparty/gaussian_splatting')]
    import numpy as np
    import torch
    from torchvision.utils import save_image
    from helper_train import getrenderpip
    from thirdparty.gaussian_splatting.scene.ourslite import GaussianModel
    from thirdparty.gaussian_splatting.scene.cameras import Camera

    camera = cameras[args.camera_index]
    rotation = np.asarray(camera['rotation'])
    translation = -rotation.T @ np.asarray(camera['position'])
    width, height = (round(camera[key] / args.resolution) for key in ('width', 'height'))
    view = Camera(colmap_id=args.camera_index, R=rotation, T=translation,
                  FoVx=2 * math.atan(camera['width'] / (2 * camera['fx'])),
                  FoVy=2 * math.atan(camera['height'] / (2 * camera['fy'])),
                  image=(width, height), gt_alpha_mask=None,
                  image_name=camera['img_name'], uid=args.camera_index)
    render, settings, rasterizer = getrenderpip('test_ours_lite')
    args.output.mkdir(parents=True)
    with torch.no_grad():
        model = GaussianModel(3)
        model.load_ply(str(args.ply.resolve()))
        background = torch.zeros(3, device='cuda')
        records = []
        for index, timestamp in enumerate(args.times):
            view.timestamp = timestamp
            result = render(view, model, None, background, GRsetting=settings, GRzer=rasterizer)
            pixels = result['render']
            if not torch.isfinite(pixels).all() or pixels.std() == 0:
                raise RuntimeError('renderer returned nonfinite or constant pixels')
            save_image(pixels.clamp(0, 1), args.output / f'{index:05d}.png')
            records.append({'normalized_time': timestamp, 'finite': True})
        report = {'renderer': 'upstream test_ours_lite', 'gpu': torch.cuda.get_device_name(),
                  'torch': torch.__version__, 'camera': camera, 'resolution': [width, height],
                  'ply': str(args.ply.resolve()), 'frames': records,
                  'note': 'Qualitative preview; no held-out metrics or throughput benchmark.'}
        (args.output / 'preview.json').write_text(json.dumps(report, indent=2) + '\n')
    print(args.output.resolve())


if __name__ == '__main__':
    main()
