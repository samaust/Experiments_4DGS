"""Explicit v2 data loss and v6 data curvature, with owned shared geometry.

Projection/robust/SVD formulas copied from hash-pinned v2/v6 sources; no
historical constructor, optimizer, rounded acceleration or evaluator imports.
"""
import numpy as np
from scipy.interpolate import BSpline
import basketball_acceleration_decimal_v15 as acceleration
from basketball_shared_accounting_v15 import freeze, bytes_of

def boundary(name):
    """Instrumentable geometry boundary; production arithmetic follows this call."""
    return None

def spline_second(spline,t):
    boundary("spline_second")
    return spline.derivative(2)(t)

def projection_first(xyz,camera,center,diameter):
    boundary("projection_first")
    R=np.asarray(camera["R"]); K=np.asarray(camera["K"])[:2,:2]; k=camera["parameters_colmap"][3]
    c=(xyz*diameter+center)@R.T+camera["t"];z=c[:,2]
    if np.any(np.abs(z)<1e-9):raise FloatingPointError("projection at camera plane")
    u=c[:,:2]/z[:,None]
    predicted=(u*(1+k*np.sum(u*u,axis=1))[:,None])@K.T+np.asarray(camera["K"])[:2,2]
    P=np.zeros((len(z),2,3));P[:,0,0]=1/z;P[:,1,1]=1/z;P[:,:,2]=-u/z[:,None]
    T=(1+k*np.sum(u*u,axis=1))[:,None,None]*np.eye(2)+2*k*u[:,:,None]*u[:,None,:]
    J=np.einsum("nai,ij->naj",np.einsum("ab,nbc,ncd->nad",K,T,P),R)*diameter
    return predicted,J

def normalized_depth(xyz,cam,center,diameter):
    boundary("normalized_depth")
    R=np.asarray(cam["R"])[2]
    return xyz@R+(R@center+cam["t"][2])/diameter

def projection_second(xyz, camera, center, diameter, residual_only=False):
    """Image value, first and second derivatives wrt rig-normalized xyz."""
    if residual_only:return (*projection_first(xyz,camera,center,diameter),None)
    boundary("projection_second")
    R=np.asarray(camera['R']);K=np.asarray(camera['K'])[:2,:2];k=camera['parameters_colmap'][3]
    c=(xyz*diameter+center)@R.T+camera['t'];z=c[:,2]
    if np.any(np.abs(z)<1e-9):raise FloatingPointError('projection at camera plane')
    u=c[:,:2]/z[:,None]
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
            pred,P,HP=(*projection_first(xyz,cam,np.asarray(c['center']),c['diameter']),None) if residual_only else projection_second(xyz,cam,np.asarray(c['center']),c['diameter'])
            e=pred-np.asarray(o['xy']);sqrt=None;point_g=None;spatial=None
            if not residual_only:
                boundary('objective_geometry')
                sqrt=np.sqrt(1+np.sum(e*e,axis=1));point_g=2*e/(c['n']*sqrt[:,None]);spatial=np.einsum('na,nai->ni',point_g,P)
            T=np.zeros((len(t),3,len(x)));T[:,:,nf:]=np.einsum('nk,ab->nakb',B,np.eye(3)).reshape(len(t),3,3*nc)
            j=p['free'].index(o['camera_id']) if o['camera_id'] in p['free'] else None
            if j is not None:T[:,:,j]=-Bp@C # q convention, offset scale exactly once
            rows.append(dict(B=B,Bp=Bp,Bpp=Bpp,C=C,e=e,sqrt=sqrt,P=P,HP=HP,point_g=point_g,spatial=spatial,T=T,j=j,R=np.asarray(cam['R'])[2],z=None if residual_only else normalized_depth(xyz,cam,np.asarray(c['center']),c['diameter'])))
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
            return dict(Fdata=F,Gdata=G,rdata=r,Jdata=J)
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
            H=np.zeros((m,m))
            for d in rows:
                self.check();e=d['e'];s=d['sqrt'];P=d['P'];W=2/self.case['n']*(np.eye(2)[None,:,:]/s[:,None,None]-e[:,:,None]*e[:,None,:]/s[:,None,None]**3)
                cur=np.einsum('nai,nab,nbj->nij',P,W,P)+np.einsum('na,naij->nij',d['point_g'],d['HP'])
                H+=np.einsum('nia,nij,njb->ab',d['T'],cur,d['T'])
                if d['j'] is not None:
                    j=d['j'];mix=-(d['Bp'].T@d['spatial']).ravel();H[j,nf:]+=mix;H[nf:,j]+=mix;H[j,j]+=np.sum(d['spatial']*(d['Bpp']@d['C']))
            return H
        out['Hdata']=audit('data_hessian',hessian)
        def full():return out['Fdata']+out['Facc'],out['Gdata']+out['Gacc'],out['Hdata']+out['Hacc']
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
        for k in ('H','Hdata','Hacc','Hz','Hg'):out[k]=out[k]/scale[:,None]/scale[None,:]
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
