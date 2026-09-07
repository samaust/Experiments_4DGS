"""Publish separately frozen timing selection and its acceptance evidence."""
import argparse
from collections import Counter
import json
from pathlib import Path
from basketball_audit import sha256
from basketball_continuation_audit import verify_hashes
from basketball_scale import read,write


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    a=parser.parse_args();run=a.workspace/'run';result=read(run/'result.json')
    verify_hashes(result['sha256']);verify_hashes(result['artifacts_sha256'])
    a.output.mkdir(parents=True,exist_ok=False)
    for name in ['result','frozen','selection-consumed']:
        value=read(run/(name+'.json'));edges=value.pop('edges',None)
        if edges is None:write(a.output/(name+'.json'),value)
        else:
            text=json.dumps(value,indent=2)[:-2]+',\n  "edges": [\n'+',\n'.join('    '+json.dumps(e) for e in edges)+'\n  ]\n}\n'
            (a.output/(name+'.json')).write_text(text)
            assert read(a.output/(name+'.json'))==read(run/(name+'.json'))
    rejection=Counter(b for e in result['edges'] for b in e['full']['blockers'])
    write(a.output/'summary.json',dict(status=result['status'],frozen_edges=len(result['edges']),
        passing_edges=sum(e['passed'] for e in result['edges']),full_window_rejection_counts=dict(rejection),
        failed_temporal_half_checks=sum(not all(h['passed'] for h in e['halves']) for e in result['edges']),
        half_disagreement_failures=sum(e['half_disagreement_frames'] is not None and e['half_disagreement_frames']>.25 for e in result['edges']),
        fitting_disagreement_failures=sum(e['fitting_disagreement_frames'] is not None and e['fitting_disagreement_frames']>.25 for e in result['edges']),
        track_counts=read(run/'tracks/result.json')['cameras'],worker_seconds=result['wall_seconds'],gpu_seconds=0))
    write(a.output/'evidence.json',dict(source_sha256={str(Path(__file__)):sha256(__file__)},
        result_sha256=sha256(run/'result.json'),logs_sha256={str(p):sha256(p) for p in a.workspace.glob('*.log')},
        ledger_sha256=sha256('.local/calibration/basketball-v1/gpu-ledger.json'),
        artifacts_sha256={str(p):sha256(p) for p in sorted(a.output.iterdir())}))


if __name__=='__main__':main()
