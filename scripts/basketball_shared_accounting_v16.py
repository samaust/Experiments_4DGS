"""Immutable canonical state, finite component ownership and checked public replay."""
from dataclasses import dataclass
from types import MappingProxyType
import hashlib
from collections.abc import Mapping
import numpy as np


def frozen_array(v):
    a=np.asarray(v,dtype='<f8');return np.frombuffer(a.tobytes(),dtype='<f8').reshape(a.shape)
def freeze(v):
    if isinstance(v,np.ndarray):return frozen_array(v)
    if isinstance(v,Mapping):return MappingProxyType({k:freeze(x) for k,x in v.items()})
    if isinstance(v,(tuple,list)):return tuple(freeze(x) for x in v)
    return v
def bytes_of(v):return np.asarray(v,dtype='<f8').tobytes()


@dataclass(frozen=True)
class State:
    identity:str
    q:np.ndarray
    x:np.ndarray
    scope:str


class Ledger:
    def __init__(self,namespace,admitted=None,max_states=200,max_iterations=200):
        if max_states>200 or max_iterations>200:raise ValueError('caps')
        self.namespace=namespace;self.admitted=admitted;self.max_states=max_states;self.max_iterations=max_iterations;self.states={};self.iterations=0;self.entries=[]
    def request(self,q,x,scope='destination'):
        qb=bytes_of(q);xb=bytes_of(x);key=(scope,qb)
        if self.admitted is not None and (qb,xb) not in self.admitted:raise ValueError('unadmitted state')
        if key not in self.states:
            if len(self.states)>=self.max_states:raise ValueError('201st state rejected')
            identity=hashlib.sha256(self.namespace.encode()+scope.encode()+qb).hexdigest();self.states[key]=State(identity,frozen_array(q),frozen_array(x),scope)
        s=self.states[key]
        if bytes_of(s.x)!=xb:raise ValueError('same q wrong physical bytes')
        return s
    def iteration(self,n):
        if n<self.iterations or n>self.max_iterations:raise ValueError('iteration cap')
        self.iterations=n
    def enter(self,s,kind,callback):
        if not any(v is s for v in self.states.values()):raise ValueError('unallocated state')
        key=(s.identity,kind)
        if any(e['key']==key for e in self.entries):raise ValueError('duplicate entry')
        e=dict(key=key,status='entered');self.entries.append(e)
        try:value=callback()
        except BaseException:e['status']='interrupted';raise
        e['status']='completed';return value


def boundary(name):
    return None

def symmetric_objective_congruence(H,P,check=lambda:None):
    boundary('congruence_validation');H=np.asarray(H);P=np.asarray(P)
    if H.ndim!=2 or H.shape[0]!=H.shape[1] or P.ndim!=2 or P.shape[0]!=H.shape[0] or not np.isfinite(H).all() or not np.isfinite(P).all() or np.any(H!=H.T):raise ValueError('candidate objective congruence input contract')
    boundary('congruence_contraction');n=H.shape[0];d=P.shape[1];B=np.zeros((n,d))
    for k in range(n):
        check();B=B+H[:,k,None]*P[k,None,:]
    i,j=np.triu_indices(d);v=np.zeros(len(i))
    for a in range(n):
        check();v=v+P[a,i]*B[a,j]
    out=np.zeros((d,d));out[i,j]=v;out[j,i]=v;return out


def report(out,state,scale,P,inverse,bound_inverse=None,check=lambda:None):
    boundary("report")
    for key in ('H','Hdata'):
        H=np.asarray(out[key])
        if H.shape!=(len(scale),len(scale)) or not np.isfinite(H).all() or np.any(H!=H.T):raise ValueError('physical objective report input contract')
    result={k:v for k,v in out.items() if not isinstance(v,np.ndarray)};frames={f:{} for f in ('x','q','y')}
    for k in ('G','Gdata','Gacc'):
        q=scale*out[k];frames['x'][k]=out[k];frames['q'][k]=q;frames['y'][k]=P.T@q
    for k in ('H','Hdata'):
        boundary('report_q_scale');i,j=np.triu_indices(len(scale));q=np.zeros_like(out[k]);v=(scale[i]*out[k][i,j])*scale[j];q[i,j]=v;q[j,i]=v
        frames['x'][k]=out[k];frames['q'][k]=q;frames['y'][k]=symmetric_objective_congruence(q,P,check)
    for k in ('Hacc','Hz','Hg'):
        q=scale[:,None]*out[k]*scale[None,:];frames['x'][k]=out[k];frames['q'][k]=q;frames['y'][k]=P.T@q@P
    for k in ('J','Jdata','Jacc','Jz','Jg'):
        q=out[k]*scale[None,:];frames['x'][k]=out[k];frames['q'][k]=q;frames['y'][k]=q@P
    for k in ('z','g','gp','gpp','vd','r','rdata','racc'):result[k]=out[k]
    vg=np.frombuffer(bytes.fromhex(state['vg_hex']),dtype='<f8');result.update(vg=vg,frames=frames)
    if state['label']=='returned':
        vby=np.frombuffer(bytes.fromhex(state['vby_hex']),dtype='<f8');Cb=(inverse if bound_inverse is None else bound_inverse).T@vby;Cd=frames['q']['Jz'].T@out['vd'];K=(frames['q']['G']+Cd)+Cb
        result.update(vby=vby,complementarity=out['vd']*(out['z']-1e-8))
        if bound_inverse is not None:
            vnew=P.T@Cb;result.update(remapped_multiplier=vnew,remap_back=inverse.T@vnew,bound_transform_inverse_hex=bytes_of(bound_inverse).hex(),remap_role='new-P algebra only; original actual vby and saved bound transform retained')
        for frame in ('x','q','y'):
            for k,v in [('Cb',Cb),('Cd',Cd),('KKT',K)]:frames[frame][k]=v/scale if frame=='x' else v if frame=='q' else P.T@v
            frames[frame]['KKT_inf']=float(np.max(np.abs(frames[frame]['KKT'])))
    else:result.update(vby=None,complementarity=None)
    return result


class Adapter:
    def __init__(self,namespace,state,scale,P,origin,inverse,provider,audit,bound_inverse=None):
        self.input=freeze(state);self.scale=frozen_array(scale);self.P=frozen_array(P);self.origin=frozen_array(origin);self.inverse=frozen_array(inverse);self.provider=provider;self.audit=audit
        qb=bytes.fromhex(state['q_hex']);xb=bytes.fromhex(state['x_hex']);self.ledger=Ledger(namespace+hashlib.sha256(bytes_of(self.P)+bytes_of(self.origin)+bytes_of(self.inverse)+bytes_of(self.scale)+(b'' if bound_inverse is None else bytes_of(bound_inverse))+state['vg_hex'].encode()+str(state['vby_hex']).encode()).hexdigest(),{(qb,xb)})
        self.state=self.ledger.request(np.frombuffer(qb,dtype='<f8'),np.frombuffer(xb,dtype='<f8'),scope=state.get('scope','destination'));self.values=None;self.report_value=None;self.probe=None;self.requests=[];self.public_requests=[]
        self.vg=state['vg_hex'];self.vby=state['vby_hex'];self.bound_inverse=None if bound_inverse is None else frozen_array(bound_inverse)
    def public_probe(self,y):
        if self.probe is None:
            product=self.P@np.asarray(y);q=self.origin+product;x=q*self.scale
            accepted=bytes_of(q).hex()==self.input['q_hex'] and bytes_of(x).hex()==self.input['x_hex']
            self.probe=freeze(dict(transform_hex=bytes_of(self.P).hex(),origin_hex=bytes_of(self.origin).hex(),y_hex=bytes_of(y).hex(),actual_q_hex=bytes_of(q).hex(),actual_x_hex=bytes_of(x).hex(),accepted=accepted,mode='public_y' if accepted else 'canonical_only'))
        elif self.probe['y_hex']!=bytes_of(y).hex():raise ValueError('probe replacement')
        return self.probe
    def request(self,name,public=False,y=None,vg_hex=None,vby_hex=None):
        """Canonical component requests return physical derivatives; R.frames names x/q/y."""
        if (vg_hex is not None and vg_hex!=self.vg) or (vby_hex is not None and vby_hex!=self.vby):raise ValueError('multiplier identity')
        if public:
            if self.probe is None or bytes_of(y).hex()!=self.probe['y_hex'] or bytes_of(self.P).hex()!=self.probe['transform_hex'] or bytes_of(self.origin).hex()!=self.probe['origin_hex'] or not self.probe['accepted']:raise ValueError('public-y bytes rejected before evaluation')
        if name not in ('O','G','H','C','CH','R'):raise ValueError('surface')
        hit=self.values is not None
        if self.values is None:self.values=freeze(self.ledger.enter(self.state,'complete',lambda:self.audit('complete',lambda:self.provider(self.input,self.audit))))
        if name=='R' and self.report_value is None:
            self.report_value=freeze(self.audit('report',lambda:report(self.values,self.input,self.scale,self.P,self.inverse,self.bound_inverse,getattr(self.audit,"check",lambda:None))))
        self.requests.append(dict(name=name,hit=hit,public=public,state=self.state.identity))
        if name=='O':return self.values['F']
        if name=='G':return self.values['G']
        if name=='H':return self.values['H']
        if name=='C':return self.values['g'],self.values['Jg']
        if name=='CH':return self.values['Hg']
        return self.report_value
    def _trace(self,name,y):self.public_requests.append(dict(wrapper=name,coordinate_frame='y',y_hex=bytes_of(y).hex(),probe_accepted=None if self.probe is None else self.probe['accepted'],state=self.state.identity))
    def public_report(self,y):
        self._trace('public_report',y);return self.request('R',True,y)
    def fun(self,y):
        self._trace('fun',y);return self.request('O',True,y)
    def jac(self,y):
        self._trace('jac',y);return self.request('R',True,y)['frames']['y']['G']
    def hess(self,y):
        self._trace('hess',y);return self.request('R',True,y)['frames']['y']['H']
    def constraint(self,y):
        self._trace('constraint',y);r=self.request('R',True,y);return r['g'],r['frames']['y']['Jg']
    def constraint_hessian(self,y,vg):
        self._trace('constraint_hessian',y);return self.request('R',True,y,vg_hex=bytes_of(vg).hex())['frames']['y']['Hg']


class TransformCache:
    def __init__(self):self.value=None;self.requests=0
    def request(self,calculator):
        self.requests+=1
        if self.value is None:self.value=freeze(calculator())
        return self.value


def public_call(adapter,name,y):
    """Actual six solver wrappers, with retained public y-coordinate returns."""
    callbacks={'O':adapter.fun,'G':adapter.jac,'H':adapter.hess,'C':adapter.constraint,'R':adapter.public_report}
    if name=='CH':return adapter.constraint_hessian(y,np.frombuffer(bytes.fromhex(adapter.input['vg_hex']),dtype='<f8'))
    return callbacks[name](y)
