"""Plan 026 absolute-update native continuation, retaining historical checks."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import signal
import socket
import time

from basketball_study import CURVE, MANIFEST, ROOT, digest, verify_files, write_new


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError(f'ambiguous study adaptation: {old}')
    return source.replace(old, new)


def extend_stg(source, *, source_frames=None):
    from stg_train_source import adapt_train
    source = adapt_train(source, source_frames=source_frames)
    source = replace_once(source, 'range(first_iter, opt.iterations + 1)', 'range(first_iter, hooks.target_update + 1)')
    return replace_once(source, 'if iteration <= opt.iterations:', 'if iteration <= hooks.target_update:')


def adapted_stg_worker(source):
    """Keep worker adaptation separately compilable and inspectable."""
    source = replace_once(source, "stop_at = float(os.environ['TRAINING_STOP_MONOTONIC'])", "stop_at = float('inf')")
    source = replace_once(source, 'class Hooks:\n', 'class Hooks:\n        target_update = a.target_update\n')
    source = replace_once(source, 'a.max_steps is not None and iteration-self.start_iteration >= a.max_steps',
                          'iteration >= a.target_update')
    source = source.replace('iteration == opt.iterations', 'iteration == a.target_update')
    source = replace_once(source, 'time.monotonic()-self.last_save >= 60', 'time.monotonic()-self.last_save >= 300 or iteration % 1000 == 0')
    source = source.replace('iteration in (1000, 2000, 5000)', 'iteration in (5000, 10000, 20000, 30000, 50000)')
    source = replace_once(source, 'return iteration+1, state', """save_checkpoint(a.output/'restored-parent.pt', model, variant=a.model,
                    training_args=restored_opt, iteration=iteration, loop_state=state,
                    provenance=provenance)
                self.training_start = time.monotonic()
                atomic_json(a.output/'timing.json', dict(optimizer_loop_start_monotonic=self.training_start))
                return iteration+1, state""")
    source = replace_once(source, 'self.final_iteration = iteration\n            loss =',
                          'self.final_iteration = iteration\n            step_complete_monotonic = time.monotonic()\n            loss =')
    source = replace_once(source, 'dict(iteration=iteration, loss=loss,',
        "dict(iteration=iteration, loss=loss, keys=[camera.key for camera in local['camindex']], elapsed_seconds=step_complete_monotonic-self.training_start,")
    source = source.replace("a.output/'checkpoint.pt'", "a.output/'checkpoint-next.pt'")
    source = replace_once(source, 'torch.cuda.synchronize()\n            save_checkpoint', """import shutil
            estimated = sum(p.numel()*p.element_size() for group in model.optimizer.param_groups for p in group['params'])*8
            if shutil.disk_usage(a.output).free < estimated + 1024**3:
                raise RuntimeError('storage pause: insufficient space for atomic recovery replacement')
            torch.cuda.synchronize()
            save_checkpoint""")
    # Existing atomic checkpoint.pt is this study's only replaceable recovery file.
    # Validate replacement immediately, before it can supersede another recovery.
    source = replace_once(source, "self.last_save = time.monotonic()\n", """saved = torch.load(a.output/'checkpoint-next.pt', map_location='cpu', weights_only=True)
            if saved['iteration'] != iteration or saved['provenance'] != provenance:
                raise ValueError('recovery checkpoint validation failed')
            if any(not torch.isfinite(v).all() for v in saved['parameters'].values()):
                raise ValueError('nonfinite checkpoint parameters')
            os.replace(a.output/'checkpoint-next.pt', a.output/'checkpoint.pt')
            self.last_save = time.monotonic()
""")
    return source


def train_stg(a, parent):
    """Reuse the hash-pinned worker with saved, explicit scheduling/save hooks."""
    worker_path = ROOT / 'scripts/train-stg-manifest.py'
    verify_files(parent['provenance']['files'])
    source = adapted_stg_worker(worker_path.read_text())
    write_new(a.output / 'provenance.json', parent['provenance'])
    generated = a.output / 'study_stg_worker.py'
    generated.write_text(source)
    spec = importlib.util.spec_from_file_location('_study_stg_worker', generated)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.adapt_train = extend_stg
    a.model, a.max_steps = 'full', None
    module.worker(a)


def train_free(a, parent):
    import random
    import numpy as np
    import torch
    from dataclasses import asdict
    from basketball_native_train import prepare_free
    from basketball_scene import FreeTimeBasketballScene
    from atgs_sampler import ManifestBalancedSampler
    from freetimegs_training import load_training
    from freetimegs_model import NativeFreeTimeModel
    from freetimegs_checkpoint import restore_checkpoint, save_checkpoint
    from torchmetrics.image.lpip import LearnedPerceptualImagePatchSimilarity
    random.seed(a.seed)
    np.random.seed(a.seed)
    torch.manual_seed(a.seed)
    torch.cuda.manual_seed_all(a.seed)
    torch.hub.set_dir(str(ROOT / '.local/cache/torch/hub'))
    cfg, _, _ = load_training(a.checkout)
    cfg.start_frame, cfg.end_frame = 0, 50
    scene, data, normalization = prepare_free(FreeTimeBasketballScene(MANIFEST), a.initialization, a.checkout)
    if a.arm == 'freetimegs-dense':
        frozen = json.loads((a.dense_initialization / 'result.json').read_text())
        archive = a.dense_initialization / 'initialization.npz'
        if frozen['status'] != 'accepted-frozen' or frozen['normalization'] != normalization or digest(archive) != frozen['archive_sha256']:
            raise ValueError('dense initialization prerequisite/provenance mismatch')
        with np.load(archive, allow_pickle=False) as arrays:
            data = {k: torch.from_numpy(arrays[k].copy()) for k in data}
        for k, value in data.items():
            if value.shape != (len(data['positions']), 3 if k in ('positions', 'colors', 'velocities') else 1) or not torch.isfinite(value).all():
                raise ValueError('invalid dense initialization arrays')
    provenance = parent['provenance'] if parent else dict(plan=26, method=a.arm, seed=a.seed,
        files={str(MANIFEST): digest(MANIFEST), str(a.dense_initialization / 'result.json'): digest(a.dense_initialization / 'result.json')})
    configuration = json.loads((a.resume.parent / 'training-config.json').read_text()) if parent else dict(native=asdict(cfg), normalization=normalization)
    if configuration['native'] != asdict(cfg) or configuration['normalization'] != normalization:
        raise ValueError('native configuration or normalization changed')
    write_new(a.output / 'training-config.json', configuration)
    if parent and digest(a.output / 'training-config.json') != provenance['configuration_sha256']:
        raise ValueError('historical configuration hash mismatch')
    provenance['configuration_sha256'] = digest(a.output / 'training-config.json')
    write_new(a.output / 'checkpoint-provenance.json', provenance)
    lpips = LearnedPerceptualImagePatchSimilarity(net_type='alex', normalize=True).cuda()
    model = NativeFreeTimeModel(a.checkout, cfg, data, scene_scale=normalization['scene_scale'], device='cuda')
    model.enable_training(a.checkout, scene_scale=normalization['scene_scale'], device='cuda', lpips=lpips)
    del data
    sampler = ManifestBalancedSampler(scene, 1, seed=a.seed)
    iteration = 0
    if a.resume:
        iteration, loop = restore_checkpoint(a.resume, model, provenance=provenance)
        sampler.load_state_dict(loop['sampler'])
        save_checkpoint(a.output / 'restored-parent.pt', model, iteration=iteration,
                        loop_state={'sampler': sampler.state_dict()}, provenance=provenance)
    stopping = [False]
    signal.signal(signal.SIGTERM, lambda *_: stopping.__setitem__(0, True))
    last_save = time.monotonic()
    recovery = None
    saved = []
    started = time.monotonic()
    write_new(a.output / 'timing.json', dict(optimizer_loop_start_monotonic=started))
    while iteration < a.target_update and not stopping[0]:
        key = next(sampler)
        camera = scene.training_camera(key, device='cuda')
        metrics = model.training_step(iteration, camera, model.schedulers)
        torch.cuda.synchronize()
        metrics = {k: float(v.detach()) if isinstance(v, torch.Tensor) else v for k, v in metrics.items()}
        if not np.isfinite(metrics['loss']):
            raise RuntimeError('nonfinite native loss')
        iteration += 1
        with (a.output / 'loss.jsonl').open('a') as stream:
            stream.write(json.dumps(dict(iteration=iteration, key=key, elapsed_seconds=time.monotonic()-started, **metrics))+'\n')
        if iteration % 100 == 0:
            print(json.dumps(dict(iteration=iteration, **metrics)), flush=True)
        if iteration in CURVE or iteration % 1000 == 0 or time.monotonic()-last_save >= 300 or iteration == a.target_update or stopping[0]:
            import shutil
            estimated = sum(p.numel()*p.element_size() for p in model.splats.values())*8
            if shutil.disk_usage(a.output).free < estimated + 1024**3:
                raise RuntimeError('storage pause: insufficient space for atomic recovery replacement')
            path = a.output / f'checkpoint-{iteration:06d}.pt'
            save_checkpoint(path, model, iteration=iteration, loop_state={'sampler': sampler.state_dict()}, provenance=provenance)
            check = torch.load(path, map_location='cpu', weights_only=True)
            if check['iteration'] != iteration or check['provenance'] != provenance:
                raise ValueError('checkpoint publication validation failed')
            saved.append(dict(iteration=iteration, path=path.name, sha256=digest(path), bytes=path.stat().st_size,
                kind='resumable-endpoint' if iteration in (5000, 50000) else 'renderable-curve-with-training-state' if iteration in CURVE else 'recovery'))
            # Delete only an already validated, superseded recovery from this output.
            if recovery is not None:
                recovery.unlink()
            recovery = None if iteration in CURVE else path
            last_save = time.monotonic()
            del check
    write_new(a.output / 'worker-result.json', dict(iteration=iteration, target_update=a.target_update,
        completed=iteration == a.target_update, interrupted=stopping[0], checkpoints=saved,
        peak_allocated_bytes=torch.cuda.max_memory_allocated(), peak_reserved_bytes=torch.cuda.max_memory_reserved()))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--arm', choices=('stg-full', 'freetimegs-sparse', 'freetimegs-dense'), required=True)
    p.add_argument('--seed', type=int, choices=range(3), required=True)
    p.add_argument('--initialization', type=Path, default=ROOT / '.local/sync-pivot/basketball-static-init')
    p.add_argument('--dense-initialization', type=Path)
    p.add_argument('--resume', type=Path)
    p.add_argument('--target-update', type=int, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if not 0 < a.target_update <= 50000:
        p.error('absolute target must be in 1..50000')
    if a.arm != 'freetimegs-dense' and not a.resume:
        p.error('sparse arms must resume their historical parent')
    if a.arm == 'freetimegs-dense' and not a.dense_initialization:
        p.error('dense arm requires frozen initialization')
    import torch
    parent = None
    if a.resume:
        parent = torch.load(a.resume, map_location='cpu', weights_only=True)
        verify_files(parent['provenance']['files'])
        if parent['provenance']['seed'] != a.seed or parent['iteration'] >= a.target_update:
            raise ValueError('resume seed/absolute target mismatch')
        method = 'stg-full' if a.arm == 'stg-full' else 'freetimegs' if a.arm == 'freetimegs-sparse' else a.arm
        if parent['provenance']['method'] != method:
            raise ValueError('resume arm mismatch')
        if parent['iteration'] == 5000 and a.arm != 'freetimegs-dense':
            historical = json.loads((ROOT / 'docs/experiments/basketball-dense-temporal/preflight-001.json').read_text())
            expected = next(r for r in historical['parents'] if r['arm'] == method and r['seed'] == a.seed)
            if digest(a.resume) != expected['sha256']:
                raise ValueError('historical checkpoint hash mismatch')
    a.output = a.output.resolve()
    a.output.mkdir(parents=True, exist_ok=False)
    (a.output / 'study_adapter.py').write_bytes(Path(__file__).read_bytes())
    a.manifest = MANIFEST
    a.checkout = ROOT / ('.local/SpacetimeGaussians' if a.arm == 'stg-full' else '.local/FreeTimeGsVanilla')
    write_new(a.output / 'study-provenance.json', dict(plan=26, arm=a.arm, seed=a.seed,
        target_update=a.target_update, parent_sha256=digest(a.resume) if a.resume else None,
        adapter_sha256=digest(__file__), schedule='native-schedule extension, 30000-step position decay' if a.arm == 'stg-full' else 'native 70000-step schedule',
        curve_retention='intermediate complete renderable snapshots retain extra training state'))
    def deny(*_, **__):
        raise RuntimeError('network disabled in study training')
    socket.create_connection = deny
    socket.socket.connect = deny
    socket.socket.connect_ex = deny
    if a.arm == 'stg-full':
        train_stg(a, parent)
    else:
        train_free(a, parent)


if __name__ == '__main__':
    main()
