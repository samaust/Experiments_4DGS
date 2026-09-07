"""Appearance-only association and binary-membership-only balanced partition."""
from collections import Counter
import time
import warnings
import numpy as np
import scipy
from scipy.optimize import milp, Bounds, LinearConstraint
from scipy.spatial.distance import cdist
from scipy.spatial import cKDTree
from scipy.sparse import lil_matrix, csr_matrix, vstack
from basketball_shared_timing_v1 import Components
from basketball_timing import undistort_points


def merge_duplicates(tracks,camera,p,check=lambda:None):
    comp=Components(range(len(tracks))); pairs=[]
    # Every contiguous >=60-frame fitting track shares a central frame.
    # Distance at that common frame is a necessary condition for the unchanged
    # maximum-overlap distance test, so a KD-tree only removes impossible pairs.
    common=max((int(t['frames'][0]) for t in tracks),default=0)
    if tracks and common<=min(int(t['frames'][-1]) for t in tracks) and all(np.all(np.diff(t['frames'])==1) for t in tracks):
        points=[t['xy'][common-int(t['frames'][0])] for t in tracks]
        candidates=sorted(cKDTree(points).query_pairs(np.nextafter(p['duplicate_maximum_distance_pixels'],np.inf)))
    else:
        candidates=((i,j) for i in range(len(tracks)) for j in range(i+1,len(tracks)))
    for i,j in candidates:
        check(); a,b=tracks[i],tracks[j]
        _,ia,ib=np.intersect1d(a['frames'],b['frames'],return_indices=True)
        if len(ia)>=p['duplicate_overlap_samples'] and np.max(np.linalg.norm(a['xy'][ia]-b['xy'][ib],axis=1))<=p['duplicate_maximum_distance_pixels']:
            comp.union(i,j); pairs.append([i,j])
    merged=[]; families=[]
    for fid,members in enumerate(comp.groups()):
        values={}; descriptors=[]
        for i in members:
            t=tracks[i]; descriptors.extend(t['descriptor_checkpoints'])
            for f,xy in zip(t['frames'],t['xy']): values.setdefault(int(f),[]).append(xy)
        frames=np.array(sorted(values)); reason=None
        if np.any(np.diff(frames)!=1): reason='noncontiguous duplicate family'
        # A transitive A~B~C family is rejected if A and C disagree, even if
        # their short overlap would not independently meet the duplicate rule.
        if any(len(v)>1 and np.max(cdist(v,v))>p['duplicate_maximum_distance_pixels'] for v in values.values()):
            reason='incompatible transitive duplicate family'
        source_ids=[tracks[i]['source_track_id'] for i in members]
        row=dict(duplicate_family_id=fid,source_track_indices=members,source_track_ids=source_ids,
                 status='rejected' if reason else 'merged',reason=reason)
        if not reason:
            xy=np.array([np.mean(values[f],axis=0) for f in frames])
            row['merged_track_id']=len(merged)
            merged.append(dict(frames=frames,xy=xy,normalized=undistort_points(xy,camera),
                descriptor_checkpoints=descriptors,source_track_ids=source_ids,duplicate_family_id=fid))
        families.append(row)
    return merged,dict(families=families,duplicate_pairs=pairs,
        raw_tracks=len(tracks),merged_tracks=len(merged),duplicate_tracks_merged=sum(len(f['source_track_ids'])-1 for f in families if f['status']=='merged'),
        incompatible_families=sum(f['status']=='rejected' for f in families),
        incompatible_source_tracks=sum(len(f['source_track_ids']) for f in families if f['status']=='rejected'))


def appearance_distances(a,b,max_separation=25):
    """One minimum per trajectory pair; checkpoints never become runner-ups."""
    d=np.full((len(a),len(b)),np.inf); provenance={}
    if not a or not b: return d,provenance
    checkpoints=[t['descriptor_checkpoints'] for t in b]
    if any(not cs for cs in checkpoints): raise ValueError('trajectory lacks checkpoint descriptors')
    ends=np.cumsum([len(cs) for cs in checkpoints]); starts=np.r_[0,ends[:-1]]
    db=[c for cs in checkpoints for c in cs]
    bframes=np.array([c['frame'] for c in db]); bdesc=np.array([c['descriptor'] for c in db])
    for i,t in enumerate(a):
        ca=t['descriptor_checkpoints']
        if not ca: raise ValueError('trajectory lacks checkpoint descriptors')
        block=cdist([c['descriptor'] for c in ca],bdesc)
        block[np.abs(np.array([c['frame'] for c in ca])[:,None]-bframes)>max_separation]=np.inf
        d[i]=np.minimum.reduceat(np.min(block,axis=0),starts)
        for j,(start,end) in enumerate(zip(starts,ends)):
            if not np.isfinite(d[i,j]): continue
            # Row-major argmin preserves the original stable checkpoint-pair
            # tie order: A checkpoint first, then B checkpoint.
            ka,kb=np.unravel_index(np.argmin(block[:,start:end]),(len(ca),end-start))
            provenance[i,j]=dict(a_checkpoint=int(ka),b_checkpoint=int(kb),a_frame=ca[ka]['frame'],
                b_frame=int(bframes[start+kb]),distance=float(d[i,j]))
    return d,provenance


def mutual_pairs(a,b,ratio=.8):
    d,provenance=appearance_distances(a,b)
    if min(d.shape)<2: return [],[]
    ab=np.argsort(d,axis=1,kind='stable')[:,:2]; ba=np.argsort(d,axis=0,kind='stable')[:2,:]
    pairs=[]; evidence=[]
    for i,(j,k) in enumerate(ab):
        # A ratio is supported only if two different trajectories have eligible
        # descriptor pairs in each direction.
        if ba[0,j]==i and np.isfinite([d[i,j],d[i,k],d[ba[1,j],j]]).all() and d[i,j]<ratio*d[i,k] and d[i,j]<ratio*d[ba[1,j],j]:
            pairs.append((i,int(j))); evidence.append(dict(a_track=i,b_track=int(j),**provenance[i,int(j)],
                a_runner_up_track=int(k),b_runner_up_track=int(ba[1,j]),a_runner_up_distance=float(d[i,k]),b_runner_up_distance=float(d[ba[1,j],j])))
    return pairs,evidence


def build_groups(tracks,edges,p,check=lambda:None):
    comp=Components([(c,i) for c in sorted(tracks) for i in range(len(tracks[c]))]); matches=[]
    for edge in edges:
        check(); a,b=edge['a'],edge['b']; pairs,evidence=mutual_pairs(tracks[a],tracks[b])
        for i,j in pairs: comp.union((a,i),(b,j))
        matches.append(dict(a=a,b=b,pairs=[list(v) for v in pairs],descriptor_provenance=evidence,
            unmatched_a=len(tracks[a])-len(pairs),unmatched_b=len(tracks[b])-len(pairs)))
        print('appearance edge',a,b,len(pairs),flush=True)
    groups=[]; rejected=[]
    for members in comp.groups():
        cameras=[c for c,_ in members]; reason=None
        if len(cameras)!=len(set(cameras)): reason='conflicting camera trajectories'
        elif len(set(cameras)-set(p['held_out_cameras']))<p['minimum_training_cameras']: reason='fewer than three training cameras'
        row=dict(members=[dict(camera_id=c,track_id=i) for c,i in members])
        if reason: rejected.append(dict(**row,reason=reason))
        else: groups.append(dict(**row,group_id=len(groups)))
    matrix=np.array([[int({e['a'],e['b']}<={m['camera_id'] for m in g['members']}) for g in groups] for e in edges],dtype=np.int8)
    return groups,rejected,matches,matrix


def partition(matrix,seconds=120):
    """Only binary E x G membership enters the solver. Seed0 lexicographic x.

    Optimize maximum |2 A x - totals|, then sum, then each seed-ordered
    binary decision (0 preferred). Every phase must prove optimality.
    """
    started=time.monotonic(); A=np.asarray(matrix)
    if A.ndim!=2 or not np.isin(A,[0,1]).all(): raise ValueError('binary membership matrix required')
    m,n=A.shape; totals=A.sum(axis=1)
    result=dict(solver='scipy.optimize.milp / bundled HiGHS',scipy_version=scipy.__version__,
        time_limit_seconds=seconds,threads=1,random_seed=0,split_seed=0,
        objectives=['minimum maximum edge imbalance','minimum total edge imbalance','seed0 ordered group decisions; 0 preferred'],
        input_shape=[m,n],edge_totals=totals.tolist(),trace=[],assignment=None)
    def finish(status):
        result.update(status=status,wall_seconds=time.monotonic()-started); return result
    if np.any(totals<24): return finish('insufficient_edge_support')
    nv=n+m+1; mat=lil_matrix((1+4*m,nv),dtype=float)
    lower=[n//2]; upper=[(n+1)//2]; mat[0,:n]=1
    for e in range(m):
        r=1+4*e
        mat[r,:n]=A[e]; lower.append(12); upper.append(int(totals[e]-12))
        mat[r+1,:n]=2*A[e]; mat[r+1,n+e]=-1; lower.append(-np.inf); upper.append(int(totals[e]))
        mat[r+2,:n]=-2*A[e]; mat[r+2,n+e]=-1; lower.append(-np.inf); upper.append(-int(totals[e]))
        mat[r+3,n+e]=1; mat[r+3,-1]=-1; lower.append(-np.inf); upper.append(0)
    mat=mat.tocsr(); lo=np.zeros(nv); hi=np.r_[np.ones(n),totals,max(totals)]
    integrality=np.ones(nv)
    def solve(objective,phase):
        remaining=seconds-(time.monotonic()-started)
        if remaining<=0: return None
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore',message='Unrecognized options detected')
            r=milp(objective,integrality=integrality,bounds=Bounds(lo,hi),
                constraints=LinearConstraint(mat,lower,upper),
                options=dict(time_limit=remaining,mip_rel_gap=0.,presolve=True,threads=1,random_seed=0))
        result['trace'].append(dict(phase=phase,status=int(r.status),message=r.message,
            objective=float(r.fun) if r.fun is not None else None,mip_gap=float(r.mip_gap) if getattr(r,'mip_gap',None) is not None else None))
        return r
    objective=np.zeros(nv); objective[-1]=1; r=solve(objective,'maximum_imbalance')
    def failure(r,tie=False):
        if r is None or r.status==1: return 'deterministic_tie_break_timeout' if tie else 'solver_timeout'
        return 'infeasible' if r.status==2 else 'numerical_failure'
    if r is None or r.status!=0: return finish(failure(r))
    max_imbalance=int(round(r.fun)); hi[-1]=max_imbalance
    objective[:]=0; objective[n:n+m]=1; r=solve(objective,'total_imbalance')
    if r is None or r.status!=0: return finish(failure(r))
    total_imbalance=int(round(r.fun)); mat=vstack([mat,csr_matrix(objective[None,:])],format='csr')
    lower.append(total_imbalance); upper.append(total_imbalance)
    order=np.random.default_rng(0).permutation(n); result['decision_order']=order.tolist()
    for index in order:
        objective[:]=0; objective[index]=1; r=solve(objective,f'group_{index}')
        if r is None or r.status!=0: return finish(failure(r,True))
        lo[index]=hi[index]=int(round(r.x[index]))
    x=np.rint(lo[:n]).astype(int)
    counts=A@x
    if abs(2*x.sum()-n)>1 or np.any(counts<12) or np.any(totals-counts<12): raise ValueError('invalid saved partition')
    if max(abs(2*counts-totals))!=max_imbalance or sum(abs(2*counts-totals))!=total_imbalance: raise ValueError('partition objective mismatch')
    result.update(assignment=x.tolist(),maximum_imbalance=max_imbalance,total_imbalance=total_imbalance)
    return finish('passed')


def reconstruct(groups,tracks,edges,assignment):
    seen_sources=set(); seen_families=set(); seen_tracks=set()
    if assignment is not None and (len(assignment)!=len(groups) or any(x not in (0,1) for x in assignment)):
        raise ValueError('incomplete partition')
    support=[]
    for g in groups:
        for m in g['members']:
            c,i=m['camera_id'],m['track_id']; t=tracks[c][i]
            identities=[(c,s) for s in t['source_track_ids']]; family=(c,t['duplicate_family_id'])
            if (c,i) in seen_tracks or family in seen_families or any(s in seen_sources for s in identities):
                raise ValueError('original trajectory or duplicate family leakage')
            seen_tracks.add((c,i)); seen_families.add(family); seen_sources.update(identities)
    for e in edges:
        ids=[g['group_id'] for g in groups if {e['a'],e['b']}<={m['camera_id'] for m in g['members']}]
        halves=None if assignment is None else {role:[i for i in ids if assignment[i]==v] for v,role in [(0,'optimization'),(1,'assessment')]}
        support.append(dict(a=e['a'],b=e['b'],eligible_groups=len(ids),group_ids=ids,
            optimization=None if halves is None else len(halves['optimization']),
            assessment=None if halves is None else len(halves['assessment']),half_group_ids=halves,
            passed=halves is not None and all(len(v)>=12 for v in halves.values())))
    return support
