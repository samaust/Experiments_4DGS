"""Independent scalar Cox-de Boor, spatial jets and exact rational acceleration.

No candidate mathematical imports, arrays or result files are accessible here.
"""
from fractions import Fraction as F
import math
import struct
import numpy as np
from types import MappingProxyType
from collections.abc import Mapping

def freeze(v):
    if isinstance(v,np.ndarray):return np.frombuffer(v.astype("<f8").tobytes(),dtype="<f8").reshape(v.shape)
    if isinstance(v,Mapping):return MappingProxyType({k:freeze(x) for k,x in v.items()})
    if isinstance(v,(tuple,list)):return tuple(freeze(x) for x in v)
    return v

def bytes_of(v):return np.asarray(v,dtype="<f8").tobytes()


def arr(h):return np.frombuffer(bytes.fromhex(h),dtype='<f8')
def rational(v):return [str(v.numerator),str(v.denominator)]

def basis(U,t,order=0):
    n=len(U)-4
    if not U[3]<=t<=U[n]:raise ValueError('basis domain')
    cache={}
    def b(i,p,d):
        key=(i,p,d)
        if key in cache:return cache[key]
        if d>p:value=t*0
        elif p==0:value=t*0+int(U[i]<=t<U[i+1] or t==U[n] and U[i]<t==U[i+1])
        elif d:
            l=U[i+p]-U[i];r=U[i+p+1]-U[i+1];value=(p*b(i,p-1,d-1)/l if l else t*0)-(p*b(i+1,p-1,d-1)/r if r else t*0)
        else:
            l=U[i+p]-U[i];r=U[i+p+1]-U[i+1];value=((t-U[i])*b(i,p-1,0)/l if l else t*0)+((U[i+p+1]-t)*b(i+1,p-1,0)/r if r else t*0)
        cache[key]=value;return value
    return [b(i,3,order) for i in range(n)]


class Jet:
    def __init__(self,v,g=None,h=None):self.v=float(v);self.g=np.zeros(3) if g is None else np.asarray(g);self.h=np.zeros((3,3)) if h is None else np.asarray(h)
    @staticmethod
    def variable(v,i):
        g=np.zeros(3);g[i]=1;return Jet(v,g)
    def __add__(self,o):
        o=o if isinstance(o,Jet) else Jet(o);return Jet(self.v+o.v,self.g+o.g,self.h+o.h)
    __radd__=__add__
    def __neg__(self):return Jet(-self.v,-self.g,-self.h)
    def __sub__(self,o):return self+-o
    def __rsub__(self,o):return -self+o
    def __mul__(self,o):
        o=o if isinstance(o,Jet) else Jet(o)
        return Jet(self.v*o.v,self.g*o.v+o.g*self.v,self.h*o.v+o.h*self.v+np.outer(self.g,o.g)+np.outer(o.g,self.g))
    __rmul__=__mul__
    def reciprocal(self):
        if self.v==0:raise ZeroDivisionError('jet reciprocal')
        return Jet(1/self.v,-self.g/self.v**2,2*np.outer(self.g,self.g)/self.v**3-self.h/self.v**2)
    def __truediv__(self,o):return self*(o.reciprocal() if isinstance(o,Jet) else 1/o)
    def sqrt(self):
        v=math.sqrt(self.v)
        if v==0:raise ValueError('sqrt derivative at zero')
        return Jet(v,self.g/(2*v),self.h/(2*v)-np.outer(self.g,self.g)/(4*v**3))


def spatial(xyz,cam,center,diameter,observed,n):
    X=[Jet.variable(xyz[i],i) for i in range(3)]
    physical=[X[i]*diameter+center[i] for i in range(3)]
    camera=[sum((physical[j]*cam['R'][i][j] for j in range(3)),Jet(cam['t'][i])) for i in range(3)]
    if abs(camera[2].v)<1e-9:raise FloatingPointError('reference camera plane')
    uv=[camera[i]/camera[2] for i in range(2)];radial=1+cam['parameters_colmap'][3]*(uv[0]*uv[0]+uv[1]*uv[1]);dist=[v*radial for v in uv]
    errors=[sum((dist[j]*cam['K'][i][j] for j in range(2)),Jet(cam['K'][i][2]-observed[i])) for i in range(2)]
    root=(1+errors[0]*errors[0]+errors[1]*errors[1]).sqrt();loss=2*(root-1)/n
    factor=(2*(root+1).reciprocal()).sqrt()/math.sqrt(n)
    residual=[e*factor for e in errors]
    return loss,residual,camera[2]/diameter


def setup(knots_hex,quadrature_hex,weight,check=lambda:None):
    U=[F.from_float(float(x)) for x in arr(knots_hex)];Q=[F.from_float(float(x)) for x in arr(quadrature_hex)];n=len(U)-4
    s=dict(n=n,active=bool(weight),scale=F(weight,len(Q)),samples=len(Q))
    if not weight:return s
    L=[]
    for t in Q:check();L.append(basis(U,t,2))
    H=[[F(0) for _ in range(n)] for _ in range(n)]
    for row in L:
        check()
        for i in range(n):
            for j in range(n):H[i][j]+=2*s['scale']*row[i]*row[j]
    s.update(L=L,H=H);return s


def acceleration(s,x,check=lambda:None):
    n=s['n'];C=[F.from_float(float(v)) for v in x];G=[F(0)]*(3*n);cost=F(0);r=[];J=[];H=np.zeros((3*n,3*n))
    if not s['active']:return dict(F=0.,G=np.zeros(3*n),H=H,r=np.zeros(0),J=np.zeros((0,3*n)),exact=None)
    scale=math.sqrt(float(s['scale']))
    for row in s['L']:
        check()
        for axis in range(3):
            a=sum((row[j]*C[3*j+axis] for j in range(n)),F(0));cost+=s['scale']*a*a
            jr=np.zeros(3*n)
            for j in range(n):G[3*j+axis]+=2*s['scale']*row[j]*a;jr[3*j+axis]=float(row[j])*scale
            r.append(float(a)*scale);J.append(jr)
    for i in range(n):
        for j in range(n):
            for k in range(3):H[3*i+k,3*j+k]=float(s['H'][i][j])
    return dict(F=float(cost),G=np.array(list(map(float,G))),H=H,r=np.array(r),J=np.array(J),exact=dict(F=rational(cost),G=list(map(rational,G)),H=[[rational(v) for v in row] for row in s['H']]))


class Reference:
    def __init__(self,case,setup,check=lambda:None):self.case=freeze(case);self.setup=freeze(setup);self.check=check;self.decoder=arr
    def evaluate(self,state,audit):
        owner=audit
        c=self.case;p=c['problem'];x=self.decoder(state['x_hex']);U=list(arr(c['knots_hex']));nf=len(p['free']);nc=len(U)-4;m=len(x);C=x[nf:].reshape(nc,3)
        vg=self.decoder(state['vg_hex']);vby=None if state['vby_hex'] is None else self.decoder(state['vby_hex'])
        actual=dict(q_hex=state['q_hex'],x_hex=bytes_of(x).hex(),coefficient_hex=bytes_of(C).hex(),vg_hex=bytes_of(vg).hex(),vby_hex=None if vby is None else bytes_of(vby).hex(),scope=state.get('scope'),case=c,setup=self.setup)
        if hasattr(owner,'observe'):
            audit=lambda kind,fn:owner(kind,lambda:owner.observe(kind,actual,fn))
        offsets={int(k):v for k,v in p['offsets'].items()};offsets.update(dict(zip(p['free'],x[:nf])))
        def prepare():
            rows=[]
            for observation in p['observations'][0]['observations']:
                camera=observation['camera_id'];cam=p['calibration'][str(camera)];j=p['free'].index(camera) if camera in p['free'] else None
                for frame,xy in zip(observation['frames'],observation['xy']):
                    self.check();t=(frame-offsets[camera])/25;B=np.array(basis(U,t));Bp=np.array(basis(U,t,1));Bpp=np.array(basis(U,t,2))
                    xyz=np.array([sum(B[i]*C[i,k] for i in range(nc)) for k in range(3)])
                    T=np.zeros((3,m));second=np.zeros((3,m,m))
                    for k in range(3):
                        for i in range(nc):T[k,nf+3*i+k]=B[i]
                        if j is not None:
                            T[k,j]=-sum(Bp[i]*C[i,k] for i in range(nc))/25;second[k,j,j]=sum(Bpp[i]*C[i,k] for i in range(nc))/625
                            for i in range(nc):second[k,j,nf+3*i+k]=second[k,nf+3*i+k,j]=-Bp[i]/25
                    rows.append((xyz,cam,xy,T,second))
            return rows
        rows=audit('prepare',prepare)
        def data():
            Fdata=0.;G=np.zeros(m);H=np.zeros((m,m));rs=[];Js=[];loss_jets=[];depth_jets=[]
            for xyz,cam,xy,T,second in rows:
                self.check();loss,residual,z=spatial(xyz,cam,c['center'],c['diameter'],xy,c['n']);Fdata+=loss.v;G+=loss.g@T
                loss_jets.append((loss,T,second))
                for r in residual:rs.append(r.v);Js.append(r.g@T)
                depth_jets.append((z,T,second))
            return dict(Fdata=Fdata,Gdata=G,rdata=np.array(rs),Jdata=np.array(Js)),(loss_jets,depth_jets)
        out,depths=audit('objective_residual',data)
        def hessian():
            H=np.zeros((m,m))
            for loss,T,second in depths[0]:
                self.check();H+=T.T@loss.h@T+sum((loss.g[k]*second[k] for k in range(3)),np.zeros((m,m)))
            return H
        out['Hdata']=audit('data_hessian',hessian)
        acc=audit('acceleration',lambda:acceleration(self.setup,x[nf:],self.check)) if c['weight'] else dict(F=0.,G=np.zeros(m-nf),H=np.zeros((m-nf,m-nf)),r=np.zeros(0),J=np.zeros((0,m-nf)),exact=None)
        out.update(Facc=acc['F'],Gacc=np.r_[np.zeros(nf),acc['G']],Hacc=np.pad(acc['H'],((nf,0),(nf,0))),racc=acc['r'],Jacc=np.pad(acc['J'],((0,0),(nf,0))),acceleration_exact=acc['exact'])
        def full():return out['Fdata']+out['Facc'],out['Gdata']+out['Gacc'],out['Hdata']+out['Hacc']
        out['F'],out['G'],out['H']=audit('full_sum',full);out['r']=np.concatenate((out['rdata'],out['racc']));out['J']=np.vstack((out['Jdata'],out['Jacc']))
        out['z'],out['Jz']=audit('raw_depth',lambda:(np.array([z.v for z,T,second in depths[1]]),np.array([z.g@T for z,T,second in depths[1]])))
        def values():
            gs=[];gps=[];gpps=[]
            for z in out['z']:
                s=float(z)-1e-8;inv=1/math.hypot(1,s);g=s/math.hypot(1,s);gp=inv*inv*inv;gpp=-3*g*inv*inv*inv*inv
                if not all(map(math.isfinite,(g,gp,gpp))) or gp==0 or s!=0 and gpp==0:raise FloatingPointError('reference bounded derivative underflow/nonfinite')
                gs.append(g);gps.append(gp);gpps.append(gpp)
            gp=np.array(gps);return np.array(gs),gp,np.array(gpps),vg*gp
        out['g'],out['gp'],out['gpp'],out['vd']=audit('bounded_values',values)
        def raw_curvature():
            H=np.zeros((m,m))
            for v,(z,T,second) in zip(out['vd'],depths[1]):
                self.check();H+=v*(T.T@z.h@T+sum((z.g[k]*second[k] for k in range(3)),np.zeros((m,m))))
            return H
        out['Hz']=audit('weighted_raw_hessian',raw_curvature)
        def bounded():
            H=out['Hz'].copy()
            for v,gpp,J in zip(vg,out['gpp'],out['Jz']):H+=(v*gpp)*np.outer(J,J)
            return out['gp'][:,None]*out['Jz'],H
        out['Jg'],out['Hg']=audit('bounded_curvature',bounded)
        for k,v in out.items():
            if isinstance(v,np.ndarray) and not np.isfinite(v).all():raise FloatingPointError('reference nonfinite '+k)
        return out


def report(out,state,scale,P,inverse):
    """Independent physical to canonical to public chain and original forces."""
    result={k:v for k,v in out.items() if not isinstance(v,np.ndarray)};frames={}
    for frame in ('x','q','y'):
        M=np.eye(len(scale)) if frame=='x' else np.diag(scale) if frame=='q' else np.diag(scale)@P
        f={k:M.T@out[k] for k in ('G','Gdata','Gacc')}
        f.update({k:M.T@out[k]@M for k in ('H','Hdata','Hacc','Hz','Hg')})
        f.update({k:out[k]@M for k in ('J','Jdata','Jacc','Jz','Jg')});frames[frame]=f
    for k in ('z','g','gp','gpp','vd','r','rdata','racc'):result[k]=out[k]
    result['vg']=arr(state['vg_hex']);result['frames']=frames
    if state['label']=='returned':
        vby=arr(state['vby_hex']);Cbq=inverse.T@vby;Cdq=frames['q']['Jz'].T@out['vd'];Gq=frames['q']['G'];K=(Gq+Cdq)+Cbq
        result.update(vby=vby,complementarity=out['vd']*(out['z']-1e-8))
        for frame,conv in [('x',np.diag(1/scale)),('q',np.eye(len(scale))),('y',P.T)]:
            frames[frame].update(Cd=conv@Cdq,Cb=conv@Cbq,KKT=conv@K,KKT_inf=float(np.max(np.abs(conv@K))))
    else:result.update(vby=None,complementarity=None)
    return result
