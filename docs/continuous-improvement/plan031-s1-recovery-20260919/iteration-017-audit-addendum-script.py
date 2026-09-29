import ast,json,hashlib,os,time,datetime
from pathlib import Path
r=Path.cwd();c=r/'docs/continuous-improvement/plan031-s1-recovery-20260919';start=json.loads((c/'iteration-017-timing-start.json').read_text())['monotonic_start']
def rec(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p.resolve()),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def save(n,v):
 p=c/n;b=(json.dumps(v,indent=2,allow_nan=False)+'\n').encode()
 with p.open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
 assert p.read_bytes()==b
 return rec(p)
def copy(src,name):
 p=c/name;b=Path(src).read_bytes()
 with p.open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
 assert p.read_bytes()==b
 return rec(p)
scripts=[copy('/tmp/plan047_handoff.py','iteration-017-audit-script.py'),copy('/tmp/plan047_handoff_addendum.py','iteration-017-audit-addendum-script.py')]
after=json.loads((c/'iteration-017-method-after-map.json').read_text());tree=ast.parse((r/'scripts/vipe_benchmark/s1_validation_contract.py').read_text());suites=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SUITES' for t in n.targets));collected=[]
for suite in suites:
 p=r/'tests'/('test_vipe_benchmark_'+suite+'.py');t=ast.parse(p.read_text())
 for cls in t.body:
  if isinstance(cls,ast.ClassDef) and any(isinstance(b,ast.Attribute) and b.attr=='TestCase' for b in cls.bases):
   for f in cls.body:
    if isinstance(f,ast.FunctionDef) and f.name.startswith('test_'):collected.append(p.stem+'.'+cls.name+'.'+f.name)
assert len(collected)==248
membership=sorted([r/'scripts/basketball_vipe_benchmark.py',r/'scripts/basketball_vipe_worker.py',r/'configs/vipe-alternatives/benchmark-v1.json',*(r/'scripts/vipe_benchmark').glob('*.py'),*(r/'tests').glob('test_vipe_benchmark_*.py')]);sources=[rec(p) for p in membership];assert sources==json.loads((c/'s1-recovery-validation-016.json').read_text())['sources']
records=[];direct=[];maxcpu=0;identities={};traces=[]
def walk(v):
 if isinstance(v,dict):
  yield v
  for child in v.values():yield from walk(child)
 elif isinstance(v,list):
  for child in v:yield from walk(child)
for d in sorted(c.glob('s1-recovery-*-017-00[123]')):
 if not d.is_dir():continue
 for p in sorted(d.glob('scenario-*.json')):
  v=json.loads(p.read_text());out=[e for e in v['events'] if e.get('event')=='progress_outcome'];record=dict(attempt=d.name,source=rec(p),scenario=v['scenario'],cleanup_confirmed=v['cleanup_confirmed'],execution_seconds=v['execution_seconds'],cleanup_seconds=v['cleanup_seconds'])
  if out:
   e=out[-1];record.update(primary=e.get('primary'),primary_observations=e.get('primary_observations'),finish=e.get('finish'),protocol_trace=e.get('protocol_trace'),counts=e['reference']['counts'],fixture_scope=e.get('fixture_scope'),production_cutoff=[x for x in v['events'] if x.get('event')=='plan047_production_cutoff'],safety_retirement=[x for x in v['events'] if x.get('event')=='plan047_safety_retirement']);traces.append(dict(attempt=d.name,scenario=v['scenario'],trace=e.get('protocol_trace')))
  records.append(record)
  for item in walk(v):
   if type(item.get('total_workers')) is int:maxcpu=max(maxcpu,item['total_workers'])
   if type(item.get('pid')) is int and type(item.get('start_ticks')) is int:identities[(item['pid'],item['start_ticks'])]=dict(pid=item['pid'],start_ticks=item['start_ticks'])
 stdout=d/'process-stdout.log'
 if stdout.exists():
  for line in stdout.read_text().splitlines():
   if line.startswith('S1_SCRIPT_CHILD '):
    v=json.loads(line[len('S1_SCRIPT_CHILD '):]);direct.append(dict(attempt=d.name,source=rec(stdout),observation=v))
    for item in walk(v):
     if type(item.get('total_workers')) is int:maxcpu=max(maxcpu,item['total_workers'])
     if type(item.get('pid')) is int and type(item.get('start_ticks')) is int:identities[(item['pid'],item['start_ticks'])]=dict(pid=item['pid'],start_ticks=item['start_ticks'])
survivors=[];readfail=[]
for key,item in identities.items():
 try:
  raw=Path('/proc',str(item['pid']),'stat').read_text();fields=raw[raw.rfind(')')+2:].split()
  if int(fields[19])==item['start_ticks']:survivors.append(dict(**item,state=fields[0],ppid=int(fields[1]),pgid=int(fields[2])))
 except FileNotFoundError:pass
 except OSError as e:readfail.append(dict(identity=item,error=repr(e)))
final=[x for x in records if x['attempt']=='s1-recovery-aggregate-017-002'];fd=[x for x in direct if x['attempt']=='s1-recovery-aggregate-017-002'];assert len(final)==42 and len(fd)==6
add=save('iteration-017-handoff-addendum.json',dict(schema='plan047-handoff-addendum/v1',recorded_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),recorded_monotonic=time.monotonic(),prior_handoff=rec(c/'s1-recovery-handoff-017.json'),prior_completion=rec(c/'iteration-017-completion.json'),audit_scripts=scripts,source_membership=sources,collection=dict(static_suite_order=suites,static_methods=collected,static_method_count=len(collected),literal_callbacks=1012,final_runtime_receipt=None),scenario_records=records,direct_script_records=direct,final_42_cleanup_confirmed=all(x['cleanup_confirmed'] for x in final),final_six_direct_scripts_passed=all(x['observation']['returncode']==0 and not x['observation']['timed_out'] for x in fd),observed_cpu_max=maxcpu,observed_owned_identity_count=len(identities),surviving_recorded_identities=survivors,proc_read_failures=readfail,interpretation='Supplement corrects the earlier primary_present top-level lookup: primary data is nested in progress_outcome events. Static248/1012 is not a passing runtime aggregate.',further_gaps=['P05/P06 still use monitored_call loss paths rather than all six P scenarios traversing actual supervise/finish; their primary_observations/finish may be empty.','P02/P03 trace and authority must be independently reviewed; no broad full loss-path acceptance is inferred.','Observed maximum excludes unknown unrecorded activity; persistent registry implementation is not fully accepted without the missing final tables/receipt.'],aggregate_passed=False,plan_complete=False))
print(json.dumps(dict(addendum=add,final_scenarios=len(final),direct_scripts=len(fd),maxcpu=maxcpu,survivors=survivors,elapsed=time.monotonic()-start),indent=2))
