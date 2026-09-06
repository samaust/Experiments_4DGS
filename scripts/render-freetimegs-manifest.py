"""Offline native FreeTimeGS checkpoint rendering on held-out/shared-sweep cameras."""
import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import runpy
import time
from types import MethodType

from freetimegs_initialization import digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkout', type=Path, default=Path('.local/FreeTimeGsVanilla'))
    for name in ('manifest', 'checkpoint', 'training-config', 'provenance', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--benchmark', action='store_true')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('choose a new output directory')
    started = time.monotonic()
    offline = runpy.run_path(str(Path(__file__).with_name('offline-python.py')))['restrict_network']()
    import torch
    from torchvision.utils import save_image
    from freetimegs_checkpoint import validate_parameters
    from freetimegs_model import NativeFreeTimeModel
    from freetimegs_normalization import NormalizedFreeTimeScene, load_normalization
    from freetimegs_source import load_initializer, load_temporal_methods
    from freetimegs_training import load_training
    import gsplat.csrc as rasterizer
    import fused_ssim_cuda
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable; no CPU rendering fallback')
    config = json.loads(args.training_config.read_text())
    provenance = json.loads(args.provenance.read_text())
    if hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest() != provenance['configuration_sha256']:
        raise ValueError('training configuration digest mismatch')
    for name, expected in config['adapters'].items():
        path = Path(__file__).parent / name
        if Path(name).name != name or name == 'prompts':
            raise ValueError('invalid adapter inventory path')
        if digest(path) != expected:
            raise ValueError('training adapter changed: '+name)
    binaries = dict(gsplat=digest(rasterizer.__file__), fused_ssim=digest(fused_ssim_cuda.__file__))
    if binaries != config['binaries']:
        raise ValueError('native renderer binary changed')
    helpers, normalization_evidence = load_normalization(args.checkout)
    if normalization_evidence != config['normalization']['source']:
        raise ValueError('normalization source changed')
    scene = NormalizedFreeTimeScene(args.manifest, config['normalization']['transform'], helpers['transform_cameras'])
    if scene.sha256 != provenance['manifest_sha256']:
        raise ValueError('render manifest differs from training')
    state = torch.load(args.checkpoint, map_location='cpu', weights_only=True)
    if state.get('schema') != 'freetimegs-training/v1' or state['provenance'] != provenance:
        raise ValueError('checkpoint schema/provenance mismatch')
    cfg, _, training_evidence = load_training(args.checkout)
    cfg.start_frame, cfg.end_frame = 4120, 4180
    if asdict(cfg) != state['config'] or asdict(cfg) != config['native']:
        raise ValueError('native render configuration mismatch')
    methods, render_digest = load_temporal_methods(args.checkout, include_render=True)
    _, init_digest = load_initializer(args.checkout)
    source_digests = dict(initializer=init_digest, render=render_digest, **training_evidence)
    if source_digests != state['source_digests']:
        raise ValueError('native model source changed')
    validate_parameters(state['parameters'], cfg.sh_degree)
    iteration = state['iteration']
    model = NativeFreeTimeModel.__new__(NativeFreeTimeModel)
    model.cfg = cfg
    model.splats = torch.nn.ParameterDict({name: torch.nn.Parameter(value.cuda(), requires_grad=False)
                                           for name, value in state['parameters'].items()})
    del state  # Optimizer state is unnecessary for inference.
    for name, method in methods.items():
        setattr(model, name, MethodType(method, model))
    degree = min(max(iteration-1, 0)//cfg.sh_degree_interval, cfg.sh_degree)
    args.output.mkdir(parents=True)
    frames, sweep_frames = [], []
    with torch.inference_mode():
        def pixels(camera, validate=True):
            image = model.render(camera, sh_degree=degree)[0][0, ..., :3].permute(2, 0, 1)
            if validate and (image.shape != (3, camera.height, camera.width) or not torch.isfinite(image).all()):
                raise ValueError('invalid native render')
            return image

        def save(camera, path):
            image = pixels(camera)
            path.parent.mkdir(parents=True, exist_ok=True)
            raw_hash = hashlib.sha256(image.cpu().contiguous().numpy().tobytes()).hexdigest()
            save_image(image.clamp(0, 1), path)
            return dict(path=str(path.relative_to(args.output)), sha256=digest(path), float_sha256=raw_hash,
                        dimensions=[camera.width, camera.height], normalized_time=camera.t)

        for key in scene.frames:
            if scene.cameras[key[0]]['split'] == 'test':
                camera = scene.camera(key, device='cuda')
                frames.append(dict(camera=key[0], frame_id=key[1],
                    **save(camera, args.output / 'images' / key[0] / f'{key[1]:06d}.png')))
        for index in range(20):
            camera = scene.sweep_camera(index, device='cuda')
            sweep_frames.append(dict(index=index, **save(camera, args.output / 'sweep' / f'{index:05d}.png')))
        benchmark = None
        if args.benchmark:
            camera = scene.camera(('0015', 4150), device='cuda')
            for _ in range(10):
                pixels(camera, validate=False)
            durations = []
            for _ in range(100):
                torch.cuda.synchronize()
                tick = time.perf_counter()
                pixels(camera, validate=False)
                torch.cuda.synchronize()
                durations.append(time.perf_counter()-tick)
            benchmark = dict(warmups=10, timed_renders=100, seconds=durations, fps=100/sum(durations),
                camera='0015', frame_id=4150, dimensions=[camera.width, camera.height],
                excludes='camera setup, loading, saving, encoding and image validation')
    bundle = dict(checkpoint_sha256=digest(args.checkpoint), iteration=iteration,
                  provenance=provenance, source_digests=source_digests)
    runtime = dict(torch=torch.__version__, binaries=binaries)
    report = dict(status='passed', model='freetimegs', iteration=iteration, bundle=bundle, runtime=runtime,
        manifest_sha256=scene.sha256, incomplete_training=iteration < cfg.max_steps,
        frames=frames, sweep=scene.manifest['sweep'], sweep_frames=sweep_frames, benchmark=benchmark,
        checkpoint_bytes=args.checkpoint.stat().st_size, wall_seconds=time.monotonic()-started,
        process_id=os.getpid(), gpu=torch.cuda.get_device_name(), network_isolation=offline,
        renderer_sha256=digest(__file__), peak_allocated_bytes=torch.cuda.max_memory_allocated(),
        active_sh_degree=degree)
    (args.output / 'render.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(iteration=iteration, held_out_frames=len(frames), sweep_poses=len(sweep_frames),
                         fps=benchmark['fps'] if benchmark else None), indent=2))


if __name__ == '__main__':
    main()
