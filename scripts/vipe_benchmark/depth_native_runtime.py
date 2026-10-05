"""Candidate-specific recipes for metered isolated D8/D11 environments."""

from pathlib import Path
import shutil
import re
import sys

from .depth_native_packages import D11_PINNED, D8_UTILS3D_REVISION, D8_CU130_PROFILE
from .files import file_record, read_json, verify_record


D8_REQUIREMENTS = (
    'torch==2.14.1+cu130', 'torchvision==0.29.1+cu130', 'numpy==1.26.4',
    'gradio', 'click', 'opencv-python', 'scipy', 'matplotlib', 'trimesh',
    'pillow', 'huggingface-hub', 'setuptools==80.9.0', 'wheel', 'packaging',
    # Pinned utils3d declares moderngl (rasterization); user chose a complete lock (Plan 070).
    'moderngl==5.12.0', 'glcontext==3.0.0',
)
UTILS3D_REPOSITORY = 'EasternJournalist/utils3d'


def recipe(candidate, run_root):
    """Bind retained Python seed and uv bytes; do not resolve or download packages."""
    if candidate not in ('D8', 'D11'):
        raise ValueError('unsupported native depth runtime candidate')
    seed_result = read_json(Path(run_root) / 'jobs/E5-setup-recovery-004/result.json')
    if (seed_result.get('status') != 'complete' or seed_result.get('environment') != 'E5' or
            seed_result.get('runtime', {}).get('versions', {}).get('python') != '3.11'):
        raise ValueError('retained E5 Python3.11 seed qualification required')
    interpreter = Path(seed_result['runtime']['python']).absolute()
    uv = shutil.which('uv')
    if uv is None:
        raise ValueError('existing uv executable unavailable')
    requirements = list(D8_REQUIREMENTS)
    if candidate == 'D11':
        requirements = []
        for name, version in D11_PINNED.items():
            if version is None:
                requirements.append(name + '>=3.10')
            else:
                suffix = '+cu128' if name in ('torch', 'torchvision') else ''
                requirements.append(name + '==' + version + suffix)
        requirements += ['packaging', 'setuptools==80.9.0', 'wheel']
    return dict(schema='plan069-depth-environment-request/v1', candidate=candidate,
        record_kind='actual', python_version='3.11',
        python_seed=file_record(interpreter), python_seed_executable=str(interpreter),
        seed_setup=file_record(Path(run_root) / 'jobs/E5-setup-recovery-004/result.json'),
        uv=file_record(uv), requirements=requirements,
        constraints=[row for row in requirements if '==' in row], requirement_sources=[],
        indexes=['https://pypi.org/simple', 'https://download.pytorch.org/whl/' +
                 ('cu130' if candidate == 'D8' else 'cu128')], sources=[],
        compatibility_profile=dict(D8_CU130_PROFILE) if candidate == 'D8' else None,
        setup_attempts=1, automatic_retries=0, python_downloads=False)


def prepare(request, output, config, *, run_root, deadline, acquire,
            download_limit, artifact_limit, request_path=None, retained_utils3d=None,
            extra_constraints=(), lock_check=None):
    """Provision a recipe only inside the caller's approved metered setup slot.

    A setup recovery passes the retained utils3d archive (reused by hash, never
    re-acquired), the original lock's exact pins as additional constraints, and a
    lock_check that refuses an unreviewed closure before anything is installed.
    """
    from .depth_environment import provision_depth_environment
    candidate = request['candidate']
    declared = request.get('environment')
    if request.get('record_kind') == 'actual' and declared != recipe(candidate, run_root):
        raise ValueError('native environment differs from retained candidate recipe')
    if not isinstance(declared, dict) or declared.get('candidate') != candidate:
        raise ValueError('native environment recipe required')
    environment = dict(declared)
    environment['constraints'] = list(declared.get('constraints', [])) + [
        pin for pin in extra_constraints if pin not in declared.get('constraints', [])]
    if request.get('record_kind') == 'actual':
        if request_path is None:
            raise ValueError('actual native environment requires original setup request')
        environment.update(ledger_path=request['ledger_path'],
                           setup_request=file_record(request_path))
    source_dir = Path(output) / 'source'
    requirements = (['models/student_pointmap/requirements.txt'] if candidate == 'D8'
                    else ['pyproject.toml', 'setup/setup_env.sh'])
    environment['requirement_sources'] = [file_record(source_dir / path) for path in requirements]
    if candidate == 'D8':
        from packaging.requirements import Requirement
        raw = (source_dir / requirements[0]).read_text()
        torch_requirements = [Requirement(line.strip()) for line in raw.splitlines()
                              if line.strip() and not line.lstrip().startswith('#') and
                              re.match(r'torch(?=[\s<=>!~\[;]|$)', line.strip())]
        if [str(row) for row in torch_requirements] != ['torch<2.5.0']:
            raise ValueError('D8 original Torch requirement differs from reviewed override')
        if environment.get('compatibility_profile') != D8_CU130_PROFILE:
            raise ValueError('D8 exact compatibility profile required')
    sources = []
    if candidate == 'D8':
        if retained_utils3d is not None:
            record = verify_record(retained_utils3d)
            archive = Path(record['path'])
        else:
            archive = Path(output) / 'utils3d-source.tar.gz'
            record = acquire('https://codeload.github.com/' + UTILS3D_REPOSITORY +
                             '/tar.gz/' + D8_UTILS3D_REVISION, archive,
                             max_bytes=32 * 2**20, deadline=deadline, run_root=run_root,
                             download_limit=download_limit, artifact_limit=artifact_limit)
        from .depth_setup import _unpack_source
        from .depth_source_integrity import source_manifest
        source = Path(output) / 'utils3d-source'
        _unpack_source(archive, source, D8_UTILS3D_REVISION, deadline=deadline,
                       required='utils3d/__init__.py', max_bytes=128 * 2**20)
        sources.append(dict(name='utils3d', revision=D8_UTILS3D_REVISION,
                            record=record, source_dir=str(source), source_manifest=source_manifest(source),
                            install_local_offline=True))
    environment['sources'] = sources
    result = provision_depth_environment(environment, Path(output) / 'runtime', config,
        run_root=run_root, deadline=deadline, download_limit=download_limit,
        artifact_limit=artifact_limit, lock_check=lock_check)
    result['source_packages'] = sources
    result['compatibility_profile'] = environment.get('compatibility_profile')
    result['requirement_sources'] = environment['requirement_sources']
    from .depth_native_packages import qualify
    result['native_qualification'] = qualify(candidate, result['python_executable'],
                                             source_packages=sources,
                                             compatibility_profile=result['compatibility_profile'])
    return result


def verify_runtime(setup, interpreter=None):
    """Require the setup interpreter and requalify exact package metadata at entry."""
    from .depth_native_packages import qualify
    runtime = setup.get('runtime', {})
    selected = str(Path(interpreter or sys.executable).absolute())
    if runtime.get('status') != 'complete' or runtime.get('python_executable') != selected:
        raise ValueError('native entry requires exact prepared interpreter')
    if setup.get('record_kind') == 'actual':
        if runtime.get('record_kind') != 'actual' or runtime.get('python') != file_record(selected):
            raise ValueError('native prepared interpreter record changed')
        for field in ('dependency_lock', 'inventory'):
            verify_record(runtime[field])
        for record in runtime['command_receipts']:
            verify_record(record)
    if setup['candidate'] == 'D8':
        if runtime.get('compatibility_profile') != D8_CU130_PROFILE:
            raise ValueError('D8 exact compatibility profile required at entry')
        expected = file_record(Path(setup['source_dir']) / 'models/student_pointmap/requirements.txt')
        if runtime.get('requirement_sources') != [expected]:
            raise ValueError('D8 original requirements changed since setup')
    qualification = qualify(setup['candidate'], selected,
                            source_packages=runtime.get('source_packages', []),
                            compatibility_profile=runtime.get('compatibility_profile'))
    if qualification != runtime.get('native_qualification'):
        raise ValueError('native package qualification changed since setup')
    return qualification
