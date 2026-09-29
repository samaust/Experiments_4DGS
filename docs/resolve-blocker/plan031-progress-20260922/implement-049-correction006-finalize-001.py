"""Standard-library-only source/AST evidence. Does not import project modules."""
import ast,collections,datetime,difflib,hashlib,json,os,pathlib,shutil,subprocess,time
ROOT=pathlib.Path.cwd();R=ROOT/'docs/resolve-blocker/plan031-progress-20260922'
def save(name,value):
    with (R/name).open('x') as stream:json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')
def record(path):
    raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
before=json.loads((R/'implement-049-before-ast-001.json').read_text())
paths=sorted([ROOT/'scripts/basketball_vipe_benchmark.py',ROOT/'scripts/basketball_vipe_worker.py',ROOT/'configs/vipe-alternatives/benchmark-v1.json',*(ROOT/'scripts/vipe_benchmark').glob('*.py'),*(ROOT/'tests').glob('test_vipe_benchmark_*.py')])
assert [str(p) for p in paths]==[r['path'] for r in before['source_records']]
records=[];methods={};decl={};syntax=[];collected=[];trees={};diff=[];changed=[]
snapshot=R/'implement-049-correction006-source-after-001';snapshot.mkdir()
oldroot=R/'implement-048-correction-source-after-002'
for path in paths:
    rel=path.relative_to(ROOT);raw=path.read_bytes();rec=record(path);records.append(rec)
    target=snapshot/rel;target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as stream:stream.write(raw)
    old=next(r for r in before['source_records'] if r['path']==str(path))
    if rec!=old:
        changed.append(dict(path=str(rel),before=old,after=rec))
        previous=(oldroot/rel).read_bytes();assert hashlib.sha256(previous).hexdigest()==old['sha256']
        diff.extend(difflib.unified_diff(previous.decode().splitlines(True),raw.decode().splitlines(True),fromfile='before/'+str(rel),tofile='after/'+str(rel)))
    if path.suffix!='.py':continue
    tree=ast.parse(raw,filename=str(path));trees[str(rel)]=tree
    if path.name.startswith('test_vipe_benchmark'):
        for node in tree.body:
            if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SUBTEST_CASES' for t in node.targets):decl.update(ast.literal_eval(node.value))
            if not isinstance(node,ast.ClassDef):continue
            for fn in node.body:
                if not isinstance(fn,(ast.FunctionDef,ast.AsyncFunctionDef)):continue
                key=path.stem+'.'+node.name+'.'+fn.name
                assertions=[ast.dump(n,include_attributes=False) for n in sorted((n for n in ast.walk(fn) if (isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and (n.func.attr.startswith('assert') or n.func.attr=='fail')) or isinstance(n,ast.Assert)),key=lambda n:(n.lineno,n.col_offset))]
                methods[key]=dict(ast=ast.dump(fn,include_attributes=False),assertions=assertions,line=fn.lineno,source=str(path))
SUITES=('s1_semantics','s1_recovery','backends','contracts','component_recovery','execution','budgets','supervisor','review_annotations')
for suite in SUITES:
    tree=trees['tests/test_vipe_benchmark_'+suite+'.py']
    for cls in sorted((n for n in tree.body if isinstance(n,ast.ClassDef)),key=lambda n:n.name):
        for fn in sorted((n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')),key=lambda n:n.name):collected.append('test_vipe_benchmark_'+suite+'.'+cls.name+'.'+fn.name)
callbacks=[]
for method in collected:
    for case in decl.get(method,[]):callbacks.append(method+'::'+json.dumps([(key,type(value).__name__,value) for key,value in sorted(case.items())],separators=(',',':'),allow_nan=False))
assert collected==before['collected'] and callbacks==before['callbacks'] and decl==before['declarations']
missing=[];additions={};removed_methods=[]
for key,old in before['methods'].items():
    if key not in methods:removed_methods.append(key);continue
    remaining=methods[key]['assertions'];cursor=0
    for assertion in old['assertions']:
        try:cursor=remaining.index(assertion,cursor)+1
        except ValueError:missing.append(dict(method=key,assertion=assertion))
    extra=collections.Counter(remaining)-collections.Counter(old['assertions'])
    if extra:additions[key]=dict(extra)
assert not removed_methods
assert len(missing)==1 and missing[0]['method'].endswith('ReservationClockTests.test_identical_reuse_and_conflicts') and "Constant(value='unverified')" in missing[0]['assertion']
allowed={'scripts/vipe_benchmark/'+name+'.py' for name in ('backends','s1_progress','s1_evidence','stages','s1_recovery','s1_cpu_helper','s1_helper_session','supervisor','s1_validation_capture','s1_validation_contract')}|{'tests/test_vipe_benchmark_'+name+'.py' for name in ('supervisor','s1_helper_fixtures','s1_recovery')}|{'scripts/basketball_vipe_worker.py'}
assert all(row['path'] in allowed for row in changed)
with (R/'implement-049-correction006-source-diff-001.patch').open('x') as stream:stream.writelines(diff)
check=subprocess.run(['git','diff','--check','--',*sorted(allowed)],capture_output=True,text=True,check=False)
assert check.returncode==0
save('implement-049-correction006-after-ast-001.json',dict(schema='plan049-stdlib-source-ast/v1',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),monotonic=time.monotonic(),source_records=records,methods=methods,collected=collected,declarations=decl,callbacks=callbacks,syntax_errors=syntax,cpu_bound='B+max(1,H)≤8'))
save('implement-049-correction006-preservation-001.json',dict(before=record(R/'implement-049-before-ast-001.json'),after=record(R/'implement-049-correction006-after-ast-001.json'),source_members=78,collected_methods=len(collected),typed_callbacks=len(callbacks),old_methods_preserved=len(before['methods']),removed_methods=removed_methods,ordered_old_assertion_differences=missing,authorized_difference='D49-1 only; prior correction001 already absent from baseline',added_assertions=additions,declarations_exact=True,six_migrations_unchanged=True,changed_sources=changed,frozen_sources_unchanged=True,diff_check=dict(command=check.args,returncode=check.returncode,stdout=check.stdout,stderr=check.stderr)))
timers=[]
for rel,tree in trees.items():
    if rel not in allowed:continue
    for node in ast.walk(tree):
        if isinstance(node,ast.Call):
            keys=[k.arg for k in node.keywords if k.arg and any(w in k.arg for w in ('timeout','deadline','seconds','duration'))]
            text=ast.unparse(node)
            if keys or any(w in text for w in ('work_deadline','total_deadline','fixture_safety_end','fixture_action_end')):
                category='behavioral original W/C/protocol/scenario bound'
                if 's1_validation_capture' in rel or 's1_validation_contract' in rel:category='legacy timed branch preserved or explicit null no-timeout mode'
                if 'p.wait(timeout=10)' in text:category='retrospective completed-process assertion; preceding actual waits unbounded'
                timers.append(dict(path=rel,line=node.lineno,expression=text,category=category))
save('implement-049-correction006-timer-inventory-after-001.json',dict(before=record(R/'implement-049-timer-inventory-before-001.json'),entries=timers,operational_limits=None,removed_execution_only=['direct six-script communicate10/forced2','generic helper subprocess5','race actual completion10'],retained='original W/C, equality-is-late, 2s action/1s retirement, setup/census/request/ack/native timing assertions',legacy_timed_capture_retained=True))
print(json.dumps(dict(changed=[r['path'] for r in changed],methods=len(collected),callbacks=len(callbacks),assertion_differences=len(missing))))
