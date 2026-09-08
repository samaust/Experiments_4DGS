"""Independent fixed Decimal80 control-polygon candidate; no oracle access."""
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


def export(value):
    if not isinstance(value,D) or not value.is_finite():raise ValueError('invalid Decimal output')
    v=float(value)
    if not math.isfinite(v):raise ValueError('nonfinite binary64 export')
    t=value.as_tuple()
    return {'decimal':str(value),'tuple':[t.sign,list(t.digits),t.exponent],
            'value':v,'hex':struct.pack('<d',v).hex()}


def validate_export(record):
    value=D(record['decimal']);t=value.as_tuple()
    if not value.is_finite() or [t.sign,list(t.digits),t.exponent]!=record['tuple']:
        raise ValueError('Decimal serialization')
    raw=bytes.fromhex(record['hex'])
    if len(raw)!=8:raise ValueError('binary64 size')
    v=struct.unpack('<d',raw)[0]
    if not math.isfinite(v) or struct.pack('<d',record['value'])!=raw or struct.pack('<d',float(value))!=raw:
        raise ValueError('binary64 serialization')
    return v


def setup(knots_hex,quadrature_hex,weight=1):
    with dec.localcontext(context()) as ctx:
        U=decode(knots_hex,len(bytes.fromhex(knots_hex))//8)
        Q=decode(quadrature_hex,len(bytes.fromhex(quadrature_hex))//8)
        n=len(U)-4
        if n<4 or not Q or any(a>b for a,b in zip(U,U[1:])) or any(a>b for a,b in zip(Q,Q[1:])):
            raise ValueError('dimension/order')
        if type(weight) is not int or weight<0:raise ValueError('invalid weight')
        alpha=[];beta=[]
        for i in range(n-1):
            da=U[i+4]-U[i+1]
            if da<=0:raise ValueError('nonpositive denominator')
            alpha.append(D(3)/da)
        for i in range(n-2):
            db=U[i+4]-U[i+2]
            if db<=0:raise ValueError('nonpositive denominator')
            beta.append(D(2)/db)
        W=U[2:-2];spans=[]
        for q in Q:
            if not U[3]<=q<=U[n]:raise ValueError('outside domain')
            candidates=[s for s in range(1,n-2) if W[s]<W[s+1] and
                        (W[s]<=q<W[s+1] if q!=U[n] else W[s+1]==q)]
            if len(candidates)!=1:raise ValueError('missing/ambiguous span')
            s=candidates[0];theta=(q-W[s])/(W[s+1]-W[s]);left=D(1)-theta
            spans.append((s,left,theta))
        scale=D(weight)/D(len(Q));twoscale=D(2)*scale
        return dict(n=n,alpha=alpha,beta=beta,spans=spans,scale=scale,
                    twoscale=twoscale,context=metadata(ctx))


def setup_record(s):
    return {**{k:s[k] for k in ('n','context')},'alpha':list(map(str,s['alpha'])),
            'beta':list(map(str,s['beta'])),'spans':[[i,str(l),str(t)] for i,l,t in s['spans']],
            'scale':str(s['scale']),'twoscale':str(s['twoscale'])}


def bundle(s,physical_hex,digest=None):
    with dec.localcontext(context()) as ctx:
        n=s['n'];values=decode(physical_hex,3*n,digest)
        C=[values[i:i+3] for i in range(0,len(values),3)]
        alpha=s['alpha'];beta=s['beta']
        deriv=[[alpha[i]*(C[i+1][a]-C[i][a]) for a in range(3)] for i in range(n-1)]
        second=[[beta[i]*(deriv[i+1][a]-deriv[i][a]) for a in range(3)] for i in range(n-2)]
        squares=D(0);gradient=[D(0) for _ in range(6)];terms=[[] for _ in range(6)]
        for span,left,theta in s['spans']:
            for axis in range(3):
                acc=(left*second[span-1][axis])+(theta*second[span][axis])
                square=acc*acc;squares=squares+square
                h=s['twoscale']*acc
                adjD={i:D(0) for i in sorted({span-1,span,span+1})}
                for i,adjE in ((span-1,left*h),(span,theta*h)):
                    v=beta[i]*adjE;adjD[i]=adjD[i]-v;adjD[i+1]=adjD[i+1]+v
                adjC=[D(0),D(0)]
                for i in sorted(adjD):
                    v=alpha[i]*adjD[i]
                    if i<2:adjC[i]=adjC[i]-v
                    if i+1<2:adjC[i+1]=adjC[i+1]+v
                for row in range(2):
                    j=3*row+axis;gradient[j]=gradient[j]+adjC[row];terms[j].append(str(adjC[row]))
        cost=s['scale']*squares
        return {'cost':export(cost),'gradient':[export(g) for g in gradient],
                'signed_contributions':terms,'context':metadata(ctx)}
