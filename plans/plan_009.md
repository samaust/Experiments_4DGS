  # Plan 009: Repair independent timing profiles and test computational feasibility

  ## 1. Objective, scope and fixed constraints

  Resolve Plan 008’s independent-evaluator failure while preserving the admitted observations and unchanged
  production fitting.

  Success means either:

  - A documented numerical, scientific or computational blocker; or
  - A selection-qualified candidate with a frozen, unexecuted final-validation protocol.

  The agreed scope is evaluator-only revision. Reuse the 1,890 production controls after verifying their
  hashes, recipes, generator, fitting implementation and start definitions. Their independent qualification
  must be reassessed with the new evaluator.

  Preserve:

  - All 34 cameras, the fixed 72-edge graph, accepted calibration and scale, held-outs 0/10/20/30, and the
    0.25-frame timing requirement.

  - Plan 008’s tracks, duplicate families, associations and partition: 667 groups per half, with at least 19
    groups per edge per half.

  - Fitting frames 50–149, previously inspected selection frames 150–199, and untouched final frames 200–
    249.

  - The six configurations: knot spacing 5/10 frames crossed with acceleration weights 0.1/1/10.
  - Historical implementations, outputs, consumption markers and the completed Plan 007 audit.

  Start a fresh four-hour elapsed clock at implementation’s first action. Include inspection,
  implementation, diagnostics, tests, failed attempts and commits. Stop computation at 3h40m and reserve the
  final 20 minutes for verification and reporting. Use existing dependencies, at most eight CPU workers with
  single-thread numerical libraries, no GPU jobs, downloads or training. Never read prompts.

  ## 2. Diagnose and freeze one evaluator revision

  ### Diagnostic comparison

  Reconstruct the exact failing 12-group control: 100 noiseless frames, direction changes, true offset −0.10
  frames, ten-frame knots and acceleration weight 1.

  Compare these predetermined solvers using identical objectives, bounds and initial states:

  1. Original sparse TRF/LSMR with unit scaling.
  2. Sparse TRF/LSMR with x_scale='jac'.
  3. Dense TRF with tr_solver='exact' and the same Jacobian scaling.

  Use groups 0, 5 and 11 at lags −25, −22, −19, −8, −1, 0, 1 and 25. The dense solver is a diagnostic
  reference, not an automatic qualification fallback. It is a local optimizer and cannot certify a global
  minimum.

  Record initial/final residuals, objective, gradient norms, solver optimality, termination reason,
  evaluations, elapsed time, singular values, numerical rank and zero-column identities. Distinguish zero
  columns at one iterate from coefficients unobservable throughout the permitted offset range.

  Compare final objectives using the numerical agreement tolerance:

  abs(F1 − F2) ≤ 1e−6 + 1e−4 × max(abs(F1), abs(F2)).

  Agreement is evidence about numerical consistency, not timing identifiability. Preserve unresolved
  differences.

  ### Frozen revision

  Implement a separately versioned independent evaluator with:

  - The existing reprojection objective, spline basis, quadratic acceleration term and observation support.
  - Analytic sparse Jacobians, TRF/LSMR, x_scale='jac', explicit regularize=True, outer tolerances 1e−6, and
    at most 200 function evaluations per solve.

  - Existing installed LSMR defaults recorded explicitly in provenance; no subsequent tolerance or iteration
    tuning.

  - The full coefficient parameterization. Do not delete coefficients merely because their current Jacobian
    columns vanish. Numerical stabilization of the linear step must not add an acceleration or ridge penalty
    to the reported data-only objective.

  SciPy documents Jacobian scaling and rank-deficiency stabilization for this solver. SciPy least-squares
  documentation

  Freeze the revision before testing its complete profiles. Permit implementation corrections supported by
  failing unit tests, but no alternative solver-policy search after scientific outcomes.

  ### Deterministic initialization and profiling

  For each training edge, group, window, knot spacing and penalty:

  1. Solve every integer lag from −25 through 25 with the original independent cold initialization.
  2. Run an ascending sweep and a descending sweep, retaining all cold results.
  3. Initialize each sweep’s endpoint from the nearest valid cold solution, breaking equal-distance ties
     toward the lower lag. Interior solves use the preceding valid solution from that sweep; if unavailable,
     use the nearest valid cold solution.

  4. Transfer coefficients and nuisance offsets only within that same group, edge gauge, window, knot
     spacing and penalty. Reset the fixed endpoint lag to the requested value.

  5. Retain the lowest-objective converged, positive-depth, nonboundary result at each lag. Preserve every
     failed start and all start provenance.

  At most three solves are allowed per group/lag. Missing seeds or failed attempts remain explicit; they do
  not trigger extra retries.

  Refine every detected basin to 0.05 frames and competing basins to 0.01 frames. Each refinement uses cold
  initialization plus the nearest valid lower ascending and upper descending solutions, with the same three-
  solve limit. Keep the group set fixed across the entire refined search.

  Retain separate ascending and descending aggregate profiles. A qualifying estimate requires complete
  evidence in both directions and lag agreement within 0.05 frames for noiseless synthetic positives, or
  0.25 frames for real/noisy qualification.

  For held-out edges, solve training-only nuisance trajectories and offsets first using the revised
  numerical solver, then freeze them before profiling held-out lag. Held-out observations cannot influence
  initialization or trajectory fitting.

  No independent solve may use production offsets, production coefficients, another group’s solution,
  another role/window, or a solution obtained with a different acceleration penalty.

  ## 3. Safeguards and stopping rules

  Complete the focused diagnosis, revision and exact failing-control retest within the first 90 minutes.
  Otherwise package an early numerical or budget blocker.

  The repaired control must have:

  - All 12 groups supported throughout the integer and refined data-only search.
  - Valid regularized and data-only profiles, with nonboundary, identifiable optima.
  - Recovery within 0.05 frames and agreement between sweep directions.
  - The unchanged bootstrap and ambiguity gates.

  Then run the complete existing 117-case independent matrix under the new evaluator. Reuse only unchanged
  production results; rerun all independent profiles, including previously passing cases and the three
  targeted short-control audits.

  Preserve the existing safeguard distinctions:

  - Independently identifiable noiseless cases must recover within 0.05 frames.
  - Long noiseless positive controls must establish independent identifiability.
  - Short unsupported or ambiguous controls remain unqualified.
  - Any noisy case reported as qualified must recover within 0.25 frames.
  - Stationary and epipolar-direction controls must remain rejected across all acceleration weights.
  - Numerical failure on a negative control is missing evidence, not successful demonstration of ambiguity.

  Add regressions for scaling and analytic derivatives; inactive coefficients becoming observable as offsets
  move; cold/warm initialization provenance; sweep disagreement; regularization-only confidence; competing
  basins; held-out isolation; production-state exclusion; cache isolation; fractional-offset sign; group
  bootstrap units; inconsistent independent cycles; deadline termination; fresh outputs; and immutable
  production-control reuse.

  Stop before real fitting if any required safeguard fails or remains incomplete. Do not raise the
  evaluation cap, narrow the lag search, remove difficult groups, or weaken timing thresholds.

  ## 4. Budget-gated real fitting and one conditional selection attempt

  ### Computational feasibility

  After safeguards pass, inventory the actual group-edge-window workload and benchmark a deterministic
  cohort selected by observation counts and edge type, without consulting timing outcomes.

  Include training and held-out edges, 100/50/25-frame windows, both knot spacings, and regularized/data-
  only solves. Record solver time, evaluations, Jacobian dimensions and memory.

  Project:

  - Six configurations with three unchanged production starts each.
  - Assessment nuisance fitting and all required edge/window profiles.
  - Three initialization attempts per profile point, refinement, bootstrap aggregation and serialization.
  - Selection adapter completion, extraction and assessment.

  Use measured per-solve costs at the 200-evaluation limit, a factor-of-two runtime margin, and observed
  eight-worker throughput. Account separately for held-out profiles, whose frozen trajectories avoid
  repeated nuisance optimization.

  Cache only mathematically identical problems. In particular, data-only curves may be shared across
  acceleration configurations with the same knot spacing. Cache keys must bind observations, role/window,
  group, edge gauge, calibration, knot spacing, penalty, solver policy and requested lag.

  Start real production fitting only if the projected complete fitting-and-assessment workload fits before
  the packaging reserve. Otherwise publish computational_blocker, with measured costs and required budget.
  Recheck the projection after each completed configuration; unfinished configurations remain unassessed.

  ### Fitting qualification

  Use unchanged production fitting on optimization groups only. Assess frozen offsets on assessment groups
  across 50–149, both 50-frame halves and all four 25-frame windows, preserving whole-group membership.

  Every required edge/window must retain:

  - At least 12 complete assessment groups and the existing spatial-consistency limits.
  - Identifiable, nonboundary regularized and data-only optima.
  - Bootstrap 95% halfwidth at most 0.25 frames.
  - Independent-versus-production disagreement at most 0.25 frames.
  - Independent cycle closure at most 0.25 frames.
  - The new sweep-consistency requirement.

  Rank configurations passing every gate by assessment reprojection error, then fewer knots, then lower
  acceleration weight. Never refit production offsets using assessment groups.

  ### Selection and final-validation boundary

  The existing selection entry is incomplete. Complete and test its adapter only after fitting
  qualification, before selection access.

  Freeze the winning configuration, evaluator, extraction/association policy and graph. Freshly extract
  selection tracks using the unchanged Plan 008 policy adapted to seeds 150, 160, …, 190 and 199, with a 30-
  frame minimum and role-specific hash-verified masks. Treat every eligible selection group as assessment
  data.

  Create a separate one-use attempt marker immediately before the first selection-frame read. Evaluate 150–
  199 and its two 25-frame halves using all 72 edges, the existing timing gates, fitting-versus-selection
  agreement and temporal-half agreement.

  Failure ends the investigation without another candidate. Success freezes candidate offsets and an
  analogous one-use protocol for 200–249. Do not execute that protocol or mark timing accepted.

  ## 5. Interfaces, evidence and completion

  Add scripts/basketball_shared_workflow_v3.py with stages:

  prepare, diagnose, safeguard, benchmark, fit, assess, select, package.

  Use a new frozen configuration at configs/basketball-rev2/timing-shared-v3.json. The prepare stage imports
  and verifies Plan 008 admission through an explicit cross-version manifest; it must not rewrite old
  configuration hashes to satisfy predecessor checks.

  Every stage consumes hashed predecessors, writes a fresh directory and shares the investigation deadline.
  Production fitting continues to call the immutable v2 implementation. New independent code must not change
  its behavior.

  Publish solver comparisons, rank diagnostics, all initialization attempts, independent/data-only curves,
  sweep comparisons, bootstrap intervals, cache provenance, runtime projections and explicit role-
  consumption metadata. Distinguish scientific_rejection, numerical_failure, computational_blocker,
  budget_exhaustion and selection_qualified. Keep accepted_timing null.

  Update the method and contender reports while retaining previous failures. Run Basketball, budget and
  SelfCap regressions; independently verify artifact hashes, partition isolation, documentation links,
  historical markers and both working-tree and staged git diff --check.

  Create local commits for validated milestones using explicit task-related paths and the repository’s
  approved staging/commit procedure. Continue after commits until the candidate/protocol or documented
  blocker is complete. Do not push.
