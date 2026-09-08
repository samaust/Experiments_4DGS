"""Plan 016 durable focused benchmark with an external process-group watchdog."""
import os
for name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:os.environ[name]='1'
import argparse
from pathlib import Path
import signal
import subprocess
import sys
import time
from basketball_shared_storage_v10 import read,publish,sha,journal_prefix,PersistenceError
from basketball_shared_verify_v10 import exact_hashes,inspect_attempt,verify_schedule

ROOT=Path('docs/experiments/basketball-shared-timing-v10')
CONFIG=Path('configs/basketball-rev2/timing-shared-v10.json')
STAGES=['prepare','persist','baseline','adapt','benchmark','package','verify']

def deadline(p,stage):return p['v10']['absolute_deadlines'][stage]
def check(p,stage):
    if time.time()>=deadline(p,stage):raise TimeoutError('absolute '+stage+' deadline')

def terminate_group(child):
    try:os.killpg(child.pid,signal.SIGTERM)
    except ProcessLookupError:pass
    # Even when the leader exits immediately, give descendants the full grace.
    end=time.monotonic()+2
    while time.monotonic()<end:time.sleep(min(.05,end-time.monotonic()))
    try:os.killpg(child.pid,signal.SIGKILL)
    except ProcessLookupError:pass
    child.wait()

def freeze_execution():
    from basketball_shared_recovery_v8 import implementation
    files=list(Path('scripts').glob('basketball*.py'))
    hashes={str(f):sha(f) for f in files}
    hashes.update(implementation())
    hashes[str(CONFIG)]=sha(CONFIG)
    publish(ROOT/'prepare/execution-sources.json',hashes)
    return hashes

def policy_file(output,policy):
    policy=dict(policy,manifest=str(ROOT/'prepare/benchmark-manifest.json'),execution_index=str(ROOT/'prepare/execution-sources.json'))
    publish(output/'policy.json',policy)
    return output/'policy.json'

def failure_path(stage):return ROOT/('adapt' if stage in ['metric','initialization','stopping'] else stage)/'failure.json'

def launch_worker(output,policy,task,stage,p):
    task_file=output/(task['id']+'.json');publish(task_file,task)
    log=(output/(task['id']+'.log')).open('wb')
    process=subprocess.Popen([sys.executable,'scripts/basketball_shared_worker_v10.py',str(output),str(policy),str(task_file),str(deadline(p,stage)),str(failure_path(stage))],stdout=log,stderr=subprocess.STDOUT)
    log.close();return process

def load_records(output):
    records=[]
    for f in sorted(output.glob('*-summary.json')):
        summary=read(f)
        for ref in summary['attempts']:
            assert sha(ref['artifact'])==ref['sha256'] and sha(ref['receipt'])==ref['receipt_sha256']
            directory=Path(ref['artifact']).parent;proof=inspect_attempt(directory)
            assert proof['completed']
            item=read(ref['artifact']);item['verification']=proof['verification']['physical'];item['artifact']=ref;records.append(item)
    return records

def run_policy(p,output,policy,stage):
    from basketball_shared_benchmark_v9 import jobs
    check(p,stage);output.mkdir();file=policy_file(output,policy);manifest=read(ROOT/'prepare/benchmark-manifest.json');tasks=jobs(manifest)
    publish(output/'scheduled.json',dict(attempts=81,task_ids=[t['id'] for t in tasks],policy_sha256=sha(file)))
    active=[];pending=list(tasks);outcomes=[];started=time.monotonic()
    while pending or active:
        check(p,stage)
        failure=failure_path(stage)
        if failure.exists():raise PersistenceError('worker signaled failure '+str(failure))
        # Inspect all completed workers before dispatching any successor.
        for proc,task in list(active):
            code=proc.poll()
            if code is None:continue
            active.remove((proc,task));outcomes.append(dict(task=task['id'],exit_code=code))
            if code!=0:
                if not failure.exists():publish(failure,dict(error='worker exited without valid result',task=task['id'],exit_code=code))
                raise PersistenceError('worker failure; dispatch stopped')
            if not (output/(task['id']+'-summary.json')).exists():raise PersistenceError('worker omitted summary')
        while pending and len(active)<6:
            if failure.exists():raise PersistenceError('dispatch cancelled')
            task=pending.pop(0);active.append((launch_worker(output,file,task,stage,p),task))
        time.sleep(.05)
    publish(output/'worker-outcomes.json',outcomes)
    records=load_records(output);assert len(records)==81 and len({r['id'] for r in records})==81
    verify_schedule(records,manifest)
    count=dict(scheduled=81,persisted_outcomes=81,executed=sum(r['row']['executed'] for r in records),solver_invocations=sum(r['row']['solver_invoked'] for r in records),qualified=sum(r['row']['valid'] for r in records),missing=sum(not r['row']['executed'] for r in records),numerical_entries=sum(len(r['row'].get('accounting',{}).get('observed_numerical_entries',[])) for r in records),wall_seconds=time.monotonic()-started)
    publish(output/'counts.json',count);check(p,stage)
    return records,count

def persist(p):
    from basketball_shared_verify_v10 import verify_item
    from basketball_shared_storage_v10 import recover_attempt
    check(p,'persist');out=ROOT/'persist';manifest=read(ROOT/'prepare/benchmark-manifest.json');byid={t['id']:t for t in manifest['targets']}
    if not (ROOT/'prepare/execution-sources.json').exists():freeze_execution()
    policy=read(ROOT/'prepare/policies.json')['policies'][0];policy['name']='preflight'
    file=policy_file(out,policy)
    task=dict(id='preflight-four',kind='conditional',preflight=[byid[i] for i in ['conditional-03','conditional-02','conditional-00','conditional-04']])
    proc=launch_worker(out,file,task,'persist',p)
    while proc.poll() is None:check(p,'persist');time.sleep(.05)
    if proc.returncode:raise PersistenceError('actual worker preflight failed')
    records=load_records(out);assert len(records)==4
    byident={r['id']:r for r in records}
    expected={'conditional-03/cold':True,'conditional-02/cold':True,'conditional-00/cold':False,'conditional-04/cold':False}
    for ident,value in expected.items():assert byident[ident]['row']['valid']==value,('unexpected frozen preflight outcome',ident)
    assert byident['conditional-00/cold']['row']['solver_invoked']
    assert byident['conditional-04/cold']['row']['error']=='no feasible deterministic initialization'
    publish(out/'four-case-decision.json',dict(passed=True,outcomes=[dict(id=r['id'],valid=r['row']['valid'],solver_invoked=r['row']['solver_invoked'],artifact=r['artifact']) for r in records]))
    task=dict(id='preflight-interruption',kind='conditional',preflight=[byid['conditional-03'],byid['conditional-00']])
    proc=launch_worker(out,file,task,'persist',p);second=out/'preflight-interruption-1/cold';entered=False
    while proc.poll() is None:
        check(p,'persist');events=journal_prefix(second/'journal.jsonl')['events']
        if any(e['event']=='numerical_entry' for e in events):
            proc.kill();proc.wait();entered=True;break
        time.sleep(.002)
    assert entered,'worker did not reach interrupt boundary'
    first=inspect_attempt(out/'preflight-interruption-0/cold');incomplete=inspect_attempt(second)
    assert first['completed'] and first['qualified'] and not incomplete['completed'] and incomplete['numerical_entries'] is None
    publish(out/'interruption-decision.json',dict(passed=True,signal='SIGKILL after observing synchronized actual numerical-entry start',worker_exit_code=proc.returncode,completed_attempt=first,interrupted_attempt=incomplete,automatic_resume=False))
    # Storage tests run no optimization; the four plus two allocations are exhausted.
    log=out/'persistence-tests.log'
    with log.open('wb') as stream:
        code=subprocess.call([sys.executable,'-m','unittest','discover','-s','tests','-p','test_basketball_shared_v10.py','-v'],stdout=stream,stderr=subprocess.STDOUT)
    if code:raise PersistenceError('persistence fault regressions failed')
    check(p,'persist')
    return dict(status='passed',preflight_allocations=6,actual_worker_cases=4,completed_outcomes=5,interrupted=1,scientific_attempts=0)

def baseline(p):
    from basketball_shared_benchmark_v9 import iteration_ids
    records,count=run_policy(p,ROOT/'baseline/policy',read(ROOT/'prepare/policies.json')['policies'][0],'baseline')
    byid={r['id']:r for r in records};denom={i:byid[i]['verification']['KKT'] for i in iteration_ids(read(ROOT/'prepare/benchmark-manifest.json'))}
    publish(ROOT/'baseline/denominators.json',dict(frozen_unix=time.time(),values=denom,positive_verified=all(v is not None and v>0 for v in denom.values()),source_counts=count,baseline_v9_usable=False))
    return dict(status='passed',counts=count)

def preservation(records,controls):
    from basketball_shared_solver_v3 import objective_agreement
    byid={r['id']:r for r in records};failed=[]
    for ident,old in controls.items():
        row=byid[ident]['row']
        if not row['valid'] or row.get('objective') is None or not objective_agreement(row['objective'],old['objective']):failed.append(ident)
    return dict(passed=not failed,required=len(controls),failed=failed)

def adapt(p):
    import basketball_shared_benchmark_v9 as inherited
    manifest=read(ROOT/'prepare/benchmark-manifest.json');controls=read(ROOT/'prepare/controls.json');denom=read(ROOT/'baseline/denominators.json');base=load_records(ROOT/'baseline/policy');decisions=[]
    for policy in read(ROOT/'prepare/policies.json')['policies'][1:]:
        name=policy['name'];check(p,name)
        if name=='metric' and not denom['positive_verified']:
            decision=dict(policy=name,status='unassessed',passed=False,reason='missing positive independently verified baseline KKT denominators')
        else:
            records,counts=run_policy(p,ROOT/'adapt'/name,policy,name)
            decision=inherited.arm_decision(policy,records,manifest,controls,base,denom['values'])
            decision['preservation']=preservation(records,controls);decision['passed'] &= decision['preservation']['passed']
            decision['status']='passed' if decision['passed'] else 'rejected';decision['counts']=counts
            decision['support_changes']=[dict(id=r['id'],replaced_blocks=r['row'].get('initialization_transfer',{}).get('replaced_blocks',[])) for r in records if r['row'].get('initialization_transfer',{}).get('replaced_blocks')]
            decision['missing_dependencies']=[r['id'] for r in records if not r['row']['executed']]
        publish(ROOT/'adapt'/(name+'-decision.json'),decision);decisions.append(decision);check(p,name)
    selected=[d['policy'] for d in decisions if d['passed']]
    final=dict(name='final',conditioned_conditional='metric' in selected,repair='initialization' in selected,disable_xtol='stopping' in selected,selected_arms=selected,frozen_unix=time.time(),standalone_decisions_sha256={str(ROOT/'adapt'/(d['policy']+'-decision.json')):sha(ROOT/'adapt'/(d['policy']+'-decision.json')) for d in decisions})
    publish(ROOT/'adapt/final-policy.json',final);check(p,'adapt')
    return dict(status='passed',selected_arms=selected,final_benchmark='authorized' if selected else 'unassessed',decisions=decisions)

def benchmark(p):
    from basketball_shared_solver_v3 import objective_agreement
    policy=read(ROOT/'adapt/final-policy.json')
    if not policy['selected_arms']:return dict(status='unassessed',reason='no standalone arm passed')
    records,count=run_policy(p,ROOT/'benchmark/policy',policy,'benchmark');controls=read(ROOT/'prepare/controls.json');keep=preservation(records,controls);byid={r['id']:r for r in records};disagreements=[]
    for target in read(ROOT/'prepare/benchmark-manifest.json')['targets']:
        costs=[byid[target['id']+'/'+path]['row'].get('objective') for path in ['cold','ascending','descending']]
        if any(c is None for c in costs) or not all(objective_agreement(costs[0],c) for c in costs[1:]):disagreements.append(target['id'])
    passed=count['qualified']==81 and count['missing']==0 and keep['passed'] and not disagreements
    result=dict(status='passed' if passed else 'rejected',terminal_kind=None if passed else 'scientific_rejection',ready_for_full_screens=passed,counts=count,preservation=keep,path_disagreements=disagreements,failed_attempts=[r['id'] for r in records if not r['row']['valid']],candidate_sha256=sha(ROOT/'benchmark/policy/policy.json') if passed else None)
    publish(ROOT/'benchmark/decision.json',result)
    return result

def package(p):
    check(p,'package');stages={}
    for stage in STAGES[:-2]:
        f=ROOT/stage/'result.json';stages[stage]=read(f) if f.exists() else dict(status='unassessed')
    attempts=[];errors=[]
    for f in sorted(ROOT.glob('**/journal.jsonl')):
        try:attempts.append(inspect_attempt(f.parent))
        except Exception as e:errors.append(dict(directory=str(f.parent),error=type(e).__name__+': '+str(e)))
    blocked=[s for s,r in stages.items() if r['status']=='blocked']
    ready=not errors and not blocked and stages['benchmark'].get('ready_for_full_screens',False)
    terminal='provenance_or_arithmetic_failure' if errors else next((stages[s].get('terminal_kind','computational_blocker') for s in blocked),None)
    if not ready and terminal is None:terminal='scientific_rejection' if stages['adapt'].get('selected_arms')==[] or stages['benchmark']['status']=='rejected' else 'unassessed'
    runtime=[];dependencies=[]
    for f in sorted(ROOT.glob('**/counts.json')):
        runtime.append(dict(policy=str(f.parent),counts=read(f),source_sha256=sha(f)))
    for a in attempts:
        if not a['completed']:continue
        artifact=Path(a['directory'])/'attempt.json.gz';item=read(artifact)
        dependencies.append(dict(id=item['id'],policy=item['row']['policy'],artifact=str(artifact),sha256=sha(artifact),seed=item['row'].get('seed')))
    publish(ROOT/'package/runtime-comparisons.json',dict(policies=runtime,preflight_separate=True,v9_baseline_comparison=None,reason='v9 baseline records unavailable',factor_two_margin=2))
    publish(ROOT/'package/dependency-index.json',dict(records=dependencies))
    if ready:
        final=read(ROOT/'benchmark/policy/counts.json');elapsed=final['wall_seconds'];factor=(144+12126+144)/81
        publish(ROOT/'package/continuation-proposal.json',dict(candidate_sha256=sha(ROOT/'benchmark/policy/policy.json'),focused_wall_seconds_including_persistence_and_verification=elapsed,proposed_full_screen_seconds=2*factor*elapsed+900,margin=2,full_screens_authorized=False,required_gates=['144 conditioning attempts preserve all 94; recover at least 25/50; median KKT ratio at most 0.1','Independent scalar grid: 7344 initial paths plus inclusive refinements; all paths and nine basin references pass','Fresh combined pilot only after both independent passes'],uncertainty='Focused measurement cannot bound full refinement workload; freeze a separate clock before launch'))
    publish(ROOT/'package/attempt-index.json',dict(attempts=attempts,errors=errors))
    result=dict(status='passed' if not errors else 'blocked',terminal_kind=terminal,scientific_status='ready_for_full_screens' if ready else terminal,ready_for_full_screens=ready,stage_statuses={s:r['status'] for s,r in stages.items()},completed_outcomes=sum(a['completed'] for a in attempts),incomplete_attempts=sum(not a['completed'] for a in attempts),qualified=sum(a['qualified'] is True for a in attempts),accepted_timing=None,production_candidate=None,final_validation_protocol=None,full_screens_launched=False)
    publish(ROOT/'package/terminal-decision.json',result)
    return result

def verify(p):
    from basketball_shared_verify_v5 import verify_partition
    import re
    check(p,'verify');admission=read(ROOT/'prepare/admission.json');exact_hashes(admission['committed_v9_sha256']);exact_hashes(read(ROOT/'prepare/execution-sources.json'))
    from basketball_shared_provenance_v9 import verify_hashes
    for k in ['source_sha256','installed_solver_sha256','markers']:verify_hashes(admission['inherited'][k])
    partition=verify_partition(p);attempts=[inspect_attempt(f.parent) for f in sorted(ROOT.glob('**/journal.jsonl'))]
    tests={}
    for name in ['basketball','budget','selfcap']:
        f=ROOT/(name+'-tests.log');s=f.read_text();assert re.search(r'\nOK\s*$',s),name
        tests[name]=dict(tests=int(re.search(r'Ran (\d+) tests?',s).group(1)),sha256=sha(f))
    schedules={}
    for folder in [ROOT/'baseline/policy',ROOT/'adapt/metric',ROOT/'adapt/initialization',ROOT/'adapt/stopping',ROOT/'benchmark/policy']:
        if (folder/'counts.json').exists():schedules[str(folder)]=verify_schedule(load_records(folder),read(ROOT/'prepare/benchmark-manifest.json'))
    for stage in STAGES[:-1]:
        f=ROOT/stage/'result.json'
        if f.exists():exact_hashes(read(f).get('artifacts_sha256',{}))
    terminal=read(ROOT/'package/terminal-decision.json')
    return dict(status='passed',scientific_status=terminal['scientific_status'],ready_for_full_screens=terminal['ready_for_full_screens'],attempts=attempts,schedules=schedules,tests=tests,partition=partition,accepted_timing=None,production_candidate=None,final_validation_protocol=None)

def finish(stage,p,result):
    result.update(stage=stage,schema='basketball-shared-timing-stage/v10',finished_unix=time.time(),elapsed_seconds=time.time()-p['investigation_started_unix'],config_sha256=sha(CONFIG),accepted_timing=None,production_candidate=None,final_validation_protocol=None)
    result['artifacts_sha256']={str(f):sha(f) for f in sorted((ROOT/stage).rglob('*')) if f.is_file() and f.name!='result.json'}
    publish(ROOT/stage/'result.json',result);print(stage,result['status'],result.get('terminal_kind'),flush=True)
    return int(result['status']=='blocked')

def scientific_stage(stage,p):
    if stage!='prepare' or not (ROOT/'prepare/admission.json').exists():check(p,stage)
    prior={'baseline':'persist','adapt':'baseline','benchmark':'adapt'}.get(stage)
    if prior and read(ROOT/prior/'result.json')['status']!='passed':raise PersistenceError('predecessor failed; numerical dispatch forbidden')
    if stage=='prepare':
        if not (ROOT/'prepare/admission.json').exists():
            from basketball_shared_admission_v10 import prepare
            prepare()
        return dict(status='passed',admission_sha256=sha(ROOT/'prepare/admission.json'))
    return globals()[stage](p)

def main(stage,worker=False):
    p=read(CONFIG);out=ROOT/stage
    if worker:
        try:result=scientific_stage(stage,p)
        except Exception as e:
            import traceback
            result=dict(status='blocked',terminal_kind='budget_exhaustion' if isinstance(e,TimeoutError) else 'computational_or_provenance_failure',error=type(e).__name__+': '+str(e),traceback=traceback.format_exc())
        return finish(stage,p,result)
    if (out/'result.json').exists():raise FileExistsError('stage already terminal; no numerical resume')
    out.mkdir(parents=True,exist_ok=True)
    remaining=deadline(p,stage)-time.time()
    if stage=='prepare' and (ROOT/'prepare/admission.json').exists():
        admitted=read(ROOT/'prepare/admission.json');assert admitted['frozen_unix']<deadline(p,'prepare')
        exact_hashes(admitted['committed_v9_sha256'])
        return finish(stage,p,dict(status='passed',admission_frozen_unix=admitted['frozen_unix'],admission_sha256=sha(ROOT/'prepare/admission.json')))
    if remaining<=0:return finish(stage,p,dict(status='blocked',terminal_kind='budget_exhaustion',error='absolute deadline before worker initialization'))
    child=subprocess.Popen([sys.executable,__file__,stage,'--worker'],start_new_session=True)
    failure=None
    try:
        while child.poll() is None:
            if (out/'failure.json').exists():failure='persistence worker failure';break
            if time.time()>=deadline(p,stage):failure='absolute watchdog deadline';break
            time.sleep(.05)
        if failure:
            terminate_group(child)
        elif child.returncode:
            terminate_group(child)
            failure='stage worker failed'
        if not (out/'result.json').exists():
            return finish(stage,p,dict(status='blocked',terminal_kind='budget_exhaustion' if failure=='absolute watchdog deadline' else 'computational_or_provenance_failure',error=failure or 'worker omitted result',worker_exit_code=child.returncode,artifact_available=any(out.iterdir())))
        return int(read(out/'result.json')['status']=='blocked')
    except BaseException:
        terminate_group(child);raise

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('stage',choices=STAGES);parser.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args();raise SystemExit(main(args.stage,args.worker))
