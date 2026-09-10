  # Plan 028 — Diagnose and repair the Basketball crossing artifacts

  ## Implementation revision (2026-09-10)

  The implementation uses new Plan 028 adapters under `scripts/` and preserves
  the Plan 027 adapter and checkpoint source bindings. The frozen initializer
  metadata resolves the automatic duration target to `0.2`; the repaired policy
  projects trainable log durations at the representable `0.02` rendering floor,
  clears only affected Adam moments, and retains step counters. Training and
  evaluation interfaces expose explicit `holdout`/`all-times` and
  `original`/`repaired` policies, with branch provenance and parent restoration
  checks. Production execution remains gated on diagnosis, qualification, and
  the storage/resource checks specified below.

  ## Summary

  Determine why sharp dense reconstructions fragment around frames 20–24, then test a
  repair while preserving player detail.

  Run the agreed full 2×2 comparison for both dense recipes and seeds 0–2:

   Arm    Training frames                        Lifetime handling
  ━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━
   A      Original temporal holdout              Original implementation
  ─────  ─────────────────────────────────────  ─────────────────────────
   B      Original temporal holdout              Repaired implementation
  ─────  ─────────────────────────────────────  ─────────────────────────
   C      All 50 frames from training cameras    Original implementation
  ─────  ─────────────────────────────────────  ─────────────────────────
   D      All 50 frames from training cameras    Repaired implementation

  Each arm starts from its matching 50k checkpoint and continues to 70k total updates.
  This produces 24 endpoints and requires 480,000 additional production updates.

  The principal repair candidate is a verified configuration defect: the automatic-
  duration sentinel -1 reaches the duration regularizer as its numerical target.
  Approximately 62% of raw lifetimes in both seed-0 checkpoints are below the renderer’s
  minimum, where image gradients cannot lengthen them. Its contribution to the visible
  artifacts remains to be established.

  ## Agent responsibilities and execution

  The implementation main agent uses gpt-5.6-luna with reasoning_effort="medium" to
  reduce costs. It delegates script creation, result analysis, and tasks requiring more
  reasoning to gpt-6-astra with reasoning_effort="medium".

  The main agent must:

  - Spawn Astra subagents with model="gpt-6-astra", reasoning_effort="medium", and
    fork_turns="none". Provide each with a bounded task, the saved plan, applicable
    repository instructions, relevant artifacts, constraints, and expected deliverables.

  - Delegate creation and substantive modification of diagnostic, repair, training,
    evaluation, and reporting scripts to Astra. Delegate mechanism analysis, numerical
    correctness questions, and interpretation of experimental results to Astra.

  - Use one Astra subagent at a time. Subagents return implementation changes, focused
    validation evidence, analysis artifacts, and unresolved concerns. They do not
    delegate further.

  - Inspect subagent outputs, integrate validated changes, and run required checks.
  - Launch and supervise long-running jobs directly, including diagnosis, qualification,
    training, and evaluation. Maintain job identities, progress, resource accounting,
    recovery state, and cleanup.

  - Maintain persistent status and artifact links so work can continue after context
    loss.

  - Stage and create local commits for completed, validated implementation milestones.
    Include only explicit task-related paths, inspect the staged diff, and supply a
    commit title and description.

  - Use separate escalated git add and git commit calls from the outset, with task-
    specific justifications and approval prefixes ["git", "add"] and ["git", "commit"],
    following repository standing approval. Do not push, amend, or rewrite history.

  - Continue with the next unfinished task after each commit. Follow repository
    interruption, staging/commit failure, and permission-failure rules.

  Apply this orchestration to the fixed study described here. Subagents prepare scripts
  and analyse results; the main agent owns execution, resource limits, validation
  handoffs, and commits.

  ## Diagnosis, repair, and experiment implementation

  Verify the six parent checkpoints, initializer metadata, source hashes, camera
  exclusions, and time conversion. Record lifetime distributions across seeds and
  existing checkpoints, including visible image contributions from lifetimes below the
  rendering floor.

  Trace actual Gaussian contributions in the existing fixed player crops at frames 19–25,
  across all four held-out cameras and six parents. Record projected position, depth,
  scale, velocity, temporal center, lifetime, opacity, and contribution after occlusion.
  Validate attribution against native RGB/alpha rendering.

  Compare contributors before, during, and after the burst. Distinguish missing temporal
  coverage from misplaced moving Gaussians and overlapping visibility. Initialization
  labels cannot establish current player identity after relocation.

  Implement one fixed repair package:

  - Resolve the automatic duration target from frozen initializer metadata: 0.2
    normalized time. Require a finite, positive resolved target.

  - Keep trainable log-durations at or above the log of the existing 0.02 rendering
    minimum, using a numerically safe boundary.

  - Apply this projection when forking the checkpoint and after every complete training
    step. Clear duration Adam moments only for projected entries; retain their optimizer
    step counters.

  - Preserve native rendering equations, regularization weights, other losses, learning
    rates, relocation policy, and point counts.

  - Verify that the initial projection preserves rendered images within measured
    numerical tolerance while restoring a usable duration gradient. Do not widen all
    lifetimes to 0.2.

  Save diagnostic evidence before production training. Freeze the repair package before
  examining new endpoint scores; this study contains no adaptive hyperparameter search.

  Use new study adapters to preserve historical checkpoints, source files bound by their
  hashes, reports, and the user’s Plan 027 edits.

  - Add explicit training-policy and lifetime-policy options to the new training/
    evaluation interfaces. Provenance must identify the parent hash, recipe, seed,
    training-key hash, repair version, resolved duration settings, and adapter source
    hashes.

  - Restore complete parent model, optimizer, scheduler, relocation, and RNG state before
    applying declared fork changes. Initialize a fresh dedicated sampler with the
    trajectory’s seed in every arm, pairing sampling within each training policy.

  - Subsequent resumes must restore the new branch exactly and reject mismatched policies
    or provenance. Preserve the absolute 70k schedule; relocation ends at update 63k.

  - Holdout arms retain 1,350 training images. All-times arms use 1,500 images, adding
    frames 20–24 only from the existing 30 training cameras. Cameras 0/10/20/30 remain
    excluded.

  - Reuse the same initializers for all four arms. Additional training images must not
    introduce new geometry, masks, correspondences, or initialization changes.

  - Qualify each of the eight recipe/arm combinations using at most 12 disposable
    optimizer updates, including save/reload and gradient checks. Charge qualification
    separately.

  - Run production serially in seed order, coarse then cropped, arms A–D. Complete every
    technically valid trajectory regardless of intermediate visual quality.

  Commit validated milestones covering implementation and checks, diagnosis and
  qualification, and completed experiment results and reporting.

  ## Validation and success criteria

  Evaluate all 24 endpoints using frozen metric definitions and the 350 original targets:
  8,400 metric rows, with the existing 13 fresh-process PNG/raw-float repeat probes per
  endpoint.

  For all-times arms, label the 150 formerly held-out training-camera targets as training
  observations. The common quality comparison uses the 200 targets from held-out cameras.

  Report paired effects of additional training, added temporal supervision, the lifetime
  repair, and their interaction. Show each recipe, seed, and camera, including:

  - Gap frames 20–24; nearby frames 17–19 and 25–27; all remaining frames.
  - Motion-pixel MAE, motion-crop LPIPS, temporal difference error, and existing full-
    image metrics.

  - Lifetime distributions, visible contributor statistics, losses, point counts, memory,
    runtime, and storage.

  Produce 24 comparison videos—one per recipe/camera/seed—with ground truth, the 50k
  parent, and arms A–D in a consistent layout. Use all 50 source frames at 25 fps,
  accompanied by the existing fixed player crops and frame sequences.

  Call a condition fixed only when the fragment burst is no longer visible in playback
  and frame inspection, while sharp player detail elsewhere is preserved. Gap metrics
  must corroborate improvement against the matched native continuation. Report
  regressions and seed/camera disagreements explicitly; aggregate scores alone cannot
  establish success.

  Required checks cover:

  - Camera/time exclusions, policy labels, and normalized-time units.
  - Duration target resolution, boundary gradients, projection, and selective optimizer-
    state changes.

  - Exact restoration outside declared fork changes and correct absolute update counts.
  - Attribution/render agreement, complete evaluation coverage, historical hash
    preservation, and serial job accounting.

  A successful all-times result establishes a reconstruction remedy with added
  supervision. A successful holdout result establishes a repair through the excluded
  interval. This remains a study of one previously inspected event, not independent
  evidence of generalization.

  ## Resources, artifacts, and completion

  Estimated additional storage is 170–180 GB:

   Component                                             Allowance
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━
   24 complete 70k checkpoints                            142.3 GB
  ──────────────────────────────────────────────────  ─────────────
   Atomic saves and recovery replacement                     12 GB
  ──────────────────────────────────────────────────  ─────────────
   Renders, float probes, videos, diagnostics, logs    Up to 25 GB

  Approximately 209 GB was available during planning. Recheck before execution, preserve
  a 20 GiB free-space reserve, and enforce a 180 GB study-artifact ceiling. Retain final
  checkpoints and validated recovery state; delete only superseded temporary checkpoints
  created by this study.

  Estimated execution is 30–45 GPU-hours, with one GPU job at a time. This estimate
  covers the computational study; agent usage is tracked separately. Execution remains
  bounded by the fixed trajectories and updates, without additional seeds or training
  variants. Record qualification, diagnosis, production, evaluations, failures, and
  resumed work separately.

  When implementation begins, update the existing plans/plan_028.md with this revised
  specification. Store large artifacts under .local/basketball-crossing-repair/ and
  compact evidence, status, and the report under docs/experiments/basketball-crossing-
  repair/.

  Completion requires the implemented repair, validated experiment, comparisons, local
  milestone commits, and an explicit assessment of whether each training condition is
  fixed. If artifacts persist or sharpness regresses, report the failed repair and
  remaining mechanism evidence; experiment completion alone does not establish
  resolution.
