"""Independent exact differentiated-control and transpose reference (Plan 019)."""
import struct
from fractions import Fraction as F


def setup_b(U,Q):
    n=len(U)-4
    da=[U[i+4]-U[i+1] for i in range(n-1)]
    db=[U[i+4]-U[i+2] for i in range(n-2)]
    if any(x<=0 for x in da+db):raise ValueError('nonpositive difference denominator')
    alpha=[F(3)/x for x in da];beta=[F(2)/x for x in db];W=U[2:-2];interpolation=[]
    for q in Q:
        if not U[3]<=q<=U[n]:raise ValueError('outside spline domain')
        if q==U[n]:s=n-3
        else:s=next(i for i in range(1,n-2) if W[i]<=q<W[i+1])
        theta=(q-W[s])/(W[s+1]-W[s]);interpolation.append((s,theta))
    return alpha,beta,interpolation


def bundle_b(setup,C,w):
    alpha,beta,interpolation=setup;n=len(C);nacc=len(interpolation)
    D=[[alpha[i]*(C[i+1][axis]-C[i][axis]) for axis in range(3)] for i in range(n-1)]
    E=[[beta[i]*(D[i+1][axis]-D[i][axis]) for axis in range(3)] for i in range(n-2)]
    cost=F(0);summands=[[] for _ in range(6)];accelerations=[]
    for s,theta in interpolation:
        acceleration=[(1-theta)*E[s-1][axis]+theta*E[s][axis] for axis in range(3)]
        accelerations.append(acceleration);cost+=sum(x*x for x in acceleration)*w/nacc
        for axis,a in enumerate(acceleration):
            h=2*w/nacc*a;adjD={}
            for i,adjE in ((s-1,(1-theta)*h),(s,theta*h)):
                adjD[i]=adjD.get(i,F(0))-beta[i]*adjE
                adjD[i+1]=adjD.get(i+1,F(0))+beta[i]*adjE
            adjC=[F(0),F(0)]
            for i,value in adjD.items():
                if i<2:adjC[i]-=alpha[i]*value
                if i+1<2:adjC[i+1]+=alpha[i]*value
            for row in range(2):summands[3*row+axis].append(adjC[row])
    return {'cost':cost,'gradient':[sum(s,F(0)) for s in summands],'summands':summands,'absolute_sums':[sum(map(abs,s),F(0)) for s in summands],'accelerations':accelerations}


def decode_b(inputs):
    import numpy as np
    knots=struct.unpack('<22d',bytes.fromhex(inputs['knots_hex']))
    U=[F.from_float(k) for k in knots];window=inputs['window']
    q=np.arange(window[0]-25,window[1]+26,dtype=float)/25
    qhex=q.astype('<f8',copy=False).tobytes().hex()
    Q=[F.from_float(v) for v in struct.unpack('<150d',bytes.fromhex(qhex))]
    return setup_b(U,Q),qhex


def coefficients_b(h):
    raw=bytes.fromhex(h);C=[]
    for row in range(18):
        values=struct.unpack_from('<3d',raw,row*24)
        C.append([F.from_float(x) for x in values])
    return C
