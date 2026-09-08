  # Plan 014: Recover historical diagnostics and compare two solver improvements

  ## 1. Objective, boundaries and fixed budget

  Recover the missing historical stationarity evidence, then independently test coefficient conditioning and
  scalar nuisance-offset search. Run a fresh combined pilot only if both experiments pass.

  Completion is either a documented blocker or a passed combined development pilot. Full evaluator
  qualification, multiple-nuisance controls, real-data fitting, selection and final validation are outside
  this plan.

  Preserve these constraints throughout:

  - 200 iterations and 200 distinct evaluated parameter states per local solve, including any historical
    replay. Neither limit may increase.

  - Immutable v2–v7 source, configurations, results, corrections and consumption markers.
  - The existing objective, observations, calibration, support thresholds, coefficient count, bounds,
    production configurations and data partitions.

  - Existing dependencies; at most six numerical workers, eight CPU workers total, and single-thread
    numerical libraries. No GPU jobs, downloads, training or reads from prompts.

  Use a fresh four-hour elapsed implementation budget, including inspection, coding, recovery, experiments,
  tests, failed work, packaging and commits. Planning does not start this clock.

   Absolute deadline    Required outcome
  ━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   30 minutes           Baseline admission, historical recovery decision and experiment manifests
  ───────────────────  ─────────────────────────────────────────────────────────────────────────────
   70 minutes           Conditioning implementation, derivative regressions and experiment decision
  ───────────────────  ─────────────────────────────────────────────────────────────────────────────
   170 minutes          Scalar-search implementation, regressions and experiment decision
  ───────────────────  ─────────────────────────────────────────────────────────────────────────────
   220 minutes          Conditional combined pilot completed; stop scientific computation
  ───────────────────  ─────────────────────────────────────────────────────────────────────────────
   240 minutes          Packaging, independent verification and local commits completed

  Freeze these deadlines before implementation. Unused time does not extend later deadlines. A scientific
  experiment failing its screening criteria does not prevent the other independent experiment; an unresolved
  arithmetic or provenance failure blocks affected work.

  ## 2. Recover the historical evidence

  ### Admit and freeze the comparison cohort

  Verify the v7 evidence manifest and its inherited hashes. Reconfirm the v6 baseline: 94/144 qualified
  attempts, including 72 regularized and 22 data-only; 50 iteration-limit failures; five three-start
  disagreements; nine reference-cost failures; and three missing required data-only transfers.

  Reuse the hash-verified 432 v6 diagnostic references and nine lowest historical reference states. Preserve
  the original reference choices. Historical and replay states remain diagnostic references and must never
  initialize either experiment or the combined pilot.

  ### First attempt: reconstruction at unchanged saved states

  Implement a separately versioned diagnostic adapter for the installed, hash-bound SciPy implementation.

  - Reconstruct the solver’s multiplier calculation from the original-coordinate objective gradient,
    canonical constraint Jacobian, slack scaling and recorded barrier parameter.

  - Audit constraint ordering, lower/upper-bound signs, feasible-slack reconstruction and returned-state
    ownership, including rejected iterations and barrier updates.

  - Handle v4 raw-depth constraints separately from the v5/v6 bounded-depth transformation.
  - Use the solver’s least-squares multiplier calculation. Do not substitute central-path estimates or
    choose multipliers merely to reproduce a scalar KKT norm.

  - Do not optimize or change any saved fitted parameters.

  Before accepting historical reconstruction, validate the method against all 288 v5/v6 returned records
  containing actual multipliers, plus instrumented synthetic v4 tests that capture actual raw-depth
  multipliers. Compare full multiplier vectors, signed gradient contributions, complementarity and KKT
  vectors.

  Freeze these comparison tolerances:

  - Multiplier vectors and signed contributions: atol=1e-10, rtol=1e-8.
  - Original objective: atol=1e-10, rtol=1e-9.
  - Original depths: atol=1e-12, rtol=1e-12.
  - Recomputed versus recorded KKT infinity norm: atol=1e-10, rtol=1e-8.

  Accept reconstruction for a historical state only when the source audit establishes that all required
  inputs are recoverable and its checks pass. Matching the historical scalar optimality alone is
  insufficient.

  ### Bounded fallback: instrumented historical replay

  For each unresolved historical state, permit one replay of its original v4 attempt, at most nine replays
  total.

  - Use an observation-only wrapper around the immutable v4 solver to capture returned multipliers.
  - Restore the recorded original seed, source lag, destination problem and sanitation procedure. Require
    the selected initialization to match the saved initialization.

  - Keep the original numerical settings, dependency implementation and both 200 limits.
  - Require identical termination status and iteration count; compare returned parameters and recorded
    parameter traces with atol=1e-10, rtol=1e-10, and compare objectives, depths and KKT norms using the
    tolerances above.

  - Record replay multipliers as supplementary reproduction evidence, never as values originally serialized
    by v4.

  - Do not retry a divergent replay, substitute another reference or relax tolerances.

  Publish an independently verified supplement identifying each state’s evidence as reconstructed, replayed
  or unresolved. Recompute the signed historical stationarity comparisons and reverify the unchanged v5
  analytical escape audit, including corrected finite-reference comparisons; do not add rays.

  Recovery passes only when all nine historical references have verified supplementary evidence. Otherwise
  package the blocker and leave both experiments unassessed.

  ## 3. Run the two independent experiments

  Freeze both schedules and screening rules before either experiment runs. Implement and test each adapter
  before invoking its scientific cohort.

  Use the same 48 problems: groups 2/9/11, weights 0 and 1, and outer lags [-25, -20, -19, -7, -6, -0.10, 0,
  25]. Use v6’s original cold, ascending and descending ordering and seed-selection rules.

  ### A. Conditioning only

  Change only the coefficient coordinates, following Plan 013:

  - Construct the fixed coefficient transform from the deterministic feasible destination-cold residual
    Jacobian.

  - Use the full SVD and inherited deterministic repeated-subspace/rank rules. For supported singular values
    use clip(1/σ, 1e-3, 1e3); use scale 1 for remaining directions.

  - Retain every coefficient and null direction. Keep identity nuisance-offset blocks.
  - Apply exact objective and constraint derivative chain rules. Keep the v6 exact Hessian, bounded-depth
    constraint and solver settings.

  - Use internal gradient tolerance 1e-6 / max(1, ||P⁻ᵀ||∞) and independently require original-coordinate
    stationarity at most 1e-6.

  - Include cold-state derivative evaluation in each local attempt’s state ledger. Freeze transform bytes
    per problem; transfer states through physical coordinates before destination sanitation.

  Run exactly the original 144 local attempts.

  Conditioning passes only if:

  - All 94 previously qualified attempts remain qualified without objective deterioration beyond 1e-6 + 1e-4
    × max(|F_old|, |F_new|).

  - At least 25 of the 50 previous failures qualify, with recoveries in all three groups.
  - The median new/old original-coordinate KKT norm ratio across those 50 attempts is at most 0.1;
    unavailable new KKT values count as infinite ratios.

  - No unresolved derivative, feasibility, support-activation or observable-growth issue remains.

  Retain all reference-cost and three-start disagreements even when the development screen passes.

  ### B. Scalar offset search only

  Use the unconditioned v6 solver. At each fixed outer lag, fix camera 3’s offset at every integer from −25
  through 25 and optimize the complete coefficient vector.

  Run three coefficient paths using inherited initialization and transfer rules: 7,344 initial conditional
  attempts. Sanitation must account for changing camera-3 support.

  Every conditional fit must pass original-objective, depth and free-coefficient stationarity checks.
  Explicitly publish the omitted camera-offset derivative; conditional qualification is not joint
  qualification.

  Refine the union of local minima from all three curves:

  - Use inclusive neighboring comparisons to retain tied minima and endpoint basins.
  - Refine each coarse minimum’s neighboring bracket at 0.05 frames.
  - Refine competing minima within ±0.05 frames at 0.01 frames, using sqrt(F) ≤ sqrt(F_best) + 0.05.
  - Evaluate all three paths at every added point. Deduplicate grid coordinates, not required paths.
  - Preserve flat intervals. A flat interval used for reference coverage must have complete 0.01-frame
    evidence throughout the interval, with qualified and agreeing paths and cost spread within the
    objective-agreement tolerance.

  - Derive every location from the curves. Historical offsets must not influence initialization, point
    selection or refinement.

  Complete the scheduled cohort despite ordinary fit failures where the deadline permits; retain unresolved
  points and do not add retries. Arithmetic or provenance failures stop affected computation immediately.

  Offset search passes only if every required conditional fit qualifies, all three costs agree at every
  point, and all nine historical basins are recovered within 0.05 frames—or within a verified flat interval—
  at costs no worse than their references within the inherited tolerance. Both objectives and all 48
  problems require complete evidence.

  ## 4. Combine only after both passes

  Freeze the combined policy before execution. Start with fresh problems and caches; no development or
  historical fitted state may seed the combined pilot.

  For each outer problem:

  - Construct the prescribed cold-state conditioning transform.
  - Run a fresh scalar profile with cold, ascending and descending conditional paths and the same refinement
    rules.

  - Preserve the original outer cold or directional-transfer local solve for each corresponding path.
  - Jointly release coefficients and camera 3’s offset from every detected interior basin on that path.
  - For a flat basin, release each distinct interior location retained by its required final grid.
  - Return the lowest qualified original objective for each complete path, retaining every internal solve.

  The combined pilot passes only when all 144 outer path results qualify, required directional transfers
  independently pass, the three complete-path costs agree, and results are no worse than the lowest
  qualified identical-problem v4/v5/v6 references.

  A competitive basin supported only by boundary-dependent joint states blocks the pilot. Successful basin
  searches must not conceal failed required transfers.

  A pass authorizes proposing subsequent qualification work; it does not qualify production timing. Stop
  this plan after the combined decision.

  ## 5. Interfaces, validation and deliverables

  Create separately versioned v8 recovery, solver, conditioning, scalar-search, profile and reporting
  components. Expose scripts/basketball_shared_workflow_v8.py with stages:

  prepare, recover, diagnose, condition, basins, pilot, package.

  Use configs/basketball-rev2/timing-shared-v8.json for all frozen policies, tolerances, schedules and
  deadlines. Each stage requires hashed predecessors and fresh outputs. The basin stage may follow a
  completed conditioning screening failure, but never an unresolved recovery or arithmetic failure.

  Maintain separate caches and ledgers for recovery, each development experiment and the combined pilot.
  Bind physical offsets, conditioned variables, observations, calibration, group, gauge, role, window,
  spacing, penalty, transform bytes and implementation hashes. Record scheduled, executed, missing and
  qualified counts separately for historical replays, local attempts, conditional fits, joint releases and
  complete outer searches.

  Required regressions cover:

  - Reconstruction against actual multipliers; raw versus transformed constraints; stale-state handling;
    divergent replay rejection.

  - Transform invertibility, deterministic repeated/null subspaces, physical round trips, exact derivative
    chain rules and rejection of misleading transformed convergence.

  - Support activation, seed isolation, conditional versus joint stationarity, refinement completeness,
    flat/boundary basins and failed inner fits.

  - Both local caps, derivative-first accounting, nested deadlines and entire-process-group termination.
  - Packaging every failed or interrupted stage, including cases with no worker artifact; unknown executed
    counts must remain unknown.

  - All inherited Basketball, budget and SelfCap tests. Preserve the scoped historical test-clock harness
    and immutable tests.

  Publish recovery evidence, both development decisions, the combined decision, complete ledgers,
  comparative costs/KKT/runtime and independent verification. Distinguish numerical/provenance failure,
  completed scientific rejection, computational blocker and budget exhaustion. Unexecuted stages remain
  unassessed.

  Keep accepted timing, production candidate and final-validation protocol null. Preserve selection/final
  consumption markers. Create local commits for validated milestones, continue through authorized gates, and
  do not push.