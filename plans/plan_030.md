  # Plan 030 — Study ViPE alternatives for calibration, scale, and dense initialization

  ## Summary

  Produce a cited study and benchmark specification focused on removing ViPE and
  improving output quality. Treat commercial-use permission and an open-source license
  other than AGPL-3.0 as optional preferences, assessed separately.

  Cover the three requested steps and adjacent motion-filtering and neighbor-selection
  algorithms. Target local execution on Ubuntu/RTX 4090; separate Python environments are
  acceptable. This study involves documentation and source inspection, with no model
  installation, inference, calibration runs, or training.

  ## Study coverage

  First map ViPE imports, wrappers, provenance checks, and downstream consumers.
  Distinguish its segmentation and depth components from the repository’s decoding,
  motion filtering, scale estimator, freeze construction, and neighbor ranking.

   Step                     2.1 — Calibration snapshots and moving-content exclusion
   Alternatives to examine  Standalone historical segmentation stack; Grounding DINO +
                            SAM 2.1; SAM 3; RT-DETRv2 + SAM 2.1. Compare current frame
                            differences with temporal-median residuals and MOG2
                            background subtraction.
   Main questions           Moving-content leakage, unnecessary background exclusion,
                            small-ball detection, stationary people, and preservation of
                            useful calibration features.
  ───────────────────────────────────────────────────────────────────────────────────────
   Step                     2.5 — Physical scale and reconstruction freeze
   Alternatives to examine  Standalone UniDepth V2, DA3METRIC-LARGE, Metric3Dv2, and
                            Depth Pro. Include independently measured distances as a
                            conditional scale anchor.
   Main questions           Compatibility with accepted intrinsics, metric-depth
                            conventions, cross-camera consistency, uncertainty, and
                            required freeze/provenance changes.
  ───────────────────────────────────────────────────────────────────────────────────────
   Step                     4.2 — Training masks and camera neighbors
   Alternatives to examine  Reuse the segmentation shortlist for keyframe/successor
                            pairs. Compare current shared-track counts with normalized
                            co-visibility and coverage/parallax-aware neighbor selection.
   Main questions           Player and ball masks, spectator handling, temporal
                            consistency, crop associations, triangulation support, and
                            camera coverage.

  For each model candidate, record exact released variants, official sources,
  preprocessing, dependencies, supported runtime, published quality evidence, reported
  resource requirements, and integration effort. Audit licenses for code, weights, and
  required dependencies separately; distinguish non-commercial restrictions, copyleft,
  and custom terms.

  Use the current ViPE stack as the reference and direct upstream components as a
  dependency-removal control. Do not assume matching model names guarantee identical
  preprocessing or outputs.

  ## Benchmark and integration specification

  Design future experiments that change one component at a time, followed by a combined
  finalist comparison.

  - Data protocol: Preserve calibration fitting frames 50–149, selection frames 150–199,
    and the recorded validation history for 200–249. Keep cameras 0, 10, 20, and 30
    excluded from reconstruction initialization and training. Include crossing frames 20–
    24 in reconstruction-mask diagnostics and flag historical guards that exclude them.
    Previously inspected data must be identified in the evidence record.

  - Mask evaluation: Specify independently reviewed annotations for players, other
    people, ball, and changing background. Measure class-specific precision/recall, mask
    and boundary accuracy, successor-frame consistency, foreground leakage into static
    evidence, and retained static-feature coverage. Include occlusion, motion blur, tiny
    balls, spectators, shadows, and changing displays.

  - Scale evaluation: Hold calibration and sparse geometry fixed. Use the existing equal-
    camera global-scale estimator, fitting frame 100 and checking the frozen estimate on
    frame 175. Preserve existing support, consistency, and uncertainty gates. Assess
    physical accuracy only where independent measured references exist; otherwise report
    repeatability and unresolved metric bias.

  - Neighbor evaluation: Keep three neighbors per reference camera and deterministic tie-
    breaking. Compare overlap, spatial coverage, parallax, accepted triangulations, and
    matching cost. Separate this comparison from experiments that regenerate calibration.

  - Interfaces: Specify future adapters for static-mask PNGs, instance-label arrays with
    semantic mappings and pair-local identities, changing-region masks, and metric
    camera-z depth arrays. Explicitly document resolution, undistortion, intrinsics
    transformations, invalid values, and optional confidence semantics.

  - Freeze compatibility: Identify ViPE-specific audit and hash dependencies that must
    become component provenance. Specify fresh experiment artifacts and consistent
    camera/geometry scaling while retaining historical evidence.

  - Future execution limits: The benchmark document must enumerate exact configurations,
    input selections, annotation effort, attempt counts, GPU/time limits, and stopping
    rules before any later experiment begins.

  ## Deliverables and acceptance

  Create:

  - docs/research/vipe-alternatives.md: dependency map, cited comparison matrix,
    licensing evidence, ranked recommendations, and unresolved questions.

  - docs/research/vipe-alternatives/benchmark-protocol.md: reproducible comparison
    design, interface requirements, validation scenarios, and bounded execution proposal.

  Recommend a primary replacement stack, a commercial-use/non-AGPL option where
  supported, and a fallback. Clearly label expected quality improvements as hypotheses
  pending Basketball measurements.

  Completion requires coverage of all three steps, traceable technical and licensing
  claims, concrete migration implications, and an executable benchmark specification.
  Validate documentation references and protocol consistency, then create a task-related
  local documentation commit.
