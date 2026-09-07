"""Actual distortion-aware shared cubic-spline fitting and independent edge gauges.

No independent evaluator entry point accepts production offsets or coefficients.
Offsets use corrected seconds = (source frame - offset) /25.
"""
import time
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
import numpy as np
from scipy.interpolate import BSpline
from scipy.optimize import least_squares,minimize_scalar
from scipy.sparse import coo_matrix,csr_matrix,kron,eye
from basketball_timing import undistort_points,essential,epipolar_pixels


class InsufficientSupport(ValueError): pass


def rig_normalization(cameras):
    centers=np.array([-np.asarray(c['R']).T@np.asarray(c['t']) for c in cameras.values()])
    diameter=float(np.max(np.linalg.norm(centers[:,None]-centers[None,:],axis=2)))
    if diameter<=0: raise ValueError('zero rig diameter')
    return centers.mean(axis=0),diameter


def basis(window,spacing):
    lo,hi=(window[0]-25)/25,(window[1]+25)/25
    inner=np.arange(lo+spacing/25,hi-1e-12,spacing/25)
    knots=np.r_[[lo]*4,inner,[hi]*4]
    spline=BSpline(knots,np.eye(len(knots)-4),3,extrapolate=False)
    return spline,np.arange(window[0]-25,window[1]+26,dtype=float)/25


def project_jacobian(x,camera,center,diameter):
    R=np.asarray(camera['R']); K=np.asarray(camera['K']); k=camera['parameters_colmap'][3]
    cam=(x*diameter+center)@R.T+camera['t']; z=cam[:,2]
    # No near-plane clamping can manufacture a successful reprojection.
    if np.any(np.abs(z)<1e-9): raise FloatingPointError('projection at camera plane')
    uv=cam[:,:2]/z[:,None]; r2=np.sum(uv*uv,axis=1)
    predicted=(uv*(1+k*r2[:,None]))@K[:2,:2].T+K[:2,2]
    radial=(1+k*r2)[:,None,None]*np.eye(2)+2*k*uv[:,:,None]*uv[:,None,:]
    perspective=np.zeros((len(x),2,3));perspective[:,0,0]=1/z;perspective[:,1,1]=1/z
    perspective[:,:,2]=-uv/z[:,None]
    jac=np.einsum('ab,nbc,ncd,de->nae',K[:2,:2],radial,perspective,R)*diameter
    return predicted,jac,z


def robust_residual_jacobian(errors,samples):
    """Pointwise one-pixel soft-L1, then sample normalization (not before)."""
    s=np.sum(errors**2,axis=1); q=np.sqrt(1+s)
    w=np.sqrt(2/(q+1))/np.sqrt(samples)
    derivative=-w/(4*q*(q+1))
    jac=w[:,None,None]*np.eye(2)+2*derivative[:,None,None]*errors[:,:,None]*errors[:,None,:]
    return errors*w[:,None],jac


def clip_groups(groups,window,allowed=None):
    result=[]
    for g in groups:
        observations=[]
        for o in g['observations']:
            if allowed is not None and o['camera_id'] not in allowed: continue
            frames=np.asarray(o['frames']); use=(frames>=window[0])&(frames<=window[1])
            if np.any(use): observations.append(dict(camera_id=o['camera_id'],frames=frames[use],xy=np.asarray(o['xy'])[use]))
        if observations: result.append(dict(group_id=g['group_id'],observations=observations))
    return result


def initialize_coefficients(group,cameras,offsets,spline,quadrature,center,diameter,window):
    observations=[]
    for o in group['observations']:
        c=o['camera_id']; f=np.asarray(o['frames'],float);xy=np.asarray(o['xy'])
        if np.any(f<window[0]) or np.any(f>window[1]): raise ValueError('initialization crosses role/window')
        observations.append((c,f,undistort_points(xy,cameras[c])))
    points=[];times=[]
    for frame in range(window[0],window[1]+1):
        rows=[];views=[]
        for c,f,uv in observations:
            query=frame+offsets[c]
            if not f[0]<=query<=f[-1]: continue
            ray=np.array([np.interp(query,f,uv[:,k]) for k in range(2)])
            P=np.column_stack((cameras[c]['R'],cameras[c]['t']))
            rows.extend([ray[0]*P[2]-P[0],ray[1]*P[2]-P[1]]);views.append(c)
        if len(views)<2: continue
        _,_,V=np.linalg.svd(rows,full_matrices=False);hom=V[-1]
        if abs(hom[3])<1e-10: continue
        xyz=hom[:3]/hom[3]
        if any((np.asarray(cameras[c]['R'])@xyz+cameras[c]['t'])[2]<=0 for c in views): continue
        points.append((xyz-center)/diameter);times.append(frame/25)
    if len(points)<4: raise InsufficientSupport('fewer than four within-window training triangulations')
    B=spline(times); A=spline.derivative(2)(quadrature)
    coefficients=np.linalg.lstsq(np.vstack([B,1e-3*A]),np.vstack([points,np.zeros((len(A),3))]),rcond=None)[0]
    return coefficients,dict(triangulations=len(points),corrected_seconds=times,source_interpolation='inside current role/window only; training observations only')


class SplineProblem:
    def __init__(self,groups,cameras,offsets,window,spacing,weight,fixed,check=lambda:None):
        self.groups=groups;self.cameras=cameras;self.offsets=dict(offsets);self.window=list(window)
        self.spacing=spacing;self.weight=weight;self.check=check
        self.center,self.diameter=rig_normalization(cameras);self.spline,self.quadrature=basis(window,spacing)
        self.nc=self.spline.c.shape[0]; self.free=sorted(set(o['camera_id'] for g in groups for o in g['observations'])-set(fixed))
        self.index={c:i for i,c in enumerate(self.free)};self.n_offsets=len(self.free)
        self.n=sum(len(o['frames']) for g in groups for o in g['observations'])
        if not self.n: raise InsufficientSupport('no observations in role/window')
        coefficients=[];self.initialization=[]
        for g in groups:
            check();co,trace=initialize_coefficients(g,cameras,offsets,self.spline,self.quadrature,self.center,self.diameter,window)
            coefficients.append(co);self.initialization.append(dict(group_id=g['group_id'],**trace))
        self.x0=np.r_[[offsets[c] for c in self.free],np.asarray(coefficients).ravel()]
        self.accel=self.spline.derivative(2)(self.quadrature)
        self.nacc=len(groups)*len(self.quadrature)
        self.cache=None;self.evaluation_trace=[]

    def unpack(self,x):
        offsets=dict(self.offsets);offsets.update({c:float(x[i]) for c,i in self.index.items()})
        return offsets,x[self.n_offsets:].reshape(len(self.groups),self.nc,3)

    def evaluate(self,x):
        self.check()
        if self.cache is not None and np.array_equal(x,self.cache[0]): return self.cache[1:]
        offsets,coefficients=self.unpack(x);residuals=[];rows=[];cols=[];values=[];rowbase=0;depths=[];raw=[]
        for gi,g in enumerate(self.groups):
            coeffbase=self.n_offsets+gi*self.nc*3
            for o in g['observations']:
                c=o['camera_id'];times=(np.asarray(o['frames'])-offsets[c])/25
                B=self.spline(times);xyz=B@coefficients[gi]
                predicted,P,z=project_jacobian(xyz,self.cameras[c],self.center,self.diameter)
                errors=predicted-o['xy']; residual,Jr=robust_residual_jacobian(errors,self.n)
                J=np.einsum('nab,nbc->nac',Jr,P);raw.extend(np.linalg.norm(errors,axis=1));depths.extend(z)
                residuals.append(residual.ravel()); ii,jj=np.nonzero(B)
                for u in range(2):
                    for v in range(3):
                        rows.extend(rowbase+2*ii+u);cols.extend(coeffbase+3*jj+v);values.extend(J[ii,u,v]*B[ii,jj])
                if c in self.index:
                    velocity=self.spline.derivative()(times)@coefficients[gi]
                    derivative=-np.einsum('nij,nj->ni',J,velocity)/25
                    rows.extend(rowbase+np.arange(len(times)*2));cols.extend([self.index[c]]*(len(times)*2));values.extend(derivative.ravel())
                rowbase+=len(times)*2
            if self.weight:
                factor=np.sqrt(self.weight/self.nacc);acc=self.accel@coefficients[gi]*factor
                residuals.append(acc.ravel());ii,jj=np.nonzero(self.accel)
                for v in range(3):
                    rows.extend(rowbase+3*ii+v);cols.extend(coeffbase+3*jj+v);values.extend(self.accel[ii,jj]*factor)
                rowbase+=acc.size
        residual=np.concatenate(residuals)
        jac=coo_matrix((values,(rows,cols)),shape=(len(residual),len(x))).tocsr()
        self.last_raw=np.asarray(raw);self.last_depths=np.asarray(depths)
        self.evaluation_trace.append(dict(evaluation=len(self.evaluation_trace)+1,objective=float(residual@residual)))
        self.cache=(x.copy(),residual,jac)
        return residual,jac


def fit_trajectories(groups,cameras,offsets,window,spacing,weight,fixed=(1,),check=lambda:None,max_nfev=200):
    started=time.monotonic()
    problem=SplineProblem(groups,cameras,offsets,window,spacing,weight,fixed,check)
    lo=np.r_[np.full(problem.n_offsets,-25.),np.full(len(problem.x0)-problem.n_offsets,-np.inf)]
    hi=np.r_[np.full(problem.n_offsets,25.),np.full(len(problem.x0)-problem.n_offsets,np.inf)]
    result=least_squares(lambda x:problem.evaluate(x)[0],problem.x0,jac=lambda x:problem.evaluate(x)[1],
        method='trf',tr_solver='lsmr',bounds=(lo,hi),ftol=1e-6,xtol=1e-6,gtol=1e-6,max_nfev=max_nfev)
    problem.evaluate(result.x);offsets,coeff=problem.unpack(result.x)
    boundary=[c for c in problem.free if abs(offsets[c])>=24.99]
    return dict(converged=bool(result.success),status=int(result.status),message=result.message,
        offsets=offsets,coefficients=coeff.tolist(),group_ids=[g['group_id'] for g in groups],
        knots=problem.spline.t.tolist(),window=list(window),spacing=spacing,weight=weight,
        center=problem.center.tolist(),diameter=problem.diameter,objective=float(2*result.cost),
        reprojection_mean_pixels=float(np.mean(problem.last_raw)),reprojection_median_pixels=float(np.median(problem.last_raw)),
        positive_depth=bool(np.all(problem.last_depths>0)),boundary_cameras=boundary,
        nfev=int(result.nfev),njev=int(result.njev),optimality=float(result.optimality),wall_seconds=time.monotonic()-started,
        initialization=problem.initialization,evaluation_trace=problem.evaluation_trace,
        solver=dict(method='trf',linear_solver='lsmr',ftol=1e-6,xtol=1e-6,gtol=1e-6,max_nfev=max_nfev,
            loss='pointwise one-pixel soft-L1 manually robustified before sample normalization; linear least-squares loss retains quadratic acceleration'))


def predict(fit,group_index,camera,frames,offset):
    spline=BSpline(fit['knots'],np.asarray(fit['coefficients'][group_index]),3,extrapolate=False)
    xyz=spline((np.asarray(frames)-offset)/25)
    return project_jacobian(xyz,camera,np.asarray(fit['center']),fit['diameter'])[0]


def estimate_held_out(groups,cameras,training_fit,held_out=(0,10,20,30),check=lambda:None):
    """Training state is read-only; scalar held-out offsets cannot change it."""
    rows={}; indices={gid:i for i,gid in enumerate(training_fit['group_ids'])}
    for c in held_out:
        observations=[(indices[g['group_id']],o) for g in groups if g['group_id'] in indices for o in g['observations'] if o['camera_id']==c]
        if not observations: rows[c]=dict(status='unsupported',offset=None);continue
        n=sum(len(o['frames']) for _,o in observations)
        def residual(x):
            check();errors=np.concatenate([predict(training_fit,i,cameras[c],o['frames'],x[0])-o['xy'] for i,o in observations])
            return robust_residual_jacobian(errors,n)[0].ravel()
        # Post-fit scalar profiling is separate from the joint sparse LSMR
        # production solve. Search every integer basin against frozen splines.
        def objective(offset):
            r=residual([offset]);return float(r@r)
        grid=np.arange(-25,26,dtype=float);costs=[objective(v) for v in grid]
        minima=[i for i in range(len(grid)) if (i==0 or costs[i]<=costs[i-1]) and (i==len(grid)-1 or costs[i]<=costs[i+1])]
        basins=[]
        for i in minima:
            r=minimize_scalar(objective,bounds=(max(-25,grid[i]-1),min(25,grid[i]+1)),method='bounded',options=dict(xatol=1e-6,maxiter=200))
            basins.append(dict(offset=float(r.x),converged=bool(r.success),nfev=int(r.nfev),objective=float(r.fun)))
        best=min(basins,key=lambda s:s['objective'])
        competing=[s for s in basins if np.sqrt(s['objective'])<=np.sqrt(best['objective'])+.05]
        good=all(s['converged'] and abs(s['offset'])<24.99 for s in competing) and np.ptp([s['offset'] for s in competing])<=.25
        rows[c]=dict(status='passed' if good else 'ambiguous_or_nonconverged',offset=best['offset'] if good else None,
            integer_grid=grid.tolist(),integer_costs=costs,basins=basins,solver='post-fit scalar profile; bounded refinement of every integer basin; trajectories frozen')
    return rows


def profile_group(group,cameras,edge,window,spacing,weight,grid,check=lambda:None):
    """Independent group/edge gauge; no production-state argument or access."""
    a,b=edge['a'],edge['b'];held={0,10,20,30};training=clip_groups([group],window,set(cameras)-held)
    observed={o['camera_id'] for g in training for o in g['observations']}
    if len(observed)<3: return dict(group_id=group['group_id'],costs=[None]*len(grid),failures=['fewer than three training cameras'])
    values=[];failures=[];traces=[]
    held_endpoint=a if a in held else b if b in held else None
    frozen=None
    if held_endpoint is not None:
        anchor=b if a in held else a
        if anchor not in observed: return dict(group_id=group['group_id'],costs=[None]*len(grid),failures=['training endpoint unsupported'])
        frozen=fit_trajectories(training,cameras,{c:0. for c in observed},window,spacing,weight,fixed=(anchor,),check=check)
    for lag in grid:
        check()
        try:
            if held_endpoint is None:
                if not {a,b}<=observed: raise InsufficientSupport('edge endpoint unsupported')
                offsets={c:0. for c in observed};offsets[b]=float(lag)
                fit=fit_trajectories(training,cameras,offsets,window,spacing,weight,fixed=(a,b),check=check)
                cost=fit['objective']
            else:
                fit=frozen
                obs=next(o for o in clip_groups([group],window)[0]['observations'] if o['camera_id']==held_endpoint)
                errors=predict(frozen,0,cameras[held_endpoint],obs['frames'],lag if held_endpoint==b else -lag)-obs['xy']
                residual=robust_residual_jacobian(errors,len(errors))[0];cost=float(np.sum(residual**2))
            valid=fit['converged'] and fit['positive_depth'] and not fit['boundary_cameras']
            values.append(float(cost) if valid else None)
            traces.append(dict(lag=float(lag),converged=fit['converged'],nfev=fit['nfev'],objective=float(cost),boundary_cameras=fit['boundary_cameras']))
            if not valid: failures.append(dict(lag=float(lag),reason='nonconverged, negative depth or nuisance boundary'))
        except (InsufficientSupport,ValueError,FloatingPointError) as error:
            values.append(None);failures.append(dict(lag=float(lag),reason=str(error)))
    return dict(group_id=group['group_id'],costs=values,failures=failures,optimizer_traces=traces)


def curve_summary(curves,grid,minimum_groups=12):
    grid=np.asarray(grid);curves=np.asarray(curves,dtype=float).reshape(-1,len(grid))
    good=np.isfinite(curves).all(axis=1);curves=curves[good]
    result=dict(passed=False,support=len(curves),support_mask=good.tolist(),lag=None,blockers=[])
    if len(curves)<minimum_groups: result['blockers'].append('insufficient groups spanning full search');return result
    aggregate=np.sqrt(np.maximum(0,np.mean(curves,axis=0)));best=int(np.argmin(aggregate));lag=float(grid[best])
    away=np.abs(grid-lag)>1;gap=float(np.min(aggregate[away])-aggregate[best]) if away.any() else 0.
    rng=np.random.default_rng(0);sample=rng.integers(0,len(curves),(256,len(curves)))
    estimates=grid[np.argmin(np.mean(curves[sample],axis=1),axis=1)];interval=np.quantile(estimates,[.025,.975])
    result.update(lag=lag,grid=grid.tolist(),cost_pixels=aggregate.tolist(),optimum_gap_pixels=gap,
        bootstrap_95_frames=interval.tolist(),bootstrap_halfwidth_frames=float(np.ptp(interval)/2),bootstrap_resamples=256,
        bootstrap_seed=0,bootstrap_unit='whole multiview group')
    if abs(lag)>=24.99: result['blockers'].append('boundary optimum')
    if gap<.05: result['blockers'].append('ambiguous optimum')
    if np.ptp(interval)/2>.25: result['blockers'].append('bootstrap halfwidth exceeds0.25')
    result['passed']=not result['blockers'];return result


def profile_job(payload):
    group,cameras,edge,window,spacing,weight,grid,deadline=payload
    import cv2
    cv2.setNumThreads(1)
    def check():
        if deadline is not None and time.time()>=deadline: raise TimeoutError('independent profile deadline; packaging reserve protected')
    return profile_group(group,cameras,edge,window,spacing,weight,grid,check)


def independent_edge(groups,cameras,edge,window,spacing,weight,check=lambda:None,minimum_groups=12,workers=1,deadline=None):
    """Full independent integer search, every basin .05 then competing basins .01.

    Curves are cached per entire group. Refinements keep exactly the same groups;
    failed refinement fits remain missing and cannot qualify a timing estimate.
    """
    selected=[g for g in groups if {edge['a'],edge['b']}<={o['camera_id'] for o in g['observations']}]
    caches={g['group_id']:{} for g in selected};traces=[]
    if not 1<=workers<=8: raise ValueError('CPU worker limit exceeded')
    executor=ProcessPoolExecutor(max_workers=workers,mp_context=multiprocessing.get_context('spawn')) if workers>1 else None
    def evaluate(grid,penalty):
        jobs=[]
        for g in selected:
            check();missing=[float(v) for v in grid if (penalty,float(v)) not in caches[g['group_id']]]
            if not missing: continue
            payload=(g,cameras,edge,window,spacing,penalty,missing,deadline)
            jobs.append((g,missing,executor.submit(profile_job,payload) if executor else None))
        for g,missing,future in jobs:
            check()
            row=future.result(timeout=max(.001,deadline-time.time()) if deadline else None) if future else profile_group(g,cameras,edge,window,spacing,penalty,missing,check)
            for lag,cost in zip(missing,row['costs']): caches[g['group_id']][penalty,lag]=cost
            traces.append(dict(weight=penalty,**row,grid=missing))
        return [[caches[g['group_id']][penalty,float(v)] for v in grid] for g in selected]
    try:
        outputs={}
        for label,penalty in [('regularized',weight),('data_only',0.)]:
            grid=np.arange(-25,26,dtype=float);curves=evaluate(grid,penalty)
            summary=curve_summary(curves,grid,minimum_groups)
            if summary['lag'] is not None:
                costs=np.asarray(summary['cost_pixels'])
                if np.ptp(costs)>1e-8:
                    minima=[i for i in range(len(grid)) if (i==0 or costs[i]<=costs[i-1]) and (i==len(grid)-1 or costs[i]<=costs[i+1])]
                    refined=np.unique(np.round(np.r_[grid,*[np.arange(max(-25,grid[i]-1),min(25,grid[i]+1)+.025,.05) for i in minima]],8))
                    curves=evaluate(refined,penalty);summary=curve_summary(curves,refined,minimum_groups);grid=refined
                    if summary['lag'] is not None:
                        costs=np.asarray(summary['cost_pixels']);minima=[i for i in range(len(grid)) if (i==0 or costs[i]<=costs[i-1]) and (i==len(grid)-1 or costs[i]<=costs[i+1]) and costs[i]<=min(costs)+.05]
                        refined=np.unique(np.round(np.r_[grid,*[np.arange(max(-25,grid[i]-.05),min(25,grid[i]+.05)+.005,.01) for i in minima]],8))
                        curves=evaluate(refined,penalty);summary=curve_summary(curves,refined,minimum_groups);grid=refined
            outputs[label]=dict(**summary,group_ids=[g['group_id'] for g in selected],group_profile_costs=curves)
        return dict(a=edge['a'],b=edge['b'],window=list(window),spacing=spacing,weight=weight,
            passed=all(r['passed'] for r in outputs.values()),profiles=outputs,optimizer_traces=traces,
            production_state_used=False)
    finally:
        if executor: executor.shutdown(wait=True,cancel_futures=True)


def independent_cycles(edges,cameras=range(34)):
    adjacency={c:[] for c in cameras}
    for i,e in enumerate(edges):
        if e.get('lag') is None: return dict(passed=False,reason='missing independent edge lag',cycles=[])
        adjacency[e['a']].append((e['b'],e['lag'],i));adjacency[e['b']].append((e['a'],-e['lag'],i))
    root=min(adjacency);potentials={root:0.};tree=set();todo=[root]
    for a in todo:
        for b,lag,i in adjacency[a]:
            if b not in potentials: potentials[b]=potentials[a]+lag;tree.add(i);todo.append(b)
    if len(potentials)!=len(adjacency): return dict(passed=False,reason='disconnected independent graph',cycles=[])
    cycles=[dict(edge=[e['a'],e['b']],closure_frames=e['lag']-(potentials[e['b']]-potentials[e['a']])) for i,e in enumerate(edges) if i not in tree]
    maximum=max((abs(c['closure_frames']) for c in cycles),default=np.inf)
    return dict(passed=bool(cycles) and maximum<=.25,cycles=cycles,maximum_closure_frames=float(maximum),source='independently measured edges; no production offsets')
