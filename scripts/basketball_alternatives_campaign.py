"""Execute finite snapshot jobs serially; retain failures and stop on errors.

Successful existing jobs are reused explicitly; a failed job is never overwritten
or retried automatically. Resolve its recorded cause before scheduling a new run.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from basketball_alternatives_protocol import SNAPSHOT_PAIRS
from basketball_audit import sha256


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',type=Path,required=True)
    p.add_argument('--methods',nargs='+',choices=['global','incremental','mast3r','da3','map-anything'],required=True)
    a=p.parse_args()
    root=Path(__file__).resolve().parents[1]
    workspace=a.workspace.resolve()
    env=os.environ.copy()
    env['TORCH_HOME']=str(root/'.local/cache/torch')
    env['HF_HOME']=str(root/'.local/cache/huggingface')
    env['MPLCONFIGDIR']=str(root/'.local/cache/matplotlib')
    env['PYTHONDONTWRITEBYTECODE']='1'
    jobs=[]
    for method in a.methods:
        for pair in SNAPSHOT_PAIRS:
            for frame in pair:
                if method in ('global','incremental'):
                    python=root/'.local/envs/calibration-global/bin/python'
                    script=root/'scripts/basketball_alternatives_colmap.py'
                    frontend=workspace/f'frontend-{frame}'
                    jobs.append((frontend,[str(python),str(script),'frontend','--source',str(workspace/'inputs'),
                                 '--frame',str(frame),'--output',str(frontend)]))
                    output=workspace/f'{method}-{frame}'
                    jobs.append((output,[str(python),str(script),method,'--source',str(frontend),'--output',str(output)]))
                else:
                    python=root/f'.local/envs/calibration-{method}/bin/python'
                    output=workspace/f'{method}-{frame}'
                    jobs.append((output,[str(python),str(root/'scripts/basketball_alternatives_learned.py'),
                        '--method',method,'--source',str(workspace/'sources'/method),
                        '--weights',str(workspace/'weights'/method),'--inputs',str(workspace/'inputs'),
                        '--frame',str(frame),'--output',str(output)]))
    for output,command in jobs:
        result=output/'result.json'
        if output.exists():
            if result.exists() and json.loads(result.read_text())['status'] in ('matched','complete','incomplete'):
                print('reuse',output.name,flush=True)
                continue
            raise ValueError(f'previous incomplete/failed job requires inspection: {output}')
        print('run',output.name,flush=True)
        start=time.monotonic()
        log=workspace/(output.name+'.log')
        with log.open('x') as stream:
            proc=subprocess.run(command,env=env,cwd=root,stdout=stream,stderr=subprocess.STDOUT)
        record=dict(command=command,exit_code=proc.returncode,wall_seconds=time.monotonic()-start,
                    log_sha256=sha256(log),result_sha256=sha256(result) if result.exists() else None)
        (workspace/(output.name+'-command.json')).write_text(json.dumps(record,indent=2)+'\n')
        if proc.returncode:
            print('failed',output.name,'see',log,flush=True)
            return proc.returncode
    return 0


if __name__=='__main__':
    raise SystemExit(main())
