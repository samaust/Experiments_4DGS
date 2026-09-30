"""Retain one admitted Torch-generated module without executing generator code."""
import ast
import os
import stat
from pathlib import Path

from .s1_progress import (operation, checked_file_record, checked_mkdir,
                          verified_bytes, acquire, retire, before)

MODULE = '_remote_module_non_scriptable'
GENERATOR = 'torch.distributed.nn.jit.instantiator'
TEMPLATE = 'torch.distributed.nn.jit.templates.remote_module_template'
SCHEMA = 's1-torch-generated-source/v1'
SUBSTITUTIONS = dict(assign_module_interface_cls='module_interface_cls = None',
    args='*args', kwargs='**kwargs', arg_types='*args, **kwargs',
    arrow_and_return_type='', arrow_and_future_return_type='', jit_script_decorator='')


def admitted_generators(request, records):
    from .s1_progress import checked_read_json
    inventory = operation(checked_read_json, request['runtime']['inventory']['path'])
    operation(verified_bytes, request['runtime']['inventory'])
    admitted = {entry['path']: entry for package in inventory['packages'] for entry in package['files']}
    expected = ((GENERATOR, '/torch/distributed/nn/jit/instantiator.py'),
                (TEMPLATE, '/torch/distributed/nn/jit/templates/remote_module_template.py'))
    if type(records) is not dict or set(records) != {GENERATOR, TEMPLATE}:
        raise ValueError('S1 generated source generator bindings required')
    for name, suffix in expected:
        rec = records[name]
        if (type(rec) is not dict or not rec.get('path', '').endswith(suffix)
                or rec != admitted.get(rec['path'])):
            raise ValueError('S1 generated source generator differs from admission')
        operation(verified_bytes, rec)
    return records


def expected_source(records):
    """Read literal templates only: never import Torch or execute source code."""
    generator = operation(ast.parse, operation(verified_bytes, records[GENERATOR]))
    functions = [node for node in generator.body if isinstance(node, ast.FunctionDef)
                 and node.name == 'instantiate_non_scriptable_remote_module_template']
    if len(functions) != 1:
        raise ValueError('S1 unsupported Torch generated source generator')
    body = functions[0].body
    # The pinned non-scriptable generator selects exactly this constant mapping.
    mappings = [node.value for node in body if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == 'str_dict' for target in node.targets)]
    if (len(mappings) != 1 or not isinstance(mappings[0], ast.Call)
            or not isinstance(mappings[0].func, ast.Name) or mappings[0].func.id != 'dict'
            or mappings[0].args or any(item.arg is None for item in mappings[0].keywords)
            or {item.arg: ast.literal_eval(item.value) for item in mappings[0].keywords} != SUBSTITUTIONS):
        raise ValueError('S1 unsupported Torch generated source substitutions')
    template = operation(ast.parse, operation(verified_bytes, records[TEMPLATE]))
    literals = {}
    for node in template.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in ('_TEMPLATE_PREFIX', '_REMOTE_FORWARD_TEMPLATE_ENABLE_MOVING_CPU_TENSORS_TO_CUDA'):
                    literals[target.id] = ast.literal_eval(node.value)
    if len(literals) != 2 or any(type(value) is not str for value in literals.values()):
        raise ValueError('S1 unsupported Torch generated source template')
    return operation(str.encode, operation(str.format,
        literals['_TEMPLATE_PREFIX'] + literals['_REMOTE_FORWARD_TEMPLATE_ENABLE_MOVING_CPU_TENSORS_TO_CUDA'], **SUBSTITUTIONS))


def capture(path, names, modules, output, request):
    from .s1_progress import TEMPORARY_OWNERS
    if names != [MODULE] or Path(path).name != MODULE + '.py' or request is None:
        raise ValueError('S1 unsupported generated source module')
    output = Path(output).absolute()
    job = request.get('job_id')
    if output.parent.name != job:
        raise ValueError('S1 generated source job evidence binding')
    generator = modules.get(GENERATOR)
    owner = getattr(generator, '_TEMP_DIR', None)
    if (owner not in TEMPORARY_OWNERS or not owner.unresolved or owner.attempted
            or owner.identity is None or Path(owner.name) != Path(path).parent
            or owner.parent != output.parent.with_name(job + '-temporary')
            or getattr(generator, 'INSTANTIATED_TEMPLATE_DIR_PATH', None) != owner.name):
        raise ValueError('S1 generated source temporary ownership required')
    info = operation(os.fstat, owner.root_fd)
    named = operation(Path(owner.name).stat, follow_symlinks=False)
    if (not stat.S_ISDIR(named.st_mode)
            or (named.st_dev,named.st_ino) != (info.st_dev,info.st_ino)
            or (info.st_dev, info.st_ino) != (owner.identity['device'], owner.identity['inode'])):
        raise ValueError('S1 generated source temporary identity changed')
    records = {name: operation(checked_file_record, getattr(modules.get(name), '__file__', ''))
               for name in (GENERATOR, TEMPLATE)}
    admitted_generators(request, records)
    original = operation(checked_file_record, path)
    raw = operation(verified_bytes, original)
    if raw != expected_source(records):
        raise ValueError('S1 generated source differs from admitted template')
    retained = output.parent / 'generated-sources' / (MODULE + '.py')
    operation(checked_mkdir, retained.parent, parents=True, exist_ok=True)
    stream = acquire(retained.open, lambda value: value.close(), 'xb', buffering=0)
    try:
        if operation(stream.write, raw) != len(raw):
            raise OSError('short generated source write')
        operation(stream.flush)
        operation(os.fsync, stream.fileno())
        operation(stream.close)
    finally:
        if not stream.closed: retire(stream.close)
    record = operation(checked_file_record, retained)
    if operation(verified_bytes, original) != operation(verified_bytes, record):
        raise ValueError('S1 generated source changed during capture')
    before()
    return dict(schema=SCHEMA, module=MODULE, original=original, retained=record,
                generators=records, temporary=dict(root=owner.name, parent=str(owner.parent),
                    identity=dict(owner.identity)), moment='live before owned temporary cleanup')


def verify(entry, request, manifest_path):
    """Verify retained evidence; original bytes remain mandatory while still live."""
    binding = entry.get('generated_source')
    if (type(binding) is not dict or set(binding) != {'schema','module','original','retained','generators','temporary','moment'}
            or binding['schema'] != SCHEMA or binding['module'] != MODULE
            or entry.get('modules') != [MODULE] or entry.get('mapped_native_library') is not False
            or binding['original'] != {key: entry[key] for key in ('path','sha256','bytes')}
            or binding['moment'] != 'live before owned temporary cleanup'):
        raise ValueError('S1 generated source binding changed')
    output = Path(manifest_path).parent
    job = request.get('job_id')
    temporary = binding['temporary']
    if (type(temporary) is not dict or set(temporary) != {'root','parent','identity'}
            or output.name != job or temporary['parent'] != str(output.with_name(job + '-temporary'))
            or Path(temporary['root']).parent != Path(temporary['parent'])
            or Path(entry['path']) != Path(temporary['root']) / (MODULE + '.py')
            or binding['retained'].get('path') != str(output / 'generated-sources' / (MODULE + '.py'))
            or type(temporary['identity']) is not dict or set(temporary['identity']) != {'device','inode','mount_id'}
            or any(type(value) is not int or value < 0 for value in temporary['identity'].values())
            or temporary['identity']['inode'] == 0 or temporary['identity']['mount_id'] == 0):
        raise ValueError('S1 generated source job/temporary binding changed')
    records = admitted_generators(request, binding['generators'])
    retained = binding['retained']
    raw = operation(verified_bytes, retained)
    if (retained['sha256'] != entry['sha256'] or retained['bytes'] != entry['bytes']
            or raw != expected_source(records)):
        raise ValueError('S1 generated source retained bytes changed')
    root = Path(temporary['root'])
    if operation(root.exists):
        info = operation(root.stat, follow_symlinks=False)
        identity = temporary['identity']
        if (not stat.S_ISDIR(info.st_mode) or (info.st_dev,info.st_ino) != (identity['device'],identity['inode'])):
            raise ValueError('S1 generated source temporary identity changed')
        operation(verified_bytes, binding['original'])
    return binding['original']
