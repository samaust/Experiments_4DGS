# 4DGS research and locally runnable implementations

[Repository overview](../README.md) · [Pretrained experiments](pretrained-experiments.md) · [Input data](input-data.md) · [Local creation](local-creation.md) · [Rendering](rendering.md)

Research date: **2026-09-05**. This is a bounded survey of publicly accessible papers, official implementations, and downloadable assets. It is not a claim to exhaust the literature. “Code available” means source was found; it does not mean this repository has reproduced the results.

For numerical quality comparisons and alternatives to our native STG renderer,
see [Native STG: published quality comparisons](stg-comparison.md). It covers
full versus lite STG, FreeTimeGS, MoE-GS, ATGS, FreeTimeGS++, and 7DGS, with
benchmark-specific results and implications for minimizing rendering artifacts.

## What counts as 4DGS?

Static 3D Gaussian Splatting optimizes spatial Gaussian primitives and their appearance from posed images. It provides useful background, but does not itself describe scene motion. Start with the [3DGS paper](https://arxiv.org/abs/2308.04079) and [official implementation](https://github.com/graphdeco-inria/gaussian-splatting).

| Representation | What changes with time? | What must be retained for rendering? |
| --- | --- | --- |
| Deformation-based dynamic Gaussians | A learned function moves or changes canonical 3D Gaussians | Canonical Gaussians, deformation network/grid, configuration |
| Native 4D primitives | A space-time Gaussian is conditioned on the requested time | Spatial and temporal parameters, appearance coefficients, matching rasterizer |
| Parametric spacetime Gaussians | Explicit trajectories, rotations, and temporal opacity | Motion/lifetime parameters and any appearance decoder |
| Per-frame 3DGS sequence | A separate Gaussian set is selected for each frame | Ordered frames and playback timing; interpolation requires an additional policy |

The first three rows describe different modeling choices; their files and renderers are not interchangeable. HUST uses a learned deformation field, Fudan models native 4D primitives, and SpacetimeGaussians uses parametric motion and temporal opacity. Sources: [Wu et al.](https://arxiv.org/abs/2310.08528), [Yang et al.](https://arxiv.org/abs/2310.10642), [Li et al.](https://arxiv.org/abs/2312.16812).

There is a second distinction: **per-scene optimization** creates a model for one capture, whereas **pretrained reconstruction** predicts a representation for new input. A downloadable checkpoint of a cooking scene is not a general-purpose world reconstruction model.

## Repository environment target

Use [uv, standard Python 3.14, Torch 2.13.0+cu130 and CUDA 13.0](environments.md). Legacy stacks below describe upstream provenance only. The [compatibility gates](environments.md#3-port-and-build-the-selected-method) distinguish dependency resolution, imports, extension builds and real checkpoint rendering; none of the native methods is certified on the target stack by this survey. Browser inspection does not depend on those ports.

## Methods worth investigating

The immediate experiment order is [existing scenes and rendering, then pretrained reconstruction](pretrained-experiments.md). Training recommendations below describe later options; they do not require training before evaluating a released checkpoint.

The last column is this repository's assessment for the intended workflow. Memory figures are author-reported unless stated otherwise; unknown means no reliable requirement was established in this review.

| Method and publication | Inputs and creation route | Local outputs and rendering | RTX 4090 relevance |
| --- | --- | --- | --- |
| **HUST 4DGaussians**, CVPR 2024. [Paper](https://arxiv.org/abs/2310.08528), [code](https://github.com/hustvl/4DGaussians), [project](https://guanjunwu.github.io/4dgs/) | Posed, timestamped images; scene optimization; synthetic and multi-view loaders | Canonical Gaussians plus deformation state; Python image/video renderer; remote training viewer | First synthetic baseline. Legacy Python 3.7 / PyTorch 1.13.1 environment needs compatibility checks. Target-workstation peak VRAM unknown. |
| **Fudan 4DGS**, ICLR 2024; extended native-primitives paper, 2024. [Original](https://arxiv.org/abs/2310.10642), [extension](https://arxiv.org/abs/2412.20720), [code](https://github.com/fudan-zvg/4d-gaussian-splatting) | Posed dynamic images; scene optimization; D-NeRF and Neural 3D input paths | Native 4D Gaussians with a dedicated rendering pipeline | Representation comparison after a baseline works. Do not assume the implementation includes every extension-paper feature. Hardware requirements refer back to 3DGS; exact custom-scene memory remains unknown. |
| **SpacetimeGaussians**, CVPR 2024. [Paper](https://arxiv.org/abs/2312.16812), [code](https://github.com/oppo-us-research/SpacetimeGaussians), [project](https://oppo-us-research.github.io/SpacetimeGaussians-website/) | Synchronized calibrated videos and initialization points; scene optimization | Lite/full variants; Python rendering; Windows native viewer; third-party browser viewer | Main multi-view baseline. README reports 24 GB for Neural 3D training, 48 GB for Technicolor. Begin with the short lite profile, not the 48 GB workload. |
| **Swift4D**, ICLR 2025. [Paper](https://arxiv.org/abs/2503.12307), [code](https://github.com/WuJH2001/Swift4d) | Posed dynamic captures; scene optimization with static/dynamic separation | Dynamic hash-based deformation and static Gaussians; upstream train/render commands | Efficiency comparison. README warns that other multi-view datasets need code adaptation and that large-motion VRU sequences use short chunks. Target memory unknown. |
| **Mango-GS**, ICLR 2026. [Paper](https://arxiv.org/abs/2603.11543), [code](https://github.com/htx0601/Mango-GS), [project](https://htx0601.github.io/Mango-GS/) | N3V or HyperNeRF-style data; scene optimization through temporally coupled control nodes | Training, rendering, metric scripts; downloadable scene models | Promising newer comparison. Release reports Python 3.8 / PyTorch 2.4.1+cu121; Ubuntu 24.04 and peak memory remain unverified here. |
| **NoPo4D**, 2026 preprint. [Paper](https://arxiv.org/abs/2605.22190), [code](https://github.com/bralani/NoPo4D), [weights](https://huggingface.co/bralani01/nopo4d) | Multi-view images with time/camera grouping; feed-forward reconstruction can estimate unknown poses | Dynamic Gaussians, predicted cameras/depth/flow; Python novel-view rendering API | Directly relevant pretrained candidate. Published setup requires Python ≥3.10 and CUDA. Memory scales with input views/frames; no verified 24 GB budget here. The reviewed release provides inference; do not assume full training/post-optimization reproduction is available. |
| **L4GM**, 2024. [Paper](https://arxiv.org/abs/2406.10324), [model card and code link](https://huggingface.co/jiawei011/L4GM) | Monocular object video; feed-forward reconstruction | Sequence of 3D Gaussian sets, with a separate interpolation model | Object-centric comparison, not the default for entire multi-view worlds. Card describes 256×256 input and typically 16 frames per pass; target memory unknown. |
| **4DGT**, NeurIPS 2025. [Paper](https://arxiv.org/abs/2506.08015), [code](https://github.com/facebookresearch/4DGT), [weights](https://huggingface.co/projectaria/4DGT) | Monocular egocentric scene video; pretrained transformer | Dynamic Gaussian predictions, novel-view rendering, and a local web GUI | Adjacent scene-scale alternative. Authors request at least 16 GB free VRAM for inference. Its input domain differs from synchronized synthetic multi-view captures. |
| **4C4D**, CVPR 2026. [Paper](https://arxiv.org/abs/2604.04063), [conference record](https://openaccess.thecvf.com/content/CVPR2026/html/Zhou_4C4D_4_Camera_4D_Gaussian_Splatting_CVPR_2026_paper.html), [code](https://github.com/yangzf-1023/4C4D) | Sparse multi-camera video; scene optimization | Native-4DGS-derived training and rendering code | Additional candidate if only a few views are available. Exact 4090 memory and dependency compatibility were not established. |

Recommendations prioritize available data paths and renderers over leaderboard rankings. Published speed numbers use different scenes, resolutions, hardware, preprocessing, and timing boundaries. They are not directly comparable and are not promises for a generated world.

## Hugging Face assets

| Repository | Asset type | How to use it locally |
| --- | --- | --- |
| [stack93/spacetimegaussians](https://huggingface.co/stack93/spacetimegaussians/tree/main) | Scene checkpoints and Windows viewer archives linked by the official implementation | Start with `n3d_sear_steak_lite_allcam.zip` for inspection. The Windows binaries are not Ubuntu executables. An all-camera checkpoint cannot provide a held-out-camera evaluation. |
| [htx0601/Mango-GS](https://huggingface.co/htx0601/Mango-GS) | Scene checkpoints | Use the matching Mango-GS loader. The documented scene bundle includes `cfg_args`, `point_cloud.ply`, and `deform.pth`. |
| [bralani01/nopo4d](https://huggingface.co/bralani01/nopo4d) | Reusable reconstruction weights | Requires the NoPo4D source and its backbone dependencies; the model card includes encoder and renderer usage. |
| [jiawei011/L4GM](https://huggingface.co/jiawei011/L4GM) | Reusable object reconstruction/interpolation models | Follow the linked implementation. Resolve the card's conflicting license statements before redistribution. |
| [projectaria/4DGT](https://huggingface.co/projectaria/4DGT) | Reusable transformer checkpoints | Full and first-stage checkpoints have different behavior. Download size is not peak inference VRAM. |

A Hugging Face paper page is bibliographic metadata; a Space is an application. Neither by itself establishes that weights or a local implementation can be downloaded. Inspect the actual files, model card, author-to-repository links, and dependencies.

## Licenses and asset provenance

This survey includes permissively licensed code and source-available research code. These labels are not interchangeable. The entries below record observed terms and unresolved provenance, rather than asserting that a top-level license covers every bundled component.

| Project | Code terms observed | Dependencies and weights |
| --- | --- | --- |
| HUST 4DGaussians | [Top-level Apache-2.0](https://github.com/hustvl/4DGaussians/blob/843d5ac636c37e4b611242287754f3d4ed150144/LICENSE.md) | Retained [source headers](https://github.com/hustvl/4DGaussians/blob/843d5ac636c37e4b611242287754f3d4ed150144/scene/dataset_readers.py) refer to noncommercial Inria terms. Audit inherited code and rasterizer submodules independently; the top-level change does not resolve all provenance. No separate weight terms verified. |
| Fudan 4DGS | [MIT](https://github.com/fudan-zvg/4d-gaussian-splatting/blob/main/LICENSE) | Built on 3DGS; inspect inherited files/submodules. No separately verified weight license in this review. |
| SpacetimeGaussians | [MIT for its own code](https://github.com/oppo-us-research/SpacetimeGaussians/blob/main/LICENSE) | [Bundled Gaussian-Splatting license](https://github.com/oppo-us-research/SpacetimeGaussians/blob/main/thirdparty/gaussian_splatting/LICENSE.md) has research/noncommercial restrictions. HF scene-weight terms are not separately explicit in the reviewed short card. |
| Swift4D | No clear top-level license found in the reviewed repository listing/README | Treat licensing as unresolved; public source is not sufficient evidence of an open-source grant. Inspect inherited components before reuse. |
| Mango-GS | [README](https://github.com/htx0601/Mango-GS) declares MIT | Check CUDA submodule licenses separately. Scene-weight terms were not independently established here. |
| NoPo4D | [Repository](https://github.com/bralani/NoPo4D) and [HF card](https://huggingface.co/bralani01/nopo4d) declare MIT | Audit the Depth Anything 3 backbone and other required components separately. |
| L4GM | HF metadata says Apache-2.0 | The same [card](https://huggingface.co/jiawei011/L4GM) states CC-BY-NC-SA-4.0 in its body and references LGM. Record this conflict, not a blanket permissive license. |
| 4DGT | [Code license](https://github.com/facebookresearch/4DGT) is Creative Commons-based | [Weights](https://huggingface.co/projectaria/4DGT) declare CC-BY-NC-SA-4.0; inherited projects have additional terms. Research-restricted candidate. |
| 4C4D | [MIT](https://github.com/yangzf-1023/4C4D/blob/main/LICENSE) | Also includes [Gaussian-Splatting terms](https://github.com/yangzf-1023/4C4D/blob/main/LICENSE_gaussian_splatting.md); inspect the initialization dependencies. |
| splaTV | [MIT](https://github.com/antimatter15/splaTV/blob/main/LICENSE) | Viewer licensing does not determine the license of a loaded scene. |
| FreeTimeGsVanilla (third-party reproduction) | [AGPL-3.0](https://github.com/OpsiClear-4DGS/FreeTimeGsVanilla/blob/911dcf4157a3ddf5c96d9147f97627480268fe0f/LICENSE) | Pin `911dcf4157a3ddf5c96d9147f97627480268fe0f`; not the author implementation. Local sparse initialization was generated from training images only, with per-cloud input hashes; it is not a released dense ROMA asset. SelfCap's dataset terms remain separate. |
| FreeTimeGS native dependencies | [gsplat Apache-2.0](https://github.com/nerfstudio-project/gsplat/blob/b60e917c95afc449c5be33a634f1f457e116ff5e/LICENSE); [fused-ssim MIT](https://github.com/rahul-goel/fused-ssim/blob/1272e21a282342e89537159e4bad508b19b34157/LICENSE) | gsplat pin `b60e917c95afc449c5be33a634f1f457e116ff5e`; fused-ssim pin `1272e21a282342e89537159e4bad508b19b34157`. GLM submodule `33b4a621a697a305bc3a7610d290677b96beb181` offers MIT or Happy Bunny terms. Native-binary hashes are recorded in the local GPU verification reports, not represented as pretrained-model licenses. |
| RoMa dense matcher | [MIT](https://github.com/Parskatt/RoMa/blob/77f8d68803526dcddfd9b7a46bc76125bdc25f15/LICENSE) | Standalone candidate pin `77f8d68803526dcddfd9b7a46bc76125bdc25f15`; EDGS runtime pin and acquired indoor/backbone hashes recorded below. The source identifies separate indoor/outdoor matcher assets and a DINOv2 ViT-L/14 backbone. No separate matcher-weight grant was independently established; do not assume the top-level code license resolves every asset. Standard DINOv2 code/weights are declared Apache-2.0 in its [README](https://github.com/facebookresearch/dinov2#license); this does not cover its separately licensed medical variants. |
| EDGS dense initializer | [Non-commercial academic research and/or non-commercial personal use only](https://github.com/CompVis/EDGS/blob/f90b022445fc88368f75e66e8fb34aea88372cac/LICENSE.txt) | Audited pin `f90b022445fc88368f75e66e8fb34aea88372cac`; other uses require a separate license. User confirmed qualifying intended use on 2026-09-06. Its RoMa submodule pin is `370117431ffc5dc000fb46f6e581b74bdb2c3ff8`, different from the standalone candidate above. Gaussian-Splatting dependencies and matcher/backbone assets require their own audits; permissive RoMa terms do not remove EDGS's restrictions. Preserve upstream copyright, conditions, and disclaimer with any redistributed source or binary derivatives. |

Dense-initializer audit updated 2026-09-06. Keep source inspection, dependency
installation, pretrained-weight acquisition, and scene-derived outputs distinct.
Before promoting a dense initializer to a tested recommendation, record its
selected weight URLs and hashes, applicable notices, exact compatibility changes,
and training-view-only input inventory. On 2026-09-06 the user confirmed that the
intended use qualifies as non-commercial academic research and/or non-commercial
personal use. This resolves the EDGS intended-use question for this work; it does
not grant broader commercial rights or waive notices and third-party terms.
The adapted dense SelfCap initialization described below is preprocessing, not a
trained-model result or a reproduction of the author's full initialization.

The EDGS-pinned RoMa revision is also checked out in `.local/RoMa-edgs`, with
its MIT notice retained and source imports verified. EDGS geometry helpers have
now executed in synthetic CPU tests via a thin loader; source, AST, and license
hashes are available from that loader. The geometry-only fast-path adapter retains
an exact copy of the upstream [EDGS notice](licenses/EDGS.txt) for attribution and
derivative-work obligations. This does not imply that EDGS and AGPL-licensed FreeTimeGS code
can be redistributed together under a single permissive license.

Released assets acquired on 2026-09-06 for the indoor EDGS candidate (local only,
not redistributed):

| Asset | Official source | SHA-256 |
| --- | --- | --- |
| RoMa indoor matcher | [Author release](https://github.com/Parskatt/storage/releases/download/roma/roma_indoor.pth) | `4d3dca889ae1ef245123dc62aab914475c7bbf41f2c8002606450fb6cf2d91e6` |
| Standard DINOv2 ViT-L/14 backbone | [Meta release](https://dl.fbaipublicfiles.com/dinov2/dinov2_vitl14/dinov2_vitl14_pretrain.pth) | `d5383ea8f4877b2472eb973e0fd72d557c7da5d3611bd527ceeb1d7162cbf428` |

These hashes identify the downloaded bytes; they are not publisher signatures.
The matcher release does not independently establish a separate weight-license
grant in the inspected page. Keep that uncertainty distinct from the RoMa code's
MIT notice and the standard DINOv2 code/weights' declared Apache-2.0 terms.
Do not infer unrestricted redistribution or commercial rights from this download.

Scene-derived assets: 24 training-only dense clouds in
`.local/data/selfcap/dance1-edgs-frameFRAME-20260906` (339,785–343,430 points each)
record every processed input image hash, source/license hashes, nearest-neighbor
pairs, filters, camera-time range, and archive digest. Camera `0015` is excluded
from geometry generation. The temporal FreeTimeGS archive at
`.local/data/selfcap/dance1-freetimegs-edgs-initialization-20260906/initialization.npz`
contains 4,106,783 points and has SHA-256
`e2753700453c55fa59f30fe5d9c14ba74627016445cefb6bc5176019d57de6b4`.
SelfCap dataset terms continue to apply; generated clouds do not become MIT
assets merely because the matcher code is MIT. Two supervised FreeTimeGS
integration segments have now trained through iteration 10. The complete local
checkpoint `.local/runs/freetimegs-selfcap-10-20260906/checkpoint-000010.pt` has
SHA-256 `265fda2ee8c9530e1643a90a020d8401bfd115d6900e3d39c79c3edc513fabd5`.
Its training configuration records the dense archive, training-only SfM reference
used for native normalization, source/binary hashes, cached LPIPS backbone, and
coordinate/time adaptations. These are locally generated research assets, not
author-released checkpoints or unrestricted pretrained weights. The subsequent
5,000-step checkpoint
`.local/runs/freetimegs-selfcap-5000-20260906/checkpoint-005000.pt` has SHA-256
`d964bc3ce2758be7c57e324d3f2343553d507a8df0048d2c79dbdf7c2852620f` and retains the
same source, dataset and initializer provenance. Its offline held-out renders
are likewise local research outputs, not separately licensed author assets. The
native STG Lite continuation later completed iteration 30,000; its final
checkpoint and rendered evidence are local outputs from the pinned STG source,
not released pretrained assets. The completed Lite checkpoint SHA-256 is
`8eac0b3373167db5ff2e5a17c757e9fe5938e60f4b0c8ad55820eff5b9d20d9c`.
Full has also completed 30,000 steps; its local checkpoint
`.local/runs/stg-full-selfcap-final-20260906/checkpoint.pt` has SHA-256
`1c810245d4faa182df201eaf00372b8dd7bc23b6e5a2ae8c1f7d0fb8a461a65a` and includes
the appearance decoder. Both retain the same audited SelfCap input and STG source
provenance. Their [final record](experiments/contender-native-stg-20260906.md)
links complete offline evidence and reproducible commands.

The final budget-limited FreeTimeGS continuation stopped at iteration 42,061.
Its local checkpoint
`.local/runs/freetimegs-selfcap-final-20260906/checkpoint-042061.pt` has SHA-256
`49d732ee75bbc85863acf4eb4b621683b3df51720a69d9e536197fa2a66f7856`.
It retains the same dense EDGS/RoMa initializer, SelfCap inputs, reproduction
source and dependency provenance as the 5,000-step pilot. Neither further
training nor rendering changes the applicable asset conditions or establishes
a separate unrestricted license for these local research outputs.

The final budget-limited ATGS continuation stopped at 61,008 microsteps
(20,336 optimizer updates). Its local bundle
`.local/runs/atgs-selfcap-final-20260906/checkpoint-061008-011` retains the
audited training-only midpoint initialization, SelfCap inputs and patched ATGS
source provenance. The `bundle.json` commit-marker SHA-256 is
`7e4d1157c133e7ec57b53aeeb11ef4b66c7cd38aec82ed956021941a39e3f621`; that marker
records each component's hash. This is locally trained research state, not an
author-released pretrained checkpoint. Existing source, recovered-rasterizer,
dependency and dataset conditions remain applicable.

## Research sources, revisions, and watchlist

The walkthrough reference revisions are HUST [`843d5ac636c37e4b611242287754f3d4ed150144`](https://github.com/hustvl/4DGaussians/tree/843d5ac636c37e4b611242287754f3d4ed150144), SpacetimeGaussians [`427abfc`](https://github.com/oppo-us-research/SpacetimeGaussians/commit/427abfc), and splaTV [`8b313fe`](https://github.com/antimatter15/splaTV/commit/8b313fe). The latter two are upstream abbreviated commit IDs; expand them with `git rev-parse HEAD` after checkout and save the result with an experiment. These are documentation references, not certified environment lockfiles. General comparison links track upstream development.

The search covered foundational 2023–2024 methods and 2025–2026 releases, including sparse-view reconstruction and downloadable pretrained models. GitHub and HF availability were checked separately from paper claims. arXiv supplies manuscripts; official CVPR proceedings and author-linked repositories help establish publication and implementation provenance.

[Multi4D](https://github.com/BatFaceWayne/Multi4D), [arXiv:2606.22197](https://arxiv.org/abs/2606.22197), is a watchlist entry: the reviewed repository says the implementation is coming soon. Do not list it as a runnable baseline. World-generation systems, human-only capture pipelines, static-only reconstruction, and proprietary hosted services are not expanded into walkthroughs here.

To update this survey, recheck released files and entry points, follow papers to their official code, inspect license changes, and record the review date. Promote a method to a tested recommendation only after recording an actual local run using the [experiment template](local-creation.md#experiment-record).

## ViPE Basketball prior audit — 2026-09-06

The pinned Tridi ViPE fork `de50e6ab1066e32c96d32499a282ecaa2fbf2d90`
was used unchanged for the [blocked Basketball pilot](experiments/basketball-calibration-20260906.md).
All listed assets were already locally cached; no model weights were downloaded
in this task. Listed URLs are the origins encoded by the pinned loaders or model
repositories, not independently verified historical download logs. Full cached
file hashes, including model configurations and BERT tokenizer assets, are in
[the evidence JSON](experiments/basketball-calibration-20260906.json).

| Component | Source/weight terms and origin |
| --- | --- |
| ViPE | Top-level source is Apache-2.0; its bundled third-party notices have separate terms. This does not make every dependency or weight Apache-licensed. |
| GeoCalib | [Author license statement](https://github.com/cvg/GeoCalib#license): source Apache-2.0, trained weights **CC BY 4.0**. Retain attribution for the weight asset. Used cached [pinhole v1.0](https://github.com/cvg/GeoCalib/releases/download/v1.0/geocalib-pinhole.tar), SHA-256 `86d6aeacd8bbd974c59ce39f61854e00d36911c732ad89be471476fd708722ac`. |
| UniDepth V2 | [Source statement](https://github.com/lpiccinelli-eth/UniDepth#license) and [model card](https://huggingface.co/lpiccinelli/unidepth-v2-vitl14): **CC BY-NC 4.0**, including noncommercial restriction. Cached ViT-L snapshot `52b349b514bd8b47642f67ac78cb7b5dc5c51dd9`; model SHA-256 `ba73d3de735302ccc64a50f1e557122050c4b1893e6060b28dba05d6af3e67c6`. Import audited; inference not reached. |
| TrackAnything | Bundled wrapper and [upstream project](https://github.com/z-x-yang/Segment-and-Track-Anything#license) are **AGPL-3.0**. Preserve applicable copyleft/source obligations when distributing derivatives or providing modified software over a network. Upstream separately addresses proprietary commercial use. No such distribution/deployment is performed here. |
| SAM ViT-B | [Author repository](https://github.com/facebookresearch/segment-anything#license) provides Apache-2.0 code/model terms; dataset licensing is separate. Cached [author checkpoint](https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth), SHA-256 `ec2df62732614e57411cdcf32a23ffdf28910380d03139ee0f4fcbe91eb8c912`. |
| DeAOT R50 | [AOT benchmark](https://github.com/yoxu515/aot-benchmark) provides its own source license. ViPE requests Google Drive asset `1QoChMkTVxdYZ_eBlZhK2acq9KMQZccPJ`; cached SHA-256 `7e8a8d83310739bac02817f6bf48b6bbe2bbd7d5325722f1084088eb3aee1e06`. No separate weight grant was independently established in this audit. |
| GroundingDINO | [Author source](https://github.com/IDEA-Research/GroundingDINO) is Apache-2.0. ViPE requests [Swin-T OGC weights](https://huggingface.co/ShilongLiu/GroundingDINO/resolve/main/groundingdino_swint_ogc.pth); cached SHA-256 `3b3ca2563c77c69f651d7bd133e97139c186df06231157a64c507099c52bc799`. Keep the source grant distinct from any independently established asset terms. BERT assets are separately hashed in the evidence. |

Only GeoCalib inference ran before the fixed-camera intrinsic stability gate
failed. Cached availability/imports do not demonstrate depth or masking quality.
No calibration-derived metric scale, shared rig, or downstream result is claimed.


The [authorized 25% continuation](experiments/basketball-calibration-20260906.md#authorized-25-continuation)
subsequently exercised the cached UniDepth and TrackAnything models successfully
on the four pilot cameras. No new weights were downloaded. The all-camera
intrinsic pass then failed at camera 5; all-camera depth/masks and downstream
geometry remain unexecuted. This supersedes the earlier pilot-only inference
status above, while preserving the same dependency-specific licensing audit.


After user removal of camera 5, the
[33-camera continuation](experiments/basketball-no-camera5.md) generated all
retained priors and tested masked SIFT, the fixed RADIAL alternative and one
bounded pass with the already audited RoMa pin/weights. No new dependencies or
weights were downloaded and no third-party checkout was modified. The final
converged training-rig candidates still failed independent-window pose stability;
no accepted estimated calibration, metric scale or model result was produced.


[Revision-one recovery](experiments/basketball-rev1.md) reuses the same pinned
models and environments. Fixed principal points improve, but do not pass, rig
stability; expanded GeoCalib observations fail the unchanged 25% gate for cameras
4, 8 and 17. Partial automatic focus screening detects no sustained change on
existing masked samples but is inconclusive for the planned ten-frame check.
No new model weights, additional RoMa inference or downstream training were used.
