"""Fail-closed Plan 069 fresh-depth admission over immutable evidence records.

This is a read-only decision. A passing decision is not a reservation or launch;
the owner must recheck live state and atomically reserve the exact approved slot.
"""
import math
import time

from .depth_extension import CONFIG
from .config import ROOT
from .files import file_record, object_hash, read_json, verify_record


INVENTORY = CONFIG.parents[2] / 'docs/specs/plan031-execution/depth-required-assets-v1.json'
PROFILES = CONFIG.parents[2] / 'docs/specs/plan031-execution/depth-runtime-profiles-v1.json'
HISTORICAL = ROOT / 'configs/vipe-alternatives/components-v1.json'
BENCHMARK = ROOT / 'configs/vipe-alternatives/benchmark-v1.json'
CAP_AMENDMENT = ROOT / 'docs/specs/plan031-execution/depth-cap-amendment-review-001.json'
D2_SPEC = dict(model='DA3METRIC-LARGE', mode='historical D2 exact invocation',
    code=dict(url='https://github.com/ByteDance-Seed/Depth-Anything-3',
              revision='3d835ec1a5802d64a8b8b15f817a1ab54809bfe4'),
    weights=dict(url='https://huggingface.co/depth-anything/DA3METRIC-LARGE',
                 revision='4010e39f3634a45bc60553321fb49fb760bd594e'))
LIMIT_KEYS = dict(download_bytes='new_download_gib_limit',
                  artifact_bytes='new_artifact_disk_gib_limit',
                  gpu_seconds='gpu_total_seconds_limit',
                  cpu_seconds='cpu_prepare_score_report_seconds_limit',
                  setup_seconds='setup_wall_seconds_limit')
LOCAL_COMMON = ('files.py', 'ledger.py', 'depth_admission.py', 'depth_extension.py',
    'depth_clips.py', 'scale.py', 'qualitative_package.py')
LOCAL_ADAPTERS = dict(D2=('backends.py', 'contracts.py', 'stages.py',
                          'd2_preflight.py', 'd2_maps.py'),
    D5=('moge_metric.py', 'moge_native.py', 'moge_setup.py'),
    D6=('moge_metric.py', 'moge_native.py', 'moge_setup.py'),
    D7=('dav2_metric.py', 'depth_setup.py'),
    D8=('moge_metric.py', 'native_d8.py', 'depth_native_packages.py',
        'depth_setup.py', 'depth_setup_other.py'),
    D9=('video_depth.py',), D10=('video_depth.py',),
    D11=('marigold_relative.py', 'native_d11.py', 'depth_native_packages.py',
         'depth_setup.py', 'depth_setup_other.py'))


def local_source_records(candidate):
    """Rehash every local inference and publication source bound by review."""
    records = [file_record(ROOT / 'scripts/vipe_benchmark' / name)
               for name in (*LOCAL_COMMON, *LOCAL_ADAPTERS[candidate])]
    if candidate == 'D2':
        records.append(file_record(ROOT / 'scripts/basketball_vipe_d2_maps.py'))
    if candidate == 'D7':
        records.append(file_record(ROOT / 'scripts/basketball_vipe_depth_setup.py'))
        records.append(file_record(ROOT / 'scripts/basketball_vipe_depth_setup_dispatch.py'))
    if candidate in ('D8', 'D11'):
        records.append(file_record(ROOT / 'scripts/basketball_vipe_depth_setup_other.py'))
        records.append(file_record(ROOT / 'scripts/basketball_vipe_depth_setup_other_dispatch.py'))
    if candidate in ('D5', 'D6'):
        records.append(file_record(ROOT / 'scripts/basketball_vipe_moge_setup.py'))
        records.append(file_record(ROOT / 'scripts/basketball_vipe_moge_setup_dispatch.py'))
    return records


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def review(proposal, *, config, commercial, assets, runtime, live,
           source_review=None, approval=None, cap_amendment=None, cap_approval=None,
           ledger_head_sha256=None, now_unix=None):
    """Return blocking reasons for one exact candidate/stage and live snapshot.

    File records are rehashed at this boundary. ``approval`` is a separate
    explicit DO record binding the proposal's canonical hash; a REVIEW document
    alone never grants execution.
    """
    blockers = []
    def check(condition, reason):
        if not condition:
            blockers.append(reason)

    def evidence(value, schema, reason):
        try:
            document = read_json(verify_record(value)['path'])
            _require(document.get('schema') == schema, reason)
            return document
        except (KeyError, TypeError, ValueError, OSError):
            blockers.append(reason)
            return {}

    historical_config = read_json(BENCHMARK)
    cap_keys = ('new_download_gib_limit', 'new_artifact_disk_gib_limit')
    if config != historical_config:
        unchanged = dict(config)
        for key in cap_keys:
            unchanged[key] = historical_config[key]
        check(unchanged == historical_config,
              'historical resource configuration changed outside amendment')
        amendment = evidence(cap_amendment, 'plan069-depth-cap-amendment/v1',
                             'approved versioned cap amendment required')
        baseline = file_record(BENCHMARK)
        expected = dict(schema='plan069-depth-cap-amendment/v1', status='REVIEW',
            historical_configuration={key: baseline[key] for key in ('sha256', 'bytes')},
            new_download_gib_limit=110, new_artifact_disk_gib_limit=210)
        check(cap_amendment == file_record(CAP_AMENDMENT) and amendment == expected and
              all(config.get(key) == amendment.get(key) for key in cap_keys) and
              cap_approval is not None and
              cap_approval.get('schema') == 'plan069-depth-cap-approval/v1' and
              cap_approval.get('status') == 'approved' and
              cap_approval.get('amendment_sha256') == object_hash(amendment),
              'approved versioned cap amendment required')

    extension = read_json(CONFIG)
    inventory = read_json(INVENTORY)
    profiles = read_json(PROFILES)['profiles']
    candidates = dict(extension['candidates'], D2=D2_SPEC)
    candidate = proposal.get('candidate')
    check(proposal.get('schema') == 'plan069-depth-execution-proposal/v1' and
          proposal.get('status') == 'REVIEW', 'exact REVIEW proposal required')
    check(candidate in candidates, 'unknown depth candidate')
    if candidate not in candidates:
        return blockers
    check(proposal.get('candidate_config') == candidates[candidate],
          'candidate source, weights or mode changed')
    check(proposal.get('required_assets') == file_record(INVENTORY),
          'required asset inventory changed')
    check(proposal.get('profile') == profiles[candidate] and
          proposal.get('profile_inventory') == file_record(PROFILES),
          'frozen native preprocessing, precision or seed profile changed')
    expected_maps = 196 if candidate == 'D2' else 256
    check(proposal.get('max_attempts') == 1 and
          proposal.get('workload') == dict(
              anchor_maps=0 if candidate == 'D2' else 60,
              unique_published_maps=expected_maps,
              native_context_frames=4500 if candidate in ('D9', 'D10') else expected_maps,
              clips=4, clip_frames=50, clip_fps=25),
          'bounded candidate workload or attempt count changed')
    reviewed = evidence(source_review,
        'plan069-depth-source-review/v1', 'independent source review receipt missing')
    check(reviewed.get('candidate') == candidate and
          reviewed.get('status') == 'passed' and
          reviewed.get('source_revision') == candidates[candidate]['code']['revision'] and
          reviewed.get('profile_inventory') == file_record(PROFILES),
          'current source review and qualification required')
    current_sources = local_source_records(candidate)
    check(bool(reviewed.get('reviewer')) and
          reviewed.get('local_sources') == current_sources,
          'current local source review required')
    scopes = ('code', 'weights', 'dependencies', 'inference_outputs')
    assessment = evidence(commercial.get('assessment'),
        'plan069-depth-commercial-assessment/v1', 'commercial assessment receipt missing')
    dependency_record = assessment.get('dependency_manifest')
    dependencies = evidence(dependency_record,
        'plan069-depth-installed-dependencies/v1',
        'installed dependency closure changed or unverified')
    dependency_files = dependencies.get('files')
    dependency_ok = (dependencies.get('candidate') == candidate and
        dependencies.get('source_revision') == candidates[candidate]['code']['revision'] and
        isinstance(dependency_files, list) and bool(dependency_files))
    if dependency_ok:
        try:
            for record in dependency_files:
                verify_record(record)
        except (KeyError, TypeError, ValueError, OSError):
            dependency_ok = False
    check(dependency_ok,
          'installed dependency closure changed or unverified')
    check(all(commercial.get(scope) == 'allowed' for scope in scopes) and
          commercial.get('candidate') == candidate and
          commercial.get('source_revision') == candidates[candidate]['code']['revision'] and
          commercial.get('weights_revision') == candidates[candidate]['weights']['revision'] and
          all(assessment.get(key) == commercial.get(key) for key in
              ('candidate', 'source_revision', 'weights_revision', *scopes)) and
          isinstance(assessment.get('primary_sources'), list) and
          len(assessment['primary_sources']) >= 2,
          'exact commercial permissions unresolved')
    expected = inventory['candidates'][candidate]['files']
    if not isinstance(assets, list) or any(not isinstance(row, dict) or
            not {'repository', 'path', 'record'} <= set(row) for row in assets):
        return blockers + ['malformed asset receipts']
    by_key = {(row['repository'], row['path']): row for row in assets}
    check(len(by_key) == len(assets) == len(expected), 'asset inventory has missing or duplicate files')
    for row in expected:
        receipt = by_key.get((row['repository'], row['path']))
        if receipt is None:
            blockers.append('missing asset: ' + row['repository'] + '/' + row['path'])
            continue
        try:
            record = verify_record(receipt['record'])
            check(record['bytes'] == row['bytes'] and
                  (row['lfs_sha256'] is None or record['sha256'] == row['lfs_sha256']),
                  'asset bytes differ: ' + row['repository'] + '/' + row['path'])
        except (KeyError, ValueError, OSError) as error:
            blockers.append('unverified asset: ' + row['path'] + ': ' + str(error))
    qualification = evidence(runtime.get('receipt'),
        'plan069-depth-runtime-qualification/v1', 'runtime qualification receipt missing')
    check(runtime.get('candidate') == candidate and
          runtime.get('source_revision') == candidates[candidate]['code']['revision'] and
          runtime.get('status') == 'passed' and
          runtime.get('config') == file_record(HISTORICAL if candidate == 'D2' else CONFIG),
          'exact runtime qualification missing or stale')
    check(all(qualification.get(key) == runtime.get(key) for key in
              ('candidate', 'source_revision', 'status', 'config')) and
          qualification.get('assets') == assets and
          qualification.get('profile') == proposal.get('profile') and
          qualification.get('local_sources') == current_sources and
          qualification.get('dependency_manifest') == dependency_record,
          'runtime qualification does not bind exact assets and profile')
    check(approval is not None and
          approval.get('schema') == 'plan069-depth-execution-approval/v1' and
          approval.get('proposal_sha256') == object_hash(proposal) and
          approval.get('candidate') == candidate and
          approval.get('status') == 'approved',
          'explicit applicable allocation approval missing')
    check(live.get('active_gpu_owner') is None and
          live.get('active_reservations') == [], 'single GPU or reservation already owned')
    sampled = live.get('sampled_unix')
    now = time.time() if now_unix is None else now_unix
    check(live.get('fresh') is True and
          type(sampled) in (int, float) and math.isfinite(sampled) and
          type(now) in (int, float) and math.isfinite(now) and
          0 <= now - sampled <= 5 and
          isinstance(ledger_head_sha256, str) and len(ledger_head_sha256) == 64 and
          live.get('ledger_head_sha256') == ledger_head_sha256,
          'fresh ledger-bound live-state snapshot required')
    allocation = proposal.get('allocation', {})
    for key, config_key in LIMIT_KEYS.items():
        amount = allocation.get(key)
        used = live.get('used', {}).get(key)
        reserved = live.get('reserved', {}).get(key)
        cap = config[config_key] * (2**30 if key.endswith('bytes') else 1)
        check(type(amount) is int and amount >= 0 and
              (key == 'download_bytes' or amount > 0) and
              type(used) in (int, float) and used >= 0 and
              type(reserved) in (int, float) and reserved >= 0 and
              used + reserved + amount <= cap,
              key + ' allocation exceeds current cap or lacks accounting')
    device = allocation.get('device_bytes')
    current_device = live.get('device_peak_bytes')
    check(type(device) is int and device > 0 and
          type(current_device) is int and current_device >= 0 and
          current_device + device <= config['gpu_peak_device_gib_limit'] * 2**30,
          'device memory allocation exceeds 22 GiB ceiling')
    return blockers
