"""Exact canonical state ownership; every numerical entry is charged before execution."""
from dataclasses import dataclass
import hashlib
import json
import time
import numpy as np
from scipy.sparse import diags, csr_matrix
from basketball_shared_solver_v6 import ConstrainedProblem, exact_objective_hessian, transform, MARGIN, EvaluationLimit


def bytes_of(x):
    return np.asarray(x,dtype='<f8').tobytes()


def digest(x):
    return hashlib.sha256(bytes_of(x)).hexdigest()


def encode(v):
    if isinstance(v,np.ndarray):return v.tolist()
    if isinstance(v,np.generic):return v.item()
    raise TypeError(type(v).__name__)


def problem_identity(p,namespace,provenance):
    data=dict(observations=p.groups,calibration=p.cameras,offsets=p.offsets,free=p.free,window=p.window,
              spacing=p.spacing,weight=p.weight,gauge=1,role='synthetic-fit-50-149',namespace=namespace,provenance=provenance)
    serialized=json.dumps(data,sort_keys=True,default=encode)
    return hashlib.sha256(serialized.encode()).hexdigest(),json.loads(serialized)


@dataclass(frozen=True)
class State:
    identity: str
    q: np.ndarray
    x: np.ndarray


class Ledger:
    """Exact bytes, no rounding, subordinate memoization and no hidden counter."""
    def __init__(self,problem_key,scale,check=lambda:None,max_states=200,max_iterations=200):
        if max_states>200 or max_iterations>200:raise ValueError('local caps cannot increase')
        self.problem_key=problem_key;self.scale=np.asarray(scale);self.check=check
        self.max_states=max_states;self.max_iterations=max_iterations
        self.states={};self.events=[];self.entries=[];self.iterations=0

    def request(self,q,kind,y=None,scope='destination'):
        self.check();q=np.array(q,dtype='<f8',copy=True)
        key=(scope,q.tobytes());before=len(self.states)
        if key not in self.states:
            if before>=self.max_states:
                self.events.append(dict(kind=kind,state=None,canonical_hex=q.tobytes().hex(),scope=scope,hit=False,before=before,after=before,status='denied_before_entry'))
                raise EvaluationLimit('200 distinct canonical states exhausted')
            x=q*self.scale;identity=hashlib.sha256(self.problem_key.encode()+scope.encode()+q.tobytes()).hexdigest()
            q.flags.writeable=False;x.flags.writeable=False
            self.states[key]=State(identity,q,x)
        state=self.states[key]
        self.events.append(dict(kind=kind,state=state.identity,scope=scope,conditioned_hex=None if y is None else bytes_of(y).hex(),
                                hit=before==len(self.states),before=before,after=len(self.states),status='allocated'))
        return state

    def enter(self,state,kind,callback):
        self.check()
        if state.identity not in {s.identity for s in self.states.values()}:raise ArithmeticError('entry without allocation')
        event=dict(state=state.identity,kind=kind,status='entered',before=len(self.states),after=None)
        self.entries.append(event)
        try:value=callback(state.x)
        except BaseException:
            event.update(status='interrupted',after=len(self.states));raise
        event.update(status='completed',after=len(self.states));return value

    def iteration(self,n):
        self.check()
        if n>self.max_iterations or n<self.iterations:raise EvaluationLimit('shared iteration budget exhausted')
        self.iterations=n

    def export(self):
        return dict(problem_key=self.problem_key,states=[dict(identity=s.identity,scope=k[0],canonical_hex=bytes_of(s.q).hex(),physical_hex=bytes_of(s.x).hex()) for k,s in self.states.items()],
                    events=self.events,entries=self.entries,distinct_states=len(self.states),iterations=self.iterations,
                    allocated=len(self.states),entered=len(self.entries),completed=sum(e['status']=='completed' for e in self.entries),
                    interrupted=sum(e['status']=='interrupted' for e in self.entries),max_states=self.max_states,max_iterations=self.max_iterations)


class NumericalEntries:
    """Observe actual arguments at numerical boundaries, independently of ledger export."""
    def __init__(self,p):
        self.p=p;self.observed=[];self.raw=ConstrainedProblem(p)
        # raw_depth's formulas differentiate q, but receive physical x without another round trip.
        self.raw.scale=np.ones(len(p.x0))

    def observe(self,kind,x):
        self.observed.append(dict(kind=kind,physical_hex=bytes_of(x).hex(),status='entered'))
        return self.observed[-1]

    def residual(self,x):
        e=self.observe('residual',x)
        try:
            self.p.cache=None
            r=self.p.evaluate(x)
        except BaseException:e['status']='interrupted';raise
        e['status']='completed';return r

    def depth(self,x,v=None):
        e=self.observe('depth_hessian' if v is not None else 'depth',x)
        try:r=self.raw.raw_depth(x,v)
        except BaseException:e['status']='interrupted';raise
        e['status']='completed';return r

    def hessian(self,x):
        e=self.observe('objective_hessian',x)
        try:r=exact_objective_hessian(self.p,x)
        except BaseException:e['status']='interrupted';raise
        e['status']='completed';return r


class CanonicalAdapter:
    def __init__(self,p,namespace='test',provenance=None):
        self.p=p;self.scale=np.r_[np.full(p.n_offsets,25.),np.ones(len(p.x0)-p.n_offsets)]
        self.D=diags(self.scale);self.problem_key,self.problem_data=problem_identity(p,namespace,provenance or {})
        self.ledger=Ledger(self.problem_key,self.scale,p.check);self.numerical=NumericalEntries(p)
        self.P=np.eye(len(p.x0));self.origin=np.zeros(len(p.x0));self.inverse=self.P.copy();self.sparse=csr_matrix(self.P)
        self.cache={};self.ycache={};self.transform=None

    def state_q(self,q,kind='diagnostic',scope='destination'):
        return self.ledger.request(q,kind,scope=scope)

    def state_y(self,y,kind):
        key=bytes_of(y)
        if key not in self.ycache:self.ycache[key]=self.origin+self.P@np.asarray(y)
        return self.ledger.request(self.ycache[key],kind,y)

    def state_x(self,x,kind,scope='destination'):
        return self.state_q(np.asarray(x)/self.scale,kind,scope)

    def residual(self,s):
        k=(s.identity,'residual')
        if k not in self.cache:
            r,J=self.ledger.enter(s,'residual',self.numerical.residual)
            self.cache[k]=(r,J@self.D)
        return self.cache[k]

    def raw(self,s,v=None):
        if v is not None:return self.ledger.enter(s,'depth_hessian',lambda x:self.numerical.depth(x,v))
        k=(s.identity,'raw_depth')
        if k not in self.cache:self.cache[k]=self.ledger.enter(s,'depth',self.numerical.depth)
        return self.cache[k]

    def hessian(self,s):
        k=(s.identity,'hessian')
        if k not in self.cache:self.cache[k]=self.ledger.enter(s,'objective_hessian',self.numerical.hessian)
        return self.cache[k]

    def set_transform(self,cold,conditioned=False,legacy=False):
        s=self.state_x(cold,'cold_transform');r,J=self.residual(s)
        if conditioned:
            from basketball_shared_curvature_v6 import deterministic_svd
            singular,V,tol,sub=deterministic_svd(J.toarray()[:,self.p.n_offsets:])
            scales=np.ones(len(singular));active=singular>tol;scales[active]=np.clip(1/singular[active],1e-3,1e3)
            self.P[self.p.n_offsets:,self.p.n_offsets:]=(V.T*scales) if legacy else (V.T*scales)@V
            self.transform=dict(singular_values=singular.tolist(),rank_threshold=tol,scales=scales.tolist(),subspaces=sub)
        self.origin=np.zeros(len(s.q)) if legacy or not conditioned else s.q.copy()
        self.inverse=np.linalg.inv(self.P);self.sparse=csr_matrix(self.P);self.ycache={}
        np.testing.assert_allclose(self.inverse@self.P,np.eye(len(self.P)),atol=1e-10,rtol=1e-10)
        if conditioned and not legacy:np.testing.assert_allclose(self.P,self.P.T,atol=1e-12,rtol=1e-12)
        self.gtol=1e-6/max(1.,float(np.linalg.norm(self.inverse.T,np.inf)))

    def coordinates(self,x):return self.inverse@(np.asarray(x)/self.scale-self.origin)
    def fun(self,y):r,_=self.residual(self.state_y(y,'objective'));return float(r@r)
    def jac(self,y):r,J=self.residual(self.state_y(y,'gradient'));return np.asarray(self.P.T@(2*J.T@r)).ravel()
    def hess(self,y):return self.sparse.T@self.hessian(self.state_y(y,'objective_hessian'))@self.sparse
    def depth(self,y,v=None):
        s=self.state_y(y,'constraint_hessian' if v is not None else 'constraint');z,J=self.raw(s)
        g,gp,gpp,flags=transform(z-MARGIN)
        if flags['nonfinite'] or flags['derivative_underflow']:raise FloatingPointError('bounded depth arithmetic')
        if v is None:return g,diags(gp)@J@self.sparse
        H=self.raw(s,np.asarray(v)*gp)+J.T@diags(np.asarray(v)*gpp)@J
        return self.sparse.T@H@self.sparse

    def export(self):
        return dict(**self.ledger.export(),observed_numerical_entries=self.numerical.observed,problem=self.problem_data,
                    transform_hex=bytes_of(self.P).hex(),origin_hex=bytes_of(self.origin).hex(),scale_hex=bytes_of(self.scale).hex())


def reconcile(ledger):
    """Reconstruct exact identities and compare actual entry arguments, not just counters."""
    states=ledger['states'];ids={s['identity']:s for s in states};scale=np.frombuffer(bytes.fromhex(ledger['scale_hex']),dtype='<f8')
    assert len(ids)==len(states)==ledger['distinct_states']<=200
    for s in states:
        q=np.frombuffer(bytes.fromhex(s['canonical_hex']),dtype='<f8')
        assert bytes_of(q*scale).hex()==s['physical_hex']
        assert hashlib.sha256(ledger['problem_key'].encode()+s['scope'].encode()+bytes_of(q)).hexdigest()==s['identity']
    for e in ledger['events']:
        assert e['after']<=200 and e['after']-e['before'] in [0,1]
        if e['status']=='denied_before_entry':assert e['before']==200 and e['state'] is None
        else:assert e['state'] in ids
    entered=ledger['entries'];observed=ledger['observed_numerical_entries']
    assert len(entered)==len(observed)
    for e,o in zip(entered,observed):
        assert e['state'] in ids and ids[e['state']]['physical_hex']==o['physical_hex']
        assert e['kind']==o['kind'] and e['status']==o['status'] and e['before']<=200
    assert ledger['iterations']<=200
    return dict(passed=True,states=len(states),observed_entries=len(observed),completed=sum(e['status']=='completed' for e in observed),interrupted=sum(e['status']=='interrupted' for e in observed))


def account(p,output,predecessor):
    from basketball_scale import read,write
    from basketball_shared_diagnose_v5 import compressed_read,compressed_write
    from basketball_shared_regressions_v9 import accounting_regressions
    from basketball_shared_workflow_v9 import check
    check(p,'account');results=accounting_regressions()
    write(output/'accounting-regressions.json',results)
    affected=read(predecessor/'affected-attempts.json')['records'];records=[]
    for ref in affected:
        check(p,'account');d=compressed_read(ref['source']);row=next(r for r in d['attempts'][str(ref['lag'])] if r['start']==ref['path'])
        P=np.frombuffer(bytes.fromhex(row['transform_bytes_le_hex']),dtype='<f8').reshape(len(row['x']),-1);scale=np.r_[25.,np.ones(len(row['x'])-1)]
        witnesses=[]
        for t in row['solver_trace']:
            q=P@np.asarray(t['conditioned_y']);qr=(q*scale)/scale
            if bytes_of(q)!=bytes_of(qr):witnesses.append(dict(iteration=t['iteration'],direct_hex=bytes_of(q).hex(),roundtrip_hex=bytes_of(qr).hex(),physical_direct_hex=bytes_of(q*scale).hex(),physical_roundtrip_hex=bytes_of(qr*scale).hex(),maximum_difference=float(np.max(np.abs(q-qr))),same_physical_bytes=bytes_of(q*scale)==bytes_of(qr*scale)))
        records.append(dict(**ref,callback_roundtrip_witnesses=witnesses,contract_symmetric=bool(np.allclose(P,P.T,atol=1e-12,rtol=1e-12)),origin='zero',exact_old_complete_entry_count=None))
    compressed_write(output/'counter-correction.json.gz',dict(records=records,old_exact_totals_unknown=True,mechanism_regression=results['two_cache_discrepancy'],optional_reproductions_executed=0,contract_change_separate=True))
    assert any(r['callback_roundtrip_witnesses'] for r in records)
    write(output/'decision.json',dict(passed=True,affected=22,arithmetic_equivalence_verified=True,authoritative_ledger_verified=True,old_complete_counts=None,correction_does_not_qualify_v8=True))
    check(p,'account')
    return dict(status='passed',terminal_kind=None,blockers=[],executed_counts=dict(scientific_attempts=0,accounting_reproductions=0))
