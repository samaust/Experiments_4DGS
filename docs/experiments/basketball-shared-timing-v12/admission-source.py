#!/usr/bin/env python3
"""Plan 019 immutable exact acceleration evidence; scientific work only in worker."""
import argparse
import functools
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
from fractions import Fraction as F

ROOT = Path('docs/experiments/basketball-shared-timing-v12')
OLD = Path('docs/experiments/basketball-shared-timing-v11')
AUTH = Path('docs/continuous-improvement/20260908-plan016/iteration-003-plan019-authorization.json')
SCRIPT = Path('scripts/basketball_acceleration_reference_v12.py')
CONTROL = Path('scripts/basketball_acceleration_control_v12.py')
TEST = Path('tests/test_basketball_acceleration_reference_v12.py')
THREADS = {k:'1' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')}
PINNED = dict(zip(('inputs.json','rays.json','probes.json.gz','primary.jsonl','independent.jsonl','admission.json','execution-sources.json','verification.json','verification-failures.json','budget.json'),('7a4b5aebeb5652051298ab88103a44af63a13ed69163eda988b333169cdf11f0','f8d0aad1f2b7f3a3de991bdab68ca3d1f37bc2306e06b7321a0f6491f8305a8c','f386896d04ad764fa17ae7b487fe30504a3967179d26e5b21c4e','f544aab2fc6f18ee22076128761a826865613c2a71836514a9b7a2821a2c8fd5','39cf317220fe6fd7b4e4b773e75b8462e2acac09de3dec1eeb6352e08c582a57','f262a40682dac776dfaacb36792f171a055ed21b63c3edf1dc3473efa9453268','285845798284eecc2b421da25f4c435fcedd18e5705d51c15b68b3f62904f50a','4be416f5567f35da5aa549770ef5392e45700c9d271f21cf1a7e986db094f944','672284899958ad7aa790e58d5a3d79d0291eb3a4034039561eb34c3f83cfb3b0','2c2c488b6ed60257216e81f8e9b7809f431651319109a39dd3dd422b375abeca')))
# The complete digest is deliberately fixed, never inferred from current bytes.
PINNED['probes.json.gz']='f386896d04ad764fa17ae7b487fe30504a3967179f026347c1979d26e5b21c4e'
SLOTS = [(f'metric/conditional-{case}/cold/ray/{ray}/amplitude/{exponent}',group,digest) for case,ray,group,hashes in [('03','0/1',2,['769ea991fdd2cf581d162e0487e459953b4b2620dd24eaf0932372e8c94642b4','57d287a53d42eca3249f20ddb68ae1bf113a61f9b3126249052ac978ed57f4bf']),('10','2/-1',9,['7adfdfa02ca0c938ff2f32edc1e3af1ca403dc5770d16679892e0542a312f40c','3592cd5f894a29a851a1950720dbb550017db1c6ba197847e7df61607ba0f8ef']),('16','2/-1',11,['53e4de694aa7bd54b0716315cd5c84cd602954befafbaedb300ca6bac95e5542','59944338d4e2729e044de9a91afecf00e0f3e718d502871bc5b8bb000822f2f8'])] for exponent,digest in zip((4,44),hashes)]

def encode(x): return (json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def read(p): return json.loads(Path(p).read_text())
def sha(p):
    p=Path(p)
    if 'prompts' in p.parts: raise ValueError('excluded path')
    return hashlib.sha256(p.read_bytes()).hexdigest()
def publish(p,x):
    with Path(p).open('xb') as f: f.write(encode(x)); f.flush(); os.fsync(f.fileno())
def hashes(mapping):
    for p,h in mapping.items():
        if sha(p)!=h: raise ValueError('source mutation: '+str(p))
def fhex(v): return struct.pack('<'+'d'*len(v),*v).hex()
def state_bytes(h,digest,size):
    b=bytes.fromhex(h)
    if len(b)!=size or hashlib.sha256(b).hexdigest()!=digest: raise ValueError('state identity')
    if not all(math.isfinite(x) for x in struct.unpack('<'+'d'*(size//8),b)): raise ValueError('nonfinite state')
    return b
def deadline(auth,key):
    if time.monotonic()>=auth['deadlines'][key]['monotonic']: raise TimeoutError(key)
def chain(p):
    prev='0'*64; out=[]
    for line in Path(p).read_bytes().splitlines(keepends=True):
        if not line.endswith(b'\n'): raise ValueError('partial chain')
        e=json.loads(line); checksum=e.pop('checksum')
        if e['seq']!=len(out) or e['previous']!=prev or hashlib.sha256(encode(e).rstrip(b'\n')).hexdigest()!=checksum: raise ValueError('chain integrity')
        e['checksum']=checksum;out.append(e);prev=checksum
    if not out: raise ValueError('empty chain')
    return out
def support(frames,offsets,ends):
    times=[(F(frame)-F(offsets[str(camera)]))/25 for camera,frame in frames]
    if not times or any(t<2 or any(t<=end for end in ends) for t in times): raise ValueError('support overlap')
    return {'observations':len(times),'minimum_time':rat(min(times)),'support_ends':[rat(x) for x in ends],'strictly_separated':True,'image_and_depth_partials_exact_zero':[0,1,2,3,4,5]}
def rat(x): return [str(x.numerator),str(x.denominator)]
def unrat(x): return F(int(x[0]),int(x[1]))

def admit():
    auth=read(AUTH);deadline(auth,'admission')
    if ROOT.exists(): raise FileExistsError('output collision')
    hashes({str(OLD/k):v for k,v in PINNED.items()})
    original=read(OLD/'inputs.json'); sources=read(OLD/'execution-sources.json')['sha256']
    hashes(original['historical_sha256']);hashes(sources)
    probes=json.loads(gzip.decompress((OLD/'probes.json.gz').read_bytes()))['records'];rays=read(OLD/'rays.json')['rays']
    journals={m:[json.loads(l) for l in (OLD/(m+'.jsonl')).read_text().splitlines()] for m in ('primary','independent')}
    states=[]; cases={};certificates={}
    for slot,group,digest in SLOTS:
        probe=[r for r in probes if r['slot']==slot];assert len(probe)==1;probe=probe[0]
        state_bytes(probe['physical_hex'],digest,432)
        case_id=slot.split('/ray/')[0];case=next(c for c in original['cases'] if c['id']==case_id)
        ray=next(r for r in rays if r['id']==slot.split('/amplitude/')[0]);assert ray['case']==case_id
        if case_id not in cases:
            row=case['row'];problem=row['accounting']['problem']
            assert case['group']==group and case['weight']==row['weight']==problem['weight']==1
            assert row['window']==problem['window']==[50,149] and row['spacing']==problem['spacing']==10
            assert problem['free']==[] and problem['offsets']=={'1':0.0,'2':-25.0,'3':-25.0}
            assert row['group_ids']==[group] and len(row['knots'])==22
            assert problem['provenance']==case['identity']
            events=chain(Path(case['directory'])/'journal.jsonl')
            assert [e['identity'] for e in events if e['event']=='allocated']==[case['identity']]
            assert len([e for e in events if e['event']=='completed'])==1
            assert [e['problem'] for e in events if e['event']=='problem']==[problem]
            assert hashlib.sha256(json.dumps(problem,sort_keys=True).encode()).hexdigest()==row['accounting']['problem_key']
            hashes(case['identity']['execution_sha256'])
            assert len(problem['observations'])==1 and problem['observations'][0]['group_id']==group
            frames=[(o['camera_id'],f) for o in problem['observations'][0]['observations'] for f in o['frames']]
            ends=[F.from_float(v) for v in row['knots'][4:6]]
            assert row['knots'][4:6]==[1.4,1.7999999999999998]
            certificates[case_id]=support(frames,problem['offsets'],ends)
            cases[case_id]=case
        archived={};ownership={}
        for method,events in journals.items():
            selected=[e for e in events if e.get('slot')==slot]
            assert [(e['event'],e.get('kind')) for e in selected]==[('allocated',None),('entry','depth'),('return','depth'),('entry','residual'),('return','residual'),('completed',None)]
            assert all(e['pass_name']==method for e in selected)
            assert all(e['physical_hex']==probe['physical_hex'] for e in selected if 'physical_hex' in e)
            result=selected[-1]['result'];assert result['physical_hex']==probe['physical_hex'] and result['status']=='finite'
            assert len(result['G'])==54 and all(math.isfinite(x) for x in result['G'])
            assert result['minimum_depth']==min(result['depths']) and result['minimum_depth']>1e-8
            assert all(math.isfinite(x) for x in result['depths'])
            for field in ('objective','data_objective','acceleration_cost'): assert math.isfinite(result[field])
            if method=='primary':
                for field in ('G','depths','minimum_depth','objective','data_objective','acceleration_cost','physical_hex'): assert probe[field]==result[field]
            archived[method]=result;ownership[method]=selected
        states.append(dict(slot=slot,group=group,physical_hex=probe['physical_hex'],physical_sha256=digest,case=case_id,ray=ray,archived=archived,archived_journal=ownership))
    definitions=[(fhex(c['row']['knots']),c['row']['window'],c['weight']) for c in cases.values()];assert all(d==definitions[0] for d in definitions)
    deadline(auth,'admission');ROOT.mkdir()
    publish(ROOT/'inputs.json',dict(states=states,cases=cases,knots_hex=definitions[0][0],window=[50,149],weight=1,historical_sha256=original['historical_sha256'],v11_sources=sources))
    with (ROOT/'original-v11-failures.json').open('xb') as f:f.write((OLD/'verification-failures.json').read_bytes())
    publish(ROOT/'admission.json',dict(passed=True,admitted_monotonic=time.monotonic(),authorization_sha256=sha(AUTH),inputs_sha256=sha(ROOT/'inputs.json'),pinned_sha256={str(OLD/k):v for k,v in PINNED.items()},support_certificates=certificates,states=6,scientific_entries=0,source_sha256=sha(SCRIPT)))
    print('Admission passed: six states; zero scientific entries',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['admit','run','package','worker']);args=parser.parse_args()
    if args.command=='admit':admit()
    else:raise RuntimeError('not implemented; no scientific entry')
