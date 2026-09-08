  # Plan 024 — Study and evaluate a practical synchronization workflow

  ## 1. Direction and objective

  Evaluate a pivot from qualifying the custom spline solver to determining which synchronization approach
  improves Basketball reconstruction reliably and economically.

  The initial recommendation is VisualSync with the accepted Basketball calibration, supported by a reduced-
  camera Sync-NeRF cross-check and explicit zero-offset controls. This recommendation remains conditional on
  code completeness and measured benefit: VisualSync’s current repository describes unfinished code and
  links a separate original-code archive. Official repository.

  Use the agreed practical reconstruction standard. Report 10 ms accuracy where ground truth supports it;
  retain historical strict-protocol failures as historical results. This campaign does not resume the
  stopped continuous improvement loop.

  ## 2. Literature, citations, benchmarks, and code audit

  Study all six named methods and these relevant additions:

   Work                                                  Role in the study
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   VisualSync                                            Primary synchronization candidate; examine
                                                         correspondence extraction, pair rejection, global
                                                         estimation, failures, and four-dataset
                                                         comparisons.
  ────────────────────────────────────────────────────  ────────────────────────────────────────────────────
   Sync-NeRF and official code                           Independent reconstruction-based timing signal.
                                                         Audit initialization sensitivity and test-view
                                                         offset optimization.
  ────────────────────────────────────────────────────  ────────────────────────────────────────────────────
   SyncTrack4D, CVPR Findings 2026                       Direct synchronization-plus-4DGS alternative. It
                                                         cites Sync-NeRF and Humans as a Calibration
                                                         Pattern and provides synchronization and rendering
                                                         comparisons. Verify implementation availability.
  ────────────────────────────────────────────────────  ────────────────────────────────────────────────────
   Humans as a Calibration Pattern and Spatiotemporal    Compare human-prior approaches, especially
   Multi-Camera Calibration using Freely Moving          multiple-person association. HCP’s repository
   People                                                currently promises a future release.
  ────────────────────────────────────────────────────  ────────────────────────────────────────────────────
   MultiViewUnsynch and its trajectory paper             Classical single-target reference; examine timing,
                                                         rolling shutter, trajectory ground truth, and
                                                         applicability to a ball or player.
  ────────────────────────────────────────────────────  ────────────────────────────────────────────────────
   Dynamic Gaussian Scene Reconstruction from            Study coarse alignment followed by reconstruction-
   Unsynchronized Videos and Sync-4DRF                   based refinement. Distinguish released
                                                         implementations from proposed or incomplete
                                                         releases.
  ────────────────────────────────────────────────────  ────────────────────────────────────────────────────
   FreeTimeGS and MoRel                                  Reconstruction and temporal-consistency
                                                         comparisons. Treat these as representation
                                                         alternatives, rather than camera synchronization
                                                         estimators.
  ────────────────────────────────────────────────────  ────────────────────────────────────────────────────
   IFID / InSynFormer                                    Examine a benchmark explicitly addressing
                                                         fractional-frame synchronization. Verify data
                                                         accessibility; the paper’s linked code URL
                                                         returned 404 during this check.

  Perform one forward-citation and one backward-reference pass for every seed, through September 8, 2026.
  Verify citation relationships in the citing paper, deduplicate publication versions, and prioritize direct
  comparisons, sports scenes, failure analysis, and usable code. Limit detailed reading to 20 relevant
  papers; retain remaining candidates and search limitations in the report.

  Produce an evidence matrix recording:

  - Actual task, camera assumptions, motion priors, offset model, and initialization.
  - Dataset, native frame rate, ground-truth provenance, injected perturbations, splits, and evaluation
    resolution.

  - Mean, median, tails, failures, excluded cameras/pairs, and timing versus reconstruction metrics.
  - Official source, revision, weights, dependencies, license identifiers, runnable entrypoints, and missing
    components.

  Explicitly reconcile discrepancies between papers. For example, VisualSync’s reported Sync-NeRF synthetic
  result differs substantially from Sync-NeRF’s original table; inspect protocols before comparing those
  numbers. Also distinguish Sync-NeRF’s test-view timing optimization from evaluation without fitting to
  test images. VisualSync comparisons, Sync-NeRF protocol.

  Audit the supplied repository diagnosis against saved evidence. Separate demonstrated failures, plausible
  explanations, and untested hypotheses.

  ## 3. Staged pilots

  Stage A — Establish runnable baselines

  - Provision Docker Engine and NVIDIA Container Toolkit on the existing Ubuntu host, using official
    installation procedures and required host-access approvals. Validate GPU access before research
    workloads. Docker instructions, NVIDIA instructions.

  - Permit author-compatible Python and Torch versions inside isolated containers. Preserve the main
    repository environment and existing driver.

  - Audit VisualSync’s original archive, Sync-NeRF’s K-Planes implementation, and MultiViewUnsynch. Pin
    source, dependencies, weights, and container images.

  - Cap runtime setup at two hours and compatibility work at two hours per baseline, with at most two setup
    attempts each. Missing core implementations remain unavailable; this campaign does not rebuild
    unpublished systems.

  Stage B — Test synchronization on known-offset data

  - Use UDBD Box and the CMU Panoptic basketball sequence evaluated by SyncTrack4D, resolving exact release
    identifiers during the audit. If either release cannot be obtained, record that benchmark as
    unavailable.

  - Evaluate available VisualSync and Sync-NeRF implementations using documented settings, alongside zero-
    offset and supplied-ground-truth controls.

  - Add independent analytic motion fixtures with known fractional offsets. Include stationary or ambiguous
    motion, occlusions, incorrect correspondences, disconnected graphs, dropped frames, and clock-rate
    mismatch.

  - Use genuine timestamps or independently generated motion for fractional ground truth. Interpolated video
    perturbations establish sensitivity, not physical subframe accuracy.

  - Report short runs as feasibility experiments when the budget prevents reproducing published schedules.

  Stage C — Evaluate calibrated Basketball synchronization

  - Freeze the accepted calibration, scale, original 34 camera IDs, and reference camera 1.
  - Audit timestamps, cadence, duplicate-frame evidence, and existing scoreboard observations. Treat clock-
    model mismatch as a hypothesis requiring evidence.

  - Use frames 50–149 for fitting and 150–199 for development and repeatability analysis. The latter window
    has already influenced previous work and is not a fresh final test.

  - Adapt runnable VisualSync code to the accepted calibration. Use per-frame dynamic masks, learned
    tracking, cross-view matching, pair rejection, and robust global offset estimation.

  - Consider all 561 camera pairs; unsupported pairs receive explicit rejection reasons. Compare the learned
    evidence against saved SIFT/LK evidence under the same global estimator.

  - Run Sync-NeRF on eight training cameras selected deterministically from calibration overlap, starting
    with camera 1 and expanding coverage; break ties by camera ID.

  - Freeze the method, settings, candidate offsets, and reporting rules before opening 200–249. Evaluate
    this window once, without subsequent tuning.

  - Report global coverage, bridges, cycle residuals, uncertainty, window disagreement, and sensitivity to
    removing individual edges. Disconnected cameras receive no inferred synchronization claim.

  Stage D — Measure reconstruction benefit

  Use the existing STG Full and FreeTimeGS reproduction implementations on Basketball frames 0–49, at
  960×540, retaining held-out cameras 0, 10, 20, 30.

  For each method, compare zero offsets with the frozen full-rig correction using seeds 0, 1, 2. Match
  source images, initialization policy, optimizer settings, and evaluation targets. Estimate held-out-camera
  timing only from separate calibration/timing windows.

  Reserve corrected-time interval [0.8, 1.0) seconds for temporal interpolation evaluation. Remove the union
  of affected training images across both timing conditions so the conditions use identical training inputs.

  Each run targets 5,000 optimizer updates within 20 minutes. Save checkpoints at 1,000, 2,000, and 5,000
  updates; compare the largest checkpoint shared by all paired runs. Incomplete schedules remain explicitly
  budget-limited.

  If no full-rig correction is available, complete zero-offset controls and report the missing paired
  comparison.

  ## 4. Interfaces and validation

  Add a versioned timing-result artifact containing camera IDs, reference camera, offsets, units,
  uncertainty, temporal window, coverage, and provenance. Preserve the repository convention:

  corrected_timestamp_seconds = source_timestamp_seconds − offset_seconds

  Feed continuous corrected timestamps into Basketball scene adapters, with one shared normalization and
  valid temporal support. Preserve source frame IDs and reject extrapolation outside supported data.

  Validate:

  - Offset signs, reference-camera invariance, units, and timestamp round trips.
  - Calibration resizing and undistortion conventions.
  - Camera/time exclusions and absence of test-image optimization.
  - Robustness to injected bad edges and explicit handling of disconnected graphs.
  - Complete model saving, fresh offline reload, and rendering across viewpoints and times.

  Report timing error distributions where truth exists, plus full-image and dynamic-region PSNR, SSIM,
  LPIPS, temporal observations, rendering speed, memory, and charged compute. Use paired seed comparisons
  and temporal block resampling; do not treat correlated pixels as independent evidence.

  ## 5. Resources, decisions, and deliverables

  The 12 GPU-hour ceiling covers all new GPU work, including failed attempts and startup:

   Allocation                                                         Maximum
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━
   GPU checks, learned preprocessing, and VisualSync evaluation       4 hours
  ─────────────────────────────────────────────────────────────────  ─────────
   Sync-NeRF: two benchmark runs and three Basketball cross-checks    3 hours
  ─────────────────────────────────────────────────────────────────  ─────────
   STG Full: six paired-condition runs                                2 hours
  ─────────────────────────────────────────────────────────────────  ─────────
   FreeTimeGS reproduction: six paired-condition runs                 2 hours
  ─────────────────────────────────────────────────────────────────  ─────────
   Rendering, metrics, and reload verification                         1 hour

  Use one GPU job at a time. Preserve the existing 24-hour training ceiling and consumed records. Keep each
  Basketball reconstruction method within its existing two-hour allocation. Unused allocations do not
  authorize additional scientific attempts or transfers.

  Apply these decision rules:

  - Recommend calibrated learned synchronization when it supports the full rig and produces repeatable held-
    out reconstruction improvement. State whether the benefit holds for both reconstruction methods or only
    one.

  - Prefer zero-offset operation when corrections provide no repeatable benefit, identifying zero as an
    operational assumption rather than verified physical synchronization.

  - Recommend a specific follow-up when evidence points to correspondence failure, clock-model mismatch, or
    reconstruction limitations. Do not automatically return to spline-evaluator refinement.

  - Report unavailable implementations, inconclusive pilots, and budget limits separately from scientific
    failures.

  Deliver a cited research report, verified citation map, benchmark/code matrix, frozen experiment protocol,
  retained results, and a ranked recommendation under docs/research/basketball-sync-pivot/. Save the
  execution specification at the next unused numbered plan and commit completed, validated milestones
  locally under the repository’s rules.
