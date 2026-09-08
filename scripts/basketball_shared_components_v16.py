"""Explicit v2 data loss and v6 data curvature, with owned shared geometry.

Projection/robust/SVD formulas copied from hash-pinned v2/v6 sources; no
historical constructor, optimizer, rounded acceleration or evaluator imports.
"""
import numpy as np
from scipy.interpolate import BSpline
import basketball_acceleration_decimal_v16 as acceleration
from basketball_shared_accounting_v16 import freeze, bytes_of

def boundary(name):
    """Instrumentable geometry boundary; production arithmetic follows this call."""
    return None

def spline_second(spline,t):
    boundary("spline_second")
    return spline.derivative(2)(t)

def projection_first(xyz,camera,center,diameter,return_focal=False,check=lambda:None):
    boundary("projection_first")
    R=np.asarray(camera["R"]); K=np.asarray(camera["K"])[:2,:2]; k=camera["parameters_colmap"][3]
    c=(xyz*diameter+center)@R.T+camera["t"];z=c[:,2]
    if np.any(np.abs(z)<1e-9):raise FloatingPointError("projection at camera plane")
    u=c[:,:2]/z[:,None]
    focal=(u*(1+k*np.sum(u*u,axis=1))[:,None])@K.T
    boundary("focal_output");predicted=focal+np.asarray(camera["K"])[:2,2]
    P=np.zeros((len(z),2,3));P[:,0,0]=1/z;P[:,1,1]=1/z;P[:,:,2]=-u/z[:,None]
    T=(1+k*np.sum(u*u,axis=1))[:,None,None]*np.eye(2)+2*k*u[:,:,None]*u[:,None,:]
    J=np.einsum("nai,ij->naj",np.einsum("ab,nbc,ncd->nad",K,T,P),R)*diameter
    return (predicted,J,focal) if return_focal else (predicted,J)

def normalized_depth(xyz,cam,center,diameter):
    boundary("normalized_depth")
    R=np.asarray(cam["R"])[2]
    return xyz@R+(R@center+cam["t"][2])/diameter

def projection_second(xyz, camera, center, diameter, residual_only=False,return_focal=False,check=lambda:None):
    """Analytical upper pairs, each evaluated once and stored twice."""
    if residual_only:
        pred,J,focal=projection_first(xyz,camera,center,diameter,True,check)
        return (pred,J,None,focal) if return_focal else (pred,J,None)
    boundary("projection_second")
    R=np.asarray(camera['R']);K=np.asarray(camera['K'])[:2,:2];k=camera['parameters_colmap'][3]
    c=(xyz*diameter+center)@R.T+camera['t'];z=c[:,2]
    if np.any(np.abs(z)<1e-9):raise FloatingPointError('projection at camera plane')
    u=c[:,:2]/z[:,None];n=len(z);eye=np.eye(2)
    focal=(u*(1+k*np.sum(u*u,axis=1))[:,None])@K.T
    boundary('focal_output');predicted=focal+np.asarray(camera['K'])[:2,2]
    P=np.zeros((n,2,3));P[:,0,0]=1/z;P[:,1,1]=1/z;P[:,:,2]=-u/z[:,None]
    boundary('HP_pairs');HP=np.zeros((n,2,3,3))
    for a in range(2):
        for i in range(3):
            for j in range(i,3):
                check();v=-1/z**2 if i==a and j==2 else 2*u[:,a]/z**2 if i==j==2 else np.zeros(n)
                HP[:,a,i,j]=v;HP[:,a,j,i]=v
    T=(1+k*np.sum(u*u,axis=1))[:,None,None]*eye+2*k*u[:,:,None]*u[:,None,:]
    boundary('HT_pairs');HT=np.zeros((n,2,2,2))
    for a in range(2):
        for i in range(2):
            for j in range(i,2):
                check();v=2*k*((a==i)*u[:,j]+(a==j)*u[:,i]+(i==j)*u[:,a]);HT[:,a,i,j]=v;HT[:,a,j,i]=v
    JP=np.einsum('ab,nbc,ncd->nad',K,T,P)
    boundary('Hcam_pairs');Hcam=np.zeros((n,2,3,3))
    for a in range(2):
        for k0 in range(3):
            for l in range(k0,3):
                check();v=np.zeros(n);w=np.zeros(n)
                for b in range(2):
                    for i in range(2):
                        for j in range(2):v=v+(((K[a,b]*HT[:,b,i,j])*P[:,i,k0])*P[:,j,l])
                for b in range(2):
                    for i in range(2):w=w+(K[a,b]*T[:,b,i])*HP[:,i,k0,l]
                v=v+w;Hcam[:,a,k0,l]=v;Hcam[:,a,l,k0]=v
    J=np.einsum('nai,ij->naj',JP,R)*diameter
    boundary('rig_pairs');H=np.zeros((n,2,3,3))
    for a in range(2):
        for k0 in range(3):
            for l in range(k0,3):
                check();v=np.zeros(n)
                for i in range(3):
                    for j in range(3):v=v+(R[i,k0]*Hcam[:,a,i,j])*R[j,l]
                v=v*diameter**2;H[:,a,k0,l]=v;H[:,a,l,k0]=v
    return (predicted,J,H,focal) if return_focal else (predicted,J,H)

def robust_residual_jacobian(errors,samples):
    """Pointwise one-pixel soft-L1, then sample normalization (not before)."""
    s=np.sum(errors**2,axis=1); q=np.sqrt(1+s)
    w=np.sqrt(2/(q+1))/np.sqrt(samples)
    derivative=-w/(4*q*(q+1))
    jac=w[:,None,None]*np.eye(2)+2*derivative[:,None,None]*errors[:,:,None]*errors[:,None,:]
    return errors*w[:,None],jac

def canonical(v):
    v = np.asarray(v, float).copy()
    if v[np.argmax(np.abs(v))] < 0:
        v *= -1
    return v

def deterministic_svd(J):
    """Canonical coordinate-pivot basis of each numerically repeated subspace.

    Projectors are invariant to LAPACK's arbitrary basis in repeated/null spaces.
    The grouping tolerance is explicitly recorded, separate from the rank rule.
    """
    if J.ndim!=2 or J.shape[0]<J.shape[1]:raise ValueError("undersized metric before SVD")
    boundary("svd")
    _, s, vt = np.linalg.svd(J, full_matrices=False)
    n = J.shape[1]
    if len(s)!=n:raise ArithmeticError("incomplete one-SVD result")
    tol = max(J.shape)*np.finfo(float).eps*(s[0] if len(s) else 0.)
    groups = []; vectors = []; i = 0
    while i < n:
        end = i+1
        while end < n and abs(s[end]-s[i]) <= tol:
            end += 1
        sub = vt[i:end]; P = sub.T@sub; basis = []
        for j in range(n):
            v = P[:, j].copy()
            for _ in range(2):
                for b in basis:
                    v -= b@v*b
            norm = np.linalg.norm(v)
            if norm > 1e-10:
                basis.append(canonical(v/norm))
            if len(basis) == end-i:
                break
        if len(basis) != end-i:
            raise ArithmeticError('unresolved deterministic singular subspace')
        vectors.extend(basis)
        groups.append(dict(indices=list(range(i, end)), projector=P.tolist(), basis=[b.tolist() for b in basis],
                           singular_values=s[i:end].tolist()))
        i = end
    return s, np.asarray(vectors), tol, groups


def arr(h):return np.frombuffer(bytes.fromhex(h),dtype='<f8')
def immutable(x):
    a=np.asarray(x,dtype='<f8');return np.frombuffer(a.tobytes(),dtype='<f8').reshape(a.shape)

def bounded(z):
    s=z-1e-8
    with np.errstate(all='ignore'):
        inv=1/np.hypot(1.,s);g=s*inv;gp=inv*inv*inv;gpp=-3*g*inv*inv*inv*inv
    if not all(np.isfinite(v).all() for v in (g,gp,gpp)) or np.any((gp==0)|((s!=0)&(gpp==0))):raise FloatingPointError('bounded derivative underflow/nonfinite')
    return g,gp,gpp


class Candidate:
    def __init__(self,case,setup,check=lambda:None):
        self.case=freeze(case);self.setup=freeze(setup);self.check=check;self.decoder=arr
    def prepare(self,x,residual_only=False):
        boundary('prepare_first' if residual_only else 'prepare_full')
        c=self.case;p=c['problem'];nc=len(arr(c['knots_hex']))-4;nf=len(p['free']);C=x[nf:].reshape(nc,3)
        spline=BSpline(arr(c['knots_hex']),np.eye(nc),3,extrapolate=False);sp1=spline.derivative()
        offsets={int(k):v for k,v in p['offsets'].items()};offsets.update(dict(zip(p['free'],x[:nf])))
        rows=[]
        for o in p['observations'][0]['observations']:
            self.check();cam=p['calibration'][str(o['camera_id'])];t=(np.asarray(o['frames'])-offsets[o['camera_id']])/25
            B=spline(t);Bp=sp1(t);Bpp=None if residual_only else spline_second(spline,t);xyz=B@C
            if not all(np.isfinite(v).all() for v in (B,Bp,xyz) + (() if residual_only else (Bpp,))):raise FloatingPointError('basis/domain')
            if residual_only:
                pred,P,focal=projection_first(xyz,cam,np.asarray(c['center']),c['diameter'],True,self.check);HP=None
            else:pred,P,HP,focal=projection_second(xyz,cam,np.asarray(c['center']),c['diameter'],return_focal=True,check=self.check)
            boundary('centered_errors');centered=np.asarray(o['xy'])-np.asarray(cam['K'])[:2,2];e=focal-centered;sqrt=None;point_g=None;spatial=None
            if not residual_only:
                boundary('objective_geometry')
                sqrt=np.sqrt(1+np.sum(e*e,axis=1));point_g=2*e/(c['n']*sqrt[:,None]);spatial=np.einsum('na,nai->ni',point_g,P)
            T=np.zeros((len(t),3,len(x)));T[:,:,nf:]=np.einsum('nk,ab->nakb',B,np.eye(3)).reshape(len(t),3,3*nc)
            j=p['free'].index(o['camera_id']) if o['camera_id'] in p['free'] else None
            if j is not None:T[:,:,j]=-Bp@C # q convention, offset scale exactly once
            rows.append(dict(camera_id=o["camera_id"],frames=o["frames"],focal=focal,centered_observation=centered,B=B,Bp=Bp,Bpp=Bpp,C=C,e=e,sqrt=sqrt,P=P,HP=HP,point_g=point_g,spatial=spatial,T=T,j=j,R=np.asarray(cam['R'])[2],z=None if residual_only else normalized_depth(xyz,cam,np.asarray(c['center']),c['diameter'])))
        return rows
    def residual(self,rows):
        rr=[];JJ=[]
        for d in rows:
            self.check();r,j=robust_residual_jacobian(d['e'],self.case['n']);rr.append(r.ravel());JJ.append(np.einsum('nab,nbi,nij->naj',j,d['P'],d['T']).reshape(-1,self.case['dimension']))
        return np.concatenate(rr),np.vstack(JJ)
    def evaluate(self,state,audit,transform_only=False):
        owner=audit
        x=self.decoder(state['x_hex']);nf=len(self.case['problem']['free']);m=len(x);scale=arr(self.case['scale_hex'])
        vg=self.decoder(state['vg_hex']);vby=None if state['vby_hex'] is None else self.decoder(state['vby_hex'])
        actual=dict(q_hex=state['q_hex'],x_hex=bytes_of(x).hex(),coefficient_hex=bytes_of(x[nf:]).hex(),vg_hex=bytes_of(vg).hex(),vby_hex=None if vby is None else bytes_of(vby).hex(),scope=state.get('scope'),case=self.case,setup=self.setup)
        if hasattr(owner,'observe'):
            audit=lambda kind,fn:owner(kind,lambda:owner.observe(kind,actual,fn))
        rows=audit('prepare',lambda:self.prepare(x,transform_only))
        def objective():
            r,J=self.residual(rows)
            if transform_only:return dict(rdata=r,Jdata=J)
            F=0.;G=np.zeros(m)
            for d in rows:F+=float(np.sum(2*(d['sqrt']-1))/self.case['n']);G+=np.einsum('ni,nij->j',d['spatial'],d['T'])
            return dict(Fdata=F,Gdata=G,rdata=r,Jdata=J,consumed_observations=[dict(observation_index=index,camera_id=d['camera_id'],frame=frame,e=d['e'][row],spatial=d['spatial'][row],focal=d['focal'][row],centered_observation=d['centered_observation'][row]) for index,(d,row,frame) in enumerate((d,row,frame) for d in rows for row,frame in enumerate(d['frames']))])
        out=audit('residual_only' if transform_only else 'objective_residual',objective)
        if self.case['weight']:
            acc=audit('acceleration',lambda:acceleration.bundle(self.setup,x[nf:].astype('<f8').tobytes().hex(),self.check,residual_only=transform_only))
        else:acc=dict(F=0.,G=[0.]*(m-nf),H=[[0.]*(m-nf) for _ in range(m-nf)],r=[],J=[])
        ar=np.asarray(acc['r']);aJ=np.zeros((len(ar),m))
        if len(ar):aJ[:,nf:]=acc['J']
        out.update(racc=ar,Jacc=aJ,r=np.concatenate((out['rdata'],ar)),J=np.vstack((out['Jdata'],aJ)))
        if transform_only:return out
        out.update(Facc=acc['F'],Gacc=np.r_[np.zeros(nf),acc['G']],Hacc=np.pad(np.asarray(acc['H']),((nf,0),(nf,0))),acceleration_decimal=acc.get('decimal'))
        def hessian():
            boundary('data_assembly');ii,jj=np.triu_indices(m);values=np.zeros(len(ii))
            for d in rows:
                self.check();e=d['e'];s=d['sqrt'];P=d['P'];W=np.zeros((len(e),2,2))
                for a in range(2):
                    for b in range(a,2):
                        v=(2/self.case['n'])*((a==b)/s-(e[:,a]*e[:,b])/s**3);W[:,a,b]=v;W[:,b,a]=v
                boundary('spatial_pairs');cur=np.zeros((len(e),3,3))
                for i in range(3):
                    for j in range(i,3):
                        self.check();v=np.zeros(len(e));w=np.zeros(len(e))
                        for a in range(2):
                            for b in range(2):v=v+(P[:,a,i]*W[:,a,b])*P[:,b,j]
                        for a in range(2):w=w+d['point_g'][:,a]*d['HP'][:,a,i,j]
                        v=v+w;cur[:,i,j]=v;cur[:,j,i]=v
                contributions=np.zeros((len(e),len(ii)))
                for a in range(3):
                    for b in range(3):
                        self.check();contributions=contributions+(d['T'][:,a,ii]*cur[:,a,b,None])*d['T'][:,b,jj]
                values=values+np.add.accumulate(contributions,axis=0,dtype=np.float64)[-1]
                if d['j'] is not None:
                    j=d['j'];mix=np.zeros(m-nf)
                    for col in range(d['Bp'].shape[1]):
                        for axis in range(3):
                            self.check();mix[3*col+axis]=-np.add.accumulate(d['Bp'][:,col]*d['spatial'][:,axis],dtype=np.float64)[-1]
                    target=(ii==j)&(jj>=nf);values[target]+=mix
                    curvature=d['Bpp']@d['C'];diagonal=0.
                    for obs in range(len(e)):
                        self.check()
                        for axis in range(3):diagonal=diagonal+d['spatial'][obs,axis]*curvature[obs,axis]
                    values[(ii==j)&(jj==j)]+=diagonal
            H=np.zeros((m,m));H[ii,jj]=values;H[jj,ii]=values;return H
        out['Hdata']=audit('data_hessian',hessian)
        def full():
            boundary('full_sum');ii,jj=np.triu_indices(m);H=np.zeros((m,m));v=out['Hdata'][ii,jj]+out['Hacc'][ii,jj];H[ii,jj]=v;H[jj,ii]=v
            return out['Fdata']+out['Facc'],out['Gdata']+out['Gacc'],H
        out['F'],out['G'],out['H']=audit('full_sum',full)
        def depth():return np.concatenate([d['z'] for d in rows]),np.vstack([np.einsum('a,naj->nj',d['R'],d['T']) for d in rows])
        out['z'],out['Jz']=audit('raw_depth',depth)
        # One chain evaluation supplies the exact weights to the raw curvature.
        def depth_chain_values():
            g,gp,gpp=bounded(out['z']);return g,gp,gpp,vg*gp
        out['g'],out['gp'],out['gpp'],out['vd']=audit('bounded_values',depth_chain_values)
        def raw_curvature():
            H=np.zeros((m,m));base=0
            for d in rows:
                self.check();w=out['vd'][base:base+len(d['z'])];base+=len(w)
                if d['j'] is not None:
                    j=d['j'];mix=(-(w@d['Bp'])[:,None]*d['R']).ravel();H[j,nf:]+=mix;H[nf:,j]+=mix;H[j,j]+=float(w@(d['Bpp']@d['C']@d['R']))
            return H
        out['Hz']=audit('weighted_raw_hessian',raw_curvature)
        def bounded_curvature():return out['gp'][:,None]*out['Jz'],out['Hz']+out['Jz'].T@((vg*out['gpp'])[:,None]*out['Jz'])
        out['Jg'],out['Hg']=audit('bounded_curvature',bounded_curvature)
        # Candidate assembly is q. Export physical components before reporting;
        # this explicit conversion prevents the inherited q Hessian gaining D twice.
        for k in ('G','Gdata','Gacc'):out[k]=out[k]/scale
        for k in ('H','Hdata'):
            boundary('objective_q_to_x');ii,jj=np.triu_indices(m);H=np.zeros((m,m));v=(out[k][ii,jj]/scale[ii])/scale[jj];H[ii,jj]=v;H[jj,ii]=v;out[k]=H
        for k in ('Hacc','Hz','Hg'):out[k]=out[k]/scale[:,None]/scale[None,:]
        for k in ('J','Jdata','Jacc','Jz','Jg'):out[k]=out[k]/scale[None,:]
        for k,v in out.items():
            if isinstance(v,np.ndarray) and not np.isfinite(v).all():raise FloatingPointError('nonfinite '+k)
        return out


def metric_transform(J,coefficient_start,origin):
    """One production metric construction, rejected before SVD if undersized."""
    J=np.asarray(J);nf=coefficient_start;m=J.shape[1]
    if J.shape[0]<m-nf:raise ValueError('undersized metric before SVD')
    singular,V,tol,sub=deterministic_svd(J[:,nf:])
    scales=np.ones(len(singular));active=singular>tol
    scales[active]=np.clip(1/singular[active],1e-3,1e3)
    P=np.eye(m);P[nf:,nf:]=(V.T*scales)@V;inverse=np.linalg.inv(P)
    return dict(P=P,inverse=inverse,origin=arr(bytes_of(origin).hex()),singular=singular,rank_threshold=tol,scales=scales,subspaces=sub,active=active,coefficient_coverage=V.T@V)


def cold_transform(model,cold_state,audit):
    def owned_transform():
        rj=model.evaluate(cold_state,audit,transform_only=True)
        return audit('svd_transform',lambda:metric_transform(rj['J'],len(model.case['problem']['free']),arr(cold_state['q_hex'])))
    return audit('transform_context',owned_transform)
