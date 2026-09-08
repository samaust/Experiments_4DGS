import ast, decimal, hashlib, json, math, os, re, struct, time
from pathlib import Path
from fractions import Fraction
root=Path('docs/experiments/basketball-shared-timing-v13')
def read(p):return json.loads(Path(p).read_text())
def sha(p):
 p=Path(p);assert 'prompts' not in p.parts;return hashlib.sha256(p.read_bytes()).hexdigest()
def checks(mapping):
 for p,h in mapping.items():assert sha(p)==h,(p,h)
auth=read('docs/continuous-improvement/20260908-plan016/iteration-004-plan020-authorization.json')
ad=read(root/'admission.json');ready=read(root/'readiness.json');start=read(root/'started.json');budget=read(root/'budget.json')
checks(ad['predecessor_sha256']);checks(ready['sha256']);checks(read(root/'execution-sources.json')['sha256'])
assert ad['admitted_monotonic']<auth['deadlines']['admission']['monotonic']
assert ready['ready_monotonic']<auth['deadlines']['implementation_ready']['monotonic']
assert budget['end_monotonic']<=auth['deadlines']['numerical_end']['monotonic']
assert budget['end_monotonic']<=start['deadline_monotonic']<=start['start_monotonic']+120
assert budget['worker_stopped'] and budget['exit_code']==0 and budget['counts']==dict(setup_entry=1,setup_return=1,entry=6,completed=6)
assert len(list(root.glob('toy-suite-??-entry.json')))==len(list(root.glob('toy-suite-??-result.json')))==2
for i in (1,2):
 a=read(root/('toy-suite-%02d-entry.json'%i));b=read(root/('toy-suite-%02d-result.json'%i))
 assert a['source_sha256']==b['source_sha256'] and a['entry_monotonic']==b['entry_monotonic']<b['return_monotonic']<ready['ready_monotonic']
 assert b['passed'] and b['cases']==12 and b['errors']==b['failures']==0
assert read(root/'toy-freeze.json')['test_sha256']==sha('tests/test_basketball_acceleration_candidate_v13.py')
assert read(root/'toy-suite-02-result.json')['source_sha256']=={p:sha(p) for p in read(root/'toy-suite-02-result.json')['source_sha256']}
entries=[json.loads(l) for l in (root/'entries.jsonl').read_text().splitlines()]
assert [e['event'] for e in entries]==['setup_entry','setup_return']+['entry','completed']*6
assert read(root/'setup-consumed.json')['monotonic']<=entries[0]['monotonic']
identity=read(root/'worker-identity.json');process=read(root/'processes.json');consumed=read(root/'worker-consumed.json')
assert identity['pid']==identity['pgid']==identity['sid']==process['child_pid']==process['child_pgid']==process['child_sid']==budget['child_pid']==consumed['pid']
assert identity['pid_namespace']==process['child_pid_namespace']
assert all(e['pid']==identity['pid'] and e['pgid']==identity['pgid'] for e in entries)
assert start['supervisor_identity']==process['supervisor'] and consumed['monotonic']>=start['start_monotonic']
setup=read(root/'setup.json');inp=read(root/'inputs.json')
assert setup['n']==18 and len(setup['spans'])==150 and len(setup['alpha'])==17 and len(setup['beta'])==16
assert setup['knots_hex']==inp['knots_hex'] and setup['quadrature_hex']==inp['quadrature_hex']
contexts=[setup['context']]
for i in range(6):
 d=read(root/('candidate-'+str(i)+'.json'));contexts.append(d['context'])
 for terms in d['signed_contributions']:
  assert len(terms)==150 and all(decimal.Decimal(t).is_finite() for t in terms)
 for v in [d['cost'],*d['gradient']]:
  val=decimal.Decimal(v['decimal']);t=val.as_tuple();assert val.is_finite()
  assert [t.sign,list(t.digits),t.exponent]==v['tuple']
  assert struct.pack('<d',v['value']).hex()==v['hex']==struct.pack('<d',float(val)).hex()
for c in contexts:
 assert (c['prec'],c['rounding'],c['Emin'],c['Emax'],c['capitals'],c['clamp'])==(80,'ROUND_HALF_EVEN',-999999,999999,1,0)
 assert {k for k,v in c['traps'].items() if v}=={'InvalidOperation','DivisionByZero','Overflow','Underflow','FloatOperation'}
 assert not any(v for k,v in c['flags'].items() if k not in {'Inexact','Rounded'})
comparison=read(root/'comparisons.json');assert comparison['passed']==42 and comparison['failed']==0
for state in comparison['states']:
 for c in state['checks']:
  v=struct.unpack('<d',bytes.fromhex(c['value_hex']))[0];allowed=struct.unpack('<d',bytes.fromhex(c['allowed_hex']))[0]
  g=Fraction(*map(int,c['oracle']));err=Fraction(*map(int,c['forward_error']));bound=Fraction(*map(int,c['allowed_error']))
  assert abs(Fraction.from_float(v)-g)==err and Fraction.from_float(allowed)==bound and err<=bound and c['passed']
for p in [Path('scripts/basketball_acceleration_decimal_v13.py'),Path('scripts/basketball_acceleration_candidate_v13.py'),Path('tests/test_basketball_acceleration_candidate_v13.py')]:ast.parse(p.read_text())
files={str(p):sha(p) for p in sorted(root.iterdir()) if p.is_file()}
report=dict(passed=True,retained_only=True,scientific_recomputation=0,json_files_parsed=sum(p.suffix=='.json' for p in root.iterdir()),sha256=files,source_snapshot_verified=True,deadlines_and_entries_verified=True,contexts_and_serialization_verified=True,worker_session_reaped=True,phase_elapsed_seconds=time.monotonic()-auth['t0_monotonic'])
with (root/'retained-integrity.json').open('x') as f:json.dump(report,f,sort_keys=True,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
print(json.dumps({k:v for k,v in report.items() if k!='sha256'}))
