#!/usr/bin/env python3
"""Budget-supervised native ATGS training on the shared SelfCap manifest."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from training_budget import TrainingBudget, atomic_json
from training_supervisor import supervise
from atgs_initialization import digest


def worker(args):
    import random
    import numpy as np
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable; ATGS training stopped, no CPU fallback')
    from atgs_scene import ATGSSelfCapScene
    from atgs_config import load_config
    from atgs_initialization import load_initial_cloud, validate_initialization
    from atgs_sampler import ManifestBalancedSampler
    from atgs_native_step import NativeTrainingStep, load_loss_helpers
    from atgs_update import load_update_helpers
    from atgs_bundle import save_bundle, load_bundle_supplements
    from atgs_checkpoint import restore_auxiliary_state
    from atgs_loop_state import restore_loop_state
    from atgs_train_control import run_training_segment
    from types import SimpleNamespace

    stopping = [False]
    signal.signal(signal.SIGTERM, lambda *_: stopping.__setitem__(0, True))
    stop_at = float(os.environ['TRAINING_STOP_MONOTONIC'])
    random.seed(0)
    np.random.seed(0)
    torch.manual_seed(0)
    torch.cuda.manual_seed_all(0)
    sys.path.insert(0, str(args.checkout))
    from scene.gaussian_model import GaussianModel
    from utils.graphics_utils import BasicPointCloud
    from gaussian_renderer import render, prefilter_voxel

    scene = ATGSSelfCapScene(args.manifest)
    initialization = validate_initialization(args.initialization, scene)
    resolved, (dataset, hidden, opt, pipe), cfg = load_config(args.checkout)
    if opt.start_stat < min(opt.update_until, opt.iterations):
        raise ValueError('active production densification requires separately validated initialization')
    helpers, helper_hash = load_update_helpers(args.checkout)
    losses, loss_hash = load_loss_helpers(args.checkout)
    # Include local patched Python code, not just the clean Git revision.
    source_files = sorted(p for p in args.checkout.rglob('*.py')
                          if 'prompts' not in p.parts and '.git' not in p.parts)
    source_hashes = {str(p.relative_to(args.checkout)): digest(p) for p in source_files}
    adapters = ('train-atgs-manifest.py', 'atgs_initialization.py', 'atgs_native_step.py',
                'atgs_train_control.py', 'atgs_bundle.py', 'atgs_checkpoint.py', 'atgs_loop_state.py',
                'atgs_sampler.py', 'atgs_config.py', 'atgs_scene.py', 'stg_scene.py',
                'training_rng.py', 'atgs_update.py')
    source_hashes.update({'adapter/' + name: digest(Path(__file__).with_name(name)) for name in adapters})
    config = dict(resolved=vars(resolved), initialization=initialization, seed=0,
                  anchor_lifetimes='midpoint geometry, native always-active frame-zero marker',
                  initialization_ratio=1., sources=source_hashes, loss_helper_ast_sha256=loss_hash)
    provenance = dict(manifest_sha256=scene.sha256,
        source_revision=subprocess.check_output(['git', '-C', str(args.checkout), 'rev-parse', 'HEAD'], text=True).strip(),
        config_sha256=hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest(),
        helper_ast_sha256=helper_hash)
    atomic_json(args.output / 'training-config.json', config)
    atomic_json(args.output / 'provenance.json', provenance)
    model = GaussianModel(hidden, opt, dataset.feat_dim, 10, dataset.voxel_size,
                          dataset.update_depth, dataset.update_init_factor, dataset.update_hierachy_factor,
                          dataset.use_feat_bank, dataset.appearance_dim, dataset.ratio,
                          dataset.add_opacity_dist, dataset.add_cov_dist, dataset.add_color_dist)
    sampler = ManifestBalancedSampler(scene, cfg.levels, seed=0)
    if args.resume:
        auxiliary, saved_loop, _ = load_bundle_supplements(args.resume, expected_provenance=provenance)
        cloud = SimpleNamespace(point_times_list=auxiliary['tensors']['point_times_list']['value'].numpy())
        model.load_ply_sparse_gaussian(str(args.resume / 'point_cloud.ply'), cloud, [0, 60])
        model.load_model(str(args.resume))
        restore_auxiliary_state(model, auxiliary, device='cuda')
        model.training_setup(opt, 1, str(args.resume))
        loop = restore_loop_state(model, sampler, saved_loop)
    else:
        cloud, extent = load_initial_cloud(args.initialization, scene, BasicPointCloud)
        model.create_from_pcd(cloud, extent, 1., [0, 60])
        model.training_setup(opt, None, '')
        loop = dict(iteration=0, micro_steps=0, encoder_visits={}, update_count=0,
                    last_update_iteration=0, ema_loss=0.)
    model.mlp_color.train()
    start_iteration = loop['iteration']
    background = torch.tensor([1., 1., 1.] if dataset.white_background else [0., 0., 0.], device='cuda')
    callbacks = NativeTrainingStep(scene=scene, opt=opt, pipe=pipe, cfg=cfg, background=background,
                                   render=render, prefilter=prefilter_voxel, losses=losses, updates=helpers)
    saved = []
    def checkpoint(current, current_sampler, state, reason):
        torch.cuda.synchronize()
        started = time.monotonic()
        path = args.output / f"checkpoint-{state['iteration']:06d}-{len(saved):03d}"
        save_bundle(path, current, current_sampler, state, provenance)
        saved.append(dict(path=str(path), iteration=state['iteration'], reason=reason,
                          wall_seconds=time.monotonic() - started))
        atomic_json(args.output / 'checkpoints.json', saved)

    def microstep(current, key, iteration):
        result = callbacks(current, key, iteration)
        with (args.output / 'loss.jsonl').open('a') as stream:
            stream.write(json.dumps(dict(iteration=iteration, key=key, **callbacks.last_metrics)) + '\n')
        return result

    # Small budget-counted integration runs pause without shortening the schedule.
    def pause():
        return stopping[0] or (args.max_steps is not None and loop['iteration'] - start_iteration >= args.max_steps)

    reason = run_training_segment(model=model, sampler=sampler, loop=loop, max_iterations=opt.iterations,
        remaining_seconds=lambda: max(0., stop_at - time.monotonic()), microstep=microstep,
        update=callbacks.update, checkpoint=checkpoint, force_update_due=callbacks.force_update_due,
        after_microstep=callbacks.after_microstep, pause_requested=pause,
        checkpoint_interval=args.checkpoint_interval, checkpoint_reserve=args.checkpoint_reserve,
        step_reserve=args.step_reserve)
    atomic_json(args.output / 'worker-result.json', dict(reason=reason, loop=loop,
        incomplete=loop['iteration'] < opt.iterations, checkpoints=saved, device=torch.cuda.get_device_name(),
        peak_allocated_bytes=torch.cuda.max_memory_allocated(), peak_reserved_bytes=torch.cuda.max_memory_reserved()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-gpu', action='store_true')
    parser.add_argument('--checkout', type=Path, default=Path('.local/ATGS'))
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--initialization', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--resume', type=Path)
    parser.add_argument('--max-steps', type=int)
    parser.add_argument('--checkpoint-interval', type=int, default=1000)
    parser.add_argument('--checkpoint-reserve', type=float, default=120.)
    parser.add_argument('--step-reserve', type=float, default=30.)
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.check_gpu:
        import torch
        if not torch.cuda.is_available():
            raise RuntimeError('CUDA unavailable; ATGS preflight stopped, no CPU fallback')
        print(torch.cuda.get_device_name())
        return
    if any(getattr(args, name) is None for name in ('manifest', 'initialization', 'output')):
        parser.error('--manifest, --initialization and --output are required')
    for name in ('checkout', 'manifest', 'initialization', 'output', 'resume'):
        if getattr(args, name) is not None:
            setattr(args, name, getattr(args, name).resolve())
    if args.max_steps is not None and args.max_steps <= 0:
        parser.error('--max-steps must be positive')
    if args.checkpoint_interval <= 0 or any(not math.isfinite(v) or v <= 0 for v in
            (args.checkpoint_reserve, args.step_reserve)):
        parser.error('checkpoint interval and time reserves must be finite and positive')
    if args.worker:
        if 'TRAINING_STOP_MONOTONIC' not in os.environ:
            parser.error('worker requires deadline supervisor')
        return worker(args)
    if args.output.exists():
        parser.error('choose a new output directory')
    repo = Path(__file__).resolve().parents[1]
    args.output.mkdir(parents=True)
    command = [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:], '--worker']
    with TrainingBudget(repo / '.local/runs/plan-004-training-budget.json', method='atgs', scene='selfcap-dance1') as budget:
        if budget.available <= args.checkpoint_reserve + args.step_reserve + 35:
            parser.error('insufficient remaining allocation for training and checkpoint reserves')
        budget.start(command=command, provenance=dict(manifest_sha256=digest(args.manifest)))
        with (args.output / 'train.log').open('w') as log:
            result = supervise(command, cwd=repo, log=log, seconds=budget.remaining_seconds())
        budget.finish('deadline' if result['stop_requested'] else 'completed' if result['exit_code'] == 0 else 'failed')
    atomic_json(args.output / 'result.json', result)
    print(json.dumps(result, indent=2))
    if result['exit_code'] != 0:
        print((args.output / 'train.log').read_text()[-12000:], file=sys.stderr)
        raise SystemExit(1)


if __name__ == '__main__':
    main()
