# Plan 015: Reconcile state accounting and qualify a focused coefficient-solver benchmark

## 1. Objective, scope and budget

Explain the v8 counter discrepancy, implement one authoritative evaluation ledger, and use a small,
frozen benchmark to diagnose and improve coefficient-only solver reliability. Test initialization and
stopping behavior separately. Preserve the successful scalar basin-discovery policy.

This plan's implementation phase has a **90-minute elapsed hard cap**. Planning does not start the clock.
Freeze the start time and absolute deadlines before the first implementation action. Include inspection,
coding, diagnostics, reproduction attempts, failed work, experiments, tests, verification and commits.

| Absolute deadline | Required outcome |
| --- | --- |
| 20 minutes | Historical admission, counter-audit findings and benchmark manifest frozen |
| 35 minutes | Accounting correction, canonical state implementation and accounting regressions verified |
| 45 minutes | Saved-state diagnosis published; candidate changes and their screening rules frozen |
| 65 minutes | Separate numerical, initialization and stopping experiments decided |
| 75 minutes | Conditional fresh benchmark of the selected policy completed; stop scientific computation |
| 90 minutes | Independent verification, terminal package and local commits completed |

Unused time does not extend later deadlines. Stop an affected stage immediately for an unresolved
arithmetic or provenance failure. Package ordinary scientific rejection, computational blockers and budget
exhaustion distinctly; do not turn an unexecuted experiment into a rejection.

Completion is either a documented blocker/rejection or `ready_for_full_screens`. The latter means only
that the focused benchmark passed. Section 8 specifies the subsequent full screens, but their execution
requires a separately frozen elapsed budget and schedule; this 90-minute phase does not launch them or
automatically extend its clock. Full evaluator qualification, real-data fitting, selection and final
validation remain outside scope.

Preserve throughout:

- At most **200 iterations and 200 distinct evaluated parameter states per local attempt**. Neither cap
  may increase, including during instrumentation, feasibility initialization or any internal restoration.
- Immutable v2–v8 sources, configurations, results, verification reports, corrections and consumption
  markers. Publish new corrections and evidence separately; never rewrite v8 into a passing experiment.
- The objective, observations, calibration, coefficient count, null directions, support/rank thresholds,
  depth and offset bounds, production configurations and data partitions.
- Existing dependencies, at most six numerical workers and eight CPU workers total, with single-thread
  numerical libraries. No GPU jobs, downloads, training or reads from `prompts`.
- Original-coordinate stationarity at most `1e-6`, qualification depth above `1e-7`, and the inherited
  objective-agreement tolerance `1e-6 + 1e-4 * max(abs(F1), abs(F2))`.

## 2. Admit the evidence and distinguish observations from hypotheses

Verify the [v8 evidence manifest](../docs/experiments/basketball-shared-timing-v8/evidence.json), its
inherited hashes, installed SciPy implementation, source freezes, independent verification and markers.
Recompute the following counts from the attempt artifacts, not merely their summaries:

- Conditioning: 144 scheduled/executed attempts, 116 qualified, 93/94 prior qualifications preserved,
  23/50 failures recovered, and median failed-attempt KKT ratio `0.2500454027892694`.
- Twenty-two conditioning attempts report the inner `200 distinct objective evaluations exhausted`
  exception while exported state counts range from 171 to 193.
- Scalar search: 48 completed profiles, 7,344 initial and 4,782 refinement path attempts; 10,596 executed
  conditional fits, 8,485 qualifications, and 1,530 missing directional fits.
- Regularized scalar fits: 8,439/8,454 executed fits qualified. Data-only scalar fits: 46/2,142 executed
  fits qualified; another 1,530 required data-only fits lacked valid seeds.
- The data-only failures include 2,093 iteration-limit exits and three infeasible cold initializations.
  The 15 regularized failures comprise nine iteration-limit exits, three infeasible cold initializations
  and three `xtol` exits without qualifying stationarity.
- Scalar path costs disagreed at 835 points. All nine historical basins passed independent coverage
  checks at detected minima, with acceptable costs.

Preserve the independently verified historical reconstruction and original-cost/KKT evidence when their
hashes and applicability remain valid. Identify precisely which accounting and efficacy claims the new
audit can support. The discrepancy is evidence of inconsistent reporting or accounting; it does not by
itself prove duplicate evaluations, a breached cap, or that conditioning would pass after repair.

## 3. Audit and repair state accounting before numerical adaptation

### Audit the actual request paths

Trace v8's physical, original scaled and conditioned coordinates through objective, gradient, Hessian,
constraint, initialization and returned-state checks. Audit both byte-keyed caches and every counter.
In particular, compare the objective's physical-coordinate round trip with the Hessian's direct `P @ y`
conversion. Establish whether differences are duplicate work, distinct floating-point states, omitted
states, or a combination; do not assume numerical closeness makes two states identical.

For all 22 affected attempts, publish the exception owner, recorded counters, available state identities,
request types and limits of recoverability. Compare the actual transform and origin with the inherited
Plan 013 contract, including its cold-state origin, symmetric coefficient transform, offset scaling and
stopping norms. Treat any contract deviation separately from the cache/counter repair.

Start with saved records and observation-only synthetic derivative sequences; do not optimize saved fitted
states. If solver execution is essential, permit at most one instrumented reproduction for one selected
affected attempt per group, three total. Freeze those choices first, restore the recorded original
initialization and source problem, and retain all outcomes without retry. Enforce both 200 caps across
the entire reproduction. Compare status, trace, parameters, objective and depths when full reproduction
is possible; if enforcing complete accounting changes termination, label it an instrumented diagnostic,
not an exact replay. Its states must never seed the benchmark.

### One authoritative state identity and ledger

Implement a separately versioned adapter that:

- Constructs one canonical original-coordinate state for each solver request, derives its physical state
  once, and supplies that same state to every objective and derivative implementation.
- Uses exact canonical bytes and an immutable mathematical-problem identity for cache ownership. Never
  round coordinates, use approximate equality, or merge neighboring states to save budget.
- Routes every request through one ledger **before** numerical evaluation. Record request type, state
  identity, physical/canonical/conditioned bytes, cache hit or miss, and counter values before and after.
- Includes cold-state transform construction, derivative-first requests, constraint-only evaluations,
  rejected trial states, sanitation/feasibility trials and any returned-state evaluation. Repeated requests
  at the same canonical state consume no additional distinct-state allowance.
- Makes inner caches subordinate memoization stores, with no independent hidden stopping counter. The
  exported ledger and the counter that enforces the cap must agree exactly.
- Prevents a 201st distinct state before any evaluation at that state. Initialization and internal
  restarts cannot reset the ledger; any iterative initialization also shares the local iteration budget.
- Separately records allocated, entered, completed and interrupted evaluations. A worker interruption
  must not turn an uncertain executed count into zero or a falsely exact total.

Do not repair counters by changing labels or copying one count into another. Independently instrument the
lowest-level numerical entry points and reconcile their observed states with the exported ledger. For a
common unchanged state, use the inherited checks: objective `atol=1e-10, rtol=1e-9`, depths
`atol=1e-12, rtol=1e-12`, and gradient/KKT contributions `atol=1e-10, rtol=1e-8`. Reproduction parameter
comparisons use `atol=1e-10, rtol=1e-10`.

Publish a correction supplement identifying the earlier verifier's blind spot. Where v8 did not serialize
enough information to recover an exact count, preserve `unknown`; do not infer it from iteration count or
rerun outputs. Admission to the new benchmark requires an explained mechanism and verified new accounting,
not fabricated completeness of the old ledger. Any change to the coordinate contract needs its own
equivalence/derivative checks and explicit label in comparisons.

## 4. Freeze a representative benchmark and diagnose it without fitting

Select at most **24 distinct conditional problems**, each identified by group, outer lag, fixed camera-3
offset and weight, from hash-verified v8 records. Preserve all associated path references when problems
overlap. Use a deterministic ordering: group, weight, outer lag, nuisance offset, then cold/ascending/
descending path. Freeze the manifest before running any numerical candidate.

Cover all three groups and both weights. Include:

- Data-only cold and directional iteration-limit failures, including support-changing transfers.
- Missing directional seeds and the failures of their source paths.
- The regularized infeasible-cold cases and all three regularized `xtol` failures.
- Six successful controls: one regularized and one data-only conditional problem per group.

For each failure stratum, select the earliest available example per group; retain all three rare `xtol`
examples globally. Deduplicate physical problems, not required paths or diagnostic labels. If a group has
no member of a stratum, record that absence rather than substituting a different failure category. Freeze
the exact resulting list, eligibility checks and selection script before fitting.

Run all three coefficient paths at each selected target. Freeze a minimal set of at most 24 additional
source-cold problems needed to exercise the transfers. These sources must be generated fresh for each
policy. For a historically missing seed, prescribe its source coordinate from the original coarse grid
and inherited ordering before execution. Preserve the inherited nearest-valid/previous-valid selection
rules within this declared benchmark schedule. These local paths do not establish full-sweep coverage.

Add at most four joint diagnostic targets: one affected conditioning case per group and the lost
regularized qualification at group 11, outer lag −19, descending. Allow at most four fresh source-cold
dependencies for these targets. Thus each policy schedules at most **104 local attempts**: 72 conditional
targets, 24 source-cold dependencies, four joint targets and four joint dependencies. Count every actual
scheduled dependency even when it is unsuccessful or unused.

Saved fitted states are references for diagnosis and cost comparison only. They must not initialize a
baseline, candidate, dependency, directional path or later full screen.

At first, middle and returned saved states where available, diagnose:

- Full residual-Jacobian spectra, coefficient support and deterministic repeated/null subspaces using the
  existing thresholds. Distinguish exact unsupported columns from weakly supported observable directions.
- Original-coordinate objective gradients, signed constraint contributions, KKT values, complementarity,
  barrier parameters, trust radii, observable motion and coefficient motion.
- Whether limited progress occurs in observable directions, flat directions, feasibility restoration or
  repeated trust-region contraction. Recompute exact curvature only for the frozen diagnostic directions;
  reuse the applicable escape audit without adding rays.
- The reason for each infeasible cold state and each missing directional seed. Missing-seed failures are
  dependencies to explain, not thousands of independent solver failures.

Keep unavailable intermediate multipliers/KKT explicitly unavailable. Do not infer that rank deficiency
authorizes coefficient removal or that a flat scalar curve establishes unidentifiable outer timing.

## 5. Test bounded, separate adaptations

After diagnosis, freeze exact implementations, settings, target subsets and screening rules by minute 45.
Allow a common corrected-accounting baseline, at most three standalone candidate arms, and at most one
fresh combined benchmark policy: **five policies and 520 local attempts maximum**, plus the three optional
accounting reproductions. These are ceilings, not targets. Do not reallocate unused arms into a tuning
sweep, replace failed cases, retry failed local solves or extend deadlines.

The baseline preserves the inherited numerical method apart from the documented accounting/coordinate
correction. Clearly distinguish comparisons with that fresh baseline from comparisons with archived v8.

### Coefficient-solver arm

Select at most one numerical adaptation supported by the frozen diagnosis. Prefer repairing the existing
full-coordinate conditioning/metric implementation when poor scaling is demonstrated. Preserve all
coefficients and null directions, identity nuisance blocks, the objective, bounded-depth constraint and
exact derivative chain rules. Freeze scales and any trust-region mapping before fitting; never select
them from successful candidate states.

Require preservation of all qualified benchmark controls without cost deterioration beyond the inherited
tolerance, recovery of at least half the frozen iteration-limit target attempts with examples in all
three groups, and median new/baseline original-coordinate KKT ratio at most 0.1 on those targets.
Freeze positive, independently verified baseline KKT denominators before fitting; an unavailable
denominator leaves this screen unassessed until its diagnostic evidence is resolved. Unavailable
candidate KKT counts as an infinite ratio. No unresolved derivative, support, feasibility or
observable-growth issue may remain. A different adaptation needs an equally explicit screen frozen before
execution; this does not authorize changing the model or fitting an unbounded sequence of alternatives.

### Initialization arm

Test one deterministic destination-feasible initialization policy only if the diagnostic evidence requires
it. Derive it from the destination observations/calibration and cold construction. For a fixed offset,
exploit the known depth-constraint structure without changing the feasible set or adding a persistent
objective penalty. Any feasibility subsolve and its evaluations must share the parent attempt's caps.

Require valid bounded parameters and depths above `2e-8` for every selected infeasible-cold case. Verify
changing camera-3 support and physical-coordinate sanitation. Also measure subsequent local qualification
and effects on controls; feasible initialization alone is not a qualified fit. Missing seeds remain missing
unless the prescribed fresh source solve qualifies—never manufacture a transfer by silently substituting
a destination cold fit.

### Stopping arm

Test one explicit stopping/trust-radius policy only if the saved traces justify it. SciPy's `xtol` concerns
trust-region radius, whereas `gtol` concerns the Lagrangian gradient; inspect the hash-bound installed
implementation as well as the [SciPy reference](https://docs.scipy.org/doc/scipy/reference/optimize.minimize-trustconstr.html).

Keep original-coordinate stationarity at `1e-6`. The lost regularized conditioning case's recorded KKT is
approximately `1.02844e-6`; its proximity to the threshold is not grounds to relax it. Require all frozen
`xtol` target attempts to qualify within the same local caps and preserve qualified controls and their
costs. No restart or second solve may conceal the total iterations/states used for one attempt.

Only individually validated changes may enter the final benchmark policy. Record the exact union and its
rationale before execution. Inactive or rejected arms remain explicit; no post-result retuning is allowed.

## 6. Focused benchmark acceptance and stopping criteria

Use fresh problems, starts, caches and dependency states for the selected policy. Freeze it before the
final benchmark; no state from another policy may seed it.

`ready_for_full_screens` requires all of the following:

- Every required conditional target, joint target and source dependency qualifies within both 200 caps;
  there are no missing required directional seeds.
- All previously qualified controls remain qualified with no cost deterioration beyond the inherited
  tolerance. All three target-path costs agree at every benchmark conditional point.
- Independently reconstructed original objectives, depths, full KKT contributions and state counts pass.
  Conditional fits also publish the omitted camera-offset objective and Lagrangian derivatives and remain
  explicitly distinct from jointly qualified fits.
- Transform/metric, support activation, seed isolation and observable-growth checks are resolved.
- Initialization and stopping changes have their separate evidence, and the final policy introduces no
  new failure among their frozen targets.
- The benchmark, tests and independent verification complete within the fixed deadlines.

Otherwise publish the failed criteria and stop with the appropriate terminal classification. A numerical
arm's development screen is not the final benchmark gate. The benchmark's pass is not a full-screen,
combined-pilot or production qualification.

## 7. Implementation, tests and deliverables

Implement separately versioned v9 accounting, solver, initialization, stopping, benchmark and reporting
components. Expose `scripts/basketball_shared_workflow_v9.py` with stages:

`prepare, account, diagnose, adapt, benchmark, package`.

Freeze policies, tolerances, case manifests, arm limits and absolute deadlines in
`configs/basketball-rev2/timing-shared-v9.json`. Require hashed predecessors and fresh outputs. Keep
separate namespaces for accounting reproduction, diagnostic probes, each policy and final benchmark.
Bind observations, calibration, group, role, gauge, window, spacing, weight, physical offsets, free
variables, transform/origin bytes, dependency provenance and implementation hashes.

Required regressions include:

- Reproduction of the two-cache discrepancy; exact canonical identity across every numerical entry point;
  adjacent floating-point states remaining distinct; offset and coefficient round trips.
- Objective-, gradient-, Hessian- and constraint-first requests, rejected iterations, barrier updates,
  cache hits, returned-state ownership and enforcement before the 201st distinct state.
- One shared iteration/state budget across initialization, transformations and internal restoration.
- Full transform invertibility and contract compliance, deterministic repeated/null subspaces, objective
  equality, exact objective/constraint derivatives and misleading transformed convergence rejection.
- Feasible initialization, support activation, missing source dependencies, seed isolation, and conditional
  versus joint stationarity; `xtol` exits must never imply original-coordinate qualification.
- Nested deadlines, entire-process-group termination and packaging failed/interrupted stages, including
  no worker artifact and truncated event records. Unknown executed counts must remain unknown.
- All inherited Basketball, budget and SelfCap tests, retaining the scoped historical test-clock harness
  and immutable tests.

Publish the v8 accounting correction, benchmark selection/diagnosis, standalone arm decisions, final
benchmark decision, source/attempt/state ledgers, cost/KKT/runtime comparisons, verification blind spots
and an independent final report under `docs/experiments/basketball-shared-timing-v9/`.

The independent verifier must observe actual numerical-entry states and cap enforcement rather than
checking only that the exported ledger agrees with itself. Reverify hashes, physical arithmetic, seed
provenance, partition isolation and consumption markers. Report scheduled, executed, missing and qualified
attempts separately from numerical evaluations and diagnostic/reproduction work.

Keep accepted timing, production candidate and final-validation protocol null. Create local commits for
completed validated milestones, continue through authorized gates, and do not push.

## 8. Specify the next full-cohort continuation before proposing it

If the focused benchmark passes, publish the frozen candidate hash and a continuation manifest. Use
measured initialization, derivative, local-solve, serialization and verification times to estimate complete
work, with a factor-of-two margin and explicit allowances for refinement and packaging. State uncertainty:
a small benchmark cannot guarantee the full refinement workload. Freeze an absolute elapsed budget and
external watchdog schedule before any full-cohort launch; do not charge those runs to an expired phase.

The continuation must preserve these gates from Plan 014:

1. Repeat the full 144-attempt conditioning screen on the original 48 problems and three paths, using
   corrected accounting. Preserve all 94 v6 qualifications and their costs; recover at least 25 of the 50
   v6 failures across all three groups; require median KKT ratio at most 0.1, with unavailable values
   counted as infinite. Retain all reference-cost and three-start disagreements. Freeze which selected
   initialization/stopping changes are common to the new baseline and which coordinate change is under
   test; do not attribute gains from multiple repairs to conditioning alone.
2. Independently repeat scalar search on all 48 problems, starting with exactly 7,344 required path
   attempts. Use the newly qualified coefficient policy, identified explicitly as a changed inner solver;
   freeze any controlled comparison needed to separate it from the outer conditioning experiment.
   Retain the original integer grid, inclusive minima/endpoints, 0.05/0.01 refinement, competition rule,
   three paths at every point and complete flat-interval evidence. Historical offsets remain assessment
   references only. Require every conditional fit, every path agreement and all nine historical basin/cost
   comparisons to pass.
3. A completed conditioning screening rejection may still be followed by the frozen independent scalar
   screen. An unresolved arithmetic/provenance failure blocks affected continuation. Complete scheduled
   cohorts despite ordinary failures where their fixed deadlines permit; retain missing work without retry.
4. Run a fresh combined pilot only if both full screens pass. Preserve the original required outer
   transfers and all interior-basin releases, including retained interior flat-grid locations. Require all
   144 complete outer paths to qualify, required transfers to pass independently, three-path cost agreement
   and no deterioration versus the lowest qualified identical-problem historical references. Competitive
   basins supported only by boundary-dependent joint states remain blockers.

No small-benchmark pass, correction of v8 accounting, successful basin recovery or near-threshold KKT value
waives any full-screen gate. A combined pass permits proposing subsequent evaluator qualification; it
does not authorize production timing or consumption of selection/final-validation data.
