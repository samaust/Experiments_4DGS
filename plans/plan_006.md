# Plan 006: Calibration alternatives for VRU Basketball DG

Status: active. This protocol supersedes camera exclusions and the cumulative
calibration GPU allowance for this investigation only. Historical experiments,
their artifacts and training budgets remain immutable.

## Objective

Recover all 34 physical cameras with lower rotation and camera-center
disagreement. The historical 23-camera search reached 5.8807 degrees and 7.1892%
despite convergence ([report](../docs/experiments/basketball-no-camera19.md)).
Geometric accuracy, coverage and reproducibility take priority over runtime and
memory. Preserve camera IDs, including 5 and 19. GeoCalib's 20% stability gate
only controls trust in priors; it must never exclude a camera or prevent masks.
Intrinsics are constant over time within each camera, independent across cameras.
Fixed zoom is not evidence of accurate intrinsics or identical focus/lenses.

## Research and installation gates

First audit the [official release](https://huggingface.co/datasets/BestWJH/VRU_Basketball/tree/main),
linked projects and preprocessing for reusable DG calibration, checking names,
image geometry and provenance. Do not substitute another venue's calibration.

Investigate and test every route passing installation and input/output checks:

| Route | Released implementation | Required distinction |
| --- | --- | --- |
| COLMAP global / GLOMAP (ECCV 2024) | https://github.com/colmap/colmap | Calibrate the view graph on a database copy when reliable focal priors are unavailable. |
| MASt3R-SfM (3DV 2025) | https://github.com/naver/mast3r | Actual sparse global alignment, not experimental COLMAP/GLOMAP examples. |
| VGGSfM (CVPR 2024) | https://github.com/facebookresearch/vggsfm | Multiview tracking, dynamic masks, COLMAP export. |
| VGGT-Ω (CVPR 2026) | https://github.com/facebookresearch/vggt-omega | Released 512 reconstruction checkpoint. |
| Depth Anything 3 | https://github.com/ByteDance-Seed/Depth-Anything-3 | Refreshed DA3-GIANT-1.1, accuracy-oriented ray-pose option. |
| Pi3 / Pi3X (ICLR 2026) | https://github.com/yyfz/Pi3 | Test Pi3X, identified as a later engineering update. |
| MapAnything (3DV 2026) | https://github.com/facebookresearch/map-anything | Image-only reconstruction; audit existing comparison adapters. |

Record paper version/venue, official revision, checkpoints, separate code/weight
licenses, inputs/outputs (K, distortion, poses, scale, synchronization), masks,
independent intrinsics, static-video/wide-baseline/limited-overlap limitations,
installation requirements, commands, export support and measured resources.
Use isolated environments under the existing Python/Torch/CUDA policy.
Pin pretrained weights and documented defaults before screening.

Compare author-reported and independently reproduced evidence separately. Audit
MASt3R-SfM sparse/view-count results, [DA3 unknown-pose vs pose-conditioned benchmarks](https://arxiv.org/html/2511.10647v1),
[RealX3D physical degradations including defocus](https://arxiv.org/html/2512.23437v1),
and [dense-match rig calibration ablations](https://arxiv.org/abs/2512.15608).
Pose AUC at several degrees does not establish 0.5-degree repeatability;
translation direction does not measure camera-center disagreement.

## Finite experiment matrix

Full rig: training cameras are 0–33 except held-outs 0, 10, 20, 30. Frames 50–149
are fitting, 150–199 selection, 200–249 final validation, 0–49 downstream only.
Generate masks and focus/quality diagnostics independently of GeoCalib success.
Use static observations until synchronization is established; frame numbers alone
do not establish synchronized player positions.

Screen each of seven routes plus an incremental COLMAP control using the same
SuperPoint/LightGlue frontend as global mapping. Three independent snapshot
pairs: (50,100), (75,125), (99,149), one image per training camera. Thus at most
48 primary reconstructions. Do not share fitted poses or intrinsics across
windows. Record native predictions, failures, convergence, wall time, peak host
and GPU memory, configuration changes, source/input/output hashes and pixel/pose
conversions. Try memory-saving modes before lowering resolution.

Apply one training-center similarity alignment. Report the complete training
set and separately the historical common-camera subset under that same
alignment; incomplete reconstructions cannot win by omission. Rank complete
routes by worst-pair max(rotation/0.5 degrees, center fraction/0.01). Break ties
by maximum rotation, maximum center disagreement, then total runtime.

Advance up to three best complete routes to the independent five-frame early
(50,62,75,87,99) and late (100,112,125,137,149) windows. Compare native output,
common robust BA with fixed predicted intrinsics, BA with one focal per camera
(square pixels, centered principal point), and that BA plus one radial term.
Compare ordinary static vs sharpness-filtered support, using spatially
distributed matches and deduplicated repeated observations. Inspect failure by
camera and region. Repeat seeds 0,1,2. At most 72 paired finalist configurations
(144 reconstructions); native duplicate configurations may be reused only with
explicit accounting. Extend iterations only for logged pre-convergence exits.

If still failing, test [Dense-SfM](https://github.com/IceTea-CV/DenseSfM-Refine)
refinement with camera optimization enabled and [MP-SfM](https://github.com/cvg/mpsfm)
separately on the best complete initialization. MP-SfM requires independently
estimated intrinsics; known-intrinsic benchmarks are not self-calibration proof.
Audit [CasCalib](https://github.com/jamestang1998/CasCalib)'s upright-person and
common-height assumptions before one pilot. Dense-match VISAPP 2026 remains
methodological evidence until an official runnable release is verified. Do not
prioritize targets, unavailable measurements or known-pose prerequisites.
Stop after declared follow-ups; no unlimited search or timeout escalation.

## Acceptance and handoff

Localize held-outs against frozen training geometry, applying the training
similarity without refitting to held-outs. All 34 cameras must satisfy:

- Maximum rotation disagreement ≤0.5 degrees and center disagreement ≤1% rig diameter.
- Validation reprojection median ≤1 px and p95 ≤3 px at 960×540 per camera.
- ≥100 independent static correspondences, support from two other cameras,
  and coverage in ≥6 of 16 grid cells.
- ≥95% positive depth, valid rotations and positive focals.
- No unresolved planar ambiguity or unstable alternative solution.

Select with 150–199, freeze one winner, evaluate 200–249 once. Repeatability is
not ground-truth accuracy. Scale and synchronization need separate validation.
Downstream Gaussian training remains gated and belongs to Plan 005.

Test ID preservation, frame isolation, resize/crop conventions, pose inversion,
similarity alignment, frozen-map localization and incomplete-model rejection.
Reload exported calibration and verify observation reprojection.

Deliver this protocol, a linked [research matrix](../docs/research/basketball-calibration-alternatives.md),
and a measured [experiment report](../docs/experiments/basketball-calibration-alternatives.md)
with machine-readable results, per-camera plots and reproducible commands.
Create local commits at validated milestones. Finish with a validated full-rig
calibration/handoff or documented ranking and precise remaining blocker.
