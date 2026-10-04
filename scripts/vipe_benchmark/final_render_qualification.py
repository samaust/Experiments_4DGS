"""Independent native qualification authority; never a production DO grant.

Actual jobs require exact frozen human approval before any allocation is consumed.
Private CPU simulations exercise ledger transitions and cannot qualify a runtime.
"""
import math
import os
from pathlib import Path
import sys
import time

from .files import file_record, object_hash, read_json, safe_path, verify_record, write_json
from .final_render_contract import PHASES
from .final_render_admission import _live, interpreter_invocation
from .extended_final_render_contract import parse_request, validate_scene_bindings

SCHEMA='plan069-final-render-qualification-do/v1'
INVOCATION='plan069-final-render-qualification-invocation/v1'
PHASE_RESULT='plan069-final-render-native-phase-qualification/v1'
WORKER_RESULT='plan069-final-render-qualification-worker-result/v1'
COMPLETION='plan069-final-render-qualification-worker-completion/v1'


def _require(condition,message):
    if not condition:
        raise ValueError(message)


def _bound(record):
    _require(type(record) is dict and set(record)=={'path','sha256','bytes'} and
        verify_record(record)==record,'exact unchanged qualification evidence required')
    return read_json(record['path'])


def validate_scope(scope):
    """Bind reviewed compatibility observations without claiming production adequacy."""
    _require(type(scope) is dict and set(scope)=={'purpose','actions','settings','production_adequacy_established'} and
        scope['purpose']=='compatibility' and scope['production_adequacy_established'] is False and
        type(scope['actions']) is list and bool(scope['actions']) and
        all(type(action) is str and bool(action.strip()) for action in scope['actions']) and
        type(scope['settings']) is dict and bool(scope['settings']),
        'explicit compatibility scope required; production adequacy is not established')
    return scope


def required_sources():
    from .final_render_admission import required_sources as production_sources
    records=production_sources()
    records.extend(file_record(Path(__file__).with_name(name)) for name in
        ('final_render_qualification.py','final_render_qualification_supervisor.py',
         'final_render_qualification_control.py'))
    records.extend(file_record(Path(__file__).resolve().parents[1]/name) for name in
        ('final-render-qualification-control.py',))
    return records


def validate_authority(record,*,actual=True):
    envelope=_bound(record)
    request=_bound(envelope['request'])
    kind='actual' if actual else 'fixture'
    _require(request.get('record_kind')==kind, 'actual REVIEW request required' if actual else 'fixture REVIEW request required')
    request=parse_request(request)
    _require(envelope.get('schema')==SCHEMA and envelope.get('record_kind')==kind and
        envelope.get('mode')==('QUALIFY' if actual else 'SIMULATE'),'distinct qualification authority required')
    fields={'schema','record_kind','mode','request','approval','commercial','source_review',
        'source_files','runtime','matcher_runtime','checkout','interpreter','interpreter_invocation',
        'arm','allocations','commands','worker','ledger_head_sha256'}
    _require(set(envelope)==fields,'exact qualification authority fields required')
    arm=envelope['arm']
    _require(arm in request['compositions'],'unknown qualification arm')
    _require(envelope['runtime']==request['bindings']['runtime'],'qualification runtime/request differs')
    allocations=envelope['allocations']
    _require(type(allocations) is list and len(allocations)==len(PHASES),'four independent phase allocations required')
    identities=set()
    for allocation,phase in zip(allocations,PHASES):
        _require(type(allocation) is dict and set(allocation)=={'id','phase','resource','seconds','scope'} and
            allocation['phase']==phase and allocation['resource']==PHASES[phase][0] and
            type(allocation['seconds']) is int and 30<allocation['seconds']<=PHASES[phase][1] and
            bool(validate_scope(allocation['scope'])),'exact qualification phase scope/bounds required')
        identity=allocation['id']
        _require(type(identity) is str and identity.startswith('native-qualification/') and
            all(part and all(c.isalnum() or c in '-_' for c in part) for part in identity.split('/')) and
            identity not in identities and identity not in {a['id'] for a in request['allocations']},
            'fresh distinct qualification identities required')
        identities.add(identity)
    commands=envelope['commands']
    _require(type(commands) is dict and set(commands)==set(PHASES) and all(
        type(argv) is list and len(argv)>=3 and all(type(v) is str and bool(v) for v in argv)
        for argv in commands.values()),'exact qualification commands required')
    if not actual:
        _require(all(envelope[name] is None for name in ('approval','commercial','source_review')),
            'fixture authority cannot carry actual approval/evidence')
        return envelope,request
    _require(request['cpu_workers_limit']>=2,'worker and supervision CPU capacity required')
    validate_scene_bindings(request)
    approval=_bound(envelope['approval'])
    _require(approval.get('schema')=='plan069-final-render-qualification-approval/v1' and
        approval.get('record_kind')=='human' and approval.get('status')=='approved' and
        type(approval.get('reviewer')) is str and bool(approval['reviewer'].strip()) and
        type(approval.get('approved_at')) is str and bool(approval['approved_at'].strip()) and
        approval.get('proposal_sha256')==object_hash({k:v for k,v in envelope.items() if k!='approval'}) and
        approval.get('request')==envelope['request'] and approval.get('allocations')==allocations,
        'independent frozen human qualification approval required')
    sources=envelope['source_files']
    _require(type(sources) is list and all(r in sources for r in required_sources()),
        'current complete qualification/native source closure required')
    _require(envelope['worker'] in sources,'reviewed qualification producer source required')
    for source in [envelope['worker'],envelope['interpreter'],*sources]:
        _require(verify_record(source)==source,'changed qualification source/interpreter')
    runtime=_bound(envelope['runtime'])
    matcher=_bound(envelope['matcher_runtime'])
    from .final_render_inventory import validate_inventory
    from .final_render_matcher import validate_inventory as validate_matcher
    validate_inventory(runtime,checkout=envelope['checkout'],interpreter=envelope['interpreter_invocation'],
        normalization=request['initializer_contract']['normalization'])
    validate_matcher(matcher)
    for inventory in (runtime,matcher):
        _require(inventory['interpreter']==envelope['interpreter'],'qualification interpreter bytes differ')
        interpreter_invocation(envelope['interpreter'],envelope['interpreter_invocation'],
            environment_prefix=inventory['environment_prefix'])
    _require(all(argv[0]==envelope['interpreter_invocation'] and envelope['worker']['path'] in argv for argv in commands.values()),
        'exact approved qualification interpreter required')
    review=_bound(envelope['source_review'])
    _require(review.get('schema')=='plan069-final-render-qualification-source-review/v1' and
        review.get('record_kind')=='actual' and review.get('status')=='passed' and
        type(review.get('reviewer')) is str and bool(review['reviewer'].strip()) and
        review.get('request')==envelope['request'] and review.get('source_files')==sources,
        'independent qualification source review required')
    commercial=_bound(envelope['commercial'])
    _require(commercial.get('schema')=='plan069-final-render-commercial-assessment/v1' and
        commercial.get('record_kind')=='actual' and commercial.get('status')=='allowed' and
        commercial.get('runtime')==envelope['runtime'] and commercial.get('source_files')==sources and
        type(commercial.get('reviewer')) is str and bool(commercial['reviewer'].strip()) and
        commercial.get('permissions')==dict.fromkeys(('code','weights','dependencies','inference_outputs'),'allowed') and
        type(commercial.get('primary_sources')) is list and bool(commercial['primary_sources']),
        'exact qualification commercial permissions required')
    for source in commercial['primary_sources']:
        _require(verify_record(source)==source,'changed qualification license evidence')
    return envelope,request


def reserve(authority_record,ledger,phase,command,*,probe,parent_result=None):
    validate_authority(authority_record)
    if parent_result is not None:
        parent=_bound(parent_result)
        validate_phase_result(parent,parent['invocation'],published=True)
    return _reserve(authority_record,ledger,phase,command,probe,parent_result,actual=True)


def reserve_fixture(authority_record,ledger,phase,command,*,probe,parent_result=None):
    envelope,_=validate_authority(authority_record,actual=False)
    _require(ledger.path.name=='fixture-ledger.jsonl' and ledger.path.parent.resolve()==
        Path(envelope['request']['path']).parent.resolve(),'private adjacent fixture ledger required')
    return _reserve(authority_record,ledger,phase,command,probe,parent_result,actual=False)


def _reserve(authority_record,ledger,phase,command,probe,parent_result,*,actual):
    with ledger.locked() as (stream,events):
        envelope,request=validate_authority(authority_record,actual=actual)
        _require(phase in PHASES and command==envelope['commands'][phase], 'exact qualification phase command required')
        if not actual:
            _require(all(e.get('record_kind')=='fixture' or e.get('evidence',{}).get('record_kind')=='fixture'
                for e in events),'fixture cannot mutate actual ledger')
        grants=[e for e in events if e.get('event')=='native_qualification_authorized' and
            e.get('envelope')==authority_record]
        head=events[-1]['event_sha256'] if events else None
        _require(len(grants)<=1 and (bool(grants) or envelope['ledger_head_sha256']==head),
            'initial qualification approval ledger head changed')
        states=ledger.states(events)
        _require(not any(e['event']=='reserve' for e in states.values()),'unreconciled active attempt')
        _require(not any(e.get('event')=='finish' and (e.get('cleanup_confirmed') is not True or
            e.get('cleanup_uncertain') is not False) for e in states.values()),'uncertain cleanup blocks qualification')
        storage=_live(probe(),request,ledger.config)
        _require(storage['artifact_bytes']+request['artifact_bytes_limit']<=ledger.config['new_artifact_disk_gib_limit']*2**30 and
            storage['download_bytes']<=ledger.config['new_download_gib_limit']*2**30 and
            storage['free_disk_bytes']>=request['artifact_bytes_limit'],'qualification storage scope unavailable')
        allocation=next(a for a in envelope['allocations'] if a['phase']==phase)
        job=allocation['id'] if actual else 'fixture/'+allocation['id']
        _require(job not in states,'qualification identity consumed; fresh approval required')
        preceding=tuple(PHASES).index(phase)
        if preceding:
            previous=envelope['allocations'][preceding-1]['id']
            previous=previous if actual else 'fixture/'+previous
            finish=states.get(previous,{})
            _require(parent_result is not None and finish.get('event')=='finish' and
                finish.get('status')=='complete' and finish.get('cleanup_confirmed') is True and
                finish.get('cleanup_uncertain') is False and finish.get('deadline_exceeded') is False and
                finish.get('result')==parent_result,'exact cleaned qualification predecessor required')
            parent=_bound(parent_result)  # Full publication validation precedes this lock.
            if actual:
                supervision=_bound(finish['supervision'])
                _require(supervision.get('status')=='complete' and
                    supervision.get('invocation')==parent['invocation'] and
                    supervision.get('cleanup_confirmed') is True and
                    supervision.get('cleanup_uncertain') is False and
                    supervision.get('native_adapter_qualified') is False and
                    supervision.get('acceptance',{}).get('result')==parent_result,
                    'completed independent compatibility supervision required')
        else:
            _require(parent_result is None,'geometry qualification cannot consume predecessor')
        totals=ledger.totals(events)
        for resource,key in [('gpu','gpu_total_seconds_limit'),('cpu','cpu_prepare_score_report_seconds_limit')]:
            outstanding=sum(a['seconds'] for a in envelope['allocations'] if
                (a['resource'] if actual else 'cpu')==resource and
                (a['id'] if actual else 'fixture/'+a['id']) not in states)
            _require(totals[resource]['elapsed_seconds']+totals[resource]['reserved_seconds']+outstanding<=ledger.config[key],
                'independent qualification cumulative resource allocation exhausted')
        evidence=dict(schema='plan069-final-render-qualification-reservation-binding/v1',
            record_kind='actual' if actual else 'fixture',role='native-qualification',envelope=authority_record,
            request=envelope['request'],arm=envelope['arm'],phase=phase,parent_result=parent_result,
            runtime=envelope['runtime'],source_files=envelope['source_files'],scope=allocation['scope'],
            execution_authorized=actual,native_adapter_qualified=False)
        if not grants:
            ledger._append(stream,events,dict(event='native_qualification_authorized',record_kind='actual' if actual else 'fixture',
                envelope=authority_record,request=envelope['request'],allocations=envelope['allocations']))
        return ledger._append(stream,events,dict(event='reserve',job_id=job,
            resource=allocation['resource'] if actual else 'cpu',seconds=allocation['seconds'],
            command=command,evidence=evidence,monotonic_start=time.monotonic(),
            boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip()))


def invocation_binding(invocation_record,request,arm,phase,*,require_worker=False):
    """Gate independent compatibility workers; this gate never supplies DO authority."""
    invocation=_bound(invocation_record)
    _require(invocation.get('schema')==INVOCATION and invocation.get('record_kind')=='actual' and
        request.get('record_kind')=='actual','actual qualification invocation/request required')
    envelope,checked=validate_authority(invocation['envelope'])
    _require(checked==parse_request(request) and invocation['request']==envelope['request'] and
        invocation['arm']==arm==envelope['arm'] and invocation['phase']==phase and phase in PHASES,
        'exact qualification request/arm/phase required')
    allocation=next(a for a in envelope['allocations'] if a['phase']==phase)
    _require(invocation.get('allocation_id')==allocation['id'] and invocation.get('scope')==allocation['scope'] and
        invocation.get('source_files')==envelope['source_files'] and
        invocation.get('interpreter')==envelope['interpreter'] and
        invocation.get('interpreter_invocation')==envelope['interpreter_invocation'] and
        invocation.get('worker')==envelope['worker'],'qualification invocation authority differs')
    from .ledger import Ledger
    ledger=Ledger(invocation['ledger_path'],_bound(request['bindings']['config']))
    with ledger.locked() as (_,events):
        reservations=[e for e in events if e.get('event')=='reserve' and e.get('job_id')==allocation['id']]
        _require(len(reservations)==1,'exact consumed independent qualification reservation required')
        reservation=reservations[0]
        grants=[e for e in events[:reservation['sequence']] if e.get('event')=='native_qualification_authorized' and
            e.get('envelope')==invocation['envelope']]
        _require(len(grants)==1 and grants[0]['request']==envelope['request'] and
            grants[0]['allocations']==envelope['allocations'],'preceding independent qualification grant required')
        evidence=reservation['evidence']
        _require(evidence.get('schema')=='plan069-final-render-qualification-reservation-binding/v1' and
            evidence.get('record_kind')=='actual' and evidence.get('role')=='native-qualification' and
            evidence.get('execution_authorized') is True and evidence.get('native_adapter_qualified') is False and
            evidence.get('envelope')==invocation['envelope'] and evidence.get('request')==envelope['request'] and
            evidence.get('runtime')==envelope['runtime'] and evidence.get('source_files')==envelope['source_files'] and
            evidence.get('scope')==allocation['scope'] and evidence.get('arm')==arm and evidence.get('phase')==phase and
            evidence.get('parent_result')==invocation.get('parent_result') and
            reservation.get('seconds')==allocation['seconds'] and reservation.get('resource')==allocation['resource'],
            'exact qualification reservation authority required')
        command=envelope['commands'][phase]
        _require(reservation['command']==command and command[0]==invocation['interpreter_invocation'] and
            invocation_record['path'] in command and invocation['worker']['path'] in command and
            '--release-file' in command and command[command.index('--release-file')+1]==invocation.get('release_path'),
            'literal independently approved qualification command required')
        root=ledger.path.resolve().parent
        output=safe_path(invocation['output']).resolve()
        release=safe_path(invocation['release_path']).resolve()
        _require(str(root)==invocation.get('run_root') and output.is_relative_to(root) and
            release.is_relative_to(root) and safe_path(invocation_record['path']).resolve().is_relative_to(root) and
            not output.is_relative_to(release) and not release.is_relative_to(output),
            'qualification output/control must remain in charged study root')
        if require_worker:
            starts=[e for e in events if e.get('event')=='started' and e.get('job_id')==allocation['id']]
            _require(os.path.abspath(sys.executable)==invocation['interpreter_invocation'] and
                ledger.states(events).get(allocation['id'],{}).get('event')=='reserve' and len(starts)==1 and
                starts[0].get('pid')==os.getpid() and starts[0].get('pgid')==os.getpgrp() and
                starts[0].get('invocation')==invocation_record,'only registered active qualification root may execute')
    return dict(request=envelope['request'],envelope=envelope,envelope_record=invocation['envelope'],
        runtime=envelope['runtime'],matcher_runtime=envelope['matcher_runtime'],reservation=reservation,
        invocation=invocation,invocation_record=invocation_record)


def validate_dispatch_invocation(invocation_record,ledger,reservation):
    invocation=_bound(invocation_record)
    _require(safe_path(invocation['ledger_path']).resolve()==ledger.path.resolve(),'qualification ledger differs')
    binding=invocation_binding(invocation_record,_bound(invocation['request']),invocation['arm'],invocation['phase'])
    _require(binding['reservation']==reservation,'qualification reservation substituted')
    return binding


def validate_phase_result(result,invocation_record,*,published=False):
    """Validate measured compatibility evidence; never produce passing qualification.

    A successful compatibility observation remains insufficient for production
    memory/retention adequacy or a completed 5,000-step trained endpoint.
    """
    invocation=_bound(invocation_record)
    _require(result.get('record_kind')==invocation.get('record_kind')=='actual','actual compatibility observations required')
    request=_bound(invocation['request'])
    binding=invocation_binding(invocation_record,request,invocation['arm'],invocation['phase'])
    allocation=next(a for a in binding['envelope']['allocations'] if a['phase']==invocation['phase'])
    fields={'schema','record_kind','status','compatibility_only','native_adapter_qualified','execution_authorized',
        'invocation','request','runtime','matcher_runtime','source_files','job_id','arm','phase','scope','command',
        'elapsed_seconds','cpu_workers_used','peak_device_bytes','artifact_bytes','cleanup_confirmed','observations','artifacts'}
    _require(type(result) is dict and set(result)==fields and result['schema']==PHASE_RESULT and
        result['status']=='measured' and result['compatibility_only'] is True and
        result['native_adapter_qualified'] is False and result['execution_authorized'] is True and
        result['invocation']==invocation_record and result['request']==binding['request'] and
        result['runtime']==binding['runtime'] and result['matcher_runtime']==binding['matcher_runtime'] and
        result['source_files']==binding['envelope']['source_files'] and result['job_id']==allocation['id'] and
        result['arm']==invocation['arm'] and result['phase']==invocation['phase'] and result['scope']==allocation['scope'] and
        result['command']==binding['reservation']['command'] and result['cleanup_confirmed'] is True,
        'exact measured compatibility receipt required; passing production qualification cannot be inferred')
    elapsed=result['elapsed_seconds']
    _require(type(elapsed) in (int,float) and math.isfinite(elapsed) and 0<elapsed<allocation['seconds'],
        'positive bounded measured qualification elapsed required')
    for name,limit in [('cpu_workers_used',request['cpu_workers_limit']),
            ('peak_device_bytes',request['device_bytes_limit']),('artifact_bytes',request['artifact_bytes_limit'])]:
        _require(type(result[name]) is int and 0<=result[name]<=limit,'invalid/excessive qualification '+name)
    _require(result['cpu_workers_used']>0,'measured positive worker usage required')
    artifacts=result['artifacts']
    output=safe_path(invocation['output']).resolve()
    _require(type(artifacts) is list and bool(artifacts) and len({r['path'] for r in artifacts})==len(artifacts) and
        all(verify_record(r)==r and safe_path(r['path']).resolve().is_relative_to(output) for r in artifacts) and
        sum(r['bytes'] for r in artifacts)<=result['artifact_bytes'],'immutable bounded compatibility artifacts required')
    observations=_bound(result['observations'])
    _require(result['observations'] in artifacts and observations.get('schema')=='plan069-native-compatibility-observations/v1' and
        observations.get('record_kind')=='actual' and observations.get('scope')==allocation['scope'] and
        observations.get('production_adequacy_established') is False,'exact limited compatibility observations required')
    if published:
        _require(not (output/'failure.json').exists() and not (output/'terminal-publication-failure.json').exists() and
            not (output.parent/(output.name+'-controls')/'terminal-publication-failure.json').exists(),
            'compatibility publication failed')
        completion=_bound(file_record(output/'completion.json'))
        _require(completion==dict(schema=COMPLETION,record_kind='actual',status='measured',
            invocation=invocation_record,result=file_record(output/'result.json'),cleanup_confirmed=True,
            native_adapter_qualified=False,compatibility_only=True) and
            _bound(completion['result'])==result,'exact measured compatibility completion required')
    return result
