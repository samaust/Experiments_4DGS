"""Read-only independent Plan 042 reconciliation; no production imports or tests."""
import ast
import datetime
import hashlib
import json
import math
import os
import subprocess
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
RUN = Path(__file__).resolve().parent
SUITES = ('s1_semantics','s1_recovery','backends','contracts','component_recovery','execution','budgets','supervisor','review_annotations')
checks = []

def check(name, condition):
    checks.append(dict(check=name, passed=bool(condition)))
    if not condition:
        raise AssertionError(name)


def record(path):
    path=Path(path).resolve()
    assert 'prompts' not in path.parts
    data=path.read_bytes()
    return dict(path=str(path),sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))


def bound(value):
    check('record '+value['path'], type(value.get('bytes')) is int and value == record(value['path']))
    return Path(value['path'])


def typed(parameters):
    assert type(parameters) is dict
    rows=[]
    for key,value in sorted(parameters.items()):
        assert type(key) is str and type(value) in (str,bool,int,float,type(None))
        assert type(value) is not float or math.isfinite(value)
        rows.append([key,type(value).__name__,value])
    return json.dumps(rows,ensure_ascii=True,separators=(',',':'),allow_nan=False)


def times(value):
    a,b=value['start'],value['end']
    numbers=(a['monotonic'],b['monotonic'],value['elapsed_seconds'])
    assert all(type(v) in (float,int) and math.isfinite(v) and v>=0 for v in numbers)
    utc=[datetime.datetime.fromisoformat(t['utc']) for t in (a,b)]
    assert all(t.tzinfo and t.utcoffset()==datetime.timedelta(0) for t in utc)
    assert numbers[0]<=numbers[1] and utc[0]<=utc[1] and abs(numbers[2]-(numbers[1]-numbers[0]))<=1e-6
    return numbers[0],numbers[1],utc[0],utc[1]


def main():
    directory=Path(sys.argv[1]).resolve()
    inner=json.loads((directory/'receipt.json').read_text())
    outer=json.loads((directory/'execution.json').read_text())
    observation=json.loads((RUN/'s1-recovery-process-observation-012.json').read_text())
    methods=[];declared={}
    for suite in SUITES:
        module='test_vipe_benchmark_'+suite
        tree=ast.parse((ROOT/'tests'/f'{module}.py').read_text())
        literals=[n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SUBTEST_CASES' for t in n.targets)]
        check('one literal '+suite,len(literals)==1)
        for d in ast.walk(literals[0].value):
            if isinstance(d,ast.Dict):
                keys=[ast.literal_eval(k) for k in d.keys]
                check('unique AST dictionary keys '+suite,len(keys)==len(set(keys)))
        declaration=ast.literal_eval(literals[0].value)
        parameterized=set()
        for cls in sorted((n for n in tree.body if isinstance(n,ast.ClassDef)),key=lambda n:n.name):
            for method in sorted((n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')),key=lambda n:n.name):
                name=f'{module}.{cls.name}.{method.name}'
                methods.append(name)
                if any(isinstance(n,ast.Attribute) and n.attr=='subTest' for n in ast.walk(method)):
                    parameterized.add(name)
        check('declared exact parameterized methods '+suite,set(declaration)==parameterized)
        declared.update({name:list(cases) for name,cases in declaration.items()})
    check('static collection',inner['collected']==methods==[c['id'] for c in inner['cases']] and len(methods)==len(set(methods)))
    check('aggregate schema',inner['schema']=='s1-cpu-aggregate/v2' and inner['diagnostic'] is False and inner['discovery_errors']==[])
    check('declaration membership',set(inner['declarations'])==set(declared))
    callbacks=0
    for case in inner['cases']:
        expected=declared.get(case['id'],[])
        wanted=[typed(p) for p in expected]
        check('declaration uniqueness '+case['id'],len(wanted)==len(set(wanted)))
        if expected:check('inner declaration '+case['id'],[typed(p) for p in inner['declarations'][case['id']]]==wanted)
        check('callback sequence '+case['id'],[typed(s['parameters']) for s in case['subtests']]==wanted)
        check('callback IDs/status '+case['id'],case['status']=='passed' and all(s['status']=='passed' and s['id']==case['id']+'::'+typed(s['parameters']) for s in case['subtests']))
        callbacks+=len(expected)
    check('suite order',inner['suite_order']==list(SUITES)==[s['suite'] for s in inner['suites']])
    limits=times(inner);previous=(limits[0],limits[2])
    for suite in inner['suites']:
        rows=[c for c in inner['cases'] if c['id'].startswith('test_vipe_benchmark_'+suite['suite']+'.')]
        check('suite collection '+suite['suite'],suite['collected']==[r['id'] for r in rows])
        expected=dict(tests_run=len(rows),subtests_run=sum(len(r['subtests']) for r in rows),failures=0,errors=0,skipped=0)
        check('suite counters '+suite['suite'],all(type(suite[k]) is int and suite[k]==v for k,v in expected.items()))
        span=times(suite)
        check('serial contained suite '+suite['suite'],previous[0]<=span[0]<=span[1]<=limits[1] and previous[1]<=span[2]<=span[3]<=limits[3])
        previous=(span[1],span[3])
    check('aggregate counters',all(type(inner[k]) is int and inner[k]==v for k,v in dict(tests_run=len(methods),subtests_run=callbacks,failures=0,errors=0,skipped=0,expected_exit_code=0).items()) and inner['passed'] is True)
    paths=sorted([ROOT/'scripts/basketball_vipe_benchmark.py',ROOT/'scripts/basketball_vipe_worker.py',ROOT/'configs/vipe-alternatives/benchmark-v1.json',*(ROOT/'scripts/vipe_benchmark').glob('*.py'),*(ROOT/'tests').glob('test_vipe_benchmark_*.py')])
    sources=[record(p) for p in paths]
    check('all four source snapshots',inner['sources_before']==inner['sources_after']==outer['sources_before']==outer['sources_after']==sources)
    for rec in sources:bound(rec)
    stdin=('import runpy\nimport sys\nsys.path.insert(0, "scripts")\nrunpy.run_module("vipe_benchmark.s1_validation_runner", run_name="__main__", alter_sys=True, init_globals={"STDIN_PYTHON_ARGV": tuple(sys.argv)})\n').encode()
    check('exact four-line stdin',bound(inner['stdin']).read_bytes()==stdin and outer['stdin']==inner['stdin'])
    check('runner snapshot',bound(inner['runner']).read_bytes()==(ROOT/'scripts/vipe_benchmark/s1_validation_runner.py').read_bytes() and outer['runner']==inner['runner'])
    check('capture snapshot',bound(outer['capture']).read_bytes()==(ROOT/'scripts/vipe_benchmark/s1_validation_capture.py').read_bytes())
    for key in ('stdout','stderr'):
        check('complete process '+key,bound(inner[key]).read_bytes()==bound(outer[key]).read_bytes())
    argv=['.local/envs/stg-colmap/bin/python','-B','-']
    env={key:'1' for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','VIPE_CPU_VALIDATION')}
    env.update(S1_HELPER_DIAGNOSTIC=None,S1_RECEIPT_DIAGNOSTIC=None)
    invoke=inner['invocation']
    check('actual argv',invoke['launcher_argv']==outer['requested_argv']==argv and invoke['python_argv']==['-'] and invoke['runpy_argv']==[str(ROOT/'scripts/vipe_benchmark/s1_validation_runner.py')])
    check('executable',invoke['executable']==str(ROOT/argv[0]) and invoke['resolved_interpreter']==str((ROOT/argv[0]).resolve()) and bound(inner['interpreter'])==(ROOT/argv[0]).resolve() and inner['interpreter']==outer['interpreter'])
    check('env/cwd/run root',invoke['environment']==outer['environment']==env and invoke['cwd']==outer['cwd']==str(ROOT) and invoke['run_directory']==inner['run_directory']==outer['run_directory']==str(directory))
    check('suite invocations',all(s['invocation']==invoke for s in inner['suites']))
    bounds=times(outer)
    check('outer timing containment',bounds[0]<=limits[0]<=limits[1]<=bounds[1] and bounds[2]<=limits[2]<=limits[3]<=bounds[3] and outer['elapsed_seconds']<=outer['timeout_seconds']<=300)
    check('external wait',type(outer['returncode']) is int and outer['returncode']==0 and outer['timed_out'] is False and outer['wait_completed'] is True and inner['boot_id']==outer['boot_id'])
    check('receipt link',bound(outer['receipt'])==directory/'receipt.json')
    check('observed actual driver completion',observation['aggregate']['tool_exit_code']==0 and observation['aggregate']['child_returncode']==outer['returncode'] and observation['aggregate']['execution']==record(directory/'execution.json'))
    child_lines=[line for line in bound(inner['stdout']).read_text().splitlines() if line.startswith('S1_SCRIPT_CHILD ')]
    children=[json.loads(line[len('S1_SCRIPT_CHILD '):]) for line in child_lines]
    child_cases=declared['test_vipe_benchmark_s1_recovery.NumericalEnvelopeTests.test_direct_script_declaration_lookup']
    check('six serial direct scripts',len(children)==len(child_cases)==6)
    last=limits[0]
    for child,case in zip(children,child_cases):
        script=ROOT/'tests'/('test_vipe_benchmark_'+case['suite']+'.py')
        check('child argv '+case['suite'],child['argv']==[invoke['executable'],'-B',str(script),case['selector'],'-v'])
        check('child completion '+case['suite'],child['returncode']==0 and child['timed_out'] is False and child['cwd']==str(ROOT))
        check('child duration '+case['suite'],last<=child['start_monotonic']<=child['end_monotonic']<=limits[1] and child['end_monotonic']-child['start_monotonic']<=12)
        last=child['end_monotonic']
        check('child requested real method '+case['suite'],'Ran 1 test' in child['stderr'] and '\nOK\n' in child['stderr'] and case['selector'].split('.')[1] in child['stderr'])
    check('script total cap',sum(c['end_monotonic']-c['start_monotonic'] for c in children)<=72)
    correction=json.loads((RUN/'s1-recovery-baseline-correction-010.json').read_text())
    for rec in correction['frozen_records']:bound(rec)
    snap=correction['ledger_snapshot'];ledger=Path(snap['path']);raw=ledger.read_bytes();events=[json.loads(line) for line in raw.splitlines()]
    check('frozen ledger',record(ledger)=={k:snap[k] for k in ('path','sha256','bytes')} and len(events)==447 and len(raw)==332437)
    previous=None
    for index,event in enumerate(events):
        payload={k:v for k,v in event.items() if k!='event_sha256'}
        actual=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
        assert event['sequence']==index and event['previous_sha256']==previous and event['event_sha256']==actual
        previous=actual
    check('ledger chain head',previous==snap['last_event_sha256']=='00cab019d73b6a3205f676b54cfb2f745f492fa5cca5c69b4567087cea62172b')
    check('no recovery events',not any(e.get('job_id')=='S1-calibration-recovery-001' for e in events))
    current=correction['bookkeeping_baseline']
    for rec in correction['bookkeeping_transitions']:
        transition=json.loads(bound(rec).read_text());check('status transition '+rec['path'],transition['old']==current);current=transition['new']
    check('status endpoint',current==record(RUN/'status.md')==correction['bookkeeping_observed'])
    predecessor=json.loads(bound(correction['predecessor']).read_text())
    check('immutable correction prefix',correction['bookkeeping_transitions'][:len(predecessor['bookkeeping_transitions'])]==predecessor['bookkeeping_transitions'])
    check('immutable baseline/frozen/ledger',all(correction[k]==predecessor[k] for k in ('baseline','frozen_records','ledger_snapshot','bookkeeping_baseline')))
    appended=correction['bookkeeping_transitions'][len(predecessor['bookkeeping_transitions']):]
    check('three actual appended transitions',len(appended)==3)
    for rec in appended:
        transition=json.loads(bound(rec).read_text())
        check('canonical new transition',transition['schema']=='plan034-s1-bookkeeping-transition/v1')
        for side in ('old','new'):
            snapshot=record(bound(transition[side+'_snapshot']))
            check('actual snapshot '+side,all(snapshot[k]==transition[side][k] for k in ('sha256','bytes')))
        if 'preserved_original' in transition:
            original=json.loads(bound(transition['preserved_original']).read_text())
            check('durable post010 replacement',all(original[k]==transition[k] for k in ('schema','old','new','old_snapshot')))
    check('canonical post011 directly appended',appended[0]==record(RUN/'s1-recovery-bookkeeping-transition-post-011.json'))
    old_wrapper_path=RUN/'s1-recovery-validation-010.json'
    old_wrapper=json.loads(old_wrapper_path.read_text())
    old_inner=json.loads(bound(old_wrapper['tests'][0]['receipt']).read_text())
    old_outer=json.loads(bound(old_wrapper['tests'][0]['execution']).read_text())
    old_methods=old_inner['collected']
    check('all 169 old methods in original relative order',[name for name in methods if name in set(old_methods)]==old_methods and len(old_methods)==169)
    old_cases={case['id']:case for case in old_inner['cases']}
    check('all 426 old passing typed callbacks retained',sum(len(c['subtests']) for c in old_cases.values())==426 and all(case==old_cases[case['id']] for case in inner['cases'] if case['id'] in old_cases))
    added=[name for name in methods if name not in set(old_methods)]
    check('seven exact collected cache additions',len(added)==7 and all(name.startswith('test_vipe_benchmark_s1_recovery.DeclarationCacheTests.test_') for name in added))
    changed=[]
    previous_sources={r['path']:r for r in old_wrapper['sources']}
    check('75 source membership preserved',set(previous_sources)=={r['path'] for r in sources} and len(sources)==75)
    for rec in sources:
        if rec!=previous_sources[rec['path']]:changed.append(str(Path(rec['path']).relative_to(ROOT)))
    allowed=['scripts/vipe_benchmark/s1_validation_contract.py','scripts/vipe_benchmark/s1_validation_runner.py','tests/test_vipe_benchmark_s1_recovery.py']
    check('only permitted three sources changed',sorted(changed)==allowed)
    source_trees={}
    for relative in allowed:
        old_text=subprocess.check_output(['git','show','HEAD:'+relative],cwd=ROOT).decode()
        check('HEAD source matches reviewed source record '+relative,hashlib.sha256(old_text.encode()).hexdigest()==previous_sources[str(ROOT/relative)]['sha256'])
        source_trees[relative]=(ast.parse(old_text),ast.parse((ROOT/relative).read_text()))
    contract_old,contract_new=source_trees[allowed[0]]
    old_parse=next(n for n in contract_old.body if isinstance(n,ast.FunctionDef) and n.name=='parse_suite')
    cached=next(n for n in contract_new.body if isinstance(n,ast.FunctionDef) and n.name=='_parse_suite_cached')
    check('real parser body preserved exactly',[ast.dump(n) for n in old_parse.body]==[ast.dump(n) for n in cached.body])
    check('LRU16 exact configuration',len(cached.decorator_list)==1 and ast.unparse(cached.decorator_list[0])=='lru_cache(maxsize=16)')
    wrapper=next(n for n in contract_new.body if isinstance(n,ast.FunctionDef) and n.name=='parse_suite')
    check('defensive copies for exact positional keys',len(wrapper.body)==2 and ast.unparse(wrapper.body[-1])=='return copy.deepcopy(_parse_suite_cached(text, module))')
    for fn in (n for n in contract_old.body if isinstance(n,ast.FunctionDef) and n.name!='parse_suite'):
        current_fn=next(n for n in contract_new.body if isinstance(n,ast.FunctionDef) and n.name==fn.name)
        check('existing contract unchanged '+fn.name,ast.dump(fn)==ast.dump(current_fn))
    for relative in allowed[1:]:
        before,after=source_trees[relative]
        if relative.endswith('s1_validation_runner.py'):
            source=subprocess.check_output(['git','show','HEAD:'+relative],cwd=ROOT).decode()
            check('runner focus only',(ROOT/relative).read_text()==source.replace("if t.__class__.__name__ == 'ReservationClockTests'","if t.__class__.__name__ == 'DeclarationCacheTests'"))
        else:
            def test_asts(tree):
                return {cls.name+'.'+fn.name:ast.dump(fn) for cls in tree.body if isinstance(cls,ast.ClassDef) for fn in cls.body if isinstance(fn,ast.FunctionDef) and fn.name.startswith('test_')}
            before_asts,after_asts=test_asts(before),test_asts(after)
            check('every prior recovery test assertion/body unchanged',all(after_asts[k]==v for k,v in before_asts.items()))
            def literal(tree):
                return next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SUBTEST_CASES' for t in n.targets))
            check('entire prior callback declaration unchanged',ast.dump(literal(before))==ast.dump(literal(after)))
    launch_records=[]
    for kind in ('diagnostic','aggregate'):
        notes=sorted(RUN.glob('s1-recovery-launch-note-012-'+kind+'-*.json'))
        check('one authorized '+kind+' invocation',len(notes)==1)
        note=json.loads(notes[0].read_text())
        completion_path=RUN/('s1-recovery-driver-012-'+kind+'-001-completion.json')
        completion=json.loads(completion_path.read_text())
        check('durable note exact verified binding '+kind,completion['note']==record(notes[0]))
        run_path=Path(note['run_directory'])
        execution=json.loads((run_path/'execution.json').read_text())
        first=note['stage_start']['monotonic']
        note_time=note['observed']['monotonic'];launch_time=completion['before_launch']['monotonic']
        check('prospective note and launch gate '+kind,first<=note_time<=launch_time<=execution['start']['monotonic'] and launch_time-first+note['timeout_seconds']+note['final_aggregate_reserve_seconds']<1620)
        check('actual completed within cutoff '+kind,execution['end']['monotonic']-first<1620 and completion['completion_observed'] is True and completion['tool_driver_returncode']==0 and execution['returncode']==0 and execution['wait_completed'] is True and execution['timed_out'] is False)
        check('one thread launch environment '+kind,all(note['environment'][key]=='1' for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')))
        check('actual serial attempts',kind!='aggregate' or json.loads((RUN/'s1-recovery-driver-012-diagnostic-001-completion.json').read_text())['end']['monotonic']<note_time)
        launch_records.append(dict(note=record(notes[0]),completion=record(completion_path),execution=record(run_path/'execution.json')))
    diagnostic=json.loads((RUN/'s1-recovery-diagnostic-012-001/receipt.json').read_text())
    check('focused seven real cache tests passed',diagnostic['collected']==added and diagnostic['passed'] is True and diagnostic['tests_run']==7 and all(diagnostic[k]==0 for k in ('failures','errors','skipped','subtests_run')))
    check('focused source exact final source',diagnostic['sources_before']==diagnostic['sources_after']==sources)
    savings=dict(outer_seconds=old_outer['elapsed_seconds']-outer['elapsed_seconds'],recovery_seconds=next(s['elapsed_seconds'] for s in old_inner['suites'] if s['suite']=='s1_recovery')-next(s['elapsed_seconds'] for s in inner['suites'] if s['suite']=='s1_recovery'))
    barrier_lines=[json.loads(line[len('S1_CLOCK_BARRIER '):]) for line in bound(inner['stdout']).read_text().splitlines() if line.startswith('S1_CLOCK_BARRIER ')]
    barrier_cases=declared['test_vipe_benchmark_s1_recovery.ReservationClockTests.test_real_segment_publication_barriers']
    check('all real barrier observations',len(barrier_lines)==len(barrier_cases))
    for observed,case in zip(barrier_lines,barrier_cases):
        check('barrier identity/counts '+case['kind'],observed['case']==case['kind'] and observed['adapter_calls']==1 and observed['loader_frames'].count(50)==case['first_loads'])
        allowed=case['kind'] in ('positive','reuse_positive')
        check('next input bound '+case['kind'],observed['loader_frames'].count(62)==int(allowed))
        check('live completion boundary '+case['kind'],(observed['completion_observation']<observed['work_deadline'])==allowed)

    result=dict(schema='plan042-independent-reconciliation/v1',passed=True,old_methods_preserved=len(old_methods),old_callbacks_preserved=426,added_methods=added,changed_source_paths=changed,launch_records=launch_records,observed_savings=savings,outer_elapsed_seconds=outer['elapsed_seconds'],recovery_elapsed_seconds=next(s['elapsed_seconds'] for s in inner['suites'] if s['suite']=='s1_recovery'),headroom_seconds=300-outer['elapsed_seconds'],checks=checks,tests_run=len(methods),subtests_run=callbacks,parameterized_methods=len(declared),source_count=len(sources),frozen_count=len(correction['frozen_records']),ledger=dict(events=len(events),record=record(ledger),head=previous),historical_failure_events=[events[i] for i in (250,255,256)],receipt=record(directory/'receipt.json'),execution=record(directory/'execution.json'),observation=record(RUN/'s1-recovery-process-observation-012.json'),correction=record(RUN/'s1-recovery-baseline-correction-010.json'),audit_script=record(__file__))
    with (RUN/'s1-recovery-audit-011.json').open('x') as stream:
        stream.write(json.dumps(result,indent=2)+'\n');stream.flush();os.fsync(stream.fileno())
    print(json.dumps({k:result[k] for k in ('passed','tests_run','subtests_run','source_count','frozen_count')}))


if __name__=='__main__':
    main()
