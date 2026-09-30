# Video depth and temporal consistency — issue #40

**Cutoff/access: 2026-09-30.** This is published evidence and release inspection, not a local experiment. Supporting records: [searches](../depth-model-survey-data/issue-40/search-log.csv), [variants](../depth-model-survey-data/issue-40/models.csv), [observations](../depth-model-survey-data/issue-40/benchmarks.csv), [licenses](../depth-model-survey-data/issue-40/licenses.csv). Unknown fields are deliberate; an external baseline without a named checkpoint does not inherit the current release's identity.

**VDA Small** is a practical relative-video and commercial starting point. **DepthCrafter** remains a useful diffusion comparator; **ChronoDepth** supplies motion-aware temporal evidence. **GemDepth** and **DVD** add newer geometry/boundary evidence, with release and licensing qualifications. No aligned table establishes physical scale or better Basketball renders.

## Sequence requirements and releases

Direct video methods below infer from monocular RGB without supplied poses/intrinsics. Ground-truth geometry may still be required for evaluation. They do not automatically exploit the project's calibrated cameras.

| Variant | Sequence / output | Release distinction |
| --- | --- | --- |
| DepthCrafter v1.0.1 | Relative inverse depth; offline windows up to 110 frames, overlapping latent initialization/interpolation for longer videos | Original and v1.0.1 results differ; final CVPR Table 1 matches the latter. External unspecified checkpoints stay separate. [DC][dc] |
| VDA Small/Base/Large | Relative inverse depth; offline windows 32, overlap 8, keyframes 2; affine alignment and interpolation; future frames within batch | Relative and metric checkpoints differ. Metric releases trained on Virtual KITTI/IRS have no unaligned metric-video scores extracted here. Experimental streaming differs from oVDA. [VDA][vda] |
| ChronoDepth v1 | Relative depth; paper clip 10 / overlap 5 context-aware diffusion; buffered streaming | Original full pipeline differs from newer v1 UNet; oVDA's one-new-frame/context 4 rerun is a separate configuration. [CH][chrono] |
| Depth Any Video | Relative depth; offline batches with temporal interpolation | VDA reports a 192-frame comparison limit; current release has window/overlap controls, so this is not asserted as a universal release limit. [DAV][dav] |
| RollingDepth v1.0 | Relative depth; offline snippets at multiple temporal spacings, global alignment and refinement | Fast/full/paper are presets of one checkpoint; external preset unknown. [Release][rolling-code] |
| FlashDepth Full/L/S | Relative depth; causal streaming, persistent Mamba state | Three checkpoints; Full combines large-model features with small-model processing. External row “FlashDepth” does not resolve Full/L. [FD][flash] |
| oVDA-small-c16 | Relative depth; current frame plus bounded cache, no future frames | Separate trained model/license from VDA's experimental streaming mode. [OV][ovda] |
| GemDepth-DAv2 / GemDepth-VDA | Relative disparity with internal pose prediction; offline attention | Two paper large-backbone variants, one unlabeled released `gemdepth.pth`; mapping unresolved. [GEM][gem] |
| DVD v1.0 / v1.1 | Relative depth; deterministic Wan adaptation, offline affine overlap stitching | March paper precedes v1.1; paper values not transferred to later weights. [DVD][dvd] |
| ICDepth | Relative video depth with diffusion context | Paper/project demos located; official weights/code and stitching details not located. [IC][ic] |

`models.csv` records environment, immutable release pins, chunking and missing limits. Practical maximum video duration remains unknown where papers claim arbitrary length without a memory bound.

## Protocols and selected evidence

AbsRel is mean absolute error divided by ground-truth depth. δ₁ is the proportion of valid pixels within the paper's ratio threshold. Both are **depth accuracy**, even for video input. Sequence-wide fitting can expose drift but does not establish metric scale; per-frame fitting can conceal drift, while first-frame fitting tests persistence of initial alignment. [OV][ovda]

**TAE** compares bidirectional camera-reprojected depth maps using evaluation intrinsics/poses. VDA's supplement and Depth Any Video print different averaging/indexing conventions; do not pool studies by metric name. Visibility masking is not sufficiently disclosed in the inspected passages. Rigid reprojection on static ScanNet is not a moving-player test. **MFC*** in ChronoDepth instead uses ground-truth optical flow for moving objects; mask details remain unresolved. Boundary F1 measures matched-edge precision/recall, not temporal consistency. [VDA supplement][vda-supp], [DAV][dav], [CH][chrono], [DVD][dvd]

| Source/protocol | Model | Depth accuracy | Temporal error ↓ |
| --- | --- | --- | --- |
| VDA Table1: ScanNet depth clips ≤500; separate TAE 170-frame benchmark | VDA-L | AbsRel **0.089**, δ₁ **0.926** | TAE **0.570** |
| Same | VDA-S | 0.110 / 0.876 | 0.703 |
| Same | DepthCrafter, checkpoint unspecified | 0.169 / 0.730 | 0.639 |
| ChronoDepth v3 Table1: Sintel, shared sequence fit | ChronoDepth | AbsRel **0.493** | MFC* **0.516** |
| Same; modified clip 10 / overlap 5 baseline | DepthCrafter | **0.374** | **0.889** |
| GemDepth v3 Table2: first 20 ScanNet sequences, 110 frames | GemDepth-DAv2 / GemDepth-VDA | separate table | TAE **0.50 / 0.47** |
| ICDepth v1 Table3: ScanNet++ 500 frames | ICDepth / DepthCrafter / Depth Any Video | separate table | TAE **2.61 / 3.07 / 5.69** |

Sources: [VDA][vda], [CH][chrono], [GEM][gem], [IC][ic]. ChronoDepth's motion consistency is better while Sintel AbsRel is worse in this **modified-window** comparison. GemDepth repeats VDA's TAE despite a different stated frame count; copied-versus-rerun status is unknown. ICDepth explicitly reruns baselines, but temporal normalization, masks and baseline revisions are incomplete.

| Later/independent source | Model | Bonn AbsRel ↓ | Bonn δ₁ ↑ |
| --- | --- | --- | --- |
| oVDA v1 Table1: full sequences, first-frame fit only | oVDA-c16 | 0.118 | 0.871 |
| Same; different inference resolution | FlashDepth-S | 0.116 | 0.848 |
| E3D-Bench v1 Table3: frames 30–140, stride 2, sequence fit | DepthCrafter, checkpoint unspecified | 0.107 | 88.3% |
| Same independent benchmark | VDA, variant unspecified | 0.268 | 48.3% |
| Same | Depth Any Video | 0.515 | 25.3% |

[Online VDA][ovda] tests drift with fixed initial alignment. [E3D-Bench][e3d] reverses the apparent VDA/DepthCrafter advantage from VDA's longer-video comparison. Different sampling, resolution and unidentified checkpoints prevent causal attribution. Preserve original percentage units.

[DVD Table3][dvd] reports ScanNet boundary F1 **0.259**, versus VDA **0.210** and DepthCrafter **0.173**. Boundary tolerances and baseline identities remain incompletely disclosed. This supports a detail test, not a temporal-error claim. [StableDPT Table1][stable] uses a **retrained VDA architecture**, not released VDA, because all original training data are not public.

| Timing source | Model | Reported result | Conditions |
| --- | --- | --- | --- |
| VDA Table3 | VDA-S / L | 9.1 / 67 ms/frame | A100, 518×518, FP32; batch details unknown |
| Same | DepthCrafter / Depth Any Video | 910 / 159 ms/frame | FP16; sampling/ensemble unknown in timing table |
| oVDA Table2 | oVDA-c16 / FlashDepth-S | 42 / 60 FPS; 0.45 / 0.69 GB | A100, 280×924, 5,000 frames; precision unspecified here |

Sources: [VDA][vda], [OV][ovda]. Throughput and buffering differ; no cross-table or host-speed ranking follows. [DAV][dav] uses three denoising steps and ensemble 20 for its own quality benchmark; do not attach those settings to another author's timing row.

## Commercial dispositions

These findings cover author code/weight declarations and documented material dependencies, not exhaustive clearance. Every variant has four separate dispositions and pinned sources in `licenses.csv`.

| Candidate | Code / weights | Commercial inference and outputs | Explicit route |
| --- | --- | --- | --- |
| DepthCrafter | Tencent research-only / same plus older SVD notice | Commercial/production inference prohibited; separate output grant not found | Business licensing: `wbhu@tencent.com` |
| VDA Small / Metric Small | Apache-2.0 / Apache-2.0 | Permitted subject to terms; no separate output restriction stated | README business-cooperation invitation; not a grant |
| VDA Base/Large and metric counterparts | Apache-2.0 / CC-BY-NC-4.0 | Commercial inference restricted; no separate output exception | Same cooperation contact in CSV |
| ChronoDepth v1 | MIT / MIT UNet plus SVD-XT | Complete stack conditional; current upstream registration/revenue/AUP rules and derivative lineage need checking | No ChronoDepth offer found; upstream enterprise process separate |
| Depth Any Video | **CC-BY-NC-4.0 / Apache-2.0 card** | Official code remains restricted; SVD lineage/output terms unresolved | None found |
| RollingDepth | Apache-2.0 / incomplete OpenRAIL++-M | Commercial grants appear, but unfilled restriction placeholders and SD2 dependencies require clarification | None found |
| FlashDepth | Apache-2.0 / Apache-2.0 card | Large DAv2 ancestry is noncommercial; Full/L clearance qualified; separate output restriction not found | None found |
| oVDA | NC-SA-UHDV1.0 with marked Apache code / NC-SA-UHDV1.0 | Company-internal research/product benchmarking also needs written permission; no separate output grant | Science Value Heidelberg; published contact in CSV |
| GemDepth | MIT / MIT card | Noncommercial large DAv2/VDA ancestry remains unresolved; declaration alone does not establish relicensing authority | None found |
| DVD v1.0/v1.1 | Apache-2.0 / CC-BY-NC-4.0 | Commercial inference restricted; no separate output grant | None found |
| ICDepth / StableDPT | Unknown / unknown | Unresolved; arXiv license is not model permission | None located |

Official sources: [DepthCrafter][dc-code], [VDA][vda-code], [ChronoDepth][chrono-code], [DAV][dav-code], [RollingDepth][rolling-code], [FlashDepth][flash-code], [oVDA][ovda-code], [GemDepth][gem-code], [DVD][dvd-code]. Exact weight cards are separately pinned in CSV. Current SVD terms do **not** prove retroactive relicensing of every derivative or remove Tencent restrictions. RollingDepth's literal template placeholders are retained as an unresolved license defect.

## Basketball fit and next-test questions

Future relative-video tests could start with **VDA Small**, **DepthCrafter v1.0.1** where licensed, and **ChronoDepth v1** for motion. Add DVD for boundaries or GemDepth after resolving the released variant. VDA metric checkpoints merit a separate physical-scale hypothesis; they do not inherit metric accuracy from relative tables. VDA Small is the clearest inspected commercial starting point; FlashDepth-S merits dependency follow-up.

Test whether one initial alignment survives moving players/occlusion, whether chunk seams appear, and whether temporal stability smears limbs or the ball. Evaluate moving-player, newly visible and static-background regions separately using camera/flow-aware visibility. These are proposed tests, not measured gains. Existing D0–D4 controls, human preferences and experiment records remain unchanged.

Bonn/Sintel include motion, but the inspected tables do not isolate Basketball or occlusion events. Static-scene TAE and long-video demonstrations do not establish hidden-geometry recovery, multi-camera agreement or 4DGS render improvement.

## Coverage and verification

The evidence records initial category discovery, two comparison/reference expansion rounds, and a targeted newer-work pass: **25 search/read records, 27 variant/configuration records, 48 observations, 27 license records**. These include unresolved benchmark identities, not independent families. The parent survey consolidates supplied-list/topic coverage; this section does not claim independent searches of every list.

NVDS and single-image baselines were screened through references but not shortlisted. VDPP is retained as a released depth-only postprocessor with upstream-model requirements. RIDE needs a metrically scaled 3DGS map/sparse geometry; StereoDiff remains a separate stereo/geometric lead. CUT3R and related geometric models belong in the companion section. Wrappers and unrelated similarly named repositories were excluded.

Exact values were rechecked against official PDF tables or versioned HTML. VDA supplementary alignment/rerun notes were inspected. Units, frame selection, modified windows and missing variant mappings remain explicit. Release metadata was inspected without weight downloads. A web PDF 403 was recovered via host access; an attempted ChronoDepth supplement URL returned 404, leaving mask details unresolved. Validation passed for all four CSVs: parsing, nonempty fields, unique identifiers, model references, numeric values and directions, and one license record per variant. Markdown reference labels and `git diff --check` passed. All 33 unique paper/code-license/weight-license URLs checked returned HTTP 200; remaining source limitations are stated above. No installs, inference, GPU benchmarks, application tests or experiment writes occurred.

[dc]: https://openaccess.thecvf.com/content/CVPR2025/papers/Hu_DepthCrafter_Generating_Consistent_Long_Depth_Sequences_for_Open-world_Videos_CVPR_2025_paper.pdf

[vda]: https://openaccess.thecvf.com/content/CVPR2025/papers/Chen_Video_Depth_Anything_Consistent_Depth_Estimation_for_Super-Long_Videos_CVPR_2025_paper.pdf

[chrono]: https://arxiv.org/html/2406.01493v3

[dav]: https://arxiv.org/html/2410.10815v2

[rolling]: https://share.phys.ethz.ch/~pf/bingkedata/rollingdepth/doc/RollingDepth_arxiv_v1.pdf

[flash]: https://openaccess.thecvf.com/content/ICCV2025/papers/Chou_FlashDepth_Real-time_Streaming_Video_Depth_Estimation_at_2K_Resolution_ICCV_2025_paper.pdf

[ovda]: https://arxiv.org/html/2510.09182v1

[gem]: https://arxiv.org/html/2605.10525v3

[dvd]: https://arxiv.org/html/2603.12250v1

[ic]: https://arxiv.org/html/2607.01677v1

[e3d]: https://arxiv.org/html/2506.01933v1

[stable]: https://arxiv.org/html/2601.02793v1

[vdpp]: https://arxiv.org/abs/2604.06665v2

[dc-code]: https://github.com/Tencent/DepthCrafter/tree/e5186120a71ecb56b69f9e89654198b4eadfaf60

[vda-code]: https://github.com/DepthAnything/Video-Depth-Anything/tree/4f5ae23172ba60fd7bc11ef671cca678842c7072

[chrono-code]: https://github.com/jiahao-shao1/ChronoDepth/tree/2580e891eb33a5c3a95eab27b745f64ac28b3514

[dav-code]: https://github.com/Nightmare-n/DepthAnyVideo/tree/3592f8c5e427327a31cf1f3775e69cc3f2f26309

[rolling-code]: https://github.com/prs-eth/RollingDepth/tree/c233765fb7adf9682442a9fbef3eb07212bb70fd

[flash-code]: https://github.com/Eyeline-Labs/FlashDepth/tree/3e08f313b9f1b08efde5e6ebacc671a173cb9f36

[ovda-code]: https://github.com/FriedFeid/OnlineVideoDepthAnything/tree/4173c24e22f528062a0cf8ae235c58a5d4376a74

[gem-code]: https://github.com/Yuecheng919/GemDepth/tree/652865b0ed20e727784a6b77314da1dca2f14e36

[dvd-code]: https://github.com/EnVision-Research/DVD/tree/62f52d16faa2cac10e31eb7815ece6e61d5449ec

[vda-supp]: https://openaccess.thecvf.com/content/CVPR2025/supplemental/Chen_Video_Depth_Anything_CVPR_2025_supplemental.pdf
