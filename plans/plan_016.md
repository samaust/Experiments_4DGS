  # Plan 016: Verify durable persistence and complete the focused benchmark

  ## Summary and budget

  Implement a separately versioned v10 workflow that preserves complete attempt evidence before announcing
  completion, survives worker interruption without losing completed records, and completes the unfinished
  Plan 015 benchmark.

  Preserve v9 unchanged, including its empty baseline artifacts, corrections and verification reports. Its
  50 reported qualifications remain unverified and cannot supply baseline costs, stationarity denominators
  or initialization states.

  Use the selected 90-minute hard elapsed budget, starting before implementation inspection. Planning does
  not start the clock. Include implementation, failed work, preflight solves, experiments, tests,
  verification and commits. Freeze absolute deadlines and an external process-group watchdog.

   Deadline     Required outcome
  ━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Minute 10    Historical admission, source hashes, cases and policies frozen
  ───────────  ──────────────────────────────────────────────────────────────────────
   Minute 20    Persistence implementation and actual-worker preflight pass
  ───────────  ──────────────────────────────────────────────────────────────────────
   Minute 35    Fresh baseline persisted and independently verified
  ───────────  ──────────────────────────────────────────────────────────────────────
   Minute 45    Conditioning arm decided
  ───────────  ──────────────────────────────────────────────────────────────────────
   Minute 52    Initialization arm decided
  ───────────  ──────────────────────────────────────────────────────────────────────
   Minute 60    Stopping arm decided; final policy frozen
  ───────────  ──────────────────────────────────────────────────────────────────────
   Minute 75    Conditional final benchmark finished; scientific computation stopped
  ───────────  ──────────────────────────────────────────────────────────────────────
   Minute 90    Verification, terminal package and local commits finished

  Unused time does not extend later deadlines. Interruption does not restart the clock without explicit user
  authorization.

  Full screens, production fitting, selection, final validation and training remain outside this phase.

  ## 1. Durable attempt lifecycle and execution control

  Expose scripts/basketball_shared_workflow_v10.py with stages prepare, persist, baseline, adapt, benchmark,
  package and verify. Freeze configuration and deadlines in configs/basketball-rev2/timing-shared-v10.json;
  publish evidence under docs/experiments/basketball-shared-timing-v10/.

  ### Admission and identities

  - Verify committed v9 evidence, corrected and archived source hashes, inherited calibration/partition/
    marker hashes and installed solver implementation.

  - Import the existing 18 conditional targets, 20 conditional dependencies, four joint targets and three
    joint dependencies: 81 scheduled attempts per policy. Preserve IDs, path ordering, seed-selection rules
    and diagnostic labels.

  - Bind each attempt to its run, policy, mathematical problem, source implementation, exact transform/
    origin bytes and dependency provenance.

  - Verify historical source substitutions explicitly. New execution hashes must identify the actual
    imported code; an archived hash cannot stand in for current execution.

  ### Persistence transaction

  Use one immutable artifact per attempt. Group summaries contain references and hashes rather than another
  copy of the records.

  For each successful, unsuccessful or missing-seed outcome:

  1. Retain parameters, traces, multipliers, initialization provenance, canonical states, actual numerical-
     entry observations and execution status.

  2. Validate finite, NumPy-aware JSON before publication.
  3. Write and synchronize a temporary artifact, publish without overwriting an existing artifact, and
     synchronize its directory.

  4. Reload the published artifact and independently verify its identity, accounting and available physical
     arithmetic.

  5. Persist a verification receipt binding the artifact hash.
  6. Only then append and synchronize the durable completion event.

  A warm dependency becomes usable only after this transaction succeeds. Numerical rejection is a valid
  persisted outcome; missing seeds receive explicit records without claiming solver execution.

  Add a synchronized, append-only journal per active attempt. Record exact state definitions and numerical-
  entry start/completion events at the actual numerical boundaries. Use sequence numbers and checksums;
  retain only the valid prefix of a truncated journal and report uncertainty beyond it.

  Keep scheduled attempts, solver invocations, persisted outcomes, qualifications and numerical evaluations
  separate. Never replace an uncertain count with zero.

  ### Failure and recovery

  - A persistence, identity, arithmetic or accounting failure stops further dispatch immediately. The
    supervisor, outside the scientific process group, terminates that entire group using a two-second
    SIGTERM grace followed by SIGKILL.

  - Ordinary solver rejection does not cancel the remaining scheduled cohort.
  - The supervisor must preserve failure details and package evidence even when a worker writes no result.
  - Recovery may verify an already-published artifact and reconstruct its missing completion receipt/event.
    It must never rerun that attempt.

  - Incomplete attempts remain interrupted or unknown. Genuine worker interruption ends the scientific
    stage; automatic numerical resume is outside scope.

  - Packaging and verification failures cannot turn a blocked run into a pass or assume fixed execution
    counts.

  ## 2. Persistence qualification before the baseline

  Freeze six preflight local-attempt allocations maximum, separate from scientific comparisons and never
  usable as benchmark seeds.

  Run four fresh cold cases through the actual worker, serializer, reload and independent verifier:

   Existing target        Required coverage
  ━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   conditional-03/cold    Regularized successful control
  ─────────────────────  ───────────────────────────────────────
   conditional-02/cold    Data-only successful control
  ─────────────────────  ───────────────────────────────────────
   conditional-00/cold    Data-only nonqualifying solver return
  ─────────────────────  ───────────────────────────────────────
   conditional-04/cold    Infeasible cold initialization

  Require successful and unsuccessful outcomes to retain their complete applicable evidence. Unexpected
  behavior is reported without choosing replacement cases or tuning the solver.

  Use the remaining two allocations in an interruption test: persist one successful attempt, start another
  fresh attempt, then kill the worker after its numerical-entry journal records entry. Confirm that the
  completed attempt remains independently verifiable and the interrupted attempt retains explicit incomplete
  accounting.

  Add deterministic storage fault tests, without additional optimization, for:

  - Encoding failure, including NumPy and nonfinite metadata.
  - Failure before publication and after publication but before completion.
  - Truncated journals, missing worker artifacts and mismatched hashes.
  - Duplicate IDs, overwrite attempts and corrupted records.
  - Completion events without verifiable artifacts.
  - Failure propagation that prevents subsequent dispatch and terminates descendants.

  Preflight passes only when complete records survive these tests, incomplete work remains explicit, and
  counts reconcile from disk. Any unresolved failure stops scientific execution.

  ## 3. Fresh baseline and unchanged adaptation screens

  Use at most five scientific policies × 81 attempts = 405 scheduled attempts, plus the six preflight
  allocations. Unused allocations cannot become retries, replacement cases or additional adaptations.

  Every policy receives fresh problems, starts, caches and source dependencies. Preserve both 200 iterations
  and 200 distinct evaluated states per local attempt, including initialization and restoration. Preserve
  original-coordinate stationarity at 1e-6, qualification depth above 1e-7, all coefficients/null
  directions, objectives, bounds and support thresholds.

  The fresh baseline need not qualify every fit to enable experiments. It must finish its complete schedule
  with verifiable records for every outcome.

  Preserve the four frozen policy definitions:

   Policy            Conditional conditioning    Feasible-cold repair    xtol
  ━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━
   Baseline                               Off                     Off    1e-6
  ────────────────  ──────────────────────────  ──────────────────────  ──────
   Conditioning                            On                     Off    1e-6
  ────────────────  ──────────────────────────  ──────────────────────  ──────
   Initialization                         Off                      On    1e-6
  ────────────────  ──────────────────────────  ──────────────────────  ──────
   Stopping                               Off                     Off       0

  Joint conditioning remains common to all policies. Retain the symmetric cold-origin transform, existing
  scale limits and exact derivative mappings. Initialization retains the frozen analytical construction with
  target depth 1e-6.

  All arms must preserve the 47 frozen archived qualified controls and their costs within 1e-6 + 1e-4 ×
  max(abs(F1), abs(F2)).

  - Conditioning: retain the six frozen iteration-limit targets. Freeze positive, independently verified
    fresh-baseline KKT denominators before execution. Require recovery of at least three targets,
    representation from all three groups and median new/baseline KKT ratio at most 0.1. Unavailable
    candidate KKT contributes infinity. Missing baseline denominators leave this arm unassessed; the other
    independent arms may continue if their evidence is sound.

  - Initialization: require feasible bounded cold parameters with depths above 2e-8 for all three frozen
    infeasible cases. Report subsequent fit qualification separately. Missing directional seeds remain
    missing unless their prescribed fresh source qualifies.

  - Stopping: require all three frozen xtol targets to qualify within the unchanged caps and stationarity
    threshold.

  Retain all control failures, support changes, observable-growth findings and missing dependencies. No
  post-result retuning or additional solver alternatives are permitted.

  ## 4. Final gate, verification and deliverables

  Only individually passing arms may enter one final policy. Freeze their exact union before running a fresh
  81-attempt benchmark. If no arm passes, the final benchmark remains unassessed.

  ready_for_full_screens requires:

  - Every target and dependency qualifies within both caps, with no missing required seeds.
  - Previously qualified controls retain acceptable costs.
  - All three conditional paths agree at every target.
  - Persisted original objectives, depths, full KKT contributions, dependency provenance and numerical-entry
    accounting pass independent verification.

  - Conditional results publish the omitted camera-offset derivatives and remain distinct from joint
    qualification.

  - Initialization, stopping, transform, support and observable-growth checks are resolved.
  - Required tests and final verification finish within the deadlines.

  The independent verifier must inspect actual numerical-entry records and reload artifacts; agreement
  between exported counters alone is insufficient.

  Run all inherited Basketball, budget and SelfCap tests with the existing scoped historical clock harness.
  Add regressions for the persistence lifecycle, interruption boundaries, exact adjacent states, derivative/
  constraint-first requests, rejection before a 201st state, shared initialization budgets and seed
  isolation.

  Publish admission, preflight evidence, attempt artifacts and journals, receipts, source/dependency
  indexes, baseline denominators, standalone decisions, final decision, runtime comparisons and an
  independent report. Distinguish scientific rejection, computational blocker, provenance/arithmetic
  failure, budget exhaustion and unassessed work.

  A focused pass produces a candidate hash and a proposed full-screen continuation budget using measured
  computation, persistence and verification costs with a factor-of-two margin. Preserve all Plan 015 full-
  screen gates; do not launch those screens in this phase.

  Keep accepted timing, production candidate and final-validation protocol null. Use existing dependencies,
  at most six numerical workers and eight CPU workers total, and single-thread numerical libraries. Perform
  no downloads, GPU jobs, training or reads from prompts. Create validated local commits under repository
  instructions; do not push or rewrite history.
