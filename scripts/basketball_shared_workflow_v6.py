"""Plan 012 saved-state curvature investigation with cross-version admission and hard deadlines."""
import os
for name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:
    os.environ[name]='1'
import argparse
import ast
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
from pathlib import Path
import signal
import subprocess
import sys
import time
import resource
import numpy as np
from basketball_audit import sha256
from basketball_scale import read,write
from basketball_continuation_audit import verify_hashes
from basketball_shared_spline_v2 import SplineProblem
from basketball_shared_synthetic_v2 import synthetic
from basketball_shared_solver_v5 import provenance

IMPLEMENTATION=['scripts/basketball_shared_'+name+'_v6.py' for name in ['workflow','curvature','diagnose']]


def bounded(p, package=False, early=False):
    limit=14400 if package else (1800 if early else 13200)
    if time.time()>=p['investigation_started_unix']+limit:
        raise TimeoutError('shared investigation deadline: '+str(limit)+' elapsed seconds')


from basketball_shared_diagnose_v6 import prepare, diagnose


def stage(a):
    p=read(a.config);bounded(p,a.stage=='package',a.stage in ['prepare','diagnose','pilot']);started=time.monotonic()
    if a.output.exists():raise FileExistsError('fresh output required')
    sources={str(a.config):sha256(a.config),**{f:sha256(f) for f in IMPLEMENTATION}}
    if a.stage!='prepare':
        prior=read(a.predecessor/'result.json')
        allowed={'diagnose':{'prepare'},'pilot':{'diagnose'},'safeguard':{'pilot'},'benchmark':{'safeguard'},'fit':{'benchmark'},'assess':{'fit'},'select':{'assess'},'package':{'prepare','diagnose','pilot','safeguard','benchmark','fit','assess','select'}}
        if prior['stage'] not in allowed[a.stage] or prior['config_sha256']!=sha256(a.config):raise ValueError('hashed predecessor role/config mismatch')
        verify_hashes(prior['source_sha256']);verify_hashes(prior['artifacts_sha256'])
        if a.stage!='package' and prior['status']!='passed':raise ValueError('blocked predecessor')
        sources.update(prior['source_sha256']);sources[str(a.predecessor/'result.json')]=sha256(a.predecessor/'result.json')
    a.output.mkdir(parents=True,exist_ok=False)
    write(a.output/'frozen.json',dict(config=p,source_sha256=sources,solver=provenance(),frozen_unix=time.time()))
    try:
        if a.stage=='prepare':result=prepare(p,a.output)
        elif a.stage=='diagnose':result=diagnose(p,a.output,a.predecessor)
        elif a.stage=='pilot':
            decision=read(a.predecessor/'diagnostic-decision.json')
            if not decision['passed']:raise ValueError('diagnostic gate prevents all scientific solver calls')
            from basketball_shared_pilot_v6 import pilot
            result=pilot(p,a.output,a.predecessor)
        elif a.stage=='safeguard':
            from basketball_shared_profiles_v6 import safeguard
            result=safeguard(p,a.output)
        elif a.stage=='package':
            if prior['status']!='blocked':raise ValueError('terminal evidence required')
            result=dict(status='blocked',terminal_kind=prior['terminal_kind'],blockers=prior['blockers'],blocked_stage=prior['stage'])
        else:raise ValueError('conditional stage requires completed preceding qualification and implementation')
        verify_hashes(sources)
    except TimeoutError as error:result=dict(status='blocked',terminal_kind='budget_exhaustion',blockers=[str(error)])
    usage=resource.getrusage(resource.RUSAGE_SELF);children=resource.getrusage(resource.RUSAGE_CHILDREN)
    result.update(schema='basketball-shared-timing-stage/v6',stage=a.stage,config_sha256=sha256(a.config),source_sha256=sources,
        artifacts_sha256={str(f):sha256(f) for f in sorted(f for f in a.output.rglob('*') if f.is_file() and (f.suffix=='.json' or f.name.endswith('.json.gz')))},wall_seconds=time.monotonic()-started,
        process_cpu_seconds=usage.ru_utime+usage.ru_stime,child_cpu_seconds=children.ru_utime+children.ru_stime,maximum_rss_kib=usage.ru_maxrss,
        investigation_elapsed_seconds=time.time()-p['investigation_started_unix'],cpu_threads_limit=8,gpu_seconds=0,
        candidate_offsets=None,accepted_timing=None,selection_previously_consumed=True,selection_consumed_this_attempt=False,
        final_validation_consumed=False,model_configurations_fitted_to_real_data=0)
    write(a.output/'result.json',result);print(a.stage,result['status'],result['blockers'],flush=True)
    return int(result['status']=='blocked')


def main(a):
    if a.output.exists():raise FileExistsError('fresh output required')
    p=read(a.config);bounded(p,a.stage=='package',a.stage in ['prepare','diagnose','pilot'])
    limit=14400 if a.stage=='package' else 1800 if a.stage in ['prepare','diagnose','pilot'] else 5400 if a.stage=='safeguard' else 13200
    if time.time()>=p['investigation_started_unix']+limit:raise TimeoutError('stage deadline')
    child=subprocess.Popen([sys.executable,str(Path(__file__)),*sys.argv[1:],'--worker'],start_new_session=True)
    try:return child.wait(timeout=max(.001,p['investigation_started_unix']+limit-time.time()))
    except subprocess.TimeoutExpired:
        os.killpg(child.pid,signal.SIGTERM)
        try:child.wait(timeout=2)
        except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
        a.output.mkdir(parents=True,exist_ok=True)
        frozen=read(a.output/'frozen.json')
        write(a.output/'result.json',dict(schema='basketball-shared-timing-stage/v6',stage=a.stage,status='blocked',terminal_kind='budget_exhaustion',
            blockers=['external watchdog terminated stage at shared deadline'],config_sha256=sha256(a.config),source_sha256=frozen['source_sha256'],
            artifacts_sha256={str(f):sha256(f) for f in a.output.rglob('*.json') if f.name!='result.json'},
            candidate_offsets=None,accepted_timing=None,selection_consumed_this_attempt=False,final_validation_consumed=False,
            model_configurations_fitted_to_real_data=0,investigation_elapsed_seconds=time.time()-p['investigation_started_unix']))
        return 1


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['prepare','diagnose','pilot','safeguard','benchmark','fit','assess','select','package'])
    parser.add_argument('--config',type=Path,required=True);parser.add_argument('--predecessor',type=Path)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args();raise SystemExit(stage(args) if args.worker else main(args))
