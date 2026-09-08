# Plan 012: Diagnose objective curvature before an exact-Hessian v6 pilot

## 1. Objective, scope and budget

Investigate whether the Gauss–Newton objective Hessian and weak spline directions explain the remaining
v5 independent-evaluator failures. Diagnose saved states without fitting first. Only if the diagnostic
gate supports the hypothesis, implement one separately versioned v6 evaluator whose sole numerical
change is the exact Hessian of the original objective. Retain v5's bounded depth constraint and its full
constraint Hessian. An exact Hessian is a hypothesis to test, not a promised convergence fix.

Completion is a documented numerical, scientific, computational or budget blocker, or a selection-qualified
candidate with a frozen, unexecuted final-validation protocol. A diagnostic or pilot pass is not timing
qualification. **Generating this plan does not execute the investigation, run new fits or start its clock.**

Carry forward [Plan 011](plan_011.md), [Plan 010](plan_010.md) and
[Plan 009 §4](plan_009.md#4-budget-gated-real-fitting-and-one-conditional-selection-attempt):

- All 34 cameras, accepted calibration and scale, the fixed 72-edge graph and held-outs 0/10/20/30.
- Plan 008's observations, duplicate families, associations and 667/667 partition, with at least 19 groups
  per edge per half. No additional observations, reassociation or support changes.
- Fitting frames 50–149, previously inspected selection frames 150–199 and untouched final frames 200–249.
- Six production configurations, three unchanged production starts, all required windows, the full
  ±25-frame qualification search and the 0.25-frame timing requirement.
- Historical code, configurations, outputs, consumption markers and the completed Plan 007 audit.
  Production fitting continues to call immutable v2 code.

Start a fresh four-hour elapsed clock at implementation's first action, including inspection, preparation,
implementation, derivative probes, tests, failed work, serialization, verification and commits. Retain the
absolute continuation deadlines; diagnosis is part of the existing pilot preparation allowance:

| Deadline from first action | Required outcome |
| --- | --- |
| 30 minutes | Preparation, saved-state diagnosis and decision, exact-Hessian regressions if authorized by that decision, escape-evidence verification, and the fixed pilot decision |
| 90 minutes | Complete evaluator freeze and full exact-control retest, conditional on the pilot passing |
| 3 hours 40 minutes | Stop scientific computation and protect the packaging reserve |
| 4 hours | Complete verification, reports and local commits |

A failed gate stops subsequent scientific stages. Incomplete work at its deadline is `budget_exhaustion`.
Do not extend deadlines or either solver cap after observing results. Use existing dependencies, at most
eight CPU workers in total and single-thread numerical libraries. Check the shared deadline inside
initialization, diagnostic probes, Hessian assembly and optimization; enforce it with an external process
watchdog that also terminates workers. No GPU jobs, downloads, training or reads from `prompts`.

## 2. Import the saved baseline and freeze the diagnostic cohort

Consume v5 through an explicit cross-version manifest, preserving predecessor paths and hashes:

- [Method and result](../docs/experiments/basketball-shared-timing-v5.md),
  [evidence](../docs/experiments/basketball-shared-timing-v5/evidence.json) and
  [final verification](../docs/experiments/basketball-shared-timing-v5/verification-final.json).
- [Pilot manifest](../docs/experiments/basketball-shared-timing-v5/diagnose-final/pilot-manifest.json),
  [pilot decision](../docs/experiments/basketball-shared-timing-v5/pilot/pilot-decision.json) and its six
  hash-referenced compressed group records, containing all 144 attempts.
- [Resources](../docs/experiments/basketball-shared-timing-v5/resources.json),
  [v4 comparisons](../docs/experiments/basketball-shared-timing-v5/v4-comparisons.json),
  [escape decision](../docs/experiments/basketball-shared-timing-v5/diagnose-final/escape-decision.json) and
  [compressed ray evidence](../docs/experiments/basketball-shared-timing-v5/diagnose-final/escape-audit.json.gz).
- [Preparation corrections](../docs/experiments/basketball-shared-timing-v5/corrections.json), the v2 admission
  and the v4 evidence imported by v5. Preserve the initial erroneous audit decisions as superseded records.

Recompute from the saved attempts: all 72 regularized attempts qualified; 21/72 data-only attempts
qualified; the other 51 stopped at 200 iterations with 192–197 distinct objective evaluations, median 196.
Their minimum original normalized depth was approximately 3.215451. Recompute original-unit optimality,
five three-start disagreements, nine qualified-reference comparison failures and the missing required
data-only transfers. Separate near-threshold failures from large remaining stationarity errors using
published continuous values; neither class qualifies by relabeling it. These observations suggest a
numerical obstacle but do not identify its cause or establish a finite global minimum.

Do not rerun v4 or v5 baseline optimization. Historical implementations may be exercised in the required
regression suite; label such unit-test solves separately from the scientific cohort.

Before new derivative probes, freeze a diagnostic manifest covering all 144 saved attempts. For each,
select the first callback state, middle callback state at index `len(trace)//2`, and returned state,
deduplicating identical states within the same mathematical problem while preserving every reference.
Include all 51 failed attempts and the successful data-only and regularized comparisons. Save the actual
indices, parameter bytes/hashes, group, lag, weight, start, physical scaling and provenance. Missing
required states or multipliers are missing evidence, not permission to choose a more convenient cohort.
Do not transfer offsets or coefficients across these problems.

## 3. Diagnose curvature and weak directions without optimization

### Original geometry, support and stationarity

At every diagnostic state, independently recompute the original residual vector, objective, analytic
objective gradient, original depths, offset bounds, sampled spline support and observable trajectory.
Measure coefficient magnitudes, data-Jacobian column norms and singular values in the fixed optimization
coordinates `q`, where physical parameters are `x = D q`, offset entries of `D` are 25, and coefficient
entries are 1. Separate data residuals from acceleration residuals.

Use the existing support threshold `max(matrix.shape) * machine_epsilon * largest_column_norm` for
coefficient blocks. Report SVD rank using `max(J.shape) * machine_epsilon * sigma_max`, retaining the entire
spectrum and nullspace dimension. Distinguish exact compact-support zeros, numerically weak support,
observable motion and source-to-destination activation. A small singular value is a diagnostic; it does
not authorize truncating a coefficient, rescaling the solver or adding a penalty. Exact unsupported
motion requires an argument about support, offsets and the acceleration term, not only a numerical rank.

For saved returned states, publish the signed vectors and their infinity norms:

```text
G                 = gradient_q F
C_depth           = J_g.T v_g = J_depth.T (v_g * g_prime)
C_bounds          = v_bounds
KKT                = G + C_depth + C_bounds
B_depth(mu)       = -mu * J_g.T (1 / g)
B_bounds(mu)_j    = mu * [1 / (1 - q_j) - 1 / (1 + q_j)]
```

The bound expression applies only to free offset variables strictly inside `(-1, 1)`; coefficient
entries have no bound barrier. Compare saved multipliers with the central-path values `v_g = -mu/g`,
and publish dual-sign and complementarity diagnostics in both constraint representations. Do not assume
those central-path values equal SciPy's returned multipliers. At first/middle states without saved
multipliers, publish the objective and analytic barrier contributions but mark multiplier-based KKT
unavailable. Record boundary, saturation, underflow or nonfinite cases explicitly instead of dividing
through them. Do not infer that comfortably positive depths make barrier forces negligible.

Relate these measurements to the saved changes in objective, gradient, barrier parameter, trust radius,
coefficients and trajectory. Distinguish slow progress in observable directions from movement in weak
coefficients, and separate barrier-subproblem progress from original-objective progress.

### Predetermined curvature probes

The current approximation is `H_GN = 2 J_r.T J_r` for the original robustified residual vector `r`.
Estimate the actual objective Hessian action using central differences of the unchanged analytic
objective gradient, independently of the proposed exact-Hessian implementation:

```text
H_FD(q) v = [G(q + h v) - G(q - h v)] / (2 h)
```

At each state, probe the four right-singular directions with the smallest singular values, normalized
objective-gradient direction if nonzero, up to two most recent distinct saved displacement directions,
and uniform positive-z coefficient translation. Use every available direction, deduplicating only exact
sign-equivalent duplicates. Make SVD signs and repeated-singular-value subspace bases deterministic;
record subspace projections so a rotated degenerate basis cannot change the diagnosis. Preserve exact-null
probes even though they cannot alone justify the continuation gate.

Use unit directions in `q` coordinates and the fixed nominal step ladder `1e-3, 1e-4, 1e-5, 1e-6`.
For each step, permit at most 20 deterministic halvings solely to keep both probes representable, within
original offset bounds and strictly above the original depth margin. Report actual steps and reject
unchanged perturbations, nonfinite arithmetic or unresolved cancellation. Do not clip states, move the
base state, enlarge a step after seeing curvature results or substitute another direction. Probe failure
is evidence about numerical conditioning. Record spline-knot proximity and check second-derivative
continuity; do not assume complex-step differentiation is valid through the existing implementation.

For two consecutive usable ladder levels with distinct actual step sizes differing by at least a factor
of two, let `u` and `u_prev` be their Hessian-vector estimates. Repeated step sizes cannot establish
independent agreement. Require stability before interpreting missing curvature:

```text
norm_inf(u - u_prev) <= 1e-7 + 1e-3 * max(norm_inf(u), norm_inf(u_prev))
```

Use the finest level with a stable predecessor, and retain every estimate. Compare it with `H_GN v`:

```text
E   = norm_inf(u - u_prev)
M   = norm_inf(u - H_GN v)
rho = M / max(norm_inf(u), norm_inf(H_GN v), 1e-12)
```

Also publish directional quadratic forms, gradient projections, observation-space motion and the
alignment of the discrepancy with the objective gradient and saved step directions. Separate data,
acceleration and constraint/barrier curvature; the diagnostic target is the objective Hessian supplied
by v5, not the entire constrained Newton system. Do not replace it with a robust-loss generalized
Gauss–Newton approximation and call that the exact Hessian.

These are fixed derivative probes, not new fits, line searches, optimized trial steps or qualification
starts. Give them a separate evaluation ledger and cache namespace; all costs consume the elapsed clock.
No diagnostic state may seed the pilot or a later qualification profile.

### Gate before implementing the optimizer change

Publish a hash-bound diagnostic decision before the first v6 pilot solve. Proceed with the exact-Hessian
implementation only if all of the following hold:

1. The saved baseline, original objective/gradient/depths, multiplier conversion and required records
   verify. No unresolved arithmetic or derivative-check discrepancy affects the claimed mechanism.
2. There is at least one failed returned state in **each** of groups 2, 9 and 11 with a stable, non-null
   gradient or saved-step probe for which `rho >= 0.1` and `M > 10 * E + 1e-7`. Publish the qualifying
   states and all counterexamples. The discrepancy must concern observable or nuisance-offset motion,
   not solely an exactly unsupported coefficient direction.
3. The support, barrier and stationarity decomposition supplies a consistent account of why missing
   objective curvature is a plausible contributor to the stalled solves. A numerical discrepancy alone,
   or successful regularization alone, is insufficient. Explicitly state competing explanations and
   whether weak conditioning or barrier forces could still dominate.

The numerical thresholds are conservative hypothesis-screening rules, not timing tolerances, proof of
causation or permission to relax a later gate. Freeze them before probes; do not adjust them to obtain
continuation. If the diagnosis is unsupported or unresolved, publish `numerical_failure` with the exact
reason and stop before fitting. Record requirements for a separate model-preserving coordinate-change
investigation if supported by the evidence, but do not implement that change in this plan.

## 4. Conditional implementation: the exact objective Hessian only

Add separately versioned v6 modules; preserve v2–v5 bytes. Derive and document the Hessian in the same
coordinates as the existing gradient:

```text
F(q)       = sum_k r_k(q)^2
H_exact(q) = 2 J_r(q).T J_r(q) + 2 sum_k r_k(q) H_r_k(q)
H_q        = D.T H_x D
```

An equivalent direct differentiation of the original pointwise loss is preferable to unstable second
derivatives of its square-root residual representation, provided independent equality tests pass. For
one two-dimensional image error `e`, using the unchanged total data-sample count `N`:

```text
phi(e)       = 2 * (sqrt(1 + e.T e) - 1) / N
b            = 2 * e / (N * sqrt(1 + e.T e))
W            = (2 / N) * [I / sqrt(1 + e.T e) - e e.T / (1 + e.T e)^(3/2)]
H_observation = J_e.T W J_e + sum_a b_a H_e_a
```

Include perspective division, the accepted radial distortion, camera rotation and rig normalization,
spline evaluation, nuisance-offset second derivatives and offset–coefficient mixed derivatives. Retain
coefficient–coefficient entries. Acceleration is linear in coefficients at the unchanged fixed quadrature;
its exact contribution is the corresponding block of `2 J_acc.T J_acc`, with no residual-curvature term.
For weight zero, add no acceleration, ridge or other penalty. The callable objective and gradient continue
to use immutable v2 residuals and their existing analytic derivative; direct-loss expressions are used to
derive/check the Hessian, not to replace reported profile costs.

Assemble an analytic sparse symmetric Hessian, preserving group sparsity and every coefficient. Do not
use finite-difference Hessians inside the optimizer, drop weak columns, project away negative eigenvalues,
add damping/ridge terms, change variables or switch to another Hessian approximation. The exact Hessian
can be indefinite. Use the existing trust-region solver's treatment of curvature without changing its
policy; record its available conjugate-gradient termination/negative-curvature diagnostics.

SciPy's [`minimize` Hessian interface](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.minimize.html)
and [`trust-constr` settings](https://docs.scipy.org/doc/scipy/reference/optimize.minimize-trustconstr.html)
provide the relevant interfaces. At implementation time, inspect and hash the installed solver source,
version, defaults and treatment of objective versus constraint Hessians. The objective Hessian callable
must not include the depth-constraint Hessian or barrier a second time.

Freeze all remaining policy identically to v5 before the pilot:

- `trust-constr`, sparse `AugmentedSystem`, the existing analytic gradient and full transformed-depth
  constraint Hessian; offset scale 25 and unchanged rig-diameter coefficient units.
- `g = (d - 1e-8) / hypot(1, d - 1e-8) >= 0`, fixed transformation scale 1 and no upper constraint.
- `gtol = xtol = barrier_tol = 1e-6`, 200 iterations and an independent 200-distinct-objective ceiling;
  unchanged initial barrier parameter/tolerance, trust radius, penalty and all installed defaults.
- `keep_feasible=True`, cold initialization, v3 seed ordering and v4 destination-cold replacement/blending.
  Original normalized initialization depth must exceed `2e-8`; no additional starts.
- Shared objective/gradient/Hessian caches count every distinct state first requested through any
  derivative. Analytic Hessian assembly gets separate counters and exclusive timing in addition to total
  derivative timing. Returned-state validation cannot create an uncounted distinct objective evaluation.

Require finite state, successful termination, independently recomputed stationarity using original
constraints in the fixed `q` coordinates at most `1e-6`, original offset bounds and the unchanged
nuisance-offset boundary check. Minimum original
normalized depth must exceed `1e-7`. Preserve original/transformed multiplier conversion, complementarity,
dual-sign and representation-agreement checks, and reject nonfinite conversion or unresolved derivative
underflow. Report only `sum(original_v2_residual**2)` as profile cost.

## 5. The single fixed v6 pilot and escape gate

Before any pilot solve, freeze the validated exact-Hessian implementation, diagnostic decision, all
numerical policy and pilot manifest. Reconstruct the immutable twelve-group noiseless direction-change
fixture with 100 frames, camera-2 truth −0.10 frames, camera-3 truth −0.20 frames, ten-frame knots and the
original observations. Construct pilot problems only for groups **2, 9 and 11**, with ordered lags:

```text
[-25, -20, -19, -7, -6, -0.10, 0, 25]
```

Both regularized weight 1 and data-only weight 0 are mandatory: 48 problems and exactly 144 scheduled
attempts, cold/ascending/descending. Within each group/objective, run all lags cold before ascending and
then descending using the unchanged ordering and sanitation. Require group 2's ascending −20 to −19
transfer and groups 9/11's descending −6 to −7 transfers for both objectives. A missing qualified source
is missing evidence; do not substitute a historical seed or add a fourth attempt. Development regressions
must not secretly run this scientific pilot, populate its cache or tune policy from fitting outcomes.

V5's 172-ray escape audit concerns the unchanged objective and feasible set. Reuse it only after verifying
its hashes, the corrected finite-reference comparisons, analytical limits and applicability to the
identical problems. Retain its 3,956 saved probes, all twelve v3 rejection records and the limitations of
the parallel-camera argument. Do not rerun or enlarge the ray grid to help a new solver pass. Failed but
feasible finite states may establish an upper bound on the best available finite objective; they are not
certified minima. Keep them separate from qualified reference optima used by the pilot cost gate.

Preserve the explanation that eight weak-support rays have not reached their analytical limits by
amplitude `10^44`, and separate finite-precision acceleration growth from exact constant-translation
invariance. Check new pilot first/intermediate/returned trajectories and support against the audited
mechanisms. Unexplained observable growth or unestablished escape feasibility/limits blocks continuation;
it does not authorize another ray search. A finite audit is not a global-minimum certificate.

The pilot passes only if, by the 30-minute deadline:

1. The diagnostic gate, exact-Hessian regressions, original-objective equality, original-unit checks and
   escape-evidence verification pass.
2. All 144 scheduled attempts qualify with unchanged solver limits and original-depth gates, including
   every required directional transfer. No limit stop or missing attempt counts as success.
3. At each problem the three original objectives agree within
   `abs(F1-F2) <= 1e-6 + 1e-4 * max(abs(F1), abs(F2))`.
4. The best v6 objective is no worse than the lowest qualified reference available from v5 or v4 for that
   identical problem, within the same tolerance. A lower v6 cost is recorded as an improvement, not forced
   to match a known inferior state. V5 supplies fractional −0.10 references where qualified; v4's
   fractional baseline remains unavailable. At identical states, v2/v5/v6 original objectives agree.
5. No unresolved arithmetic, misleading transformed convergence or unexplained observable growth remains.

Publish separate directional costs and every attempt, including failures. Record convergence, original
optimality, iteration and distinct-evaluation counts, Hessian calls and assembly cost, barrier parameters,
trust radii, original depths, multiplier diagnostics, coefficient/support and trajectory diagnostics,
initialization costs, seed provenance, warnings, memory and serialization. Relate any improvement or
failure to the preregistered curvature hypothesis without claiming causation from a pass alone.

A failed or incomplete pilot stops further scientific computation. No retuning, larger cap, reduced
cohort, relaxed gate, substitute Hessian, alternative coordinate system or second pilot is authorized.

## 6. Conditional full qualification and production continuation

Only after the diagnostic, pilot and escape gates pass, freeze the complete v6 evaluator and start the
full exact-control retest from fresh cold starts and fresh qualification caches. V5 or v6 diagnostic and
pilot states must not seed it. Retain all twelve groups in both objectives, every integer lag −25 through
25, both sweep directions and every refinement round. Refine every detected basin to 0.05 frames and
competing basins to 0.01 frames. Require nonboundary identifiable optima, unchanged ambiguity and whole-group
bootstrap gates, and recovery and sweep agreement within 0.05 frames. Complete the retest by 90 minutes;
failure or incompleteness stops continuation.

Then carry forward [Plan 011 §6](plan_011.md#6-conditional-qualification-and-production-continuation),
including all gates in Plans 010 and 009:

1. Rerun all 117 independent controls and three targeted short-control audits. Verify the 1,890 immutable
   production controls, generator, recipes, fitting code and three-start definitions before reuse. Numerical
   failure on noisy or negative controls is missing evidence, not successful ambiguity; qualified noisy
   controls must recover within 0.25 frames.
2. Inventory actual group-edge-window workloads and benchmark minimum/median/maximum observation-count
   cohorts in training/held-out, window-length, spacing and penalty strata with deterministic ties. Include
   exact objective Hessians, transformed constraint Hessians, original-unit validation, initialization,
   sanitation, refinement, serialization, memory and measured throughput with at most eight workers.
3. Project all six configurations, three starts, assessment nuisance fitting, both objectives, required
   windows, bootstrap, conditional selection and adapter implementation/testing with the existing
   factor-of-two runtime margin. Start real fitting only if all work fits before the reserve; otherwise
   publish `computational_blocker`. Recheck after each configuration. Never invoke an unimplemented adapter.
4. Fit optimization groups with immutable v2. Assess on assessment groups without refitting production
   offsets across 50–149, both 50-frame halves and all four 25-frame windows. Preserve every edge's support,
   spatial, timing, bootstrap, independent-versus-production and cycle gates. Rank passing configurations
   by assessment reprojection, then fewer knots, then lower acceleration.
5. After fitting qualification, complete and test selection, freeze the candidate and extraction,
   association and evaluator policy, and allow one selection attempt with a fresh consumption marker
   immediately before the first 150–199 frame read. Preserve the existing full/half-window gates. Failure
   ends the investigation; success freezes candidate offsets and an analogous one-use protocol for
   200–249. Do not execute final validation; `accepted_timing` remains null.

Held-out observations cannot influence training nuisance fitting, initialization or replacement. Fit and
constrain training-only nuisance state first, then freeze it before held-out lag evaluation. Independent
entry points exclude production states and cross-role/window/group seeds. A more accurate Hessian does
not relax isolation, identifiability or scientific acceptance requirements.

## 7. Interfaces, regression coverage and completion

Add `scripts/basketball_shared_workflow_v6.py` with stages:

```text
prepare, diagnose, pilot, safeguard, benchmark, fit, assess, select, package
```

Use `configs/basketball-rev2/timing-shared-v6.json`, separately versioned independent solver/profile and
curvature-diagnostic modules, and v6 reports/evidence. Every executed stage consumes hashed predecessors,
writes a fresh directory and shares the investigation clock. `pilot` requires a passed diagnostic decision
and validated exact Hessian; `safeguard` requires a passed pilot. Packaging must handle diagnosis-only,
pilot-failure and deadline-interrupted outcomes without assuming later artifacts exist. Publish scheduled,
executed, missing and qualified counts separately. Do not create fabricated empty success records.

Extend cache identities with objective-Hessian policy/version and derivative source hashes in addition
to the existing depth transformation, scale, margins, solver/transfer policy, observations, calibration,
role/window, group, edge gauge, spacing, penalty and requested lag. Separate diagnostic, pilot and
qualification namespaces. Changes to exercised solver/profile mathematics invalidate prior passes and
cannot authorize a second scientific pilot after a qualification failure. Never rewrite predecessor
hashes or patch a failure into success; preserve corrections and classify their effect on prior gates.

Add regressions for:

- Exact objective gradient/Hessian agreement with independent finite differences on fixed feasible
  synthetic states, both weights, all coefficient/offset blocks, nonzero reprojection errors, distortion,
  knot-near states, symmetry, sparsity and scaled-coordinate chain rules. Check stable multiple-step
  agreement and a nonzero residual-curvature case where `H_exact` differs from `2 J_r.T J_r`.
- The exactly linear acceleration Hessian, its absence at weight zero, no added penalty, unchanged original
  residuals/objectives and constant-translation invariance with explicit finite-precision limitations.
- Stable diagnostic direction selection, exact-null/weak/observable distinctions, missing snapshots,
  finite-difference cancellation, barrier versus multiplier stationarity and a negative diagnostic gate
  preventing every scientific solver call. Do not infer intermediate multipliers absent from saved traces.
- No double-counting of constraint/barrier curvature; unchanged bounded-depth derivatives, multiplier
  conversion, strict original-depth and offset gates, underflow/saturation rejection and misleading
  transformed-success rejection. Preserve full coefficients and deterministic destination-cold sanitation.
- Hessian-first evaluation accounting, both independent solver caps, derivative/initialization deadlines,
  30/90-minute gates, packaging reserve, external watchdog, fresh stage outputs and zero extra pilot starts.
- All inherited fixed-membership, refinement, sweep disagreement, competing-basin, boundary-confidence,
  fractional-sign, whole-group bootstrap, cycle, held-out isolation, production-state exclusion and
  cross-version/role/cache-isolation checks. Verify immutable production-control reuse separately.

Run Basketball, budget and SelfCap regressions. Independently verify current and historical hashes,
partition isolation, original objectives/depths, exact-Hessian actions, multiplier and seed provenance,
documentation links, historical consumption markers, and working-tree and staged `git diff --check`.
Publish the diagnostic hypothesis decision, full curvature/support and barrier decompositions, finite-
difference step/error ledgers, exact-Hessian derivation and validation, policy freezes, pilot and later
stage decisions, portable compressed attempt records stored once, runtime/storage accounting and role
consumption metadata. Keep unavailable profiles, intervals, projections, candidate and final protocol
explicitly null or unassessed.

Use `numerical_failure`, `scientific_rejection`, `computational_blocker`, `budget_exhaustion` and
`selection_qualified` consistently. Failure to substantiate the curvature hypothesis is a numerical
blocker, not evidence that the scientific model is false. A claim of no finite minimum requires a
mathematical argument. Update method and contender reports while preserving previous failures. Create
local commits for validated milestones under the repository procedure, then continue to the documented
blocker or candidate/protocol completion. Do not push.
