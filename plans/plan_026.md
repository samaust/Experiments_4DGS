  # Plan 026 — Basketball initialization and training-length comparison

  ## 1. Summary and experiment design

  Determine whether FreeTimeGsVanilla’s Basketball weakness comes from insufficient
  training, inadequate initialization, or a persistent disadvantage under the tested
  workflows.

  Use three arms and seeds 0, 1, and 2:

   Arm                          Initialization      Starting point      Required results
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━
   STG Full                     Existing sparse     Resume each Plan    5,000 and 50,000
                                static              024 checkpoint      total updates
                                initialization      at 5,000
  ───────────────────────────  ──────────────────  ──────────────────  ──────────────────
   FreeTimeGS sparse            Existing 45,828     Resume each Plan    5,000 and 50,000
                                static temporal     024 checkpoint      total updates
                                copies              at 5,000
  ───────────────────────────  ──────────────────  ──────────────────  ──────────────────
   FreeTimeGS dense temporal    New validated       Train from          5,000 and 50,000
                                dense               initialization      total updates
                                initialization

  Also retain results at 10,000, 20,000, and 30,000 updates to reveal learning
  trajectories.

  Preserve the accepted calibration, scale, original camera IDs, zero-offset operational
  assumption, 960×540 resolution, source frames 0–49, held-out cameras 0/10/20/30, and
  temporal exclusion [0.8,1.0) seconds. All arms use the existing 1,350 training images
  and 350 evaluation images.

  The user has removed time and GPU-hour limits for this study, including the previous
  method ceilings and overall 24-hour training cap. Continue recording consumption
  without resetting historical records. Run one GPU job at a time. This is a fixed
  experiment, not a continuous-improvement loop.

  When implementation begins, save the plan as plans/plan_026.md, or the next unused
  number if necessary.

  ## 2. Dense temporal initialization

  ### Inputs and reusable components

  Reuse the pinned RoMa/EDGS geometry helpers, existing ViPE person/ball segmentation and
  tracking components, and FreeTimeGS initialization equations. Adapt their SelfCap-
  specific camera counts and frame assumptions through new Basketball adapters; preserve
  code and artifacts referenced by Plan 024’s hashes.

  Use only training-camera images outside frames 20–24 for geometry, segmentation,
  tracking, colors, and initialization selection. Reset temporal trackers across the
  excluded interval.

  Build clouds at keyframes 0, 5, 10, 15, 25, 30, 35, 40, 45, with their immediate
  successors for motion estimation. Begin with a pilot using 0/1, 25/26, and 45/46.

  ### Geometry construction

  - Choose three candidate neighboring training cameras per reference by shared static-
    track overlap, with camera ID as the tie-breaker. Record missing overlap and rejected
    pairs explicitly.

  - Use the existing pinned RoMa indoor matcher and calibrated triangulation. Keep the
    dance1 default of 15,000 sampled candidates per reference/time, distributed across
    neighboring pairs; reserve half for person regions when present and balance that
    portion across detected instances.

  - Validate finite coordinates, positive depth, at least 1° triangulation angle, and
    reprojection error no greater than two pixels at 960×540. Require foreground points
    to have consistent support from at least three cameras.

  - Fuse and deduplicate reliable static observations across the pilot times, excluding
    person/ball masks and changing image regions. Initialize static geometry with zero
    velocity.

  - Keep player geometry local to its observed time. Mask labels constrain candidate
    associations but do not establish cross-camera identity.

  - Retain ball candidates and rejection reasons separately. Reliable ball reconstruction
    is not a prerequisite for training.

  The initial implementation will use measured dense geometry without adding synthetic
  court-plane samples. Report remaining floor holes; plane completion would introduce an
  additional modeling assumption and is outside this comparison.

  ### Motion and assembly

  Estimate foreground motion from adjacent-frame image tracks in supporting cameras, then
  triangulate the tracked endpoints. Use bidirectional pyramidal LK tracking with a 31-
  pixel window, four pyramid levels, and a one-pixel forward/backward consistency
  threshold. Require agreement with the tracked person instance and geometric checks at
  both times.

  Use native 3D nearest-neighbor displacement as a diagnostic comparison, not sufficient
  evidence of temporal identity. Unsupported velocities remain explicitly flagged; encode
  zero as an initialization value without labeling it measured motion.

  Reuse the sparse FreeTimeGS arm’s coordinate normalization, scene scale, keyframe
  centers, and normalized duration of 0.2. Convert velocities through the shared time
  normalization and spatial transform. Freeze one initialization artifact for all three
  dense seeds.

  The initialization interface extends the existing NPZ arrays—positions, colors,
  velocities, times, durations—with sidecar provenance, region labels, supporting
  observations, and velocity-validity information. Do not replace missing geometry by
  duplicating sparse points to reach a target count.

  ### Pilot acceptance

  Before full dense training, retain point projections, foreground-only initial renders,
  motion overlays, and comparisons with sparse initialization.

  At each pilot time, require:

  - Recognizable, separated player components supported by at least three cameras.
  - Consistent adjacent-frame associations for at least two visible players.
  - Improved projected player coverage relative to sparse initialization.
  - No evident gross player-to-background associations, identity switches, or foreground
    floaters in the inspected supporting views.

  Inspect fixed training cameras 1/11/21/31 and record occlusion or visibility
  limitations. Report static support, player coverage, rejected matches, uncertain
  velocities, and ball support independently.

  If coarse matching fails this assessment, use person-cropped RoMa matching with exact
  crop-to-image coordinate mapping, retaining the same geometry checks. If credible
  player support still cannot be established, stop the dense arm and report the
  prerequisite as unmet; do not present background-only initialization as suitable dense
  temporal initialization.

  ## 3. Training, checkpointing, and evaluation

  ### Training behavior

  Add a study runner with explicit arm, seed, initialization, resume checkpoint, and
  absolute target update arguments. Continuing a 5,000-update checkpoint requires 45,000
  further updates.

  - STG Full: preserve the native optimizer settings, densification timing, and 30,000-
    step position-learning-rate decay. Extend both the training loop and optimizer-step
    guard to 50,000; retain the final position learning rate thereafter. Label this as a
    native-schedule extension.

  - Both FreeTimeGS arms: retain the native 70,000-step schedule and existing losses,
    regularization, relocation, sampling, and optimizer settings. Stop at 50,000 total
    updates.

  - Keep initialization as the only intended difference between the two FreeTimeGS arms,
    including its point count, geometry, and initial motion.

  - Restore optimizer, scheduler, random-generator, sampler, and method-specific state.
    Record parent-checkpoint hashes and new adapter provenance without weakening the old
    checkpoint checks.

  - Freeze the dense recipe before evaluating trained dense models. Do not tune from
    held-out scores.

  ### Retention and supervision

  Keep full resumable checkpoints at 5,000 and 50,000, plus the latest recovery
  checkpoint. Save recovery state every 1,000 updates or five minutes, whichever comes
  first. Intermediate curve points retain complete renderable model snapshots, explicitly
  distinguished from resumable training checkpoints.

  Use a new study ledger linked to immutable historical accounting. Record
  initialization, training, evaluation, failures, and resumed segments separately. No
  total-job deadline applies; retain process-group cleanup, graceful interruption,
  nonfinite-value checks, and disk/GPU failure reporting.

  Check projected storage needs before production initialization and training. The
  workspace currently has approximately 91 GB free. Remove only superseded recovery files
  created by this study after their replacement is validated; preserve endpoint
  checkpoints, intermediate model snapshots, and historical results. Pause for storage
  resolution rather than deleting unrelated data or silently reducing the experiment.

  ### Evaluation and artifacts

  Evaluate all five curve checkpoints on the same 350 targets using Plan 024’s pinned
  metric definitions and frozen motion masks. Reuse historical 5,000-update baseline
  results only after verifying checkpoint, target, protocol, and render hashes.

  Report:

  - Full-image and motion-crop PSNR, SSIM, and LPIPS.
  - Motion-pixel PSNR/MAE and adjacent-frame difference error.
  - Training loss, point count, memory, checkpoint size, rendering speed, and charged
    compute.

  - Curves against both optimizer updates and training time, with initialization cost
    shown separately.

  Use the same three-seed/five-frame-block bootstrap procedure for matched comparisons.
  Preserve the limitation that temporal interpolation contains only one temporal block.

  At 5,000 and 50,000, produce all retained PNGs, fixed court/display/player comparisons,
  and 25-fps side-by-side videos showing ground truth and all three arms for each held-
  out camera and seed. Do not synthesize intermediate video frames.

  Store large artifacts under .local/basketball-dense-temporal/ and the report, curves,
  artifact index, and compact evidence under docs/experiments/basketball-dense-temporal/.

  ## 4. Validation and interpretation

  ### Required checks

  - Camera resizing, undistortion, crop-coordinate mapping, projection, and time/velocity
    units.

  - Rejection of held-out cameras and frames during every initialization stage, including
    neighboring-frame access.

  - Synthetic moving-point cases covering incorrect correspondences, occlusion, identity
    switches, missing velocity support, and disconnected camera support.

  - Initialization shapes, finite values, color bounds, source hashes, and shared
    normalization across FreeTimeGS arms.

  - Resume tests preserving sample sequences and optimizer state.
  - A specific STG test proving that parameters receive optimizer updates after 30,000.
  - Fresh offline reload/render checks for every snapshot; repeat the existing 13 camera/
    time probes and retain raw-float and PNG comparisons.

  - Complete evaluation coverage, finite metrics, correct arm/seed/checkpoint pairing,
    and preserved historical evidence.

  ### Scientific conclusions

  Report four separate effects:

  1. Training duration: sparse FreeTimeGS at 50,000 versus 5,000.
  2. Initialization: dense versus sparse FreeTimeGS at matched updates.
  3. Interaction: whether dense initialization changes the improvement between 5,000 and
     50,000.

  4. Workflow comparison: STG Full versus dense FreeTimeGS across the learning curves.

  Require player-region evidence before describing an improvement as better dynamic
  reconstruction. Better court scores alone do not establish better players. Equal update
  counts do not imply equal compute, and this comparison cannot isolate individual
  contributions from point count, geometry, and initial velocity within the dense
  initialization.

  Completion requires all nine trajectories to reach 50,000, the required evaluations and
  visual artifacts, and a report that separates measured improvements from unresolved
  limitations. A failed initialization prerequisite or interrupted run remains
  incomplete, with retained evidence. Commit validated milestones locally and continue
  through the study without launching additional arms or modifying synchronization.
