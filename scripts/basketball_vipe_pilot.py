"""Thin pinned-ViPE pilot; priors only, never a shared rig or initialization."""
import argparse
import gc
import json
import os
import math
import statistics
from pathlib import Path
import subprocess
import sys
import time

from basketball_audit import PIN, frame_roles, sha256

FRAMES = [50, 75, 100, 125, 149]
CONFIG = {'schema': 'basketball-vipe-pilot/v2', 'cameras': [4, 12, 21, 29],
          'source_frames': FRAMES, 'resolution': [960, 540],
          'mask_phrases': ['person', 'basketball'],
          'max_focal_relative_range': .25, 'min_dynamic_fraction': .001,
          'max_dynamic_fraction': .75, 'min_positive_depth_fraction': .99,
          'motion_gray_threshold': 20, 'motion_dilation_pixels': 9,
          'depth_scale': 'uncertain estimated scale; not measured metric ground truth'}


def fitting_frame(camera_id, frame_id, *, all_priors=False):
    cameras = range(34) if all_priors else frame_roles()['training_cameras']
    if camera_id not in cameras or frame_id not in frame_roles()['fit']:
        raise ValueError('pilot may only access training-camera fitting frames')
    return frame_id - 50


def intrinsic_stability(focals):
    """Frozen pilot sanity gate for a fixed physical camera, not rig accuracy."""
    if len(focals) != len(FRAMES) or any(not math.isfinite(f) or f <= 0 for f in focals):
        return {"passed": False, "relative_range": None}
    relative_range = (max(focals)-min(focals))/statistics.median(focals)
    return {"passed": relative_range <= CONFIG["max_focal_relative_range"],
            "relative_range": relative_range}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--vipe', type=Path, required=True)
    parser.add_argument('--output', type=Path, help='New attempt directory; never overwritten')
    parser.add_argument('--all-priors', type=Path, metavar='PASSED_PILOT_RESULT',
                        help='Process all 34 cameras after a successful pilot')
    a = parser.parse_args()
    config = dict(CONFIG)
    if a.all_priors:
        pilot = json.loads(a.all_priors.read_text())
        if pilot['status'] != 'pilot-passed' or pilot['blockers']:
            raise ValueError('all-camera priors require a successful pilot')
        if pilot['input_audit_sha256'] != sha256(a.workspace / 'input-audit.json'):
            raise ValueError('pilot input provenance changed')
        config.update(schema='basketball-vipe-all-priors/v1', cameras=list(range(34)), seed=0,
                      pilot_result_sha256=sha256(a.all_priors))
    output = a.output if a.output is not None else a.workspace / 'pilot'
    output.mkdir(exist_ok=False)
    (output / 'config.json').write_text(json.dumps(config, indent=2) + '\n')
    audit = json.loads((a.workspace / 'input-audit.json').read_text())
    if audit['status'] != 'inputs-verified':
        raise ValueError('input audit blocked')
    if sha256(a.workspace / 'frame-roles.json') != audit['frame_roles_sha256']:
        raise ValueError('changed frame-role provenance')
    git = lambda *args: subprocess.check_output(['git', '-C', str(a.vipe), *args], text=True).strip()
    if git('rev-parse', 'HEAD') != PIN or git('status', '--porcelain') or git('branch', '--show-current') != 'tridi':
        raise ValueError('changed ViPE provenance')
    result = {'schema': 'basketball-vipe-pilot-result/v1', 'status': 'blocked',
              'blockers': [], 'observations': [], 'source_sha256': {}, 'weight_sha256': {},
              'intrinsic_stability': {},
              'adapter_sha256': sha256(__file__),
              'input_audit_sha256': sha256(a.workspace / 'input-audit.json'),
              'config_sha256': sha256(output / 'config.json'), 'vipe_revision': PIN}
    # Explicitly hash relevant source/config and extension files without traversing prompts.
    for relative in git('ls-files', 'vipe', 'configs', 'pyproject.toml', 'uv.lock',
                        'LICENSE', 'THIRD_PARTY_LICENSES.md').splitlines():
        path = a.vipe / relative
        if 'prompts' not in path.parts and path.is_file():
            result['source_sha256'][relative] = sha256(path)
    for path in a.vipe.glob('*.so'):
        result['source_sha256'][path.name] = sha256(path)
    hub = Path.home() / '.cache/torch/hub'
    weights = [hub / 'geocalib/pinhole.tar', hub / 'sam/sam_vit_b_01ec64.pth',
               hub / 'aot/R50_DeAOTL_PRE_YTB_DAV.pth', hub / 'checkpoints/groundingdino_swint_ogc.pth']
    hf = Path.home() / '.cache/huggingface/hub'
    for name in ['models--lpiccinelli--unidepth-v2-vitl14', 'models--bert-base-uncased']:
        weights.extend(p for p in (hf / name / 'snapshots').glob('*/*') if p.is_file())
    for path in weights:
        result['weight_sha256'][str(path)] = sha256(path)
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    os.environ['TORCH_EXTENSIONS_DIR'] = str((a.workspace / 'torch_extensions').resolve())
    sys.path.insert(0, str(a.vipe.resolve()))
    started = time.monotonic()
    try:
        import cv2
        import numpy as np
        import torch
        import vipe_ext
        from vipe.utils.device import configure_device
        device = configure_device('cuda')
        from vipe.priors.geocalib import GeoCalib
        from vipe.priors.depth.unidepth import UniDepth2Model
        from vipe.priors.depth.base import DepthEstimationInput
        from vipe.priors.track_anything import TrackAnythingPipeline
        from vipe.streams.base import VideoFrame
        result['runtime'] = {'python': sys.version, 'torch': torch.__version__,
                             'cuda': torch.version.cuda, 'gpu': torch.cuda.get_device_name(),
                             'extension': vipe_ext.__file__}
        if 'seed' in config:
            import random
            random.seed(config['seed'])
            np.random.seed(config['seed'])
            torch.manual_seed(config['seed'])
            torch.cuda.manual_seed_all(config['seed'])
        torch.cuda.reset_peak_memory_stats()
        calib = GeoCalib().to(device).eval()
        videos = {int(v['camera_id']): v for v in audit['videos']}
        for camera in config['cameras']:
            source = videos[camera]
            if sha256(source['path']) != source['sha256']:
                raise ValueError(f'changed video provenance: {camera}')
            capture = cv2.VideoCapture(source['path'])
            focals = []
            for frame_id in FRAMES:
                stream_id = fitting_frame(camera, frame_id, all_priors=bool(a.all_priors))
                images = []
                # Neighbor remains strictly inside fitting membership.
                neighbor = frame_id + 1 if frame_id < 149 else frame_id - 1
                for index in [frame_id, neighbor]:
                    fitting_frame(camera, index, all_priors=bool(a.all_priors))
                    capture.set(cv2.CAP_PROP_POS_FRAMES, index)
                    ok, bgr = capture.read()
                    if not ok:
                        raise ValueError(f'cannot decode {camera}/{index}')
                    images.append(cv2.cvtColor(cv2.resize(bgr, (960, 540), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB))
                rgb = torch.from_numpy(images[0]).to(device).float() / 255
                with torch.inference_mode():
                    prior = calib.calibrate(rgb.permute(2, 0, 1))
                K = prior['camera'].K[0].cpu().numpy()
                focal = float(K[0, 0])
                focals.append(focal)
                stem = f'camera{camera}-frame{frame_id}'
                cv2.imwrite(str(output / (stem + '.png')), cv2.cvtColor(images[0], cv2.COLOR_RGB2BGR))
                motion = cv2.absdiff(cv2.cvtColor(images[0], cv2.COLOR_RGB2GRAY), cv2.cvtColor(images[1], cv2.COLOR_RGB2GRAY)) > config['motion_gray_threshold']
                motion = cv2.dilate(motion.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
                np.save(output / (stem + '-motion.npy'), motion)
                entry = {'camera_id': camera, 'source_frame_id': frame_id, 'stream_frame_id': stream_id,
                         'K_960x540': K.tolist(), 'focal_uncertainty': prior['focal_uncertainty'].cpu().tolist(),
                         'stem': stem}
                result['observations'].append(entry)
                print(f'GeoCalib {camera}/{frame_id}: focal={focal:.2f}', flush=True)
            capture.release()
            stability = intrinsic_stability(focals)
            result['intrinsic_stability'][str(camera)] = stability
            if not stability['passed']:
                result['blockers'].append(f'camera {camera}: unusable intrinsic stability')
        del calib
        gc.collect()
        torch.cuda.empty_cache()
        # Stop before expensive depth/masks if intrinsic pilot has already failed.
        if not result['blockers']:
            depth = UniDepth2Model()
            for entry in result['observations']:
                if entry['source_frame_id'] != 100:
                    continue
                rgb = torch.from_numpy(cv2.cvtColor(cv2.imread(str(output / (entry['stem'] + '.png'))), cv2.COLOR_BGR2RGB)).to(device).float()/255
                K = np.array(entry['K_960x540'])
                with torch.inference_mode():
                    predicted = depth.estimate(DepthEstimationInput(rgb=rgb, intrinsics=torch.tensor([K[0,0], K[1,1], K[0,2], K[1,2]], device=device)))
                array = predicted.metric_depth.cpu().numpy()
                entry['positive_depth_fraction'] = float(np.mean(np.isfinite(array) & (array > 0)))
                np.savez_compressed(output / (entry['stem'] + '-depth.npz'), depth=array, confidence=predicted.confidence.cpu().numpy())
                if entry['positive_depth_fraction'] < config['min_positive_depth_fraction']:
                    result['blockers'].append(f"{entry['stem']}: invalid depth")
            del depth
            gc.collect()
            torch.cuda.empty_cache()
            for entry in result['observations']:
                # Independent semantic detections avoid tracking across nonconsecutive pilot samples.
                tracker = TrackAnythingPipeline(config['mask_phrases'])
                rgb = torch.from_numpy(cv2.cvtColor(cv2.imread(str(output / (entry['stem'] + '.png'))), cv2.COLOR_BGR2RGB)).to(device).float()/255
                with torch.inference_mode():
                    instance, phrases = tracker.track(VideoFrame(raw_frame_idx=entry['stream_frame_id'], rgb=rgb, information=f"source_frame_id={entry['source_frame_id']}"))
                semantic = instance.cpu().numpy() > 0
                moving = semantic | np.load(output / (entry['stem'] + '-motion.npy'))
                cv2.imwrite(str(output / (entry['stem'] + '-static.png')), (~moving).astype(np.uint8)*255)
                entry['semantic_fraction'] = float(semantic.mean())
                entry['dynamic_fraction'] = float(moving.mean())
                entry['phrases'] = phrases
                if not config['min_dynamic_fraction'] <= entry['semantic_fraction'] <= config['max_dynamic_fraction']:
                    result['blockers'].append(f"{entry['stem']}: unusable semantic masking")
                print(f"mask {entry['stem']}: {entry['dynamic_fraction']:.4f}", flush=True)
                del tracker
                gc.collect()
                torch.cuda.empty_cache()
        result['peak_allocated_bytes'] = torch.cuda.max_memory_allocated()
        result['peak_reserved_bytes'] = torch.cuda.max_memory_reserved()
    except BaseException as error:
        result['blockers'].append(f'{type(error).__name__}: {error}')
        raise
    finally:
        result['wall_seconds'] = time.monotonic() - started
        result['status'] = 'blocked' if result['blockers'] else ('priors-generated' if a.all_priors else 'pilot-passed')
        (output / 'result.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    return bool(result['blockers'])


if __name__ == '__main__':
    raise SystemExit(main())
