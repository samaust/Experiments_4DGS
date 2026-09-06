"""Generate one training-only dense cloud using adapted released EDGS helpers.

Uses native RoMa matching and EDGS nearest-neighbor/triangulation functions.
This geometry-only adapter is not the complete EDGS Gaussian initialization.
EDGS workflow attribution and non-commercial terms: docs/licenses/EDGS.txt.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

import numpy as np
from PIL import Image
import torch

from edgs_source import ROMA_PIN, ROMA_WEIGHTS, calibrated_projection, load_geometry, load_roma
from stg_scene import SelfCapScene


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--edgs', type=Path, required=True)
    parser.add_argument('--roma', type=Path, required=True)
    parser.add_argument('--weights', type=Path, required=True)
    parser.add_argument('--frame-id', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('choose a new output directory')
    scene = SelfCapScene(args.manifest)
    keys = sorted(scene.training_keys(args.frame_id))
    if len(keys) != 23:
        parser.error('requires a selected frame with exactly 23 training cameras')
    pin = subprocess.check_output(['git', '-C', str(args.edgs), 'rev-parse', 'HEAD'],
                                  text=True).strip()
    if pin != 'f90b022445fc88368f75e66e8fb34aea88372cac':
        parser.error('expected audited EDGS source revision')
    if subprocess.check_output(['git', '-C', str(args.edgs), 'status', '--porcelain',
                                '--untracked-files=no'], text=True):
        parser.error('modified EDGS source')
    native, evidence = load_geometry(args.edgs)
    views = [scene.camera(key, device='cpu', load_image=True) for key in keys]
    transforms = torch.stack([view.world_view_transform.flatten() for view in views])
    neighbors = native['k_closest_vectors'](transforms, 1)[:, 0].tolist()
    images = [Image.fromarray((view.original_image.permute(1, 2, 0) * 255)
                             .round().byte().numpy()) for view in views]
    torch.manual_seed(0)
    start = time.monotonic()
    model = load_roma(args.roma, args.weights)
    torch.cuda.reset_peak_memory_stats()
    projections = [calibrated_projection(torch.tensor(scene.cameras[key[0]]['K']),
                                         view.world_view_transform.T).cuda()
                   for key, view in zip(keys, views)]
    positions, colors, pairs = [], [], []
    with torch.inference_mode():
        for index, other in enumerate(neighbors):
            image_a, image_b = images[index], images[other]
            warp, confidence = model.match(image_a, image_b, device='cuda')
            if not torch.isfinite(warp).all() or not torch.isfinite(confidence).all():
                raise RuntimeError('non-finite RoMa matches')
            # Released EDGS fast sampling: threshold certainty, no replacement.
            probability = confidence.flatten().clone()
            probability[probability > model.sample_thresh] = 1
            count = min(15000, int((probability > 0).sum().item()))
            if count < 4:
                raise RuntimeError('too few positive-certainty matches')
            selected = torch.multinomial(probability, count, replacement=False)
            matches = warp.reshape(-1, 4)[selected]
            uv_a, uv_b = model.to_pixel_coordinates(matches, image_a.height,
                image_a.width, image_b.height, image_b.width)
            xyz, _, _ = native['triangulate_points'](projections[index], projections[other],
                uv_a[:, 0], uv_a[:, 1], uv_b[:, 0], uv_b[:, 1], device='cuda')
            projected_a, projected_b = xyz @ projections[index], xyz @ projections[other]
            error_a = ((projected_a[:, :2] / projected_a[:, 2:3] - uv_a).abs()
                       * uv_a.new_tensor([2/image_a.width, 2/image_a.height])).sum(1)
            error_b = ((projected_b[:, :2] / projected_b[:, 2:3] - uv_b).abs()
                       * uv_b.new_tensor([2/image_b.width, 2/image_b.height])).sum(1)
            positive = (projected_a[:, 2] > 0) & (projected_b[:, 2] > 0)
            finite = torch.isfinite(xyz).all(1) & torch.isfinite(error_a) & torch.isfinite(error_b)
            good = finite & positive & (error_a <= .01) & (error_b <= .01)
            # Continuous pixel centers start at .5, so floor indexes source RGB.
            xy = uv_a[good].floor().long().cpu().numpy()
            rgb = np.asarray(image_a)[xy[:, 1].clip(0, image_a.height-1),
                                      xy[:, 0].clip(0, image_a.width-1)]
            positions.append(xyz[good, :3].cpu().numpy())
            colors.append(rgb.astype(np.float32)/255)
            record = dict(source=keys[index][0], neighbor=keys[other][0],
                          sampled=count, retained=int(good.sum().item()),
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
    report = dict(status='prepared', schema='edgs-selfcap-cloud/v1', frame_id=args.frame_id,
        manifest_sha256=scene.sha256, edgs_pin=pin, roma_pin=ROMA_PIN,
        source_evidence=evidence, weight_sha256=ROMA_WEIGHTS, inputs=inputs,
        pairs=pairs, points=len(points), archive_sha256=archive_sha256,
        time=float(np.mean([item['normalized_time'] for item in inputs])),
        time_range=[min(item['normalized_time'] for item in inputs),
                    max(item['normalized_time'] for item in inputs)],
        wall_seconds=time.monotonic()-start, peak_allocated_bytes=torch.cuda.max_memory_allocated(),
        device=torch.cuda.get_device_name(), seed=0,
        adaptations=['geometry-only EDGS fast path; all 23 training references, one native nearest neighbor',
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
