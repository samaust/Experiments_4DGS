"""One concrete dependency resolution per prescribed environment."""
from pathlib import Path
import shutil

from .files import read_json, verify_record
from .runtime import ENVIRONMENTS, TARGETS

BUILD_REQUIREMENTS = ['pip', 'setuptools==80.9.0', 'wheel', 'packaging', 'ninja']
COMMON_REQUIREMENTS = ['safetensors', 'huggingface-hub', 'psutil', 'Pillow', 'opencv-python']
EXTRAS = {
    'E1': ['transformers==4.30.2', 'addict==2.4.0', 'yapf==0.40.2', 'timm==0.4.5',
           'opencv-python==4.10.0.84', 'Pillow==10.4.0', 'scikit-image==0.24.0',
           'matplotlib==3.9.2', 'supervision==0.22.0', 'pycocotools==2.0.8', 'scipy', 'einops'],
    'E2': ['transformers==4.51.3', 'addict', 'yapf', 'timm', 'opencv-python',
           'supervision>=0.22.0', 'pycocotools', 'tqdm>=4.66.1', 'hydra-core>=1.3.2',
           'iopath>=0.1.10', 'pillow>=9.4.0', 'scipy', 'einops'],
    'E3': ['timm>=1.0.17', 'ftfy==6.1.1', 'regex', 'iopath>=0.1.10', 'typing_extensions',
           'huggingface_hub', 'tqdm', 'einops', 'scipy', 'pycocotools', 'psutil', 'opencv-python', 'pillow'],
    'E4': ['xformers==0.0.28.post3', 'torchaudio==2.5.1+cu124', 'einops>=0.7.0', 'gradio',
           'h5py>=3.10.0', 'huggingface-hub>=0.22.0', 'imageio', 'matplotlib', 'opencv-python',
           'pandas', 'pillow>=10.2.0', 'protobuf>=4.25.3', 'scipy', 'tables', 'tabulate',
           'termcolor', 'timm', 'tqdm', 'trimesh', 'triton>=2.4.0', 'wandb'],
    'E5': ['xformers==0.0.28.post3', 'pre-commit', 'trimesh', 'einops', 'huggingface_hub',
           'imageio', 'opencv-python', 'open3d', 'fastapi', 'uvicorn', 'requests', 'typer>=0.9.0',
           'pillow', 'omegaconf', 'evo', 'e3nn', 'moviepy==1.0.3', 'plyfile', 'pillow_heif',
           'safetensors', 'pycolmap', 'hatchling>=1.25', 'hatch-vcs>=0.4', 'scipy', 'addict'],
    'E6': ['xformers==0.0.21', 'opencv-python', 'Pillow', 'DateTime', 'matplotlib', 'plyfile',
           'HTML4Vision', 'timm', 'tensorboardX', 'imgaug', 'iopath', 'imagecorruptions', 'mmcv==1.7.2', 'yapf==0.40.1', 'scipy'],
    'E7': ['timm', 'pillow_heif', 'matplotlib', 'pillow', 'setuptools-scm', 'opencv-python', 'scipy'],
}
EDITABLE = {'E1': ['sam_source', 'grounding_source'], 'E2': ['grounding_source', 'sam2_source'],
            'E3': ['sam3_source'], 'E4': ['unidepth_source'], 'E5': ['da3_source'], 'E6': [],
            'E7': ['depth_pro_source']}

# Import-only qualification: never call these builders or a model's forward.
# Each tuple identifies a module, its required source asset (None means an
# installed distribution), and symbols whose lazy imports must also succeed.
CORE_IMPORTS = {
    'E1': [('segment_anything', 'sam_source', ['SamPredictor']),
           ('groundingdino._C', 'grounding_source', []),
           ('groundingdino.util.inference', 'grounding_source', ['predict']),
           ('aot_tracker', 'samtrack_source', ['get_aot']),
           ('configs.pre_ytb_dav', 'aot_source', ['EngineConfig']),
           ('networks.layers.attention', 'aot_source', ['enable_corr']),
           ('aot.networks.layers.attention', 'aot_source', ['enable_corr']),
           ('spatial_correlation_sampler', None, ['SpatialCorrelationSampler'])],
    'E2': [('groundingdino._C', 'grounding_source', []),
           ('groundingdino.util.inference', 'grounding_source', ['predict']),
           ('sam2._C', 'sam2_source', []),
           ('sam2.build_sam', 'sam2_source', ['build_sam2', 'build_sam2_video_predictor']),
           ('sam2.sam2_image_predictor', 'sam2_source', ['SAM2ImagePredictor']),
           ('sam2.sam2_video_predictor', 'sam2_source', ['SAM2VideoPredictor']),
           ('transformers', None, ['RTDetrImageProcessor', 'RTDetrV2ForObjectDetection'])],
    'E3': [('sam3.model_builder', 'sam3_source', ['build_sam3_image_model', 'build_sam3_video_model']),
           ('sam3.model.sam3_image_processor', 'sam3_source', ['Sam3Processor']),
           ('sam3.model.sam3_video_inference', 'sam3_source', ['Sam3VideoInferenceWithInstanceInteractivity']),
           ('sam3.perflib.triton.connected_components', 'sam3_source', ['connected_components_triton']),
           ('sam3.perflib.triton.nms', 'sam3_source', ['nms_triton'])],
    'E4': [('unidepth.models', 'unidepth_source', ['UniDepthV2']), ('xformers.ops', None, [])],
    'E5': [('depth_anything_3.api', 'da3_source', ['DepthAnything3']), ('xformers.ops', None, [])],
    'E6': [('hubconf', 'metric3d_source', ['metric3d_vit_large']),
           ('mono.model.monodepth_model', 'metric3d_source', ['get_configured_monodepth_model']),
           ('mmcv.utils', None, ['Config']), ('xformers.ops', None, [])],
    'E7': [('depth_pro.depth_pro', 'depth_pro_source', ['create_model_and_transforms'])],
}


def recipe(environment):
    if environment not in EXTRAS:
        raise ValueError('only seven prescribed new environments may be built')
    base = [f'{k}=={v}' for k, v in TARGETS[environment].items() if k != 'python'] + BUILD_REQUIREMENTS
    return dict(base_requirements=base, requirements=base + COMMON_REQUIREMENTS + EXTRAS[environment],
        editable_sources=EDITABLE[environment],
        native_correlation='spatial-correlation-sampler==0.5.0' if environment == 'E1' else None,
        cuda_toolkit='12.4.1' if environment in ('E1', 'E2') else None)


def request(local, environment):
    if environment not in EXTRAS:
        raise ValueError('only seven prescribed new environments may be built')
    local = Path(local).resolve()
    uv = shutil.which('uv')
    if not uv:
        raise ValueError('existing uv executable unavailable')
    historical = read_json(local / 'qualification/historical-assets.json')
    # Source build trees are not shared: setup may generate version.py or native
    # extensions. Share only verified weight bytes via historical assets.
    return dict(job_id=environment + '-setup', environment=environment,
        components=sorted(c for c, e in ENVIRONMENTS.items() if e == environment),
        historical_assets=historical['assets'], historical_parent=historical['parent'],
        run_root=str(local), forbidden_vipe_roots=[historical['assets']['vipe_source']['path']],
        reuse_assets={}, uv=uv, uv_cache=str(local / 'setup-cache'),
        python_install_dir=str(local / 'managed-python'), transfer_dir=str(local / 'transfers'),
        **recipe(environment),
        toolkit_directory=str(local / 'toolkits/cuda-12.4.1'),
        source_default_dependencies='include pinned source default inference dependency lists; no optional app/gs/train extras',
        no_runtime_fallback=True, no_automatic_retry=True)


def recovery_request(local, authorization):
    """Use the user's registered recovery and its verified asset preparation."""
    from .config import load
    from .ledger import Ledger
    from .backends import REQUIRED_ASSETS
    document = read_json(verify_record(authorization)['path'])
    events = Ledger(Path(local) / 'ledger.jsonl', load()).events()
    matching = [event for event in events if event['event'] == 'setup_recovery_authorized' and
                event['authorization'] == authorization and event['job_id'] == document['job_id']]
    if len(matching) != 1 or document['environment'] not in ('E1', 'E3'):
        raise ValueError('SAM3 recovery is not registered in this run')
    if document['environment'] == 'E1':
        result = request(local, 'E1')
        result.update(job_id=document['job_id'], recovery_authorization=authorization)
        return result
    preparation = read_json(verify_record(document['asset_preparation'])['path'])
    assets = read_json(verify_record(preparation['assets'])['path'])
    result = request(local, 'E3')
    # A new editable build must not mutate the immutable preparation source.
    # Re-extract its verified archive into the fresh recovery output instead.
    result.update(job_id=document['job_id'], recovery_authorization=authorization,
        reuse_assets={name: assets[name] for name in REQUIRED_ASSETS['S3']
                      if name not in ('sam3_source', 'bpe_vocabulary')},
        reuse_source_archives={'sam3_source': assets['sam3_source']['archive']})
    return result
