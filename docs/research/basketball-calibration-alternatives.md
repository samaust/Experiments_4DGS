# Basketball DG calibration alternatives

Investigation date: 2026-09-07. Protocol: [Plan 006](../../plans/plan_006.md).
Results and the recommendation are in the [measured experiment](../experiments/basketball-calibration-alternatives.md).
Paper rankings below are author evidence, not reproduced DG calibration accuracy.

## Dataset calibration audit

The [official Hugging Face release](https://huggingface.co/datasets/BestWJH/VRU_Basketball/tree/8592b0ddd27938e2c12dbd592fca2ecca54dec38)
contains DG, GZ and Long360 archives. The locally audited DG ZIP contains exactly
34 MP4 files, named 0–33, and no calibration. Its decoded videos are 1920×1080,
25 fps, 250 frames. The dataset card's general statement of 36 views does not
override that physical file inventory. Its prescribed held-outs are 0,10,20,30.

[Swift4D](https://github.com/WuJH2001/Swift4D/tree/5cc270897a4af2e6148b1951d2721bdc286a6e4d)
links [VRU-Basketball](https://github.com/WuJH2001/VRU-Basketball/tree/d60bd449e0ded02a0b3623cb49bff7c9662e0c18),
whose release note points to a Baidu drive rather than shipping camera files.
Its contents have not been authenticated or established compatible with this DG
release. [LocalDyGS](https://github.com/WuJH2001/LocalDyGS) offers a processed
**GZ** camera/point-cloud archive and describes additional undistortion steps.
GZ calibration is not compatible evidence for DG. No verified reusable DG
calibration was discovered in these checked files. This is a bounded provenance
audit, not proof that calibration cannot exist elsewhere.

## Released implementation matrix

Full source and checkpoint revisions are recorded alongside the machine-readable
experiment evidence. Short source revisions below identify the audited release;
for COLMAP, the tested wheel is distinguished from inspected development source.

| Route and source | Inputs and actual outputs | Camera/scene constraints | Local installation and inference status |
| --- | --- | --- | --- |
| [COLMAP global / GLOMAP](https://github.com/colmap/colmap), tested PyCOLMAP 4.2.0 (`be5e29168d4aff238409d60424812df66aac919f`), audited main `ed8080b`; GLOMAP ECCV 2024 | Images or feature database → K, world-to-camera poses, sparse tracks, COLMAP native export. Selected model is SIMPLE_PINHOLE. | Per-camera K; masks enforced at keypoints. Static windows can pool observations into one physical pose. Needs a connected, geometrically reliable correspondence graph; no metric scale or synchronization from ordinary SfM. | Installed in `calibration-global`; SuperPoint/LightGlue frontend, then view-graph calibration on a private DB copy. Incremental control uses identical pre-calibration matches. |
| [MASt3R-SfM](https://github.com/naver/mast3r/tree/f5209afc300cec36239a7ac992263f36847bbba0), 3DV 2025 | Images → sparse global alignment, per-view K, camera-to-world poses, sparse/dense geometry. Uses actual `sparse_global_alignment`, not `demo_glomap.py`. | Independent intrinsics; learned wide-baseline correspondence initialization. No native person mask in the exercised API: neutralized dynamic pixels are an explicit input adaptation. Temporal camera tying needs the common rig adapter. | Installed in `calibration-mast3r`; pinned DUSt3R `3cc8c88`, CroCo `d7de070`. Narrow [SciPy API patch](../../patches/mast3r-scipy-distance.patch). Upstream Torch RoPE fallback retained. |
| [VGGSfM](https://github.com/facebookresearch/vggsfm/tree/e1d9d2eb2b3575525792206fb94b2c749c58dc50), CVPR 2024; released v2 differs from paper v1.1 | Images, optional binary dynamic masks → camera parameters, tracks, COLMAP sparse export. | `shared_camera=False` for independent cameras; dynamic-mask polarity is **1 = excluded**. Chunked tracking and triangulation support memory control. Video mode is sequential-camera processing, not automatically a fixed multi-camera rig. | Released PyCOLMAP 3.10.0 dependency has no CPython 3.14 wheel; installation failed. No DG inference claimed. A source/API port is required. |
| [VGGT-Ω](https://github.com/facebookresearch/vggt-omega/tree/f6c3c5bb26cdaa2e1525e8f9d08acb74ebfcf447), CVPR 2026 | Images → pose encoding, K/extrinsics through `encoding_to_camera`, depth/confidence. | Released 512 reconstruction variant; inferred pinhole model, no demonstrated distortion or synchronization estimation. Direct prediction gives coverage but does not guarantee reliable geometry. | Package and model imports pass in `calibration-vggt-omega`. Official 512 weight access returns **403 GatedRepoError**. No alternate checkpoint substituted. |
| [Depth Anything 3](https://github.com/ByteDance-Seed/Depth-Anything-3/tree/3d835ec1a5802d64a8b8b15f817a1ab54809bfe4), arXiv 2511.10647 | Images, optional known calibration → depth, confidence, K, world-to-camera extrinsics. Our runs supply no calibration. | DA3-GIANT-1.1 is relative geometry; it must not inherit metric claims from DA3METRIC or NESTED variants. `use_ray_pose=True` selects the slower accuracy-oriented option. No distortion or synchronization output. | Installed in `calibration-da3` using the existing [Python 3.14 patch](../../patches/da3-python314.patch). Refreshed weights pinned; native NPZ and converted cameras saved. |
| [Pi3 / Pi3X](https://github.com/yyfz/Pi3/tree/9fa3ddb3f8d53041f8b2738df404f62223bbaa7b), Pi3 ICLR 2026 | Pi3X image-only mode predicts local/world geometry and camera-to-world poses; recover K from predicted rays. Optional geometric conditioning is separate. | Pi3X is a later engineering update, not interchangeable with the original paper's Pi3 results. A centered-principal-point recovery option is documented. No established lens-distortion or synchronization recovery. | Released requirements demand Torch 2.5.1/torchvision 0.20.1, conflicting with this repository's required ABI. Checkpoint metadata pinned; no inference under a silently altered stack. |
| [MapAnything](https://github.com/facebookresearch/map-anything/tree/3d10cf7a3016fc0f9bb13a071ee66c47b10be0d9), 3DV 2026 | Images alone, or optional rays/poses/depth → K, OpenCV camera-to-world poses, depth and world geometry. | Independent predicted intrinsics. Metric output is a learned estimate; DG metric scale still needs independent validation. Dynamic pixels neutralized before preprocessing; geometry masks do not themselves validate camera support. | Installed in `calibration-map-anything`; image-only weights pinned. Memory-efficient inference, minibatch 1, bf16. Native predictions retained; upstream crop transform inverted for exported K. |

The GLOMAP repository is archived and points to COLMAP's global mapper. The
[official CLI workflow](https://colmap.github.io/cli.html) places
`view_graph_calibrator` before global mapping when trustworthy focal priors are
absent. Calibration modifies the database; the shared frontend is preserved.

## Code and checkpoint licenses

These are recorded license identifiers, not a legal compatibility opinion.

| Route | Code | Weights |
| --- | --- | --- |
| COLMAP / frontend | COLMAP BSD-3-Clause; LightGlue Apache-2.0; SuperPoint inference follows the separate Magic Leap agreement | LightGlue Apache-2.0; SuperPoint [Magic Leap noncommercial research agreement](https://github.com/magicleap/SuperPointPretrainedNetwork/blob/master/LICENSE); checkpoint hashes recorded separately |
| MASt3R | CC-BY-NC-SA-4.0 | CC-BY-NC-SA-4.0 plus upstream `CHECKPOINTS_NOTICE` training-data conditions; no blanket commercial permission inferred |
| VGGSfM | CC-BY-NC-4.0 | Official Hugging Face card: CC-BY-NC-4.0 |
| VGGT-Ω | FAIR Noncommercial Research License | Gated research materials; exact downloaded checkpoint terms cannot be verified until access is granted |
| DA3 | Apache-2.0 | DA3-GIANT-1.1: CC-BY-NC-4.0 |
| Pi3X | BSD-3-Clause | Official Pi3X card: CC-BY-NC-4.0 |
| MapAnything | Apache-2.0 | Tested `facebook/map-anything`: CC-BY-NC-4.0; separate Apache weights exist but are not substituted |

## How comparative evidence informs this campaign

- [MASt3R-SfM](https://arxiv.org/abs/2409.19152) motivates testing learned matching
  and global alignment on sparse and variable-size view collections. Its
  released repository explicitly separates this pipeline from experimental
  COLMAP/GLOMAP examples. Its benchmark results are not this rig's 0.5° test.
- [DA3 v1 benchmark](https://arxiv.org/html/2511.10647v1) compares camera-pose
  estimation on HiRoom, ETH3D, DTU, 7Scenes and ScanNet++. Unknown-pose results
  must be separated from pose-conditioned reconstruction. The released benchmark
  uses AUC@3°/30°; neither is equivalent to maximum center error after one Sim(3).
  The tested refreshed GIANT-1.1 weights also differ from the original paper
  release, so original tables are contextual evidence rather than predictions.
- [RealX3D v1](https://arxiv.org/html/2512.23437v1) includes physical defocus,
  motion blur, illumination and occlusion. Reference-view pose estimation uses
  calibrated intrinsics and laser-scan registration. Thus its reference geometry
  is stronger than repeatability, and its different pose/geometry rankings
  motivate multiple families rather than declaring a universal winner on DG.
- [Dense-match rig calibration](https://arxiv.org/abs/2512.15608) motivates
  correspondence-cycle filtering, initialization and camera-model ablations.
  An official runnable release was not verified; it is not counted as an
  independently executed candidate.
- [VGGT-Ω's upstream notice](https://github.com/facebookresearch/vggt-omega)
  reports possible benchmark contamination in an ancestor checkpoint and
  potentially inflated reported 1B results. Do not use those tables as a
  quantitative ordering for this investigation.

No paper AUC, translation-direction statistic, or training reprojection error is
treated as evidence that all 34 DG cameras pass validation. Failure handling in
our comparison rejects incomplete, nonfinite and invalid-focal models from the
ranking, including otherwise converged reconstructions.

## Conditional follow-ups

| Follow-up | Verified prerequisite / limitation | Decision rule |
| --- | --- | --- |
| [Dense-SfM](https://github.com/IceTea-CV/DenseSfM-Refine/tree/6b827724ed5e7abf2b04c1000faaae922e7f9dbb), CVPR 2025 | Release provides full SfM and standalone refinement, but omits the paper's Gaussian track extension. Custom COLMAP and RoIAlign builds required. `triangulation_mode=True` fixes poses, so it must be **False** for calibration refinement. Released Torch 2.5.1 conflicts with the required stack. | Installation gate fails before a GPU pilot; retain as adaptation pending, not a measured geometric failure. |
| [MP-SfM](https://github.com/cvg/mpsfm/tree/fa49640862391437865b2fd89ca3db3e6948b63b), CVPR 2025 | Requires per-image/shared intrinsic YAML, forked COLMAP and pyceres; released requirements include `cupy-cuda12x`, MMCV and depth-prior submodules. Can accept independent K, but published known-intrinsic results are not demonstrated self-calibration. | Hybrid only on a complete initialization with independently estimated K; custom source/ABI adaptation remains to be validated. |
| [CasCalib](https://github.com/jamestang1998/CasCalib/tree/ee641452a42ce792b88d89ca967726b2d387725c), FG 2024 | Single-view code takes assumed neck height `h`, filters body angles, infers a ground plane from ankle detections, then aligns time and cameras. No measured common player height or verified upright grounded observations are supplied for DG. | Prerequisite audit does not pass. Basketball jumping/crouching and variable player height need evidence before a pilot; do not introduce a fictitious height. |

Methods requiring targets, measured geometry, known poses, or established motion
synchronization are not treated as interchangeable automatic self-calibration
implementations. The remaining measured work and unresolved gates are listed in
the experiment report, rather than converted into unsupported recommendations.

## Recommendation from the DG measurements

Use the validated incremental COLMAP initialization with ordinary masked static
SIFT support and common robust BA refining one centered square-pixel focal and
one radial term per physical camera. All 34 cameras pass the declared final
static-track reprojection gates. Full-rig early/late worst-seed repeatability is
0.163815° rotation and 0.354980% center disagreement; final worst-camera median
and p95 are 0.505951 and 2.228025 pixels. See the
[export and handoff](../experiments/basketball-calibration-alternatives.md#plan-005-handoff).

MapAnything and MASt3R ranked first and second on snapshots but did not yield a
configuration passing all later gates. This supports testing initialization,
camera model and correspondence robustness together rather than assuming a
learned model's paper ranking predicts sub-degree rig calibration. The selected
radial configuration substantially outperforms focal-only fitting on this rig;
it is evidence for this configuration, not proof of the lenses' true distortion.

The recommendation is limited to estimated static calibration. Metric scale,
synchronization and downstream dynamic-scene training require their separate
Plan 005 checks. The matching-policy failures and unmeasured installation/access
failures remain part of the evidence; no blocked model is assigned a geometric rank.
