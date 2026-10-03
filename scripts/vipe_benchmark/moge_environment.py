"""Frozen source-derived MoGe dependency recipes; no acquisition or model imports."""
from pathlib import Path
import re
import tomllib

from .files import file_record, verify_record


CONSTRAINTS = ('torch==2.6.0+cu124', 'torchvision==0.21.0+cu124',
               'triton==3.2.0', 'numpy==2.1.3')
INDEXES = ('https://pypi.org/simple', 'https://download.pytorch.org/whl/cu124')
SOURCE_PINS = (
    ('utils3d_moge', 'EasternJournalist/utils3d-moge', '62f09d58509485564e24d5d9f6aac9ee9ebc0c37'),
    ('pipeline', 'EasternJournalist/pipeline', '1c511390d90226c00c101f34b84df26a0f8789b4'),
    ('flex-gemm', 'JeffreyXiang/FlexGEMM', 'b2fadb29d41846c7981ade6801ffc689fae119cf'),
)


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _source_specifications():
    return [dict(name=name, revision=revision,
        url=f'https://codeload.github.com/{repository}/tar.gz/{revision}',
        max_bytes=16 * 2**20, install_local_offline=True)
        for name, repository, revision in SOURCE_PINS]


def _requirements(source):
    pyproject = Path(source) / 'pyproject.toml'
    document = tomllib.loads(pyproject.read_text())
    project = document.get('project', {})
    dependencies = project.get('dependencies')
    _require(project.get('name') == 'moge' and isinstance(dependencies, list) and dependencies,
             'pinned MoGe source requirements missing')
    expected_direct = {f'{name} @ git+https://github.com/{repository}.git@{revision}'
                       for name, repository, revision in SOURCE_PINS}
    direct = {requirement for requirement in dependencies if ' @ ' in requirement}
    _require(direct == expected_direct, 'pinned offline source requirements changed')
    ordinary = [requirement for requirement in dependencies if requirement not in direct]
    build = document.get('build-system', {}).get('requires', [])
    _require(isinstance(build, list) and build and all(isinstance(r, str) and
             re.match(r'^[A-Za-z0-9_.-]', r) and not any(c in r for c in ('@', '/', '\n'))
             for r in ordinary + build), 'unsafe source requirements')
    # FlexGEMM's pinned metadata requires Triton>=3.2; builds remain offline.
    requirements = list(dict.fromkeys(ordinary + build + ['wheel', 'triton>=3.2.0']))
    return requirements, file_record(pyproject)


def environment_request(candidate, source, *, python_seed_executable, uv, record_kind='actual'):
    """Freeze one reviewed recipe before any candidate setup reservation."""
    _require(candidate in ('D5', 'D6') and record_kind in ('actual', 'fixture'),
             'MoGe environment candidate/origin changed')
    requirements, requirement_source = _requirements(source)
    seed = str(Path(python_seed_executable).absolute())
    return dict(schema='plan069-depth-environment-request/v1', candidate=candidate,
        record_kind=record_kind, python_seed_executable=seed, python_seed=file_record(seed),
        python_version='3.11', uv=file_record(uv), requirements=requirements,
        constraints=list(CONSTRAINTS), requirement_sources=[requirement_source],
        indexes=list(INDEXES), sources=_source_specifications())


def validate_environment_request(recipe, source, candidate, record_kind):
    """Require source requirements to match independently reviewed frozen content."""
    _require(recipe.get('schema') == 'plan069-depth-environment-request/v1' and
             recipe.get('candidate') == candidate and recipe.get('record_kind') == record_kind and
             recipe.get('python_version') == '3.11' and recipe.get('constraints') == list(CONSTRAINTS)
             and recipe.get('indexes') == list(INDEXES), 'frozen MoGe environment profile changed')
    requirements, extracted_record = _requirements(source)
    records = recipe.get('requirement_sources', [])
    _require(recipe.get('requirements') == requirements and len(records) == 1,
             'reviewed MoGe source requirements changed')
    reviewed_record = verify_record(records[0])
    _require(all(extracted_record[k] == reviewed_record[k] for k in ('bytes', 'sha256')),
             'extracted source requirements differ from reviewed source')
    _require(recipe.get('sources') == _source_specifications(), 'pinned offline source changed')
    _require(str(Path(recipe['python_seed_executable']).absolute()) == recipe['python_seed_executable']
             and file_record(recipe['python_seed_executable']) == verify_record(recipe['python_seed']),
             'reviewed Python seed changed')
    verify_record(recipe['uv'])
