# Current continuation

Continue with [plan_005_rev1.md](plan_005_rev1.md), including its latest authorized
20% camera selection: 24 cameras, 21 training and held-outs 0, 10, 30; 1,200
expected images (1,050 training and 150 held-out). The camera counts and 25%
continuation below are historical and superseded by that revision.

# Authorized camera-set revision

The user removed physical camera 5 after the 25% intrinsic-stability continuation.
The active variant is `basketball-no-camera5/v1`: **33 cameras, 29 training and
four held-out (0, 10, 20, 30)**, with original camera IDs preserved. Preparation
must contain **1,650 images: 1,450 training and 200 held-out**. All rig acceptance
gates apply to all 33 retained cameras. Raw input inventory remains 34 videos;
retain camera 5's source and historical evidence, but exclude its observations
from subsequent estimation, geometry, initialization, training and evaluation.
Keep the 25% intrinsic limit, original budgets and existing training ledger.
These counts supersede the original 34-camera/30-training/1,700-image counts below.

  # ViPE-assisted Basketball calibration and experiment continuation

  ## Summary and constraints

  Recover an estimated calibration for all 34 VRU Basketball DG cameras, validate synchronization, prepare
  the shared scene, then execute the runnable Basketball contenders.

  - Use /home/auss/git_repos/samaust/Tridi/vipe, branch tridi, pinned to
    de50e6ab1066e32c96d32499a282ecaa2fbf2d90. Keep that checkout unchanged.

  - Combine ViPE priors with cross-camera geometric reconstruction. ViPE’s multi-view interface requires an
    initial rig; independent per-video trajectories cannot be treated as a shared coordinate system.

  - Exclude frames 0–49 from calibration estimation. Use frames 50–149 for fitting, 150–199 for model
    selection, and 200–249 for final validation.

  - Allow eight GPU-hours total for calibration, synchronization and initialization, tracked separately from
    training. Include failed GPU attempts; run GPU jobs sequentially.

  - Use automatic methods only. Failed or ambiguous validation produces a specific blocker; do not request
    manual annotations or silently substitute another dataset’s cameras.

  - Preserve the original two-hour Basketball allocation per method and the existing global training ledger.

  ViPE supplies intrinsics, depth and optional masks; geometric verification remains necessary. ViPE
  documentation

  ## 1. Audit inputs and generate ViPE priors

  1. Verify the pinned fork, clean working tree, Python 3.14/CUDA runtime, compiled extensions and model-
     weight availability. Prefer its existing .venv without modifying it; if incompatible, prepare an
     isolated environment inside this repository.

  2. Inventory and hash all 34 videos. Verify dimensions, decoded frame counts, frame rates, timestamps and
     camera numbering—not just camera 0. Reject missing frames, unresolved variable timing or insufficient
     calibration coverage.

  3. Create a separate calibration workspace under .local/; record frame-role assignments before running
     estimation. Preserve original frame IDs through ViPE’s reindexed stream API.

  4. Through a thin adapter, reuse the fork’s GeoCalib, UniDepth and TrackAnything components:
      - Estimate per-camera intrinsic priors from multiple fitting frames.
      - Generate depth priors at representative fitting frames.
      - Mask people, balls and other moving regions for static-scene reconstruction. Supplement semantic
        masks with temporal-motion rejection.

      - Treat depth as uncertain estimated scale, not measured metric ground truth.

  5. Do not run independent monocular SLAM and concatenate its poses. Do not use static_vda unmodified: it
     disables instance masking.

  6. Run a pilot on training cameras 4, 12, 21 and 29 before processing all cameras. Stop if runtime,
     masking or intrinsic estimation is unusable.

  Record source, extension, configuration and weight hashes, download origins, licenses, timings and memory
  measurements. Update docs/research.md, including dependency-specific restrictions; do not describe all
  downloaded weights as Apache-licensed.

  ## 2. Recover and validate the shared rig

  ### Static geometry

  - Use the existing pinned PyCOLMAP environment with masked SIFT matching across camera pairs. Camera
    adjacency must come from verified overlap, not numeric IDs.

  - Build the initial reconstruction from the 30 training cameras only, using ViPE intrinsic priors. Use
    additional fitting timestamps to recover static features hidden by players.

  - Refine one fixed pose and one intrinsic calibration per physical camera with robust bundle adjustment.
    Do not average unrelated per-video coordinate systems.

  - Localize held-out cameras 0, 10, 20 and 30 against the frozen training-camera map using their fitting-
    window images. Their observations must not refine training-camera geometry.

  - Start with PINHOLE. Allow one predefined alternative with radial distortion, retaining fixed zero
    tangential distortion; select it only if selection-window residuals improve by at least 20% and final
    validation passes.

  - Use a single global scale estimated robustly from training-view ViPE depth. Record scale uncertainty; do
    not impose an assumed regulation court size.

  - If SIFT cannot form a reliable connected rig, allow one bounded dense-matching pass using the already
    pinned RoMa implementation, restricted to static regions. No unbounded matcher or model search.

  Explicitly convert pixel-center conventions, pose direction and resizing transforms. COLMAP and OpenCV
  calibration conventions differ. COLMAP calibration guidance

  ### Synchronization

  - Estimate constant camera offsets relative to training camera 1 using dynamic-region correspondences and
    temporal tracks from calibration frames.

  - Search integer offsets within ±25 frames, then refine using interpolated tracks. Use robust epipolar/
    triangulation consistency across overlapping cameras, with cycle-consistency checks.

  - Reserve the final validation window for timing verification. Do not infer synchronization from matching
    frame rates or static backgrounds.

  - Reject ambiguous offsets, boundary-hitting solutions, inconsistent cycles or evidence of clock drift.
    Never silently assign zero offsets.

  ### Acceptance gates

  Publish accepted calibration only when:

  - All 34 cameras are registered in one connected coordinate system with valid rotations and positive focal
    lengths.

  - Each camera has at least 100 independent static validation correspondences, support from at least two
    other cameras, and adequate image-area coverage.

  - Validation reprojection error, expressed at 960×540, has median ≤1 pixel and 95th percentile ≤3 pixels
    per camera.

  - At least 95% of retained triangulated observations have positive depth; planar degeneracy or unstable
    alternate reconstructions are rejected.

  - Independent temporal-window pose checks show ≤0.5° rotation disagreement and ≤1% of rig diameter in
    camera-center disagreement.

  - Timing estimates agree within 0.25 frame across validation subsets and graph cycles, with a
    distinguishable optimum.

  These are engineering gates, not claims of author-calibration accuracy. Failure retains diagnostics and
  blocks downstream training; thresholds are not relaxed after viewing evaluation results.

  ## 3. Export calibration and integrate Basketball safely

  Produce a versioned calibration artifact containing:

  - Raw image dimensions, intrinsics, distortion, world-to-camera transforms and camera centers.
  - Camera-to-video mapping, synchronization offsets and uncertainty.
  - Coordinate/scale conventions, fit/selection/validation membership, source hashes and validation results.
  - Estimated-calibration labeling and accepted/blocked status.
  - COLMAP-compatible export plus reprojection, rig-layout and timing diagnostics.

  Add a Basketball processed-manifest schema using the existing camera/time field conventions. Do not label
  Basketball as selfcap-processed/v1.

  Prepare frames 0–49 at 960×540:

  - 30 training cameras, four held-out cameras.
  - Exactly 1,700 images, including 200 held-out images.
  - Explicit undistortion/resizing transforms and shared corrected-time normalization.
  - One shared 20-pose sweep at frame 25, from held-out camera 0 to its nearest training camera.
  - Ground-truth-selected fixed detail crops, frozen before model inspection.

  Add versioned Basketball-specific scene, initialization, training and evaluation adapters. Reuse unchanged
  native method components, but preserve existing hash-bound SelfCap adapters so their checkpoints remain
  reloadable. No checkpoint migration or SelfCap checkpoint reuse.

  Calibration maps and ViPE depth must not become Gaussian initialization automatically. Generate
  initialization anew from training cameras:

  - STG Lite, STG Full and ATGS: fixed-calibration midpoint geometry at frame 25.
  - FreeTimeGS reproduction: the existing dense EDGS/RoMa approach for keyframes 0, 5, …, 45 and successors
    1, 6, …, 46, with explicit time and scale conversion.

  ## 4. Resume experiments and deliver evidence

  After calibration, synchronization and initialization pass:

  1. Run STG Lite, STG Full, FreeTimeGS reproduction and ATGS sequentially, starting fresh on Basketball.
  2. Charge every attempt to its existing Basketball ledger allocation. Preserve native schedules,
     checkpoint reserves and complete resume state; do not redistribute unused budgets.

  3. Evaluate the last complete checkpoint at native completion or budget stop.
  4. Render all 200 held-out frames plus 20 sweep views in two fresh network-disabled processes.
  5. Produce per-camera and aggregate PSNR, SSIM and LPIPS-Alex, baseline deltas, PNGs, MP4s, fixed crops,
     contact sheets, checkpoint sizes, training resources and synchronized throughput.

  6. Benchmark camera 0/frame 25 with ten warmups and 100 timed renders. Keep blur, ghosting, floaters and
     temporal limitations distinct from numeric metrics.

  7. Update reports 006–010 and the comparison summary. MoE-GS and FreeTimeGS++ retain their independent
     implementation blockers; calibration alone does not authorize substitute implementations.

  Mark all Basketball results as using estimated calibration, not official benchmark cameras. Create
  validated local milestone commits without pushing, and continue until the executable work finishes or a
  defined gate blocks it.

  ## Test plan

  - Synthetic recovery tests for pose inversion, pixel centers, distortion, resizing, global scale and known
    fractional timing offsets.

  - Failure tests for disconnected rigs, planar ambiguity, moving-background contamination, camera-ID swaps,
    missing frames, ambiguous synchronization and changed provenance.

  - Leakage tests proving fitting cannot access frames 0–49 and Gaussian initialization cannot access held-
    out images or calibration clouds.

  - Manifest tests for all 34 cameras, 50 frames, 200 held-out images, corrected timestamps and identical
    sweep paths across methods.

  - Regression checks preserving existing SelfCap behavior and checkpoint provenance.
  - Short budget-charged Basketball training/resume checks before long runs, followed by complete offline
    reload comparisons and shared-evaluator validation.

  - Documentation links, command syntax, budget accounting and git diff --check.

  Success means validated estimated calibration and reproducible Basketball results—or precise, evidenced
  blockers without exceeding the agreed budgets.
