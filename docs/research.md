# 4DGS research and locally runnable implementations

[Repository overview](../README.md) · [Pretrained experiments](pretrained-experiments.md) · [Input data](input-data.md) · [Local creation](local-creation.md) · [Rendering](rendering.md)

Research date: **2026-09-05**. This is a bounded survey of publicly accessible papers, official implementations, and downloadable assets. It is not a claim to exhaust the literature. “Code available” means source was found; it does not mean this repository has reproduced the results.

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

## Research sources, revisions, and watchlist

The walkthrough reference revisions are HUST [`843d5ac636c37e4b611242287754f3d4ed150144`](https://github.com/hustvl/4DGaussians/tree/843d5ac636c37e4b611242287754f3d4ed150144), SpacetimeGaussians [`427abfc`](https://github.com/oppo-us-research/SpacetimeGaussians/commit/427abfc), and splaTV [`8b313fe`](https://github.com/antimatter15/splaTV/commit/8b313fe). The latter two are upstream abbreviated commit IDs; expand them with `git rev-parse HEAD` after checkout and save the result with an experiment. These are documentation references, not certified environment lockfiles. General comparison links track upstream development.

The search covered foundational 2023–2024 methods and 2025–2026 releases, including sparse-view reconstruction and downloadable pretrained models. GitHub and HF availability were checked separately from paper claims. arXiv supplies manuscripts; official CVPR proceedings and author-linked repositories help establish publication and implementation provenance.

[Multi4D](https://github.com/BatFaceWayne/Multi4D), [arXiv:2606.22197](https://arxiv.org/abs/2606.22197), is a watchlist entry: the reviewed repository says the implementation is coming soon. Do not list it as a runnable baseline. World-generation systems, human-only capture pipelines, static-only reconstruction, and proprietary hosted services are not expanded into walkthroughs here.

To update this survey, recheck released files and entry points, follow papers to their official code, inspect license changes, and record the review date. Promote a method to a tested recommendation only after recording an actual local run using the [experiment template](local-creation.md#experiment-record).
