# Research and code provenance for the Basketball experiments

This explanation records the code and source audit discussed with the user on
2026-09-11. The three experiments share existing reconstruction, matching, and
masking components. This repository adds the Basketball data adapters, dense
initialization workflow, experiment management, and crossing repair.

**FreeTimeGS uses an independent reproduction. STG uses the paper authors'
repository with local patches.** The experiment names describe workflows in this
repository, rather than three separately published reconstruction methods.

| Experiment | Reconstruction code used | What this project adds |
|---|---|---|
| **basketball-dense-temporal — Plan 026** | STG Full and FreeTimeGsVanilla | Longer training comparisons and a Basketball dense initialization pipeline. The dense pilots failed their visual acceptance criteria, so dense production training did not proceed in this plan. |
| **basketball-dense-training — Plan 027** | The same FreeTimeGsVanilla backend | Full coarse and person-cropped dense initializers, followed by training to 50k. STG and sparse FreeTimeGS comparison results were reused from Plan 026. |
| **basketball-crossing-repair — Plan 028** | FreeTimeGsVanilla, continuing Plan 027's dense checkpoints | The A–D experiment, restoration of crossing-frame supervision, and the duration repair used by B/D. |

Execution details are recorded in the [Plan 026 status](basketball-dense-temporal/status.md),
[Plan 027 status](basketball-dense-training/status.md), and
[crossing workflow explanation](basketball-crossing-repair/workflow-explanation.md).

The principal research and code dependencies are:

| Research paper | Actual repository and pinned revision | Role here |
|---|---|---|
| [**FreeTimeGS: Free Gaussian Primitives at Anytime Anywhere for Dynamic Scene Reconstruction**, CVPR 2025](https://zju3dv.github.io/freetimegs/) | [OpsiClear-4DGS/FreeTimeGsVanilla](https://github.com/OpsiClear-4DGS/FreeTimeGsVanilla), `911dcf4` | Moving Gaussians with position, velocity, temporal center, and duration; reconstruction training and rendering. This is an independent minimal reproduction. |
| [**Spacetime Gaussian Feature Splatting for Real-Time Dynamic View Synthesis**, CVPR 2024](https://oppo-us-research.github.io/SpacetimeGaussians-website/) | [oppo-us-research/SpacetimeGaussians](https://github.com/oppo-us-research/SpacetimeGaussians), `427abfc`, plus local patches | The STG Full comparison baseline. |
| [**EDGS: Eliminating Densification for Efficient Convergence of 3DGS**](https://compvis.github.io/EDGS/) | [CompVis/EDGS](https://github.com/CompVis/EDGS), `f90b022` | Dense initialization approach and selected geometry/triangulation functions. |
| [**RoMa: Robust Dense Feature Matching**, CVPR 2024](https://openaccess.thecvf.com/content/CVPR2024/papers/Edstedt_RoMa_Robust_Dense_Feature_Matching_CVPR_2024_paper.pdf) | [Parskatt/RoMa](https://github.com/Parskatt/RoMa), `3701174` | Pretrained dense correspondences between camera images. |
| [**ViPE: Video Pose Engine for 3D Geometric Perception**](https://research.nvidia.com/labs/toronto-ai/vipe/) | [NVIDIA ViPE](https://github.com/nv-tlabs/vipe), through the user's `samaust/vipe` fork at `de50e6a` | Person/ball segmentation and adjacent-frame mask tracking. |
| [**gsplat: An Open-Source Library for Gaussian Splatting**](https://arxiv.org/abs/2409.06765) | [nerfstudio-project/gsplat](https://github.com/nerfstudio-project/gsplat), `b60e917` | FreeTimeGsVanilla's CUDA rasterization and Gaussian optimization utilities. |

The [reconstruction source inventory](../research/basketball-sync-pivot/source-license-inventory.json),
[EDGS source audit](basketball-dense-temporal/pilot-source-audit.json),
[RoMa loader](../../scripts/edgs_source.py), and
[native dependency build script](../../scripts/build-freetimegs-native.sh)
retain the corresponding full revisions or source hashes. The
[mask adapter](../../scripts/basketball_temporal_masks.py) verifies the ViPE
revision and source/weight hashes against the saved calibration input audit.

**FreeTimeGsVanilla's computational core is reused directly.** The adapters load
selected upstream function bodies, including:

- Gaussian parameter and optimizer initialization.
- Position-at-time and temporal-opacity calculations.
- Rendering and regularization.
- The central training step: losses, scheduling, optimizer updates, relocation,
  and pruning.

The audited external FreeTimeGsVanilla checkout is clean. The experiments use
this repository's camera inputs, sampling, checkpointing, and execution loops
around those functions. Consequently, this is reuse of the native computational
core, rather than execution of its complete stock pipeline. The boundary is
explicit in [freetimegs_source.py](../../scripts/freetimegs_source.py) and
[freetimegs_training.py](../../scripts/freetimegs_training.py).

For **EDGS**, the loader extracts four unchanged upstream function bodies:
`prepare_tensor`, `triangulate_points`, `pairwise_distances`, and
`k_closest_vectors`. The Basketball pipeline uses the triangulation helper and
reuses a calibrated projection adapter written in this repository during the
earlier EDGS/SelfCap integration. **It does not run EDGS's Gaussian trainer.**
See [edgs_source.py](../../scripts/edgs_source.py).

**The calibrated projection adapter is local integration code.** Git history
shows that `calibrated_projection()` was introduced on **2026-09-06** in commit
`21327005a4b699f53b72c1d91d9ed91c85dea52e` (`2132700`), titled
"Validate pinned EDGS geometry and RoMa CUDA execution." The
[SelfCap initializer](../../scripts/initialize-edgs-selfcap.py) and later
[Basketball cloud builder](../../scripts/basketball_temporal_cloud.py) import the
same function. The earlier wording that Basketball "adds its own" adapter did
not make this reuse history clear.

Its mathematics is the standard pinhole-camera projection, `P = K[R|t]`.
`K` contains the focal lengths and principal point, while `R` and `t` describe
the rotation and translation from world coordinates into the camera frame.
This established formulation is documented, for example, in
[OpenCV's camera geometry reference](https://docs.opencv.org/4.13.0/d9/d0c/group__calib3d.html).
The adapter itself is a small local PyTorch implementation.

The custom part packages that projection matrix for the pinned EDGS helper's
four-column, row-vector interface:

- Its triangulation equations use column index **2** for camera depth.
- Its reprojection-error calculation uses column index **3**.
- The adapter transposes the standard projection matrix and places the depth
  coefficients in both columns. These indices are zero-based.

The essential implementation is two lines:

```python
projection = intrinsics @ world_to_camera[:3]
return torch.cat((projection.T, projection[2, :, None]), dim=1)
```

The remaining code checks matrix dimensions, finite values, and coordinate
conventions. The reason for this arrangement is also recorded in the
[original compatibility notes](007-freetimegs.md#released-geometry-compatibility-check).
It uses processed-image pixel coordinates and camera depth; it is not a graphics
near/far clip-space projection.

**"Calibrated" means the adapter consumes existing camera calibration.** It does
not estimate or improve calibration. Basketball supplies its saved camera
matrices, this adapter converts their representation, and the unchanged EDGS
helper triangulates the matched pixels.

For **RoMa**, the upstream indoor matcher and pretrained weights are reused
without fine-tuning. The loader verifies the revision and weight hashes and
selects inference settings, including disabling symmetric matching and prediction
upsampling. RoMa's pretrained features include
[DINOv2](https://github.com/facebookresearch/dinov2).

**The dense initialization procedure is the largest addition in this project.**
It assembles those components into a Basketball-specific workflow:

| Added code | What it does |
|---|---|
| [basketball_temporal_masks.py](../../scripts/basketball_temporal_masks.py) | Runs ViPE with `person` and `basketball` queries on allowed training images, resetting tracking for each keyframe/successor pair. |
| [basketball_temporal_neighbors.py](../../scripts/basketball_temporal_neighbors.py) | Chooses neighboring cameras using shared sparse scene tracks. |
| [basketball_temporal_cloud.py](../../scripts/basketball_temporal_cloud.py) | Combines masks, RoMa matches, sampling, and triangulation. Adds person-cropped matching and maps crop coordinates back into the calibrated images. |
| [basketball_temporal_geometry.py](../../scripts/basketball_temporal_geometry.py) | Checks multiview support, depth, reprojection, and triangulation geometry. Uses OpenCV's Lucas–Kanade tracking to estimate adjacent-frame motion and triangulates its endpoints into 3D velocities. |
| [basketball_dense_fusion.py](../../scripts/basketball_dense_fusion.py) | Fuses measured static observations, creates static copies at the retained keyframe times, preserves foreground observations, and packages the initializer with provenance. |

The **coarse/person-cropped recipes are local integrations**. RoMa supplies
matching; EDGS supplies selected geometry code; these scripts decide which
observations to trust and how to turn them into FreeTimeGS initialization arrays.
The stock FreeTimeGsVanilla keyframe point-cloud combiner is not the complete
dense preparation workflow used here. These additions use established
techniques; "added here" does not imply that each technique is a new research
invention.

**At `de50e6a`, ViPE uses an adapted implementation of
[Segment-and-Track-Anything (SAM-Track)](https://github.com/z-x-yang/Segment-and-Track-Anything),
combining three pretrained models.** The source explicitly credits that
repository in
[TrackAnythingPipeline](https://github.com/samaust/vipe/blob/de50e6ab1066e32c96d32499a282ecaa2fbf2d90/vipe/priors/track_anything/__init__.py).

| Stage | Model used | What it does |
|---|---|---|
| **Detect people and balls** | [GroundingDINO](https://github.com/IDEA-Research/GroundingDINO), **Swin-T**, with a **BERT-base-uncased** text encoder | Takes the image and text queries such as `person` and `basketball`, then predicts bounding boxes. |
| **Produce pixel masks** | [Segment Anything — SAM](https://github.com/facebookresearch/segment-anything), **ViT-B** | Uses those bounding boxes as prompts to identify the pixels belonging to each detected object. |
| **Track masks across frames** | [DeAOT](https://github.com/yoxu515/aot-benchmark), **ResNet-50 DeAOT-L** | Propagates the existing masks into subsequent frames and maintains instance identities within that tracker. |

The checkpoint files selected by the code are:

- GroundingDINO: `groundingdino_swint_ogc.pth`
- SAM: `sam_vit_b_01ec64.pth`
- DeAOT: `R50_DeAOTL_PRE_YTB_DAV.pth`

The pinned
[detector loader](https://github.com/samaust/vipe/blob/de50e6ab1066e32c96d32499a282ecaa2fbf2d90/vipe/priors/track_anything/detector.py)
selects the GroundingDINO checkpoint; `TrackAnythingPipeline` selects the SAM
and DeAOT models and checkpoints.

**The implementations are bundled inside ViPE's source tree**, a practice
called *vendoring*:

```text
vipe/priors/track_anything/
├── groundingdino/   # Object detector implementation
├── sam/            # Segment Anything implementation
├── aot/            # AOT/DeAOT tracking implementation
├── detector.py     # Integration wrappers
├── segmentor.py
├── aot_tracker.py
└── seg_tracker.py
```

For example, the wrappers import `from .sam import ...` and
`from .groundingdino.models import ...`. They use these bundled copies, with
adaptations, rather than relying solely on separately installed SAM or
GroundingDINO packages.

The Basketball execution stack is **Python, PyTorch, torchvision, and CUDA**.
Hugging Face **Transformers** supplies BERT and its tokenizer. GroundingDINO
also uses ViPE's compiled `grounding_dino_ext` attention operator. NumPy,
Pillow, and OpenCV support image handling around the pipeline.

The user's fork adds runtime changes such as **shared model caching, processing
images and masks directly as GPU tensors, batched tracking-image encoding, and
device handling**. Those changes adapt existing model implementations and
pretrained weights.

For the Basketball experiments, the local adapter supplies the words **`person`
and `basketball`**. GroundingDINO performs the semantic selection; SAM produces
the boundaries. No new Basketball segmentation network is trained.

The [Basketball mask adapter](../../scripts/basketball_temporal_masks.py) creates
a fresh tracker for each camera/keyframe pair: detection and SAM segmentation
run on the keyframe, then DeAOT tracks its immediate successor. Consequently,
those instance IDs belong to that camera and pair; they do not establish player
identities across cameras. The Basketball adapter reuses this masking component
without using ViPE's complete pose/depth pipeline to replace the accepted
camera calibration.

**STG requires a separate qualification about "as is."** Its model, renderer,
losses, densification, and error-guided point insertion remain upstream-derived,
but the integration includes:

- Basketball camera/frame loading and complete checkpoint restoration.
- Training-loop hooks and a correction ensuring the final iteration performs
  its optimizer update.
- A fix initializing newly inserted Gaussian rotations to a valid identity
  quaternion.
- Dependency-loading and CUDA compilation compatibility changes.

The training adaptations are visible in
[stg_train_source.py](../../scripts/stg_train_source.py); scene loading and
checkpoint state are handled by [stg_scene.py](../../scripts/stg_scene.py) and
[stg_checkpoint.py](../../scripts/stg_checkpoint.py). The quaternion,
dependency-loading, and compilation fixes are patches in the external STG
checkout. A base commit alone therefore does not describe that checkout's
executed source. STG also inherits code from the original
[3D Gaussian Splatting](https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/)
implementation.

**The crossing repair is implemented here; it does not come from a separate
repair paper or repository.**

- **C** changes the local training selection to include frames 20–24 from the
  training cameras. It keeps the existing FreeTimeGsVanilla duration behavior.
- **D** includes those frames and adds the local duration correction: resolve
  the automatic setting to `0.2`, keep learned durations above the existing
  `0.02` rendering floor, and clear only the affected Adam moments while retaining
  optimizer step counters.

The frame selection is in
[basketball_crossing_train.py](../../scripts/basketball_crossing_train.py);
the new duration logic is in
[basketball_crossing_repair.py](../../scripts/basketball_crossing_repair.py).
The original temporal exclusion was this project's experiment protocol. The
duration defect was observed in the reproduction/configuration path used here;
it should not be attributed automatically to the FreeTimeGS paper or its
authors' implementation.

Both approved solutions reuse the frozen dense initializer and continue the
matching 50k checkpoint to 70k. C/D require no new masks or geometry in this
experiment. The [workflow explanation](basketball-crossing-repair/workflow-explanation.md)
records the `0.2` penalty threshold, `0.02` trainable floor, normalized time units,
user assessment, and limits of what the continuation results establish.

To reproduce these workflows elsewhere, the upstream repositories alone are
insufficient: the initialization, camera/time conventions, training adapters,
and—when using D—the duration repair are also required. The coarse/cropped
initializer choice remains independent of the C/D training-policy choice.
