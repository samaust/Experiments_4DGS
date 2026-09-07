"""Publish full-resolution loop refinement without changing accepted timing."""
import argparse
import json
from pathlib import Path
from basketball_audit import sha256
from basketball_continuation_audit import verify_hashes
from basketball_scale import read,write
from basketball_timing_advertising_package import cycle_diagnostics


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    a=parser.parse_args();run=a.workspace/'run';result=read(run/'result.json')
    verify_hashes(result['sha256']);verify_hashes(result['artifacts_sha256'])
    a.output.mkdir(parents=True,exist_ok=False)
    for name in ['result','fit','frozen']:
        value=read(run/(name+'.json'));edges=value.pop('edges',None)
        if edges is None:write(a.output/(name+'.json'),value)
        else:
            text=json.dumps(value,indent=2)[:-2]+',\n  "edges": [\n'+',\n'.join('    '+json.dumps(e) for e in edges)+'\n  ]\n}\n'
            (a.output/(name+'.json')).write_text(text)
            assert read(a.output/(name+'.json'))==read(run/(name+'.json'))
    try:
        cycles=cycle_diagnostics(result['edges'])
    except ValueError:
        cycles=dict(status='unavailable',reason='full-rig graph disconnected')
    write(a.output/'cycle-diagnostics.json',cycles)
    prior=read('docs/experiments/basketball-advertising-recovery/result.json')
    previous={(e['a'],e['b']):e for e in prior['edges']}
    fits=read(run/'fit.json');rows=[]
    for edge in fits['edges']:
        key=edge['a'],edge['b'];refined=edge.get('refined',edge['integer'])
        rows.append(dict(a=key[0],b=key[1],prior_lag=previous[key]['lag'],new_lag=edge['lag'],passed=edge['passed'],
                         support=refined['support'],bootstrap_95_frames=refined.get('bootstrap_95_frames'),
                         subset_difference_frames=edge.get('subsets',{}).get('lag_difference_frames'),blockers=refined['blockers']))
    write(a.output/'comparison.json',dict(edges=rows,prior_sha256=sha256('docs/experiments/basketball-advertising-recovery/result.json')))
    write(a.output/'evidence.json',dict(source_sha256={str(Path(__file__)):sha256(__file__)},
        result_sha256=sha256(run/'result.json'),track_counts=read(run/'tracks/result.json')['cameras'],
        logs_sha256={str(p):sha256(p) for p in a.workspace.glob('*.log')},
        ledger_sha256=sha256('.local/calibration/basketball-v1/gpu-ledger.json'),
        artifacts_sha256={str(p):sha256(p) for p in sorted(a.output.iterdir())},gpu_seconds=0,worker_seconds=result['wall_seconds']))


if __name__=='__main__':main()
