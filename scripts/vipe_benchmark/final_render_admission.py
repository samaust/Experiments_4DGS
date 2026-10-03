"""Explicit selected-depth DO authority, atomically checked on the shared ledger.

REVIEW remains immutable. CPU fixtures can exercise the locked reservation seam
only on a private ledger; they never become actual approvals or qualifications.
"""
import math
from pathlib import Path
import time

from .extended_final_render_contract import admit_review, parse_request
from .files import file_record, object_hash, read_json, verify_record
from .final_render_contract import PHASES

SCHEMA = 'plan069-final-render-do/v1'


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _bound(record):
    _require(type(record) is dict and set(record) == {'path','sha256','bytes'} and
        verify_record(record) == record, 'exact unchanged admission evidence required')
    return read_json(record['path'])


class _Snapshot:
    """Read the already locked snapshot without recursively locking the ledger."""
    def __init__(self, ledger, events):
        self.ledger, self.snapshot, self.config = ledger, events, ledger.config
        self.all_events = events
        self.credit = {}

    def events(self):
        return self.snapshot

    def states(self, events):
        return self.ledger.states(events)

    def totals(self, events):
        totals = self.ledger.totals(self.all_events)
        for resource, amount in self.credit.items():
            totals[resource]["elapsed_seconds"] -= amount
        return totals



def required_sources():
    """Return the fixed current admission/native control source closure."""
    names = ('final_render_admission.py','ledger.py','files.py','extended_final_render_contract.py',
        'final_render_contract.py','final_render_inventory.py','final_render_loaders.py',
        'final_render_matcher.py','final_render_geometry.py','final_render_initializer.py',
        'final_render_native.py','final_render_adapter.py','final_render_actual_result.py',
        'final_render_actual_worker.py','final_render_actual_dispatch.py','final_render_actual_control.py',
        'final_render_actual_supervisor.py','final_render_workers.py','supervisor.py','config.py',
        'depth_review.py','s1_validation_contract.py')
    required = [file_record(Path(__file__).with_name(name)) for name in names]
    required.extend(file_record(Path(__file__).resolve().parents[1]/name) for name in
        ('final-render-actual-worker.py','final-render-actual-control.py'))
    return required

def _actual_evidence(envelope, request, events):
    fields = {'schema','record_kind','mode','request','approval','qualification','commercial',
        'source_review','commands','interpreter','checkout','source_files','ledger_head_sha256','matcher_runtime'}
    _require(set(envelope) == fields, 'exact DO authority envelope required')
    _require(envelope['record_kind'] == 'actual' and envelope['mode'] == 'DO', 'actual DO authority required')
    approval = _bound(envelope['approval'])
    proposal = {k:v for k,v in envelope.items() if k != 'approval'}
    _require(approval.get('schema') == 'plan069-final-render-do-approval/v1' and
        approval.get('record_kind') == 'human' and approval.get('status') == 'approved' and
        bool(approval.get('reviewer','').strip()) and bool(approval.get('approved_at','').strip()) and
        approval.get('proposal_sha256') == object_hash(proposal) and
        approval.get('request') == envelope['request'] and approval.get('allocations') == request['allocations'],
        'explicit frozen human approval for exact allocations required')
    commands = envelope['commands']
    _require(type(commands) is dict and set(commands) ==
        {a['arm']+'/'+a['phase'] for a in request['allocations'] if a['phase'] in PHASES} and
        all(type(argv) is list and len(argv) >= 3 and
            all(type(arg) is str and arg for arg in argv) and argv[0] == envelope['interpreter']['path']
            for argv in commands.values()), 'all exact approved native commands required')
    sources = envelope['source_files']
    required = required_sources()
    _require(type(sources) is list and all(record in sources for record in required),
        'complete current native control/admission source closure required')
    from .final_render_matcher import validate_inventory as validate_matcher_inventory
    validate_matcher_inventory(_bound(envelope['matcher_runtime']))
    for record in [envelope['interpreter'], *sources]:
        _require(verify_record(record) == record, 'current source/interpreter pins changed')
    review = _bound(envelope['source_review'])
    _require(review.get('schema') == 'plan069-final-render-source-review/v1' and
        review.get('record_kind') == 'actual' and review.get('status') == 'passed' and
        bool(review.get('reviewer','').strip()) and review.get('request') == envelope['request'] and
        review.get('source_files') == sources, 'independent current native source review required')
    qualification = _bound(envelope['qualification'])
    runtime_record = request['bindings']['runtime']
    runtime = _bound(runtime_record)
    from .final_render_inventory import validate_inventory
    validate_inventory(runtime,checkout=envelope['checkout'],interpreter=envelope['interpreter']['path'],
        normalization=request['initializer_contract']['normalization'])
    _require(qualification.get('schema') == 'plan069-final-render-native-qualification/v1' and
        qualification.get('record_kind') == 'actual' and qualification.get('status') == 'passed' and
        qualification.get('request') == envelope['request'] and qualification.get('runtime') == runtime_record and
        qualification.get('source_files') == sources and qualification.get('interpreter') == envelope['interpreter'] and
        qualification.get('matcher_runtime') == envelope['matcher_runtime'],
        'actual native qualification for exact runtime/request required')
    runs = qualification.get('runs')
    _require(type(runs) is dict and set(runs) == set(PHASES), 'all native phases require measured qualification')
    for phase, record in runs.items():
        run = _bound(record)
        _require(run.get('job_id') not in {a['id'] for a in request['allocations']},
            'qualification must precede and be independently allocated from production slots')
        _require(run.get('schema') == 'plan069-final-render-native-phase-qualification/v1' and
            run.get('record_kind') == 'actual' and run.get('status') == 'passed' and
            run.get('phase') == phase and run.get('runtime') == runtime_record and
            run.get('cleanup_confirmed') is True and run.get('native_adapter_qualified') is True and
            run.get('request') == envelope['request'] and
            type(run.get('elapsed_seconds')) in (int,float) and math.isfinite(run['elapsed_seconds']) and
            0 < run['elapsed_seconds'] <= PHASES[phase][1] and
            type(run.get('cpu_workers_used')) is int and 0 < run['cpu_workers_used'] <= request['cpu_workers_limit'] and
            type(run.get('peak_device_bytes')) is int and 0 <= run['peak_device_bytes'] <= request['device_bytes_limit'] and
            type(run.get('artifact_bytes')) is int and 0 <= run['artifact_bytes'] <= request['artifact_bytes_limit'],
            'passing measured native phase qualification required')
        _require(any(e.get('event') == 'finish' and e.get('status') == 'complete' and
            e.get('job_id') == run.get('job_id') and e.get('result') == record and
            e.get('cleanup_confirmed') is True and e.get('cleanup_uncertain') is False and
            e.get('deadline_exceeded') is False for e in events),
            'native qualification lacks cleaned successful ledger provenance')
        starts = [e for e in events if e.get('event') == 'reserve' and e.get('job_id') == run['job_id']]
        _require(len(starts) == 1 and starts[0].get('evidence',{}).get('record_kind') == 'actual' and
            starts[0]['evidence'].get('role') == 'native-qualification' and
            starts[0]['evidence'].get('runtime') == runtime_record and
            starts[0]['evidence'].get('source_files') == sources and
            starts[0].get('command') == run.get('command') and
            type(run.get('command')) is list and bool(run['command']) and
            run['command'][0] == envelope['interpreter']['path'],
            'independently allocated actual qualification command/source lineage required')
    commercial = _bound(envelope['commercial'])
    _require(commercial.get('schema') == 'plan069-final-render-commercial-assessment/v1' and
        commercial.get('record_kind') == 'actual' and commercial.get('status') == 'allowed' and
        commercial.get('runtime') == runtime_record and commercial.get('source_files') == sources and
        bool(commercial.get('reviewer','').strip()) and
        set(commercial.get('permissions',{})) == {'code','weights','dependencies','inference_outputs'} and
        all(v == 'allowed' for v in commercial['permissions'].values()) and
        type(commercial.get('primary_sources')) is list and bool(commercial['primary_sources']),
        'exact native commercial permissions required')
    for source in commercial['primary_sources']:
        _bound(source)
    return qualification


def _live(live, request, config, qualification=None):
    fields = {'artifact_bytes','download_bytes','free_disk_bytes','device_bytes','gpu_pids',
        'cpu_workers_used','cleanup_confirmed','observed_unix'}
    _require(type(live) is dict and set(live) == fields, 'complete current live resource reading required')
    for field in fields - {'gpu_pids','cleanup_confirmed','observed_unix'}:
        _require(type(live[field]) is int and live[field] >= 0, 'invalid measured live resources')
    observed = live['observed_unix']
    _require(type(observed) in (int,float) and math.isfinite(observed) and
        0 <= time.time()-observed <= 30, 'stale live resource reading')
    _require(live['gpu_pids'] == [] and live['cleanup_confirmed'] is True,
        'exclusive idle GPU and confirmed cleanup required')
    _require(live['cpu_workers_used'] + request['cpu_workers_limit'] <= config['cpu_max_workers'],
        'live CPU capacity unavailable')
    _require(live['device_bytes'] + request['device_bytes_limit'] <= config['gpu_peak_device_gib_limit']*2**30,
        'live device capacity unavailable')
    if qualification is not None:
        for name in ('initializer_bytes','checkpoint_bytes','cleanup_seconds','checkpoint_seconds'):
            amount = qualification.get(name)
            _require(type(amount) in (int,float) and math.isfinite(amount) and amount > 0,
                'measured retention and cleanup viability required')
        _require(qualification['initializer_bytes'] + qualification['checkpoint_bytes'] < request['artifact_bytes_limit'] and
            qualification['cleanup_seconds'] + qualification['checkpoint_seconds'] < PHASES['train'][1],
            'measured publication/cleanup reserves exceed allocation')
    return {key:live[key] for key in ('artifact_bytes','download_bytes','free_disk_bytes')}


def reserve(envelope_record, ledger, arm, phase, command, *, probe, parent_result=None):
    """Recheck immutable authority and live state under lock, then consume one slot.

    No approval, qualification, allocation or retry is manufactured here. The
    ordinary reserve/finish ledger accounting remains the source of truth.
    """
    envelope = _bound(envelope_record)
    request = _bound(envelope['request'])
    _require(request.get('record_kind') == 'actual', 'actual REVIEW request required; fixture cannot authorize DO')
    if parent_result is not None:
        phases = tuple(PHASES)
        _require(phase in phases and phases.index(phase) > 0, 'geometry cannot consume predecessor')
        # Full publication validation acquires its historical ledger lock. Do
        # this before this reservation's lock; exact bytes/finish are rechecked
        # inside the transaction below, avoiding recursive flock deadlocks.
        from .final_render_actual_result import validate_actual_worker_result
        previous = validate_actual_worker_result(request,arm,phases[phases.index(phase)-1],_bound(parent_result))
        _require(previous['status'] == 'complete', 'complete actual predecessor required')
    return _reserve(envelope_record,ledger,arm,phase,command,probe,parent_result,actual=True)


def reserve_fixture(envelope_record, ledger, arm, phase, command, *, probe, parent_result=None):
    """CPU-only private-ledger simulation; never consume prospective actual slots."""
    envelope = _bound(envelope_record)
    _require(envelope.get('record_kind') == 'fixture' and envelope.get('mode') == 'SIMULATE',
        'explicit fixture simulation required')
    _require(_bound(envelope['request']).get('record_kind') == 'fixture', 'fixture request required')
    _require(ledger.path.name == 'fixture-ledger.jsonl' and ledger.path.parent.resolve() ==
        Path(envelope['request']['path']).parent.resolve(), 'private fixture ledger adjacent to request required')
    _require(all(e.get('record_kind') == 'fixture' or
        e.get('evidence',{}).get('record_kind') == 'fixture' or
        str(e.get('job_id','')).startswith('fixture/') for e in ledger.events()),
        'fixture simulator cannot consume an actual ledger')
    return _reserve(envelope_record,ledger,arm,phase,command,probe,parent_result,actual=False)


def _reserve(envelope_record, ledger, arm, phase, command, probe, parent_result, *, actual):
    with ledger.locked() as (stream, events):
        envelope = _bound(envelope_record)
        request = parse_request(_bound(envelope['request']))
        _require(request['record_kind'] == ('actual' if actual else 'fixture') and
            envelope.get('record_kind') == request['record_kind'], 'authority record kind changed')
        _require(arm in request['compositions'] and phase in PHASES, 'unknown final-render arm/phase')
        _require(type(command) is list and bool(command) and all(type(s) is str and s for s in command),
            'literal nonempty command required')
        head = events[-1]['event_sha256'] if events else None
        if actual:
            grants = [e for e in events if e.get('event') == 'final_render_do_authorized' and
                e.get('request') == envelope['request']]
            _require(len(grants) <= 1 and (grants[0]['envelope'] == envelope_record if grants else
                envelope.get('ledger_head_sha256') == head), 'DO grant missing or initial approval ledger head changed')
            qualification = _actual_evidence(envelope,request,events)
            expected = envelope['commands'].get(arm+'/'+phase)
            _require(command == expected and command[0] == envelope['interpreter']['path'],
                'exact approved command/interpreter required')
        else:
            qualification = None
        live = probe()
        storage = _live(live,request,ledger.config,qualification)
        allocation = next(a for a in request['allocations'] if a['arm'] == arm and a['phase'] == phase)
        job = allocation['id'] if actual else 'fixture/'+allocation['id']
        # Review checks all prospective scope; previously consumed phases are
        # handled below, without weakening the immutable REVIEW parser.
        identities = {a['id'] if actual else 'fixture/'+a['id'] for a in request['allocations']}
        pending = [e for e in events if e.get('job_id') not in identities]
        snapshot = _Snapshot(ledger,pending)
        snapshot.all_events = events
        # The whole REVIEW allocation is tested against the remaining scope.
        # Completed slots retain their actual charges; credit only their planned
        # ceilings to avoid charging the same prospective scope twice.
        for a in request['allocations']:
            identity = a['id'] if actual else 'fixture/'+a['id']
            if ledger.states(events).get(identity,{}).get('event') == 'finish':
                resource_credit = a['resource'] if actual else 'cpu'
                snapshot.credit[resource_credit] = snapshot.credit.get(resource_credit,0) + a['seconds']
        admit_review(request,snapshot,storage)
        states = ledger.states(events)
        _require(not any(e['event'] == 'reserve' for e in states.values()), 'unreconciled active attempt')
        _require(job not in states, 'phase identity consumed; no automatic retry')
        phases = tuple(PHASES)
        index = phases.index(phase)
        if index:
            previous_job = request['id']+'/'+arm+'/'+phases[index-1]
            if not actual:
                previous_job = 'fixture/'+previous_job
            previous = states.get(previous_job,{})
            _require(previous.get('event') == 'finish' and previous.get('status') == 'complete' and
                previous.get('cleanup_confirmed') is True and previous.get('cleanup_uncertain') is False and
                previous.get('deadline_exceeded') is False and
                parent_result is not None and previous.get('result') == parent_result,
                'exact cleaned successful predecessor required')
            _bound(parent_result)
        else:
            _require(parent_result is None, 'geometry cannot consume predecessor')
        resource = allocation['resource'] if actual else 'cpu'
        total = ledger.totals(events)[resource]
        key = 'gpu_total_seconds_limit' if resource == 'gpu' else 'cpu_prepare_score_report_seconds_limit'
        _require(total['elapsed_seconds'] + total['reserved_seconds'] + allocation['seconds'] <= ledger.config[key],
            'cumulative resource wall allocation exhausted')
        evidence = dict(schema='plan069-final-render-reservation-binding/v1',
            record_kind='actual' if actual else 'fixture',envelope=envelope_record,request=envelope['request'],
            arm=arm,phase=phase,parent_result=parent_result,live=live,
            execution_authorized=actual,native_adapter_qualified=actual)
        if actual and not grants:
            ledger._append(stream,events,dict(event='final_render_do_authorized',
                envelope=envelope_record,request=envelope['request'],allocations=request['allocations']))
        return ledger._append(stream,events,dict(event='reserve',job_id=job,resource=resource,
            seconds=allocation['seconds'],command=command,evidence=evidence,monotonic_start=time.monotonic(),
            boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip()))


def invocation_binding(invocation_record, request, arm, phase, *, require_worker=False):
    """Validate a reserved immutable invocation; optionally require its live root.

    A callable or Boolean cannot confer authority. Actual worker code must be the
    root PID/PGID registered by the supervisor, in the exact reserved command.
    """
    import os
    from .ledger import Ledger
    invocation = _bound(invocation_record)
    _require(invocation.get('schema') == 'plan069-final-render-actual-invocation/v1' and
        invocation.get('record_kind') == 'actual' and request.get('record_kind') == 'actual' and
        invocation.get('arm') == arm and invocation.get('phase') == phase and
        _bound(invocation['request']) == parse_request(request), 'exact actual invocation/request required')
    envelope = _bound(invocation['envelope'])
    _require(envelope['request'] == invocation['request'] and envelope.get('schema') == SCHEMA,
        'invocation approved envelope differs')
    config = _bound(request['bindings']['config'])
    ledger = Ledger(invocation['ledger_path'],config)
    with ledger.locked() as (_, events):
        job = request['id']+'/'+arm+'/'+phase
        reservations = [e for e in events if e.get('event') == 'reserve' and e.get('job_id') == job]
        _require(len(reservations) == 1, 'exact consumed actual reservation required')
        reservation = reservations[0]
        grants = [e for e in events[:reservation['sequence']] if
            e.get('event') == 'final_render_do_authorized' and e.get('envelope') == invocation['envelope']]
        _require(len(grants) == 1 and grants[0]['request'] == invocation['request'] and
            grants[0]['allocations'] == request['allocations'], 'exact preceding DO grant required')
        evidence = reservation['evidence']
        _require(evidence.get('schema') == 'plan069-final-render-reservation-binding/v1' and
            evidence.get('record_kind') == 'actual' and evidence.get('execution_authorized') is True and
            evidence.get('native_adapter_qualified') is True and evidence.get('envelope') == invocation['envelope'] and
            evidence.get('request') == invocation['request'] and evidence.get('arm') == arm and
            evidence.get('phase') == phase and evidence.get('parent_result') == invocation.get('parent_result'),
            'invocation does not match actual reservation authority')
        _actual_evidence(envelope,request,events[:reservation['sequence']])
        expected = envelope['commands'].get(arm+'/'+phase)
        _require(reservation['command'] == expected and invocation['interpreter'] == envelope['interpreter'] and
            expected[0] == invocation['interpreter']['path'] and invocation_record['path'] in expected,
            'invocation command/interpreter not reserved')
        _require(invocation['source_files'] == envelope['source_files'], 'invocation control source pins differ')
        for record in [invocation['worker'],invocation['interpreter'],*invocation['source_files']]:
            _require(verify_record(record) == record, 'invocation worker/source bytes changed')
        _require(invocation['worker']['path'] in expected and invocation['worker'] in invocation['source_files'],
            'pinned worker entry not in exact command/control sources')
        if require_worker:
            state = ledger.states(events).get(job,{})
            starts = [e for e in events if e.get('event') == 'started' and e.get('job_id') == job]
            _require(state.get('event') == 'reserve' and len(starts) == 1 and
                starts[0].get('pid') == os.getpid() and starts[0].get('pgid') == os.getpgrp() and
                starts[0].get('invocation') == invocation_record,
                'only registered active worker root can use native authority')
        return dict(request=envelope['request'],envelope=envelope,envelope_record=invocation['envelope'],
            runtime=request['bindings']['runtime'],matcher_runtime=envelope['matcher_runtime'],
            reservation=reservation,invocation=invocation,invocation_record=invocation_record)


def worker_binding(invocation_record, request, arm, phase):
    """Actual model entry gate; always require the registered active worker root."""
    return invocation_binding(invocation_record,request,arm,phase,require_worker=True)


def validate_dispatch_invocation(invocation_record, ledger, reservation):
    """Validate the reserved command before launch, without requiring a PID yet."""
    invocation = _bound(invocation_record)
    _require(Path(invocation['ledger_path']).resolve() == ledger.path.resolve(),
        'invocation shared ledger differs')
    binding = invocation_binding(invocation_record,_bound(invocation['request']),
        invocation['arm'],invocation['phase'])
    _require(binding['reservation'] == reservation, 'dispatch consumed substituted reservation')
    return binding
