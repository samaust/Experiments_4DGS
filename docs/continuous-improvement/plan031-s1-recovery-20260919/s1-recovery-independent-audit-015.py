"""Read-only Plan045 evidence audit; imports no production or test modules."""
import ast
from collections import Counter
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
ROOT=Path(__file__).resolve().parents[3]
RUN=Path(__file__).resolve().parent
BASE='ebf9d9ad39c25b5732fadefcdc36cb71e0bde613'
SUITES=('s1_semantics','s1_recovery','backends','contracts','component_recovery','execution','budgets','supervisor','review_annotations')
checks=[]
def check(name,passed):checks.append(dict(check=name,passed=bool(passed)))
def rec(path):
    path=Path(path).absolute()
    if 'prompts' in path.parts:raise ValueError('forbidden path')
    raw=path.read_bytes();return dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def read(path):return json.loads(Path(path).read_text())
def bound(value):
    check('exact record '+value['path'],rec(value['path'])=={k:value[k] for k in ('path','sha256','bytes')})
    return Path(value['path'])
def save(path,value):
    raw=(json.dumps(value,indent=2,allow_nan=False)+'\n').encode()
    with Path(path).open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
    assert Path(path).read_bytes()==raw
    return rec(path)
def typed(v):return json.dumps([[k,type(x).__name__,x] for k,x in sorted(v.items())],separators=(',',':'),allow_nan=False)
def extract(text,module):
    tree=ast.parse(text);methods=[];declarations={};assertions={}
    for node in tree.body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SUBTEST_CASES' for t in node.targets):declarations=ast.literal_eval(node.value)
    for cls in sorted((n for n in tree.body if isinstance(n,ast.ClassDef)),key=lambda n:n.name):
        for fn in sorted((n for n in cls.body if isinstance(n,ast.FunctionDef)),key=lambda n:n.name):
            name=module+'.'+cls.name+'.'+fn.name
            if fn.name.startswith('test_'):methods.append(name)
            assertions[name]=Counter(ast.dump(n,include_attributes=False) for n in ast.walk(fn) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr.startswith('assert'))
    return methods,declarations,assertions

def main():
    check('fresh exact implementation HEAD',subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==BASE)
    old_receipt=read(RUN/'s1-recovery-aggregate-014-002/receipt.json')
    methods=[];old_methods=[];cases={};old_cases={};assertion_map=[]
    for suite in SUITES:
        module='test_vipe_benchmark_'+suite;relative='tests/'+module+'.py'
        old=extract(subprocess.check_output(['git','show',BASE+':'+relative],cwd=ROOT,text=True),module)
        new=extract((ROOT/relative).read_text(),module)
        old_methods.extend(old[0]);methods.extend(new[0]);old_cases.update(old[1]);cases.update(new[1])
        for name,values in old[1].items():check('exact prior typed callback '+name,[typed(v) for v in values]==[typed(v) for v in new[1].get(name,[])])
        for name,assertions in old[2].items():
            missing=assertions-new[2].get(name,Counter());check('substantive assertions '+name,not missing)
            assertion_map.append(dict(method=name,baseline_assertions=sum(assertions.values()),missing=list(missing)))
    check('all221 exact ordered old methods',len(old_methods)==221 and old_methods==old_receipt['collected'] and [m for m in methods if m in old_methods]==old_methods)
    check('all426 old callbacks preserved',sum(map(len,old_cases.values()))==426 and {k:[typed(v) for v in values] for k,values in old_cases.items()}=={k:[typed(v) for v in values] for k,values in old_receipt['declarations'].items()})
    check('all840 old class-method substantive calls preserved',sum(v['baseline_assertions'] for v in assertion_map)==840)
    check('230 current methods and466 declarations',len(methods)==230 and sum(map(len,cases.values()))==466)
    baseline=read(RUN/'s1-recovery-validation-013.json');old_sources={v['path']:v for v in baseline['sources']}
    paths=sorted([ROOT/'scripts/basketball_vipe_benchmark.py',ROOT/'scripts/basketball_vipe_worker.py',ROOT/'configs/vipe-alternatives/benchmark-v1.json',*(ROOT/'scripts/vipe_benchmark').glob('*.py'),*(ROOT/'tests').glob('test_vipe_benchmark_*.py')])
    sources=[rec(p) for p in paths];new_paths={v['path'] for v in sources}
    check('77 prior source members plus new progress module',len(sources)==78 and set(old_sources)<=new_paths and new_paths-set(old_sources)=={str(ROOT/'scripts/vipe_benchmark/s1_progress.py')})
    changed=[v['path'] for v in sources if v!=old_sources.get(v['path'])]
    allowed={str(ROOT/p) for p in ['scripts/vipe_benchmark/s1_progress.py','scripts/vipe_benchmark/s1_evidence.py','scripts/vipe_benchmark/stages.py','scripts/vipe_benchmark/s1_recovery.py','scripts/vipe_benchmark/s1_cpu_helper.py','scripts/vipe_benchmark/s1_helper_session.py','scripts/vipe_benchmark/supervisor.py','tests/test_vipe_benchmark_supervisor.py','tests/test_vipe_benchmark_s1_helper_fixtures.py','tests/test_vipe_benchmark_s1_recovery.py']}
    check('source changes within plan scope',set(changed)<=allowed)
    for p in ['scripts/vipe_benchmark/s1_validation_capture.py','scripts/vipe_benchmark/s1_validation_runner.py','scripts/vipe_benchmark/s1_validation_contract.py','scripts/vipe_benchmark/backends.py','configs/vipe-alternatives/benchmark-v1.json','scripts/basketball_vipe_worker.py']:
        check('unchanged protected '+p,rec(ROOT/p)==old_sources[str(ROOT/p)])
    correction=read(RUN/'s1-recovery-baseline-correction-013.json');previous=read(bound(correction['predecessor']));dispatch=read(RUN/'implementation-dispatch-015.json')
    check('complete predecessor correction prefix',correction['bookkeeping_transitions'][:len(previous['bookkeeping_transitions'])]==previous['bookkeeping_transitions'])
    check('all canonical dispatch transitions appended',correction['bookkeeping_transitions'][len(previous['bookkeeping_transitions']):]==dispatch['required_transitions'])
    current=correction['bookkeeping_baseline']
    for ref in correction['bookkeeping_transitions']:
        value=read(bound(ref));check('status chain '+ref['path'],value['old']==current);current=value['new']
    for ref in dispatch['required_transitions']:
        value=read(ref['path'])
        for side in ['old','new']:
            snap=rec(bound(value[side+'_snapshot']));check('durable actual '+side+ref['path'],all(snap[k]==value[side][k] for k in ('sha256','bytes')))
    check('actual frozen IMPLEMENT015 status',current==rec(RUN/'status.md')==dispatch['status']==correction['bookkeeping_observed'])
    for value in correction['frozen_records']:bound(value)
    check('all38 frozen records',len(correction['frozen_records'])==38)
    ledger_path=bound(correction['ledger_snapshot']);raw=ledger_path.read_bytes();events=[json.loads(line) for line in raw.splitlines()];last=None
    for index,event in enumerate(events):
        payload={k:v for k,v in event.items() if k!='event_sha256'};digest=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
        check('ledger chain '+str(index),event['sequence']==index and event['previous_sha256']==last and event['event_sha256']==digest);last=digest
    active={}
    for event in events:
        if event['event']=='reserve':active[event['job_id']]=event
        elif event['event'] in ('finish','checkpoint'):active.pop(event.get('job_id'),None)
    gpu=[v for v in events if v.get('resource')=='gpu'];gpu_attempts=sum(v['event']=='reserve' for v in gpu);gpu_elapsed=sum(v.get('elapsed_seconds',0) for v in gpu if v['event']=='finish')
    check('original ledger447332437 head and accounting',len(events)==447 and len(raw)==332437 and last=='00cab019d73b6a3205f676b54cfb2f745f492fa5cca5c69b4567087cea62172b' and gpu_attempts==30 and gpu_elapsed==4374.044265462899 and not active)
    check('no recovery ledger events',not any(v.get('job_id')=='S1-calibration-recovery-001' for v in events))
    check('exact original failure events250255256',[events[i] for i in (250,255,256)]==read(RUN/'s1-recovery-ledger-audit-013.json')['preserved_events'])
    consumed=[];scenario_results=[];all_censuses=[];periods=[]
    current_match=[]
    for index in (1,2,3):
        directory=RUN/f's1-recovery-diagnostic-015-{index:03d}';note=read(RUN/f's1-recovery-launch-note-015-diagnostic-{index:03d}.json')
        prefix=RUN/f's1-recovery-driver-015-diagnostic-{index:03d}'
        launch=read(str(prefix)+'-exec-start.json');toolstart=read(str(prefix)+'-tool-start.json');completion=read(str(prefix)+'-tool-completion.json')
        inner=read(directory/'receipt.json');outer=read(directory/'execution.json')
        check('durable prospective first/all note '+str(index),launch['note']==rec(RUN/f's1-recovery-launch-note-015-diagnostic-{index:03d}.json') and note['observed']['monotonic']<=launch['before_launch']['monotonic']<=outer['start']['monotonic'])
        check('fresh full timeout and evidence reserve fit '+str(index),outer['start']['monotonic']-note['stage_start']['monotonic']+120+300<3300)
        check('all native env limits from first launch '+str(index),all(note['environment'][key]=='1' for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','OPENCV_FOR_THREADS_NUM','VIPE_CPU_VALIDATION')))
        check('actual outer tool completion '+str(index),type(toolstart['session_id']) is int and completion['exit_code']==outer['returncode']==1)
        check('actual capture terminal wait '+str(index),outer['wait_completed'] and not outer['timed_out'] and outer['timeout_seconds']==120 and outer['elapsed_seconds']<=120)
        check('stable paired source snapshots '+str(index),note['sources']==outer['sources_before']==outer['sources_after']==inner['sources_before']==inner['sources_after'])
        for key in ('stdout','stderr','stdin','runner','interpreter'):
            bound(inner[key]);bound(outer[key]);check('paired '+key+str(index),inner[key]==outer[key])
        bound(outer['capture']);bound(outer['receipt'])
        for case in inner['cases']:
            expected=inner['declarations'].get(case['id'],[])
            # The first pure metadata method failed before entering its table.
            actual=[typed(v['parameters']) for v in case['subtests']]
            check('callback prefix '+str(index)+case['id'],actual==[typed(v) for v in expected][:len(actual)])
        records=[]
        for path in sorted(directory.glob('scenario-*.json')):
            value=read(path);records.append(value)
            check('bounded retired scenario '+str(index)+value['scenario'],value['cleanup_confirmed'] is True and value['ownership']==[] and value['execution_seconds']<=2 and value['cleanup_seconds']<=1 and value['end']<=value['safety_cutoff'])
            check('original scenario cutoffs '+str(index)+value['scenario'],value['action_cutoff']==value['constructor_entry']+2 and value['safety_cutoff']==value['constructor_entry']+3)
            for event in value.get('events',[]):
                if event['event']=='census':
                    check('actual census arithmetic '+str(index)+value['scenario'],event['total_workers']==sum(event['process_threads'].values()))
                    all_censuses.append(dict(invocation=index,scenario=value['scenario'],**event))
        bytime=sorted(records,key=lambda v:v['constructor_entry'])
        check('42 serial scenario wrappers '+str(index),len(records)==42 and all(a['end']<=b['constructor_entry'] for a,b in zip(bytime,bytime[1:])))
        check('126 combined scenario cap '+str(index),sum(v['end']-v['constructor_entry'] for v in records)<=126)
        new=[v for v in records if v['scenario'].startswith('P')]
        check('new progress integrations not falsely claimed '+str(index),all(not any(e.get('event')=='progress_outcome' for e in v.get('events',[])) for v in new))
        check('saved failed result '+str(index),not inner['passed'] and inner['expected_exit_code']==1)
        current_match.append(sources==outer['sources_after'])
        consumed.append(dict(index=index,kind='diagnostic',receipt=rec(directory/'receipt.json'),execution=rec(directory/'execution.json'),note=rec(RUN/f's1-recovery-launch-note-015-diagnostic-{index:03d}.json'),tool_start=rec(str(prefix)+'-tool-start.json'),tool_completion=rec(str(prefix)+'-tool-completion.json'),
            tests_run=inner['tests_run'],subtests_run=inner['subtests_run'],failures=inner['failures'],errors=inner['errors'],elapsed_seconds=outer['elapsed_seconds'],inner_elapsed_seconds=inner['elapsed_seconds'],headroom_seconds=120-outer['elapsed_seconds'],passed=False,current_source_applicable=current_match[-1]))
        scenario_results.append(dict(invocation=index,records=[rec(p) for p in sorted(directory.glob('scenario-*.json'))],all_helpers_retired=True,all_ownership_empty=True,new_progress_cases_reached=False))
        periods.append((outer['start']['monotonic'],outer['end']['monotonic']))
    check('serial three focused invocations',all(a[1]<b[0] for a,b in zip(periods,periods[1:])))
    check('exact consumed3 focused0 aggregate',len(list(RUN.glob('s1-recovery-launch-note-015-diagnostic-*.json')))==3 and not list(RUN.glob('s1-recovery-launch-note-015-aggregate-*.json')))
    check('current source frozen since final failed diagnostic',current_match==[False,False,True])
    sandbox=[v['total_workers'] for v in all_censuses if v['invocation']==1];host=[v['total_workers'] for v in all_censuses if v['invocation']>1]
    check('sandbox bound and exact host violation retained',max(sandbox)==8 and min(host)>8 and max(host)==62)
    result=dict(schema='plan045-read-only-evidence-audit/v1',recorded_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),passed=all(v['passed'] for v in checks),checks=checks,check_count=len(checks),
        interpretation='Audit consistency only; all Plan045 acceptance remains unsupported/failed. No aggregate run.',sources=sources,source_count=len(sources),changed_source_paths=changed,
        collected_methods=methods,old_method_count=len(old_methods),current_method_count=len(methods),old_callback_count=sum(map(len,old_cases.values())),current_callback_count=sum(map(len,cases.values())),current_parameterized_methods=len(cases),assertion_map=assertion_map,
        old_substantive_assertions=sum(v['baseline_assertions'] for v in assertion_map),frozen_count=38,ledger=dict(record=rec(ledger_path),events=len(events),head=last,gpu_reservations=gpu_attempts,gpu_elapsed_seconds=gpu_elapsed,gpu_reserved_seconds=0,active_jobs=[],preserved_events=[events[i] for i in (250,255,256)]),
        consumed=consumed,scenarios=scenario_results,censuses=all_censuses,correction=rec(RUN/'s1-recovery-baseline-correction-013.json'),audit_script=rec(__file__),
        strict_plan045_acceptance=False,technical_plan045_acceptance=False,aggregate_passed=False,historical_strict_acceptance={'Plan041':False,'Plan043':False,'Plan044':False})
    save(RUN/'s1-recovery-audit-015.json',result)
    print(json.dumps({'passed':result['passed'],'checks':len(checks),'failures':[v for v in checks if not v['passed']],'sources':len(sources),'methods':len(methods),'callbacks':sum(map(len,cases.values()))}))

if __name__=='__main__':main()
