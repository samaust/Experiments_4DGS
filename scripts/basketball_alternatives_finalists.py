"""Finite five-frame/seed/support/policy matrix for the selected complete routes."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
from basketball_alternatives_protocol import EARLY,LATE
from basketball_audit import sha256


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',type=Path,required=True)
    p.add_argument('--methods',nargs='+',choices=['incremental','global','da3','map-anything','mast3r'])
    p.add_argument('--native-only',action='store_true')
    a=p.parse_args()
    root=Path(__file__).resolve().parents[1];w=a.workspace.resolve()
    selected=a.methods or [r['method'] for r in json.loads((w/'screening.json').read_text())['ranking'][:3]]
    if not selected or len(selected)>3:
        raise ValueError('need one to three ranked complete routes')
    env=os.environ.copy()
    for key,relative in [('TORCH_HOME','.local/cache/torch'),('HF_HOME','.local/cache/huggingface'),('MPLCONFIGDIR','.local/cache/matplotlib')]:
        env[key]=str(root/relative)
    env['PYTHONDONTWRITEBYTECODE']='1'
    cm_python=str(root/'.local/envs/calibration-global/bin/python')
    def run(output,command):
        if output.exists():
            result=output/'result.json'
            if result.exists() and json.loads(result.read_text())['status'] in ('complete','incomplete'):
                print('reuse',output.name,flush=True);return
            raise ValueError(f'failed or partial job needs inspection: {output}')
        print('run',output.name,flush=True)
        log=w/(output.name+'.log');start=time.monotonic()
        with log.open('x') as stream:
            proc=subprocess.run(command,cwd=root,env=env,stdout=stream,stderr=subprocess.STDOUT)
        record=dict(command=command,exit_code=proc.returncode,wall_seconds=time.monotonic()-start,log_sha256=sha256(log))
        (w/(output.name+'-command.json')).write_text(json.dumps(record,indent=2)+'\n')
        if proc.returncode:
            raise RuntimeError(f'job failed ({proc.returncode}); inspect {log}')
    for method in selected:
        for seed in (0,1,2):
            for side,frames in [('early',EARLY),('late',LATE)]:
                for sharp in (False,True):
                    support='sharp-' if sharp else ''
                    features=w/f'pooled-{support}{side}'
                    # Learned native inference is identical for the two feature
                    # support policies; record one prediction and reuse it.
                    tag=support if method in ('incremental','global') else ''
                    native=w/f'{method}-window-{tag}{side}-seed{seed}'
                    if method in ('incremental','global'):
                        command=[cm_python,str(root/'scripts/basketball_alternatives_colmap.py'),method,
                                 '--source',str(features),'--output',str(native),'--seed',str(seed)]
                    else:
                        command=[str(root/f'.local/envs/calibration-{method}/bin/python'),
                            str(root/'scripts/basketball_alternatives_learned.py'),'--method',method,
                            '--source',str(w/'sources'/method),'--weights',str(w/'weights'/method),
                            '--inputs',str(w/'inputs'),'--frames',*map(str,frames),'--seed',str(seed),'--output',str(native)]
                    run(native,command)
                    r=json.loads((native/'result.json').read_text())
                    if r['status']!='complete':
                        print('reject incomplete',native.name,flush=True);continue
                    if a.native_only:continue
                    for policy in ('fixed','focal','radial'):
                        output=w/f'{method}-ba-{support}{policy}-{side}-seed{seed}'
                        command=[cm_python,str(root/'scripts/basketball_alternatives_refine.py'),'refine',
                            '--source',str(features),'--native',str(native/f"calibration-{r['model_id']}.json"),
                            '--policy',policy,'--seed',str(seed),'--output',str(output)]
                        run(output,command)
                        log=output.with_suffix('.log').read_text()
                        if 'NO_CONVERGENCE' in log.split('Termination :')[-1]:
                            extended=output.with_name(output.name+'-iter1000')
                            extended_command=command.copy()
                            extended_command[-1]=str(extended)
                            extended_command+=['--iterations','1000','--extend-from',str(output)]
                            run(extended,extended_command)


if __name__=='__main__':main()
