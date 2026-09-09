  # Plan 027 — Train coarse and cropped dense Basketball initializations

  ## Summary and experiment design

  Extend Plan 026 to test whether training repairs the observed dense-initialization
  fragments and smearing. Visual pilot defects become recorded diagnostics, not training
  acceptance gates.

  Train both recipes selected by the user:

   Arm                         Initialization           Seeds      Training
  ━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━
   FreeTimeGS dense coarse     Full keyframe            0, 1, 2    From initialization
                               extension of coarse                 to 50,000 updates
                               RoMa pilot
  ──────────────────────────  ───────────────────────  ─────────  ───────────────────────
   FreeTimeGS dense cropped    Full keyframe            0, 1, 2    From initialization
                               extension of person-                to 50,000 updates
                               cropped RoMa pilot

  Retain and evaluate 5,000, 10,000, 20,000, 30,000, and 50,000 updates. Reuse the six
  completed STG Full and sparse FreeTimeGS trajectories after verifying their hashes.

  The combined comparison has four arms, twelve trajectories, and sixty curve results.
  Six new dense trajectories require 300,000 training updates. This remains a fixed
  experiment, with one GPU job at a time and no time or GPU-hour ceiling.

  When implementation begins, save this specification as plans/plan_027.md, using the
  next unused number if necessary.

  ## Initialization and revised acceptance policy

  Preserve the experiment controls. Use the accepted calibration, scale, original camera
  IDs, zero-offset assumption, 960×540 images, and frames 0–49. Geometry, masks,
  tracking, colors, and initialization decisions must exclude cameras 0/10/20/30 and
  frames 20–24. Preserve the 1,350-image training split and 350-target evaluation
  protocol.

  Complete both recipes before evaluating trained models.

  - Generate one shared mask set for keyframes 0, 5, 10, 15, 25, 30, 35, 40, and 45 and
    their immediate successors. Preserve pinned ViPE processing and fresh tracker state
    for each pair.

  - Generate full coarse and cropped clouds using the existing pinned geometry
    algorithms. Use identical neighbor selection, sampling seed, candidate allocations,
    geometric thresholds, and motion checks. Person-cropped refinement is the recipe
    difference.

  - Preserve finite-coordinate, positive-depth, ≥1° triangulation-angle, ≤2-pixel
    reprojection, and three-camera foreground-support requirements. Preserve the
    specified LK checks. Unsupported foreground velocities remain explicitly flagged and
    initialized to zero.

  - Retain person and ball observations separately, with their source cameras, local
    instance labels, rejection reasons, and velocity validity. Do not treat semantic
    labels as verified cross-camera identities.

  - Do not introduce additional visual cleanup, matching variants, synthetic court
    geometry, synchronization changes, or point-count targets.

  Implement deterministic static fusion. This assembly step was not completed in Plan
  026:

  - Exclude masked foreground and changing-region observations using the existing checks.
  - Define one spatial voxel width for both recipes: half the median positive nearest-
    neighbor distance of the unique, normalized historical sparse static points. Record
    the resulting width before constructing either initializer; do not tune it from
    renders or scores.

  - Within each recipe, fuse static observations across keyframes by voxel. Use median
    positions and colors, retain the contributing-observation mapping, and set velocity
    to zero.

  - Instantiate the fused measured static geometry at the nine retained temporal centers,
    matching sparse FreeTimeGS’s temporal representation. Keep foreground observations at
    their observed keyframe; do not fuse them across times or duplicate sparse geometry
    to fill holes.

  - Preserve the sparse arm’s coordinate transform, scene scale, normalized centers, and
    duration of 0.2. Record physical static-point counts separately from temporal
    Gaussian copies.

  Freeze one initializer per recipe for all three seeds. Each contains the native arrays
  plus provenance, region labels, observation mappings, and velocity-validity sidecars.

  Separate technical validity from visual quality. Record authorization as “frozen for
  experimental training with known visual defects,” while preserving the failed Plan 026
  assessment. Do not relabel either pilot as visually accepted.

  Fragments, smearing, uncertain identity, incomplete floor coverage, poor ball support,
  or disappointing checkpoint images must not stop training. Technical failures—invalid
  arrays, empty initialization, provenance mismatch, split leakage, nonfinite training,
  insufficient storage, or device failures—still require correction or a documented stop
  under repository rules.

  ## Training and pipeline changes

  Add distinct arm identifiers, freetimegs-dense-coarse and freetimegs-dense-cropped,
  throughout training, checkpoint provenance, evaluation records, reporting, and artifact
  names.

  - Keep the native renderer/metric method identifier freetimegs; store the experimental
    arm separately. Separate output directories must prevent coarse, cropped, and sparse
    results from colliding.

  - Use new study adapters where changing existing code would invalidate historical
    source hashes. Preserve Plan 024/026 checkpoints, reports, ledgers, executed
    adapters, and rejection evidence.

  - Verify recipe identity, initializer hash, seed, native configuration, and
    normalization when starting or resuming a trajectory. Cross-recipe resumes must fail
    explicitly.

  - Preserve the sparse FreeTimeGS arm’s native 70,000-step schedule, losses, sampling,
    relocation, optimizer settings, and initialization equations. Do not introduce point-
    budget pruning or equalize point counts.

  - Train all six trajectories to 5,000 first, in seed order with coarse then cropped.
    Save and evaluate those endpoints. Then resume each corresponding checkpoint to
    50,000, retaining the intermediate curves. Neither visual quality nor relative scores
    at 5,000 may cancel continuation or change a recipe.

  - Save complete resumable endpoints and recovery state every 1,000 updates or five
    minutes, whichever comes first. Validate replacement recoveries before deleting
    superseded study recoveries.

  Before production training, measure actual initializer sizes and perform a short save/
  reload validation on each full initializer. Use that evidence to project GPU memory and
  storage for all retained checkpoints and renders. Charge validation work separately. If
  resources are insufficient, pause for resolution; do not silently downsample or change
  the scientific comparison.

  Use a new ledger linked by hashes to historical accounting. Retain failures and resumed
  segments without resetting consumption. Preserve process cleanup and repository
  permission-failure rules. Commit validated implementation milestones locally without
  pushing.

  ## Evaluation and interpretation

  Reuse the frozen Plan 024 v3 renderer, metric definitions, masks, and bootstrap
  procedure.

  - Evaluate all thirty new dense checkpoints on all 350 targets: 10,500 new metric rows.
    Perform fresh-process reload checks and all thirteen PNG/raw-float repeat probes for
    every new checkpoint.

  - Report full-image and motion-crop PSNR/SSIM/LPIPS, motion-pixel PSNR/MAE, and
    adjacent-frame difference error.

  - Report native-loss curves, point counts, memory, checkpoint sizes, rendering speed,
    training time, and charged compute. Show initialization cost separately.

  - At 5,000 and 50,000, produce fixed court/display/player comparisons and twelve videos
    per endpoint—one per held-out camera and seed—showing ground truth and all four arms.
    Use all fifty source frames at 25 fps, with no synthesized frames.

  - Retain initialization and trained comparisons in cameras 1/11/21/31 at pilot frames
    0/25/45 to inspect the previously observed defects. Label these as training-view
    diagnostics, separate from held-out quality evidence.

  Report the original effects for each dense recipe: initialization versus sparse
  FreeTimeGS, duration improvement, initialization-by-duration interaction, and
  comparison with STG Full. Add a matched coarse-versus-cropped comparison at every
  checkpoint.

  Do not select a winning seed, tune from evaluation results, or infer better players
  from court metrics alone. State whether the inspected fragments and smearing improve,
  persist, or worsen. Preserve the one-block temporal-interpolation limitation and
  acknowledge that initialization changes point count, geometry, and motion together.

  ## Validation, artifacts, and completion

  Required checks include:

  - Split and successor-frame rejection; coordinate, color, shape, finiteness,
    normalization, and velocity-unit validation.

  - Deterministic static fusion, correct contributing-observation mappings, zero static
    velocity, and no foreground fusion across times.

  - A visually flagged but technically valid initializer can start training; corrupted or
    mismatched initializers cannot.

  - Exact restoration of saved optimizer, sampler, RNG, and method state; preserve the
    existing qualification that GPU training is not bitwise reproducible.

  - Resume from 5,000 to exactly 50,000 without resetting schedules or performing an
    extra 50,000 updates.

  - Distinct recipe identities across checkpoints, metric files, bootstrap cohorts, and
    visual panels.

  - Complete sixty-result combined coverage, preserved historical hashes, and no
    overlapping or unclosed GPU jobs.

  Store new large artifacts under .local/basketball-dense-training/ and the report,
  curves, compact evidence, and artifact index under docs/experiments/basketball-dense-
  training/.

  Completion requires both frozen initializers, all six new 50,000-update endpoints, all
  required evaluations and visuals, and the four-arm report. A poor dense result is a
  valid completed experiment. A technical interruption remains incomplete with retained
  evidence; the historical Plan 026 visual rejection remains unchanged.
