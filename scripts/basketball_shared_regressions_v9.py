"""Observation-only accounting and derivative regressions; no scientific optimizer runs."""
import numpy as np
from unittest.mock import patch
from basketball_shared_accounting_v9 import CanonicalAdapter,Ledger,bytes_of,reconcile
from basketball_shared_solver_v6 import ConstrainedProblem,EvaluationLimit
from basketball_shared_recovery_v8 import fixture


def accounting_regressions():
    from basketball_shared_solver_v8 import Adapter as Old
    old=Old(fixture(2,-25.,0.),True);y=old.coordinates(old.cold)
    rng=np.random.default_rng(15);witness=None
    for _ in range(100):
        trial=y+rng.normal(size=len(y))*.001;q=old.P@trial;qr=q*old.scale/old.scale
        if bytes_of(q)!=bytes_of(qr):witness=(trial,q,qr);break
    assert witness is not None
    trial,q,qr=witness;before=old.base.evaluations;outer=len(old.distinct)
    old.hess(trial)
    assert old.base.evaluations-before==2 and len(old.distinct)-outer==1
    discrepancy=dict(inner_added=old.base.evaluations-before,exported_added=len(old.distinct)-outer,maximum_q_difference=float(np.max(np.abs(q-qr))),physical_equal=bytes_of(q*old.scale)==bytes_of(qr*old.scale))
    records=[]
    for weight in [0.,1.]:
        p=fixture(2,-19.,weight);a=CanonicalAdapter(p,'regression')
        # Record actual lowest-level arguments independently with wrappers around unmodified implementations.
        observed=[];original=p.evaluate;raw=a.numerical.raw.raw_depth
        def observe_residual(x):observed.append(('residual',bytes_of(x)));return original(x)
        def observe_depth(x,v=None):observed.append(('depth',bytes_of(x)));return raw(x,v)
        p.evaluate=observe_residual;a.numerical.raw.raw_depth=observe_depth
        a.set_transform(p.x0,True);y=np.zeros(len(p.x0));s=a.state_y(y,'first')
        before=len(a.ledger.states)
        a.depth(y);a.hess(y);a.jac(y);a.fun(y);a.depth(y,np.ones(p.n))
        assert len(a.ledger.states)==before
        assert all(x==bytes_of(s.x) for _,x in observed)
        oldp=fixture(2,-19.,weight);b=ConstrainedProblem(oldp);r,J=b.evaluate(s.q);z,D=b.raw_depth(s.q)
        np.testing.assert_allclose(a.fun(y),r@r,atol=1e-10,rtol=1e-9)
        np.testing.assert_allclose(a.raw(s)[0],z,atol=1e-12,rtol=1e-12)
        np.testing.assert_allclose(a.jac(y),a.P.T@(2*J.T@r),atol=1e-10,rtol=1e-8)
        v=rng.normal(size=len(y));v/=max(1.,np.linalg.norm(a.P@v));h=1e-5
        H=a.hess(y);fd=(a.jac(y+h*v)-a.jac(y-h*v))/(2*h)
        np.testing.assert_allclose(H@v,fd,atol=2e-5,rtol=2e-4)
        z,D=a.depth(y);w=rng.normal(size=len(z));CH=a.depth(y,w)
        cfd=(a.depth(y+h*v)[1].T@w-a.depth(y-h*v)[1].T@w)/(2*h)
        np.testing.assert_allclose(CH@v,cfd,atol=1e-7,rtol=2e-4)
        np.testing.assert_allclose(a.origin,s.q,atol=0,rtol=0)
        np.testing.assert_allclose(a.P,a.P.T,atol=1e-12,rtol=1e-12)
        np.testing.assert_allclose(a.inverse@a.P,np.eye(len(y)),atol=1e-10,rtol=1e-10)
        records.append(dict(weight=weight,objective_hessian_error=float(np.max(np.abs(H@v-fd))),constraint_hessian_error=float(np.max(np.abs(CH@v-cfd))),**reconcile(a.export())))
    # Adjacent doubles are never merged, including two q values that round to identical physical x.
    l=Ledger('unit',np.ones(2));s=l.request([1.,0.],'constraint_first');t=l.request([np.nextafter(1.,2.),0.],'hessian_first')
    assert s.identity!=t.identity and len(l.states)==2
    for i in range(2,200):l.request([float(i),1.],'rejected_trial')
    l.request(s.q,'returned_state');assert len(l.states)==200
    entered=[]
    try:
        state=l.request([201.,0.],'constraint_only');l.enter(state,'forbidden',lambda x:entered.append(x))
    except EvaluationLimit:pass
    else:raise AssertionError('201st state entered')
    assert not entered
    l.iteration(200)
    try:l.iteration(201)
    except EvaluationLimit:pass
    else:raise AssertionError('iteration reset/bypass')
    l2=Ledger('interrupt',np.ones(1));s=l2.request([1.],'initialization')
    def fail(x):raise TimeoutError('interrupted numerical entry')
    try:l2.enter(s,'residual',fail)
    except TimeoutError:pass
    assert l2.export()['interrupted']==1 and l2.export()['completed']==0
    # Every first-request route owns its canonical state, including Hessian- and constraint-first calls.
    for first in ['fun','jac','hess','depth']:
        a=CanonicalAdapter(fixture(2,0.,1.));q=a.p.x0/a.scale
        getattr(a,first)(q);a.fun(q);a.jac(q);a.hess(q);a.depth(q)
        assert len(a.ledger.states)==1;reconcile(a.export())
    from basketball_shared_stopping_v9 import qualified
    assert not qualified(True,np.array([1.02844e-6]),np.array([3.]),[])
    assert not qualified(True,None,np.array([3.]),[])
    return dict(passed=True,two_cache_discrepancy=discrepancy,derivatives=records,adjacent_states_distinct=True,
        canonical_all_entries=True,derivative_and_constraint_first=True,cap_before_201=True,shared_iteration_budget=True,interrupted_entries_retained=True,
        returned_state_ownership=True,stationarity_unchanged=True,scientific_solves=0)
