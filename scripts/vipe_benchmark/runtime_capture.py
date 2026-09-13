"""Record modules and native libraries actually loaded by an allocated worker."""
from pathlib import Path
import sys

from .files import file_record, safe_path, write_json


def loaded_runtime(output, *, modules=None, maps_path=Path('/proc/self/maps')):
    modules = sys.modules if modules is None else modules
    names = {}
    for name, module in list(modules.items()):
        filename = getattr(module, '__file__', None)
        if filename is None:
            continue
        path = safe_path(filename).resolve()
        if not path.is_file():
            continue
        names.setdefault(path, []).append(name)
    libraries = set()
    for line in safe_path(maps_path).read_text().splitlines():
        fields = line.split(maxsplit=5)
        if len(fields) != 6 or not fields[5].startswith('/'):
            continue
        filename = fields[5]
        if '.so' not in Path(filename).name:
            continue
        if filename.endswith(' (deleted)'):
            raise ValueError('loaded native library was deleted before provenance capture')
        libraries.add(safe_path(filename).resolve())
    files = []
    for path in sorted(set(names) | libraries):
        files.append(dict(file_record(path), modules=sorted(names.get(path, [])),
                          mapped_native_library=path in libraries))
    write_json(output, dict(schema='vipe-benchmark-loaded-runtime/v1', files=files,
                           interpreter=dict(version=sys.version, executable=file_record(sys.executable),
                                            invoked_executable=sys.executable, prefix=sys.prefix, base_prefix=sys.base_prefix),
                           moment='after the first allocated real result',
                           new_imports=False, new_inference=False))
    return file_record(output)
