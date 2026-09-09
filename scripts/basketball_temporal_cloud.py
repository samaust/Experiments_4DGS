"""Measured Plan 026 pilot geometry; no sparse duplication or synthetic court points."""
import argparse
import json
from pathlib import Path
import signal
import subprocess
import time

import cv2
import numpy as np
from PIL import Image
import torch

from basketball_study import CAMERAS, MANIFEST, ROOT, digest, training_key, verify_files, write_new
from basketball_temporal_geometry import geometry_gate, labels_at, project, projection, track_lk, velocity_from_support
from edgs_source import ROMA_PIN, ROMA_WEIGHTS, calibrated_projection, load_geometry, load_roma


def person_crop_warp(model, warp, confidence, image0, image1, labels0, labels1, phrases0, phrases1):
    """Refine person correspondences with exactly mapped crops; IDs are view-local."""
    uv0 = (warp[..., :2].reshape(-1, 2)+1)*[480, 270]
    uv1 = (warp[..., 2:].reshape(-1, 2)+1)*[480, 270]
    source_labels, target_labels = labels_at(labels0, uv0), labels_at(labels1, uv1)
    records = []
    for label, phrase in phrases0.items():
        label = int(label)
        if phrase != 'person' or not label:
            continue
        selected = np.flatnonzero(source_labels == label)
        votes = [(int(i), int((target_labels[selected] == i).sum())) for i in np.unique(target_labels[selected])
                 if phrases1.get(str(i)) == 'person' and i > 0]
        votes.sort(key=lambda x: (-x[1], x[0]))
        if not votes:
            records.append(dict(source_instance=label, rejection='no coarse person-region association'))
            continue
        other = votes[0][0]
        boxes = []
        for mask, instance in ((labels0, label), (labels1, other)):
            y, x = np.where(mask == instance)
            mx, my = max(2, int(np.ceil((x.max()-x.min()+1)*.1))), max(2, int(np.ceil((y.max()-y.min()+1)*.1)))
            boxes.append((max(0, int(x.min())-mx), max(0, int(y.min())-my),
                          min(960, int(x.max())+1+mx), min(540, int(y.max())+1+my)))
        crops = [Image.fromarray(im).crop(box) for im, box in zip((image0, image1), boxes)]
        with torch.inference_mode():
            refined, certainty = model.match(*crops, device='cuda')
        if not torch.isfinite(refined).all() or not torch.isfinite(certainty).all():
            raise RuntimeError('nonfinite person-cropped prediction')
        refined, certainty = refined.cpu().numpy(), certainty.cpu().numpy()
        x0, y0, x1, y1 = boxes[0]
        h, w = refined.shape[:2]
        grid = (uv0[selected]-[x0, y0])*[w/(x1-x0), h/(y1-y0)]-.5
        maps = [grid[:, i].astype(np.float32)[None] for i in (0, 1)]
        predicted = cv2.remap(refined[..., 2:], *maps, cv2.INTER_LINEAR)[0]
        tx0, ty0, tx1, ty1 = boxes[1]
        global_uv = (predicted+1)*[(tx1-tx0)/2, (ty1-ty0)/2]+[tx0, ty0]
        warp.reshape(-1, 4)[selected, 2:] = global_uv/[480, 270]-1
        confidence.reshape(-1)[selected] = cv2.remap(certainty, *maps, cv2.INTER_LINEAR)[0]
        records.append(dict(source_instance=label, target_instance=other, coarse_votes=votes,
                            source_box=boxes[0], target_box=boxes[1], refined_samples=len(selected)))
    return warp, confidence, records


def balanced_samples(confidence, labels, phrases, count, rng):
    probability = confidence.reshape(-1).copy()
    usable = np.isfinite(probability) & (probability > 0)
    selected = []
    people = [int(i) for i, phrase in phrases.items() if phrase == 'person' and int(i) > 0]
    active = [i for i in people if np.any(usable & (labels == i))]
    if active:
        quotas = np.full(len(active), (count//2)//len(active))
        quotas[:(count//2)%len(active)] += 1
        for label, quota in zip(active, quotas):
            ids = np.flatnonzero(usable & (labels == label))
            n = min(len(ids), int(quota))
            if n:
                selected.extend(rng.choice(ids, n, replace=False, p=probability[ids]/probability[ids].sum()))
    usable[selected] = False
    ids = np.flatnonzero(usable)
    n = min(count-len(selected), len(ids))
    if n:
        selected.extend(rng.choice(ids, n, replace=False, p=probability[ids]/probability[ids].sum()))
    return np.asarray(selected, dtype=int)


def query_warp(warp, uv):
    """Sample asymmetric RoMa warp at continuous full-image coordinates."""
    h, w = warp.shape[:2]
    grid = np.asarray(uv, np.float32)*[w/960, h/540]-.5
    out = cv2.remap(warp[..., 2:].astype(np.float32), grid[:, 0].astype(np.float32)[None],
                    grid[:, 1].astype(np.float32)[None], cv2.INTER_LINEAR,
                    borderMode=cv2.BORDER_CONSTANT, borderValue=float('nan'))[0]
    return (out+1)*[480, 270]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--masks', type=Path, required=True)
    p.add_argument('--neighbors', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--cropped', action='store_true')
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    masks = json.loads((a.masks / 'result.json').read_text())
    if masks['status'] != 'masks-generated':
        raise ValueError('mask prerequisite missing')
    verify_files({str(a.masks / name): h for name, h in masks['artifacts'].items()})
    mask_config = json.loads((a.masks / 'config.json').read_text())
    if digest(a.masks / 'config.json') != masks['config_sha256'] or digest(MANIFEST) != mask_config['manifest_sha256']:
        raise ValueError('mask provenance changed')
    observations = {(int(r['camera_id']), r['frame_id']): r for r in masks['observations']}
    neighbors = json.loads(a.neighbors.read_text())
    verify_files(neighbors['source_files'])
    manifest = json.loads(MANIFEST.read_text())
    cameras = {int(c['id']): c for c in manifest['cameras']}
    cfgpath = ROOT / '.local/sync-pivot/runs/freetimegs-zero-seed0/worker/training-config.json'
    provenance = json.loads(cfgpath.with_name('checkpoint-provenance.json').read_text())
    if digest(cfgpath) != provenance['configuration_sha256']:
        raise ValueError('sparse normalization changed')
    normalization = json.loads(cfgpath.read_text())['normalization']
    transform = np.array(normalization['transform'])
    edgs = ROOT / '.local/EDGS'
    edgs_pin = subprocess.check_output(['git', '-C', str(edgs), 'rev-parse', 'HEAD'], text=True).strip()
    if edgs_pin != 'f90b022445fc88368f75e66e8fb34aea88372cac' or subprocess.check_output(
            ['git', '-C', str(edgs), 'status', '--porcelain', '--untracked-files=no'], text=True):
        raise ValueError('EDGS source revision changed')
    native, source = load_geometry(edgs)
    roma = load_roma(ROOT / '.local/RoMa-edgs', ROOT / '.local/weights/roma-edgs')
    torch.manual_seed(0)
    rng = np.random.default_rng(0)
    stopping = [False]
    signal.signal(signal.SIGTERM, lambda *_: stopping.__setitem__(0, True))
    config = dict(schema='basketball-temporal-cloud/v1', normalization=normalization,
        mask_result_sha256=digest(a.masks / 'result.json'), neighbors_sha256=digest(a.neighbors),
        geometry_source=source, edgs_pin=edgs_pin, roma_pin=ROMA_PIN, roma_weights=ROMA_WEIGHTS,
        adapter_sha256=digest(__file__),
        geometry_adapter_sha256=digest(ROOT / 'scripts/basketball_temporal_geometry.py'),
        sampled_per_reference=15000, reprojection_pixels=2, angle_degrees=1,
        foreground_min_cameras=3, mode='person-cropped' if a.cropped else 'coarse', frames=mask_config['frames'])
    write_new(a.output / 'config.json', config)
    started = time.monotonic()
    records = []
    result = dict(status='incomplete', records=records)
    def image(c, f):
        _, f = training_key(c, f)
        entry = cameras[c]['frames'][f]
        path = MANIFEST.parent / entry['path']
        if digest(path) != entry['sha256']:
            raise ValueError('changed training image')
        return np.array(Image.open(path).convert('RGB'))
    def mask(c, f):
        training_key(c, f)
        return np.load(a.masks / f'camera{c}-frame{f}.npy', allow_pickle=False)
    try:
        for frame in mask_config['frames']:
            images = {c: image(c, frame) for c in CAMERAS}
            successor = {c: image(c, frame+1) for c in CAMERAS}
            labels = {c: mask(c, frame) for c in CAMERAS}
            next_labels = {c: mask(c, frame+1) for c in CAMERAS}
            changing = {c: np.load(a.masks / f'camera{c}-frame{frame}-changing.npy') for c in CAMERAS}
            for ref in CAMERAS:
                if stopping[0]:
                    raise InterruptedError('cloud worker interrupted')
                others = neighbors['neighbors'][str(ref)]
                if len(others) != 3:
                    records.append(dict(frame=frame, reference=ref, rejection='fewer than three overlap neighbors'))
                    continue
                ids = [ref]+others
                warps, candidates = {}, []
                P = np.array([projection(cameras[c]) for c in ids])
                centers = np.array([cameras[c]['center'] for c in ids])
                for j, other in enumerate(others):
                    with torch.inference_mode():
                        warp, confidence = roma.match(Image.fromarray(images[ref]), Image.fromarray(images[other]), device='cuda')
                    if not torch.isfinite(warp).all() or not torch.isfinite(confidence).all():
                        raise RuntimeError('nonfinite RoMa prediction')
                    w = warp.cpu().numpy()
                    prob = confidence.cpu().numpy()
                    if a.cropped:
                        w, prob, crop_records = person_crop_warp(roma, w, prob, images[ref], images[other],
                            labels[ref], labels[other], observations[ref, frame]['phrases'], observations[other, frame]['phrases'])
                        write_new(a.output / f'crops-frame{frame}-ref{ref}-other{other}.json', crop_records)
                    warps[other] = w
                    uv0 = (w[..., :2].reshape(-1, 2)+1)*[480, 270]
                    prob = prob.reshape(-1)
                    prob[prob > roma.sample_thresh] = 1
                    sampled = balanced_samples(prob, labels_at(labels[ref], uv0), observations[ref, frame]['phrases'], 5000, rng)
                    uv1 = (w[..., 2:].reshape(-1, 2)[sampled]+1)*[480, 270]
                    candidates.append((j+1, uv0[sampled], uv1))
                for pair, uv0, uv1 in candidates:
                    other = ids[pair]
                    Ps = []
                    for c in (ref, other):
                        extrinsic = torch.eye(4)
                        extrinsic[:3, :3] = torch.tensor(cameras[c]['world_to_camera_R'])
                        extrinsic[:3, 3] = torch.tensor(cameras[c]['world_to_camera_T'])
                        Ps.append(calibrated_projection(torch.tensor(cameras[c]['K']), extrinsic).cuda())
                    u0, u1 = torch.tensor(uv0, device='cuda', dtype=torch.float32), torch.tensor(uv1, device='cuda', dtype=torch.float32)
                    xyz, _, _ = native['triangulate_points'](Ps[0], Ps[1], u0[:, 0], u0[:, 1], u1[:, 0], u1[:, 1], device='cuda')
                    xyz = xyz[:, :3].cpu().numpy()
                    good, diagnostics = geometry_gate(xyz, [uv0, uv1], P[[0, pair]], centers[[0, pair]])
                    all_uv = np.array([uv0]+[uv1 if c == other else query_warp(warps[c], uv0) for c in others])
                    sampled_labels = np.array([labels_at(labels[c], uv) for c, uv in zip(ids, all_uv)])
                    semantic = np.zeros_like(sampled_labels)
                    for k, c in enumerate(ids):
                        for label, phrase in observations[c, frame]['phrases'].items():
                            semantic[k, sampled_labels[k] == int(label)] = {'person': 1, 'basketball': 2}.get(phrase, 0)
                    region = semantic[0]
                    support = np.zeros((4, len(xyz)), bool)
                    for k in range(4):
                        projected, depth = project(xyz, P[k])
                        support[k] = np.isfinite(projected).all(1) & (depth > 0) & (np.linalg.norm(projected-all_uv[k], axis=1) <= 2)
                        support[k] &= (semantic[k] == region) & (sampled_labels[k] >= 0)
                    foreground = region > 0
                    good &= support[0] & support[pair]
                    good &= ~foreground | (support.sum(0) >= 3)
                    static = ~foreground
                    for k in (0, pair):
                        good &= ~static | (labels_at(changing[ids[k]], all_uv[k]) == 0)
                    kept = np.flatnonzero(good)
                    X, UV, support = xyz[kept], all_uv[:, kept], support[:, kept]
                    region_kept = region[kept]
                    velocities = np.zeros_like(X)
                    measured = np.zeros(len(X), bool)
                    fg = np.flatnonzero(region_kept > 0)
                    if len(fg):
                        ends, valid = [], []
                        for k, c in enumerate(ids):
                            end, ok = track_lk(images[c], successor[c], UV[k, fg], labels[c], next_labels[c])
                            ends.append(end)
                            valid.append(ok & support[k, fg])
                        velocities[fg], measured[fg] = velocity_from_support(X[fg], np.array(ends), P, centers,
                            np.array(valid), ids, transform, manifest['time']['duration_seconds'])
                    normalized = X @ transform[:3, :3].T + transform[:3, 3]
                    xy = np.floor(uv0[kept]).astype(int)
                    colors = images[ref][xy[:, 1].clip(0, 539), xy[:, 0].clip(0, 959)]/255.
                    archive = a.output / f'frame{frame}-ref{ref}-other{other}.npz'
                    np.savez_compressed(archive, positions=normalized.astype(np.float32), world_positions=X,
                        colors=colors.astype(np.float32), velocities=velocities.astype(np.float32),
                        times=np.full((len(X), 1), frame/50, np.float32), durations=np.full((len(X), 1), .2, np.float32),
                        region=region_kept, velocity_valid=measured, camera_ids=np.array(ids), uv=UV,
                        support=support, instance_labels=sampled_labels[:, kept])
                    record = dict(frame=frame, reference=ref, other=other, sampled=len(xyz), retained=len(X),
                        static=int((region_kept == 0).sum()), person=int((region_kept == 1).sum()), ball=int((region_kept == 2).sum()),
                        measured_velocity=int(measured.sum()), unsupported_velocity=int(((region_kept > 0) & ~measured).sum()),
                        rejected_geometry=int((~geometry_gate(xyz, [uv0, uv1], P[[0, pair]], centers[[0, pair]])[0]).sum()),
                        rejected_person=int(((region == 1) & ~good).sum()), rejected_ball=int(((region == 2) & ~good).sum()),
                        path=archive.name, sha256=digest(archive))
                    records.append(record)
                    with (a.output / 'records.jsonl').open('a') as stream:
                        stream.write(json.dumps(record)+'\n')
                print(json.dumps(dict(frame=frame, reference=ref, seconds=time.monotonic()-started)), flush=True)
            del images, successor
        result['status'] = 'geometry-generated-not-accepted'
    except BaseException as error:
        result['error'] = f'{type(error).__name__}: {error}'
        raise
    finally:
        result['wall_seconds'] = time.monotonic()-started
        result['peak_allocated_bytes'] = torch.cuda.max_memory_allocated()
        result['config_sha256'] = digest(a.output / 'config.json')
        write_new(a.output / 'result.json', result)


if __name__ == '__main__':
    main()
