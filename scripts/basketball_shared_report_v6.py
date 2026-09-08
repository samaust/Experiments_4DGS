"""Package Plan 012's terminal evidence without running scientific computation."""
import json
from pathlib import Path
import time
import numpy as np
from basketball_scale import read,write
from basketball_audit import sha256
from basketball_shared_diagnose_v5 import compressed_read

ROOT=Path('docs/experiments/basketball-shared-timing-v6')


def report():
    root=ROOT;p=read('configs/basketball-rev2/timing-shared-v6.json')
    if not (root/'pilot/pilot-decision.json').exists():
        return report_partial(root,p)
    decision=read(root/'diagnose/diagnostic-decision.json');pilot=read(root/'pilot/pilot-decision.json')
    baseline=read(root/'prepare/baseline.json');final=read(root/'package/result.json')
    rows=[];dynamics=[];probe_count=0;level_count=0;rejected=0;calls=0;distinct=0;probe_seconds=0.
    ranks=[];rho_by_group={};stationarity=[]
    for artifact in decision['artifacts']:
        records=compressed_read(root/'diagnose'/artifact['path'])['records']
        grouped={}
        for row in records:
            a=row['analysis'];stat=a['stationarity'];ranks.append(a['spectrum']['rank'])
            calls+=a['ledger']['calls'];distinct+=a['ledger']['distinct_states'];probe_seconds+=a['ledger']['seconds']
            for probe in a['probes']:
                probe_count+=1;level_count+=len(probe['levels']);rejected+=sum(l['rejected'] is not None for l in probe['levels'])
                if row['label']=='returned' and not row['saved_valid'] and probe['selected'] is not None and any(s=='gradient' or s.startswith('saved_step') for s in probe['labels']):
                    rho_by_group.setdefault(str(row['group_id']),[]).append(probe['selected']['rho'])
            if row['label']=='returned':
                stationarity.append(dict(reference=row['reference'],valid=row['saved_valid'],G_inf=stat['G_inf'],
                    KKT_inf=stat['KKT_inf'],B_depth_inf=stat['B_depth_inf'],B_bounds_inf=stat.get('B_bounds_inf'),
                    C_depth_inf=stat['C_depth_inf'],C_bounds_inf=stat['C_bounds_inf'],
                    central_path_multiplier_error_inf=stat['central_path_multiplier_error_inf']))
            group=row['reference'].rsplit('/',1)[0]
            xyz=np.concatenate([o['normalized_xyz'] for o in a['observations']])
            grouped.setdefault(group,[]).append(dict(label=row['label'],callback_index=row['index'],objective=a['objective'],
                objective_gradient_inf=stat['G_inf'],barrier_parameter=stat['barrier_parameter'],depth_barrier_inf=stat['B_depth_inf'],
                coefficient_norm=a['coefficient_norm'],coefficient_max=a['coefficient_max'],trajectory_norm=float(np.linalg.norm(xyz)),
                data_rank=a['spectrum']['rank'],nullspace=a['spectrum']['nullspace_dimension']))
        dynamics.extend(dict(reference=k,states=v,source_callback_trust_radius='see immutable source attempt solver_trace at callback_index') for k,v in grouped.items())
    diagnostic_summary=dict(probes=probe_count,ladder_levels=level_count,rejected_levels=rejected,
        objective_calls=calls,sum_per_reference_distinct_states=distinct,objective_evaluation_seconds=probe_seconds,
        diagnostic_reference_data_rank_range=[min(ranks),max(ranks)],parameter_count=55,
        failed_returned_gradient_step_rho={k:dict(min=min(v),median=float(np.median(v)),max=max(v)) for k,v in rho_by_group.items()},
        stationarity=stationarity,attempt_dynamics=dynamics,scientific_solves=0)
    write(root/'diagnostic-summary.json',diagnostic_summary)
    attempts=[];group_summary=[];hessian_calls=0;hessian_seconds=0.;init_seconds=0.;maxrss=0
    for artifact in pilot['artifacts']:
        state=compressed_read(root/'pilot'/artifact['path']);rs=[r for values in state['attempts'].values() for r in values]
        group_summary.append(dict(group_id=state['group_id'],weight=state['weight'],scheduled=24,executed=len(rs),
                                  qualified=sum(r['valid'] for r in rs),wall_seconds=state['wall_seconds']))
        for row in rs:
            hessian_calls+=row['objective_hessian_calls'];hessian_seconds+=row['objective_hessian_seconds']
            init_seconds+=row['initialization_seconds']+row['problem_initialization_seconds'];maxrss=max(maxrss,row['maximum_rss_kib'])
            attempts.append(dict(group_id=state['group_id'],weight=state['weight'],lag=row['lag'],start=row['start'],valid=row['valid'],
                objective=row['objective'],optimality=row['optimality'],nfev=row['nfev'],iterations=row['solver_trace'][-1]['iteration'],
                depth=row['minimum_normalized_depth'],hessian_calls=row['objective_hessian_calls'],hessian_seconds=row['objective_hessian_seconds']))
    failed=[r for r in attempts if not r['valid']]
    pilot_summary=dict(groups=group_summary,attempts=attempts,failed_iteration_counts=sorted(set(r['iterations'] for r in failed)),
                       failed_nfev_range=[min(r['nfev'] for r in failed),max(r['nfev'] for r in failed)],
                       failed_nfev_median=float(np.median([r['nfev'] for r in failed])),
                       failed_optimality_range=[min(r['optimality'] for r in failed),max(r['optimality'] for r in failed)],
                       minimum_failed_depth=min(r['depth'] for r in failed),
                       three_start_disagreements=sum(not r['three_start_agreement'] for r in pilot['comparisons']),
                       reference_failures=sum(not r['no_worse'] for r in pilot['comparisons']),
                       improvements=sum(r['improvement'] for r in pilot['comparisons']))
    write(root/'pilot-summary.json',pilot_summary)
    resources=dict(investigation_started_unix=p['investigation_started_unix'],first_action_utc='2026-09-08T00:59:50Z (conservative)',
        scientific_stop_elapsed_seconds=pilot['elapsed_seconds'],report_elapsed_seconds=time.time()-p['investigation_started_unix'],
        absolute_deadlines_unix={label:p['investigation_started_unix']+value for label,value in [('pilot',1800),('full_exact',5400),('science',13200),('package',14400)]},
        workers=6,cpu_worker_cap=8,numerical_threads_per_worker=1,gpu_seconds=0,
        diagnostic_objective_calls=calls,diagnostic_objective_seconds=probe_seconds,exact_hessian_validation_actions=2769,
        pilot_hessian_calls=hessian_calls,pilot_exclusive_hessian_assembly_seconds=hessian_seconds,
        pilot_initialization_seconds=init_seconds,maximum_worker_rss_kib=maxrss,
        pilot_serialization_seconds=sum(r['serialization_seconds'] for r in pilot['artifacts']),
        diagnostic_serialization_seconds=sum(r['serialization_seconds'] for r in decision['artifacts']),
        workers_wall_seconds_sum=sum(r['wall_seconds'] for r in group_summary),
        cpu_and_stage_wall_records={stage:read(root/stage/'result.json') for stage in ['prepare','diagnose','pilot','package']},
        unit_test_solves='historical and v6 fixed regression fixtures; separate from scientific cohort and caches',
        full_workload_projection=None,benchmark=None,training_seconds=0)
    write(root/'resources.json',resources)
    write(root/'corrections.json',dict(numerical_policy_tuned=False,pilot_runs=1,records=[
        dict(kind='development_test',initial='coarse h=1e-4 all-column FD test failed at H[32,34]: -12.301484487 versus -12.305823086',
             resolution='retained coarse step and required stable fine-step agreement at 1e-5 and 1e-6 plus decreasing maximum error; exact Hessian formula unchanged'),
        dict(kind='development_test',initial='inherited test patched workflow owner and passed v4 config to v6 admission, producing KeyError v4_evidence',
             resolution='test now patches v6 diagnostic owner and uses v6 config; corrupted control recipe is rejected'),
        dict(kind='metadata_clarification',initial='generic stage frozen.json solver field is inherited v5 baseline provenance',
             resolution='pilot/exact-policy-freeze.json is the authoritative executed v6 policy and source freeze, independently verified; generic record is preserved as baseline metadata',
             affects_numerical_gates=False),
        dict(kind='verification_clock',initial='immutable v5 verifier deadline refers to completed Plan 011',
             resolution='in-memory override only of investigation_started_unix used fresh Plan 012 clock during reuse verification; historical code, configs and evidence unchanged')]))
    result=dict(status='blocked',terminal_kind='numerical_failure',blocked_stage='pilot',blockers=final['blockers'],
        diagnostic_gate_passed=True,exact_hessian_validated=True,pilot_scheduled=144,pilot_executed=144,pilot_missing=0,pilot_qualified=94,
        exact_control_retest=None,independent_controls=None,benchmark=None,workload_projection=None,
        configuration_assessments=None,profiles=None,intervals=None,candidate_offsets=None,final_validation_protocol=None,accepted_timing=None,
        selection_previously_consumed=True,selection_consumed_this_attempt=False,final_validation_consumed=False,
        real_configurations_fitted=0,scientific_computation_stopped=True)
    write(root/'result.json',result)
    table='\n'.join(f'| {r["group_id"]} | {int(r["weight"])} | {r["qualified"]}/24 | {r["wall_seconds"]:.2f} |' for r in group_summary)
    text=f'''# Basketball shared timing v6: exact objective curvature

Plan 012 ends at **`numerical_failure`** after its single fixed pilot. The diagnostic hypothesis gate passed, but the exact Hessian qualified **94/144** attempts (v5: 93/144): all 72 regularized attempts and 22/72 data-only attempts. All 50 failures reached 200 iterations. Five three-start disagreements, nine qualified-reference failures and all three missing required data-only transfers remain. No later scientific stage ran; accepted timing is null.

[Plan](../../plans/plan_012.md) · [previous v5 failure](basketball-shared-timing-v5.md) · [result](basketball-shared-timing-v6/result.json) · [evidence](basketball-shared-timing-v6/evidence.json) · [independent verification](basketball-shared-timing-v6/verification-final.json).

## Frozen admission and diagnosis

The [cross-version manifest](basketball-shared-timing-v6/prepare/cross-version-manifest.json) verifies the v2 admission, 1,890 production controls, all historical source/artifact hashes, v5 corrections and superseded decisions. All 34 cameras, fixed 72 edges, accepted calibration/scale, 667/667 groups, minimum 19 groups per edge per half, held-outs and role windows remain fixed. Production still uses immutable v2. There were no v4/v5 baseline optimization reruns.

The [baseline recomputation](basketball-shared-timing-v6/prepare/baseline.json) recovers 72/72 regularized and 21/72 data-only qualifications, 51 failures at 200 iterations and 192–197 distinct evaluations (median 196), minimum failed depth {baseline['minimum_failed_depth']:.9f}, five disagreements, nine reference failures and the missing data-only transfers. Continuous original-unit optimalities retain near-threshold and larger errors without relabeling either as success.

The [compressed manifest](basketball-shared-timing-v6/prepare/diagnostic-manifest.json.gz) freezes all 144 attempts and 432 first/middle/returned references. Identical parameter bytes are deduplicated within each mathematical problem while every source, actual callback index, state hash, scaling and reference remains. No required snapshot or returned multiplier is missing. Attempt-specific displacement directions retain their own histories even when parameter storage is shared.

All {probe_count:,} prescribed directions and {level_count:,} ladder levels are retained in six compressed files referenced by the [diagnostic decision](basketball-shared-timing-v6/diagnose/diagnostic-decision.json). There are {rejected:,} explicitly rejected levels and 2,769 stable actions. Directions include the four weakest data singular directions, objective gradient, up to two saved displacements and uniform positive-z translation; only exact sign duplicates are combined. Full spectra, column norms, compact-support distinctions, deterministic repeated-subspace projectors, observation trajectories, raw residuals, original depths and spline-knot checks are retained. The fixed rank range is {min(ranks)}–{max(ranks)} of 55 parameters. Rank does not authorize coefficient truncation.

There are 16 failed returned-state witnesses in each of groups 2, 9 and 11. Each has a stable observable gradient/saved-step probe satisfying the frozen `rho >= 0.1` and `M > 10 E + 1e-7` conditions. All counterexamples are also published. Independent scalar geometry agrees with the original objective to {decision['maximum_independent_objective_error']:.3g} and normalized depths to {decision['maximum_independent_depth_error']:.3g}; no unresolved gradient check remains.

The [diagnostic summary](basketball-shared-timing-v6/diagnostic-summary.json) relates first/middle/returned objectives, gradient, barrier parameter, coefficients, rank and observable trajectory changes; original trust radii remain at the linked trace indices. Returned states publish signed `G`, `C_depth`, `C_bounds`, `KKT`, `B_depth` and `B_bounds` vectors and infinity norms. First/middle multiplier-based KKT is explicitly unavailable. Central-path values are compared with actual multipliers, never substituted for them. Dual signs, complementarity and original/transformed representation agreement are retained. Failed-state objective gradient norms range from {decision['account']['objective_gradient_inf_range'][0]:.6g} to {decision['account']['objective_gradient_inf_range'][1]:.6g}; depth barrier norms range from {decision['account']['depth_barrier_inf_range'][0]:.6g} to {decision['account']['depth_barrier_inf_range'][1]:.6g}. Comfortably positive depth does not remove these forces.

These observable curvature discrepancies and remaining stationarity errors support testing the exact objective Hessian. Weak coefficients, barrier subproblem progress, bound forces and finite trust-region/iteration budgets remain competing explanations; the diagnosis is not causal proof. Exact-null directions alone supplied no gate witness. A separate coordinate-change investigation would need model-preserving invertibility, unchanged bounds/physical units and support activation, derivative/cache/isolation regressions, a new preregistered budget and qualification; no such change is implemented here.

## Exact Hessian and validation

For the unchanged original residual vector, `F = sum(r²)` and `H = 2 JᵀJ + 2 sum(r_k H_rk)`. Implementation directly differentiates each two-dimensional image error instead of differentiating its square-root robust residual:

```text
s = sqrt(1 + eᵀe)
b = 2 e / (N s)
W = (2/N) [I/s - e eᵀ/s³]
H_observation = J_eᵀ W J_e + sum_a b_a H_ea
H_q = Dᵀ H_x D,  D_offsets = 25, D_coefficients = 1
```

Perspective division, accepted radial distortion, rotation/rig normalization and cubic-spline first/second derivatives are included, with full coefficient–coefficient and offset–coefficient blocks. In q coordinates, spline-time offset derivatives are `-B' c`, `B'' c` and mixed `-B'`. The acceleration Hessian is exactly its fixed linear `2 J_accᵀ J_acc` block, absent at weight zero. No penalty, support truncation, rescaling or robust generalized-Gauss–Newton substitution was added. Objective and gradient still call immutable v2 residuals/derivatives.

The [validation](basketball-shared-timing-v6/exact-hessian-validation.json) binds all exercised sources and installed SciPy source/defaults. Synthetic tests cover both weights, every parameter column, nonzero errors, radial distortion, rotated cameras, near-knot states, symmetry, scaled chain rules, exact acceleration, finite-precision constant translation and Hessian-first accounting. All 2,769 previously frozen stable FD actions agree with the analytic Hessian; [per-action errors](basketball-shared-timing-v6/exact-hessian-actions.json.gz) are retained. Development test corrections and the generic workflow baseline-provenance field are explained in [corrections](basketball-shared-timing-v6/corrections.json); no scientific policy was tuned from pilot results.

The authoritative [pilot policy freeze](basketball-shared-timing-v6/pilot/exact-policy-freeze.json) uses sparse `trust-constr` / `AugmentedSystem`, unchanged full bounded-depth constraint Hessian, `1e-6` tolerances, 200 iterations and 200 distinct objective states. Installed SciPy adds objective and multiplier-weighted constraint Hessians separately; the objective callable contains no constraint or barrier term. Shared objective/gradient/Hessian state accounting includes Hessian-first requests, with separate exclusive assembly counters/timing. Full coefficients, cold initialization, ordering, source-support replacement and feasible blending remain unchanged. Diagnostic, pilot and fresh qualification identities remain separate and bind derivative sources.

## Single fixed pilot and stop

The pilot used precisely groups 2/9/11, both weights and ordered lags `[-25, -20, -19, -7, -6, -0.10, 0, 25]`, with cold then ascending then descending starts. Scheduled 144; executed 144; missing 0; qualified 94. Six compressed attempt records are stored once and hash-referenced by the [pilot decision](basketball-shared-timing-v6/pilot/pilot-decision.json). Each includes costs, state traces, multipliers, support/trajectory checks, initialization and seed provenance, Hessian counts, warnings, memory and serialization.

| Group | Weight | Qualified | Worker wall seconds |
| --- | --- | --- | --- |
{table}

The 50 failures used {pilot_summary['failed_nfev_range'][0]}–{pilot_summary['failed_nfev_range'][1]} distinct objective evaluations (median {pilot_summary['failed_nfev_median']:g}) and reached the unchanged 200-iteration cap. Original optimalities remain {pilot_summary['failed_optimality_range'][0]:.6g}–{pilot_summary['failed_optimality_range'][1]:.6g}; minimum failed depth is {pilot_summary['minimum_failed_depth']:.9f}. The [summary](basketball-shared-timing-v6/pilot-summary.json) publishes continuous values for every attempt. Reference costs use the lowest qualified v4/v5 state for the identical problem, including available v5 fractional references. Lower v6 costs are improvements, not forced matches. Five disagreements and nine reference failures remain, and no required data-only transfer qualifies. The required regularized transfers pass. No second pilot, cap increase, alternate Hessian, new coordinates or retuning ran.

The unchanged v5 escape audit was reused only after [independent re-verification](basketball-shared-timing-v6/v5-reuse-verification.json) of all 172 analytical rays, 3,956 existing probes, corrected finite-reference comparisons, twelve v3 rejection records and source hashes. No ray grid was rerun or enlarged. The eight weak-support rays whose amplitude-10⁴⁴ endpoints have not reached their analytical limits remain explicitly unresolved at that finite endpoint, with established analytical limits. Constant-translation acceleration invariance is exact algebraically; extreme finite coefficients can exhibit rounding growth. Failed feasible finite states provide upper bounds, not certified minima. Parallel-camera and finite-ray arguments do not establish a finite global minimum. Pilot support and observable trajectories triggered no unexplained-growth flag.

The exact Hessian substantially reduced regularized evaluation counts but only added one data-only qualification. This pilot therefore does not establish missing objective curvature as the dominant obstacle or qualify timing. Weak conditioning and constrained optimization remain plausible obstacles. The failure is numerical, not evidence that the scientific model is false.

## Resources, verification and role consumption

The fresh conservative clock started at 2026-09-08 00:59:50 UTC, including initial inspection, preparation, failed development work, diagnostics, tests and commits. The diagnostic decision completed at {decision['elapsed_seconds']:.2f} seconds and the failed pilot decision at {pilot['elapsed_seconds']:.2f} seconds, both before the fixed 1,800-second deadline. Scientific computation stopped there. All original 90-minute, 3h40 and four-hour deadlines remain in [resources](basketball-shared-timing-v6/resources.json). Six pilot workers used single-thread numerical libraries within the eight-worker cap; GPU/training time is zero. Shared checks and external watchdogs bounded scientific work.

Validation passes **193 Basketball, 7 budget and 3 SelfCap tests**, plus **3 terminal-packaging/watchdog tests**. Historical regression solves and v6 unit-test solves are labeled separately from the scientific cohort. The [independent verification](basketball-shared-timing-v6/verification-final.json) checks original geometry and direct-loss gradients, saved probe/stability arithmetic, exact-policy hashes, pilot KKT, seeds, immutable partition/control evidence, documentation links, consumption markers and both working/staged diff whitespace checks.

Full exact qualification, the 117 independent controls, benchmarks, runtime projection, real fitting, assessment, candidate, intervals and final-validation protocol are null/unassessed. Selection frames 150–199 were not consumed again; final frames 200–249 remain untouched. Production v2–v5 code/configuration/evidence and the completed historical audits are preserved. No timing or Basketball training allocation is accepted by this result.
'''
    root.with_suffix('.md').write_text(text)
    for filename,link in [('docs/contender-experiments.md','experiments/basketball-shared-timing-v6.md'),
                          ('docs/experiments/contender-summary.md','basketball-shared-timing-v6.md'),
                          ('docs/experiments/basketball-rev2.md','basketball-shared-timing-v6.md')]:
        file=Path(filename);current=file.read_text();notice=f'[Plan 012 exact-Hessian pilot]({link}) ends at `numerical_failure`: the curvature diagnostic passed, but only 94/144 pilot attempts qualified (72 regularized, 22 data-only). No later scientific stage or new selection/final-frame consumption ran; accepted timing remains null.\n\n'
        if notice not in current:
            first,rest=current.split('\n',1);file.write_text(first+'\n\n'+notice+rest.lstrip('\n'))
    sources={str(f):sha256(f) for f in [Path('configs/basketball-rev2/timing-shared-v6.json'),*Path('scripts').glob('basketball_shared_*_v6.py'),*Path('tests').glob('test_basketball*v6.py')]}
    artifacts={str(f):sha256(f) for f in sorted(root.rglob('*')) if f.is_file() and f.name not in ['evidence.json','verification-final.json']}
    write(root/'evidence.json',dict(source_sha256=sources,artifacts_sha256=artifacts,storage_bytes=sum(f.stat().st_size for f in root.rglob('*') if f.is_file()),
        predecessor_evidence_sha256=sha256('docs/experiments/basketball-shared-timing-v5/evidence.json'),
        diagnostic_gate_passed=True,pilot_passed=False,selection_consumed_this_attempt=False,final_validation_consumed=False))
    print('terminal report packaged',flush=True)

def report_partial(root,p):
    """Deadline/diagnosis-only packaging never assumes unexecuted stage artifacts."""
    terminal=read(root/'package/result.json')
    assert terminal['status']=='blocked'
    available={stage:read(root/stage/'result.json') for stage in ['prepare','diagnose','pilot'] if (root/stage/'result.json').exists()}
    executed=0;qualified=0
    # A watchdog may leave completed group records without a pilot decision.
    for path in (root/'pilot').glob('weight*-group*.json.gz'):
        state=compressed_read(path)
        attempts=[r for rows in state['attempts'].values() for r in rows]
        executed+=len(attempts);qualified+=sum(r['valid'] for r in attempts)
    result=dict(status='blocked',terminal_kind=terminal['terminal_kind'],blockers=terminal['blockers'],
        stage_statuses=available,pilot_scheduled=144,pilot_executed=executed,pilot_missing=144-executed,pilot_qualified=qualified,
        pilot_decision=None,full_exact_retest=None,benchmark=None,workload_projection=None,profiles=None,intervals=None,
        candidate_offsets=None,final_validation_protocol=None,accepted_timing=None,
        selection_consumed_this_attempt=False,final_validation_consumed=False)
    write(root/'result.json',result)
    write(root/'resources.json',dict(investigation_started_unix=p['investigation_started_unix'],
          packaging_elapsed_seconds=time.time()-p['investigation_started_unix'],available_stage_resources=available,
          gpu_seconds=0,full_workload_projection=None))
    root.with_suffix('.md').write_text('# Basketball shared timing v6: interrupted or diagnosis-only outcome\n\n'
        +f"Plan 012 stops at `{terminal['terminal_kind']}`: "+'; '.join(terminal['blockers'])
        +f'. Pilot scheduled 144; completed serialized attempts {executed}; missing evidence {144-executed}; qualified {qualified}. '
        +'No pilot pass or later qualification is inferred. Accepted timing, candidate and final protocol remain null.\n')
    write(root/'evidence.json',dict(source_sha256={str(Path(__file__)):sha256(__file__)},
          artifacts_sha256={str(f):sha256(f) for f in root.rglob('*') if f.is_file() and f.name!='evidence.json'},
          later_artifacts_assumed=False,selection_consumed_this_attempt=False,final_validation_consumed=False))


if __name__=='__main__':report()
