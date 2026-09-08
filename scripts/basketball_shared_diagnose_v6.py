"""Cross-version admission and complete, frozen Plan 012 saved-state cohort."""
import hashlib
import inspect
import json
from pathlib import Path
import time
import numpy as np
import scipy
from scipy.optimize._trustregion_constr import tr_interior_point, minimize_trustregion_constr
from basketball_audit import sha256
from basketball_scale import read, write
from basketball_continuation_audit import verify_hashes
from basketball_shared_diagnose_v5 import compressed_read, compressed_write
from basketball_shared_curvature_v6 import POLICY, snapshots, parameter_hash, analyze, gate
from basketball_shared_synthetic_v2 import synthetic
from basketball_shared_spline_v2 import SplineProblem
from basketball_shared_solver_v3 import objective_agreement
from basketball_shared_verify_v5 import objective_depth, verify_partition

ROOT = Path('docs/experiments/basketball-shared-timing-v5')


def check(p):
    if time.time() >= p['investigation_started_unix']+1800:
        raise TimeoutError('30-minute preparation/diagnosis/pilot deadline')


def saved_groups():
    decision = read(ROOT/'pilot/pilot-decision.json')
    for entry in decision['artifacts']:
        path = ROOT/'pilot'/entry['path']
        if sha256(path) != entry['sha256']:
            raise ValueError('saved attempt hash mismatch: '+str(path))
        yield path, compressed_read(path)


def prepare(p, output):
    hashes = {}
    for evidence in [ROOT/'evidence.json', Path(p['prior_evidence']), Path(p['v4_evidence'])]:
        check(p); e = read(evidence); hashes[str(evidence)] = sha256(evidence)
        for key in ['source_sha256', 'immutable_sha256', 'artifact_sha256', 'artifacts_sha256', 'test_logs_sha256']:
            if key in e:
                verify_hashes(e[key]); hashes.update(e[key])
    # Preserve the superseded decisions as well as their corrected replacements.
    for f in sorted(ROOT.rglob('*')):
        if f.is_file():
            hashes[str(f)] = sha256(f)
    hashes[str(ROOT.with_suffix('.md'))] = sha256(ROOT.with_suffix('.md'))
    for key in ['source_sha256', 'artifacts_sha256']:
        verify_hashes(read(ROOT/'prepare-final/result.json')[key])
    verify_hashes(read(ROOT/'prepare-final/v4-import.json')['source_sha256'])
    old = read('configs/basketball-rev2/timing-shared-v5.json')
    for key in ['fit_frames', 'target_cameras', 'held_out_cameras', 'configurations', 'injections', 'audit_windows',
                'roles', 'previous_frozen', 'admission', 'controls', 'independent_solver', 'independent_initialization']:
        if p[key] != old[key]:
            raise ValueError('changed inherited policy '+key)
    partition = verify_partition(p)
    controls = read(ROOT/'prepare-final/controls-reuse.json')['controls']
    assert len(controls) == 1890
    verify_hashes({r['path']: r['sha256'] for r in controls})
    for r in controls:
        saved = read(r['path'])
        assert len(saved['result']['starts']) == 3
        assert all(saved[k] == r[k] for k in ['configuration', 'motion', 'length', 'noise_pixels', 'known_offset_frames'])
    attempts = []; states = {}; references = []; missing = []; comparisons = []; transfers = []
    for path, group in saved_groups():
        check(p)
        weight, gid = group['weight'], group['group_id']
        historical = compressed_read(Path('docs/experiments/basketball-shared-timing-v4')/
                                     f'{"regularized" if weight else "data_only"}-group{gid:02d}.json.gz')
        for lag, rows in group['attempts'].items():
            assert [r['start'] for r in rows] == ['cold', 'ascending', 'descending']
            values = [r['objective'] for r in rows]
            refs = [r['objective'] for r in historical['attempts'].get(str(float(lag)), []) if r['valid']]
            best, ref = min(values), min(refs) if refs else None
            comparisons.append(dict(group_id=gid, weight=weight, lag=float(lag),
                                    three_start_agreement=all(objective_agreement(values[0], v) for v in values),
                                    no_worse=ref is None or best <= ref or objective_agreement(best, ref),
                                    best=best, qualified_v4_reference=ref))
            for row in rows:
                name = f'{weight}/{gid}/{lag}/{row["start"]}'
                attempts.append(dict(reference=name, group_id=gid, weight=weight, lag=float(lag), start=row['start'],
                                     valid=row['valid'], optimality=row['optimality'], nfev=row['nfev'],
                                     iterations=row['solver_trace'][-1]['iteration'], min_depth=row['minimum_normalized_depth']))
                try:
                    snaps = snapshots(row)
                except ValueError as error:
                    missing.append(dict(reference=name, error=str(error))); continue
                for snap in snaps:
                    # Deduplication is within the same objective, group and lag only.
                    key = f'{weight}/{gid}/{lag}/{snap["sha256"]}'
                    if key not in states:
                        states[key] = dict(x=snap['x'], parameter_sha256=snap['sha256'],
                                           parameter_bytes_le_hex=np.asarray(snap['x'], dtype='<f8').tobytes().hex(),
                                           scale=[25.]+[1.]*(len(snap['x'])-1), group_id=gid, weight=weight, lag=float(lag),
                                           center=row['center'], diameter=row['diameter'], knots=row['knots'], window=row['window'])
                    references.append(dict(reference=name+'/'+snap['label'], state_key=key, source=str(path),
                                           source_sha256=sha256(path), lag_key=lag, start=row['start'], label=snap['label'],
                                           index=snap['index'], group_id=gid, weight=weight, saved_valid=row['valid']))
        source, destination, direction = (-20., -19., 'ascending') if gid == 2 else (-6., -7., 'descending')
        row = next(r for r in group['attempts'][str(destination)] if r['start'] == direction)
        transfers.append(dict(group_id=gid, weight=weight, source=source, destination=destination, direction=direction,
                              verified=bool(row['valid'] and row['seed_lag'] == source)))
    failed = [r for r in attempts if not r['valid']]
    summary = dict(attempts=attempts, regularized_qualified=sum(r['valid'] for r in attempts if r['weight']),
                   data_only_qualified=sum(r['valid'] for r in attempts if not r['weight']), failed=len(failed),
                   failed_iterations=sorted(set(r['iterations'] for r in failed)),
                   failed_nfev_range=[min(r['nfev'] for r in failed), max(r['nfev'] for r in failed)],
                   failed_nfev_median=float(np.median([r['nfev'] for r in failed])),
                   minimum_failed_depth=min(r['min_depth'] for r in failed), comparisons=comparisons, transfers=transfers,
                   three_start_disagreements=sum(not r['three_start_agreement'] for r in comparisons),
                   qualified_reference_failures=sum(not r['no_worse'] for r in comparisons), baseline_optimization_rerun=False,
                   optimality_classification='continuous original-unit values retained; no relabeling of threshold failures')
    assert len(attempts) == 144 and summary['regularized_qualified'] == 72 and summary['data_only_qualified'] == 21
    assert summary['failed_iterations'] == [200] and summary['failed_nfev_range'] == [192, 197]
    assert summary['failed_nfev_median'] == 196 and summary['three_start_disagreements'] == 5
    assert summary['qualified_reference_failures'] == 9
    write(output/'baseline.json', summary)
    installed = {}
    for module in [tr_interior_point, minimize_trustregion_constr]:
        f = inspect.getsourcefile(module); installed[f] = sha256(f)
    manifest = dict(schema='v6-diagnostic-cohort/1', policy=POLICY, states=states, references=references,
                    scheduled_attempts=144, scheduled_references=432, unique_states=len(states), missing=missing,
                    frozen_unix=time.time(), source_sha256=hashes, no_cross_problem_state_transfer=True)
    compressed_write(output/'diagnostic-manifest.json.gz', manifest)
    write(output/'cross-version-manifest.json', dict(source_sha256=hashes, partition=partition,
          controls_verified=1890, scipy=scipy.__version__, installed_solver_sha256=installed,
          old_config_hashes_rewritten=False, predecessor_verification=sha256(ROOT/'verification-final.json'),
          diagnostic_manifest_sha256=sha256(output/'diagnostic-manifest.json.gz')))
    check(p)
    return dict(status='passed' if not missing else 'blocked', terminal_kind='numerical_failure' if missing else None,
                blockers=['missing required diagnostic evidence'] if missing else [])


def diagnose(p, output, predecessor):
    manifest = compressed_read(predecessor/'diagnostic-manifest.json.gz')
    verify_hashes(manifest['source_sha256'])
    if manifest['policy'] != POLICY:
        raise ValueError('diagnostic policy changed after cohort freeze')
    groups, cameras, truth, window = synthetic('direction_changes', 0., -.1, 100, groups=12)
    assert truth == {1:0., 2:-.1, 3:-.2}
    source_cache = {}; problem_cache = {}; analysis_cache = {}; results = []; discrepancies = []
    artifacts = []; max_objective_error = 0.; max_depth_error = 0.
    for ref in manifest['references']:
        check(p); source = ref['source']
        if source not in source_cache:
            source_cache[source] = compressed_read(source)
        row = next(r for r in source_cache[source]['attempts'][ref['lag_key']] if r['start'] == ref['start'])
        state = manifest['states'][ref['state_key']]
        key = (state['group_id'], state['lag'], state['weight'])
        if key not in problem_cache:
            problem_cache[key] = SplineProblem([groups[key[0]]], cameras, {1:0., 2:key[1], 3:0.}, window, 10, key[2], (1,2), lambda:check(p))
        problem = problem_cache[key]
        # Derivative directions include attempt-specific history, so shared parameter states
        # may share storage but must preserve all distinct saved-step references.
        snap = dict(x=state['x'], sha256=state['parameter_sha256'], label=ref['label'], index=ref['index'])
        result = analyze(problem, row, snap)
        cost, depths = objective_depth(groups, cameras, row, state['x'], state['lag'])
        err = abs(cost-result['objective']); max_objective_error = max(max_objective_error, err)
        de = float(np.max(np.abs(depths-result['stationarity']['original_depths']))); max_depth_error = max(max_depth_error, de)
        np.testing.assert_allclose(cost, result['objective'], rtol=1e-9, atol=1e-10)
        np.testing.assert_allclose(depths, result['stationarity']['original_depths'], rtol=1e-12, atol=1e-12)
        saved_cost = row['objective'] if ref['index'] is None else row['solver_trace'][ref['index']]['objective']
        np.testing.assert_allclose(cost, saved_cost, rtol=1e-9, atol=1e-10)
        # Use the finest stable objective directional derivative to check the analytic gradient.
        for probe in result['probes']:
            if probe['selected'] is not None:
                level = probe['levels'][probe['selected']['level']]
                fd, analytic = level['objective_directional_fd'], level['objective_gradient_projection']
                if abs(fd-analytic) > 2e-6+2e-3*max(abs(fd), abs(analytic)):
                    discrepancies.append(dict(reference=ref['reference'], labels=probe['labels'], fd=fd, analytic=analytic))
        results.append(dict(**ref, analysis=result))
        if len(results) % 24 == 0:
            print('diagnostic references', len(results), '/432', flush=True)
    # Publish all measurements before making the mechanism decision. Quantitative
    # witnesses are necessary; barrier and weak-support alternatives remain explicit.
    preliminary = gate(results, not discrepancies, True)
    returned = [r for r in results if r['label'] == 'returned' and not r['saved_valid']]
    account = dict(failed_returned_states=len(returned),
                   objective_gradient_inf_range=[min(r['analysis']['stationarity']['G_inf'] for r in returned),
                                                 max(r['analysis']['stationarity']['G_inf'] for r in returned)],
                   depth_barrier_inf_range=[min(r['analysis']['stationarity']['B_depth_inf'] for r in returned),
                                            max(r['analysis']['stationarity']['B_depth_inf'] for r in returned)],
                   barrier_dominance_count=sum(r['analysis']['stationarity']['B_depth_inf'] > r['analysis']['stationarity']['G_inf'] for r in returned),
                   weak_conditioning='Full spectra, compact support and observable trajectories retained; no truncation or rescaling authorized.',
                   competing_explanations=['weak coefficient conditioning', 'barrier-subproblem progress and changing barrier forces',
                                           'trust-region policy and finite iteration budget'],
                   interpretation='Missing objective curvature is plausible only with an observable gradient/saved-step witness in every required group; '
                                  'weak conditioning and barrier forces can still dominate. This screen cannot establish causality or a finite global minimum.')
    decision = gate(results, not discrepancies, not preliminary['missing_groups'])
    decision.update(account=account, derivative_discrepancies=discrepancies,
                    maximum_independent_objective_error=max_objective_error, maximum_independent_depth_error=max_depth_error,
                    manifest_sha256=sha256(predecessor/'diagnostic-manifest.json.gz'),
                    scheduled_references=432, executed_references=len(results), missing_references=432-len(results),
                    scheduled_pilot_attempts=144, executed_pilot_attempts=0, qualified_pilot_attempts=0,
                    elapsed_seconds=time.time()-p['investigation_started_unix'])
    # One compressed record per original group/objective, with every attempted probe retained.
    for source in source_cache:
        subset = [r for r in results if r['source'] == source]
        artifacts.append(compressed_write(output/Path(source).name, dict(records=subset)))
    decision['artifacts'] = artifacts
    write(output/'diagnostic-decision.json', decision)
    check(p)
    return dict(status='passed' if decision['passed'] else 'blocked', terminal_kind=decision['terminal_kind'], blockers=decision['blockers'],
                diagnostic_references=len(results), pilot_scheduled=144, pilot_executed=0, pilot_missing=144, pilot_qualified=0)
