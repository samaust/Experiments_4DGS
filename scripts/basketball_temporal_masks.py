"""Training-only Plan 026 masks from pinned ViPE; reset tracking at every pair."""
import argparse
import gc
import json
import os
from pathlib import Path
import random
import signal
import socket
import subprocess
import sys
import time

from basketball_study import CAMERAS, KEYFRAMES, MANIFEST, PILOT, ROOT
from basketball_study import digest, training_key, verify_files, write_new


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vipe', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--full', action='store_true')
    a = parser.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    historical = json.loads((ROOT / '.local/calibration/basketball-v1/pilot/result.json').read_text())
    audit = json.loads((ROOT / '.local/calibration/basketball-v1/input-audit.json').read_text())
    revision = subprocess.check_output(['git', '-C', str(a.vipe), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != audit['vipe']['revision']:
        raise ValueError('ViPE revision changed')
    verify_files({str(a.vipe / p): h for p, h in historical['source_sha256'].items()})
    weights = {p: h for p, h in historical['weight_sha256'].items()
               if any(s in p for s in ('/sam/', '/aot/', 'groundingdino', 'bert-base'))}
    verify_files(weights)
    preflight = json.loads((ROOT / 'docs/experiments/basketball-dense-temporal/preflight-001.json').read_text())
    if digest(MANIFEST) != preflight['manifest_sha256']:
        raise ValueError('manifest changed')
    manifest = json.loads(MANIFEST.read_text())
    cameras = {c['id']: c for c in manifest['cameras']}
    frames = KEYFRAMES if a.full else PILOT
    config = dict(schema='basketball-temporal-masks/v1', frames=list(frames), cameras=list(CAMERAS),
                  manifest_sha256=digest(MANIFEST), vipe_revision=revision,
                  adapter_sha256=digest(__file__), weight_sha256=weights,
                  source_sha256=historical['source_sha256'],
                  phrases=['person', 'basketball'], seed=0,
                  tracking='fresh state at each keyframe; track only its immediate successor',
                  coordinates='960x540 undistorted processed RGB; array indices, no further resize')
    write_new(a.output / 'config.json', config)
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    def deny(*_, **__):
        raise RuntimeError('network disabled in Plan 026 mask worker')
    socket.create_connection = deny
    socket.socket.connect = deny
    socket.socket.connect_ex = deny
    sys.path.insert(0, str(a.vipe.resolve()))
    import cv2
    import numpy as np
    import torch
    from PIL import Image
    from vipe.priors.track_anything import TrackAnythingPipeline
    from vipe.streams.base import VideoFrame
    from vipe.utils.device import configure_device
    from vipe.utils.model_cache import ModelCache
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable; no CPU fallback')
    device = configure_device('cuda')
    random.seed(0)
    np.random.seed(0)
    torch.manual_seed(0)
    torch.cuda.manual_seed_all(0)
    stopping = [False]
    signal.signal(signal.SIGTERM, lambda *_: stopping.__setitem__(0, True))
    cache = ModelCache()
    started = time.monotonic()
    observations = []
    result = dict(status='incomplete', observations=observations, config_sha256=digest(a.output / 'config.json'))
    try:
        for camera in CAMERAS:
            for frame in frames:
                if stopping[0]:
                    raise InterruptedError('mask worker interrupted')
                tracker = TrackAnythingPipeline(config['phrases'], model_cache=cache)
                images = []
                for f in (frame, frame+1):
                    c, f = training_key(camera, f)
                    entry = cameras[c]['frames'][f]
                    path = MANIFEST.parent / entry['path']
                    if digest(path) != entry['sha256']:
                        raise ValueError(f'changed training RGB: {path}')
                    rgb = np.array(Image.open(path).convert('RGB'))
                    if rgb.shape != (540, 960, 3):
                        raise ValueError('processed resolution changed')
                    images.append(rgb)
                    with torch.inference_mode():
                        mask, phrases = tracker.track(VideoFrame(raw_frame_idx=f,
                            rgb=torch.from_numpy(rgb.copy()).to(device).float()/255))
                    labels = mask.cpu().numpy()
                    stem = f'camera{camera}-frame{f}'
                    np.save(a.output / (stem + '.npy'), labels, allow_pickle=False)
                    record = dict(camera_id=c, frame_id=f, pair_start=frame,
                                  image_sha256=entry['sha256'], phrases=phrases,
                                  mask_sha256=digest(a.output / (stem + '.npy')),
                                  instances={str(i): int((labels == i).sum()) for i in np.unique(labels)})
                    observations.append(record)
                    with (a.output / 'observations.jsonl').open('a') as stream:
                        stream.write(json.dumps(record) + '\n')
                    if camera in (1, 11, 21, 31):
                        overlay = rgb.copy()
                        for label in np.unique(labels):
                            if label:
                                color = np.array([(int(label)*97)%255, (int(label)*53)%255, (int(label)*191)%255])
                                overlay[labels == label] = (.5*rgb[labels == label]+.5*color).astype(np.uint8)
                        Image.fromarray(overlay).save(a.output / (stem + '-overlay.png'))
                motion = cv2.absdiff(cv2.cvtColor(images[0], cv2.COLOR_RGB2GRAY),
                                    cv2.cvtColor(images[1], cv2.COLOR_RGB2GRAY)) > 20
                motion = cv2.dilate(motion.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
                np.save(a.output / f'camera{camera}-frame{frame}-changing.npy', motion)
                print(json.dumps(dict(camera=camera, pair=[frame, frame+1], seconds=time.monotonic()-started)), flush=True)
                del tracker
                gc.collect()
        result['status'] = 'masks-generated'
    except BaseException as error:
        result['error'] = f'{type(error).__name__}: {error}'
        raise
    finally:
        result['wall_seconds'] = time.monotonic()-started
        result['peak_allocated_bytes'] = torch.cuda.max_memory_allocated()
        result['artifacts'] = {p.name: digest(p) for p in sorted(a.output.iterdir()) if p.suffix in ('.npy', '.png')}
        write_new(a.output / 'result.json', result)


if __name__ == '__main__':
    main()
