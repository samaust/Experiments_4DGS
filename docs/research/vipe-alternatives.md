# ViPE alternatives for Basketball calibration, scale, and initialization

Study date: 2026-09-12. Implements [Plan 030](../../plans/plan_030.md).
Repository source inspected at `35dc5016ea67d44f5845095240e9f53a42d7a059`.
The companion [benchmark protocol](vipe-alternatives/benchmark-protocol.md)
defines future experiments; **no model installation, inference, calibration,
annotation campaign, or training was performed for this study**. Upstream source,
release documentation, license text, and public model metadata were inspected.

The recommended first migration is **Grounding DINO Swin-T OGC + SAM 2.1
Hiera-L, with standalone UniDepth V2 ViT-L**. This replaces the segmentation
implementation while retaining a depth dependency-removal control. The strongest
option supported by the inspected licensing evidence for commercial use with
open-source software other than AGPL-3.0 is **RT-DETRv2-L + SAM 2.1 Hiera-L +
DA3METRIC-LARGE**, subject to the dependency qualifications below. The fallback
is the standalone historical segmentation stack plus standalone UniDepth V2.
These are engineering recommendations, not measured Basketball winners.

Expected improvements in ball recall, boundaries, temporal consistency, retained
static features, or dense geometry are **hypotheses pending Basketball
measurements**. License preferences are assessed separately from quality.
Neither a permissive license nor a newer checkpoint establishes better output.

## 1. What removing ViPE actually changes

The accepted workflow uses a static COLMAP reconstruction, not ViPE camera
trajectory estimation. Its current boundaries are documented in the
[workflow](../multicamera-freetimegs-workflow.md). The local ViPE checkout is
`/home/auss/git_repos/samaust/Tridi/vipe`, branch `tridi`, pinned to
`de50e6ab1066e32c96d32499a282ecaa2fbf2d90`; its historical source/weight hashes
are recorded in the [prior audit](../experiments/basketball-calibration-20260906.json).

| Boundary and source | Actual dependency and behavior | Migration implication |
| --- | --- | --- |
| Input audit: [basketball_audit.py](../../scripts/basketball_audit.py), [continuation audit](../../scripts/basketball_continuation_audit.py) | Video inventory, frame roles and hashes are local. Both also check ViPE revision/branch/cleanliness; continuation checks frozen calibration and consumed validation evidence. | Separate data provenance from component provenance. Retain membership, video, geometry and historical-evidence checks. |
| Historical [pilot](../../scripts/basketball_vipe_pilot.py) and [subset priors](../../scripts/basketball_subset_priors.py) | Pilot imports GeoCalib, `UniDepth2Model`, `DepthEstimationInput`, `TrackAnythingPipeline`, `VideoFrame`, device helpers and `vipe_ext`; hashes broad source/config/extension/weight sets. | Preserve historical replay. GeoCalib's historical focal gate is not a requirement of the accepted COLMAP route or a new depth adapter. |
| **2.1** [snapshot preparation](../../scripts/basketball_alternatives_prepare.py) | Local OpenCV decode and area resize to 960×540. ViPE supplies person/ball instance masks. A fresh tracker is created for every snapshot. Local frame difference and dilation exclude additional changing pixels. | Adapter returns semantic/instance evidence in the resized, still-distorted snapshot coordinates; local code builds the static PNG. |
| [SIFT frontend/refinement](../../scripts/basketball_alternatives_refine.py), [localization](../../scripts/basketball_alternatives_localize.py), [evaluation](../../scripts/basketball_alternatives_evaluate.py) | Consume PNG images/static masks and sparse geometry. No segmentation model is called here. | A new mask may change feature support and any subsequently regenerated map. A mask-only study must keep the accepted geometry fixed. |
| **2.5** [basketball_scale.py](../../scripts/basketball_scale.py) | Local undistortion, sparse-point support, depth sampling, robust global scale and gates; only `infer` uses ViPE's UniDepth wrapper. Runtime is explicitly pinned to Python 3.14 / torch 2.13.0+cu130 / torchvision 0.28.0+cu130 and imports `vipe_ext`. | New inference workers can use separate environments. Retain the estimator and gates; replace wrapper and broad ViPE provenance checks with a named depth component. |
| [Calibration freeze](../../scripts/basketball_alternatives_freeze.py), [packaging](../../scripts/basketball_alternatives_package.py), [reconstruction freeze](../../scripts/basketball_sync_audit.py) | Hash-bound historical paths connect calibration, selection, final validation, map, scale and source videos. Sync audit consumes fixed calibration/scale/winner paths. | A changed scale/model cannot overwrite a passing historical record. New adapters need explicit artifact inputs and fresh experiment freezes. |
| [Scene preparation](../../scripts/prepare-basketball-sync.py), [scene camera conversion](../../scripts/basketball_scene.py), [static initialization](../../scripts/initialize-basketball-sync.py) | Decode/undistort locally; multiply camera translations, centers and map XYZ by the frozen scale. RGB, manifest and initializer are hash-bound. | Regenerate dependent manifests/initializers for a changed freeze. Preserve image and camera coordinate conventions. |
| **4.2** [temporal masks](../../scripts/basketball_temporal_masks.py) | ViPE tracker and `ModelCache`; source hashes and SAM/AOT/GroundingDINO/BERT weight hashes checked. State resets at each keyframe, then tracks only its immediate successor. Local difference produces `changing.npy`. | Keep pair-local identity; include pair ID in paths because crossing diagnostics introduce overlapping pairs. Replace the source/weight allowlist with component-specific manifests. |
| [Neighbor ranking](../../scripts/basketball_temporal_neighbors.py) | Local shared sparse-track counts; descending count, then ascending physical camera ID. Chooses up to three positive-overlap cameras. | ViPE removal alone cannot improve ranking. Enforce exactly three usable neighbors or record failure; compare explicit ranking algorithms. |
| [Temporal cloud](../../scripts/basketball_temporal_cloud.py), [geometry](../../scripts/basketball_temporal_geometry.py), [fusion](../../scripts/basketball_dense_fusion.py) | RoMa matching, person crops, local numerical triangulation, semantic support, LK tracking, velocity and fusion consume masks. `track_lk` requires equal positive IDs within a pair. Cross-camera association uses coarse-match votes, not identical IDs. | Preserve mappings and rejection reasons. Ball masks do not currently receive the person-crop refinement or the person-specific sampling quota. A better mask alone does not add those capabilities. |

### Wrapper details that make the direct-component control necessary

The inspected local `vipe/priors/track_anything/__init__.py` uses
`groundingdino_swint_ogc.pth`, `sam_vit_b_01ec64.pth`, and
`R50_DeAOTL_PRE_YTB_DAV.pth`. It requests `person.basketball.`, uses box threshold
0.35, and starts with detection plus SAM; the second call propagates DeAOT
labels without detecting new arrivals. `sam_run_gap=10` does not cause another
detection in a two-frame pair. Model caching shares weights, not pair identity.

The fork's `detector.py` uses GPU tensor bilinear resizing with antialiasing and
ImageNet normalization; it selects the best phrase from token logits. Its tensor
path does not use the nominal 0.5 text threshold. Direct upstream Grounding DINO
uses a PIL-oriented transform and thresholded token phrases in
[inference.py](https://github.com/IDEA-Research/GroundingDINO/blob/856dde20aee659246248e20734ef9ba5214f5e44/groundingdino/util/inference.py).
The same weight file therefore does not imply identical boxes or classes.
The wrapper's 200-pixel new-object/automatic-mask settings are also **not a
universal minimum area for first-frame box-prompted masks**: the inspected
`SegTracker.detect_and_seg` calls the box segmenter directly. Small-ball loss
must be measured at detection, segmentation and propagation separately.

The local `vipe/priors/depth/unidepth/__init__.py` sets bilinear interpolation,
converts RGB float `[0,1]` to byte NCHW, and reconstructs K using only `fx`, with
`fy=fx`, `cx=W/2`, `cy=H/2`. It ignores supplied `fy,cx,cy`. Consequently the
existing scale preparation deliberately undistorts to `(cx,cy)=(480,270)`.
The control must match that preprocessing before testing support for arbitrary
accepted intrinsics. Read-only source inspection does not establish numerical
equivalence of the fork and upstream UniDepth.

### Existing Basketball evidence and its limits

The accepted [calibration validation](../experiments/basketball-calibration-alternatives/validation.json)
passed all 34 cameras, but evaluated established static tracks. It is neither a
mask annotation benchmark nor independent metric ground truth. The saved
[scale fit](../experiments/basketball-rev2/scale-fit.json) is
1.315069470778244 estimated metres per map unit, with a camera-bootstrap 95%
interval approximately [1.29961, 1.33332]. The
[frame-175 check](../experiments/basketball-rev2/scale-selection.json) disagrees
by 3.13%. Common monocular metric bias remains unresolved.

The [dense pilot review](../experiments/basketball-dense-temporal/pilot-review.md)
records spectators in person masks, large false-positive ball masks, detached
foreground fragments and smearing. Its 769 ball-labeled cropped-pilot
observations were not 769 verified ball points. These findings justify the
class-specific benchmark; they do not isolate segmentation as the cause.
Historical [crossing diagnostics](../../scripts/basketball_dense_crossing_audit.py)
and [Plan 028](../../plans/plan_028.md) also studied lifetime and training-time
coverage. Replacing ViPE is not a demonstrated repair for those defects.

## 2. Segmentation candidates for steps 2.1 and 4.2

The rows specify released variants, not interchangeable family names. Runtime
choices in the protocol are proposals until qualification; published GPU figures
are not RTX 4090 end-to-end guarantees. Peak VRAM is **unreported for this exact
Basketball workload** unless a local historical measurement is explicitly cited.

| Candidate | Released variants and selected comparison | Published evidence and reported resources | Runtime, preprocessing and integration |
| --- | --- | --- | --- |
| **S0 reference / S1 standalone historical stack** | Grounding DINO Swin-T OGC + SAM ViT-B + R50-DeAOTL PRE_YTB_DAV. Upstream also releases SAM ViT-L/H and other DeAOT backbones; they are outside the comparison. [SAM-Track release documentation](https://github.com/z-x-yang/Segment-and-Track-Anything/blob/99ca4bd5074a6ed62db4664285073ab669503926/README.md). | Historical Basketball outputs exist; independently annotated mask scores do not. Upstream reports roughly 16 GB for up to 255 objects, without matching this clip's settings. | Upstream reports Python 3.9, torch 1.10 / torchvision 0.11 testing; those old CUDA wheels are not a qualified 4090 environment. S1 proposes a separate modern CUDA environment and exact historical weights. Medium effort: replace ViPE data/device wrappers and compare tensor/PIL processing, mask merge order and DeAOT state. AGPL remains. |
| **S2 Grounding DINO + SAM 2.1** | Detector: Swin-T OGC; Swin-B COGCOOR is a released larger option, not an extra arm. SAM 2.1 releases Hiera tiny, small, base-plus, large; choose `sam2.1_hiera_large.pt` + `sam2.1_hiera_l.yaml`. [Detector release](https://github.com/IDEA-Research/GroundingDINO/blob/856dde20aee659246248e20734ef9ba5214f5e44/README.md), [SAM 2.1 release](https://github.com/facebookresearch/sam2/blob/2b90b9f5ceec907a1c18123530e92e794ad901a4/README.md). | Swin-T's release table reports 48.4 zero-shot COCO box AP. SAM 2.1-L reports 79.5 SA-V test J&F, 224.4M parameters and 39.5 FPS on A100 with compiled components, torch 2.5.1 / CUDA 12.4. These are separate detector and prompted-video evaluations, not combined person/ball accuracy. | SAM 2 requires Python ≥3.10, torch ≥2.5.1, torchvision ≥0.20.1; custom CUDA postprocessing has separate build requirements. Detector short side 800/max 1333, ImageNet normalization; SAM 2 predictor uses a 1024 square input with its own coordinate transform. Medium effort: boxes to masks, phrase mapping, pair reset and video propagation. [SAM transforms](https://github.com/facebookresearch/sam2/blob/2b90b9f5ceec907a1c18123530e92e794ad901a4/sam2/utils/transforms.py). |
| **S3 SAM 3** | Original `facebook/sam3` / `sam3.pt`, image concept segmentation and original video predictor. Current source also offers **SAM 3.1 Object Multiplex** with separate checkpoints; it is recorded but receives no additional experiment allocation. [SAM 3 release](https://github.com/facebookresearch/sam3/blob/660a5e9e1b8b4c02c0ad97229b88a09a6e4ff5b7/README.md), [3.1 release](https://github.com/facebookresearch/sam3/blob/660a5e9e1b8b4c02c0ad97229b88a09a6e4ff5b7/RELEASE_SAM3p1.md). | SAM 3 has 848M parameters and reports concept segmentation/detection/tracking on SA-Co and video benchmarks. The [paper](https://arxiv.org/abs/2511.16719) supports text-driven instance discovery, not Basketball accuracy. SAM 3.1's reported ~7× speedup at 128 objects on H100 cannot be assigned to the original SAM 3 or a 4090. | README calls for Python ≥3.12, torch ≥2.7 and CUDA ≥12.6; gated checkpoint access. Image processor defaults to 1008 square RGB, normalized with mean/std 0.5. High effort: merge separate person/ball concept results, map video IDs, control births and overlapping concepts, and qualify memory. [Processor](https://github.com/facebookresearch/sam3/blob/660a5e9e1b8b4c02c0ad97229b88a09a6e4ff5b7/sam3/model/sam3_image_processor.py). |
| **S4 RT-DETRv2 + SAM 2.1** | Select RT-DETRv2-L/R50vd, paired with the same SAM 2.1-L. Native checkpoint `rtdetrv2_r50vd_6x_coco_ema.pth`; benchmark uses the explicitly identified `PekingU/rtdetr_v2_r50vd` conversion. Released sizes include S/R18, M/R34, M/R50-m, L/R50, X/R101; discrete-sampling variants are distinct. [Native releases](https://github.com/lyuwenyu/RT-DETR/blob/29320b6fd828f8e0987a71426cf2d961b09dfed7/rtdetrv2_pytorch/README.md), [model card](https://huggingface.co/PekingU/rtdetr_v2_r50vd). | Native L reports COCO AP 53.4, 42M parameters, 108 FPS at 640² on T4 TensorRT FP16. That is detector-only throughput, not PyTorch + SAM timing. [RT-DETRv2 paper](https://arxiv.org/abs/2407.17140). | Native runtime table uses torch 2.4 / torchvision 0.19; proposed converted route shares a newer SAM environment. Processor resizes RGB to 640² and rescales by 1/255 with normalization disabled. Use label names `person` and `sports ball`; explicitly map the latter to the ball candidate class. Medium effort; closed categories avoid text ambiguity but do not distinguish basketballs from other balls. [Processor configuration](https://huggingface.co/PekingU/rtdetr_v2_r50vd/blob/282494075698cab9faa1096ae26856890030c817/preprocessor_config.json). |

**Quality hypotheses.** S2's video memory and newer mask model may improve
successor boundaries, but cannot recover a ball never detected at the keyframe.
S3 may discover newly visible instances; overlapping concept masks and tiny
blurred balls remain failure cases. S4 can reduce text-prompt sensitivity but
640² detection can lose tiny balls. Neither `person` nor `sports ball` identifies
players or court relevance. Evaluate stationary people, spectators and officials
separately; exclude all people from calibration static evidence even when still.
Keep player/other-person annotation metadata separate from model semantics.

### Adjacent motion algorithms

| Algorithm | Useful behavior to test | Failure mechanism and integration |
| --- | --- | --- |
| **M0 current adjacent difference** | Exact control: grayscale absolute difference >20, followed by one 9×9 dilation. Cheap, local, deterministic. | Misses stationary people and persistent displays; edges, shadows, exposure changes and motion blur can exclude useful background. Semantics must be combined with motion, not replaced. |
| **M1 temporal-median residual** | Proposed nine-frame, role-bounded temporal median with the same threshold and dilation. Can identify a broader moving silhouette than adjacent differences. | Persistent foreground can enter the median; rapidly changing displays and lighting may exclude large regions. Needs an explicit context list, including boundary behavior. No claimed published Basketball advantage; this is a local algorithm proposal. |
| **M2 MOG2** | Adaptive mixture background model; explicit learning rate, history and shadow label. [OpenCV MOG2 API](https://docs.opencv.org/4.13.0/d7/d7b/classcv_1_1BackgroundSubtractorMOG2.html). | Cold start, stationary-object absorption and camera/exposure changes matter. Shadow-valued pixels are not ordinary background. Keep per-camera/per-role state and report warmup effects; do not train state using validation frames. |

Motion outputs should identify changing regions separately from instance masks.
A shadow is not a player instance, but its changing pixels may be unsuitable
static evidence. Inspect display panels as a separate annotation layer. The
protocol compares M0/M1/M2 with S0 held fixed before any combined stack.

## 3. Depth and physical scale candidates for step 2.5

All depth arms keep the accepted intrinsics, poses, sparse XYZ and eligible
static sample locations fixed. Output must be **camera-z depth in metres**,
not relative depth, inverse depth, or Euclidean distance along a ray. Fitting a
separate affine transform per image would hide metric bias and invalidate the
comparison. None of these single-image replacements guarantees cross-camera
consistency or physical accuracy in this gym.

| Candidate and released variant | Intrinsics, preprocessing and output | Published quality and resource evidence | Runtime and integration |
| --- | --- | --- | --- |
| **D0 reference / D1 standalone UniDepth V2**: `unidepth-v2-vitl14`; V2 also releases `vits14` and `vitb14`. The README model-zoo row for ViT-B repeats a small-model name; use the actual loader/config rather than that typo. [Source](https://github.com/lpiccinelli-eth/UniDepth/blob/8d8cfe4c7ee15297099983607febf0d4f32eb3d6/README.md). | Official `infer` accepts byte RGB and a K tensor or a concrete camera object. Preserve aspect ratio and the checkpoint's pixel bounds; V2 exposes resolution level and bilinear interpolation. Depth and within-image relative confidence are returned. Supply the existing target pinhole K; do not re-estimate it. [V2 contract](https://github.com/lpiccinelli-eth/UniDepth/blob/8d8cfe4c7ee15297099983607febf0d4f32eb3d6/assets/docs/V2_README.md). | The [V2 paper](https://arxiv.org/abs/2502.20110) studies metric geometry, edges and generalization. Author code reports >30% faster inference than V1 on RTX 4090 in float16. The existing Basketball scale result is the only local depth evidence here; it is repeatability evidence, not measured accuracy. | [Requirements](https://github.com/lpiccinelli-eth/UniDepth/blob/8d8cfe4c7ee15297099983607febf0d4f32eb3d6/requirements.txt) include torch ≥2.4, torchvision ≥0.19, NumPy ≥2, Triton and xFormers. Low/medium adapter effort; medium environment/parity qualification. The training edge-extraction extension is not evidence that inference requires `vipe_ext`. |
| **D2 DA3METRIC-LARGE**: `depth-anything/DA3METRIC-LARGE`, 0.35B parameters. This is distinct from DA3MONO, DA3-LARGE-1.1, DA3-GIANT-1.1 and DA3NESTED. [Model card](https://huggingface.co/depth-anything/DA3METRIC-LARGE). | Bare metric model predicts canonical depth. Apply `z = raw_depth * mean(fx_processed, fy_processed) / 300` once, then map back to 960×540. Use the preprocessing-transformed accepted K. Generic examples showing predicted poses/confidence do not establish those outputs for this monocular variant. [Metric FAQ](https://github.com/ByteDance-Seed/Depth-Anything-3/blob/3d835ec1a5802d64a8b8b15f817a1ab54809bfe4/README.md), [model source](https://github.com/ByteDance-Seed/Depth-Anything-3/blob/3d835ec1a5802d64a8b8b15f817a1ab54809bfe4/src/depth_anything_3/model/da3.py). | The [DA3 paper](https://arxiv.org/abs/2511.10647) reports broad visual-geometry and monocular evaluations. Main/nested multi-view gains do not prove superiority of this metric-only checkpoint. Its model card gives no matched 4090 latency/peak memory; the streaming family's <12 GB statement is not a DA3METRIC requirement. | [Package metadata](https://github.com/ByteDance-Seed/Depth-Anything-3/blob/3d835ec1a5802d64a8b8b15f817a1ab54809bfe4/pyproject.toml) allows Python ≥3.9 and ≤3.13, torch ≥2, NumPy <2, xFormers and a broad tool/export dependency set. Medium effort: explicit canonical scaling, image/K transformations and optional outputs. Use a separate environment, avoiding the historical Python 3.14 patch. |
| **D3 Metric3Dv2 ViT-L**: `metric_depth_vit_large_800k.pth`, `metric3d_vit_large`, config `vit.raft5.large.py`; V2 also releases ViT-S and ViT-giant2. ConvNeXt checkpoints are V1. [Loader and variants](https://github.com/YvanYin/Metric3D/blob/eb5b6fac0dc155e4e52f576e304fbf11655ff339/hubconf.py). | Fit RGB inside 616×1064 for the ViT hub path, pad with RGB means, normalize, infer canonical depth, unpad and bilinearly restore. Multiply by the **resized** `fx/1000`, not the original fx and not twice. Depth/normal confidence are different quantities. Model is focal-conditioned through de-canonicalization, not an arbitrary full-K ray-conditioned substitute. | The [paper](https://arxiv.org/abs/2404.15506) evaluates joint metric depth/normals. The [release table](https://github.com/YvanYin/Metric3D/blob/eb5b6fac0dc155e4e52f576e304fbf11655ff339/README.md) separates metric and affine-invariant results; ViT-L metric NYUv2 AbsRel is 0.047. No exact-workload VRAM/latency established. | [V2 dependencies](https://github.com/YvanYin/Metric3D/blob/eb5b6fac0dc155e4e52f576e304fbf11655ff339/requirements_v2.txt) pin torch 2.0.1, torchvision 0.15.2, NumPy 1.23.1 and xFormers 0.0.21; MMCV/config dependencies need qualification. Medium/high effort: older environment, image/canonical transforms and weight-license uncertainty. Do not silently change dependencies if resolution fails. |
| **D4 Depth Pro**: official `apple/DepthPro/depth_pro.pt`, using Apple's native implementation; no fine-tuned or quantized derivative. [Model card](https://huggingface.co/apple/DepthPro). | Official transforms normalize RGB; `infer` internally resizes to 1536². Supply accepted `fx` at the original input width via `f_px` as a tensor. Native code converts canonical inverse depth using `W/f_px`, restores inverse depth to input dimensions, then inverts. Passing fx disables use of predicted focal for depth scaling; it does not provide full-K conditioning. [Inference source](https://github.com/apple/ml-depth-pro/blob/9e65e4dbe9568d23c546fcec53302b10445e109e/src/depth_pro/depth_pro.py). | [Paper](https://arxiv.org/abs/2410.02073) reports sharp boundaries and a 2.25-megapixel output in 0.3 seconds on a GPU. The released model was retrained and explicitly does not exactly match the paper model. This is not a measured 4090 result or proof of accurate long-range gym depth. | Native [setup](https://github.com/apple/ml-depth-pro/blob/9e65e4dbe9568d23c546fcec53302b10445e109e/README.md) recommends Python 3.9; [dependencies](https://github.com/apple/ml-depth-pro/blob/9e65e4dbe9568d23c546fcec53302b10445e109e/pyproject.toml) include torch/torchvision, timm, NumPy <2 and pillow_heif. Medium adapter effort; high internal resolution needs memory qualification. No confidence map should be fabricated. |

For DA3, the inspected [input processor](https://github.com/ByteDance-Seed/Depth-Anything-3/blob/3d835ec1a5802d64a8b8b15f817a1ab54809bfe4/src/depth_anything_3/utils/io/input_processor.py)
rescales K with the image, rounds dimensions to patch multiples, and can crop
mixed-size batches. Its [API](https://github.com/ByteDance-Seed/Depth-Anything-3/blob/3d835ec1a5802d64a8b8b15f817a1ab54809bfe4/src/depth_anything_3/api.py)
also has pose-scale alignment facilities. The benchmark uses one image at a
time, no extrinsics, no pose alignment and no Gaussian export. That prevents the
accepted map scale from being fed back into a supposedly independent estimate.
[Output conversion](https://github.com/ByteDance-Seed/Depth-Anything-3/blob/3d835ec1a5802d64a8b8b15f817a1ab54809bfe4/src/depth_anything_3/utils/io/output_processor.py)
allows absent confidence and camera outputs; validate actual fields and units.

**Independently measured distances are a conditional anchor, not a fifth neural
model.** If surveyed camera-center baselines or distances between independently
identified static 3D endpoints become available, estimate one global scale from
their measured lengths/map lengths, with measurement uncertainty. Hold out a
separate measured distance for physical validation. Record endpoints, instrument,
units and provenance before comparing predictions. Court regulation dimensions,
an apparent ball diameter, or distances read from this reconstruction are not
independent measurements of this scene. Without independent references, report
repeatability and unresolved common metric bias for every depth model.

## 4. License audit: code, weights and dependencies

This is an evidence inventory of the identified assets, not a blanket license
for an assembled application. **Commercial permission and an open-source license
other than AGPL-3.0 are separate preferences.** AGPL is copyleft and permits
commercial activity; it is not a noncommercial license. CC BY-NC and Apple's
research-model terms restrict use. SAM 3's custom terms are neither AGPL nor a
substitute for the requested open-source-license preference.

| Component | Code evidence | Weight evidence | Preference assessment |
| --- | --- | --- | --- |
| ViPE / historical SAM-Track wrapper | ViPE top-level Apache-2.0 does not override bundled notices. Local tracker files identify AGPL-3.0; upstream [LICENSE.txt](https://github.com/z-x-yang/Segment-and-Track-Anything/blob/99ca4bd5074a6ed62db4664285073ab669503926/LICENSE.txt) confirms it. | Not one weight license: SAM, Grounding DINO, BERT and DeAOT have separate assets. | Removing ViPE by copying or importing its tracker does not remove AGPL. Upstream's proprietary-commercial offer is separate from AGPL use. |
| SAM 1 / SAM 2.1 | [SAM 1 license statement](https://github.com/facebookresearch/segment-anything/blob/dca509fe793f601edb92606367a655c15ac00fdf/README.md), [SAM 2 LICENSE](https://github.com/facebookresearch/sam2/blob/2b90b9f5ceec907a1c18123530e92e794ad901a4/LICENSE): Apache-2.0. | Author release statements cover model checkpoints; [SAM 2.1-L model card](https://huggingface.co/facebook/sam2.1-hiera-large) also identifies Apache-2.0. Dataset terms are separate. | Both preferences supported for these components; retain notices and optional CUDA-component license. |
| Grounding DINO | [Code license](https://github.com/IDEA-Research/GroundingDINO/blob/856dde20aee659246248e20734ef9ba5214f5e44/LICENSE): Apache-2.0. | Author-linked [ShilongLiu model repository](https://huggingface.co/ShilongLiu/GroundingDINO) now explicitly labels Apache-2.0. This is stronger current evidence than the historical audit's unresolved asset grant; it does not prove an old download's origin. [BERT assets](https://huggingface.co/google-bert/bert-base-uncased) have their own Apache-2.0 model card. | Both preferences supported by these declarations; pin asset bytes and tokenizer/config files. |
| DeAOT | [AOT benchmark LICENSE](https://github.com/yoxu515/aot-benchmark/blob/601c138435a1764eb01404f3495b914e6e2e8eca/LICENSE): BSD-3-Clause. | Historical Google Drive R50 asset is hash-recorded, but a separate explicit weight grant was not established. Source BSD alone cannot resolve this. | Code meets both preferences; complete weight permission remains unverified. The enclosing historical wrapper remains AGPL. |
| RT-DETRv2 | [Native LICENSE](https://github.com/lyuwenyu/RT-DETR/blob/29320b6fd828f8e0987a71426cf2d961b09dfed7/LICENSE): Apache-2.0. Converted route uses Apache-2.0 Transformers. | The selected [PekingU R50vd model card](https://huggingface.co/PekingU/rtdetr_v2_r50vd) explicitly declares Apache-2.0. Record it as a conversion rather than asserting byte/processor parity with the native release. | Both preferences supported for the specified route. Choosing an Ultralytics wrapper instead would require a different audit; it is not part of this proposal. |
| SAM 3 | [SAM License](https://github.com/facebookresearch/sam3/blob/660a5e9e1b8b4c02c0ad97229b88a09a6e4ff5b7/LICENSE) covers code and trained models. | [Model metadata](https://huggingface.co/facebook/sam3) identifies custom terms and manual access gating. | Commercial use is not excluded by the grant, but custom redistribution, acknowledgement, reverse-engineering and use restrictions apply. It does not satisfy the open-source-license preference. The package's MIT classifier and lower Python metadata conflict with LICENSE/README; use the latter as authoritative. |
| UniDepth V2 | [LICENSE](https://github.com/lpiccinelli-eth/UniDepth/blob/8d8cfe4c7ee15297099983607febf0d4f32eb3d6/LICENSE) and author README: CC BY-NC 4.0. | Historical audit treats the checkpoint as noncommercial. The inspected [exact model card](https://huggingface.co/lpiccinelli/unidepth-v2-vitl14/blob/52b349b514bd8b47642f67ac78cb7b5dc5c51dd9/README.md) has no independent license field or grant; it points to the source project. | No commercial permission established. Noncommercial project terms are not an open-source software license merely because they are not AGPL. Preserve that restriction/uncertainty in the replacement control. |
| DA3METRIC-LARGE | [Code LICENSE](https://github.com/ByteDance-Seed/Depth-Anything-3/blob/3d835ec1a5802d64a8b8b15f817a1ab54809bfe4/LICENSE): Apache-2.0. | [Exact model card](https://huggingface.co/depth-anything/DA3METRIC-LARGE/blob/4010e39f3634a45bc60553321fb49fb760bd594e/README.md): Apache-2.0. Large/giant/nested family licenses must not be substituted. | Both preferences supported at model level. Full dependency installation includes other licenses, especially GPL/LGPL below. |
| Metric3Dv2 | [LICENSE](https://github.com/YvanYin/Metric3D/blob/eb5b6fac0dc155e4e52f576e304fbf11655ff339/LICENSE): BSD-2-Clause; README separately invites commercial inquiries. | Author-linked [JUGGHM repository](https://huggingface.co/JUGGHM/Metric3D) has checkpoints but no model card/license declaration. No explicit separate weight grant established. | Code meets both preferences; weight/commercial permission is unverified, not proven noncommercial and not proven BSD. Resolve before an execution that requires such permission. |
| Depth Pro | [Apple software LICENSE](https://github.com/apple/ml-depth-pro/blob/9e65e4dbe9568d23c546fcec53302b10445e109e/LICENSE) grants source/binary use and redistribution under custom notice conditions. | [Apple AMLR weight LICENSE](https://huggingface.co/apple/DepthPro/blob/ccd1350a774eb2248bcdfb3be430e38f1d3087ef/LICENSE) limits model and derivatives to noncommercial research and excludes product development/commercial exploitation. | Research candidate only under these weights. A permissive-looking code grant does not grant commercial use of the model. Custom terms also fail the requested standard open-source option. |

### Required dependency scope

The runtime matrix above links each candidate's dependency declaration. The
following material dependencies must be audited independently; a top-level
license cannot replace these notices. A full installed transitive closure and
native-wheel bill of materials cannot be verified without selecting/building
the future environments, so complete application-level permission remains
conditional on that recorded check.

| Dependency / affected routes | Inspected license evidence and consequence |
| --- | --- |
| PyTorch ecosystem / all GPU routes | [PyTorch LICENSE](https://github.com/pytorch/pytorch/blob/main/LICENSE) contains its BSD-style grant and bundled third-party notices. Freeze torch/torchvision wheels and their notices together. CUDA libraries/driver have separate NVIDIA platform terms; no model license makes them open-source software. |
| Transformers / Grounding DINO and converted RT-DETRv2 | [Apache-2.0 source](https://github.com/huggingface/transformers/blob/main/LICENSE). Record Hugging Face Hub, tokenizer, safetensors and BERT assets separately in the resolved environment inventory. |
| timm and DINOv2 / detector and depth backbones | [timm Apache-2.0](https://github.com/huggingface/pytorch-image-models/blob/main/LICENSE), [DINOv2 Apache-2.0](https://github.com/facebookresearch/dinov2/blob/main/LICENSE). Do not enable an implicit alternate pretrained-backbone download. |
| xFormers / UniDepth, DA3, Metric3D | [BSD-3-Clause plus bundled notices](https://github.com/facebookresearch/xformers/blob/main/LICENSE). Match the CUDA/torch ABI. Triton or optional attention kernels are additional resolved artifacts, not automatically covered by xFormers. |
| OpenCV / decoding, motion, geometry | [4.13.0 Apache-2.0](https://github.com/opencv/opencv/blob/4.13.0/LICENSE); historical versions and wheel-bundled codecs may have other notices. Freeze the actual version and decoder build. |
| SAM 2 connected-components extension | [BSD-3-Clause notice](https://github.com/facebookresearch/sam2/blob/2b90b9f5ceec907a1c18123530e92e794ad901a4/LICENSE_cctorch). Optional postprocessing choices affect reproducibility even when the model can run without this extension. Demo font licenses are irrelevant to this headless adapter, since the demo is not used. |
| MMCV / Metric3D configuration and utilities | [Apache-2.0](https://github.com/open-mmlab/mmcv/blob/main/LICENSE). Package/extension version remains an explicit environment qualification item. |
| COCO API / detection tooling and evaluation | [BSD-style source conditions](https://github.com/cocodataset/cocoapi/blob/master/license.txt) concern code, not COCO image/annotation rights or the Basketball archive. |
| `evo` / DA3 default package dependencies | [GPL-3.0](https://github.com/MichaelGrupp/evo/blob/master/LICENSE). Commercial use and non-AGPL open-source preferences are compatible with GPL obligations; the installed DA3 stack is not all Apache. A minimal import route must be independently audited before claiming this dependency is absent. |
| `pillow_heif` and libheif / DA3, Depth Pro default dependencies | [pillow_heif notice](https://github.com/bigcat88/pillow_heif/blob/master/LICENSE.txt), [libheif LGPL-3.0 and wrapper terms](https://github.com/strukturag/libheif/blob/master/COPYING). Audit bundled codecs and their linking/redistribution terms; using PNG inputs does not erase installed-wheel obligations. |

Separate environments solve dependency conflicts and allow explicit file-based
interfaces; they do not by themselves remove copyleft obligations. The new
commercial-preference adapters should be written against direct upstream APIs,
with their own semantic/serialization code, without copying the AGPL tracker.
No deployment, distribution or legal clearance is claimed by this study.

## 5. Neighbors, migration order and recommendations

| Neighbor method | What changes | What it can and cannot establish |
| --- | --- | --- |
| **N0 shared-track count** | Current top-three ranking by intersection cardinality, with physical camera ID as tie-breaker. | Cheap and reproducible. Favors cameras with large feature pools and can concentrate support in one image region; static overlap is only a proxy for players/ball. |
| **N1 normalized co-visibility** | Rank `J(c,o)=|T_c ∩ T_o| / |T_c ∪ T_o|` on the same training-only map. Keep positive shared support and deterministic ties. | Corrects raw-count imbalance but can favor two sparse views. Publish raw support alongside Jaccard, and keep triangulation acceptance unchanged. This exact score is a proposed local comparison. |
| **N2 coverage/parallax-aware selection** | Greedily select three neighbors using new reference-image grid coverage, new shared points and useful ray-angle support; the protocol fixes the ranking tuple. | May diversify triangulation support, but greater baseline can hurt matching and occlusion. The [COLMAP source-view guidance](https://colmap.github.io/faq.html#manual-specification-of-source-images-during-dense-reconstruction) motivates assessing visual overlap and source-view cost. The angle gate comes from this repository; neither source validates this custom ranking. |

All methods use the accepted map and identical camera set. Exactly three
neighbors bounds matching cost; a missing third usable neighbor is an explicit
failure, not permission to include a held-out camera. Count accepted static,
person and ball triangulations separately, measure image/camera coverage and
matching cost, and retain geometric rejection reasons. Normalized co-visibility
alone says nothing about motion masks or metric scale.

Recommended order, with integration effort measured as engineering scope rather
than an unverified time estimate:

1. **Establish the S1/D1 controls and neutral interfaces.** Keep the original
   model assets and compare intermediate resized RGB, K, boxes, phrases, masks,
   depths and per-camera scale ratios. Porting upstream components establishes
   dependency removal only after runtime/provenance checks; do not claim parity
   by name. Preserve all historical adapters and evidence.
2. **Primary stack: S2 + D1.** This is the first quality hypothesis to prioritize:
   SAM 2.1 may improve segmentation/propagation while the depth model has existing
   scene evidence. Keep M0/N0 until the independent M/N comparisons justify a
   change. UniDepth remains noncommercial; primary quality preference does not
   imply satisfying the optional license preferences.
3. **Commercial-use/non-AGPL option: S4 + D2.** Author/publisher declarations
   support Apache model code/weights for the specified detector, SAM and metric
   depth variants. Include the GPL/LGPL and native dependency inventory; this
   recommendation does not mean every dependency is permissively licensed.
   A measured distance can replace learned metric anchoring if independently
   available and validated. Small-ball recall and DA3 metric bias are open gates.
4. **High-upside challenger: S3; further depth challengers: D3 and D4.** SAM 3
   has useful concept-discovery capabilities but higher integration and access
   uncertainty. Metric3D's camera normalization and Depth Pro's boundaries merit
   controlled study, with their weight-permission limitations retained. Do not
   promote any of them from unrelated leaderboard results.
5. **Fallback: S1 + D1 + M0 + N0.** This minimizes conceptual changes while
   removing ViPE orchestration, but retains historical segmentation limitations,
   AGPL and depth/DeAOT permission qualifications. If control outputs cannot be
   validated, keep the archived ViPE stack as the reference and report migration
   incomplete rather than forcing a production replacement.

### Freeze and provenance changes required by a later implementation

Create an experiment-scoped component manifest covering detector, segmenter,
tracker, depth model, motion algorithm and neighbor selector, each with source
revision/files, weights/config/tokenizer hashes, dependency lock/wheel hashes,
native extension hashes, runtime, device/dtype and preprocessing parameters.
Include component license evidence and its inspection date. Replace new-output
claims of `vipe_revision` with these component identities; do not merely remove
the old verification calls. New workers must run with ViPE paths unavailable.

Generalize hardcoded parent paths in the new audit/scale/freeze workers to explicit
hash-bound inputs. Preserve old `frozen-winner.json`, `validation-consumed.json`,
depth outputs, scale reports, `.local/` manifests and checkpoint provenance.
New masks cannot inherit historical calibration-validation claims. New scales
must reference their own passing frame-100 fit and frozen frame-175 check.

For scale `s`, apply `X'=sX`, `t'=st`, `C'=sC`, with R/K unchanged; camera
projection is invariant. Recompute any derived normalization consistently, and
keep velocity/scene-distance units consistent with that transform and the fixed
time convention. Scaling only depth, only points, or only camera translation
breaks the chain. Scale-only changes may leave normalized rendering unchanged;
do not interpret this as independent physical-scale validation. Fresh freeze,
scene, static cloud and dense diagnostic artifacts must refer to the same scale.

## 6. Source and asset pins

These are read-only inspection pins, obtained from official repository/model
metadata on the study date. They are not an installed environment lock and do
not establish byte-level checkpoint verification. Pin the exact listed source
revision and model snapshot in a future run; compute local SHA-256 after any
authorized retrieval, including configuration/tokenizer files. The historical
SAM/DeAOT/GroundingDINO and UniDepth weight hashes remain available in the
[existing audit](../experiments/basketball-calibration-20260906.json).

| Upstream source | Inspected commit |
| --- | --- |
| [SAM-Track](https://github.com/z-x-yang/Segment-and-Track-Anything/tree/99ca4bd5074a6ed62db4664285073ab669503926) | `99ca4bd5074a6ed62db4664285073ab669503926` |
| [AOT benchmark](https://github.com/yoxu515/aot-benchmark/tree/601c138435a1764eb01404f3495b914e6e2e8eca) | `601c138435a1764eb01404f3495b914e6e2e8eca` |
| [SAM 1](https://github.com/facebookresearch/segment-anything/tree/dca509fe793f601edb92606367a655c15ac00fdf) | `dca509fe793f601edb92606367a655c15ac00fdf` |
| [Grounding DINO](https://github.com/IDEA-Research/GroundingDINO/tree/856dde20aee659246248e20734ef9ba5214f5e44) | `856dde20aee659246248e20734ef9ba5214f5e44` |
| [SAM 2](https://github.com/facebookresearch/sam2/tree/2b90b9f5ceec907a1c18123530e92e794ad901a4) | `2b90b9f5ceec907a1c18123530e92e794ad901a4` |
| [SAM 3](https://github.com/facebookresearch/sam3/tree/660a5e9e1b8b4c02c0ad97229b88a09a6e4ff5b7) | `660a5e9e1b8b4c02c0ad97229b88a09a6e4ff5b7` |
| [RT-DETRv2](https://github.com/lyuwenyu/RT-DETR/tree/29320b6fd828f8e0987a71426cf2d961b09dfed7) | `29320b6fd828f8e0987a71426cf2d961b09dfed7` |
| [UniDepth](https://github.com/lpiccinelli-eth/UniDepth/tree/8d8cfe4c7ee15297099983607febf0d4f32eb3d6) | `8d8cfe4c7ee15297099983607febf0d4f32eb3d6` |
| [DA3](https://github.com/ByteDance-Seed/Depth-Anything-3/tree/3d835ec1a5802d64a8b8b15f817a1ab54809bfe4) | `3d835ec1a5802d64a8b8b15f817a1ab54809bfe4` |
| [Metric3D](https://github.com/YvanYin/Metric3D/tree/eb5b6fac0dc155e4e52f576e304fbf11655ff339) | `eb5b6fac0dc155e4e52f576e304fbf11655ff339` |
| [Depth Pro](https://github.com/apple/ml-depth-pro/tree/9e65e4dbe9568d23c546fcec53302b10445e109e) | `9e65e4dbe9568d23c546fcec53302b10445e109e` |

| Model repository | Inspected snapshot | Selected file |
| --- | --- | --- |
| ShilongLiu/GroundingDINO | `a94c9b567a2a374598f05c584e96798a170c56fb` | `groundingdino_swint_ogc.pth` |
| facebook/sam2.1-hiera-large | `665f8e2ad61cf5f53d65644ff27c8ee525124610` | `sam2.1_hiera_large.pt` |
| facebook/sam3 | `3c879f39826c281e95690f02c7821c4de09afae7` | `sam3.pt` (manual access gate; not requested) |
| PekingU/rtdetr_v2_r50vd | `282494075698cab9faa1096ae26856890030c817` | `model.safetensors` and processor/config JSON |
| lpiccinelli/unidepth-v2-vitl14 | `52b349b514bd8b47642f67ac78cb7b5dc5c51dd9` | `model.safetensors`, matching the historical audit's selected serialization |
| depth-anything/DA3METRIC-LARGE | `4010e39f3634a45bc60553321fb49fb760bd594e` | `model.safetensors` |
| JUGGHM/Metric3D | `80d2d1410afb4b23cd9d18c6be9144483d4b70b6` | `metric_depth_vit_large_800k.pth` |
| apple/DepthPro | `ccd1350a774eb2248bcdfb3be430e38f1d3087ef` | `depth_pro.pt` |

The audit records UniDepth's selected `model.safetensors` SHA-256 as
`ba73d3de735302ccc64a50f1e557122050c4b1893e6060b28dba05d6af3e67c6`.
Do not substitute the same snapshot's alternative `pytorch_model.bin` while
claiming identical historical asset provenance.

## 7. Unresolved questions and completion evidence

- Do better pixel/instance masks retain enough static calibration features,
  especially where held-out camera 0 already has limited support?
- Does either open detector recover tiny blurred balls without the large
  false-positive masks seen historically? Do propagated IDs survive crossings?
- How much person coverage is spectators rather than players, and does crop
  association transfer masks to the correct person across cameras?
- Can D1 reproduce the fork closely enough to isolate dependency removal? Do
  D2/D3/D4 pass all existing scale gates, and do independently measured distances
  exist to resolve shared metric bias?
- Does N2 improve coverage/accepted triangulation at tolerable matching cost,
  or does wider viewpoint separation erase the expected benefit?
- Can the pinned environments, SAM 3 access and exact weight/dependency grants be
  qualified within the proposed limits? Missing evidence is not a passing result.

Plan 030 completion is the cited coverage of all three workflow steps, concrete
interfaces/migration requirements and a bounded comparison specification. It does
not establish replacement quality or authorize the proposed benchmark.

Documentation validation on 2026-09-12 passed: 54 local links/heading targets,
80 distinct external source URLs (GitHub file links checked through their raw
source equivalents), the external section anchor, Markdown fences and whitespace.
The embedded protocol JSON parses; its selections yield 232 annotation images,
690 distinct reconstruction RGB images, 6,750 primary mask rows and 36 GPU jobs
bounded by 93,600 seconds. Camera/frame exclusions, geometry/crop counts and the
13 recorded scale gate/seed values were checked against the protocol and existing
scale configuration. This validates the specification, not the proposed adapters
or runtime. Execution evidence must be created by a later admitted run as
specified in the [protocol](vipe-alternatives/benchmark-protocol.md).
