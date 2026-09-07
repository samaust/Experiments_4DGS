  # Plan 010: Preserve positive depth and stabilize independent timing profiles

  ## 1. Objective and fixed constraints

  Implement one separately versioned v4 independent evaluator that addresses Plan 009’s negative-depth
  solutions and unstable warm-start transfer.

  Success is either a documented numerical, scientific, computational or budget blocker, or a selection-
  qualified candidate with a frozen, unexecuted final-validation protocol.

  Preserve Plan 009’s admitted observations, production fitting and qualification thresholds:

  - All 34 cameras, accepted calibration and scale, the fixed 72-edge graph and held-outs 0/10/20/30.
  - Plan 008’s tracks, duplicate families, associations and 667/667 partition, with at least 19 groups per
    edge per half.

  - Fitting frames 50–149, previously inspected selection frames 150–199 and untouched final frames 200–249.
  - The six configurations, three unchanged production starts, full ±25-frame search and 0.25-frame timing
    requirement.

  - Historical code, configurations, outputs, consumption markers and the completed Plan 007 audit.

  Start a fresh four-hour elapsed clock at implementation’s first action. Include inspection,
  implementation, diagnostics, tests, failures and commits. Complete diagnosis, evaluator freeze and the
  exact-control retest within 90 minutes. Stop computation at 3h40m and reserve 20 minutes for verification
  and reporting. Use existing dependencies, at most eight CPU workers and single-thread numerical libraries.
  No GPU jobs, downloads, training or reads from prompts.

  ## 2. Diagnose coefficient growth before freezing v4

  Reconstruct the exact 12-group, 100-frame noiseless direction-change control: true offset −0.10 frames,
  ten-frame knots and acceleration weight 1.

  Audit all 12 rejected v3 attempts and their saved seeds, emphasizing:

  - Group 2, ascending at lag −19: positive-depth initialization followed by a camera-plane crossing.
  - Groups 9 and 11, descending from lag −6 to −7: invalid transferred seeds.
  - In those two saved lag −6 seeds, coefficient block 16 has magnitude approximately (10^{43}), while its
    sampled basis-column norm is approximately (3\times10^{-45}). This is evidence of extreme numerical
    conditioning; it does not by itself establish the complete failure mechanism.

  Record source-lag and destination-lag basis support, Jacobian column norms, singular values, numerical
  rank, coefficient magnitudes, trajectory coordinates, per-observation depths, residuals and objectives.
  Distinguish:

  1. Exactly unsupported coefficients.
  2. Numerically weak coefficients that become observable after transfer.
  3. Large motion in observable trajectory directions.
  4. Positive-depth trajectories escaping toward infinity while retaining or improving reprojection fit.

  For each suspect coefficient block, evaluate deterministic amplitude probes along its saved displacement
  from the cold initialization, using both signs and amplitudes (10^0,10^2,\ldots,10^{44}). Keep offsets
  fixed separately at the source and destination lag. These are diagnostic evaluations, not qualification
  solves.

  Compare objectives with the existing tolerance:

  abs(F1 − F2) <= 1e−6 + 1e−4 * max(abs(F1), abs(F2)).

  Finite probes cannot prove a global minimum or nonexistence of one. If observable escape remains
  unresolved, publish a numerical blocker. Use a scientific/model blocker only when supported by a
  mathematical argument or a failed scientific safeguard. Do not introduce coefficient bounds or a data-only
  ridge penalty to conceal the problem.

  ## 3. Freeze one numerical and initialization policy

  ### Constrained optimization

  Replace the independent TRF/LSMR solve with installed SciPy trust-constr. Use analytic sparse objective
  gradients and depth-constraint Jacobians, a sparse Gauss–Newton objective Hessian, and analytic sparse
  constraint Hessians. SciPy supports nonlinear inequality constraints with feasibility preservation through
  this optimizer. Constraint documentation

  Freeze these settings before complete profiles:

  - Retain the original reprojection residuals, spline basis, acceleration term, observation support and
    full coefficient parameterization.

  - Optimize dimensionless offsets offset_frames / 25; retain coefficients in existing rig-diameter units.
    Use fixed physical scaling, without inverse scaling by vanishing Jacobian columns.

  - Require every fitted observation’s normalized depth z / rig_diameter >= 1e−8, with keep_feasible=True.
  - Use sparse augmented-system factorization; set gtol, xtol and barrier_tol to 1e−6, with at most 200
    optimizer iterations.

  - Independently enforce the existing 200 objective-evaluation ceiling. maxiter alone is insufficient.
    Share residual/Jacobian caches and count every distinct residual evaluation, including evaluations
    requested through derivative calculations.

  - Record constraint evaluations, initialization checks, factorization warnings, barrier parameters,
    optimality and constraint violation separately. They all count toward elapsed time.

  - Freeze remaining installed defaults explicitly in provenance. No solver fallback or policy search after
    scientific outcomes.

  The reported objective remains sum(original_residual**2). Internal constraint merit functions and barriers
  must never enter reported profile costs or bootstrap confidence.

  Require finite state, successful termination, optimality at most 1e−6, the depth margin and unchanged
  nuisance-offset boundary checks. Independently recompute these checks at the returned state. A near-
  optimum solution with minimum normalized depth at or below 1e−7 remains unqualified because its result may
  depend on the numerical depth boundary.

  ### Deterministic warm-start transfer

  Keep the original cold initialization and v3 seed-selection order. Modify transfer as follows:

  1. Reset the fixed endpoint to the requested lag.
  2. Classify numerically unsupported source coefficient blocks using sampled spline-basis column norms. Use
     threshold
     max(matrix.shape) * machine_epsilon * largest_column_norm.
     A block is unsupported only when its data basis is below threshold and its acceleration column is also
     below the corresponding threshold, or acceleration weight is zero.

  3. Replace those blocks with coefficients from that same problem’s destination-lag cold initialization.
     Retain every coefficient as an optimization variable; leave other transferred blocks unchanged.

  4. Validate finiteness, offset bounds and destination-lag depths. Require initialization depth strictly
     above twice the optimization margin.

  5. If necessary, blend toward the valid cold initialization using the fixed sequence 1, 1/2, …, 2^-20, 0,
     selecting the first feasible blend. If neither the transferred seed nor cold initialization can provide
     a feasible state, record a failed start. Do not run another initialization optimizer.

  Record replaced blocks, support thresholds, original and sanitized states, source lag, destination lag,
  blend fraction and depth checks. These changes affect initialization only; they add no objective penalty.

  Preserve cold, ascending and descending attempts, with at most three profile solves per group/lag. Retain
  separate directional curves; a cold fallback must remain visible in provenance. Never substitute the best-
  of-three curve for missing directional evidence.

  For held-out edges, constrain and fit training-only nuisance state first. Freeze it before evaluating
  held-out lag. Held-out observations must not influence initialization, coefficient replacement or nuisance
  optimization.

  ## 4. Qualification and budget-gated continuation

  Run the exact control first. It must retain all 12 groups throughout both regularized and data-only
  integer and refined searches, including each sweep direction.

  Preserve:

  - Every integer lag from −25 through 25.
  - Refinement of every detected basin to 0.05 frames and competing basins to 0.01 frames.
  - Fixed group membership across both directions and every refinement round.
  - Nonboundary, identifiable optima; unchanged ambiguity and whole-group bootstrap gates.
  - Recovery and sweep agreement within 0.05 frames for the noiseless control.

  Failure or an incomplete retest at 90 minutes ends the investigation.

  After it passes, rerun all 117 independent controls and the three targeted short-control audits. Verify
  the 1,890 production controls’ hashes, recipes, generator, fitting code and start definitions before
  reuse; reassess their independent qualification. Preserve the distinction between ambiguous negative
  controls and missing numerical evidence. Qualified noisy cases must recover within 0.25 frames.

  After all safeguards pass:

  - Inventory actual group-edge-window workloads.
  - Select benchmark cohorts by minimum, median and maximum observation counts within training/held-out,
    window-length, knot-spacing and penalty strata, breaking ties by group and edge IDs.

  - Measure initialization, constrained optimization, derivative evaluation, refinement, serialization,
    memory and actual eight-worker throughput.

  - Project all six production configurations, their three starts, assessment nuisance fitting, both
    objectives, all required windows, bootstrap aggregation and conditional selection work. Include seed
    sanitation and constraint costs; apply the existing factor-of-two runtime margin.

  - Start real fitting only if the projected complete workload fits before the packaging reserve. Otherwise
    publish computational_blocker. Recheck after each configuration.

  Carry forward Plan 009 §4’s real-fitting, assessment, ranking and selection rules unchanged. Implement and
  test the currently incomplete conditional stage adapters before their first use. Complete the selection
  adapter only after fitting qualification.

  Allow one selection attempt, with a fresh consumption marker immediately before the first selection-frame
  read. Selection failure ends the investigation. Selection success freezes candidate offsets and an
  analogous one-use protocol for frames 200–249. Do not execute that protocol; keep accepted_timing null.

  ## 5. Interfaces, tests and completion

  Add scripts/basketball_shared_workflow_v4.py with stages:

  prepare, diagnose, safeguard, benchmark, fit, assess, select, package.

  Use configs/basketball-rev2/timing-shared-v4.json. Import historical admission through explicit cross-
  version manifests without rewriting predecessor hashes. Production fitting continues to call immutable v2
  code.

  Every executed stage consumes hashed predecessors, writes a fresh directory and shares the investigation
  deadline. Extend cache identities with the v4 solver, scaling, depth margin and transfer policy. Bind
  observations, calibration, role/window, group, edge gauge, spacing, penalty and requested lag.

  Add regressions for:

  - Analytic objective and depth derivatives, fixed scaling and absence of added data-only penalties.
  - Group 2’s camera-plane crossing and groups 9/11’s weak-column activation.
  - Destination-lag seed validation, deterministic replacement/blending, infeasible seeds and preservation
    of every coefficient.

  - Strict evaluation accounting, deadline termination and no fourth profile attempt.
  - Fixed group membership in each direction, sweep disagreement, competing basins and constraint-boundary-
    dependent confidence.

  - Held-out isolation, production-state exclusion, cache isolation, fractional-offset sign, group bootstrap
    and independent cycles.

  - Fresh outputs and immutable production-control reuse.

  Publish depth trajectories, coefficient/support diagnostics, amplitude probes, all initialization
  attempts, constrained-solver traces, separate directional profiles, bootstrap intervals, cache provenance,
  workload projections and role-consumption metadata. Distinguish numerical_failure, scientific_rejection,
  computational_blocker, budget_exhaustion and selection_qualified.

  Update method and contender reports while retaining prior failures. Run Basketball, budget and SelfCap
  regressions; independently verify hashes, partition isolation, seed provenance, documentation links,
  historical markers and both working-tree and staged git diff --check.

  Create local commits for validated milestones using the repository’s approved staging and commit
  procedure. Continue until the documented blocker or candidate/protocol is complete. Do not push.