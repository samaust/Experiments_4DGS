"""Audit a frozen synthetic failure without changing its stopping decision."""
import os
for name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[name]='1'
import argparse
from pathlib import Path
import time
from basketball_audit import sha256
from basketball_scale import read,write
from basketball_continuation_audit import verify_hashes
from basketball_shared_timing_v1 import predecessor
from basketball_shared_timing_v2 import bounded
from basketball_shared_synthetic_v2 import synthetic
from basketball_shared_spline_v2 import independent_edge


def run(a):
    p=read(a.config);bounded(p);prior=predecessor(a.safeguard,sha256(a.config),{'safeguard'})
    if prior['status']!='blocked':raise ValueError('frozen safeguard failure required')
    case_path=a.safeguard/'optimizer-controls'/f'case{a.case:04d}.json';case=read(case_path)
    if case['safeguard_passed']:raise ValueError('case did not fail')
    sources={**prior['source_sha256'],str(a.safeguard/'result.json'):sha256(a.safeguard/'result.json'),str(case_path):sha256(case_path),str(Path(__file__)):sha256(__file__)}
    verify_hashes(sources);a.output.mkdir(parents=True,exist_ok=False)
    write(a.output/'frozen.json',dict(source_sha256=sources,case_id=a.case,role='synthetic failure audit only'))
    started=time.monotonic();groups,cameras,truth,window=synthetic(case['motion'],case['noise_pixels'],case['known_offset_frames'],case['length'],groups=3)
    result=independent_edge(groups,cameras,dict(a=1,b=2),window,case['configuration']['knot_spacing_frames'],case['configuration']['acceleration_weight'],
        check=lambda:bounded(p),minimum_groups=3,workers=3,deadline=p['investigation_started_unix']+13200)
    write(a.output/'profiles.json',result);verify_hashes(sources)
    write(a.output/'result.json',dict(status='diagnostic_complete',case_id=a.case,known_offset_frames=truth[2],
        regularized_lag=result['profiles']['regularized']['lag'],data_only_lag=result['profiles']['data_only']['lag'],
        source_sha256=sources,artifacts_sha256={str(f):sha256(f) for f in a.output.glob('*.json')},
        wall_seconds=time.monotonic()-started,investigation_elapsed_seconds=time.time()-p['investigation_started_unix'],
        synthetic_groups=3,minimum_groups_for_this_diagnostic=3,real_minimum_groups_unchanged=12,
        qualifies_timing=False,candidate_offsets=None,accepted_timing=None,safeguard_stopping_decision_unchanged=True,
        selection_consumed_this_attempt=False,final_validation_consumed=False,
        interpretation='Exact three-group failing synthetic fixture; independently fit nuisance profiles without the failed production offsets or coefficients. Three-group intervals cannot qualify a real edge.'))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['config','safeguard','output']:parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--case',type=int,required=True)
    run(parser.parse_args())
