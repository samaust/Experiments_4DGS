"""Frozen source-derived MoGe dependency recipes; no acquisition or model imports."""
from pathlib import Path
import os
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


def validate_build_environment():
    """Refuse inherited requests for an unreviewed CUDA source build."""
    _require(not any(name in os.environ for name in ('FLEX_GEMM_BUILD_CUDA', 'BUILD_CUDA')),
             'inherited FlexGEMM CUDA build flags must be absent')


def _source_specifications():
    return [dict(name=name, revision=revision,
        url=f'https://codeload.github.com/{repository}/tar.gz/{revision}',
        max_bytes=16 * 2**20, install_local_offline=True)
        for name, repository, revision in SOURCE_PINS]


def _safe_requirements(requirements):
    _require(isinstance(requirements, list) and all(isinstance(r, str) and
             re.match(r'^[A-Za-z0-9_.-]', r) and not any(c in r for c in ('@', '/', '\n'))
             for r in requirements), 'unsafe source requirements')
    return requirements


def _dependency_requirements(dependency_sources):
    _require(set(dependency_sources) == {p[0] for p in SOURCE_PINS},
             'all three reviewed VCS dependency sources required')
    requirements, reviews = [], []
    for name, _, revision in SOURCE_PINS:
        path = Path(dependency_sources[name]) / 'pyproject.toml'
        document = tomllib.loads(path.read_text())
        project = document.get('project', {})
        _require(str(project.get('name', '')).replace('_', '-') == name.replace('_', '-'),
                 'reviewed dependency project name differs')
        requirements.extend(_safe_requirements(project.get('dependencies', [])))
        requirements.extend(_safe_requirements(document.get('build-system', {}).get('requires', [])))
        review = dict(name=name, revision=revision, pyproject=file_record(path))
        if name == 'flex-gemm':
            review['setup'] = file_record(path.parent / 'setup.py')
        reviews.append(review)
    return requirements, reviews


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
    _require(bool(build), 'unsafe source requirements')
    requirements = list(dict.fromkeys(_safe_requirements(ordinary + build) + ['wheel']))
    return requirements, file_record(pyproject)


def environment_request(candidate, source, *, python_seed_executable, uv,
                        dependency_sources, runtime_directory, record_kind='actual'):
    """Freeze one reviewed recipe before any candidate setup reservation."""
    _require(candidate in ('D5', 'D6') and record_kind in ('actual', 'fixture'),
             'MoGe environment candidate/origin changed')
    validate_build_environment()
    from .moge_source_build import cache_path
    cache = cache_path(runtime_directory)
    _require(record_kind == 'fixture' or
             (cache.parent.parent.name == 'runtime' and
              cache.parent.parent.parent.name == f'plan069-{candidate}-setup-001'),
             'reviewed MoGe runtime directory differs from owned setup')
    requirements, requirement_source = _requirements(source)
    dependency_requirements, dependency_reviews = _dependency_requirements(dependency_sources)
    requirements = list(dict.fromkeys(requirements + dependency_requirements))
    seed = str(Path(python_seed_executable).absolute())
    return dict(schema='plan069-depth-environment-request/v1', candidate=candidate,
        record_kind=record_kind, python_seed_executable=seed, python_seed=file_record(seed),
        python_version='3.11', uv=file_record(uv), requirements=requirements,
        constraints=list(CONSTRAINTS),
        requirement_sources=[requirement_source] + [r['pyproject'] for r in dependency_reviews],
        dependency_reviews=dependency_reviews,
        flex_cache_path=str(cache),
        indexes=list(INDEXES), sources=_source_specifications())


def validate_environment_request(recipe, source, candidate, record_kind):
    """Require source requirements to match independently reviewed frozen content."""
    validate_build_environment()
    from .moge_source_build import cache_path
    cache = Path(recipe['flex_cache_path'])
    _require(str(cache_path(cache.parent.parent)) == recipe['flex_cache_path'] and
             (record_kind == 'fixture' or cache.parent.parent.parent.name ==
              f'plan069-{candidate}-setup-001'), 'reviewed MoGe scoped cache changed')
    _require(recipe.get('schema') == 'plan069-depth-environment-request/v1' and
             recipe.get('candidate') == candidate and recipe.get('record_kind') == record_kind and
             recipe.get('python_version') == '3.11' and recipe.get('constraints') == list(CONSTRAINTS)
             and recipe.get('indexes') == list(INDEXES), 'frozen MoGe environment profile changed')
    requirements, extracted_record = _requirements(source)
    records = recipe.get('requirement_sources', [])
    reviews = recipe.get('dependency_reviews', [])
    _require(isinstance(reviews, list) and len(reviews) == 3 and
             [(r.get('name'), r.get('revision')) for r in reviews] ==
             [(name, revision) for name, _, revision in SOURCE_PINS],
             'reviewed VCS dependency lineage changed')
    dependency_sources = {}
    for review in reviews:
        dependency_sources[review['name']] = Path(verify_record(review['pyproject'])['path']).parent
        if review['name'] == 'flex-gemm':
            verify_record(review['setup'])
    extra, current_reviews = _dependency_requirements(dependency_sources)
    requirements = list(dict.fromkeys(requirements + extra))
    _require(recipe.get('requirements') == requirements and len(records) == 4 and
             reviews == current_reviews and records[1:] == [r['pyproject'] for r in reviews],
             'reviewed MoGe source requirements changed')
    reviewed_record = verify_record(records[0])
    _require(all(extracted_record[k] == reviewed_record[k] for k in ('bytes', 'sha256')),
             'extracted source requirements differ from reviewed source')
    _require(recipe.get('sources') == _source_specifications(), 'pinned offline source changed')
    _require(str(Path(recipe['python_seed_executable']).absolute()) == recipe['python_seed_executable']
             and file_record(recipe['python_seed_executable']) == verify_record(recipe['python_seed']),
             'reviewed Python seed changed')
    verify_record(recipe['uv'])
