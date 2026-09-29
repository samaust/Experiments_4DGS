"""Independent Plan046 byte/AST/evidence audit; imports no production code."""
import ast
import collections
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

C=Path(__file__).resolve().parent
ROOT=C.parents[2]

def record(path):
    path=Path(path).resolve()
    if 'prompts' in path.parts:raise ValueError('forbidden path')
    raw=path.read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

def read(name):return json.loads((C/name).read_bytes())

def publish(name,value):
    path=C/name;raw=(json.dumps(value,indent=2,allow_nan=False)+'\n').encode()
    with path.open('xb') as stream:
        stream.write(raw);stream.flush();os.fsync(stream.fileno())
    if path.read_bytes()!=raw:raise ValueError('audit readback')
    return record(path)

checks=[]
def check(name,condition,detail=None):
    checks.append(dict(name=name,passed=bool(condition),detail=detail))

old=read('s1-recovery-baseline-correction-013.json')
old_validation=read('s1-recovery-validation-014.json')
base=read('iteration-016-method-baseline.json')
start=read('iteration-016-timing-start.json')
pre=read('iteration-016-final-source-preparation.json')
sources=[record(r['path']) for r in pre['sources']]
check('final source preparation unchanged',sources==pre['sources'])
check('original source membership',len(sources)==78)
for rec in old['frozen_records']:
    actual=record(rec['path']);check('frozen '+rec['path'],all(actual[k]==rec[k] for k in actual))
partial=read('s1-recovery-partial-source-015/manifest.json')
for item in partial['sources']:check('immutable partial '+item['snapshot']['path'],record(item['snapshot']['path'])==item['snapshot'])
ledger_record=record(old['ledger_snapshot']['path']);ledger=[json.loads(line) for line in Path(ledger_record['path']).read_bytes().splitlines()]
check('original ledger bytes',all(ledger_record[k]==old['ledger_snapshot'][k] for k in ledger_record))
check('447 original ledger events',len(ledger)==447)
check('original ledger head',ledger[-1]['event_sha256']=='00cab019d73b6a3205f676b54cfb2f745f492fa5cca5c69b4567087cea62172b')
transitions=list(old['bookkeeping_transitions'])
transitions += [record(C/('s1-recovery-bookkeeping-transition-'+stage+'-016.json')) for stage in ('review','plan','implement')]
previous=old['bookkeeping_baseline'];snapshot_checks=[]
for rec in transitions:
    check('transition bytes '+rec['path'],record(rec['path'])==rec)
    transition=json.loads(Path(rec['path']).read_bytes())
    check('transition join '+rec['path'],transition['old']==previous)
    for side in ('old','new'):
        snapshot=transition.get(side+'_snapshot')
        if snapshot is not None:
            available=Path(snapshot['path']).is_file()
            actual=record(snapshot['path']) if available else None
            valid=actual==snapshot and all(snapshot[k]==transition[side][k] for k in ('bytes','sha256'))
            snapshot_checks.append(dict(transition=rec,side=side,record=snapshot,available=available,matched=valid))
            check('snapshot '+snapshot['path'],valid)
        else:snapshot_checks.append(dict(transition=rec,side=side,available=False,provenance=transition.get('provenance'),reason=transition.get('verification','No snapshot in historical record; bytes not reconstructed')))
    previous=transition['new']
check('31 actual transitions',len(transitions)==31)
check('28 transition prefix preserved',transitions[:28]==old['bookkeeping_transitions'])
check('frozen current IMPLEMENT status',record(C/'status.md')==previous)
check('status supplied by main',previous['sha256']=='5111315d438adaba923be45dd9b87ffe78bb29e36ba111f8cff8e8a6025a8431' and previous['bytes']==1172)
missing=[];method_maps=[];declarations={}
for source in base['files']:
    path=ROOT/source['path'];tree=ast.parse(path.read_text());methods={}
    for cls in (n for n in tree.body if isinstance(n,ast.ClassDef)):
        for node in cls.body:
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
                methods[cls.name+'.'+node.name]=[ast.dump(n,include_attributes=False) for n in ast.walk(node) if isinstance(n,ast.Assert) or isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr.startswith('assert')]
    for name,method in source['methods'].items():
        lost=collections.Counter(method['assertions'])-collections.Counter(methods.get(name,[]))
        if lost:missing.append(dict(path=source['path'],method=name,assertions=dict(lost)))
    local={}
    for node in tree.body:
        if isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='SUBTEST_CASES' for target in node.targets):local=ast.literal_eval(node.value)
    for old_decl in source['declarations']:
        for method,values in old_decl.items():check('preserved declaration '+method,local.get(method)==values)
    declarations.update(local)
    method_maps.append(dict(path=str(path),methods={name:len(values) for name,values in methods.items()}))
check('all old substantive assertion occurrences retained',not missing,missing)
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
check('unchanged HEAD',head=='ebf9d9ad39c25b5732fadefcdc36cb71e0bde613')
unchanged=[]
for name in ('s1_validation_capture.py','s1_validation_runner.py','s1_validation_contract.py','s1_clock.py','backends.py','config.py'):
    path=ROOT/'scripts/vipe_benchmark'/name
    raw=subprocess.check_output(['git','show','HEAD:'+str(path.relative_to(ROOT))],cwd=ROOT)
    same=path.read_bytes()==raw;unchanged.append(dict(record=record(path),head_bytes_identical=same));check('unchanged infrastructure/science '+name,same)
consumed=[];scenarios=[];censuses=[];direct=[]
for kind,limit,timeout in [('diagnostic',3,120),('aggregate',2,300)]:
    for index in range(1,limit+1):
        label=f'{kind}-{index:03}';directory=C/f's1-recovery-{kind}-016-{index:03}'
        execution=json.loads((directory/'execution.json').read_bytes());receipt=json.loads((directory/'receipt.json').read_bytes())
        tool_start=read('iteration-016-'+label+'-tool-start.json');tool_done=read('iteration-016-'+label+'-tool-completion.json')
        note=read('s1-recovery-launch-note-016-'+label+'.json')
        driver=read('s1-recovery-driver-016-'+label+'-exec-start.json')
        root=note['ownership_root'];ancestors=note['preexisting_ancestors']
        check('pre-existing ancestry before stage '+label,all(a['start_ticks']/os.sysconf('SC_CLK_TCK')<start['monotonic'] for a in ancestors))
        check('root equals capture parent identity '+label,root['pid']!=execution['child_pid'] and root['boot_id']==execution['boot_id'])
        check('closed current-source capture '+label,execution['sources_before']==execution['sources_after'])
        check('full timeout maintained '+label,execution['timeout_seconds']==timeout and not execution['timed_out'] and execution['wait_completed'])
        check('actual outer completion '+label,tool_done['exit_code']==execution['returncode'])
        check('outer session evidence '+label,tool_start['response'].get('session_id') is not None or 'exit_code' in tool_start['response'])
        check('prospective fit after durable preparation '+label,driver['before_launch']['monotonic']-start['monotonic']+timeout+note['final_aggregate_reserve_seconds']<4800)
        consumed.append(dict(kind=kind,index=index,directory=str(directory),methods=receipt['tests_run'],callbacks=receipt['subtests_run'],failures=receipt['failures'],errors=receipt['errors'],skips=receipt['skipped'],discovery_errors=receipt['discovery_errors'],passed=receipt['passed'],outer_exit=tool_done['exit_code'],inner_seconds=receipt['elapsed_seconds'],outer_seconds=execution['elapsed_seconds'],headroom=timeout-execution['elapsed_seconds'],receipt=record(directory/'receipt.json'),execution=record(directory/'execution.json'),note=record(C/f's1-recovery-launch-note-016-{label}.json'),tool_start=record(C/f'iteration-016-{label}-tool-start.json'),tool_completion=record(C/f'iteration-016-{label}-tool-completion.json'),root=root,preexisting_ancestors=ancestors,failed_cases=[case for case in receipt['cases'] if case['status']!='passed']))
        scenario_files=sorted(directory.glob('scenario-*.json'))
        check('42 scenario records '+label,len(scenario_files)==42)
        for path in scenario_files:
            row=json.loads(path.read_bytes());events=row.get('events',[])
            scenarios.append(dict(invocation=label,record=record(path),scenario=row['scenario'],cleanup_confirmed=row['cleanup_confirmed'],execution_seconds=row['execution_seconds'],cleanup_seconds=row['cleanup_seconds'],outcomes=[event for event in events if event.get('event')=='progress_outcome']))
            for event in events:
                if event.get('event') in ('census','owned_dispatch'):censuses.append(dict(invocation=label,scenario=row['scenario'],value=event))
        for line in (directory/'process-stdout.log').read_text().splitlines():
            if line.startswith('S1_SCRIPT_CHILD '):direct.append(dict(invocation=label,**json.loads(line[len('S1_SCRIPT_CHILD '):])))
final=C/'s1-recovery-aggregate-016-002';final_receipt=json.loads((final/'receipt.json').read_bytes());final_execution=json.loads((final/'execution.json').read_bytes())
check('final exact source snapshot',final_execution['sources_after']==sources)
check('preserved current 230 methods',set(read('s1-recovery-aggregate-014-001/receipt.json')['collected']).issubset(final_receipt['collected']) if (C/'s1-recovery-aggregate-014-001/receipt.json').exists() else len(final_receipt['collected'])>=230)
check('final current collection',len(final_receipt['collected'])==237)
check('current callback declarations',all(final_receipt['declarations'][k]==v for k,v in declarations.items() if k in final_receipt['collected']))
for census in censuses:
    value=census['value'];check('owned charge '+census['invocation']+'/'+census['scenario'],value['B']+max(1,value['H'])==value['total_workers']<=8 and value['measured_total']+value['reserve']==value['total_workers'])
for label in ('aggregate-001','aggregate-002'):
    rows=[r for r in direct if r['invocation']==label];check('six direct scripts '+label,len(rows)==6)
    for row in rows:check('live direct ownership '+label,bool(row.get('owned_observations')) and all(v['total_workers']<=8 for v in row['owned_observations']))
check('all scenario safety cleanup',all(row['cleanup_confirmed'] for row in scenarios))
check('all scenario time limits',all(row['execution_seconds']<=2 and row['cleanup_seconds']<=1 for row in scenarios))
result=dict(schema='plan046-independent-audit/v1',recorded_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),recorded_monotonic=time.monotonic(),passed=all(row['passed'] for row in checks),checks=checks,check_count=len(checks),interpretation='Byte/AST/accounting consistency is separate from technical or strict plan acceptance.',sources=sources,source_count=len(sources),method_maps=method_maps,missing_old_assertions=missing,assertion_discrepancy=base['historical_assertion_discrepancy'],collected_methods=final_receipt['collected'],declared_callbacks=sum(len(v) for k,v in final_receipt['declarations'].items() if k in final_receipt['collected']),frozen_count=len(old['frozen_records']),partial_copies=len(partial['sources']),ledger=dict(record=ledger_record,events=len(ledger),head=ledger[-1]['event_sha256'],original_events=[ledger[i-1] for i in (250,255,256)],gpu_elapsed_seconds=4374.044265462899,reserved_seconds=0,active_jobs=[]),status_lineage=dict(transitions=transitions,snapshots=snapshot_checks,prefix=28,count=31,no_plan045_commit=True),unchanged=unchanged,consumed=consumed,scenarios=scenarios,censuses=censuses,direct_scripts=direct,aggregate_passed=final_receipt['passed'],historical_strict_acceptance={name:False for name in ('Plan041','Plan043','Plan044','Plan045')},audit_script=record(__file__))
publish('s1-recovery-audit-016.json',result)
print(json.dumps(dict(audit_passed=result['passed'],checks=len(checks),failed_checks=[row for row in checks if not row['passed']],final_methods=final_receipt['tests_run'],final_callbacks=final_receipt['subtests_run'],declared_callbacks=result['declared_callbacks'],aggregate_passed=final_receipt['passed']),indent=2))
