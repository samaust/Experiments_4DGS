"""CPU-only pinned dependency checks before D8/D11 runtime smoke."""

from importlib import metadata
import json


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
    found = {}
    for name in names:
        try:
            dist = metadata.distribution(name)
            direct = dist.read_text('direct_url.json')
            found[name] = dict(version=dist.version,
                direct_url=json.loads(direct) if direct else None)
        except metadata.PackageNotFoundError:
            found[name] = None
    return found


def blockers(candidate, packages):
    if candidate == 'D8':
        problems = [f'{name} missing' for name in D8_REQUIRED if not packages.get(name)]
        torch = packages.get('torch') or {}
        version = torch.get('version', '').split('+', 1)[0]
        major_minor = version.split('.')[:2]
        if len(major_minor) != 2 or not all(part.isdigit() for part in major_minor) or \
                tuple(map(int, major_minor)) >= (2, 5):
            problems.append('D8 requires torch<2.5.0')
        utils = packages.get('utils3d') or {}
        vcs = (utils.get('direct_url') or {}).get('vcs_info') or {}
        if vcs.get('commit_id') != D8_UTILS3D_REVISION:
            problems.append('D8 requires pinned utils3d Git revision')
        return problems
    if candidate == 'D11':
        problems = []
        for name, exact in D11_PINNED.items():
            entry = packages.get(name)
            if entry is None:
                problems.append(name + ' missing')
            elif exact is not None and entry.get('version', '').split('+', 1)[0] != exact:
                problems.append(name + ' differs from pinned version ' + exact)
        h5py = packages.get('h5py') or {}
        h5py_parts = h5py.get('version', '').split('.')[:2]
        if len(h5py_parts) != 2 or not all(part.isdigit() for part in h5py_parts) or \
                tuple(map(int, h5py_parts)) < (3, 10):
            problems.append('h5py requires version >=3.10')
        return problems
    raise ValueError('unsupported native dependency candidate')
