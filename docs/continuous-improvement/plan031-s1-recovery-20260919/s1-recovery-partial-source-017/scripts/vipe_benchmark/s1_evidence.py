"""S1 first-result and failure evidence, with no model imports or extra forwards."""
from pathlib import Path
import time
import traceback
import numpy as np

from .files import file_record, load_array, read_json, verify_record, write_json
from .s1_recovery import JOB, AMENDMENT
from .s1_progress import operation, with_deadline, DeadlineSink, before

REQUIRED = ('detector_raw_token_logits', 'detector_raw_boxes_cxcywh',
    'detector_token_scores', 'detector_native_boxes_cxcywh', 'detector_selected_scores',
    'detector_selected_query_indices', 'detector_token_ids', 'detector_rgb',
    'detector_native_phrase_utf8', 'detector_native_phrase_offsets')


@with_deadline
def load_array(record):
    # Keep hash verification and the subsequent NPY load as separate W gates.
    operation(verify_record,record)
    return operation(np.load,record['path'],allow_pickle=False)


@with_deadline
def numeric_file(path, arrays):
    if any(np.asarray(v).dtype.hasobject for v in arrays.values()):
        raise ValueError('native intermediates must be non-pickled numeric arrays')
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    before()
    with Path(path).open('xb', buffering=0) as stream:
        before()
        operation(np.savez_compressed, DeadlineSink(stream), **arrays)
    return operation(file_record,path)


class BoundedArrays:
    def __init__(self, arrays):self.arrays=arrays;self.files=arrays.files
    def __contains__(self, key):return key in self.files
    def __getitem__(self, key):return operation(self.arrays.__getitem__,key)


def elapsed(clock, *, work=True):
    from .s1_clock import require_clock
    return require_clock(clock).observe(work=work)


def verify_failure(value, request, clock):
    from .s1_clock import require_clock
    from .s1_recovery import strict_record
    clock = require_clock(clock)
    clock.match(value.get('reservation_clock'))
    clock.recorded(value.get('elapsed_seconds_from_reservation'), value.get('status'))
    auth = request['recovery_authorization']
    if (value.get('schema') != 'plan032-s1-first-result/v1' or value.get('job_id') != JOB
            or value.get('status') not in ('failed', 'not_reached')
            or value.get('clock_status') != 'verified'
            or value.get('authorization') != auth
            or value.get('semantic_amendment') != read_json(strict_record(auth)['path'])['semantic_amendment']
            or not value.get('error') or not value.get('failure_stage')
            or read_json(strict_record(value['request'])['path']) != request):
        raise ValueError('invalid worker first-result failure evidence')
    for record in value.get('raw_evidence', []):
        strict_record(record)
    return True


def first_record(request, output, status, *, clock, rows=(), runtime=None, error=None,
                 stage=None, raw=(), checks=()):
    from .s1_clock import require_clock, diagnostic
    path = Path(output) / 'first-result-qualification.json'
    if status=='passed':require_clock(clock).observe()
    # Cleanup preserves verified original bytes without taking a new live sample.
    if path.exists() and status != 'passed':
        existing = read_json(path)
        if existing.get('status') == 'passed':
            clock.observe()
            verify_first(existing, request, clock=clock, deadline=clock.work_deadline)
        else:
            verify_failure(existing, request, clock)
        return file_record(path)
    try:
        clock = require_clock(clock)
        seconds = elapsed(clock, work=status == 'passed')
        clock_fields = dict(reservation_clock=clock.mapping(), clock_status='verified',
                            elapsed_seconds_from_reservation=seconds)
    except Exception as clock_error:
        if status == 'passed':
            raise
        clock_fields = diagnostic(clock, clock_error)
    auth = request.get('recovery_authorization')
    try:
        amendment = read_json(verify_record(auth)['path'])['semantic_amendment'] if auth else None
    except Exception:
        amendment = None
    config = Path(output) / 'config.json'
    request_record = file_record(config) if config.exists() else (clock.mapping()['request'] if clock else None)
    value = dict(schema='plan032-s1-first-result/v1', job_id=request['job_id'],
        status=status, identity=rows[0]['identity'] if rows else None, count=len(rows),
        rows=list(rows), runtime=runtime or {}, semantic_amendment=amendment,
        authorization=auth, request=request_record, checks=list(checks), raw_evidence=list(raw),
        error=error, failure_stage=stage, **clock_fields)
    if path.exists():
        existing = read_json(path)
        clock.observe()
        verify_first(existing, request, clock=clock, deadline=clock.work_deadline)
        comparable = dict(value, elapsed_seconds_from_reservation=existing['elapsed_seconds_from_reservation'])
        if comparable != existing:
            raise ValueError('conflicting first-result publication')
    else:
        if status == 'passed':
            verify_first(value, request, clock=clock, deadline=clock.work_deadline)
            clock.observe()  # qualification completion, before immutable publication
        elif value['clock_status'] == 'verified':
            verify_failure(value, request, clock)
        write_json(path, value)
    if status=='passed':clock.observe()
    record = file_record(path)
    if status=='passed':clock.observe()
    persisted = read_json(verify_record(record)['path'])
    if status == 'passed':
        clock.observe()  # No new raw requalification after publication reaches W.
        verify_first(persisted, request, clock=clock, deadline=clock.work_deadline)
        clock.observe()  # publication/hash/read-back/requalification completion
    elif value['clock_status'] == 'verified':
        verify_failure(persisted, request, clock)
    return record


def reconcile_first(request, output, *, clock, error):
    """Reuse verified worker evidence only for cleanup, never advancement."""
    path = Path(output) / 'first-result-qualification.json'
    if not path.exists():
        first_record(request, output, 'not_reached', clock=clock, error=error, stage='supervisor_cleanup')
    record = file_record(path)
    value = read_json(verify_record(record)['path'])
    if value.get('status') == 'passed':
        clock.observe()
        verify_first(value, request, clock=clock, deadline=clock.work_deadline)
    else:
        verify_failure(value, request, clock)
    return record


def preserve_failure(request, output, identity, error, *, adapter=None, prediction=None,
                     stage='adapter', parent=None, runtime=None, clock=None):
    """Best effort publication; caller always re-raises the original exception."""
    output = Path(output)
    if request.get('job_id') == JOB and clock is not None and time.monotonic() >= clock.work_deadline:
        from .s1_progress import read_bytes, record
        from .s1_clock import diagnostic
        error.s1_progress_unavailable='work deadline reached; raw bytes retained without new qualification'
        first=output/'first-result-qualification.json'
        if not first.exists():
            # A bounded unverified diagnostic is not new first-result authority.
            write_json(first,dict(schema='plan032-s1-first-result/v1',job_id=JOB,status='failed',
                identity=None,count=0,rows=[],runtime={},semantic_amendment=None,
                authorization=request.get('recovery_authorization'),request=clock.mapping()['request'],
                checks=[],raw_evidence=[],error=str(error),failure_stage=stage,
                **diagnostic(clock,TimeoutError('work deadline reached'))))
        try:error.s1_first_result=record(first,read_bytes(first,1024*1024))
        except FileNotFoundError:error.s1_first_result=None
        stem=identity.key() if identity is not None else 'unavailable-input'
        path=output/(stem+'-failure-evidence.json')
        write_json(path,dict(schema='plan032-s1-failure-evidence/v1',job_id=JOB,error_type=type(error).__name__,
            error=str(error),failure_stage=stage,array_records={},available_fields=[],unavailable_fields={'arrays':'work deadline reached'},
            **diagnostic(clock,TimeoutError('work deadline reached'))))
        error.s1_failure_record=file_record(path)
        return error.s1_failure_record
    output.mkdir(parents=True, exist_ok=True)
    evidence = getattr(error, 's1_evidence', None)
    detector = getattr(adapter, 'detector', None)
    if evidence is None and detector is not None and hasattr(detector, 'evidence'):
        evidence = detector.evidence()
    evidence = evidence or {}
    arrays = dict(evidence.get('arrays', {}))
    if prediction is not None:
        arrays.update(getattr(prediction, 'diagnostics', {}) or {})
        arrays['labels'] = prediction.labels
    stem = identity.key() if identity is not None else 'unavailable-input'
    records, unavailable = {}, {}
    numeric = {}
    for key, value in arrays.items():
        if np.asarray(value).dtype.hasobject:
            unavailable[key] = 'object array prohibited'
        else:
            numeric[key] = value
    serialization_error = None
    try:
        if numeric:
            record = numeric_file(output / (stem + '-failure-evidence.npz'), numeric, deadline=clock.work_deadline if clock is not None else None)
            records = {key: dict(file=record, member=key, shape=list(np.shape(value)),
                                dtype=str(np.asarray(value).dtype), finite=bool(np.isfinite(value).all()))
                       for key, value in numeric.items()}
    except BaseException as exc:
        serialization_error = f'{type(exc).__name__}: {exc}'
    for key in REQUIRED:
        if key not in records:
            unavailable[key] = serialization_error or 'not captured before failure; no additional forward'
    auth = request.get('recovery_authorization')
    try:
        amendment = read_json(verify_record(auth)['path'])['semantic_amendment'] if auth else None
    except Exception:
        amendment = None
    clock_fields = {}
    if request['job_id'] == JOB:
        from .s1_clock import require_clock, diagnostic
        try:
            seconds = require_clock(clock).observe(work=False)
            clock_fields = dict(clock_status='verified', reservation_clock=clock.mapping(), elapsed_seconds_from_reservation=seconds)
        except Exception as clock_error:
            clock_fields = diagnostic(clock, clock_error)
    value = dict(schema='plan032-s1-failure-evidence/v1', job_id=request['job_id'],
        identity=identity.record() if identity is not None else None,
        failure_stage=evidence.get('failure_stage', stage) if stage == 'adapter' else stage,
        error_type=type(error).__name__, error=str(error), traceback=traceback.format_exc(),
        native_phrases=evidence.get('native_phrases', []), assignments=evidence.get('assignments', []),
        array_records=records, available_fields=sorted(records), unavailable_fields=unavailable,
        forward_count=evidence.get('forward_count', 0), inputs=request.get('inputs'),
        input=parent, request=file_record(output / 'config.json') if (output / 'config.json').exists() else None,
        semantic_amendment=amendment, serialization_error=serialization_error, **clock_fields)
    path = output / (stem + '-failure-evidence.json')
    write_json(path, value)
    record = file_record(path)
    error.s1_failure_record = record
    if request['job_id'] == JOB:
        error.s1_first_result = first_record(request, output,
            'failed' if evidence.get('forward_count', 0) else 'not_reached',
            clock=clock, runtime=runtime, error=f'{type(error).__name__}: {error}', stage=value['failure_stage'], raw=[record])
    return record


@with_deadline
def produced_row(row, request, *, loader=None):
    """Verify serialization and provenance without claiming semantic success."""
    from .access import Identity, output_identities
    from .config import load
    from .s1_recovery import strict_record
    import cv2
    if not isinstance(row, dict) or not isinstance(row.get('identity'), dict):
        raise ValueError('produced row mapping/identity required')
    identity = Identity(**row['identity'])
    if (type(identity.camera) is not int or type(identity.frame) is not int
            or identity not in output_identities(load(), 'calibration')):
        raise ValueError('produced row outside admitted identities')
    loader = loader or input_loader(request)
    parent = loader.row(identity)
    if (any(row.get(k) != parent[k] for k in ('K', 'grid', 'valid'))
            or row.get('source_rgb_sha256') != parent['rgb']['sha256']):
        raise ValueError('produced row input provenance changed')
    operation(strict_record,parent['rgb'])
    if not isinstance(row.get('semantics'), dict) or not isinstance(row.get('metadata'), dict):
        raise ValueError('produced row serialized fields required')
    for key in ('instances', 'semantic_static', 'diagnostics', 'valid'):
        operation(strict_record,row[key])
    valid = operation(load_array,row['valid'])
    labels = operation(load_array,row['instances'])
    static = operation(cv2.imread,row['semantic_static']['path'], cv2.IMREAD_UNCHANGED)
    if (valid.dtype != np.bool_ or labels.shape != valid.shape or labels.dtype != np.int32
            or static is None or static.shape != valid.shape or static.dtype != np.uint8):
        raise ValueError('produced row artifact shape/type changed')
    with operation(np.load,row['diagnostics']['path'], allow_pickle=False) as raw_arrays:
        arrays = BoundedArrays(raw_arrays)
        if any(k not in arrays for k in REQUIRED) or any(arrays[k].dtype.hasobject for k in arrays.files):
            raise ValueError('produced row numeric serialization missing')
    return identity


def reconcile_rows(output, request, *, result=None, deadline=None, publisher=None):
    """Closed candidate coverage precedes authoritative structural lower bounds."""
    from .access import output_identities, Identity
    from .config import load
    from .s1_progress import candidate_inventory, before
    expected=output_identities(load(),'calibration');loader=input_loader(request)
    variants={};errors=[];sources=[];produced=[];qualified=[];closed=False
    authority={}
    if publisher is not None and publisher.worker_authority is not None:
        worker_reference,worker=publisher.worker_authority
        for sealed in worker['rows']:
            identity=Identity(**sealed['identity']);authority[identity]=sealed
            produced.append(identity.record())
            if sealed['qualified']:qualified.append(identity.record())
            copied=dict(sealed);copied['authority']=dict(sealed['authority'],worker_reference=worker_reference)
            indices=[]
            for old_index in sealed['source_indices']:
                rec=worker['sources'][old_index]
                if rec not in publisher.sources:publisher.sources.append(rec)
                indices.append(publisher.sources.index(rec))
            copied['source_indices']=indices
            from .s1_progress import identity_index
            publisher.rows[identity_index(sealed['identity'],publisher.context)]=copied
        if publisher.rows:publisher.publish()
    def error(source,exc):
        if publisher is not None:publisher.failure(exc,str(source)[:96])
        if len(errors)<32:errors.append(dict(evidence=str(source)[:2048],error=str(exc)[:1024]))
    def check():
        if deadline is not None:before(deadline)
    try:
        candidates,sources=candidate_inventory(output,result,deadline)
        for source,row,record,version in candidates:
            check()
            try:
                identity=Identity(**row['identity'])
                if identity not in expected or any(type(row['identity'][k]) is not int for k in ('camera','frame')):raise ValueError('out-of-set row')
                options=variants.setdefault(identity,{})
                if version not in options and len(options)>=4:raise OverflowError('row variant overflow')
                options[version]=(row,record)
            except OverflowError:raise
            except Exception as exc:error(source,exc)
        sources.recheck(deadline);check();closed=True
        if publisher is not None:publisher.inventory=sources
        if publisher is not None and publisher.coverage not in ('conflict','overflow'):publisher.coverage='closed'
        if isinstance(result,dict) and [r.get('identity') for r in result['rows']] != [i.record() for i in expected]:
            error('result_order','incomplete/reordered/extra identities')
        for identity in expected:
            options=variants.get(identity,{})
            sealed=authority.get(identity)
            if sealed is not None:
                if any(version!=sealed['version'] for version in options):
                    error(identity.record(),'conflicting discovered variant against acknowledged worker')
                    publisher.coverage='conflict'
                # The exact acknowledged seal remains the monotone lower bound.
                continue
            if len(options)>1:
                error(identity.record(),'conflicting duplicate identity')
                if publisher is not None:publisher.coverage='conflict'
                continue
            if not options:continue
            row,record=next(iter(options.values()))
            try:
                check();produced_row(row,request,loader=loader,deadline=deadline);check()
                produced.append(identity.record())
                if publisher is not None:publisher.seal(row,record)
                check();qualify_row(row,request,first=identity==expected[0],loader=loader,deadline=deadline);check()
                qualified.append(identity.record())
                if publisher is not None:publisher.seal(row,record,qualified=True)
            except TimeoutError:raise
            except Exception as exc:
                error(identity.record(),exc)
                if publisher is not None and publisher.stopped:raise
    except Exception as exc:
        error('inventory_or_guard',exc);closed=False
        if publisher is not None and publisher.stopped:raise
    if closed:
        try:sources.recheck(deadline)
        except Exception as exc:
            error('inventory_closure',exc);closed=False;produced=[i.record() for i in authority];qualified=[i.record() for i,r in authority.items() if r['qualified']]
            if publisher is not None:
                publisher.stopped=True
                if isinstance(exc,TimeoutError):raise
                from .s1_progress import ProgressIntegrityError
                raise ProgressIntegrityError(str(exc)) from exc
    if publisher is not None and not publisher.stopped:
        publisher.errors=list(dict.fromkeys(publisher.errors+[e['error'] for e in errors]))[:32]
        if not closed and publisher.coverage not in ('conflict','overflow'):publisher.coverage='incomplete' if not publisher.rows else 'overflow'
        if publisher.rows:
            check();publisher.publish()
    return dict(produced_identities=produced,qualified_identities=qualified,sources=sources,
        verification_errors=errors,scan_complete=closed,counts=evidence_counts(produced,qualified))


def evidence_counts(produced=(), qualified=(), *, complete=False):
    def fit(rows): return sum(i['frame'] < 150 for i in rows)
    return dict(expected=510, complete=510 if complete else 0,
        produced=510 if complete else 'unknown', produced_lower_bound=len(produced),
        qualified=len(qualified), qualified_total=510 if complete else 'unknown',
        fit_expected=340, selection_expected=170,
        fit_produced_lower_bound=fit(produced), selection_produced_lower_bound=len(produced)-fit(produced),
        fit_qualified=fit(qualified), selection_qualified=len(qualified)-fit(qualified))


def numerical_duration(value, field):
    """Accept only finite nonnegative built-in values representable in binary64."""
    import math
    if type(value) not in (int, float):
        raise ValueError(f'S1 {field} requires a finite nonnegative duration')
    try:
        seconds = float(value)
    except (OverflowError, ValueError):
        raise ValueError(f'S1 {field} duration overflows binary64') from None
    if not math.isfinite(seconds) or seconds < 0:
        raise ValueError(f'S1 {field} requires a finite nonnegative duration')
    return seconds


def validate_row_numerics(row):
    seconds = numerical_duration(row.get('native_group_wall_seconds'), 'native_group_wall_seconds')
    if type(row.get('group_size')) is not int or row['group_size'] != 1:
        raise ValueError('S1 group_size must be exact integer 1 for calibration')
    return seconds


def validate_result_numerics(result, config):
    """Bounded local allocator and singleton-group timing consistency only."""
    import math
    from .access import output_identities
    rows = result.get('rows')
    if type(rows) is not list or len(rows) != len(output_identities(config, 'calibration')):
        raise ValueError('S1 numerical rows require the exact calibration count')
    if any(type(row) is not dict for row in rows):
        raise ValueError('S1 numerical rows require mappings')
    durations = [validate_row_numerics(row) for row in rows]
    total = numerical_duration(result.get('native_wall_seconds'), 'native_wall_seconds')
    cap = config['gpu_peak_device_gib_limit'] * 2**30
    for field in ('peak_allocated_bytes', 'peak_reserved_bytes'):
        value = result.get(field)
        if type(value) is not int or value < 0 or value > cap:
            raise ValueError(f'S1 {field} requires nonnegative integer bytes within configured cap')
    if result['peak_allocated_bytes'] > result['peak_reserved_bytes']:
        raise ValueError('S1 peak_allocated_bytes exceeds peak_reserved_bytes')
    try:
        reference = math.fsum(durations)
        # n nonnegative serial additions versus fsum, plus final rounding.
        # JSON preserves the binary64 inputs; no scientific tolerance is added.
        tolerance = (len(rows) + 1) * math.ulp(reference)
    except (OverflowError, ValueError):
        raise ValueError('S1 native_wall_seconds group sum overflows binary64') from None
    if not math.isfinite(reference) or not math.isfinite(tolerance):
        raise ValueError('S1 native_wall_seconds group sum/tolerance is nonfinite')
    if (reference == 0 and total != 0) or (reference != 0 and abs(total-reference) > tolerance):
        raise ValueError('S1 native_wall_seconds differs from singleton group sum')
    return True


@with_deadline
def qualify_row(row, request, *, first=False, loader=None):
    """Recompute retained-query assignments from serialized numeric evidence."""
    from .contracts import instances, validate_static
    from .backends import s1_class_assignments
    from .access import Identity, RGBLoader
    validate_row_numerics(row)
    identity = Identity(**row['identity'])
    if first and identity.record() != dict(branch='calibration', camera=0, frame=50, pair_start=None):
        raise ValueError('first S1 input must be calibration camera 0 frame 50')
    if loader is None:
        loader = input_loader(request)
    parent = loader.row(identity)
    if any(row[k] != parent[k] for k in ('K', 'grid', 'valid')) or row['source_rgb_sha256'] != parent['rgb']['sha256']:
        raise ValueError('S1 input provenance changed')
    operation(verify_record,parent['rgb'])
    if row['grid'] != 'distorted-opencv-integer':
        raise ValueError('S1 requires distorted input grid')
    valid = operation(load_array,row['valid'])
    labels = operation(load_array,row['instances'])
    instances(labels, row['semantics'], valid)
    if labels.dtype != np.int32 or np.any(labels[valid] > 255):
        raise ValueError('S1 labels exceed int32/255 contract')
    import cv2
    static = operation(cv2.imread,operation(verify_record,row['semantic_static'])['path'], cv2.IMREAD_UNCHANGED)
    validate_static(static, valid)
    # Match the existing zero-changing-mask semantic-static contract exactly.
    from .backends import SegmentationResult
    expected_static = SegmentationResult(labels, row['semantics'], valid, {}).static(np.zeros_like(valid))
    if not np.array_equal(static, expected_static):
        raise ValueError('S1 semantic static mismatch')
    with operation(np.load,operation(verify_record,row['diagnostics'])['path'], allow_pickle=False) as raw_arrays:
        arrays = BoundedArrays(raw_arrays)
        if any(k not in arrays for k in REQUIRED) or any(arrays[k].dtype.hasobject for k in arrays.files):
            raise ValueError('missing/non-numeric S1 evidence')
        rgb = operation(loader.load,identity)
        processed = arrays['detector_rgb']
        expected_rgb = operation(processed_rgb,rgb)
        if (processed.shape != expected_rgb.shape or not np.isfinite(processed).all()
                or not np.allclose(processed, expected_rgb, atol=2e-6, rtol=1e-6)):
            raise ValueError('S1 processed RGB differs from frozen native preprocessing')
        scores, logits, boxes = (
            arrays['detector_token_scores'], arrays['detector_raw_token_logits'], arrays['detector_raw_boxes_cxcywh'])
        if (scores.ndim != 2 or logits.shape != scores.shape or boxes.shape != (len(scores), 4)
                or not all(np.isfinite(x).all() for x in (scores, logits, boxes))
                or np.any((scores < 0) | (scores > 1))
                or not np.allclose(scores, 1 / (1 + np.exp(-logits)), atol=1e-7, rtol=1e-6)):
            raise ValueError('invalid raw S1 logits/probabilities/boxes')
        selected = np.flatnonzero(scores.max(axis=1) > .35)
        if (not np.array_equal(selected, arrays['detector_selected_query_indices'])
                or not np.array_equal(boxes[selected], arrays['detector_native_boxes_cxcywh'])
                or not np.array_equal(scores[selected].max(axis=1), arrays['detector_selected_scores'])):
            raise ValueError('S1 native query selection changed')
        ids = arrays['detector_token_ids'].tolist()
        # Frozen BERT uncased caption layout; verify both spans, even with zero detections.
        if ids != [101, 2711, 1012, 3455, 1012, 102]:
            raise ValueError('S1 frozen caption token layout changed')
        class Caption:
            def decode(self, tokens):
                return {(2711,): 'person', (3455,): 'basketball'}[tuple(tokens)]
        detections = row['metadata']['detections']
        encoded = arrays['detector_native_phrase_utf8']
        offsets = arrays['detector_native_phrase_offsets']
        if (encoded.dtype != np.uint8 or encoded.ndim != 1 or offsets.dtype != np.int64
                or offsets.shape != (len(selected)+1,) or offsets[0] != 0
                or offsets[-1] != len(encoded) or np.any(np.diff(offsets) < 0)):
            raise ValueError('S1 invalid native phrase capture')
        phrases = [encoded[a:b].tobytes().decode('utf-8') for a,b in zip(offsets[:-1], offsets[1:])]
        if [d['native_class'] for d in detections] != phrases:
            raise ValueError('S1 native phrase consistency changed')
        pixel = boxes[selected].astype(np.float64) * ([rgb.shape[1], rgb.shape[0]] * 2)
        pixel = np.concatenate((pixel[:,:2]-pixel[:,2:]/2, pixel[:,:2]+pixel[:,2:]/2), axis=1)
        assignments = s1_class_assignments(scores[selected], {'input_ids': ids}, Caption(), phrases, .5)
        if len(detections) != len(selected):
            raise ValueError('S1 retained assignments missing')
        for index, (detection, assignment) in enumerate(zip(detections, assignments)):
            if (detection.get('id') != index+1 or detection.get('index') != index
                    or not np.array_equal(detection.get('box'), pixel[index])
                    or detection['class_assignment'] != assignment or detection['class'] != assignment['derived_class']
                    or detection['score'] != float(arrays['detector_selected_scores'][index])):
                raise ValueError('S1 independently recomputed assignment mismatch')
        native_mapping, skipped = {}, []
        for detection in detections:
            box = np.asarray(detection['box']).astype(np.int64)
            if (box[2]-box[0]) * (box[3]-box[1]) > valid.size:
                skipped.append(detection['index'])
                continue
            native_mapping[detection['index']] = dict(detection, id=len(native_mapping)+1, box=box.tolist())
        if row['metadata'].get('skipped_box_indices') != skipped:
            raise ValueError('S1 skipped detection mapping changed')
        for key, semantic in row['semantics'].items():
            index = semantic.get('index')
            if type(index) is not int or index not in native_mapping:
                raise ValueError('S1 surviving semantic index invalid')
            original = native_mapping[index]
            if str(original['id']) != str(key) or any(semantic.get(k) != original[k]
                    for k in ('id', 'box', 'class', 'native_class', 'score', 'class_assignment')):
                raise ValueError('S1 surviving metadata changed')
    return [dict(name=name, status='passed') for name in
            ('input_identity', 'native_query_alignment', 'all_retained_assignments', 'output_contracts', 'numeric_evidence')]


@with_deadline
def validate_result(result, request, config, *, clock):
    from .s1_clock import require_clock
    require_clock(clock).match(result.get('reservation_clock'))
    from .access import output_identities, validate_membership
    if (result.get('status') != 'complete' or result.get('job_id') != JOB
            or result.get('component') != 'S1' or result.get('branch') != 'calibration'):
        raise ValueError('wrong S1 recovered result')
    validate_membership(result['rows'], output_identities(config, 'calibration'))
    if [r['identity'] for r in result['rows']] != [i.record() for i in output_identities(config, 'calibration')]:
        raise ValueError('S1 calibration order changed')
    validate_result_numerics(result, config)
    qualify_runtime(result['runtime'], request)
    first = operation(read_json,operation(verify_record,result['first_result'])['path'])
    loader = input_loader(request)
    verify_first(first, request, clock=clock, loader=loader)
    if (first['rows'] != result['rows'][:1] or first['runtime'] != result['runtime']
            or first['request'] != result['configuration']):
        raise ValueError('S1 first-result envelope differs from terminal result')
    if operation(read_json,operation(verify_record,result['configuration'])['path']) != request:
        raise ValueError('S1 result request changed')
    for row in result['rows']:
        qualify_row(row, request, loader=loader)
    return True


@with_deadline
def input_loader(request):
    from .access import RGBLoader
    from .config import load
    return RGBLoader(operation(read_json,operation(verify_record,request['inputs'])['path'])['rgb'], load())


def processed_rgb(rgb):
    """Frozen GroundingDINO PIL bilinear resize, ToTensor, Normalize; CPU only."""
    from PIL import Image
    h, w = rgb.shape[:2]
    size = 800
    if max(h,w) / min(h,w) * size > 1333:
        size = int(round(1333 * min(h,w) / max(h,w)))
    oh, ow = (size, int(size*w/h)) if h < w else (int(size*h/w), size)
    image = Image.fromarray(rgb).resize((ow, oh), resample=Image.Resampling.BILINEAR)
    tensor = np.asarray(image).transpose(2,0,1).astype(np.float32) / np.float32(255)
    return (tensor - np.array([.485,.456,.406],np.float32)[:,None,None]) / np.array([.229,.224,.225],np.float32)[:,None,None]


@with_deadline
def verify_first(value, request, *, clock, loader=None):
    from .s1_clock import require_clock
    clock = require_clock(clock)
    clock.match(value.get('reservation_clock'))
    clock.recorded(value.get('elapsed_seconds_from_reservation'), 'passed')
    auth = request['recovery_authorization']
    amendment = operation(read_json,operation(verify_record,auth)['path'])['semantic_amendment']
    seconds = value.get('elapsed_seconds_from_reservation')
    if (value.get('schema') != 'plan032-s1-first-result/v1' or value.get('status') != 'passed'
            or value.get('job_id') != JOB or value.get('count') != 1
            or len(value.get('rows', [])) != 1 or value.get('authorization') != auth
            or value.get('semantic_amendment') != amendment
            or value.get('identity') != value['rows'][0]['identity']
            or value.get('clock_status') != 'verified'
            or value.get('error') is not None or value.get('failure_stage') is not None):
        raise ValueError('passed S1 first-result envelope required')
    if operation(read_json,operation(verify_record,value['request'])['path']) != request:
        raise ValueError('S1 first-result request changed')
    qualify_runtime(value['runtime'], request)
    checks = qualify_row(value['rows'][0], request, first=True, loader=loader)
    if value.get('checks') != checks or value.get('raw_evidence') != [value['rows'][0]['diagnostics']]:
        raise ValueError('S1 first-result checks/raw evidence changed')
    return True


@with_deadline
def qualify_runtime(runtime, request):
    if (not isinstance(runtime, dict) or not isinstance(request, dict)
            or not isinstance(runtime.get('isolation'), dict)):
        raise ValueError('S1 runtime mapping/isolation required')
    if (runtime.get('versions') != request['runtime']['versions']
            or runtime.get('isolation', {}).get('import_guard') is not True
            or runtime['isolation'].get('subprocesses') is not False
            or runtime['isolation'].get('source_roots') != request['forbidden_vipe_roots']):
        raise ValueError('S1 loaded runtime/isolation differs from admission')
    from .s1_recovery import strict_record
    manifest = operation(read_json,operation(strict_record,runtime['loaded_files'])['path'])
    if manifest.get('schema') != 'vipe-benchmark-loaded-runtime/v1' or not manifest.get('files'):
        raise ValueError('S1 loaded runtime manifest required')
    interpreter = manifest.get('interpreter', {})
    executable = interpreter.get('executable', {})
    if (interpreter.get('invoked_executable') != request['runtime']['python']
            or executable != operation(file_record,request['runtime']['python'])):
        raise ValueError('S1 loaded interpreter differs from admission')
    operation(strict_record,executable)
    inventory = operation(read_json,operation(strict_record,request['runtime']['inventory'])['path'])
    if inventory.get('versions') != request['runtime']['versions'] or inventory.get('executable') != request['runtime']['python']:
        raise ValueError('S1 inventory runtime identity changed')
    admitted = {str(Path(f['path']).resolve()): f for p in inventory['packages'] for f in p['files']}
    from .setup_recipes import CORE_IMPORTS
    imports = operation(read_json,operation(strict_record,request['runtime']['imports'])['path'])
    imported = {entry['module']: entry for entry in imports.get('modules', [])}
    if len(imported) != len(imports.get('modules', [])):
        raise ValueError('S1 duplicate E1 import identity')
    required_imports = CORE_IMPORTS['E1']
    for name, source, symbols in required_imports:
        entry = imported.get(name, {})
        if entry.get('source_asset') != source or entry.get('symbols') != symbols or 'file' not in entry:
            raise ValueError('S1 required E1 import identity missing')
        operation(strict_record,entry['file'])
        if source:
            tree = request['assets'][source]
            if entry['file'] not in tree['files']:
                raise ValueError('S1 E1 import differs from admitted source tree')
        elif entry['file'] != admitted.get(entry['file']['path']):
            raise ValueError('S1 E1 import differs from installed inventory')
    build = operation(read_json,operation(strict_record,request['runtime']['build_inputs'])['path'])
    correlation = build.get('correlation', {})
    if correlation.get('version') != '0.5.0' or correlation.get('repository') != 'spatial-correlation-sampler':
        raise ValueError('S1 native correlation build identity missing')
    operation(strict_record,{k:correlation[k] for k in ('path','sha256','bytes')})
    modules, seen, native = set(), set(), False
    loaded_names = {}

    for entry in manifest['files']:
        path = Path(entry['path'])
        names = entry.get('modules', [])
        if (entry['path'] in seen or any(n.split('.')[0] in ('vipe','vipe_ext') for n in names)
                or any(path.resolve().is_relative_to(Path(root).resolve()) for root in request['forbidden_vipe_roots'])):
            raise ValueError('S1 forbidden/duplicate loaded runtime file')
        seen.add(entry['path'])
        record = {k:entry[k] for k in ('path','sha256','bytes')}
        operation(strict_record,record)
        if entry['path'] in admitted and any(record[k] != admitted[entry['path']][k] for k in ('sha256','bytes')):
            raise ValueError('S1 loaded file differs from admitted inventory')
        for name in names:
            if name in loaded_names:
                raise ValueError('S1 duplicate loaded module identity')
            loaded_names[name] = record
            source = {'groundingdino':'grounding_source', 'segment_anything':'sam_source'}.get(name.split('.')[0])
            if source and record not in request['assets'][source]['files']:
                raise ValueError('S1 loaded source differs from admitted asset tree')
        modules.update(n.split('.')[0] for n in names)
        native |= entry.get('mapped_native_library') is True
        if any(n.split('.')[0] in ('torch','torchvision','numpy') for n in names) and entry['path'] not in admitted:
            raise ValueError('S1 required module absent from admitted inventory')
    if any(loaded_names.get(name) != imported[name]['file'] for name, _, _ in required_imports):
        raise ValueError('S1 loaded native/import identity differs from E1')
    native_file = imported['groundingdino._C']['file']
    if not any(e['path'] == native_file['path'] and e.get('mapped_native_library') is True for e in manifest['files']):
        raise ValueError('S1 admitted native extension is not mapped')
    if not {'torch','torchvision','numpy','groundingdino','segment_anything'} <= modules or not native:
        raise ValueError('S1 required loaded modules/native library missing')
    if runtime.get('installed_inventory') != request['runtime']['inventory']:
        raise ValueError('S1 runtime inventory differs')
    operation(verify_record,runtime['installed_inventory'])
