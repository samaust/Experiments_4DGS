"""Pinned offline RoMa preparation and lazy CUDA geometry backend.

An inventory binds bytes, not execution permission or successful qualification.
The supervised worker verifies admission before calling any model operation.
"""
import csv
from email.parser import Parser
import re
import subprocess
import sys
from pathlib import Path

from .files import file_record, read_json, safe_path, verify_record, write_json
from .final_render_geometry import _matching_helpers

SCHEMA = 'plan069-final-render-matcher-runtime/v1'
DEPENDENCIES = {'torch','einops','torchvision','opencv-python','kornia','albumentations',
    'loguru','tqdm','matplotlib','h5py','wandb','timm','poselib','numpy','Pillow'}

OPENCV_PROVIDERS = {'opencv-python','opencv-python-headless'}

FIELDS = {'schema','record_kind','status','checkout','weights','revision',
    'environment_prefix','interpreter','dependencies','source_files','checkout_files'}


def required_sources():
    scripts = Path(__file__).resolve().parents[1]
    return [file_record(scripts/name) for name in ('edgs_source.py','triangulation.py',
        'basketball_temporal_cloud.py','basketball_temporal_geometry.py',
        'vipe_benchmark/final_render_matcher.py','vipe_benchmark/final_render_geometry.py',
        'vipe_benchmark/diagnostics.py','vipe_benchmark/geometry.py',
        'vipe_benchmark/final_render_loaders.py')]


def _checkout_files(checkout, revision):
    checkout = safe_path(checkout)
    def git(*args):
        return subprocess.check_output(['git','-C',str(checkout),*args],text=True).strip()
    if git('rev-parse','HEAD') != revision or git('status','--porcelain','--untracked-files=no'):
        raise ValueError('expected clean EDGS-pinned RoMa revision')
    names = git('ls-files','-z').split('\0')
    if not names or names == ['']:
        raise ValueError('empty RoMa source checkout')
    records = []
    for name in names:
        if not name:
            continue
        path = safe_path(checkout/name)
        if not path.resolve().is_relative_to(checkout.resolve()):
            raise ValueError('RoMa checkout source escapes checkout')
        records.append(file_record(path))
    return records


def _dependencies(records, environment, *, active=False):
    """Require complete installed distribution bytes, not a metadata-only list."""
    by_path = {}
    for record in records:
        path = safe_path(record['path']).resolve()
        if path in by_path or not path.is_relative_to(environment):
            raise ValueError('duplicate or escaped matcher dependency file')
        by_path[path] = record
    metadata = {}
    for path in by_path:
        if path.name == 'METADATA' and path.parent.name.endswith('.dist-info'):
            value = Parser().parsestr(path.read_text())
            names = value.get_all('Name') or []
            if len(names) != 1:
                raise ValueError('ambiguous matcher dependency metadata')
            name = re.sub(r'[-_.]+','-',names[0]).lower()
            if name in metadata:
                raise ValueError('duplicate matcher dependency distribution')
            metadata[name] = path
    providers = OPENCV_PROVIDERS.intersection(metadata)
    if len(providers) != 1:
        raise ValueError('exactly one OpenCV provider required for matcher runtime')
    required = (DEPENDENCIES-{'opencv-python'}) | providers
    for name in required:
        canonical = re.sub(r'[-_.]+','-',name).lower()
        if canonical not in metadata:
            raise ValueError('missing complete matcher dependency: '+name)
        source = metadata[canonical]
        record_path = source.parent/'RECORD'
        if record_path not in by_path:
            raise ValueError('missing matcher dependency RECORD: '+name)
        for row in csv.reader(record_path.read_text().splitlines()):
            if not row:
                continue
            relative = Path(row[0])
            if 'prompts' in relative.parts or '__pycache__' in relative.parts or relative.suffix in ('.pyc','.pyo'):
                continue
            resolved = (source.parent.parent/relative).resolve()
            if not resolved.is_relative_to(environment) or resolved not in by_path:
                raise ValueError('incomplete matcher dependency files: '+name)
        if active:
            from importlib.metadata import distribution
            installed = distribution(name)
            matches = [installed.locate_file(path) for path in installed.files or []
                if Path(path).name == 'METADATA' and Path(path).parent.name.endswith('.dist-info')]
            if len(matches) != 1 or file_record(matches[0]) != by_path[source]:
                raise ValueError('active matcher dependency differs: '+name)


def validate_inventory(inventory, *, active=False):
    if (type(inventory) is not dict or set(inventory) != FIELDS or
            inventory['schema'] != SCHEMA or inventory['record_kind'] != 'actual' or
            inventory['status'] != 'prepared'):
        raise ValueError('exact prepared matcher inventory required')
    _,_,revision,weights = _matching_helpers()
    if inventory['revision'] != revision or set(inventory['weights']) != set(weights):
        raise ValueError('historical RoMa pins differ')
    for name,record in inventory['weights'].items():
        if Path(record['path']).name != name or record['sha256'] != weights[name]:
            raise ValueError('checkpoint hash mismatch: '+name)
    sources = inventory['source_files']
    if type(sources) is not list or sources != required_sources():
        raise ValueError('matcher source inventory differs')
    if inventory['checkout_files'] != _checkout_files(inventory['checkout'],revision):
        raise ValueError('RoMa checkout file inventory differs')
    dependencies = inventory['dependencies']
    if type(dependencies) is not list or not dependencies:
        raise ValueError('explicit matcher dependency files required')
    environment = safe_path(inventory['environment_prefix']).resolve()
    if any(not safe_path(record['path']).resolve().is_relative_to(environment) for record in dependencies):
        raise ValueError('matcher dependencies outside exact environment')
    _dependencies(dependencies,environment,active=active)
    records = [inventory['interpreter'],*sources,*inventory['checkout_files'],
        *inventory['weights'].values(),*dependencies]
    for record in records:
        if type(record) is not dict or set(record) != {'path','sha256','bytes'} or verify_record(record) != record:
            raise ValueError('matcher runtime file changed')
    if active and (environment != Path(sys.prefix).resolve() or
            inventory['interpreter'] != file_record(sys.executable)):
        raise ValueError('matcher interpreter/environment differs')
    return inventory


def prepare_inventory(*, checkout, weights, environment_prefix, interpreter, dependencies, output):
    """Freeze explicit local inputs CPU-only; incorrect weights never publish."""
    _,_,revision,names = _matching_helpers()
    records = {name:file_record(safe_path(weights)/name) for name in names}
    # Reject incorrect checkpoints before inspecting or freezing the checkout.
    for name,record in records.items():
        if record['sha256'] != names[name]:
            raise ValueError('checkpoint hash mismatch: '+name)
    inventory = dict(schema=SCHEMA,record_kind='actual',status='prepared',
        checkout=str(safe_path(checkout).resolve()),weights=records,revision=revision,
        environment_prefix=str(safe_path(environment_prefix).resolve()),interpreter=interpreter,
        dependencies=dependencies,source_files=required_sources(),checkout_files=_checkout_files(checkout,revision))
    validate_inventory(inventory)
    write_json(output,inventory)
    return inventory


class NativeGeometryBackend:
    """Lazy unchanged native matcher/solver; no fixture SDK or CPU fallback."""
    record_kind = 'actual'

    def __init__(self, inventory_record):
        if verify_record(inventory_record) != inventory_record:
            raise ValueError('matcher inventory changed')
        self.inventory_record = dict(inventory_record)
        self.inventory = validate_inventory(read_json(inventory_record['path']))
        self.backend = None
        self.closed = False
        self.invocation = None

    def bind_worker(self, invocation_record, request, arm):
        """Validate actual root-process admission centrally before model loading."""
        from .final_render_admission import worker_binding
        binding = worker_binding(invocation_record,request,arm,'geometry')
        if binding.get('matcher_runtime') != self.inventory_record:
            raise ValueError('admitted matcher runtime differs')
        self.invocation = (invocation_record,request,arm)

    def _load(self):
        if self.closed:
            raise ValueError('matcher runtime is closed')
        if self.invocation is None:
            raise ValueError('matcher model loading requires admitted worker invocation')
        if self.backend is None:
            from .final_render_admission import worker_binding
            invocation,request,arm = self.invocation
            binding = worker_binding(invocation,request,arm,'geometry')
            if binding.get('matcher_runtime') != self.inventory_record:
                raise ValueError('admitted matcher runtime differs')
            if verify_record(self.inventory_record) != self.inventory_record:
                raise ValueError('matcher inventory changed')
            validate_inventory(self.inventory,active=True)
            if 'romatch' in sys.modules:
                raise ValueError('matcher needs a fresh process')
            from .diagnostics import NativeBackend
            weight_paths = [safe_path(record['path']).parent for record in self.inventory['weights'].values()]
            if len(set(weight_paths)) != 1:
                raise ValueError('matcher weights require one pinned directory')
            self.backend = NativeBackend(self.inventory['checkout'],weight_paths[0])
        return self.backend

    @property
    def sample_thresh(self):
        return self._load().model.sample_thresh

    def match(self, first, second):
        return self._load().match(first,second)

    def crop(self, warp, probability, images, labels, ids):
        return self._load().crop(warp,probability,images,labels,ids)

    def triangulate(self, P0, P1, uv0, uv1):
        return self._load().triangulate(P0,P1,uv0,uv1)

    def usage(self):
        if self.backend is None:
            return dict(peak_device_bytes=0,cpu_workers_used=1)
        resources = self.backend.resources()
        return dict(peak_device_bytes=max(resources['peak_allocated_bytes'],resources['peak_reserved_bytes'],
            resources['peak_observed_device_bytes']),cpu_workers_used=self.backend.torch.get_num_threads())

    def close(self):
        if self.backend is not None:
            torch = self.backend.torch
            self.backend.model = None
            torch.cuda.synchronize()
            torch.cuda.empty_cache()
        self.closed = True
