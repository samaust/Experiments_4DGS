#!/usr/bin/env python3
"""Offline held-out and shared-sweep rendering from an ATGS scene bundle."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys
import time
from types import SimpleNamespace

from atgs_initialization import digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkout', type=Path, default=Path('.local/ATGS'))
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--training-config', type=Path, required=True)
    parser.add_argument('--provenance', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--benchmark', action='store_true')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('choose a new output directory')
    started = time.monotonic()
    offline = runpy.run_path(str(Path(__file__).with_name('offline-python.py')))['restrict_network']()
    print(json.dumps(offline), flush=True)
    import torch
    from torchvision.utils import save_image
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable; ATGS rendering stopped, no CPU fallback')
    from atgs_bundle import inspect_bundle
    from atgs_checkpoint import restore_auxiliary_state
    from atgs_scene import ATGSSelfCapScene
    from atgs_config import load_config
    from atgs_update import load_update_helpers
    scene = ATGSSelfCapScene(args.manifest)
    provenance = json.loads(args.provenance.read_text())
    config = json.loads(args.training_config.read_text())
    if provenance['manifest_sha256'] != scene.sha256:
        raise ValueError('render manifest differs from training')
    if hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest() != provenance['config_sha256']:
        raise ValueError('training configuration digest mismatch')
    # Check actual patched source contents, not merely the upstream revision.
    for name, expected in config['sources'].items():
        root = Path(__file__).parent if name.startswith('adapter/') else args.checkout
        relative = name.removeprefix('adapter/') if name.startswith('adapter/') else name
        path = root / relative
        if 'prompts' in Path(relative).parts or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError('invalid source inventory path')
        if digest(path) != expected:
            raise ValueError('training source changed: ' + name)
    record = inspect_bundle(args.checkpoint, expected_provenance=provenance)
    sys.path.insert(0, str(args.checkout.resolve()))
    from scene.gaussian_model import GaussianModel
    from gaussian_renderer import render, prefilter_voxel
    resolved, (dataset, hidden, opt, pipe), cfg = load_config(args.checkout)
    if vars(resolved) != config['resolved']:
        raise ValueError('resolved rendering configuration differs from training')
    _, helper_hash = load_update_helpers(args.checkout)
    if helper_hash != provenance['helper_ast_sha256']:
        raise ValueError('update helper provenance mismatch')
    auxiliary = torch.load(args.checkpoint / 'auxiliary.pth', map_location='cpu', weights_only=True)
    model = GaussianModel(hidden, opt, dataset.feat_dim, 10, dataset.voxel_size,
                          dataset.update_depth, dataset.update_init_factor, dataset.update_hierachy_factor,
                          dataset.use_feat_bank, dataset.appearance_dim, dataset.ratio,
                          dataset.add_opacity_dist, dataset.add_cov_dist, dataset.add_color_dist)
    cloud = SimpleNamespace(point_times_list=auxiliary['tensors']['point_times_list']['value'].numpy())
    model.load_ply_sparse_gaussian(str(args.checkpoint / 'point_cloud.ply'), cloud, [0, 60])
    model.load_model(str(args.checkpoint))
    restore_auxiliary_state(model, auxiliary, device='cuda')
    model.mlp_color.eval()
    background = torch.tensor([1., 1., 1.] if dataset.white_background else [0., 0., 0.], device='cuda')
    args.output.mkdir(parents=True)
    frames, sweep_frames = [], []
    with torch.no_grad():
        def pixels(view, validate=True):
            visible = prefilter_voxel(view, model, pipe, background)
            image = render(view, model, pipe, background, iteration=record['iteration'], visible_mask=visible)['render']
            if validate and (image.shape != (3, view.image_height, view.image_width) or not torch.isfinite(image).all()):
                raise ValueError('invalid rendered image')
            return image

        def save(view, destination):
            image = pixels(view)
            destination.parent.mkdir(parents=True, exist_ok=True)
            raw_hash = hashlib.sha256(image.cpu().contiguous().numpy().tobytes()).hexdigest()
            save_image(image.clamp(0, 1), destination)
            return dict(path=str(destination.relative_to(args.output)), sha256=digest(destination),
                        float_sha256=raw_hash, dimensions=[view.image_width, view.image_height],
                        normalized_time=view.time)

        for key in scene.frames:
            if scene.cameras[key[0]]['split'] != 'test':
                continue
            view = scene.camera(key, device='cuda')
            frames.append(dict(camera=key[0], frame_id=key[1],
                               **save(view, args.output / 'images' / key[0] / f'{key[1]:06d}.png')))
        for index in range(20):
            view = scene.sweep_camera(index, device='cuda')
            sweep_frames.append(dict(index=index, **save(view, args.output / 'sweep' / f'{index:05d}.png')))
        benchmark = None
        if args.benchmark:
            camera_id = scene.manifest['sweep']['start_camera']
            view = scene.camera((camera_id, 4150), device='cuda')
            for _ in range(10):
                pixels(view, validate=False)
            durations = []
            for _ in range(100):
                torch.cuda.synchronize()
                tick = time.perf_counter()
                pixels(view, validate=False)
                torch.cuda.synchronize()
                durations.append(time.perf_counter() - tick)
            benchmark = dict(warmups=10, timed_renders=100, seconds=durations, fps=100 / sum(durations),
                             camera=camera_id, frame_id=4150, dimensions=[view.image_width, view.image_height],
                             excludes='camera setup, loading, saving, encoding and image validation')
    report = dict(status='passed', model='atgs', iteration=record['iteration'], bundle=record,
        manifest_sha256=scene.sha256, incomplete_training=record['iteration'] < opt.iterations,
        frames=frames, sweep=scene.manifest['sweep'], sweep_frames=sweep_frames, benchmark=benchmark,
        checkpoint_bytes=sum(item['bytes'] for item in record['files'].values()),
        wall_seconds=time.monotonic() - started, process_id=os.getpid(), gpu=torch.cuda.get_device_name(),
        network_isolation=offline, peak_allocated_bytes=torch.cuda.max_memory_allocated())
    (args.output / 'render.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(iteration=record['iteration'], held_out_frames=len(frames), sweep_poses=len(sweep_frames),
                         fps=benchmark['fps'] if benchmark else None), indent=2))


if __name__ == '__main__':
    main()
