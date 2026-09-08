# Basketball shared timing v6: exact objective curvature

Plan 012 ends at **`numerical_failure`** after its single fixed pilot. The diagnostic hypothesis gate passed, but the exact Hessian qualified **94/144** attempts (v5: 93/144): all 72 regularized attempts and 22/72 data-only attempts. All 50 failures reached 200 iterations. Five three-start disagreements, nine qualified-reference failures and all three missing required data-only transfers remain. No later scientific stage ran; accepted timing is null.

[Plan](../../plans/plan_012.md) · [previous v5 failure](basketball-shared-timing-v5.md) · [result](basketball-shared-timing-v6/result.json) · [evidence](basketball-shared-timing-v6/evidence.json) · [independent verification](basketball-shared-timing-v6/verification.json).

## Frozen admission and diagnosis

The [cross-version manifest](basketball-shared-timing-v6/prepare/cross-version-manifest.json) verifies the v2 admission, 1,890 production controls, all historical source/artifact hashes, v5 corrections and superseded decisions. All 34 cameras, fixed 72 edges, accepted calibration/scale, 667/667 groups, minimum 19 groups per edge per half, held-outs and role windows remain fixed. Production still uses immutable v2. There were no v4/v5 baseline optimization reruns.

The [baseline recomputation](basketball-shared-timing-v6/prepare/baseline.json) recovers 72/72 regularized and 21/72 data-only qualifications, 51 failures at 200 iterations and 192–197 distinct evaluations (median 196), minimum failed depth 3.215451039, five disagreements, nine reference failures and the missing data-only transfers. Continuous original-unit optimalities retain near-threshold and larger errors without relabeling either as success.

The [compressed manifest](basketball-shared-timing-v6/prepare/diagnostic-manifest.json.gz) freezes all 144 attempts and 432 first/middle/returned references. Identical parameter bytes are deduplicated within each mathematical problem while every source, actual callback index, state hash, scaling and reference remains. No required snapshot or returned multiplier is missing. Attempt-specific displacement directions retain their own histories even when parameter storage is shared.

All 3,120 prescribed directions and 12,480 ladder levels are retained in six compressed files referenced by the [diagnostic decision](basketball-shared-timing-v6/diagnose/diagnostic-decision.json). There are 1,397 explicitly rejected levels and 2,769 stable actions. Directions include the four weakest data singular directions, objective gradient, up to two saved displacements and uniform positive-z translation; only exact sign duplicates are combined. Full spectra, column norms, compact-support distinctions, deterministic repeated-subspace projectors, observation trajectories, raw residuals, original depths and spline-knot checks are retained. The fixed rank range is 43–49 of 55 parameters. Rank does not authorize coefficient truncation.

There are 16 failed returned-state witnesses in each of groups 2, 9 and 11. Each has a stable observable gradient/saved-step probe satisfying the frozen `rho >= 0.1` and `M > 10 E + 1e-7` conditions. All counterexamples are also published. Independent scalar geometry agrees with the original objective to 4e-15 and normalized depths to 3.55e-15; no unresolved gradient check remains.

The [diagnostic summary](basketball-shared-timing-v6/diagnostic-summary.json) relates first/middle/returned objectives, gradient, barrier parameter, coefficients, rank and observable trajectory changes; original trust radii remain at the linked trace indices. Returned states publish signed `G`, `C_depth`, `C_bounds`, `KKT`, `B_depth` and `B_bounds` vectors and infinity norms. First/middle multiplier-based KKT is explicitly unavailable. Central-path values are compared with actual multipliers, never substituted for them. Dual signs, complementarity and original/transformed representation agreement are retained. Failed-state objective gradient norms range from 1.35609e-06 to 0.068365; depth barrier norms range from 7.84626e-08 to 0.000350298. Comfortably positive depth does not remove these forces.

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
| 2 | 1 | 24/24 | 9.28 |
| 9 | 1 | 24/24 | 8.85 |
| 11 | 1 | 24/24 | 8.74 |
| 2 | 0 | 6/24 | 63.12 |
| 9 | 0 | 7/24 | 62.77 |
| 11 | 0 | 9/24 | 57.37 |

The 50 failures used 193–197 distinct objective evaluations (median 196) and reached the unchanged 200-iteration cap. Original optimalities remain 3.50679e-06–0.0168307; minimum failed depth is 2.846144000. The [summary](basketball-shared-timing-v6/pilot-summary.json) publishes continuous values for every attempt. Reference costs use the lowest qualified v4/v5 state for the identical problem, including available v5 fractional references. Lower v6 costs are improvements, not forced matches. Five disagreements and nine reference failures remain, and no required data-only transfer qualifies. The required regularized transfers pass. No second pilot, cap increase, alternate Hessian, new coordinates or retuning ran.

The unchanged v5 escape audit was reused only after [independent re-verification](basketball-shared-timing-v6/v5-reuse-verification.json) of all 172 analytical rays, 3,956 existing probes, corrected finite-reference comparisons, twelve v3 rejection records and source hashes. No ray grid was rerun or enlarged. The eight weak-support rays whose amplitude-10⁴⁴ endpoints have not reached their analytical limits remain explicitly unresolved at that finite endpoint, with established analytical limits. Constant-translation acceleration invariance is exact algebraically; extreme finite coefficients can exhibit rounding growth. Failed feasible finite states provide upper bounds, not certified minima. Parallel-camera and finite-ray arguments do not establish a finite global minimum. Pilot support and observable trajectories triggered no unexplained-growth flag.

The exact Hessian substantially reduced regularized evaluation counts but only added one data-only qualification. This pilot therefore does not establish missing objective curvature as the dominant obstacle or qualify timing. Weak conditioning and constrained optimization remain plausible obstacles. The failure is numerical, not evidence that the scientific model is false.

## Resources, verification and role consumption

The fresh conservative clock started at 2026-09-08 00:59:50 UTC, including initial inspection, preparation, failed development work, diagnostics, tests and commits. The diagnostic decision completed at 540.99 seconds and the failed pilot decision at 1014.52 seconds, both before the fixed 1,800-second deadline. Scientific computation stopped there. All original 90-minute, 3h40 and four-hour deadlines remain in [resources](basketball-shared-timing-v6/resources.json). Six pilot workers used single-thread numerical libraries within the eight-worker cap; GPU/training time is zero. Shared checks and external watchdogs bounded scientific work.

Validation passes **193 Basketball, 7 budget and 3 SelfCap tests**. Historical regression solves and v6 unit-test solves are labeled separately from the scientific cohort. The [independent verification](basketball-shared-timing-v6/verification.json) checks original geometry and direct-loss gradients, saved probe/stability arithmetic, exact-policy hashes, pilot KKT, seeds, immutable partition/control evidence, documentation links, consumption markers and both working/staged diff whitespace checks.

Full exact qualification, the 117 independent controls, benchmarks, runtime projection, real fitting, assessment, candidate, intervals and final-validation protocol are null/unassessed. Selection frames 150–199 were not consumed again; final frames 200–249 remain untouched. Production v2–v5 code/configuration/evidence and the completed historical audits are preserved. No timing or Basketball training allocation is accepted by this result.
