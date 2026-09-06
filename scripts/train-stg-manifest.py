#!/usr/bin/env python3
"""Budget-supervised native STG training on the prepared SelfCap profile.

Uses hash-checked upstream training source with narrow, saved adapter hooks.
The optional max-steps boundary is for budget-counted integration runs, not a
different optimization schedule. Every retry shares the central budget ledger.
"""
import argparse
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import time

from training_budget import TrainingBudget, atomic_json
from training_supervisor import supervise
from stg_train_source import adapt_train, LOOP_KEYS


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def worker(a):
    stop_at = float(os.environ['TRAINING_STOP_MONOTONIC'])
    stopping = [False]
    signal.signal(signal.SIGTERM, lambda *_: stopping.__setitem__(0, True))
    import random
    import numpy as np
    import torch
    from plyfile import PlyData
    from stg_scene import SelfCapScene
    from stg_checkpoint import save_checkpoint, restore_checkpoint

    sys.path[:0] = [str(a.checkout), str(a.checkout/'thirdparty/gaussian_splatting')]
    from arguments import OptimizationParams, PipelineParams
    from utils.graphics_utils import BasicPointCloud
    source = adapt_train((a.checkout/'train.py').read_text())
    (a.output/'adapted_train.py').write_text(source)
    namespace = {'__name__': '_manifest_stg', '__file__': str(a.checkout/'train.py')}
    exec(compile(source, str(a.output/'adapted_train.py'), 'exec'), namespace)
    random.seed(0)
    np.random.seed(0)
    torch.manual_seed(0)
    torch.cuda.manual_seed_all(0)
    torch.cuda.reset_peak_memory_stats()
    manifest = SelfCapScene(a.manifest)
    parser = argparse.ArgumentParser()
    opt_group = OptimizationParams(parser)
    pipe_group = PipelineParams(parser)
    defaults = parser.parse_args([])
    opt, pipe = opt_group.extract(defaults), pipe_group.extract(defaults)
    # Use the upstream Techni-style densifier (3), avoiding N3D's world-z=4.5
    # floor cutoff, which has no meaning in the supplied SelfCap coordinates.
    config = dict(optimization=vars(opt), densify=3, seed=0, duration=60,
                  rgbfunction='sandwich' if a.model == 'full' else 'rgbv1',
                  initialization='training-only midpoint, mean corrected training time',
                  image_loading='two-entry CPU image and GPU camera caches',
                  final_iteration='optimizer step performed before checkpoint')
    provenance = json.loads((a.output/'provenance.json').read_text())
    provenance['training_config'] = config
    atomic_json(a.output/'training-config.json', config)

    @lru_cache(maxsize=2)
    def geometry(key):
        return manifest.camera(key, device='cuda', full=a.model == 'full')

    @lru_cache(maxsize=2)
    def image(key):
        return manifest.camera(key, device='cpu', load_image=True).original_image

    class LazyCamera:
        def __init__(self, key):
            self.key = key
            self.source_frame = key[1]
            # Upstream EMS dictionaries are keyed by camera, not frame.
            self.image_name = key[0]
            self.timestamp = manifest.frames[key]['normalized_time']
            c = manifest.cameras[key[0]]
            self.image_width, self.image_height = c['width'], c['height']

        @property
        def original_image(self):
            return image(self.key)

        def __getattr__(self, name):
            return getattr(geometry(self.key), name)

    class Scene:
        def __init__(self, dataset, model, **kwargs):
            self.model_path, self.model = str(a.output), model
            centers = np.array([c['center'] for c in manifest.cameras.values() if c['split'] == 'train'])
            self.cameras_extent = float(np.linalg.norm(centers-centers.mean(0), axis=1).max()*1.1)
            ply = PlyData.read(str(a.initialization/'initialization.ply'))['vertex']
            xyz = np.column_stack([ply[k] for k in ('x', 'y', 'z')]).astype(np.float32)
            colors = np.column_stack([ply[k] for k in ('red', 'green', 'blue')]).astype(np.float32)/255
            midpoint = np.mean([manifest.frames[k]['normalized_time'] for k in manifest.training_keys(4150)])
            model.create_from_pcd(BasicPointCloud(xyz, colors, np.zeros_like(xyz),
                np.full((len(xyz), 1), midpoint, dtype=np.float32)), self.cameras_extent)
            if a.model == 'full':
                model.rgbdecoder.cuda()

        def getTrainCameras(self):
            return [LazyCamera(k) for k in manifest.training_keys()]

        def recordpoints(self, iteration, note):
            with (a.output/'points.jsonl').open('a') as stream:
                stream.write(json.dumps(dict(iteration=iteration, note=note,
                                              points=len(self.model._xyz)))+'\n')

        def save(self, iteration):
            self.model.save_ply(str(a.output/f'point_cloud/iteration_{iteration}/point_cloud.ply'))

    class Hooks:
        last_save = time.monotonic()
        start_iteration = 0
        final_iteration = 0

        def loop_state(self, local):
            return {k: local[k] for k in LOOP_KEYS}

        def save(self, model, opt, iteration, local):
            torch.cuda.synchronize()
            save_checkpoint(a.output/'checkpoint.pt', model, variant=a.model,
                training_args=opt, iteration=iteration, loop_state=self.loop_state(local),
                provenance=provenance)
            self.last_save = time.monotonic()

        def before_loop(self, model, opt, local):
            if a.resume:
                iteration, state, restored_opt = restore_checkpoint(a.resume, model,
                    variant=a.model, provenance=provenance, device='cuda')
                if vars(restored_opt) != vars(opt):
                    raise ValueError('resume optimization configuration differs')
                # Bounds participate in GPU comparisons; other loop state is scalar metadata.
                for key in ('maxbounds', 'minbounds'):
                    state[key] = [v.cuda() if isinstance(v, torch.Tensor) else v for v in state[key]]
                self.start_iteration = iteration
                self.final_iteration = iteration
                return iteration+1, state
            self.save(model, opt, 0, local)
            return 1, {}

        def after_iteration(self, model, opt, iteration, local):
            self.final_iteration = iteration
            loss = float(local['loss'].detach())
            if not np.isfinite(loss):
                raise RuntimeError('nonfinite training loss')
            stop = stopping[0] or time.monotonic() >= stop_at or (
                a.max_steps is not None and iteration-self.start_iteration >= a.max_steps)
            if stop or iteration == opt.iterations or time.monotonic()-self.last_save >= 60:
                self.save(model, opt, iteration, local)
                if stop or iteration == opt.iterations:
                    model.save_ply(str(a.output/'final/point_cloud.ply'))
            with (a.output/'loss.jsonl').open('a') as stream:
                stream.write(json.dumps(dict(iteration=iteration, loss=loss,
                                              points=len(model._xyz)))+'\n')
            return stop

    hooks = Hooks()
    namespace.update(Scene=Scene, hooks=hooks, args=argparse.Namespace(model_path=str(a.output), **config))
    dataset = argparse.Namespace(model='ours_'+a.model, sh_degree=3, loader='manifest', white_background=False)
    namespace['train'](dataset, opt, pipe, [], -1, densify=3, duration=60,
                       rgbfunction=config['rgbfunction'], rdpip='train_ours_'+a.model)
    atomic_json(a.output/'worker-result.json', dict(iteration=hooks.final_iteration,
        incomplete=hooks.final_iteration < opt.iterations,
        gpu=torch.cuda.get_device_name(), peak_allocated_bytes=torch.cuda.max_memory_allocated(),
        peak_reserved_bytes=torch.cuda.max_memory_reserved()))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--checkout', type=Path, required=True)
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--initialization', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--model', choices=['lite', 'full'], required=True)
    p.add_argument('--resume', type=Path)
    p.add_argument('--max-steps', type=int)
    p.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    a = p.parse_args()
    for key in ('checkout', 'manifest', 'initialization', 'output', 'resume'):
        if getattr(a, key) is not None:
            setattr(a, key, getattr(a, key).resolve())
    if a.max_steps is not None and a.max_steps <= 0:
        p.error('max-steps must be positive')
    if a.worker:
        if 'TRAINING_STOP_MONOTONIC' not in os.environ:
            p.error('worker requires deadline supervisor')
        return worker(a)
    if a.output.exists():
        p.error('choose a new output directory; use --resume to load earlier state')
    adapt_train((a.checkout/'train.py').read_text())
    init = json.loads((a.initialization/'result.json').read_text())
    if (init.get('status') != 'triangulated' or init['manifest_sha256'] != digest(a.manifest)
            or {f['camera_id'] for f in init['inputs']} != {f'{i:04d}' for i in range(24) if i != 15}):
        p.error('initialization manifest provenance or training exclusion mismatch')
    repo = Path(__file__).resolve().parents[1]
    files = [a.manifest, a.initialization/'initialization.ply', a.initialization/'result.json',
             a.checkout/'train.py', a.checkout/'helper_train.py',
             a.checkout/f'thirdparty/gaussian_splatting/scene/ours{a.model}.py',
             a.checkout/'thirdparty/gaussian_splatting/renderer/__init__.py']
    files += [repo/'scripts'/name for name in ('stg_scene.py', 'stg_checkpoint.py',
              'stg_train_source.py', 'train-stg-manifest.py')]
    provenance = dict(model=a.model, files={str(f): digest(f) for f in files})
    a.output.mkdir(parents=True)
    atomic_json(a.output/'provenance.json', provenance)
    command = [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:], '--worker']
    with TrainingBudget(repo/'.local/runs/plan-004-training-budget.json',
                        method='stg-'+a.model, scene='selfcap-dance1') as budget:
        if budget.available <= 35:
            p.error('insufficient allocation remaining for checkpoint/shutdown margin')
        budget.start(command=command, provenance=provenance)
        with (a.output/'train.log').open('w') as log:
            result = supervise(command, cwd=repo, log=log, seconds=budget.remaining_seconds())
        budget.finish('deadline' if result['stop_requested'] else
                      'completed' if result['exit_code'] == 0 else 'failed')
    atomic_json(a.output/'result.json', result)
    print(json.dumps(result, indent=2))
    if result['exit_code'] != 0:
        print((a.output/'train.log').read_text()[-12000:], file=sys.stderr)
        raise SystemExit(1)


if __name__ == '__main__':
    main()
