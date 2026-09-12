"""Generate a training-only dense cloud with pinned RoMa and local PyTorch geometry.

The script name is retained for compatibility with historical EDGS workflows.
"""
import argparse
import hashlib
import json
from pathlib import Path
import warnings
import time

import numpy as np
from PIL import Image
import torch

from edgs_source import ROMA_PIN, ROMA_WEIGHTS, load_roma
from triangulation import solver_metadata, triangulate_points
from stg_scene import SelfCapScene


def nearest_neighbors(transforms):
    """Euclidean distance over flattened transforms; exact ties choose lowest index."""
    distances = torch.cdist(transforms, transforms, compute_mode='donot_use_mm_for_euclid_dist')
    distances.fill_diagonal_(float('inf'))
    return distances.argmin(dim=1)


def geometry_mask(xyz, numerical, P1, P2, uv1, uv2, size1, size2):
    """Retain positive depth and <=0.01 normalized L1 residual in both views."""
    positive = torch.ones(len(xyz), dtype=torch.bool, device=xyz.device)
    good = numerical & torch.isfinite(xyz).all(1)
    for P, uv, (width, height) in zip((P1, P2), (uv1, uv2), (size1, size2)):
        projected = xyz @ P[:, :3].T + P[:, 3]
        error = ((projected[:, :2] / projected[:, 2:3] - uv).abs()
                 * uv.new_tensor([2/width, 2/height])).sum(1)
        positive &= projected[:, 2] > 0
        good &= torch.isfinite(error) & (error <= .01)
    return good & positive, positive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--edgs', help='deprecated, ignored; no EDGS checkout is needed')
    parser.add_argument('--roma', type=Path, required=True)
    parser.add_argument('--weights', type=Path, required=True)
    parser.add_argument('--frame-id', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.edgs is not None:
        warnings.warn('--edgs is deprecated and ignored', FutureWarning, stacklevel=2)
    if args.output.exists():
        parser.error('choose a new output directory')
    scene = SelfCapScene(args.manifest)
    keys = sorted(scene.training_keys(args.frame_id))
    if len(keys) != 23:
        parser.error('requires a selected frame with exactly 23 training cameras')
    views = [scene.camera(key, device='cpu', load_image=True) for key in keys]
    transforms = torch.stack([view.world_view_transform.flatten() for view in views])
    neighbors = nearest_neighbors(transforms).tolist()
    images = [Image.fromarray((view.original_image.permute(1, 2, 0) * 255)
                             .round().byte().numpy()) for view in views]
    torch.manual_seed(0)
    start = time.monotonic()
    model = load_roma(args.roma, args.weights)
    torch.cuda.reset_peak_memory_stats()
    projections = [(torch.tensor(scene.cameras[key[0]]['K'], dtype=torch.float32)
                    @ view.world_view_transform.T[:3]).cuda()
                   for key, view in zip(keys, views)]
    positions, colors, pairs = [], [], []
    with torch.inference_mode():
        for index, other in enumerate(neighbors):
            image_a, image_b = images[index], images[other]
            warp, confidence = model.match(image_a, image_b, device='cuda')
            # Released EDGS fast sampling: threshold certainty, no replacement.
            probability = confidence.flatten().clone()
            probability[~torch.isfinite(probability) | (probability < 0)] = 0
            probability[probability > model.sample_thresh] = 1
            count = min(15000, int((probability > 0).sum().item()))
            if count < 4:
                raise RuntimeError('too few positive-certainty matches')
            selected = torch.multinomial(probability, count, replacement=False)
            matches = warp.reshape(-1, 4)[selected]
            uv_a, uv_b = model.to_pixel_coordinates(matches, image_a.height,
                image_a.width, image_b.height, image_b.width)
            xyz, numerical = triangulate_points(projections[index], projections[other],
                uv_a, uv_b, device='cuda', dtype=torch.float32)
            good, positive = geometry_mask(xyz, numerical, projections[index], projections[other],
                uv_a, uv_b, image_a.size, image_b.size)
            # Continuous pixel centers start at .5, so floor indexes source RGB.
            xy = uv_a[good].floor().long().cpu().numpy()
            rgb = np.asarray(image_a)[xy[:, 1].clip(0, image_a.height-1),
                                      xy[:, 0].clip(0, image_a.width-1)]
            positions.append(xyz[good, :3].cpu().numpy())
            colors.append(rgb.astype(np.float32)/255)
            record = dict(source=keys[index][0], neighbor=keys[other][0],
                          sampled=count, retained=int(good.sum().item()),
                          numerical_rejections=int((~numerical).sum().item()),
                          positive_depth=int(positive.sum().item()))
            pairs.append(record)
            print(json.dumps(record), flush=True)
    torch.cuda.synchronize()
    points, rgb = np.concatenate(positions), np.concatenate(colors)
    if len(points) < 4:
        raise RuntimeError('insufficient validated dense geometry')
    args.output.mkdir(parents=True)
    archive = args.output / 'cloud.npz'
    np.savez(archive, positions=points, colors=rgb)
    with archive.open('rb') as stream:
        archive_sha256 = hashlib.file_digest(stream, 'sha256').hexdigest()
    inputs = [dict(camera_id=key[0], **scene.frames[key]) for key in keys]
    report = dict(status='prepared', schema='edgs-selfcap-cloud/v2', frame_id=args.frame_id,
        manifest_sha256=scene.sha256, roma_pin=ROMA_PIN,
        geometry_source=solver_metadata(),
        numerical_rejections=sum(pair['numerical_rejections'] for pair in pairs), weight_sha256=ROMA_WEIGHTS, inputs=inputs,
        pairs=pairs, points=len(points), archive_sha256=archive_sha256,
        time=float(np.mean([item['normalized_time'] for item in inputs])),
        time_range=[min(item['normalized_time'] for item in inputs),
                    max(item['normalized_time'] for item in inputs)],
        wall_seconds=time.monotonic()-start, peak_allocated_bytes=torch.cuda.max_memory_allocated(),
        device=torch.cuda.get_device_name(), seed=0,
        adaptations=['local PyTorch geometry; all 23 training references, one nearest neighbor; exact ties use lowest camera index',
                     'indoor matcher; 15000 weighted samples per reference; coarse 560, asymmetric, no upsampling',
                     'RoMa continuous pixel coordinates with shared K; no W-1/H-1 endpoint remapping',
                     'drop nonfinite/negative-depth points and >0.01 L1 NDC residual in either view',
                     'omit EDGS opacity/scale/SH initialization; retain world-space points and source RGB'],
        limitations=['two-view fits are not multi-view tracks',
                     'same source frame has residual per-camera corrected-time differences',
                     'no dense temporal initialization or trained quality claim'])
    (args.output / 'result.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({key: report[key] for key in ('points', 'wall_seconds', 'peak_allocated_bytes')}))


if __name__ == '__main__':
    main()
