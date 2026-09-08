# Plan 011: Pilot a bounded depth barrier without changing the timing model

## 1. Objective, scope and budget

Implement one separately versioned v5 independent evaluator that changes only the numerical
representation of the depth inequality. Test whether removing the log barrier's unbounded reward for
increasing depth restores reliable constrained profiles under the existing limits.

Completion is either a documented numerical, scientific, computational or budget blocker, or a
selection-qualified candidate with a frozen, unexecuted final-validation protocol. A pilot pass alone
is not timing qualification. Generating this plan does not execute the investigation or start its clock.

Carry forward [Plan 010](plan_010.md) and [Plan 009 §4](plan_009.md#4-budget-gated-real-fitting-and-one-conditional-selection-attempt):

- All 34 cameras, accepted calibration and scale, the fixed 72-edge graph and held-outs 0/10/20/30.
- Plan 008's tracks, duplicate families, associations and 667/667 partition, with at least 19 groups per
  edge per half. No new observations or reassociation.
- Fitting frames 50–149, previously inspected selection frames 150–199 and untouched final frames 200–249.
- Six production configurations, three unchanged production starts, full ±25-frame qualification search,
  all required windows and the 0.25-frame timing requirement.
- Historical implementations, configurations, outputs, consumption markers and the completed Plan 007
  audit. Production fitting continues to call immutable v2 code.

Start a fresh four-hour elapsed clock at implementation's first action. Include preparation, inspection,
coding, tests, diagnostics, failures, serialization, verification and commits. Use these absolute limits:

| Deadline from first action | Required outcome |
| --- | --- |
| 30 minutes | Complete preparation, derivative checks, escape audit, fixed pilot and its decision |
| 90 minutes | Complete the evaluator freeze and full exact-control retest |
| 3 hours 40 minutes | Stop scientific computation; protect the packaging reserve |
| 4 hours | Complete verification, reports and local commits |

A failed or incomplete pilot stops continuation. A failed or incomplete exact retest stops continuation.
Use at most eight CPU workers and single-thread numerical libraries, with shared deadlines checked inside
initialization, derivative evaluation and optimization and enforced by an external watchdog. Use existing
dependencies. No GPU jobs, downloads, training or reads from `prompts`.

## 2. Establish the mechanism and preserve the baseline

Consume hashed v4 evidence through an explicit cross-version manifest:

- [Method and result](../docs/experiments/basketball-shared-timing-v4.md).
- [Exact retest](../docs/experiments/basketball-shared-timing-v4/exact-retest.json).
- [Initialization ledger](../docs/experiments/basketball-shared-timing-v4/initialization-attempts.json).
- [Portable full group records](../docs/experiments/basketball-shared-timing-v4/profile-groups.json).
- [Coefficient diagnostics](../docs/experiments/basketball-shared-timing-v4/coefficient-diagnostics.json).
- [Evaluator freeze](../docs/experiments/basketball-shared-timing-v4/evaluator-freeze.json) and
  [verification](../docs/experiments/basketball-shared-timing-v4/verification.json).

Recompute the baseline summary from saved records: 1,774/1,836 data-only attempts fail, their median
objective-evaluation count is 197, and every failed data-only state's minimum normalized depth exceeds
3.59. Distinguish the 200-iteration ceiling from the independent 200-objective-evaluation ceiling.
Do not rerun v4 optimization or infer that a larger iteration cap will resolve the problem.

Inspect and hash the installed SciPy `tr_interior_point.py` implementation, including its
`F - mu * sum(log(slack))` barrier expression. Record the installed version and source location rather
than assuming a documentation formula matches the installed code.

Write the mathematical argument for the exact synthetic camera arrangement:

1. The generator uses parallel cameras with identity rotations and translations along the x axis.
2. Add the same positive z translation to every spline coefficient while fixing all offsets.
   Partition of unity translates the complete trajectory; the second derivative of this constant
   translation is zero in exact arithmetic, preserving the acceleration term.
3. As translation tends to infinity, depths increase and projected points tend to finite image points.
   The original robust reprojection objective therefore has a finite limit; the acceleration term
   remains unchanged.
4. At any fixed positive `mu`, the raw-depth log-barrier objective tends to negative infinity.

This establishes an unbounded barrier subproblem in this fixture. It does not establish nonexistence of a
finite minimum of the original objective, explain every v4 stalled solve, or establish the same recession
direction for the real rig. Separate exact-arithmetic statements from finite-precision spline effects.

## 3. Freeze the single v5 numerical change

Let `d = z / rig_diameter`, `m = 1e-8`, and `s = d - m`. Replace the depth constraint supplied to the
optimizer by:

```text
g(s) = s / sqrt(1 + s²) >= 0
```

For finite real `s`, this is equivalent to `d >= m`. There is no additional upper constraint on `g`, no
maximum depth, and no change to the feasible set in exact arithmetic. For positive slack, `0 < g < 1`,
so `-mu * log(g)` is nonnegative and approaches zero as depth increases. This removes the unbounded
negative barrier reward; it does not remove every finite-depth barrier bias or guarantee convergence.

Fix the dimensionless constant in `sqrt(1 + s²)` at 1, corresponding to the existing rig-diameter depth
units. Do not search over transformation scales, initial barriers, tolerances, Hessian policies or solvers.
Freeze the policy and pilot manifest before the first pilot solve. After the pilot passes, freeze the
complete evaluator before the full profiles; the numerical policy must remain identical to the pilot.

### Analytic derivatives and stable evaluation

Retain dimensionless offset variables `offset_frames / 25` and existing rig-diameter coefficient units.
For each observation, use:

```text
g'(s)  = (1 + s²)^(-3/2)
g''(s) = -3s * (1 + s²)^(-5/2)
J_g    = diag(g'(s)) J_s
H_g(v) = sum_i v_i [g'(s_i) H_s_i + g''(s_i) J_s_i.T J_s_i]
```

The second term in the constraint Hessian is required, including coefficient–coefficient entries.
Preserve sparse group structure and the full coefficient parameterization. Use `hypot(1, s)` and inverse
powers arranged to avoid unnecessary overflow; do not compute `s*s` for extreme diagnostic amplitudes.
Record saturation, derivative underflow and nonfinite arithmetic explicitly. Never clip depths or
silently replace derivatives with zero to manufacture a qualified solution.

### Solver, initialization and returned-state checks

Carry forward v4 unchanged except for the transformed depth function and its chain-rule derivatives:

- SciPy `trust-constr`, sparse `AugmentedSystem`, analytic sparse objective gradients and a sparse
  Gauss–Newton objective Hessian. Keep all remaining installed defaults explicitly frozen.
- `gtol = xtol = barrier_tol = 1e-6`, at most 200 iterations, `keep_feasible=True` for the depth inequality
  and offset bounds, and an independent ceiling of 200 distinct objective evaluations.
- Shared residual/Jacobian caches count evaluations requested through derivatives. Initialization and
  constraint evaluations, derivative time, warnings and serialization have separate counters and still
  consume elapsed time. Validation must not create an uncounted distinct objective evaluation.
- Original v2 residuals, sample normalization, spline basis, acceleration term and all coefficients.
  Report only `F = sum(original_residual**2)`; internal barriers and merit terms cannot enter profile costs.
- Original cold initialization, v3 seed-selection order and v4 source-support replacement/blending.
  Validate initialization using original normalized depth strictly above `2e-8`, not transformed slack.
  Preserve cold, ascending and descending attempts, with no fourth profile attempt.

Independently recompute finiteness, original normalized depths, original offset bounds and the original
objective at returned states. Map transformed constraint multipliers back using
`v_depth_i = v_g_i * g'(s_i)`, retain bound multipliers, and recompute stationarity in the original
constraints and fixed optimization coordinates. Publish multipliers, original and transformed residuals,
and complementarity/dual-sign diagnostics so saturation cannot hide a failure behind a small transformed
constraint gradient.

Require successful termination, recomputed optimality at most `1e-6`, the original depth margin and the
unchanged nuisance-offset boundary checks. Any returned state with minimum original normalized depth at
or below `1e-7` remains unqualified. Nonfinite multiplier conversion, unresolved derivative underflow or
numerical disagreement between the two constraint representations is a numerical failure. These checks
must not be weakened in response to pilot outcomes.

## 4. Predetermined pilot and 30-minute decision

Reconstruct the exact noiseless direction-change fixture using the immutable generator: all twelve groups,
100 frames, true camera-2 offset −0.10 frames, the original nuisance-camera truth, ten-frame knots and
acceleration weight 1. Construct pilot problems only for groups **2, 9 and 11** and this ordered lag grid:

```text
[-25, -20, -19, -7, -6, -0.10, 0, 25]
```

Evaluate both regularized weight 1 and data-only weight 0. There are **48 group/lag/objective problems**
and exactly **144 scheduled initialization attempts**: cold, ascending and descending for each problem.
Missing seeds remain failed attempts; no replacement solve is allowed. Do not drop a group or lag.

Within each group/objective, first solve all pilot lags cold, then ascend and descend with the unchanged
v3 ordering and v4 sanitation. This exercises group 2's ascending −20 to −19 transfer and groups 9/11's
descending −6 to −7 transfers when their required source states qualify. Failure of a required source is
missing evidence, not permission to substitute another experiment. The sparse pilot grid is diagnostic
only and never replaces the full qualification search or supports a timing confidence claim.

Compare with hash-verified v4 records where the same integer-lag problems exist. V4 has no completed
fractional retest at −0.10; mark that baseline unavailable rather than rerunning a baseline solve. Saved
v3 pathological seeds are permitted only in separately identified, non-optimizing sanitation regressions;
they must not become extra pilot starts or qualification seeds.

For every attempt, publish original objectives, convergence, optimality, iterations, distinct residual
counts, barrier parameters, trust radii, original depths, coefficient/support diagnostics, observable
trajectory coordinates, warnings, initialization and derivative costs, memory and seed provenance.
Compare the first, intermediate and returned states to distinguish depth-barrier progress from movement
in weak coefficient directions. Use the existing objective tolerance:

```text
abs(F1 - F2) <= 1e-6 + 1e-4 * max(abs(F1), abs(F2))
```

The pilot passes only if all of the following hold by the 30-minute deadline:

1. Transformation, chain-rule derivatives, original-objective equality and original-unit returned-state
   checks pass their regressions; the baseline evidence and mathematical barrier argument are verified.
2. All 144 scheduled attempts qualify under the unchanged solver limits and original-depth gates,
   including the specified directional transfers. No missing attempt or iteration/evaluation-limit stop
   is credited as success.
3. The three v5 start objectives agree within the existing tolerance at every pilot problem. Where v4
   has a qualified reference, the lowest v5 objective is no worse beyond that tolerance. A lower v5
   objective is recorded as an improvement, not forced to match a known inferior solution. V4 failures
   are comparison states, not certified minima. At identical states, v4/v5 original-objective evaluators
   agree independently of their internal barriers.
4. The preregistered escape audit in §5 is resolved for its audited directions. Saturated constraints,
   unchecked growth, or small gradients alone cannot qualify a pilot.

These are conservative pilot continuation gates, not new claims of global optimality or replacements for
full profile qualification. Any failed gate stops further scientific computation; publish the evidence and
its classification. If work is incomplete at 30 minutes, publish `budget_exhaustion`. Do not increase caps,
change settings, enlarge the cohort, add starts or start a second pilot after seeing the results.

## 5. Audit original-objective escape separately

Before pilot solves, bind the following audit directions and amplitudes in the pilot manifest:

- Uniform positive z translation of every coefficient for each pilot group, lag and objective,
  starting from that problem's cold initialization.
- Every suspect block and nonzero saved displacement direction in the twelve v3 rejection records
  already published by v4, at their separate source and destination lags, with both signs.

Reuse saved probes as historical comparisons. For the same predetermined rays, derive the limiting
projection, original objective and depth feasibility where the limit exists. Check analytical limits
against diagnostic amplitudes `10^0, 10^2, ..., 10^44`, using original, raw-barrier and bounded-barrier
objectives separately. Keep endpoint and nuisance offsets fixed at explicitly recorded values; do not
optimize offsets along a probe. These evaluations are diagnostic, not extra profile solves. Count their
cost separately toward the pilot deadline. Compare against feasible finite solutions, including pilot
solutions where they describe the same mathematical problem; do not treat a cold or failed state as an
optimum.

Classify each direction separately:

- Exactly unsupported coefficient motion with no observable trajectory change at the fixed offsets.
- Numerically weak support, including activation at a destination lag.
- Observable trajectory growth whose limiting original objective is worse than a feasible finite
  solution by more than the existing tolerance.
- Analytically objective-preserving motion with a finite attained value. A noncompact set of equal-cost
  states alone does not prove that a minimum is unattainable. Treat it as resolved only with an argument
  establishing its invariance and its implications for timing costs and seed transfer; otherwise leave
  the numerical question open.
- Observable escape whose limit improves or is indistinguishable from the best available finite value,
  without such an invariance argument, or whose limit/depth feasibility cannot be established.

The last category, or any unexplained observable growth in pilot traces, produces a numerical blocker.
A mathematical demonstration that the original objective has no finite minimizer can support a
scientific/model blocker. Finite probes alone cannot establish that result. Resolving this finite audit
is not a global-minimum certificate and must be described with that limitation.

Do not add coefficient bounds, scene-volume bounds, new trajectory priors or a data-only ridge penalty to
make the audit pass. Any change to the scientific model requires a separate investigation; it is outside
this plan. Do not generalize the parallel-camera argument to the real rig without checking its geometry.

## 6. Conditional qualification and production continuation

Only after the pilot and escape audit pass, freeze the complete v5 evaluator and run the full exact
control from fresh cold starts and fresh v5 qualification caches. Pilot states remain diagnostic and must
not seed or replace this retest.

Require all twelve groups throughout both objectives, every integer lag −25 through 25, both directions,
and every refinement round. Refine every detected basin to 0.05 frames and competing basins to 0.01 frames.
Retain nonboundary identifiable optima, unchanged ambiguity and whole-group bootstrap gates, and recovery
and sweep agreement within 0.05 frames. Complete this by 90 minutes from the investigation's first action.
Failure or incompleteness ends continuation.

Then carry forward Plan 010 §4 and Plan 009 §4 without relaxing any gate:

1. Rerun all 117 independent controls and the three targeted short-control audits. Verify the 1,890
   production controls' hashes, recipes, generator, fitting code and three-start definitions before reuse;
   unchanged production results require fresh independent qualification. Numerical failures on negative
   or noisy controls are missing evidence, not successful ambiguity demonstrations. Qualified noisy
   cases must recover within 0.25 frames.
2. After every safeguard passes, inventory actual group-edge-window workloads. Select minimum, median
   and maximum observation-count cohorts within training/held-out, window-length, knot-spacing and
   penalty strata, breaking ties by group and edge IDs. Include transformed-constraint Hessians,
   original-unit verification, sanitation, refinement, serialization, memory and measured eight-worker
   throughput in the benchmark.
3. Project all six configurations, three starts, assessment nuisance fitting, both objectives, required
   windows, bootstrap and conditional selection work with the existing factor-of-two runtime margin.
   Include completion/testing of conditional adapters. Start real fitting only if the complete workload
   fits before the packaging reserve; otherwise publish `computational_blocker`. Recheck after each
   configuration. Do not start an adapter before implementing and testing it.
4. Fit optimization groups using immutable v2 code. Assess without refitting production offsets on
   assessment groups across 50–149, both 50-frame halves and all four 25-frame windows. Preserve every
   required edge's support, spatial, timing, bootstrap, independent-versus-production and cycle gates.
   Rank passing configurations by assessment reprojection, then fewer knots, then lower acceleration.
5. Complete the selection adapter only after fitting qualification. Freeze the candidate and extraction,
   association and evaluator policy. Permit one selection attempt with a fresh consumption marker
   immediately before the first selection-frame read, using the existing 150–199 and half-window gates.
   Selection failure ends the investigation. Success freezes candidate offsets and an analogous one-use
   protocol for 200–249. Do not execute that protocol; keep `accepted_timing` null.

Held-out edges must always constrain and fit training-only nuisance state first, then freeze it before
held-out lag evaluation. Held-out observations cannot affect initialization, replacement or nuisance
fitting. Independent entry points must exclude production states and cross-role/window/group seeds.

## 7. Interfaces, tests, evidence and completion

Add `scripts/basketball_shared_workflow_v5.py` with stages:

```text
prepare, diagnose, pilot, safeguard, benchmark, fit, assess, select, package
```

Use `configs/basketball-rev2/timing-shared-v5.json` and separately versioned independent solver/profile
modules. Every executed stage consumes hashed predecessors, writes a fresh directory and shares the
investigation clock. The prepare manifest must import v2 admission and v4 evidence without rewriting
predecessor hashes. Reuse historical verification where appropriate, but verify its current hashes.

Extend cache identities with the v5 transformation, its fixed scale, derivative policy, original depth
margin, solver settings and transfer policy, plus observations, calibration, role/window, group, edge
gauge, spacing, penalty and requested lag. Separate diagnostic, pilot and qualification caches explicitly.
After the pilot passes, changes to exercised solver/profile mathematics invalidate that pass. This plan
does not authorize a different numerical policy or a second pilot after an observed qualification failure.

Add regressions for:

- Feasible-set equivalence, zero and near-zero slack, large positive/negative slack, stable evaluation,
  saturation, derivative underflow and the analytical barrier limits.
- Objective and transformed-depth derivatives, the full constraint Hessian chain rule, fixed physical
  scaling, original-unit multiplier conversion and rejection of misleading transformed convergence.
- Unchanged original objectives, acceleration under constant translation and no added data-only penalty.
- Group 2's camera-plane crossing; groups 9/11's weak-column activation; deterministic destination-cold
  replacement/blending, infeasible seeds and preservation of every coefficient.
- Shared evaluation accounting including derivative requests, strict original depth checks, both early
  deadlines and the packaging reserve, no fourth attempt, and fresh stage outputs.
- Fixed membership in every direction and refinement, sweep disagreement, competing basins, boundary-
  dependent confidence, fractional-offset sign, whole-group bootstrap and independent cycles.
- Held-out isolation, production-state exclusion, cross-version/role/pilot cache isolation and immutable
  production-control reuse.

Publish the mathematical argument and its assumptions, fixed pilot manifest, all pilot decisions,
analytical escape limits and probes, depth/coefficient/support diagnostics, seed ledgers, solver and
barrier traces, original-unit optimality checks, separate directional profiles, bootstrap intervals,
workload projections and role-consumption metadata. Keep unavailable estimates and unexecuted work
explicitly null or unassessed. Retain full evidence in compressed records stored once per attempt, with
hashes and portable references; record serialization and storage costs.

Use `numerical_failure`, `scientific_rejection`, `computational_blocker`, `budget_exhaustion` and
`selection_qualified` consistently. Report the exact gate that stopped continuation. A bounded barrier
alone is not a scientific success or justification for relaxing a gate.

Update method and contender reports while preserving previous failures. Run Basketball, budget and
SelfCap regressions; independently verify hashes, partition isolation, original depths/objectives,
multiplier and seed provenance, documentation links, historical markers, and both working-tree and staged
`git diff --check`. Create local commits for validated milestones using the approved repository procedure.
Continue to the documented blocker or candidate/protocol completion. Do not push.
