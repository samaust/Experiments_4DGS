#!/usr/bin/env python3
"""Plan021 immutable admission, one owned pass, and retained-only packaging."""
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

ROOT=Path('docs/experiments/basketball-shared-timing-v14')
AUTH=Path('docs/continuous-improvement/20260908-plan016/iteration-005-plan021-authorization.json')
SCRIPT=Path('scripts/basketball_shared_evaluator_v14.py')
TEST=Path('tests/test_basketball_shared_evaluator_v14.py')
PYTHON='.local/envs/calibration-global/bin/python'
THREADS={k:'1' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')}
SOURCES=[Path('scripts')/(s+'_v14.py') for s in ('basketball_acceleration_decimal','basketball_shared_components','basketball_shared_accounting','basketball_shared_solver','basketball_shared_reference','basketball_shared_evaluator')]
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
 publish(ROOT/'archive.json',archive);publish(ROOT/'provenance.json',provenance)
 publish(ROOT/'historical-sources.json',dict(historical=historic,v11=v11src,substitutions=[dict(path=p,old_sha256=h,replacement_sha256=v11src[p],attestation=str(old/'execution-sources.json')) for p,h in historic.items() if p in v11src and h!=v11src[p]],pinned=pinned))
 publish(ROOT/'environment.json',environment)
 (ROOT/'admission-source.py').write_bytes(SCRIPT.read_bytes())
 deadline('admission')
 publish(ROOT/'admission.json',dict(passed=True,cases=16,slots=32,scientific_entries=0,admitted_monotonic=time.monotonic(),authorization_sha256=sha(AUTH),source_sha256=sha(ROOT/'admission-source.py'),inputs_sha256={name:sha(ROOT/name/'inputs.json') for name in ('candidate-inputs','reference-inputs')},environment_sha256=sha(ROOT/'environment.json'),historical_sha256=sha(ROOT/'historical-sources.json'),provenance_sha256=sha(ROOT/'provenance.json')))
 print('Admission passed: 16 cases, 32 immutable states; zero scientific entries.',flush=True)

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('command',choices=['admit','ready','run','package','worker']);args=parser.parse_args();globals()[args.command]()
