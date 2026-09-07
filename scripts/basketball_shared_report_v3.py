"""Publish Plan009 terminal evidence without changing historical artifacts."""
import os
for name in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:os.environ[name]='1'
import argparse
from collections import Counter
from pathlib import Path
import shutil
import time
import numpy as np
from basketball_audit import sha256
from basketball_scale import read,write
from basketball_continuation_audit import verify_hashes
from basketball_shared_solver_v3 import provenance
from basketball_shared_workflow_v3 import bounded


def publish(a):
    p=read(a.config);bounded(p,package=True)
    stages={name:read(a.root/name/'result.json') for name in ['prepare','diagnose','safeguard','package']}
    if stages['package']['status']!='blocked':raise ValueError('documented blocker required')
    sources={}
    for name,stage in stages.items():
        verify_hashes(stage['source_sha256']);verify_hashes(stage['artifacts_sha256'])
        sources.update(stage['source_sha256']);sources.update(stage['artifacts_sha256'])
        sources[str(a.root/name/'result.json')]=sha256(a.root/name/'result.json')
    manifest=read(a.root/'prepare/cross-version-manifest.json');verify_hashes(manifest['source_sha256'])
    sources.update(manifest['source_sha256'])
    freeze=read(a.root/'safeguard/evaluator-freeze.json');verify_hashes(freeze['source_sha256']);sources.update(freeze['source_sha256'])
    a.output.mkdir(parents=True,exist_ok=False)
    for name in ['cross-version-manifest.json','controls-reuse.json']:
        shutil.copyfile(a.root/'prepare'/name,a.output/name)
    shutil.copyfile(a.root/'package/result.json',a.output/'result.json')
    shutil.copyfile(a.root/'safeguard/evaluator-freeze.json',a.output/'evaluator-freeze.json')
    diagnostics=[]
    for file in sorted((a.root/'diagnose').glob('comparison[0-9]*.json')):
        row=read(file)
        solvers={}
        for name,r in row['solvers'].items():
            solvers[name]={k:r[k] for k in ['valid','converged','status','message','objective','nfev','njev','optimality','wall_seconds','gradient_l2','gradient_inf','jacobian_shape','structurally_inactive_columns']}
            for point in ['initial','final']:
                solvers[name][point]={k:v for k,v in r[point].items() if k!='residual'}
            solvers[name]['raw_residuals_and_coefficients']=str(file)
        diagnostics.append({**row,'solvers':solvers})
    write(a.output/'solver-comparisons.json',dict(provenance=provenance(),problems=diagnostics,
        objective_agreement='abs(F1-F2) <= 1e-6 + 1e-4 * max(abs(F1),abs(F2)); F=sum(residual**2)',
        dense_reference_is_local=True,agreement_does_not_certify_identifiability=True))
    retest=read(a.root/'safeguard/exact-retest/result.json')
    stats={};attempt_rows=[]
    for trace in retest['result']['optimizer_traces']:
        name='data_only' if trace['weight']==0 else 'regularized'
        rows=[]
        for state in trace['states']:
            for lag,attempts in state['attempts'].items():
                for r in attempts:
                    rows.append(r)
                    attempt_rows.append(dict(group_id=state['group_id'],weight=trace['weight'],lag=float(lag),
                        **{k:r.get(k) for k in ['start','seed_lag','seed_start','problem_key','cache_key','valid','converged','positive_depth','boundary_cameras','nfev','njev','objective','optimality','status','message','error','wall_seconds','jacobian_shape','jacobian_bytes']}))
        stats[name]=dict(total_attempts=len(rows),valid_attempts=sum(r['valid'] for r in rows),
            failed_attempts=sum(not r['valid'] for r in rows),negative_depth_attempts=sum(not r.get('positive_depth',True) for r in rows),evaluation_cap_hits=sum(r.get('nfev')==200 and not r['converged'] for r in rows),
            attempts_by_start=dict(Counter(r['start'] for r in rows)),
            failures_by_start=dict(Counter(r['start'] for r in rows if not r['valid'])),
            solve_wall_seconds=sum(r.get('wall_seconds',0.) for r in rows))
    profiles=retest['result']['profiles']
    write(a.output/'exact-retest.json',dict(**{k:v for k,v in retest.items() if k!='result'},
        recipe=dict(motion='direction_changes',length=100,noise_pixels=0.,known_offset_frames=-.1,groups=12,knot_spacing_frames=10,acceleration_weight=1.),
        profiles=profiles,attempt_statistics=stats,raw_profiles_and_initializations=str(a.root/'safeguard/exact-retest/result.json')))
    write(a.output/'initialization-attempts.json',dict(attempts=attempt_rows,full_states=str(a.root/'safeguard/exact-retest/result.json')))
    write(a.output/'qualification.json',dict(exact_retest_passed=retest['safeguard_passed'],
        planned_independent_controls=117,independent_controls_attempted=stages['safeguard'].get('independent_controls_attempted',0),
        planned_targeted_controls=3,targeted_controls_attempted=stages['safeguard'].get('targeted_controls_attempted',0),
        reused_production_controls=1890,production_independent_qualification='unqualified: mandatory exact retest failed before matrix',
        benchmark_status='not reached: safeguards failed',runtime_projection=None,
        real_configurations=[dict(configuration=c,status='unassessed',reason='required synthetic safeguard failed') for c in p['configurations']],
        selection_adapter='conditional implementation not reached',selection_consumed_this_attempt=False,
        final_validation_consumed=False,final_validation_protocol=None,candidate_offsets=None,accepted_timing=None))
    write(a.output/'resources.json',dict(investigation_started_unix=p['investigation_started_unix'],
        clock_origin='2026-09-07 21:33:00 UTC; conservatively rounded down before the first inspection tool call',
        elapsed_seconds=time.time()-p['investigation_started_unix'],limit_seconds=14400,computation_limit_seconds=13200,
        early_retest_limit_seconds=5400,cpu_workers_limit=8,numerical_threads_per_worker=1,gpu_seconds=0,downloads=0,
        solver=provenance(),stages={k:{f:v.get(f) for f in ['wall_seconds','process_cpu_seconds','child_cpu_seconds','maximum_rss_kib','investigation_elapsed_seconds']} for k,v in stages.items()}))
    plot(a.output,profiles)
    write(a.output/'evidence.json',dict(source_sha256=sources,
        artifacts_sha256={str(f):sha256(f) for f in a.output.iterdir()},
        historical_evidence_sha256=sha256(p['prior_evidence']),report_script_sha256=sha256(__file__),
        accepted_timing=None,prior_plan007_audit_reused=True))


def plot(output,profiles):
    os.environ['MPLCONFIGDIR']='/tmp/plan009-matplotlib'
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,1,figsize=(10,6),layout='constrained')
    for ax,(name,row) in zip(axes,profiles.items()):
        for label,profile in [('best of three',row),*row['sweeps'].items()]:
            if profile.get('grid'):ax.plot(profile['grid'],profile['cost_pixels'],label=label)
        ax.axvline(-.1,color='black',ls='--',label='true lag −0.10')
        ax.set(title=f"{name}: {row['support']}/12 complete groups; passed={row['passed']}",ylabel='Profile score')
        ax.legend();ax.grid(alpha=.2)
    axes[-1].set_xlabel('Camera 2 relative to camera 1 (frames)')
    fig.savefig(output/'profiles.svg',metadata={'Date':None});plt.close(fig)
    file=output/'profiles.svg';file.write_text('\n'.join(l.rstrip() for l in file.read_text().splitlines())+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True);parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    publish(parser.parse_args())
