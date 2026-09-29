"""Derive all selections, settings, source pins and allocations from the protocol."""
import json
from pathlib import Path
import re

from .files import digest, read_json, safe_path

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / 'docs/research/vipe-alternatives.md'
PROTOCOL = ROOT / 'docs/research/vipe-alternatives/benchmark-protocol.md'
PLAN = ROOT / 'plans/plan_031.md'
SOURCE_HASHES = {
    'study': '6fbb6e55dedf444766c75e946c3d5099426839e0df158706d98d28b635353e8e',
    'protocol': '6d32683e3d351f8f19afffa11fe5664c5a15515f84a2b9380f86a39a757072f5',
}

# User-directed E4 amendment recorded in Plan 031. Preserve the frozen source
# documents and their hashes, as well as every prior run's recorded targets.
E4_RUNTIME_AMENDMENT = (
    'Python 3.11 / torch 2.13.0+cu130 / torchvision 0.28.0+cu130; '
    'torchaudio 2.11.0+cu130; NumPy 2.1.3; xFormers >=0.0.26 resolved once '
    'under exact Torch constraints and hash-locked. E4-only cu130 amendment '
    'in Plan 031; package availability and native compatibility unqualified.'
)


def source_documents():
    for name, path in [('study', STUDY), ('protocol', PROTOCOL)]:
        if digest(path) != SOURCE_HASHES[name]:
            raise ValueError(f'{name} changed; a recorded protocol amendment is required')
    return STUDY.read_text(), PROTOCOL.read_text()


def derive():
    study, protocol = source_documents()
    blocks = re.findall(r'^```json\n(.*?)^```', protocol, re.M | re.S)
    if len(blocks) != 1:
        raise ValueError('expected one scheduling specification')
    config = json.loads(blocks[0])
    settings = {}
    runtimes = {}
    for line in protocol.splitlines():
        cells = [x.strip() for x in line.strip('|').split('|')]
        if len(cells) == 2 and re.fullmatch(r'[SDMN]\d', cells[0]):
            settings[cells[0]] = cells[1]
        if len(cells) == 3 and re.match(r'E[0-8] ', cells[0]):
            runtimes[cells[0].split()[0]] = dict(name=cells[0], scope=cells[1], target=cells[2])
    pins = []
    section = study.split('## 6. Source and asset pins\n', 1)[1].split('## 7.', 1)[0]
    for line in section.splitlines():
        cells = [x.strip() for x in line.strip('|').split('|')]
        if len(cells) in (2, 3) and re.fullmatch(r'`[a-f0-9]{40}`', cells[1]):
            pins.append(dict(source=cells[0], revision=cells[1].strip('`'),
                             selected_file=cells[2] if len(cells) == 3 else None))
    if len(settings) != 16 or len(runtimes) != 9 or len(pins) != 19:
        raise ValueError('missing component settings, runtime targets or pins')
    runtimes['E4']['target'] = E4_RUNTIME_AMENDMENT
    return config, dict(schema='vipe-benchmark-components/v1', source_hashes=SOURCE_HASHES,
                        settings=settings, runtimes=runtimes, pins=pins)


def load(config_path=None):
    expected, components = derive()
    path = config_path or ROOT / 'configs/vipe-alternatives/benchmark-v1.json'
    config = read_json(safe_path(path))
    if config != expected:
        raise ValueError('configuration differs from protocol JSON')
    if read_json(ROOT / 'configs/vipe-alternatives/components-v1.json') != components:
        raise ValueError('component settings/pins differ from the source documents')
    return config


def training_cameras(config):
    return [c for c in range(34) if c not in config['held_out_cameras']]


def distinct_pair_frames(config):
    return sorted({f for t in config['pair_starts'] for f in (t, t + 1)})


def counts(config):
    cameras = len(training_cameras(config))
    calibration = 34 * (len(config['fit_snapshots']) + len(config['selection_snapshots']))
    pairs = cameras * len(config['pair_starts'])
    frames = distinct_pair_frames(config)
    contexts = len(config['diagnostic_cameras']) * len(config['diagnostic_pair_starts'])
    edges = contexts * config['neighbors_per_reference']
    return dict(calibration_fit=34 * len(config['fit_snapshots']),
                calibration_selection=34 * len(config['selection_snapshots']),
                reconstruction_pairs=pairs, reconstruction_contexts=2 * pairs,
                reconstruction_rgb=cameras * len(frames), geometry_contexts=contexts,
                geometry_edges=edges, depth_inputs=2 * cameras,
                annotation_images=len(config['annotation_calibration_cameras']) *
                len(config['annotation_calibration_frames']) + len(config['diagnostic_cameras']) * len(frames),
                motion_rgb=34 * (199 - 50 + 1) + cameras * 50,
                primary_mask_rows=5 * (calibration + 2 * pairs), primary_depths=5 * 2 * cameras,
                isolated_matches=9 * edges, combined_matches=4 * edges,
                max_person_crops=4 * edges * 255,
                gpu_jobs=sum(j['attempts'] for j in config['gpu_jobs']),
                gpu_seconds=sum(j['attempts'] * j['seconds_each'] for j in config['gpu_jobs']))


def jobs(config):
    """Stable process identities; limits are taken only from the embedded JSON."""
    groups = [
        [f'S{i}-calibration' for i in range(5)],
        [f'S{i}-reconstruction' for i in range(5)],
        [f'D{i}-fit' for i in range(5)],
        [f'D{i}-check' for i in range(5)],
        [f'G-S{i}' for i in range(5)],
        ['G-M1', 'G-M2'], ['G-N1', 'G-N2'],
        [f'C{i}' for i in range(4)], ['R-S', 'R-D', 'R-G'],
    ]
    result = {}
    for spec, ids in zip(config['gpu_jobs'], groups, strict=True):
        if spec['attempts'] != len(ids):
            raise ValueError('job identities no longer match the protocol allocation')
        for job_id in ids:
            result[job_id] = dict(id=job_id, resource='gpu', scope=spec['scope'],
                                  seconds=spec['seconds_each'])
    for prefix, allocation in [('M', 'cpu_motion_jobs'), ('N', 'cpu_neighbor_jobs')]:
        for i in range(config[allocation]['attempts']):
            key = f'{prefix}{i}'
            result[key] = dict(id=key, resource='motion' if prefix == 'M' else 'neighbor',
                               scope=allocation, seconds=config[allocation]['seconds_each'])
    for i in range(1, config['environment_builds_limit'] + 1):
        key = f'E{i}-setup'
        result[key] = dict(id=key, resource='setup', scope='serial environment builds',
                           seconds=config['setup_wall_seconds_limit'])
    # Aggregation is a single resumable transaction with frozen stage checkpoints.
    for key in ['prepare', 'annotations', 'aggregate', 'report']:
        result[key] = dict(id=key, resource='cpu', scope='preparation/import/scoring/report',
                           seconds=config['cpu_prepare_score_report_seconds_limit'])
    return result


def execution_order():
    result = []
    for i in range(5):
        result += [f'S{i}-calibration', f'S{i}-reconstruction']
        if i == 1:
            result += ['R-S']
    result += [f'M{i}' for i in range(3)]
    for i in range(5):
        result += [f'D{i}-fit']
        if i == 1:
            result += ['R-D']
    result += [f'D{i}-check' for i in range(5)]
    result += [f'N{i}' for i in range(3)]
    result += ['G-S0', 'R-G'] + [f'G-S{i}' for i in range(1, 5)]
    result += ['G-M1', 'G-M2', 'G-N1', 'G-N2', 'C0', 'C1', 'C2', 'C3']
    return result
