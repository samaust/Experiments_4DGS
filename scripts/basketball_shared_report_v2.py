"""Publish hash-bound Plan008 evidence after admitted support and a later blocker."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import argparse
from collections import Counter,defaultdict
from pathlib import Path
import shutil
import time
import sys
import cv2
import scipy
import numpy as np
from basketball_audit import sha256
from basketball_scale import read,write
from basketball_continuation_audit import verify_hashes
from basketball_shared_timing_v1 import predecessor
from basketball_shared_timing_v2 import bounded


def compact_controls(folder):
    rows=[];invalid=[]
    for file in sorted(folder.glob('case*.json')):
        try:row=read(file)
        except (ValueError,OSError) as error:invalid.append(dict(path=str(file),error=str(error)));continue
        result=row.pop('result')
        production=row.pop('production_result',None)
        if production is not None:row['production_starts_summary']=[{k:r.get(k) for k in ['start','converged','nfev','objective','error']} for r in production['starts']]
        if 'profiles' in result:
            row['profiles']={label:{k:v for k,v in profile.items() if k!='group_profile_costs'} for label,profile in result['profiles'].items()}
            row['estimator_gates_passed']=result['passed']
            row['group_profiles_and_optimizer_traces_path']=str(file)
        else:
            row['starts']=[{k:r.get(k) for k in ['start','converged','status','message','nfev','njev','objective','optimality','boundary_cameras','positive_depth','error']} for r in result['starts']]
            row['maximum_start_disagreement_frames']=result['maximum_start_disagreement_frames']
        rows.append(row)
    return rows,invalid


def summarize(rows):
    groups=defaultdict(list)
    for row in rows:
        c=row['configuration'];groups[c['knot_spacing_frames'],c['acceleration_weight'],row['motion'],row['length'],row['noise_pixels']].append(row)
    summary=[]
    for (spacing,weight,motion,length,noise),items in groups.items():
        errors=[v for row in items for v in row['absolute_errors_frames']]
        summary.append(dict(knot_spacing_frames=spacing,acceleration_weight=weight,motion=motion,length=length,noise_pixels=noise,
            controls=len(items),required_noiseless_controls=sum(r['required_noiseless_recovery'] for r in items),
            safeguards_failed=sum(r['safeguard_passed'] is False for r in items),pending_identifiability_audits=sum(r['safeguard_passed'] is None for r in items),
            converged_starts=sum(r['converged'] for row in items for r in row['starts']),
            absolute_error_median_frames=float(np.median(errors)) if errors else None,
            absolute_error_maximum_frames=max(errors) if errors else None))
    return summary


def plot_failure(output,control_path):
    os.environ['MPLCONFIGDIR']='/tmp/plan008-matplotlib'
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    case=read(control_path);result=case['result'];regularized=result['profiles']['regularized'];data=result['profiles']['data_only']
    if not regularized.get('grid'):return None
    grid=next(r['grid'] for r in result['optimizer_traces'] if r['weight']==0.)
    valid=np.array([[v is not None for v in row] for row in data['group_profile_costs']])
    fig,axes=plt.subplots(2,1,figsize=(10,6),layout='constrained')
    axes[0].plot(regularized['grid'],regularized['cost_pixels'],color='#225c9a')
    axes[0].axvline(case['delta'],color='#111111',ls='--',lw=1,label=f"True lag {case['delta']:+.2f}")
    axes[0].set(ylabel='Regularized profile score',title='Regularized profile passes; this alone cannot qualify timing')
    axes[0].legend(loc='upper right');axes[0].grid(alpha=.2)
    image=axes[1].imshow(valid.astype(int),origin='lower',aspect='auto',interpolation='nearest',
        extent=[min(grid)-.5,max(grid)+.5,-.5,len(valid)-.5],vmin=0,vmax=1,cmap=ListedColormap(['#d9544d','#cce3d5']))
    axes[1].set(xlabel='Independent lag: camera 2 relative to camera 1 (frames)',ylabel='Synthetic multiview group',
        title=f"Data-only fits: {(~valid).sum()} missing solves, {valid.all(axis=1).sum()}/{len(valid)} complete full-search curves")
    axes[1].set_yticks(range(len(valid)))
    colorbar=fig.colorbar(image,ax=axes[1],ticks=[0,1],fraction=.025,pad=.02)
    colorbar.ax.set_yticklabels(['No convergence','Converged'])
    fig.suptitle(f"Noiseless {case['length']}-frame direction-change safeguard; true offset {case['delta']:+.2f} frames")
    destination=output/'independent-failure.svg';fig.savefig(destination,metadata={'Date':None});plt.close(fig)
    destination.write_text('\n'.join(line.rstrip() for line in destination.read_text().splitlines())+'\n')
    return dict(path=str(destination),matplotlib_version=matplotlib.__version__,missing_data_only_solves=int((~valid).sum()))


def publish(a):
    p=read(a.config);bounded(p,package=True);digest=sha256(a.config)
    folders={'prepare':a.prepare,'associate':a.associate,'terminal':a.terminal,'package':a.package}
    stages={name:predecessor(folder,digest,{'safeguard','fit','assess','select'} if name=='terminal' else {name}) for name,folder in folders.items()}
    if any(stages[s]['status']!='passed' for s in ['prepare','associate']) or any(stages[s]['status']!='blocked' for s in ['terminal','package']):
        raise ValueError('publisher requires admitted support and an evidenced later blocker')
    sources={str(f):sha256(f) for folder in folders.values() for f in sorted(folder.rglob('*.json'))}
    for r in stages.values():sources.update(r['source_sha256'])
    sources.update({str(a.config):digest,str(Path(__file__)):sha256(__file__)})
    masks=read(a.associate/'tracks/result.json')['source_sha256'];verify_hashes(masks);sources.update(masks)
    old=read(p['prior_evidence'])
    for key in ['source_sha256','immutable_sha256','artifact_sha256','test_logs_sha256']:verify_hashes(old[key])
    ledger='.local/calibration/basketball-v1/gpu-ledger.json'
    verify_hashes({ledger:read('docs/experiments/basketball-timing-selection/evidence.json')['ledger_sha256']})
    a.output.mkdir(parents=True,exist_ok=False)
    for name in ['support.json','groups.json','membership.json','partition.json']:shutil.copyfile(a.associate/name,a.output/name)
    optimizer,invalid_optimizer=compact_controls(a.terminal/'optimizer-controls')
    profiles,invalid_profiles=compact_controls(a.terminal/'independent-controls')
    targeted,invalid_targeted=compact_controls(a.terminal/'targeted-controls')
    failed=[r for r in optimizer if r['safeguard_passed'] is False]
    failed_profiles=[r for r in profiles if r['safeguard_passed'] is False]
    plot=plot_failure(a.output,failed_profiles[0]['group_profiles_and_optimizer_traces_path']) if failed_profiles else None
    write(a.output/'synthetic-summary.json',dict(optimizer_controls_attempted=len(optimizer),planned_optimizer_controls=1890,
        optimizer_matrix_complete=len(optimizer)==1890,independent_controls_attempted=len(profiles),planned_independent_controls=117,
        independent_matrix_complete=len(profiles)==117,optimizer_summary=summarize(optimizer),failed_optimizer_controls=failed,
        failed_independent_controls=failed_profiles,independent_controls=profiles,targeted_identifiability_controls=targeted,failed_targeted_controls=[r for r in targeted if r['safeguard_passed'] is False],
        incomplete_artifacts=invalid_optimizer+invalid_profiles+invalid_targeted,
        interpretation='Synthetic optimizer errors are diagnostics, not timing qualification. Negative controls need not recover arbitrary truth. Noiseless recovery is required only after independent identifiability; long noiseless positive controls must also establish that evidence. Short unidentifiable/unsupported controls remain unqualified. Limits remain0.05 frames noiseless and0.25 for qualified noisy cases. Missing controls remain unexecuted.'))
    write(a.output/'optimizer-controls.json',dict(rows=optimizer))
    terminal=stages['terminal']
    write(a.output/'result.json',dict(status='blocked',terminal_kind=terminal['terminal_kind'],blockers=terminal['blockers'],
        blocked_stage=terminal['stage'],support_admission='passed',eligible_groups=stages['associate']['eligible_groups'],
        partition_status='passed',candidate_offsets=None,accepted_timing=None,
        model_configurations_fitted_to_real_data=terminal.get('model_configurations_fitted_to_real_data',0),
        selection_previously_consumed=True,selection_consumed_this_attempt=False,final_validation_consumed=False,
        implemented_stages=['prepare','associate','safeguard','fit','assess','package'],
        selection_adapter_status='guarded; completion conditional on passing fitting qualification',
        role_frames=p['roles']))
    write(a.output/'configuration-assessments.json',dict(configurations=[dict(**c,status='not_run_on_real_observations',reason='synthetic safeguards did not pass') for c in p['configurations']],
        real_spline_parameters=None,real_independent_profiles=None,real_group_bootstrap_intervals=None))
    interrupted=[]
    root=Path('.local/calibration/basketball-rev2/shared-v2')
    for archive,prepares in [('interrupted-implementation',['prepare']),('association-interrupted-implementation',['prepare-batched']),('synthetic-interrupted-implementation',[]),('guard-correction-implementation',[])]:
        path=root/archive/'attempt.json'
        if not path.exists():continue
        row=read(path);verify_hashes(row['source_archive_sha256']);sources.update(row['source_archive_sha256']);sources[str(path)]=sha256(path)
        partial=Path(row['partial_output']);frozen=read(partial/'frozen.json')
        rebound={str(path.parent/Path(name).name) if (path.parent/Path(name).name).exists() else name:digest for name,digest in frozen['source_sha256'].items()}
        verify_hashes(rebound);sources.update(rebound)
        row.update(exit_code=1 if row['status']=='superseded_invalid_guard' else 241,termination_signal=None if row['status']=='superseded_invalid_guard' else 'SIGTERM',elapsed_since_stage_frozen_seconds=row['ended_unix']-(partial/'frozen.json').stat().st_mtime,
            optimizer_controls_preserved=len(list((partial/'optimizer-controls').glob('case*.json'))))
        interrupted.append(row)
        for folder in [partial,*[root/name for name in prepares]]:sources.update({str(f):sha256(f) for f in folder.rglob('*.json')})
    original_package=root/'package'
    if original_package.exists() and original_package!=a.package:
        original=read(original_package/'result.json')
        rebound={str(root/'guard-correction-implementation'/Path(name).name) if (root/'guard-correction-implementation'/Path(name).name).exists() else name:digest for name,digest in original['source_sha256'].items()}
        verify_hashes(rebound);verify_hashes(original['artifacts_sha256']);sources.update(rebound)
        sources.update({str(f):sha256(f) for f in original_package.rglob('*.json')})
    failures=[dict(stage='identifiability guard development',error='A motion label was incorrectly treated as proof of short-window identifiability',outcome='Corrected to the user plan: independent data-only evidence determines whether recovery is required. All thresholds, configurations and existing fits remain unchanged; original rejection is superseded.'),dict(stage='test fixture development',error='FileExistsError from exclusive-create write used to mutate an existing test fixture',outcome='test fixture corrected before extraction'),
        dict(stage='edit command',error='/bin/bash: line 1: python: command not found',outcome='used installed calibration interpreter; no dependency download'),
        dict(stage='held-out estimator development',error='SciPy one-dimensional bounded TRF/LSMR: IndexError: index 1 is out of bounds for axis 1 with size 1',
            outcome='joint production solver remains sparse TRF/LSMR; separate held-out estimation profiles scalar lag against frozen trajectories and refines integer basins')]
    failure_audit=None
    if a.failure_audit:
        failure_audit=read(a.failure_audit/'result.json')
        audit_sources={str(root/'guard-correction-implementation'/Path(name).name) if (root/'guard-correction-implementation'/Path(name).name).exists() else name:digest for name,digest in failure_audit['source_sha256'].items()}
        verify_hashes(audit_sources);verify_hashes(failure_audit['artifacts_sha256'])
        sources.update({str(f):sha256(f) for f in a.failure_audit.glob('*.json')});sources.update(audit_sources)
        shutil.copyfile(a.failure_audit/'result.json',a.output/'failure-audit.json')
        shutil.copyfile(a.failure_audit/'profiles.json',a.output/'failure-profiles.json')
    write(a.output/'resources.json',dict(environment=dict(python=sys.version,opencv=cv2.__version__,scipy=scipy.__version__),
        investigation_started_unix=p['investigation_started_unix'],elapsed_seconds=time.time()-p['investigation_started_unix'],
        limit_elapsed_seconds=14400,packaging_reserve_seconds=1200,cpu_threads_limit=8,
        extraction_wall_seconds=read(a.associate/'tracks/result.json')['wall_seconds'],
        stages={name:{k:r.get(k) for k in ['wall_seconds','process_cpu_seconds','child_cpu_seconds','maximum_rss_kib','investigation_elapsed_seconds']} for name,r in stages.items()},
        interrupted_attempts=interrupted,development_failures=failures,failure_audit_wall_seconds=failure_audit['wall_seconds'] if failure_audit else None,plot=plot,gpu_seconds=0,ledger_sha256=sha256(ledger),
        archived_source_verification='Earlier v2 code hashes are verified against byte-identical archived Python sources; data/config/video hashes retain their original paths. Plan007 hashes are unchanged.',
        accounting='Elapsed includes first inspection, implementation, tests, failed/interrupted commands, extraction and reporting. Profile pool has at most eight single-thread CPU workers. No downloads, GPU work, initialization or training.'))
    logs={}
    for path in sorted(Path('/tmp').glob('plan008-*.log')):
        target=a.output/path.name.removeprefix('plan008-');shutil.copyfile(path,target);logs[str(target)]=sha256(target)
    for suite in ['basketball','budget','selfcap']:
        shutil.copyfile(a.output/f'{suite}-final-tests.log',a.output/f'{suite}-tests.log')
        logs[str(a.output/f'{suite}-tests.log')]=sha256(a.output/f'{suite}-tests.log')
    commands=[]
    for name,folder in folders.items():
        stage=stages[name]['stage'];script='basketball_shared_timing_v2.py' if name in ['prepare','associate'] else 'basketball_shared_workflow_v2.py'
        before=None if name=='prepare' else a.prepare if name=='associate' else a.associate if name=='terminal' else a.terminal
        command=f'.local/envs/calibration-global/bin/python scripts/{script} {stage} --config {a.config} '+('' if before is None else f'--predecessor {before} ')+f'--output {folder}'
        if name=='associate':command+=' --extracted-predecessor '+read(a.associate/'extraction-reused.json')['predecessor']
        if name=='terminal' and terminal.get('reused_optimizer_controls',0):command+=f' --controls-predecessor {root}/safeguard-parallel --controls-archive {root}/guard-correction-implementation'
        commands.append(command)
    if a.failure_audit:
        commands.append(f'.local/envs/calibration-global/bin/python scripts/basketball_shared_failure_audit_v2.py --config {a.config} --safeguard {root}/safeguard-parallel --case 798 --output {a.failure_audit}')
    write(a.output/'evidence.json',dict(source_sha256=sources,immutable_sha256=stages['prepare']['source_sha256'],
        artifact_sha256={str(f):sha256(f) for f in sorted(a.output.iterdir()) if f.is_file()},test_logs_sha256=logs,
        config_sha256=digest,source_commands=commands,prior_audit_reused=True,prior_evidence_sha256=sha256(p['prior_evidence'])))
    verify_hashes(sources)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['config','prepare','associate','terminal','package','output']:parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--failure-audit',type=Path)
    publish(parser.parse_args())
