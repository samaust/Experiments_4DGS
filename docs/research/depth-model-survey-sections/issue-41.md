# Multi-view depth and geometric models — issue #41

Evidence cutoff and access date: **2026-09-30**. This section addresses [#41](https://github.com/samaust/Experiments_4DGS/issues/41) under [#36](https://github.com/samaust/Experiments_4DGS/issues/36). It contains published evidence and release checks, not local measurements. The [model inventory](../depth-model-survey-data/issue-41/models.csv), [observations](../depth-model-survey-data/issue-41/benchmarks.csv), [licenses](../depth-model-survey-data/issue-41/licenses.csv), and [search log](../depth-model-survey-data/issue-41/search-log.csv) retain exact revisions and comparison limits.

Multi-view geometry is a plausible additional role for calibrated Basketball footage. It is not automatically a replacement for monocular physical-scale estimation: several strong models return arbitrary-scale geometry, and many reported improvements use ground-truth alignment. Synchronized views of one instant and a video of moving players also pose different problems. None of the inspected comparisons measures this project's final 4DGS render quality.

## Inputs and released identities

| Family / exact release group | Views, cameras and output | Release qualification |
| --- | --- | --- |
| VGGT-1B / VGGT-1B-Commercial | RGB image sets; inferred cameras; arbitrary-scale depth and points | Original and commercial weights differ; original paper scores are not commercial-checkpoint measurements. Dynamic tracking in the paper uses a separately fine-tuned backbone. [VGGT paper](https://arxiv.org/abs/2503.11651v1), [release](https://github.com/facebookresearch/vggt/tree/a288dd0f14786c93483e45524328726ab7b1b4ce). |
| DA3-GIANT, LARGE, BASE, SMALL | Any-view RGB; optional intrinsics/extrinsics; relative camera-z depth and rays | Keep unconditioned and known-camera evaluations separate. Original Giant/Large deprecated; Giant/Large-1.1 retrained after a training bug. Paper and release parameter counts also differ. [Paper](https://arxiv.org/abs/2511.10647v1), [release](https://github.com/ByteDance-Seed/Depth-Anything-3/tree/3d835ec1a5802d64a8b8b15f817a1ab54809bfe4). |
| DA3NESTED-GIANT-LARGE / -1.1 | Any-view geometry plus monocular metric scaler | Returns metric depth; separate from D2 DA3METRIC-LARGE and from plain DA3 paper rows. |
| MapAnything / MapAnything-Apache, each v1 and current | RGB sets; optional calibration, poses or depth; metric ray-depth/ray/pose representation | September releases archived as `-v1`; current releases dated January 2026. Apache weights use different training data. Neither change inherits older NC scores. [Paper](https://arxiv.org/abs/2509.13414v1), [release](https://github.com/facebookresearch/map-anything/tree/3d10cf7a3016fc0f9bb13a071ee66c47b10be0d9). |
| Pi3 / Pi3X | Pi3: unordered images, inferred cameras, scale-invariant points. Pi3X: optional cameras/depth and approximate metric scale | Pi3X is a later engineering update, not the Pi3 paper model. [Paper](https://arxiv.org/abs/2507.13347v1), [release](https://github.com/yyfz/Pi3/tree/9fa3ddb3f8d53041f8b2738df404f62223bbaa7b). |
| DUSt3R ViT-L 512 DPT / MASt3R ViT-L 512 CatMLP+DPT metric / Fast3R ViT-L 512 | Pairwise alignment / matching and alignment / direct set processing; cameras need not be given | Historical geometric baselines remain useful. MASt3R is metric-trained; that does not demonstrate accurate absolute scale on unseen scenes. [DUSt3R](https://github.com/naver/dust3r/tree/4c24a6ebf04809f2cfe59915e51779c8984aaa40), [MASt3R](https://github.com/naver/mast3r/tree/f5209afc300cec36239a7ac992263f36847bbba0), [Fast3R](https://github.com/facebookresearch/fast3r/tree/33104d4b5b8df43795ecded236194958bbdac572). |
| VGGT-Ω 1B-512 / 1B-416-Reproduction | RGB image sets or dynamic video; predicted depth and cameras | Gated, distinct artifacts. Original benchmark contamination risk was inconclusive; authors designate the September reproduction checkpoint for future benchmarking. The 512 release is designated for in-the-wild use, **not benchmarking**. The paper's 10B headline is not a released 1B score. [Release and reproduction disclosure](https://github.com/facebookresearch/vggt-omega/tree/48b23c8ce72c9a8fcf987f0d7f43d8e4870759f6). |

The established geometry comparisons primarily concern a common static scene. Reported dynamic benchmarks below do not establish synchronization tolerances, occlusion recovery or moving-player depth boundaries on Basketball. Native resolutions and camera models also require a future evaluation of how calibration survives resizing from the project's 960×540 images.

## Published comparisons with information regimes visible

**Reconstructed geometry, not pixel depth.** DA3 v1 Table 3 evaluates DTU evaluation scans using all views, background removal and fusion. Pose-free reconstruction uses trajectory alignment to ground truth. Known-pose columns have additional camera information; they do not imply every baseline natively conditions its network on cameras. Resolution and some alignment details are insufficiently specified. Smaller is better. [DA3 v1, §§6–7, Table 3](https://arxiv.org/abs/2511.10647v1).

| Evaluated row | DTU Chamfer, no poses (mm) | DTU Chamfer, supplied poses (mm) |
| --- | ---: | ---: |
| VGGT | 2.05 | 1.44 |
| Pi3 | 3.28 | 1.72 |
| DA3-Giant | 1.85 | 1.85 |
| DA3-Large | 2.08 | 1.23 |
| DA3-Base | 2.87 | 2.36 |
| MapAnything, release hash unspecified | 7.91 | 3.97 |

These are source-specific observations: supplied poses do not improve every row. They must not be merged with VGGT's original DTU Table 2, whose camera access, fusion and evaluation setup differ. That table also contains calibrated MASt3R triangulation and cost-volume MVS methods; these are not unknown-camera competitors.

**Independent depth evaluation with GT cameras and scale.** E3D-Bench v1 Table 2 / Appendix B.1 uses ground-truth intrinsics and poses, per-view median depth alignment, quasi-optimal source views with a fallback, native input resolutions and original-resolution outputs. Exact view count is unreported. Higher is better. [E3D-Bench v1](https://arxiv.org/abs/2506.01933v1).

| Evaluated row | DTU δ < 1.03 (%) | KITTI δ < 1.03 (%) |
| --- | ---: | ---: |
| DUSt3R / LSM shared weights | 75.685 | 39.495 |
| MASt3R | 68.301 | 46.805 |
| VGGT | 94.305 | 41.309 |
| Fast3R | 62.120 | 26.734 |

VGGT's advantage on DTU does not extend to MASt3R on KITTI under this test. None of these aligned percentages establishes absolute scale. E3D's displayed AbsRel normalization is unclear, so this section transcribes its explicitly defined percentage metric instead of silently dividing those values.

**Later independent scale check.** UAV3DCrop v1 Table 6 evaluates RGB-only subsets, reserves reference cameras for scoring, aligns geometry by scene, and averages by sequence. Its domain is agricultural imagery, not indoor sport. Exact checkpoint hashes are absent; the MapAnything row cannot support an Apache-release accuracy claim. Smaller is better. [UAV3DCrop v1, Track B / Table 6](https://arxiv.org/abs/2608.06404v1).

| Evaluated family | Aligned z-depth AbsRel | Unaligned scale AbsRel |
| --- | ---: | ---: |
| MapAnything, variant unresolved | 0.033 | 0.027 |
| VGGT | 0.082 | 0.965 |
| Pi3 | 0.055 | 0.963 |
| MASt3R | 0.148 | 0.890 |

The raw-scale column intentionally exposes the limitation of nonmetric models; it is not a fair contest between models with identical output contracts.

**Pose and dynamics remain separate tasks.** DA3 Table 2 reports ETH3D pose AUC@3° of 26.3 for VGGT, 35.2 for Pi3 and 48.4 for DA3-Giant; these do not measure depth or rendering. VGGT-Ω's original 1B Sintel depth AbsRel / pose AUC@3° are 0.097 / 35.3; its replacement reports 0.094 / 35.5. Depth-alignment details remain unknown, and the original result carries the later contamination qualification. [DA3 Table 2](https://arxiv.org/abs/2511.10647v1), [Ω Tables 1–2](https://arxiv.org/abs/2605.15195v1), [replacement results](https://github.com/facebookresearch/vggt-omega/blob/48b23c8ce72c9a8fcf987f0d7f43d8e4870759f6/reproduction.md).

**Resources.** DA3 Table 8 reports throughput on an A100 for a scene of 32 images at 504×336: VGGT 34.1, DA3-Giant 37.6, Large 78.37, Base 126.5 and Small 160.5 frames/s. Precision, warmup and full timing boundaries are unspecified. These are old evaluated variants; they are not measurements for 1.1, current VGGT memory fixes, or this host. No observed resource limit for the Basketball camera/view count is available.

## Commercial findings

These findings describe inspected author terms, not an exhaustive dependency audit. Each pinned contender has four separate fields in the license CSV.

| Exact artifact group | Code | Weights | Inference / outputs | Commercial path |
| --- | --- | --- | --- | --- |
| VGGT original / Commercial | Custom permissive grant + AUP | Original NC; Commercial conditional permission | Commercial checkpoint permits commercial inference subject to AUP; output/result provisions must be retained | Explicit gated commercial checkpoint; access was not requested. [License](https://github.com/facebookresearch/vggt/blob/a288dd0f14786c93483e45524328726ab7b1b4ce/LICENSE.txt). |
| DA3 Base / Small | Apache-2.0 | Apache-2.0 | Commercial inference permitted; no separate output restriction found | Public checkpoints. |
| DA3 Giant / original Large / Nested, including Giant/Nested-1.1 | Apache-2.0 | CC-BY-NC-4.0 | Commercial inference restricted; no automatic assertion that every output is CC-licensed | No explicit negotiated offer found. |
| DA3-LARGE-1.1 | Apache-2.0 | **Conflict:** model card Apache; author README NC | Unresolved; omit from affirmative commercial shortlist | [Exact card](https://huggingface.co/depth-anything/DA3-LARGE-1.1/blob/0e109ae307c5982f319a67cf6f9f99ccdc0ec97c/README.md) versus [author table](https://github.com/ByteDance-Seed/Depth-Anything-3/blob/3d835ec1a5802d64a8b8b15f817a1ab54809bfe4/README.md). |
| MapAnything Apache v1/current | Apache-2.0 | Apache-2.0 | Commercial inference permitted; no separate output restriction found | Explicit alternative to NC weights; different training set. [Author release terms](https://github.com/facebookresearch/map-anything/blob/3d10cf7a3016fc0f9bb13a071ee66c47b10be0d9/README.md#code-license). |
| MapAnything NC v1/current | Apache-2.0 | CC-BY-NC-4.0 | Commercial inference restricted; output-specific rights unresolved | Apache alternative, not permission for the NC checkpoint. |
| Pi3 / Pi3X | BSD-3-Clause | Current author statement NC; original Pi3 card conflicts | Original Pi3 permission unresolved; Pi3X commercial inference restricted | Original Pi3 card explicitly invites commercial inquiry, but no offered terms or licensing-specific address. [Card](https://huggingface.co/yyfz233/Pi3/blob/ae722e7039287d0c8fde9f11f197f804f44b510c/README.md), [current statement](https://github.com/yyfz/Pi3/blob/9fa3ddb3f8d53041f8b2738df404f62223bbaa7b/README.md#-license). |
| DUSt3R / MASt3R | CC-BY-NC-SA | CC-BY-NC-SA plus training-data/base-model conditions | Commercial inference restricted; additional output implications unresolved | No explicit offer found. MASt3R [checkpoint notice](https://github.com/naver/mast3r/blob/f5209afc300cec36239a7ac992263f36847bbba0/CHECKPOINTS_NOTICE) contains material MapFree/CroCo conditions. |
| Fast3R / VGGT-Ω | FAIR NC Research | FAIR NC Research | Express restriction covers **outputs/results**, as well as inference | No explicit commercial offer found. [Fast3R terms](https://github.com/facebookresearch/fast3r/blob/33104d4b5b8df43795ecded236194958bbdac572/LICENSE), [Ω terms](https://github.com/facebookresearch/vggt-omega/blob/48b23c8ce72c9a8fcf987f0d7f43d8e4870759f6/LICENSE). |

VGGT's Hugging Face gate is labeled `manual` in API metadata although its README describes automatic processing. Public metadata was inspected without requesting approval; gated file contents were not retrieved. Code permission does not erase dependency terms or resolve contradictory weight notices.

## Project-fit decisions and bounded coverage

A future **metric/calibrated-input test** should start with a separately pinned current MapAnything-Apache release, comparing RGB-only and known-camera modes. Its uncertainty is actual metric-scale and player-boundary accuracy; the inspected NC/unspecified benchmark scores do not establish Apache performance. DA3-Base is a permissively licensed **calibrated geometry/detail candidate**, with the question of whether conditioning on metric camera poses preserves useful depth scale and improves synchronized-view boundaries. VGGT-1B-Commercial is an optional **geometry reference**, subject to gate/AUP; it still needs a scale bridge. These are alternatives by role, not a combined winner.

For **dynamic research**, VGGT-Ω-416-Reproduction is worth considering after the commercial restrictions are accepted for the intended research use. The concrete question is whether its dynamic-scene gains survive moving players and occlusions with known fixed cameras. There is no affirmative commercially usable dynamic winner in this section. Pi3X remains a conditional-input research lead; its approximate-scale claim is not measured Basketball evidence.

The initial category search and two explicit expansion rounds are recorded, followed by a bounded later-evaluation/release pass. The package contains **34 model/disposition rows, 45 observations, 23 license rows and 36 search/release checks**. These counts describe records, not unique proven model families or exhaustive coverage. Nine full paper PDFs were inspected; seven provided seed/reference context and two supplied late evidence. Broad supplied-list/topic coverage is owned by the parent discovery section and is not falsely counted as a separate search here.

PoW3R, MUSt3R and WorldMirror remain relevant secondary calibrated/any-prior leads. S-MUSt3R and WorldMirror 2.0 are later unaudited leads. MVSNet/GeoMVSNet require calibrated multi-view preparation, which the project may support; they are not excluded merely for being MVS. Depth-completion or sensor-assisted variants require unavailable depth inputs and are excluded from the RGB comparison groups. Fisheye3R/VGGT-360 require a different camera/image regime. MonST3R, CUT3R and video/diffusion variants are cross-category leads for issue #40; wrapper models are not counted as new families. Discovery-only rows deliberately do not imply release or license verification.

**Verification and acceptance:** exact transcribed values were checked against PDF tables and pinned author release text; CSV parsing, unique identifiers, model references and task-only diff checks passed. All shortlisted release hashes and terms were inspected. Remaining upstream gaps are explicit: baseline binary identity, some masks/depth caps/alignment details, refresh-to-paper equivalence, conflicting Pi3/DA3 license statements, gated access, dynamic occlusion evidence, and any Basketball/render benefit. No model was installed, run or downloaded; no experiment record changed.

Source-check record (2026-09-30): observations 001–016 were checked against DA3 v1 Table 3, p15; 017–020 against Table 2, p14; 021–028 against E3D v1 Table 2, p4 and Appendix B.1/B.3; 029–033 against DA3 Table 8, p18; 034–041 against UAV3DCrop v1 Table 6, p8 and Track B protocol; 042–043 against Ω v1 Tables 1–2, p8; 044–045 against the pinned reproduction table. Paper-link title checks covered all inventory paper URLs; GeoMVSNet was resolved to its CVPR accepted version. Release verification covered public GitHub readmes/licenses and Hugging Face metadata/cards at the recorded revisions, with separate dependency notices for MASt3R. Gated binary/license-file retrieval was not performed; public author license text and metadata provide the qualified findings above.
