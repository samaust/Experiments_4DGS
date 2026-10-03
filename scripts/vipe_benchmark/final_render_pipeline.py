"""CPU fixture result seam for future selected-depth native workers.

No worker runs here. Actual execution/results require a separately qualified
native adapter and DO contract; these fixture records never satisfy that gate.
"""
import copy
import math

from .extended_final_render_contract import parse_request
from .files import object_hash, read_json, verify_record, safe_path
from .final_render_contract import PHASES


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _bound(record):
    _require(type(record) is dict and set(record) == {'path', 'sha256', 'bytes'} and
        verify_record(record) == record, 'exact immutable worker artifact required')
    return read_json(record['path'])


def _validate_publication(request, arm, phase, result):
    if 'terminal_publication' not in result:
        return  # Historical synthetic fixture records predate worker publication.
    path = safe_path(result['terminal_publication'])
    _require(path.name == 'completion.json' and not (path.parent/'failure.json').exists(),
        'worker terminal publication failed')
    completion = read_json(path)
    elapsed = completion.get('elapsed_seconds')
    _require(completion.get('schema') == 'plan069-final-render-worker-completion/v1' and
        completion.get('record_kind') == 'fixture' and completion.get('status') == 'complete' and
        completion.get('arm') == arm and completion.get('phase') == phase and
        completion.get('request_sha256') == object_hash(request) and
        completion.get('cleanup_confirmed') is True and completion.get('execution_authorized') is False and
        completion.get('native_adapter_qualified') is False and
        type(elapsed) in (float,int) and math.isfinite(elapsed) and
        result['elapsed_seconds'] <= elapsed < PHASES[phase][1] and
        completion.get('artifact_bytes') == result['artifact_bytes'],
        'bound successful worker publication completion required')
    published = completion.get('result')
    _require(published.get('path') == str(path.parent/'result.json') and _bound(published) == result,
        'completion must bind the exact published result')


def validate_worker_result(request, arm, phase, result):
    """Validate a fixture worker outcome, including finite resource bounds."""
    _require(request.get('record_kind') == result.get('record_kind') == 'fixture',
        'fixture-only worker seam; actual native adapter is unqualified')
    request = parse_request(request)
    _require(arm in request['compositions'] and phase in PHASES, 'unknown QF arm/phase')
    _require(result.get('schema') == 'plan069-final-render-worker-result/v1' and
        result.get('arm') == arm and result.get('phase') == phase and
        result.get('composition') == request['compositions'][arm] and
        result.get('request_sha256') == object_hash(request) and
        result.get('allocation_id') == request['id']+'/'+arm+'/'+phase, 'worker request/arm/phase identity differs')
    _require(result.get('execution_authorized') is False and result.get('native_adapter_qualified') is False,
        'fixture cannot grant execution or native qualification')
    fields = {'schema', 'record_kind', 'status', 'arm', 'phase', 'composition', 'request_sha256',
        'allocation_id', 'parent_result', 'elapsed_seconds', 'peak_device_bytes', 'artifact_bytes',
        'cpu_workers_used', 'execution_authorized', 'native_adapter_qualified', 'artifacts'}
    if result.get('status') != 'complete':
        fields.add('reason')
    elif phase == 'train':
        fields.update(('completed_iterations', 'checkpoint'))
    elif phase == 'render':
        fields.update(('checkpoint', 'reload_validation', 'iteration', 'render_settings', 'rendered_frames'))
    if 'terminal_publication' in result:
        fields.add('terminal_publication')
    _require(set(result) == fields, 'exact worker result fields required')
    _validate_publication(request,arm,phase,result)
    elapsed = result.get('elapsed_seconds')
    _require(type(elapsed) in (int, float) and math.isfinite(elapsed) and
        0 <= elapsed <= PHASES[phase][1], 'worker exceeded finite phase deadline')
    for field, limit in [('peak_device_bytes', request['device_bytes_limit']),
            ('artifact_bytes', request['artifact_bytes_limit']), ('cpu_workers_used', request['cpu_workers_limit'])]:
        _require(type(result.get(field)) is int and 0 <= result[field] <= limit, 'invalid/excessive '+field)
    artifacts = result.get('artifacts')
    _require(type(artifacts) is list, 'worker artifacts required')
    unique = {}
    for record in artifacts:
        _require(verify_record(record) == record, 'worker artifact bytes changed')
        unique[object_hash(record)] = record
    _require(result['artifact_bytes'] >= sum(record['bytes'] for record in unique.values()),
        'worker storage omits published artifacts')
    status = result.get('status')
    _require(status in ('complete', 'failed', 'blocked'), 'invalid worker status')
    phases = tuple(PHASES)
    parent = result.get('parent_result')
    if phase == phases[0]:
        _require(parent is None, 'geometry cannot consume a previous phase')
    else:
        previous = _bound(parent)
        _validate_publication(request,arm,phases[phases.index(phase)-1],previous)
        _require(previous.get('status') == 'complete' and previous.get('record_kind') == 'fixture' and
            previous.get('phase') == phases[phases.index(phase)-1] and previous.get('arm') == arm and
            previous.get('request_sha256') == object_hash(request) and
            previous.get('composition') == request['compositions'][arm], 'complete same-arm predecessor required')
    if status != 'complete':
        _require(type(result.get('reason')) is str and bool(result['reason'].strip()), 'failed/blocked worker requires reason')
        return copy.deepcopy(result)
    _require(bool(artifacts), 'completed worker lacks immutable artifacts')
    if phase == 'train':
        _require(type(result.get('completed_iterations')) is int and result['completed_iterations'] == 5000 and
            result.get('checkpoint') in artifacts, 'exact training endpoint and published checkpoint required')
    if phase == 'render':
        checkpoint = result.get('checkpoint')
        _require(type(result.get('iteration')) is int and result['iteration'] == 5000 and
            checkpoint == previous.get('checkpoint') and previous.get('completed_iterations') == 5000,
            'render must reload exact 5000-iteration training checkpoint')
        _require(type(checkpoint) is dict and set(checkpoint) == {'path', 'sha256', 'bytes'} and
            verify_record(checkpoint) == checkpoint, 'consumed training checkpoint bytes changed')
        reload = _bound(result.get('reload_validation'))
        _require(result['reload_validation'] in artifacts and reload == dict(
            schema='plan069-final-render-fixture-reload/v1', record_kind='fixture', status='passed',
            checkpoint=checkpoint, iteration=5000, request_sha256=object_hash(request), arm=arm),
            'exact fixture checkpoint reload validation required')
        _require(result.get('render_settings') == request['render'], 'render settings differ')
        frames = result.get('rendered_frames')
        _require(type(frames) is list and len(frames) == 200 and all(
            type(row.get('camera')) is int and type(row.get('frame')) is int and row.get('rgb') in artifacts
            for row in frames), 'bound heldout render frames required')
        _require({(row['camera'], row['frame']) for row in frames} ==
            {(c, f) for c in request['render']['cameras'] for f in request['render']['frames']},
            'complete unique heldout render coverage required')
    return copy.deepcopy(result)


def validate_pipeline(request, arm, records):
    """Check ordered immutable fixture outcomes and preserve stopped stages."""
    _require(request.get('record_kind') == 'fixture', 'fixture-only pipeline; actual native adapter is unqualified')
    request = parse_request(request)
    _require(arm in request['compositions'] and set(records) <= set(PHASES), 'unknown pipeline arm/phase')
    status = 'blocked'; reason = ''; previous = None; frames = 0
    phases = tuple(PHASES)
    for index, phase in enumerate(phases):
        remaining = set(phases[index+1:]) & set(records)
        if phase not in records:
            _require(not remaining, 'pipeline skipped a prerequisite phase')
            reason = 'missing '+phase+' result'
            status = 'blocked'
            break
        result = validate_worker_result(request, arm, phase, _bound(records[phase]))
        _require(result['parent_result'] == previous, 'pipeline consumed a substituted predecessor result')
        status = result['status']
        previous = records[phase]
        if status != 'complete':
            _require(not remaining, 'pipeline continued after failed/blocked predecessor')
            reason = result['reason']
            break
        if phase == 'render':
            frames = len(result['rendered_frames'])
    return dict(schema='plan069-final-render-fixture-pipeline/v1', record_kind='fixture', status=status,
        reason=reason, arm=arm, composition=request['compositions'][arm], request_sha256=object_hash(request),
        records=copy.deepcopy(records), rendered_frames=frames, execution_authorized=False,
        native_adapter_qualified=False, actual_final_renders=False)
