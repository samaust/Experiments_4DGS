"""Plan 028 policy-aware FreeTimeGS continuation adapter.

This file is intentionally separate from the Plan 027 adapter so historical
checkpoint source bindings remain valid.
"""
import argparse
import json
from pathlib import Path
import random
import signal
import socket
import time

from basketball_study import CURVE, MANIFEST, ROOT, digest, verify_files, write_new
from basketball_dense_training import ARMS
from basketball_crossing_repair import (policy_record, project_duration_parameter_,
    resolve_duration_target, training_key_hash)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arm', choices=ARMS, required=True)
    parser.add_argument('--seed', type=int, choices=range(3), required=True)
    parser.add_argument('--initialization', type=Path, default=ROOT/'.local/sync-pivot/basketball-static-init')
    parser.add_argument('--dense-initialization', type=Path, required=True)
    parser.add_argument('--resume', type=Path)
    parser.add_argument('--target-update', type=int, required=True)
    parser.add_argument('--training-policy', choices=('holdout', 'all-times'), required=True)
    parser.add_argument('--lifetime-policy', choices=('original', 'repaired'), required=True)
    parser.add_argument('--output', type=Path, required=True)
    a = parser.parse_args()
    if not 0 < a.target_update <= 70000:
        parser.error('absolute target must be in 1..70000')
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

    parent = None
    if a.resume:
        parent = torch.load(a.resume, map_location='cpu', weights_only=True)
        verify_files(parent['provenance']['files'])
        if (parent['provenance'].get('method') != 'freetimegs' or
                parent['provenance'].get('arm') != a.arm or parent['provenance'].get('seed') != a.seed or
                parent['iteration'] >= a.target_update):
            raise ValueError('resume parent recipe, seed, or absolute target mismatch')
        if parent['provenance'].get('plan') == 28 and (
                parent['provenance'].get('training_policy') != a.training_policy or
                parent['provenance'].get('lifetime_policy') != a.lifetime_policy):
            raise ValueError('resume policy does not match branch provenance')
    a.output = a.output.resolve()
    a.output.mkdir(parents=True, exist_ok=False)
    (a.output/'study_adapter.py').write_bytes(Path(__file__).read_bytes())
    a.checkout = ROOT/'.local/FreeTimeGsVanilla'
    write_new(a.output/'study-provenance.json', dict(plan=28, method='freetimegs', arm=a.arm, seed=a.seed,
        training_policy=a.training_policy, lifetime_policy=a.lifetime_policy,
        target_update=a.target_update, parent_sha256=digest(a.resume) if a.resume else None,
        adapter_sha256=digest(__file__), schedule='absolute native 70000-step schedule; relocation ends at 63000'))

    random.seed(a.seed); np.random.seed(a.seed); torch.manual_seed(a.seed); torch.cuda.manual_seed_all(a.seed)
    torch.hub.set_dir(str(ROOT/'.local/cache/torch/hub'))
    cfg, _, _ = load_training(a.checkout)
    cfg.start_frame, cfg.end_frame = 0, 50
    initializer_record = json.loads((a.dense_initialization/'result.json').read_text())
    target = resolve_duration_target(initializer_record) if a.lifetime_policy == 'repaired' else None
    if target is not None:
        cfg.init_duration = target
    scene, data, normalization = prepare_free(FreeTimeBasketballScene(MANIFEST), a.initialization, a.checkout)
    from basketball_dense_fusion import load_frozen, NATIVE
    arrays, frozen = load_frozen(a.dense_initialization, a.arm, normalization)
    data = {key: torch.from_numpy(arrays[key]) for key in NATIVE}
    provenance = dict(plan=28, method='freetimegs', arm=a.arm, seed=a.seed,
        training_policy=a.training_policy, lifetime_policy=a.lifetime_policy,
        policy=policy_record(a.training_policy, a.lifetime_policy, target or .2),
        initializer_sha256=frozen['archive_sha256'], files={str(p.resolve()): digest(p) for p in (
            MANIFEST, a.dense_initialization/'result.json', Path(__file__),
            ROOT/'scripts/basketball_dense_fusion.py', ROOT/'scripts/freetimegs_checkpoint.py',
            ROOT/'scripts/freetimegs_model.py', ROOT/'scripts/freetimegs_training.py',
            ROOT/'scripts/basketball_native_train.py', ROOT/'scripts/basketball_crossing_repair.py')})
    lpips = LearnedPerceptualImagePatchSimilarity(net_type='alex', normalize=True).cuda()
    model = NativeFreeTimeModel(a.checkout, cfg, data, scene_scale=normalization['scene_scale'], device='cuda')
    model.enable_training(a.checkout, scene_scale=normalization['scene_scale'], device='cuda', lpips=lpips)
    del data
    if a.training_policy == 'all-times':
        scene._training_keys = [(camera, frame) for camera in sorted(scene.cameras)
                                if camera not in {'0', '10', '20', '30'} for frame in range(50)]
    sampler = ManifestBalancedSampler(scene, 1, seed=a.seed)
    provenance['training_key_sha256'] = training_key_hash(scene.training_keys())
    iteration = 0
    if a.resume:
        # Plan 027 encoded the sentinel in its config.  Recreate that config
        # only for restoration; the declared repair is applied after restore.
        restore_sentinel = a.lifetime_policy == 'repaired' and parent['provenance'].get('plan') == 27
        if restore_sentinel:
            cfg.init_duration = -1.0
        iteration, loop = restore_checkpoint(a.resume, model, provenance=parent['provenance'])
        save_checkpoint(a.output/'restored-parent.pt', model, iteration=iteration,
                        loop_state={'sampler': loop['sampler']}, provenance=parent['provenance'])
        from basketball_study_resume_check import differences
        restored = torch.load(a.output/'restored-parent.pt', map_location='cpu', weights_only=True)
        changed = differences(parent, restored)
        write_new(a.output/'restore-validation.json', dict(passed=not changed, differences=changed))
        if changed:
            raise ValueError('saved-state restoration mismatch: '+str(changed[:10]))
        sampler = ManifestBalancedSampler(scene, 1, seed=a.seed)
        if restore_sentinel:
            cfg.init_duration = target
    configuration = dict(native=asdict(cfg), normalization=normalization,
                         training_policy=a.training_policy, lifetime_policy=a.lifetime_policy)
    write_new(a.output/'training-config.json', configuration)
    provenance['configuration_sha256'] = digest(a.output/'training-config.json')
    write_new(a.output/'checkpoint-provenance.json', provenance)
    if a.lifetime_policy == 'repaired':
        write_new(a.output/'initial-duration-projection.json',
                  project_duration_parameter_(model.splats['durations'], model.optimizers['durations']))
    stopping = [False]
    signal.signal(signal.SIGTERM, lambda *_: stopping.__setitem__(0, True))
    started = time.monotonic(); last_save = started; saved = []
    while iteration < a.target_update and not stopping[0]:
        camera = scene.training_camera(next(sampler), device='cuda')
        metrics = model.training_step(iteration, camera, model.schedulers)
        torch.cuda.synchronize(); iteration += 1
        metrics = {k: float(v.detach()) if isinstance(v, torch.Tensor) else v for k, v in metrics.items()}
        if a.lifetime_policy == 'repaired':
            metrics['duration_projection_changed'] = project_duration_parameter_(
                model.splats['durations'], model.optimizers['durations'])['changed_entries']
        if not np.isfinite(metrics['loss']):
            raise RuntimeError('nonfinite native loss')
        with (a.output/'loss.jsonl').open('a') as stream:
            stream.write(json.dumps(dict(iteration=iteration, elapsed_seconds=time.monotonic()-started,
                                         **metrics))+'\n')
        if iteration in CURVE or iteration in (63000, 70000) or time.monotonic()-last_save >= 300:
            path = a.output/f'checkpoint-{iteration:06d}.pt'
            save_checkpoint(path, model, iteration=iteration,
                            loop_state={'sampler': sampler.state_dict()}, provenance=provenance)
            saved.append(dict(iteration=iteration, path=path.name, sha256=digest(path), bytes=path.stat().st_size))
            last_save = time.monotonic()
    write_new(a.output/'worker-result.json', dict(iteration=iteration, target_update=a.target_update,
        completed=iteration == a.target_update, interrupted=stopping[0], checkpoints=saved,
        peak_allocated_bytes=torch.cuda.max_memory_allocated(), peak_reserved_bytes=torch.cuda.max_memory_reserved()))


if __name__ == '__main__':
    main()
