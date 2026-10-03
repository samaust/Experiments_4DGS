"""Frozen D9/D10 environment recipe bound to the acquired native source."""
from pathlib import Path
import shutil

from .config import ROOT
from .files import file_record, read_json, verify_record


RECIPE = ROOT / 'configs/vipe-alternatives/video-environment-v1.json'


def environment_request(candidate, local, *, seed_executable=None, uv_executable=None,
                        record_kind='actual', media_tools=None):
    if candidate not in ('D9', 'D10') or record_kind not in ('actual', 'fixture'):
        raise ValueError('exact native video environment candidate required')
    recipe = read_json(RECIPE)
    seed = Path(seed_executable or Path(local) / 'jobs/E5-setup/environment/bin/python').absolute()
    uv = uv_executable or shutil.which('uv')
    if uv is None:
        raise ValueError('explicit installed uv required for video environment')
    tools = {}
    for name in ('ffmpeg', 'ffprobe'):
        path = (media_tools or {}).get(name) or shutil.which(name)
        if path is None:
            raise ValueError('native video media tool missing: ' + name)
        tools[name] = file_record(path)
    return dict(schema='plan069-depth-environment-request/v1', candidate=candidate,
        record_kind=record_kind, python_version=recipe['python_version'],
        python_seed_executable=str(seed), python_seed=file_record(seed), uv=file_record(uv),
        requirements=recipe['requirements'], constraints=recipe['constraints'],
        indexes=recipe['indexes'], sources=[], recipe=file_record(RECIPE),
        requirement_sources=[file_record(RECIPE)], media_tools=tools,
        xformers='absent; native torch attention fallback')


def bind_source_environment(environment, source_dir, revision, *, candidate, record_kind):
    """Reject recipe drift and bind the extracted requirement and fallback files."""
    recipe = read_json(RECIPE)
    if (environment.get('recipe') != file_record(RECIPE) or
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
    evidence = [file_record(RECIPE), file_record(requirements)]
    evidence += [file_record(source_dir / relative) for relative in recipe['fallback_sources']]
    return dict(environment, requirement_sources=evidence)
