"""Verify historical coverage using detected minima or complete flat intervals."""
import argparse
import gzip
import json
import math
from pathlib import Path
import time
from basketball_scale import read,write
from basketball_audit import sha256

def unpack(p):
    with gzip.open(p,'rt') as f:return json.load(f)

def agrees(a,b):return abs(a-b)<=1e-6+1e-4*max(abs(a),abs(b))

def verify(root,output):
    if output.exists():raise FileExistsError('fresh coverage verification required')
    policy=read('configs/basketball-rev2/timing-shared-v8.json');refs=unpack(root/'prepare/diagnostic-manifest.json.gz')['historical']
    result=[];flat_issues=[];states={}
    for f in (root/'basins').glob('weight1.0*.json.gz'):
        s=unpack(f)
        if not any((r['group_id'],r['lag'])==(s['group_id'],s['lag']) for r in refs):continue
        curves={d:{float(x):r for x,r in c.items()} for d,c in s['curves'].items()};grid=sorted(curves['cold']);candidates=set()
        for d,curve in curves.items():
            expected=[]
            for i,x in enumerate(grid):
                row=curve[x]
                if not row['valid']:continue
                neighbors=[curve[grid[j]] for j in [i-1,i+1] if 0<=j<len(grid)]
                if all(n['valid'] and row['objective']<=n['objective'] for n in neighbors):expected.append(x)
            assert expected==s['minima'][d]
            candidates.update(expected)
        valid_flats=[]
        for lo,hi in s['flat_intervals']:
            points=[k/100 for k in range(round(lo*100),round(hi*100)+1)]
            values=[curves[d][x]['objective'] for d in curves for x in points if x in curves[d] and curves[d][x]['valid']]
            good=len(values)==3*len(points) and agrees(min(values),max(values))
            if good:valid_flats.append([lo,hi])
            else:flat_issues.append(dict(group_id=s['group_id'],lag=s['lag'],interval=[lo,hi],reason='incomplete or total spread exceeds agreement tolerance'))
        def no_worse(x,ref):
            rows=[c[x] for c in curves.values()]
            return all(r['valid'] and (r['objective']<=ref['objective'] or agrees(r['objective'],ref['objective'])) for r in rows) and all(agrees(rows[0]['objective'],r['objective']) for r in rows)
        for ref in refs:
            if (ref['group_id'],ref['lag'])!=(s['group_id'],s['lag']):continue
            matches=[x for x in sorted(candidates) if abs(x-ref['nuisance_offset'])<=.05+1e-12 and no_worse(x,ref)]
            flats=[iv for iv in valid_flats if iv[0]<=ref['nuisance_offset']<=iv[1] and all(no_worse(k/100,ref) for k in range(round(iv[0]*100),round(iv[1]*100)+1))]
            result.append(dict(**ref,recovered=bool(matches or flats),matching_detected_minima=matches,verified_covering_flat_intervals=flats,source_sha256=sha256(f)))
        if time.time()>=policy['investigation_started_unix']+14400:raise TimeoutError('packaging deadline')
    assert len(result)==9
    write(output,dict(status='passed',historical_basins_verified=sum(r['recovered'] for r in result),references=result,flat_interval_issues=flat_issues,worker_coverage_claim=sum(r['recovered'] for r in read(root/'basins/basin-decision.json')['coverage']),verifier_sha256=sha256(__file__)))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    a=parser.parse_args();verify(a.root,a.output)
