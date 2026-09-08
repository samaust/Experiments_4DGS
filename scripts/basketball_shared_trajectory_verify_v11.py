"""Independent scalar-coefficient spline arithmetic and fixed entry audit.

Only immutable serialization, schedules and journal budget helpers are shared.
No primary mathematical arrays or classifications are used to compute results.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
from scipy.interpolate import BSpline
from basketball_shared_trajectory_diagnostic_v11 import (
    ROOT, Entries, read, publish, plain, sha, exact_hashes, schedules, TOLS)


class Direct:
    def __init__(self,case):
        self.case=case; self.row=case['row']; p=self.row['accounting']['problem']
        self.knots=np.asarray(self.row['knots']); self.center=np.asarray(self.row['center']); self.diameter=self.row['diameter']
        self.weight=p['weight']; self.samples=[]
        self.basis=[BSpline(self.knots,np.eye(18)[i],3,extrapolate=False) for i in range(18)]
        self.quad=np.arange(p['window'][0]-25,p['window'][1]+26,dtype=float)/25
        self.A=np.column_stack([b.derivative(2)(self.quad) for b in self.basis])
        self.nacc=len(self.quad); self.n=300
        for obs in p['observations'][0]['observations']:
            cid=obs['camera_id']; t=(np.asarray(obs['frames'])-p['offsets'][str(cid)])/25
            cam=p['calibration'][str(cid)]; B=np.column_stack([b(t) for b in self.basis])
            self.samples.append(dict(cid=cid,frames=obs['frames'],times=t,B=B,R=np.asarray(cam['R']),tvec=np.asarray(cam['t']),
                                     K=np.asarray(cam['K']),k=cam['parameters_colmap'][3],xy=np.asarray(obs['xy'])))
        a=self.row['accounting']; self.P=np.frombuffer(bytes.fromhex(a['transform_hex']),dtype='<f8').reshape(54,54)
        self.inverse=np.linalg.inv(self.P)
    def trajectory(self,C,t,derivative=0):
        return np.column_stack([BSpline(self.knots,C[:,axis],3,extrapolate=False).derivative(derivative)(t) for axis in range(3)])
    def depth(self,x):
        C=x.reshape(18,3); z=[]; jac=[]
        for s in self.samples:
            world=self.trajectory(C,s['times'])*self.diameter+self.center
            camera=world@s['R'].T+s['tvec']; z.extend(camera[:,2]/self.diameter)
            # Independent coefficient partials from basis and camera rotation.
            jac.append(np.column_stack([s['B'][:,i]*s['R'][2,k] for i in range(18) for k in range(3)]))
        return np.asarray(z),np.vstack(jac)
    def objective(self,x):
        C=x.reshape(18,3); G=np.zeros((18,3)); losses=[]; xyz_rows=[]
        for s in self.samples:
            xyz=self.trajectory(C,s['times']); camera=(xyz*self.diameter+self.center)@s['R'].T+s['tvec']
            u=camera[:,:2]/camera[:,2,None]; r2=np.sum(u*u,axis=1)
            predicted=(u*(1+s['k']*r2)[:,None])@s['K'][:2,:2].T+s['K'][:2,2]
            e=predicted-s['xy']; losses.extend(2*(np.sqrt(1+np.sum(e*e,axis=1))-1))
            point=2*e/(self.n*np.sqrt(1+np.sum(e*e,axis=1)))[:,None]
            radial=(1+s['k']*r2)[:,None,None]*np.eye(2)+2*s['k']*u[:,:,None]*u[:,None,:]
            perspective=np.zeros((len(u),2,3)); perspective[:,0,0]=1/camera[:,2]; perspective[:,1,1]=1/camera[:,2]
            perspective[:,:,2]=-u/camera[:,2,None]
            image=np.einsum('ab,nbc,ncd,de->nae',s['K'][:2,:2],radial,perspective,s['R'])*self.diameter
            G+=s['B'].T@np.einsum('na,nab->nb',point,image)
            xyz_rows.append(dict(camera=s['cid'],frames=s['frames'],times=s['times'],xyz=xyz))
        acc=self.trajectory(C,self.quad,2)
        G+=2*self.weight/self.nacc*self.A.T@acc
        data=float(np.mean(losses)); acceleration=float(self.weight*np.sum(acc*acc)/self.nacc)
        return dict(objective=data+acceleration,data_objective=data,acceleration_cost=acceleration,G=G.ravel(),
                    trajectories=xyz_rows,sampled_max_abs=float(max(np.max(np.abs(r['xyz'])) for r in xyz_rows)),coefficient_max_abs=float(np.max(np.abs(x))))
    def forces(self,z,D,G,snapshot):
        vg=np.asarray(snapshot['callback']['multipliers'][0]); vb=np.asarray(snapshot['callback']['multipliers'][1])
        slack=z-1e-8; reciprocal=1/np.hypot(1,slack); derivative=reciprocal*reciprocal*reciprocal
        vd=vg*derivative; Cdepth=D.T@vd; Cbounds=self.inverse.T@vb; KKT=G+Cdepth+Cbounds
        return dict(multipliers_transformed=vg,multipliers_depth=vd,bound_multipliers=Cbounds,C_depth=Cdepth,C_bounds=Cbounds,KKT=KKT,
                    transformed_KKT=self.P.T@KKT,complementarity_original=vd*slack)
    def ray(self,case,operand,sign):
        base=np.frombuffer(bytes.fromhex(case['selected'][-1]['x_hex']),dtype='<f8')
        other=np.frombuffer(bytes.fromhex(case['selected'][operand]['x_hex']),dtype='<f8'); delta=base-other
        # Independently reconstructed scalar basis; same normalization definition.
        m=float(max(np.max(np.abs(s['B']@delta.reshape(18,3))) for s in self.samples))
        return base,delta,m,None if m==0 else sign*delta/m
    def limit(self,base,d,reference):
        if d is None: return dict(classification='degenerate',objective_limit=None)
        C=base.reshape(18,3); delta=d.reshape(18,3); unknown=[]; feasible=True; divergent=False
        all_static=True; transition=0.; boundaries=[]; errors=[]; observations=[]
        for s in self.samples:
            b=(self.trajectory(C,s['times'])*self.diameter+self.center)@s['R'].T+s['tvec']
            v=self.trajectory(delta,s['times'])*self.diameter@s['R'].T
            certificate=np.ones(v.shape,dtype=bool)
            # Exact interval and coefficient-factor proof, independently expressed.
            for sample_index,t in enumerate(s['times']):
                for axis in range(3):
                    for i in range(18):
                        if s['B'][sample_index,i]!=0 or self.knots[i]<t<self.knots[i+4]:
                            if any(delta[i,j]!=0 and s['R'][axis,j]!=0 for j in range(3)):
                                certificate[sample_index,axis]=False; break
            all_static=all_static and bool(certificate.all())
            for axis in range(3):
                if np.any((v[:,axis]==0)&~certificate[:,axis]): unknown.append('uncertified camera component cancellation')
            slopes=v[:,2]; moving=slopes!=0; neg=slopes<0
            if np.any(neg):
                feasible=False; boundaries.extend(((b[neg,2]-1e-8*self.diameter)/(-slopes[neg])).tolist())
            if np.any((slopes==0)&(b[:,2]/self.diameter<=1e-8)): feasible=False
            if np.any(moving): transition=max(transition,float(np.max(np.abs(b[moving,2]/slopes[moving]))))
            if np.any((slopes==0)&np.any(v[:,:2]!=0,axis=1)&certificate[:,2]): divergent=True
            uv=b[:,:2]/b[:,2,None]; uv[moving]=v[moving,:2]/slopes[moving,None]
            xy=(uv*(1+s['k']*np.sum(uv**2,axis=1))[:,None])@s['K'][:2,:2].T+s['K'][:2,2]
            errors.extend(np.sum((xy-s['xy'])**2,axis=1))
            observations.append(dict(camera=s['cid'],b=b,v=v,structural_zero_components=certificate))
        acc=self.trajectory(C,self.quad,2); da=self.trajectory(delta,self.quad,2)
        invariant=all(np.array_equal(delta[i],delta[0]) for i in range(18))
        if self.weight:
            if np.any(da!=0) and not invariant: divergent=True
            elif not invariant: unknown.append('uncertified acceleration cancellation')
        data=float(np.mean(2*(np.sqrt(1+np.asarray(errors))-1)))
        acceleration=float(self.weight*np.sum(acc**2)/self.nacc)
        limit=None if divergent else data+acceleration
        if not np.isfinite(data) or not np.isfinite(acceleration) or not np.isfinite(transition): unknown.append('nonfinite analytical arithmetic')
        if unknown: classification='unresolved_arithmetic'
        elif not feasible: classification='infeasible_at_infinity'
        elif all_static and (not self.weight or invariant): classification='structurally_unobservable_objective_invariant'
        elif divergent: classification='divergent_objective'
        elif limit>reference+1e-6+1e-4*max(abs(limit),abs(reference)): classification='finite_noncompetitive_limit'
        else: classification='competitive_feasible_finite_limit'
        return plain(dict(classification=classification,objective_limit=limit,data_limit=data,acceleration_base_cost=acceleration,
                    feasible_at_infinity=feasible,unresolved=sorted(set(unknown)),samples=observations,
                    first_feasibility_boundary=min(boundaries) if boundaries else None,transition_amplitude=transition,
                    acceleration_invariant_structural=invariant,structurally_unobservable=all_static))


def arithmetic_check(a,b,kind):
    a=np.asarray(a); b=np.asarray(b); atol,rtol=TOLS[kind]
    return dict(passed=bool(a.shape==b.shape and np.isfinite(a).all() and np.isfinite(b).all() and np.allclose(a,b,atol=atol,rtol=rtol)),
                maximum_absolute_error=float(np.max(np.abs(a-b))) if a.shape==b.shape and a.size else None)


def direct_slot(p,x,slot,ledger,snapshot=None):
    hx=x.astype('<f8').tobytes().hex(); ledger.allocate(slot,hx,None if snapshot is None else snapshot['state']['identity'])
    result=dict(slot=slot,physical_hex=hx,status=None,objective=None)
    try:
        if not np.isfinite(x).all(): result['status']='nonfinite_state'
        else:
            z,D=ledger.call(slot,'depth',x,lambda:p.depth(x))
            if not np.isfinite(z).all() or not np.isfinite(D).all(): result['status']='nonfinite_depth'
            else:
                result.update(depths=z,minimum_depth=float(min(z)))
                if np.any(z<=1e-8): result['status']='infeasible'
                else:
                    value=ledger.call(slot,'residual',x,lambda:p.objective(x))
                    if not all(np.isfinite(value[k]).all() for k in ('objective','data_objective','acceleration_cost','G')): result['status']='nonfinite_objective_or_gradient'
                    else:
                        result.update(value,status='finite')
                        if snapshot is not None: result.update(p.forces(z,D,value['G'],snapshot))
    except (FloatingPointError,OverflowError,ValueError) as e:
        result.update(status='entry_error',error=type(e).__name__+': '+str(e),objective=None)
    result=plain(result); ledger.finish(slot,result); return result


def audit_events(path,finite,limits):
    events=[json.loads(l) for l in Path(path).read_text().splitlines()]
    allocated={}; entries={}; returns=set(); errors=set(); completed=set(); counts={}
    for e in events:
        slot=e['slot']; assert slot in set(finite)|set(limits)
        if e['event']=='allocated':
            assert slot not in allocated and e['cache_hit'] is False
            assert hashlib.sha256(bytes.fromhex(e['physical_hex'])).hexdigest()==e['physical_sha256']; allocated[slot]=e
        elif e['event']=='entry':
            key=(slot,e['kind']); assert key not in entries and slot in allocated and slot not in completed
            assert e['physical_hex']==allocated[slot]['physical_hex']
            assert e['kind'] in (('depth','residual') if slot in finite else ('limit',))
            if e['kind']=='residual': assert (slot,'depth') in returns
            entries[key]=e; counts[e['kind']]=counts.get(e['kind'],0)+1
        elif e['event'] in ('return','error'):
            key=(slot,e['kind']); assert key in entries and key not in returns|errors
            (returns if e['event']=='return' else errors).add(key)
        elif e['event']=='completed':
            assert slot in allocated and slot not in completed; completed.add(slot)
        else: raise AssertionError('unknown journal event')
    assert len(allocated)==len(completed)==len(finite)+len(limits)
    assert set(entries)==returns|errors
    assert counts.get('depth',0)<=600 and counts.get('residual',0)<=600 and counts.get('limit',0)==24
    return dict(passed=True,allocated=len(allocated),completed=len(completed),entries=counts,errors=len(errors))


def verify(end):
    inputs=read(ROOT/'inputs.json'); exact_hashes(inputs['historical_sha256']); exact_hashes(read(ROOT/'execution-sources.json')['sha256'])
    cases=inputs['cases']; finite,limits=schedules(cases)
    primary={r['slot']:r for name in ('snapshots.json.gz','probes.json.gz') for r in read(ROOT/name)['records']}
    primary_limits={r['slot']:r for r in read(ROOT/'limits.json')['records']}
    saved_rays={r['id']:r for r in read(ROOT/'rays.json')['rays']}
    ledger=Entries(ROOT/'independent.jsonl','independent',finite,limits,end)
    checks=[]; limit_checks=[]; identities=[]
    def compare(result):
        expected=primary[result['slot']]; detail=dict(slot=result['slot'],status_match=result['status']==expected['status'],
             physical_identity=result.get('physical_hex')==expected.get('physical_hex'),checks={})
        for k in ('depths','minimum_depth'):
            if k in result and k in expected: detail['checks'][k]=arithmetic_check(result[k],expected[k],'depths')
        if result['status']==expected['status']=='finite':
            for k in ('objective','data_objective','acceleration_cost'): detail['checks'][k]=arithmetic_check(result[k],expected[k],'objective')
            for k in ('G','C_depth','C_bounds','KKT','transformed_KKT'):
                if k in result: detail['checks'][k]=arithmetic_check(result[k],expected[k],'forces')
            for k in ('multipliers_transformed','multipliers_depth','bound_multipliers','complementarity_original'):
                if k in result: detail['checks'][k]=arithmetic_check(result[k],expected[k],'multipliers')
        detail['passed']=result['status']!='entry_error' and detail['status_match'] and detail['physical_identity'] and all(v['passed'] for v in detail['checks'].values())
        checks.append(detail)
    try:
        for case in cases:
            # Reload originals, not the primary snapshots, as arithmetic inputs.
            original=read(Path(case['directory'])/'attempt.json.gz'); assert original['row']==case['row'] and original['identity']==case['identity']
            p=Direct(case)
            for snapshot in case['selected']:
                x=np.frombuffer(bytes.fromhex(snapshot['x_hex']),dtype='<f8'); slot=case['id']+'/snapshot/'+str(snapshot['ordinal'])
                compare(direct_slot(p,x,slot,ledger,snapshot))
            if case['arm']!='metric': continue
            for operand in (0,2):
                for sign in (1,-1):
                    rid=case['id']+f'/ray/{operand}/{sign}'; saved=saved_rays[rid]
                    base,delta,m,d=p.ray(case,operand,sign)
                    identity=(base.astype('<f8').tobytes().hex()==saved['base_hex'] and np.array_equal(delta,saved['delta']) and m==saved['m'] and
                              (d is None and saved['direction_hex'] is None or d is not None and d.astype('<f8').tobytes().hex()==saved['direction_hex']))
                    identities.append(dict(ray_id=rid,exact_derivation=bool(identity)))
                    for e in range(0,45,2):
                        slot=rid+f'/amplitude/{e}'
                        if d is None:
                            ledger.allocate(slot,saved['base_hex']); result=dict(slot=slot,status='degenerate_skipped',objective=None)
                            ledger.finish(slot,result); compare(result)
                        else: compare(direct_slot(p,base+float(10**e)*d,slot,ledger))
                    slot=rid+'/limit'; hx=base.astype('<f8').tobytes().hex(); ledger.allocate(slot,hx)
                    result=ledger.call(slot,'limit',hx,lambda:p.limit(base,d,case['row']['objective']))
                    ledger.finish(slot,result); expected=primary_limits[slot]
                    detail=dict(slot=slot,classification_match=result['classification']==expected['classification'],checks={})
                    for k in ('objective_limit','data_limit','acceleration_base_cost'):
                        if result.get(k) is not None and expected.get(k) is not None: detail['checks'][k]=arithmetic_check(result[k],expected[k],'objective')
                        elif result.get(k)!=expected.get(k): detail['checks'][k]=dict(passed=False,maximum_absolute_error=None)
                    detail['feasibility_match']=result.get('feasible_at_infinity')==expected.get('feasible_at_infinity')
                    detail['cancellation_or_sign_disagreement']=[]
                    for actual_sample,saved_sample in zip(result.get('samples',[]),expected.get('samples',[])):
                        a=np.asarray(actual_sample['v']); b=np.asarray(saved_sample['v'])
                        if not np.array_equal(np.sign(a[:,2]),np.sign(b[:,2])):
                            detail['cancellation_or_sign_disagreement'].append(actual_sample['camera'])
                    detail['passed']=bool(detail['classification_match'] and detail['feasibility_match'] and not detail['cancellation_or_sign_disagreement'] and all(v['passed'] for v in detail['checks'].values()))
                    limit_checks.append(detail)
    finally: ledger.close()
    audits={name:audit_events(ROOT/(name+'.jsonl'),finite,limits) for name in ('primary','independent')}
    for kind in ('depth','residual'): assert sum(a['entries'].get(kind,0) for a in audits.values())<=1200
    saved_checks=[check for r in read(ROOT/'snapshots.json.gz')['records'] for check in r.get('saved_checks',{}).values()]
    exact_hashes(inputs['historical_sha256']); exact_hashes(read(ROOT/'execution-sources.json')['sha256'])
    passed=(len(checks)==600 and len(limit_checks)==24 and len(identities)==24 and all(c['passed'] for c in checks+limit_checks+saved_checks)
            and all(c['exact_derivation'] for c in identities))
    maxima={}
    for detail in checks+limit_checks:
        for name,check in detail['checks'].items():
            if check['maximum_absolute_error'] is not None: maxima[name]=max(maxima.get(name,0),check['maximum_absolute_error'])
    publish(ROOT/'verification.json',dict(passed=bool(passed),finite_checks=checks,limit_checks=limit_checks,ray_identities=identities,
        journals=audits,saved_callback_checks_passed=all(c['passed'] for c in saved_checks),max_errors=maxima,
        historical_hashes_unchanged=True,execution_hashes_unchanged=True,independent_arithmetic='scalar coefficient BSplines and direct point-loss differentiation'))
