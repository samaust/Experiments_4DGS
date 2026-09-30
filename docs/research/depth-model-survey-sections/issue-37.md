# D0–D4 reference evidence and discovery map

Survey cutoff and access date: **2026-09-30**. Implements issue #37 under
[the survey specification](../../specs/depth-model-survey.md). This section
contains published evidence and release review; it supplies no new local
measurements and makes no claim about improved Basketball renders.

The five numerical source papers predate the access date:

| Paper version | Evidence version date |
|---|---|
| [UniDepthV2 2502.20110v2](https://arxiv.org/abs/2502.20110v2) | 2025-12-18 |
| [DA3 2511.10647v1](https://arxiv.org/abs/2511.10647v1) | 2025-11-13 |
| [Metric3Dv2 2404.15506v4](https://arxiv.org/abs/2404.15506v4) | 2025-01-03 |
| [Depth Pro 2410.02073v2](https://arxiv.org/abs/2410.02073v2) | 2025-04-21 |
| [MoGe-2 2507.02546v1](https://arxiv.org/abs/2507.02546v1) | 2025-07-03 |

## Reference identities

The existing [component manifest](../../../configs/vipe-alternatives/components-v1.json)
is authoritative for project roles. D0 and D1 are implementation controls within
**UniDepth V2-L**, not independent model families and not UniDepth V1.

| Reference | Exact selected artifact and role | Camera/depth contract | Paper correspondence |
|---|---|---|---|
| D0 | Historical ViPE `UniDepth2Model`, type `l`; original runtime and serialization | Single image, historical calibrated-camera invocation, metric camera-z depth | No paper evaluates this wrapper. Its paper score is missing, not zero. |
| D1 | Official `UniDepthV2`; `lpiccinelli/unidepth-v2-vitl14`, `model.safetensors` | Optional K; project supplies pinhole K and uses default resolution policy | Large architecture matches; RGB-only paper results do not measure this exact adapter. |
| D2 | `depth-anything/DA3METRIC-LARGE`, `model.safetensors` | Canonical depth; processed focal/300 converts to metres once | DA3-metric final row is relevant, but paper has no released-file hash. Other DA3 modes and ablations are separate. |
| D3 | `metric_depth_vit_large_800k.pth`, `metric3d_vit_large`, `vit.raft5.large.py` | Supplied resized focal; canonical-to-metric conversion | ViT-L paper row is relevant; the selected raft5 configuration sets eight refinement steps, matching the supplement. Giant scores do not describe D3. |
| D4 | Apple native `depth_pro.pt` | Optional focal; project supplies `f_px`; native inversion returns metres | Native paper model is relevant; camera-estimation and supplied-focal evaluations are different modes. |

D1–D4 official links and frozen source/weight revisions are in
[models.csv](../depth-model-survey-data/issue-37/models.csv). D0's wrapper source
revision is not re-audited here; its exact role and shared weight serialization
come from the project manifest. Current ViPE main must not be substituted for
historical wrapper evidence.

## Comparisons that survive the identity check

AbsRel is mean absolute relative error, lower is better. Delta1 is the proportion
of pixels within the multiplicative 1.25 threshold, higher is better. Percent
and ratio units are retained as printed; percentages are not silently merged
with ratios. **No table below is an overall model ranking.**

### Same evaluator, known-camera metric depth

MoGe-2's later evaluation explicitly separates metric depth from aligned point
maps. Appendix A.3 states no alignment or added prediction clamp for metric
depth, allowing native hard-coded postprocessing. Appendix A.2 identifies both
reference backbones as ViT-L. Exact evaluation checkpoint hashes, crop and
resolution remain unspecified, so this is architectural corroboration rather
than proof of the project's selected bytes. [MoGe-2 v1, Tables A.2/B.4](https://arxiv.org/html/2507.02546v1#A1.SS2).

| ETH3D; supplied GT intrinsics; Table B.4 metric-depth block | AbsRel % ↓ | Delta1 % ↑ |
|---|---:|---:|
| UniDepth V2 ViT-L | 15.0 | 85.2 |
| Metric3D V2 ViT-L | 11.8 | 88.8 |

These observations favour Metric3D in this particular setting; they do not
establish exact checkpoint parity or predict results for moving players. The CSV
uses source-specific paper identities `i37-unidepth-v2-vitl-moge2` and
`i37-metric3dv2-vitl-moge2`; neither inherits the selected D1/D3 weight artifacts.

### Original Metric3D ViT-L zero-shot row

| Metric3Dv2 v4, Table I, `Ours ViT-L CSTM_label ZS` | AbsRel ratio ↓ | Delta1 ratio ↑ |
|---|---:|---:|
| NYUv2 | 0.063 | 0.975 |
| KITTI | 0.052 | 0.974 |

The FT rows are excluded. Supplement Table 2 describes 654 NYUv2 and 652 KITTI
test samples and supplied intrinsics. Crop/range remain unresolved here.
The selected [`vit.raft5.large.py`](https://github.com/YvanYin/Metric3D/blob/eb5b6fac0dc155e4e52f576e304fbf11655ff339/mono/configs/HourglassDecoder/vit.raft5.large.py)
sets `iters=8`, matching the paper; its filename does not imply five steps.
The evaluated checkpoint hash is still undisclosed. The selected values were unchanged between
v2 and the subsequently checked v4. [Metric3Dv2 v4, Table I and supplement](https://arxiv.org/html/2404.15506v4#S4).

### DA3 authors' metric comparison: useful but incomplete protocol

| DA3 v1 Table 11, ETH3D | AbsRel ratio ↓ | Delta1 ratio ↑ |
|---|---:|---:|
| Depth Pro | 0.349 | 0.386 |
| Metric3D v2, backbone unspecified | 0.138 | 0.830 |
| UniDepth v1, backbone unspecified | 0.464 | 0.234 |
| UniDepth v2, backbone unspecified | 0.152 | 0.863 |
| DA3-metric, final model | 0.104 | 0.917 |

The table supports the reported DA3-metric result, but baseline backbone,
checkpoint, copied-versus-rerun origin, split, crop, depth cap and inference
resolution are not established by Section 7.4. It therefore cannot support an
exact D1/D2/D3 winner. The CSV also preserves SUN-RGBD and DIODE-indoor rows.
Teacher ablations use a different training resolution and are excluded.
**DIODE Metric3Dv2 reports Delta1 0.018 alongside AbsRel 0.154:** visual PDF
inspection confirms the source prints these values. They are retained as an
unresolved anomaly and excluded from conclusions. [DA3 v1, Table 11, p.21](https://arxiv.org/html/2511.10647v1#S7.SS4).

### Independent baseline reruns in Depth Pro

| Depth Pro v2 Tables 1/4 | ETH3D Delta1 % ↑ | ETH3D AbsRel ↓ | SUN-RGBD Delta1 % ↑ | SUN-RGBD AbsRel ↓ |
|---|---:|---:|---:|---:|
| UniDepth **V1 ViT-L** | 25.3 | 0.457 | 95.8 | 0.087 |
| Metric3Dv2 **giant** | 87.7 | 0.124 | 75.6 | 0.156 |
| Depth Pro | 41.5 | 0.327 | 89.0 | 0.113 |

The authors rerun baselines. ETH3D uses raw images/EXIF handling, a 0.1–200 m
valid range and 454 samples; SUN-RGBD uses 0.001–10 m and 5050 samples. Predictions
are bilinearly resized to GT resolution. Metric3D receives domain-specific
crops, explicitly marked as violating strict zero-shot evaluation. Neither
baseline is the selected D0/D1/D3 variant. [Depth Pro v2, Appendix C.5–C.6](https://arxiv.org/html/2410.02073v2#A3.SS5).

Its separate iBims boundary F1 comparison is Depth Pro **0.176**, Metric3Dv2
giant **0.096**, and UniDepth V1 **0.039**. This scale-invariant boundary metric
supports a detail-testing role, not physical-scale or temporal accuracy.
[Depth Pro v2, Table 2](https://arxiv.org/html/2410.02073v2#S4).

### Alignment conflict in UniDepthV2

| UniDepthV2 v2 Table I, SUN-RGBD | Printed AbsRel % ↓ | Printed Delta1 % ↑ |
|---|---:|---:|
| UniDepthV2-Large | 6.8 | 96.4 |
| Depth Pro | 13.3 | 83.1 |
| Metric3Dv2, backbone unspecified | 13.3 | 81.2 |

All baselines are explicitly rerun, without test augmentation; Metric3Dv2 uses
GT intrinsics. The official README says NYUv2 overlap is removed from SUN-RGBD.
However, Section IV-A calls the depth metric **Delta1 SSI**, while the table
omits SSI. The PDF confirms this notation conflict. These values remain in an
**alignment-unresolved** protocol and cannot be merged into the unaligned
metric tables. [UniDepthV2 v2, Table I and Section IV-A, pp.6–7](https://arxiv.org/html/2502.20110v2#S4.SS1).

## Availability and commercial findings

The exact author model APIs confirmed public, ungated metadata and the selected
files for D1–D4; no model weights were downloaded. The frozen revisions are
preserved instead of replacing them with today's latest models. Public access
does not settle licensing. D0 is the existing historical control, not a newly
qualified environment.

| Reference | Commercial code | Commercial weights | Inference and outputs | Explicit offer |
|---|---|---|---|---|
| D0 | ViPE wrapper Apache; UniDepth component NC restriction remains | No commercial grant established for shared UniDepth weights | Wrapper permission does not override model terms; no independent output grant identified | None found for this depth route |
| D1 | CC BY-NC 4.0: restricted | Exact HF card has no independent grant; project NC context | Commercial inference not established; NC is not automatically asserted as every output's copyright license | None found |
| D2 | Apache-2.0 | Exact metric checkpoint card Apache-2.0 | Commercial inference supported under those terms; no additional output restriction found | No separate offer needed/found |
| D3 | BSD-2-Clause | **Unresolved**: exact weight repository lacks README/LICENSE | No commercial model/output permission inferred from source BSD | Explicit commercial-inquiry route to Wei Yin and Mu Hu; no promised terms |
| D4 | Apple custom software grant permits use subject to notices | Apple AMLR: noncommercial research only | Model use excludes commercial exploitation/product development; output disclaimer is not a separate commercial grant | None found |

Governing sources: [UniDepth LICENSE](https://github.com/lpiccinelli-eth/UniDepth/blob/8d8cfe4c7ee15297099983607febf0d4f32eb3d6/LICENSE),
[UniDepth exact card](https://huggingface.co/lpiccinelli/unidepth-v2-vitl14/blob/52b349b514bd8b47642f67ac78cb7b5dc5c51dd9/README.md),
[DA3 code](https://github.com/ByteDance-Seed/Depth-Anything-3/blob/3d835ec1a5802d64a8b8b15f817a1ab54809bfe4/LICENSE),
[DA3 metric card](https://huggingface.co/depth-anything/DA3METRIC-LARGE/blob/4010e39f3634a45bc60553321fb49fb760bd594e/README.md),
[Metric3D code/contact](https://github.com/YvanYin/Metric3D/blob/eb5b6fac0dc155e4e52f576e304fbf11655ff339/README.md),
[Metric3D exact weights tree](https://huggingface.co/JUGGHM/Metric3D/tree/80d2d1410afb4b23cd9d18c6be9144483d4b70b6),
[Apple code](https://github.com/apple/ml-depth-pro/blob/9e65e4dbe9568d23c546fcec53302b10445e109e/LICENSE),
[Apple exact weight terms](https://huggingface.co/apple/DepthPro/blob/ccd1350a774eb2248bcdfb3be430e38f1d3087ef/LICENSE),
and [ViPE third-party notice](https://github.com/nv-tlabs/vipe#license).

A material contradiction remains: Apple's pinned README says weights share its
repository license; the exact HF artifact supplies a restrictive AMLR license.
This report follows the latter for the selected asset and does not infer a
commercial exception. Metric3D's contacts are an actual commercial-inquiry
invitation, not proof of a commercial weight license. Addresses and complete
four-part dispositions are in [licenses.csv](../depth-model-survey-data/issue-37/licenses.csv).

Environment limits are explicit in [models.csv](../depth-model-survey-data/issue-37/models.csv):
UniDepth's documented Linux/Python/CUDA setup and xFormers compatibility;
DA3's constrained Python/NumPy and broad export dependencies; Metric3D's pinned
older torch/xFormers requirements; and Depth Pro's Python 3.9 example plus timm
and media dependencies. See the pinned [UniDepth README](https://github.com/lpiccinelli-eth/UniDepth/blob/8d8cfe4c7ee15297099983607febf0d4f32eb3d6/README.md),
[DA3 pyproject](https://github.com/ByteDance-Seed/Depth-Anything-3/blob/3d835ec1a5802d64a8b8b15f817a1ab54809bfe4/pyproject.toml),
[Metric3D requirements](https://github.com/YvanYin/Metric3D/blob/eb5b6fac0dc155e4e52f576e304fbf11655ff339/requirements_v2.txt),
and [Depth Pro pyproject](https://github.com/apple/ml-depth-pro/blob/9e65e4dbe9568d23c546fcec53302b10445e109e/pyproject.toml).
These declarations do not establish host compatibility, latency, VRAM use or
application-wide dependency clearance. No installs or runtime qualification
were performed.

## Discovery coverage and handoff

[search-log.csv](../depth-model-survey-data/issue-37/search-log.csv) contains
22 dated steps: **all eleven supplied entry points**, four reference-paper
screens, a ZoeDepth citation follow-up, two second-round follow-ups, a later-work
search, and three verification steps. Coverage is bounded to displayed topic
pages, named queries and selected category files, not exhaustive pagination.

| Entry point | Actual screen and category disposition |
|---|---|
| arXiv | Metric/zero-shot comparison query; ZeroDepth and FoV-conditioned diffusion to metric; MDEC independent-evaluation lead |
| GitHub | Video/temporal/dynamic-scene query; GemDepth and DVD to video; stereo DynamicStereo and sensor-assisted DVSR excluded from monocular RGB comparison |
| Hugging Face | Depth filter had incomplete model-list rendering; targeted search and author APIs recovered exact releases; DA V2 Small to efficient, RollingDepth to video; mirrors deduplicated |
| Ideal-111 foundation list | Discriminative/generative/completion sections; MoGe-2, VGGT, DUSt3R, PatchRefiner, DepthCrafter; completion needs separate inputs |
| scott89 list | Older supervised/unsupervised entries; Eigen, FCRN, DORN, BTS ancestry retained without importing old scores |
| hitcslj robust list | Weather/nighttime/corruption entries; md4all and WeatherDepth leads; TODO sections and indoor relevance limits recorded |
| choyingw monocular list | DepthFM, NVDS, IEBins and PatchFusion leads; October 2024 update limit recorded |
| AndyLiming list | Followed monocular, multiview and video files; ZeroDepth, NeWCRFs, GeoMVSNet, IterMVS, NVDS; polarimetric stereo excluded from RGB-only group |
| depth-prediction topic | FCRN/AdelaiDepth leads; DepthFlow is an application, sparse-to-dense needs sensor depth |
| depth-estimation topic | MapAnything/Marigold/ZoeDepth leads; pySLAM is a pipeline, not another independent estimator |
| monocular-depth-estimation topic | Cross-checked DA/MiDaS/Marigold/MoGe/ZoeDepth/Metric3D; aliases deduplicated |

First expansion: reference tables led to ZoeDepth, whose Table 1 explicitly
copies prior-paper scores and whose Table 2 retrains modified architectures.
Second expansion followed its NeWCRFs citation to the original paper and sought
later independent reference comparisons, extracting MoGe-2's camera-conditioned
rows. A final targeted search identified **Marigold V2 (September 2026)** and
transparent-surface evaluation leads. These were passed to the category
researchers; they are not silently promoted into audited recommendations here.
[ZoeDepth v1](https://arxiv.org/html/2302.12288v1),
[NeWCRFs v2](https://arxiv.org/abs/2203.01502v2),
[Marigold V2](https://arxiv.org/abs/2609.08084).

## Project fit and verification

For known-camera physical scale, D1/D3 have relevant later supplied-intrinsics
comparisons, while D2 is the clearest commercial model-level reference among
these controls. D4 has useful boundary evidence but restrictive selected weights.
D0/D1 remain the migration-control pair. These are reasons for future tests,
not a changed experiment selection. An appropriate future question is whether
unaligned scale and player/ball boundaries remain stable across synchronized
Basketball views. None of the extracted image metrics establishes temporal
stability, moving-person accuracy, occlusion handling or final 4DGS quality.

The package contains **35 model/lead records, 59 numeric observations and five
reference license records**. Nineteen inventory entries are explicitly discovery
leads; the remaining entries separate controls and paper evaluation identities.
All benchmark and license model IDs resolve. `unknown` means unreported or
unresolved; `not_applicable` means the field cannot apply. Missing scores are
absent observations, never zero. Protocol IDs scope evaluator, dataset and
alignment; they are not declarations that unknown details match across papers.

Validation: CSV parsing, ID uniqueness/references, numeric values and task-only
diff were checked. Extracted values were rechecked against exact-version tables;
DA3 p.21 and UniDepthV2 p.6 were additionally rendered and inspected. Public
release APIs and pinned license sources were read. Web PDF rendering and the
Apple license blob had access/rendering failures; direct public-file reads
succeeded. One sandbox raw-GitHub network denial succeeded on its authorized
outside-sandbox retry. The report records the unresolved alignment, checkpoint,
training-overlap, license and anomalous-value cases rather than claiming their
resolution. No application tests, GPU work or experiment changes were needed.

Acceptance assessment: identity, all-source screening, paper extraction,
compatibility separation, exact-release availability, four licensing dimensions,
structured records and source checks are present. Remaining upstream gaps are
explicit findings; category-wide synthesis and independent review belong to
the parent issue.
