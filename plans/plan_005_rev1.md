# Authorized camera 19 removal

The user explicitly removed camera 19 and instructed continuation. The active
protocol is `basketball-intrinsic20-no-camera19/v1`: **23 cameras, 20 training,
held-outs 0, 10, 30**. Expected preparation is **1,150 images, 1,000 training
and 150 held-out**. Exclusions are **4, 5, 8, 11, 15, 16, 17, 18, 19, 20, 23**.
These counts supersede earlier counts below. Preserve original IDs, the 20%
intrinsic gate, all pose/validation gates, historical artifacts and budget charges.

Rebuild the previously best fixed-principal, expanded sharp-SIFT recipe using
initial pair 6–12 from databases containing only retained training observations;
do not merely remove camera 19 from the previous error vector. Reuse verified
complete retained priors and masks. If independent poses pass, continue frozen-map
held-out localization and the remaining original validation/downstream work.
If recovery is still needed, the same finite A/B/C configurations bound the new
camera-set search; count the rebuilt best configuration once within that bound.

# Authorized 20% camera-set revision

The user restored the intrinsic-prior variation limit to **20%** and excluded
all failures from the completed ten-frame test. Camera 5 remains excluded.
Active exclusions: **4, 5, 8, 11, 15, 16, 17, 18, 20, 23**.
The active protocol is `basketball-intrinsic20/v1`: **24 cameras, 21 training,
three held-out (0, 10, 30)**. Preserve physical IDs; do not replace removed
held-out camera 20. Expected preparation: **1,200 images, 1,050 training and
150 held-out**. These values supersede the 25%, 33/29/4-camera and
1,650/1,450/200-image values in the historical revision below and downstream
reports. All rig acceptance gates apply to the 24 retained cameras.

Reuse hash-bound retained ten-frame priors, complete missing masks, and restart
the same finite A/B/C search for this camera set. Remove excluded observations
from copied match databases before reconstruction. Preserve all previous
attempts and budget charges; the existing downstream-only extension policy and
per-method training allocations are unchanged. No additional camera removal
based on pose or matching results is authorized by this selection.

# Plan 005 revision 1: Stable Basketball calibration and experiment continuation

## Objective and preserved constraints

Recover validated estimated Basketball calibration, then complete synchronization,
preparation, initialization and the runnable experiments from plan_005.md. This
revision supersedes that plan's camera counts and exhausted recovery options.
Preserve the original plan and historical evidence.

- Active protocol: basketball-no-camera5/v1; 33 retained cameras, 29 training and
  held-out cameras 0, 10, 20, 30. Preserve physical IDs and camera 5's raw video;
  exclude camera 5 from subsequent estimation, initialization and evaluation.
- Frames 50–149 fit, 150–199 selection, 200–249 final validation. Frames 0–49
  cannot enter calibration estimation. Held-out observations cannot refine the
  training map.
- Retain the pinned ViPE checkout and dependencies. Preserve hash-bound SelfCap
  adapters, checkpoints and the original two-hour Basketball allocation per method.
- Keep the 25% prior variation check and all original acceptance gates, including
  maximum 0.5 degree rotation and 1% rig-diameter center disagreement.
- Automatic methods only; no manual annotations, additional camera exclusions,
  threshold relaxation or substitute calibrations.

The previous converged result failed at 7.3065 degrees and 4.1972% center error.
Independent principal points differed by about 110 pixels median / 134 maximum
at 960x540. Mapping completed well below its ten-minute cap; more timeout is not
a recovery strategy.

The user observes unchanged zoom during playback, different focus distances
between cameras, and apparently stable focus within videos. Verify focus
automatically. Use one constant pose and intrinsic set per physical camera per
reconstruction, with different intrinsic values allowed between cameras. Focus
distance does not establish focal length. The 25% check screens prior estimates;
it neither models physical zoom changes nor constrains bundle adjustment.

## Recovery implementation

Use immutable revision-specific outputs with effective options, input/config/code
hashes, frame and feature provenance, intrinsic drift, initialization pairs,
termination, timings and budget charges. Freeze the search manifest before runs.
Provide explicit intrinsic-policy, feature-recipe, fitting-frame and initial-pair
interfaces. Share native option construction between mapping, absolute-pose
registration and final adjustment so fixed parameters stay fixed throughout.

Defaults: PINHOLE; seed 0; eight CPU threads; mapping at most 600 seconds;
SOFT_L1 scale 1 pixel; final adjustment at most 1,000 iterations / 120 seconds;
function, gradient and parameter tolerances 1e-8. No further distortion search.
Start from original priors and observations, never previously drifted intrinsics.

Two policies, in order:
1. Fixed principal point with free fx/fy.
2. Fixed principal point and fx/fy throughout, including absolute-pose registration.

Use componentwise median GeoCalib intrinsics from the relevant window only.
Independent windows must not share estimated intrinsics, poses or geometry.

### Expanded observations and automatic focus screening

Early frames: 50, 62, 75, 87, 99. Late: 100, 112, 125, 137, 149.
Reuse verified existing artifacts; generate only missing priors and semantic /
temporal-motion masks. Retain valid representative depth maps. Apply the same
25% variation formula to all ten samples for each retained camera.

Track static patches using forward/backward consistency and robust alignment.
Report patch sharpness, track survival, alignment residuals and apparent scale.
Flag changes exceeding 30% median matched-patch sharpness or 1% apparent scale
for three successive samples relative to the first usable sample. Insufficient
tracks are inconclusive. These are screening heuristics, not proof of autofocus
or zoom. Do not infer focus distance or reject a whole camera for local blur.
Flagged cameras must still pass the unchanged pose and validation gates.

### Focus-aware feature recipes

Retain static descriptor-support rejection and two-pixel observation deduplication;
affine features use their actual support extent for mask clearance. Score each
21x21 grayscale patch by mean squared Laplacian divided by local variance plus
1e-6, with intensities in [0,1]. Reject variance below 1e-4. Keep the highest
score in each deduplication cell, ties by source frame then feature index.
Require both matched endpoints to meet their camera/window's 20th percentile
score. Record rejections and spatial coverage; do not loosen thresholds later.
Repeated timestamps do not count as independent geometric support.

Expanded recipes, in order:
1. Standard SIFT, 8,192 features per image, focus-aware selection.
2. Affine/DSP-SIFT, 16,384 features, focus-aware selection, guided matching.
3. Recipe 2 plus new RoMa correspondences with confidence >=0.95.
4. Recipe 2 plus the same RoMa predictions with confidence >=0.90.

Authorize one new pinned RoMa inference pass: frames 50 and 149, at most 64
training-camera pairs / 128 inferences. Select verified-overlap spanning-tree
and ranked extra edges deterministically, never camera-ID adjacency. Retain
predictions sufficient for both confidence variants without reinference. Require
eight-pixel static-mask clearance, bilateral sharpness checks, one match per
16-pixel cell in each image and at most 1,500 matches per pair, followed by native
geometric verification.

### Finite search and stopping

| Stage | Configurations | Maximum independent reconstructions |
| --- | --- | ---: |
| A | Two policies x existing SIFT-only / SIFT+RoMa; original early/late samples | 8 |
| B | Two policies x four expanded recipes | 16 |
| C | Two policies x two explicit initial pairs using the policy's best complete B recipe | 8 |

Maximum 16 paired configurations / 32 independent reconstructions. Run stages
and policies/recipes in listed order. Complete each stage before comparison;
advance only if it yields no eligible candidate. Failures, timeouts, incomplete
registration and unresolved degeneracy are failed configurations, not invitations
to add seeds, thresholds, models or result-improving retries.

Stage C ranks complete B results by max(max_rotation/0.5, max_center_fraction/0.01),
ties by configuration ID. Initial pairs must be eligible in both windows: >=100
inliers, >=16 degree triangulation angle, support in >=6 cells of a 4x4 grid in
both images, and homography support below 80% of verified matches. Rank by minimum
inlier count across windows then physical IDs. Use the same pair in both windows;
run at most two. Skip missing eligible pairs or policies without complete maps.

## Selection, acceptance and budgets

Require one connected complete 29-camera training map. Use the existing single
global similarity alignment for independent windows, reporting conditioning;
do not change alignment to reduce the metric. Independently localize held-outs
against each frozen map, then apply the training-derived alignment without
refitting it. All 33 cameras must meet pose gates.

For fitting-eligible candidates, build pooled fitting maps using their exact
recipe/policy and localize held-outs against frozen training geometry. At most
eight pooled candidates are needed because search stops at the first eligible
stage. Selection observations evaluate frozen candidates without refinement.
Rank by lowest worst-camera p95 reprojection error, aggregate median, then ID;
require support and coverage before ranking. Freeze one winner before final
validation. A final-validation failure blocks continuation; do not use final
results to select another candidate.

All original acceptance gates apply: all 33 registered; valid rotations and
positive focal lengths; >=100 independent static validation correspondences per
camera with support from >=2 other cameras; coverage in >=6 of 16 image-grid
cells; median <=1 pixel and p95 <=3 pixels at 960x540 per camera; >=95% positive
depth; no planar ambiguity or unstable alternatives; independent-window maximum
rotation <=0.5 degree and center <=1% rig diameter; timing agreement <=0.25 frame
with distinguishable optima and consistent cycles.

Read the live original GPU ledger (previously 718.3131 / 28,800 seconds charged).
Recovery may consume its remaining allowance, subject to the finite search.
Do not reset charges. GPU jobs run sequentially, including failed-attempt charges;
CPU work is timed separately and bounded by attempts and per-run limits.

If accepted calibration leaves insufficient allowance for downstream synchronization,
validation or initialization, authorize one additional eight GPU-hours for those
stages only, with an explicit separately accounted extension. It cannot fund more
recovery or enlarge/redistribute any method's two-hour training budget.

## Original downstream continuation

After static calibration passes, complete plan_005.md with corrected membership:

- Estimate one robust scale from training-view ViPE depth, with uncertainty;
  never assume court dimensions.
- Estimate dynamic-track synchronization relative to camera 1 with integer search
  +/-25 frames and fractional refinement. Reject ambiguity, boundary solutions,
  inconsistent cycles or drift; never assume zero offsets.
- Export versioned estimated calibration, coordinate/pixel/time conventions,
  uncertainty, provenance, validation and diagnostics.
- Prepare frames 0–49 at 960x540: exactly 1,650 images, 1,450 training and 200
  held-out. Preserve corrected-time normalization, undistortion/resizing,
  ground-truth-selected fixed crops and the shared 20-pose sweep from camera 0 /
  frame 25 to its nearest retained training camera.
- Generate initialization anew from training observations: midpoint geometry for
  STG Lite, STG Full and ATGS; pinned EDGS/RoMa keyframes 0,5,...45 and successors
  1,6,...46 for FreeTimeGS reproduction. No held-out images or calibration clouds
  as initialization. Preserve hash-bound SelfCap code/checkpoints unchanged.
- Run the four methods sequentially under existing Basketball training ledgers.
  Evaluate last complete checkpoints and reproduce all 200 held-out / 20 sweep
  renders in two fresh network-disabled processes.
- Deliver PSNR, SSIM, LPIPS-Alex, baseline deltas, PNGs, MP4s, crops, contact
  sheets, checkpoint sizes and resource measurements. Benchmark camera 0/frame
  25 with ten warmups and 100 timed renders. Keep visual defects distinct from
  numeric metrics. Update reports 006–010 and comparisons; preserve independent
  MoE-GS and FreeTimeGS++ blockers.

## Tests and completion

Test native fixed-parameter invariants; per-camera distinction and window
independence; synthetic pose/intrinsic ambiguity, alignment and pixel transforms;
blur priority, deterministic deduplication and bilateral filtering; focus flags
and inconclusive cases; expanded provenance / camera exclusion / leakage guards;
search ordering, ranking, caps, timeout charges and downstream-only extension;
registration, coverage, degeneracy, depth and timing failures; image counts,
shared sweep, fresh initialization and SelfCap regression; offline reload,
evaluator and existing budget checks. Validate documentation and git diff --check.

Publish per-configuration errors, intrinsic drift, support, solver termination
and resources, distinguishing diagnostics from accepted calibration. Create
validated local milestone commits with titles/descriptions, without pushing.
Continue after commits until results are reproducible or a defined evidenced
blocker prevents progress within authorized search and budgets.
