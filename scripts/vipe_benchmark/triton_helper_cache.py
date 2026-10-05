"""Hash-bound prebuilt Triton CUDA helper cache for subprocess-free GPU-aware imports.

Triton compiles its ``cuda_utils`` C helper with ldconfig/gcc on a cache miss when the
CUDA driver is first initialized. A separately metered CPU step builds that helper once
with Triton's own code path into a run-owned cache; a guarded worker may then point
``TRITON_CACHE_DIR`` at the verified cache and prove afterwards that nothing changed.
"""
import base64
import hashlib
import os
import sys
from pathlib import Path

from .files import file_record, read_json, verify_record

SCHEMA = 'plan069-triton-helper-cache/v1'
# Triton >= 3.3 keys its helper cache by source, platform and compile configuration, and resolves
# libcuda eagerly; v2 bindings record a fixed TRITON_LIBCUDA_PATH so neither builder nor worker runs ldconfig.
SCHEMA_V2 = 'plan069-triton-helper-cache/v2'
LIBCUDA_DIRECTORY = '/usr/lib/x86_64-linux-gnu'
HELPER = 'cuda_utils'


def require(value, message):
    if not value:
        raise ValueError(message)


def driver_source(triton_directory):
    """Return the installed Triton NVIDIA driver helper source record."""
    return file_record(Path(triton_directory) / 'backends/nvidia/driver.c')


def cache_key(source_bytes):
    # Triton hashes the UTF-8 text it reads; decoding first rejects non-UTF-8 sources.
    return hashlib.sha256(source_bytes.decode('utf-8').encode('utf-8')).hexdigest()


def cache_directory_name(key):
    """Triton 3.2 runtime.cache._base64: the per-key directory under TRITON_CACHE_DIR."""
    return base64.urlsafe_b64encode(bytes.fromhex(key)).decode('utf-8').rstrip('=')


def installed_version(triton_directory):
    """Read __version__ from the installed package without importing Triton."""
    for line in (Path(triton_directory) / '__init__.py').read_text().splitlines():
        if line.startswith('__version__ = '):
            return line.split('=', 1)[1].strip().strip('\'"')
    raise ValueError('installed Triton version missing')


def manifest(cache_directory):
    """List every directory and file under the cache; reject links and specials."""
    root = Path(cache_directory)
    require(root.is_dir() and not root.is_symlink() and root.absolute() == root.resolve(),
            'Triton helper cache must be a literal physical directory')
    directories, files = [], []
    for current, names, filenames in os.walk(root, followlinks=False):
        for name in sorted(names):
            path = Path(current) / name
            require(not path.is_symlink(), 'Triton helper cache contains a link')
            directories.append(str(path.relative_to(root)))
        for name in sorted(filenames):
            path = Path(current) / name
            require(path.is_file() and not path.is_symlink(), 'Triton helper cache contains a non-regular file')
            files.append(dict(relative_path=str(path.relative_to(root)), record=file_record(path)))
    return dict(directories=sorted(directories), files=sorted(files, key=lambda row: row['relative_path']))


def _helper_name():
    import sysconfig
    return HELPER + sysconfig.get_config_var('EXT_SUFFIX')


def build_v2(cache_directory, output_directory):
    """Build the Triton >= 3.3 helper through Triton's own CudaUtils; CPU only, GPUs hidden."""
    import shutil
    import time
    from .files import write_json
    start = time.monotonic()
    cache, out = Path(cache_directory).absolute(), Path(output_directory).absolute()
    require(not cache.exists() and not out.exists(), 'fresh Triton helper cache and output required')
    require(os.environ.get('CUDA_VISIBLE_DEVICES') == '', 'Triton helper build must hide GPUs')
    require(not any(name.startswith('TRITON_') for name in os.environ), 'inherited Triton environment rejected')
    libcuda = Path(LIBCUDA_DIRECTORY) / 'libcuda.so.1'
    require(libcuda.is_file(), 'host libcuda.so.1 required in the bound directory')
    out.mkdir(parents=True)
    cache.mkdir(parents=True)
    os.environ.update(TRITON_CACHE_DIR=str(cache), TRITON_LIBCUDA_PATH=LIBCUDA_DIRECTORY)
    import triton
    require(tuple(int(part) for part in triton.__version__.split('.')[:2]) >= (3, 3),
            'the v2 helper cache requires Triton >= 3.3')
    from triton.backends.nvidia.driver import CudaUtils
    triton_directory = Path(triton.__file__).parent
    CudaUtils()
    receipt = dict(schema='plan069-triton-helper-build/v2', record_kind='actual', helper=HELPER,
                   python=str(Path(sys.executable).absolute()), triton_version=triton.__version__,
                   compiler=os.environ.get('CC') or shutil.which('gcc') or shutil.which('clang'),
                   libcuda_path=LIBCUDA_DIRECTORY, cuda_visible_devices='', gpu_operations=False,
                   elapsed_seconds=time.monotonic() - start)
    write_json(out / 'build-receipt.json', receipt)
    binding = dict(schema=SCHEMA_V2, status='built', helper=HELPER, cache_directory=str(cache),
                   triton_version=triton.__version__, driver_source=driver_source(triton_directory),
                   libcuda_path=LIBCUDA_DIRECTORY, libcuda=file_record(libcuda), helper_file=_helper_name(),
                   manifest=manifest(cache),
                   build_receipt=file_record(out / 'build-receipt.json'))
    write_json(out / 'binding.json', binding)
    validate_binding(file_record(out / 'binding.json'), triton_directory=triton_directory)
    return out / 'binding.json'


def build(cache_directory, output_directory):
    """Build the helper once with Triton's own code path; CPU only, no GPU initialization."""
    import shutil
    import time
    from .files import write_json
    start = time.monotonic()
    cache, out = Path(cache_directory).absolute(), Path(output_directory).absolute()
    require(not cache.exists() and not out.exists(), 'fresh Triton helper cache and output required')
    require(os.environ.get('CUDA_VISIBLE_DEVICES') == '', 'Triton helper build must hide GPUs')
    require(not any(name.startswith('TRITON_') for name in os.environ), 'inherited Triton environment rejected')
    out.mkdir(parents=True)
    cache.mkdir(parents=True)
    os.environ['TRITON_CACHE_DIR'] = str(cache)
    import triton
    from triton.backends.nvidia import driver
    triton_directory = Path(triton.__file__).parent
    source = driver_source(triton_directory)
    driver.compile_module_from_src(Path(source['path']).read_text(), HELPER)
    receipt = dict(schema='plan069-triton-helper-build/v1', record_kind='actual', helper=HELPER,
                   python=str(Path(sys.executable).absolute()), triton_version=triton.__version__,
                   compiler=os.environ.get('CC') or shutil.which('gcc') or shutil.which('clang'),
                   cuda_visible_devices='', gpu_operations=False, elapsed_seconds=time.monotonic() - start)
    write_json(out / 'build-receipt.json', receipt)
    binding = dict(schema=SCHEMA, status='built', helper=HELPER, cache_directory=str(cache),
                   triton_version=triton.__version__, driver_source=source,
                   key=cache_key(Path(source['path']).read_bytes()), manifest=manifest(cache),
                   build_receipt=file_record(out / 'build-receipt.json'))
    write_json(out / 'binding.json', binding)
    validate_binding(file_record(out / 'binding.json'), triton_directory=triton_directory)
    return out / 'binding.json'


def validate_binding(binding_record, *, triton_directory=None):
    """Verify the bound cache bytes, layout and Triton source; return the binding."""
    binding = read_json(verify_record(binding_record)['path'])
    if binding.get('schema') == SCHEMA_V2:
        return _validate_v2(binding, triton_directory)
    require(binding.get('schema') == SCHEMA and binding.get('helper') == HELPER and
            binding.get('status') == 'built', 'exact built Triton helper cache binding required')
    source = verify_record(binding['driver_source'])
    if triton_directory is not None:
        require(driver_source(triton_directory) == source, 'installed Triton driver source differs from cache binding')
        require(installed_version(triton_directory) == binding.get('triton_version'),
                'installed Triton version differs from cache binding')
    key = cache_key(Path(source['path']).read_bytes())
    require(binding.get('key') == key, 'Triton helper cache key differs from driver source')
    cache = Path(binding['cache_directory'])
    require(manifest(cache) == binding.get('manifest'), 'Triton helper cache contents changed')
    helpers = [row for row in binding['manifest']['files'] if Path(row['relative_path']).name.startswith(HELPER + '.')]
    require(len(helpers) == 1 and len(binding['manifest']['files']) == 1 and
            helpers[0]['relative_path'] == cache_directory_name(key) + '/' + HELPER + '.so' and
            binding['manifest']['directories'] == [cache_directory_name(key)],
            'exactly one cached cuda_utils helper at the Triton key directory required')
    require(binding.get('triton_version') and binding.get('build_receipt'), 'Triton cache provenance required')
    verify_record(binding['build_receipt'])
    return binding


def _validate_v2(binding, triton_directory):
    require(binding.get('helper') == HELPER and binding.get('status') == 'built' and binding.get('triton_version') and
            binding.get('libcuda_path') == LIBCUDA_DIRECTORY and
            verify_record(binding['libcuda']) == binding['libcuda'] and
            Path(binding['libcuda']['path']) == (Path(LIBCUDA_DIRECTORY) / 'libcuda.so.1').resolve(),
            'exact built Triton v2 helper cache binding required')
    source = verify_record(binding['driver_source'])
    if triton_directory is not None:
        require(driver_source(triton_directory) == source, 'installed Triton driver source differs from cache binding')
        require(installed_version(triton_directory) == binding.get('triton_version'),
                'installed Triton version differs from cache binding')
    cache = Path(binding['cache_directory'])
    require(manifest(cache) == binding.get('manifest'), 'Triton helper cache contents changed')
    files, directories = binding['manifest']['files'], binding['manifest']['directories']
    name = binding.get('helper_file', '')
    require(name.startswith(HELPER + '.') and name.endswith('.so') and '/' not in name and
            len(files) == 1 and len(directories) == 1 and files[0]['relative_path'] == directories[0] + '/' + name,
            'exactly one cached cuda_utils helper in one Triton key directory required')
    build = read_json(verify_record(binding['build_receipt'])['path'])
    require(build.get('schema') == 'plan069-triton-helper-build/v2' and build.get('libcuda_path') == LIBCUDA_DIRECTORY and
            build.get('gpu_operations') is False and build.get('triton_version') == binding.get('triton_version'),
            'Triton v2 cache provenance required')
    return binding
