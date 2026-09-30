# Relative and diffusion depth — issue #39

Evidence cutoff and access date: **2026-09-30**. This section supports [issue #39](https://github.com/samaust/Experiments_4DGS/issues/39) and parent #36. It contains published observations, release checks, and project inferences; no local model measurements.

**Useful candidates depend on the role.** Depth Anything V2 Small is a practical commercial depth-ordering baseline. Marigold V2 Log-stage2 is a released detail candidate with declared Apache code, adapters, and Qwen base. Lotus-D adds a deterministic diffusion-derived alternative. None recovers physical scale merely because its predictions score well after ground-truth alignment.

## Discovery and release inventory

The [search log](../depth-model-survey-data/issue-39/search-log.csv) records 16 query/table/release/protocol steps. Initial category searches led to Depth Anything V2 and Marigold; first expansion followed their tables to older and generative baselines; second expansion inspected Lotus and GenPercept. Later Lotus-2, Marigold V2, and MDEC2025 evaluations extended coverage through the cutoff. The [21-row inventory](../depth-model-survey-data/issue-39/models.csv) distinguishes artifacts from unresolved comparison-row identities. The parent discovery section owns the supplied community-list/topic census; this category does not claim exhaustive coverage.

| Family / exact relevant variant | Output and release disposition |
| --- | --- |
| Depth Anything V2 Small / Large | Public relative students; affine-invariant **inverse depth**. Large-hf is a separate Transformers implementation. |
| Depth Anything V2 Giant | Paper results; official checkpoint table still says “Coming soon.” A failed guessed endpoint does not establish a gated release. |
| Depth Anything V2 Hypersim metric fine-tune | Separate metric model; cross-reference metric section, never substitute its scores for relative students. |
| Marigold depth-v1-0 / depth-v1-1 | Public linear relative depth; scheduler/training changes make these distinct releases. |
| Marigold V2 `depth/Log-stage2` | Public adapters and base; affine-invariant **log depth**. Uniform/disparity ablations are different models. |
| Lotus D `v2-0-disparity` / G `v2-1-disparity` | Public inverse-depth releases; D deterministic, G stochastic. Old D `v1-1` predicts linear depth. Exact current-file correspondence to final paper rows is unreported. |
| Lotus-2 depth core + sharpener | Public adapters, gated FLUX.1-dev dependency. Core-only and full method differ. |
| GenPercept | Public depth/disparity and decoder variants. Main-paper collection is not safely interchangeable with the unspecified checkpoint in Lotus's rerun row. |

Official release evidence: [Depth Anything V2](https://github.com/DepthAnything/Depth-Anything-V2/blob/a561b849ebae10a6f5ef49e26c83cbbcd36c71bf/README.md), [Marigold](https://github.com/prs-eth/Marigold/blob/2bfbdeae5d10a50b71f1ba20c865d46e480f6010/README.md), [Marigold V2](https://github.com/huawei-bayerlab/marigold-v2/blob/bf21e4ad9fb0ae1376bbfb2ec79e999802f19a85/README.md), [Lotus](https://github.com/EnVision-Research/Lotus/blob/b737e12238d2a41fc582ee8c6c6b1104d318d799/README.md), [Lotus-2](https://github.com/EnVision-Research/Lotus-2/blob/2d5e4522f7213611184fd31992d0fac17ec36035/README.md), [GenPercept](https://github.com/aim-uofa/GenPercept/blob/7cff083bee566e88f0c82259eb7c62c94dd1dca1/README.md). CSVs pin code and available weight repository revisions separately; pins are metadata snapshots, not downloaded weight checksums.

MiDaS/DPT remain older references; DepthFM/GeoWizard are screened generative leads. PPD and InfiniDepth are later detail contenders cross-referenced to the high-resolution section. FE2E is screened only and not shortlisted; its full release/licensing audit remains a coverage gap. BetterDepth/PrimeDepth remain refinement coverage gaps. Sparse-depth Marigold-DC/SSD and metric MetricGold require different roles. No release or commercial permission is inferred for these screened candidates.

## What the comparisons establish

[Benchmark records](../depth-model-survey-data/issue-39/benchmarks.csv) contain 44 observations. Unknown split/crop/cap/fit-domain information remains explicit. The following groups are separate; their scores must not be pooled.

**Ordinal depth, DA-2K.** The original author's Table 3 reports pairwise ordering accuracy: Small **95.3%**, Large **97.1%**, Giant **97.4%**, Marigold **86.8%**. This supports ordering, without fitting metric depth. Pair selection includes model-disagreement mining; it is neither dense boundary accuracy nor a random sample of Basketball footage. Table 2 also retains Small/Large/Giant NYU and KITTI AbsRel in the CSV; its incomplete alignment specification prevents comparison with Marigold's depth-space fit. [Depth Anything V2, 2406.09414v2, Tables 2–3 and §6](https://arxiv.org/html/2406.09414v2).

**Linear-depth least squares, NYUv2.** Each prediction receives its own ground-truth scale and shift. All values below are percentages; rows use the same Marigold extension protocol, with standard VAE and full precision.

| Release | Ensemble × steps | AbsRel ↓ | δ1 ↑ |
| --- | --- | --- | --- |
| Marigold v1.0 | 10 × 50 | 5.5 | 96.4 |
| Marigold v1.1 | 1 × 1 | 5.9 | 96.1 |
| Marigold v1.1 | 10 × 4 | 5.5 | 96.4 |

The extension's Table II measures v1.1 at **0.568 s/image**, one step and one ensemble, **768×768 on RTX 3090**. These settings cannot be attached to the many-evaluation accuracy row. [Marigold extension, 2505.09358v1, Tables I–II and §III-F](https://arxiv.org/html/2505.09358v1).

**Other least-squares reports, with incomplete protocol equivalence.** Lotus final v5 Table 1 reports NYU/KITTI AbsRel (%) of **5.1/8.1** for D and **5.4/8.5** for G. Its marked GenPercept rerun gives **5.6/13.0**. These are source observations, not a controlled ranking against earlier tables: fit-domain details and exact released-file correspondence are incomplete. Earlier Lotus v2 scores differ; the CSV uses final v5. [Lotus, 2409.18124v5, Table 1 and Appendix A.2](https://arxiv.org/html/2409.18124v5). Lotus-2's original least-squares report gives NYU/DIODE **4.1/22.1**, using the full predictor/sharpener. [Lotus-2, 2512.01030v1, Table I and §V-A](https://arxiv.org/html/2512.01030v1).

**Later RANSAC and detail evidence.** Marigold V2 Table 1 reports NYU/DIODE AbsRel (%) **3.6/5.2**, and its Lotus-2 rerun **3.7/6.5**. Table 2 reports Hypersim SEE3 **0.352** for V2, **0.404** for PPD and **0.470** for InfiniDepth. SEE tolerates a small edge displacement; Hypersim is also a training domain. These observations support further detail testing without establishing moving-player or unseen-domain superiority. [Marigold V2, 2609.08084v1, Tables 1–2](https://arxiv.org/html/2609.08084v1).

The [released evaluator](https://github.com/huawei-bayerlab/marigold-v2/blob/bf21e4ad9fb0ae1376bbfb2ec79e999802f19a85/evaluation/depth/eval.py) fits **log depth**, then exponentiates. Its DIODE mask also rejects large ground-truth depth gradients. This differs from older linear-depth fitting. The CSV preserves the older Marigold DIODE **30.8** and V2's copied **10.0** separately; changed masks/alignment may explain part of the discrepancy, but copied-baseline provenance does not fully reconcile it. V2 copies most older rows from PPD; only named reruns can be treated as new evaluations. Original PPD text does not by itself establish the later evaluator's full protocol. [PPD original comparison](https://arxiv.org/html/2510.07316v1).

**External challenge and boundaries.** MDEC2025 reruns v1.0 and Large-hf at native resolution; Marigold uses ten DDIM steps and one ensemble.

| Baseline | Reconstruction F ↑ | Edge F ↑ | AbsRel ↓ |
| --- | --- | --- | --- |
| Marigold v1.0 | 17.01 | 9.19 | 29.42 |
| DA V2 Large-hf | 14.34 | 6.72 | 33.57 |

Values retain the table's reported scale. Section 3 describes depth-space scale-and-shift fitting after disparity inversion, but §5 permits median scaling or least squares. Without resolving each row's alignment, this is suggestive external evidence, not a definitive common-protocol ranking. The test data excludes dynamic artifacts; several authors overlap Marigold's team. [MDEC2025, Table 1 p.6187, §§3–5](https://openaccess.thecvf.com/content/CVPR2025W/MDEC/papers/Obukhov_The_Fourth_Monocular_Depth_Estimation_Challenge_CVPRW_2025_paper.pdf).

Runtime remains deployment-specific. V2 Table 6 reports **1.9 s / 16.9 GB** at **1024²** on an unnamed **32 GB GPU**; full Lotus-2 is **8.9 s / 26.1 GB** under that evaluator. The official Lotus-2 README separately requires **40 GB** for its own pipeline. Precision, loading and implementation differences are unresolved; neither measurement guarantees operation on this host. Batch/warmup and some baseline sampling details remain unknown. No temporal score was found for these shortlisted single-image releases.

## Commercial dispositions

The [license records](../depth-model-survey-data/issue-39/licenses.csv) cover 12 serious release variants with separate code, weight, output and commercial-offer fields. They use official license files, cards and README statements; this is not a complete dependency clearance.

| Candidate | Code / weights | Inference and outputs | Explicit commercial route |
| --- | --- | --- | --- |
| DA V2 Small | Apache / Apache | Commercial inference allowed under declared terms; no separate output clause found | None found |
| DA V2 Large / Large-hf | Apache / CC-BY-NC | Commercial operation needs further permission; ordinary outputs are not automatically assigned the weight license | None found |
| Marigold v1.0 | Apache / artifact Apache conflicts with repository RAIL notice | Unresolved full-pipeline declaration conflict | None found |
| Marigold v1.1 | Apache / Open RAIL++ | Conditional commercial use; output use must comply with model restrictions | None found |
| Marigold V2 Log-stage2 | Apache / Apache adapters and Qwen base | Declared commercial inference permitted; no special output clause found | None needed under inspected grants |
| Lotus D/G | Apache / Apache cards | Upstream SD component qualification remains; no special Lotus output clause found | None found |
| Lotus-2 | Apache / Apache adapters + gated FLUX NC base | Commercial outputs and commercial model operation have different permissions | [BFL licensing](https://bfl.ai/licensing); coverage must be checked |
| GenPercept | BSD files conflict with NC academic README | Commercial permission unresolved; no project output grant found | README explicitly directs commercial inquiries to Chunhua Shen |

Key adverse evidence: [Marigold v1.0 artifact license](https://huggingface.co/prs-eth/marigold-depth-v1-0/blob/f4fc453d7d217cbe30ddcad3eb311d1ad9a11c4c/LICENSE.txt), [RAIL model terms](https://github.com/prs-eth/Marigold/blob/2bfbdeae5d10a50b71f1ba20c865d46e480f6010/LICENSE-MODEL.txt), [GenPercept license and README](https://github.com/aim-uofa/GenPercept/tree/7cff083bee566e88f0c82259eb7c62c94dd1dca1), [FLUX weight terms](https://huggingface.co/black-forest-labs/FLUX.1-dev/blob/main/LICENSE.md). FLUX's current HF and BFL terms identify different versions; the applicable acquisition agreement must be pinned before use. Generic author addresses are not treated as licensing offers.

## Basketball fit and future questions

**Project inference:** known intrinsics determine rays but do not recover the missing depth scale/shift. Linear relative depth needs spatially distributed metric anchors to fit an affine map. Inverse depth needs fitting in inverse depth before inversion; log depth needs log-domain anchoring before exponentiation. Anchors could come from reliable calibrated multiview correspondences or surveyed geometry, with motion/occlusion handling and held-out validation. A single global scale alone generally cannot identify two affine degrees of freedom. Even successful per-image fits can drift between cameras and frames.

A bounded future set is **DA V2 Small** for ordering/commercial practicality, **Marigold V2 Log-stage2** for detail, and **Lotus-D disparity** as a deterministic comparator. Test whether player silhouettes, limbs and net boundaries improve after separately validated anchors; whether cross-camera depth agrees at occlusions; and whether frame-to-frame scale and edge placement remain stable. Marigold v1.1 is an optional sampling-cost control. Lotus-2 is a secondary research comparator once resource and backbone terms are resolved. No single-image method here earns a video-consistency or unanchored metric-scale recommendation. These questions do not authorize experiments or alter D0–D4 evidence.

## Verification and acceptance record

Rechecked each selected number against its named table/header/row, including percentage-versus-ratio units and step/ensemble settings. MDEC Table 1 was rendered and visually inspected after PDF extraction warnings; its table was legible. Read final Lotus v5 after discovering older-draft differences. Checked V2 alignment/masks in pinned code without running it. Cross-paper contradictions, ambiguous fits, copied rows and non-identical implementations remain visible.

CSV parsing, nonempty fields, scoped IDs, benchmark/license foreign keys, numeric values, task-only diff and whitespace checks passed. Primary paper URLs, official code/model endpoints and shortlisted license pages were accessed; exact model data were not downloaded. All inspected code-commit and model-modification timestamps fall before the cutoff; model repository creation dates are recorded separately and do not prove public first release. Historical first-release dates and paper-to-artifact hashes not established by these snapshots remain unknown. All acceptance topics are covered; unresolved upstream crop/protocol and licensing facts are findings, not inferred permission or fabricated measurements.
