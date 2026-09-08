#!/usr/bin/env python3
"""The frozen twenty Plan021 fixtures. Invocation marker precedes math imports."""
import ast
import json
import os
from pathlib import Path
import sys
import time
import traceback
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import basketball_shared_evaluator_v14 as harness


def main():
    harness.deadline('readiness');slot=next((i for i in (1,2) if not (harness.ROOT/f'toy-suite-{i:02}-consumed.json').exists()),None)
    if slot is None:raise ValueError('both toy suites consumed')
    begin=time.monotonic();sources={str(p):harness.sha(p) for p in harness.SOURCES+[harness.TEST]}
    harness.publish(harness.ROOT/f'toy-suite-{slot:02}-consumed.json',dict(slot=slot,start_monotonic=begin,source_sha256=sources,definition='Plan021 section7 fixed20'))
    import numpy as np
    from decimal import Decimal as D
    import decimal
    from fractions import Fraction as F
    import tempfile
    import struct
    from types import SimpleNamespace
    import basketball_acceleration_decimal_v14 as dc
    import basketball_shared_components_v14 as cc
    import basketball_shared_accounting_v14 as ac
    import basketball_shared_reference_v14 as rr
    import basketball_shared_solver_v14 as solver
    for p in harness.SOURCES+[harness.TEST]:compile(p.read_text(),str(p),'exec')
    U=[0.,0.,0.,0.,1.,1.,1.,1.];Q=[0.,.5,1.]
    C4=np.array([[0.,0.,0.],[0.,0.,0.],[0.,0.,0.],[1.,2.,-1.]])
    A=np.array([[6*(1-t),-12+18*t,6-18*t,6*t] for t in Q]);HA=np.kron((2/3)*(A.T@A),np.eye(3))
    def close(a,b):np.testing.assert_allclose(a,b,atol=1e-12,rtol=1e-11)
    def raises(fn,error=Exception):
        try:fn()
        except error:return
        raise AssertionError('expected rejection')
    def acceleration(C,U=U,Q=Q,w=1):
        s=dc.setup(harness.fhex(U),harness.fhex(Q),w);return s,dc.bundle(s,harness.fhex(np.asarray(C).ravel()))
    def analytic(C):
        acceleration_values=A@C;return np.sum(acceleration_values**2)/3,(2/3*A.T@acceleration_values).ravel()
    def dummy_values():
        m=6;return dict(F=7.,Fdata=5.,Facc=2.,G=np.arange(1.,7.),Gdata=np.arange(1.,7.),Gacc=np.zeros(m),H=np.eye(m),Hdata=np.eye(m),Hacc=np.zeros((m,m)),Hz=np.zeros((m,m)),Hg=np.eye(m),J=np.ones((2,m)),Jdata=np.ones((2,m)),Jacc=np.zeros((0,m)),Jz=np.ones((2,m)),Jg=np.ones((2,m)),z=np.array([2.,3.]),g=np.array([.8,.9]),gp=np.array([.1,.2]),gpp=np.array([-.1,-.1]),vd=np.array([.3,.4]),r=np.array([100.,100.]),rdata=np.array([100.,100.]),racc=np.zeros(0))
    def dummy_adapter(namespace='toy',q=None,P=None,origin=None):
        q=np.zeros(6) if q is None else np.asarray(q);P=np.eye(6) if P is None else P;origin=np.zeros(6) if origin is None else origin
        state=dict(label='returned',q_hex=harness.fhex(q),x_hex=harness.fhex(q),vg_hex=harness.fhex([3.,2.]),vby_hex=harness.fhex([0.]*6),y_hex=harness.fhex(q));counts={}
        def audit(k,fn):counts[k]=counts.get(k,0)+1;return fn()
        def provider(s,audit):
            for k in ('O','G','H','C','CH'):audit(k,lambda:None)
            return dummy_values()
        a=ac.Adapter(namespace,state,np.ones(6),P,origin,np.linalg.inv(P),provider,audit);return a,counts
    def case1():
        C=np.full((4,3),7.);s,v=acceleration(C);assert v['F']==0 and np.count_nonzero(v['G'])==0;close(v['H'],HA);close(np.asarray(v['H'])@np.ones(12),0)
    def case2():
        x=np.arange(4.);C=np.column_stack((x,2*x,-x));s,v=acceleration(C);assert v['F']==0 and np.count_nonzero(v['G'])==0
        for axis in range(3):
            mode=np.zeros((4,3));mode[:,axis]=x;close(np.asarray(v['H'])@mode.ravel(),0);mode[:,axis]=1;close(np.asarray(v['H'])@mode.ravel(),0)
    def case3():
        C=np.zeros((4,3));C[:,0]=[0,0,1,3];s,v=acceleration(C);assert v['F']==36;close(v['G'],analytic(C)[1]);close(v['H'],HA)
    def case4():
        s,v=acceleration(C4);f,g=analytic(C4);close(v['F'],f);close(v['G'],g);close(v['H'],HA);close(v['r'],(A@C4).ravel()/np.sqrt(3));close(v['J'],np.kron(A,np.eye(3))/np.sqrt(3))
    def case5():
        x=np.arange(4.);C=np.column_stack((x,2*x,-x))+2.**40;h=harness.fhex(C.ravel());s,v=acceleration(C);assert h==harness.fhex(C.ravel());assert v['F']==0 and np.count_nonzero(v['G'])==0
    def case6():
        U=[0.]*4+list(map(float,range(1,15)))+[15.]*4;Q=[0.,.5,7.,14.5,15.];C=np.zeros((18,3));C[:,0]=[sum(U[i+1:i+4])/3 for i in range(18)];C[:,1]=7;C[:,2]=-7
        s,v=acceleration(C,U,Q);assert len(v['G'])==54 and np.shape(v['H'])==(54,54);close(v['F'],0);close(v['G'],0)
        for t,L in zip(Q,s['L']):
            exact=rr.basis([F.from_float(x) for x in U],F.from_float(t),2)
            with decimal.localcontext(dc.context()):
                for a,b in zip(L,exact):assert abs(a-D(b.numerator)/D(b.denominator))<D('1e-65')
    def case7():
        U=[0.,0.,0.,0.,1.,2.,2.,2.,2.];C=np.zeros((5,3));C[:,0]=[0,1,3,5,6];s,v=acceleration(C,U,[0.,.5,1.,1.5,2.]);close(v['F'],0);close(v['G'],0)
        assert rr.basis(U,0.)==[1.,0.,0.,0.,0.] and rr.basis(U,2.)==[0.,0.,0.,0.,1.]
        U2=[0.,0.,0.,0.,1.,1.,2.,2.,2.,2.];s,v=acceleration(np.zeros((6,3)),U2,[0.,.5,1.,1.5,2.]);assert [x[0] for x in s['spans']]==[1,1,3,3,3]
        raises(lambda:dc.setup(harness.fhex(U),harness.fhex([-1.]),1));raises(lambda:dc.setup(harness.fhex([0.]*8),harness.fhex([0.]),1))
    def case8():
        original=dc.mapping
        def sentinel(*a):raise AssertionError('inactive map entered')
        dc.mapping=sentinel
        try:s,v=acceleration(C4,w=0)
        finally:dc.mapping=original
        assert v['F']==0 and np.count_nonzero(v['G'])==np.count_nonzero(v['H'])==0 and v['r']==v['J']==[]
    def case9():
        _,base=acceleration(C4);before=decimal.getcontext().copy()
        with decimal.localcontext() as ambient:
            ambient.prec=7;ambient.rounding=decimal.ROUND_UP;ambient.traps[decimal.Inexact]=True
            _,v=acceleration(C4);assert harness.encode(v)==harness.encode(base);assert ambient.prec==7 and ambient.traps[decimal.Inexact]
            decoded=dc.decode(harness.fhex([.1,-0.]),2);assert decoded[0]==D.from_float(.1) and decoded[1].is_signed()
        assert decimal.getcontext()==before or decimal.getcontext().prec==before.prec
        for d in (D('NaN'),D('Infinity'),D('1e400'),D('1e-400')):raises(lambda d=d:dc.output(d))
        raises(lambda:dc.decode(harness.fhex([float('nan')]),1));raises(lambda:dc.decode('00',1))
    def case10():
        X,Y,Z=[rr.Jet.variable(v,i) for i,v in enumerate((1.,2.,3.))];f=X*Y+Z*Z;assert f.v==11.;close(f.g,[2,1,6]);close(f.h,[[0,1,0],[1,0,0],[0,0,2]])
        inv=(1+X).reciprocal();close(inv.g,[-.25,0,0]);close(inv.h,np.diag([.25,0,0]));root=(1+X).sqrt();close(root.g,[1/(2*np.sqrt(2)),0,0]);close(root.h,np.diag([-1/(4*2**1.5),0,0]))
    def toy_camera(k=0.,rotation=None):return dict(R=np.eye(3).tolist() if rotation is None else rotation,t=[0.,0.,0.],K=np.eye(3).tolist(),parameters_colmap=[1.,0.,0.,k])
    def case11():
        xyz=np.array([[1.,2.,4.]])
        for cam in (toy_camera(),toy_camera(.125,[[0.,-1.,0.],[1.,0.,0.],[0.,0.,1.]])):
            pred,P,H=cc.projection_second(xyz,cam,np.zeros(3),1.);e=pred;s=np.sqrt(1+np.sum(e*e));b=2*e[0]/s;W=2*(np.eye(2)/s-np.outer(e[0],e[0])/s**3);grad=b@P[0];hess=P[0].T@W@P[0]+np.einsum('a,aij->ij',b,H[0]);loss,res,z=rr.spatial(xyz[0],cam,[0.,0.,0.],1.,[0.,0.],1)
            close(loss.v,2*(s-1));close(loss.g,grad);close(loss.h,hess)
            r,j=cc.robust_residual_jacobian(e,1);close([a.v for a in res],r[0]);close(np.array([a.g for a in res]),j[0]@P[0])
        cam=toy_camera();pred,P,H=cc.projection_second(xyz,cam,np.zeros(3),1.);close(pred,[[.25,.5]]);close(P[0],[[.25,0,-1/16],[0,.25,-1/8]])
    def case12():
        t=.5;B=np.array(rr.basis(U,t));Bp=np.array(rr.basis(U,t,1));Bpp=np.array(rr.basis(U,t,2));close(B,[.125,.375,.375,.125]);close(-Bp@C4/25,[-.03,-.06,.03]);close(Bpp@C4/625,[.0048,.0096,-.0048])
        scale=np.r_[25.,np.ones(12)];T=np.zeros((3,13));T[:,0]=-Bp@C4/25;T[:,1:]=np.kron(B.reshape(1,-1),np.eye(3));P=np.diag(np.arange(2.,15.));close((T*scale)[:,0],-Bp@C4);close(((T*scale)@P)[:,0],-2*Bp@C4)
        mixed=-Bp/25;close(mixed*25,-Bp);close(mixed*25*P[0,0],-2*Bp)
    def case13():
        z=np.array([8.]);J=np.array([[2.,5.]]);Hz=np.array([[0.,1.],[1.,2.]]);vg=np.array([3.]);g,gp,gpp=cc.bounded(z);s=8-1e-8;close(g,[s/np.sqrt(1+s*s)]);close(gp,[(1+s*s)**-1.5]);close(gpp,[-3*s*(1+s*s)**-2.5]);vd=vg*gp;H=vd[0]*Hz+J.T@((vg*gpp)[:,None]*J);close(H,3*gp[0]*Hz+3*gpp[0]*np.outer(J[0],J[0]));close(vd*(z-1e-8),3*gp*s);raises(lambda:cc.bounded(np.array([1e200])),FloatingPointError)
    def case14():
        results=[]
        for seq,order in enumerate(harness.ORDERS):
            a,counts=dummy_adapter(str(seq));a.public_probe(np.zeros(6))
            if seq==4:counts['T']=1
            first=[harness.encode(harness.plain(a.request(k))) for k in order];second=[harness.encode(harness.plain(a.request(k))) for k in order];assert first==second and all(v==1 for v in counts.values());results.append(harness.encode(harness.plain(a.request('R'))))
        assert len(set(results))==1
    def case15():
        a,counts=dummy_adapter();a.public_probe(np.zeros(6));state=SimpleNamespace(nit=1,v=[np.array([3.,2.]),np.zeros(6)])
        def mock(fun,y,**kw):kw['callback'](y,state);return SimpleNamespace(x=y,v=state.v)
        v=solver.solve(a,mock,np.zeros(6));assert v['report']['F']==7 and v['callbacks'][0] is v['report'];assert len(a.ledger.entries)==1
        def interrupted(fun,y,**kw):kw['callback'](y,state);raise RuntimeError('toy interrupted')
        w=solver.solve(a,interrupted,np.zeros(6));assert w['report'] is v['report'] and w['interrupted'];close(w['report']['frames']['q']['KKT'],np.arange(1.,7.)+.7)
        def wrong(fun,y,**kw):return SimpleNamespace(x=y,v=[np.array([4.,2.]),np.zeros(6)])
        assert 'multiplier ownership' in solver.solve(a,wrong,np.zeros(6))['error']
    def case16():
        adjacent=struct.unpack('<d',bytes.fromhex('010000000000f03f'))[0];l=ac.Ledger('toy')
        s=[l.request([v],[v]) for v in (1.,adjacent,0.,-0.)];assert len(l.states)==4;s2=l.request([1.],[1.],scope='other');assert s2.identity!=s[0].identity
        assert ac.Ledger('other').request([1.],[1.]).identity!=s[0].identity;raises(lambda:s[0].q.__setitem__(0,2.));raises(lambda:s[0].q.setflags(write=True))
        a,_=dummy_adapter();v=a.request('R');raises(lambda:v.__setitem__('F',0));raises(lambda:v['frames']['x']['G'].__setitem__(0,0))
    def case17():
        l=ac.Ledger('integer-toy')
        for i in range(200):l.request([float(i)],[float(i)]);l.iteration(i+1)
        raises(lambda:l.request([200.],[200.]));raises(lambda:l.iteration(201));assert len(l.states)==200 and l.iterations==200 and not l.entries
    def case18():
        l=ac.Ledger('throws');s=l.request([0.],[0.])
        def fail():raise RuntimeError('entered toy calculator')
        raises(lambda:l.enter(s,'O',fail));assert len(l.entries)==1 and l.entries[0]['status']=='interrupted';raises(lambda:l.enter(s,'O',lambda:1))
        a,_=dummy_adapter();raises(lambda:a.request('R',vg_hex=harness.fhex([2.,3.])));assert not a.ledger.entries
        audit=harness.Audit('candidate',time.monotonic()+10,{});audit.context_set('toy',dict(q_hex='00',x_hex='00',vg_hex='00',vby_hex=None))
        raises(lambda:audit('prepare',lambda:audit.observe('prepare',dict(q_hex='01',x_hex='00',vg_hex='00',vby_hex=None),lambda:1)))
        assert audit.counts['prepare']==1 and audit.records[-1]['status']=='interrupted'
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'source';p.write_text('new');raises(lambda:harness.hashes({str(p):'0'*64}))
    def case19():
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'marker';raises(lambda:harness.worker_guard(dict(token='a',supervisor_pid=0),'b',0,p));assert not p.exists();harness.publish(p,{'first':1});raises(lambda:harness.publish(p,{'second':2}));assert harness.read(p)=={'first':1}
        a,_=dummy_adapter(q=np.ones(6));assert a.public_probe(np.ones(6))['accepted'];a.request('O',True,np.ones(6))
        # Large origin destroys a tiny exact retained coordinate on forward replay.
        b,_=dummy_adapter(q=np.ones(6),origin=np.full(6,2.**54));y=np.ones(6)-b.origin;probe=b.public_probe(y);assert not probe['accepted'];raises(lambda:b.request('O',True,y));assert not b.ledger.entries;b.request('O');assert len(b.ledger.entries)==1 and probe['mode']=='canonical_only'
    def case20():
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);script=p/'tree.py';script.write_text("import subprocess,signal,sys,time\np=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'])\ndef stop(s,f):\n p.terminate();p.wait();sys.exit(0)\nsignal.signal(signal.SIGTERM,stop)\nprint('partial',flush=True)\ntime.sleep(30)\n")
            for mode in ('deadline','interruption'):
                start=time.monotonic();result=harness.supervise([sys.executable,str(script)],start+3,p/(mode+'.log'),interrupt_after=.2 if mode=='interruption' else None,reserve=2)
                assert result['worker_stopped'] and result['within_deadline'] and not result['remaining_live_descendants'];assert 'partial' in (p/(mode+'.log')).read_text()
    cases=[]
    for i in range(1,21):
        start=time.monotonic()
        try:locals()['case'+str(i)]();case=dict(case=i,passed=True)
        except BaseException as exc:case=dict(case=i,passed=False,error=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc())
        case['elapsed_seconds']=time.monotonic()-start;cases.append(case);print(json.dumps(case),flush=True)
    end=time.monotonic();result=dict(slot=slot,source_sha256=sources,cases=cases,passed=all(c['passed'] for c in cases),start_monotonic=begin,end_monotonic=end,elapsed_seconds=end-begin,scientific_entries=0)
    harness.publish(harness.ROOT/f'toy-suite-{slot:02}-result.json',result)
    return 0 if result['passed'] else 1

if __name__=='__main__':sys.exit(main())
