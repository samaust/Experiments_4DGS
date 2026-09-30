# Depth estimation models: literature and release survey

**Cutoff: 2026-09-30 · Plan 068 · Issues #36–#43**

## Findings in brief

The strongest next-test candidates serve different purposes: **MoGe-2** for
metric scale with known cameras, **MoGe-3** for the scale/detail tradeoff,
**Marigold V2** for relative detail, **Video Depth Anything Small** for temporal
depth, and **Depth Anything V2 Small** for efficient depth ordering. A separate
**MapAnything-Apache** test could examine calibrated multi-view geometry.
These are report recommendations based on the evidence below, not measured
Basketball improvements or an overall ranking.

Three distinctions matter throughout:

- Good depth after ground-truth alignment does not demonstrate physical scale.
- A newer/larger checkpoint does not inherit another checkpoint's scores or license.
- Image detail, temporal consistency and final 4DGS rendering are separate outcomes.

The six [research sections](#coverage-and-evidence) contain the full comparisons.
The consolidated [model inventory](depth-model-survey-data/models.csv),
[benchmark observations](depth-model-survey-data/benchmarks.csv),
[license findings](depth-model-survey-data/licenses.csv) and
[search record](depth-model-survey-data/search-log.csv) retain exact source
versions, missing settings and disagreements. The [data guide](depth-model-survey-data/README.md)
explains fields and reconciliation.

## What is available

| Role | Released candidates examined | Material availability limits |
| --- | --- | --- |
| Existing controls | D0 historical ViPE/UniDepth V2-L; D1 standalone UniDepth V2-L; D2 DA3METRIC-LARGE; D3 Metric3Dv2 ViT-L; D4 Depth Pro | D0/D1 are two implementations of one family. A paper does not measure the historical wrapper. |
| Additional metric depth | MoGe-2/3, ZoeDepth N/K/NK, DAC, UniDAC, UniK3D, MetricAnything students, ZeroDepth | Camera requirements and radial-distance versus camera-z outputs differ. MetricAnything teacher is not a released RGB-only student. |
| Relative/diffusion depth | DA V2 Small/Large, Marigold v1/V2, Lotus D/G, Lotus-2, GenPercept | DA V2 Giant has no verified public weights; Lotus-2 needs a gated base. Linear, inverse and log-depth outputs need different anchoring. |
| Video | VDA relative/metric variants, DepthCrafter, ChronoDepth, Depth Any Video, RollingDepth, FlashDepth, oVDA, GemDepth, DVD | Offline, buffered and causal methods differ. GemDepth's released file is not mapped to its two paper variants. ICDepth remains a paper/demo lead. |
| Multi-view geometry | VGGT and gated Commercial variant; DA3; MapAnything and Apache variants; Pi3/Pi3X; DUSt3R/MASt3R/Fast3R; VGGT-Ω | Refreshed DA3 and MapAnything releases need distinct identities. VGGT-Ω designates a replacement checkpoint for benchmarking after a contamination concern. |
| Efficiency/high resolution | DA V2 Small, MiDaS small variants, PatchFusion, PatchRefiner/V2, PRO, InfiniDepth, PPD | Exact PRV2 M/E/C release mapping is unresolved. EfficientDepth's evaluated release was not located. Refiners require their base model too. |

Availability means inspected official metadata/files, not downloaded or qualified
weights. Exact pins, environments and input contracts are in each inventory row.
Screened leads with unresolved artifacts remain visible and are not recommendations.

## Selected comparisons

Each group uses its own evaluator. Arrows show the better direction. Values
are transcribed observations; unknown settings remain limitations even within
one source. No cross-group averaging is used.

### Metric scale and camera information

MoGe-2's original metric-depth evaluation explicitly uses **no GT alignment**.
Known FoV supplies additional information, so it is a separate condition.
AbsRel is expressed as a percentage. [MoGe-2 v1, Appendix A.3/Table B.4](https://arxiv.org/html/2507.02546v1).

| Exact model/input | NYUv2 AbsRel ↓ | iBims-1 AbsRel ↓ |
| --- | ---: | ---: |
| MoGe-2 ViT-L, predicted camera | 7.33 | 13.6 |
| Same weights, supplied FoV | 6.46 | 9.92 |

MoGe-3's later source-local comparison reports the following metric-depth
percentages. Its detailed crop/cap/alignment implementation is incompletely
specified; its MoGe-2 baseline differs from the original paper above.
[MoGe-3 v2, Table C.1](https://arxiv.org/html/2607.17967v2).

| Predicted-camera paper row | NYUv2 AbsRel ↓ | iBims-1 AbsRel ↓ |
| --- | ---: | ---: |
| MoGe-2 ViT-L | 6.90 | 14.6 |
| MoGe-3 ViT-L, three refinement steps | 8.43 | 11.7 |
| MoGe-3 ViT-G, three refinement steps | 10.5 | 11.0 |

Thus the later models improve iBims-1 while worsening NYUv2 here. Neither table
establishes cross-camera scale stability on Basketball. See [metric evidence](depth-model-survey-sections/issue-38.md)
for independent adverse-domain results and known-camera alternatives.

### Relative ordering

DA-2K measures pairwise closer/farther accuracy, without recovering metres.
Its pair selection includes model-disagreement mining. [DA V2 v2, Table 3](https://arxiv.org/html/2406.09414v2).

| Paper model | Ordering accuracy ↑ |
| --- | ---: |
| Marigold v1.0 | 86.8% |
| DA V2 Small | 95.3% |
| DA V2 Large | 97.1% |
| DA V2 Giant, unreleased | 97.4% |

This does not contradict other papers' boundary or aligned-depth results.
Marigold V2's newer detail evidence uses a different log-depth fit and masks;
the [relative-depth section](depth-model-survey-sections/issue-39.md) preserves
those distinctions and copied-baseline conflicts.

### Temporal consistency

VDA's ScanNet 170-frame TAE uses shared sequence alignment and camera reprojection;
lower is better. The static-scene evaluation does not isolate moving-player
accuracy. [VDA, Table 1 and supplement](https://openaccess.thecvf.com/content/CVPR2025/papers/Chen_Video_Depth_Anything_Consistent_Depth_Estimation_for_Super-Long_Videos_CVPR_2025_paper.pdf).

| Evaluated row | TAE ↓ |
| --- | ---: |
| VDA Large | 0.570 |
| DepthCrafter, checkpoint unspecified | 0.639 |
| VDA Small | 0.703 |

Large performs better here but has different weight terms. Later independent
E3D evidence reverses some depth-accuracy comparisons; oVDA instead fixes
alignment from the first frame. Those tests are retained separately in the
[video section](depth-model-survey-sections/issue-40.md).

### Multi-view geometry

DA3's DTU table measures fused point-cloud Chamfer distance, in millimetres.
Pose-free processing includes GT trajectory alignment; the other column supplies
poses. Both have additional processing beyond monocular prediction. These
original paper variants do not establish DA3-1.1 or VGGT-Commercial performance.
[DA3 v1, Table 3](https://arxiv.org/html/2511.10647v1).

| Paper model | No supplied poses ↓ | Supplied poses ↓ |
| --- | ---: | ---: |
| VGGT | 2.05 | 1.44 |
| DA3 Large | 2.08 | 1.23 |
| DA3 Base | 2.87 | 2.36 |

The [multi-view section](depth-model-survey-sections/issue-41.md) separately
examines pose, scale and dynamic-scene evidence. Static reconstructed geometry
does not establish final-render quality for moving players.

### Detail versus compute

PRV2's target-trained UnrealStereo4K comparison uses P16 and a shared ZoeDepth
coarse route. **Times exclude the coarse estimator**; A100 inference is stated,
precision and patch batching are unresolved. Dagger denotes matched pretraining.
[PRV2 v1, Table 1 and §4.4](https://arxiv.org/html/2501.01121v1).

| Refiner | RMSE (m) ↓ | Boundary SEE ↓ | Refiner seconds ↓ |
| --- | ---: | ---: | ---: |
| PatchRefiner † | 0.941 | 0.771 | 1.45 |
| PRV2-M | 1.003 | 0.832 | 0.32 |
| PRV2-C | 0.884 | 0.787 | 0.62 |

The lower-RMSE model is not the lowest-boundary-error model. These are neither
zero-shot Basketball results nor full-pipeline host timings. The
[efficiency section](depth-model-survey-sections/issue-42.md) covers lightweight
alternatives, base/refiner obligations and unavailable releases.

## Commercial-use findings

These four dimensions summarize inspected terms. “Permitted” is subject to
the stated license and material dependencies; it does not establish output
ownership or complete application clearance. Exact documents, contacts and
release pins are in [licenses.csv](depth-model-survey-data/licenses.csv).

| Exact candidate/control | Code | Weights | Commercial inference / outputs | Explicit commercial offer |
| --- | --- | --- | --- | --- |
| D0/D1 UniDepth route | UniDepth NC restriction; wrapper permission does not override it | No independent commercial grant established | Commercial inference not established; output copyright not inferred | None found |
| D2 DA3METRIC-LARGE | Apache-2.0 | Apache-2.0 | Permitted; no separate output restriction found | None needed/found |
| D3 Metric3Dv2 ViT-L | BSD-2-Clause | Exact weight grant unresolved | Unresolved | Explicit commercial inquiry to Wei Yin/Mu Hu |
| D4 Depth Pro | Custom permissive software grant | Selected HF asset AMLR research-only | Commercial exploitation/product development excluded; no separate output grant | None found |
| MoGe-2 original ViT-L / MoGe-3 ViT-L | MIT plus notices | Exact cards MIT | Permitted; no separate output restriction stated | None found |
| DA V2 Small | Apache-2.0 | Apache-2.0 | Permitted; no separate output restriction found | None found |
| Marigold V2 Log-stage2 | Apache-2.0 | Apache adapters and Qwen base | Permitted under inspected declarations; no separate output clause found | None needed/found |
| VDA Small / Metric Small | Apache-2.0 | Apache-2.0 | Permitted; no separate output restriction stated | Business cooperation invitation; not an alternative grant |
| MapAnything-Apache current | Apache-2.0 | Apache-2.0 | Permitted; no separate output restriction found | Explicit Apache alternative to NC weights |

Sources: [reference audit](depth-model-survey-sections/issue-37.md#availability-and-commercial-findings),
[MoGe exact card](https://huggingface.co/Ruicheng/moge-2-vitl/blob/39c4d5e957afe587e04eec59dc2bcc3be5ecd968/README.md),
[MoGe-3 exact card](https://huggingface.co/Ruicheng/moge-3-vitl/blob/184008f877d7ad1ad4c2cd2182a9bd1f63d0e5be/README.md),
[DA V2 Small](https://huggingface.co/depth-anything/Depth-Anything-V2-Small/blob/03876f8651c73a60fe4c2c48294e09fcb6838fcf/README.md),
[Marigold V2](https://huggingface.co/huawei-bayerlab/marigold-v2-0/blob/cdf9810fb690886391a63aec012b5f501064fb0d/README.md),
[VDA Small](https://huggingface.co/depth-anything/Video-Depth-Anything-Small/blob/256875362cff76724b920335dfb4b29dd611f66e/README.md),
[Metric Small](https://huggingface.co/depth-anything/Metric-Video-Depth-Anything-Small/blob/273d090f2ce17df50c2872d82c8322c45da5b4dd/README.md),
[MapAnything-Apache](https://huggingface.co/facebook/map-anything-apache/blob/00f9c245bbcb60522d1ed7f9e9d88462c6e3f38a/README.md).

Important unresolved cases remain in the full inventory: conflicting DA3-Large-1.1,
Pi3, PRO and GenPercept declarations; unnamed external weight grants;
RollingDepth's incomplete license template; and restricted upstream bases in
otherwise permissively labeled adapters. Current upstream terms do not prove
retroactive permission for every derivative.

## Recommended future tests

These are **report inferences and proposed experiments**, not an execution plan.
The commercial shortlist is the permissive rows above; unresolved and NC
methods remain useful research evidence without becoming commercial recommendations.

| Priority / role | Exact variant(s) | Evidence-based reason | Question on calibrated Basketball footage |
| --- | --- | --- | --- |
| Metric scale | MoGe-2 original ViT-L, predicted versus supplied FoV; retain D2 control | Explicit unaligned metric evidence and known-camera comparison | Does supplied camera information improve scale agreement across cameras and frames? |
| Metric/detail tradeoff | MoGe-3 ViT-L, three refinement steps, against MoGe-2 | Newer geometry evidence with visible dataset regressions | Do player/court boundaries improve without losing scale accuracy or temporal stability? |
| Relative detail | Marigold V2 Log-stage2 against DA V2 Small | New detail evidence plus two distinct relative representations | Can independently validated log/inverse-depth anchors preserve net/limb boundaries and cross-camera agreement? |
| Video consistency | VDA Small relative; Metric Small as a separate hypothesis | Temporal evidence and exact permissive checkpoints | Does alignment survive occlusion and chunk boundaries? Does the metric checkpoint retain physical scale indoors? |
| Efficient baseline | DA V2 Small | Released lightweight model with ordinal and efficiency evidence | Is its actual full-pipeline cost acceptable while preserving player boundaries at 960×540? |
| Optional multi-view extension | Current MapAnything-Apache, RGB-only versus supplied cameras | Metric/camera-conditioned interface and verified Apache alternative | Does it handle synchronized moving players, and how does its scale compare? NC/unspecified paper rows do not establish this checkpoint's accuracy. |

No shortlisted single-image model has established Basketball temporal quality.
Known intrinsics alone cannot identify both scale and shift in relative depth;
anchors must match the output domain and be checked on held-out geometry.
Keep physical-scale estimation separate from dense-depth reconstruction priors.
Subsequent qualitative review should compare matched frames/clips and eventually
final renders. Existing D0–D4 measurements and human preferences remain separate
historical evidence and were not replaced by literature scores.

## Coverage and evidence

| Section | Scope |
| --- | --- |
| [#37 reference/discovery](depth-model-survey-sections/issue-37.md) | D0–D4, all eleven supplied entry points, cross-category map |
| [#38 metric](depth-model-survey-sections/issue-38.md) | Camera/scale variants, later releases, independent transfer evidence |
| [#39 relative/diffusion](depth-model-survey-sections/issue-39.md) | Alignment domains, generative detail, independent challenge |
| [#40 video](depth-model-survey-sections/issue-40.md) | Temporal metrics, motion, drift, chunking and streaming |
| [#41 multi-view](depth-model-survey-sections/issue-41.md) | Depth/pose/geometry, camera inputs, release changes |
| [#42 efficiency/detail](depth-model-survey-sections/issue-42.md) | Small models, refinement, complete-combination costs/terms |

Each section records initial discovery, two citation/table expansion rounds,
later evaluations and a bounded final gap pass. All user-supplied lists/topics,
arXiv, GitHub and Hugging Face have explicit dispositions. Search-record counts
are inspection steps, not claims that every linked source was exhaustively read.
The [verification record](depth-model-survey-data/verification.md) gives final
counts, overlap reconciliation, review outcomes and remaining evidence limits.

Publication dates, exact paper versions and inspected release revisions are
preserved. Some historical release dates, checkpoint-to-paper mappings, masks,
training overlap, runtime boundaries and dependency permissions remain unknown.
Late screened leads such as FE2E, HyDen, YOLO26, OptiGeo and WorldMirror 2.0 are
explicit coverage gaps. No model installation, weight download, inference,
training, GPU measurement or new human evaluation was performed for this survey.
