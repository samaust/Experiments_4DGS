"""Execute the frozen B/C search once per workspace, with durable per-run evidence."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
from basketball_audit import sha256
from basketball_protocol import PROTOCOL
from basketball_recovery import EARLY,LATE,POLICIES
from basketball_pose_stability import compare_poses,load_candidate


def run_pair(workspace,config,sources,initial_pair=None):
    runs=[]
    for window,frames,source in zip(['early','late'],[EARLY,LATE],sources):
        target=workspace/(config['id']+'-'+window)
        command=[sys.executable,'scripts/basketball_recovery.py','--source',str(source),
                 '--priors',str(workspace/'retained-priors/result.json'),'--output',str(target),
                 '--frames',*map(str,frames),'--policy',config['policy']]
        if initial_pair:command+=['--initial-pair',*map(str,initial_pair)]
        started=time.monotonic()
        with target.with_suffix('.log').open('x') as log:
            try:code=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=1020).returncode
            except subprocess.TimeoutExpired:code=124
        runs.append(dict(window=window,command=command,exit_code=code,wall_seconds=time.monotonic()-started,
                         log_sha256=sha256(target.with_suffix('.log'))))
        print(config['id'],window,'exit',code,flush=True)
    entry=dict(config=config,runs=runs,sources=list(map(str,sources)),initial_pair=initial_pair)
    if all(r['exit_code']==0 for r in runs):
        folders=[workspace/(config['id']+'-'+w) for w in ['early','late']]
        entry['stability']=compare_poses(*load_candidate(folders[0]),*load_candidate(folders[1]))
        entry['result_hashes']=[sha256(f/'result.json') for f in folders]
        print('rotation',max(entry['stability']['rotation_degrees']),'center',max(entry['stability']['center_fraction_of_diameter']),flush=True)
    return entry


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',type=Path,required=True)
    p.add_argument('--stage',choices=['B','C'],required=True)
    a=p.parse_args();workspace=a.workspace
    manifest=json.loads((workspace/'search.json').read_text())
    if manifest['protocol']!=PROTOCOL:raise ValueError('wrong camera protocol')
    previous=json.loads((workspace/f'stage-{chr(ord(a.stage)-1)}.json').read_text())
    if any(e.get('stability',{}).get('passed') for e in previous):
        raise ValueError('previous stage has a fitting-pose candidate; validate before advancing')
    progress=workspace/f'stage-{a.stage}.json'
    with progress.open('x') as out:out.write('[]\n')
    results=[]
    if a.stage=='B':
        for config in manifest['stages']['B']:
            sources=[workspace/f'features-{config["recipe"]}-{w}' for w in ['early','late']]
            results.append(run_pair(workspace,config,sources))
            progress.write_text(json.dumps(results,indent=2)+'\n')
    else:
        from basketball_initial_pairs import inspect_pairs,rank_common
        for policy in POLICIES:
            complete=[e for e in previous if e['config']['policy']==policy and 'stability' in e]
            if not complete:
                results.append(dict(policy=policy,status='skipped',reason='no complete Stage B pair'))
                progress.write_text(json.dumps(results,indent=2)+'\n');continue
            def score(e):
                s=e['stability'];return max(max(s['rotation_degrees'])/.5,max(s['center_fraction_of_diameter'])/.01),e['config']['id']
            best=min(complete,key=score);sources=list(map(Path,best['sources']))
            early=inspect_pairs(sources[0]/'merged.db');late=inspect_pairs(sources[1]/'merged.db');pairs=rank_common(early,late)
            selection=dict(schema='basketball-initial-pairs/v1',protocol=PROTOCOL,policy=policy,source_configuration=best['config']['id'],
                           early=early,late=late,pairs=pairs,database_sha256=[sha256(s/'merged.db') for s in sources])
            with (workspace/f'initial-pairs-{policy}.json').open('x') as out:json.dump(selection,out,indent=2)
            for i in range(2):
                config=next(c for c in manifest['stages']['C'] if c['policy']==policy and c['recipe']==f'initial-pair-{i+1}')
                if i>=len(pairs):
                    results.append(dict(config=config,status='skipped',reason='no further pair eligible in both windows'))
                else:results.append(run_pair(workspace,config,sources,pairs[i]))
                progress.write_text(json.dumps(results,indent=2)+'\n')


if __name__=='__main__':main()
