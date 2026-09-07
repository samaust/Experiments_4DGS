# Plan 005 revision 2: Basketball continuation with accepted calibration

## Scope and accepted inputs

Status: static calibration complete; metric scale, synchronization, shared input
preparation, fresh initialization and Basketball experiments remain gated. This
standalone continuation replaces the recovery work in [revision 1](plan_005_rev1.md)
and [Plan 005](plan_005.md). Preserve both files and their historical evidence.
Creating this revision is a documentation-only milestone; it does not launch the
continuation described below.

[Plan 006](plan_006.md) accepted incremental COLMAP initialization, ordinary
masked SIFT support and robust bundle adjustment with one centered square-pixel
focal length and one radial coefficient per physical camera (`SIMPLE_RADIAL`).
The common adjustment used SOFT_L1 at one pixel. The exported rig uses seed 0's
early fitting map and fitting-only held-out localization against frozen training
geometry; independent late maps and other seeds remain diagnostics.

Use these immutable inputs:

- [Accepted estimated calibration](../docs/experiments/basketball-calibration-alternatives/calibration.json),
  SHA-256 `21139df550a6fa72c9730d4c658a58464ce00be9ff268380ab433c3d9471e74f`.
- [Full-rig scene profile](../configs/scene-manifest.vru-basketball-dg.full-rig.json),
  SHA-256 `c19598363821b41ea3e143a9175595a2fb7ed56f952a4f6844a01c8bdaa4de82`,
  protocol `basketball-alternatives/v1`, training-ledger scene `vru-basketball-dg`.
- [Handoff and limitations](../docs/experiments/basketball-calibration-alternatives.md#plan-005-handoff),
  [full-rig repeatability](../docs/experiments/basketball-calibration-alternatives/full-rig.json),
  [frozen winner](../docs/experiments/basketball-calibration-alternatives/frozen-winner.json),
  [final static validation](../docs/experiments/basketball-calibration-alternatives/validation.json)
  and [export reload evidence](../docs/experiments/basketball-calibration-alternatives/export-reload.json).

All **34 physical camera IDs 0–33** are retained: **30 training cameras** and
held-outs **0, 10, 20, 30**. There are no camera exclusions or renumbering.
GeoCalib is not an initialization requirement for this accepted rig. Retain the
**20%** GeoCalib variation threshold solely to assess trust in priors where such
priors are used; it neither excludes cameras nor constrains accepted intrinsics.

Completed static acceptance evidence at 960×540:

| Check | Accepted result | Gate |
| --- | ---: | ---: |
| Registered cameras, valid rotations and positive focal lengths | All 34 | All 34 |
| Maximum early/late rotation disagreement across three seeds | 0.163815° | ≤0.5° |
| Maximum early/late center disagreement across three seeds | 0.354980% of rig diameter | ≤1% |
| Worst-camera final median reprojection | 0.505951 px | ≤1 px |
| Worst-camera final p95 reprojection | 2.228025 px | ≤3 px |
| Minimum independent final static points per camera | 108 | ≥100 |
| Minimum occupied final grid cells | 11/16 | ≥6/16 |
| Minimum positive depth | 100% | ≥95% |
| Minimum robust nonplanarity diagnostic | 0.072753 | ≥0.01 |

Static support requires at least two other cameras. The saved evaluator measures
continued established static tracks, not arbitrary new-feature matching.
Camera 0 has only a modest support margin. Preserve those limitations and the
validation evidence; these engineering gates do not establish official-camera
accuracy, metric scale or synchronization.

## 1. Verify provenance and conventions

Before downstream computation, verify the calibration and profile hashes above,
all frozen map/anchor hashes, and the source-video hashes in
`.local/calibration/basketball-v1/input-audit.json`. Audit all 34 video mappings,
dimensions, decoded frame counts, frame rates and timestamps. Reject changed
inputs, camera-ID swaps, missing frames or unresolved variable timing. Record
code, configuration, environment, dependency and weight hashes for new outputs.

Preserve Plan 006's consumed `validation-consumed.json` beside its local frozen
winner, plus the winner and all saved validation artifacts. Never delete/reset
that marker, rerun static final evaluation, reopen static candidate selection,
or refine the accepted calibration. Hash checks and replay of saved observation
projections may verify integrity without consuming final images again. Use new
versioned downstream artifacts linked to the immutable calibration hash.

The calibration has world-to-camera poses `X_camera = R X_world + t`, camera
centers `C = -R^T t`, and OpenCV integer pixel centers at 960×540. `K` contains
OpenCV principal points; `parameters_colmap = [f, cx, cy, k1]` contains COLMAP
half-integer principal points. Explicitly add 0.5 to OpenCV image coordinates and
principal points when converting to COLMAP; subtract 0.5 on return.

Preserve normalized radial distortion `x_d = x(1 + k1 r²)`,
`y_d = y(1 + k1 r²)`, with `r² = x² + y²`. For an integer-center resize by
`sx, sy`, use `fx' = sx fx`, `fy' = sy fy`,
`cx' = sx(cx + 0.5) - 0.5`, `cy' = sy(cy + 0.5) - 0.5`; retain `k1`.
A crop subtracts its origin from the principal point. Honor distortion directly
or undistort consistently for every consumer, propagating the resulting K,
valid-image region, crop and resize transforms. Never treat distorted images as
pinhole images. Record raw-to-calibration and calibration-to-processed transforms.

## 2. Validate scale and synchronization with separate frame roles

Preserve the ViPE checkout `/home/auss/git_repos/samaust/Tridi/vipe`, branch
`tridi`, revision `de50e6ab1066e32c96d32499a282ecaa2fbf2d90`, unchanged.
Verify its pinned dependencies, compiled extensions and weights under the
[environment policy](../docs/environments.md). Prefer its existing environment;
any necessary compatible isolated environment belongs inside this repository.
Reuse only hash-verified fitting-view depth or generate missing training-view
ViPE depth. Fit one robust positive global scale against fixed training geometry,
report uncertainty, support and cross-view consistency, and block unsupported or
inconsistent scale. Depth supplies uncertain estimated scale; do not assume court
dimensions or combine unrelated monocular pose systems. Apply the one scale
consistently to derived geometry, centers and translations, preserving rotations
and the immutable unscaled input. Freeze the scale estimator and its validation
criteria before inspecting reserved data; report estimated rather than measured
metric accuracy.

Use this separation for the remaining timing task:

| Original source frames | Remaining role |
| --- | --- |
| 50–149 | Fit constant timing offsets and training-view scale |
| 150–199 | Timing model/parameter selection and independent scale checks |
| 200–249 | Separately frozen final timing validation only |
| 0–49 | Downstream preparation, initialization, training and evaluation only |

Plan 006 already consumed these reserved windows for static selection/validation.
Their timing use is a separately declared dynamic-track assessment with its own
freeze and consumption record; it cannot revise static calibration. Freeze timing
tracks, support rules, scoring, uncertainty policy and selection before timing
final validation. A final timing failure blocks continuation rather than selecting
a replacement from those results.

Estimate constant offsets relative to **training camera 1** using dynamic-region
cross-camera correspondences and temporal tracks. Search integer offsets **±25
frames**, then refine fractional offsets with interpolated tracks and robust
undistorted epipolar/triangulation consistency on verified overlap edges. Record
per-camera offset sign, units, uncertainty, search curves and graph support; do
not infer timing from equal frame rates or static backgrounds. Require agreement
**≤0.25 frame** across independent validation subsets and graph cycles, with a
distinguishable optimum for every camera. Reject ambiguous or boundary-hitting
solutions, disconnected support, inconsistent cycles and evidence of drift; never
silently assign zero offsets. Held-out timing observations may estimate their
fixed offsets but cannot update training geometry or seed Gaussian initialization.

Enforce roles on both endpoints and all interpolation support samples; an offset
search must not cross a role boundary into reserved or downstream frames. Trim
unsupported track intervals and report insufficient overlap as a blocker. No
threshold relaxation, manual annotations or substitute calibration is authorized.

## 3. Prepare shared downstream inputs

After provenance, conventions, scale and timing pass, produce a versioned
Basketball processed manifest and Basketball-specific scene, initialization,
training and evaluation adapters. Use existing camera/time field conventions;
do not label the scene `selfcap-processed/v1`. Keep the accepted inputs unchanged
and place derived scale/timing/calibration transforms in separately hashed outputs.

Prepare exactly **1,700 images at 960×540**, using original source frames **0–49**
for all 34 cameras: **1,500 training** and **200 held-out**. Preserve physical
camera IDs and original frame IDs even through reindexed APIs. Store explicit
source timestamps, corrected timestamps, offset convention and one shared time
normalization for every method and evaluation view. Do not relabel equal source
frame numbers as simultaneous. Record any temporal interpolation and its valid
support; missing required support blocks preparation rather than changing counts
or silently extrapolating.

Freeze detail crops selected from ground truth before inspecting model outputs.
Create one shared **20-pose sweep** at camera 0/frame 25's corrected time, from
camera 0 to its nearest training camera by accepted camera-center distance;
record the chosen camera and deterministic tie handling. All methods consume the
same sweep, crops, image transforms and time normalization.

## 4. Generate fresh training-only initialization

Preserve existing hash-bound SelfCap adapters, checkpoints and reload behavior;
use versioned Basketball adapters without checkpoint migration or SelfCap
checkpoint reuse. Generate Gaussian initialization anew from the 30 training
cameras' downstream observations. Held-out images, calibration clouds and ViPE
depth cannot become Gaussian initialization. Calibration provides fixed cameras
and scale only; retain per-point observation provenance to prove isolation.

- STG Lite, STG Full and ATGS: fixed-calibration midpoint geometry at frame 25,
  with explicit treatment of corrected observation times.
- FreeTimeGS reproduction: training-only dense EDGS/RoMa temporal geometry at
  keyframes **0, 5, …, 45** and successors **1, 6, …, 46**, with explicit time
  and scale conversion. Preserve EDGS revision
  `f90b022445fc88368f75e66e8fb34aea88372cac` and its matching RoMa revision
  `370117431ffc5dc000fb46f6e581b74bdb2c3ff8` in `.local/RoMa-edgs`, as documented
  in [report 007](../docs/experiments/007-freetimegs.md). Preserve the recorded
  adapted geometry-only fast recipe, filters and dependency/asset hashes; use
  the full 30-view training membership. This remains an adapted released
  initializer, not a claim to EDGS's default pipeline.

## 5. Run eligible methods and evaluate artifacts

Only after all preceding gates pass, start fresh Basketball runs sequentially:
**STG Lite, STG Full, FreeTimeGS reproduction, then ATGS**. Preserve native
schedules, optimizer/sampler/RNG resume state, checkpoint reserves and the shared
budget supervisor. Run short budget-charged train/resume checks before long runs.
Evaluate the last complete checkpoint at native completion or budget stop.

Render all **200 held-out images and 20 sweep views** in **two fresh
network-disabled processes**, compare reload outputs and validate the shared
evaluator. Deliver per-camera and aggregate PSNR, SSIM and LPIPS-Alex, baseline
deltas, PNGs, MP4s, fixed crops, contact sheets, checkpoint sizes, training
resources and synchronized throughput. Benchmark camera 0/frame 25 with **ten
warmups and 100 timed renders**. Inspect blur, ghosting, floaters and temporal
limitations separately from numeric metrics; label results as using estimated
calibration, not official benchmark cameras.

[MoE-GS](../docs/experiments/008-moe-gs.md) remains blocked pending a validated
released modified-STG expert-training route or matching pretrained checkpoint.
[FreeTimeGS++](../docs/experiments/010-freetimegs-plus-plus.md) remains blocked
pending an identified, validated author implementation for fixed configuration B.
These independent implementation requirements survive static calibration success;
no substitute recipe or paper-only reimplementation is part of this continuation.

## Budgets and deliverables

Preserve `.local/calibration/basketball-v1/gpu-ledger.json` and all historical
charges. The handoff records **1,056.087320 seconds charged** against the original
**28,800 seconds (eight GPU-hours)** for calibration, synchronization and
initialization, leaving **27,743.912680 seconds** at that checkpoint. Read the
live ledger before scheduling; this snapshot is not a reset or new allowance.
Charge downstream work against its remaining allowance, including failures,
startup and supervised reservations. Serialize GPU jobs and time CPU work
separately. Plan 006's uncapped investigation accounting stays separate and
cannot erase historical charges or enlarge downstream/training allowances.

Retain revision 1's conditional **one additional eight GPU-hours**, separately
accounted and available only if accepted calibration leaves insufficient allowance
for downstream synchronization, validation or initialization. It cannot fund
calibration recovery, increase training allocations or be granted repeatedly.

Each method keeps its original **two-hour Basketball training allocation** in the
existing training ledger, including failed attempts and validation/resume pilots.
Preserve checkpoint reserves and crash-conservative charging; do not redistribute
unused time between methods or scenes. Stop when a defined gate or remaining
budget prevents progress and preserve evidence of the blocker.

During the future continuation, update [report 006](../docs/experiments/006-stg-full.md),
[007](../docs/experiments/007-freetimegs.md), [008](../docs/experiments/008-moe-gs.md),
[009](../docs/experiments/009-atgs.md), [010](../docs/experiments/010-freetimegs-plus-plus.md)
and the [contender summary](../docs/experiments/contender-summary.md), including
STG Lite evidence. Clearly distinguish completed static calibration, pending
scale/timing/input gates, measured method results and independent implementation
blockers. Retain historical reports and ledger entries. Deliver versioned
provenance, uncertainty, timing diagnostics, processed manifests, initialization
provenance, resolved method configurations, checkpoints, metrics and inspected
render artifacts. Record dependency restrictions in [research documentation](../docs/research.md).

## Verification and completion

Before downstream acceptance, require:

- Provenance/hash and frozen-artifact checks, including the static consumed marker;
  changed-video/profile/calibration rejection and immutable source preservation.
- Synthetic pose inversion, OpenCV/COLMAP pixel-center conversion, radial
  distortion round trips, resize/crop/undistortion propagation and global-scale
  consistency/uncertainty checks.
- Camera-ID and split checks for all 34 cameras, held-outs 0/10/20/30, and exactly
  1,700 images with 1,500/200 membership; missing-frame and swapped-ID rejection.
- Frame/time role and leakage checks: fitting cannot access 0–49; timing support
  cannot cross role boundaries; held-outs cannot refine training geometry;
  Gaussian initialization cannot read held-out images or calibration clouds.
- Synthetic known fractional-offset recovery, ambiguity/boundary/drift/cycle and
  disconnected-support failures; ≤0.25-frame validation agreement; separately
  frozen timing validation and no reopening of static selection.
- Shared corrected timestamps, normalization, crops and 20-pose sweep checks;
  fresh initialization provenance and unchanged SelfCap checkpoint regressions.
- Budget/reservation/failure accounting, downstream-only extension constraints,
  train/resume validation, offline reload comparisons and shared metric checks.

For this documentation milestone, validate relative Markdown links, hashes,
accepted evidence, camera/image counts and budget consistency; run
`git diff --check`. Stage only `plans/plan_005_rev2.md` and create a local commit
with a title and description. Preserve revision 1 and do not push or execute
experiments as part of this change. Future implementation commits are checkpoints;
continue within this scope until reproducible eligible results or an evidenced
gate/budget blocker is reached.
