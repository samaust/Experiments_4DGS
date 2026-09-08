"""Package the Plan 011 terminal decision without rerunning scientific computation."""
import argparse
import shutil
import time
from pathlib import Path
from basketball_scale import read,write
from basketball_audit import sha256
from basketball_continuation_audit import verify_hashes


def package(root,output):
    if output.exists():raise FileExistsError('fresh publication required')
    p=read('configs/basketball-rev2/timing-shared-v5.json')
    if time.time()>=p['investigation_started_unix']+14400:raise TimeoutError('four-hour packaging deadline')
    terminal=read(root/'package-final/result.json')
    assert terminal['status']=='blocked'
    output.mkdir(parents=True)
    portable={};sources={}
    for stage in ['prepare-final','diagnose-final','pilot','package-final']:
        folder=root/stage
        if not folder.exists():continue
        result=read(folder/'result.json');verify_hashes(result['source_sha256']);verify_hashes(result['artifacts_sha256'])
        sources.update(result['source_sha256'])
        destination=output/stage;destination.mkdir()
        for f in sorted(folder.iterdir()):
            if not f.is_file():continue
            shutil.copyfile(f,destination/f.name)
            portable[str(f)]=dict(path=f'{stage}/{f.name}',sha256=sha256(f))
    # Preserve pre-pilot implementation/analysis failures, not as qualification evidence.
    failures=output/'pre-pilot-corrections';failures.mkdir()
    for stage in ['prepare','prepare-verified','diagnose','package']:
        folder=root/stage
        for name in ['result.json','frozen.json','cross-version-manifest.json','escape-decision.json','escape-audit.json.gz']:
            f=folder/name
            if f.exists():
                dst=failures/f'{stage}-{name}';shutil.copyfile(f,dst)
                portable[str(f)]=dict(path=str(dst.relative_to(output)),sha256=sha256(f))
    for name in ['prepare','prepare-verified','diagnose','package','prepare-final','diagnose-final','pilot','package-final',
                 'development','development-final','development-audit','basketball-tests','budget-tests','selfcap-tests']:
        f=Path('/tmp')/f'plan011-{name}.log'
        if f.exists():shutil.copyfile(f,output/f'{name}.log')
    import gzip,json,collections
    audit=output/'diagnose-final/escape-audit.json.gz'
    with gzip.open(audit,'rt') as stream:rays=json.load(stream)['records']
    pilot=read(output/'pilot/pilot-decision.json') if (output/'pilot/pilot-decision.json').exists() else None
    if pilot is not None:
        rows=[];profiles=[];comparisons=[]
        for artifact in pilot['artifacts']:
            with gzip.open(output/'pilot'/artifact['path'],'rt') as stream:state=json.load(stream)
            label='regularized' if state['weight'] else 'data_only'
            with gzip.open(Path('docs/experiments/basketball-shared-timing-v4')/f'{label}-group{state["group_id"]:02d}.json.gz','rt') as stream:old=json.load(stream)
            for lag,attempts in state['attempts'].items():
                rows.extend(attempts)
                baseline=old['attempts'].get(lag,[])
                comparisons.append(dict(group_id=state['group_id'],weight=state['weight'],lag=float(lag),
                    historical_problem_key=old['problem_key'] if baseline else None,
                    baseline_available=bool(baseline),v4=[{k:r.get(k) for k in ['start','valid','objective','nfev','optimality','minimum_normalized_depth','message']} for r in baseline],
                    v5=[{k:r.get(k) for k in ['start','valid','objective','nfev','optimality','minimum_normalized_depth','message']} for r in attempts]))
            grid=sorted(map(float,state['attempts']))
            profiles.append(dict(group_id=state['group_id'],weight=state['weight'],grid=grid,
                costs={direction:[next(r['objective'] if r['valid'] else None for r in state['attempts'][str(lag)] if r['start']==direction) for lag in grid]
                       for direction in ['cold','ascending','descending']},confidence_interval=None,qualification=False))
        write(output/'pilot-profiles.json',dict(profiles=profiles,sparse_diagnostic_only=True,bootstrap_interval=None))
        write(output/'v4-comparisons.json',dict(problems=comparisons,failed_states_are_not_certified_minima=True,fractional_baseline=None))
        import statistics
        failed=[r for r in rows if not r['valid']]
        write(output/'resources.json',dict(pilot_attempts=len(rows),pilot_qualified=sum(r['valid'] for r in rows),
            failures_by_objective=dict(collections.Counter('regularized' if r['weight'] else 'data_only' for r in failed)),
            failed_iteration_counts=sorted(set(r['solver_trace'][-1]['iteration'] for r in failed)),
            failed_distinct_objective_counts=sorted(set(r['nfev'] for r in failed)),
            failed_minimum_original_depth=min(r['minimum_normalized_depth'] for r in failed),
            median_failed_objective_evaluations=statistics.median(r['nfev'] for r in failed),
            solver_wall_seconds_sum=sum(r['wall_seconds'] for r in rows),
            initialization_seconds_sum=sum(r['initialization_seconds']+r['problem_initialization_seconds'] for r in rows),
            derivative_seconds_sum_inclusive=sum(r['derivative_seconds'] for r in rows),
            residual_seconds_sum=sum(r['residual_seconds'] for r in rows),
            serialized_attempt_bytes=sum(a['bytes'] for a in pilot['artifacts']),
            serialization_seconds=sum(a['serialization_seconds'] for a in pilot['artifacts']),
            maximum_worker_rss_kib=max(r['maximum_rss_kib'] for r in rows),workers=6,numerical_threads_per_worker=1,
            pilot_decision_elapsed_seconds=pilot['elapsed_seconds'],gpu_seconds=0,workload_projection=None))
    result=dict(terminal,plan='plans/plan_011.md',completion='documented blocker',
        escape_ray_classifications=dict(collections.Counter(r['classification'] for r in rays)),
        diagnostic_probe_count=sum(len(r['probes']) for r in rays),
        pilot=pilot,full_exact_retest=None,independent_controls=None,targeted_controls=None,
        workload_projection=None,fit=None,assessment=None,selection=None,final_validation_protocol=None,
        accepted_timing=None,candidate_offsets=None,investigation_elapsed_at_publication=time.time()-p['investigation_started_unix'])
    write(output/'result.json',result)
    write(output/'corrections.json',dict(
        first_prepare='Installed-source assertion expected fun; installed implementation uses f. Corrected before pilot.',
        first_audit='Initial comparison omitted feasible stalled v4 states. Verification resolved all 24 flagged rays using lower saved feasible objectives; no baseline optimization was rerun.',
        metadata='Corrected v5 cross-version new_config hash (initial copy named v4); historical manifests preserved.',
        second_pilot=False,numerical_policy_tuned=False,first_pilot_after_all_corrections=True))
    write(output/'evidence.json',dict(source_sha256=sources,
        report_script_sha256=sha256(__file__),portable_sources=portable,
        artifacts_sha256={str(f):sha256(f) for f in output.rglob('*') if f.is_file()},
        historical_v4_evidence_sha256=sha256(p['v4_evidence']),historical_v2_evidence_sha256=sha256(p['prior_evidence']),
        storage_bytes=sum(f.stat().st_size for f in output.rglob('*') if f.is_file()),
        selection_consumed_this_attempt=False,final_validation_consumed=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();package(args.root,args.output)
