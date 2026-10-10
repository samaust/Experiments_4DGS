"""Build the 70k-step, crossing-repaired, LPIPS-history-fixed D8 production (006) and QUALIFY (005) REVIEW requests (#34).

The settings equal review-002 except the 70,000-step endpoint, its allocations, a
20 GiB device limit (2 GiB headroom for desktop display memory) and
the v2 cap extension (380 GiB artifacts, 288,000 GPU-s, 66,000 CPU-s), the 14,400 s train ceiling (LPIPS history released each update) and the documented crossing repair (all-times training, repaired durations). The scene freeze and voxel
basis are reused from review-002.

Writes scene-freeze.json, proposal.json and request.json into this folder, then
runs extended_final_render_contract.admit_review against the live ledger. It
creates no ledger event and grants no setup, GPU, training or render authority.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'scripts'))

from vipe_benchmark.files import file_record, object_hash, read_json, write_json  # noqa: E402
from vipe_benchmark import extended_final_render_contract as contract  # noqa: E402
from vipe_benchmark.final_render_contract import FROZEN_SCOPE, PRESET_SOURCE, PROCESSED_MANIFEST, TRAINING_CAMERAS, allocation_specs  # noqa: E402

ITERATIONS = 70000
SHARED = Path(__file__).resolve().parent.parent/'plan069-final-render-review-002'
from vipe_benchmark.ledger import Ledger  # noqa: E402

RUN = Path('/home/auss/git_repos/samaust/Experiments_4DGS/.local/vipe-alternatives/plan031-20260913T032700Z')
REPO = Path('/home/auss/git_repos/samaust/Experiments_4DGS')
HERE = Path(__file__).resolve().parent
STATIC = REPO/'.local/sync-pivot/basketball-static-init'
RUNTIME = ROOT/'docs/research/vipe-alternatives/plan069-final-render-runtime-004/gs-runtime.json'


def build(qualification, identity):
    import numpy as np
    decision_record = file_record(RUN / 'reviews/plan069-depth-comparison-002/decision.json')
    decision = read_json(decision_record['path'])
    candidate = decision['selected_candidate_ids'][0]
    evidence = decision['engineering_eligibility'][candidate]['evidence']
    inputs = read_json(evidence['inputs']['path'])
    reference = inputs['reference_geometry']
    fit = read_json(evidence['fit']['path'])
    factor = fit['scale'] / reference['scale']
    matrix = np.asarray(reference['normalization']['transform'], dtype=np.float64)
    matrix[:, :3] /= factor
    normalization = dict(transform=matrix.tolist())
    # Static voxel basis: the accepted frame-25 static prior in normalized D8
    # coordinates, filtered exactly as final_render_initializer.assemble checks.
    origin = read_json(STATIC/'result.json')
    assert origin['freeze_sha256'] == reference['freeze']['sha256']
    with np.load(STATIC/'static-cloud.npz', allow_pickle=False) as prior:
        positions = prior['positions']
    normalized = (positions*(fit['scale']/reference['scale']) @ matrix[:3, :3].T + matrix[:3, 3]).astype(np.float32)
    normalized = normalized[np.linalg.norm(normalized, axis=1) < 5*reference['normalization']['scene_scale']]
    basis_path = SHARED/'voxel-basis.npz'  # shared with review-002
    if not basis_path.exists():
        with basis_path.open('xb') as stream:
            np.savez(stream, normalized_positions=normalized)
    with np.load(basis_path, allow_pickle=False) as stored:
        assert np.array_equal(stored['normalized_positions'], normalized)
    voxel_basis = file_record(basis_path)
    voxel_source = dict(archive=file_record(STATIC/'static-cloud.npz'), receipt=file_record(STATIC/'result.json'))
    manifest_record = file_record(REPO / PROCESSED_MANIFEST[0])
    manifest = read_json(manifest_record['path'])
    cameras = {}
    for camera in manifest['cameras']:
        if int(camera['id']) not in TRAINING_CAMERAS:
            continue
        K = np.asarray(camera['K'], dtype=np.float64).copy()
        K[:2, 2] -= .5
        cameras[camera['id']] = dict(K=K.tolist(), R=camera['world_to_camera_R'],
            t=(np.asarray(camera['world_to_camera_T']) * factor).tolist(),
            center=(np.asarray(camera['center']) * factor).tolist())
    scene = dict(schema='plan069-final-render-scene/v1', status='complete', depth_component=candidate,
        scale=fit['scale'], scale_evidence=dict(fit=evidence['fit'], check=evidence['check']),
        normalization=matrix.tolist(), historical_reference=reference, map=inputs['map'],
        units=dict(normalized_time_seconds=2., frame_seconds=.04,
                   velocity='metres/second -> normalization linear map * 2 seconds'),
        cameras=cameras, physical_rescaling_factor=factor,
        derivation='Historical reference geometry rescaled from its camera scale to the frozen D8 fit scale; rotation and normalized coordinates preserved.')
    scene_path = SHARED/'scene-freeze.json'  # shared with review-002
    if not scene_path.exists():
        write_json(scene_path, scene)
    assert read_json(scene_path) == scene
    s2 = file_record(RUN / 'jobs/S2-reconstruction-recovery-001/result.json')
    bindings = dict(
        source=file_record(ROOT / 'scripts/vipe_benchmark/extended_final_render_contract.py'),
        preset=file_record(REPO / '.local/FreeTimeGsVanilla/src/simple_trainer_freetime_4d_pure_relocation.py'),
        runtime=file_record(RUNTIME),
        config=file_record(REPO / 'configs/vipe-alternatives/benchmark-v1.json'),  # historical worker/qualification binding
        qualification=file_record(qualification), scene_manifest=manifest_record,
        scene_freeze=file_record(scene_path), inputs=evidence['inputs'],
        segmentation_decision=file_record(ROOT / FROZEN_SCOPE['segmentation_decision'][0]),
        depth_decision=decision_record, S2=s2, D_fit=evidence['fit'], D_check=evidence['check'],
        **{name: file_record(RUN / 'jobs' / name / 'result.json') for name in ('M0', 'M1', 'M2', 'N0', 'N1', 'N2')})
    assert bindings['preset']['sha256'] == PRESET_SOURCE
    request = dict(schema=contract.SCHEMA, record_kind='actual', mode='REVIEW', id=identity,
        depth_candidate=candidate, compositions=contract.compositions(candidate), seed=0, iterations=ITERATIONS,
        training_policy='all-times', lifetime_policy='repaired',
        preset='default_keyframe', preset_source_sha256=PRESET_SOURCE,
        geometry=dict(keyframes=[0, 5, 10, 15, 25, 30, 35, 40, 45], samples_per_edge=5000, neighbors_per_reference=3),
        render=dict(cameras=[0, 10, 20, 30], frames=list(range(50)), fps=25, resolution=[960, 540]),
        artifact_bytes_limit=12 * 2**30, device_bytes_limit=20 * 2**30, cpu_workers_limit=8,
        initializer_contract=dict(schema='plan069-final-render-initializer/v1', time_formula='frame/50',
            velocity_units='normalized-scene/normalized-time', normalization=normalization,
            voxel_basis=voxel_basis, voxel_basis_source=voxel_source),
        allocations=allocation_specs(identity, ITERATIONS),
        budget_amendment=dict(
            amendment=file_record(ROOT / 'docs/specs/plan031-execution/depth-cap-amendment-review-001.json'),
            authorization=file_record(ROOT / 'docs/research/vipe-alternatives/plan031-execution/depth-approval-001.json'),
            artifact_extension=dict(
                amendment=file_record(ROOT / 'docs/specs/plan031-execution/final-render-cap-amendment-review-004.json'),
                authorization=file_record(ROOT / 'docs/research/vipe-alternatives/plan031-execution/final-render-cap-approval-004.json'))))
    proposal = dict(schema='plan069-final-render-review-proposal/v1', record_kind='actual', mode='REVIEW',
        depth_candidate=candidate, bindings=bindings,
        settings_sha256=object_hash({key: value for key, value in request.items() if key != 'bindings'}))
    write_json(HERE / 'proposal.json', proposal)
    request['bindings'] = dict(bindings, proposal=file_record(HERE / 'proposal.json'))
    write_json(HERE / 'request.json', request)
    from basketball_dense_fusion import voxel_width
    write_json(HERE / 'voxel-width.json', dict(schema='plan069-final-render-voxel-width/v1', record_kind='actual',
        rule='half median positive nearest-neighbor distance', request_sha256=object_hash(request),
        scene=bindings['scene_freeze'], basis=voxel_basis, source=voxel_source,
        width=voxel_width(normalized)))
    return request


def admit(request):
    # The approved v2 extension raises the cumulative artifact cap and GPU limit.
    ledger = Ledger(RUN / 'ledger.jsonl', contract.amended_configuration(request))
    from vipe_benchmark.budgets import budget_snapshot
    snapshot = budget_snapshot(RUN)
    storage = dict(artifact_bytes=snapshot['artifact_bytes'], download_bytes=snapshot['download_bytes'],
                   free_disk_bytes=shutil.disk_usage(RUN).free)
    result = contract.admit_review(request, ledger, storage)
    events = ledger.events()
    write_json(HERE / 'admission.json', dict(schema='plan069-final-render-review-admission/v1', record_kind='actual',
        status='admitted_for_review', request=file_record(HERE / 'request.json'),
        request_sha256=result.request_sha256, coverage_edges_per_arm=result.coverage_edges_per_arm,
        gpu_seconds=result.gpu_seconds, cpu_seconds=result.cpu_seconds,
        execution_authorized=result.execution_authorized, blockers=list(result.blockers), storage=storage,
        ledger_head_sequence=events[-1]['sequence'], ledger_head_sha256=events[-1]['event_sha256']))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--qualification', required=True)
    args = parser.parse_args()
    base = Path(__file__).resolve().parent
    for identity, folder in [('plan069-final-render-D8-006', 'production'),
                             ('plan069-final-render-D8-qualification-005', 'qualify')]:
        HERE = base/folder
        HERE.mkdir(exist_ok=False)
        print(identity, admit(build(Path(args.qualification).resolve(), identity)))
