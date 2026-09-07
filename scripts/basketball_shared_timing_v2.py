"""Plan008 stage CLI with shared elapsed deadline and external process watchdog.

Production implementation is deliberately gated on fresh support admission.
No stage reads final-validation frames.
"""
import os
for _name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS']:
    os.environ[_name]='1'
import argparse
from collections import Counter
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time
import shutil
import numpy as np
from basketball_audit import sha256
from basketball_scale import read,write
from basketball_continuation_audit import verify_hashes,CALIBRATION,WORKSPACE
from basketball_shared_timing_v1 import baseline,validate_config as validate_v1,predecessor,serial_track
from basketball_shared_tracks_v2 import extract
from basketball_shared_association_v2 import merge_duplicates,build_groups,partition,reconstruct

SCRIPTS=['scripts/basketball_shared_timing_v2.py','scripts/basketball_shared_tracks_v2.py','scripts/basketball_shared_association_v2.py']


def bounded(p,package=False):
    limit=p['maximum_cpu_seconds']-(0 if package else p['packaging_reserve_seconds'])
    if time.time()>=p['investigation_started_unix']+limit:
        raise TimeoutError('investigation deadline reached'+('' if package else '; packaging reserve protected'))


def validate_config(p):
    old=read(p['prior_config']); validate_v1(old)
    unchanged=['target_cameras','held_out_cameras','roles','configurations','minimum_groups_per_half','minimum_training_cameras',
        'duplicate_overlap_samples','duplicate_maximum_distance_pixels','sift_features','seed_spacing_native_pixels',
        'maximum_tracks_per_seed','lk_window_native_pixels','maximum_forward_backward_native_pixels','minimum_adjacent_patch_correlation',
        'native_dimensions','base_frozen_protocol','previous_frozen','audit','model_policy']
    if any(p[k]!=old[k] for k in unchanged): raise ValueError('changed fixed Plan008 invariant')
    fixed=dict(schema='basketball-shared-trajectories/v2',fit_frames=[50,149],seed_frames=list(range(50,150,10))+[149],
        maximum_cpu_seconds=14400,packaging_reserve_seconds=1200,partition_seconds=120,split_seed=0,
        maximum_descriptor_frame_separation=25,descriptor_checkpoint_spacing_frames=10,cpu_threads=8)
    if any(p.get(k)!=v for k,v in fixed.items()): raise ValueError('changed Plan008 extraction/deadline invariant')
    return read(p['base_frozen_protocol'])


def historical_sources(p):
    sources=baseline(read(p['prior_config']))
    evidence=read(p['prior_evidence'])
    for key in ['source_sha256','immutable_sha256','artifact_sha256','test_logs_sha256']:
        verify_hashes(evidence[key]); sources.update(evidence[key])
    old=predecessor(Path(p['prior_audit']),sha256(p['prior_config']),{'audit'})
    if old['status']!='passed': raise ValueError('Plan007 estimator audit incomplete')
    sources.update(p['source_sha256']); verify_hashes(sources)
    return sources


def load_raw(folder):
    tracks={}
    for path in sorted(folder.glob('camera*-tracks.json')):
        row=read(path)
        if row['role']!='fit': raise ValueError('wrong role')
        items=row['tracks']
        for t in items:
            for key in ['frames','xy','normalized']: t[key]=np.asarray(t[key])
            if t['frames'].min()<50 or t['frames'].max()>149: raise ValueError('nonfitting observation')
        tracks[row['camera_id']]=items
    if set(tracks)!=set(range(34)): raise ValueError('incomplete camera extraction')
    return tracks


def associate(p,output,extracted=None):
    check=lambda:bounded(p)
    if extracted is None:
        folder=extract(p,read(p['audit']),output,check)
    else:
        folder=extracted/'tracks'
        (output/'tracks').symlink_to(folder.resolve(),target_is_directory=True)
        write(output/'extraction-reused.json',dict(predecessor=str(extracted),tracks_result_sha256=sha256(folder/'result.json'),policy_unchanged=True))
    raw=load_raw(folder)
    cameras={c['camera_id']:c for c in read(CALIBRATION)['cameras']}; tracks={}; counts=[]
    for c,items in sorted(raw.items()):
        check(); tracks[c],families=merge_duplicates(items,cameras[c],p,check)
        write(output/f'duplicate-camera{c}.json',families)
        counts.append(dict(camera_id=c,**{k:v for k,v in families.items() if k not in ['families','duplicate_pairs']}))
        write(output/f'merged-camera{c}.json',dict(camera_id=c,role='fit',tracks=[serial_track(t) for t in tracks[c]]))
        print('merged camera',c,len(items),len(tracks[c]),flush=True)
    edges=read(p['previous_frozen'])['edges']
    groups,rejected,matches,matrix=build_groups(tracks,edges,p,check)
    write(output/'membership.json',dict(edge_order=[dict(a=e['a'],b=e['b']) for e in edges],group_order=[g['group_id'] for g in groups],matrix=matrix.tolist()))
    decision=partition(matrix,p['partition_seconds']); write(output/'partition.json',decision)
    if decision['assignment'] is not None:
        for g,value in zip(groups,decision['assignment']): g['split']='assessment' if value else 'optimization'
    write(output/'groups.json',dict(groups=groups,rejected=rejected,matches=matches,partition_sha256=sha256(output/'partition.json')))
    # Read the saved state back, rather than trust only the in-memory counts.
    saved=read(output/'groups.json'); decision=read(output/'partition.json')
    support=reconstruct(saved['groups'],tracks,edges,decision['assignment'])
    old={(e['a'],e['b']):e for e in read('docs/experiments/basketball-shared-timing-v1/support.json')['edges']}
    for e in support:
        before=old[e['a'],e['b']]; e.update(plan007_eligible_groups=before['optimization']+before['assessment'],
            eligible_group_change=e['eligible_groups']-before['optimization']-before['assessment'],
            plan007_optimization=before['optimization'],plan007_assessment=before['assessment'])
    write(output/'support.json',dict(edges=support,cameras=counts,extraction=read(folder/'result.json')['cameras'],
        reconstructed_from_saved_partition=True,no_original_trajectory_or_duplicate_family_leakage=True))
    passed=decision['status']=='passed'
    numerical=decision['status'] in ['numerical_failure','solver_timeout','deterministic_tie_break_timeout']
    return dict(status='passed' if passed else 'blocked',terminal_kind=None if passed else 'numerical_failure' if numerical else 'scientific_rejection',
        blockers=[] if passed else [decision['status']],eligible_groups=len(groups),rejected_components=len(rejected),
        rejected_reasons=dict(Counter(g['reason'] for g in rejected)),passed_edges=sum(e['passed'] for e in support),
        edges_below_24=[dict(a=e['a'],b=e['b'],eligible_groups=e['eligible_groups']) for e in support if e['eligible_groups']<24],
        partition_status=decision['status'],model_configurations_fitted=0)


def extraction_sources(path,p):
    frozen=read(path/'frozen.json')
    if frozen['config']!=p: raise ValueError('extracted predecessor configuration mismatch')
    extractor='scripts/basketball_shared_tracks_v2.py'
    if frozen['source_sha256'][extractor]!=sha256(extractor): raise ValueError('extraction implementation changed')
    folder=path/'tracks'; result=read(folder/'result.json')
    if result['status']!='complete' or result['role']!='fit' or sorted(c['camera_id'] for c in result['cameras'])!=list(range(34)):
        raise ValueError('extracted predecessor incomplete or wrong role')
    sources={str(path/'frozen.json'):sha256(path/'frozen.json'),str(folder/'result.json'):sha256(folder/'result.json'),
        **result['source_sha256'],**{str(folder/f"camera{c['camera_id']}-tracks.json"):c['sha256'] for c in result['cameras']}}
    verify_hashes(sources)
    return sources


def stage_sources(p,config,prior_path):
    sources={str(config):sha256(config),**{s:sha256(s) for s in SCRIPTS}}
    if prior_path:
        r=read(prior_path/'result.json'); sources.update(r['source_sha256'])
        sources[str(prior_path/'result.json')]=sha256(prior_path/'result.json')
        # Reject code changes between stages as well as altered predecessor files.
        verify_hashes(sources)
    else: sources.update(historical_sources(p))
    return sources


def worker(a):
    started=time.monotonic(); p=read(a.config); validate_config(p); bounded(p,a.stage=='package')
    prior=None
    stages={'associate':{'prepare'},'safeguard':{'associate'},'fit':{'safeguard'},'assess':{'fit'},'select':{'assess'},'package':{'prepare','associate','safeguard','fit','assess','select'}}
    if a.stage!='prepare':
        if a.predecessor is None: raise ValueError('hashed predecessor required')
        prior=predecessor(a.predecessor,sha256(a.config),stages[a.stage])
        if a.stage!='package' and prior['status']!='passed': raise ValueError('blocked predecessor: '+str(prior['blockers']))
    if a.stage in ['safeguard','fit','assess','select']:
        raise ValueError('production implementation deferred until Plan008 support admission; no qualifying evidence')
    sources=stage_sources(p,a.config,a.predecessor)
    if a.extracted_predecessor:
        if a.stage!='associate': raise ValueError('extraction reuse only applies to association')
        sources.update(extraction_sources(a.extracted_predecessor,p))
    a.output.mkdir(parents=True,exist_ok=False)
    write(a.output/'frozen.json',dict(config=p,source_sha256=sources))
    try:
        if a.stage=='prepare':
            result=dict(status='passed',blockers=[],reused_audit=str(Path(p['prior_audit'])/'result.json'),estimator_audit_rerun=False)
        elif a.stage=='associate': result=associate(p,a.output,a.extracted_predecessor)
        else:
            if prior['status']!='blocked': raise ValueError('package requires an evidenced terminal blocker')
            for name in ['support.json','groups.json','membership.json','partition.json']:
                if (a.predecessor/name).exists(): shutil.copyfile(a.predecessor/name,a.output/name)
            result=dict(status='blocked',blockers=prior['blockers'],terminal_kind=prior['terminal_kind'],blocked_stage=prior['stage'],
                model_configurations_fitted=0)
        verify_hashes(sources)
    except TimeoutError as error:
        result=dict(status='blocked',terminal_kind='budget_exhaustion',blockers=[str(error)])
    usage=resource.getrusage(resource.RUSAGE_SELF)
    result.update(schema='basketball-shared-timing-stage/v2',stage=a.stage,config_sha256=sha256(a.config),source_sha256=sources,
        wall_seconds=time.monotonic()-started,investigation_elapsed_seconds=time.time()-p['investigation_started_unix'],
        process_cpu_seconds=usage.ru_utime+usage.ru_stime,maximum_rss_kib=usage.ru_maxrss,cpu_threads_limit=8,gpu_seconds=0,
        candidate_offsets=None,accepted_timing=None,roles=p['roles'],selection_previously_consumed=True,
        selection_consumed_this_attempt=False,final_validation_consumed=False,
        artifacts_sha256={str(f):sha256(f) for f in sorted(a.output.rglob('*.json'))})
    write(a.output/'result.json',result)
    print('stage',a.stage,result['status'],result['blockers'],flush=True)
    return int(result['status']=='blocked')


def watchdog(a):
    p=read(a.config); validate_config(p); bounded(p,a.stage=='package')
    if a.output.exists(): raise FileExistsError('fresh output required: '+str(a.output))
    reserve=0 if a.stage=='package' else p['packaging_reserve_seconds']
    seconds=p['investigation_started_unix']+p['maximum_cpu_seconds']-reserve-time.time()
    command=[sys.executable,str(Path(__file__)),*sys.argv[1:],'--worker']
    child=subprocess.Popen(command,start_new_session=True)
    try: return child.wait(timeout=max(.001,seconds))
    except subprocess.TimeoutExpired:
        os.killpg(child.pid,signal.SIGTERM)
        try: child.wait(timeout=2)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid,signal.SIGKILL); child.wait()
        a.output.mkdir(parents=True,exist_ok=True)
        # The watchdog preserves partial work, but does not claim stage success.
        sources={str(a.config):sha256(a.config),**{s:sha256(s) for s in SCRIPTS}}
        if a.predecessor: sources[str(a.predecessor/'result.json')]=sha256(a.predecessor/'result.json')
        write(a.output/'result.json',dict(schema='basketball-shared-timing-stage/v2',stage=a.stage,status='blocked',
            terminal_kind='budget_exhaustion',blockers=['external watchdog terminated stage at shared deadline'],
            config_sha256=sha256(a.config),source_sha256=sources,
            artifacts_sha256={str(f):sha256(f) for f in sorted(a.output.rglob('*.json')) if f.name!='result.json'},
            candidate_offsets=None,accepted_timing=None,selection_consumed_this_attempt=False,final_validation_consumed=False,
            investigation_elapsed_seconds=time.time()-p['investigation_started_unix'],gpu_seconds=0))
        return 1


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['prepare','associate','safeguard','fit','assess','select','package'])
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--predecessor',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--extracted-predecessor',type=Path,help='Reuse a complete hash-verified fitting extraction with identical config and extractor')
    parser.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args()
    raise SystemExit(worker(args) if args.worker else watchdog(args))
