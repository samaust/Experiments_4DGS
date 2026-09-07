"""Two preregistered timing recovery stages; immutable calibration and frame roles."""
import argparse
import json
from pathlib import Path
import time
import numpy as np
from basketball_audit import sha256
from basketball_continuation_audit import CALIBRATION, CALIBRATION_SHA, WORKSPACE, verify_hashes
from basketball_scale import read, write
from basketball_timing import camera_graph, essential, solve_curve, graph_offsets, match_tracks, undistort_points


def signed_errors(x,y,E,focal):
    x=np.column_stack((x,np.ones(len(x))));y=np.column_stack((y,np.ones(len(y))))
    ex=x@E.T;ey=y@E
    denom=np.sqrt(np.sum(ex[:,:2]**2,axis=1)+np.sum(ey[:,:2]**2,axis=1))
    return np.sum(ex*y,axis=1)/np.maximum(denom,1e-12)*focal


def temporal_cost(a,b,lag,E,focal,p):
    radius=p['integer_search_radius']
    # Keep exactly the same reference observations for every hypothesis.
    times=a['frames'];use=(times>=b['frames'][0]+radius)&(times<=b['frames'][-1]-radius)
    if use.sum()<p['minimum_pair_samples_per_track']:return np.nan
    target=times[use]+lag
    if target.min()<b['frames'][0] or target.max()>b['frames'][-1]:return np.nan
    yy=np.column_stack([np.interp(target,b['frames'],b['normalized'][:,i]) for i in range(2)])
    error=signed_errors(a['normalized'][use],yy,E,focal)
    residual=error-np.median(error)
    absolute=np.abs(residual)
    # sqrt(2*Huber) has pixel units and equals RMS for residuals <=1px.
    return float(np.sqrt(np.mean(np.where(absolute<=1,residual**2,2*absolute-1))))


def load_tracks(folder):
    r=read(folder/'result.json')
    if r['status']!='complete' or r['role']!='fit':raise ValueError('need complete fitting tracks')
    tracks={}
    for row in r['cameras']:
        c=row['camera_id'];path=folder/f'camera{c}-tracks.json';verify_hashes({str(path):row['sha256']})
        if c in tracks:raise ValueError('duplicate camera')
        tracks[c]=read(path)['tracks']
        for t in tracks[c]:
            for k in ['frames','xy','normalized','descriptor']:
                if k in t:t[k]=np.asarray(t[k])
            f=t['frames']
            if not len(f) or f[0]<50 or f[-1]>149 or np.any(np.diff(f)!=1):raise ValueError('fitting track role/gap violation')
    if set(tracks)!=set(range(34)):raise ValueError('incomplete physical rig')
    return tracks


def freeze(a):
    p=read(a.protocol);base=read(p['base_protocol']);audit=read(a.audit)
    if audit['status']!='passed':raise ValueError('provenance has not passed')
    verify_hashes(audit['sha256'])
    for v in audit['videos']:verify_hashes({v['path']:v['sha256']})
    if p['calibration_sha256']!=CALIBRATION_SHA or p['timing_gate_frames']!=.25 or p['integer_search_radius']!=25:
        raise ValueError('accepted gate changed')
    for key,value in [('fit_frames',[50,149]),('selection_frames',[150,199]),('validation_frames',[200,249])]:
        if p[key]!=value:raise ValueError('changed frame roles')
    base.update(p)
    base['graph']=camera_graph(base)
    base['config_sha256']=sha256(a.protocol)
    base['base_protocol_sha256']=sha256(p['base_protocol'])
    base['audit_sha256']=sha256(a.audit)
    base['source_sha256']={str(Path(__file__)):sha256(__file__),'scripts/basketball_timing.py':sha256('scripts/basketball_timing.py')}
    a.output.mkdir(parents=True,exist_ok=False);write(a.output/'protocol.json',base)
    print('frozen',len(base['graph']),'geometric edges')


def fit(a):
    p=read(a.protocol);tracks=load_tracks(a.tracks)
    verify_hashes(p['source_sha256']);verify_hashes({str(CALIBRATION):CALIBRATION_SHA})
    cams={e['camera_id']:e for e in read(CALIBRATION)['cameras']}
    started=time.monotonic();edges=[]
    integer=np.arange(-25,26,dtype=float)
    for e in p['graph']:
        if time.monotonic()-started>p['maximum_cpu_seconds_per_stage']:raise TimeoutError('timing CPU bound')
        ca,cb=e['a'],e['b'];E=essential(cams[ca],cams[cb]);focal=np.mean([cams[c]['K'][0][0] for c in (ca,cb)])
        if a.stage=='sift-temporal-bias':
            pairs=match_tracks(tracks[ca],tracks[cb],p)
        else:
            left={t['pair_key']:i for i,t in enumerate(tracks[ca]) if t.get('other_camera')==cb}
            right={t['pair_key']:i for i,t in enumerate(tracks[cb]) if t.get('other_camera')==ca}
            pairs=[(left[k],right[k]) for k in sorted(left.keys()&right.keys())]
        compute=lambda grid:np.array([[temporal_cost(tracks[ca][i],tracks[cb][j],d,E,focal,p) for d in grid] for i,j in pairs]).reshape(len(pairs),len(grid))
        costs=compute(integer)
        # Freeze descriptor/seed associations; reject only invalid full-search support.
        valid=np.isfinite(costs).all(axis=1);coarse=solve_curve(costs[valid],integer,p)
        row=dict(e,pair_tracks=len(pairs),integer=coarse,passed=False,lag=None)
        if coarse['lag'] is not None and abs(coarse['lag'])<25:
            grid=np.unique(np.round(np.r_[integer,np.arange(coarse['lag']-1,coarse['lag']+1.00001,.05)],8))
            refined=solve_curve(compute(grid)[valid],grid,p)
            # Report and gate the original spatial residual at the chosen timing.
            biases=[]
            for i,j in np.array(pairs,dtype=int)[valid]:
                ta,tb=tracks[ca][i],tracks[cb][j];t=ta['frames']
                use=(t>=tb['frames'][0]+25)&(t<=tb['frames'][-1]-25)
                yy=np.column_stack([np.interp(t[use]+refined['lag'],tb['frames'],tb['normalized'][:,k]) for k in range(2)])
                biases.append(float(np.median(signed_errors(ta['normalized'][use],yy,E,focal))))
            median_bias=float(np.median(np.abs(biases))) if biases else None
            if median_bias is None or median_bias>p['bias_limit_pixels']:
                refined['passed']=False;refined['blockers'].append('original spatial epipolar support fails')
            row.update(refined=refined,passed=refined['passed'],lag=refined['lag'],median_absolute_bias_pixels=median_bias)
        edges.append(row);print('edge',ca,cb,'tracks',coarse['support'],'lag',row['lag'],'passed',row['passed'],flush=True)
    graph=graph_offsets(edges,tolerance=.25)
    write(a.output,dict(schema='basketball-timing-recovery-fit/v1',stage=a.stage,**graph,edges=edges,
        wall_seconds=time.monotonic()-started,protocol_sha256=sha256(a.protocol),tracks_sha256=sha256(a.tracks/'result.json'),
        source_sha256=p['source_sha256'],calibration_sha256=CALIBRATION_SHA,selection_consumed=False,final_validation_consumed=False))
    return graph['status']!='passed'


def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='mode',required=True)
    q=s.add_parser('freeze');q.add_argument('--protocol',type=Path,required=True);q.add_argument('--audit',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=s.add_parser('fit');q.add_argument('--protocol',type=Path,required=True);q.add_argument('--tracks',type=Path,required=True)
    q.add_argument('--stage',choices=['sift-temporal-bias','roma-temporal-bias'],required=True);q.add_argument('--output',type=Path,required=True)
    a=p.parse_args();return {'freeze':freeze,'fit':fit}[a.mode](a)


if __name__=='__main__':raise SystemExit(main())
