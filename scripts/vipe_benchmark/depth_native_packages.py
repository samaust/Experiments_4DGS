"""CPU-only pinned dependency checks before D8/D11 runtime smoke."""

from importlib import metadata
import json
from pathlib import Path
import os
import subprocess
import sys
from typing import Any

from packaging.version import Version

from .files import file_record, object_hash


D8_CU130_PROFILE: dict[str, Any] = dict(
    schema='plan069-D8-runtime-compatibility-profile/v1',
    name='D8-torch-2.14.1-cu130',
    torch='2.14.1+cu130', torchvision='0.29.1+cu130',
    upstream_torch_constraint='torch<2.5.0',
    scope='local-qualified-inference', upstream_supported=False)


D8_UTILS3D_REVISION = '3fab839f0be9931dac7c8488eb0e1600c236e183'
D8_REQUIRED = ('torch', 'torchvision', 'gradio', 'click', 'opencv-python',
               'scipy', 'matplotlib', 'trimesh', 'pillow', 'huggingface-hub', 'utils3d')
D11_PINNED = {
    'torch': '2.10.0', 'torchvision': '0.25.0', 'accelerate': '1.13.0',
    'bitsandbytes': '0.49.2', 'diffusers': '0.38.0',
    'huggingface-hub': '1.8.0', 'matplotlib': '3.10.8', 'numpy': '2.2.5',
    'omegaconf': '2.3.0', 'opencv-python-headless': '4.13.0.92',
    'pandas': '2.3.3', 'peft': '0.18.1', 'pillow': '12.1.1',
    'pyarrow': '18.0', 'pyyaml': '6.0.3', 'safetensors': '0.8.0',
    'scikit-image': '0.25.2', 'scikit-learn': '1.7.2', 'scipy': '1.15.3',
    'tabulate': '0.10.0', 'tensorboard': '2.20.0', 'tqdm': '4.67.3',
    'transformers': '5.4.0', 'wandb': '0.26.1', 'h5py': None, 'lpips': '0.1.4',
}


def installed(names):
    """Read package metadata without importing Torch or touching a GPU."""
    found: dict[str, Any] = {}
    for name in names:
        try:
            dist = metadata.distribution(name)
            direct = dist.read_text('direct_url.json')
            found[name] = dict(version=dist.version,
                direct_url=json.loads(direct) if direct else None)
        except metadata.PackageNotFoundError:
            found[name] = None
    return found


def blockers(candidate, packages, source_packages=(), compatibility_profile=None):
    if candidate == 'D8':
        problems = [f'{name} missing' for name in D8_REQUIRED if not packages.get(name)]
        torch = packages.get('torch') or {}
        version = torch.get('version', '').split('+', 1)[0]
        major_minor = version.split('.')[:2]
        if compatibility_profile is not None:
            if compatibility_profile != D8_CU130_PROFILE:
                problems.append('D8 compatibility profile differs from reviewed profile')
            for name in ('torch', 'torchvision'):
                if (packages.get(name) or {}).get('version') != D8_CU130_PROFILE[name]:
                    problems.append('D8 compatibility profile requires exact ' + name + ' ' +
                                    D8_CU130_PROFILE[name])
        elif len(major_minor) != 2 or not all(part.isdigit() for part in major_minor) or \
                tuple(map(int, major_minor)) >= (2, 5):
            problems.append('D8 requires torch<2.5.0')
        utils = packages.get('utils3d') or {}
        vcs = (utils.get('direct_url') or {}).get('vcs_info') or {}
        archive = next((row for row in source_packages if row.get('name') == 'utils3d' and
                        row.get('revision') == D8_UTILS3D_REVISION), None)
        direct = utils.get('direct_url') or {}
        archive_info = direct.get('archive_info')
        archive_matches = False
        if archive is not None and isinstance(archive_info, dict):
            expected = archive['record']
            # PEP 610 permits an empty archive_info for an exact local archive.
            # qualify() rehashes the archive and complete source manifest first.
            valid_fields = set(direct) == {'url', 'archive_info'} and \
                set(archive_info) <= {'hash', 'hashes'}
            hashes = archive_info.get('hashes', {})
            valid_hashes = isinstance(hashes, dict) and set(hashes) <= {'sha256'} and \
                ('sha256' not in hashes or hashes['sha256'] == expected['sha256'])
            valid_hash = 'hash' not in archive_info or \
                archive_info['hash'] == 'sha256=' + expected['sha256']
            archive_matches = valid_fields and valid_hashes and valid_hash and \
                direct.get('url') == Path(expected['path']).absolute().as_uri()
        pinned = archive_matches if source_packages else vcs.get('commit_id') == D8_UTILS3D_REVISION
        if not pinned:
            problems.append('D8 requires pinned utils3d Git revision')
        return problems
    if candidate == 'D11':
        problems = []
        for name, exact in D11_PINNED.items():
            entry = packages.get(name)
            if entry is None:
                problems.append(name + ' missing')
            elif exact is not None and Version(entry.get('version', '').split('+', 1)[0]) != Version(exact):
                problems.append(name + ' differs from pinned version ' + exact)
        h5py = packages.get('h5py') or {}
        h5py_parts = h5py.get('version', '').split('.')[:2]
        if len(h5py_parts) != 2 or not all(part.isdigit() for part in h5py_parts) or \
                tuple(map(int, h5py_parts)) < (3, 10):
            problems.append('h5py requires version >=3.10')
        return problems
    raise ValueError('unsupported native dependency candidate')


def qualify(candidate, interpreter=None, *, source_packages=(), compatibility_profile=None):
    """Probe exact entry interpreter without importing models or initializing CUDA."""
    interpreter = Path(interpreter or sys.executable).absolute()
    names = D8_REQUIRED if candidate == 'D8' else tuple(D11_PINNED)
    before = file_record(interpreter)
    if candidate == 'D8' and str(interpreter) == str(Path(sys.executable).absolute()):
        packages = installed(names)
    else:
        scripts = str(Path(__file__).resolve().parents[1])
        code = ('import sys, json; sys.path.insert(0, ' + repr(scripts) + '); '
                'from vipe_benchmark.depth_native_packages import installed; '
                'print(json.dumps(installed(' + repr(names) + ')))')
        result = subprocess.run([str(interpreter), '-I', '-B', '-c', code],
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'),
            capture_output=True, text=True, check=True, timeout=60)
        packages = json.loads(result.stdout)
    for source in source_packages:
        if file_record(source['record']['path']) != source['record']:
            raise ValueError('native dependency source archive changed')
        from .depth_source_integrity import source_manifest
        if source_manifest(source['source_dir']) != source['source_manifest']:
            raise ValueError('native dependency source tree changed')
    problems = blockers(candidate, packages, source_packages, compatibility_profile)
    if problems:
        raise ValueError('native dependency qualification failed: ' + '; '.join(problems))
    if before != file_record(interpreter):
        raise ValueError('native interpreter changed during qualification')
    return dict(schema='plan069-depth-native-packages/v1', status='passed',
                candidate=candidate, interpreter_path=str(interpreter),
                interpreter=before, packages=packages, packages_sha256=object_hash(packages),
                source_packages=list(source_packages), compatibility_profile=compatibility_profile)
