"""Budget-supervised native FreeTimeGsVanilla training on shared SelfCap inputs."""
import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import random
import signal
import socket
import sys
import time

from training_budget import TrainingBudget, atomic_json
from training_supervisor import supervise
from freetimegs_initialization import digest


def worker(args):
    import numpy as np
    import torch
    from atgs_sampler import ManifestBalancedSampler
    from freetimegs_checkpoint import restore_checkpoint, save_checkpoint
    from freetimegs_model import NativeFreeTimeModel
    from freetimegs_normalization import prepare_training_inputs
    from freetimegs_scene import FreeTimeSelfCapScene
    from freetimegs_training import load_training
    from torchmetrics.image.lpip import LearnedPerceptualImagePatchSimilarity
    import gsplat.csrc as rasterizer
    import fused_ssim_cuda

    stopping = [False]
    signal.signal(signal.SIGTERM, lambda *_: stopping.__setitem__(0, True))
    stop_at = float(os.environ['TRAINING_STOP_MONOTONIC'])

    def deny_network(*unused, **kwargs):
        raise RuntimeError('network disabled during FreeTimeGS training')

    socket.create_connection = deny_network
    socket.socket.connect = deny_network
    socket.socket.connect_ex = deny_network
    torch.hub.set_dir(str(args.torch_cache / 'hub'))
    random.seed(0)
    np.random.seed(0)
    torch.manual_seed(0)
    torch.cuda.manual_seed_all(0)
    cfg, _, _ = load_training(args.checkout)
    cfg.start_frame, cfg.end_frame = 4120, 4180
    base_scene = FreeTimeSelfCapScene(args.manifest)
    scene, data, normalization = prepare_training_inputs(args.checkout, base_scene,
                                                         args.initialization, args.reference_cloud)
    adapters = ('train-freetimegs-manifest.py', 'freetimegs_model.py', 'freetimegs_training.py',
                'freetimegs_checkpoint.py', 'freetimegs_source.py', 'freetimegs_normalization.py',
                'freetimegs_scene.py', 'stg_scene.py', 'freetimegs_initialization.py',
                'training_rng.py', 'stg_checkpoint.py', 'atgs_sampler.py')
    configuration = dict(native=asdict(cfg), normalization=normalization, seed=0,
        sampler='synchronous shuffled epochs; reused balanced sampler with one bucket, no prefetch',
        adapters={name: digest(Path(__file__).with_name(name)) for name in adapters},
        binaries=dict(gsplat=digest(rasterizer.__file__), fused_ssim=digest(fused_ssim_cuda.__file__)),
        alexnet_sha256=digest(args.torch_cache / 'hub/checkpoints/alexnet-owt-7be5be79.pth'))
    provenance = dict(manifest_sha256=scene.sha256,
        initialization_sha256=normalization['initialization_sha256'],
        configuration_sha256=hashlib.sha256(json.dumps(configuration, sort_keys=True).encode()).hexdigest())
    atomic_json(args.output / 'training-config.json', configuration)
    atomic_json(args.output / 'provenance.json', provenance)
    lpips = LearnedPerceptualImagePatchSimilarity(net_type='alex', normalize=True).cuda()
    model = NativeFreeTimeModel(args.checkout, cfg, data, scene_scale=normalization['scene_scale'], device='cuda')
    del data
    model.enable_training(args.checkout, scene_scale=normalization['scene_scale'], device='cuda', lpips=lpips)
    sampler = ManifestBalancedSampler(scene, 1, seed=0)
    iteration = 0
    if args.resume:
        iteration, loop = restore_checkpoint(args.resume, model, provenance=provenance)
        sampler.load_state_dict(loop['sampler'])
    start_iteration = iteration
    saved = []
    reason = 'schedule_complete'

    def checkpoint(reason):
        torch.cuda.synchronize()
        path = args.output / f'checkpoint-{iteration:06d}.pt'
        start = time.monotonic()
        save_checkpoint(path, model, iteration=iteration,
                        loop_state={'sampler': sampler.state_dict()}, provenance=provenance)
        saved.append(dict(path=str(path), iteration=iteration, reason=reason,
                          wall_seconds=time.monotonic()-start, bytes=path.stat().st_size,
                          sha256=digest(path)))
        atomic_json(args.output / 'checkpoints.json', saved)

    while iteration < cfg.max_steps:
        if stopping[0] or stop_at-time.monotonic() <= args.checkpoint_reserve+args.step_reserve:
            reason = 'deadline'
            break
        if args.max_steps is not None and iteration-start_iteration >= args.max_steps:
            reason = 'requested_segment'
            break
        key = next(sampler)
        camera = scene.training_camera(key, device='cuda', load_image=True)
        metrics = model.training_step(iteration, camera, model.schedulers)
        torch.cuda.synchronize()
        metrics = {name: value.item() if isinstance(value, torch.Tensor) else value
                   for name, value in metrics.items()}
        if not np.isfinite(metrics['loss']):
            raise RuntimeError('non-finite native loss; training stopped')
        iteration += 1
        with (args.output / 'loss.jsonl').open('a') as stream:
            stream.write(json.dumps(dict(iteration=iteration, key=key, **metrics), allow_nan=False)+'\n')
        if iteration % 50 == 0 or iteration <= 5:
            print(json.dumps(dict(iteration=iteration, **metrics)), flush=True)
        if iteration % args.checkpoint_interval == 0:
            checkpoint('periodic')
    if not saved or saved[-1]['iteration'] != iteration:
        checkpoint(reason)
    atomic_json(args.output / 'worker-result.json', dict(reason=reason, iteration=iteration,
        incomplete=iteration < cfg.max_steps, checkpoints=saved, device=torch.cuda.get_device_name(),
        peak_allocated_bytes=torch.cuda.max_memory_allocated(), peak_reserved_bytes=torch.cuda.max_memory_reserved()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkout', type=Path, default=Path('.local/FreeTimeGsVanilla'))
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--initialization', type=Path)
    parser.add_argument('--reference-cloud', type=Path)
    parser.add_argument('--torch-cache', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--resume', type=Path)
    parser.add_argument('--max-steps', type=int)
    parser.add_argument('--checkpoint-interval', type=int, default=1000)
    parser.add_argument('--checkpoint-reserve', type=float, default=120.)
    parser.add_argument('--step-reserve', type=float, default=30.)
    parser.add_argument('--check-gpu', action='store_true')
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable; FreeTimeGS stopped before budget reservation, no CPU fallback')
    if args.check_gpu:
        print(torch.cuda.get_device_name())
        return
    for name in ('manifest', 'initialization', 'reference_cloud', 'torch_cache', 'output'):
        if getattr(args, name) is None:
            parser.error(f'--{name.replace("_", "-")} is required')
    for name in ('checkout', 'manifest', 'initialization', 'reference_cloud', 'torch_cache', 'output', 'resume'):
        if getattr(args, name) is not None:
            setattr(args, name, getattr(args, name).resolve())
    if args.max_steps is not None and args.max_steps <= 0:
        parser.error('--max-steps must be positive')
    import math
    if args.checkpoint_interval <= 0 or any(not math.isfinite(value) or value <= 0 for value in
                                           (args.checkpoint_reserve, args.step_reserve)):
        parser.error('checkpoint interval and reserves must be finite and positive')
    if not (args.torch_cache / 'hub/checkpoints/alexnet-owt-7be5be79.pth').is_file():
        parser.error('cached AlexNet weights required')
    if args.worker:
        if 'TRAINING_STOP_MONOTONIC' not in os.environ:
            parser.error('worker requires deadline supervisor')
        return worker(args)
    if args.output.exists():
        parser.error('choose a new output directory')
    repo = Path(__file__).resolve().parents[1]
    args.output.mkdir(parents=True)
    command = [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:], '--worker']
    with TrainingBudget(repo / '.local/runs/plan-004-training-budget.json',
                        method='freetimegs', scene='selfcap-dance1') as budget:
        if budget.available <= args.checkpoint_reserve+args.step_reserve+35:
            parser.error('insufficient remaining training allocation')
        budget.start(command=command, provenance=dict(manifest_sha256=digest(args.manifest)))
        with (args.output / 'train.log').open('w') as log:
            result = supervise(command, cwd=repo, log=log, seconds=budget.remaining_seconds())
        budget.finish('deadline' if result['stop_requested'] else
                      'completed' if result['exit_code'] == 0 else 'failed')
    atomic_json(args.output / 'result.json', result)
    print(json.dumps(result, indent=2))
    if result['exit_code'] != 0:
        print((args.output / 'train.log').read_text()[-12000:], file=sys.stderr)
        raise SystemExit(1)


if __name__ == '__main__':
    main()
