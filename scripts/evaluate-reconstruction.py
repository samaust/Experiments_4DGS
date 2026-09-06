#!/usr/bin/env python3
"""Evaluate matched PNG sequences with the shared PSNR/SSIM/LPIPS-Alex protocol."""
import argparse
import json
import math
from pathlib import Path


def read(path):
    import numpy as np
    from PIL import Image
    return np.asarray(Image.open(path).convert('RGB'), dtype=np.float32) / 255.0


def ssim(a, b):
    from skimage.metrics import structural_similarity
    return float(structural_similarity(a, b, channel_axis=-1, data_range=1.0,
                                      win_size=7, use_sample_covariance=True))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--predictions', type=Path, required=True)
    p.add_argument('--ground-truth', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--lpips-alex', action='store_true',
                   help='compute LPIPS-Alex using the installed lpips package')
    args = p.parse_args()
    try:
        import numpy as np
    except ImportError as error:
        p.error('evaluation requires numpy and Pillow in the selected environment: ' + str(error))
    if args.output.exists():
        p.error('refusing to overwrite existing output')
    predictions = sorted(args.predictions.glob('*.png'))
    if not predictions:
        p.error('no prediction PNGs found')
    if {p.name for p in predictions} != {p.name for p in args.ground_truth.glob('*.png')}:
        p.error('prediction and ground-truth PNG filename sets must match exactly')
    rows = []
    for path in predictions:
        target = args.ground_truth / path.name
        if not target.is_file():
            p.error('missing ground truth for ' + path.name)
        pred, gt = read(path), read(target)
        if pred.shape != gt.shape:
            p.error(f'dimension mismatch for {path.name}: {pred.shape} != {gt.shape}')
        mse = float(np.mean((pred - gt) ** 2))
        row = {'frame': path.stem, 'psnr': 'Infinity' if mse == 0 else -10 * math.log10(mse),
               'ssim': ssim(pred, gt)}
        rows.append(row)
    if args.lpips_alex:
        try:
            import torch
            import lpips
            metric = lpips.LPIPS(net='alex').eval()
            with torch.no_grad():
                for row, path in zip(rows, predictions):
                    pred, gt = read(path), read(args.ground_truth / path.name)
                    x = torch.from_numpy(pred).permute(2, 0, 1).unsqueeze(0) * 2 - 1
                    y = torch.from_numpy(gt).permute(2, 0, 1).unsqueeze(0) * 2 - 1
                    row['lpips_alex'] = float(metric(x, y).item())
        except (ImportError, RuntimeError) as error:
            p.error('LPIPS-Alex requested but unavailable: ' + str(error))
    keys = [key for key in rows[0] if key not in ('frame',)]
    aggregate = {key: 'Infinity' if any(row[key] == 'Infinity' for row in rows)
                 else float(np.mean([row[key] for row in rows])) for key in keys}
    result = {'protocol': {'color': 'RGB uint8 converted to [0,1]',
                           'psnr': 'mean squared error over all pixels',
                           'ssim': 'skimage RGB, window 7, sample covariance, data_range=1',
                           'infinity_encoding': 'Infinity string means positive infinity',
                           'lpips': 'AlexNet, only when --lpips-alex is supplied'},
              'count': len(rows), 'aggregate': aggregate, 'per_frame': rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'count': len(rows), 'aggregate': aggregate}, indent=2))


if __name__ == '__main__':
    main()
