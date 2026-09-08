#!/usr/bin/env python3
"""Plan022 immutable admission, one owned pass, and retained-only packaging."""
import argparse
import ast
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import struct
import subprocess
import sys
import time

ROOT=Path('docs/experiments/basketball-shared-timing-v15')
AUTH=Path('docs/continuous-improvement/20260908-plan016/iteration-006-plan022-authorization.json')
SCRIPT=Path('scripts/basketball_shared_evaluator_v15.py')
TEST=Path('tests/test_basketball_shared_evaluator_v15.py')
PYTHON='.local/envs/calibration-global/bin/python'
THREADS={k:'1' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')}
SOURCES=[Path('scripts')/(s+'_v15.py') for s in ('basketball_acceleration_decimal','basketball_shared_components','basketball_shared_accounting','basketball_shared_solver','basketball_shared_reference','basketball_shared_evaluator')]
GATES=dict(accepted_timing=None,production_candidate=None,final_validation_protocol=None,ready_for_full_screens=False,main_objective_attained=False)
ORDERS=[['O','G','H','C','CH','R'],['G','O','H','C','CH','R'],['H','O','G','C','CH','R'],['C','O','G','H','CH','R'],['O','G','H','C','CH','R']]

def encode(v):return (json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def read(p):
 p=Path(p);b=p.read_bytes();return json.loads(gzip.decompress(b) if p.suffix=='.gz' else b)
def sha(p):
 p=Path(p)
 if 'prompts' in p.parts:raise ValueError('excluded path')
 return hashlib.sha256(p.read_bytes()).hexdigest()
def publish(p,v):
 p=Path(p);b=encode(v)
 if p.suffix=='.gz':b=gzip.compress(b,mtime=0)
 with p.open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
 return sha(p)
def event(p,**v):
 v.update(monotonic=time.monotonic(),pid=os.getpid(),pgid=os.getpgrp())
 with Path(p).open('ab') as f:f.write(encode(v));f.flush();os.fsync(f.fileno())
def hashes(m):
 for p,h in m.items():
  if sha(p)!=h:raise ValueError('source mutation '+p)
def fhex(v):return struct.pack('<'+'d'*len(v),*v).hex()
def raw(h,n):
 b=bytes.fromhex(h)
 if len(b)!=n*8 or not all(map(math.isfinite,struct.unpack('<'+'d'*n,b))):raise ValueError('binary64 shape/finite')
 return b
def deadline(key):
 if time.monotonic()>=read(AUTH)['deadlines'][key]['monotonic']:raise TimeoutError(key+' deadline')
def journal(p):
 prev='0'*64;out=[]
 for line in Path(p).read_bytes().splitlines(keepends=True):
  assert line.endswith(b'\n');e=json.loads(line);h=e.pop('checksum')
  assert e['seq']==len(out) and e['previous']==prev and hashlib.sha256(encode(e).rstrip(b'\n')).hexdigest()==h
  e['checksum']=h;out.append(e);prev=h
 return out

def admit():
 deadline('admission')
 previous=Path('docs/experiments/basketball-shared-timing-v14')
 assert sha(previous/'admission.json')=='7f294998d9ee7f12448740710bd7951ec503f111297a96582024f843e240611c'
 for side in ('candidate-inputs','reference-inputs'):
  assert sha(previous/side/'inputs.json')=='1b4779b8c0328f9f893af6c2cd1b2fa9133bdad337467a2f805525d8913c1eed'
 if ROOT.exists():raise FileExistsError('output collision')
 old=Path('docs/experiments/basketball-shared-timing-v11');prev=Path('docs/experiments/basketball-shared-timing-v13')
 assert sha(old/'inputs.json')=='7a4b5aebeb5652051298ab88103a44af63a13ed69163eda988b333169cdf11f0'
 assert sha(prev/'inputs.json')=='5cdc33308ad68dacd70522ab423286b42f060c53c02343e90b05a377a75034fc'
 v11=read(old/'inputs.json');v13=read(prev/'inputs.json');historic=dict(v11['historical_sha256']);hashes(historic)
 v11src=read(old/'execution-sources.json')['sha256'];hashes(v11src)
 pinned={str(old/'inputs.json'):sha(old/'inputs.json'),str(prev/'inputs.json'):sha(prev/'inputs.json')}
 for version in ('v12','v13'):
  d=Path('docs/experiments/basketball-shared-timing-'+version)
  for name in ('admission.json','inputs.json','execution-sources.json','readiness.json','decision.json','package-validation.json','budget.json'):
   pinned[str(d/name)]=sha(d/name)
  ad=read(d/'admission.json')
  for name in ('pinned_sha256','predecessor_sha256'):
   hashes(ad.get(name,{}));pinned.update(ad.get(name,{}))
  hashes(read(d/'execution-sources.json')['sha256'])
  assert read(d/'package-validation.json')['passed']
 assert read('docs/experiments/basketball-shared-timing-v12/inputs.json')['knots_hex']==v13['knots_hex']
 review=Path('docs/continuous-improvement/20260908-plan016/iteration-005-recommendations.md').read_text()
 import re
 returned_pins=dict(re.findall(r'\| (baseline/conditional-\d+/cold|metric/conditional-\d+/cold|metric/joint-\d+/\w+) \| [01] \| `([0-9a-f]{64})`',review))
 joint_pins=dict(re.findall(r'\| (joint-\d+/\w+/attempt.json.gz) \| `([0-9a-f]{64})`',review))
 cold_cond=['849b99238f58dceb28465f58905c35f4bba1c1ba0b43dc794c92ad6967ba4e9d','7623d26719bcc2e67ae62e0f27e220458099249b45f7feafe1e5d29f6f054b57','39df69e0ce47977ace256d87704492edcf8a62a4355c3660a410bba5b3192be2']
 cold_joint=['82daae22162a53c414a840902052562517bc960bbaa9d99b33a31e001d00805d','f0b5078087e21a08d5e06f05a2bb19b56ef41ac43df509298d64fa688b37a789','42e19435abf7d0798143d24ea883cf7b1cdf8d5cf4ae9ccca9ca4d42aa85507b','f7da9896e5af60d6447a54a6611a240d15ad15c15c9e5f692c0be57ab7cb733a']
 cases=[];archive=[];provenance=[]
 directories=[c['directory'] for c in v11['cases']]+['docs/experiments/basketball-shared-timing-v10/adapt/metric/'+s.rsplit('/',1)[0] for s in joint_pins]
 assert len(directories)==16 and len(returned_pins)==16
 def bind(p):p=str(p);pinned[p]=sha(p);return read(p)
 for i,directory in enumerate(directories):
  deadline('admission');d=Path(directory);item=bind(d/'attempt.json.gz');rec=bind(d/'receipt.json');pinned[str(d/'journal.jsonl')]=sha(d/'journal.jsonl');events=journal(d/'journal.jsonl')
  r=item['row'];a=r['accounting'];p=a['problem'];ident=item['identity'];key=hashlib.sha256(json.dumps(p,sort_keys=True).encode()).hexdigest()
  caseid=v11['cases'][i]['id'] if i<12 else 'metric/'+str(d.relative_to('docs/experiments/basketball-shared-timing-v10/adapt/metric'))
  if i>=12:assert sha(d/'attempt.json.gz')==joint_pins[str(d.relative_to('docs/experiments/basketball-shared-timing-v10/adapt/metric'))+'/attempt.json.gz']
  assert key==a['problem_key'] and p['provenance']==ident and p['namespace']==ident['namespace']
  assert item['id']==ident['attempt_id']==rec['id'] and item['reference']==ident['reference']
  assert [e['identity'] for e in events if e['event']=='allocated']==[ident]
  completion=[e for e in events if e['event']=='completed'];assert len(completion)==1
  assert completion[0]['artifact_sha256']==rec['artifact_sha256']==sha(d/'attempt.json.gz') and completion[0]['receipt_sha256']==sha(d/'receipt.json') and rec['verification']['passed']
  assert ident['allocation'] is None and ident['run_id']=='basketball-shared-v10-1788843120'
  for field in ('manifest','policy_file'):
   bind(ident[field]);assert pinned[ident[field]]==ident['manifest_sha256' if field=='manifest' else 'policy_sha256']
  hashes(ident['execution_sha256']);historic.update(ident['execution_sha256'])
  dep=ident['dependency_provenance'];assert r['seed']==dep
  if dep:
   src=bind(dep['artifact']);assert sha(dep['artifact'])==dep['artifact_sha256'] and src['row']['returned_state']==dep['state'] and src['id']==dep['id']
  states={s['identity']:s for s in a['states']};assert len(states)==a['distinct_states']<=200
  js=[{k:e[k] for k in ('identity','scope','canonical_hex','physical_hex')} for e in events if e['event']=='state'];assert js==a['states']
  for s in states.values():assert hashlib.sha256(key.encode()+s['scope'].encode()+bytes.fromhex(s['canonical_hex'])).hexdigest()==s['identity']
  last=next(e for e in reversed(events) if e['event'] in ('problem','transform'));assert last['transform_hex']==a['transform_hex'] and last['origin_hex']==a['origin_hex']
  entered=[e for e in events if e['event']=='numerical_entry'];done=[e for e in events if e['event']=='numerical_return'];assert len(entered)==len(done)==len(a['entries'])==len(a['observed_numerical_entries'])
  for e,z,o in zip(entered,a['entries'],a['observed_numerical_entries']):assert e['state']==z['state'] and e['physical_hex']==o['physical_hex']==states[e['state']]['physical_hex'] and e['kind']==z['kind']==o['kind'] and z['status']==o['status']=='completed'
  n=54 if i<12 else 55;assert p['free']==([] if i<12 else [3])
  assert p['window']==r['window']==[50,149] and p['spacing']==r['spacing']==10 and p['weight']==r['weight'] in (0,1)
  assert p['gauge']==1 and p['role']=='synthetic-fit-50-149' and len(p['observations'])==1 and r['group_ids']==[p['observations'][0]['group_id']]
  obs=p['observations'][0]['observations'];assert [o['camera_id'] for o in obs]==[1,2,3] and all(o['frames']==list(range(50,150)) and len(o['xy'])==100 for o in obs)
  assert fhex(r['knots'])==v13['knots_hex'] and v13['samples']==150 and v13['window']==[50,149] and v13['spacing']==10
  cold_events=[e for e in a['events'] if e['kind']=='cold_transform'];assert len(cold_events)==1
  cold=states[cold_events[0]['state']];ret=states[r['returned_state']];trace=r['solver_trace'][-1]
  assert trace['state']==r['returned_state'] and fhex(trace['q'])==fhex(r['canonical_q'])==ret['canonical_hex'] and fhex(trace['x'])==fhex(r['x'])==ret['physical_hex']
  assert fhex(trace['multipliers'][0])==fhex(r['multipliers_transformed'])
  if i<12:
   selected=v11['cases'][i]['selected'][-1];assert selected['callback']==trace and selected['state']==ret
  cp=cold_cond[i%3] if i<12 else cold_joint[i-12]
  for field in ('canonical_hex','physical_hex'):assert hashlib.sha256(raw(cold[field],n)).hexdigest()==cp
  assert hashlib.sha256(raw(ret['physical_hex'],n)).hexdigest()==returned_pins[caseid]
  raw(a['transform_hex'],n*n);raw(a['origin_hex'],n);raw(a['scale_hex'],n)
  assert a['scale_hex']==fhex(([25.] if i>=12 else [])+[1.]*54)
  slots=[]
  for label,s in [('cold',cold),('returned',ret)]:
   vg=[1.]*300 if label=='cold' else trace['multipliers'][0];vby=None if label=='cold' else trace['multipliers'][1]
   slots.append(dict(label=label,ledger_identity=s['identity'],scope=s['scope'],q_hex=s['canonical_hex'],x_hex=s['physical_hex'],q_sha256=hashlib.sha256(raw(s['canonical_hex'],n)).hexdigest(),x_sha256=hashlib.sha256(raw(s['physical_hex'],n)).hexdigest(),vg_hex=fhex(vg),vby_hex=None if vby is None else fhex(vby),y_hex=None if label=='cold' else fhex(trace['y']),multipliers_role='synthetic derivative-only ones; no cold KKT' if label=='cold' else 'actual last callback'))
  cases.append(dict(index=i,id=caseid,group=r['group_ids'][0],weight=int(r['weight']),dimension=n,problem={k:v for k,v in p.items() if k not in ('provenance','namespace')},knots_hex=v13['knots_hex'],quadrature_hex=v13['quadrature_hex'],center=r['center'],diameter=r['diameter'],n=300,nacc=150,P_hex=a['transform_hex'],origin_hex=a['origin_hex'],scale_hex=a['scale_hex'],slots=slots))
  archive.append(dict(id=caseid,row={k:r[k] for k in ('objective','G','C_depth','C_bounds','KKT','optimality','complementarity_original','multipliers_depth','bound_multipliers')},qualified=r['valid']))
  provenance.append(dict(id=caseid,identity=ident,problem_key=key,directory=directory,cold_event=cold_events[0],returned_state=r['returned_state'],callback_ordinal=len(r['solver_trace'])-1))
 assert sum(c['weight'] for c in cases)==7
 # Bind installed code without importing numerical packages. Include Python, all
 # NumPy/SciPy source/extensions, bundled libraries and the stdlib implementation.
 environment={}
 for base in (Path(PYTHON).resolve(),Path('.local/envs/calibration-global/lib/python3.14/site-packages')):
  paths=[base] if base.is_file() else [p for p in base.rglob('*') if p.is_file() and (p.parts[len(base.parts)].startswith(('numpy','scipy')) and p.suffix not in ('.pyc',))]
  for p in paths:environment[str(p)]=sha(p)
 import sysconfig
 lib=Path(sysconfig.get_path('stdlib'))
 for p in lib.rglob('*'):
  if 'site-packages' in p.parts or not p.is_file() or p.suffix not in ('.py','.so'):continue
  environment[str(p)]=sha(p)
 ROOT.mkdir();(ROOT/'candidate-inputs').mkdir();(ROOT/'reference-inputs').mkdir()
 inputs=dict(cases=cases,synthetic_origin='v10 synthetic benchmark original observations; not reconstruction evidence')
 for name in ('candidate-inputs','reference-inputs'):publish(ROOT/name/'inputs.json',inputs)
 for side in ('candidate-inputs','reference-inputs'):
  assert sha(ROOT/side/'inputs.json')==sha(previous/side/'inputs.json')
 publish(ROOT/'archive.json',archive);publish(ROOT/'provenance.json',provenance)
 publish(ROOT/'historical-sources.json',dict(historical=historic,v11=v11src,substitutions=[dict(path=p,old_sha256=h,replacement_sha256=v11src[p],attestation=str(old/'execution-sources.json')) for p,h in historic.items() if p in v11src and h!=v11src[p]],pinned=pinned))
 publish(ROOT/'environment.json',environment)
 (ROOT/'admission-source.py').write_bytes(SCRIPT.read_bytes())
 deadline('admission')
 publish(ROOT/'admission.json',dict(passed=True,cases=16,slots=32,scientific_entries=0,admitted_monotonic=time.monotonic(),authorization_sha256=sha(AUTH),source_sha256=sha(ROOT/'admission-source.py'),inputs_sha256={name:sha(ROOT/name/'inputs.json') for name in ('candidate-inputs','reference-inputs')},environment_sha256=sha(ROOT/'environment.json'),historical_sha256=sha(ROOT/'historical-sources.json'),provenance_sha256=sha(ROOT/'provenance.json')))
 publish(ROOT/'admission-chain.json',dict(authorization_path=str(AUTH),authorization_sha256=sha(AUTH),plan_sha256=sha('plans/plan_022.md'),objective_sha256=sha('docs/continuous-improvement/20260908-plan016/objective.md'),leaves={str(p):sha(p) for p in [ROOT/'admission.json',ROOT/'admission-source.py',ROOT/'archive.json',ROOT/'provenance.json',ROOT/'historical-sources.json',ROOT/'environment.json',ROOT/'candidate-inputs/inputs.json',ROOT/'reference-inputs/inputs.json',previous/'admission.json',previous/'candidate-inputs/inputs.json',previous/'reference-inputs/inputs.json']}))
 print('Admission passed: 16 cases, 32 immutable states; zero scientific entries.',flush=True)


def plain(v):
 from collections.abc import Mapping
 if isinstance(v,Mapping):return {k:plain(x) for k,x in v.items()}
 if isinstance(v,(list,tuple)):return [plain(x) for x in v]
 if hasattr(v,'tolist'):return plain(v.tolist())
 return v

def process_identity():
 return dict(pid=os.getpid(),pgid=os.getpgrp(),sid=os.getsid(0),pid_namespace=os.readlink('/proc/self/ns/pid'),namespace_status=[l for l in Path('/proc/self/status').read_text().splitlines() if l.startswith(('NSpid:','NSpgid:','NSsid:'))])

def supervise(command,end,log,identity_path=None,interrupt_after=None,reserve=5):
 begin=time.monotonic();p=None;reason=None;termination=None
 def interrupted(s,f):raise KeyboardInterrupt('signal '+str(s))
 handlers={s:signal.signal(s,interrupted) for s in (signal.SIGINT,signal.SIGTERM)}
 try:
  with Path(log).open('xb') as stream:
   p=subprocess.Popen(command,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True,env={**os.environ,**THREADS})
   ident=dict(supervisor=process_identity(),child_pid=p.pid,child_pgid=os.getpgid(p.pid),child_sid=os.getsid(p.pid),child_pid_namespace=os.readlink('/proc/'+str(p.pid)+'/ns/pid'),command=command)
   if identity_path:publish(identity_path,ident)
   while p.poll() is None:
    now=time.monotonic()
    if now>=end-reserve:reason='deadline';break
    if interrupt_after is not None and now-begin>=interrupt_after:reason='interrupted';break
    time.sleep(.02)
 except BaseException as e:reason=type(e).__name__+': '+str(e)
 finally:
  if p is not None:
   # Kill the entire owned group even if the leader already exited.
   termination=time.monotonic()
   try:os.killpg(p.pid,signal.SIGTERM)
   except ProcessLookupError:pass
   try:p.wait(timeout=min(1,max(.01,end-time.monotonic()-.2)))
   except subprocess.TimeoutExpired:
    try:os.killpg(p.pid,signal.SIGKILL)
    except ProcessLookupError:pass
    p.wait(timeout=max(.01,end-time.monotonic()))
   try:os.killpg(p.pid,signal.SIGKILL)
   except ProcessLookupError:pass
  for s,h in handlers.items():signal.signal(s,h)
 finish=time.monotonic();remaining=[]
 if p:
  for entry in Path('/proc').iterdir():
   if not entry.name.isdigit():continue
   try:
    status=(entry/'stat').read_text().rsplit(')',1)[1].split()
    if int(status[2])==p.pid and status[0]!='Z':remaining.append(int(entry.name))
   except (FileNotFoundError,ProcessLookupError):pass
 return dict(start_monotonic=begin,end_monotonic=finish,wall_seconds=finish-begin,deadline_monotonic=end,exit_code=None if p is None else p.returncode,reason=reason,worker_stopped=p is not None and p.poll() is not None,child_pid=None if p is None else p.pid,remaining_live_descendants=remaining,cleanup_seconds=0 if termination is None else finish-termination,within_deadline=finish<=end)

def worker_guard(started,token,parent_pid,path):
 if not token or token!=started.get('token') or parent_pid!=started.get('supervisor_pid') or os.getsid(0)!=os.getpid() or os.getpgrp()!=os.getpid():raise ValueError('direct worker rejected')
 publish(path,dict(consumed=True,identity=process_identity(),monotonic=time.monotonic()))


def ready():
 deadline('readiness');ad=read(ROOT/'admission.json');assert ad['passed'] and ad['authorization_sha256']==sha(AUTH)
 coverage=read(ROOT/'readiness-coverage.json')
 if not coverage['passed']:
  publish(ROOT/'readiness-status.json',dict(passed=False,status='incomplete',reason=coverage['missing'],scientific_entry_prohibited=True,monotonic=time.monotonic()))
  print('Readiness incomplete: frozen suite lacks required assertions; science prohibited.',flush=True)
  return
 for name,h in ad['inputs_sha256'].items():assert sha(ROOT/name/'inputs.json')==h
 suites=[read(p) for p in sorted(ROOT.glob('toy-suite-??-result.json'))]
 assert 1<=len(suites)<=2 and suites[-1]['passed'] and len(suites[-1]['cases'])==20
 new={str(p):sha(p) for p in SOURCES+[TEST]};assert suites[-1]['source_sha256']==new
 assert not any(n.module and 'v14' in n.module for n in ast.walk(ast.parse(Path('scripts/basketball_shared_reference_v15.py').read_text())) if isinstance(n,ast.ImportFrom))
 # Resolve direct math imports: NumPy/SciPy environment is fully byte-pinned;
 # all local v14 imports are in new. No historical numerical import is allowed.
 imports={}
 for p in SOURCES+[TEST]:
  names=[]
  for n in ast.walk(ast.parse(p.read_text())):
   if isinstance(n,ast.Import):names += [x.name for x in n.names]
   elif isinstance(n,ast.ImportFrom) and n.module:names.append(n.module)
  imports[str(p)]=names
  for name in names:
   if name.startswith('basketball_'):assert Path('scripts/'+name+'.py') in SOURCES
 hashes(read(ROOT/'environment.json'))
 publish(ROOT/'execution-sources.json',dict(sha256=new,imports=imports,environment_manifest_sha256=sha(ROOT/'environment.json'),threads=THREADS))
 publish(ROOT/'readiness.json',dict(passed=True,ready_monotonic=time.monotonic(),sha256=new,toy_suite=suites[-1]['slot'],admission_sha256=sha(ROOT/'admission.json'),source_inspection='no mathematical candidate import in reference; all 6 surfaces present; direct-worker guard before numerical import; fixed entry ceilings'))
 print('Readiness passed: frozen 20 cases and all evaluator surfaces.',flush=True)


CAPS=dict(setup=2,complete=96,transform_context=16,prepare=112,objective_residual=96,residual_only=16,data_hessian=96,full_sum=96,raw_depth=96,bounded_values=96,weighted_raw_hessian=96,bounded_curvature=96,report=80,cold_report=16,svd_transform=16,saved_inverse=80,public_probe=80,extra_transport=16,acceleration=49)
REFCAPS={**CAPS,'complete':32,'prepare':32,'objective_residual':32,'data_hessian':32,'full_sum':32,'raw_depth':32,'bounded_values':32,'weighted_raw_hessian':32,'bounded_curvature':32,'report':16,'saved_inverse':16,'acceleration':14,'cold_report':16,'transform_context':0,'residual_only':0,'svd_transform':0,'public_probe':0,'extra_transport':0}


class Audit:
 def __init__(self,method,end,source_map,path=None):
  self.method=method;self.end=end;self.sources=source_map;self.path=path;self.counts={};self.context=None;self.used=set();self.records=[];self.ordinal=0
 def check(self):
  if time.monotonic()>=self.end:raise TimeoutError('numerical deadline')
 def context_set(self,name,state):self.context=(name,state);self.ordinal=0
 def __call__(self,kind,fn):
  self.check();hashes(self.sources)
  if self.context is None:raise ValueError('no context')
  name,state=self.context;key=(name,kind)
  if key in self.used:raise ValueError('duplicate immutable component')
  cap=(CAPS if self.method=='candidate' else REFCAPS).get(kind,0)
  if self.counts.get(kind,0)>=cap:raise ValueError('unallocated entry '+kind)
  self.used.add(key);self.counts[kind]=self.counts.get(kind,0)+1;self.ordinal+=1
  e=dict(method=self.method,context=name,kind=kind,ordinal=self.ordinal,q_hex=state.get('q_hex'),x_hex=state.get('x_hex'),vg_hex=state.get('vg_hex'),vby_hex=state.get('vby_hex'),source_sha256=self.sources,status='entered',start_monotonic=time.monotonic());self.records.append(e)
  if self.path:event(self.path,event='entry',**e)
  # This distinct record is emitted at the actual calculator boundary before fn.
  if kind not in ('prepare','objective_residual','residual_only','acceleration','data_hessian','full_sum','raw_depth','bounded_values','weighted_raw_hessian','bounded_curvature'):
   self.observe(kind,state,lambda:None)
  try:v=fn();self.check()
  except BaseException as exc:
   e.update(status='interrupted',error=type(exc).__name__+': '+str(exc),end_monotonic=time.monotonic())
   if self.path:event(self.path,event='interrupted',**e)
   raise
  e.update(status='completed',end_monotonic=time.monotonic())
  if self.path:event(self.path,event='completed',**e)
  return v

 def observe(self,kind,actual,fn):
  self.check();name,expected=self.context
  for key in ('q_hex','x_hex','vg_hex','vby_hex'):
   if actual.get(key)!=expected.get(key):raise ValueError('actual calculator operand mismatch '+key)
  record=dict(method=self.method,context=name,kind=kind,ordinal=self.ordinal,q_hex=actual.get('q_hex'),x_hex=actual.get('x_hex'),vg_hex=actual.get('vg_hex'),vby_hex=actual.get('vby_hex'),source_sha256=self.sources,status='entered')
  if self.path:event(self.path.with_name('actual-entries.jsonl'),event='actual_entry',**record)
  return fn()


def compare_arrays(candidate,reference,atol,rtol,rational_values=None):
 import numpy as np
 from fractions import Fraction
 a=np.asarray(candidate,dtype='<f8');b=np.asarray(reference,dtype='<f8')
 if a.shape!=b.shape:return dict(passed=False,shape_mismatch=[a.shape,b.shape])
 failed=[];records=[]
 for index in np.ndindex(a.shape):
  v=float(a[index]);r=float(b[index]);product=rtol*abs(r);allowed=atol+product;error=abs(v-r);passed=math.isfinite(v) and math.isfinite(r) and error<=allowed
  record=dict(index=list(index),candidate_hex=fhex([v]),reference_hex=fhex([r]),error_hex=fhex([error]),allowed_hex=fhex([allowed]),passed=passed)
  if rational_values is not None:
   exact=rational_values[index] if a.shape else rational_values.item();err=abs(Fraction.from_float(v)-exact);bound=Fraction.from_float(allowed);passed=err<=bound;record.update(oracle=[str(exact.numerator),str(exact.denominator)],forward_error=[str(err.numerator),str(err.denominator)],allowed_rational=[str(bound.numerator),str(bound.denominator)],passed=passed)
  if not passed:failed.append(list(index))
  records.append(record)
 return dict(passed=not failed,shape=list(a.shape),failed_indices=failed,records=records,atol=atol,rtol=rtol)


def comparisons(c,r):
 checks={}
 for k in ('F','Fdata','Facc'):checks[k]=compare_arrays(c[k],r[k],1e-10,1e-9)
 for k in ('z','g'):checks[k]=compare_arrays(c[k],r[k],1e-12,1e-12)
 for k in ('gp','gpp'):checks[k]=compare_arrays(c[k],r[k],2e-6,2e-5)
 for k in ('vg','vd','vby'):
  if c.get(k) is not None:checks[k]=compare_arrays(c[k],r[k],1e-12,1e-10)
 for k in ('r','rdata','racc'):checks[k]=compare_arrays(c[k],r[k],2e-5,2e-4)
 if c['complementarity'] is not None:checks['complementarity']=compare_arrays(c['complementarity'],r['complementarity'],1e-10,1e-8)
 for frame in ('x','q','y'):
  for k in r['frames'][frame]:
   a,b=c['frames'][frame][k],r['frames'][frame][k]
   tol=(1e-10,1e-8) if k.startswith(('G','C','KKT')) else (2e-5,3e-5) if k in ('H','Hdata','Hacc') else (2e-5,2e-5) if k in ('Hz','Hg') else (2e-6,2e-5) if k in ('Jz','Jg') else (2e-5,2e-4)
   checks[frame+'/'+k]=compare_arrays(a,b,*tol)
   if k.startswith('H'):
    import numpy as np
    checks[frame+'/'+k+'/candidate_symmetry']=compare_arrays(a,np.asarray(a).T,1e-10,0)
    checks[frame+'/'+k+'/reference_symmetry']=compare_arrays(b,np.asarray(b).T,1e-10,0)
 return checks


def worker():
 started=read(ROOT/'started.json');worker_guard(started,os.environ.get('V15_TOKEN'),os.getppid(),ROOT/'worker-consumed.json')
 source_map=read(ROOT/'execution-sources.json')['sha256'];hashes(source_map);end=started['deadline_monotonic']-5
 # Scientific imports begin only inside the owned invocation.
 import numpy as np
 import basketball_acceleration_decimal_v15 as decimal_candidate
 import basketball_shared_components_v15 as candidate
 import basketball_shared_accounting_v15 as accounting
 import basketball_shared_solver_v15 as solver
 import basketball_shared_reference_v15 as reference
 def save(path,value):return publish(ROOT/path,plain(value))
 cinputs=read(ROOT/'candidate-inputs/inputs.json');ca=Audit('candidate',end,source_map,ROOT/'entries.jsonl');setups={}
 for w in (0,1):
  ca.context_set('setup/'+str(w),{});base=cinputs['cases'][0];setups[w]=ca('setup',lambda w=w:decimal_candidate.setup(base['knots_hex'],base['quadrature_hex'],w,ca.check))
  save('candidate-setup-'+str(w)+'.json',{'n':setups[w]['n'],'active':setups[w]['active'],'context':setups[w]['context'],'L':[[str(v) for v in row] for row in setups[w].get('L',[])],'H':[[str(v) for v in row] for row in setups[w].get('H',[])]})
 for c in cinputs['cases']:
  ci=c['index'];cold,ret=c['slots'];scale=candidate.arr(c['scale_hex']);m=c['dimension'];savedP=candidate.arr(c['P_hex']).reshape(m,m);savedOrigin=candidate.arr(c['origin_hex']);model=candidate.Candidate(c,setups[c['weight']],ca.check)
  ca.context_set(str(ci)+'/cold',cold);ca('complete',lambda:None);out=model.evaluate(cold,ca);cold_report=ca('cold_report',lambda:accounting.report(out,cold,scale,np.eye(m),np.eye(m)));save(f'candidate-{ci}-cold.json.gz',cold_report)
  for seq,order in enumerate(ORDERS,1):
   name=f'{ci}/returned/{seq}';transform=None
   if seq==5:
    ca.context_set(f'{ci}/transform',cold);ca('transform_context',lambda:None);rj=model.evaluate(cold,ca,True)
    def transform_work():
     J=rj['J'];nf=len(c['problem']['free']);assert J.shape[0]>=m-nf
     singular,V,tol,sub=candidate.deterministic_svd(J[:,nf:]);scales=np.ones(len(singular));active=singular>tol;scales[active]=np.clip(1/singular[active],1e-3,1e3);P=np.eye(m);P[nf:,nf:]=(V.T*scales)@V;inverse=np.linalg.inv(P)
     return dict(P=P,inverse=inverse,origin=candidate.arr(cold['q_hex']),singular=singular,rank_threshold=tol,scales=scales,subspaces=sub,active=active,identity_error=inverse@P-np.eye(m),symmetry_error=P-P.T,coefficient_coverage=V.T@V,offset_identity=P[:nf,:nf])
    transform_cache=accounting.TransformCache();transform=transform_cache.request(lambda:ca('svd_transform',transform_work));save(f'transform-{ci}.json.gz',transform)
   ca.context_set(name,ret);inverse=ca('saved_inverse',lambda:np.linalg.inv(savedP));P=savedP if seq<5 else transform['P'];origin=savedOrigin if seq<5 else transform['origin'];pinverse=inverse if seq<5 else transform['inverse']
   # The canonical report always retains historical multipliers/saved transform;
   # the fifth public probe uses the new transform, with its separate algebra below.
   adapter=accounting.Adapter(name,ret,scale,P,origin,pinverse,lambda s,a:model.evaluate(s,a),ca,bound_inverse=inverse if seq==5 else None)
   def probe():
    y=candidate.arr(ret['y_hex']) if seq<5 else pinverse@(candidate.arr(ret['q_hex'])-origin)
    value=adapter.public_probe(y)
    return y,value
   y,probe_result=ca('public_probe',probe)
   if not probe_result['accepted']:
    try:adapter.request('O',True,y)
    except ValueError:pass
    else:raise AssertionError('inexact public state evaluated')
   ca('complete',lambda:None);first=[];second=[]
   for repeat in (0,1):
    for field in order:
     value=adapter.request(field,public=bool(probe_result['accepted']),y=y)
     (first if repeat==0 else second).append(hashlib.sha256(encode(plain(value))).hexdigest())
   assert first==second
   returned=solver.owned_report(adapter);assert returned is solver.owned_report(adapter)
   extra=None;transform_hit=False
   if seq==5:
    def forbidden_transform():raise AssertionError('repeated transform entered math')
    transform_hit=transform_cache.request(forbidden_transform) is transform
    assert transform_hit and transform_cache.requests==2
    extra=returned
    returned=ca('extra_transport',lambda:accounting.report(adapter.values,ret,scale,savedP,inverse))
   save(f'candidate-{ci}-returned-{seq}.json.gz',dict(report=returned,extra_newP=extra,probe=probe_result,requests=adapter.requests,cache_hashes=[first,second],transform_repeated_cache_hit=transform_hit,owned_states=len(adapter.ledger.states),owned_iterations=adapter.ledger.iterations))
  print('candidate case',ci,'complete',flush=True)
 save('candidate-closed.json',dict(counts=ca.counts,monotonic=time.monotonic()))
 # Drop all candidate state/results before independently constructing reference.
 del cinputs,setups,model,adapter,out,returned,cold_report,transform,extra
 rinputs=read(ROOT/'reference-inputs/inputs.json');ra=Audit('reference',end,source_map,ROOT/'entries.jsonl');rsetups={}
 for w in (0,1):
  ra.context_set('setup/'+str(w),{});base=rinputs['cases'][0];rsetups[w]=ra('setup',lambda w=w:reference.setup(base['knots_hex'],base['quadrature_hex'],w,ra.check));save('reference-setup-'+str(w)+'.json',dict(n=rsetups[w]['n'],active=rsetups[w]['active'],L=[[reference.rational(v) for v in row] for row in rsetups[w].get('L',[])],H=[[reference.rational(v) for v in row] for row in rsetups[w].get('H',[])]))
 for c in rinputs['cases']:
  model=reference.Reference(c,rsetups[c['weight']],ra.check);m=c['dimension'];scale=reference.arr(c['scale_hex'])
  for state in c['slots']:
   label=state['label'];ra.context_set(f'{c["index"]}/{label}',state);ra('complete',lambda:None);out=model.evaluate(state,ra)
   P=np.eye(m) if label=='cold' else reference.arr(c['P_hex']).reshape(m,m);inverse=np.eye(m) if label=='cold' else ra('saved_inverse',lambda:np.linalg.inv(P))
   result=ra('cold_report' if label=='cold' else 'report',lambda:reference.report(out,state,scale,P,inverse));save(f'reference-{c["index"]}-{label}.json.gz',result)
  print('reference case',c['index'],'complete',flush=True)
 save('reference-closed.json',dict(counts=ra.counts,monotonic=time.monotonic()));del model,rsetups,out,result
 comparison_summary=[]
 for c in rinputs['cases']:
  for label in ('cold','returned'):
   ra.check();ref=read(ROOT/f'reference-{c["index"]}-{label}.json.gz');seqs=[0] if label=='cold' else range(1,6)
   exact_frames=None;exact_cost=None
   if ref.get('acceleration_exact'):
    from fractions import Fraction
    exact=ref['acceleration_exact'];nf=len(c['problem']['free']);m=c['dimension'];G=np.array([Fraction(0)]*nf+[Fraction(int(v[0]),int(v[1])) for v in exact['G']],dtype=object);H=np.full((m,m),Fraction(0),dtype=object)
    for i,row in enumerate(exact['H']):
     for j,v in enumerate(row):
      for axis in range(3):H[nf+3*i+axis,nf+3*j+axis]=Fraction(int(v[0]),int(v[1]))
    P=np.eye(m) if label=='cold' else reference.arr(c['P_hex']).reshape(m,m)
    FP=np.array([[Fraction.from_float(float(v)) for v in row] for row in P],dtype=object)
    exact_frames={'x':(G,H),'q':(G,H),'y':(FP.T@G,FP.T@H@FP)}
    exact_cost=np.array(Fraction(int(exact['F'][0]),int(exact['F'][1])),dtype=object)
    ra.check()
   for seq in seqs:
    candidate_path=ROOT/(f'candidate-{c["index"]}-cold.json.gz' if not seq else f'candidate-{c["index"]}-returned-{seq}.json.gz');saved=read(candidate_path);cand=saved if not seq else saved['report'];checks=comparisons(cand,ref)
    if exact_frames is not None:
     checks['rational/Facc']=compare_arrays(cand['Facc'],ref['Facc'],1e-10,1e-9,exact_cost)
     for frame,(eg,eh) in exact_frames.items():
      checks['rational/'+frame+'/Gacc']=compare_arrays(cand['frames'][frame]['Gacc'],np.array(eg,dtype=float),1e-10,1e-8,eg)
      checks['rational/'+frame+'/Hacc']=compare_arrays(cand['frames'][frame]['Hacc'],np.array(eh,dtype=float),2e-5,3e-5,eh)
    path=f'comparison-{c["index"]}-{label}-{seq}.json.gz';save(path,checks)
    comparison_summary.append(dict(case=c['index'],label=label,sequence=seq,path=path,failed_checks=[k for k,v in checks.items() if not v['passed']],public_replay=None if not seq else saved['probe']['accepted']))
   event(ROOT/'comparisons-journal.jsonl',event='component_comparison_context',case=c['index'],label=label)
 for c in rinputs['cases']:
  ra.check();i=c['index'];transform=read(ROOT/f'transform-{i}.json.gz');saved=read(ROOT/f'candidate-{i}-returned-5.json.gz');ref=read(ROOT/f'reference-{i}-returned.json.gz');P=np.array(transform['P']);m=c['dimension'];extra=saved['extra_newP'];checks={}
  for k,v in ref['frames']['q'].items():
   a=np.asarray(v)
   if k.startswith('H'):r=P.T@a@P
   elif k.startswith('J'):r=a@P
   elif k=='KKT_inf':continue
   else:r=P.T@a
   tol=(2e-5,3e-5) if k.startswith('H') else (2e-6,2e-5) if k in ('Jz','Jg') else (2e-5,2e-4) if k.startswith('J') else (1e-10,1e-8)
   checks[k]=compare_arrays(extra['frames']['y'][k],r,*tol)
  checks['inverse']=compare_arrays(np.array(transform['inverse'])@P,np.eye(m),1e-10,1e-10);checks['symmetry']=compare_arrays(P,P.T,1e-12,1e-12);checks['coverage']=compare_arrays(transform['coefficient_coverage'],np.eye(54),1e-10,1e-10);checks['remap_back']=compare_arrays(extra['remap_back'],ref['frames']['q']['Cb'],1e-12,1e-10)
  save(f'newP-comparison-{i}.json.gz',checks);comparison_summary.append(dict(case=i,label='newP',failed_checks=[k for k,v in checks.items() if not v['passed']]))
  event(ROOT/'comparisons-journal.jsonl',event='newP_comparison_context',case=i)
 save('comparison-summary.json',comparison_summary)
 save('worker-complete.json',dict(monotonic=time.monotonic(),candidate_counts=ca.counts,reference_counts=ra.counts,slots=32,canonical_failed=sum(bool(v['failed_checks']) for v in comparison_summary),public_failed=sum(v.get('public_replay') is False for v in comparison_summary)))


def run():
 deadline('readiness');ready=read(ROOT/'readiness.json');assert ready['passed'];hashes(ready['sha256']);hashes(read(ROOT/'environment.json'))
 start=time.monotonic();auth=read(AUTH);end=min(start+900,auth['deadlines']['scientific_cleanup']['monotonic']);token=os.urandom(32).hex()
 publish(ROOT/'started.json',dict(start_monotonic=start,deadline_monotonic=end,token=token,supervisor_pid=os.getpid(),authorization_sha256=sha(AUTH),admission_sha256=sha(ROOT/'admission.json'),readiness_sha256=sha(ROOT/'readiness.json')))
 os.environ['V15_TOKEN']=token
 budget=supervise([PYTHON,str(SCRIPT),'worker'],end,ROOT/'worker.log',ROOT/'process.json');budget.update(phase_elapsed_seconds=time.monotonic()-auth['t0_monotonic'],scientific_invocations=1,training_seconds=0,forbidden_entries=0)
 publish(ROOT/'budget.json',budget);print(json.dumps(budget),flush=True)
 if not budget['worker_stopped'] or budget['remaining_live_descendants']:raise RuntimeError('cleanup incomplete')


def package():
 deadline('phase');ad=read(ROOT/'admission.json');assert ad['authorization_sha256']==sha(AUTH)
 suites=[read(p) for p in sorted(ROOT.glob('toy-suite-??-result.json'))]
 assert suites and suites[-1]['passed'];hashes(suites[-1]['source_sha256'])
 if (ROOT/'execution-sources.json').exists():hashes(read(ROOT/'execution-sources.json')['sha256'])
 for name,h in ad['inputs_sha256'].items():assert sha(ROOT/name/'inputs.json')==h
 history=read(ROOT/'historical-sources.json')
 for k in ('historical','v11','pinned'):hashes(history[k])
 entries=[json.loads(s) for s in (ROOT/'entries.jsonl').read_text().splitlines()] if (ROOT/'entries.jsonl').exists() else []
 actual=[json.loads(s) for s in (ROOT/'actual-entries.jsonl').read_text().splitlines()] if (ROOT/'actual-entries.jsonl').exists() else []
 entered=[e for e in entries if e['event']=='entry'];done=[e for e in entries if e['event']=='completed'];interrupted=[e for e in entries if e['event']=='interrupted']
 assert len(entered)==len(actual)
 for a,b in zip(entered,actual):
  for k in ('method','context','kind','q_hex','x_hex','vg_hex','vby_hex','ordinal'):assert a[k]==b[k]
 counts={}
 for method,caps in [('candidate',CAPS),('reference',REFCAPS)]:
  counts[method]={k:sum(e['method']==method and e['kind']==k for e in entered) for k in caps}
  assert all(counts[method][k]<=v for k,v in caps.items())
 summary=read(ROOT/'comparison-summary.json') if (ROOT/'comparison-summary.json').exists() else []
 if not (ROOT/'started.json').exists():
  publish(ROOT/'budget.json',dict(scientific_invocations=0,scientific_seconds=0,worker_stopped=True,remaining_live_descendants=[],within_deadline=True,exit_code=None,training_seconds=0,forbidden_entries=0,toy_suites=len(suites),toy_seconds=sum(s['elapsed_seconds'] for s in suites),phase_elapsed_seconds=time.monotonic()-read(AUTH)['t0_monotonic'],reason='incomplete frozen readiness; scientific allocation never entered and terminal Plan022 allocation is not reusable'))
 budget=read(ROOT/'budget.json');complete=(ROOT/'worker-complete.json').exists() and budget['worker_stopped'] and not budget['remaining_live_descendants'] and budget['within_deadline'] and budget['exit_code']==0
 canonical_failed=sum(bool(v['failed_checks']) for v in summary);public_failed=sum(v.get('public_replay') is False for v in summary)
 outcome='incomplete' if not complete else 'rejected' if canonical_failed or public_failed else 'qualified_on_fixed_cohort'
 manifest={str(p):sha(p) for p in ROOT.rglob('*') if p.is_file() and p.name not in ('decision.json','package-validation.json','evidence-manifest.json')}
 for p in ROOT.glob('*.json.gz'):read(p)
 publish(ROOT/'evidence-manifest.json',manifest)
 publish(ROOT/'decision.json',dict(**GATES,status=outcome,implementation_complete=complete,canonical_components='incomplete' if not complete else 'rejected' if canonical_failed else 'qualified_on_fixed_cohort',readiness=read(ROOT/'readiness-status.json') if (ROOT/'readiness-status.json').exists() else read(ROOT/'readiness.json'),public_y_replay='incomplete' if not complete else 'rejected' if public_failed else 'passed',canonical_failed_contexts=canonical_failed,public_failed_replays=public_failed,package_integrity='passed',historical_v11_A2_A3='failed; unchanged',other_v11_failed_states_unadjudicated=57))
 publish(ROOT/'package-validation.json',dict(passed=True,complete=complete,counts=counts,entered=len(entered),completed=len(done),interrupted=len(interrupted),unknown=len(entered)-len(done)-len(interrupted),sources_unchanged=True,phase_elapsed_seconds=time.monotonic()-read(AUTH)['t0_monotonic']))
 print(json.dumps(dict(status=outcome,canonical_failed=canonical_failed,public_failed=public_failed,complete=complete)),flush=True)


if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('command',choices=['admit','ready','run','package','worker']);args=parser.parse_args();globals()[args.command]()
