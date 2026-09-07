"""Publish native timing recovery and explicit cycle failures from saved evidence."""
import argparse
from pathlib import Path
import shutil

from basketball_audit import sha256
from basketball_continuation_audit import verify_hashes
from basketball_scale import read, write


def cycle_diagnostics(edges):
    neighbors={i:set() for i in range(34)}; directed={}
    for e in edges:
        if not e['passed']: continue
        a,b=e['a'],e['b']; neighbors[a].add(b); neighbors[b].add(a)
        directed[a,b]=e['lag']; directed[b,a]=-e['lag']
    parents={1:None}; offsets={1:0.}; pending=[1]; tree=set()
    while pending:
        c=pending.pop(0)
        for n in sorted(neighbors[c]):
            if n not in offsets:
                offsets[n]=offsets[c]+directed[c,n]; parents[n]=c
                tree.add(frozenset((c,n))); pending.append(n)
    if len(offsets)!=34: raise ValueError('diagnostic requires connected full rig')
    def ancestors(c):
        route=[]
        while c is not None:
            route.append(c); c=parents[c]
        return route
    cycles=[]
    for e in edges:
        if not e['passed']: continue
        a,b=e['a'],e['b']
        if frozenset((a,b)) in tree: continue
        pa,pb=ancestors(a),ancestors(b); common=next(c for c in pa if c in pb)
        route=pa[:pa.index(common)+1]+list(reversed(pb[:pb.index(common)]))+[a]
        closure=abs(sum(directed[x,y] for x,y in zip(route,route[1:])))
        cycles.append(dict(cameras=route,closure_frames=closure,passed=closure<=.25))
    covered={frozenset((a,b)) for c in cycles for a,b in zip(c['cameras'],c['cameras'][1:])}
    bridges=[list(e) for e in sorted({tuple(sorted(k)) for k in directed if frozenset(k) not in covered})]
    return dict(reachable_cameras=sorted(offsets),bridges=bridges,cycles=cycles)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',type=Path,required=True); p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(); local=a.workspace/'native-fit'; result=read(local/'result.json')
    verify_hashes(result['sha256']); verify_hashes(result['artifacts_sha256'])
    a.output.mkdir(parents=True,exist_ok=False)
    for name in ['result','fit','transitions','frozen']:
        value=read(local/(name+'.json'))
        # Preserve all numeric search curves, with one edge per line for review.
        import json
        edges=value.pop('edges',None)
        if edges is None: write(a.output/(name+'.json'),value)
        else:
            text=json.dumps(value,indent=2)[:-2]+',\n  "edges": [\n'+',\n'.join('    '+json.dumps(e) for e in edges)+'\n  ]\n}\n'
            (a.output/(name+'.json')).write_text(text)
            assert read(a.output/(name+'.json'))==read(local/(name+'.json'))
    cycles=cycle_diagnostics(result['edges']); write(a.output/'cycle-diagnostics.json',cycles)
    for name in ['fitting-preview.jpg','transition-preview.jpg']:
        shutil.copyfile(a.workspace/name,a.output/name)
    logs={str(f):sha256(f) for f in a.workspace.glob('*.log')}
    write(a.output/'evidence.json',dict(source_sha256={__file__:sha256(__file__)},
        local_result_sha256=sha256(local/'result.json'),logs_sha256=logs,
        ledger_sha256=sha256('.local/calibration/basketball-v1/gpu-ledger.json'),
        artifacts_sha256={str(f):sha256(f) for f in sorted(a.output.iterdir())},
        gpu_seconds=0,interpretation='CPU-only recovery; original GPU and training ledgers unchanged'))


if __name__=='__main__': main()
