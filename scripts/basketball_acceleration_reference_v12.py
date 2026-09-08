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
PINNED = dict(zip(('inputs.json','rays.json','probes.json.gz','primary.jsonl','independent.jsonl','admission.json','execution-sources.json','verification.json','verification-failures.json','budget.json'),('7a4b5aebeb5652051298ab88103a44af63a13ed69163eda988b333169cdf11f0','f8d0aad1f2b7f3a3de991bdab68ca3d1f37bc2306e06b7321a0f6491f8305a8c','f386896d04ad764fa17ae7b487fe30504a3967179f026347c1979d26e5b21c4e','f544aab2fc6f18ee22076128761a826865613c2a71836514a9b7a2821a2c8fd5','39cf317220fe6fd7b4e4b773e75b8462e2acac09de3dec1eeb6352e08c582a57','f262a40682dac776dfaacb36792f171a055ed21b63c3edf1dc3473efa9453268','285845798284eecc2b421da25f4c435fcedd18e5705d51c15b68b3f62904f50a','4be416f5567f35da5aa549770ef5392e45700c9d271f21cf1a7e986db094f944','672284899958ad7aa790e58d5a3d79d0291eb3a4034039561eb34c3f83cfb3b0','2c2c488b6ed60257216e81f8e9b7809f431651319109a39dd3dd422b375abeca')))
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


def setup_a(U, Q):
    """Independent degree/basis derivative recurrence, exact endpoint limits."""
    n=len(U)-4; matrix=[]
    for q in Q:
        if not U[3]<=q<=U[n]: raise ValueError('outside spline domain')
        final=next((i for i in range(len(U)-2,-1,-1) if U[i]<U[i+1]==q),None) if q==U[n] else None
        @functools.cache
        def value(i,p,m):
            if m>p:return F(0)
            if p==0:return F(int(i==final if final is not None else U[i]<=q<U[i+1]))
            left=U[i+p]-U[i];right=U[i+p+1]-U[i+1];out=F(0)
            if m:
                if left:out+=F(p)/left*value(i,p-1,m-1)
                if right:out-=F(p)/right*value(i+1,p-1,m-1)
            else:
                if left:out+=(q-U[i])/left*value(i,p-1,0)
                if right:out+=(U[i+p+1]-q)/right*value(i+1,p-1,0)
            return out
        matrix.append([value(i,3,2) for i in range(n)])
    return matrix

def bundle_a(matrix,C,w):
    nacc=len(matrix);scale=2*w/nacc;cost=F(0);summands=[[] for _ in range(6)];accelerations=[]
    for basis in matrix:
        a=[sum((b*c[axis] for b,c in zip(basis,C)),F(0)) for axis in range(3)]
        accelerations.append(a);cost+=sum(x*x for x in a)*w/nacc
        for j in range(6):summands[j].append(scale*basis[j//3]*a[j%3])
    return {'cost':cost,'gradient':[sum(s,F(0)) for s in summands],'summands':summands,'absolute_sums':[sum(map(abs,s),F(0)) for s in summands],'accelerations':accelerations}

def decode_a(inputs):
    import numpy as np
    U=[F.from_float(x) for x in struct.unpack('<22d',bytes.fromhex(inputs['knots_hex']))]
    window=inputs['window'];q=np.arange(window[0]-25,window[1]+26,dtype=float)/25
    qhex=q.astype('<f8',copy=False).tobytes().hex()
    Q=[F.from_float(x) for x in struct.unpack('<150d',bytes.fromhex(qhex))]
    return setup_a(U,Q),qhex

def coefficients_a(h):
    values=[F.from_float(x) for x in struct.unpack('<54d',bytes.fromhex(h))]
    return [values[i:i+3] for i in range(0,54,3)]

def serialized(result):
    return {'cost':rat(result['cost']),'gradient':[rat(x) for x in result['gradient']],
            'summands':[[rat(x) for x in s] for s in result['summands']],
            'absolute_sums':[rat(x) for x in result['absolute_sums']]}

class Ledger:
    """Entry ownership is consumed before callbacks, including failing callbacks."""
    def __init__(self,schedule,deadline_value,path=None,cap=12):
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

def source_manifest():
    paths={str(SCRIPT),str(CONTROL),str(TEST),str(Path(sys.executable).resolve())}
    # NumPy imported only by numerical methods; hash all its installed implementation
    # bytes without importing it during readiness or package validation.
    site=Path('.local/envs/calibration-global/lib/python3.14/site-packages')
    for folder in ('numpy','numpy.libs'):
        paths.update(str(p) for p in (site/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
    for mod in list(sys.modules.values()):
        filename=getattr(mod,'__file__',None)
        if filename and Path(filename).is_file():
            path=Path(filename)
            if path.suffix=='.pyc' and path.with_suffix('.py').exists():path=path.with_suffix('.py')
            paths.add(str(path))
    return {p:sha(p) for p in sorted(paths)}

def worker_guard(started,provided,parent_pid,allocation_path):
    if not provided or provided!=started.get('token') or parent_pid!=started.get('supervisor_pid'):raise ValueError('direct worker rejected')
    publish(allocation_path,{'consumed':True,'pid':os.getpid(),'monotonic':time.monotonic()})

def worker():
    started=read(ROOT/'started.json');worker_guard(started,os.environ.get('V12_WORKER_TOKEN'),os.getppid(),ROOT/'worker-consumed.json')
    assert all(os.environ.get(k)==v for k,v in THREADS.items())
    assert sha(AUTH)==started['authorization_sha256'] and sha(ROOT/'admission.json')==started['admission_sha256'] and sha(ROOT/'readiness.json')==started['readiness_sha256']
    hashes(read(ROOT/'execution-sources.json')['sha256'])
    inputs=read(ROOT/'inputs.json');assert sha(ROOT/'inputs.json')==read(ROOT/'admission.json')['inputs_sha256']
    end=started['deadline_monotonic'];ledger=Ledger(started['schedule'],end,ROOT/'entries.jsonl')
    publish(ROOT/'worker-identity.json',process_identity())
    import basketball_acceleration_control_v12 as control
    for method in ('A','B'):
        if time.monotonic()>=end:raise TimeoutError('setup deadline')
        event(ROOT/'entries.jsonl',event='setup_entry',method=method,source_manifest_sha256=sha(ROOT/'execution-sources.json'))
        setup,qhex=decode_a(inputs) if method=='A' else control.decode_b(inputs)
        publish(ROOT/(method+'-setup.json'),{'quadrature_hex':qhex,'samples':150,'method':method,'knots_hex':inputs['knots_hex']})
        event(ROOT/'entries.jsonl',event='setup_return',method=method)
        for index,state in enumerate(inputs['states']):
            h=state['physical_hex'];state_bytes(h,state['physical_sha256'],432)
            hashes(read(ROOT/'execution-sources.json')['sha256'])
            def calculate():
                result=bundle_a(setup,coefficients_a(h),F(1)) if method=='A' else control.bundle_b(setup,control.coefficients_b(h),F(1))
                return serialized(result)
            result=ledger.enter(method,state['slot'],h,calculate)
            result.update(method=method,slot=state['slot'],physical_sha256=state['physical_sha256'],physical_hex=h,source_manifest_sha256=sha(ROOT/'execution-sources.json'))
            path=ROOT/(method+'-'+str(index)+'.json');publish(path,result)
            event(ROOT/'entries.jsonl',event='completed',method=method,slot=state['slot'],result_path=str(path),result_sha256=sha(path))
    print('All 12 reference bundles completed',flush=True)

def run():
    auth=read(AUTH);deadline(auth,'implementation_ready')
    admission=read(ROOT/'admission.json');ready=read(ROOT/'readiness.json')
    assert admission['passed'] and admission['admitted_monotonic']<auth['deadlines']['admission']['monotonic']
    assert ready['passed'] and ready['ready_monotonic']<auth['deadlines']['implementation_ready']['monotonic']
    assert sha(AUTH)==admission['authorization_sha256'];assert sha(ROOT/'inputs.json')==admission['inputs_sha256']
    hashes(ready['sha256']);hashes(read(ROOT/'execution-sources.json')['sha256'])
    inputs=read(ROOT/'inputs.json');hashes(inputs['historical_sha256']);hashes(inputs['v11_sources']);hashes(admission['pinned_sha256'])
    start=time.monotonic();end=min(start+120,auth['deadlines']['numerical_end']['monotonic'])
    token=os.urandom(24).hex();schedule={m+'/'+s['slot']:s['physical_hex'] for m in ('A','B') for s in inputs['states']}
    publish(ROOT/'started.json',dict(start_monotonic=start,deadline_monotonic=end,token=token,supervisor_pid=os.getpid(),supervisor_identity=process_identity(),authorization_sha256=sha(AUTH),admission_sha256=sha(ROOT/'admission.json'),readiness_sha256=sha(ROOT/'readiness.json'),schedule=schedule,setup_slots=['A','B']))
    os.environ['V12_WORKER_TOKEN']=token
    budget=supervise([sys.executable,str(SCRIPT),'worker'],end,ROOT/'worker.log',ROOT/'processes.json')
    budget['supervised_start_monotonic']=budget['start_monotonic'];budget['start_monotonic']=start;budget['wall_seconds']=budget['end_monotonic']-start
    budget['phase_elapsed_seconds']=budget['end_monotonic']-auth['t0_monotonic'];budget['limits']=auth['limits']
    events=[json.loads(l) for l in (ROOT/'entries.jsonl').read_text().splitlines()] if (ROOT/'entries.jsonl').exists() else []
    budget['counts']={kind:sum(e['event']==kind for e in events) for kind in ('setup_entry','setup_return','entry','completed')}
    budget['forbidden_entries']=0;budget['training_seconds']=0;publish(ROOT/'budget.json',budget)
    print(json.dumps(budget),flush=True)
    if not budget['worker_stopped'] or budget['exit_code']!=0:raise RuntimeError('worker did not complete; allocation consumed')

def compare_saved(v,g,rtol):
    allowed=1e-10+rtol*abs(v);allowed_exact=F.from_float(allowed);error=abs(F.from_float(v)-g)
    return dict(saved_value=v,saved_hex=fhex([v]),reference=rat(g),forward_error=rat(error),allowed_error=rat(allowed_exact),allowed_hex=fhex([allowed]),status='within_tolerance' if error<=allowed_exact else 'outside_tolerance')

def compare_pair(a,b,state):
    fields=('cost','gradient','summands','absolute_sums')
    agrees=a is not None and b is not None and all(a[k]==b[k] for k in fields)
    out={'slot':state['slot'],'reference_agreement':agrees,'archived':{}}
    for method,archived in state['archived'].items():
        if agrees:
            components=[compare_saved(v,unrat(g),1e-8) for v,g in zip(archived['G'][:6],a['gradient'])]
            for j,c in enumerate(components):c.update(component=j,absolute_summand_sum=a['absolute_sums'][j],signed_summands_reference=str(ROOT/('A-'+str([x[0] for x in SLOTS].index(state['slot']))+'.json')))
            cost=compare_saved(archived['acceleration_cost'],unrat(a['cost']),1e-9)
            status='within_tolerance' if all(c['status']=='within_tolerance' for c in components) else 'outside_tolerance'
        else:components=[{'component':j,'status':'unverified'} for j in range(6)];cost={'status':'unverified'};status='unverified'
        out['archived'][method]={'components':components,'acceleration_cost':cost,'gradient_status':status}
    return out

def package():
    """Only retained JSON, hashes and exact comparison arithmetic; no evaluators."""
    auth=read(AUTH);deadline(auth,'phase_end');admission=read(ROOT/'admission.json');inputs=read(ROOT/'inputs.json');ready=read(ROOT/'readiness.json');budget=read(ROOT/'budget.json');started=read(ROOT/'started.json')
    hashes(admission['pinned_sha256']);hashes(inputs['historical_sha256']);hashes(inputs['v11_sources']);hashes(read(ROOT/'execution-sources.json')['sha256']);hashes(ready['sha256'])
    assert sha(ROOT/'original-v11-failures.json')==PINNED['verification-failures.json']
    assert sha(AUTH)==admission['authorization_sha256']==started['authorization_sha256'] and sha(ROOT/'inputs.json')==admission['inputs_sha256']
    events=[json.loads(l) for l in (ROOT/'entries.jsonl').read_text().splitlines()] if (ROOT/'entries.jsonl').exists() else []
    entries=[e for e in events if e['event']=='entry'];completions=[e for e in events if e['event']=='completed'];setups=[e for e in events if e['event']=='setup_entry']
    assert len(entries)<=12 and len(setups)<=2
    assert len({(e['method'],e['slot']) for e in entries})==len(entries)
    for e in entries:assert started['schedule'][e['method']+'/'+e['slot']]==e['physical_hex'] and started['start_monotonic']<=e['monotonic']<started['deadline_monotonic']
    assert [e['method'] for e in setups] in ([],['A'],['A','B'])
    assert len({(e['method'],e['slot']) for e in completions})==len(completions)
    assert len([e for e in events if e['event']=='setup_return'])==budget['counts']['setup_return']
    assert len(entries)==budget['counts']['entry'] and len(completions)==budget['counts']['completed']
    assert len(setups)==budget['counts']['setup_entry']
    assert sha(ROOT/'admission-source.py')==admission['source_sha256']
    for e in completions:
        assert sha(e['result_path'])==e['result_sha256']
        owner=[entry for entry in entries if entry['method']==e['method'] and entry['slot']==e['slot']]
        assert len(owner)==1 and owner[0]['monotonic']<e['monotonic']<started['deadline_monotonic']
        result=read(e['result_path'])
        assert result['method']==e['method'] and result['slot']==e['slot'] and result['physical_hex']==owner[0]['physical_hex']
        assert result['source_manifest_sha256']==sha(ROOT/'execution-sources.json')
    for setup_entry in setups:
        returns=[e for e in events if e['event']=='setup_return' and e['method']==setup_entry['method']]
        owned=[e for e in entries if e['method']==setup_entry['method']]
        assert len(returns)<=1
        if owned:assert len(returns)==1 and setup_entry['monotonic']<returns[0]['monotonic']<min(e['monotonic'] for e in owned)
        assert setup_entry['source_manifest_sha256']==sha(ROOT/'execution-sources.json')
    results=[]
    for index,state in enumerate(inputs['states']):
        pair=[]
        for method in ('A','B'):
            p=ROOT/(method+'-'+str(index)+'.json');r=read(p) if p.exists() else None
            if r:
                assert r['slot']==state['slot'] and r['physical_hex']==state['physical_hex'] and r['physical_sha256']==state['physical_sha256']
                assert len(r['gradient'])==len(r['summands'])==len(r['absolute_sums'])==6
                for gradient,summands,absolute in zip(r['gradient'],r['summands'],r['absolute_sums']):
                    assert len(summands)==150 and sum(map(unrat,summands),F(0))==unrat(gradient) and sum((abs(unrat(x)) for x in summands),F(0))==unrat(absolute)
                assert len([e for e in completions if e['method']==method and e['slot']==state['slot']])==1
            pair.append(r)
        results.append(compare_pair(*pair,state))
    complete=len(entries)==len(completions)==12 and len(setups)==2 and budget['worker_stopped'] and budget['exit_code']==0 and budget['wall_seconds']<=120 and budget['within_deadline']
    if complete:assert read(ROOT/'A-setup.json')['quadrature_hex']==read(ROOT/'B-setup.json')['quadrature_hex']
    exact=complete and all(r['reference_agreement'] for r in results)
    summary={m:{kind:sum(c['status']==kind for r in results for c in r['archived'][m]['components']) for kind in ('within_tolerance','outside_tolerance','unverified')} for m in ('primary','independent')}
    costs={m:{kind:sum(r['archived'][m]['acceleration_cost']['status']==kind for r in results) for kind in ('within_tolerance','outside_tolerance','unverified')} for m in ('primary','independent')}
    publish(ROOT/'comparisons.json',{'states':results,'gradient_counts':summary,'cost_counts':costs,'exact_references_agree':exact})
    gates={'accepted_timing':None,'production_candidate':None,'final_validation_protocol':None,'ready_for_full_screens':False,'main_objective_attained':False,'historical_v11_A2_A3':'failed; unchanged'}
    publish(ROOT/'decision.json',{**gates,'reference_plan_complete':exact,'gradient_counts':summary,'cost_counts':costs,'scope':'six retained states, six components each; other 57 v11 failed states unadjudicated'})
    publish(ROOT/'package-validation.json',dict(passed=exact,provenance_passed=True,complete=complete,paired_costs=6 if complete else None,paired_gradients=36 if complete else None,gradient_outputs=len(completions)*6,cost_outputs=len(completions),original_failure_unchanged=True,source_hashes_unchanged=True,counts=budget['counts'],phase_elapsed_seconds=time.monotonic()-auth['t0_monotonic'],gates=gates))
    print(json.dumps({'complete':complete,'exact':exact,'gradients':summary,'costs':costs}),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['admit','run','package','worker']);args=parser.parse_args()
    {'admit':admit,'run':run,'package':package,'worker':worker}[args.command]()
