#!/usr/bin/env python3
"""Render an STG full or lite checkpoint with the native renderer.

No dataset, COLMAP, training, or evaluation metrics are involved. Timestamps
are normalized model time, not recovered physical capture timestamps.
"""
import argparse
import json
import math
from pathlib import Path
import sys
import time
import hashlib


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkout', type=Path, required=True)
    parser.add_argument('--ply', type=Path, required=True)
    parser.add_argument('--cameras', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--camera-index', type=int, default=0)
    parser.add_argument('--resolution', type=int, default=2)
    parser.add_argument('--model', choices=('lite', 'full'), default='lite',
                        help='STG representation to load (default: lite)')
    parser.add_argument('--rgb-function', choices=('sandwich', 'sandwichnoact'),
                        help='upstream decoder variant used by the checkpoint')
    parser.add_argument('--decoder', type=Path,
                        help='full-model decoder state; defaults to point_cloud.ply with .pt')
    parser.add_argument('--times', type=float, nargs='+', default=[0, 0.5, 0.98])
    parser.add_argument('--benchmark', action='store_true',
                        help='ten warmups and 100 synchronized renders, excluding saving')
    args = parser.parse_args()
    if args.model == 'lite' and (args.decoder or args.rgb_function):
        parser.error('decoder options require --model full')
    if args.model == 'full':
        if not args.rgb_function:
            parser.error('--model full requires the checkpoint\'s --rgb-function')
        sidecar = args.ply.with_suffix('.pt').resolve()
        if args.decoder and args.decoder.resolve() != sidecar:
            parser.error('upstream requires --decoder beside the PLY with the same stem and .pt suffix')
        if not sidecar.is_file():
            parser.error('missing full STG decoder: ' + str(sidecar))
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
    if args.model == 'full':
        from thirdparty.gaussian_splatting.scene.oursfull import GaussianModel
    else:
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
                  rayd=True if args.model == 'full' else None,
                  image_name=camera['img_name'], uid=args.camera_index)
    render, settings, rasterizer = getrenderpip(
        'test_ours_full_fused' if args.model == 'full' else 'test_ours_lite')
    args.output.mkdir(parents=True)
    with torch.no_grad():
        model = GaussianModel(3, args.rgb_function) if args.model == 'full' else GaussianModel(3)
        if args.model == 'full':
            decoder = (args.decoder or args.ply.with_suffix('.pt')).resolve()
            if not decoder.is_file():
                raise FileNotFoundError(
                    f'full STG requires decoder state: {decoder}; pass --decoder explicitly')
            import torch
            state = torch.load(decoder, map_location='cpu', weights_only=True)
            if not isinstance(state, dict):
                raise ValueError(f'full STG decoder is not a state dict: {decoder}')
            missing, unexpected = model.rgbdecoder.load_state_dict(state, strict=False)
            if missing or unexpected:
                raise ValueError('full STG decoder mismatch: '
                                 f'missing={list(missing)}, unexpected={list(unexpected)}')
            model.rgbdecoder.cuda().eval()
        model.load_ply(str(args.ply.resolve()))
        if args.model == 'full':
            view.rays = torch.cat((view.rayo, view.rayd), dim=1)
        background = torch.zeros(9 if args.model == 'full' else 3, device='cuda')
        records = []
        for index, timestamp in enumerate(args.times):
            view.timestamp = timestamp
            result = render(view, model, None, background, GRsetting=settings, GRzer=rasterizer)
            pixels = result['render']
            if not torch.isfinite(pixels).all() or pixels.std() == 0:
                raise RuntimeError('renderer returned nonfinite or constant pixels')
            save_image(pixels.clamp(0, 1), args.output / f'{index:05d}.png')
            records.append({'normalized_time': timestamp, 'finite': True})
        timing = None
        if args.benchmark:
            def timed_render(index):
                view.timestamp = args.times[index % len(args.times)]
                return render(view, model, None, background, GRsetting=settings, GRzer=rasterizer)
            for index in range(10):
                timed_render(index)
            torch.cuda.synchronize()
            durations = []
            for index in range(100):
                torch.cuda.synchronize()
                started = time.perf_counter()
                timed_render(index)
                torch.cuda.synchronize()
                durations.append(time.perf_counter() - started)
            timing = dict(warmup_renders=10, timed_renders=100,
                          synchronized_seconds=durations, fps=100/sum(durations),
                          excludes='loading, PNG saving, encoding')
        provenance = {}
        for component in [args.ply, args.cameras] + ([args.ply.with_suffix('.pt')] if args.model == 'full' else []):
            with component.open('rb') as stream:
                provenance[str(component.resolve())] = dict(bytes=component.stat().st_size,
                    sha256=hashlib.file_digest(stream, 'sha256').hexdigest())
        report = {'renderer': 'upstream ' + ('test_ours_full_fused' if args.model == 'full'
                                             else 'test_ours_lite'),
                  'model': args.model, 'rgb_function': args.rgb_function,
                  'decoder': str((args.decoder or args.ply.with_suffix('.pt')).resolve())
                  if args.model == 'full' else None,
                  'gpu': torch.cuda.get_device_name(),
                  'torch': torch.__version__, 'camera': camera, 'resolution': [width, height],
                  'ply': str(args.ply.resolve()), 'frames': records,
                  'benchmark': timing, 'provenance': provenance,
                  'note': 'Qualitative preview; no held-out metrics.'}
        (args.output / 'preview.json').write_text(json.dumps(report, indent=2) + '\n')
    print(args.output.resolve())


if __name__ == '__main__':
    main()
