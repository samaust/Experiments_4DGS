"""Publish v4 terminal evidence, retaining complete traces in portable gzip JSON."""
import os
for name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:os.environ[name]='1'
import argparse
from collections import Counter
import gzip
from pathlib import Path
import shutil
import time
from basketball_audit import sha256
from basketball_scale import read,write
from basketball_continuation_audit import verify_hashes
from basketball_shared_solver_v4 import provenance
from basketball_shared_solver_v3 import objective_agreement
from basketball_shared_workflow_v4 import bounded


def compressed_copy(source,destination):
    with open(source,'rb') as src,open(destination,'wb') as raw:
        with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as dst:shutil.copyfileobj(src,dst)


def publish(a):
    p=read(a.config);bounded(p,package=True)
    folders=dict(prepare='prepare-validated',diagnose='diagnose-validated',safeguard='safeguard',package='package')
    stages={k:read(a.root/v/'result.json') for k,v in folders.items()}
    if stages['package']['status']!='blocked':raise ValueError('terminal blocker required')
    sources={}
    for name,stage in stages.items():
        verify_hashes(stage['source_sha256']);verify_hashes(stage['artifacts_sha256'])
        sources.update(stage['source_sha256']);sources.update(stage['artifacts_sha256'])
        f=a.root/folders[name]/'result.json';sources[str(f)]=sha256(f)
    sources[p['diagnostic_evidence']]=sha256(p['diagnostic_evidence'])
    historical=read(p['diagnostic_evidence'])
    for key in ['source_sha256','artifacts_sha256']:
        verify_hashes(historical[key]);sources.update(historical[key])
    a.output.mkdir(parents=True,exist_ok=False)
    for name in ['cross-version-manifest.json','controls-reuse.json']:shutil.copyfile(a.root/folders['prepare']/name,a.output/name)
    shutil.copyfile(a.root/'package/result.json',a.output/'result.json')
    shutil.copyfile(a.root/'safeguard/evaluator-freeze.json',a.output/'evaluator-freeze.json')
    diagnostic=read(a.root/folders['diagnose']/'diagnosis.json');summaries=[]
    for entry in diagnostic['attempts']:
        f=Path(entry['artifact']);row=read(f);compressed=a.output/(f.stem+'.json.gz');compressed_copy(f,compressed)
        probes=[]
        for probe in row['probes']:
            compact={k:v for k,v in probe.items() if k not in ['residual','observations']}
            if 'objective' in probe:
                saved=row['states']['source_seed' if probe['origin']=='seed' else 'destination_final']['objective']
                compact.update(saved_objective=saved,agrees_with_saved=objective_agreement(probe['objective'],saved),
                               improves_saved=probe['objective']<saved)
            probes.append(compact)
        states={}
        for name,state in row['states'].items():
            states[name]={k:v for k,v in state.items() if k not in ['residual','observations']}
            depths=[z for o in state['observations'] for z in o['normalized_depth']]
            states[name].update(min_normalized_depth=min(depths),max_normalized_depth=max(depths),
                max_abs_normalized_coordinate=max(abs(v) for o in state['observations'] for xyz in o['normalized_xyz'] for v in xyz))
        summaries.append(dict(**entry,states=states,probe_count=entry['probes'],probe_details=probes,portable_full_evidence=compressed.name))
    write(a.output/'coefficient-diagnostics.json',dict(**{k:v for k,v in diagnostic.items() if k!='attempts'},attempts=summaries))
    raw_file=a.root/'safeguard/exact-retest/result.json'
    retest=read(raw_file);stats={};ledger=[]
    for trace in retest['result']['optimizer_traces']:
        name='data_only' if trace['weight']==0 else 'regularized';rows=[]
        for state in trace['states']:
            for lag,attempts in state['attempts'].items():
                for row in attempts:
                    rows.append(row);transfer=row.get('initialization_transfer',{})
                    ledger.append(dict(group_id=state['group_id'],weight=trace['weight'],lag=float(lag),
                        **{k:row.get(k) for k in ['start','seed_lag','seed_start','problem_key','cache_key','valid','converged','positive_depth',
                            'boundary_cameras','nfev','objective','optimality','constraint_violation','minimum_normalized_depth','constraint_boundary_dependent',
                            'status','message','error','wall_seconds','constraint_evaluations','factorization_warnings']},
                        iterations=len(row.get('solver_trace',[])),
                        final_barrier_parameter=(row['solver_trace'][-1]['barrier_parameter'] if row.get('solver_trace') else None),
                        replaced_blocks=transfer.get('replaced_blocks'),blend_fraction=transfer.get('blend_fraction'),
                        initial_depth_checks=transfer.get('checks')))
        stats[name]=dict(total_attempts=len(rows),valid_attempts=sum(r['valid'] for r in rows),
            failed_attempts=sum(not r['valid'] for r in rows),converged_attempts=sum(r['converged'] for r in rows),
            negative_depth_attempts=sum(not r.get('positive_depth',True) for r in rows),
            iteration_ceiling_hits=sum(len(r.get('solver_trace',[]))>=200 and not r['converged'] for r in rows),
            objective_ceiling_hits=sum(r.get('nfev',0)==200 and not r['converged'] for r in rows),
            attempts_by_start=dict(Counter(r['start'] for r in rows)),failures_by_start=dict(Counter(r['start'] for r in rows if not r['valid'])),
            failure_messages=dict(Counter(r.get('message') or r.get('error') for r in rows if not r['valid'])),
            solve_wall_seconds=sum(r.get('wall_seconds',0.) for r in rows),
            replaced_initializations=sum(bool(r.get('initialization_transfer',{}).get('replaced_blocks')) for r in rows),
            blended_initializations=sum(r.get('initialization_transfer',{}).get('blend_fraction') not in [None,1.] for r in rows),
            constraint_boundary_dependent=sum(r.get('constraint_boundary_dependent',False) for r in rows),
            factorization_warning_count=sum(len(r.get('factorization_warnings',[])) for r in rows))
    # Publish each group once; directional dictionaries in raw JSON duplicate attempts.
    portable_groups=[]
    import json
    for trace in retest['result']['optimizer_traces']:
        label='data_only' if trace['weight']==0 else 'regularized'
        for state in trace['states']:
            target=a.output/f"{label}-group{state['group_id']:02d}.json.gz"
            compact={k:v for k,v in state.items() if k not in ['cold','ascending','descending']}
            with open(target,'wb') as raw_stream:
                with gzip.GzipFile(filename='',mode='wb',fileobj=raw_stream,mtime=0) as zipped:
                    with __import__('io').TextIOWrapper(zipped,encoding='utf8') as text_stream:
                        json.dump(compact,text_stream,separators=(',',':'),allow_nan=False)
            portable_groups.append(dict(weight=trace['weight'],group_id=state['group_id'],path=target.name))
    write(a.output/'profile-groups.json',dict(groups=portable_groups,directions='reconstruct by each attempt start field; no duplicate solver records'))
    profiles=retest['result']['profiles']
    for trace in retest['result']['optimizer_traces']:
        label='data_only' if trace['weight']==0 else 'regularized'
        grid=sorted(map(float,trace['states'][0]['attempts']))
        for row in [profiles[label],*profiles[label]['sweeps'].values()]:
            row.setdefault('grid',grid)
            row.setdefault('bootstrap_95_frames',None)
            row.setdefault('bootstrap_halfwidth_frames',None)
            if row['lag'] is None:row['confidence_status']='unavailable: incomplete numerical evidence'
    write(a.output/'exact-retest.json',dict(**{k:v for k,v in retest.items() if k!='result'},
        recipe=dict(motion='direction_changes',length=100,noise_pixels=0.,known_offset_frames=-.1,groups=12,knot_spacing_frames=10,acceleration_weight=1.),
        profiles=profiles,attempt_statistics=stats,raw_profiles_and_initializations=str(raw_file),portable_full_evidence='profile-groups.json'))
    write(a.output/'initialization-attempts.json',dict(attempts=ledger,full_evidence='profile-groups.json'))
    write(a.output/'qualification.json',dict(exact_retest_passed=retest['safeguard_passed'],planned_independent_controls=117,independent_controls_attempted=0,
        planned_targeted_controls=3,targeted_controls_attempted=0,reused_production_controls=1890,
        production_independent_qualification='not qualified under v4; mandatory investigation stop',
        benchmark_status='not reached: safeguards failed',runtime_projection=None,
        real_configurations=[dict(configuration=c,status='unassessed',reason='required independent qualification missing') for c in p['configurations']],
        conditional_adapters='not reached; must implement and test before first use',selection_adapter='not reached before fitting qualification',
        selection_consumed_this_attempt=False,final_validation_consumed=False,final_validation_protocol=None,candidate_offsets=None,accepted_timing=None))
    write(a.output/'resources.json',dict(investigation_started_unix=p['investigation_started_unix'],
        clock_origin='2026-09-07 23:29:00 UTC; conservatively rounded down before first action',elapsed_seconds=time.time()-p['investigation_started_unix'],
        limit_seconds=14400,computation_limit_seconds=13200,early_retest_limit_seconds=5400,cpu_workers_limit=8,numerical_threads_per_worker=1,gpu_seconds=0,downloads=0,
        prefreeze_failure=dict(stage='diagnose',error='TypeError: Object of type int64 is not JSON serializable',
            preserved_output=str(a.root/'diagnose'),resolution='serialize block IDs as Python integers; fresh prepare and diagnosis outputs; no solver-policy change'),
        solver=provenance(),stages={k:{f:v.get(f) for f in ['wall_seconds','process_cpu_seconds','child_cpu_seconds','maximum_rss_kib','investigation_elapsed_seconds']} for k,v in stages.items()}))
    plot(a.output,profiles)
    write(a.output/'evidence.json',dict(source_sha256=sources,artifacts_sha256={str(f):sha256(f) for f in a.output.iterdir()},
        historical_evidence_sha256=sha256(p['prior_evidence']),v3_evidence_sha256=sha256(p['diagnostic_evidence']),report_script_sha256=sha256(__file__),
        accepted_timing=None,prior_plan007_audit_reused=True))


def plot(output,profiles):
    os.environ['MPLCONFIGDIR']='/tmp/plan010-matplotlib'
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    fig,axes=plt.subplots(2,2,figsize=(12,7),layout='constrained')
    for i,(name,row) in enumerate(profiles.items()):
        costs=row['directional_group_costs']
        for j,direction in enumerate(['ascending','descending']):
            ax=axes[i,j]
            for gid,curve in zip(row['group_ids'],costs[direction]):
                grid=row.get('grid',np.arange(-25,26,dtype=float))
                ax.plot(grid,np.sqrt(np.asarray(curve,dtype=float)),lw=.8,alpha=.75,label=str(gid))
            ax.axvline(-.1,color='black',ls='--')
            ax.set(title=f"{name}, {direction}: {row['sweeps'][direction]['support']}/12 complete groups",
                   xlabel='Camera 2 relative to camera 1 (frames)',ylabel='Group profile score')
            ax.grid(alpha=.2)
    fig.suptitle('Individual directional evidence; missing/invalid points are gaps')
    fig.savefig(output/'profiles.svg',metadata={'Date':None});plt.close(fig)
    file=output/'profiles.svg';file.write_text('\n'.join(l.rstrip() for l in file.read_text().splitlines())+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ['config','root','output']:parser.add_argument('--'+key,type=Path,required=True)
    publish(parser.parse_args())
