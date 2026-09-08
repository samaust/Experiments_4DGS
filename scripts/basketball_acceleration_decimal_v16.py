"""Full fixed Decimal80 control-difference acceleration; v13 context/map."""
import decimal as dec

from decimal import Decimal as D

import hashlib

import math

import struct

def context():
    return dec.Context(prec=80,rounding=dec.ROUND_HALF_EVEN,Emin=-999999,Emax=999999,
                       capitals=1,clamp=0,flags=[],traps=[dec.InvalidOperation,
                       dec.DivisionByZero,dec.Overflow,dec.Underflow,dec.FloatOperation])

def metadata(ctx):
    return dict(prec=ctx.prec,rounding=ctx.rounding,Emin=ctx.Emin,Emax=ctx.Emax,
                capitals=ctx.capitals,clamp=ctx.clamp,
                traps={k.__name__:v for k,v in ctx.traps.items()},
                flags={k.__name__:v for k,v in ctx.flags.items()})

def decode(h,count,digest=None):
    raw=bytes.fromhex(h)
    if len(raw)!=8*count or (digest is not None and hashlib.sha256(raw).hexdigest()!=digest):
        raise ValueError('input size/hash')
    vals=struct.unpack('<'+str(count)+'d',raw)
    if not all(map(math.isfinite,vals)):raise ValueError('nonfinite input')
    return [D.from_float(x) for x in vals]

def output(v):
    if not isinstance(v,D) or not v.is_finite():raise ValueError('invalid Decimal')
    x=float(v)
    if not math.isfinite(x) or (v!=0 and x==0):raise FloatingPointError('binary64 overflow/underflow')
    return x


def mapping(s,C):
    n=s['n'];a=s['alpha'];b=s['beta']
    first=[a[i]*(C[i+1]-C[i]) for i in range(n-1)]
    second=[b[i]*(first[i+1]-first[i]) for i in range(n-2)]
    return [l*second[j-1]+t*second[j] for j,l,t in s['spans']]


def setup(knots_hex,quadrature_hex,weight=1,check=lambda:None):
    with dec.localcontext(context()) as ctx:
        U=decode(knots_hex,len(bytes.fromhex(knots_hex))//8);Q=decode(quadrature_hex,len(bytes.fromhex(quadrature_hex))//8);n=len(U)-4
        if n<4 or not Q or type(weight) is not int or weight not in (0,1):raise ValueError('shape/weight')
        if any(a>b for a,b in zip(U,U[1:])) or any(a>b for a,b in zip(Q,Q[1:])):raise ValueError('order')
        if any(not U[3]<=q<=U[n] for q in Q):raise ValueError('domain')
        s=dict(n=n,active=bool(weight),samples=len(Q),scale=D(weight)/D(len(Q)),context=metadata(ctx))
        if not weight:return s
        da=[U[i+4]-U[i+1] for i in range(n-1)];db=[U[i+4]-U[i+2] for i in range(n-2)]
        if min(da+db)<=0:raise ValueError('denominator')
        s.update(alpha=[D(3)/d for d in da],beta=[D(2)/d for d in db]);W=U[2:-2];spans=[]
        for q in Q:
            check();ids=[j for j in range(1,n-2) if W[j]<W[j+1] and (W[j]<=q<W[j+1] if q!=U[n] else W[j+1]==q)]
            if len(ids)!=1:raise ValueError('span')
            j=ids[0];theta=(q-W[j])/(W[j+1]-W[j]);spans.append((j,D(1)-theta,theta))
        s['spans']=spans;L=[[D(0)]*n for _ in Q]
        for j in range(n):
            check();unit=[D(0)]*n;unit[j]=D(1)
            for k,v in enumerate(mapping(s,unit)):L[k][j]=v
        H=[[D(0)]*n for _ in range(n)]
        for row in L:
            check()
            for i in range(n):
                for j in range(n):H[i][j]+=D(2)*s['scale']*(row[i]*row[j])
        s.update(L=L,H=H,Hfloat=tuple(tuple(output(v) for v in row) for row in H),sqrt_scale=s['scale'].sqrt(),context=metadata(ctx))
        return s


def bundle(s,coefficient_hex,check=lambda:None,residual_only=False):
    with dec.localcontext(context()) as ctx:
        n=s['n'];values=decode(coefficient_hex,3*n)
        if not s['active']:return dict(F=0.,G=[0.]*(3*n),H=[[0.]*(3*n) for _ in range(3*n)],r=[],J=[],context=metadata(ctx))
        C=[values[i:i+3] for i in range(0,len(values),3)];a=s['alpha'];b=s['beta']
        first=[[a[i]*(C[i+1][k]-C[i][k]) for k in range(3)] for i in range(n-1)]
        second=[[b[i]*(first[i+1][k]-first[i][k]) for k in range(3)] for i in range(n-2)]
        F=D(0);G=[D(0)]*(3*n);rs=[];js=[]
        for sample,(j,l,t) in enumerate(s['spans']):
            check()
            for axis in range(3):
                acc=l*second[j-1][axis]+t*second[j][axis]
                if not residual_only:F+=acc*acc
                h=D(0) if residual_only else D(2)*s['scale']*acc
                if not residual_only:
                    adj={i:D(0) for i in (j-1,j,j+1)}
                    for k,e in ((j-1,l*h),(j,t*h)):
                        v=b[k]*e;adj[k]-=v;adj[k+1]+=v
                    gc=[D(0)]*n
                    for k in sorted(adj):v=a[k]*adj[k];gc[k]-=v;gc[k+1]+=v
                    for k in range(n):G[3*k+axis]+=gc[k]
                rs.append(output(s['sqrt_scale']*acc));jr=[0.]*(3*n)
                for k in range(n):jr[3*k+axis]=output(s['sqrt_scale']*s['L'][sample][k])
                js.append(jr)
        if residual_only:return dict(r=rs,J=js,context=metadata(ctx))
        H=[[0.]*(3*n) for _ in range(3*n)]
        for i in range(n):
            for j in range(n):
                v=s['Hfloat'][i][j]
                for axis in range(3):H[3*i+axis][3*j+axis]=v
        return dict(F=output(s['scale']*F),G=list(map(output,G)),H=H,r=rs,J=js,decimal=dict(F=str(s['scale']*F),G=list(map(str,G)),H=[[str(v) for v in row] for row in s['H']]),context=metadata(ctx))
