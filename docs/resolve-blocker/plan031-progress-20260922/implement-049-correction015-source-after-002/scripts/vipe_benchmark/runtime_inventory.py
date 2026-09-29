"""Read an installed environment without importing models or touching CUDA."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys


def inventory():
    packages = []
    for dist in importlib.metadata.distributions():
        metadata = dist.metadata
        files = []
        for relative in dist.files or []:
            if 'prompts' in Path(relative).parts:
                continue
            name = str(relative).lower()
            if '__pycache__' in Path(name).parts or name.endswith(('.pyc', '.pyo')):
                continue
            path = Path(dist.locate_file(relative))
            if 'prompts' in path.resolve().parts or not path.is_file():
                continue
            with path.open('rb') as stream:
                accumulator = hashlib.sha256()
                while block := stream.read(2**20):
                    accumulator.update(block)
                checksum = accumulator.hexdigest()
            files.append(dict(path=str(path.absolute()), sha256=checksum, bytes=path.stat().st_size))
        packages.append(dict(name=metadata['Name'], version=dist.version,
                             license=metadata.get('License-Expression', metadata.get('License')),
                             classifiers=metadata.get_all('Classifier', []), files=files))
    versions = {'python': f'{sys.version_info.major}.{sys.version_info.minor}'}
    for name in ('torch', 'torchvision', 'numpy'):
        versions[name] = importlib.metadata.version(name)
    return dict(versions=versions, executable=sys.executable, packages=sorted(packages, key=lambda r: r['name'].lower()),
                inventory_only=True, model_imports=False, gpu_operations=False,
                scope='all installed distribution files except ephemeral Python bytecode; source, native libraries and notices hashed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    with args.output.open('x') as stream:
        json.dump(inventory(), stream, indent=2)
        stream.write('\n')
