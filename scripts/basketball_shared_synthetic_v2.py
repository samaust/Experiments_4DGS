"""Continuous 3D synthetic controls for the actual spline model/evaluator."""
import numpy as np
from basketball_shared_timing_v1 import project


def synthetic(motion='acceleration',noise=0.,delta=.25,length=100,groups=12,held_out=False,outliers=False):
    K=[[800.,0,479.5],[0,800.,269.5],[0,0,1]]
    cameras={c:dict(camera_id=c,K=K,parameters_colmap=[800.,480.,270.,.01],R=np.eye(3).tolist(),t=[x,0.,0.]) for c,x in [(1,0.),(2,-1.),(3,1.),(0,-.5)]}
    if not held_out: cameras.pop(0)
    offsets={1:0.,2:delta,3:-.2}
    if held_out: offsets[0]=.1
    frames=np.arange(50,50+length,dtype=float);rng=np.random.default_rng(0);rows=[]
    for gid in range(groups):
        observations=[]
        for c in cameras:
            t=frames-50-offsets[c];phase=gid*.03
            x=.03*gid+.002*t
            y=.008*t+phase
            if motion=='acceleration':y+=.0003*t*t
            elif motion=='direction_changes':y=.000002*(t-40)**3-.004*(t-40)+phase
            elif motion=='stationary':x=np.full_like(t,.03*gid);y=np.full_like(t,phase)
            elif motion=='epipolar_direction':y=np.full_like(t,phase)
            elif motion!='constant_velocity':raise ValueError(motion)
            xyz=np.column_stack((x,y,np.full_like(t,8.+gid*.1)))
            xy=project(xyz,cameras[c])+rng.normal(0,noise,(len(t),2))
            if outliers:xy[::13]+=rng.normal(0,12,(len(xy[::13]),2))
            observations.append(dict(camera_id=c,frames=frames.copy(),xy=xy))
        rows.append(dict(group_id=gid,observations=observations))
    return rows,cameras,offsets,[50,49+length]
