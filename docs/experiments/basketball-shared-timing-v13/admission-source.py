#!/usr/bin/env python3
"""Plan 019 immutable exact acceleration evidence; scientific work only in worker."""
import argparse
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

ROOT = Path('docs/experiments/basketball-shared-timing-v13')
OLD = Path('docs/experiments/basketball-shared-timing-v12')
AUTH = Path('docs/continuous-improvement/20260908-plan016/iteration-004-plan020-authorization.json')
SCRIPT = Path('scripts/basketball_acceleration_candidate_v13.py')
CONTROL = Path('scripts/basketball_acceleration_decimal_v13.py')
TEST = Path('tests/test_basketball_acceleration_candidate_v13.py')
THREADS = {k:'1' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')}
PINNED = {'inputs.json': '022552d14297dba718d7ee9f758e54c0827a72d8a246305cb3cec0f2c442f897', 'admission.json': '1fe783903e0b83dcc421a172f0c5e7def8e970c74cba49220b10c52255058513', 'A-setup.json': '5bfcfc40889306a87188a61c544f0af84e29ba6bb9647e521da800dec8b657bd', 'B-setup.json': '77c30063aa6d382ca2415471156292893e90810b09b2da54d4e47f644946deb9', 'comparisons.json': '7d3f6d4925e5fb0f9d6507c41a236dbc96b91cf3feffd1beffe9caacd5b071f1', 'decision.json': '8e4211665ae25d09401241944b768f18db4e3ed00f150d7310fd7f9537167105', 'package-validation.json': '59191f1d93dc7ddfc92e7ca54ebaec4d1d40779a413342129d383043dbb9a367', 'execution-sources.json': '023fe33a35af2066829539f930c235ff7fca4ea0b1ec4dbcc054ef45369b9bc4', 'budget.json': '713a664392cb16be80fccace52b2e0b252ad551b56f0473ca2cb0da716da6553', 'entries.jsonl': 'bfff876073c7e79b449c028a1e282a49805e1e9c80bed7a5bf8f5a30c550b4a8', 'original-v11-failures.json': '672284899958ad7aa790e58d5a3d79d0291eb3a4034039561eb34c3f83cfb3b0', 'A-0.json': '359b8ca2ce9c6663f9354633cdd199b7bddd2fab9a7e3f4f3cf4ca392389ba9d', 'B-0.json': '145ece8be66ec6cc751b662d17f5e8b5ea3c9e374801c41afefe09ef73ec4086', 'A-1.json': 'bf2aeb91ac8a80686641d8f059ec15a017e6a9fdcae517753042aee2a394fa21', 'B-1.json': 'e1061b356d2a0a6332f700942d8534e2d52ee37dacdbe5dd16e173c981d41354', 'A-2.json': 'd345a3f7e3fbf4e9368e80f6bf698bcb4ebb3fa2501c04ab6b985616c9de5774', 'B-2.json': '22580810f78b675be319d6346483b9c7371ae7174e842ed5e7280dbfc634e657', 'A-3.json': '55a5f266fc61a1e3ea2e54d9b904861b183002b506fca4933c33b33743c925e4', 'B-3.json': 'b47b97e478ee774934394a1ec0f1dbb88a6b76641acfb64ffb4df09329c3afc6', 'A-4.json': 'd0f8dc2e9d94121c8b19cc8af335882306f6424c122f3220f63057ac11616d2a', 'B-4.json': '5ce140d62481248c67ed6e28d9d12fb6ba0674a5061ae08500ccf4ce2192bcd4', 'A-5.json': '812250b5daeeae57e5e0304bac2bfea10e0dd472032376ca31f09d4c6ee2b4b8', 'B-5.json': '5c7a4c671c016b16033bd890104227274560dd11e85921017a70750a48c00da9'}
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

class Ledger:
    """Entry ownership is consumed before callbacks, including failing callbacks."""
    def __init__(self,schedule,deadline_value,path=None,cap=6):
        self.schedule=schedule;self.deadline=deadline_value;self.path=path;self.cap=cap;self.used=[]
    def enter(self,method,slot,physical_hex,callback):
        if time.monotonic()>=self.deadline:raise TimeoutError('entry deadline')
        key=method+'/'+slot
        if key not in self.schedule or self.schedule[key]!=physical_hex:raise ValueError('unallocated/wrong method/physical bytes')
        if key in self.used or len(self.used)>=self.cap:raise ValueError('consumed allocation/cap')
        self.used.append(key)
        if self.path:event(self.path,event='entry',method=method,slot=slot,physical_hex=physical_hex,entry_count=len(self.used))
        out=callback()
        if time.monotonic()>=self.deadline:raise TimeoutError('return deadline')
        return out

def event(path,**record):
    record.update(monotonic=time.monotonic(),pid=os.getpid(),pgid=os.getpgrp())
    with Path(path).open('ab') as f:f.write(encode(record));f.flush();os.fsync(f.fileno())

def process_identity():
    return {'pid':os.getpid(),'pgid':os.getpgrp(),'sid':os.getsid(0),'pid_namespace':os.readlink('/proc/self/ns/pid'),'namespace_status':[l for l in Path('/proc/self/status').read_text().splitlines() if l.startswith(('NSpid:','NSpgid:','NSsid:'))]}

def supervise(command,end,log,identity_path=None,interrupt_after=None):
    """Own and reap a child session. Deadline includes startup and cleanup."""
    begin=time.monotonic();p=None;reason=None;termination=None
    def interrupted(signum,frame):raise KeyboardInterrupt('signal '+str(signum))
    old={s:signal.signal(s,interrupted) for s in (signal.SIGTERM,signal.SIGINT)}
    try:
        with Path(log).open('xb') as stream:
            p=subprocess.Popen(command,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True,env={**os.environ,**THREADS})
            ident={'supervisor':process_identity(),'child_pid':p.pid,'child_pgid':p.pid,'child_pid_namespace':os.readlink('/proc/'+str(p.pid)+'/ns/pid'),'command':command}
            if identity_path:publish(identity_path,ident)
            while p.poll() is None:
                now=time.monotonic()
                if now>=end-2:reason='timeout';break
                if interrupt_after is not None and now-begin>=interrupt_after:reason='interrupted';break
                time.sleep(min(.02,max(.001,end-2-now)))
    except BaseException as exc:
        reason=type(exc).__name__+': '+str(exc)
    finally:
        if p is not None and p.poll() is None:
            termination=time.monotonic();os.killpg(p.pid,signal.SIGTERM)
            try:p.wait(timeout=max(0,min(1,end-time.monotonic()-.2)))
            except subprocess.TimeoutExpired:
                os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=max(.01,end-time.monotonic()))
        for s,h in old.items():signal.signal(s,h)
    finish=time.monotonic()
    return {'start_monotonic':begin,'end_monotonic':finish,'wall_seconds':finish-begin,'deadline_monotonic':end,'exit_code':None if p is None else p.returncode,'reason':reason,'worker_stopped':p is not None and p.poll() is not None,'child_pid':None if p is None else p.pid,'termination_monotonic':termination,'cleanup_seconds':0 if termination is None else finish-termination,'within_deadline':finish<=end}

def worker_guard(started,provided,parent_pid,allocation_path):
    if not provided or provided!=started.get('token') or parent_pid!=started.get('supervisor_pid'):raise ValueError('direct worker rejected')
    publish(allocation_path,{'consumed':True,'pid':os.getpid(),'monotonic':time.monotonic()})


def admit():
    auth=read(AUTH);deadline(auth,'admission')
    if ROOT.exists():raise FileExistsError('output collision')
    hashes({str(OLD/k):v for k,v in PINNED.items()})
    prior=read(OLD/'inputs.json');ad=read(OLD/'admission.json')
    hashes(prior['historical_sha256']);hashes(prior['v11_sources'])
    hashes(read(OLD/'execution-sources.json')['sha256']);hashes(read(OLD/'readiness.json')['sha256'])
    hashes(ad['pinned_sha256'])
    assert sha(OLD/'admission-source.py')==ad['source_sha256']
    assert sha('docs/continuous-improvement/20260908-plan016/iteration-003-plan019-authorization.json')==ad['authorization_sha256']
    assert read(OLD/'package-validation.json')['passed'] and read(OLD/'decision.json')['reference_plan_complete']
    assert read(OLD/'comparisons.json')['exact_references_agree']
    decision=read(OLD/'decision.json')
    assert decision['gradient_counts']['primary']['outside_tolerance']==25
    assert decision['gradient_counts']['independent']['outside_tolerance']==17
    assert all(decision['cost_counts'][m]['within_tolerance']==6 for m in ('primary','independent'))
    setups=[read(OLD/(m+'-setup.json')) for m in ('A','B')]
    assert setups[0]['knots_hex']==setups[1]['knots_hex']==prior['knots_hex']
    assert setups[0]['quadrature_hex']==setups[1]['quadrature_hex']
    for h,n in [(prior['knots_hex'],22),(setups[0]['quadrature_hex'],150)]:
        raw=bytes.fromhex(h);assert len(raw)==n*8 and all(map(math.isfinite,struct.unpack('<'+str(n)+'d',raw)))
    events=[json.loads(l) for l in (OLD/'entries.jsonl').read_text().splitlines()]
    assert [(e['event'],e['method']) for e in events if e['event'].startswith('setup')]==[('setup_entry','A'),('setup_return','A'),('setup_entry','B'),('setup_return','B')]
    expected=[(m,s[0]) for m in ('A','B') for s in SLOTS]
    assert [(e['method'],e['slot']) for e in events if e['event']=='entry']==expected
    assert [(e['method'],e['slot']) for e in events if e['event']=='completed']==expected
    states=[];oracles=[];certificates={}
    for i,((slot,group,digest),state) in enumerate(zip(SLOTS,prior['states'])):
        assert (state['slot'],state['group'],state['physical_sha256'])==(slot,group,digest)
        state_bytes(state['physical_hex'],digest,432)
        case=prior['cases'][state['case']];row=case['row'];problem=row['accounting']['problem']
        assert case['group']==group and case['weight']==row['weight']==problem['weight']==1
        assert row['window']==problem['window']==[50,149] and row['spacing']==problem['spacing']==10
        assert problem['free']==[] and problem['offsets']=={'1':0.0,'2':-25.0,'3':-25.0}
        assert row['group_ids']==[group] and fhex(row['knots'])==prior['knots_hex']
        assert state['ray']['case']==state['case'] and state['ray']['id']==slot.split('/amplitude/')[0]
        frames=[(o['camera_id'],f) for o in problem['observations'][0]['observations'] for f in o['frames']]
        cert=support(frames,problem['offsets'],list(map(F.from_float,row['knots'][4:6])))
        assert cert==ad['support_certificates'][state['case']];certificates[state['case']]=cert
        for archived in state['archived'].values():
            assert all(map(math.isfinite,archived['depths'])) and min(archived['depths'])==archived['minimum_depth']>1e-8
        pair=[read(OLD/(m+'-'+str(i)+'.json')) for m in ('A','B')]
        for m,r in zip(('A','B'),pair):
            assert r['slot']==slot and r['physical_hex']==state['physical_hex'] and r['physical_sha256']==digest
            assert r['source_manifest_sha256']==sha(OLD/'execution-sources.json')
            ent=next(e for e in events if e['event']=='entry' and e['method']==m and e['slot']==slot)
            done=next(e for e in events if e['event']=='completed' and e['method']==m and e['slot']==slot)
            assert ent['physical_hex']==state['physical_hex'] and sha(done['result_path'])==done['result_sha256']
            assert ent['monotonic']<done['monotonic']
            def normalized(x):
                value=unrat(x);assert int(x[1])>0 and rat(value)==x;return value
            normalized(r['cost'])
            assert len(r['gradient'])==len(r['summands'])==len(r['absolute_sums'])==6
            for g,terms,total in zip(r['gradient'],r['summands'],r['absolute_sums']):
                assert len(terms)==150
                values=list(map(normalized,terms))
                assert sum(values,F(0))==normalized(g) and sum(map(abs,values),F(0))==normalized(total)
        assert all(pair[0][k]==pair[1][k] for k in ('cost','gradient','summands','absolute_sums'))
        states.append({k:state[k] for k in ('slot','group','case','physical_hex','physical_sha256')})
        oracles.append({'slot':slot,'cost':pair[0]['cost'],'gradient':pair[0]['gradient'],'files':{str(OLD/(m+'-'+str(i)+'.json')):sha(OLD/(m+'-'+str(i)+'.json')) for m in ('A','B')}})
    assert len(states)==len(prior['states'])==6
    predecessor={str(p):sha(p) for p in sorted(OLD.iterdir()) if p.is_file()}
    deadline(auth,'admission');ROOT.mkdir()
    publish(ROOT/'inputs.json',dict(states=states,knots_hex=prior['knots_hex'],quadrature_hex=setups[0]['quadrature_hex'],window=[50,149],spacing=10,weight=1,shape=[18,3],samples=150))
    publish(ROOT/'oracle.json',dict(states=oracles,predecessor_sha256=predecessor,support_certificates=certificates))
    with (ROOT/'original-v11-failures.json').open('xb') as f:f.write((OLD/'original-v11-failures.json').read_bytes());f.flush();os.fsync(f.fileno())
    with (ROOT/'admission-source.py').open('xb') as f:f.write(SCRIPT.read_bytes());f.flush();os.fsync(f.fileno())
    publish(ROOT/'admission.json',dict(passed=True,admitted_monotonic=time.monotonic(),authorization_sha256=sha(AUTH),inputs_sha256=sha(ROOT/'inputs.json'),oracle_sha256=sha(ROOT/'oracle.json'),source_sha256=sha(SCRIPT),predecessor_sha256=predecessor,states=6,scientific_entries=0))
    print('Admission passed: six states, common exact oracle, zero scientific entries',flush=True)

if __name__=='__main__':
    assert sys.argv[1:] == ['admit']
    admit()
