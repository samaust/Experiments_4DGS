"""Plan049 sole exec driver: explicit no-timeout mode, no operational ceilings."""
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
RUN=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts'))
from vipe_benchmark.s1_validation_contract import session_json, session_proof, no_timeout_launch, identity_record, _identity_record, identity_projection
from vipe_benchmark.s1_helper_session import prepare_job_ledger,initialize_job_ledger,append_job_event,_prepare_owned_candidate,census,owned_charge

def stamp():return dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),monotonic=time.monotonic())
def record(path):
    raw=Path(path).read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def publish(path,value):
    raw=(json.dumps(value,indent=2,allow_nan=False)+'\n').encode()
    with path.open('xb',buffering=0) as stream:
        if stream.write(raw)!=len(raw):raise OSError('short launch evidence write')
        stream.flush();os.fsync(stream.fileno())
    if path.read_bytes()!=raw:raise ValueError('launch evidence readback')
    return record(path)
def identity_difference(stage,check,expected,observed,*,not_sampled=(),invariant=None):
    """Pure failed-comparison diagnostics from retained operands; no observations."""
    paths=set()
    def pointer(key):return str(key).replace('~','~0').replace('/','~1')
    def compare(left,right,path):
        if type(left) is not type(right):
            paths.add(path);return
        if type(left) is dict:
            for key in sorted(set(left)|set(right)):
                child=path+'/'+pointer(key)
                if key not in left or key not in right:paths.add(child)
                else:compare(left[key],right[key],child)
        elif type(left) in (list,tuple):
            common=min(len(left),len(right))
            for index in range(common):compare(left[index],right[index],path+'/'+str(index))
            if len(left)!=len(right):
                paths.add(path)
                for index in range(common,max(len(left),len(right))):paths.add(path+'/'+str(index))
        elif left!=right:paths.add(path)
    if invariant=='threads_nonempty':paths.add('/threads_before_after')
    else:compare(expected,observed,'')
    return 'plan049-identity-diff/v1 '+json.dumps(dict(schema='plan049-identity-diff/v1',stage=stage,check=check,
        different_paths=sorted(paths),not_sampled=list(not_sampled),invariant=invariant),sort_keys=True,separators=(',',':'),allow_nan=False)

def attempt_evidence_names(kind,index):
    value=str(index).zfill(3);names={
        'launch-identity-049-%s-%s.json'%(kind,value),
        'launch-admission-049-%s-%s.json'%(kind,value),
        'launch-note-049-%s-%s.json'%(kind,value),
        'driver-049-%s-%s-exec-start.json'%(kind,value),
        'driver-049-%s-%s-stdout.log'%(kind,value),
        'driver-049-%s-%s-stderr.log'%(kind,value),
        '.job-ledger-%s-049-%s.jsonl'%(kind,value),
        '.job-ledger-%s-049-%s.lock'%(kind,value),
        'main-session-proof-049-%s-%s.json'%(kind,value),
        'main-admission-preparation-049-%s-%s.json'%(kind,value),
        'main-launch-preparation-049-%s-%s.json'%(kind,value),
        'main-process-preflight-049-%s-%s.json'%(kind,value),
        'main-preflight-049-%s-%s-final.json'%(kind,value),
        'main-launch-state-049-%s-%s.json'%(kind,value),
        'main-cleanup-049-%s-%s.json'%(kind,value),
        'main-storage-049-%s-%s.json'%(kind,value),
    }
    names.update('main-%s-049-%s-%s.json'%(stem,kind,value) for stem in
        ('launch-attempt-start','launch-attempt-terminal','launch-start','launch-terminal','attempt-start','attempt-terminal','start','terminal'))
    if kind=='diagnostic':
        names.update(('main-diagnostic-outcome-049-diagnostic-%s.json'%value,
                      'main-diagnostic-timestamp-correction-049-diagnostic-%s.json'%value))
    return names

def attempt_high_water(kind):
    patterns=[re.compile(r'launch-(?:identity|admission|note)-049-'+kind+r'-(\d+)\.json'),
        re.compile(r'driver-049-'+kind+r'-(\d+)-(?:exec-start\.json|stdout\.log|stderr\.log)'),
        re.compile(r'\.job-ledger-'+kind+r'-049-(\d+)\.(?:jsonl|lock)'),
        re.compile(r'main-session-proof-049-'+kind+r'-(\d+)\.json'),
        re.compile(r'main-session-049-'+kind+r'-(\d+)-(?:event|send|poll|terminal)-(\d+)\.json'),
        re.compile(r'main-(?:launch-)?(?:attempt-)?(?:start|terminal)-049-'+kind+r'-(\d+)\.json'),
        re.compile(r'main-(?:admission-preparation|launch-preparation|process-preflight|launch-state|cleanup)-049-'+kind+r'-(\d+)\.json'),
        re.compile(r'main-preflight-049-'+kind+r'-(\d+)-final\.json'),
        re.compile(r'main-storage-049-'+kind+r'-(\d+)\.json')]
    if kind=='diagnostic':patterns.extend((re.compile(r'main-diagnostic-outcome-049-diagnostic-(\d+)\.json'),re.compile(r'main-diagnostic-timestamp-correction-049-diagnostic-(\d+)\.json'),re.compile(r'main-storage-049-(\d+)\.json')))
    found=[]
    for path in RUN.iterdir():
        if path.is_symlink():
            if any(pattern.fullmatch(path.name) for pattern in patterns) or re.fullmatch(r'main-launch-(?:attempt-start|terminal)-\d+\.json',path.name):raise ValueError('symlink in Plan049 attempt high-water evidence')
        if path.parent!=RUN:raise ValueError('non-direct Plan049 evidence enumeration')
        for pattern in patterns:
            match=pattern.fullmatch(path.name)
            if match:
                found.append(int(match[1]));break
        legacy=re.fullmatch(r'main-launch-(?:attempt-start|terminal)-(\d+)\.json',path.name)
        if legacy:
            prior=session_json(path);prior_kind=prior.get('kind');prior_index=prior.get('index',prior.get('attempt_index'))
            if prior_kind is None and type(prior.get('driver_command')) is list and len(prior['driver_command'])==7:
                try:prior_kind=prior['driver_command'][4];prior_index=int(prior['driver_command'][5])
                except (TypeError,ValueError,IndexError):raise ValueError('malformed legacy attempt high-water evidence') from None
            if prior_kind==kind:
                if type(prior_index) is not int or prior_index<1:raise ValueError('unknown legacy attempt index')
                found.append(prior_index)
        old_storage=re.fullmatch(r'main-storage-049-(\d+)\.json',path.name)
        if kind=='diagnostic' and old_storage:found.append(int(old_storage[1]))
    return max(found,default=0)

def main():
    kind,index,reason=sys.argv[1],int(sys.argv[2]),sys.argv[3]
    if kind not in ('diagnostic','aggregate') or index<1 or not reason.strip():raise ValueError('launch kind/index/reason')
    if index!=attempt_high_water(kind)+1:raise ValueError('candidate must be the next vacant high-water index')
    directory=RUN/(kind+'-049-'+str(index).zfill(3))
    if directory.exists() or directory.is_symlink():raise ValueError('output path occupied')
    for name in attempt_evidence_names(kind,index):
        path=RUN/name
        if path.exists() or path.is_symlink():raise ValueError('attempt evidence output path occupied: '+name)
    # Prepare exact bootstrap bytes without touching the filesystem. Main then
    # binds the opaque returned exec handle before the ledger's first mutation.
    prepared_ledger=prepare_job_ledger(kind,index)
    job_ledger={key:prepared_ledger[key] for key in ('path','lock','initial_sha256','schema')}
    boot_line=json.dumps(dict(awaiting_main_start_proof=job_ledger,kind=kind,index=index),sort_keys=True,separators=(',',':'))
    print(boot_line,flush=True)
    frame=session_json_line=sys.stdin.readline()
    digit_limit=sys.get_int_max_str_digits()
    try:
        if digit_limit and digit_limit<20000:sys.set_int_max_str_digits(20000)
        try:start_frame=json.loads(session_json_line)
        except (TypeError,ValueError):raise ValueError('Main start proof JSON frame') from None
        valid_frame=type(start_frame) is dict and set(start_frame)=={'schema','session_id','event'} and start_frame['schema']=='plan049-main-start-frame/v1' and type(start_frame['session_id']) is int and start_frame['session_id']>0 and len(str(start_frame['session_id']))<=16384
    finally:
        if digit_limit and digit_limit<20000:sys.set_int_max_str_digits(digit_limit)
    if not valid_frame:
        raise ValueError('Main start proof frame')
    start_event=start_frame['event']
    if type(start_event) is not dict or set(start_event)!={'schema','kind','index','ordinal','role','tool','arguments','result','started','returned','output_sha256'} or start_event['schema']!='plan049-session-tool-event/v2' or start_event['kind']!=kind or type(start_event['index']) is not int or start_event['index']!=index or type(start_event['ordinal']) is not int or start_event['ordinal']!=0 or start_event['role']!='start' or start_event['tool']!='exec_command' or type(start_event['result']) is not dict or type(start_event['result'].get('session_id')) is not int or start_event['result']['session_id']!=start_frame['session_id']:
        raise ValueError('exact returned Main session handle')
    if type(start_event.get('result',{}).get('output')) is not str or start_event['result']['output'] not in (boot_line+'\n',boot_line+'\r\n') or start_event['result'].get('exit_code') is not None or start_event['result'].get('error') or start_event['result'].get('isError'):
        raise ValueError('Main live bootstrap output')
    if start_event.get('output_sha256')!=hashlib.sha256(start_event['result']['output'].encode()).hexdigest() or start_event.get('arguments',{}).get('cmd')!=__import__('shlex').join(['exec',str(ROOT/'.local/envs/stg-colmap/bin/python'),'-B',str(Path(__file__).resolve()),kind,str(index),reason]):
        raise ValueError('Main bootstrap command/output binding')
    for key in ('started','returned'):
        if type(start_event.get(key)) is not dict or set(start_event[key])!={'utc'}:raise ValueError('Main bootstrap UTC stamp')
        try:observed=datetime.datetime.fromisoformat(start_event[key]['utc'])
        except (KeyError,TypeError,ValueError):raise ValueError('Main bootstrap UTC') from None
        if observed.tzinfo is None or observed.utcoffset()!=datetime.timedelta(0):raise ValueError('Main bootstrap UTC timezone')
    if datetime.datetime.fromisoformat(start_event['started']['utc'])>datetime.datetime.fromisoformat(start_event['returned']['utc']):raise ValueError('Main bootstrap event order')
    suffix=kind+'-'+str(index).zfill(3)
    # Include unadmitted/retired driver attempts, not only capture starts.
    counts={k:len(list(RUN.glob('driver-049-'+k+'-*-exec-start.json'))) for k in ('diagnostic','aggregate')}
    admission_path=RUN/('launch-admission-049-'+suffix+'.json')
    if admission_path.exists() or admission_path.is_symlink():raise ValueError('preexisting admission forbidden')
    # Main binds the opaque tool session to local identity, never a predicted PID.
    # The sole driver may wait on its existing stdin for Main's explicit ADMIT.
    admission=None
    dispatch_path=RUN/'implementation-dispatch-049.json';dispatch=session_json(dispatch_path)
    plan=record(ROOT/'plans/plan_049.md');status=dispatch['implementation_status_snapshot'];authorization=dispatch['authorization_note']
    # The immutable dispatch binds the original Plan049 revision. Plan049 was
    # subsequently amended under the user's six-lane authorization and the
    # adopted Plan053 measured-size review; retain both identities explicitly.
    if (dispatch['schema']!='plan049-implementation-dispatch/v1'
            or dispatch['plan']!={'path':str(ROOT/'plans/plan_049.md'),'sha256':'a27329ee5c9d9439515093e6797ad72f61bd6faf1e43c5f45f2b2cf4c013cc1f'}
            or plan['sha256']!='89d1f634ad2407b02558ff9c030d4a4f12f8f4ab010c93e2cf532876564afe7e'):
        raise ValueError('fixed original dispatch and adopted Plan049 revision')
    if status['path']!=str(RUN/'implementation-status-049.md') or record(Path(status['path']))!=status:raise ValueError('fixed immutable status')
    if authorization['path']!=str(RUN/'authorization-049.md') or record(Path(authorization['path']))!=authorization:raise ValueError('fixed authorization')
    if any(dispatch['authorization'][key] is not None for key in ('invocation_timeout','attempt_ceiling','correction_ceiling','operational_duration_ceiling_seconds')):raise ValueError('no-timeout authority required')
    contract=ast.parse((ROOT/'scripts/vipe_benchmark/s1_validation_contract.py').read_text())
    stdin=ast.literal_eval(next(n.value for n in contract.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='STDIN' for t in n.targets))).encode()
    function=next(n for n in contract.body if isinstance(n,ast.FunctionDef) and n.name=='source_paths')
    paths=[]
    for item in function.body[0].value.args[0].elts:
        if isinstance(item,ast.BinOp):paths.append(ROOT/ast.literal_eval(item.right))
        else:
            call=item.value;paths.extend((ROOT/ast.literal_eval(call.func.value.right)).glob(ast.literal_eval(call.args[0])))
    sources=[record(path) for path in sorted(paths)]
    if len(sources)!=78:raise ValueError('source membership count')
    for path in paths:
        if path.suffix=='.py':ast.parse(path.read_bytes())
    command=[str(ROOT/'.local/envs/stg-colmap/bin/python'),'-B','-m','vipe_benchmark.s1_validation_capture',str(directory),'--no-timeout']
    if kind=='diagnostic':command.append('--diagnostic')
    settings={key:'1' for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','OPENCV_FOR_THREADS_NUM','VIPE_CPU_VALIDATION')}
    settings['PYTHONPATH']=str(ROOT/'scripts');env=dict(os.environ,**settings)
    for key in ('S1_HELPER_DIAGNOSTIC','S1_RECEIPT_DIAGNOSTIC'):env.pop(key,None)
    # The final note digest is created only after Main admission. Its path and
    # fixed-width digest slot are nevertheless size-checked before mutation.
    placeholder_env=dict(env,S1_OWNED_ROOT_NOTE=str(RUN/('launch-note-049-'+suffix+'.json')),
        S1_OWNED_ROOT_SHA256='0'*64,S1_JOB_LEDGER=job_ledger['path'])
    exec_preflight=_prepare_owned_candidate(os.execve,(command[0],command,placeholder_env),{})
    boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    def process(pid, *, ancestor_root=None):
        def row():
            fields=Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split()
            return dict(boot_id=boot,pid=pid,ppid=int(fields[1]),pgid=int(fields[2]),start_ticks=int(fields[19]))
        def tasks():
            result=[]
            for path in sorted(Path('/proc',str(pid),'task').iterdir(),key=lambda value:int(value.name)):
                fields=(path/'stat').read_text().rsplit(')',1)[1].split()
                result.append(dict(boot_id=boot,pid=pid,process_start_ticks=first['start_ticks'],tid=int(path.name),start_ticks=int(fields[19])))
            return result
        first=row();threads=tasks();again=tasks();last=row()
        if first!=last:
            error=ValueError('unstable driver identity')
            try:error.add_note(identity_difference(process.stage,'process_before_after',dict(process_before_after=first),dict(process_before_after=last),not_sampled=('threads_before_after',)))
            except BaseException:
                try:error.add_note('plan049-identity-diff/v1 diagnostic-unavailable')
                except BaseException:pass
            raise error
        if ancestor_root is None and threads!=again:
            error=ValueError('unstable driver identity')
            try:error.add_note(identity_difference(process.stage,'threads_before_after',dict(threads_before_after=threads),dict(threads_before_after=again)))
            except BaseException:
                try:error.add_note('plan049-identity-diff/v1 diagnostic-unavailable')
                except BaseException:pass
            raise error
        if not threads:
            error=ValueError('unstable driver identity')
            try:error.add_note(identity_difference(process.stage,'threads_nonempty',None,None,invariant='threads_nonempty'))
            except BaseException:
                try:error.add_note('plan049-identity-diff/v1 diagnostic-unavailable')
                except BaseException:pass
            raise error
        value=dict(first,threads=threads,threads_before=[dict(task) for task in threads],threads_after=again,process_before=first,process_after=last)
        if ancestor_root is None:return identity_record(value)
        if pid==ancestor_root['pid']:raise ValueError('ancestor role cannot contain root')
        return _identity_record(value,ancestor=True)
    def local_identity(stage='initial'):
        # Stage metadata only; process calls/samples and predicates stay exact.
        process.stage=stage
        root=process(os.getpid());ancestors=[];cursor=root['ppid'];seen={root['pid']}
        while cursor:
            if cursor in seen:raise ValueError('ancestry cycle')
            seen.add(cursor);row=process(cursor,ancestor_root=root);ancestors.append(row);cursor=row['ppid']
        if not ancestors:raise ValueError('terminated ancestry required')
        observed_root=process(os.getpid())
        if observed_root!=root:
            error=ValueError('unstable full driver ancestry')
            try:error.add_note(identity_difference(stage,'local_root_stability',dict(ownership_root=root),dict(ownership_root=observed_root),not_sampled=('preexisting_ancestors',)))
            except BaseException:
                try:error.add_note('plan049-identity-diff/v1 diagnostic-unavailable')
                except BaseException:pass
            raise error
        observed_ancestors=[process(row['pid'],ancestor_root=root) for row in ancestors]
        expected_projection=identity_projection(root,ancestors)
        # Every sampled row was typed by process(); compare the recorded PID
        # sequence before any chain error can obscure changed process paths.
        observed_projection=dict(ownership_root=root,preexisting_ancestors=[
            {key:value for key,value in row.items() if key not in ('threads','threads_before','threads_after')}
            for row in observed_ancestors])
        if observed_projection!=expected_projection:
            error=ValueError('unstable full driver ancestry')
            try:error.add_note(identity_difference(stage,'local_ancestry_stability',expected_projection,observed_projection))
            except BaseException:
                try:error.add_note('plan049-identity-diff/v1 diagnostic-unavailable')
                except BaseException:pass
            raise error
        return root,ancestors
    root,ancestors=local_identity()
    observed=census();owned={os.getpid()}
    for _ in range(len(observed)):
        additions={pid for pid,row in observed.items() if row['ppid'] in owned}-owned
        if not additions:break
        owned.update(additions)
    if owned!={os.getpid()}:raise ValueError('pre-mutation driver already has an unaccounted child')
    owned_charge(0,1)  # The exact returned Main exec session is the sole live H.
    # All source/authority/output/high-water and live process identity reads
    # above are complete. Create the exclusive ledger as the first mutation.
    job_ledger=initialize_job_ledger(kind,index,prepared_ledger)
    digit_limit=sys.get_int_max_str_digits()
    try:
        if digit_limit and digit_limit<20000:sys.set_int_max_str_digits(20000)
        start_hash=hashlib.sha256(json.dumps(start_event,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    finally:
        if digit_limit and digit_limit<20000:sys.set_int_max_str_digits(digit_limit)
    append_job_event('main-handle',dict(session_id=start_frame['session_id'],start_event_sha256=start_hash),job_ledger['path'])
    prefix=RUN/('driver-049-'+suffix)
    outputs=[str(directory/name) for name in ('receipt.json','execution.json','process-stdout.log','process-stderr.log','stdout.log','stderr.log','stdin.py','runner.py','capture.py')]+[str(prefix)+ending for ending in ('-exec-start.json','-stdout.log','-stderr.log')]
    identity_request_path=RUN/('launch-identity-049-'+suffix+'.json')
    identity_binding=dict(ownership_root=root,preexisting_ancestors=ancestors,ancestry_terminal=dict(pid=ancestors[-1]['pid'],ppid=0),retained_wrappers=[],output_paths=outputs)
    identity_request=publish(identity_request_path,dict(schema='plan049-prospective-identity/v1',kind=kind,index=index,driver=record(Path(__file__)),**identity_binding))
    print(json.dumps(dict(awaiting_main_admission=str(admission_path),identity_request=identity_request)),flush=True)
    if sys.stdin.readline()!='ADMIT\n':raise ValueError('explicit Main admission handoff required')
    admission=session_json(admission_path)
    if type(admission) is not dict:raise ValueError('Main admission dictionary')
    if any(admission.get(k)!=v for k,v in dict(kind=kind,index=index,reason=reason,counts_before=counts,execution_mode='no-timeout',timeout_seconds=None,cpu_bound='B+max(1,H)≤8').items()):raise ValueError('main admission correlation')
    if admission.get('approved') is not True or admission.get('cleanup_resolved') is not True:raise ValueError('main cleanup/approval prerequisite')
    if 'timeout_seconds' not in admission:raise ValueError('explicit null timeout required')
    capacity=admission.get('resource_capacity',{})
    B=capacity.get('B');H=capacity.get('H')
    if type(B) is not int or type(H) is not int or min(B,H)<0 or B+max(1,H)>8 or type(capacity.get('charge')) is not int or capacity['charge']!=B+max(1,H):raise ValueError('main resource capacity proof')
    if type(capacity.get('artifact_bytes')) is not int or not 0<=capacity['artifact_bytes']<=150*1024**3:raise ValueError('artifact cap proof')
    if [r['path'] for r in sources]!=admission['source_paths'] or sources!=admission['sources']:raise ValueError('main source snapshot changed')
    addenda=[record(RUN/name) for name in ('plan049-correction-001.md','plan049-correction-002.md','plan049-correction-003.md','plan049-correction-004.md','plan049-correction-005.md','plan049-correction-006.md','plan049-correction-007.md','plan049-correction-008.md','plan049-correction-009.md','plan049-correction-010.md','plan049-correction-011.md','plan049-correction-012.md','plan049-correction-013.md','plan049-correction-014.md','plan049-correction-015.md','plan049-correction-015-source-scope-addendum-001.md','plan049-correction-015-source-scope-addendum-002.md','plan049-correction-015-source-scope-addendum-003.md','plan049-correction-015-source-scope-addendum-006.md')]
    ancestor_authorization=record(RUN/'authorization-049-ancestor-process-001.md')
    if ancestor_authorization['sha256']!='734fc8fc67f2cc7f60ead6eba279b797abff47bbf32602cf5106e07ef540605d':raise ValueError('fixed ancestor authorization bytes')
    plan054=record(ROOT/'plans/plan_054.md')
    evidence_amendment=record(ROOT/'docs/resolve-blocker/plan031-session-proof-wrapper-20260923/correction-008-trust-amendment-001-proposal.md')
    if plan054['sha256']!='91d0ac7191d944b8cf2175b74c74aff3d70d4dba4a530431f223cb8aab2df62d' or evidence_amendment['sha256']!='9a27dbb60afcf358409364987e0b74d219431e4b5a83652ac9c607f658426d84':raise ValueError('adopted exact v2 trust authority')
    proof_record=record(RUN/('main-session-proof-049-'+suffix+'.json'))
    proof=session_proof(proof_record,kind,index,record(Path(__file__)),identity_request,str(admission_path),reason)
    if proof['session_id']!=start_frame['session_id'] or session_json(proof['tool_events'][0]['path'])!=start_event:raise ValueError('Main start frame differs from durable same-handle proof')
    expected=dict(session_proof=proof_record,plan054=plan054,evidence_amendment=evidence_amendment,plan=plan,dispatch=record(dispatch_path),status=status,authorization=authorization,ancestor_authorization=ancestor_authorization,driver=record(Path(__file__)),command=command,environment=settings,stdin=dict(bytes=len(stdin),sha256=hashlib.sha256(stdin).hexdigest()),run_directory=str(directory),identity_request=identity_request,addenda=addenda,job_ledger=job_ledger,**identity_binding)
    if json.dumps(admission.get('bindings'),sort_keys=True,allow_nan=False)!=json.dumps(expected,sort_keys=True,allow_nan=False):raise ValueError('main immutable typed command/authority/identity binding')
    if (observed_projection:=identity_projection(*local_identity('before_note')))!=(expected_projection:=identity_projection(root,ancestors)):
        error=ValueError('Main prospective identity changed')
        try:error.add_note(identity_difference('before_note','prospective_identity',expected_projection,observed_projection))
        except BaseException:
            try:error.add_note('plan049-identity-diff/v1 diagnostic-unavailable')
            except BaseException:pass
        raise error
    if capacity['B']!=0 or capacity['H']!=1:raise ValueError('Main live outer session capacity mismatch')
    bindings=[plan,record(dispatch_path),status,authorization,ancestor_authorization,record(admission_path),identity_request,proof_record,proof['user_authorization'],plan054,evidence_amendment]+proof['tool_events']+addenda
    note=dict(schema='plan049-prospective-launch/v1',execution_mode='no-timeout',timeout_seconds=None,driver=record(Path(__file__)),admission=record(admission_path),bindings=bindings,sources=sources,status={k:status[k] for k in ('bytes','sha256')},kind=kind,attempt_index=index,counts_before=counts,counts_after=dict(counts,**{kind:counts[kind]+1}),reason=reason,command=command,cwd=str(ROOT),run_directory=str(directory),environment=settings,unset_environment=['S1_HELPER_DIAGNOSTIC','S1_RECEIPT_DIAGNOSTIC'],stdin_identity=dict(bytes=len(stdin),sha256=hashlib.sha256(stdin).hexdigest(),content=stdin.decode()),ownership_root=root,preexisting_ancestors=ancestors,ancestry_terminal=dict(pid=ancestors[-1]['pid'],ppid=0),retained_wrappers=[],output_paths=outputs,job_ledger=job_ledger,observed=stamp(),cpu_bound='B+max(1,H)≤8',existing_scenarios=42,direct_scripts=6,scenario_execution_seconds=2,scenario_cleanup_seconds=1)
    note_record=publish(RUN/('launch-note-049-'+suffix+'.json'),note)
    no_timeout_launch(note_record,str(directory),diagnostic=kind=='diagnostic')
    env['S1_OWNED_ROOT_NOTE']=note_record['path'];env['S1_OWNED_ROOT_SHA256']=note_record['sha256']
    env['S1_JOB_LEDGER']=job_ledger['path']
    exec_candidate=_prepare_owned_candidate(os.execve,(command[0],command,env),{})
    preflight_descriptor=json.loads(exec_preflight[0]);actual_descriptor=json.loads(exec_candidate[0])
    preflight_environment=preflight_descriptor['environment'];actual_environment=actual_descriptor['environment']
    if ({key:value for key,value in preflight_descriptor.items() if key!='environment'}!={key:value for key,value in actual_descriptor.items() if key!='environment'}
            or {key:value for key,value in preflight_environment.items() if key!='sha256'}!={key:value for key,value in actual_environment.items() if key!='sha256'}):
        raise ValueError('driver exec candidate differs from pre-mutation size preflight')
    with Path(str(prefix)+'-stdout.log').open('xb') as out,Path(str(prefix)+'-stderr.log').open('xb') as err:
        logs={}
        for number,stream in [(1,out),(2,err)]:
            stream.flush();os.fsync(stream.fileno());info=os.fstat(stream.fileno());logs[str(number)]=dict(device=info.st_dev,inode=info.st_ino)
        # Fresh bytes, not age, determine admission immediately before exec.
        for item in bindings+sources+[note['driver'],note_record]:
            if record(Path(item['path']))!=item:raise ValueError('authority/source changed before exec')
        if (observed_projection:=identity_projection(*local_identity('before_exec_record')))!=(expected_projection:=identity_projection(root,ancestors)):
            error=ValueError('driver identity changed')
            try:error.add_note(identity_difference('before_exec_record','prospective_identity',expected_projection,observed_projection))
            except BaseException:
                try:error.add_note('plan049-identity-diff/v1 diagnostic-unavailable')
                except BaseException:pass
            raise error
        publish(Path(str(prefix)+'-exec-start.json'),dict(schema='plan049-exec-launch/v1',execution_mode='no-timeout',timeout_seconds=None,note=note_record,before_launch=stamp(),logs=logs,command=command,process_candidate=dict(descriptor=exec_candidate[0].decode('ascii'),sha256=hashlib.sha256(exec_candidate[0]).hexdigest()),replacement='driver execve unchanged child capture'))
        os.dup2(out.fileno(),1);os.dup2(err.fileno(),2)
    if (observed_projection:=identity_projection(*local_identity('immediate_pre_exec')))!=(expected_projection:=identity_projection(root,ancestors)):
        error=ValueError('driver full identity changed immediately before exec')
        try:error.add_note(identity_difference('immediate_pre_exec','prospective_identity',expected_projection,observed_projection))
        except BaseException:
            try:error.add_note('plan049-identity-diff/v1 diagnostic-unavailable')
            except BaseException:pass
        raise error
    checked_exec_candidate=_prepare_owned_candidate(os.execve,exec_candidate[2],exec_candidate[3])
    if checked_exec_candidate[0]!=exec_candidate[0] or checked_exec_candidate[1]!=exec_candidate[1]:raise ValueError('driver exec candidate changed before execve')
    os.execve(*checked_exec_candidate[2])
if __name__=='__main__':main()
