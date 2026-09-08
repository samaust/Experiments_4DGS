"""Full-coordinate v6 exact solver adapter with derivative-first state accounting."""
import hashlib
import time
import warnings
import numpy as np
from scipy.sparse import csr_matrix,diags
from scipy.optimize import minimize,Bounds,NonlinearConstraint
from basketball_shared_solver_v6 import ConstrainedProblem as Base, sanitize, transform, POLICY, MARGIN, QUALIFICATION_DEPTH, EvaluationLimit, support
from basketball_shared_curvature_v6 import deterministic_svd

def matrix_transform(J,n_offsets):
    J=np.asarray(J);s,V,tol,sub=deterministic_svd(J[:,n_offsets:])
    scales=np.ones(len(s));mask=s>tol;scales[mask]=np.clip(1/s[mask],1e-3,1e3)
    P=np.eye(J.shape[1]);P[n_offsets:,n_offsets:]=V.T*scales
    if not np.allclose(np.linalg.inv(P)@P,np.eye(len(P)),atol=1e-10,rtol=1e-10):raise ArithmeticError('noninvertible coefficient transform')
    return P,dict(singular_values=s.tolist(),rank_threshold=tol,scales=scales.tolist(),subspaces=sub)

class Adapter:
    def __init__(self,p,conditioned=False,P=None):
        self.p=p;self.base=Base(p);self.scale=self.base.scale;self.physical_cache={};self.distinct={}
        self.P=np.eye(len(p.x0));self.transform=None
        cold,init=sanitize(p)
        if cold is None:raise ValueError('infeasible destination cold')
        self.cold=cold
        # Destination-cold derivative is charged to every conditioned local attempt.
        if conditioned or P is not None:
            rr,JJ=self.base.evaluate(cold/self.scale)
            if conditioned:self.P,self.transform=matrix_transform(JJ.toarray(),p.n_offsets)
            self.distinct[hashlib.sha256(np.asarray(cold,dtype='<f8').tobytes()).hexdigest()]=dict(x=cold.tolist(),first='cold_transform')
        if P is not None:
            if conditioned and not np.array_equal(P,self.P):raise ArithmeticError('destination transform changed')
            self.P=np.asarray(P)
        self.inverse=np.linalg.inv(self.P);self.sparse=csr_matrix(self.P)
        self.gtol=1e-6/max(1.,float(np.linalg.norm(self.inverse.T,np.inf)))
        self.transform_sha256=hashlib.sha256(np.asarray(self.P,dtype='<f8').tobytes()).hexdigest()
        self.cache={}
    def coordinates(self,x):return self.inverse@(np.asarray(x)/self.scale)
    def physical(self,y):return (self.P@np.asarray(y))*self.scale
    def evaluate(self,y,first='objective'):
        self.p.check();key=np.asarray(y,dtype='<f8').tobytes()
        if key not in self.cache:
            x=self.physical(y);h=hashlib.sha256(np.asarray(x,dtype='<f8').tobytes()).hexdigest()
            if h not in self.distinct:
                if len(self.distinct)>=200:raise EvaluationLimit('200 distinct parameter states exhausted')
                self.distinct[h]=dict(x=x.tolist(),first=first)
            r,J=self.base.evaluate(x/self.scale);self.cache[key]=(r,J@self.sparse)
        return self.cache[key]
    def fun(self,y):r,_=self.evaluate(y);return float(r@r)
    def jac(self,y):r,J=self.evaluate(y,'gradient');return np.asarray(2*J.T@r).ravel()
    def hess(self,y):
        self.evaluate(y,'objective_hessian');q=self.P@np.asarray(y)
        return self.sparse.T@self.base.hess(q)@self.sparse
    def raw_depth(self,y,v=None):
        self.evaluate(y,'constraint_derivative');q=self.P@np.asarray(y)
        if v is not None:return self.sparse.T@self.base.raw_depth(q,v)@self.sparse
        z,J=self.base.raw_depth(q);return z,J@self.sparse
    def depth(self,y,v=None):
        self.evaluate(y,'constraint');q=self.P@np.asarray(y)
        if v is not None:return self.sparse.T@self.base.depth(q,v)@self.sparse
        z,J=self.base.depth(q);return z,J@self.sparse


def solve(problem,seed=None,source_lag=None,endpoint=None,conditioned=False,P=None):
    started=time.monotonic();x0,init=sanitize(problem,seed,source_lag,endpoint)
    if x0 is None:return dict(valid=False,converged=False,objective=None,error='no feasible deterministic initialization',nfev=0,initialization_transfer=init)
    a=Adapter(problem,conditioned,P);y0=a.coordinates(x0);n=problem.n_offsets
    bounds=Bounds(np.r_[np.full(n,-1.),np.full(len(y0)-n,-np.inf)],np.r_[np.full(n,1.),np.full(len(y0)-n,np.inf)],keep_feasible=True)
    constraint=NonlinearConstraint(lambda y:a.depth(y)[0],0.,np.inf,jac=lambda y:a.depth(y)[1],hess=lambda y,v:a.depth(y,v),keep_feasible=True)
    trace=[];last=y0.copy();result=None;error=None
    def callback(y,state):
        nonlocal last
        problem.check();last=y.copy()
        trace.append(dict(iteration=int(state.nit),objective=float(state.fun),optimality=float(state.optimality),barrier_parameter=float(state.barrier_parameter),trust_radius=float(state.tr_radius),x=a.physical(y).tolist(),conditioned_y=y.tolist(),min_depth=float(np.min(a.raw_depth(y)[0]))))
    policy={**POLICY,'gtol':a.gtol}
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        try:result=minimize(a.fun,y0,method='trust-constr',jac=a.jac,hess=a.hess,bounds=bounds,constraints=[constraint],callback=callback,options=policy)
        except EvaluationLimit as e:error=str(e)
    y=last if result is None else result.x;x=a.physical(y);q=x/a.scale
    r,J=a.base.evaluate(q);z,D=a.base.raw_depth(q);g,gp,_,flags=transform(z-MARGIN)
    vg=vd=vb=None;kkt=None
    if result is not None:
        vg=np.asarray(result.v[0]);vd=vg*gp;vb=a.inverse.T@result.v[1]
        kkt=np.asarray(2*J.T@r+D.T@vd+vb).ravel()
    offsets,coeff=problem.unpack(x);boundary=[c for c in problem.free if abs(offsets[c])>=24.99]
    original=problem.evaluate(x)[0];equal=bool(np.allclose(original,r,atol=1e-12,rtol=1e-12))
    opt=None if kkt is None else float(np.max(np.abs(kkt)))
    if flags['nonfinite'] or flags['derivative_underflow'] or not np.isfinite(x).all() or not np.isfinite(r).all():raise ArithmeticError('nonfinite/underflowed original state')
    valid=bool(result is not None and result.success and equal and opt<=1e-6 and np.min(z)>QUALIFICATION_DEPTH and not boundary)
    return dict(valid=valid,converged=bool(result is not None and result.success),status=None if result is None else int(result.status),message=error if result is None else str(result.message),objective=float(r@r),optimality=opt,KKT=None if kkt is None else kkt.tolist(),
        nfev=len(a.distinct),state_ledger=list(a.distinct.values()),initialization_transfer=init,initial_x=x0.tolist(),x=x.tolist(),conditioned_y=y.tolist(),solver_trace=trace,
        normalized_depths=z.tolist(),minimum_normalized_depth=float(np.min(z)),multipliers_transformed=None if vg is None else vg.tolist(),multipliers_depth=None if vd is None else vd.tolist(),bound_multipliers=None if vb is None else vb.tolist(),
        offsets=offsets,coefficients=coeff.tolist(),boundary_cameras=boundary,weight=problem.weight,window=problem.window,spacing=problem.spacing,group_ids=[g['group_id'] for g in problem.groups],knots=problem.spline.t.tolist(),center=problem.center.tolist(),diameter=problem.diameter,
        transform_sha256=a.transform_sha256,transform_bytes_le_hex=np.asarray(a.P,dtype='<f8').tobytes().hex(),gtol=a.gtol,original_objective_equal=equal,original_support=support(problem,x),factorization_warnings=[str(w.message) for w in caught],wall_seconds=time.monotonic()-started)
