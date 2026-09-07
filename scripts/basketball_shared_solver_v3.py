"""Frozen independent numerical revision; immutable v2 supplies only the model.

No production state enters this module. Linear-step regularization is not a
residual penalty. All coefficients, including inactive ones, remain parameters.
"""
import inspect
import time
import numpy as np
import scipy
from scipy.optimize import least_squares
from scipy.sparse.linalg import lsmr
from basketball_shared_spline_v2 import SplineProblem

POLICY = dict(method='trf', tr_solver='lsmr', x_scale='jac',
              tr_options=dict(regularize=True), ftol=1e-6, xtol=1e-6,
              gtol=1e-6, max_nfev=200)


def provenance():
    return dict(policy=POLICY, scipy=scipy.__version__,
                lsmr_defaults={k: v.default for k, v in inspect.signature(lsmr).parameters.items()
                               if v.default is not inspect.Parameter.empty},
                effective_lsmr_maxiter='min(m,n) for each augmented linear system',
                objective='sum of squared v2 residuals; no added ridge residual',
                reference='https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.least_squares.html')


def column_id(problem, i):
    if i < problem.n_offsets:
        return dict(column=i, camera_offset=problem.free[i])
    j=i-problem.n_offsets
    return dict(column=i, group_id=problem.groups[j//(problem.nc*3)]['group_id'],
                coefficient=(j//3)%problem.nc, coordinate='xyz'[j%3])


def rank_record(problem, x):
    r, J=problem.evaluate(x); A=J.toarray(); singular=np.linalg.svd(A,compute_uv=False)
    tolerance=max(A.shape)*np.finfo(float).eps*singular[0]
    zeros=np.flatnonzero(~np.any(A!=0,axis=0))
    return dict(residual=r.tolist(), objective=float(r@r), residual_norm=float(np.linalg.norm(r)),
                gradient_l2=float(np.linalg.norm(J.T@r)), gradient_inf=float(np.max(np.abs(J.T@r))),
                jacobian_shape=list(A.shape), singular_values=singular.tolist(),
                numerical_rank=int(np.sum(singular>tolerance)), rank_tolerance=float(tolerance),
                zero_columns=[column_id(problem,int(i)) for i in zeros])


def structural_inactivity(problem):
    """Basis-support proof over continuous permitted offsets, not sampled ranks.

    Free offsets range over [-25,25]. Fixed endpoint offsets remain fixed for
    this solve. A coefficient is potentially observable if any observation's
    corrected-time interval intersects the open support of its cubic basis.
    Geometric degeneracies are not certified by this support test.
    """
    inactive=[]; knots=problem.spline.t
    for gi,g in enumerate(problem.groups):
        for k in range(problem.nc):
            active=False
            for o in g['observations']:
                c=o['camera_id']; frames=np.asarray(o['frames'])
                low,high=(-25.,25.) if c in problem.free else (problem.offsets[c],)*2
                left=(frames-high)/25;right=(frames-low)/25
                active |= bool(np.any((right>knots[k]) & (left<knots[k+4])))
            if problem.weight and np.any(problem.accel[:,k]): active=True
            if not active:
                inactive.extend(column_id(problem,problem.n_offsets+gi*problem.nc*3+3*k+j) for j in range(3))
    return inactive


def solve(problem, seed=None, diagnostic_policy=None, diagnostics=False):
    started=time.monotonic(); x0=problem.x0.copy() if seed is None else np.asarray(seed,float).copy()
    if x0.shape!=problem.x0.shape: raise ValueError('seed parameterization mismatch')
    policy={**POLICY,'tr_options':dict(POLICY['tr_options'])}
    if diagnostic_policy=='unit': policy['x_scale']=1.
    elif diagnostic_policy=='dense': policy.update(tr_solver='exact',tr_options={})
    elif diagnostic_policy not in (None,'scaled'): raise ValueError('unknown diagnostic policy')
    initial=rank_record(problem,x0) if diagnostics else None
    n=problem.n_offsets
    bounds=(np.r_[np.full(n,-25.),np.full(len(x0)-n,-np.inf)],
            np.r_[np.full(n,25.),np.full(len(x0)-n,np.inf)])
    def jac(x):
        J=problem.evaluate(x)[1]
        return J.toarray() if policy['tr_solver']=='exact' else J
    result=least_squares(lambda x:problem.evaluate(x)[0],x0,jac=jac,bounds=bounds,**policy)
    residual,J=problem.evaluate(result.x); offsets,coeff=problem.unpack(result.x)
    boundary=[c for c in problem.free if abs(offsets[c])>=24.99]
    positive=bool(np.all(problem.last_depths>0))
    row=dict(valid=bool(result.success and positive and not boundary),converged=bool(result.success),
             status=int(result.status),message=result.message,objective=float(residual@residual),
             nfev=int(result.nfev),njev=int(result.njev),optimality=float(result.optimality),
             gradient_l2=float(np.linalg.norm(J.T@residual)),gradient_inf=float(np.max(np.abs(J.T@residual))),
             positive_depth=positive,boundary_cameras=boundary,offsets=offsets,
             x=result.x.tolist(),initial_x=x0.tolist(),coefficients=coeff.tolist(),
             group_ids=[g['group_id'] for g in problem.groups],knots=problem.spline.t.tolist(),
             center=problem.center.tolist(),diameter=problem.diameter,window=problem.window,
             spacing=problem.spacing,weight=problem.weight,initialization=problem.initialization,
             evaluation_trace=problem.evaluation_trace,wall_seconds=time.monotonic()-started,
             jacobian_shape=list(J.shape),jacobian_bytes=int(J.data.nbytes+J.indices.nbytes+J.indptr.nbytes))
    if diagnostics:
        row.update(initial=initial,final=rank_record(problem,result.x),
                   structurally_inactive_columns=structural_inactivity(problem),solver=policy)
    return row


def objective_agreement(a,b):
    return abs(a-b)<=1e-6+1e-4*max(abs(a),abs(b))
