"""Frozen D9/D10 environment recipe bound to the acquired native source."""
from pathlib import Path
import shutil

from .config import ROOT
from .files import file_record, read_json, verify_record


RECIPE = ROOT / 'configs/vipe-alternatives/video-environment-v1.json'
CU130_RECIPE = ROOT / 'configs/vipe-alternatives/video-environment-v2.json'


def selected_recipe(path=None):
    path = RECIPE if path is None else Path(path).absolute()
    if path not in (RECIPE, CU130_RECIPE):
        raise ValueError('exact versioned video recipe required')
    return path


def validate_runtime_versions(environment, versions):
    """Reject a CUDA/version drift before loading native executable code."""
    path = selected_recipe(environment['recipe']['path'])
    if environment['recipe'] != file_record(path):
        raise ValueError('video runtime recipe changed')
    recipe = read_json(path)
    for constraint in recipe['constraints']:
        name, version = constraint.split('==')
        if versions.get(name) != version:
            raise ValueError('video runtime version differs: ' + name)
    if (versions.get('xformers') is not None or
            environment.get('runtime_profile') != recipe.get('runtime_profile')):
        raise ValueError('video runtime profile or attention fallback differs')


def environment_request(candidate, local, *, seed_executable=None, uv_executable=None,
                        record_kind='actual', media_tools=None, recipe_path=None):
    if candidate not in ('D9', 'D10') or record_kind not in ('actual', 'fixture'):
        raise ValueError('exact native video environment candidate required')
    path = selected_recipe(recipe_path)
    recipe = read_json(path)
    seed = Path(seed_executable or Path(local) / 'jobs/E5-setup/environment/bin/python').absolute()
    uv = uv_executable or shutil.which('uv')
    if uv is None:
        raise ValueError('explicit installed uv required for video environment')
    tools = {}
    for name in ('ffmpeg', 'ffprobe'):
        tool_path = (media_tools or {}).get(name) or shutil.which(name)
        if tool_path is None:
            raise ValueError('native video media tool missing: ' + name)
        tools[name] = file_record(tool_path)
    request = dict(schema='plan069-depth-environment-request/v1', candidate=candidate,
        record_kind=record_kind, python_version=recipe['python_version'],
        python_seed_executable=str(seed), python_seed=file_record(seed), uv=file_record(uv),
        requirements=recipe['requirements'], constraints=recipe['constraints'],
        indexes=recipe['indexes'], sources=[], recipe=file_record(path),
        requirement_sources=[file_record(path)], media_tools=tools,
        xformers='absent; native torch attention fallback')
    if 'runtime_profile' in recipe:
        request['runtime_profile'] = recipe['runtime_profile']
    return request


def bind_source_environment(environment, source_dir, revision, *, candidate, record_kind):
    """Reject recipe drift and bind the extracted requirement and fallback files."""
    path = selected_recipe(environment['recipe']['path'])
    recipe = read_json(path)
    if (environment.get('recipe') != file_record(path) or
            environment.get('runtime_profile') != recipe.get('runtime_profile') or
            recipe.get('source_revision') != revision or
            environment.get('schema') != 'plan069-depth-environment-request/v1' or
            environment.get('candidate') != candidate or
            environment.get('record_kind') != record_kind or
            environment.get('python_version') != recipe['python_version'] or
            any(environment.get(key) != recipe[key] for key in
                ('requirements', 'constraints', 'indexes')) or
            environment.get('sources') != [] or
            environment.get('xformers') != 'absent; native torch attention fallback'):
        raise ValueError('video environment differs from frozen native recipe')
    source_dir = Path(source_dir)
    requirements = source_dir / recipe['source_requirement']
    lines = [line.strip() for line in requirements.read_text().splitlines() if line.strip()]
    if lines != recipe['upstream_requirements']:
        raise ValueError('extracted video requirements differ from pinned source')
    tools = environment.get('media_tools', {})
    if set(tools) != {'ffmpeg', 'ffprobe'}:
        raise ValueError('exact video media tool evidence required')
    for record in tools.values():
        verify_record(record)
    evidence = [file_record(path), file_record(requirements)]
    evidence += [file_record(source_dir / relative) for relative in recipe['fallback_sources']]
    return dict(environment, requirement_sources=evidence)
