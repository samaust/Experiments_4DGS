"""Prepare all-camera fitting images and static masks without an intrinsic gate.

Run in the pinned ViPE environment. Reuse only hash-verified image/mask pairs;
missing masks use the historical independent person/ball detection plus motion.
Never estimates or imports fitted intrinsics or poses.
"""
import argparse
import gc
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from basketball_audit import sha256, PIN
from basketball_alternatives_protocol import CAMERAS, EARLY, LATE, manifest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--audit', type=Path, required=True)
    p.add_argument('--vipe', type=Path, required=True)
    p.add_argument('--reuse', type=Path, nargs='*', default=[])
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--role', choices=['fit','selection','validation'], default='fit')
    p.add_argument('--frozen-winner',type=Path)
    a = p.parse_args()
    planned={'fit':EARLY+LATE,'selection':(150,162,175,187,199),
             'validation':(200,212,225,237,249)}[a.role]
    role_start,role_end={'fit':(50,149),'selection':(150,199),'validation':(200,249)}[a.role]
    if a.role=='validation':
        if a.frozen_winner is None:
            raise ValueError('validation requires a frozen selected winner')
        frozen=json.loads(a.frozen_winner.read_text())
        if frozen.get('status')!='frozen' or not frozen.get('selection_passed'):
            raise ValueError('winner has not passed selection')
    audit = json.loads(a.audit.read_text())
    if audit['status'] != 'inputs-verified':
        raise ValueError('input audit failed')
    videos = {int(v['camera_id']): v for v in audit['videos']}
    if set(videos) != set(CAMERAS):
        raise ValueError('need all 34 physical cameras')
    git = lambda *args: subprocess.check_output(['git', '-C', str(a.vipe), *args], text=True).strip()
    if git('rev-parse', 'HEAD') != PIN or git('status', '--porcelain'):
        raise ValueError('changed ViPE source')
    for v in videos.values():
        if sha256(v['path']) != v['sha256']:
            raise ValueError('changed source video')
    cached = {}
    for folder in a.reuse:
        artifacts = json.loads((folder/'artifacts.json').read_text())
        for camera in CAMERAS:
            for frame in planned:
                stem = f'camera{camera}-frame{frame}'
                names = [stem+'.png', stem+'-static.png']
                if all(n in artifacts for n in names):
                    for n in names:
                        if sha256(folder/n) != artifacts[n]:
                            raise ValueError(f'changed cache {folder/n}')
                    cached[camera, frame] = folder
    a.output.mkdir(parents=True, exist_ok=False)
    (a.output/'protocol.json').write_text(json.dumps(manifest(), indent=2)+'\n')
    result = dict(status='running', input_audit_sha256=sha256(a.audit),
                  adapter_sha256=sha256(__file__), vipe_revision=PIN, observations=[],
                  source_video_sha256={c: v['sha256'] for c, v in videos.items()},
                  gpu_limit_seconds=None, failures=[],role=a.role,source_frames=planned,
                  frozen_winner_sha256=sha256(a.frozen_winner) if a.frozen_winner else None)
    lock=(a.output.parent/'gpu.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX)
    started = time.monotonic()
    import cv2
    import numpy as np
    import torch
    sys.path.insert(0, str(a.vipe.resolve()))
    os.environ['HF_HUB_OFFLINE'] = '1'  # Explicit reuse of the previously validated mask weights.
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    from vipe.priors.track_anything import TrackAnythingPipeline
    from vipe.streams.base import VideoFrame
    from vipe.utils.device import configure_device
    device = configure_device('cuda')
    torch.manual_seed(0)
    torch.cuda.reset_peak_memory_stats()
    try:
        for camera in CAMERAS:
            capture = cv2.VideoCapture(videos[camera]['path'])
            for frame in planned:
                stem = f'camera{camera}-frame{frame}'
                image_path, mask_path = a.output/(stem+'.png'), a.output/(stem+'-static.png')
                entry = dict(camera_id=camera, source_frame_id=frame, stem=stem)
                if (camera, frame) in cached:
                    folder = cached[camera, frame]
                    for path in (image_path, mask_path):
                        shutil.copy2(folder/path.name, path)
                    entry['reuse_source'] = str(folder)
                else:
                    images = []
                    for index in (frame, frame+1 if frame < role_end else frame-1):
                        assert role_start <= index <= role_end
                        capture.set(cv2.CAP_PROP_POS_FRAMES, index)
                        ok, bgr = capture.read()
                        if not ok:
                            raise ValueError(f'decode failed {camera}/{index}')
                        images.append(cv2.resize(bgr, (960, 540), interpolation=cv2.INTER_AREA))
                    cv2.imwrite(str(image_path), images[0])
                    rgb = torch.from_numpy(cv2.cvtColor(images[0], cv2.COLOR_BGR2RGB)).to(device).float()/255
                    tracker = TrackAnythingPipeline(['person', 'basketball'])
                    with torch.inference_mode():
                        instance, phrases = tracker.track(VideoFrame(raw_frame_idx=frame-role_start, rgb=rgb,
                                                           information=f'source_frame_id={frame}'))
                    semantic = instance.cpu().numpy() > 0
                    gray = [cv2.cvtColor(im, cv2.COLOR_BGR2GRAY) for im in images]
                    motion = cv2.dilate((cv2.absdiff(*gray) > 20).astype(np.uint8), np.ones((9,9), np.uint8)) > 0
                    cv2.imwrite(str(mask_path), (~(semantic | motion)).astype(np.uint8)*255)
                    entry.update(semantic_fraction=float(semantic.mean()), phrases=phrases)
                    if not .001 <= semantic.mean() <= .75:
                        result['failures'].append(f'{stem}: semantic masking gate failed')
                    del tracker, rgb
                    gc.collect()
                    torch.cuda.empty_cache()
                image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
                mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE) > 0
                if image.shape != (540,960) or mask.shape != image.shape:
                    raise ValueError('incorrect input geometry')
                lap = cv2.Laplacian(image, cv2.CV_64F)
                entry.update(image_sha256=sha256(image_path), mask_sha256=sha256(mask_path),
                             static_fraction=float(mask.mean()),
                             static_laplacian_variance=float(lap[mask].var()) if mask.any() else None)
                result['observations'].append(entry)
                print(stem, 'reused' if 'reuse_source' in entry else 'generated', flush=True)
            capture.release()
        result['status'] = 'blocked' if result['failures'] else 'prepared'
    except BaseException as error:
        result['status'] = 'blocked'
        result['failures'].append(f'{type(error).__name__}: {error}')
        raise
    finally:
        result.update(wall_seconds=time.monotonic()-started,
                      peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                      peak_reserved_bytes=torch.cuda.max_memory_reserved())
        (a.output/'result.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    return result['status'] != 'prepared'


if __name__ == '__main__':
    raise SystemExit(main())
