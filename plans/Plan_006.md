  # Plan 006: Research and compare calibration alternatives for VRU Basketball DG

  ## 1. Objective and agreed constraints

  Find an existing implementation that recovers calibration for all 34 cameras with lower rotational and
  camera-center disagreement. Prioritize geometric accuracy, camera coverage and reproducibility; measure
  runtime and memory as secondary criteria.

  The current 23-camera search reached 5.8807° maximum rotation disagreement and 7.1892% center
  disagreement, despite solver convergence. This supports investigating different reconstruction methods and
  constraints before increasing timeouts. Current experiment report (docs/experiments/basketball-no-
  camera19.md)

  Apply these decisions:

  - Reconsider every camera, including 5 and 19. Preserve physical camera IDs.
  - Keep 20% as the threshold for trusting GeoCalib priors, rather than excluding cameras from other
    methods.

  - Remove the cumulative GPU-hour limit for this calibration investigation. Record resource usage and
    failures; use a finite experiment matrix.

  - Model intrinsics as constant over time within each physical camera, while allowing differences between
    cameras.

  - Account for different focus distances through matching quality and robustness tests. Fixed zoom does not
    establish accurate intrinsics or identical lenses.

  - Preserve automatic processing, existing validation thresholds and frame separation. This investigation
    ends with a calibration recommendation and validated artifacts; downstream Gaussian-splatting training
    remains a separate continuation.

  ## 2. Research shortlist: prioritize released implementations

  Investigate these seven routes, then test every route that passes installation and input/output checks.

   Candidate                        Publication and existing code        Reason to investigate
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   COLMAP global mapper / GLOMAP    GLOMAP, ECCV 2024; now               Changes incremental reconstruction
                                    incorporated into COLMAP.            to joint global estimation. Run
                                                                         view_graph_calibrator on a
                                                                         database copy before global
                                                                         mapping when reliable focal priors
                                                                         are unavailable. Official workflow
  ───────────────────────────────  ───────────────────────────────────  ────────────────────────────────────
   MASt3R-SfM                       Paper, 3DV 2025; official code.      Learned matching and global
                                                                         alignment for sparse, difficult
                                                                         image collections. Use the actual
                                                                         MASt3R-SfM pipeline; the
                                                                         repository distinguishes it from
                                                                         its experimental COLMAP/GLOMAP
                                                                         examples.
  ───────────────────────────────  ───────────────────────────────────  ────────────────────────────────────
   VGGSfM                           CVPR 2024; official code.            Learned multiview tracking with
                                                                         geometric optimization. Released
                                                                         code supports dynamic-object masks
                                                                         and COLMAP export.
  ───────────────────────────────  ───────────────────────────────────  ────────────────────────────────────
   VGGT-Ω                           CVPR 2026 paper and project;         Direct camera and depth prediction
                                    official code.                       offers substantially different
                                                                         initialization from the current
                                                                         pipeline. Test the released 512-
                                                                         resolution reconstruction
                                                                         checkpoint.
  ───────────────────────────────  ───────────────────────────────────  ────────────────────────────────────
   Depth Anything 3                 arXiv paper; official code.          Predicts intrinsics and
                                                                         extrinsics, with an existing
                                                                         comparison framework. Use
                                                                         refreshed DA3-GIANT-1.1 weights
                                                                         and evaluate the accuracy-oriented
                                                                         ray-pose option.
  ───────────────────────────────  ───────────────────────────────────  ────────────────────────────────────
   Pi3 / Pi3X                       Pi3, ICLR 2026; paper, official      Investigates sensitivity to
                                    code.                                reference-view choice. Test Pi3X,
                                                                         identifying it separately as the
                                                                         repository’s later engineering
                                                                         update.
  ───────────────────────────────  ───────────────────────────────────  ────────────────────────────────────
   MapAnything                      Paper, 3DV 2026; official code.      Supports image-only calibration
                                                                         and optional geometric inputs. Its
                                                                         existing model adapters could
                                                                         reduce comparison infrastructure
                                                                         work.

  Research these additional approaches as conditional follow-ups:

  - Dense-SfM, CVPR 2025: longer, refined multiview tracks could improve precision. Its released
    implementation supports both complete SfM and refinement of an existing reconstruction; verify that
    camera optimization is enabled.

  - MP-SfM, CVPR 2025: depth and normal constraints address weak geometry. Its published comparisons use
    known intrinsics, so assess it as a hybrid using independently estimated intrinsics—not as demonstrated
    end-to-end self-calibration. Paper, code.

  - CasCalib, FG 2024: uses people to estimate calibration and synchronization. Audit its upright-person and
    common-height assumptions against basketball motion before allocating a pilot. Paper, code.

  - Robust Multi-view Camera Calibration from Dense Matches, VISAPP 2026: particularly relevant to rigid
    camera rigs and correspondence-cycle filtering. Use as methodological evidence; an official runnable
    release has not yet been verified. Paper.

  Do not prioritize methods that require calibration targets, unavailable measurements or known camera
  poses. Record those prerequisites explicitly instead of treating all reconstruction software as
  calibration software.

  ## 3. Build an evidence-based comparison

  First check the dataset’s official release, linked projects and published preprocessing code for reusable
  DG calibration. Verify camera names, image geometry and provenance before considering any discovered
  calibration compatible. Dataset release

  For each candidate, record:

  - Paper version, publication venue, official repository, commit, checkpoints and separate code/weight
    licenses.

  - Required inputs and actual outputs: intrinsics, distortion, extrinsics, scale and synchronization.
  - Support for independent camera intrinsics, static-camera video, masks, wide baselines and limited
    overlap.

  - Installation requirements, local memory measurements, export support and reproducible commands.
  - Comparative evidence, including dataset, supplied calibration, refinement settings, metric definition
    and failure handling.

  Use comparison papers deliberately:

  - MASt3R-SfM: sparse-view and variable-view-count comparisons.
  - DA3: camera-pose comparisons across five datasets, separating unknown-pose reconstruction from pose-
    conditioned results. Benchmark paper

  - RealX3D: comparisons under physical degradations, including defocus. Its differing pose and geometry
    rankings justify testing several model families on this footage. Study

  - VISAPP dense-match calibration: ablations of correspondence selection, initialization and camera models.

  Do not equate paper AUC scores at several degrees with the project’s 0.5° limit, or translation-direction
  error with camera-center disagreement. Separate author-reported results from independently reproduced
  results.

  ## 4. Run a finite, comparable experiment campaign

  ### Establish the evaluation protocol

  - Restore the original full-rig split: 30 training cameras; held-outs 0, 10, 20 and 30.
  - Preserve frames 50–149 for fitting, 150–199 for selection, 200–249 for final validation, and 0–49 for
    downstream experiments.

  - Generate missing masks and quality diagnostics for all cameras independently of GeoCalib success.
  - Keep early and late reconstructions independent: no shared fitted poses or fitted intrinsics across
    windows.

  - Use static observations until synchronization is established. Equal video frame numbers do not establish
    synchronized player positions.

  ### Screen the seven candidates

  Use released pretrained weights and documented inference defaults, pinned before testing. Run three
  independent snapshot comparisons: 50 versus 100, 75 versus 125, and 99 versus 149, with one image per
  training camera.

  Add an incremental COLMAP control using the same SuperPoint/LightGlue features as the global-mapper route.
  This separates frontend improvements from the effect of global reconstruction.

  For every run:

  - Save native predictions, registration failures, convergence information, runtime and peak memory.
  - Convert outputs into the existing coordinate and pixel conventions.
  - Report rotation and center disagreement after the existing single similarity alignment.
  - Report metrics on the complete training set and, separately, the historical common-camera subset.
    Partial reconstructions cannot win through omission of difficult cameras.

  Use isolated environments. Test memory-saving modes before reducing image resolution, and record any
  changed inference configuration.

  ### Refine and test the strongest candidates

  Rank complete candidates by their worst snapshot-pair score:

  max(rotation_disagreement / 0.5°, center_disagreement / 1%)

  Advance the best three, breaking ties by lower rotation disagreement, then center disagreement, then
  runtime.

  Reconstruct the existing five-frame early and late windows. Compare four configurations:

  1. Native pipeline output.
  2. Common robust bundle adjustment with predicted intrinsics fixed.
  3. Bundle adjustment refining one focal length per physical camera, with square pixels and centered
     principal point.

  4. Configuration 3 plus one radial-distortion coefficient.

  Use static masks, spatially distributed correspondences and repeated-observation deduplication. Compare
  ordinary static support with the existing sharpness-filtered support; inspect failures by camera and image
  region. Repeated views of the same static point must not inflate independent support counts.

  Repeat finalist configurations with seeds 0, 1 and 2. Extend an optimizer’s iteration allowance only when
  logs show termination before convergence.

  If these candidates still fail, test Dense-SfM refinement and MP-SfM separately on the best complete
  initialization. Treat CasCalib as an additional pilot only if its prerequisite audit passes. Stop after
  these declared follow-ups and report remaining failure modes.

  ## 5. Acceptance, tests and deliverables

  Localize held-out cameras against frozen training geometry. Apply the training-derived similarity
  transform without refitting it to held-outs.

  Retain the existing acceptance requirements across all 34 cameras:

  - Maximum rotation disagreement ≤0.5°.
  - Maximum center disagreement ≤1% of rig diameter.
  - Per-camera validation reprojection median ≤1 pixel, p95 ≤3 pixels, measured at 960×540.
  - At least 100 independent static correspondences, support from two other cameras and coverage in six of
    sixteen grid cells.

  - At least 95% positive depth, valid rotations and positive focal lengths.
  - No unresolved planar ambiguity or unstable alternative solution.

  Select using frames 150–199, freeze one winner, then evaluate frames 200–249 once. Report stability as
  repeatability evidence, not ground-truth calibration accuracy. Synchronization and metric scale require
  their existing separate validation before downstream use.

  Test camera-ID preservation, frame isolation, resize/crop transforms, pose inversion, similarity
  alignment, fixed-map localization and rejection of incomplete models. Verify exported calibration by
  reprojecting observations after reloading it.

  Produce:

  - plans/plan_006.md: this investigation protocol.
  - docs/research/basketball-calibration-alternatives.md: linked evidence matrix, runnable shortlist and
    recommendation.

  - docs/experiments/basketball-calibration-alternatives.md: measured comparisons, per-camera plots,
    failures and reproducibility instructions, with machine-readable results alongside it.

  Preserve historical artifacts and budget accounting. Create local commits for validated milestones. Finish
  with either a validated full-rig calibration and handoff to Plan 005, or a documented ranking and precise
  remaining blocker.
