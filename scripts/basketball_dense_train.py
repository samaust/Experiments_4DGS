"""Plan 027 native dense training with explicit recipe and initializer identity."""
import argparse
import json
import os
from pathlib import Path
import signal
import socket
import time
from basketball_study import CURVE, MANIFEST, ROOT, digest, verify_files, write_new
from basketball_dense_training import ARMS


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
    from basketball_dense_fusion import load_frozen, NATIVE
    arrays, frozen = load_frozen(a.dense_initialization, a.arm, normalization)
    data = {k: torch.from_numpy(arrays[k]) for k in NATIVE}
    del arrays
    provenance = dict(plan=27, method='freetimegs', arm=a.arm, seed=a.seed,
        initializer_sha256=frozen['archive_sha256'],
        files={str(p.resolve()): digest(p) for p in (
            MANIFEST, a.dense_initialization/'result.json', Path(__file__),
            ROOT/'scripts/basketball_dense_fusion.py',
            ROOT/'scripts/freetimegs_checkpoint.py', ROOT/'scripts/freetimegs_model.py',
            ROOT/'scripts/freetimegs_training.py', ROOT/'scripts/basketball_native_train.py')})
    configuration = dict(native=asdict(cfg), normalization=normalization)
    write_new(a.output/'training-config.json', configuration)
    provenance['configuration_sha256'] = digest(a.output/'training-config.json')
    if parent and parent['provenance'] != provenance:
        raise ValueError('resume recipe, initializer, seed, native configuration or source mismatch')
    write_new(a.output/'checkpoint-provenance.json', provenance)
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
    if parent:
        from basketball_study_resume_check import differences
        restored = torch.load(a.output/'restored-parent.pt', map_location='cpu', weights_only=True)
        changed = differences(parent, restored)
        write_new(a.output/'restore-validation.json', dict(passed=not changed, differences=changed,
            qualification='exact saved-state restoration; GPU training is not bitwise reproducible'))
        if changed:
            raise ValueError('saved-state restoration mismatch: '+str(changed[:10]))
        del restored
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
    p.add_argument('--arm', choices=ARMS, required=True)
    p.add_argument('--seed', type=int, choices=range(3), required=True)
    p.add_argument('--initialization', type=Path, default=ROOT/'.local/sync-pivot/basketball-static-init')
    p.add_argument('--dense-initialization', type=Path, required=True)
    p.add_argument('--resume', type=Path)
    p.add_argument('--target-update', type=int, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if not 0 < a.target_update <= 50000:
        p.error('absolute target must be in 1..50000')
    import torch
    parent = None
    if a.resume:
        parent = torch.load(a.resume, map_location='cpu', weights_only=True)
        verify_files(parent['provenance']['files'])
        if (parent['provenance']['seed'] != a.seed or parent['provenance'].get('arm') != a.arm
                or parent['provenance']['method'] != 'freetimegs' or parent['iteration'] >= a.target_update):
            raise ValueError('resume recipe/seed/absolute target mismatch')
    a.output = a.output.resolve()
    a.output.mkdir(parents=True, exist_ok=False)
    (a.output/'study_adapter.py').write_bytes(Path(__file__).read_bytes())
    a.checkout = ROOT/'.local/FreeTimeGsVanilla'
    write_new(a.output/'study-provenance.json', dict(plan=27, arm=a.arm, method='freetimegs', seed=a.seed,
        target_update=a.target_update, parent_sha256=digest(a.resume) if a.resume else None,
        adapter_sha256=digest(__file__), schedule='native 70000-step schedule'))
    def deny(*_, **__):
        raise RuntimeError('network disabled in study training')
    socket.create_connection = deny
    socket.socket.connect = deny
    socket.socket.connect_ex = deny
    train_free(a, parent)


if __name__ == '__main__':
    main()
