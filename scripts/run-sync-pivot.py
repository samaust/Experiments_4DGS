"""Serial GPU attempt supervisor for Plan 024, preserving campaign and training ledgers."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from training_budget import TrainingBudget, atomic_json
from training_supervisor import supervise


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--allocation',choices=['visualsync','sync-nerf','stg-full','freetimegs','evaluation'],required=True)
    p.add_argument('--role',required=True)
    p.add_argument('--seconds',type=float,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--docker-image')
    p.add_argument('--container-name')
    p.add_argument('command',nargs=argparse.REMAINDER)
    a=p.parse_args()
    if a.command and a.command[0]=='--':a.command=a.command[1:]
    if not a.command or not 35<a.seconds<=14400:p.error('bounded command and valid duration required')
    cap={'stg-full':1200,'freetimegs':1200,'sync-nerf':2400,'evaluation':3600,'visualsync':14400}[a.allocation]
    if a.seconds>cap:p.error('per-attempt allocation exceeded')
    if a.allocation in ('stg-full','freetimegs'):
        allowed={f'{a.allocation}-basketball-{condition}-seed{seed}'
                 for condition in ('zero','corrected') for seed in range(3)}
        if a.role not in allowed:p.error('unknown reconstruction scientific attempt')
    if a.allocation=='sync-nerf':
        allowed={'syncnerf-box','syncnerf-panoptic'}|{f'syncnerf-basketball-seed{i}' for i in range(3)}
        if a.role not in allowed:p.error('unknown Sync-NeRF scientific attempt')
        if a.role in ('syncnerf-box','syncnerf-panoptic') and a.seconds>1800:
            p.error('benchmark run exceeds 1800 seconds')
    if bool(a.docker_image)!=bool(a.container_name):p.error('Docker image and unique container name required together')
    root=Path(__file__).resolve().parents[1]
    ledger_path=root/'docs/research/basketball-sync-pivot/gpu-budget.json'
    with ledger_path.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        ledger=json.loads(ledger_path.read_text())
        if any(x['status']=='reserved' for x in ledger['attempts']):
            p.error('unresolved prior reservation; confirm shutdown and account before another GPU job')
        if any(x['role']==a.role for x in ledger['attempts']):
            p.error('role already consumed; scientific replacement attempts prohibited')
        used=sum(x['charged_seconds'] for x in ledger['attempts'])
        allocation_used=sum(x['charged_seconds'] for x in ledger['attempts'] if x['allocation']==a.allocation)
        if used+a.seconds>ledger['limit_seconds'] or allocation_used+a.seconds>ledger['allocation_limits_seconds'][a.allocation]:
            p.error('insufficient remaining campaign allocation')
        command=a.command
        if a.docker_image:
            command=['docker','run','--rm','--name',a.container_name,'--network','none','--gpus','all',
                     '--user',f'{os.getuid()}:{os.getgid()}', '-e','TRAINING_STOP_MONOTONIC',
                     '-e','MPLCONFIGDIR=/tmp/matplotlib','--entrypoint',a.command[0],
                     '-v',f'{root}:{root}','-w',str(root),a.docker_image,*a.command[1:]]
        a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=False)
        training=None
        if a.allocation in ('stg-full','freetimegs'):
            training=TrainingBudget(root/'.local/runs/plan-004-training-budget.json',method=a.allocation,scene='vru-basketball-dg')
            training.__enter__()
            if training.available<a.seconds:
                training.__exit__(None,None,None);p.error('insufficient central training budget')
        started=time.monotonic()
        attempt=dict(allocation=a.allocation,role=a.role,status='reserved',reserved_seconds=a.seconds,
                     charged_seconds=a.seconds,started_unix_seconds=time.time(),runner_pid=os.getpid(),
                     container=a.container_name,command=command,output=str(a.output))
        ledger['attempts'].append(attempt);atomic_json(ledger_path,ledger)
        try:
            if training:training.start(command=command,provenance={'plan':24,'role':a.role},seconds=a.seconds)
            with (a.output/'supervisor.log').open('w') as stream:
                result=supervise(command,cwd=root,log=stream,seconds=a.seconds-(time.monotonic()-started))
            if a.container_name:
                # A Docker client can exit before its container. Check only this
                # attempt's recorded name, never stop unrelated containers.
                active=subprocess.check_output(['docker','ps','-q','--filter',f'name=^/{a.container_name}$'],text=True).strip()
                if active:subprocess.run(['docker','kill',a.container_name],check=True,timeout=10)
            status='deadline' if result['stop_requested'] else 'completed' if result['exit_code']==0 else 'failed'
            if training:training.finish(status)
            elapsed=time.monotonic()-started
            attempt.update(status=status,charged_seconds=elapsed,wall_seconds=elapsed)
            atomic_json(ledger_path,ledger);atomic_json(a.output/'supervisor-result.json',result)
            print(json.dumps(dict(role=a.role,**result),indent=2))
            if elapsed>a.seconds:raise RuntimeError('GPU attempt overrun recorded; stop campaign')
            if result['exit_code']!=0:
                print((a.output/'supervisor.log').read_text()[-5000:],file=sys.stderr)
                raise SystemExit(result['exit_code'])
        finally:
            if training:training.__exit__(None,None,None)
            # On interruption retain the entire GPU reservation. The supervisor
            # kills host descendants; Docker attempts require explicit name stop.
            if a.container_name and attempt['status']=='reserved':
                subprocess.run(['docker','kill',a.container_name],timeout=10,check=False)


if __name__=='__main__':main()
