"""Pinned, run-local CUDA 12.4 build inputs; never probes a compiler or GPU.

Acquisition belongs inside the controller's existing E1/E2 setup allocation.
The controller accounts for overall setup time and disk use. ``runtime.download``
accounts for every transferred byte. An incomplete directory is never retried
implicitly, and a completed receipt is reused only after verifying its files.
"""
from email.parser import Parser
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tarfile

from .files import file_record, read_json, safe_path, verify_record, write_json


VERSION = '12.4.1'
MANIFEST = 'https://developer.download.nvidia.com/compute/cuda/redist/redistrib_12.4.1.json'
BASE_URL = 'https://developer.download.nvidia.com/compute/cuda/redist/'
COMPONENTS = (
    dict(name='cuda_nvcc', version='12.4.131', bytes=51184484,
         relative_path='cuda_nvcc/linux-x86_64/cuda_nvcc-linux-x86_64-12.4.131-archive.tar.xz',
         sha256='7ffba1ada0e4b8c17e451ac7a60d386aa2642ecd08d71202a0b100c98bd74681'),
    dict(name='cuda_cudart', version='12.4.127', bytes=1099680,
         relative_path='cuda_cudart/linux-x86_64/cuda_cudart-linux-x86_64-12.4.127-archive.tar.xz',
         sha256='0483bff9a36e7a44465db3cd42874f6f70f019297dcf803fbefcbf58d7448c8f'),
    dict(name='cuda_cccl', version='12.4.127', bytes=1157180,
         relative_path='cuda_cccl/linux-x86_64/cuda_cccl-linux-x86_64-12.4.127-archive.tar.xz',
         sha256='e1636f27a142d24e73dfd831c54bbf5575b498fd5900648d7372fae46f824fdf'),
)
RECEIPT = 'toolkit-receipt.json'
REQUIRED_TOOLKIT_FILES = (
    'bin/nvcc', 'bin/ptxas', 'bin/fatbinary', 'bin/nvlink', 'nvvm/bin/cicc',
    'nvvm/libdevice/libdevice.10.bc', 'include/cuda.h', 'include/cuda_runtime.h',
    'include/cuda_runtime_api.h', 'include/crt/host_config.h',
    'include/cuda_fp16.h', 'include/cuda_bf16.h', 'include/driver_types.h',
    'include/library_types.h', 'include/vector_types.h',
    'include/nv/target', 'include/cub/cub.cuh', 'include/thrust/version.h',
    'include/cuda/std/type_traits', 'lib64/libcudart.so',
)
WHEEL_HEADERS = {
    'nvidia-cublas-cu12': ('cublas', ('cublas_v2.h', 'cublasLt.h')),
    'nvidia-cusparse-cu12': ('cusparse', ('cusparse.h',)),
    'nvidia-cusolver-cu12': ('cusolver', ('cusolverDn.h',)),
}


def _inside(path, root):
    path = safe_path(path)
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f'toolkit path escapes its root: {path}')
    return path


def _destination(name, component):
    """Map a tar member without opening its data; None skips forbidden names."""
    path = PurePosixPath(name)
    if 'prompts' in path.parts:
        return None
    if path.is_absolute() or '..' in path.parts or '\\' in name:
        raise ValueError(f'unsafe toolkit archive path: {name}')
    expected = Path(component['relative_path']).name.removesuffix('.tar.xz')
    if not path.parts or path.parts[0] != expected:
        raise ValueError(f'toolkit archive root differs from its pinned component: {name}')
    parts = path.parts[1:]
    if not parts:
        return Path('.')
    relative = Path(*parts)
    if len(parts) == 1:
        # Component-level license/version files must not overwrite one another.
        category = ('licenses' if parts[0].lower().startswith(
            ('license', 'eula', 'notice', 'copyright')) else 'metadata')
        if parts[0] not in ('bin', 'include', 'lib', 'lib64', 'nvvm', 'share', 'targets'):
            return Path(category) / component['name'] / relative
    return relative


def _link_destination(relative, target, root):
    link = PurePosixPath(target)
    if link.is_absolute() or '\\' in target or 'prompts' in link.parts:
        raise ValueError('unsafe toolkit archive symlink')
    resolved = _inside(root / relative.parent / Path(target), root)
    if resolved == root or resolved.resolve() == root.resolve():
        raise ValueError('toolkit archive symlink targets the toolkit root')
    return resolved


def _extract(archive, root, component, links, *, remaining):
    written = 0
    with tarfile.open(archive, mode='r:xz') as source:
        for member in source:
            relative = _destination(member.name, component)
            if relative is None or relative == Path('.'):
                continue
            target = _inside(root / relative, root)
            if member.mode & 0o7000:
                raise ValueError('unsafe special permission bits in toolkit archive')
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            elif member.issym():
                _link_destination(relative, member.linkname, root)
                links.append((relative, member.linkname))
            elif member.isfile():
                if member.size < 0 or written + member.size > remaining:
                    raise ValueError('toolkit extraction exceeds the artifact disk allocation')
                target.parent.mkdir(parents=True, exist_ok=True)
                with source.extractfile(member) as inp, target.open('xb') as out:
                    shutil.copyfileobj(inp, out, length=2**20)
                target.chmod(member.mode & 0o777)
                written += member.size
            else:
                raise ValueError('toolkit archive contains a hardlink or special file')
    return written


def _inventory(root):
    files, links = [], []
    for base, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in ('prompts', 'archives'))
        for name in sorted(dirs + names):
            path = Path(base) / name
            if path.name == RECEIPT or path.name == 'prompts':
                continue
            _inside(path, root)
            if path.is_symlink():
                target = os.readlink(path)
                _link_destination(path.relative_to(root), target, root)
                if not path.exists():
                    raise ValueError(f'dangling toolkit symlink: {path}')
                links.append(dict(path=str(path.absolute()), target=target))
            elif path.is_file():
                files.append(dict(file_record(path), mode=stat.S_IMODE(path.stat().st_mode)))
            elif not path.is_dir():
                raise ValueError(f'unexpected toolkit filesystem object: {path}')
    return files, links


def _verify(record):
    root = safe_path(record['path']).absolute()
    if root.is_symlink() or not root.is_dir():
        raise ValueError('toolkit root must be an existing real directory')
    if record.get('version') != VERSION or record.get('components') != list(COMPONENTS):
        raise ValueError('toolkit receipt differs from the pinned CUDA components')
    if record.get('manifest') != MANIFEST or record.get('platform') != 'linux-x86_64':
        raise ValueError('toolkit receipt has the wrong source or platform')
    if 'receipt' in record:
        if safe_path(record['receipt']['path']).absolute() != root / RECEIPT:
            raise ValueError('toolkit receipt file is outside its declared root')
        verify_record(record['receipt'])
    archives = record.get('archives', [])
    if len(archives) != len(COMPONENTS):
        raise ValueError('toolkit receipt does not contain every pinned archive')
    for archive, component in zip(archives, COMPONENTS):
        expected = root / 'archives' / Path(component['relative_path']).name
        if Path(archive['path']).absolute() != expected or archive.get('sha256') != component['sha256']:
            raise ValueError('toolkit archive receipt differs from its published identity')
        if archive.get('bytes') != component['bytes'] or archive.get('url') != BASE_URL + component['relative_path']:
            raise ValueError('toolkit archive receipt differs from its published size/URL')
        verify_record(archive)
    actual_files, actual_links = _inventory(root)
    if actual_files != record.get('files') or actual_links != record.get('links'):
        raise ValueError('toolkit files, modes or symlinks changed after acquisition')
    return root


def acquire_toolkit(local, transfer_dir, config):
    """Acquire once or verify/reuse a completed toolkit, within existing budgets."""
    root = safe_path(local).absolute()
    receipt = root / RECEIPT
    if root.exists() or root.is_symlink():
        if root.is_symlink() or not receipt.is_file():
            raise ValueError('incomplete or unreceipted toolkit exists; no automatic reacquisition')
        record = read_json(receipt)
        if Path(record['path']).absolute() != root:
            raise ValueError('toolkit receipt belongs to a different directory')
        _verify(record)
        return dict(record, receipt=file_record(receipt), reused=True)
    root.mkdir(parents=True, exist_ok=False)
    from .runtime import download  # The controller owns transport accounting.
    archives, pending_links = [], []
    unpacked = 0
    disk_limit = int(config['new_artifact_disk_gib_limit'] * 2**30)
    for component in COMPONENTS:
        destination = root / 'archives' / Path(component['relative_path']).name
        record = download(BASE_URL + component['relative_path'], destination, Path(transfer_dir),
                          limit=int(config['new_download_gib_limit'] * 2**30))
        verified = file_record(destination, component['sha256'])
        if record['sha256'] != verified['sha256'] or verified['bytes'] != component['bytes']:
            raise ValueError('toolkit archive differs from its published bytes/receipt')
        archives.append(dict(verified, url=BASE_URL + component['relative_path']))
        unpacked += _extract(destination, root, component, pending_links,
                             remaining=disk_limit - unpacked - sum(a['bytes'] for a in archives))
    for relative, target in pending_links:
        path = _inside(root / relative, root)
        _link_destination(relative, target, root)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.symlink_to(target)
        _inside(path, root)
    if not (root / 'lib64').exists() and (root / 'lib').is_dir():
        (root / 'lib64').symlink_to('lib', target_is_directory=True)
    files, links = _inventory(root)
    record = dict(path=str(root), version=VERSION, platform='linux-x86_64', manifest=MANIFEST,
                  components=list(COMPONENTS), archives=archives, files=files, links=links,
                  archive_bytes=sum(a['bytes'] for a in archives), unpacked_bytes=unpacked,
                  allocation='existing E1/E2 setup; no additional environment attempt')
    _verify(record)
    write_json(receipt, record)
    return dict(record, receipt=file_record(receipt), reused=False)


def _metadata(site, name):
    pattern = name.replace('-', '_') + '-*.dist-info/METADATA'
    matches = sorted(site.glob(pattern))
    if len(matches) != 1:
        raise ValueError(f'exactly one installed {name} metadata record is required')
    path = safe_path(matches[0])
    metadata = Parser().parsestr(path.read_text())
    actual = re.sub(r'[-_.]+', '-', metadata.get('Name', '')).lower()
    if actual != name:
        raise ValueError(f'installed metadata does not identify {name}')
    return metadata, file_record(path)


def build_environment(toolkit_record, pythonenv):
    """Return ``{env, headers, packages}`` without executing the declared Python.

    ``env`` is merged into the controller's build environment. Header/package
    records must be saved alongside it; this verifies required header locations
    and bytes, not whether native compilation or model inference will succeed.
    """
    root = _verify(toolkit_record)
    env_root = safe_path(pythonenv).absolute()
    if env_root.parent.name == 'bin' and env_root.name.startswith('python'):
        env_root = env_root.parent.parent
    sites = sorted({p.resolve() for p in env_root.glob('lib*/python3.11/site-packages') if p.is_dir()})
    if len(sites) != 1:
        raise ValueError('E1/E2 require exactly one declared Python 3.11 site-packages directory')
    site = sites[0]
    torch_meta, torch_record = _metadata(site, 'torch')
    if torch_meta.get('Version') != '2.5.1+cu124':
        raise ValueError('toolkit build requires the exact torch 2.5.1+cu124 target')
    headers, includes = [], [str(root / 'include')]
    for name in REQUIRED_TOOLKIT_FILES:
        path = _inside(root / name, root)
        if not path.is_file():
            raise ValueError(f'CUDA 12.4 toolkit closure missing {name}')
        if name.startswith(('bin/', 'nvvm/bin/')) and not path.stat().st_mode & 0o111:
            raise ValueError(f'toolkit compiler executable mode missing: {name}')
        headers.append(dict(file_record(path), role='toolkit', requested_path=str(path)))
    packages = [dict(name='torch', version=torch_meta['Version'], metadata=torch_record)]
    requirements = torch_meta.get_all('Requires-Dist', [])
    for name, (subdir, required) in WHEEL_HEADERS.items():
        expression = r'^' + re.escape(name) + r'\s*\(?\s*==\s*([^;,)\s]+)'
        versions = {match.group(1) for req in requirements
                    if (match := re.match(expression, req, flags=re.I))}
        if len(versions) != 1:
            raise ValueError(f'exact torch metadata must pin {name}')
        package, package_record = _metadata(site, name)
        if package.get('Version') != next(iter(versions)):
            raise ValueError(f'{name} differs from the exact cu124 torch requirement')
        include = safe_path(site / 'nvidia' / subdir / 'include')
        if not include.is_dir() or any(not (include / header).is_file() for header in required):
            raise ValueError(f'cu124 header closure missing {name}: {required}')
        includes.append(str(include))
        # Retain all companion headers, including unlisted transitive includes.
        for base, dirs, names in os.walk(include, followlinks=False):
            dirs[:] = sorted(d for d in dirs if d != 'prompts')
            for filename in sorted(names):
                if filename == 'prompts':
                    continue
                path = safe_path(Path(base) / filename)
                if path.is_symlink() or not path.is_file():
                    raise ValueError('cu124 wheel header tree contains a symlink or special file')
                headers.append(dict(file_record(path), role=name))
        packages.append(dict(name=name, version=package['Version'], metadata=package_record,
                             required_by_torch=next(iter(versions))))
    environment = dict(CUDA_HOME=str(root),
        PATH=os.pathsep.join((str(root / 'bin'), str(env_root / 'bin'), os.environ.get('PATH', ''))),
        CPATH=os.pathsep.join(includes), TORCH_CUDA_ARCH_LIST='8.9',
        SAM2_BUILD_CUDA='1', SAM2_BUILD_ALLOW_ERRORS='0', MAX_JOBS='8')
    return dict(env=environment, headers=headers, packages=packages,
                toolkit_receipt=toolkit_record.get('receipt'),
                verification='required local headers and hashes; native build not executed')
