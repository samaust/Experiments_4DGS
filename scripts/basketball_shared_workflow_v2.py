"""Plan008 full versioned workflow; production stages follow frozen admission.

Support implementation remains immutable after its completed run. This wrapper
adds actual spline safeguards, fitting and independent assessment without
rewriting the admission code or its hashes. Final frames have no reader.
"""
import os
for _name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:
    os.environ[_name]='1'
import argparse
import copy
import json
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time
import numpy as np
import cv2
cv2.setNumThreads(1)
from basketball_audit import sha256
from basketball_scale import read,write
from basketball_continuation_audit import verify_hashes,CALIBRATION
from basketball_shared_timing_v1 import predecessor
from basketball_shared_timing_v2 import bounded,validate_config
from basketball_shared_spline_v2 import (fit_trajectories,clip_groups,estimate_held_out,independent_edge,independent_cycles,InsufficientSupport)
from basketball_shared_synthetic_v2 import synthetic

IMPLEMENTATION=['scripts/basketball_shared_workflow_v2.py','scripts/basketball_shared_spline_v2.py','scripts/basketball_shared_synthetic_v2.py','tests/test_basketball_shared_spline_v2.py','tests/test_basketball_shared_profiles_v2.py']


def starts(cameras,current):
    rng=np.random.default_rng(0);order=sorted(cameras)
    base={c:float(current[c]-current.get(1,0.)) for c in order}
    zero={c:0. for c in order};perturbed={c:base[c]+float(rng.uniform(-.5,.5)) for c in order}
    if 1 in perturbed:perturbed[1]=0.
    return [('current',base),('zero',zero),('perturbed_seed0',perturbed)]


def production_starts(groups,cameras,current,window,configuration,check):
    training=set(cameras)-{0,10,20,30};observations=clip_groups(groups,window,training);fits=[]
    observed={o['camera_id'] for g in observations for o in g['observations']}
    for label,offsets in starts(observed,current):
        check()
        try:
            result=fit_trajectories(observations,cameras,offsets,window,configuration['knot_spacing_frames'],configuration['acceleration_weight'],check=check)
            result['start']=label;fits.append(result)
        except (InsufficientSupport,ValueError,FloatingPointError) as error:fits.append(dict(start=label,converged=False,error=str(error)))
    qualifying=[r for r in fits if r['converged'] and r['positive_depth'] and not r['boundary_cameras']]
    agreement=None
    if len(qualifying)==3:
        agreement=float(max(np.ptp([r['offsets'][c] for r in qualifying]) for c in observed))
    passed=len(qualifying)==3 and agreement<=.25
    best=min(qualifying,key=lambda r:r['objective']) if qualifying else None
    return dict(passed=passed,starts=fits,maximum_start_disagreement_frames=agreement,best=best)


def safeguard(p,output,check):
    """Stop on a failed required safeguard; preserve every attempted control."""
    optimizer_dir=output/'optimizer-controls';optimizer_dir.mkdir()
    profile_dir=output/'independent-controls';profile_dir.mkdir()
    rows=[];profile_rows=[];failures=[]
    motions=['constant_velocity','acceleration','direction_changes','stationary','epipolar_direction']
    planned_optimizer=6*5*3*3*7
    # Freeze the full requested injection/length/noise cross product before
    # running it. Three actual starts are evaluated for every optimizer control.
    for ci,configuration in enumerate(p['configurations']):
        for motion in motions:
            for length in [100,50,25]:
                for noise in [0.,.25,.5]:
                    for delta in p['injections']:
                        check();groups,cameras,truth,window=synthetic(motion,noise,delta,length,groups=3)
                        current={1:0.,2:.1,3:-.1}
                        result=production_starts(groups,cameras,current,window,configuration,check)
                        errors=[abs(r['offsets'][2]-truth[2]) for r in result['starts'] if r['converged']]
                        positive=motion in motions[:3];required=positive and noise==0
                        passed=not required or (result['passed'] and len(errors)==3 and max(errors)<=.05)
                        row=dict(case_id=len(rows),configuration=configuration,motion=motion,length=length,noise_pixels=noise,
                            known_offset_frames=delta,absolute_errors_frames=errors,required_noiseless_recovery=required,
                            safeguard_passed=passed,timing_qualified=False,qualification_reason='optimizer control only; independent profile required',result=result)
                        write(optimizer_dir/f'case{len(rows):04d}.json',row);rows.append({k:v for k,v in row.items() if k!='result'})
                        if not passed:
                            failures.append(dict(stage='optimizer_control',case_id=row['case_id'],kind='numerical_failure' if any(not r['converged'] for r in result['starts']) else 'scientific_rejection',reason='noiseless identifiable production control failed convergence,0.05 recovery or three-start agreement'))
                            break
                    if failures:break
                if failures:break
            if failures:break
        if failures:break
        print('synthetic optimizer configuration',ci,'controls',len(rows),flush=True)
    # Independent positive cases cover every requested offset x length x noise.
    # Motion rotates deterministically through all three positive geometries.
    cases=[]
    for length in [100,50,25]:
        for noise in [0.,.25,.5]:
            for delta in p['injections']:
                cases.append(dict(motion=motions[len(cases)%3],length=length,noise=noise,delta=delta,weight=1.,negative=False))
    for motion in motions[3:]:
        for weight in [.1,1.,10.]:
            for length in [100,50,25]:
                for noise in [0.,.25,.5]:cases.append(dict(motion=motion,length=length,noise=noise,delta=.25,weight=weight,negative=True))
    if not failures:
        for case in cases:
            check();groups,cameras,truth,window=synthetic(case['motion'],case['noise'],case['delta'],case['length'],groups=12)
            result=independent_edge(groups,cameras,dict(a=1,b=2),window,10,case['weight'],check,workers=8,deadline=p['investigation_started_unix']+13200)
            regularized=result['profiles']['regularized'];data=result['profiles']['data_only']
            errors={k:None if v['lag'] is None else abs(v['lag']-truth[2]) for k,v in result['profiles'].items()}
            threshold=.05 if case['noise']==0 else .25
            # Long noiseless positive controls have overlapping calibrated
            # observations throughout the full search and must be identifiable.
            required=not case['negative'] and case['noise']==0 and case['length']==100
            passed=(not result['passed'] if case['negative'] else (not result['passed'] or all(e is not None and e<=threshold for e in errors.values())))
            if required:passed=passed and result['passed'] and all(e is not None and e<=.05 for e in errors.values())
            row=dict(case_id=len(profile_rows),**case,result=result,absolute_errors_frames=errors,safeguard_passed=passed,
                interval_covers_truth={k:(v['bootstrap_95_frames'][0]<=truth[2]<=v['bootstrap_95_frames'][1]) if v.get('bootstrap_95_frames') else None for k,v in result['profiles'].items()})
            write(profile_dir/f'case{len(profile_rows):04d}.json',row);profile_rows.append({k:v for k,v in row.items() if k!='result'})
            print('independent synthetic control',row['case_id'],case,'passed safeguard',passed,flush=True)
            if not passed:
                failures.append(dict(stage='independent_control',case_id=row['case_id'],kind='numerical_failure' if any(r.get('support',0)<12 for r in result['profiles'].values()) else 'scientific_rejection',reason='required recovery/identifiability or negative-control rejection failed'));break
    summary=dict(status='blocked' if failures else 'passed',terminal_kind=failures[0]['kind'] if failures else None,
        blockers=failures,optimizer_controls=rows,independent_controls=profile_rows,
        planned_optimizer_controls=planned_optimizer,planned_independent_controls=len(cases),
        optimizer_matrix_complete=len(rows)==planned_optimizer,independent_matrix_complete=len(profile_rows)==len(cases),
        model_configurations_fitted_to_real_data=0)
    write(output/'synthetic-summary.json',summary)
    return {k:v for k,v in summary.items() if k not in ['optimizer_controls','independent_controls']}


def load_associated(folder):
    saved=read(folder/'groups.json')['groups'];tracks={c:read(folder/f'merged-camera{c}.json')['tracks'] for c in range(34)}
    result=[]
    for g in saved:
        result.append(dict(group_id=g['group_id'],split=g['split'],observations=[dict(camera_id=m['camera_id'],
            frames=np.asarray(tracks[m['camera_id']][m['track_id']]['frames']),xy=np.asarray(tracks[m['camera_id']][m['track_id']]['xy'])) for m in g['members']]))
    return result


def fit_real(p,output,association,check):
    groups=load_associated(association);optimization=[g for g in groups if g['split']=='optimization']
    cameras={c['camera_id']:c for c in read(CALIBRATION)['cameras']}
    current={int(k):v for k,v in read(p['previous_frozen'])['candidate']['offsets'].items()}
    rows=[]
    for index,configuration in enumerate(p['configurations']):
        check();result=production_starts(optimization,cameras,current,[50,149],configuration,check)
        if result['passed']:
            held_starts=[estimate_held_out(optimization,cameras,r,check=check) for r in result['starts']]
            result['held_out_starts']=held_starts
            result['passed']=all(row['status']=='passed' for held in held_starts for row in held.values())
            if result['passed']:
                disagreement=max(np.ptp([held[c]['offset'] for held in held_starts]) for c in [0,10,20,30])
                result['held_out_start_disagreement_frames']=float(disagreement);result['passed']=disagreement<=.25
            if result['passed']:
                best_index=next(i for i,r in enumerate(result['starts']) if r is result['best'])
                result['candidate_offsets']={**result['best']['offsets'],**{c:r['offset'] for c,r in held_starts[best_index].items()}}
        write(output/f'configuration{index}.json',dict(configuration=configuration,**result))
        rows.append(dict(configuration_id=index,configuration=configuration,passed=result['passed']))
        print('real fitting configuration',index,result['passed'],flush=True)
    return dict(status='passed' if any(r['passed'] for r in rows) else 'blocked',
        terminal_kind=None if any(r['passed'] for r in rows) else 'numerical_failure',
        blockers=[] if any(r['passed'] for r in rows) else ['no stable converged production configuration'],configurations=rows,
        association=str(association),model_configurations_fitted_to_real_data=6)


def assess_real(p,output,fit_path,association,check):
    groups=[g for g in load_associated(association) if g['split']=='assessment'];cameras={c['camera_id']:c for c in read(CALIBRATION)['cameras']}
    edges=read(p['previous_frozen'])['edges'];results=[]
    for ci,configuration in enumerate(p['configurations']):
        production=read(fit_path/f'configuration{ci}.json')
        if not production['passed']:results.append(dict(configuration_id=ci,passed=False,reason='production did not converge stably'));continue
        offsets={int(c):v for c,v in production['candidate_offsets'].items()};directory=output/f'configuration{ci}';directory.mkdir()
        windows=[];reprojections=[]
        for wi,window in enumerate([[50,149],*p['audit_windows']]):
            check();clipped=clip_groups(groups,window);training=[g for g in clip_groups(clipped,window,set(cameras)-{0,10,20,30}) if len(g['observations'])>=3]
            nuisance=fit_trajectories(training,cameras,offsets,window,configuration['knot_spacing_frames'],configuration['acceleration_weight'],fixed=set(cameras),check=check)
            write(directory/f'window{wi}-reprojection.json',nuisance)
            from basketball_shared_spline_v2 import predict
            indices={gid:i for i,gid in enumerate(nuisance['group_ids'])};errors=[]
            for g in clipped:
                if g['group_id'] not in indices:continue
                for o in g['observations']:
                    errors.extend(np.linalg.norm(predict(nuisance,indices[g['group_id']],cameras[o['camera_id']],o['frames'],offsets[o['camera_id']])-o['xy'],axis=1))
            reprojections.append(float(np.mean(errors)))
            independent=[];passed=nuisance['converged'] and nuisance['positive_depth']
            for ei,edge in enumerate(edges):
                check();result=independent_edge(clipped,cameras,edge,window,configuration['knot_spacing_frames'],configuration['acceleration_weight'],check,workers=8,deadline=p['investigation_started_unix']+13200)
                lag=result['profiles']['regularized']['lag'];data_lag=result['profiles']['data_only']['lag']
                expected=offsets[edge['b']]-offsets[edge['a']]
                result['production_lag_disagreement_frames']=None if lag is None else abs(lag-expected)
                result['data_only_production_disagreement_frames']=None if data_lag is None else abs(data_lag-expected)
                result['passed']=result['passed'] and lag is not None and data_lag is not None and abs(lag-expected)<=.25 and abs(data_lag-expected)<=.25
                # Original spatial support: median absolute calibrated epipolar
                # discrepancy at the independently measured lag, within role.
                spatial=[]
                if lag is not None:
                    from basketball_timing import undistort_points,essential,epipolar_pixels
                    for g in clipped:
                        obs={o['camera_id']:o for o in g['observations']}
                        if not {edge['a'],edge['b']}<=set(obs):continue
                        a,b=obs[edge['a']],obs[edge['b']];q=a['frames']+lag;use=(q>=b['frames'][0])&(q<=b['frames'][-1])
                        if use.sum()<15:continue
                        ua=undistort_points(a['xy'][use],cameras[edge['a']]);ub=undistort_points(b['xy'],cameras[edge['b']])
                        vb=np.column_stack([np.interp(q[use],b['frames'],ub[:,k]) for k in range(2)])
                        spatial.append(float(np.median(epipolar_pixels(ua,vb,essential(cameras[edge['a']],cameras[edge['b']]),np.mean([cameras[c]['K'][0][0] for c in [edge['a'],edge['b']]])))))
                result['spatial_group_count']=len(spatial);result['median_absolute_spatial_bias_pixels']=float(np.median(spatial)) if spatial else None
                result['passed']=result['passed'] and len(spatial)>=12 and np.median(spatial)<=3.
                write(directory/f'window{wi}-edge{ei}.json',result);passed=passed and result['passed']
                independent.append(dict(a=edge['a'],b=edge['b'],lag=lag,data_only_lag=data_lag))
            cycles=independent_cycles(independent);data_cycles=independent_cycles([dict(a=e['a'],b=e['b'],lag=e['data_only_lag']) for e in independent])
            passed=passed and cycles['passed'] and data_cycles['passed'];windows.append(dict(window=window,passed=passed,cycles=cycles,data_only_cycles=data_cycles))
        row=dict(configuration_id=ci,configuration=configuration,passed=all(w['passed'] for w in windows),windows=windows,assessment_reprojection_pixels=float(np.mean(reprojections)))
        results.append(row);write(directory/'assessment.json',row)
    passing=[r for r in results if r['passed']]
    winner=min(passing,key=lambda r:(r['assessment_reprojection_pixels'],-r['configuration']['knot_spacing_frames'],r['configuration']['acceleration_weight'])) if passing else None
    return dict(status='passed' if winner else 'blocked',terminal_kind=None if winner else 'scientific_rejection',
        blockers=[] if winner else ['no configuration passes every independent fitting window'],configurations=results,
        selected_configuration=winner,fit_path=str(fit_path),association=str(association))


def stage(a):
    p=read(a.config);validate_config(p);bounded(p,a.stage=='package');started=time.monotonic()
    permitted={'safeguard':{'associate'},'fit':{'safeguard'},'assess':{'fit'},'select':{'assess'},'package':{'safeguard','fit','assess','select'}}
    prior=predecessor(a.predecessor,sha256(a.config),permitted[a.stage])
    if a.stage!='package' and prior['status']!='passed':raise ValueError('blocked predecessor')
    sources={**prior['source_sha256'],str(a.predecessor/'result.json'):sha256(a.predecessor/'result.json')}
    if a.stage!='safeguard':verify_hashes(sources)
    sources.update({name:sha256(name) for name in IMPLEMENTATION});sources[str(a.config)]=sha256(a.config)
    if a.association:
        admission=predecessor(a.association,sha256(a.config),{'associate'})
        if admission['status']!='passed':raise ValueError('support admission failed')
        sources[str(a.association/'result.json')]=sha256(a.association/'result.json')
    a.output.mkdir(parents=True,exist_ok=False);write(a.output/'frozen.json',dict(config=p,source_sha256=sources))
    check=lambda:bounded(p)
    try:
        if a.stage=='safeguard':result=safeguard(p,a.output,check)
        elif a.stage=='fit':
            if a.association is None:raise ValueError('hashed association required')
            result=fit_real(p,a.output,a.association,check)
        elif a.stage=='assess':result=assess_real(p,a.output,a.predecessor,Path(prior['association']),check)
        elif a.stage=='select':
            # Selection extraction requires its own fitting-independent mask
            # manifest and a complete fitting winner. No selection reads happen
            # through an incomplete implementation or failed safeguard.
            raise InsufficientSupport('selection extraction/evaluation adapter requires completion after fitting qualification')
        else:
            if prior['status']!='blocked':raise ValueError('package requires evidenced terminal blocker')
            result=dict(status='blocked',terminal_kind=prior['terminal_kind'],blockers=prior['blockers'],blocked_stage=prior['stage'])
        verify_hashes(sources)
    except TimeoutError as error:result=dict(status='blocked',terminal_kind='budget_exhaustion',blockers=[str(error)])
    except (InsufficientSupport,FloatingPointError) as error:result=dict(status='blocked',terminal_kind='numerical_failure',blockers=[str(error)])
    usage=resource.getrusage(resource.RUSAGE_SELF);children=resource.getrusage(resource.RUSAGE_CHILDREN)
    result.update(schema='basketball-shared-timing-stage/v2',stage=a.stage,config_sha256=sha256(a.config),source_sha256=sources,
        artifacts_sha256={str(f):sha256(f) for f in sorted(a.output.rglob('*.json'))},wall_seconds=time.monotonic()-started,
        process_cpu_seconds=usage.ru_utime+usage.ru_stime,child_cpu_seconds=children.ru_utime+children.ru_stime,maximum_rss_kib=usage.ru_maxrss,
        investigation_elapsed_seconds=time.time()-p['investigation_started_unix'],cpu_threads_limit=8,gpu_seconds=0,
        candidate_offsets=None,accepted_timing=None,selection_previously_consumed=True,selection_consumed_this_attempt=False,final_validation_consumed=False)
    write(a.output/'result.json',result);print('stage',a.stage,result['status'],result['blockers'],flush=True)
    return int(result['status']=='blocked')


def main(a):
    if a.stage in ['prepare','associate']:
        return subprocess.call([sys.executable,'scripts/basketball_shared_timing_v2.py',*sys.argv[1:]])
    p=read(a.config);bounded(p,a.stage=='package')
    if a.output.exists():raise FileExistsError('fresh output required')
    reserve=0 if a.stage=='package' else 1200
    remaining=p['investigation_started_unix']+14400-reserve-time.time()
    child=subprocess.Popen([sys.executable,str(Path(__file__)),*sys.argv[1:],'--worker'],start_new_session=True)
    try:return child.wait(timeout=max(.001,remaining))
    except subprocess.TimeoutExpired:
        os.killpg(child.pid,signal.SIGTERM)
        try:child.wait(timeout=2)
        except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
        a.output.mkdir(parents=True,exist_ok=True)
        sources=read(a.predecessor/'result.json')['source_sha256']
        sources={**sources,**{name:sha256(name) for name in IMPLEMENTATION},str(a.predecessor/'result.json'):sha256(a.predecessor/'result.json')}
        write(a.output/'result.json',dict(schema='basketball-shared-timing-stage/v2',stage=a.stage,status='blocked',
            terminal_kind='budget_exhaustion',blockers=['external watchdog terminated production work before packaging reserve'],
            config_sha256=sha256(a.config),source_sha256=sources,artifacts_sha256={str(f):sha256(f) for f in a.output.rglob('*.json') if f.name!='result.json'},
            candidate_offsets=None,accepted_timing=None,selection_consumed_this_attempt=False,final_validation_consumed=False,
            investigation_elapsed_seconds=time.time()-p['investigation_started_unix'],gpu_seconds=0))
        return 1


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['prepare','associate','safeguard','fit','assess','select','package'])
    parser.add_argument('--config',type=Path,required=True);parser.add_argument('--predecessor',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--association',type=Path)
    parser.add_argument('--extracted-predecessor',type=Path);parser.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args();raise SystemExit(stage(args) if args.worker else main(args))
