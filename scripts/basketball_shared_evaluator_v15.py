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
 if hasattr(v,'shape') and getattr(v,'size',1)==0 and len(v.shape)>1:return dict(array_shape=list(v.shape),array_hex=v.astype('<f8').tobytes().hex())
 if hasattr(v,'tolist'):return plain(v.tolist())
 if type(v).__module__ in ('decimal','fractions'):return str(v)
 if all(hasattr(v,k) for k in ('v','g','h')):return dict(jet_value=plain(v.v),jet_gradient=plain(v.g),jet_hessian=plain(v.h))
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
 if os.getppid()!=parent_pid:raise ValueError('actual worker parent mismatch')
 if started.get('supervisor_identity',{}).get('pid_namespace')!=os.readlink('/proc/self/ns/pid'):raise ValueError('worker namespace mismatch')
 publish(path,dict(consumed=True,identity=process_identity(),monotonic=time.monotonic()))


def effective_frozen(root):
 root=Path(root);frozen=read(root/'frozen.json');hashes(frozen['leaves'])
 correction=root/'suite-02-source-correction.json'
 if correction.exists():
  change=read(correction);first=read(root/'toy-suite-01-result.json')
  if first['passed'] or change['previous_result_sha256']!=sha(root/'toy-suite-01-result.json') or change['original_frozen_sha256']!=sha(root/'frozen.json'):raise ValueError('invalid source correction basis')
  test=TEST if root==ROOT else root/'test.py'
  if change['test_sha256']!=first['test_sha256'] or change['test_sha256']!=sha(test):raise ValueError('frozen test correction forbidden')
  frozen={**frozen,'sources':change['source_sha256']}
 hashes(frozen['sources']);return frozen


def verify_chain(stage,root=ROOT,authorization=AUTH):
 root=Path(root);authorization=Path(authorization);auth=read(authorization)
 if auth['plan_sha256']!=sha(auth['plan']) or auth['objective_sha256']!=sha(auth['objective']):raise ValueError('authorization leaf mutation')
 if not all(os.environ.get(k)==v for k,v in THREADS.items()):raise ValueError('thread policy')
 if auth['phase_seconds']!=7200 or auth['scientific_invocations']!=1 or auth['toy_suite_invocations']!=2:raise ValueError('authorization limits')
 chain=read(root/'admission-chain.json')
 if chain['authorization_path']!=str(authorization) or chain['authorization_sha256']!=sha(authorization):raise ValueError('authorization mutation')
 hashes(chain['leaves'])
 ad=read(root/'admission.json')
 if not ad['passed'] or ad['admitted_monotonic']>auth['deadlines']['admission']['monotonic']:raise ValueError('admission late/incomplete')
 hashes(read(root/'environment.json'))
 history=read(root/'historical-sources.json')
 for key in ('historical','v11','pinned'):hashes(history[key])
 if stage=='admission':return dict(passed=True,stage=stage)
 frozen=effective_frozen(root)
 coverage=read(root/'readiness-coverage.json');definitions=read(root/'toy-definitions.json')
 if not coverage['rows'] or {r['id'] for r in coverage['rows']}!=set(definitions['required_coverage']):raise ValueError('missing coverage row')
 if any(not r['production_calls'] or not r['assertions'] or not r['boundaries'] for r in coverage['rows']):raise ValueError('incomplete source coverage')
 if stage=='toy':return dict(passed=True,stage=stage)
 results=[read(p) for p in sorted(root.glob('toy-suite-??-result.json'))]
 if not results or not results[-1]['passed']:raise ValueError('no applicable passing suite')
 last=results[-1];hashes(last['source_sha256'])
 if last['source_sha256']!=frozen['sources']:raise ValueError('toy source mismatch')
 if last['test_sha256']!=sha(TEST if root==ROOT else root/'test.py'):raise ValueError('test mutation')
 observed=last['coverage']
 for row in coverage['rows']:
  if row['id'] not in observed or not observed[row['id']]['passed'] or set(observed[row['id']]['assertions'])!=set(row['assertions']):raise ValueError('unexecuted coverage '+row['id'])
 marker=root/f"toy-suite-{last['slot']:02}-consumed.json"
 if last['marker_sha256']!=sha(marker):raise ValueError('toy marker mismatch')
 if stage=='ready':return dict(passed=True,stage=stage)
 readiness=read(root/'readiness.json');hashes(readiness['leaves'])
 if readiness['ready_monotonic']>auth['deadlines']['readiness']['monotonic'] or not readiness['passed']:raise ValueError('readiness late/incomplete')
 if readiness['authorization_sha256']!=sha(authorization):raise ValueError('readiness auth mismatch')
 if stage=='worker':
  started=read(root/'started.json')
  if started['readiness_sha256']!=sha(root/'readiness.json') or started['authorization_sha256']!=sha(authorization):raise ValueError('started graph mismatch')
 return dict(passed=True,stage=stage)


def ready():
 deadline('readiness')
 try:
  verify_chain('ready');last=sorted(ROOT.glob('toy-suite-??-result.json'))[-1]
  leafs=[ROOT/'admission-chain.json',ROOT/'frozen.json',ROOT/'readiness-coverage.json',ROOT/'toy-definitions.json',ROOT/'coverage-source-review.md',ROOT/'comparison-schema.json',ROOT/'expected-schedule.json',last]
  publish(ROOT/'execution-sources.json',dict(sha256=effective_frozen(ROOT)['sources'],threads=THREADS))
  publish(ROOT/'readiness.json',dict(passed=True,ready_monotonic=time.monotonic(),authorization_sha256=sha(AUTH),leaves={str(p):sha(p) for p in leafs}))
  print('Complete source and executed coverage readiness passed.',flush=True)
 except (ValueError,FileNotFoundError,AssertionError) as exc:
  publish(ROOT/'readiness-status.json',dict(passed=False,status='incomplete',reason=str(exc),scientific_entry_prohibited=True,monotonic=time.monotonic()))
  print('Readiness incomplete: '+str(exc),flush=True)


def toy():
 deadline('readiness');verify_chain('toy')
 slot=next((i for i in (1,2) if not (ROOT/f'toy-suite-{i:02}-consumed.json').exists()),None)
 if slot is None:raise ValueError('both suites consumed')
 if slot==2:
  first=read(ROOT/'toy-suite-01-result.json');correction=read(ROOT/'suite-02-source-correction.json')
  if first['passed'] or correction['test_sha256']!=sha(TEST) or correction['previous_result_sha256']!=sha(ROOT/'toy-suite-01-result.json'):raise ValueError('second suite not justified')
 begin=time.monotonic();end=min(begin+120,read(AUTH)['deadlines']['readiness']['monotonic']);token=os.urandom(32).hex()
 marker=ROOT/f'toy-suite-{slot:02}-consumed.json'
 publish(marker,dict(slot=slot,start_monotonic=begin,deadline_monotonic=end,source_sha256={str(p):sha(p) for p in SOURCES+[TEST]},token=token,supervisor_pid=os.getpid(),supervisor_identity=process_identity()))
 os.environ['V15_TOY_TOKEN']=token;os.environ['V15_TOY_SLOT']=str(slot)
 result=supervise([PYTHON,str(SCRIPT),'toy-worker'],end,ROOT/f'toy-suite-{slot:02}.log',ROOT/f'toy-suite-{slot:02}-process.json')
 publish(ROOT/f'toy-suite-{slot:02}-supervision.json',result)
 print(json.dumps(result),flush=True)


def toy_worker():
 slot=int(os.environ.get('V15_TOY_SLOT','0'));marker=ROOT/f'toy-suite-{slot:02}-consumed.json';started=read(marker)
 verify_chain('toy')
 worker_guard(started,os.environ.get('V15_TOY_TOKEN'),os.getppid(),ROOT/f'toy-suite-{slot:02}-worker.json')
 import runpy
 module=runpy.run_path(str(TEST),run_name='owned_toy_module')
 raise SystemExit(module['main'](slot,started,sha(marker)))


CAPS=dict(setup=2,complete=96,transform_context=16,prepare=112,objective_residual=96,residual_only=16,data_hessian=96,full_sum=96,raw_depth=96,bounded_values=96,weighted_raw_hessian=96,bounded_curvature=96,report=80,cold_report=16,svd_transform=16,saved_inverse=80,public_probe=80,extra_transport=16,acceleration=49)
REFCAPS={**CAPS,'complete':32,'prepare':32,'objective_residual':32,'data_hessian':32,'full_sum':32,'raw_depth':32,'bounded_values':32,'weighted_raw_hessian':32,'bounded_curvature':32,'report':16,'saved_inverse':16,'acceleration':14,'cold_report':16,'transform_context':0,'residual_only':0,'svd_transform':0,'public_probe':0,'extra_transport':0}


def operand_digest(value):return hashlib.sha256(encode(plain(value))).hexdigest()


def setup_entry(audit,knots_hex,quadrature_hex,weight,expected,calculator):
 actual=dict(knots_hex=knots_hex,quadrature_hex=quadrature_hex,weight=weight)
 if actual!=expected:raise ValueError('setup operand mismatch before setup math')
 return audit('setup',calculator)


class Audit:
 def __init__(self,method,end,source_map,path=None,caps=None):
  self.method=method;self.end=end;self.sources=source_map;self.path=path;self.counts={};self.context=None;self.used=set();self.records=[];self.ordinal=0;self.stack=[];self.operands=None;self.caps=caps or (CAPS if method=='candidate' else REFCAPS)
 def check(self):
  if time.monotonic()>=self.end:raise TimeoutError('numerical deadline')
 def bind_operands(self,case,setup):self.operands=(operand_digest(case),operand_digest(setup),len(case['problem']['free']))
 def context_set(self,name,state):
  if self.stack:raise ValueError('context changed during owned entry')
  self.context=(name,dict(state));self.ordinal=0
 def __call__(self,kind,fn):
  self.check();hashes(self.sources)
  if self.context is None:raise ValueError('no context')
  name,state=self.context;key=(name,kind)
  if key in self.used:raise ValueError('duplicate immutable component')
  if self.counts.get(kind,0)>=self.caps.get(kind,0):raise ValueError('unallocated entry '+kind)
  self.used.add(key);self.counts[kind]=self.counts.get(kind,0)+1;self.ordinal+=1
  identity='/'.join((self.method,name,kind,str(self.ordinal)))
  e=dict(id=identity,parent_id=self.stack[-1]['id'] if self.stack else None,method=self.method,context=name,kind=kind,ordinal=self.ordinal,scope=state.get('scope'),q_hex=state.get('q_hex'),x_hex=state.get('x_hex'),vg_hex=state.get('vg_hex'),vby_hex=state.get('vby_hex'),source_sha256=self.sources,status='entered',start_monotonic=time.monotonic())
  self.records.append(e);self.stack.append(e)
  if self.path:event(self.path,event='entry',**e)
  try:
   value=fn();self.check()
   snapshot=plain(value);digest=operand_digest(snapshot)
   if self.path:
    output=self.path.parent/('entry-output-'+identity.replace('/','_')+'.json.gz');publish(output,snapshot);e['output_path']=str(output);e['output_sha256']=sha(output)
   e.update(status='completed',value_sha256=digest,end_monotonic=time.monotonic())
   if self.path:event(self.path,event='completed',**e)
   return value
  except BaseException as exc:
   e.update(status='interrupted',error=type(exc).__name__+': '+str(exc),end_monotonic=time.monotonic())
   if self.path:event(self.path,event='interrupted',**e)
   raise
  finally:self.stack.pop()
 def observe(self,kind,actual,fn):
  self.check();name,expected=self.context
  for key in ('q_hex','x_hex','vg_hex','vby_hex','scope'):
   if actual.get(key)!=expected.get(key):raise ValueError('actual calculator operand mismatch '+key)
  if self.operands is None:raise ValueError('missing owned geometry binding')
  case_digest,setup_digest,nf=self.operands
  if actual['coefficient_hex']!=expected['x_hex'][16*nf:]:raise ValueError('actual coefficient mismatch')
  if operand_digest(actual['case'])!=case_digest or operand_digest(actual['setup'])!=setup_digest:raise ValueError('actual setup/geometry mismatch')
  record=dict(id=self.stack[-1]['id'],parent_id=self.stack[-1]['parent_id'],method=self.method,context=name,kind=kind,scope=actual.get('scope'),q_hex=actual['q_hex'],q_derivation='owned admitted q; never inverse-roundtripped',x_hex=actual['x_hex'],coefficient_hex=actual['coefficient_hex'],vg_hex=actual['vg_hex'],vby_hex=actual['vby_hex'],case_sha256=case_digest,setup_sha256=setup_digest)
  self.stack[-1]['observed']=record
  if self.path:event(self.path.with_name('actual-entries.jsonl'),event='actual_entry',**record)
  return fn()


def numerical_array(value):
 import numpy as np
 if isinstance(value,dict) and set(value)=={'array_shape','array_hex'}:
  return np.frombuffer(bytes.fromhex(value['array_hex']),dtype='<f8').reshape(value['array_shape'])
 return np.asarray(value,dtype='<f8')


def compare_arrays(candidate,reference,atol,rtol,rational_values=None,check=lambda:None):
 import numpy as np
 from fractions import Fraction
 a=numerical_array(candidate);b=numerical_array(reference)
 if a.shape!=b.shape:return dict(passed=False,complete=True,integrity_failure=True,shape_mismatch=[list(a.shape),list(b.shape)])
 failed=[];errors=[];allowed_values=[];exact_records=[]
 for ordinal,index in enumerate(np.ndindex(a.shape)):
  if ordinal%128==0:check()
  v=float(a[index]);r=float(b[index]);product=rtol*abs(r);allowed=atol+product;error=abs(v-r);passed=all(map(math.isfinite,(v,r,allowed,error))) and error<=allowed
  errors.append(error);allowed_values.append(allowed)
  if rational_values is not None and all(map(math.isfinite,(v,r,allowed))):
   exact=rational_values[index] if a.shape else rational_values.item();err=abs(Fraction.from_float(v)-exact);bound=Fraction.from_float(allowed);passed=err<=bound
   exact_records.append(dict(index=list(index),oracle=[str(exact.numerator),str(exact.denominator)],forward_error=[str(err.numerator),str(err.denominator)],allowed_rational=[str(bound.numerator),str(bound.denominator)]))
  if not passed:failed.append(list(index))
 return dict(passed=not failed,complete=True,shape=list(a.shape),candidate_hex=a.tobytes().hex(),reference_hex=b.tobytes().hex(),error_hex=fhex(errors),allowed_hex=fhex(allowed_values),failed_indices=failed,atol=atol,rtol=rtol,exact=exact_records)


def comparison_spec(m,n,nacc,label,nf=0):
 spec={}
 def add(path,shape,tol,exact=False):spec[path]=dict(shape=shape,atol=tol[0],rtol=tol[1],exact=exact)
 for k in ('F','Fdata','Facc'):add(k,[],(1e-10,1e-9),k=='Facc' and nacc==0)
 for k in ('z','g'):add(k,[n],(1e-12,1e-12))
 for k in ('gp','gpp'):add(k,[n],(2e-6,2e-5))
 for k in ('vg','vd'):add(k,[n],(1e-12,1e-10))
 add('vby',[m] if label=='returned' else None,(1e-12,1e-10))
 add('complementarity',[n] if label=='returned' else None,(1e-10,1e-8))
 for k,rows in [('r',2*n+nacc),('rdata',2*n),('racc',nacc)]:add(k,[rows],(2e-5,2e-4))
 for f in ('x','q','y'):
  for k in ('G','Gdata','Gacc'):add(f'frames.{f}.{k}',[m],(1e-10,1e-8),k=='Gacc' and nacc==0)
  for k in ('H','Hdata','Hacc','Hz','Hg'):add(f'frames.{f}.{k}',[m,m],(2e-5,2e-5) if k in ('Hz','Hg') else (2e-5,3e-5),k=='Hacc' and nacc==0)
  for k,rows in [('J',2*n+nacc),('Jdata',2*n),('Jacc',nacc),('Jz',n),('Jg',n)]:add(f'frames.{f}.{k}',[rows,m],(2e-6,2e-5) if k in ('Jz','Jg') else (2e-5,2e-4))
  if label=='returned':
   for k in ('Cd','Cb','KKT'):add(f'frames.{f}.{k}',[m],(1e-10,1e-8))
   add(f'frames.{f}.KKT_inf',[],(1e-10,1e-8))
 for f in ('x','q','y'):
  for k in ('Gacc','Hacc','Jacc'):spec[f'frames.{f}.{k}']['zero_prefix']=nf
 return spec


def field(value,path):
 for key in path.split('.'):value=value[key]
 return value


def comparisons(c,r,spec,check=lambda:None,policy_fixture=None):
 import numpy as np
 checks={}
 for path,rule in spec.items():
  check()
  try:a=field(c,path);b=field(r,path)
  except KeyError:
   checks[path]=dict(passed=False,complete=False,missing=True);continue
  shape=rule['shape']
  if shape is None:
   checks[path]=dict(passed=a is None and b is None,complete=True,exact_null=True);continue
  a=numerical_array(a);b=numerical_array(b)
  if list(a.shape)!=shape or list(b.shape)!=shape:
   checks[path]=dict(passed=False,complete=True,integrity_failure=True,expected_shape=shape,actual_shapes=[list(np.shape(a)),list(np.shape(b))]);continue
  checks[path]=compare_arrays(a,b,rule['atol'],rule['rtol'],check=check)
  nf=rule.get('zero_prefix',0)
  if nf:
   k=path.split('.')[-1];blocks=lambda v:[v[:nf]] if k=='Gacc' else [v[:nf,:],v[:,:nf]] if k=='Hacc' else [v[:,:nf]]
   checks[path+'/offset_zero']=dict(passed=all(bool(np.all(block==0)) for v in (a,b) for block in blocks(v)),complete=True)
  if rule['exact']:
   checks[path+'/exact_zero']=dict(passed=bool(np.all(np.asarray(a)==0) and np.all(np.asarray(b)==0)),complete=True,candidate_hex=np.asarray(a,dtype='<f8').tobytes().hex(),reference_hex=np.asarray(b,dtype='<f8').tobytes().hex())
  if path.split('.')[-1] in ('H','Hdata','Hacc','Hz','Hg'):
   checks[path+'/candidate_symmetry']=compare_arrays(a,np.asarray(a).T,1e-10,0,check=check)
   checks[path+'/reference_symmetry']=compare_arrays(b,np.asarray(b).T,1e-10,0,check=check)
 if set(c.get('frames',{}))!={'x','q','y'} or set(r.get('frames',{}))!={'x','q','y'}:checks['frame_schema']=dict(passed=False,complete=False)
 if policy_fixture is not None:
  checks['explicit_test_policy']=compare_arrays(policy_fixture['candidate'],policy_fixture['reference'],policy_fixture['atol'],policy_fixture['rtol'],policy_fixture.get('rational'),check)
 return checks


def transform_checks(transform,nf,check=lambda:None):
 import numpy as np
 P=np.asarray(transform['P']);inv=np.asarray(transform['inverse']);m=len(P);checks={}
 checks['inverse_left']=compare_arrays(inv@P,np.eye(m),1e-10,1e-10,check=check)
 checks['inverse_right']=compare_arrays(P@inv,np.eye(m),1e-10,1e-10,check=check)
 checks['symmetry']=compare_arrays(P,P.T,1e-12,1e-12,check=check)
 checks['nuisance_exact']=dict(passed=bool(np.array_equal(P[:nf,:nf],np.eye(nf)) and np.all(P[:nf,nf:]==0) and np.all(P[nf:,:nf]==0) and np.array_equal(inv[:nf,:nf],np.eye(nf)) and np.all(inv[:nf,nf:]==0) and np.all(inv[nf:,:nf]==0)),complete=True)
 if 'coefficient_coverage' in transform:
  checks['coverage']=compare_arrays(transform['coefficient_coverage'],np.eye(m-nf),1e-10,1e-10,check=check)
  checks['inactive_scale_exact']=dict(passed=bool(np.all(np.asarray(transform['scales'])[~np.asarray(transform['active'],dtype=bool)]==1)),complete=True)
 return checks


def transport_reference(reference,P,check=lambda:None):
 import numpy as np
 out={**reference,'frames':{k:dict(v) for k,v in reference['frames'].items()}};P=np.asarray(P)
 for k,v in reference['frames']['q'].items():
  check();a=numerical_array(v)
  if k=='KKT_inf':continue
  out['frames']['y'][k]=P.T@a@P if k.startswith('H') else a@P if k.startswith('J') else P.T@a
 if 'KKT' in out['frames']['y']:out['frames']['y']['KKT_inf']=float(np.max(np.abs(out['frames']['y']['KKT'])))
 return out


def newp_comparisons(candidate,reference,transform,spec,nf,check=lambda:None,transported=None):
 import numpy as np
 transported=transport_reference(reference,transform['P'],check) if transported is None else transported
 checks=comparisons(candidate,transported,spec,check);checks.update({'transform/'+k:v for k,v in transform_checks(transform,nf,check).items()})
 if 'remapped_multiplier' not in candidate or 'remap_back' not in candidate:
  checks['remapped_multiplier']=dict(passed=False,complete=False,missing=True)
 else:
  remap=np.asarray(transform['P']).T@np.asarray(reference['frames']['q']['Cb'])
  checks['remapped_multiplier']=compare_arrays(candidate['remapped_multiplier'],remap,1e-12,1e-10,check=check)
  checks['remap_back']=compare_arrays(candidate['remap_back'],np.asarray(reference['frames']['q']['Cb']),1e-12,1e-10,check=check)
 return checks


def historical_comparisons(archive,reference,spec,check=lambda:None):
 mapping={'objective':'F','G':'frames.q.G','C_depth':'frames.q.Cd','C_bounds':'frames.q.Cb','KKT':'frames.q.KKT','optimality':'frames.q.KKT_inf','complementarity_original':'complementarity','multipliers_depth':'vd','bound_multipliers':'frames.q.Cb'};checks={}
 for old,new in mapping.items():
  if old not in archive['row']:checks[old]=dict(passed=False,complete=False,missing=True);continue
  rule=spec[new];checks[old]=compare_arrays(archive['row'][old],field(reference,new),rule['atol'],rule['rtol'],check=check)
 return dict(qualified_historical_unchanged=archive['qualified'],checks=checks)


def reduce_decision(dimensions):
 required=('source_coverage','package_integrity','schedule','canonical','public_api','transform')
 complete=all(dimensions[k]['complete'] for k in required) and dimensions['historical']['complete']
 failed=any(dimensions[k]['failures'] for k in required)
 return dict(status='incomplete' if not complete else 'rejected' if failed else 'qualified_on_fixed_cohort',dimensions=dimensions,known_required_failure=failed,**GATES)


def validate_package(expected,retained):
 """Only retained JSON/bytes/hashes: never import or recompute evaluator math."""
 dimensions={k:dict(complete=True,failures=[],missing=[]) for k in ('source_coverage','package_integrity','schedule','canonical','public_api','transform','historical')}
 def missing(d,label):dimensions[d]['complete']=False;dimensions[d]['missing'].append(label)
 if not retained.get('ready'):missing('source_coverage','readiness')
 actual=retained.get('entries',[]);ids=[v['id'] for v in actual if v['event']=='entry']
 if ids!=expected['entries']:
  missing('schedule','exact entry sequence');dimensions['schedule']['failures'] += ['duplicate identity'] if len(ids)!=len(set(ids)) else []
 for identity in ids:
  completed=[v for v in actual if v['id']==identity and v['event']=='completed'];interrupted=[v for v in actual if v['id']==identity and v['event']=='interrupted']
  if len(completed)!=1:missing('schedule','completion '+identity)
  if interrupted:dimensions['schedule']['failures'].append('interrupted '+identity)
  if completed:
   e=completed[0]
   if retained.get('hashes',{}).get(e.get('output_path'))!=e.get('output_sha256'):dimensions['package_integrity']['failures'].append('output hash '+identity)
 for identity in expected.get('observed',[]):
  actual_observations=[v for v in retained.get('observed',[]) if v['id']==identity]
  if len(actual_observations)!=1:missing('schedule','actual operands '+identity)
  elif any(actual_observations[0].get(k)!=v for k,v in expected.get('operands',{}).get(identity,{}).items()):dimensions['package_integrity']['failures'].append('actual operand mismatch '+identity)
 for path,dimension in expected['outputs'].items():
  if path not in retained.get('outputs',{}):missing(dimension,path);missing('schedule',path);continue
  value=retained['outputs'][path]
  receipts=[r for r in retained.get('output_receipts',[]) if r['path']==path]
  if len(receipts)!=1:missing('package_integrity','output receipt '+path)
  elif receipts[0]['sha256']!=retained.get('hashes',{}).get(path):dimensions['package_integrity']['failures'].append('artifact hash '+path)
  if path not in retained.get('hashes',{}):missing('package_integrity','hash '+path)
  if dimension in ('canonical','transform','historical'):
   checks=value.get('checks',value)
   required_checks=expected.get('checks',{}).get(path,[])
   for key in required_checks:
    if key not in checks:missing(dimension,path+':'+key)
   if not required_checks:missing(dimension,'required check schema '+path)
   for key,v in checks.items():
    if not isinstance(v,dict) or 'passed' not in v:continue
    target='public_api' if key.startswith('public/') else dimension
    if not v.get('complete',True):missing(target,path+':'+key)
    elif not v['passed']:dimensions[target]['failures'].append(path+':'+key)
  elif dimension=='public_api':
   if 'accepted' not in value:missing('public_api',path)
   elif not value['accepted']:dimensions['public_api']['failures'].append(path)
 for path,meta in expected.get('replays',{}).items():
  saved=retained.get('outputs',{}).get(path)
  if saved is None:continue
  accepted=saved.get('probe',{}).get('accepted');mode='public_returns' if accepted else 'canonical_returns';traversals=saved.get(mode,[]);order=meta['order']
  if len(traversals)!=2 or any(set(v)!=set(order) for v in traversals):missing('public_api' if accepted else 'canonical',path+' traversal fields')
  elif operand_digest(traversals[0])!=operand_digest(traversals[1]):dimensions['package_integrity']['failures'].append(path+' unequal repeats')
  if saved.get('traversal_order')!=order:dimensions['schedule']['failures'].append(path+' request order')
  if saved.get('canonical_identity')!=meta['state']:dimensions['package_integrity']['failures'].append(path+' admitted state identity')
  if not saved.get('cache_repeated_no_entries'):dimensions['package_integrity']['failures'].append(path+' repeat entered math')
  traces=saved.get('public_requests',[]);wrappers={'O':'fun','G':'jac','H':'hess','C':'constraint','CH':'constraint_hessian','R':'public_report'}
  if accepted:
   names=[wrappers[k] for k in order]*2
   if [v.get('wrapper') for v in traces]!=names:missing('public_api',path+' exact wrapper order')
   for trace in traces:
    if trace.get('coordinate_frame')!='y' or trace.get('y_hex')!=saved['probe'].get('y_hex') or trace.get('probe_accepted') is not True or trace.get('state')!=saved.get('owned_state_identity'):dimensions['package_integrity']['failures'].append(path+' public request identity')
   comparison_path=meta['comparison'];actual_checks=retained.get('outputs',{}).get(comparison_path,{})
   spec=comparison_spec(meta['dimension'],meta['n'],meta['acc_rows'],'returned',meta['nf'])
   for repeat in (0,1):
    required=[f'public/{repeat}/{k}' for k in ('O','G','H','CH')]+[f'public/{repeat}/C/{k}' for k in ('g','Jg')]+[f'public/{repeat}/R/'+k for k in check_names(spec)]
    for key in required:
     if key not in actual_checks:missing('public_api',comparison_path+':'+key)
  else:
   if saved.get('public_rejection') is not True or len(traces)!=1 or traces[0].get('wrapper')!='fun' or traces[0].get('probe_accepted') is not False:missing('public_api',path+' guarded rejection before entries')
   if [v.get('name') for v in saved.get('requests',[])[:12]]!=order*2:missing('schedule',path+' canonical request order')
 if not retained.get('summary_present'):missing('schedule','comparison summary')
 return reduce_decision(dimensions)


def rational_oracle(reference,P,check):
 import numpy as np
 from fractions import Fraction
 exact=reference.get('acceleration_exact')
 if not exact:return {}
 m=len(P);nf=m-len(exact['G']);G=np.array([Fraction(0)]*nf+[Fraction(int(a),int(b)) for a,b in exact['G']],dtype=object);H=np.full((m,m),Fraction(0),dtype=object)
 for i,row in enumerate(exact['H']):
  check()
  for j,(a,b) in enumerate(row):
   for axis in range(3):H[nf+3*i+axis,nf+3*j+axis]=Fraction(int(a),int(b))
 FP=np.array([[Fraction.from_float(float(v)) for v in row] for row in P],dtype=object)
 # Check within every exact matrix row; no opaque long object-array matmul.
 def product(A,B):
  out=np.empty((len(A),B.shape[1]),dtype=object)
  for i in range(len(A)):
   check()
   for j in range(B.shape[1]):out[i,j]=sum((A[i,k]*B[k,j] for k in range(A.shape[1]) if A[i,k] and B[k,j]),Fraction(0))
  return out
 Gy=product(FP.T,G.reshape(-1,1)).ravel();Hy=product(product(FP.T,H),FP)
 return dict(cost=np.array(Fraction(*map(int,exact['F'])),dtype=object),frames={'x':(G,H),'q':(G,H),'y':(Gy,Hy)})


def rational_checks(candidate,reference,oracle,check):
 import numpy as np
 if not oracle:return {}
 checks={'rational/Facc':compare_arrays(candidate['Facc'],reference['Facc'],1e-10,1e-9,oracle['cost'],check)}
 for frame,(eg,eh) in oracle['frames'].items():
  checks['rational/'+frame+'/Gacc']=compare_arrays(candidate['frames'][frame]['Gacc'],np.asarray(eg,dtype=float),1e-10,1e-8,eg,check)
  checks['rational/'+frame+'/Hacc']=compare_arrays(candidate['frames'][frame]['Hacc'],np.asarray(eh,dtype=float),2e-5,3e-5,eh,check)
 return checks


def public_checks(saved,reference,spec,check):
 import numpy as np
 checks={}
 if not saved['probe']['accepted']:return checks
 expected={'O':reference['F'],'G':reference['frames']['y']['G'],'H':reference['frames']['y']['H'],'C':[reference['g'],reference['frames']['y']['Jg']],'CH':reference['frames']['y']['Hg'],'R':reference}
 for repeat in (0,1):
  values=saved['public_returns'][repeat] if len(saved.get('public_returns',[]))>repeat else {}
  for k in ('O','G','H','C','CH','R'):
   prefix=f'public/{repeat}/{k}'
   if k not in values:checks[prefix]=dict(passed=False,complete=False,missing=True);continue
   value=values[k]
   if k=='R':checks.update({prefix+'/'+n:v for n,v in comparisons(value,reference,spec,check).items()})
   elif k=='C':
    checks[prefix+'/g']=compare_arrays(value[0],expected[k][0],1e-12,1e-12,check=check);checks[prefix+'/Jg']=compare_arrays(value[1],expected[k][1],2e-6,2e-5,check=check)
   else:
    tol=(1e-10,1e-9) if k=='O' else (1e-10,1e-8) if k=='G' else (2e-5,2e-5) if k=='CH' else (2e-5,3e-5)
    checks[prefix]=compare_arrays(value,expected[k],*tol,check=check)
 return checks


def worker():
 verify_chain('worker')
 started=read(ROOT/'started.json');worker_guard(started,os.environ.get('V15_TOKEN'),os.getppid(),ROOT/'worker-consumed.json')
 source_map=read(ROOT/'execution-sources.json')['sha256'];hashes(source_map);end=started['deadline_monotonic']-5
 import numpy as np
 import basketball_acceleration_decimal_v15 as decimal_candidate
 import basketball_shared_components_v15 as candidate
 import basketball_shared_accounting_v15 as accounting
 import basketball_shared_solver_v15 as solver
 import basketball_shared_reference_v15 as reference
 def save(path,value):
  digest=publish(ROOT/path,plain(value));event(ROOT/'artifacts.jsonl',path=path,sha256=digest,source_sha256=source_map);return digest
 cinputs=read(ROOT/'candidate-inputs/inputs.json');ca=Audit('candidate',end,source_map,ROOT/'entries.jsonl');setups={}
 for w in (0,1):
  ca.context_set('setup/'+str(w),{});base=cinputs['cases'][0];operands=dict(knots_hex=base['knots_hex'],quadrature_hex=base['quadrature_hex'],weight=w)
  setups[w]=setup_entry(ca,**operands,expected=operands,calculator=lambda w=w:decimal_candidate.setup(base['knots_hex'],base['quadrature_hex'],w,ca.check))
  save('candidate-setup-'+str(w)+'.json',setups[w])
 for c in cinputs['cases']:
  ci=c['index'];cold,ret=c['slots'];scale=candidate.arr(c['scale_hex']);m=c['dimension'];savedP=candidate.arr(c['P_hex']).reshape(m,m);savedOrigin=candidate.arr(c['origin_hex']);model=candidate.Candidate(c,setups[c['weight']],ca.check);ca.bind_operands(c,setups[c['weight']])
  ca.context_set(str(ci)+'/cold',cold);out=ca('complete',lambda:model.evaluate(cold,ca));cold_report=ca('cold_report',lambda:accounting.report(out,cold,scale,np.eye(m),np.eye(m)));save(f'candidate-{ci}-cold.json.gz',cold_report)
  for seq,order in enumerate(ORDERS,1):
   name=f'{ci}/returned/{seq}';transform=None
   if seq==5:
    ca.context_set(f'{ci}/transform',cold);transform_cache=accounting.TransformCache();transform=transform_cache.request(lambda:candidate.cold_transform(model,cold,ca));save(f'transform-{ci}.json.gz',transform)
   ca.context_set(name,ret);inverse=ca('saved_inverse',lambda:np.linalg.inv(savedP));P=savedP if seq<5 else transform['P'];origin=savedOrigin if seq<5 else transform['origin'];pinverse=inverse if seq<5 else transform['inverse']
   adapter=accounting.Adapter(name,ret,scale,P,origin,pinverse,lambda s,a:model.evaluate(s,a),ca,bound_inverse=inverse if seq==5 else None)
   def probe():
    y=candidate.arr(ret['y_hex']) if seq<5 else pinverse@(candidate.arr(ret['q_hex'])-origin)
    return y,adapter.public_probe(y)
   y,probe_result=ca('public_probe',probe)
   public_rejection=False
   if not probe_result['accepted']:
    before_rejection=dict(ca.counts)
    try:adapter.fun(y)
    except ValueError:public_rejection=not adapter.ledger.entries and ca.counts==before_rejection
    else:raise AssertionError('inexact public state evaluated')
   traversals=[]
   for repeat in (0,1):
    values={}
    for field in order:
     values[field]=accounting.public_call(adapter,field,y) if probe_result['accepted'] else adapter.request(field)
    traversals.append(values)
    if repeat==0:before_repeat=dict(ca.counts)
   cache_repeated_no_entries=ca.counts==before_repeat
   if not cache_repeated_no_entries:raise ValueError('repeat entered numerical work')
   if operand_digest(traversals[0])!=operand_digest(traversals[1]):raise ValueError('cache repeat mutated')
   returned=solver.owned_report(adapter);assert returned is solver.owned_report(adapter)
   extra=None;transform_hit=False
   if seq==5:
    def forbidden_transform():raise AssertionError('repeated transform entered math')
    transform_hit=transform_cache.request(forbidden_transform) is transform
    assert transform_hit and transform_cache.requests==2
    extra=returned;returned=ca('extra_transport',lambda:accounting.report(adapter.values,ret,scale,savedP,inverse))
   save(f'candidate-{ci}-returned-{seq}.json.gz',dict(report=returned,extra_newP=extra,probe=probe_result,public_rejection=public_rejection,canonical_identity=adapter.input,owned_state_identity=adapter.state.identity,cache_repeated_no_entries=cache_repeated_no_entries,requests=adapter.requests,public_requests=adapter.public_requests,traversal_order=order,public_returns=traversals if probe_result['accepted'] else [],canonical_returns=traversals if not probe_result['accepted'] else [],transform_repeated_cache_hit=transform_hit,owned_states=len(adapter.ledger.states),owned_iterations=adapter.ledger.iterations))
   save(f'public-{ci}-{seq}.json',probe_result)
  print('candidate case',ci,'complete',flush=True)
 save('candidate-closed.json',dict(counts=ca.counts,monotonic=time.monotonic()))
 del cinputs,setups,model,adapter,out,returned,cold_report,transform,extra
 rinputs=read(ROOT/'reference-inputs/inputs.json');ra=Audit('reference',end,source_map,ROOT/'entries.jsonl');rsetups={}
 for w in (0,1):
  ra.context_set('setup/'+str(w),{});base=rinputs['cases'][0];operands=dict(knots_hex=base['knots_hex'],quadrature_hex=base['quadrature_hex'],weight=w)
  rsetups[w]=setup_entry(ra,**operands,expected=operands,calculator=lambda w=w:reference.setup(base['knots_hex'],base['quadrature_hex'],w,ra.check));save('reference-setup-'+str(w)+'.json',rsetups[w])
 for c in rinputs['cases']:
  model=reference.Reference(c,rsetups[c['weight']],ra.check);ra.bind_operands(c,rsetups[c['weight']]);m=c['dimension'];scale=reference.arr(c['scale_hex'])
  for state in c['slots']:
   label=state['label'];ra.context_set(f'{c["index"]}/{label}',state);out=ra('complete',lambda:model.evaluate(state,ra))
   P=np.eye(m) if label=='cold' else reference.arr(c['P_hex']).reshape(m,m);inverse=np.eye(m) if label=='cold' else ra('saved_inverse',lambda:np.linalg.inv(P))
   result=ra('cold_report' if label=='cold' else 'report',lambda:reference.report(out,state,scale,P,inverse));save(f'reference-{c["index"]}-{label}.json.gz',result)
  print('reference case',c['index'],'complete',flush=True)
 save('reference-closed.json',dict(counts=ra.counts,monotonic=time.monotonic()));del model,rsetups,out,result
 da=Audit('driver',end,source_map,ROOT/'entries.jsonl',caps=dict(component_comparison=32,newP_comparison=16));summary=[];archive=read(ROOT/'archive.json')
 for c in rinputs['cases']:
  for label in ('cold','returned'):
   state=c['slots'][0 if label=='cold' else 1];da.context_set(f'{c["index"]}/{label}',state)
   def component_context():
    ref=read(ROOT/f'reference-{c["index"]}-{label}.json.gz');spec=comparison_spec(c['dimension'],c['n'],3*c['nacc'] if c['weight'] else 0,label,len(c['problem']['free']));P=np.eye(c['dimension']) if label=='cold' else reference.arr(c['P_hex']).reshape(c['dimension'],c['dimension'])
    exact_oracle=rational_oracle(ref,P,da.check)
    for seq in ([0] if label=='cold' else range(1,6)):
     saved=read(ROOT/(f'candidate-{c["index"]}-cold.json.gz' if not seq else f'candidate-{c["index"]}-returned-{seq}.json.gz'));cand=saved if not seq else saved['report'];checks=comparisons(cand,ref,spec,da.check)
     checks.update(rational_checks(cand,ref,exact_oracle,da.check))
     if seq:
      # S5 wrapper outputs are compared once in its allocated new-P context.
      if seq<5:checks.update(public_checks(saved,ref,spec,da.check))
      checks.update({'saved_transform/'+k:v for k,v in transform_checks(dict(P=P,inverse=read(ROOT/('entry-output-candidate_'+str(c['index'])+'_returned_'+str(seq)+'_saved_inverse_1.json.gz'))),len(c['problem']['free']),da.check).items()})
     path=f'comparison-{c["index"]}-{label}-{seq}.json.gz';save(path,checks);summary.append(dict(path=path,failed_checks=[k for k,v in checks.items() if not v['passed']]))
    if label=='returned':save(f'historical-{c["index"]}.json.gz',historical_comparisons(archive[c['index']],ref,spec,da.check))
    return dict(case=c['index'],label=label,completed=True)
   da('component_comparison',component_context)
 for c in rinputs['cases']:
  i=c['index'];da.context_set(f'{i}/newP',c['slots'][1])
  def new_context():
   transform=read(ROOT/f'transform-{i}.json.gz');saved=read(ROOT/f'candidate-{i}-returned-5.json.gz');ref=read(ROOT/f'reference-{i}-returned.json.gz');spec=comparison_spec(c['dimension'],c['n'],3*c['nacc'] if c['weight'] else 0,'returned',len(c['problem']['free']))
   transported=transport_reference(ref,transform['P'],da.check);exact_oracle=rational_oracle(ref,transform['P'],da.check)
   checks=newp_comparisons(saved['extra_newP'],ref,transform,spec,len(c['problem']['free']),da.check,transported);checks.update(rational_checks(saved['extra_newP'],ref,exact_oracle,da.check))
   if saved['probe']['accepted']:checks.update(public_checks(saved,transported,spec,da.check))
   save(f'newP-comparison-{i}.json.gz',checks);summary.append(dict(path=f'newP-comparison-{i}.json.gz',failed_checks=[k for k,v in checks.items() if not v['passed']]))
   return dict(case=i,completed=True)
  da('newP_comparison',new_context)
 save('comparison-summary.json',summary);save('worker-complete.json',dict(monotonic=time.monotonic(),candidate_counts=ca.counts,reference_counts=ra.counts,driver_counts=da.counts))



def launch_readiness(root=ROOT,authorization=AUTH):
 return verify_chain('run',root,authorization)


def run():
 launch_readiness();ready=read(ROOT/'readiness.json')
 start=time.monotonic();auth=read(AUTH);end=min(start+1500,auth['deadlines']['scientific_cleanup']['monotonic']);token=os.urandom(32).hex()
 publish(ROOT/'started.json',dict(start_monotonic=start,deadline_monotonic=end,token=token,supervisor_pid=os.getpid(),supervisor_identity=process_identity(),authorization_sha256=sha(AUTH),admission_sha256=sha(ROOT/'admission.json'),readiness_sha256=sha(ROOT/'readiness.json')))
 os.environ['V15_TOKEN']=token
 budget=supervise([PYTHON,str(SCRIPT),'worker'],end,ROOT/'worker.log',ROOT/'process.json');budget.update(phase_elapsed_seconds=time.monotonic()-auth['t0_monotonic'],scientific_invocations=1,training_seconds=0,forbidden_entries=0)
 publish(ROOT/'budget.json',budget);print(json.dumps(budget),flush=True)
 if not budget['worker_stopped'] or budget['remaining_live_descendants']:raise RuntimeError('cleanup incomplete')


def check_names(spec):
 result=[]
 for path,rule in spec.items():
  result.append(path)
  if rule['exact']:result.append(path+'/exact_zero')
  if rule.get('zero_prefix',0):result.append(path+'/offset_zero')
  if path.split('.')[-1] in ('H','Hdata','Hacc','Hz','Hg'):result += [path+'/candidate_symmetry',path+'/reference_symmetry']
 return result


def expected_schedule(cases):
 entries=[];observed=[];operands={};outputs={};checks={}
 actual_kinds={'prepare','objective_residual','residual_only','acceleration','data_hessian','full_sum','raw_depth','bounded_values','weighted_raw_hessian','bounded_curvature'}
 def context(method,name,kinds,state=None,case=None):
  for ordinal,kind in enumerate(kinds,1):
   identity='/'.join((method,name,kind,str(ordinal)));entries.append(identity)
   if kind in actual_kinds:
    observed.append(identity);operands[identity]={k:state.get(k) for k in ('q_hex','x_hex','vg_hex','vby_hex','scope')}
    operands[identity].update(coefficient_hex=state['x_hex'][16*len(case['problem']['free']):],case_sha256=operand_digest(case))
 def components(method,w):
  first=['complete','prepare','objective_residual']
  middle=(['acceleration'] if w else [])+['data_hessian'] if method=='candidate' else ['data_hessian']+(['acceleration'] if w else [])
  return first+middle+['full_sum','raw_depth','bounded_values','weighted_raw_hessian','bounded_curvature']
 for method in ('candidate','reference'):
  for w in (0,1):context(method,'setup/'+str(w),['setup'])
  for c in cases:
   i=c['index'];cold,ret=c['slots'];w=c['weight'];base=components(method,w)
   context(method,f'{i}/cold',base+['cold_report'],cold,c);outputs[f'{method}-{i}-cold.json.gz']='schedule'
   if method=='candidate':
    for seq in range(1,6):
     if seq==5:context(method,f'{i}/transform',['transform_context','prepare','residual_only']+(['acceleration'] if w else [])+['svd_transform'],cold,c)
     context(method,f'{i}/returned/{seq}',['saved_inverse','public_probe']+base+['report']+(['extra_transport'] if seq==5 else []),ret,c)
     outputs[f'candidate-{i}-returned-{seq}.json.gz']='schedule';outputs[f'public-{i}-{seq}.json']='public_api'
    outputs[f'transform-{i}.json.gz']='schedule'
   else:context(method,f'{i}/returned',base+['saved_inverse','report'],ret,c);outputs[f'reference-{i}-returned.json.gz']='schedule'
 for c in cases:
  i=c['index']
  for label in ('cold','returned'):
   context('driver',f'{i}/{label}',['component_comparison'])
   spec=comparison_spec(c['dimension'],c['n'],3*c['nacc'] if c['weight'] else 0,label,len(c['problem']['free']))
   for seq in ([0] if label=='cold' else range(1,6)):
    path=f'comparison-{i}-{label}-{seq}.json.gz';outputs[path]='canonical';checks[path]=check_names(spec)
    if c['weight']:checks[path]+=['rational/Facc']+[f'rational/{f}/{k}' for f in ('x','q','y') for k in ('Gacc','Hacc')]
    if seq:checks[path]+=['saved_transform/'+k for k in ('inverse_left','inverse_right','symmetry','nuisance_exact')]
  path=f'historical-{i}.json.gz';outputs[path]='historical';checks[path]=['objective','G','C_depth','C_bounds','KKT','optimality','complementarity_original','multipliers_depth','bound_multipliers']
 for c in cases:
  i=c['index'];context('driver',f'{i}/newP',['newP_comparison']);path=f'newP-comparison-{i}.json.gz';outputs[path]='transform';spec=comparison_spec(c['dimension'],c['n'],3*c['nacc'] if c['weight'] else 0,'returned',len(c['problem']['free']));checks[path]=check_names(spec)+['transform/'+k for k in ('inverse_left','inverse_right','symmetry','nuisance_exact','coverage','inactive_scale_exact')]+['remapped_multiplier','remap_back']
  if c['weight']:checks[path]+=['rational/Facc']+[f'rational/{f}/{k}' for f in ('x','q','y') for k in ('Gacc','Hacc')]
 replays={}
 for c in cases:
  for seq,order in enumerate(ORDERS,1):
   replays[f'candidate-{c["index"]}-returned-{seq}.json.gz']=dict(order=order,state=c['slots'][1],comparison=f'comparison-{c["index"]}-returned-{seq}.json.gz' if seq<5 else f'newP-comparison-{c["index"]}.json.gz',dimension=c['dimension'],n=c['n'],acc_rows=3*c['nacc'] if c['weight'] else 0,nf=len(c['problem']['free']))
 return dict(entries=entries,observed=observed,operands=operands,outputs=outputs,checks=checks,replays=replays,cases=cases)


def package():
 deadline('phase');ROOT.mkdir(exist_ok=True);source_failures=[]
 try:
  verify_chain('worker' if (ROOT/'started.json').exists() else 'run' if (ROOT/'readiness.json').exists() else 'toy' if (ROOT/'frozen.json').exists() else 'admission')
 except (ValueError,FileNotFoundError,AssertionError,KeyError) as exc:source_failures.append(type(exc).__name__+': '+str(exc))
 suites=[read(p) for p in sorted(ROOT.glob('toy-suite-??-result.json'))]
 entries=[json.loads(v) for v in (ROOT/'entries.jsonl').read_text().splitlines()] if (ROOT/'entries.jsonl').exists() else []
 observed=[json.loads(v) for v in (ROOT/'actual-entries.jsonl').read_text().splitlines()] if (ROOT/'actual-entries.jsonl').exists() else []
 manifest={str(p):sha(p) for p in ROOT.rglob('*') if p.is_file() and p.name not in ('decision.json','package-validation.json','evidence-manifest.json')}
 try:expected=read(ROOT/'expected-schedule.json')
 except (ValueError,FileNotFoundError,KeyError) as exc:
  expected=dict(entries=['missing fixed schedule'],outputs={'missing fixed schedule':'canonical'},checks={});source_failures.append(str(exc))
 outputs={};invalid_artifacts=[]
 for path in expected['outputs']:
  if not (ROOT/path).exists():continue
  try:outputs[path]=read(ROOT/path)
  except (ValueError,OSError) as exc:invalid_artifacts.append(dict(path=path,error=str(exc)))
 hashmap={**manifest,**{p:sha(ROOT/p) for p in outputs}}
 receipts=[json.loads(v) for v in (ROOT/'artifacts.jsonl').read_text().splitlines()] if (ROOT/'artifacts.jsonl').exists() else []
 retained=dict(entries=entries,observed=observed,output_receipts=receipts,outputs=outputs,hashes=hashmap,ready=(ROOT/'readiness.json').exists(),summary_present=(ROOT/'comparison-summary.json').exists())
 decision=validate_package(expected,retained)
 if not (ROOT/'budget.json').exists():publish(ROOT/'budget.json',dict(scientific_invocations=0,scientific_seconds=0,worker_stopped=True,remaining_live_descendants=[],within_deadline=True,exit_code=None,training_seconds=0,forbidden_entries=0,toy_suites=len(suites),toy_seconds=sum(read(p)['wall_seconds'] for p in ROOT.glob('toy-suite-??-supervision.json')),phase_elapsed_seconds=time.monotonic()-read(AUTH)['t0_monotonic']))
 budget=read(ROOT/'budget.json')
 if not budget['worker_stopped'] or budget['remaining_live_descendants'] or not budget['within_deadline'] or (budget['scientific_invocations'] and budget['exit_code']!=0):decision['dimensions']['schedule']['failures'].append('unconfirmed process cleanup');decision['dimensions']['schedule']['complete']=False;decision=reduce_decision(decision['dimensions'])
 if invalid_artifacts:decision['dimensions']['package_integrity']['failures']+=invalid_artifacts
 if source_failures:decision['dimensions']['source_coverage']['failures']+=source_failures;decision=reduce_decision(decision['dimensions'])
 publish(ROOT/'decision.json',decision)
 publish(ROOT/'package-validation.json',dict(passed=not decision['dimensions']['package_integrity']['failures'],complete=decision['status']!='incomplete',entered=sum(e['event']=='entry' for e in entries),completed=sum(e['event']=='completed' for e in entries),interrupted=sum(e['event']=='interrupted' for e in entries),missing_artifacts=[p for p in expected['outputs'] if p not in outputs],consumed_toy_slots=[p.name for p in ROOT.glob('toy-suite-??-consumed.json')],source_failures=source_failures,phase_elapsed_seconds=time.monotonic()-read(AUTH)['t0_monotonic']))
 manifest={str(p):sha(p) for p in ROOT.rglob('*') if p.is_file() and p.name!='evidence-manifest.json'};publish(ROOT/'evidence-manifest.json',manifest)
 print(json.dumps(dict(status=decision['status'],known_required_failure=decision['known_required_failure'])),flush=True)


if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('command',choices=['admit','toy','ready','run','package','worker','toy-worker']);args=parser.parse_args();globals()[args.command.replace('-','_')]()
