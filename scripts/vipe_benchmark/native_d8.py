"""Strict native loader for the pinned MetricAnything PointMap student."""

from pathlib import Path

from .files import file_record
from .moge_metric import MetricAnythingPointMapAdapter, POINTMAP_PIN


SOURCE_REVISION = '616a5e6762f5fc40d1a4ef990fee04c800532f59'
WEIGHT_SHA256 = 'f3b49bf78bc2699e79a7c8a53498d4520b30d2c1620c5c4f6f02cc7e94229d58'


def load(setup_result, *, torch_module=None, model_class=None):
    """Construct the exact bundled model with strict weights and no HF fallback."""
    if (setup_result.get('schema') != 'plan069-depth-setup-result/v1' or
            setup_result.get('status') != 'complete' or
            setup_result.get('candidate') != 'D8' or
            setup_result.get('source_revision') != SOURCE_REVISION):
        raise ValueError('D8 requires completed pinned setup')
    assets = setup_result.get('assets', [])
    if len(assets) != 1 or assets[0].get('repository') != 'metricanything' or \
            assets[0].get('path') != 'student_pointmap.pt':
        raise ValueError('D8 requires exact PointMap asset')
    record = assets[0]['record']
    if file_record(record['path']) != record or record['sha256'] != WEIGHT_SHA256:
        raise ValueError('D8 PointMap weights changed')
    source = Path(setup_result['source_dir']) / 'models/student_pointmap'
    if not (source / 'moge/model/v2.py').is_file():
        raise ValueError('D8 bundled MoGe source missing')
    native_source = setup_result.get('native_source')
    if native_source != file_record(source / 'moge/model/v2.py'):
        raise ValueError('D8 bundled MoGe source changed since setup')
    if torch_module is None:
        import torch as torch_module
    if model_class is None:
        import sys
        sys.path.insert(0, str(source))
        from moge.model.v2 import MoGeModel as model_class
        if not Path(sys.modules[model_class.__module__].__file__).resolve().is_relative_to(source.resolve()):
            raise ValueError('D8 imported a different MoGe implementation')
    checkpoint = torch_module.load(record['path'], map_location='cpu', weights_only=True)
    if not isinstance(checkpoint, dict) or not isinstance(checkpoint.get('model_config'), dict) or \
            not isinstance(checkpoint.get('model'), dict):
        raise ValueError('D8 checkpoint structure differs')
    model = model_class(**checkpoint['model_config'])
    model.load_state_dict(checkpoint['model'], strict=True)
    model = model.to('cuda').eval()
    if getattr(model, 'training', True):
        raise ValueError('D8 model must be in eval mode')
    return MetricAnythingPointMapAdapter(model, POINTMAP_PIN)
