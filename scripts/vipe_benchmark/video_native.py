"""Pinned D9/D10 Video Depth Anything Small source and checkpoint boundary."""

import importlib
import importlib.metadata
from pathlib import Path
import sys

from .files import file_record, read_json, verify_record, write_json


REQUIRED_SOURCE = (
    'run.py', 'requirements.txt', 'LICENSE',
    'video_depth_anything/video_depth.py',
    'video_depth_anything/dinov2.py',
    'video_depth_anything/dinov2_layers/attention.py',
    'video_depth_anything/dpt_temporal.py',
    'video_depth_anything/motion_module/motion_module.py',
    'utils/util.py',
)
REQUIRED_DISTRIBUTIONS = (
    'torch', 'torchvision', 'numpy', 'opencv-python', 'einops',
    'easydict', 'tqdm',
)


def native_source_records(source_dir):
    """Hash the pinned inference import closure before loading executable code."""
    source_dir = Path(source_dir).resolve()
    for relative in REQUIRED_SOURCE:
        path = (source_dir / relative).resolve()
        if not path.is_relative_to(source_dir) or not path.is_file():
            raise ValueError('incomplete or escaping native video source: ' + relative)
    source_files = [path for path in source_dir.rglob('*.py') if path.is_file()]
    source_files += [source_dir / 'requirements.txt', source_dir / 'LICENSE']
    return [file_record(path) for path in sorted(set(source_files))]


def installed_dependency_versions():
    """Inventory direct native inference distributions; this is not clearance."""
    versions = {}
    for name in REQUIRED_DISTRIBUTIONS:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError as error:
            raise ValueError('native video dependency missing: ' + name) from error
    try:
        versions['xformers'] = importlib.metadata.version('xformers')
    except importlib.metadata.PackageNotFoundError:
        versions['xformers'] = None
    return versions


def write_dependency_inventory(candidate, setup_result, output):
    """Snapshot installed direct packages, binary objects and notices on CPU."""
    if candidate not in ('D9', 'D10'):
        raise ValueError('video dependency candidate required')
    setup = read_json(verify_record(setup_result)['path'])
    if setup.get('candidate') != candidate or setup.get('status') != 'complete':
        raise ValueError('completed exact video setup required')
    source_files = native_source_records(setup['source_dir'])
    if setup.get('source_files') != source_files:
        raise ValueError('native video source changed before dependency inventory')
    versions = installed_dependency_versions()
    files = []
    notices = []
    for name, version in versions.items():
        if version is None:
            continue
        dist = importlib.metadata.distribution(name)
        paths = dist.files or []
        selected = [entry for entry in paths if (
            entry.name in ('METADATA', 'RECORD', 'WHEEL') or
            entry.suffix in ('.so', '.pyd') or
            'LICENSE' in entry.name.upper() or
            'NOTICE' in entry.name.upper())]
        if not selected:
            raise ValueError('installed dependency has no verifiable metadata: ' + name)
        for entry in selected:
            path = Path(dist.locate_file(entry))
            if not path.is_file():
                raise ValueError('installed dependency file missing: ' + str(path))
            record = file_record(path)
            files.append(record)
            if 'LICENSE' in entry.name.upper() or 'NOTICE' in entry.name.upper():
                notices.append(record)
    document = dict(schema='plan069-depth-installed-dependencies/v1',
        candidate=candidate, source_revision=setup['source_revision'],
        setup=setup_result, versions=versions, files=files,
        notices=notices, native_source_files=source_files,
        status='captured-not-commercially-cleared')
    write_json(output, document)
    return file_record(output)


def load_native_video(candidate, setup_result, *, device='cuda'):
    """Construct the exact Small architecture and load one strict state dict."""
    if candidate not in ('D9', 'D10') or device not in ('cuda', 'cpu'):
        raise ValueError('D9/D10 native candidate and explicit device required')
    setup = read_json(verify_record(setup_result)['path'])
    if (setup.get('schema') != 'plan069-video-setup-result/v1' or
            setup.get('status') != 'complete' or setup.get('candidate') != candidate or
            setup.get('record_kind') != 'actual'):
        raise ValueError('completed actual video setup required')
    source_dir = Path(setup['source_dir']).resolve()
    if setup.get('source_files') != native_source_records(source_dir):
        raise ValueError('native video source changed after setup')
    checkpoint = verify_record(setup['checkpoint'])['path']
    if Path(checkpoint).resolve().parent != Path(setup_result['path']).resolve().parent:
        raise ValueError('native video checkpoint escaped setup directory')
    installed_dependency_versions()
    if str(source_dir) not in sys.path:
        sys.path.insert(0, str(source_dir))
    import torch
    native = importlib.import_module('video_depth_anything.video_depth')
    if not Path(native.__file__).resolve().is_relative_to(source_dir):
        raise ValueError('native video import resolved outside pinned source')
    util = importlib.import_module('utils.util')
    if not Path(util.__file__).resolve().is_relative_to(source_dir):
        raise ValueError('native video utility resolved outside pinned source')
    model = native.VideoDepthAnything(encoder='vits', features=64,
        out_channels=[48, 96, 192, 384], metric=candidate == 'D10')
    state = torch.load(checkpoint, map_location='cpu', weights_only=True)
    model.load_state_dict(state, strict=True)
    return model.to(device).eval()
