"""Plan 018: immutable admission and a single bounded evaluation-only diagnostic.

Admission and packaging use the standard library only. Scientific imports occur
inside the supervised worker, after its wall clock has started. No free rerun.
"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import signal
import struct
import subprocess
import sys
import time

ROOT = Path('docs/experiments/basketball-shared-timing-v11')
V10 = Path('docs/experiments/basketball-shared-timing-v10')
AUTH = Path('docs/continuous-improvement/20260908-plan016/iteration-002-plan018-authorization.json')
PYTHON = '.local/envs/calibration-global/bin/python'
SCRIPT = 'scripts/basketball_shared_trajectory_diagnostic_v11.py'
VERIFY = 'scripts/basketball_shared_trajectory_verify_v11.py'
THREADS = {k: '1' for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS')}
CASES = [(0,2,0,200,200), (7,9,0,200,200), (13,11,0,200,200),
         (3,2,1,38,32), (10,9,1,39,32), (16,11,1,36,30)]
TOLS = {'objective': [1e-10,1e-9], 'depths': [1e-12,1e-12],
        'forces': [1e-10,1e-8], 'multipliers': [1e-12,1e-10]}


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def read(path):
    path = Path(path)
    data = path.read_bytes()
    if path.suffix == '.gz': data = gzip.decompress(data)
    value = json.loads(data, parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
    encode(value)
    return value


def sha(path):
    path = Path(path)
    if 'prompts' in path.parts: raise ValueError('excluded path')
    return hashlib.sha256(path.read_bytes()).hexdigest()


def publish(path, value):
    path = Path(path)
    data = encode(value)
    if path.suffix == '.gz': data = gzip.compress(data, mtime=0)
    with path.open('xb') as f:
        f.write(data); f.flush(); os.fsync(f.fileno())
    return sha(path)


def fhex(values):
    return struct.pack('<' + 'd'*len(values), *values).hex()


def exact_hashes(mapping):
    for path, digest in mapping.items():
        if sha(path) != digest: raise ValueError('source mutation: ' + path)


def journal(path):
    previous = '0'*64; events = []
    for line in Path(path).read_bytes().splitlines(keepends=True):
        if not line.endswith(b'\n'): raise ValueError('incomplete journal')
        event = json.loads(line); checksum = event.pop('checksum')
        if event['seq'] != len(events) or event['previous'] != previous:
            raise ValueError('journal sequence')
        if hashlib.sha256(encode(event)).hexdigest() != checksum: raise ValueError('journal checksum')
        event['checksum'] = checksum; events.append(event); previous = checksum
    if not events: raise ValueError('empty journal')
    return events


def deadline(auth, key):
    if time.monotonic() >= auth['deadlines'][key]['monotonic']:
        raise TimeoutError(key + ' deadline exhausted')


def validate_item(item, events, receipt, artifact_hash, receipt_hash):
    """JSON/bytes only: no reconstruction, imported verifier or scientific call."""
    row = item['row']; ident = item['identity']; a = row['accounting']
    assert item['id'] == ident['attempt_id'] and item['reference'] == ident['reference']
    assert row['policy'] == ident['policy']
    assert ident['run_id'] == 'basketball-shared-v10-1788843120'
    assert row['seed'] is ident['dependency_provenance'] is None
    assert ident['allocation'] is None  # historical cohort allocation identity
    assert [e['identity'] for e in events if e['event']=='allocated'] == [ident]
    completions = [e for e in events if e['event']=='completed']; assert len(completions)==1
    end=completions[0]
    assert end['artifact_sha256']==receipt['artifact_sha256']==artifact_hash
    assert end['receipt_sha256']==receipt_hash and end['id']==receipt['id']==item['id']
    assert receipt['verification']['passed']
    problem=a['problem']; problem_key=hashlib.sha256(json.dumps(problem,sort_keys=True).encode()).hexdigest()
    assert a['problem_key']==problem_key and problem['provenance']==ident
    assert problem['namespace']==ident['namespace']
    pe=[e for e in events if e['event']=='problem']; assert len(pe)==1
    assert pe[0]['problem']==problem and pe[0]['problem_key']==problem_key
    last=next(e for e in reversed(events) if e['event'] in ('problem','transform'))
    assert last['transform_hex']==a['transform_hex'] and last['origin_hex']==a['origin_hex']
    assert pe[0]['scale_hex']==a['scale_hex']==fhex([1.]*54)
    assert len(bytes.fromhex(a['transform_hex']))==54*54*8 and len(bytes.fromhex(a['origin_hex']))==54*8
    states=[{k:e[k] for k in ('identity','scope','canonical_hex','physical_hex')} for e in events if e['event']=='state']
    assert states==a['states'] and len(states)==a['distinct_states']
    byid={s['identity']:s for s in states}; assert len(byid)==len(states)
    for s in states:
        assert s['physical_hex']==s['canonical_hex']
        assert hashlib.sha256(problem_key.encode()+s['scope'].encode()+bytes.fromhex(s['canonical_hex'])).hexdigest()==s['identity']
    entered=[e for e in events if e['event']=='numerical_entry']
    returned=[e for e in events if e['event']=='numerical_return']
    assert len(entered)==len(returned)==len(a['entries'])==len(a['observed_numerical_entries'])
    returns={e['index']:e for e in returned}; assert len(returns)==len(returned)
    for i,(e,entry,observed) in enumerate(zip(entered,a['entries'],a['observed_numerical_entries'])):
        assert e['index']==i and e['state']==entry['state']
        assert e['physical_hex']==observed['physical_hex']==byid[e['state']]['physical_hex']
        assert e['kind']==entry['kind']==observed['kind']
        assert returns[i]['status']==entry['status']==observed['status']=='completed'
        assert e['seq']<returns[i]['seq']
    assert len([e for e in events if e['event']=='solver_invocation'])==1
    assert row['solver_trace'][-1]['state']==row['returned_state']
    assert fhex(row['x'])==fhex(row['solver_trace'][-1]['x'])==byid[row['returned_state']]['physical_hex']
    assert fhex(row['canonical_q'])==fhex(row['solver_trace'][-1]['q'])==byid[row['returned_state']]['canonical_hex']
    assert fhex(row['multipliers_transformed'])==fhex(row['solver_trace'][-1]['multipliers'][0])
    for c in row['solver_trace']:
        assert fhex(c['x'])==byid[c['state']]['physical_hex'] and fhex(c['q'])==byid[c['state']]['canonical_hex']
        assert len(c['y'])==54 and [len(v) for v in c['multipliers']]==[300,54]
        assert all(k in c for k in ('objective','min_depth','optimality','barrier_parameter','trust_radius'))
    return byid


def admit():
    auth=read(AUTH); deadline(auth,'admission')
    if ROOT.exists(): raise FileExistsError(ROOT)
    for path in (VERIFY,):
        if not Path(path).exists(): raise FileNotFoundError(path)
    hashes={}; cases=[]
    def bind(path):
        hashes[str(path)]=sha(path); return read(path)
    index=bind(V10/'package/attempt-index.json')
    manifest=bind(V10/'prepare/benchmark-manifest.json')
    sources=bind(V10/'prepare/execution-sources.json'); exact_hashes(sources); hashes.update(sources)
    evidence=bind(V10/'evidence.json'); report=bind(V10/'independent-report.json')
    assert evidence['ready_for_full_screens'] is report['ready_for_full_screens'] is False
    assert evidence['accepted_timing'] is report['accepted_timing'] is None
    for f in ('docs/experiments/basketball-shared-timing-v5/diagnose-final/escape-decision.json',
              'docs/experiments/basketball-shared-timing-v5/diagnose-final/pilot-manifest.json',
              'docs/experiments/basketball-shared-timing-v5/diagnose-final/escape-audit.json.gz',
              'docs/experiments/basketball-shared-timing-v9/diagnose/escape-reuse.json'):
        bind(f)
    for arm,sub,count_idx in [('baseline','baseline/policy',3),('metric','adapt/metric',4)]:
        for spec in CASES:
            nn,gid,weight=spec[:3]; directory=V10/sub/f'conditional-{nn:02d}'/'cold'
            entry=next(e for e in index['attempts'] if e['directory']==str(directory))
            assert entry['completed'] and entry['journal_intact'] and entry['verification']['passed']
            item=bind(directory/'attempt.json.gz'); receipt=bind(directory/'receipt.json')
            hashes[str(directory/'journal.jsonl')]=sha(directory/'journal.jsonl')
            events=journal(directory/'journal.jsonl')
            byid=validate_item(item,events,receipt,hashes[str(directory/'attempt.json.gz')],hashes[str(directory/'receipt.json')])
            ident=item['identity']; row=item['row']; p=row['accounting']['problem']
            policy=bind(ident['policy_file']); assert hashes[ident['policy_file']]==ident['policy_sha256'] and policy['name']==ident['policy']
            assert ident['manifest']==str(V10/'prepare/benchmark-manifest.json') and ident['manifest_sha256']==hashes[ident['manifest']]
            assert ident['execution_sha256']==sources
            assert item['reference']==dict(group_id=gid,weight=weight,lag=-25.,offset=-25.)
            target=next(t for t in manifest['targets'] if t['id']==f'conditional-{nn:02d}')
            assert all(target[k]==v for k,v in item['reference'].items())
            assert p['free']==[] and p['window']==[50,149] and p['spacing']==10 and p['weight']==weight
            assert p['offsets']=={'1':0.,'2':-25.,'3':-25.} and p['gauge']==1 and p['role']=='synthetic-fit-50-149'
            assert len(p['observations'])==1 and p['observations'][0]['group_id']==gid
            assert [o['camera_id'] for o in p['observations'][0]['observations']]==[1,2,3]
            assert all(o['frames']==list(range(50,150)) for o in p['observations'][0]['observations'])
            assert row['window']==[50,149] and row['spacing']==10 and len(row['knots'])==22
            trace=row['solver_trace']; assert len(trace)==spec[count_idx]
            ordinals=[0,(len(trace)-1)//3,2*(len(trace)-1)//3,len(trace)-1]
            selected=[]
            for ordinal in ordinals:
                c=trace[ordinal]
                selected.append(dict(ordinal=ordinal,callback=c,state=byid[c['state']],
                                     x_hex=fhex(c['x']),q_hex=fhex(c['q']),y_hex=fhex(c['y']),
                                     multipliers_hex=[fhex(v) for v in c['multipliers']]))
            cases.append(dict(id=f'{arm}/conditional-{nn:02d}/cold',arm=arm,group=gid,weight=weight,
                              directory=str(directory),identity=ident,selected=selected,
                              returned={k:row[k] for k in ('x','canonical_q','returned_state','multipliers_depth','multipliers_transformed','bound_multipliers')},
                              row=row,ordinal_rule='0,floor((n-1)/3),floor(2*(n-1)/3),n-1'))
            deadline(auth,'admission')
    ROOT.mkdir()
    publish(ROOT/'inputs.json',dict(cases=cases,historical_sha256=hashes))
    commands=[f'{PYTHON} {SCRIPT} {op}' for op in ('admit','run','package')]
    publish(ROOT/'admission.json',dict(passed=True,admitted_monotonic=time.monotonic(),authorization=str(AUTH),authorization_sha256=sha(AUTH),
        inputs_sha256=sha(ROOT/'inputs.json'),commands=commands,threads=THREADS,tolerances=TOLS,deadlines=auth['deadlines'],
        namespace='plan018/v11/{pass}/{case}/{snapshot-or-ray-slot}',cases=12,snapshots_per_pass=48,rays_per_pass=24,
        amplitudes=[10**e for e in range(0,45,2)],limits=auth['limits'],
        exclusions=['optimizer','initialization','Hessian','finite_difference','GPU','training','rendering','download','install'],
        admission_source_sha256=sha(SCRIPT),execution_sources_freeze='Final implementation and installed arithmetic frozen by run before worker entry',
        rerun='Fresh explicit allocation required; this admission is single use'))
    print('Admission passed: 12 cases, 48 exact callback slots; no numerical entries.',flush=True)

def plain(value):
    """Convert scientific results, rejecting nonfinite numbers at publication."""
    if isinstance(value,dict): return {str(k):plain(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)): return [plain(v) for v in value]
    if hasattr(value,'tolist'): return plain(value.tolist())
    return value


class Entries:
    """Fixed slot ownership, charged and flushed before actual entry."""
    def __init__(self,path,pass_name,slots,limits,end):
        self.path=Path(path); self.file=self.path.open('x'); self.pass_name=pass_name
        self.slots=set(slots); self.limits=set(limits); self.end=end
        self.allocated=set(); self.entered=set(); self.finished=set(); self.counts={}; self.physical={}
    def append(self,event,**kw):
        self.file.write(encode(plain(dict(event=event,pass_name=self.pass_name,monotonic=time.monotonic(),**kw))).decode()+'\n')
        self.file.flush(); os.fsync(self.file.fileno())
    def check(self):
        if time.monotonic()>=self.end: raise TimeoutError('numerical deadline')
    def allocate(self,slot,physical_hex,operands=None):
        self.check()
        if slot not in self.slots|self.limits: raise ValueError('unallocated slot '+slot)
        if slot in self.allocated: raise ValueError('duplicate slot '+slot)
        self.allocated.add(slot); self.physical[slot]=physical_hex
        self.append('allocated',slot=slot,physical_hex=physical_hex,
                    physical_sha256=hashlib.sha256(bytes.fromhex(physical_hex)).hexdigest(),
                    operands=operands,cache_hit=False)
    def call(self,slot,kind,x,callback):
        self.check()
        if slot not in self.allocated or (slot,kind) in self.entered or slot in self.finished:
            raise ValueError('entry ownership or duplicate')
        if (slot in self.slots and kind not in ('depth','residual')) or (slot in self.limits and kind!='limit'):
            raise ValueError('entry kind outside allocation')
        observed=x.astype('<f8').tobytes().hex() if hasattr(x,'dtype') else x
        if observed!=self.physical[slot]: raise ValueError('actual entry bytes differ from allocation')
        self.entered.add((slot,kind)); self.counts[kind]=self.counts.get(kind,0)+1
        self.append('entry',slot=slot,kind=kind,physical_hex=observed,counts=self.counts.copy())
        try: result=callback()
        except BaseException as e:
            self.append('error',slot=slot,kind=kind,error=type(e).__name__+': '+str(e)); raise
        self.append('return',slot=slot,kind=kind)
        return result
    def finish(self,slot,result):
        if slot not in self.allocated or slot in self.finished: raise ValueError('completion ownership')
        self.finished.add(slot); self.append('completed',slot=slot,result=result)
    def close(self): self.file.close()


def schedules(cases):
    finite=[]; limits=[]
    for case in cases:
        finite.extend(case['id']+'/snapshot/'+str(s['ordinal']) for s in case['selected'])
        if case['arm']=='metric':
            for operand in (0,2):
                for sign in (1,-1):
                    ray=case['id']+f'/ray/{operand}/{sign}'
                    limits.append(ray+'/limit')
                    finite.extend(ray+f'/amplitude/{e}' for e in range(0,45,2))
    assert len(finite)==len(set(finite))==600 and len(limits)==24
    return finite,limits


def frozen_sources():
    paths={SCRIPT,VERIFY,'tests/test_basketball_shared_trajectory_v11.py'}
    paths.update(read(V10/'prepare/execution-sources.json'))
    # No imports here: bind the installed distribution metadata and arithmetic files.
    site=Path('.local/envs/calibration-global/lib/python3.14/site-packages')
    for name in ('numpy','scipy'):
        for folder in [site/name,site/(name+'.libs'),*site.glob(name+'-*.dist-info')]:
            for p in folder.rglob('*'):
                if p.is_file() and (p.suffix in ('.py','.so') or p.name in ('METADATA','RECORD')):
                    paths.add(str(p))
    return {p:sha(p) for p in sorted(paths)}


def decode_case(case,check):
    """Populate evaluation-only fields; never call the fitting constructor."""
    import numpy as np
    from scipy.interpolate import BSpline
    from basketball_shared_spline_v2 import SplineProblem
    row=case['row']; data=row['accounting']['problem']
    p=object.__new__(SplineProblem)
    p.groups=[]
    for group in data['observations']:
        p.groups.append(dict(group_id=group['group_id'],observations=[
            dict(camera_id=o['camera_id'],frames=np.asarray(o['frames']),xy=np.asarray(o['xy'])) for o in group['observations']]))
    p.cameras={int(k):v for k,v in data['calibration'].items()}
    p.offsets={int(k):v for k,v in data['offsets'].items()}
    p.window=data['window']; p.spacing=data['spacing']; p.weight=data['weight']; p.check=check
    p.center=np.asarray(row['center']); p.diameter=row['diameter']; p.nc=18
    p.spline=BSpline(row['knots'],np.eye(18),3,extrapolate=False)
    p.quadrature=np.arange(p.window[0]-25,p.window[1]+26,dtype=float)/25
    p.accel=p.spline.derivative(2)(p.quadrature); p.nacc=len(p.quadrature)
    p.free=[];p.index={};p.n_offsets=0;p.n=300;p.cache=None;p.evaluation_trace=[]
    p.x0=np.frombuffer(bytes.fromhex(case['selected'][0]['x_hex']),dtype='<f8').copy()
    # Shape reference only: this is saved callback data, never an initializer.
    lo,hi=(p.window[0]-25)/25,(p.window[1]+25)/25
    expected=np.r_[[lo]*4,np.arange(lo+p.spacing/25,hi-1e-12,p.spacing/25),[hi]*4]
    np.testing.assert_array_equal(expected,p.spline.t)
    centers=np.array([-np.asarray(c['R']).T@np.asarray(c['t']) for c in p.cameras.values()])
    np.testing.assert_array_equal(centers.mean(axis=0),p.center)
    assert float(np.max(np.linalg.norm(centers[:,None]-centers[None,:],axis=2)))==p.diameter
    a=row['accounting']; p.saved_P=np.frombuffer(bytes.fromhex(a['transform_hex']),dtype='<f8').reshape(54,54)
    p.saved_origin=np.frombuffer(bytes.fromhex(a['origin_hex']),dtype='<f8')
    p.saved_inverse=np.linalg.inv(p.saved_P)
    for snapshot in case['selected']:
        y=np.frombuffer(bytes.fromhex(snapshot['y_hex']),dtype='<f8')
        assert (p.saved_origin+p.saved_P@y).astype('<f8').tobytes().hex()==snapshot['q_hex']
        assert snapshot['q_hex']==snapshot['x_hex']  # admitted scale exactly one
    return p


def geometry(p,x):
    import numpy as np
    C=np.asarray(x).reshape(18,3); samples=[]
    for o in p.groups[0]['observations']:
        cid=o['camera_id']; t=(o['frames']-p.offsets[cid])/25
        B=p.spline(t); xyz=B@C
        samples.append(dict(camera=cid,frames=o['frames'],times=t,xyz=xyz,B=B,observation=o))
    return samples


def primary_depth(p,x):
    """Pinned v4 raw-depth operation order with all physical bytes authoritative."""
    import numpy as np
    C=x.reshape(18,3); depths=[]; jac=[]
    for sample in geometry(p,x):
        cam=p.cameras[sample['camera']]; R=np.asarray(cam['R'])[2]; B=sample['B']
        depths.extend(B@C@R+(R@p.center+cam['t'][2])/p.diameter)
        jac.append((B[:,:,None]*R).reshape(len(B),54))
    return np.asarray(depths),np.vstack(jac)


def primary_residual(p,x):
    import numpy as np
    p.cache=None
    r,J=p.evaluate(x)
    data=float(r[:2*p.n]@r[:2*p.n]); acc=float(r[2*p.n:]@r[2*p.n:])
    return dict(objective=float(r@r),data_objective=data,acceleration_cost=acc,G=np.asarray(2*J.T@r).ravel())


def snapshot_forces(p,z,D,G,snapshot):
    import numpy as np
    vg=np.asarray(snapshot['callback']['multipliers'][0]); vb_y=np.asarray(snapshot['callback']['multipliers'][1])
    s=z-1e-8; h=np.hypot(1.,s); inv=1./h; gp=inv*inv*inv; g=s/h
    vd=vg*gp; Cd=D.T@vd; Cb=p.saved_inverse.T@vb_y; KKT=G+Cd+Cb
    return dict(multipliers_transformed=vg,multipliers_depth=vd,bound_multipliers=Cb,
                C_depth=Cd,C_bounds=Cb,KKT=KKT,transformed_KKT=p.saved_P.T@KKT,
                original_KKT_inf=float(np.max(np.abs(KKT))),solver_KKT_inf=float(np.max(np.abs(p.saved_P.T@KKT))),
                complementarity_original=vd*s,raw_slacks=s,transformed_slacks=g,depth_transform_derivative=gp,
                saturation=int(np.count_nonzero(np.abs(g)==1)),derivative_underflow=int(np.count_nonzero(gp==0)))


def compare_values(actual,expected,kind):
    import numpy as np
    a=np.asarray(actual); b=np.asarray(expected); atol,rtol=TOLS[kind]
    return dict(passed=bool(a.shape==b.shape and np.isfinite(a).all() and np.isfinite(b).all() and np.allclose(a,b,atol=atol,rtol=rtol)),
                maximum_absolute_error=float(np.max(np.abs(a-b))) if a.shape==b.shape and a.size else None,atol=atol,rtol=rtol)


def compare_saved(result,case,snapshot):
    checks={}; callback=snapshot['callback']
    for key,old,kind in [('objective','objective','objective'),('minimum_depth','min_depth','depths'),('solver_KKT_inf','optimality','forces')]:
        checks[key]=compare_values(result[key],callback[old],kind)
    if snapshot['ordinal']==case['selected'][-1]['ordinal']:
        row=case['row']
        for key in ('G','C_depth','C_bounds','KKT'):
            checks['returned_'+key]=compare_values(result[key],row[key],'forces')
        for key in ('multipliers_transformed','multipliers_depth','bound_multipliers','complementarity_original'):
            checks['returned_'+key]=compare_values(result[key],row[key],'multipliers')
        checks['returned_depths']=compare_values(result['depths'],row['normalized_depths'],'depths')
    return checks


def finite_slot(p,x,slot,ledger,snapshot=None,case=None):
    import numpy as np
    hx=np.asarray(x,dtype='<f8').tobytes().hex()
    ledger.allocate(slot,hx, None if snapshot is None else {'source_state':snapshot['state']['identity']})
    result=dict(slot=slot,physical_hex=hx,status=None,objective=None)
    try:
        if not np.isfinite(x).all(): result['status']='nonfinite_state'
        else:
            z,D=ledger.call(slot,'depth',x,lambda:primary_depth(p,x))
            if not np.isfinite(z).all() or not np.isfinite(D).all(): result['status']='nonfinite_depth'
            else:
                result.update(depths=z,minimum_depth=float(min(z)))
                if np.any(z<=1e-8): result['status']='infeasible'
                else:
                    measurement=ledger.call(slot,'residual',x,lambda:primary_residual(p,x))
                    if not all(np.isfinite(v).all() for v in measurement.values()): result['status']='nonfinite_objective_or_gradient'
                    else:
                        result.update(measurement,status='finite')
                        xyz=geometry(p,x)
                        result.update(sampled_max_abs=float(max(np.max(np.abs(s['xyz'])) for s in xyz)),coefficient_max_abs=float(np.max(np.abs(x))),
                                      trajectories=[{k:s[k] for k in ('camera','frames','times','xyz')} for s in xyz])
                        if snapshot is not None:
                            result.update(snapshot_forces(p,z,D,measurement['G'],snapshot))
                            result['saved_checks']=compare_saved(result,case,snapshot)
    except (FloatingPointError,OverflowError,ValueError) as e:
        result.update(status='entry_error',error=type(e).__name__+': '+str(e),objective=None)
    result=plain(result); ledger.finish(slot,result); return result


def freeze_rays(cases,problems):
    import numpy as np
    rays=[]
    for case in cases:
        if case['arm']!='metric': continue
        p=problems[case['id']]; base=np.frombuffer(bytes.fromhex(case['selected'][-1]['x_hex']),dtype='<f8')
        for operand in (0,2):
            before=np.frombuffer(bytes.fromhex(case['selected'][operand]['x_hex']),dtype='<f8')
            delta=base-before
            m=float(max(np.max(np.abs(s['B']@delta.reshape(18,3))) for s in geometry(p,base)))
            for sign in (1,-1):
                direction=sign*delta/m if m>0 else None
                rays.append(plain(dict(id=case['id']+f'/ray/{operand}/{sign}',case=case['id'],operand=operand,sign=sign,
                    base_hex=base.astype('<f8').tobytes().hex(),delta=delta,m=m,direction=direction,
                    direction_hex=None if direction is None else direction.astype('<f8').tobytes().hex(),
                    operand_states=[case['selected'][-1]['state']['identity'],case['selected'][operand]['state']['identity']],
                    delta_exactly_zero=bool(np.all(delta==0)),equation='C(a)=C_return+a*sign*(C_return-C_operand)/max(abs(B*(C_return-C_operand)))',
                    sources={str(ROOT/'inputs.json'):sha(ROOT/'inputs.json'),str(ROOT/'execution-sources.json'):sha(ROOT/'execution-sources.json')})))
    assert len(rays)==24
    publish(ROOT/'rays.json',dict(rays=rays,amplitude_exponents=list(range(0,45,2))))
    return rays


def structural_components(knots,t,B,d,R):
    """Sufficient exact zero proof only; unsupported cancellation stays unknown."""
    import numpy as np
    supported=(t[:,None]>knots[:-4])&(t[:,None]<knots[4:]) | (B!=0)
    zero=np.ones((len(t),3),dtype=bool)
    for axis in range(3):
        active=np.any((d!=0)&(R[axis]!=0),axis=1)
        if active.any(): zero[:,axis]=~np.any(supported[:,active],axis=1)
    return zero


def primary_limit(p,ray,reference):
    import numpy as np
    if ray['direction'] is None:
        return dict(classification='degenerate',reason='zero sampled normalization',m=ray['m'],objective_limit=None)
    base=np.frombuffer(bytes.fromhex(ray['base_hex']),dtype='<f8').reshape(18,3)
    d=np.asarray(ray['direction']).reshape(18,3); samples=[]; errors=[]; unresolved=[]
    negative=False; divergence=False; all_zero=True; transition=0.; boundaries=[]
    for o in p.groups[0]['observations']:
        cam=p.cameras[o['camera_id']]; R=np.asarray(cam['R']); t=(o['frames']-p.offsets[o['camera_id']])/25
        B=p.spline(t); b=(B@base*p.diameter+p.center)@R.T+cam['t']; v=(B@d*p.diameter)@R.T
        zero=structural_components(p.spline.t,t,B,d,R)
        all_zero=all_zero and bool(zero.all()); vz=v[:,2]; bz=b[:,2]
        neg=vz<0; negative=negative or bool(neg.any())
        if neg.any(): boundaries.extend(((bz[neg]-1e-8*p.diameter)/(-vz[neg])).tolist())
        nz=vz!=0
        if nz.any(): transition=max(transition,float(np.max(np.abs(bz[nz]/vz[nz]))))
        if np.any((vz==0)&(bz/p.diameter<=1e-8)): negative=True
        for j in range(3):
            if np.any((v[:,j]==0)&~zero[:,j]): unresolved.append('uncertified camera component cancellation')
        transverse=(vz==0)&np.any(v[:,:2]!=0,axis=1)
        if np.any(transverse & zero[:,2]): divergence=True
        uv=b[:,:2]/bz[:,None]; uv[nz]=v[nz,:2]/vz[nz,None]
        pred=(uv*(1+cam['parameters_colmap'][3]*np.sum(uv*uv,axis=1))[:,None])@np.asarray(cam['K'])[:2,:2].T+np.asarray(cam['K'])[:2,2]
        errors.extend(pred-o['xy'])
        samples.append(dict(camera=o['camera_id'],frames=o['frames'],times=t,b=b,v=v,structural_zero_components=zero,
                            normalized_base_depth=bz/p.diameter,normalized_depth_slope=vz/p.diameter))
    Ad=p.accel@d; Ab=p.accel@base; invariant=bool(np.all(d==d[0]))
    if p.weight:
        if np.any(Ad!=0) and not invariant: divergence=True
        elif not invariant: unresolved.append('uncertified acceleration cancellation')
    e=np.asarray(errors); data=float(np.mean(2*(np.sqrt(1+np.sum(e*e,axis=1))-1)))
    accel=float(p.weight*np.sum(Ab*Ab)/p.nacc)
    limit=data+accel if not divergence else None
    if not np.isfinite(data) or not np.isfinite(accel) or not np.isfinite(transition): unresolved.append('nonfinite analytical arithmetic')
    feasible=not negative
    if unresolved: classification='unresolved_arithmetic'
    elif not feasible: classification='infeasible_at_infinity'
    elif all_zero and (not p.weight or invariant): classification='structurally_unobservable_objective_invariant'
    elif divergence: classification='divergent_objective'
    elif limit>reference+1e-6+1e-4*max(abs(limit),abs(reference)): classification='finite_noncompetitive_limit'
    else: classification='competitive_feasible_finite_limit'
    return plain(dict(classification=classification,unresolved=sorted(set(unresolved)),samples=samples,
        feasible_at_infinity=feasible,objective_limit=limit if limit is None or np.isfinite(limit) else None,
        data_limit=data if np.isfinite(data) else None,acceleration_base_cost=accel,
        acceleration_direction=Ad,acceleration_invariant_structural=invariant,
        first_feasibility_boundary=min(boundaries) if boundaries else None,
        transition_amplitude=transition,transition_to_endpoint_ratio=transition/1e44,
        objective_reference=reference,structurally_unobservable=all_zero))


def finite_trend(probes,reference,limit):
    values=[p['objective'] for p in probes if p['status']=='finite']
    def tau(a,b): return 1e-6+1e-4*max(abs(a),abs(b))
    if len(values)<2: trend='insufficient_finite_probe_trend'
    elif any(b>a+tau(a,b) for a,b in zip(values,values[1:])) and any(b<a-tau(a,b) for a,b in zip(values,values[1:])): trend='nonmonotonic'
    elif values[-1]<reference-tau(values[-1],reference): trend='strictly_lower'
    elif abs(values[-1]-reference)<=tau(values[-1],reference): trend='indistinguishable'
    else: trend='higher_than_returned'
    return dict(trend=trend,finite_probes=len(values),minimum_finite_objective=min(values) if values else None,
                endpoint_limit_gap=None if not probes or probes[-1]['objective'] is None or limit is None else probes[-1]['objective']-limit)


def forbid_fitting():
    """Runtime guards supplement the absence of fitting call sites."""
    import scipy.optimize as opt
    import numpy as np
    import basketball_shared_spline_v2 as spline
    def denied(*a,**kw): raise RuntimeError('Plan 018 forbids optimizer/initialization/Hessian entry')
    for name in ('minimize','least_squares','minimize_scalar','least_squares'):
        if hasattr(opt,name): setattr(opt,name,denied)
        if hasattr(spline,name): setattr(spline,name,denied)
    spline.SplineProblem.__init__=denied; spline.initialize_coefficients=denied
    np.linalg.lstsq=denied; np.linalg.svd=denied
    # Historical constructors/Hessians are not imported or reachable from this worker.


def worker(end):
    started=read(ROOT/'started.json'); auth=read(AUTH)
    assert started['authorization_sha256']==sha(AUTH)
    assert end==started['deadline_monotonic']-2 and time.monotonic()<end
    assert os.getppid()==started['supervisor_pid']==int(os.environ['V11_SUPERVISOR_PID'])
    assert os.getsid(0)==os.getpid()
    if (ROOT/'budget.json').exists(): raise RuntimeError('allocation consumed')
    publish(ROOT/'worker-claimed.json',dict(pid=os.getpid(),supervisor=os.getppid(),monotonic=time.monotonic()))
    # Wall time includes these imports, all basis construction and independent reload.
    import numpy as np
    for k,v in THREADS.items(): assert os.environ.get(k)==v
    forbid_fitting()
    admission=read(ROOT/'admission.json'); inputs=read(ROOT/'inputs.json')
    exact_hashes(read(ROOT/'execution-sources.json')['sha256']); exact_hashes(inputs['historical_sha256'])
    assert sha(ROOT/'inputs.json')==admission['inputs_sha256']
    cases=inputs['cases']; finite,limits=schedules(cases)
    ledger=Entries(ROOT/'primary.jsonl','primary',finite,limits,end)
    try:
        problems={c['id']:decode_case(c,ledger.check) for c in cases}
        snapshots=[]
        for case in cases:
            for s in case['selected']:
                slot=case['id']+'/snapshot/'+str(s['ordinal']); x=np.frombuffer(bytes.fromhex(s['x_hex']),dtype='<f8')
                snapshots.append(finite_slot(problems[case['id']],x,slot,ledger,s,case))
        publish(ROOT/'snapshots.json.gz',dict(records=snapshots))
        rays=freeze_rays(cases,problems); probes=[]; analytical=[]
        for ray in rays:
            p=problems[ray['case']]; base=np.frombuffer(bytes.fromhex(ray['base_hex']),dtype='<f8'); ray_probes=[]
            for e in range(0,45,2):
                slot=ray['id']+f'/amplitude/{e}'
                if ray['direction'] is None:
                    ledger.allocate(slot,ray['base_hex'],ray['operand_states'])
                    result=dict(slot=slot,status='degenerate_skipped',objective=None,amplitude=10**e)
                    ledger.finish(slot,result)
                else:
                    x=base+float(10**e)*np.asarray(ray['direction'])
                    result=finite_slot(p,x,slot,ledger); result['amplitude']=10**e
                probes.append(result); ray_probes.append(result)
            slot=ray['id']+'/limit'; ledger.allocate(slot,ray['base_hex'],ray['operand_states'])
            reference=next(c['row']['objective'] for c in cases if c['id']==ray['case'])
            result=ledger.call(slot,'limit',ray['base_hex'],lambda:primary_limit(p,ray,reference))
            result.update(slot=slot,ray_id=ray['id'],**finite_trend(ray_probes,reference,result['objective_limit']))
            ledger.finish(slot,result); analytical.append(result)
        publish(ROOT/'probes.json.gz',dict(records=probes)); publish(ROOT/'limits.json',dict(records=analytical))
    finally: ledger.close()
    from basketball_shared_trajectory_verify_v11 import verify
    verify(end)


def run():
    auth=read(AUTH); deadline(auth,'implementation_ready')
    admission=read(ROOT/'admission.json'); assert sha(AUTH)==admission['authorization_sha256']
    assert admission['admitted_monotonic']<auth['deadlines']['admission']['monotonic']
    if (ROOT/'started.json').exists() or (ROOT/'budget.json').exists(): raise RuntimeError('single pass already started or consumed')
    ready=read(ROOT/'readiness.json'); exact_hashes(ready['source_sha256'])
    assert ready['passed'] and ready['monotonic']<auth['deadlines']['implementation_ready']['monotonic']
    log=Path(ready['test_log']).read_text(); assert '\nOK\n' in log or log.rstrip().endswith('OK')
    sources=frozen_sources(); publish(ROOT/'execution-sources.json',dict(sha256=sources,python=PYTHON,threads=THREADS,readiness_monotonic=time.monotonic(),tests_sha256=sha(ready['test_log']),readiness_sha256=sha(ROOT/'readiness.json')))
    deadline(auth,'implementation_ready')
    start=time.monotonic(); end=min(start+120,auth['deadlines']['numerical_end']['monotonic'])
    if end-start<2: raise TimeoutError('insufficient numerical window')
    publish(ROOT/'started.json',dict(start_monotonic=start,deadline_monotonic=end,authorization_sha256=sha(AUTH),supervisor_pid=os.getpid(),slots=1200,limits=48))
    env=os.environ.copy(); env.update(THREADS); env['V11_SUPERVISOR_PID']=str(os.getpid()); child=None; exit_code=None; reason=None
    output=(ROOT/'worker.log').open('x')
    def interrupt(signum,frame): raise KeyboardInterrupt('supervisor signal '+str(signum))
    old_handlers={sig:signal.signal(sig,interrupt) for sig in (signal.SIGTERM,signal.SIGINT)}
    try:
        child=subprocess.Popen([PYTHON,SCRIPT,'worker','--deadline',str(end-2)],env=env,stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
        publish(ROOT/'worker-process.json',dict(pid=child.pid,pgid=child.pid,supervisor_pid=os.getpid(),threads=THREADS,process_limit=2,deadline=end))
        print('Numerical worker PID/PGID',child.pid,'supervisor',os.getpid(),'deadline monotonic',end,flush=True)
        try: exit_code=child.wait(timeout=max(.001,end-time.monotonic()-2))
        except subprocess.TimeoutExpired: reason='numerical deadline'
        except KeyboardInterrupt as e: reason=str(e)
    finally:
        if child is not None and child.poll() is None:
            os.killpg(child.pid,signal.SIGTERM)
            try: child.wait(timeout=max(.001,min(2,end-time.monotonic())))
            except subprocess.TimeoutExpired: os.killpg(child.pid,signal.SIGKILL); child.wait()
        if child is not None: exit_code=child.returncode
        output.close()
        for sig,handler in old_handlers.items(): signal.signal(sig,handler)
        counts={}
        for name in ('primary','independent'):
            path=ROOT/(name+'.jsonl'); events=[json.loads(l) for l in path.read_text().splitlines()] if path.exists() else []
            counts[name]={kind:sum(e['event']=='entry' and e['kind']==kind for e in events) for kind in ('depth','residual','limit')}
            counts[name].update(allocated=sum(e['event']=='allocated' for e in events),completed=sum(e['event']=='completed' for e in events),errors=sum(e['event']=='error' for e in events))
        publish(ROOT/'budget.json',dict(start_monotonic=start,end_monotonic=time.monotonic(),numerical_wall_seconds=time.monotonic()-start,exit_code=exit_code,
            stop_reason=reason,counts=counts,worker_pid=None if child is None else child.pid,worker_stopped=child is None or child.poll() is not None,
            numerical_cap_seconds=120,optimizer_attempts=0,hessians=0,finite_differences=0,gpu_jobs=0,training=0,rendering=0,downloads_installs=0,
            phase_elapsed_seconds=time.monotonic()-auth['t0_monotonic']))
    print('Numerical pass finished:',exit_code,reason,flush=True)


def package():
    auth=read(AUTH); deadline(auth,'phase_end')
    inputs=read(ROOT/'inputs.json'); exact_hashes(inputs['historical_sha256'])
    budget=read(ROOT/'budget.json') if (ROOT/'budget.json').exists() else None
    verification=read(ROOT/'verification.json') if (ROOT/'verification.json').exists() else None
    limits=read(ROOT/'limits.json')['records'] if (ROOT/'limits.json').exists() else []
    snapshots=read(ROOT/'snapshots.json.gz')['records'] if (ROOT/'snapshots.json.gz').exists() else []
    probes=read(ROOT/'probes.json.gz')['records'] if (ROOT/'probes.json.gz').exists() else []
    complete_evaluations=(len(snapshots)==48 and len(probes)==552 and len(limits)==24 and
        all(r['status']=='finite' for r in snapshots) and all(r['status'] in ('finite','infeasible','nonfinite_state','nonfinite_depth','degenerate_skipped') for r in probes))
    cases=[]
    for case in inputs['cases']:
        rows=[r for r in snapshots if r['slot'].startswith(case['id']+'/snapshot/')]
        growth=None
        if len(rows)==4 and all(r['status']=='finite' for r in rows):
            first,last=rows[0]['sampled_max_abs'],rows[-1]['sampled_max_abs']
            growth=dict(initial=first,final=last,ratio=last/first,old_flag=last>max(1e6,100*first),rule='final > max(1e6,100*initial)',
                        original_KKT_inf=[r['original_KKT_inf'] for r in rows],objective=[r['objective'] for r in rows])
        cases.append(dict(case=case['id'],group=case['group'],weight=case['weight'],regularized_control=bool(case['weight']),growth=growth,
                          rays=[{k:r[k] for k in ('ray_id','classification','objective_limit','first_feasibility_boundary','trend','minimum_finite_objective')} for r in limits if r['ray_id'].startswith(case['id']+'/')]))
    passed=bool(verification and verification['passed'] and budget and budget['exit_code']==0 and budget['numerical_wall_seconds']<=120)
    publish(ROOT/'decision.json',dict(status='diagnostic_complete' if passed else 'diagnostic_incomplete_or_failed',acceptance=dict(A1=len(inputs['cases'])==12 and len(snapshots)==48 and (ROOT/'rays.json').exists(),A2=bool(complete_evaluations and verification and verification['passed']),A3=passed,A4='report and validated local commit required'),
        cases=cases,budget=budget,verification_passed=bool(verification and verification['passed']),
        ready_for_full_screens=False,accepted_timing=None,production_candidate=None,final_validation_protocol=None,
        historical_hashes_unchanged=True,main_objective_attained=False,
        next_step='Review retained diagnostic evidence and resolve any arithmetic/ownership gap before another numerical allocation; do not launch a solver policy from this diagnostic alone.'))
    print('Packaged:', 'passed' if passed else 'incomplete or failed',flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('operation',choices=['admit','run','package','worker'])
    parser.add_argument('--deadline',type=float); args=parser.parse_args()
    if args.operation=='admit': admit()
    elif args.operation=='run': run()
    elif args.operation=='package': package()
    else: worker(args.deadline)
