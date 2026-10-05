"""Load the exact local MoGe checkpoint through its pinned native model class."""

import importlib
import os
from pathlib import Path
import sys

from .files import read_json, verify_record
from .moge_metric import MoGe2Adapter, MoGe3Adapter
from .moge_setup import source_tree_records


def load_adapter(candidate, setup_result_record, *, device='cuda'):
    """Require a complete state dict and never fall back to a Hub download."""
    if candidate not in ('D5', 'D6'):
        raise ValueError('MoGe native candidate must be D5 or D6')
    setup = read_json(verify_record(setup_result_record)['path'])
    from .setup_recovery_core import candidate_for_job
    # An approved runtime replacement keeps the original sources and checkpoint in the same layout.
    replaced = candidate_for_job(setup.get('job_id')) == candidate
    if (setup.get('schema') != ('plan069-depth-setup-recovery-result/v1' if replaced else
                                'plan069-depth-setup-result/v1') or
            setup.get('status') != 'complete' or
            setup.get('candidate') != candidate or
            setup.get('source_revision') !=
                '74fbce054ebed49800de42d0ad0e83495065719a'):
        raise ValueError('verified exact MoGe setup result required')
    source = Path(setup['source_dir']).resolve()
    verify_record(setup['source_archive'])
    if source_tree_records(source) != setup.get('source_tree'):
        raise ValueError('MoGe extracted source differs from verified setup')
    version = 'v2' if candidate == 'D5' else 'v3'
    expected_module = source / 'moge/model' / (version + '.py')
    if not expected_module.is_file() or not (source / 'LICENSE').is_file():
        raise ValueError('pinned MoGe native source and license required')
    checkpoint = Path(verify_record(setup['checkpoint'])['path']).resolve()
    if checkpoint.name != 'model.pt':
        raise ValueError('pinned MoGe model.pt required')
    if not source.is_relative_to(checkpoint.parent):
        raise ValueError('MoGe source and checkpoint must share one setup output')
    if str(source) not in sys.path:
        sys.path.insert(0, str(source))
    from .moge_source_build import cache_path, verify_derivation
    runtime_record = verify_record(setup['runtime_environment'])
    if Path(runtime_record['path']).parent != source.parent / 'runtime':
        raise ValueError('MoGe runtime escaped owned setup directory')
    runtime = read_json(runtime_record['path'])
    flex_sources = [row for row in runtime.get('source_packages', []) if row['name'] == 'flex-gemm']
    if len(flex_sources) != 1:
        raise ValueError('verified installed FlexGEMM derivation required')
    verify_derivation(flex_sources[0])
    scoped_cache = str(cache_path(Path(runtime_record['path']).parent))
    if (runtime.get('candidate') != candidate or runtime.get('status') != 'complete' or
            runtime.get('flex_cache_path') != scoped_cache):
        raise ValueError('owned FlexGEMM runtime cache binding required')
    # A source build created this directory as a side effect; a cached-wheel install does not.
    Path(scoped_cache).parent.mkdir(exist_ok=True)
    if not Path(scoped_cache).parent.is_dir() or Path(scoped_cache).parent.is_symlink():
        raise ValueError('owned FlexGEMM runtime cache binding required')
    cached_config = sys.modules.get('flex_gemm.config')
    if cached_config is not None and getattr(cached_config, 'AUTOTUNE_CACHE_PATH', None) != scoped_cache:
        raise ValueError('previous FlexGEMM import used an unowned cache')
    previous_cache = os.environ.get('FLEX_GEMM_AUTOTUNE_CACHE_PATH')
    os.environ['FLEX_GEMM_AUTOTUNE_CACHE_PATH'] = scoped_cache
    # Native imports must preserve the exact extracted source receipt.
    previous_bytecode = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        module = importlib.import_module('moge.model.' + version)
        if module.__file__ is None or Path(module.__file__).resolve() != expected_module:
            raise ValueError('loaded MoGe module differs from pinned source')
        for name, loaded in sys.modules.items():
            if name == 'moge' or name.startswith('moge.'):
                location = getattr(loaded, '__file__', None)
                if location is not None and not Path(location).resolve().is_relative_to(source):
                    raise ValueError('MoGe import closure escaped pinned source')
        import torch
        saved = torch.load(checkpoint, map_location='cpu', weights_only=True)
        if not isinstance(saved, dict) or not {'model_config', 'model'} <= set(saved):
            raise ValueError('MoGe checkpoint payload lacks native config and state')
        model = module.MoGeModel(**saved['model_config'])
        model.load_state_dict(saved['model'], strict=True)
        if candidate == 'D6' and not hasattr(model, 'refiner'):
            raise ValueError('MoGe-3 checkpoint lacks required sparse refiner')
        model = model.to(device).eval()
        return MoGe2Adapter(model) if candidate == 'D5' else MoGe3Adapter(model)
    finally:
        sys.dont_write_bytecode = previous_bytecode
        if previous_cache is None:
            os.environ.pop('FLEX_GEMM_AUTOTUNE_CACHE_PATH', None)
        else:
            os.environ['FLEX_GEMM_AUTOTUNE_CACHE_PATH'] = previous_cache
