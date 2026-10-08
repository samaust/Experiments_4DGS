"""Actual worker evidence checked against immutable admission and stage lineage.

These records are worker candidates. The dispatcher independently measures
process resources and confirms cleanup before accepting a ledger completion.
"""
import copy
import math
from pathlib import Path

import numpy as np
from PIL import Image

from .files import object_hash, read_json, safe_path, verify_record
from .final_render_contract import PHASES, phase_seconds
from .extended_final_render_contract import parse_request, validate_scene_bindings
from .final_render_adapter import prepare_model_input


SCHEMA = 'plan069-final-render-actual-worker-result/v1'
COMPLETION = 'plan069-final-render-actual-worker-completion/v1'


def _require(value, message):
    if not value:
        raise ValueError(message)


def _bound(record):
    _require(type(record) is dict and set(record) == {'path','sha256','bytes'} and
        verify_record(record) == record, 'exact immutable actual record required')
    return read_json(record['path'])


def validate_actual_worker_result(request, arm, phase, result, *, published=True):
    """Validate guarded actual evidence; never promote a CPU fixture result."""
    _require(request.get('record_kind') == result.get('record_kind') == 'actual', 'actual request and result required')
    request = parse_request(request)
    validate_scene_bindings(request)
    _require(arm in request['compositions'] and phase in PHASES, 'unknown actual arm/phase')
    from .final_render_admission import invocation_binding
    binding = invocation_binding(result.get('invocation'), request, arm, phase, require_worker=False)
    invocation = binding['invocation']
    _require(result.get('schema') == SCHEMA and result.get('status') == 'complete' and
        result.get('arm') == arm and result.get('phase') == phase and
        result.get('composition') == request['compositions'][arm] and
        result.get('request_sha256') == object_hash(request) and
        result.get('allocation_id') == request['id']+'/'+arm+'/'+phase and
        result.get('parent_result') == invocation['parent_result'] and
        result.get('execution_authorized') is True and result.get('native_adapter_qualified') is True,
        'actual result identity/admission differs')
    fields = {'schema','record_kind','status','arm','phase','composition','request_sha256','allocation_id',
        'parent_result','elapsed_seconds','peak_device_bytes','artifact_bytes','cpu_workers_used',
        'execution_authorized','native_adapter_qualified','artifacts','invocation'}
    fields.update({'geometry','coverage_edges'} if phase == 'geometry' else
        {'initializer','assembly','native_input'} if phase == 'initializer' else
        {'completed_iterations','checkpoint'} if phase == 'train' else
        {'checkpoint','reload_validation','iteration','render_settings','rendered_frames'})
    if 'terminal_publication' in result:
        fields.add('terminal_publication')
    _require(set(result) == fields, 'exact actual result fields required')
    elapsed = result['elapsed_seconds']
    _require(type(elapsed) in (float,int) and math.isfinite(elapsed) and 0 <= elapsed < phase_seconds(request,phase),
        'actual worker exceeded phase deadline')
    for name,limit in [('peak_device_bytes',request['device_bytes_limit']),
            ('artifact_bytes',request['artifact_bytes_limit']),('cpu_workers_used',request['cpu_workers_limit'])]:
        _require(type(result[name]) is int and 0 <= result[name] <= limit, 'invalid/excessive '+name)
    artifacts = result['artifacts']
    _require(type(artifacts) is list and artifacts and all(verify_record(r) == r for r in artifacts),
        'immutable actual artifacts required')
    _require(len({r['path'] for r in artifacts}) == len(artifacts), 'duplicate actual artifact paths')
    output = safe_path(invocation['output']).resolve()
    _require(all(Path(r['path']).resolve().is_relative_to(output) for r in artifacts),
        'actual artifacts must belong to stage output')
    _require(result['artifact_bytes'] >= sum(r['bytes'] for r in artifacts), 'actual artifact storage omitted')
    parent = None
    if phase == 'geometry':
        _require(result['parent_result'] is None, 'geometry cannot consume predecessor')
    else:
        preceding = tuple(PHASES)[tuple(PHASES).index(phase)-1]
        parent = validate_actual_worker_result(request,arm,preceding,_bound(result['parent_result']))
    if phase == 'geometry':
        geometry = _bound(result['geometry'])
        _require(result['geometry'] in artifacts and type(result['coverage_edges']) is int and result['coverage_edges'] == 810 and
            geometry.get('schema') == 'plan069-final-render-geometry/v1' and
            geometry.get('record_kind') == 'actual' and geometry.get('status') == 'complete' and
            geometry.get('arm') == arm and geometry.get('request_sha256') == object_hash(request) and
            len(geometry.get('rows',[])) == 810 and geometry.get('recipe',{}).get('native_model_verified') is True and
            geometry.get('recipe',{}).get('matcher_runtime') == binding['matcher_runtime'] and
            geometry.get('recipe',{}).get('invocation') == result['invocation'],
            'qualified full-rig geometry required')
        from .final_render_initializer import _geometry
        checked, _, _ = _geometry(request,arm,result['geometry'])
        _require(all(row['artifact'] in artifacts for row in checked.rows),
            'geometry result omits published observation archives')
    elif phase == 'initializer':
        bundle = _bound(result['initializer'])
        assembly = _bound(result['assembly'])
        native_input = _bound(result['native_input'])
        _require(result['initializer'] in artifacts and result['assembly'] in artifacts and result['native_input'] in artifacts and
            bundle.get('schema') == 'plan069-final-render-prepared-initializer/v1' and bundle.get('record_kind') == 'actual' and
            bundle.get('arm') == arm and bundle.get('request_sha256') == object_hash(request) and bundle.get('archive') in artifacts and
            bundle.get('execution_authorized') is False and bundle.get('native_adapter_qualified') is False and
            assembly.get('schema') == 'plan069-final-render-assembly-result/v1' and assembly.get('status') == 'complete' and
            assembly.get('record_kind') == 'actual' and assembly.get('geometry') == parent['geometry'] and
            assembly.get('voxel_width') == invocation.get('voxel_width') and assembly.get('coverage_edges') == 810 and
            assembly.get('initializer_receipt') == bundle.get('initializer_receipt'), 'exact geometry-derived initializer required')
        with np.load(safe_path(bundle['archive']['path']), allow_pickle=False) as archive:
            arrays = {name:archive[name].copy() for name in archive.files}
        _, expected = prepare_model_input(request,arm,bundle['initializer_receipt'],arrays)
        _require(native_input == expected and assembly.get('arrays_sha256') == expected['arrays_sha256'],
            'full initializer arrays/receipt differ')
        # The actual archive must derive from the published geometry, not merely
        # have a self-consistent hash and initializer header.
        from .final_render_initializer import assemble
        derived, expected_assembly = assemble(request,arm,parent['geometry'],invocation['voxel_width'])
        _require(assembly == expected_assembly and set(arrays) == set(derived) and
            all(np.array_equal(arrays[name],derived[name]) for name in arrays),
            'actual initializer differs from full geometry assembly')
    elif phase == 'train':
        _require(type(result['completed_iterations']) is int and result['completed_iterations'] == request['iterations'] and
            result['checkpoint'] in artifacts and invocation.get('initializer') == parent['initializer'],
            'exact trained initializer and request endpoint required')
    else:
        _require(type(result['iteration']) is int and result['iteration'] == request['iterations'] and
            result['checkpoint'] == parent['checkpoint'] and parent['completed_iterations'] == request['iterations'] and
            verify_record(result['checkpoint']) == result['checkpoint'] and
            result['render_settings'] == request['render'], 'exact reloaded checkpoint/settings required')
        reload = _bound(result['reload_validation'])
        _require(result['reload_validation'] in artifacts and reload.get('schema') == 'plan069-final-render-actual-reload/v1' and
            reload.get('record_kind') == 'actual' and reload.get('status') == 'passed' and
            reload.get('checkpoint') == result['checkpoint'] and type(reload.get('iteration')) is int and reload.get('iteration') == request['iterations'] and
            reload.get('request_sha256') == object_hash(request) and reload.get('arm') == arm and
            reload.get('restored_state_equal') is True and reload.get('restored_checkpoint') in artifacts,
            'full actual checkpoint restoration evidence required')
        frames = result['rendered_frames']
        _require(type(frames) is list and len(frames) == 200 and all(type(r.get('camera')) is int and
            type(r.get('frame')) is int and r.get('rgb') in artifacts for r in frames) and
            {(r['camera'],r['frame']) for r in frames} == {(c,f) for c in request['render']['cameras'] for f in request['render']['frames']} and
            len({r['rgb']['path'] for r in frames}) == 200, 'unique complete heldout coverage required')
        for row in frames:
            with Image.open(safe_path(row['rgb']['path'])) as image:
                _require(image.format == 'PNG' and image.mode == 'RGB' and image.size == (960,540),
                    'matched lossless RGB render dimensions required')
                image.load()
    if published:
        path = safe_path(result.get('terminal_publication','')).resolve()
        _require(path == output/'completion.json' and not (output/'failure.json').exists(), 'actual terminal publication failed')
        completion = read_json(path)
        actual = completion.get('elapsed_seconds')
        _require(completion.get('schema') == COMPLETION and completion.get('record_kind') == 'actual' and
            completion.get('status') == 'complete' and completion.get('invocation') == result['invocation'] and
            completion.get('arm') == arm and completion.get('phase') == phase and
            completion.get('request_sha256') == object_hash(request) and completion.get('cleanup_confirmed') is True and
            completion.get('execution_authorized') is True and completion.get('native_adapter_qualified') is True and
            completion.get('artifact_bytes') == result['artifact_bytes'] and type(actual) in (float,int) and
            math.isfinite(actual) and elapsed <= actual < phase_seconds(request,phase) and
            completion.get('result',{}).get('path') == str(output/'result.json') and
            _bound(completion['result']) == result, 'bound publication-inclusive actual completion required')
    return copy.deepcopy(result)
