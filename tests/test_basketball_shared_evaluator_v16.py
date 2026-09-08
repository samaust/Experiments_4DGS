#!/usr/bin/env python3
"""The frozen twenty-two Plan023 fixtures. Invocation marker precedes math imports."""
import ast
import json
import os
from pathlib import Path
import sys
import time
import traceback
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import basketball_shared_evaluator_v16 as harness


def main(slot,started,marker_hash):
    if os.environ.get('V16_TOY_TOKEN')!=started['token'] or not (harness.ROOT/f'toy-suite-{slot:02}-worker.json').exists():raise ValueError('direct test rejected before math import')
    owned=harness.read(harness.ROOT/f'toy-suite-{slot:02}-worker.json')['identity']
    if owned['pid']!=os.getpid() or owned['pgid']!=os.getpgrp() or owned['sid']!=os.getsid(0) or os.getppid()!=started['supervisor_pid']:raise ValueError('direct test process identity rejected before math import')
    begin=started['start_monotonic'];end=started['deadline_monotonic']-5;sources=started['source_sha256']
    import numpy as np
    from decimal import Decimal as D
    import decimal
    from fractions import Fraction as F
    import tempfile
    import struct
    from types import SimpleNamespace
    import basketball_acceleration_decimal_v16 as dc
    import basketball_shared_components_v16 as cc
    import basketball_shared_accounting_v16 as ac
    import basketball_shared_reference_v16 as rr
    import basketball_shared_solver_v16 as solver
    for p in harness.SOURCES+[harness.TEST]:compile(p.read_text(),str(p),'exec')
    U=[0.,0.,0.,0.,1.,1.,1.,1.];Q=[0.,.5,1.]
    C4=np.array([[0.,0.,0.],[0.,0.,0.],[0.,0.,0.],[1.,2.,-1.]])
    A=np.array([[6*(1-t),-12+18*t,6-18*t,6*t] for t in Q]);HA=np.kron((2/3)*(A.T@A),np.eye(3))
    records=[];coverage={};counts={};retained={};current=0
    def check():
        if time.monotonic()>=end:raise TimeoutError('toy deadline')
    def mark(name,condition,evidence=None):
        records.append(dict(assertion=name,passed=bool(condition),evidence=harness.plain(evidence)))
        assert condition,name
    def close(a,b):
        if np.shape(b)==() and np.shape(a)!=():b=np.full(np.shape(a),b)
        result=harness.compare_arrays(a,b,1e-12,1e-11,check=check);records.append(dict(assertion=f'{current:02}.array.{len(records)}',**result));assert result['passed'],records[-1]
    def instrument(module,name,key=None):
        original=getattr(module,name);key=key or module.__name__+'.'+name
        def wrapped(*args,**kwargs):
            check();counts[key]=counts.get(key,0)+1
            return original(*args,**kwargs)
        setattr(module,name,wrapped);return original
    for module,names in ((dc,('setup','bundle','mapping')),(rr,('setup','basis','spatial')),(cc,('projection_first','projection_second','robust_residual_jacobian'))):
        for name in names:instrument(module,name)
    instrument(cc.Candidate,'evaluate','Candidate.evaluate');instrument(rr.Reference,'evaluate','Reference.evaluate')
    original_boundary=cc.boundary
    forbidden=set()
    def boundary(name):
        counts['boundary.'+name]=counts.get('boundary.'+name,0)+1
        if name in forbidden:raise AssertionError('forbidden actual boundary '+name)
        return original_boundary(name)
    cc.boundary=boundary
    def other_boundary(prefix):
        def wrapped(name):
            check();key=prefix+'.'+name;counts[key]=counts.get(key,0)+1
            if name in forbidden:raise AssertionError('forbidden actual boundary '+name)
        return wrapped
    ac.boundary=other_boundary('accounting');rr.boundary=other_boundary('reference')
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
        a=ac.Adapter(namespace,state,np.ones(6),P,origin,np.eye(6),provider,audit);return a,counts
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
    def integrated_fixture(weight):
        C=np.array([[0.,0.,4.],[1.,0.,4.],[1.,1.,5.],[2.,1.,6.]])
        scale=np.r_[25.,np.ones(12)];P=np.diag(np.r_[1.,np.full(12,2.)]);P[1:3,1:3]=[[1.25,.75],[.75,1.25]]
        inverse=np.diag(np.r_[1.,np.full(12,.5)]);inverse[1:3,1:3]=[[1.25,-.75],[-.75,1.25]]
        camera1=toy_camera();camera3=toy_camera(.125,[[0.,-1.,0.],[1.,0.,0.],[0.,0.,1.]])
        camera3.update(t=[1.,-1.,2.],K=[[2.,0.,.25],[0.,3.,-.5],[0.,0.,1.]])
        x=np.r_[0.,C.ravel()];y=np.r_[0.,C.ravel()/2];vg=np.arange(1.,13.)/8;vby=np.array([(-1.)**j*(j+1)/16 for j in range(13)])
        state=dict(label='returned',scope='toy-returned',q_hex=harness.fhex(x),x_hex=harness.fhex(x),y_hex=harness.fhex(y),vg_hex=harness.fhex(vg),vby_hex=harness.fhex(vby))
        case=dict(index=weight,id='integrated/'+str(weight),weight=weight,dimension=13,knots_hex=harness.fhex(U),quadrature_hex=harness.fhex(Q),center=[1.,-2.,3.],diameter=2.,n=12,nacc=3,scale_hex=harness.fhex(scale),P_hex=harness.fhex(P.ravel()),origin_hex=harness.fhex(np.zeros(13)),problem=dict(free=[3],offsets={'1':0.,'3':0.},calibration={'1':camera1,'3':camera3},observations=[dict(observations=[dict(camera_id=c,frames=[0,5,10,15,20,25],xy=[[0.,0.] for _ in range(6)]) for c in (1,3)])]))
        return dict(case=case,state=state,C=C,scale=scale,P=P,inverse=inverse,origin=np.zeros(13),y=y,vg=vg,vby=vby)
    def oracle_geometry(fixture):
        case=fixture['case'];C=fixture['C'];m=13;Fdata=0.;G=np.zeros(m);H=np.zeros((m,m));rs=[];Js=[];zs=[];Jzs=[];seconds=[]
        for observation in case['problem']['observations'][0]['observations']:
            camera=observation['camera_id'];cam=case['problem']['calibration'][str(camera)]
            for frame in observation['frames']:
                t=frame/25;B=np.array([(1-t)**3,3*t*(1-t)**2,3*t*t*(1-t),t**3]);Bp=np.array([-3*(1-t)**2,3-12*t+9*t*t,6*t-9*t*t,3*t*t]);Bpp=np.array([6*(1-t),-12+18*t,6-18*t,6*t]);T=np.zeros((3,m));T[:,1:]=np.kron(B.reshape(1,4),np.eye(3));second=np.zeros((3,m,m))
                if camera==3:
                    T[:,0]=-Bp@C/25;second[:,0,0]=Bpp@C/625
                    for axis in range(3):
                        for col in range(4):second[axis,0,1+3*col+axis]=second[axis,1+3*col+axis,0]=-Bp[col]/25
                loss,res,z=rr.spatial(B@C,cam,case['center'],case['diameter'],[0.,0.],12)
                Fdata+=loss.v;G+=loss.g@T;H+=T.T@loss.h@T+np.einsum('k,kij->ij',loss.g,second)
                rs.extend(r.v for r in res);Js.extend(r.g@T for r in res);zs.append(z.v);Jzs.append(z.g@T);seconds.append(T.T@z.h@T+np.einsum('k,kij->ij',z.g,second))
        z=np.asarray(zs);Jz=np.asarray(Jzs);s=z-1e-8;den=np.sqrt(1+s*s);g=s/den;gp=1/den**3;gpp=-3*s/den**5;vd=fixture['vg']*gp;Hz=sum((v*h for v,h in zip(vd,seconds)),np.zeros((m,m)));Hg=Hz+Jz.T@((fixture['vg']*gpp)[:,None]*Jz)
        return dict(Fdata=Fdata,Gdata=G,Hdata=H,rdata=np.asarray(rs),Jdata=np.asarray(Js),z=z,Jz=Jz,g=g,gp=gp,gpp=gpp,vd=vd,Hz=Hz,Hg=Hg,Jg=gp[:,None]*Jz)
    def oracle_full(fixture,geometry):
        w=fixture['case']['weight'];C=fixture['C'];out=dict(geometry);m=13
        if w:
            values=A@C;Facc=float(np.sum(values*values)/3);Gacc=np.r_[0.,((2/3)*(A.T@values)).ravel()];Hacc=np.pad(HA,((1,0),(1,0)));racc=values.ravel()/np.sqrt(3);Jacc=np.pad(np.kron(A,np.eye(3))/np.sqrt(3),((0,0),(1,0)))
        else:Facc=0.;Gacc=np.zeros(m);Hacc=np.zeros((m,m));racc=np.zeros(0);Jacc=np.zeros((0,m))
        out.update(Facc=Facc,Gacc=Gacc,Hacc=Hacc,racc=racc,Jacc=Jacc,F=out['Fdata']+Facc,G=out['Gdata']+Gacc,H=out['Hdata']+Hacc,r=np.r_[out['rdata'],racc],J=np.vstack((out['Jdata'],Jacc)))
        return out
    def oracle_report(out,fixture,P=None,inverse=None,bound_inverse=None):
        P=fixture['P'] if P is None else P;inverse=fixture['inverse'] if inverse is None else inverse;scale=fixture['scale'];frames={}
        for name,M in [('x',np.eye(13)),('q',np.diag(scale)),('y',np.diag(scale)@P)]:
            frames[name]={k:M.T@out[k] for k in ('G','Gdata','Gacc')}
            frames[name].update({k:M.T@out[k]@M for k in ('H','Hdata','Hacc','Hz','Hg')});frames[name].update({k:out[k]@M for k in ('J','Jdata','Jacc','Jz','Jg')})
        Cb=(inverse if bound_inverse is None else bound_inverse).T@fixture['vby'];Cd=frames['q']['Jz'].T@out['vd'];K=(frames['q']['G']+Cd)+Cb
        for name,M in [('x',np.diag(1/scale)),('q',np.eye(13)),('y',P.T)]:
            frames[name].update(Cb=M@Cb,Cd=M@Cd,KKT=M@K,KKT_inf=float(np.max(np.abs(M@K))))
        result={k:out[k] for k in ('F','Fdata','Facc','z','g','gp','gpp','vd','r','rdata','racc')};result.update(frames=frames,vg=fixture['vg'],vby=fixture['vby'],complementarity=out['vd']*(out['z']-1e-8))
        if bound_inverse is not None:result.update(remapped_multiplier=P.T@Cb,remap_back=inverse.T@(P.T@Cb))
        return result
    def assert_report(actual,expected,w):
        spec=harness.comparison_spec(13,12,9 if w else 0,'returned',1)
        for path,rule in spec.items():
            if rule['shape'] is None:assert harness.field(actual,path) is None
            else:close(harness.field(actual,path),harness.field(expected,path))
        return spec
    def audit_for(method,name,fixture,setup):
        audit=harness.Audit(method,end,{},caps={k:200 for k in set(harness.CAPS)|set(harness.REFCAPS)});audit.bind_operands(fixture['case'],setup);audit.context_set(name,fixture['state']);return audit
    def case12():
        assert all(v['passed'] for v in cases),'prior analytic prerequisite failed'
        fixtures={w:integrated_fixture(w) for w in (0,1)};geometry=oracle_geometry(fixtures[0]);csetups={};rsetups={}
        for w in (0,1):csetups[w]=dc.setup(harness.fhex(U),harness.fhex(Q),w,check)
        for w in (0,1):rsetups[w]=rr.setup(harness.fhex(U),harness.fhex(Q),w,check)
        for w in (0,1):
            f=fixtures[w];ca=audit_for('candidate',f'12/{w}',f,csetups[w]);ra=audit_for('reference',f'12/{w}',f,rsetups[w]);model=cc.Candidate(f['case'],csetups[w],check);ref=rr.Reference(f['case'],rsetups[w],check)
            cout=ca('complete',lambda:model.evaluate(f['state'],ca));rout=ra('complete',lambda:ref.evaluate(f['state'],ra));creport=ca('report',lambda:ac.report(cout,f['state'],f['scale'],f['P'],f['inverse']));rreport=ra('report',lambda:rr.report(rout,f['state'],f['scale'],f['P'],f['inverse']))
            expected=oracle_full(f,geometry);expected_report=oracle_report(expected,f)
            for out in (cout,rout):
                for k,v in expected.items():close(out[k],v)
            spec=assert_report(creport,expected_report,w);assert_report(rreport,expected_report,w)
            checks=harness.comparisons(creport,rreport,spec,check);assert all(v['passed'] for v in checks.values())
            retained[w]=dict(fixture=f,csetup=csetups[w],rsetup=rsetups[w],model=model,reference=ref,cout=cout,rout=rout,creport=creport,rreport=rreport,oracle=expected,oracle_report=expected_report,ca=ca,ra=ra,adapters=[],checks=[checks],reports=[creport])
        mark('12.full-components',len(retained)==2,{'candidate_full':2,'reference_full':2,'every_spec_field_and_physical_component_compared':True})
    def case13():
        assert len(retained)==2
        for w,t in retained.items():
            for report in (t['creport'],t['rreport']):assert_report(report,t['oracle_report'],w)
            checks=harness.transform_checks(t['fixture'],1,check);assert all(v['passed'] for v in checks.values())
            assert ac.bytes_of(t['creport']['vg']).hex()==t['fixture']['state']['vg_hex'];assert ac.bytes_of(t['creport']['vby']).hex()==t['fixture']['state']['vby_hex']
        raises(lambda:cc.bounded(np.array([1e200])),FloatingPointError)
        mark('13.depth-forces',True)
    def case14():
        assert len(retained)==2
        for w,t in retained.items():
            f=t['fixture']
            for seq,order in enumerate(harness.ORDERS,1):
                audit=audit_for('candidate',f'14/{w}/{seq}',f,t['csetup']);P=f['P'];inverse=f['inverse'];origin=f['origin'];y=f['y'];bound=None;transform=None
                if seq==5:
                    cold={**f['state'],'label':'cold','scope':'toy-cold','vby_hex':None,'y_hex':None};audit.context_set(f'14/{w}/transform',cold);cache=ac.TransformCache();before=dict(counts)
                    forbidden.update(('projection_second','spline_second','normalized_depth','objective_geometry','HP_pairs','HT_pairs','Hcam_pairs','rig_pairs','spatial_pairs','data_assembly','full_sum','objective_q_to_x','report_q_scale','congruence_validation','congruence_contraction'))
                    try:transform=cache.request(lambda:cc.cold_transform(t['model'],cold,audit))
                    finally:forbidden.clear()
                    def no_transform():raise AssertionError('repeat transform invoked calculator')
                    assert cache.request(no_transform) is transform and cache.requests==2
                    for key in ('projection_second','spline_second','normalized_depth','objective_geometry'):assert counts.get('boundary.'+key,0)==before.get('boundary.'+key,0)
                    assert counts['boundary.svd']==before.get('boundary.svd',0)+1
                    assert counts['boundary.prepare_first']==before.get('boundary.prepare_first',0)+1
                    checks=harness.transform_checks(transform,1,check);assert all(v['passed'] for v in checks.values());close(transform['rank_threshold'],max(24+9*w,12)*np.finfo(float).eps*transform['singular'][0]);active=np.asarray(transform['active'],dtype=bool);close(np.asarray(transform['scales'])[active],np.clip(1/np.asarray(transform['singular'])[active],1e-3,1e3));assert len(transform['singular'])==12 and sum(len(g['indices']) for g in transform['subspaces'])==12
                    P=transform['P'];inverse=transform['inverse'];origin=transform['origin'];y=np.zeros(13);bound=f['inverse'];audit.context_set(f'14/{w}/{seq}',f['state']);t['transform']=transform
                adapter=ac.Adapter(f'14/{w}/{seq}',f['state'],f['scale'],P,origin,inverse,lambda s,a:t['model'].evaluate(s,a),audit,bound)
                assert adapter.public_probe(y)['accepted'];first={};second={}
                before=dict(counts)
                for k in order:first[k]=ac.public_call(adapter,k,y)
                after=dict(counts)
                for k in order:second[k]=ac.public_call(adapter,k,y)
                assert counts==after and harness.operand_digest(first)==harness.operand_digest(second)
                assert counts['Candidate.evaluate']==before.get('Candidate.evaluate',0)+1
                report=adapter.public_report(y);expected=oracle_report(t['oracle'],f,P,inverse,bound);assert_report(report,expected,w)
                expected_returns={'O':expected['F'],'G':expected['frames']['y']['G'],'H':expected['frames']['y']['H'],'C':(expected['g'],expected['frames']['y']['Jg']),'CH':expected['frames']['y']['Hg']}
                for k,v in expected_returns.items():
                    for result in (first,second):
                        if k=='C':close(result[k][0],v[0]);close(result[k][1],v[1])
                        else:close(result[k],v)
                canonical_report=report
                if seq==5:
                    canonical_report=audit('extra_transport',lambda:ac.report(adapter.values,f['state'],f['scale'],f['P'],f['inverse']));t['newreport']=report
                    extra=harness.newp_comparisons(report,t['rreport'],transform,harness.comparison_spec(13,12,9 if w else 0,'returned',1),1,check);assert all(v['passed'] for v in extra.values());t['newchecks']=extra
                    close(report['remapped_multiplier'],expected['remapped_multiplier']);close(report['remap_back'],expected['remap_back'])
                checks=harness.comparisons(canonical_report,t['rreport'],harness.comparison_spec(13,12,9 if w else 0,'returned',1),check);assert all(v['passed'] for v in checks.values());t['checks'].append(checks);t['reports'].append(canonical_report);t['adapters'].append((adapter,audit,y))
        before=dict(counts);raises(lambda:cc.metric_transform(np.zeros((1,12)),0,np.zeros(12)),ValueError);assert counts==before
        mark('14.real-public-transform',True,counts)
    def case15():
        assert all(len(t['adapters'])==5 for t in retained.values())
        before=dict(counts)
        for w,t in retained.items():
            adapter,audit,y=t['adapters'][0];f=t['fixture'];owned=adapter.public_report(y);state=SimpleNamespace(nit=1,v=[f['vg'],f['vby']])
            for mode in ('completed','interrupted','wrong_state','wrong_multiplier'):
                def mock(fun,initial,**kw):
                    close(fun(initial),owned['F']);close(kw['jac'](initial),owned['frames']['y']['G']);close(kw['hess'](initial),owned['frames']['y']['H']);g,Jg=kw['constraint'](initial);close(g,owned['g']);close(Jg,owned['frames']['y']['Jg']);close(kw['constraint_hessian'](initial,f['vg']),owned['frames']['y']['Hg']);kw['callback'](initial,state)
                    if mode=='interrupted':raise RuntimeError('fixed interrupted callback')
                    return SimpleNamespace(x=initial+1 if mode=='wrong_state' else initial,v=[f['vg']+1,f['vby']] if mode=='wrong_multiplier' else state.v)
                result=solver.solve(adapter,mock,y);assert result['report'] is owned and result['callbacks'][0] is owned
                assert result['success']==(mode=='completed');assert (result['error'] is None)==(mode=='completed')
                if mode!='completed':assert result['report_role']=='last valid cached report'
        assert counts==before
        value=dummy_values();state=dict(label='returned',vg_hex=harness.fhex([3.,2.]),vby_hex=harness.fhex([0.]*6));report=ac.report(value,state,np.ones(6),np.eye(6),np.eye(6));assert report['F']==7.;close(report['frames']['x']['G'],np.arange(1.,7.));assert report['F']!=float(value['r']@value['r']);close(report['frames']['q']['KKT'],np.arange(1.,7.)+.7)
        mark('15.solver-report',True)
    def case16():
        adjacent=struct.unpack('<d',bytes.fromhex('010000000000f03f'))[0];ledger=ac.Ledger('byte-toy');states=[ledger.request([v],[v]) for v in (1.,adjacent,0.,-0.)];assert len(ledger.states)==4
        assert ledger.request([1.],[1.],scope='other').identity!=states[0].identity;assert ac.Ledger('other').request([1.],[1.]).identity!=states[0].identity
        raises(lambda:states[0].q.__setitem__(0,2.));raises(lambda:states[0].q.setflags(write=True))
        for w,t in retained.items():
            f=t['fixture'];before_owned=[harness.operand_digest(v) for v in (t['model'].case,t['model'].setup,t['reference'].case,t['reference'].setup)]
            original_case=f['case'];original_setup=t['csetup'];original_reference_setup=t['rsetup']
            original_case['center'][0]=999.;original_setup['samples']=999;original_reference_setup['samples']=999
            assert before_owned==[harness.operand_digest(v) for v in (t['model'].case,t['model'].setup,t['reference'].case,t['reference'].setup)]
            original_case['center'][0]=1.;original_setup['samples']=3;original_reference_setup['samples']=3
            for adapter,audit,y in t['adapters']:
                digest=harness.operand_digest(adapter.public_report(y));input_before=adapter.input['x_hex'];old=f['state']['x_hex'];f['state']['x_hex']='00';assert adapter.input['x_hex']==input_before;f['state']['x_hex']=old
                for a in (adapter.scale,adapter.P,adapter.origin,adapter.inverse,adapter.bound_inverse):
                    if a is not None:raises(lambda a=a:a.setflags(write=True));raises(lambda a=a:a.__setitem__(0,2.))
                assert harness.operand_digest(adapter.public_report(y))==digest
            savedP=f['P'].copy();savedInverse=f['inverse'].copy();savedOrigin=f['origin'].copy();savedScale=f['scale'].copy();f['P'][0,0]=2.;f['inverse'][0,0]=2.;f['origin'][0]=2.;f['scale'][0]=2.
            for adapter,audit,y in t['adapters']:assert adapter.P[0,0]==1. and adapter.inverse[0,0]==1. and adapter.scale[0]==25.
            f['P'][:]=savedP;f['inverse'][:]=savedInverse;f['origin'][:]=savedOrigin;f['scale'][:]=savedScale
            audit=audit_for('candidate',f'16/{w}',f,t['csetup']);adapter=ac.Adapter(f'16/{w}',f['state'],f['scale'],f['P'],f['origin'],f['inverse'],lambda s,a:t['model'].evaluate(s,a),audit);before=counts['Candidate.evaluate'];report=adapter.request('R');after=dict(counts);assert adapter.request('R') is report and counts==after;assert counts['Candidate.evaluate']==before+1;assert adapter.values is not t['adapters'][0][0].values
            assert_report(report,t['oracle_report'],w);checks=harness.comparisons(report,t['rreport'],harness.comparison_spec(13,12,9 if w else 0,'returned',1),check);assert all(v['passed'] for v in checks.values());t['checks'].append(checks);t['reports'].append(report)
            raises(lambda:report['frames']['x']['G'].setflags(write=True));raises(lambda:adapter.input.__setitem__('x_hex','00'))
        mark('16.owned-bytes',True)
    def case17():
        l=ac.Ledger('integer-toy')
        for i in range(200):l.request([float(i)],[float(i)]);l.iteration(i+1)
        raises(lambda:l.request([200.],[200.]));raises(lambda:l.iteration(201));assert len(l.states)==200 and l.iterations==200 and not l.entries
        mark('17.caps',True)
    def case18():
        assert len(retained)==2
        t=retained[0];f=t['fixture']
        for method,model,setup in [('candidate',t['model'],t['csetup']),('reference',t['reference'],t['rsetup'])]:
            audit=audit_for(method,'18/'+method+'/decoder',f,setup);decoder=model.decoder
            def wrong(h):
                result=decoder(h)
                if h==f['state']['x_hex']:result=result.copy();result[-1]+=1.
                return result
            model.decoder=wrong;before=dict(counts)
            try:raises(lambda:audit('complete',lambda:model.evaluate(f['state'],audit)),ValueError)
            finally:model.decoder=decoder
            assert audit.counts['complete']==audit.counts['prepare']==1 and audit.records[-1]['status']=='interrupted';assert counts.get('boundary.prepare_full',0)==before.get('boundary.prepare_full',0)
            audit=audit_for(method,'18/'+method+'/interrupted',f,setup);original=audit.observe
            def interrupt(kind,actual,fn):
                def throwing():raise RuntimeError('actual pre-math preparation interruption')
                return original(kind,actual,throwing if kind=='prepare' else fn)
            audit.observe=interrupt;raises(lambda:audit('complete',lambda:model.evaluate(f['state'],audit)),RuntimeError);assert audit.records[-1]['status']=='interrupted' and 'observed' in audit.records[-1]
            raises(lambda:audit('complete',lambda:None),ValueError)
        for t in retained.values():
            adapter,audit,y=t['adapters'][0];before=dict(counts);raises(lambda:adapter.request('R',vg_hex='00'),ValueError);raises(lambda:adapter.request('R',vby_hex='00'),ValueError);assert before==counts
        l=ac.Ledger('foreign');foreign=ac.Ledger('other').request([0.],[0.]);raises(lambda:l.enter(foreign,'complete',lambda:None),ValueError)
        audit=harness.Audit('candidate',end,{})
        sentinel=lambda:(_ for _ in ()).throw(AssertionError('setup math entered'))
        raises(lambda:harness.setup_entry(audit,'00','00',0,dict(knots_hex='01',quadrature_hex='00',weight=0),sentinel),ValueError);assert not audit.counts
        expected=dict(f['state']);audit.context_set('scope',expected);audit.bind_operands(f['case'],t['csetup'])
        actual=dict(q_hex=expected['q_hex'],x_hex=expected['x_hex'],vg_hex=expected['vg_hex'],vby_hex=expected['vby_hex'],scope='wrong',coefficient_hex=expected['x_hex'][16:],case=f['case'],setup=t['csetup'])
        raises(lambda:audit('prepare',lambda:audit.observe('prepare',actual,sentinel)),ValueError)
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'source';path.write_text('changed');audit=harness.Audit('candidate',end,{str(path):'0'*64});audit.context_set('source',expected);raises(lambda:audit('prepare',sentinel),ValueError);assert not audit.counts
        mark('18.actual-boundary-rejection',True)
    def tiny_report():
        spec=harness.comparison_spec(2,2,0,'returned');report={'frames':{'x':{},'q':{},'y':{}}}
        for path,rule in spec.items():
            shape=rule['shape'];value=np.zeros(shape) if shape else 0.;parts=path.split('.');target=report
            for key in parts[:-1]:target=target[key]
            target[parts[-1]]=value
        report.update(F=1.,Fdata=1.,Facc=0.,z=np.array([1.,2.]),g=np.array([.5,.75]),gp=np.array([.25,.125]),gpp=np.array([-.125,-.0625]),vg=np.array([1.,2.]),vd=np.array([.25,.25]),remapped_multiplier=np.zeros(2),remap_back=np.zeros(2))
        for frame in report['frames'].values():frame['H']=np.eye(2);frame['Hdata']=np.eye(2)
        return report,spec
    def chain_fixture(root):
        plan=root/'plan.md';objective=root/'objective.md';source=root/'source.py';test=root/'test.py'
        for path,value in [(plan,'tiny plan'),(objective,'tiny objective'),(source,'# tiny byte-only source'),(test,'# tiny byte-only assertion source')]:path.write_text(value)
        auth={**harness.read(harness.AUTH),'plan':str(plan),'objective':str(objective),'plan_sha256':harness.sha(plan),'objective_sha256':harness.sha(objective)};authorization=root/'authorization.json';harness.publish(authorization,auth)
        harness.publish(root/'environment.json',{});harness.publish(root/'historical-sources.json',dict(historical={},v11={},pinned={}));harness.publish(root/'input.json',{'original_byte':'00'})
        harness.publish(root/'admission.json',dict(passed=True,admitted_monotonic=auth['t0_monotonic']))
        leaves={str(p):harness.sha(p) for p in [root/'admission.json',root/'environment.json',root/'historical-sources.json',root/'input.json']}
        harness.publish(root/'admission-chain.json',dict(authorization_path=str(authorization),authorization_sha256=harness.sha(authorization),leaves=leaves))
        row=dict(id='tiny-chain',production_calls=['verify_chain'],boundaries=['read bytes'],assertions=['tiny-chain.bytes'])
        harness.publish(root/'readiness-coverage.json',dict(rows=[row]));harness.publish(root/'toy-definitions.json',dict(required_coverage=['tiny-chain']))
        harness.publish(root/'frozen.json',dict(leaves={str(p):harness.sha(p) for p in [root/'readiness-coverage.json',root/'toy-definitions.json']},sources={str(source):harness.sha(source),str(test):harness.sha(test)}))
        harness.publish(root/'toy-suite-01-consumed.json',dict(slot=1));harness.publish(root/'toy-suite-01-result.json',dict(passed=True,slot=1,test_sha256=harness.sha(test),source_sha256={str(source):harness.sha(source),str(test):harness.sha(test)},marker_sha256=harness.sha(root/'toy-suite-01-consumed.json'),coverage={'tiny-chain':dict(passed=True,assertions=['tiny-chain.bytes'])}))
        harness.publish(root/'readiness.json',dict(passed=True,ready_monotonic=auth['t0_monotonic'],authorization_sha256=harness.sha(authorization),leaves={str(p):harness.sha(p) for p in [root/'frozen.json',root/'toy-suite-01-result.json']}))
        return authorization
    def case19():
        import copy
        # These actual byte equality assertions are the tiny chain fixture's claims.
        for variant in ('intact','input','auth','source','coverage'):
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory);authorization=chain_fixture(root)
                if variant=='intact':assert harness.launch_readiness(root,authorization)['passed']
                else:
                    path={'input':root/'input.json','auth':authorization,'source':root/'source.py','coverage':root/'readiness-coverage.json'}[variant]
                    value=harness.read(path) if path.suffix=='.json' else None
                    if variant=='input':value['original_byte']='01'
                    elif variant=='auth':value['scientific_invocations']=2
                    elif variant=='coverage':value['rows']=[]
                    path.write_bytes(harness.encode(value) if value is not None else b'# changed source')
                    raises(lambda:harness.launch_readiness(root,authorization),ValueError)
                assert not (root/'started.json').exists()
        adapter,dummy_counts=dummy_adapter(q=np.ones(6),origin=np.full(6,2.**54));y=np.ones(6)-adapter.origin;probe=adapter.public_probe(y);assert not probe['accepted']
        for name in ('O','G','H','C','CH','R'):raises(lambda name=name:ac.public_call(adapter,name,y),ValueError)
        assert not adapter.ledger.entries and not dummy_counts;adapter.request('O');assert len(adapter.ledger.entries)==1
        base,spec=tiny_report();transform=dict(P=np.eye(2),inverse=np.eye(2),origin=np.zeros(2));outcomes=[]
        for variant in range(1,11):
            candidate=copy.deepcopy(base);reference=copy.deepcopy(base);policy=None
            if variant==2:del candidate['frames']['y']['KKT_inf']
            if variant==3:candidate['frames']['x']['Jg']=np.zeros((2,1))
            if variant==4:candidate['F']=2.
            if variant in (5,6):
                reference['frames']['q']['Hg']=np.eye(2);reference['frames']['y']['Hg']=np.eye(2);candidate['frames']['q']['Hg']=np.eye(2);candidate['frames']['y']['Hg']=np.eye(2)*(1+2.**-15 if variant==5 else 1+3*2.**-16)
            if variant==7:
                for report in (candidate,reference):
                    for frame in ('q','y'):report['frames'][frame]['H'][0,1]=2.**-20
            if variant==8:candidate['frames']['x']['Gacc'][0]=2.**-40
            if variant==9:policy=dict(candidate=2.,reference=1.,atol=0.,rtol=.5)
            if variant==10:policy=dict(candidate=1/3,reference=1/3,atol=0.,rtol=0.,rational=np.array(F(1,3),dtype=object))
            result=harness.newp_comparisons(harness.plain(candidate),harness.plain(reference),transform,spec,0,check,transported=harness.plain(reference) if variant==7 else None) if variant in (5,6,7) else harness.comparisons(harness.plain(candidate),harness.plain(reference),spec,check,policy)
            outcomes.append(result)
            if variant in (1,5):assert all(v['passed'] for v in result.values())
            else:assert any(not v['passed'] for v in result.values())
            if variant==2:assert not result['frames.y.KKT_inf']['complete']
            if variant==3:assert result['frames.x.Jg']['integrity_failure']
            if variant==7:assert not result['frames.y.H/candidate_symmetry']['passed'] and not result['frames.y.H/reference_symmetry']['passed']
            if variant==8:assert not result['frames.x.Gacc/exact_zero']['passed']
        ids=['candidate/cold','candidate/returned','reference/cold','reference/returned','public/one','transform/one'];entries=[];observations=[];hashes={};outputs={'ccold':{'F':1.},'cret':{'F':1.},'rcold':{'F':1.},'rret':{'F':1.},'canonical':{'F':outcomes[0]['F']},'public':{'accepted':True},'transform':{'F':outcomes[0]['F']},'historical':{'F':outcomes[0]['F']}}
        for identity in ids:
            path=identity+'.json';digest=harness.operand_digest({'id':identity});hashes[path]=digest;entries.extend([dict(id=identity,event='entry'),dict(id=identity,event='completed',output_path=path,output_sha256=digest)]);observations.append(dict(id=identity,x_hex='00',scope='fixed'))
        order=harness.ORDERS[0];toy_state=dict(x_hex=harness.fhex([0.,0.]),q_hex=harness.fhex([0.,0.]),vg_hex=harness.fhex([1.,2.]),vby_hex=harness.fhex([0.,0.]),scope='tiny-fixed',label='returned');toy_y=harness.fhex([0.,0.]);names={'O':'fun','G':'jac','H':'hess','C':'constraint','CH':'constraint_hessian','R':'public_report'}
        values=dict(O=base['F'],G=base['frames']['y']['G'],H=base['frames']['y']['H'],C=[base['g'],base['frames']['y']['Jg']],CH=base['frames']['y']['Hg'],R=base)
        outputs['cret']=dict(probe=dict(accepted=True,y_hex=toy_y),public_returns=[values,values],canonical_returns=[],traversal_order=order,canonical_identity=toy_state,owned_state_identity='tiny-owned',cache_repeated_no_entries=True,public_requests=[dict(wrapper=names[k],coordinate_frame='y',y_hex=toy_y,probe_accepted=True,state='tiny-owned') for k in order*2])
        for repeat in (0,1):
            for k,key in [('O','F'),('G','frames.y.G'),('H','frames.y.H'),('CH','frames.y.Hg'),('C/g','g'),('C/Jg','frames.y.Jg')]:outputs['canonical'][f'public/{repeat}/{k}']=outcomes[0][key]
            for key,value in outcomes[0].items():outputs['canonical'][f'public/{repeat}/R/{key}']=value
        hashes.update({k:harness.operand_digest(v) for k,v in outputs.items()});expected=dict(entries=ids,observed=ids,operands={i:dict(x_hex='00',scope='fixed') for i in ids},outputs={k:('schedule' if k in ('ccold','cret','rcold','rret') else 'public_api' if k=='public' else k) for k in outputs},checks={k:['F'] for k in ('canonical','transform','historical')})
        expected['replays']={'cret':dict(order=order,state=toy_state,comparison='canonical',dimension=2,n=2,acc_rows=0,nf=0)}
        retained_package=dict(entries=entries,observed=observations,output_receipts=[dict(path=k,sha256=hashes[k]) for k in outputs],hashes=hashes,outputs=outputs,ready=True,summary_present=True);decisions=[]
        for variant in range(8):
            data=copy.deepcopy(retained_package)
            if variant in (1,6):del data['outputs']['cret'];data['summary_present']=False
            if variant==2:data['entries'].append(dict(id=ids[0],event='entry'))
            if variant==3:
                data['entries']=[v for v in data['entries'] if not (v['id']==ids[0] and v['event']=='completed')];data['entries'].append(dict(id=ids[0],event='interrupted'))
            if variant==4:data['hashes'][ids[0]+'.json']='wrong'
            if variant==5:del data['outputs']['canonical']['public/0/R/frames.y.KKT_inf']
            if variant==6:data['outputs']['canonical']['F']=outcomes[3]['F']
            if variant==7:
                data['outputs']['public']=harness.plain(probe);saved=data['outputs']['cret'];saved.update(probe=harness.plain(probe),public_rejection=True,public_returns=[],canonical_returns=[values,values],public_requests=[adapter.public_requests[0]],requests=[dict(name=k) for k in order*2])
            for key,value in data['outputs'].items():data['hashes'][key]=harness.operand_digest(value)
            data['output_receipts']=[dict(path=k,sha256=data['hashes'][k]) for k in data['outputs']]
            decision=harness.validate_package(expected,data);decisions.append(decision)
            if variant==0:assert decision['status']=='qualified_on_fixed_cohort'
            elif variant in (4,7):assert decision['status']=='rejected'
            else:assert decision['status']=='incomplete'
            if variant==6:assert decision['dimensions']['canonical']['failures'] and not decision['dimensions']['schedule']['complete']
            if variant==7:assert decision['dimensions']['public_api']['failures']
        retained['protocol']=dict(comparisons=outcomes,decisions=decisions)
        mark('19.production-protocol',True)
    def case20():
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory);script=p/'tree.py';script.write_text("import subprocess,signal,sys,time\np=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'])\ndef stop(s,f):\n p.terminate();p.wait();sys.exit(0)\nsignal.signal(signal.SIGTERM,stop)\nprint('partial',flush=True)\ntime.sleep(30)\n")
            for mode in ('deadline','interruption'):
                import threading,signal
                timer=threading.Timer(.2,lambda:os.kill(os.getpid(),signal.SIGTERM)) if mode=='interruption' else None
                start=time.monotonic()
                if timer:timer.start()
                try:result=harness.supervise([sys.executable,str(script)],start+3,p/(mode+'.log'),reserve=2)
                finally:
                    if timer:timer.cancel();timer.join()
                if mode=='interruption':assert 'signal 15' in result['reason']
                assert result['worker_stopped'] and result['within_deadline'] and not result['remaining_live_descendants'];assert 'partial' in (p/(mode+'.log')).read_text();records.append(dict(assertion='20.process.'+mode,passed=True,evidence=result,partial=(p/(mode+'.log')).read_text()))
            marker=p/'marker';raises(lambda:harness.worker_guard(dict(token='a',supervisor_pid=0),'b',0,marker),ValueError);assert not marker.exists();harness.publish(marker,{'first':1});raises(lambda:harness.publish(marker,{'second':2}),FileExistsError);assert harness.read(marker)=={'first':1}
        mark('20.supervisor-guard',True)
    def case21():
        import math
        assert len(retained)==3 and all(v['passed'] for v in cases),'integrated setup prerequisite'
        counts['oracle21.constant']=counts.get('oracle21.constant',0)+1
        xyz=[2.**-21+2.**-62,2.**-22-2.**-63,2.**-8];C=np.tile(xyz,(4,1));m=12
        P=np.diag(np.full(m,2.));P[:2,:2]=[[1.25,.75],[.75,1.25]];inverse=np.diag(np.full(m,.5));inverse[:2,:2]=[[1.25,-.75],[-.75,1.25]]
        xf=[F.from_float(float(v)) for v in C.ravel()];y=np.array([float(sum((F.from_float(float(inverse[i,j]))*xf[j] for j in range(m)),F(0))) for i in range(m)])
        state=dict(label='returned',scope='tiny-centered-returned',q_hex=harness.fhex(C.ravel()),x_hex=harness.fhex(C.ravel()),y_hex=harness.fhex(y),vg_hex=harness.fhex([0.]*3),vby_hex=harness.fhex([0.]*m))
        camera=toy_camera();camera['K']=[[1024.,0.,512.],[0.,1024.,256.],[0.,0.,1.]]
        case=dict(index=21,id='constant-centered',weight=0,dimension=m,knots_hex=harness.fhex(U),quadrature_hex=harness.fhex(Q),center=[0.,0.,0.],diameter=1.,n=3,nacc=3,scale_hex=harness.fhex([1.]*m),P_hex=harness.fhex(P.ravel()),origin_hex=harness.fhex([0.]*m),problem=dict(free=[],offsets={'1':0.},calibration={'1':camera},observations=[dict(observations=[dict(camera_id=1,frames=[0.,12.5,25.],xy=[[512.+1/8,256.+1/16]]*3)])]))
        f=dict(case=case,state=state);t=retained[0];ca=audit_for('candidate','21/candidate',f,t['csetup']);ra=audit_for('reference','21/reference',f,t['rsetup'])
        # The inactive separately owned setup keys are the exact original group12 keys.
        assert t['fixture']['case']['knots_hex']==case['knots_hex'] and t['fixture']['case']['quadrature_hex']==case['quadrature_hex'] and t['fixture']['case']['weight']==0
        model=cc.Candidate(case,t['csetup'],check);ref=rr.Reference(case,t['rsetup'],check)
        cout=ca('complete',lambda:model.evaluate(state,ca));rout=ra('complete',lambda:ref.evaluate(state,ra));creport=ca('report',lambda:ac.report(cout,state,np.ones(m),P,inverse,check=check));rreport=ra('report',lambda:rr.report(rout,state,np.ones(m),P,inverse,check))
        with decimal.localcontext() as ctx:
            ctx.prec=80;ctx.rounding=decimal.ROUND_HALF_EVEN
            def dec(v):return D(v.numerator)/D(v.denominator)
            X,Y,Z=map(F.from_float,xyz);focal=[1024*X/Z,1024*Y/Z];errors=[focal[0]-F(1,8),focal[1]-F(1,16)];assert errors==[F(1,2**44),-F(1,2**45)]
            e=list(map(dec,errors));root=(D(1)+e[0]*e[0]+e[1]*e[1]).sqrt();pg=[2*v/(3*root) for v in e]
            pder=[[F(1024)/Z,F(0),-1024*X/(Z*Z)],[F(0),F(1024)/Z,-1024*Y/(Z*Z)]]
            hp=[[[F(0) for _ in range(3)] for _ in range(3)] for _ in range(2)]
            for axis,coord in enumerate((X,Y)):
                hp[axis][axis][2]=hp[axis][2][axis]=-F(1024)/(Z*Z);hp[axis][2][2]=2048*coord/(Z*Z*Z)
            W=[[D(2)/3*(D(a==b)/root-e[a]*e[b]/root**3) for b in range(2)] for a in range(2)]
            sg=[sum((pg[a]*dec(pder[a][i]) for a in range(2)),D(0)) for i in range(3)]
            curvature=[[sum((dec(pder[a][i])*W[a][b]*dec(pder[b][j]) for a in range(2) for b in range(2)),D(0))+sum((pg[a]*dec(hp[a][i][j]) for a in range(2)),D(0)) for j in range(3)] for i in range(3)]
            loss=float(2*(root-1)/3);q=float(root);weight=math.sqrt(float(2/(root+1)))/math.sqrt(3);derivative=-weight/(4*q*(q+1))
            spatial=np.array(list(map(float,sg)));pfirst=np.array(pder,dtype=float);e64=np.array(list(map(float,errors)));r=e64*weight;rfirst=(weight*np.eye(2)+2*derivative*np.outer(e64,e64))@pfirst
            B=[];Bp=[];Bpp=[]
            for tf in (F(0),F(1,2),F(1)):
                counts['oracle21.bernstein']=counts.get('oracle21.bernstein',0)+1
                B.append([(1-tf)**3,3*tf*(1-tf)**2,3*tf*tf*(1-tf),tf**3]);Bp.append([-3*(1-tf)**2,3-12*tf+9*tf*tf,6*tf-9*tf*tf,3*tf*tf]);Bpp.append([6*(1-tf),-12+18*tf,6-18*tf,6*tf])
            G=np.zeros(m);H=np.zeros((m,m));J=[];Jz=[]
            for i in range(m):
                G[i]=float(sum((sg[i%3]*dec(row[i//3]) for row in B),D(0)))
                for j in range(m):H[i,j]=float(sum((curvature[i%3][j%3]*dec(row[i//3])*dec(row[j//3]) for row in B),D(0)))
            for row in B:
                T=np.kron(np.asarray(row,dtype=float).reshape(1,4),np.eye(3));J.extend(rfirst@T);Jz.append(np.array([0.,0.,1.])@T)
        counts['oracle21.full_report']=counts.get('oracle21.full_report',0)+1
        z=np.full(3,float(Z));delta=float(Z)-1e-8;hyp=math.hypot(1.,delta);inv=1/hyp;g=delta*inv;gp=inv*inv*inv;gpp=-3*g*inv*inv*inv*inv;Jz=np.array(Jz);J=np.array(J);rv=np.tile(r,3);zeros=np.zeros((m,m))
        oracle=dict(F=3*loss,Fdata=3*loss,Facc=0.,G=G,Gdata=G,Gacc=np.zeros(m),H=H,Hdata=H,Hacc=zeros,r=rv,rdata=rv,racc=np.zeros(0),J=J,Jdata=J,Jacc=np.zeros((0,m)),z=z,Jz=Jz,g=np.full(3,g),gp=np.full(3,gp),gpp=np.full(3,gpp),vd=np.zeros(3),Hz=zeros,Hg=zeros,Jg=gp*Jz)
        def exact_transport(H,M):
            result=np.zeros((m,m))
            for i in range(m):
                check()
                for j in range(m):result[i,j]=float(sum((F.from_float(float(M[a,i]))*F.from_float(float(H[a,b]))*F.from_float(float(M[b,j])) for a in range(m) for b in range(m) if M[a,i] and H[a,b] and M[b,j]),F(0)))
            return result
        frames={}
        for name,M in [('x',np.eye(m)),('q',np.eye(m)),('y',P)]:
            frame={k:M.T@oracle[k] for k in ('G','Gdata','Gacc')};frame.update({k:exact_transport(oracle[k],M) for k in ('H','Hdata','Hacc','Hz','Hg')});frame.update({k:oracle[k]@M for k in ('J','Jdata','Jacc','Jz','Jg')});frame.update(Cd=np.zeros(m),Cb=np.zeros(m),KKT=M.T@G,KKT_inf=float(np.max(np.abs(M.T@G))));frames[name]=frame
        expected={k:oracle[k] for k in ('F','Fdata','Facc','z','g','gp','gpp','vd','r','rdata','racc')};expected.update(vg=np.zeros(3),vby=np.zeros(m),complementarity=np.zeros(3),frames=frames)
        for actual in (cout,rout):
            for k,v in oracle.items():close(actual[k],v)
            for k in ('H','Hdata'):mark('21.physical-symmetry.'+('candidate' if actual is cout else 'reference')+'.'+k,ac.bytes_of(actual[k])==ac.bytes_of(actual[k].T))
        spec=harness.comparison_spec(m,3,0,'returned')
        for label,report in [('candidate',creport),('reference',rreport)]:
            for path,rule in spec.items():close(harness.field(report,path),harness.field(expected,path))
            for frame in ('x','q','y'):
                for k in ('H','Hdata'):mark('21.report-symmetry.'+label+'.'+frame+'.'+k,ac.bytes_of(report['frames'][frame][k])==ac.bytes_of(report['frames'][frame][k].T))
        crow=next(v for v in ca.records if v['kind']=='prepare')
        # Actual prepare bytes are retained by Audit in science; here recover the already
        # consumed rows through its observer, never call prepare again.
        consumed_candidate=cout['consumed_observations'];consumed_reference=rout['consumed_observations']
        for label,observations in [('candidate',consumed_candidate),('reference',consumed_reference)]:
            mark('21.exact-errors.'+label,all(np.array_equal(v['e'],e64) for v in observations),observations)
            for row in observations:close(row['spatial'],spatial)
        close(P@inverse,np.eye(m));close(inverse@P,np.eye(m))
        counts['oracle21.production_comparison']=counts.get('oracle21.production_comparison',0)+1
        comparisons=harness.comparisons(creport,rreport,spec,check);assert all(v['passed'] for v in comparisons.values())
        retained['centered']=dict(case=case,state=state,candidate=creport,reference=rreport,oracle=expected,oracle_errors=e64,oracle_focal=list(map(float,focal)),B=B,Bp=Bp,Bpp=Bpp,consumed_candidate=consumed_candidate,consumed_reference=consumed_reference,checks=comparisons)
        mark('21.centered-full-oracle',True)
    def case22():
        H=np.array([[2.**40,2.**20,-2.**18],[2.**20,3.,-1.],[-2.**18,-1.,2.]]);P=np.array([[1.,.5,0.],[.5,2.,.25],[0.,.25,1.]])
        candidate=ac.symmetric_objective_congruence(H,P,check);reference=rr.symmetric_objective_congruence(H,P,check);oracle=np.zeros((3,3));exact=[]
        for i in range(3):
            for j in range(3):
                value=F(0)
                for a in range(3):
                    for b in range(3):
                        counts['oracle22.fraction_term']=counts.get('oracle22.fraction_term',0)+1;value+=F.from_float(float(P[a,i]))*F.from_float(float(H[a,b]))*F.from_float(float(P[b,j]))
                oracle[i,j]=float(value);exact.append([str(value.numerator),str(value.denominator)])
        for name,result in [('candidate',candidate),('reference',reference)]:
            mark('22.exact-congruence.'+name,np.array_equal(result,oracle));mark('22.exact-symmetry.'+name,ac.bytes_of(result)==ac.bytes_of(result.T))
        bad=H.copy();bad[0,1]+=1.
        for name,module in [('candidate',ac),('reference',rr)]:
            prefix='accounting' if name=='candidate' else 'reference';before=counts[prefix+'.congruence_contraction'];raises(lambda:module.symmetric_objective_congruence(bad,P,check),ValueError);mark('22.input-rejected.'+name,counts[prefix+'.congruence_contraction']==before)
        retained['congruence']=dict(H=H,P=P,candidate=candidate,reference=reference,oracle=oracle,exact=exact)
        mark('22.dyadic-input-contract',True)
    cases=[]
    for i in range(1,23):
        current=i;start=time.monotonic();record_start=len(records)
        try:
            check();locals()['case'+str(i)]()
            if i<=11:mark(f'{i:02}.analytic-kernel',True)
            case=dict(case=i,passed=True)
        except BaseException as exc:case=dict(case=i,passed=False,error=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc())
        case['elapsed_seconds']=time.monotonic()-start;case['assertion_records']=records[record_start:];cases.append(case);print(json.dumps({k:v for k,v in case.items() if k!='assertion_records'}),flush=True)
        stable=[r['assertion'] for r in records[record_start:] if '.array.' not in r['assertion'] and '.process.' not in r['assertion']]
        coverage[f'{i:02}']=dict(passed=case['passed'],assertions=stable,observed_boundaries=dict(counts))
    expected_counts=harness.read(harness.ROOT/'arithmetic-contract.json')['toy_inner_counts']
    inventory_passed=counts==expected_counts;finish=time.monotonic()
    result=dict(slot=slot,source_sha256=sources,test_sha256=harness.sha(harness.TEST),marker_sha256=marker_hash,cases=cases,coverage=coverage,counts=counts,expected_counts=expected_counts,inventory_passed=inventory_passed,passed=all(c['passed'] for c in cases) and inventory_passed,start_monotonic=begin,end_monotonic=finish,elapsed_seconds=finish-begin,scientific_entries=0)
    harness.publish(harness.ROOT/f'toy-suite-{slot:02}-result.json',result)
    harness.publish(harness.ROOT/f'toy-suite-{slot:02}-protocol.json.gz',{key:retained[key] for key in ('protocol','centered','congruence') if key in retained})
    print(json.dumps(dict(passed=result['passed'],inventory_passed=inventory_passed,counts=counts,expected=expected_counts)),flush=True)
    return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit('direct test entry rejected before numerical imports; use supervised harness toy')
