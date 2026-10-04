"""Pinned D9/D10 Video Depth Anything Small source and checkpoint boundary."""

import importlib
import importlib.metadata
from pathlib import Path
import sys
import shutil

from .files import file_record, read_json, verify_record, write_json


REQUIRED_SOURCE = (
    'run.py', 'requirements.txt', 'LICENSE',
    'video_depth_anything/video_depth.py',
    'video_depth_anything/dinov2.py',
    'video_depth_anything/dinov2_layers/attention.py',
    'video_depth_anything/dpt_temporal.py',
    'video_depth_anything/motion_module/motion_module.py',
    'video_depth_anything/motion_module/attention.py',
    'video_depth_anything/dpt.py', 'video_depth_anything/util/transform.py',
    'utils/util.py',
)
REQUIRED_DISTRIBUTIONS = (
    'torch', 'torchvision', 'numpy', 'opencv-python', 'einops',
    'easydict', 'tqdm',
    'matplotlib', 'pillow', 'imageio', 'imageio-ffmpeg', 'decord', 'OpenEXR',
)


def setup_environment(setup):
    """Require the provisioned environment and tools before inventory or inference."""
    runtime = read_json(verify_record(setup['runtime_environment'])['path'])
    if (runtime.get('schema') != 'plan069-depth-environment-result/v1' or
            runtime.get('status') != 'complete' or runtime.get('candidate') != setup['candidate'] or
            runtime.get('record_kind') != setup.get('record_kind') or
            runtime.get('python_executable') != setup.get('python_executable') or
            setup.get('python_executable') != str(Path(setup['runtime_environment']['path']).parent /
                                                'environment/bin/python') or
            str(Path(sys.executable).absolute()) != setup.get('python_executable') or
            any(runtime.get(key) != setup.get(key) for key in ('python', 'dependency_lock', 'inventory'))):
        raise ValueError('exact provisioned video environment interpreter required')
    for key in ('python', 'dependency_lock', 'inventory'):
        verify_record(runtime[key])
    from .video_environment import CU130_RECIPE, PYPI_RECIPE
    selected = [path for path in (CU130_RECIPE, PYPI_RECIPE)
        if file_record(path) in runtime.get("requirement_sources", [])]
    if len(selected) > 1:
        raise ValueError("video runtime contains mixed versioned recipe bindings")
    recipe = file_record(selected[0]) if selected else None
    if selected:
        if (setup.get('runtime_recipe') != recipe or
                setup.get('runtime_profile') != read_json(selected[0])['runtime_profile']):
            raise ValueError('video cu130 runtime profile binding missing or changed')
    elif setup.get('runtime_recipe') is not None or setup.get('runtime_profile') is not None:
        raise ValueError('video cu130 runtime profile differs from installed source bindings')
    for name, record in setup['media_tools'].items():
        installed = shutil.which(name)
        if installed is None or file_record(installed) != verify_record(record):
            raise ValueError('video media tool invocation differs from frozen setup: ' + name)
    return runtime


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


def installed_dependency_versions(setup=None):
    """Inventory direct native inference distributions; this is not clearance."""
    versions: dict[str, str | None] = {}
    names = list(REQUIRED_DISTRIBUTIONS)
    if setup and 'runtime_recipe' in setup:
        from .video_environment import PYPI_RECIPE
        if setup['runtime_recipe'] == file_record(PYPI_RECIPE):
            names = [constraint.split('==')[0] for constraint in read_json(PYPI_RECIPE)['constraints']]
    for name in names:
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
    runtime = setup_environment(setup)
    source_files = native_source_records(setup['source_dir'])
    if setup.get('source_files') != source_files:
        raise ValueError('native video source changed before dependency inventory')
    versions = installed_dependency_versions(setup)
    if 'runtime_recipe' in setup:
        from .video_environment import validate_runtime_versions
        validate_runtime_versions(dict(recipe=setup['runtime_recipe'],
            runtime_profile=setup.get('runtime_profile')), versions)
    inventory = read_json(runtime['inventory']['path'])
    if inventory.get('executable') != setup['python_executable'] or not inventory.get('inventory_only'):
        raise ValueError('video installed dependency inventory interpreter changed')
    files = [verify_record(record) for package in inventory['packages'] for record in package['files']]
    if not files:
        raise ValueError('video dependency inventory has no verifiable closure')
    notices = [record for record in files if any(
        name in Path(record['path']).name.upper() for name in ('LICENSE', 'NOTICE'))]
    document = dict(schema='plan069-depth-installed-dependencies/v1',
        candidate=candidate, source_revision=setup['source_revision'],
        setup=setup_result, versions=versions, files=files,
        notices=notices, native_source_files=source_files,
        runtime_environment=setup['runtime_environment'], inventory=runtime['inventory'],
        dependency_lock=runtime['dependency_lock'], python_executable=setup['python_executable'],
        python=runtime['python'], media_tools=setup['media_tools'], xformers=setup['xformers'],
        status='captured-not-commercially-cleared')
    if 'runtime_recipe' in setup:
        from .video_environment import observe_runtime
        observation = observe_runtime(dict(recipe=setup['runtime_recipe'], runtime_profile=setup['runtime_profile']))
        if observation is not None:
            document.update(runtime_recipe=setup['runtime_recipe'], runtime_observation=observation)
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
    setup_environment(setup)
    if setup.get('source_files') != native_source_records(source_dir):
        raise ValueError('native video source changed after setup')
    checkpoint = verify_record(setup['checkpoint'])['path']
    if Path(checkpoint).resolve().parent != Path(setup_result['path']).resolve().parent:
        raise ValueError('native video checkpoint escaped setup directory')
    versions = installed_dependency_versions(setup)
    if 'runtime_recipe' in setup:
        from .video_environment import validate_runtime_versions
        validate_runtime_versions(dict(recipe=setup['runtime_recipe'],
            runtime_profile=setup.get('runtime_profile')), versions)
    if 'runtime_recipe' in setup:
        from .video_environment import observe_runtime
        observe_runtime(dict(recipe=setup['runtime_recipe'], runtime_profile=setup['runtime_profile']))
    if versions['xformers'] is not None:
        raise ValueError('video recipe requires the qualified native torch attention fallback')
    if str(source_dir) not in sys.path:
        sys.path.insert(0, str(source_dir))
    import torch
    native = importlib.import_module('video_depth_anything.video_depth')
    if native.__file__ is None or not Path(native.__file__).resolve().is_relative_to(source_dir):
        raise ValueError('native video import resolved outside pinned source')
    util = importlib.import_module('utils.util')
    if util.__file__ is None or not Path(util.__file__).resolve().is_relative_to(source_dir):
        raise ValueError('native video utility resolved outside pinned source')
    model = native.VideoDepthAnything(encoder='vits', features=64,
        out_channels=[48, 96, 192, 384], metric=candidate == 'D10')
    state = torch.load(checkpoint, map_location='cpu', weights_only=True)
    model.load_state_dict(state, strict=True)
    return model.to(device).eval()
