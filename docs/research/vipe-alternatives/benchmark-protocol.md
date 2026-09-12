# Basketball ViPE replacement benchmark protocol

Version 1, proposed 2026-09-12, accompanying the
[Plan 030 study](../vipe-alternatives.md). **This is a specification for future
implementation and execution, not an implemented benchmark runner or an
authorization to run models under Plan 030.** Current work is documentation
and source inspection only. Future execution needs the adapters, asset/license
inventory and admission record below. Existing experiment limits and ledgers
remain intact; the proposed allocation cannot consume or reset them.

## 1. Questions and fixed controls

Test segmentation, changing-region detection, metric depth and neighbor ranking
independently, then test combined stacks. Use the current ViPE calls as S0/D0
references and direct upstream components as S1/D1 dependency-removal controls.
Treat a changed processor or tracker as a changed implementation even when model
names and weight bytes match.

The accepted [calibration](../../experiments/basketball-calibration-alternatives/calibration.json),
[winner](../../experiments/basketball-calibration-alternatives/frozen-winner.json),
[scale protocol](../../../configs/basketball-rev2/scale.json), native sparse map,
source videos, split definitions, RoMa model, local triangulation implementation,
sampling policy and normalization are fixed for component comparisons. All
geometry acceptance tests retain finite/positive depth, ≤2-pixel reprojection,
≥1° parallax and ≥3-camera foreground support from the
[current consumer](../../../scripts/basketball_temporal_cloud.py).

This allocation contains **zero calibration regeneration, training, fine-tuning,
hyperparameter search, new final-window evaluation, or trained-render scoring**.
Calibration masks are compared by annotations and frozen feature/track support.
Neighbors and combined stacks are compared by matching and diagnostic
triangulation. A later map-regeneration study must be separately specified so
changed geometry cannot confound the neighbor comparison.

## 2. Data manifest and previously inspected evidence

Use physical IDs 0–33 and source frame IDs at 25 fps. Never infer camera IDs
from file ordering or confuse a pair's internal index 0/1 with source frames.
The input audit identifies `.local/data/vru-basketball/Basketball_dg/{camera}.mp4`.
Resolve and verify its recorded paths/hashes rather than finding alternate video
copies. Calibration branch: area-resized 960×540 distorted RGB. Reconstruction
branch: hash-verified 960×540 undistorted RGB from
`.local/sync-pivot/basketball-zero/manifest.json`.

| Role | Exact selection | Permitted use |
| --- | --- | --- |
| Calibration fitting | Window 50–149; snapshots `[50,62,75,87,99,100,112,125,137,149]`, all 34 cameras: 340 images. | Fit-side mask diagnostics and threshold-independent comparison. Only the 30 training cameras may contribute reconstruction map observations. |
| Calibration selection | Window 150–199; snapshots `[150,162,175,187,199]`, all 34 cameras: 170 images. | Score already fixed mask configurations. Camera 0/10/20/30 support is localization-only evidence, never initialization/training evidence. |
| Calibration final history | Window 200–249; historically evaluated snapshots `[200,212,225,237,249]`. | Read existing reports/consumption marker only. No image decoding, new masks, retuning or replacement winner on this window in this allocation. |
| Depth scale | Training cameras only, frame 100 fit and frame 175 frozen check: 30 + 30 inputs per model. | Reuse exactly prepared undistorted RGB, source static masks and sparse sample lists for all D arms. New segmentation must not change these inputs in the isolated depth comparison. |
| Reconstruction masks | Training cameras only. Pair starts `[0,5,10,15,20,21,22,23,24,25,30,35,40,45]`, each paired with `t+1`. | 30 × 14 = 420 pairs, 840 frame contexts, **690 distinct RGB images** (23 per camera). Crossing pairs are diagnostic inputs, not a change to any historical training split. |
| Geometry diagnostics | Reference cameras `[1,6,11,16,21,26,31,33]`; pair starts `[0,20,21,22,23,24,25,45]`; three training neighbors each. | 64 reference/pair contexts and 192 directed reference/neighbor matches per geometry arm. Supporting cameras may be any of the 30 training cameras. |
| Motion context | Calibration: all integer frames in 50–149 and 150–199, separately, for 34 cameras; reconstruction: 0–49 for 30 training cameras. | At most 6,600 branch-specific RGB images. Context does not cross a role boundary. No hidden lookahead into 200–249. |

All reconstruction/initialization/training inputs exclude `[0,10,20,30]`.
The existing [training_key guard](../../../scripts/basketball_study.py), its
`KEYFRAMES`, historical manifests, and [fusion frame checks](../../../scripts/basketball_dense_fusion.py)
exclude 20–24. The future benchmark must have a **separate diagnostic loader**
that verifies membership in the explicit selection above and reads the existing
processed RGB by manifest hash. Do not weaken these historical guards or place
crossing diagnostic clouds in production initializers. Pair-specific paths are
mandatory: frame 21 is both the successor of pair 20 and the start of pair 21.

Before inspecting new outputs, write `exposure-history.json` with the following
records, the exact source hashes and any other discovered prior exposure:

| Existing record | Exposure that must be disclosed |
| --- | --- |
| [Calibration report](../../experiments/basketball-calibration-alternatives.md), [selection](../../experiments/basketball-calibration-alternatives/selection.json), [validation marker](../../experiments/basketball-calibration-alternatives/validation-consumed.json) | Fitting/selection were inspected during calibration development. Five final timestamps per camera were already consumed. Preserve the marker; the remaining final-window frames are not automatically a fresh test set. |
| [Scale fit](../../experiments/basketball-rev2/scale-fit.json) and [selection](../../experiments/basketball-rev2/scale-selection.json) | Frames 100 and 175 already informed published repeatability reports. Frame 175 is a frozen repeatability check, not new independent evidence. |
| [Dense pilot review](../../experiments/basketball-dense-temporal/pilot-review.md), [visual assessment](../../experiments/basketball-dense-temporal/visual-assessment.md), [dense report](../../experiments/basketball-dense-temporal/report.md) | Prior masks/geometry used 0/1, 25/26, 45/46 and later historical keyframes. Spectator masks, ball false positives and foreground artifacts were inspected. Read the final report alongside the earlier stopped pilot; the pilot alone is not current study status. |
| [Crossing audit source](../../../scripts/basketball_dense_crossing_audit.py) and [Plan 028](../../../plans/plan_028.md) | Frames near 20–24 and held-out-camera renders were selected after observing artifacts; all-times arms also used formerly withheld training-camera frames. New crossing diagnostics are exploratory regression evidence. |

Record report inspection separately from original-image inspection. Plan 030
opened documentation/source/metadata, not Basketball images. The fixed diagnostic
camera sample is an engineering coverage sample, not a random population sample.
Do not present confidence intervals from it as an unbiased estimate for other
gyms, and do not describe any of this reused scene as an untouched external test.

## 3. Independently reviewed annotation protocol

Annotate calibration cameras `[0,1,10,11,20,21,30,31]` at
`[50,100,149,150,175,199]`: **48 images**. Annotate all **184 distinct images**
in the reconstruction mask selection for the eight geometry-reference cameras.
Total: **232 unique images**, each linked to its exact branch, RGB hash and K.
Annotate each unique image once; store pair-specific ground-truth associations
separately so overlapping contexts do not count as independent annotations.

Use a primary annotator and an independent reviewer who sees RGB/context and
annotations but no candidate output, method identity, or method scores. Review
every image; adjudicate disagreements and retain both revisions. Freeze the
adjudicated annotation hash before comparing candidate predictions. Allocate
72 person-hours to annotation, 24 to independent review, 8 to adjudication and
8 to static-feature review: **112 person-hours total**. If the cap leaves images
incomplete, retain them as incomplete and stop scored comparison; do not silently
shrink the test set or replace manual review with candidate-generated labels.

Required annotation layers:

- Visible instance masks and pair-local identity for **player**, **other person**
  (official, spectator, or bench participant), and **ball**.
  Player membership is independently judged context metadata, not a capability
  assumed from the model's `person` label. Record role-uncertain instances.
- Changing-background masks independent of the instance layer, with tags for
  shadows, displays, illumination changes and uncertain motion. These can overlap
  semantics; do not count a person's shadow as part of the person's mask.
- Valid-image footprint, uncertain/ignored boundary pixels, visibility/occlusion,
  blur and tiny-ball flags. Annotate visible surfaces only; do not invent masks
  for fully occluded objects. Report absent balls and negative images too.
- Fixed static-feature audit: up to one deterministic SIFT location per occupied
  4×4 grid cell in each annotated calibration image, at most 768 locations. Order
  by response then coordinate; reviewers classify suitability for static evidence.
  Keep the frozen full SIFT feature pool for automatic coverage measurements.

Report pixel precision/recall, IoU, Dice and boundary F1 within two pixels at
960×540 for person union, ball, changing background and usable static evidence,
plus the player/other-person conditional scores below. Report one-to-one instance
precision/recall at IoU 0.5 for person union and ball. Use Hungarian matching
within those semantic classes, maximizing eligible matches then total IoU,
tie-breaking by annotation ID then prediction ID. For balls of area ≤100 pixels,
additionally report visible-ball detection recall, center error in pixels and
mask area; do not hide their failures
inside image-averaged IoU. Empty/empty cases are marked not applicable for IoU;
negative-frame false positives and missing-instance false negatives remain counted.

For player-conditioned pixel scores, compare predicted person union with player
truth while ignoring truth pixels of other people; reverse the roles for
other-person scores. Ignore role-uncertain truth pixels in both role reports,
but retain them in person-union scores. Background false positives remain counted
in both conditional reports. These measure segmentation within role-defined
evaluation domains, not player-classifier accuracy; publish the person-union
scores alongside them.

After person-union instance matching, assign each match its annotated role to
report role-specific recall and matched-mask accuracy. Let U be the number of
unmatched person predictions and TP_r the matches for role r. Their unknown role
prevents a point estimate of role-specific instance precision: publish its bounds
`[TP_r/(TP_r+U), 1]` when TP_r>0, and undefined otherwise, plus U and all role
counts. Do not allocate false positives using guessed roles or use truth labels
to improve inference-time masks.

Measure temporal consistency against independently annotated pair associations.
Match predictions to truth independently in each frame. For a truth identity
visible and matched in both frames, differing predicted IDs count as a switch.
Report missing successor matches, false births and false continuations separately
from annotated appearances/disappearances. Report successor Dice conditional on
a keyframe match alongside recall over **all** visible successor instances, so
missed keyframe detections remain visible in the results. For identities visible
in both frames, also report absolute error in predicted mask-area change divided
by the sum of the two truth areas; assign zero predicted area for a missing mask.
Stratify by visibility; unwarped overlap alone can reward a frozen incorrect mask.
Report
foreground leakage into the predicted static mask as a fraction of annotated
player/other-person/ball/changing pixels, and retained annotated-static area,
static SIFT count, occupied grid cells and retained accepted-map observations.
Report model semantic masks and final static masks separately to expose motion
filter effects. Stratify every relevant score by occlusion, blur, tiny ball,
stationary people, spectators, shadows and changing displays; mark missing strata
unverified rather than manufacturing examples or changing the data selection.

Use paired differences on identical RGB/annotation items, camera-balanced means
and per-camera worst cases. Pool pixel/instance numerators and denominators over
scored images within each camera and class before computing its score; average
defined camera scores with equal weight and disclose undefined cases. Within
each branch/role report, bootstrap camera IDs
with replacement, then temporal groups within each sampled camera, keeping the
original camera/group counts. Groups are connected components of scored frame
IDs under adjacency by one frame: reconstruction has `[0,1]`, `[5,6]`, `[10,11]`,
`[15,16]`, `[20,21,22,23,24,25,26]`, `[30,31]`, `[35,36]`, `[40,41]`, `[45,46]`;
calibration annotation timestamps are singleton groups within their respective
roles. Keep all overlapping pair contexts in their shared group. Use 10,000
resamples, NumPy PCG64 seed 0, ascending IDs and identical draws across methods;
report 2.5/97.5 percentile intervals with linear quantile interpolation. Also
publish raw numerators, denominators and counts. No new mask quality pass
threshold is inferred from historical semantic-area sanity checks.

## 4. Adapter contracts and coordinate validation

Every output has `schema`, component ID/revision, config hash, source RGB hash,
camera/frame IDs, role, branch, dimensions, valid-footprint hash, output hash and
transform metadata. Arrays are non-pickled numeric NPZ/NPY, with JSON sidecars.
Write fresh output directories exclusively; partial results have incomplete
status and cannot be consumed as passing evidence.

| Interface | Exact exported contract |
| --- | --- |
| Static calibration mask | `camera{c}-frame{f}-static.png`, uint8 `[540,960]`, values only 0/255; **255 = usable static evidence**. Same distorted area-resized grid as calibration PNG. Construct as valid footprint AND NOT (person OR ball OR changing region). No alpha channel, implicit crop, or inversion. |
| Semantic instances | `camera{c}/pair{t}/frame{f}-instances.npy`, int32 `[540,960]`; 0 background, positive pair-local instance IDs, -1 outside valid footprint. Sidecar maps every positive ID to `person` or `basketball`, retaining native class/token/score and optional role metadata. One instance has one semantic class; unresolved phrases are explicit failures/unknowns, not silently static. |
| Identity | Namespace is `(camera_id,pair_start,instance_id)`. Stable across the pair where tracking supports it; never stable by numerical coincidence across cameras or pairs. Preserve births, disappearances and unresolved associations. Cross-camera person crops use coarse correspondence votes and geometry, not equality of local integers. |
| Changing region | Boolean `[540,960]` NPY for each calibration snapshot and reconstruction pair/frame, true = changing/excluded. Store method parameters, context frame IDs, role and state hash. Retain shadow/unknown labels separately if the algorithm provides them. |
| Depth | `camera{c}-frame{f}-depth.npz`: float32 `depth[540,960]` camera-z in metres, boolean `valid[540,960]`; invalid values are NaN and `valid=false`. Record any native zero/negative/clamped values before conversion. Optional float32 `confidence` with matching shape, meaning, direction and calibration status; omit when absent. Preserve canonical/raw depth as a diagnostic artifact. |

Before a legacy consumer sees int32 instance arrays, validate its supported
range and invalid-value handling. Do not cast to uint8 and wrap IDs. Geometry
workers must use the valid footprint and reject -1 samples. Current legacy
semantics are `person`/`basketball`; richer player/other-person classes must be
mapped deliberately without losing the richer evaluation metadata.

Pixel coordinates use **OpenCV integer centers** in array adapters. The accepted
calibration exports `K_cv` with principal points 0.5 below `parameters_colmap`.
For a pixel-center-preserving resize, `u' = sx*(u+0.5)-0.5`; thus
`fx'=sx*fx`, `cx'=sx*(cx+0.5)-0.5`, and similarly for y. Subtract crop origins
and add padding offsets. These transformations change K, not metric depth values.
Record upstream-specific resize conventions rather than applying a second
half-pixel correction to their already transformed K.

The scale grid undistorts SIMPLE_RADIAL images to the existing accepted focal
and `(480,270)`. Reconstruction RGB instead preserves its OpenCV K (typically
`(479.5,269.5)` here), while the renderer/RoMa coordinates add 0.5. These grids
must never be interchanged by shape alone. Use nearest-neighbor mapping for
labels/validity, the frozen RGB remap for images, and validity-aware bilinear
mapping for depth. Require all contributing source depth samples valid at a
bilinear interpolation location; do not interpolate through invalid padding.
At sparse sample UVs retain the existing `cv2.remap(..., INTER_LINEAR)` kernel;
reject a sample if any nonzero-weight contributor is invalid. Apply this common
adapter validation to every D arm and report any D0 invalid-support differences
from its historical evaluator. For fully valid depth fields the sampling path
is unchanged. Existing static-mask clearance, sample UVs, scale estimator and
acceptance thresholds stay frozen.

Depth-specific conversion is prescribed in the [study](../vipe-alternatives.md):
D1 uses official camera-aware inference; D2 uses processed focal/300 exactly
once; D3 uses resized fx/1000 exactly once; D4 supplies input fx and lets native
inverse-depth conversion run. D2 uses the K returned by its input processor,
not a pose head or invented camera. Never infer depth type from an array's name.
If a future backend emits ray range `r`, convert with
`z = r / norm(inv(K) @ [u,v,1])` for a ray whose z component is 1. Inverse or
relative depth without a documented metric conversion is ineligible.

Qualification fixtures must cover identity resize, nonuniform resize, off-center
K, crop/pad restoration, radial undistortion, the two half-pixel conventions,
flat known-z planes, off-axis ray range, invalid borders, overlapping masks,
missing semantics, >255 IDs, and pair resets. Scale camera translations and XYZ
together in a synthetic fixture and verify unchanged projection. Use independently
computed float64 geometric references (≤1e-6 pixels for analytic transforms;
≤1e-3 pixels for OpenCV float remap-coordinate comparisons). These are proposed
adapter numeric tolerances, not changes to scientific acceptance gates.

## 5. Frozen configurations

Use the [study's source/asset pins](../vipe-alternatives.md#6-source-and-asset-pins)
and seed 0. Every row is one configuration, with **no threshold sweep, alternate
checkpoint, input tiling, prompt search, test-time augmentation, quantization or
compilation search**. Use batch size 1. Cap live instance count at 255; if a
candidate exceeds capacity, record an incomplete/failing sample rather than
silently dropping objects. This is an execution limit, not a truth-label cap.

| ID | Exact model/algorithm settings |
| --- | --- |
| S0 | Pinned ViPE historical Grounding DINO/SAM-B/R50-DeAOTL calls, float32, phrases `['person','basketball']`, box threshold 0.35; effective fork phrase assignment and reset behavior described in the study. Reproduce existing invocation behavior through a diagnostic worker; keep historical source unchanged. |
| S1 | Direct upstream SAM-Track/SAM-B/R50-DeAOTL with the same historical checkpoint bytes; caption `person.basketball.`, box 0.35, nominal text 0.5, SAM gap 10, 255-object limit, historical new-object/automatic-mask area 200. Preserve box-prompted first-frame behavior and propagate exactly one successor. Float32. Record differences from S0, including effective phrase assignment, preprocessing and overlap order. |
| S2 | Native Grounding DINO Swin-T OGC, caption `person.basketball.`, box threshold 0.35, text threshold 0.25; native 800/max-1333 preprocessing, float32. SAM 2.1 Hiera-L, `sam2.1_hiera_l.yaml`, 1024², bfloat16 autocast, no compilation, default supplied postprocessing recorded. Choose highest predicted-IoU mask for each keyframe box; propagate to the successor using the video predictor with fresh pair state. No successor detector rerun. |
| S3 | Original SAM 3 `sam3.pt`, original image/video builders (not the 3.1 multiplex builder), 1008², bfloat16, no compilation, confidence threshold 0.5. Issue `person` and `basketball` concept prompts separately; union for calibration exclusion and merge instances deterministically for reconstruction. Fresh video session for each two-frame pair; native detector/tracker births allowed and recorded. No examples, clicks, MLLM agent or manual inference correction. |
| S4 | `PekingU/rtdetr_v2_r50vd` snapshot from the study, `RTDetrImageProcessor` and `RTDetrV2ForObjectDetection`, float32, 640² RGB, rescale 1/255, no mean/std normalization. Keep `person`/`sports ball` by model label names at score ≥0.35; map sports ball to `basketball`. Exactly S2's SAM checkpoint, precision, box prompting and pair policy. |
| D0 | Historical ViPE UniDepth2Model type `l`; float32 invocation and bilinear interpolation, original source/weights/runtime. |
| D1 | Official `UniDepthV2` ViT-L, historical snapshot/serialization, byte RGB NCHW, supplied pinhole K, bilinear, checkpoint-default pixel bounds/resolution policy (no resolution-level override), float32 invocation. Save actual internal processing dimensions. |
| D2 | `DA3METRIC-LARGE`, `process_res=504`, `process_res_method='upper_bound_resize'`, ImageNet normalization, batch of one image, native bfloat16 inference. No input extrinsics, no pose-scale alignment, `infer_gs=false`, no export that requires predicted cameras. Compute processed-K focal/300 scaling once and restore output grid; retain raw depth and actual processed K. |
| D3 | `metric3d_vit_large` with `metric_depth_vit_large_800k.pth` and `vit.raft5.large.py`; float32, fit/pad to H=616/W=1064, RGB mean `[123.675,116.28,103.53]`, std `[58.395,57.12,57.375]`. Native hub de-canonicalization using resized fx/1000. Record native [0,300] metre clamp and saturated fraction; no percentile clipping. |
| D4 | Apple native `depth_pro.pt`, float32, official transform and internal 1536² inference. Supply accepted input fx as a float32 device tensor to `f_px`; native output restore/inversion, no extra focal multiplication. Record native inverse-depth clamp saturation; confidence omitted. |
| M0 | For calibration frame f, compare f+1 except at role end where f−1 is used. For reconstruction, compare t and t+1. RGB→grayscale, `absdiff>20`, one 9×9 all-ones dilation. Same pair-changing mask for both members of an M0 reconstruction pair. |
| M1 | For each target f in role [lo,hi], let `a=max(lo,min(f-4,hi-8))`; context is all nine frames a…a+8. Pixelwise median of grayscale values; `abs(gray_f-median)>20`, one 9×9 dilation. Compute both pair members separately; exclude the union of their changing masks when checking pair-static evidence. |
| M2 | OpenCV MOG2 per camera and role, history=50, varThreshold=16, detectShadows=true, learningRate=0.02. Reset at each role start; process every frame chronologically once. Classify output 127 and 255 as excluded, then one 9×9 dilation. Retain cold-start behavior in scores; no hidden warmup or reuse of final-window state. For pair-static evidence use the union of both members. |
| N0 | Current raw shared-track count, descending; exact tie by lower physical camera ID. Positive overlap only; three neighbors required. |
| N1 | Jaccard co-visibility on the same track sets; descending J, then raw shared count, then lower camera ID. Positive overlap only; three neighbors required. |
| N2 | Greedy coverage/parallax selection defined immediately below, three iterations and deterministic ties. No learned or image-adaptive neighbor scoring. |

S2/S4 map native mask logits to the original grid before thresholding at zero.
For overlapping instances, choose the greatest mask logit; exact ties use detector
score, then stable detector index. S3 uses its returned mask scores, with ties by
semantic name then native ID; retain suppressed overlap pixels in diagnostics.
S0/S1 retain their native merge policy as part of the control. Object IDs are
allocated deterministically and persist across a pair; separately evaluate
semantic union accuracy so arbitrary numeric ID choices do not affect it.

**N2 definition.** For each camera c, T_c is the set of unique sparse point IDs
observed by that training camera. For candidate o, start from their intersection.
Project these points into the fixed processed pinhole grids; eligible support
must have finite positive depths, be inside both valid image footprints and have
ray angle ≥1°. Do not reject based on new depth predictions. Empty support
disqualifies that edge for N2. Grid indices are `floor(u/240), floor(v/135)` in
OpenCV coordinates for a 4×4 grid. At each greedy step maximize this tuple:

```text
(new occupied reference cells,
 number of shared point IDs not already covered by selected neighbors,
 occupied candidate-image cells,
 median sin(ray_angle) over eligible common points,
 Jaccard(T_c,T_o), raw shared-track count,
 -physical_camera_id)
```

Use float64 geometry, angles in [0,π], score rounding to 12 decimals before
comparison, and ascending point IDs. Update covered reference cells/point IDs
after each choice. Fail a reference with fewer than three eligible neighbors;
do not backfill with a zero-overlap or held-out camera. This is a proposed ranking
heuristic; its ≥1° eligibility does not replace downstream triangulation gates.

### Runtime proposal and qualification scope

Target Ubuntu on one RTX 4090. No installation or host GPU probe was run in this
study. New environments are isolated; do not downgrade or mutate historical ones.
The exact full dependency/wheel lock must be saved before model admission.
The following runtime targets remove ambiguity about the intended attempt while
remaining explicitly **unqualified proposals**:

| Environment | Configuration scope | Target Python / torch / torchvision / CUDA wheel; notable pins |
| --- | --- | --- |
| E0 existing ViPE | S0, D0 | Existing Python 3.14 / 2.13.0+cu130 / 0.28.0+cu130; verify historical runtime/source hashes. |
| E1 standalone legacy | S1 | Python 3.11 / torch 2.5.1+cu124 / torchvision 0.20.1+cu124; NumPy 1.26.4. Exact DeAOT native extensions and remaining packages resolved once. |
| E2 SAM 2 detector adapters | S2, S4 | Python 3.11 / torch 2.5.1+cu124 / torchvision 0.20.1+cu124; NumPy 1.26.4; Transformers 4.51.3 for S4. Grounding DINO and SAM source pins from study; record CUDA extension build. |
| E3 SAM 3 | S3 | Python 3.12 / torch 2.10.0+cu128 / torchvision 0.25.0+cu128; NumPy 1.26.4. No FlashAttention-3 or multiplex acceleration. Use core inference imports and explicitly recorded required extras. |
| E4 UniDepth | D1 | Python 3.11 / torch 2.5.1+cu124 / torchvision 0.20.1+cu124; NumPy 2.1.3, xFormers 0.0.28.post3. |
| E5 DA3 metric | D2 | Python 3.11 / torch 2.5.1+cu124 / torchvision 0.20.1+cu124; NumPy 1.26.4, xFormers 0.0.28.post3. Include default package dependencies in license inventory; no app/gs extras. |
| E6 Metric3D | D3 | Python 3.10 / torch 2.0.1+cu118 / torchvision 0.15.2+cu118; NumPy 1.23.1, xFormers 0.0.21. Pin resolved MMCV/config dependencies before admission. |
| E7 Depth Pro | D4 | Python 3.11 / torch 2.5.1+cu124 / torchvision 0.20.1+cu124; NumPy 1.26.4; record timm and image/codec packages. |
| E8 existing geometry | All diagnostic geometry | Existing hash-verified RoMa/geometry environment and runtime; no changes to matcher weights, native kernels, solver, calibration or normalization. |

The proposed torch/torchvision/CUDA combinations follow the
[official wheel matrix](https://pytorch.org/get-started/previous-versions/).
Transformers 4.51.3 documents the selected
[RT-DETRv2 API](https://huggingface.co/docs/transformers/v4.51.3/en/model_doc/rt_detr_v2).
These upstream interfaces do not establish compatibility of a full candidate
environment; that is the bounded setup attempt's purpose.

There are at most seven new environment builds, one attempt each, serially,
within **16 hours total setup wall time**. Setup includes dependency resolution,
asset verification and imports, with no model inference. If a target dependency
combination fails, save the resolver/build error and mark the candidate blocked;
no silent version upgrade, CPU fallback, smaller model or second build attempt.
Exact resolved non-model dependencies, imported modules and native libraries
must be inventoried before claiming either optional license preference. This
qualification requirement is especially material for the old Metric3D stack,
SAM 3's metadata discrepancies and DA3's broad dependency list.

## 6. Scale evaluation and physical references

Prepare one immutable sample manifest from the existing accepted map, static
masks and training-camera frame-100/frame-175 inputs. Preserve point IDs, UV,
camera-z, valid footprints and hashes. All D arms receive the same inputs and
support; confidence scores are reported but **not used to drop samples, change
camera weights or relax gates**. A candidate's invalid samples reduce its own
support, not the shared manifest or another candidate's sample set.

For each camera c, compute `m_c=median(log(z_model/z_map))` on valid eligible
samples, then `s=exp(median_c(m_c))`. One camera has one vote. Preserve the
current [scale_statistics implementation](../../../scripts/basketball_scale.py)
and the complete [scale configuration](../../../configs/basketball-rev2/scale.json):

| Gate | Required value |
| --- | --- |
| Training map support per eligible point | At least 3 cameras and ≥1° map parallax |
| Static-mask clearance / spatial deduplication | At least 8 pixels / 2-pixel cells, stable point-ID order |
| Per-camera valid scale samples / occupied grid cells | At least 100 / at least 6 of 16 |
| Positive finite depth fraction over valid image footprint | At least 0.99 |
| Within-camera median absolute deviation in log ratios | At most 0.25 |
| Each camera median scale deviation from global/frozen scale | At most 0.25 relative |
| Camera bootstrap | Seed 0, 10,000 resamples; 95% relative halfwidth at most 0.10 |
| Frame-175 diagnostic global scale vs frozen frame-100 scale | At most 0.10 relative disagreement |

Fit only frame 100, freeze the scale result/config hash, and check that unchanged
scale at frame 175 only for models passing fitting. Preserve camera deviations
against the frozen fit as well as the diagnostic window scale. A failed camera
is not dropped. There is no per-camera scale, affine shift, focal adjustment,
geometric refit or frame-175 refit.

Publish all preregistered D arms descriptively. D1 is the preselected depth for
the primary/fallback combined stacks; D2 is preselected for the commercial-use
option. Frame 175 does not select a different depth model or authorize a second
winner after failure. A failed D1/D2 freezes its dependent combined arm as
ineligible; it does not trigger a substitution from D3/D4. Any subsequent model
selection needs its own evidence protocol without rebranding frame 175 as new.

If independent distances already exist, preregister endpoint correspondence,
measurement source, units, uncertainties and fit/check assignment before model
results. A minimal conditional test has two fitting distances and a third
independent checking distance. Fit `s_measured=median(d_measured/d_map)` and
propagate endpoint/measurement uncertainty with seed-0 resampling. This separate
anchor must not replace or relax the learned-depth gates in the D comparison.
Report absolute/relative physical errors only on independent checking references.
No new survey, guessed court dimensions or inferred ball size is allocated here.
With insufficient measurements, mark physical accuracy **unverified** and report
camera/frame repeatability plus unresolved common metric bias.

## 7. Comparison order, geometry and finalist selection

Run in this order after admission; record skipped/ineligible arms without
replacing them. Complete technically valid preregistered arms regardless of
intermediate visual quality, within their individual and total caps.

1. Generate S0–S4 calibration/paired masks. Run contract checks on each first
   result before continuing that same job. Compare S1/S0 intermediate outputs,
   not only final unions. Geometry later uses a common freshly evaluated reference
   under the same harness; old pilot scores are historical context, not matched
   new baseline measurements.
2. Run M0–M2 CPU changing masks with S0 semantics held fixed. Score all S arms
   with M0 and all M arms with S0. Freeze mask/annotation metrics and raw outputs.
   Do not alter segmentation and motion thresholds together.
3. Run D0–D4 frame-100 inference/evaluation; freeze every passing fit, then run
   its frame-175 check. Masks, sample UVs and geometry stay fixed.
4. Compute N0–N2 from the same static map. Evaluate five geometry arms
   `(S_i,D0,M0,N0)` for i=0…4, two additional motion arms `(S0,D0,M_j,N0)`
   for j=1,2, and two neighbor arms `(S0,D0,M0,N_k)` for k=1,2. The shared
   `(S0,D0,M0,N0)` result is reused as baseline: **nine geometry arms total**.
5. Freeze S*, M*, N* and the combined-arm manifest before combined runs. Run
   the four person-cropped arms below, then produce the report and stop.

All nine isolated geometry arms use **coarse** RoMa matching with 5,000 samples
per directed neighbor edge, 15,000 per reference context; seed 0 and identical
canonical loop order. No candidate receives a different point budget. Preserve
the source's semantic sampling rule (half budget shared across `person`
instances, remaining samples from other usable locations). Record any shortage
instead of duplicating samples. Ball-specific quotas would be a different
experiment and are not allocated.

Use the existing positive-depth, reprojection, parallax, semantic support, LK
round-trip ≤1-pixel and three-camera velocity gates. Keep unsupported motion
flagged, even when its stored initialization velocity is zero. Preserve the
local numerical solver's rank screening and keep numerical validity distinct
from geometric acceptance. The existing LK settings are a 31×31 window, pyramid
maxLevel=3, and at most 30 iterations with epsilon 0.01. Log all rejected stages
separately.

For each reference camera/pair/neighbor, report raw and normalized overlap,
4×4 occupied cells in both images, union and marginal coverage over the three
neighbors, min/median/p95 parallax, attempted/accepted triangulations by class,
distinct supporting cameras, velocity-valid fraction and spatial distribution.
Include zero-support/fewer-than-three-neighbor failures. Report synchronized
CUDA time, total wall time, peak allocated/reserved/device memory, full-image
and crop match counts and input/output bytes. Report reciprocal-pair duplication
and potential cache reuse, but disable result caching across arms for timing.

**Deterministic finalist rule.** These are selection rules, not new scientific
quality thresholds. On calibration selection annotations, rank S1–S4 by largest
minimum of person-union Dice and ball Dice, then lowest foreground leakage into
static evidence, then largest retained static-feature fraction, then largest
boundary F1, then ID. Rank M0–M2 with S0 fixed by largest annotated usable-static
Dice, then lowest foreground leakage, then retained static-feature fraction,
then ID. Aggregate with equal camera weight. Round scores to 12 decimals before
ties; lower IDs win final ties. Reconstruction diagnostics reveal weaknesses
but do not retune these settings. If selection lacks either required semantic
class, S* defaults to the predeclared S2 and its quality selection is marked
unverified; this does not establish superiority.

Rank eligible N0–N2 on the fixed coarse diagnostic set by greatest mean union
of occupied reference cells among accepted foreground points, then accepted
foreground fraction, then lowest matching wall time, then ID. Publish ball and
person results separately even though selection pools foreground. This ranking
does not establish physical correctness of the triangulated points. A method
without three usable neighbors for every tested reference is ineligible.

| Combined arm | Exact composition | Comparison purpose |
| --- | --- | --- |
| C0 | S0 + D0 + M0 + N0 | Fresh reference under the same person-cropped matcher settings as C1–C3. |
| C1 | S* + D1 + M* + N* | Primary quality finalist; the study's initial hypothesis is S2/D1. D1 must pass its own scale fit/check. |
| C2 | S4 + D2 + M* + N* | Predeclared commercial-use/non-AGPL option, conditional on exact asset/dependency evidence and scale gates. |
| C3 | S1 + D1 + M0 + N0 | Dependency-removal fallback with historical motion/neighbors. |

All combined arms use the same current person-crop policy: coarse-match votes
associate view-local person instances; boxes expand by 10% with minimum two
pixels, clipped to image bounds; crop transforms map matches back exactly.
They do not equate cross-camera integer IDs, crop balls as people, or exclude
spectators using ground truth. Record voted alternatives, selected associations,
crop boxes and changes to correspondence coverage. Permit at most one crop
refinement per reference person per directed edge, hence at most 255, with
overflow recorded as failure. Add no new crop heuristic or matcher fine-tuning.

For each combined depth scale, create a fresh diagnostic scene freeze and scale
camera translations, centers and XYZ consistently. Derive normalization so the
same physical-to-normalized mapping is used; do not apply the old normalization
matrix to newly scaled XYZ unchanged. Publish the transforms and projection
invariance checks. C2's scale may change physical units without changing normalized
geometry. Combined metrics do not isolate interactions; attribute component
effects only using the independent arms above.

If an arm fails a required scale/license/contract gate, skip dependent work and
report the precise reason. Do not swap D3/D4 into its slot or call an incomplete
arm a winner. If S*, M* or N* lacks eligible evidence, use no data-dependent
replacement except the explicit missing-class S2 rule; record combined selection
blocked. Identical combined configurations may reuse one result, with the saved
hash and no additional attempts. They cannot spend the saved time elsewhere.

## 8. Bounded future execution proposal

The following JSON is a machine-readable scheduling specification embedded in
this document. `attempts` counts process-level jobs, not individual images;
`seconds_each` is a hard wall limit including loading, qualification, inference,
serialization and cleanup. One process group may use the GPU at a time. All
failures consume their attempt and elapsed allocation. The sum is **36 GPU jobs
and 26 GPU-supervised hours**, with no unallocated retry pool.

```json
{
  "schema": "vipe-alternatives-benchmark/v1",
  "scene": "Basketball_dg",
  "seed": 0,
  "held_out_cameras": [0, 10, 20, 30],
  "fit_snapshots": [50, 62, 75, 87, 99, 100, 112, 125, 137, 149],
  "selection_snapshots": [150, 162, 175, 187, 199],
  "validation_history_snapshots": [200, 212, 225, 237, 249],
  "scale_fit_frame": 100,
  "scale_check_frame": 175,
  "pair_starts": [0, 5, 10, 15, 20, 21, 22, 23, 24, 25, 30, 35, 40, 45],
  "diagnostic_cameras": [1, 6, 11, 16, 21, 26, 31, 33],
  "diagnostic_pair_starts": [0, 20, 21, 22, 23, 24, 25, 45],
  "annotation_calibration_cameras": [0, 1, 10, 11, 20, 21, 30, 31],
  "annotation_calibration_frames": [50, 100, 149, 150, 175, 199],
  "neighbors_per_reference": 3,
  "samples_per_neighbor": 5000,
  "gpu_concurrency": 1,
  "gpu_peak_device_gib_limit": 22,
  "gpu_total_seconds_limit": 93600,
  "gpu_jobs": [
    {"scope": "S0-S4 calibration", "attempts": 5, "seconds_each": 3600},
    {"scope": "S0-S4 reconstruction pairs", "attempts": 5, "seconds_each": 5400},
    {"scope": "D0-D4 frame100 fit", "attempts": 5, "seconds_each": 900},
    {"scope": "D0-D4 frame175 check if fit passes", "attempts": 5, "seconds_each": 900},
    {"scope": "five segmentation geometry arms", "attempts": 5, "seconds_each": 1800},
    {"scope": "two additional motion geometry arms", "attempts": 2, "seconds_each": 1800},
    {"scope": "two additional neighbor geometry arms", "attempts": 2, "seconds_each": 1800},
    {"scope": "C0-C3 combined cropped geometry", "attempts": 4, "seconds_each": 5400},
    {"scope": "R-S R-D R-G repeats", "attempts": 3, "seconds_each": 600}
  ],
  "cpu_motion_jobs": {"attempts": 3, "seconds_each": 1800},
  "cpu_neighbor_jobs": {"attempts": 3, "seconds_each": 300},
  "cpu_prepare_score_report_seconds_limit": 57600,
  "cpu_max_workers": 8,
  "environment_builds_limit": 7,
  "setup_wall_seconds_limit": 57600,
  "annotation_person_hours_limit": 112,
  "new_download_gib_limit": 60,
  "new_artifact_disk_gib_limit": 150,
  "calibration_runs": 0,
  "training_updates": 0,
  "new_final_window_evaluations": 0
}
```

The GPU memory limit is a **proposed stopping ceiling**, not a measured model
requirement or a guarantee against allocation failure. Measure total device
usage, not only PyTorch allocated bytes. Stop the worker if usage exceeds 22 GiB
or the device cannot be used exclusively; do not evict another user's process.
An OOM ends that attempt; unused time does not authorize a reduced-resolution run.

The three repeat jobs are fixed: **R-S**, S1 on camera 1 pair 20/21 in a fresh
process; **R-D**, D1 on camera 1 frame 100 in a fresh process; **R-G**, the coarse
S0/D0/M0/N0 geometry reference for camera 1 pair 20/21 and its three neighbors.
Compare against saved primary-run outputs, reporting per-pixel disagreement,
depth differences/scale-ratio differences and geometry acceptance changes.
Run each after its source result exists. They are not extra model-selection
attempts, GPU warmup loops or whole-matrix reruns.

Maximum scored primary mask outputs are 5 × (510 calibration + 840 paired
contexts) = **6,750 rows**, with pair contexts grouped for statistics. Depth
outputs are at most **300** (150 fitting, at most 150 frozen checking), yielding
at most ten full-rig scale evaluations. Isolated geometry uses 9 × 192 = **1,728
full-image matches**; combined geometry uses another **768**, plus at most
**195,840 person-crop refinements**. R-G adds exactly three full-image matches;
R-S adds two mask outputs and R-D one depth output. The crop ceiling is a worst
case, not an expected count or permission to exceed time/storage caps. Stop on
the first limit reached, and retain partial counts rather than claiming completion.

CPU motion jobs cover M0/M1/M2 once; neighbor jobs produce N0/N1/N2 once.
The 16-hour CPU preparation/scoring/reporting limit is a separate cumulative
wall allowance, at most eight workers, with one preparation, one annotation
import/check, one metric aggregation and one report pass. Pure syntax/schema
checks before admission are part of implementation, not extra model experiments.
The 16-hour setup allowance, 112 person-hour annotation allowance, 26-hour GPU
allowance and CPU allowances are separate scopes; none can fund extra attempts
or compensate for an exhausted scope. Download/disk caps cover all new candidate
environments/assets/results; preserve existing artifacts instead of deleting them
to fit. Missing data/access/annotations or inadequate free space blocks admission
to the affected stage.

## 9. Future implementation, admission and artifact checklist

The future implementation should add new adapters and an experiment-scoped
runner; the present repository commands are historical interfaces, not a ready
execution command for this matrix. Before launching a model job, complete:

1. A decoder/diagnostic loader with exact manifest membership checks, role-bound
   motion contexts, valid-footprint handling, and pair-specific output paths.
   Assert all camera/frame counts from the embedded JSON and reject held-out
   reconstruction cameras and final-window image access.
2. Segmentation and depth workers implementing the contracts above, plus a
   component-provenance schema and dependency/license inventory. Keep historical
   model/data files read-only. Make ViPE source access fail deliberately in tests
   of S1–S4/D1–D4, while allowing S0/D0 reference workers explicitly.
3. A neutral scale worker using the frozen input samples, existing estimator and
   exact gates; a neighbor worker with hand-computable count/Jaccard/coverage
   fixtures, deterministic ties and exactly-three-or-failure behavior; geometry
   and crop adapters preserving the current numerical and semantic gates.
4. A supervisor that enforces per-job/global wall limits, attempts, one-GPU
   concurrency, memory/disk limits and process-group cleanup. The existing
   [basketball_study supervisor](../../../scripts/basketball_study.py) explicitly
   has no total deadline, so it cannot be used unchanged to enforce this budget.
   Record worker PID/process group, invocation, environment lock and monotonic
   start/finish; terminate on interruption/limit, then force-stop remaining child
   work within 30 seconds. Cleanup time is charged within the cap.
5. Independent annotations and review evidence, schema/geometric fixture results,
   source/model snapshots plus local asset hashes, accepted calibration/map and
   historical-evidence hashes, complete exposure history, actual runtime/device
   and available resources. A metadata pin is not proof of a downloaded file's
   content. Never accept custom/gated asset terms on the user's behalf merely to
   make an arm runnable.

Save artifacts under a fresh `.local/vipe-alternatives/{run-id}/`, with a compact
report under `docs/research/vipe-alternatives/{run-id}/`. Required records are
`admission.json`, `inputs.json`, `exposure-history.json`, `components.json`,
`annotations.json`, append-only `ledger.jsonl`, per-arm `config.json`,
`result.json`, logs, output hashes, mask/scale/neighbor metrics, `finalists.json`,
fresh combined freezes and `assessment.md`. Every planned arm must be accounted
for as complete, failed, blocked or skipped with a reason. Keep old calibration
and validation-consumption records unchanged; link them as historical parents.

Admission records the saved protocol/config hash, authorized allocation scope,
remaining applicable user ceilings and implementation validation. Plan 030 does
not itself start this future run or a continuous-improvement loop. Where a later
authorized plan is covered by repository standing execution-budget approval,
record that basis without asking for routine approval again.

During execution, apply the repository's permission retry/stop policy, stop on
user interruption, and stop on staging/commit failure. Do not replace a denied
network or GPU operation with a different path to the same restricted resource.
Do not use unavailable model results, stale masks or incomplete annotations as
successful evidence. No automatic new allocation, extra method, second finalist
or rewritten historical record is permitted on exhaustion.

## 10. Reporting and acceptance

Documentation acceptance requires traceable source/license claims, all three
workflow boundaries, explicit interfaces, data history, preserved scale gates,
exact algorithms and consistent limits. Validation of this specification does
not mean any candidate passed the future benchmark.

For a future run, report the complete paired mask/motion/scale/neighbor matrices
and all four combined slots, including ineligible entries. Distinguish:

- **Dependency removal:** new eligible workers import/access no ViPE code and
  carry complete component provenance; control deviations are quantified.
- **Engineering qualification:** interfaces, runtime, budget and historical
  artifact guards pass. This alone says nothing about output quality.
- **Measured quality evidence:** class/stratum scores and paired uncertainty,
  leakage/static support, temporal identity and accepted geometry/coverage/cost.
  Claim improvement only for named metrics with supporting paired evidence;
  disclose regressions. An interval spanning zero is inconclusive, not a win.
- **Physical accuracy:** independently measured checking references are required.
  Passing scale repeatability gates cannot establish metric truth.
- **License preferences:** assess commercial permission and non-AGPL open-source
  licensing separately for the actual code, weights and installed dependencies.
  A technically successful research-only stack does not satisfy those preferences.

End the proposed run after its report or a required stop, even if no replacement
is better. Keep the archived reference usable; improvement hypotheses remain
unverified wherever the allocated comparison cannot resolve them.
