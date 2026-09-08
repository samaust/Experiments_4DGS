"""Exact-objective-Hessian v6 independent evaluator; immutable v2 objective and state."""
import inspect
import time
import warnings
import numpy as np
import scipy
from scipy.optimize import minimize, Bounds, NonlinearConstraint
from scipy.optimize._trustregion_constr.minimize_trustregion_constr import _minimize_trustregion_constr
from scipy.sparse import coo_matrix, diags

MARGIN = 1e-8
QUALIFICATION_DEPTH = 1e-7
MAX_EVALUATIONS = 200
POLICY = dict(gtol=1e-6, xtol=1e-6, barrier_tol=1e-6, maxiter=200,
              sparse_jacobian=True, factorization_method='AugmentedSystem',
              initial_constr_penalty=1., initial_tr_radius=1.,
              initial_barrier_parameter=.1, initial_barrier_tolerance=.1,
              verbose=0, disp=False, finite_diff_rel_step=None, workers=None)


def provenance():
    return dict(method='trust-constr', policy=POLICY, scipy=scipy.__version__,
        installed_defaults={k:v.default for k,v in inspect.signature(_minimize_trustregion_constr).parameters.items()
                            if v.default is not inspect.Parameter.empty},
        scaling=dict(offset_frames=25., coefficients='existing rig-diameter units'),
        depth_margin=MARGIN, qualification_depth=QUALIFICATION_DEPTH, keep_feasible=True,
        max_objective_evaluations=MAX_EVALUATIONS, objective='sum(original_v2_residual**2)',
        transfer='source sampled weak blocks reset to destination cold; blends 2**-k k=0..20 then 0',
        constraint_hessian='full sparse chain rule including coefficient outer products',
        transformation='s/hypot(1,s)', transformation_scale=1., cache_version='v6', objective_hessian='exact direct soft-L1 loss, perspective, distortion and spline chain rule', objective_hessian_version='v6-exact-1')


class EvaluationLimit(RuntimeError):
    pass


class ConstrainedProblem:
    """One residual/Jacobian cache shared by every objective derivative request."""
    def __init__(self, problem):
        self.problem=problem
        self.scale=np.r_[np.full(problem.n_offsets,25.),np.ones(len(problem.x0)-problem.n_offsets)]
        self.D=diags(self.scale)
        self.cache={};self.evaluations=0;self.constraint_evaluations=0
        self.derivative_seconds=0.;self.residual_seconds=0.
        self.hessian_calls=0;self.hessian_assemblies=0;self.hessian_seconds=0.;self.hessian_cache={}

    def evaluate(self,q):
        self.problem.check();q=np.asarray(q,float);key=q.tobytes()
        if key not in self.cache:
            if self.evaluations>=MAX_EVALUATIONS:raise EvaluationLimit('200 distinct objective evaluations exhausted')
            self.evaluations+=1;start=time.monotonic()
            r,J=self.problem.evaluate(q*self.scale)
            self.cache[key]=(r,J@self.D)
            self.residual_seconds+=time.monotonic()-start
        return self.cache[key]

    def fun(self,q):
        r,_=self.evaluate(q);return float(r@r)

    def jac(self,q):
        started=time.monotonic();r,J=self.evaluate(q);result=np.asarray(2*J.T@r).ravel()
        self.derivative_seconds+=time.monotonic()-started;self.problem.check();return result

    def hess(self,q):
        self.problem.check();self.hessian_calls+=1
        # Any derivative can be the first request for this distinct objective state.
        self.evaluate(q);key=np.asarray(q,float).tobytes()
        if key not in self.hessian_cache:
            started=time.monotonic()
            self.hessian_cache[key]=exact_objective_hessian(self.problem,np.asarray(q)*self.scale)
            elapsed=time.monotonic()-started
            self.hessian_seconds+=elapsed;self.derivative_seconds+=elapsed;self.hessian_assemblies+=1
        self.problem.check();return self.hessian_cache[key]

    def raw_depth(self,q,v=None):
        """Normalized z, dz/dq and Hessian of v.T z in dimensionless coordinates."""
        self.problem.check();self.constraint_evaluations+=1;start=time.monotonic()
        p=self.problem;offsets,coeff=p.unpack(np.asarray(q)*self.scale)
        z=[];rows=[];cols=[];values=[];hr=[];hc=[];hv=[];base=0
        for gi,g in enumerate(p.groups):
            cb=p.n_offsets+gi*p.nc*3
            for o in g['observations']:
                c=o['camera_id'];cam=p.cameras[c];R=np.asarray(cam['R'])[2]
                t=(np.asarray(o['frames'])-offsets[c])/25;B=p.spline(t)
                z.extend(B@coeff[gi]@R+(R@p.center+cam['t'][2])/p.diameter)
                ii,jj=np.nonzero(B)
                for k in range(3):
                    rows.extend(base+ii);cols.extend(cb+3*jj+k);values.extend(B[ii,jj]*R[k])
                if c in p.index:
                    j=p.index[c];Bp=p.spline.derivative()(t)
                    rows.extend(base+np.arange(len(t)));cols.extend([j]*len(t));values.extend(-Bp@coeff[gi]@R)
                    if v is not None:
                        w=np.asarray(v)[base:base+len(t)]
                        hr.append(j);hc.append(j);hv.append(float(w@(p.spline.derivative(2)(t)@coeff[gi]@R)))
                        mixed=-(w@Bp)[:,None]*R
                        for k,val in enumerate(mixed.ravel()):
                            if val:hr.extend([j,cb+k]);hc.extend([cb+k,j]);hv.extend([val,val])
                base+=len(t)
        shape=(len(q),len(q))
        self.derivative_seconds+=time.monotonic()-start
        if v is not None:return coo_matrix((hv,(hr,hc)),shape=shape).tocsr()
        return np.asarray(z),coo_matrix((values,(rows,cols)),shape=(base,len(q))).tocsr()


    def depth(self,q,v=None):
        start=time.monotonic()
        z,J=self.raw_depth(q)
        g,first,second,flags=transform(z-MARGIN)
        self.problem.check()
        if flags['nonfinite'] or flags['derivative_underflow']:
            raise FloatingPointError('nonfinite or underflowed bounded-depth derivatives')
        if v is None:result=(g,diags(first)@J)
        else:result=self.raw_depth(q,np.asarray(v)*first)+J.T@diags(np.asarray(v)*second)@J
        self.derivative_seconds+=time.monotonic()-start
        return result


def transform(s):
    s=np.asarray(s,float)
    with np.errstate(over='ignore',under='ignore',invalid='ignore'):
        h=np.hypot(1.,s);inv=1./h;g=s/h
        first=inv*inv*inv
        second=-3.*g*inv*inv*inv*inv
    return g,first,second,dict(saturation=int(np.count_nonzero(np.abs(g)==1)),
        derivative_underflow=int(np.count_nonzero((first==0)|((s!=0)&(second==0)))),
        nonfinite=bool(not all(np.isfinite(v).all() for v in [g,first,second])))


def support(problem,x):
    offsets,_=problem.unpack(np.asarray(x));records=[]
    A=problem.accel;an=np.linalg.norm(A,axis=0);at=max(A.shape)*np.finfo(float).eps*max(an)
    for gi,g in enumerate(problem.groups):
        B=np.vstack([problem.spline((np.asarray(o['frames'])-offsets[o['camera_id']])/25) for o in g['observations']])
        bn=np.linalg.norm(B,axis=0);bt=max(B.shape)*np.finfo(float).eps*max(bn)
        records.append(dict(group_id=g['group_id'],group_index=gi,data_norms=bn.tolist(),data_threshold=float(bt),
            acceleration_norms=an.tolist(),acceleration_threshold=float(at),
            exactly_unsupported=np.flatnonzero((bn==0)&((an==0)|(problem.weight==0))).tolist(),
            unsupported=np.flatnonzero((bn<bt)&((an<at)|(problem.weight==0))).tolist()))
    return records


def sanitize(problem,seed=None,source_lag=None,endpoint=None):
    p=problem;cold=p.x0.copy();original=cold.copy() if seed is None else np.asarray(seed,float).copy()
    if original.shape!=cold.shape:raise ValueError('seed parameterization mismatch')
    adapter=ConstrainedProblem(p);checks=[];replaced=[];source_support=[]
    def valid(x):
        p.check();finite=bool(np.isfinite(x).all());bounds=bool(np.all(np.abs(x[:p.n_offsets])<=25))
        depths=adapter.raw_depth(x/adapter.scale)[0] if finite and bounds else np.array([np.nan])
        good=bool(finite and bounds and np.isfinite(depths).all() and np.min(depths)>2*MARGIN)
        checks.append(dict(finite=finite,offset_bounds=bounds,min_depth=float(np.min(depths)) if np.isfinite(depths).all() else None,valid=good))
        return good
    sanitized=original.copy()
    if seed is not None:
        if endpoint is None or source_lag is None:raise ValueError('source lag and fixed endpoint required')
        destination=p.offsets[endpoint]
        try:
            p.offsets[endpoint]=source_lag
            source_support=support(p,original)
        finally:p.offsets[endpoint]=destination
        for row in source_support:
            for block in row['unsupported']:
                begin=p.n_offsets+row['group_index']*p.nc*3+block*3
                sanitized[begin:begin+3]=cold[begin:begin+3]
                replaced.append(dict(group_id=row['group_id'],block=block))
    original_valid=valid(original);cold_valid=valid(cold)
    selected=None;fraction=None
    for fraction in [2.**-k for k in range(21)]+[0.]:
        # Avoid 0 * infinity and preserve the exact endpoints.
        trial=cold.copy() if fraction==0 else sanitized.copy() if fraction==1 else cold+fraction*(sanitized-cold)
        if valid(trial):selected=trial;break
    return selected,dict(source_lag=source_lag,destination_lag=None if endpoint is None else p.offsets[endpoint],
        original_x=original.tolist(),sanitized_x=sanitized.tolist(),cold_x=cold.tolist(),
        selected_x=None if selected is None else selected.tolist(),replaced_blocks=replaced,source_support=source_support,
        destination_support=support(p,cold),blend_fraction=fraction if selected is not None else None,
        original_valid=original_valid,cold_valid=cold_valid,checks=checks,initialization_constraint_evaluations=adapter.constraint_evaluations)


def solve(problem,seed=None,source_lag=None,endpoint=None):
    started=time.monotonic();x0,initialization=sanitize(problem,seed,source_lag,endpoint)
    if x0 is None:
        return dict(valid=False,converged=False,objective=None,error='no feasible deterministic initialization',initialization_transfer=initialization,nfev=0)
    initialization_seconds=time.monotonic()-started
    a=ConstrainedProblem(problem);q0=x0/a.scale;n=problem.n_offsets
    bounds=Bounds(np.r_[np.full(n,-1.),np.full(len(q0)-n,-np.inf)],np.r_[np.full(n,1.),np.full(len(q0)-n,np.inf)],keep_feasible=True)
    constraint=NonlinearConstraint(lambda q:a.depth(q)[0],0.,np.inf,jac=lambda q:a.depth(q)[1],hess=lambda q,v:a.depth(q,v),keep_feasible=True)
    trace=[];last=q0.copy();result=None;error=None
    def callback(q,state):
        nonlocal last
        problem.check();last=q.copy()
        trace.append(dict(iteration=int(state.nit),objective=float(state.fun),optimality=float(state.optimality),
            constraint_violation=float(state.constr_violation),barrier_parameter=float(state.barrier_parameter),
            barrier_tolerance=float(state.barrier_tolerance),trust_radius=float(state.tr_radius),
            min_depth=float(np.min(a.raw_depth(q)[0])),x=(q*a.scale).tolist()))
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter('always')
        try:result=minimize(a.fun,q0,method='trust-constr',jac=a.jac,hess=a.hess,bounds=bounds,constraints=[constraint],callback=callback,options=POLICY)
        except (EvaluationLimit,FloatingPointError,ValueError) as exc:error=str(exc)
    q=last if result is None else result.x;x=q*a.scale
    # Independent returned-state residual and KKT/depth checks; repeated state does not consume a new distinct evaluation.
    r,J=a.evaluate(q);depth,Dz=a.raw_depth(q);offsets,coeff=problem.unpack(x)
    # Re-evaluate the same physical state independently without adding a distinct q.
    problem.cache=None;rr,JJ=problem.evaluate(x)
    objective_equal=bool(np.allclose(rr,r,rtol=1e-12,atol=1e-12))
    g,gp,gpp,flags=transform(depth-MARGIN)
    vg=None;vd=None;vb=None;representation_error=None
    boundary=[c for c in problem.free if abs(offsets[c])>=24.99]
    optimality=None
    if result is not None:
        vg=np.asarray(result.v[0]);vd=vg*gp;vb=np.asarray(result.v[1])
        gradient=2*(JJ@a.D).T@rr+Dz.T@vd+vb
        transformed=2*J.T@r+(diags(gp)@Dz).T@vg+vb
        representation_error=float(np.max(np.abs(gradient-transformed)))
        optimality=float(np.linalg.norm(gradient,np.inf))
    finite=bool(np.isfinite(x).all() and np.isfinite(r).all() and np.isfinite(depth).all())
    violation=float(max(0.,MARGIN-min(depth),np.max(np.abs(q[:n])-1) if n else 0.))
    success=bool(result is not None and result.success)
    valid=bool(objective_equal and not flags['nonfinite'] and not flags['derivative_underflow'] and representation_error is not None and representation_error<=1e-10 and np.isfinite(vd).all() and finite and success and optimality<=1e-6 and violation==0 and min(depth)>QUALIFICATION_DEPTH and not boundary)
    return dict(valid=valid,converged=success,status=None if result is None else int(result.status),message=error if result is None else str(result.message),
        objective=float(r@r),original_objective_equal=objective_equal,transformation_diagnostics=flags,
        transformed_slacks=g.tolist(),original_slacks=(depth-MARGIN).tolist(),
        multipliers_transformed=None if vg is None else vg.tolist(),
        multipliers_depth=None if vd is None else vd.tolist(),bound_multipliers=None if vb is None else vb.tolist(),
        stationarity_representation_error=representation_error,
        complementarity_original=None if vd is None else (vd*(depth-MARGIN)).tolist(),
        complementarity_transformed=None if vg is None else (vg*g).tolist(),
        dual_sign_violation=None if vd is None else float(max(0.,max(vd))),
        nfev=a.evaluations,optimality=optimality,constraint_violation=violation,
        positive_depth=bool(min(depth)>=MARGIN),minimum_normalized_depth=float(min(depth)),normalized_depths=depth.tolist(),
        constraint_boundary_dependent=bool(min(depth)<=QUALIFICATION_DEPTH),boundary_cameras=boundary,
        offsets=offsets,x=x.tolist(),initial_x=x0.tolist(),coefficients=coeff.tolist(),
        group_ids=[g['group_id'] for g in problem.groups],knots=problem.spline.t.tolist(),center=problem.center.tolist(),diameter=problem.diameter,
        window=problem.window,spacing=problem.spacing,weight=problem.weight,initialization_transfer=initialization,
        evaluation_trace=problem.evaluation_trace,solver_trace=trace,constraint_evaluations=a.constraint_evaluations,
        factorization_warnings=[str(w.message) for w in captured],derivative_seconds=a.derivative_seconds,
        objective_hessian_calls=a.hessian_calls,objective_hessian_assemblies=a.hessian_assemblies,objective_hessian_seconds=a.hessian_seconds,
        residual_seconds=a.residual_seconds,initialization_seconds=initialization_seconds,wall_seconds=time.monotonic()-started)


def projection_second(xyz, camera, center, diameter):
    """Image value, first and second derivatives wrt rig-normalized xyz."""
    R=np.asarray(camera['R']);K=np.asarray(camera['K'])[:2,:2];k=camera['parameters_colmap'][3]
    c=(xyz*diameter+center)@R.T+camera['t'];z=c[:,2];u=c[:,:2]/z[:,None]
    n=len(z);eye=np.eye(2)
    predicted=(u*(1+k*np.sum(u*u,axis=1))[:,None])@K.T+np.asarray(camera['K'])[:2,2]
    P=np.zeros((n,2,3));P[:,0,0]=1/z;P[:,1,1]=1/z;P[:,:,2]=-u/z[:,None]
    HP=np.zeros((n,2,3,3))
    for a in range(2):
        HP[:,a,a,2]=-1/z**2;HP[:,a,2,a]=-1/z**2;HP[:,a,2,2]=2*u[:,a]/z**2
    T=(1+k*np.sum(u*u,axis=1))[:,None,None]*eye+2*k*u[:,:,None]*u[:,None,:]
    HT=np.zeros((n,2,2,2))
    for a in range(2):
        for i in range(2):
            for j in range(2):
                HT[:,a,i,j]=2*k*((a==i)*u[:,j]+(a==j)*u[:,i]+(i==j)*u[:,a])
    JP=np.einsum('ab,nbc,ncd->nad',K,T,P)
    Hcam=np.einsum('ab,nbij,nik,njl->nakl',K,HT,P,P)+np.einsum('ab,nbi,nikl->nakl',K,T,HP)
    J=np.einsum('nai,ij->naj',JP,R)*diameter
    H=np.einsum('ik,naij,jl->nakl',R,Hcam,R)*diameter**2
    return predicted,J,H


def exact_objective_hessian(p,x):
    """Objective curvature only, in q coordinates. No constraints or barriers.

    phi=2(sqrt(1+e.e)-1)/N, b=2e/(N sqrt(1+e.e)),
    W=(2/N)(I/sqrt(1+e.e)-ee.T/(1+e.e)**(3/2)).
    Hxyz=P.T W P + sum_a b_a H_projection_a.
    q-offsets shift spline time by -q, so their trajectory first/second
    derivatives are -B'c and B''c, and mixed derivatives are -B'.
    """
    p.check();offsets,coeff=p.unpack(x);H=np.zeros((len(x),len(x)))
    for gi,group in enumerate(p.groups):
        cb=p.n_offsets+gi*p.nc*3;sl=slice(cb,cb+3*p.nc)
        for obs in group['observations']:
            p.check();c=obs['camera_id'];t=(np.asarray(obs['frames'])-offsets[c])/25
            B=p.spline(t);xyz=B@coeff[gi]
            pred,P,HP=projection_second(xyz,p.cameras[c],p.center,p.diameter)
            e=pred-obs['xy'];s=np.sqrt(1+np.sum(e*e,axis=1));b=2*e/(p.n*s[:,None])
            W=2/p.n*(np.eye(2)[None,:,:]/s[:,None,None]-e[:,:,None]*e[:,None,:]/s[:,None,None]**3)
            spatial=np.einsum('na,nai->ni',b,P)
            curvature=np.einsum('nai,nab,nbj->nij',P,W,P)+np.einsum('na,naij->nij',b,HP)
            H[sl,sl]+=np.einsum('nk,nl,nij->kilj',B,B,curvature).reshape(3*p.nc,3*p.nc)
            if c in p.index:
                j=p.index[c];Bp=p.spline.derivative()(t);v=-Bp@coeff[gi];acc=p.spline.derivative(2)(t)@coeff[gi]
                mixed=(np.einsum('ni,nij,nk->kj',v,curvature,B)-Bp.T@spatial).ravel()
                H[j,sl]+=mixed;H[sl,j]+=mixed
                H[j,j]+=np.einsum('ni,nij,nj->',v,curvature,v)+np.sum(spatial*acc)
        if p.weight:
            H[sl,sl]+=np.kron(2*p.weight/p.nacc*(p.accel.T@p.accel),np.eye(3))
        p.check()
    if not np.isfinite(H).all():raise FloatingPointError('nonfinite exact objective Hessian')
    return coo_matrix(H).tocsr()
