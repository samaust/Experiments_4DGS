"""Plan 015 immutable admission, diagnostics and fail-closed stage packaging."""
import os
for name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:
    os.environ[name]='1'
import argparse
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time
from basketball_audit import sha256
from basketball_scale import read,write
from basketball_shared_provenance_v9 import verify_hashes

STAGES=['prepare','account','diagnose','adapt','benchmark','package']

def deadline(p,stage):
    return min(p['investigation_started_unix']+60*p['v9']['deadlines_minutes'][stage],p['investigation_started_unix']+(5400 if stage=='package' else 4500))


def check(p,stage):
    if time.time()>=deadline(p,stage):raise TimeoutError('absolute '+stage+' deadline')


def source_hashes(config,stage):
    names={'prepare':['audit'], 'account':['accounting','solver','regressions'], 'diagnose':['diagnose'],
           'adapt':['benchmark','solver','initialization','stopping'], 'benchmark':['benchmark','solver','initialization','stopping'], 'package':['report','verify']}[stage]
    files=['scripts/basketball_shared_workflow_v9.py','scripts/basketball_shared_provenance_v9.py','docs/experiments/basketball-shared-timing-v9/corrections/serialization.json',*['scripts/basketball_shared_'+n+'_v9.py' for n in names]]
    return {str(config):sha256(config),**{f:sha256(f) for f in files}}


def predecessor(a):
    if a.stage=='prepare':return None,{}
    if a.predecessor is None:raise ValueError('hashed predecessor required')
    file=a.predecessor/'result.json';prior=read(file)
    if prior['schema']!='basketball-shared-timing-stage/v9' or prior['config_sha256']!=sha256(a.config):raise ValueError('predecessor schema/config mismatch')
    verify_hashes(prior['source_sha256']);verify_hashes(prior['artifacts_sha256'])
    allowed={'account':['prepare'],'diagnose':['account'],'adapt':['diagnose'],'benchmark':['adapt'],'package':STAGES[:-1]}
    if prior['stage'] not in allowed[a.stage]:raise ValueError('predecessor stage mismatch')
    return prior,{**prior['source_sha256'],str(file):sha256(file)}


def finish(a,p,result,sources,started):
    usage=resource.getrusage(resource.RUSAGE_SELF)
    result.setdefault('executed_counts',None)
    result.update(schema='basketball-shared-timing-stage/v9',stage=a.stage,config_sha256=sha256(a.config),source_sha256=sources,
        artifacts_sha256={str(f):sha256(f) for f in sorted(a.output.rglob('*')) if f.is_file() and f.name!='result.json'},
        wall_seconds=time.monotonic()-started,elapsed_seconds=time.time()-p['investigation_started_unix'],maximum_rss_kib=usage.ru_maxrss,
        cpu_seconds=usage.ru_utime+usage.ru_stime,cpu_workers_limit=8,numerical_threads=1,gpu_seconds=0,
        candidate_offsets=None,accepted_timing=None,profiles=None,intervals=None,final_protocol=None,
        selection_consumed_this_attempt=False,final_validation_consumed=False,production_solver='immutable v2',model_configurations_fitted_to_real_data=0)
    write(a.output/'result.json',result)
    print(a.stage,result['status'],result.get('terminal_kind'),flush=True)
    return int(result['status']=='blocked')


def stage(a):
    p=read(a.config);started=time.monotonic()
    if a.output.exists():raise FileExistsError('fresh stage output required')
    prior,inherited=predecessor(a);sources={**inherited,**source_hashes(a.config,a.stage)}
    a.output.mkdir(parents=True)
    write(a.output/'frozen.json',dict(config=p,source_sha256=sources,frozen_unix=time.time(),namespace='v9-'+a.stage))
    try:
        check(p,a.stage)
        if a.stage=='package':
            from basketball_shared_report_v9 import package
            result=package(a.output,prior,a.predecessor,p)
        elif prior is not None and prior['status']!='passed':
            result=dict(status='blocked',terminal_kind=prior['terminal_kind'],blockers=prior['blockers'],scientific_solves=0,reason='predecessor gate failed')
        else:
            import importlib
            module={'prepare':'audit','account':'accounting','diagnose':'diagnose','adapt':'benchmark','benchmark':'benchmark'}[a.stage]
            implementation=importlib.import_module('basketball_shared_'+module+'_v9')
            result=getattr(implementation,a.stage)(p,a.output) if a.stage=='prepare' else getattr(implementation,a.stage)(p,a.output,a.predecessor)
        verify_hashes(sources)
    except TimeoutError as e:result=dict(status='blocked',terminal_kind='budget_exhaustion',blockers=[str(e)])
    except (ValueError,ArithmeticError,AssertionError,KeyError,ImportError,FileNotFoundError) as e:
        result=dict(status='blocked',terminal_kind='arithmetic_or_provenance_failure',blockers=[type(e).__name__+': '+str(e)])
    return finish(a,p,result,sources,started)


def terminate_group(child):
    try:os.killpg(child.pid,signal.SIGTERM)
    except ProcessLookupError:pass
    try:child.wait(timeout=2)
    except subprocess.TimeoutExpired:pass
    # Descendants can survive after the group leader exits; always kill the group.
    try:os.killpg(child.pid,signal.SIGKILL)
    except ProcessLookupError:pass
    child.wait()


def interrupted(a,p,reason,sources,started):
    a.output.mkdir(parents=True,exist_ok=True)
    frozen=a.output/'frozen.json'
    if not frozen.exists():write(frozen,dict(config=p,source_sha256=sources,worker_initialized=False))
    return finish(a,p,dict(status='blocked',terminal_kind='budget_exhaustion',blockers=[reason],worker_artifact_available=any(f.name!='frozen.json' for f in a.output.iterdir())),sources,started)


def main(a):
    if a.output.exists():raise FileExistsError('fresh stage output required')
    p=read(a.config);started=time.monotonic();sources=source_hashes(a.config,a.stage)
    try:
        _,inherited=predecessor(a);sources={**inherited,**sources}
    except (ValueError,KeyError,FileNotFoundError) as e:
        a.output.mkdir(parents=True)
        return finish(a,p,dict(status='blocked',terminal_kind='provenance_failure',blockers=[str(e)],worker_initialized=False),sources,started)
    remaining=deadline(p,a.stage)-time.time()
    if remaining<=0:return interrupted(a,p,'absolute deadline before worker initialization',sources,started)
    argv=[sys.executable,str(Path(__file__)),a.stage,'--config',str(a.config),'--output',str(a.output),'--worker']
    if a.predecessor is not None:argv+=['--predecessor',str(a.predecessor)]
    child=subprocess.Popen(argv,start_new_session=True)
    try:
        code=child.wait(timeout=remaining)
        if (a.output/'result.json').exists():return code
        a.output.mkdir(parents=True,exist_ok=True)
        return finish(a,p,dict(status='blocked',terminal_kind='numerical_failure',blockers=[f'worker exited {code} without result'],worker_exit_code=code),sources,started)
    except subprocess.TimeoutExpired:
        terminate_group(child)
        return interrupted(a,p,'external watchdog terminated entire worker process group',sources,started)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=STAGES);parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--predecessor',type=Path);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    a=parser.parse_args();raise SystemExit(stage(a) if a.worker else main(a))
