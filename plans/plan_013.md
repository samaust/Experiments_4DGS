  # Plan 013: Diagnose conditioning and nuisance-offset basins before qualifying v7

  ## 1. Objective, preserved constraints and budget

  Investigate two distinct obstacles identified by v6:

  - Stationarity: 50 data-only attempts still reached the 200-iteration limit.
  - Basin coverage: nine regularized problems converged to costs above qualified historical references, with
    substantially different nuisance offsets.

  Test coefficient conditioning and nuisance-offset search separately, then qualify their combination only
  if both development experiments pass. Completion is a documented blocker or a selection-qualified
  candidate with a frozen, unexecuted final-validation protocol. A development improvement is not timing
  qualification.

  Generating this plan does not execute the investigation, run fits or start its clock.

  Carry forward Plan 012’s admitted observations, calibration, scale, 34 cameras, 72 edges, held-outs,
  667/667 partition, support requirements, six production configurations and three production starts.
  Preserve fitting frames 50–149, previously inspected selection frames 150–199 and untouched final frames
  200–249. Production fitting continues to use immutable v2. Preserve v2–v6 source bytes, configurations,
  evidence, corrections and consumption markers.

  Use a fresh four-hour elapsed budget, starting at implementation’s first action and including inspection,
  coding, diagnostics, tests, failed work, serialization, verification and commits.

   Absolute deadline    Required outcome
  ━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   30 minutes           Baseline verification, saved-state diagnosis, experiment manifests and derivative
                        regressions
  ───────────────────  ─────────────────────────────────────────────────────────────────────────────────────
   60 minutes           Conditioning experiment decision
  ───────────────────  ─────────────────────────────────────────────────────────────────────────────────────
   105 minutes          Scalar nuisance-basin experiment decision
  ───────────────────  ─────────────────────────────────────────────────────────────────────────────────────
   120 minutes          Combined evaluator pilot decision and numerical-policy freeze
  ───────────────────  ─────────────────────────────────────────────────────────────────────────────────────
   165 minutes          Full twelve-group exact-control qualification
  ───────────────────  ─────────────────────────────────────────────────────────────────────────────────────
   195 minutes          Multiple-nuisance qualification and inherited independent controls
  ───────────────────  ─────────────────────────────────────────────────────────────────────────────────────
   220 minutes          Stop scientific computation, including any conditional production/selection work
  ───────────────────  ─────────────────────────────────────────────────────────────────────────────────────
   240 minutes          Complete packaging, verification and local commits

  Use existing dependencies, at most eight CPU workers total and single-thread numerical libraries. No GPU
  jobs, downloads, training or reads from prompts.

  Check shared deadlines inside initialization, metric construction, derivatives, local solves and nested
  searches. An external watchdog must terminate the entire worker process group. Package interrupted stages
  even when no worker artifact exists.

  Development experiments have separate decisions: a failed conditioning experiment may be followed by the
  already frozen scalar-basin experiment, but prevents combined qualification. Arithmetic/provenance
  failures stop affected scientific work immediately. Deadlines and policies cannot be extended after
  observing results.

  ## 2. Verify the baseline and diagnose saved states

  Import v6 through a cross-version manifest binding its final verification, exact-Hessian validation,
  diagnostic records, six compressed pilot records, authoritative pilot policy freeze, corrections and
  inherited v4/v5 reference and escape evidence. Treat the generic v6 workflow’s inherited baseline solver
  metadata separately from its actual exact-Hessian freeze.

  Recompute:

  - 94/144 qualifications: 72 regularized and 22 data-only.
  - Fifty data-only iteration-limit failures, five three-start disagreements and nine reference-cost
    failures.

  - All nine reference failures belonging to regularized groups 2/9/11 at outer lags −25, −20 and −19.
  - The three missing required data-only transfers.
  - Original objectives, depths, KKT residuals, multipliers and seed provenance.

  Freeze first, middle and returned snapshots for all 144 v6 attempts, deduplicating parameter storage
  within identical problems while preserving every reference. Include the lowest qualified historical
  reference for each of the nine cost failures. Historical fitted states are diagnostic references only.

  At these states:

  - Recompute signed objective, depth-multiplier, bound-multiplier and barrier contributions in original q
    coordinates.

  - Separate observable motion, weakly supported coefficients and exact compact-support zeros using the
    existing support/rank thresholds. Retain complete singular spectra and subspace projections.

  - Relate stationarity to saved coefficient motion, observable trajectory changes, barrier parameters and
    trust radii.

  - Compare the nine solution pairs’ nuisance offsets, costs, trajectories, support and stationarity.
    Describe separated stationary solutions as evidence of different basins, not proof of global minima.

  - Mark intermediate multiplier-based KKT unavailable where traces lack multipliers.

  Publish a diagnosis before fitting. Rank deficiency alone neither authorizes removing coefficients nor
  establishes that preconditioning will work. Missing required evidence blocks continuation.

  Reuse the v5 escape audit only after checking hashes, analytical limits, corrected finite-reference
  comparisons and applicability to the unchanged objective/feasible set. Do not enlarge its ray grid.

  ## 3. Freeze and run the two development experiments

  ### A. Conditioning alone

  Use the original 48 pilot problems: groups 2/9/11, both weights and outer lags [-25, -20, -19, -7, -6,
  -0.10, 0, 25]. Run exactly the original 144 cold/ascending/descending local attempts with unchanged
  ordering and physical-state sanitation.

  Change only the coefficient coordinates. For each problem, construct a fixed transformation from its
  deterministic feasible destination-cold state:

  1. Extract coefficient columns of the original residual Jacobian, including acceleration rows only when
     the problem’s weight is nonzero.

  2. Compute a full SVD, with the existing numerical-rank threshold and deterministic repeated-subspace
     handling.

  3. For singular values above that threshold, use t_i = clip(1/sigma_i, 1e-3, 1e3); use t_i = 1 for
     remaining directions.

  4. Form the symmetric, invertible coefficient transform T = V diag(t_i) Vᵀ.
  5. Optimize using q = q_cold + P y, with identity offset blocks and coefficient blocks T.

  Retain every coefficient and null direction. Freeze the transform for the entire problem; never recompute
  it from warm starts or successful fits. A nonfinite, noninvertible or numerically unverifiable transform
  is a failure, not permission to substitute another metric.

  Apply exact chain rules:

  gradient_y = Pᵀ gradient_q
  H_y        = Pᵀ H_q P
  J_g,y      = J_g,q P
  H_g,y(v)   = Pᵀ H_g,q(v) P

  Keep v6’s exact objective Hessian, bounded-depth constraint, full constraint Hessian, initial barrier/
  trust-region settings and solver caps. Preserve original-unit tolerances. Use the conservative internal
  gradient tolerance 1e-6 / max(1, ||P⁻ᵀ||∞) and independently require original-coordinate stationarity at
  most 1e-6; transformed termination alone cannot qualify.

  Count cold-state metric construction in the evaluation ledger, including derivative-first requests. Each
  local attempt retains the 200-iteration and 200-distinct-state ceilings. Map transferred states through
  physical coordinates before destination sanitation and coordinate conversion.

  Conditioning passes only if:

  - All 94 previously qualified attempts remain qualified and their costs do not worsen beyond the inherited
    objective tolerance.

  - At least 25 of the 50 previous failures now qualify, with improvements present in all three groups.
  - Across those 50 attempts, the median ratio of new to previous original-coordinate KKT infinity norms is
    at most 0.1.

  - No unresolved derivative, feasibility, support-activation or observable-growth issue remains.

  These are development screening thresholds, frozen before execution. Record all objective/reference
  disagreements; they are not waived for combined qualification.

  ### B. Scalar nuisance-basin coverage alone

  Use the same 48 problems, with the untransformed v6 local solver, independently of experiment A’s outcome.
  This isolates the effect of searching the nuisance offset.

  For each fixed outer lag, profile camera 3’s nuisance offset nu over every integer from −25 through 25. At
  each point, fix nu and optimize the full coefficient vector. Use cold, ascending and descending
  coefficient paths with deterministic destination-cold sanitation. The initial grid schedules 7,344
  conditional local attempts.

  Each conditional fit must satisfy the original objective, depth and coefficient-stationarity checks. It is
  not a qualified joint fit: publish the omitted nuisance-offset derivative explicitly.

  Refine the union of detected minima from all three directional curves:

  - Refine every detected basin on a 0.05-frame grid within its neighboring coarse-grid bracket.
  - Refine competing minima to 0.01 frames within ±0.05 frames, using the inherited sqrt(F) <= sqrt(F_best)
    + 0.05 competition rule.

  - Preserve flat intervals and boundary basins. A flat nuisance profile alone is not evidence that the
    outer timing parameter is unidentified.

  - Use the same three conditional paths at every added point. Never drop an unresolved point or introduce
    unscheduled retries.

  Candidate locations come solely from these searches. Historical nuisance offsets may assess coverage but
  must not seed fits, define refinement points or influence initialization.

  Basin coverage passes only if:

  - Every scheduled conditional fit qualifies and the three costs agree at each required point within 1e-6 +
    1e-4 * max(|F1|, |F2|).

  - All nine historical lower-cost basins are recovered within 0.05 frames of the reference nuisance offset,
    or contain it in a verified flat interval.

  - Recovered conditional costs are no worse than the corresponding qualified references within that
    tolerance.

  - Both objectives and all 48 problems have complete evidence.

  This establishes tested scalar coverage, not a global-minimum certificate. Record conditional fits,
  refinement fits and later joint fits separately; none may be hidden inside the original “144 attempts”
  count.

  ## 4. Combined qualification and conditional production

  ### Combined pilot

  Proceed only after both development decisions pass. Freeze one combined v7 policy and run a fresh pilot on
  the same 48 problems.

  Use the conditioning transform from A and scalar search from B. Maintain cold, ascending and descending
  outer paths. For each path:

  - Execute its original cold or directional-transfer local solve.
  - Jointly release the nuisance offset and coefficients from every detected interior basin on that path.
  - Validate every required joint solve in original coordinates.
  - Return the lowest qualified original objective for that complete path, while retaining every internal
    result.

  The three-start cost gate applies to the three complete search results. Do not claim that different
  internal local minima agree. Required outer directional transfers remain explicit joint solves; successful
  basin searches cannot conceal failed required transfers.

  Boundary basins remain recorded. A competitive basin that yields only boundary-dependent joint states
  blocks qualification.

  Require all 144 outer search results to qualify, all required transfers to pass, three-path cost
  agreement, and costs no worse than the lowest qualified identical-problem v4/v5/v6 references. No
  development state or cache may seed this pilot.

  Freeze the implementation after a pass. From fresh cold states and qualification caches, run all twelve
  groups, both objectives, every integer outer lag −25 through 25 and inherited 0.05/0.01 refinements.
  Preserve the original identifiability, ambiguity, whole-group bootstrap, nonboundary and 0.05-frame
  noiseless recovery/sweep gates.

  ### Gated extension to multiple nuisance offsets

  The real groups contain 3–20 training cameras. A training-edge gauge can therefore leave up to 18 nuisance
  offsets; training-only fitting for a held-out edge can leave up to 19. Scalar success does not qualify
  these workloads.

  Implement one deterministic extension:

  - Maintain cold, ascending and descending outer paths.
  - Profile each free nuisance offset across its full bounds while locally optimizing the other free
    variables, using the same grid/refinement rules.

  - Also profile a common shift of all nuisance offsets over the exact interval allowed by their bounds.
  - Process individual offsets by camera ID in the ascending path and reverse order in the descending path;
    the cold path uses ascending order.

  - Permit at most four complete cycles. Stop earlier only when a complete cycle changes every nuisance
    offset by at most 0.01 frames and changes objective within the inherited agreement tolerance.

  - Finish with a full joint solve and original-coordinate qualification. Every conditional subproblem must
    qualify in its free variables; no recursive invocation of the basin-search engine is permitted.

  This is a deterministic search policy, not exhaustive joint basin enumeration.

  Validate it on added noiseless direction-change controls with 3, 4 and 20 training cameras, training and
  held-out edge roles, both objectives and twelve groups. Preserve the existing trajectory model and three-
  camera fixture. Add training cameras using the lowest available non-held-out IDs, translations t_x = 2 +
  k/(C-3) for zero-based extra-camera index k, and truth offsets −0.2 + 0.01(k+1); retain the existing held-
  out camera-0 construction. Use the full outer range and inherited recovery gates.

  Benchmark the fixed group-0, lag-0 cases across these camera-count/role/objective combinations before
  launching the complete added suite. If twice the measured projected work cannot fit its deadline, publish
  computational_blocker. Do not omit high-dimensional groups or silently substitute scalar qualification.

  ### Production continuation

  Only after complete evaluator qualification:

  - Rerun all 117 independent controls and three targeted short-control audits; independently verify reuse
    of the 1,890 immutable production controls.

  - Inventory actual group-edge-window workloads, including nuisance dimension. Benchmark minimum/median/
    maximum observation-count cohorts in the inherited role, window, spacing and penalty strata.

  - Include all inner searches, joint releases, initialization, derivatives, validation, serialization and
    memory in the factor-of-two runtime projection.

  - Start real fitting only if all remaining work fits before minute 220. Keep production v2, its six
    configurations and three starts unchanged.

  - Carry forward Plan 012’s assessment, spatial/timing/bootstrap/cycle gates, ranking and one-use selection
    protocol. Implement and test every adapter before invocation.

  - Allow one selection attempt only after candidate/policy freeze and a fresh consumption marker. Final
    validation remains unexecuted and accepted_timing remains null.

  A failed combined pilot or qualification stops subsequent scientific stages. No retuning, increased caps,
  extra cycles, reduced cohort or alternative search is authorized.

  ## 5. Interfaces, verification and completion

  Add separately versioned solver, conditioning, basin-search, profile, diagnostic and reporting modules.
  Expose scripts/basketball_shared_workflow_v7.py with stages:

  prepare, diagnose, condition, basins, pilot, safeguard,
  multinuisance, controls, benchmark, fit, assess, select, package

  Use configs/basketball-rev2/timing-shared-v7.json for all frozen thresholds, schedules and budgets.

  Every stage consumes hashed predecessors and writes fresh outputs. Use explicit caches for diagnosis, each
  development experiment, combined pilot, qualification and production assessment. Bind transform bytes,
  derivative/search source hashes, full physical offsets, conditioned-variable sets, role/window/group/
  gauge, observations, calibration, spacing and penalty. Permit only the explicitly authorized within-family
  sweep transfers; prohibit historical, production and cross-role seeds.

  Record scheduled, executed, missing and qualified counts separately for outer searches, conditional fits
  and joint solves. Store compressed attempt records once, with references from summaries. Packaging must
  support every failed or interrupted stage without inventing absent success artifacts.

  Required regressions include:

  - Invertibility, bounded scaling, deterministic repeated/null subspaces, physical-state round trips and
    objective equality.

  - Exact objective/constraint chain rules, both weights, original-coordinate KKT, mapped stopping
    tolerances and misleading transformed-success rejection.

  - Support activation under nuisance changes and sanitation through physical coordinates.
  - Conditional versus joint stationarity, flat/boundary profiles, refinement completeness, missed basins,
    failed inner fits and reference isolation.

  - Multiple-offset/common-shift bounds, cycle limits, held-out training isolation and production-state
    exclusion.

  - Nested evaluation accounting, both local caps, all absolute deadlines, process-group termination and
    packaging before worker initialization.

  - All inherited Basketball, budget and SelfCap regressions.

  Independently verify historical/current hashes, original objectives and depths, derivatives, multipliers,
  seed provenance, partition isolation, documentation links and consumption markers. Publish both
  development decisions, full search ledgers, the combined decision, resource projections and the terminal
  outcome. Keep unavailable profiles, candidate, intervals and final protocol explicitly null or unassessed.

  Use numerical_failure, scientific_rejection, computational_blocker, budget_exhaustion and
  selection_qualified consistently. Create local commits for validated milestones under the repository
  procedure, continue through the authorized stages, and do not push.