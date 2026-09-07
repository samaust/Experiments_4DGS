"""Revision-one bounded recovery configuration and immutable database reconstruction."""
import argparse
import json
from pathlib import Path
import sqlite3
import time
import tempfile

import numpy as np
from basketball_audit import sha256
from basketball_geometry import opencv_to_colmap
from basketball_protocol import TRAINING, PROTOCOL

POLICIES = ('fixed-principal', 'fixed-intrinsics')
EARLY = (50, 62, 75, 87, 99)
LATE = (100, 112, 125, 137, 149)


def search_manifest():
    stages = {}
    for stage, recipes in [('A', ('sift', 'dense')), ('B', ('sharp-sift', 'sharp-dsp', 'sharp-dsp-roma95', 'sharp-dsp-roma90')),
                           ('C', ('initial-pair-1', 'initial-pair-2'))]:
        stages[stage] = [dict(id=f'{stage}-{policy}-{recipe}', policy=policy, recipe=recipe)
                         for policy in POLICIES for recipe in recipes]
    return dict(schema='basketball-recovery-search/v1', protocol=PROTOCOL, stages=stages,
                max_independent_runs=32, max_pooled_runs=8, early_frames=EARLY, late_frames=LATE,
                mapping_seconds=600, adjustment_seconds=120, seed=0,
                original_gpu_limit_seconds=28800, downstream_only_extension_seconds=28800)


def native_options(colmap, policy, initial_pair=None):
    if policy not in POLICIES:
        raise ValueError('unknown intrinsic policy')
    free_focal = policy == 'fixed-principal'
    mapper = colmap.IncrementalPipelineOptions(num_threads=8, random_seed=0, min_model_size=3,
        max_num_models=3, ba_refine_focal_length=free_focal, ba_refine_principal_point=False,
        ba_refine_extra_params=False, max_runtime_seconds=600, extract_colors=False)
    mapper.mapper.abs_pose_refine_focal_length = free_focal
    mapper.mapper.abs_pose_refine_extra_params = False
    if initial_pair is not None:
        if len(set(initial_pair)) != 2 or any(c not in TRAINING for c in initial_pair):
            raise ValueError('initial pair must contain two training cameras')
        mapper.init_image_id1, mapper.init_image_id2 = (c + 1 for c in initial_pair)
    ba = colmap.BundleAdjustmentOptions(refine_focal_length=free_focal,
                                        refine_principal_point=False, refine_extra_params=False)
    ba.ceres.loss_function_type = colmap.LossFunctionType.SOFT_L1
    ba.ceres.loss_function_scale = 1.
    options = ba.ceres.solver_options
    options.num_threads = 8
    options.max_num_iterations = 1000
    options.max_solver_time_in_seconds = 120
    options.function_tolerance = options.gradient_tolerance = options.parameter_tolerance = 1e-8
    absolute = colmap.AbsolutePoseRefinementOptions(refine_focal_length=free_focal, refine_extra_params=False)
    return mapper, ba, absolute


def window_intrinsics(priors, frames):
    if not frames or len(set(frames)) != len(frames) or any(f < 50 or f >= 150 for f in frames):
        raise ValueError('unique fitting frames required')
    entries = [e for e in priors['observations'] if e['source_frame_id'] in frames and e['camera_id'] in TRAINING]
    expected = {(c, f) for c in TRAINING for f in frames}
    if {(e['camera_id'], e['source_frame_id']) for e in entries} != expected or len(entries) != len(expected):
        raise ValueError('missing or duplicate training-window priors')
    return {c: opencv_to_colmap(np.median([e['K_960x540'] for e in entries if e['camera_id'] == c], axis=0))
            for c in TRAINING}


def check_fixed(before, after, policy):
    start = 2 if policy == 'fixed-principal' else 0
    if not np.allclose(before[start:], after[start:], atol=1e-10, rtol=0):
        raise ValueError(f'fixed intrinsic parameters changed under {policy}')


def subset_database(colmap, source, target, Ks):
    """Copy only retained training observations; never mutate historical databases."""
    from basketball_static_rig import register_image
    digest = sha256(source)
    # Native Database.open updates SQLite metadata even for read-only method calls.
    # Open a SQLite read-only backup instead, preserving historical file hashes.
    with tempfile.TemporaryDirectory(dir=target.parent) as temporary:
        snapshot = Path(temporary) / 'source.db'
        with sqlite3.connect(f'file:{source.resolve()}?mode=ro', uri=True) as old_sql, sqlite3.connect(snapshot) as copied_sql:
            old_sql.backup(copied_sql)
        _copy_subset(colmap, snapshot, target, Ks, register_image)
    if sha256(source) != digest:
        raise ValueError('historical source database changed')


def _copy_subset(colmap, source, target, Ks, register_image):
    with colmap.Database.open(source) as old, colmap.Database.open(target) as new:
        available = {im.camera_id - 1 for im in old.read_all_images()}
        if not set(TRAINING) <= available:
            raise ValueError('source is missing retained training cameras')
        for c in TRAINING:
            register_image(new, colmap, camera_id=c+1, image_id=c+1, name=f'camera{c}.png', K=Ks[c])
            new.write_keypoints(c+1, old.read_keypoints(c+1))
            if old.exists_descriptors(c+1):
                new.write_descriptors(c+1, old.read_descriptors(c+1))
        for i, c in enumerate(TRAINING):
            for other in TRAINING[i+1:]:
                if old.exists_matches(c+1, other+1):
                    new.write_matches(c+1, other+1, old.read_matches(c+1, other+1))
                if old.exists_two_view_geometry(c+1, other+1):
                    new.write_two_view_geometry(c+1, other+1, old.read_two_view_geometry(c+1, other+1))


def reconstruct(source, priors_path, output, frames, policy, initial_pair=None):
    import pycolmap as colmap
    if colmap.__version__ != '4.2.0':
        raise ValueError('requires pinned PyCOLMAP 4.2.0')
    priors = json.loads(priors_path.read_text())
    if priors['status'] != 'priors-generated' or priors['blockers']:
        raise ValueError('requires passing priors')
    Ks = window_intrinsics(priors, frames)
    mapper, ba, absolute = native_options(colmap, policy, initial_pair)
    output.mkdir(exist_ok=False)
    dbpath = output / 'merged.db'
    subset_database(colmap, source / 'merged.db', dbpath, Ks)
    before = {}
    with colmap.Database.open(dbpath) as db:
        if sorted(im.camera_id - 1 for im in db.read_all_images()) != list(TRAINING):
            raise ValueError('source must contain exactly the retained training cameras')
        for c in TRAINING:
            K = Ks[c]
            camera = db.read_camera(c + 1)
            if camera.model_name != 'PINHOLE':
                raise ValueError('revision one requires PINHOLE')
            camera.params = [K[0, 0], K[1, 1], K[0, 2], K[1, 2]]
            camera.has_prior_focal_length = True
            db.update_camera(camera)
            before[c] = camera.params.copy()
    images = output / 'merged-images'
    images.mkdir()
    for c in TRAINING:
        (images / f'camera{c}.png').symlink_to((source / 'merged-images' / f'camera{c}.png').resolve())
    config = dict(schema='basketball-recovery-run/v1', protocol=PROTOCOL, policy=policy,
                  frames=frames, initial_pair=initial_pair, source=str(source),
                  source_database_sha256=sha256(source / 'merged.db'), priors_sha256=sha256(priors_path),
                  adapter_sha256=sha256(__file__), mapping_options=mapper.todict(),
                  adjustment_options=ba.todict(), absolute_options=absolute.todict())
    (output / 'config.json').write_text(json.dumps(config, indent=2, default=str) + '\n')
    report = dict(schema='basketball-static-rig-result/v1', protocol=PROTOCOL, status='blocked',
                  blockers=[], models=[], config_sha256=sha256(output / 'config.json'))
    started = time.monotonic()
    try:
        colmap.set_random_seed(0)
        models = colmap.incremental_mapping(dbpath, images, output / 'sparse', options=mapper)
        for index, model in models.items():
            # Check after mapping as well as after final adjustment.
            for c in model.cameras:
                check_fixed(before[c - 1], model.camera(c).params, policy)
            colmap.bundle_adjustment(model, options=ba)
            intrinsics = {}
            for c in model.cameras:
                final = model.camera(c).params
                check_fixed(before[c - 1], final, policy)
                intrinsics[str(c - 1)] = dict(prior=before[c - 1].tolist(), final=final.tolist())
            model.write(output / 'sparse' / str(index))
            registered = sorted(im.camera_id - 1 for im in model.images.values() if im.has_pose)
            report['models'].append(dict(model_id=index, cameras=registered, points=model.num_points3D(),
                mean_reprojection_error=model.compute_mean_reprojection_error(), intrinsics=intrinsics))
        complete = [m for m in report['models'] if m['cameras'] == list(TRAINING)]
        if len(complete) != 1:
            report['blockers'].append('no unique complete training reconstruction')
        else:
            report.update(status='candidate-rig', model_id=complete[0]['model_id'])
    except BaseException as error:
        report['blockers'].append(f'{type(error).__name__}: {error}')
        raise
    finally:
        report['wall_seconds'] = time.monotonic() - started
        (output / 'result.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--priors', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--frames', nargs='+', type=int, required=True)
    p.add_argument('--policy', choices=POLICIES, required=True)
    p.add_argument('--initial-pair', nargs=2, type=int)
    a = p.parse_args()
    return reconstruct(a.source, a.priors, a.output, a.frames, a.policy, a.initial_pair)['status'] != 'candidate-rig'


if __name__ == '__main__':
    raise SystemExit(main())
