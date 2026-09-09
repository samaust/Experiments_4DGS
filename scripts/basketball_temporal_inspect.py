"""Fixed training-view point projections and sparse/dense coverage for pilot review."""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

from basketball_study import MANIFEST, PILOT, ROOT, digest, write_new
from basketball_temporal_geometry import project, projection


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cloud', type=Path, required=True)
    p.add_argument('--masks', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    result = json.loads((a.cloud / 'result.json').read_text())
    manifest = json.loads(MANIFEST.read_text())
    cameras = {int(c['id']): c for c in manifest['cameras']}
    normalization = json.loads((a.cloud / 'config.json').read_text())['normalization']
    transform = np.array(normalization['transform'])
    sparse = np.load(ROOT / '.local/sync-pivot/basketball-static-init/static-cloud.npz')['positions']
    masks = json.loads((a.masks / 'result.json').read_text())
    obs = {(int(r['camera_id']), r['frame_id']): r for r in masks['observations']}
    summaries = []
    for frame in PILOT:
        arrays = []
        for r in result['records']:
            if r['frame'] == frame and 'path' in r:
                if digest(a.cloud / r['path']) != r['sha256']:
                    raise ValueError('cloud changed')
                arrays.append(dict(np.load(a.cloud / r['path'], allow_pickle=False)))
        xyz = np.concatenate([x['world_positions'] for x in arrays])
        region = np.concatenate([x['region'] for x in arrays])
        vel = np.concatenate([x['velocities'] for x in arrays])
        measured = np.concatenate([x['velocity_valid'] for x in arrays])
        colors = np.concatenate([x['colors'] for x in arrays])
        for camera in (1, 11, 21, 31):
            c = cameras[camera]
            rgb = np.array(Image.open(MANIFEST.parent / c['frames'][frame]['path']).convert('RGB'))
            labels = np.load(a.masks / f'camera{camera}-frame{frame}.npy')
            projected = []
            panels = []
            for title, points, color in [('sparse projection', sparse, None),
                                          ('dense player projection', xyz[region == 1], colors[region == 1])]:
                uv, z = project(points, projection(c))
                valid = np.isfinite(uv).all(1) & (z > 0) & (uv[:, 0] >= 0) & (uv[:, 0] < 960) & (uv[:, 1] >= 0) & (uv[:, 1] < 540)
                xy = np.floor(uv[valid]).astype(int)
                coverage = np.zeros((540, 960), np.uint8)
                coverage[xy[:, 1], xy[:, 0]] = 1
                coverage = cv2.dilate(coverage, np.ones((3, 3), np.uint8)).astype(bool)
                projected.append(coverage)
                panel = rgb.copy()
                panel[coverage] = [0, 255, 128] if color is None else [255, 64, 192]
                image = Image.fromarray(panel)
                ImageDraw.Draw(image).text((8, 8), f'{title} camera {camera} frame {frame}', fill='white', stroke_width=2, stroke_fill='black')
                panels.append(image)
            canvas = Image.new('RGB', (1920, 540))
            for i, panel in enumerate(panels):
                canvas.paste(panel, (960*i, 0))
            canvas.save(a.output / f'camera{camera}-frame{frame}-comparison.png')
            motion = Image.fromarray(rgb)
            draw = ImageDraw.Draw(motion)
            indices = np.flatnonzero((region == 1) & measured)[::10]
            world_velocity = vel[indices] @ np.linalg.inv(transform[:3, :3]).T
            first, depth = project(xyz[indices], projection(c))
            second, _ = project(xyz[indices]+world_velocity*.02, projection(c))
            for uv, end, z in zip(first, second, depth):
                if z > 0 and np.isfinite([*uv, *end]).all() and 0 <= uv[0] < 960 and 0 <= uv[1] < 540:
                    draw.line([tuple(uv-.5), tuple(end-.5)], fill=(0, 255, 128), width=1)
            motion.save(a.output / f'camera{camera}-frame{frame}-motion.png')
            components = []
            for label, phrase in obs[camera, frame]['phrases'].items():
                if phrase != 'person':
                    continue
                mask = labels == int(label)
                components.append(dict(instance=int(label), pixels=int(mask.sum()),
                    sparse_covered=int((mask & projected[0]).sum()), dense_covered=int((mask & projected[1]).sum())))
            summaries.append(dict(camera=camera, frame=frame, components=components,
                static_points=int((region == 0).sum()), person_points=int((region == 1).sum()),
                ball_points=int((region == 2).sum()), measured_velocities=int(measured.sum()),
                unsupported_velocities=int(((region > 0) & ~measured).sum())))
    write_new(a.output / 'coverage.json', dict(schema='basketball-temporal-pilot-coverage/v1',
        summaries=summaries, cloud_result_sha256=digest(a.cloud / 'result.json'),
        coverage='3x3 pixel projection footprint; not a learned-render metric or semantic acceptance',
        accepted=False, review='pending visual inspection and foreground-only native initial rendering'))


if __name__ == '__main__':
    main()
