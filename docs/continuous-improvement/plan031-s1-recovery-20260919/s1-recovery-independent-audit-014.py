"""Fresh Plan044 standard-library reconciliation; no production imports or fixtures."""
import ast
from collections import Counter
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[3]
RUN=Path(__file__).resolve().parent
BASE='8ce3b5736852a49220f5f2cbd91c799785e0dce7'
SUITES=('s1_semantics','s1_recovery','backends','contracts','component_recovery','execution','budgets','supervisor','review_annotations')
checks=[]
def check(name,value):
    checks.append(dict(check=name,passed=bool(value)))
def rec(path):
    path=Path(path).resolve();assert 'prompts' not in path.parts
    raw=path.read_bytes();return dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def bound(value):
    check('bound '+value['path'],rec(value['path'])==value);return Path(value['path'])
def read(path):return json.loads(Path(path).read_text())
def save(path,value):
    raw=(json.dumps(value,indent=2,allow_nan=False)+'\n').encode()
    with Path(path).open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    assert Path(path).read_bytes()==raw

def typed(value):
    return json.dumps([[k,type(v).__name__,v] for k,v in sorted(value.items())],separators=(',',':'),ensure_ascii=True,allow_nan=False)
def extract(tree,module):
    methods=[];declared={};assertions={}
    for node in tree.body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SUBTEST_CASES' for t in node.targets):declared=ast.literal_eval(node.value)
    for cls in sorted((n for n in tree.body if isinstance(n,ast.ClassDef)),key=lambda n:n.name):
        for fn in sorted((n for n in cls.body if isinstance(n,ast.FunctionDef)),key=lambda n:n.name):
            name=module+'.'+cls.name+'.'+fn.name
            if fn.name.startswith('test_'):methods.append(name)
            assertions[name]=Counter(ast.dump(n,include_attributes=False) for n in ast.walk(fn) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr.startswith('assert'))
    return methods,declared,assertions

def main():
    directory=Path(sys.argv[1]).resolve();inner=read(directory/'receipt.json');outer=read(directory/'execution.json')
    methods=[];declared={};old_methods=[];assertion_map=[];prior_assertions=0
    for suite in SUITES:
        module='test_vipe_benchmark_'+suite;relative='tests/'+module+'.py'
        old_text=subprocess.check_output(['git','show',BASE+':'+relative],cwd=ROOT,text=True)
        old=extract(ast.parse(old_text),module);new=extract(ast.parse((ROOT/relative).read_text()),module)
        old_methods.extend(old[0]);methods.extend(new[0]);declared.update(new[1])
        check('literal typed callback preservation '+suite,{k:[typed(v) for v in rows] for k,rows in old[1].items()}=={k:[typed(v) for v in rows] for k,rows in new[1].items()})
        for name,before in old[2].items():
            missing=before-new[2].get(name,Counter());count=sum(before.values());prior_assertions+=count
            check('substantive assertion preservation '+name,not missing)
            assertion_map.append(dict(method=name,baseline_assertions=count,missing=list(missing),mapping='exact AST multiset inclusion; additions allowed'))
    check('205 baseline methods',len(old_methods)==205 and [m for m in methods if m in set(old_methods)]==old_methods)
    check('exact current AST collection',methods==inner['collected']==[r['id'] for r in inner['cases']] and len(methods)==len(set(methods)))
    callbacks=0
    for case in inner['cases']:
        expected=[typed(v) for v in declared.get(case['id'],[])];callbacks+=len(expected)
        check('actual typed callbacks '+case['id'],[typed(v['parameters']) for v in case['subtests']]==expected and all(v['status']=='passed' and v['id']==case['id']+'::'+typed(v['parameters']) for v in case['subtests']))
        check('passing method '+case['id'],case['status']=='passed')
    check('426 exact callbacks',callbacks==426)
    check('aggregate success',inner['passed'] and not inner['diagnostic'] and inner['tests_run']==len(methods) and inner['subtests_run']==callbacks and all(inner[k]==0 for k in ('failures','errors','skipped','expected_exit_code')) and inner['discovery_errors']==[])
    check('suite order',inner['suite_order']==list(SUITES)==[v['suite'] for v in inner['suites']])
    previous=inner['start']['monotonic']
    for suite in inner['suites']:
        check('serial suite '+suite['suite'],previous<=suite['start']['monotonic']<=suite['end']['monotonic']<=inner['end']['monotonic']);previous=suite['end']['monotonic']
    paths=sorted([ROOT/'scripts/basketball_vipe_benchmark.py',ROOT/'scripts/basketball_vipe_worker.py',ROOT/'configs/vipe-alternatives/benchmark-v1.json',*(ROOT/'scripts/vipe_benchmark').glob('*.py'),*(ROOT/'tests').glob('test_vipe_benchmark_*.py')])
    sources=[rec(p) for p in paths]
    check('77 complete current source membership',len(sources)==77)
    check('all four final source snapshots',sources==inner['sources_before']==inner['sources_after']==outer['sources_before']==outer['sources_after'])
    baseline=read(RUN/'s1-recovery-validation-012.json');prior={v['path']:v for v in baseline['sources']}
    changed=[str(Path(v['path']).relative_to(ROOT)) for v in sources if v!=prior.get(v['path'])]
    allowed={'scripts/vipe_benchmark/s1_helper_session.py','scripts/vipe_benchmark/supervisor.py','scripts/vipe_benchmark/s1_cpu_helper.py','tests/test_vipe_benchmark_supervisor.py','tests/test_vipe_benchmark_s1_helper_fixtures.py','tests/test_vipe_benchmark_s1_recovery.py','scripts/vipe_benchmark/s1_validation_runner.py'}
    check('allowed source edits only',set(changed)<=allowed)
    for relative in ('scripts/vipe_benchmark/s1_validation_capture.py','scripts/vipe_benchmark/s1_validation_contract.py','scripts/vipe_benchmark/backends.py','scripts/vipe_benchmark/s1_evidence.py','scripts/vipe_benchmark/stages.py','scripts/vipe_benchmark/s1_recovery.py'):
        check('unchanged protected source '+relative,rec(ROOT/relative)==prior[str(ROOT/relative)])
    stdin=b'import runpy\nimport sys\nsys.path.insert(0, "scripts")\nrunpy.run_module("vipe_benchmark.s1_validation_runner", run_name="__main__", alter_sys=True, init_globals={"STDIN_PYTHON_ARGV": tuple(sys.argv)})\n'
    check('exact stdin',bound(inner['stdin']).read_bytes()==stdin and inner['stdin']==outer['stdin'])
    for key in ('runner','interpreter'):check('paired '+key,inner[key]==outer[key]);bound(inner[key])
    bound(outer['capture']);bound(outer['receipt'])
    for key in ('stdout','stderr'):check('paired closed '+key,bound(inner[key]).read_bytes()==bound(outer[key]).read_bytes())
    argv=['.local/envs/stg-colmap/bin/python','-B','-'];invoke=inner['invocation']
    check('unchanged argv',invoke['launcher_argv']==outer['requested_argv']==argv and invoke['python_argv']==['-'])
    check('cwd',invoke['cwd']==outer['cwd']==str(ROOT))
    check('outer actual wait',outer['returncode']==0 and outer['wait_completed'] is True and outer['timed_out'] is False and outer['timeout_seconds']==300 and outer['elapsed_seconds']<=300)
    check('inner outer timing',outer['start']['monotonic']<=inner['start']['monotonic']<=inner['end']['monotonic']<=outer['end']['monotonic'])
    check('outer elapsed arithmetic',abs(outer['elapsed_seconds']-(outer['end']['monotonic']-outer['start']['monotonic']))<1e-6)
    children=[json.loads(line[len('S1_SCRIPT_CHILD '):]) for line in bound(inner['stdout']).read_text().splitlines() if line.startswith('S1_SCRIPT_CHILD ')]
    check('six direct script children',len(children)==6)
    previous=inner['start']['monotonic']
    for child in children:
        check('serial direct child '+str(child['argv']),previous<=child['start_monotonic']<=child['end_monotonic']<=inner['end']['monotonic'] and child['end_monotonic']-child['start_monotonic']<=12 and child['returncode']==0 and not child['timed_out']);previous=child['end_monotonic']
    check('direct children combined cap',sum(c['end_monotonic']-c['start_monotonic'] for c in children)<=72)
    correction=read(RUN/'s1-recovery-baseline-correction-012.json');oldcor=read(bound(correction['predecessor']))
    for item in correction['frozen_records']:bound(item)
    check('38 frozen records',len(correction['frozen_records'])==38)
    check('complete immutable correction prefix',correction['bookkeeping_transitions'][:len(oldcor['bookkeeping_transitions'])]==oldcor['bookkeeping_transitions'] and all(correction[k]==oldcor[k] for k in ('baseline','frozen_records','ledger_snapshot','bookkeeping_baseline')))
    appended=correction['bookkeeping_transitions'][len(oldcor['bookkeeping_transitions']):];dispatch=read(RUN/'implementation-dispatch-014.json')
    check('canonical three dispatch transitions',appended==dispatch['required_transitions'] and appended[0]==rec(RUN/'s1-recovery-bookkeeping-transition-post-013.json'))
    current=correction['bookkeeping_baseline']
    for item in correction['bookkeeping_transitions']:
        transition=read(bound(item));check('transition chain '+item['path'],transition['old']==current);current=transition['new']
    for item in appended:
        transition=read(item['path'])
        for side in ('old','new'):
            snapshot=rec(bound(transition[side+'_snapshot']));check('durable snapshot '+side+item['path'],all(snapshot[k]==transition[side][k] for k in ('sha256','bytes')))
    check('frozen actual IMPLEMENT status',current==correction['bookkeeping_observed']==rec(RUN/'status.md')==dispatch['status'])
    snap=correction['ledger_snapshot'];ledger=Path(snap['path']);raw=ledger.read_bytes();events=[json.loads(line) for line in raw.splitlines()]
    check('unchanged447 event ledger',rec(ledger)=={k:snap[k] for k in ('path','sha256','bytes')} and len(events)==447 and len(raw)==332437)
    previous=None
    for index,event in enumerate(events):
        payload={k:v for k,v in event.items() if k!='event_sha256'};digest=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
        check('ledger chain '+str(index),event['sequence']==index and event['previous_sha256']==previous and event['event_sha256']==digest);previous=digest
    check('unchanged ledger head',previous=='00cab019d73b6a3205f676b54cfb2f745f492fa5cca5c69b4567087cea62172b')
    check('no S1 recovery ledger event',not any(e.get('job_id')=='S1-calibration-recovery-001' for e in events))
    gpu=[v for v in events if v.get('resource')=='gpu'];gpu_attempts=sum(v['event']=='reserve' for v in gpu)
    gpu_elapsed=sum(v.get('elapsed_seconds',0) for v in gpu if v['event']=='finish')
    active={}
    for event in events:
        if event['event']=='reserve': active[event['job_id']]=event
        elif event['event'] in ('finish','checkpoint'): active.pop(event.get('job_id'),None)
    gpu_reserved=sum(v['seconds'] for v in active.values() if v.get('resource')=='gpu')
    check('independent original ledger accounting',gpu_attempts==30 and gpu_elapsed==4374.044265462899 and gpu_reserved==0 and not active)
    oldledger=read(RUN/'s1-recovery-ledger-audit-013.json');check('original failures250255256',[events[i] for i in (250,255,256)]==oldledger['preserved_events'])
    consumed=[];intervals=[];scenario_summary=[]
    for kind,limit in (('diagnostic',3),('aggregate',2)):
        notes=sorted(RUN.glob('s1-recovery-launch-note-014-'+kind+'-*.json'));check('attempt cap '+kind,len(notes)<=limit)
        for index,path in enumerate(notes,1):
            note=read(path);run=Path(note['run_directory']);execution=read(run/'execution.json');receipt=read(run/'receipt.json')
            launch=read(RUN/f's1-recovery-driver-014-{kind}-{index:03}-exec-start.json')
            check('durable prospective note '+path.name,launch['note']==rec(path) and note['stage_start']['monotonic']<=note['observed']['monotonic']<=launch['before_launch']['monotonic']<=execution['start']['monotonic'])
            check('full timeout execution fit '+path.name,execution['start']['monotonic']-note['stage_start']['monotonic']+note['timeout_seconds']+note['final_aggregate_reserve_seconds']<3300 and execution['end']['monotonic']-note['stage_start']['monotonic']<3300)
            check('all five native settings '+path.name,all(note['environment'][k]=='1' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','OPENCV_FOR_THREADS_NUM')))
            check('closed actual invocation '+path.name,execution['wait_completed'] and not execution['timed_out'] and execution['returncode']==receipt['expected_exit_code'] and execution['sources_before']==execution['sources_after']==receipt['sources_before']==receipt['sources_after'])
            for key in ('stdout','stderr'):bound(execution[key]);bound(receipt[key])
            completion=read(RUN/f's1-recovery-tool-completion-014-{kind}-{index:03}.json')
            if not(kind=='diagnostic' and index==1):check('actual tool exit '+path.name,completion['completion']['exit_code']==execution['returncode'])
            else:check('first tool observation loss disclosed',completion['completion']['tool_completion_retained'] is False)
            records=[read(v) for v in sorted(run.glob('scenario-L*.json'))]
            check('36 real scenarios '+path.name,len(records)==36 and [v['scenario'] for v in records]==[f'L{i:02}' for i in range(1,37)])
            for row in records:
                check('fixture timing '+path.name+row['scenario'],row['execution_seconds']<=2 and row['cleanup_seconds']<=1 and row['end']-row['constructor_entry']<=3 and row['cleanup_confirmed'])
                check('fixture fixed cutoffs '+path.name+row['scenario'],abs(row['action_cutoff']-row['constructor_entry']-2)<1e-6 and abs(row['safety_cutoff']-row['constructor_entry']-3)<1e-6)
            check('serial36 fixture scenarios '+path.name,all(a['end']<=b['constructor_entry'] for a,b in zip(records,records[1:])))
            check('108sec combined fixture cap '+path.name,sum(v['end']-v['constructor_entry'] for v in records)<=108)
            censuses=[e for r in records for e in r.get('events',[]) if e['event']=='census']
            if not(kind=='diagnostic' and index==1):check('measured final topology '+path.name,all(e['total_workers']==sum(e['process_threads'].values())<=8 and e['controller_threads']==2 for e in censuses))
            consumed.append(dict(kind=kind,index=index,note=rec(path),execution=rec(run/'execution.json'),receipt=rec(run/'receipt.json'),returncode=execution['returncode'],elapsed_seconds=execution['elapsed_seconds'],censuses=censuses))
            intervals.append((execution['start']['monotonic'],execution['end']['monotonic']))
            scenario_summary.append(dict(run=str(run),records=[rec(v) for v in sorted(run.glob('scenario-L*.json'))]))
    intervals.sort();check('all invocations serial',all(a[1]<b[0] for a,b in zip(intervals,intervals[1:])))
    phase=read(directory/'controller-phase-trace.json');rows=phase['phases']
    check('actual controller phases',{'initial_sample','reserve_guard','reserve_call','prelaunch','worker_sample','acceptance','reconciliation','publication','retirement'}<={r['phase'] for r in rows})
    check('one exact helper pair through retirement',len(rows[0]['identities'])==2 and all(r['identities']==rows[0]['identities'] and r['session']==rows[0]['session'] and r['boot']==rows[0]['boot'] for r in rows) and rows[-1]['cleanup_confirmed'] and phase['replacements']==0)
    check('actual controller CPU workers',all(r['total_workers']<=8 for r in rows if 'total_workers' in r))
    check('helper and worker active identities recorded',all(r['worker'] is not None for r in rows if r['phase'] in ('worker_sample','acceptance','reconciliation')) and all(r['worker_retired'] for r in rows if r['phase'] in ('publication','retirement')))
    for role in ('work','sample'):
        seq=[r['request_sequences'][role] for r in rows];check('monotonic actual phase requests '+role,seq==sorted(seq))
    for label in ('L29','L30'):
        row=read(directory/('scenario-'+label+'.json'));e=next(e for e in row['events'] if e['event']=='readable_deadline_equality')['observation']
        check('complete readable equality '+label,e['frame']['bytes']>4 and e['decision']==e['deadline'] and e['payload']['acquisition_end']<=e['post']['acquisition_start'] and e['pre']['generation']<e['post']['generation'] and row['last_sample'] is None and row['max_gap']<=.1)
    ambiguous=read(directory/'scenario-L36.json');check('actual child acquired before ambiguous launch return',bool(ambiguous['production']['actually_acquired']) and ambiguous['production']['state']=='launch_unknown' and ambiguous['production']['returned']<=ambiguous['production']['deadline']+.1)
    for path in directory.glob('scenario-L*.json'):
        row=read(path)
        check('recorded tighter call bounds '+path.name,all(o['returned']<=o['deadline']+.1 for o in row.get('call_observations',[])))
    for name in ('transport-controls','construction-controls','census-controls','trace-controls'):bound(rec(directory/(name+'.json')))
    process=read(RUN/'s1-recovery-process-observation-014.json');check('final observed completion',process['aggregate']['execution']==rec(directory/'execution.json') and process['aggregate']['tool_exit_code']==0)
    result=dict(schema='plan044-independent-reconciliation/v1',passed=all(c['passed'] for c in checks),checks=checks,check_count=len(checks),source_count=len(sources),sources=sources,changed_source_paths=changed,tests_run=len(methods),subtests_run=callbacks,parameterized_methods=len(declared),old_methods_preserved=len(old_methods),old_assertions_preserved=prior_assertions,assertion_map=assertion_map,added_methods=[m for m in methods if m not in set(old_methods)],frozen_count=len(correction['frozen_records']),ledger=dict(record=rec(ledger),events=len(events),head=previous,gpu_attempts=gpu_attempts,gpu_elapsed_seconds=gpu_elapsed,gpu_reserved_seconds=gpu_reserved,active_jobs=list(active),prior_accounting=oldledger),consumed=consumed,scenarios=scenario_summary,receipt=rec(directory/'receipt.json'),execution=rec(directory/'execution.json'),controller_phase_trace=rec(directory/'controller-phase-trace.json'),correction=rec(RUN/'s1-recovery-baseline-correction-012.json'),audit_script=rec(__file__),outer_elapsed_seconds=outer['elapsed_seconds'],headroom_seconds=300-outer['elapsed_seconds'],strict_plan044_acceptance=False,procedural_observations=rec(RUN/'s1-recovery-procedural-observations-014.json'),historical_plan041_strict=False,historical_plan043_strict=False)
    save(RUN/'s1-recovery-audit-014.json',result)
    print(json.dumps(dict(passed=result['passed'],checks=len(checks),failed=[v['check'] for v in checks if not v['passed']],methods=len(methods),callbacks=callbacks,assertions=prior_assertions)))

if __name__=='__main__':main()
