"""Pre-cohort derivative and search regressions, without scientific cohort fits."""
import numpy as np
from basketball_shared_recovery_v8 import fixture
from basketball_shared_solver_v8 import Adapter,matrix_transform,EvaluationLimit

def conditioning_regressions():
    p=fixture(2,-19.,1.);a=Adapter(p,True);y=a.coordinates(a.cold)
    np.testing.assert_allclose(a.physical(y),a.cold,atol=1e-10,rtol=1e-10)
    rng=np.random.default_rng(14);v=rng.normal(size=len(y));v/=np.linalg.norm(v)
    h=1e-5
    # Smaller internal directions keep physical perturbations in the local regime.
    v/=max(1.,np.linalg.norm(a.P@v));H=a.hess(y);fd=(a.jac(y+h*v)-a.jac(y-h*v))/(2*h)
    np.testing.assert_allclose(H@v,fd,atol=2e-5,rtol=2e-4)
    z,D=a.depth(y);w=rng.normal(size=len(z));CH=a.depth(y,w)
    cfd=(a.depth(y+h*v)[1].T@w-a.depth(y-h*v)[1].T@w)/(2*h)
    np.testing.assert_allclose(CH@v,cfd,atol=1e-7,rtol=2e-4)
    np.testing.assert_allclose(a.jac(y)@v,(a.fun(y+h*v)-a.fun(y-h*v))/(2*h),atol=1e-6,rtol=1e-4)
    J=np.diag([2.,2.,0.,0.]);P,meta=matrix_transform(J,0);P2,_=matrix_transform(J,0)
    np.testing.assert_array_equal(P,P2);assert meta['scales']==[.5,.5,1.,1.]
    np.testing.assert_allclose(P.T@P,np.diag([.25,.25,1.,1.]),atol=1e-12)
    assert a.gtol<=1e-6 and len(a.distinct)<=200
    # Derivative-first calls share one ledger state and enforce the same hard cap.
    b=Adapter(fixture(2,0.,1.));q=b.coordinates(b.cold)
    b.hess(q);assert len(b.distinct)==1;b.jac(q);b.depth(q);assert len(b.distinct)==1
    b.distinct={str(i):{} for i in range(200)}
    try:b.hess(q+np.eye(1,len(q),2).ravel()*1e-5)
    except EvaluationLimit:pass
    else:raise AssertionError('derivative-first state cap bypass')
    return dict(passed=True,round_trip=True,deterministic_repeated_and_null=True,objective_hessian_fd_error=float(np.max(np.abs(H@v-fd))),constraint_hessian_fd_error=float(np.max(np.abs(CH@v-cfd))),derivative_first_cap=True,full_coefficients=len(P))

def scalar_regressions():
    from basketball_shared_scalar_search_v8 import minima,refinement
    assert minima([-1,0,1],[1,1,2])==[0,1]
    assert minima([-1,0,1],[1,None,0])==[]
    curves={d:{float(x):dict(valid=True,objective=1.) for x in [-1,0,1]} for d in ['cold','ascending','descending']}
    added=refinement(curves,.05)
    assert len(added)==38 and -.95 in added and .95 in added
    for curve in curves.values():
        for x in added:curve[x]=dict(valid=True,objective=1.)
    finer=refinement(curves,.01,True)
    assert all(round(x,2)==x for x in finer) and -.99 in finer and .99 in finer
    return dict(passed=True,inclusive_ties_and_endpoints=True,failed_neighbors_retained=True,flat_refinement_complete=True)
