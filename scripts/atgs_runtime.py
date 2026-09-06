"""Fingerprint installed native extensions without importing them or using CUDA."""
import hashlib
import importlib.metadata
from pathlib import Path
import sysconfig


EXTENSIONS = ('diff_gaussian_rasterization', 'simple_knn', 'tinycudann_bindings', 'torch_scatter')


def extension_inventory(site_packages):
    root = Path(site_packages)
    inventory = {}
    for component in EXTENSIONS:
        paths = sorted((root / component).glob('*.so'))
        if not paths:
            raise ValueError('missing compiled extension: ' + component)
        for path in paths:
            with path.open('rb') as stream:
                checksum = hashlib.file_digest(stream, 'sha256').hexdigest()
            inventory[str(path.relative_to(root))] = dict(bytes=path.stat().st_size, sha256=checksum)
    return inventory


def runtime_inventory():
    packages = ('torch', 'torchvision', 'numpy', 'mmengine', 'plyfile', 'torch-scatter')
    return dict(schema='atgs-runtime/v1', extensions=extension_inventory(sysconfig.get_paths()['platlib']),
                packages={name: importlib.metadata.version(name) for name in packages},
                scope='current installed extension bytes and package versions; not historical training attestation or full shared-library closure')
