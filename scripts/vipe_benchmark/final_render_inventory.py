"""Immutable CPU preparation metadata; never a qualification or admission receipt.

All dependencies and binaries are supplied explicitly. This module neither imports
native libraries nor discovers/downloads assets. Resolved configuration receives
an independent exact native comparison when the admitted runtime is loaded.
"""
from email.parser import Parser
import math
import re
from pathlib import Path

from .final_render_contract import normalization_matrix
from .files import file_record, read_json, safe_path, verify_record, write_json

SCHEMA = 'plan069-final-render-native-runtime/v1'
DEPENDENCIES = {'torch','numpy','scipy','Pillow','torchvision','torchmetrics','gsplat','fused-ssim'}
FIELDS = {'schema','record_kind','status','environment_prefix','interpreter',
    'source_files','binaries','resolved_config','lpips_checkpoint','dependencies'}


def required_sources(checkout):
    """Return current exact adapters and native checkout files without imports."""
    scripts = Path(__file__).resolve().parents[1]
    names = ('freetimegs_training.py','freetimegs_model.py','freetimegs_source.py',
        'freetimegs_checkpoint.py','atgs_sampler.py','training_rng.py','stg_checkpoint.py',
        'offline-python.py','basketball_study_resume_check.py')
    paths = [scripts/name for name in names]
    paths += [Path(__file__).resolve(), scripts/'vipe_benchmark/final_render_native.py',
        scripts/'vipe_benchmark/final_render_adapter.py',
        safe_path(checkout)/'src/utils.py',
        safe_path(checkout)/'src/simple_trainer_freetime_4d_pure_relocation.py']
    return [file_record(path) for path in paths]


def validate_inventory(inventory, *, checkout, environment_prefix=None, interpreter=None,
        normalization=None, scene_scale=None, installed_dependencies=False):
    """Rehash an exact prepared inventory through the native preparation seam."""
    if (type(inventory) is not dict or set(inventory) != FIELDS or
            inventory['schema'] != SCHEMA or inventory['record_kind'] != 'actual' or
            inventory['status'] != 'prepared'):
        raise ValueError('exact prepared native runtime inventory required')
    environment = safe_path(inventory['environment_prefix']).resolve()
    if environment_prefix is not None and environment != safe_path(environment_prefix).resolve():
        raise ValueError('native environment differs')
    sources = inventory['source_files']
    if type(sources) is not list or not all(record in sources for record in required_sources(checkout)):
        raise ValueError('complete current native source inventory required')
    if (type(inventory['binaries']) is not dict or set(inventory['binaries']) != {'gsplat','fused_ssim'} or
            type(inventory['dependencies']) is not dict or set(inventory['dependencies']) != DEPENDENCIES):
        raise ValueError('complete native binaries and dependency metadata required')
    records = [inventory['interpreter'], *sources, *inventory['binaries'].values(),
        inventory['resolved_config'], inventory['lpips_checkpoint']]
    for name, dependency in inventory['dependencies'].items():
        if type(dependency) is not dict or set(dependency) != {'version','metadata','record'}:
            raise ValueError('exact dependency metadata required: '+name)
        records.extend([dependency['metadata'],dependency['record']])
        metadata_path = safe_path(dependency['metadata']['path']).resolve()
        record_path = safe_path(dependency['record']['path']).resolve()
        if (metadata_path.name != 'METADATA' or record_path.name != 'RECORD' or
                metadata_path.parent != record_path.parent or
                not metadata_path.parent.name.endswith('.dist-info') or
                not metadata_path.is_relative_to(environment)):
            raise ValueError('dependency metadata outside exact environment: '+name)
        metadata = Parser().parsestr(metadata_path.read_text())
        identities = metadata.get_all('Name') or []
        if (len(identities) != 1 or
                re.sub(r'[-_.]+','-',identities[0]).lower() != re.sub(r'[-_.]+','-',name).lower() or
                metadata.get_all('Version') != [dependency['version']] or
                not isinstance(dependency['version'],str) or not dependency['version']):
            raise ValueError('dependency identity/version differs: '+name)
        if installed_dependencies:
            from importlib.metadata import distribution
            active = distribution(name)
            # The imported environment must resolve the same installed metadata,
            # not another distribution selected through PYTHONPATH/user-site.
            for filename, expected in [('METADATA',dependency['metadata']),('RECORD',dependency['record'])]:
                matches = [active.locate_file(path) for path in active.files or []
                    if Path(path).name == filename and Path(path).parent.name.endswith('.dist-info')]
                if len(matches) != 1 or file_record(matches[0]) != expected:
                    raise ValueError('active native dependency differs: '+name)

    for record in records:
        if (type(record) is not dict or set(record) != {'path','sha256','bytes'} or
                type(record['bytes']) is not int or record['bytes'] < 0 or
                verify_record(record) != record):
            raise ValueError('native inventory file changed or malformed')
    executable = safe_path(inventory['interpreter']['path']).resolve()
    if interpreter is not None and inventory['interpreter'] != file_record(interpreter):
        raise ValueError('native interpreter differs')
    # Venv interpreters may resolve to a host binary. Its bytes are pinned above;
    # the separately bound environment prefix is checked in the fresh process.
    if not executable.is_file():
        raise ValueError('native interpreter unavailable')
    for binary in inventory['binaries'].values():
        if not safe_path(binary['path']).resolve().is_relative_to(environment):
            raise ValueError('native binary outside exact environment')
    checkpoint = safe_path(inventory['lpips_checkpoint']['path'])
    if checkpoint.name != 'alexnet-owt-7be5be79.pth' or checkpoint.parent.name != 'checkpoints':
        raise ValueError('offline AlexNet checkpoint location required')
    configuration = read_json(inventory['resolved_config']['path'])
    if (type(configuration) is not dict or set(configuration) != {'native','normalization','scene_scale'} or
            type(configuration['native']) is not dict or
            type(configuration['native'].get('start_frame')) is not int or configuration['native']['start_frame'] != 0 or
            type(configuration['native'].get('end_frame')) is not int or configuration['native']['end_frame'] != 50 or
            type(configuration['scene_scale']) not in (int,float) or
            not math.isfinite(configuration['scene_scale']) or configuration['scene_scale'] <= 0):
        raise ValueError('resolved native configuration required')
    normalization_matrix(configuration['normalization'], actual=True)
    if normalization is not None and configuration['normalization'] != normalization:
        raise ValueError('resolved configuration normalization differs')
    if scene_scale is not None and configuration['scene_scale'] != scene_scale:
        raise ValueError('resolved configuration scene scale differs')
    return inventory


def prepare_inventory(*, checkout, environment_prefix, interpreter, binaries,
        dependencies, resolved_config, lpips_checkpoint, output, source_files=()):
    """Publish once from explicit verified files, retaining any existing output.

    File contents may be fixtures in CPU tests. The `actual` tag describes the
    native runtime inventory contract, not evidence of execution or qualification.
    """
    inventory = dict(schema=SCHEMA,record_kind='actual',status='prepared',
        environment_prefix=str(safe_path(environment_prefix).resolve()),interpreter=interpreter,
        source_files=required_sources(checkout)+list(source_files),binaries=binaries,
        dependencies=dependencies,resolved_config=resolved_config,lpips_checkpoint=lpips_checkpoint)
    validate_inventory(inventory,checkout=checkout)
    write_json(output,inventory)
    return inventory
