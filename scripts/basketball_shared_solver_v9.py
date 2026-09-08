"""Canonical v9 full-coordinate exact constrained solver; no hidden evaluation budget."""
import time
import warnings
import numpy as np
from scipy.optimize import minimize,Bounds,NonlinearConstraint
from basketball_shared_accounting_v9 import CanonicalAdapter,bytes_of,reconcile
from basketball_shared_initialization_v9 import sanitize,sampled_support
from basketball_shared_stopping_v9 import options,qualified
from basketball_shared_solver_v6 import transform,MARGIN,EvaluationLimit


def solve(problem,seed=None,source_lag=None,endpoint=None,conditioned=False,repair=False,disable_xtol=False,namespace='v9-test',provenance=None):
    started=time.monotonic();a=CanonicalAdapter(problem,namespace,provenance);trace=[];result=None;error=None;last=None;last_v=None
    init={};cold=None;x0=None
    try:
        x0,cold,init=sanitize(a,seed,source_lag,endpoint,repair)
        if x0 is None:return dict(valid=False,converged=False,objective=None,error='no feasible deterministic initialization',nfev=len(a.ledger.states),initialization_transfer=init,
            accounting=a.export(),accounting_verification=reconcile(a.export()),wall_seconds=time.monotonic()-started,iterations=0)
        a.set_transform(cold,conditioned);y0=a.coordinates(x0);n=problem.n_offsets
        initial=a.state_y(y0,'solver_initialization');last=initial
        lower=np.r_[np.full(n,-1.)-a.origin[:n],np.full(len(y0)-n,-np.inf)]
        upper=np.r_[np.full(n,1.)-a.origin[:n],np.full(len(y0)-n,np.inf)]
        bounds=Bounds(lower,upper,keep_feasible=True)
        constraint=NonlinearConstraint(lambda y:a.depth(y)[0],0.,np.inf,jac=lambda y:a.depth(y)[1],hess=lambda y,v:a.depth(y,v),keep_feasible=True)
        def callback(y,state):
            nonlocal last,last_v
            problem.check();a.ledger.iteration(int(state.nit));s=a.state_y(y,'callback');last=s;last_v=[np.asarray(v).copy() for v in state.v]
            trace.append(dict(iteration=int(state.nit),objective=float(state.fun),optimality=float(state.optimality),barrier_parameter=float(state.barrier_parameter),
                trust_radius=float(state.tr_radius),x=s.x.tolist(),q=s.q.tolist(),y=np.asarray(y).tolist(),state=s.identity,
                multipliers=[v.tolist() for v in last_v],min_depth=float(np.min(a.raw(s)[0]))))
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            try:result=minimize(a.fun,y0,method='trust-constr',jac=a.jac,hess=a.hess,bounds=bounds,constraints=[constraint],callback=callback,options=options(a,disable_xtol))
            except (EvaluationLimit,FloatingPointError,ValueError) as e:error=type(e).__name__+': '+str(e)
        warning_messages=[str(w.message) for w in caught]
        if result is not None:
            last=a.state_y(result.x,'returned_state');last_v=[np.asarray(v) for v in result.v];a.ledger.iteration(int(result.nit))
        else:
            # Retain the exact callback-owned state, never map physical coordinates back to a new q.
            a.ledger.request(last.q,'interrupted_returned_state')
        r,J=a.residual(last);z,D=a.raw(last);_,gp,_,flags=transform(z-MARGIN)
        vg=vd=vb=KKT=None;G=np.asarray(2*J.T@r).ravel();Cd=Cb=None
        if last_v is not None:
            vg=last_v[0];vd=vg*gp;vb=a.inverse.T@last_v[1]
            Cd=np.asarray(D.T@vd).ravel();Cb=vb;KKT=G+Cd+Cb
        offsets,coeff=problem.unpack(last.x);boundary=[c for c in problem.free if abs(offsets[c])>=24.99]
        finite=not flags['nonfinite'] and not flags['derivative_underflow'] and np.isfinite(last.x).all() and np.isfinite(r).all()
        valid=qualified(result is not None and result.success,KKT,z,boundary,finite)
        # Read-only support analysis at already-owned original state is included in the same ledger.
        # Avoid a q->x->q round trip here.
        final_support=None
        final_support=sampled_support(a,last.x,'returned_support',state=last)
        accounting=a.export();verified=reconcile(accounting)
        return dict(valid=valid,converged=bool(result is not None and result.success),status=None if result is None else int(result.status),message=error if result is None else str(result.message),
            objective=float(r@r),optimality=None if KKT is None else float(np.linalg.norm(KKT,np.inf)),KKT=None if KKT is None else KKT.tolist(),G=G.tolist(),C_depth=None if Cd is None else Cd.tolist(),C_bounds=None if Cb is None else Cb.tolist(),
            multipliers_transformed=None if vg is None else vg.tolist(),multipliers_depth=None if vd is None else vd.tolist(),bound_multipliers=None if vb is None else vb.tolist(),
            complementarity_original=None if vd is None else (vd*(z-MARGIN)).tolist(),normalized_depths=z.tolist(),minimum_normalized_depth=float(np.min(z)),
            initial_x=x0.tolist(),x=last.x.tolist(),canonical_q=last.q.tolist(),returned_state=last.identity,offsets=offsets,coefficients=coeff.tolist(),boundary_cameras=boundary,
            initialization_transfer=init,solver_trace=trace,iterations=a.ledger.iterations,nfev=len(a.ledger.states),accounting=accounting,accounting_verification=verified,
            transform=a.transform,gtol=a.gtol,original_support=final_support,factorization_warnings=warning_messages,wall_seconds=time.monotonic()-started,
            group_ids=[g['group_id'] for g in problem.groups],weight=problem.weight,window=problem.window,spacing=problem.spacing,knots=problem.spline.t.tolist(),center=problem.center.tolist(),diameter=problem.diameter,
            conditional_qualified=valid if problem.n_offsets==0 else False,joint_qualified=valid if problem.n_offsets else False)
    except EvaluationLimit as e:
        return dict(valid=False,converged=False,objective=None,error=str(e),initialization_transfer=init,accounting=a.export(),accounting_verification=reconcile(a.export()),nfev=len(a.ledger.states),iterations=a.ledger.iterations,wall_seconds=time.monotonic()-started)
