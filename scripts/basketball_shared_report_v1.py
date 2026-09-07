"""Publish compact, hash-bound Plan007 blocker evidence from completed stages."""
import argparse
from collections import Counter
from pathlib import Path
import shutil
import time
import numpy as np
from basketball_audit import sha256
from basketball_scale import read,write
from basketball_continuation_audit import verify_hashes
from basketball_shared_timing_v1 import predecessor


def summarize(rows):
    errors=[abs(r['relative_recovery_error_frames']) for r in rows if r['relative_recovery_error_frames'] is not None]
    coverage=[r['conditional_interval_covers_shifted_baseline'] for r in rows if r['conditional_interval_covers_shifted_baseline'] is not None]
    return dict(curves=len(rows),score_gates_passed=sum(r['passed'] for r in rows),
        qualifying_timing_curves=0,blocker_counts=dict(Counter(b for r in rows for b in r['blockers'])),
        identifiable_relative_comparisons=len(errors),
        absolute_relative_error_median_frames=float(np.median(errors)) if errors else None,
        absolute_relative_error_p95_frames=float(np.quantile(errors,.95)) if errors else None,
        conditional_coverage_count=len(coverage),conditional_coverage_fraction=float(np.mean(coverage)) if coverage else None,
        support_median=float(np.median([r['support'] for r in rows])),
        median_speed_pixels_per_frame=float(np.median([r['median_speed_pixels_per_frame'] for r in rows if r['median_speed_pixels_per_frame'] is not None])) if any(r['median_speed_pixels_per_frame'] is not None for r in rows) else None,
        median_acceleration_pixels_per_frame2=float(np.median([r['median_acceleration_pixels_per_frame2'] for r in rows if r['median_acceleration_pixels_per_frame2'] is not None])) if any(r['median_acceleration_pixels_per_frame2'] is not None for r in rows) else None)


def publish(a):
    config=read(a.config);digest=sha256(a.config)
    audit=predecessor(a.audit,digest,{'audit'})
    associate=predecessor(a.association,digest,{'associate'})
    package=predecessor(a.package,digest,{'package'})
    if audit['status']!='passed' or associate['status']!='blocked' or package['status']!='blocked':
        raise ValueError('this report only supports the audited admission blocker')
    raw=read(a.audit/'real-audit.json');verify_hashes(raw['source_sha256'])
    sources={str(f):sha256(f) for folder in [a.audit,a.association,a.package] for f in sorted(folder.rglob('*.json'))}
    sources.update({str(a.config):digest,str(Path(__file__)):sha256(__file__)})
    # The old ledger must still match the previous published selection evidence.
    previous=read('docs/experiments/basketball-timing-selection/evidence.json')
    ledger='.local/calibration/basketball-v1/gpu-ledger.json'
    verify_hashes({ledger:previous['ledger_sha256']})
    a.output.mkdir(parents=True,exist_ok=False)
    summaries=[]
    for length in [25,50]:
        for search in ['full_unchanged','local_nonqualifying']:
            for estimator in ['absolute','temporal_bias']:
                rows=[r for row in raw['rows'] if row['window'][1]-row['window'][0]+1==length and row['search']==search and row['estimator']==estimator for r in row['injections']]
                summaries.append(dict(length=length,search=search,estimator=estimator,**summarize(rows)))
    per_edge=[dict(**{k:row[k] for k in ['a','b','window','estimator','search']},**summarize(row['injections'])) for row in raw['rows']]
    write(a.output/'audit-summary.json',dict(by_window_length=summaries,per_edge=per_edge,
        interpretation='Score-gate passes in local diagnostics do not qualify timing. Coverage is conditional on the estimated unshifted lag, not absolute ground-truth coverage. Null denotes unsupported or ambiguous recovery.'))
    for folder,names in [(a.audit,['synthetic-audit.json']),(a.association,['support.json','groups.json'])]:
        for name in names:shutil.copyfile(folder/name,a.output/name)
    write(a.output/'result.json',dict(status='blocked',blocker='inadequate multiview support',
        failed_edges=associate['failed_edges'],passed_edges=associate['passed_edges'],
        eligible_groups=associate['eligible_groups'],rejected_reasons=associate['rejected_reasons'],
        cameras=associate['cameras'],candidate_offsets=None,accepted_timing=None,
        model_configurations_fitted=0,selection_consumed_this_attempt=False,selection_previously_consumed=True,
        final_validation_consumed=False,implemented_stages=['audit','associate','package'],
        deferred_at_blocker=['spline optimization','independent nuisance trajectory assessment','selection reevaluation','final-validation protocol'],
        role_frames=config['roles']))
    write(a.output/'resources.json',dict(audit_wall_seconds=audit['wall_seconds'],association_wall_seconds=associate['wall_seconds'],
        package_wall_seconds=package['wall_seconds'],successful_stage_wall_seconds=sum(r['wall_seconds'] for r in [audit,associate,package]),
        elapsed_since_investigation_freeze_seconds=time.time()-config['investigation_started_unix'],
        limit_wall_seconds=14400,gpu_seconds=0,model_configurations_fitted=0,predeclared_configurations=6,
        failed_attempts=[dict(stage='audit startup',wall_seconds=.465799199,error='TypeError: dict() got multiple values for keyword argument; fixed provenance-map merge before output creation')],
        accounting='Elapsed since freeze includes implementation, tests, failed startup, stage execution and packaging. Initial read-only repository inspection preceded the freeze. No GPU/training charge.',
        ledger_sha256=sha256(ledger)))
    tests={}
    for suite in ['basketball','budget','selfcap']:
        source=Path(f'/tmp/plan007-{suite}-tests.log');target=a.output/f'{suite}-tests.log'
        shutil.copyfile(source,target);tests[str(target)]=sha256(target)
    write(a.output/'evidence.json',dict(source_sha256=sources,immutable_sha256=audit['source_sha256'],
        artifact_sha256={str(f):sha256(f) for f in sorted(a.output.iterdir()) if f.is_file()},
        test_logs_sha256=tests,config_sha256=digest,
        source_commands=[f'.local/envs/calibration-global/bin/python scripts/basketball_shared_timing_v1.py {stage} --config {a.config} '+
          ('' if stage=='audit' else f'--predecessor {pre} ')+f'--output {folder}' for stage,pre,folder in [('audit',None,a.audit),('associate',a.audit,a.association),('package',a.association,a.package)]]))
    verify_hashes(sources)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['config','audit','association','package','output']:parser.add_argument('--'+name,type=Path,required=True)
    publish(parser.parse_args())
