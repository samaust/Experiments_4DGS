"""Load the exact local MoGe checkpoint through its pinned native model class."""

import importlib
from pathlib import Path
import sys

from .files import verify_record
from .moge_metric import MoGe2Adapter, MoGe3Adapter


def load_adapter(candidate, source_dir, checkpoint_record, *, device='cuda'):
    """Require a complete state dict and never fall back to a Hub download."""
    if candidate not in ('D5', 'D6'):
        raise ValueError('MoGe native candidate must be D5 or D6')
    source = Path(source_dir).resolve()
    version = 'v2' if candidate == 'D5' else 'v3'
    expected_module = source / 'moge/model' / (version + '.py')
    if not expected_module.is_file() or not (source / 'LICENSE').is_file():
        raise ValueError('pinned MoGe native source and license required')
    checkpoint = Path(verify_record(checkpoint_record)['path']).resolve()
    if checkpoint.name != 'model.pt':
        raise ValueError('pinned MoGe model.pt required')
    if not source.is_relative_to(checkpoint.parent):
        raise ValueError('MoGe source and checkpoint must share one setup output')
    if str(source) not in sys.path:
        sys.path.insert(0, str(source))
    module = importlib.import_module('moge.model.' + version)
    if Path(module.__file__).resolve() != expected_module:
        raise ValueError('loaded MoGe module differs from pinned source')
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
