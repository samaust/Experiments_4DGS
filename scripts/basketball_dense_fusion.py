"""Deterministic Plan 027 measured-static fusion and initializer provenance."""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

from basketball_study import KEYFRAMES, ROOT, digest, training_key, verify_files, write_new
from basketball_dense_training import ARMS

AUTHORIZATION = 'frozen for experimental training with known visual defects'
NATIVE = ('positions', 'colors', 'velocities', 'times', 'durations')


def voxel_width(points):
    points = np.unique(np.asarray(points, dtype=np.float64), axis=0)
    if points.ndim != 2 or points.shape[1] != 3 or len(points) < 2 or not np.isfinite(points).all():
        raise ValueError('invalid historical static points')
    distances = cKDTree(points).query(points, k=2)[0][:, 1]
    positive = distances[distances > 0]
    if not len(positive):
        raise ValueError('no positive nearest-neighbor distances')
    return float(np.median(positive) / 2)


def fuse(positions, colors, width):
    """Lexicographic voxel order; mapping indexes each input observation's voxel."""
    positions, colors = np.asarray(positions), np.asarray(colors)
    if positions.shape != colors.shape or positions.ndim != 2 or positions.shape[1] != 3:
        raise ValueError('invalid static shapes')
    if not np.isfinite(positions).all() or not np.isfinite(colors).all() or not np.isfinite(width) or width <= 0:
        raise ValueError('invalid static values or voxel width')
    cells = np.floor(positions.astype(np.float64) / width)
    if np.any(np.abs(cells) >= 2**63):
        raise ValueError('voxel index overflow')
    voxels, mapping = np.unique(cells.astype(np.int64), axis=0, return_inverse=True)
    order = np.argsort(mapping, kind='stable')
    groups = np.split(order, np.flatnonzero(np.diff(mapping[order]))+1) if len(order) else []
    xyz = np.array([np.median(positions[g], axis=0) for g in groups], dtype=np.float32).reshape(-1, 3)
    rgb = np.array([np.median(colors[g], axis=0) for g in groups], dtype=np.float32).reshape(-1, 3)
    return xyz, rgb, mapping, voxels


def validate(arrays):
    count = len(arrays['positions'])
    if not count:
        raise ValueError('empty initialization')
    for key in NATIVE:
        value = arrays[key]
        shape = (count, 3 if key in NATIVE[:3] else 1)
        if value.shape != shape or value.dtype != np.float32 or not np.isfinite(value).all():
            raise ValueError('invalid native array: '+key)
    if np.any((arrays['colors'] < 0) | (arrays['colors'] > 1)):
        raise ValueError('invalid color range')
    if not np.allclose(arrays['durations'], .2, rtol=0, atol=1e-8):
        raise ValueError('invalid duration')
    if not np.isin(arrays['times'], np.array(KEYFRAMES, np.float32)/50).all():
        raise ValueError('invalid center or held-out frame')
    region, validity = arrays['region'], arrays['velocity_valid']
    if region.shape != (count,) or validity.shape != (count,) or validity.dtype != np.bool_ or not np.isin(region, [0, 1, 2]).all():
        raise ValueError('invalid region/velocity sidecar')
    if np.any(arrays['velocities'][(region == 0) | ~validity] != 0):
        raise ValueError('unmeasured or static velocity is nonzero')


def load_frozen(path, arm, normalization):
    record = json.loads((path/'result.json').read_text())
    if record['arm'] != arm or arm not in ARMS:
        raise ValueError('initializer recipe mismatch')
    if record['authorization'] != AUTHORIZATION or record['normalization'] != normalization:
        raise ValueError('initializer authorization/normalization mismatch')
    verify_files(record['files'])
    if digest(path/'initialization.npz') != record['archive_sha256']:
        raise ValueError('initializer hash mismatch')
    with np.load(path/'initialization.npz', allow_pickle=False) as archive:
        arrays = {key: archive[key].copy() for key in archive.files}
    validate(arrays)
    return arrays, record


def freeze(cloud, width_file, output, arm):
    config = json.loads((cloud/'config.json').read_text())
    result = json.loads((cloud/'result.json').read_text())
    width_record = json.loads(width_file.read_text())
    if result['status'] != 'geometry-generated-not-accepted' or digest(cloud/'config.json') != result['config_sha256']:
        raise ValueError('incomplete or changed geometry')
    expected_mode = 'coarse' if arm == ARMS[0] else 'person-cropped'
    if config['mode'] != expected_mode or config['frames'] != list(KEYFRAMES):
        raise ValueError('recipe or full-keyframe coverage mismatch')
    if config['normalization'] != width_record['normalization']:
        raise ValueError('normalization mismatch')
    verify_files(width_record['files'])
    chunks, sources, files = [], [], {str(width_file.resolve()): digest(width_file)}
    for name in ('config.json', 'result.json'):
        files[str((cloud/name).resolve())] = digest(cloud/name)
    for record in result['records']:
        training_key(record['reference'], record['frame'])
        training_key(record['reference'], record['frame']+1)
        if 'path' not in record:
            continue
        path = cloud/record['path']
        if digest(path) != record['sha256']:
            raise ValueError('observation hash mismatch')
        files[str(path.resolve())] = record['sha256']
        with np.load(path, allow_pickle=False) as data:
            chunk = {k: data[k].copy() for k in (*NATIVE, 'region', 'velocity_valid')}
            validate(chunk) if len(chunk['positions']) else None
            for camera in data['camera_ids']:
                training_key(int(camera), record['frame'])
            if not np.all(chunk['times'] == np.float32(record['frame']/50)):
                raise ValueError('observation time mismatch')
        sources.append(dict(path=str(path.resolve()), offset=sum(len(c['positions']) for c in chunks), count=len(chunk['positions'])))
        chunks.append(chunk)
    if not chunks or not sum(len(c['positions']) for c in chunks):
        raise ValueError('empty full cloud')
    observations = {k: np.concatenate([c[k] for c in chunks]) for k in chunks[0]}
    static = observations['region'] == 0
    xyz, rgb, mapping, voxels = fuse(observations['positions'][static], observations['colors'][static], width_record['width'])
    n, centers = len(xyz), np.array(KEYFRAMES, np.float32)/50
    arrays = dict(positions=np.tile(xyz, (9, 1)), colors=np.tile(rgb, (9, 1)),
        velocities=np.zeros((n*9, 3), np.float32), times=np.repeat(centers, n)[:, None],
        durations=np.full((n*9, 1), .2, np.float32), region=np.zeros(n*9, np.int64),
        velocity_valid=np.zeros(n*9, bool))
    arrays = {k: np.concatenate([v, observations[k][~static]]) for k, v in arrays.items()}
    arrays['physical_static_id'] = np.concatenate([np.tile(np.arange(n), 9), np.full((~static).sum(), -1)])
    arrays['foreground_observation_id'] = np.concatenate([np.full(n*9, -1), np.flatnonzero(~static)])
    validate(arrays)
    output.mkdir(parents=True, exist_ok=False)
    np.savez_compressed(output/'initialization.npz', **arrays)
    np.savez_compressed(output/'observation-mapping.npz', static_observation_id=np.flatnonzero(static),
        static_physical_id=mapping, voxels=voxels)
    write_new(output/'sources.json', sources)
    for name in ('observation-mapping.npz', 'sources.json'):
        files[str((output/name).resolve())] = digest(output/name)
    write_new(output/'result.json', dict(schema='basketball-dense-frozen/v1', arm=arm,
        method='freetimegs', authorization=AUTHORIZATION, visual_acceptance=False,
        normalization=config['normalization'], archive_sha256=digest(output/'initialization.npz'),
        physical_static_points=n, temporal_static_copies=n*9, foreground_observations=int((~static).sum()),
        total_gaussians=len(arrays['positions']), voxel_width=width_record['width'], files=files,
        identities='semantic regions and view-local labels only; not verified cross-camera identities',
        velocity_units='normalized scene coordinates per normalized time', adapter_sha256=digest(__file__)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    width = sub.add_parser('width')
    width.add_argument('--output', type=Path, required=True)
    assembly = sub.add_parser('freeze')
    for name in ('cloud', 'width-file', 'output'):
        assembly.add_argument('--'+name, type=Path, required=True)
    assembly.add_argument('--arm', choices=ARMS, required=True)
    a = parser.parse_args()
    if a.action == 'freeze':
        freeze(a.cloud, a.width_file, a.output, a.arm)
    else:
        cfg = ROOT/'.local/sync-pivot/runs/freetimegs-zero-seed0/worker/training-config.json'
        provenance = json.loads(cfg.with_name('checkpoint-provenance.json').read_text())
        if digest(cfg) != provenance['configuration_sha256']:
            raise ValueError('historical normalization changed')
        archive = ROOT/'.local/sync-pivot/basketball-static-init/static-cloud.npz'
        init = json.loads(archive.with_name('result.json').read_text())
        if digest(archive) != init['archive_sha256']:
            raise ValueError('historical static cloud changed')
        norm = json.loads(cfg.read_text())['normalization']
        transform = np.asarray(norm['transform'])
        with np.load(archive, allow_pickle=False) as data:
            xyz = (data['positions'] @ transform[:3, :3].T + transform[:3, 3]).astype(np.float32)
        xyz = xyz[np.linalg.norm(xyz, axis=1) < 5*norm['scene_scale']]
        write_new(a.output, dict(width=voxel_width(xyz), normalization=norm,
            unique_static_points=len(np.unique(xyz, axis=0)), rule='half median positive nearest-neighbor distance',
            files={str(p): digest(p) for p in (cfg, archive)}, adapter_sha256=digest(__file__)))


if __name__ == '__main__':
    main()
