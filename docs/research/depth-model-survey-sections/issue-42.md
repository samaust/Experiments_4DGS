# Efficient and high-resolution depth methods — issue #42

Research cutoff and access date: **2026-09-30**. This section supports
[issue #42](https://github.com/samaust/Experiments_4DGS/issues/42) and the
[parent survey](https://github.com/samaust/Experiments_4DGS/issues/36).
It contains published evidence, not measurements on this host. The evidence
package has [models](../depth-model-survey-data/issue-42/models.csv),
[observations](../depth-model-survey-data/issue-42/benchmarks.csv),
[licenses](../depth-model-survey-data/issue-42/licenses.csv), and
[search history](../depth-model-survey-data/issue-42/search-log.csv).

**Depth Anything V2 Small is the clearest released candidate for a first
throughput/detail test with permissive code and exact weight terms.** Its
relative output cannot replace physical-scale estimation without another
source of scale. Its separately released Hypersim Small checkpoint is a
metric indoor candidate, but the paper's NYUv2-finetuned scores do not describe
that checkpoint. PatchFusion and its successors offer actual boundary evidence;
additional output pixels alone are insufficient evidence of detail. Missing
full-pipeline timings and component permissions limit a deployment choice.

## Small models: useful comparisons and limits

These are separate protocol groups. Unknown settings remain unknown in the CSV;
none of these tables establishes speed or memory use on this project's host.

| Published group | Model | Reported quality | Reported compute | Interpretation |
| --- | --- | --- | --- | --- |
| EfficientDepth v1, Tables 2–3 | DA V2 Small | NYUv2 AbsRel .035; ETH3D .0767 | .048 s/image, A40 | Baseline rerun by EfficientDepth authors. |
| Same tables | EfficientDepth Stage 3 | NYUv2 AbsRel .029; ETH3D .0729 | .055 s/image, A40 | Favorable author comparison, but no verified model release located. |
| MiDaS v3.1 v1, Table 1 | SwinV2-T | ETH3D AbsRel .111 | 64 FPS, RTX3090, square 256×256 | Released efficient legacy alternative. |
| Same table | LeViT224 | ETH3D AbsRel .121 | 73 FPS, RTX3090, square 224×224 | Different input sizes prevent a matched-resolution speed ranking. |
| LiteDepth v1, Table 1 | Zhenyu Li challenge submission | si-RMSE .311; RMSE 3.79 | 37 ms/image, Raspberry Pi 4 | Challenge-domain mobile evidence, not an indoor zero-shot foundation comparison. |

Sources: [EfficientDepth 2509.22527v1, §§4.1–4.3](https://arxiv.org/html/2509.22527v1),
[MiDaS 2307.14460v1, Table 1 and Figure 1](https://arxiv.org/pdf/2307.14460v1),
[LiteDepth 2209.00961v1](https://arxiv.org/html/2209.00961v1).

EfficientDepth times include preprocessing and postprocessing, exclude image
loading, and use a variable-resolution image collection. Batch size and
inference precision are unreported; BF16 is a **training** statement. The paper
cites MiDaS evaluation scripts but does not pin their alignment/crop implementation,
so these accuracy observations remain provisional within-paper comparisons.
They must not be pooled with other papers' NYUv2/ETH3D values. Stage 3 timing
excludes SimpleBoost. Its later patch blending route is a separate inventory row.

MiDaS's square models resize inputs and outputs. Its KITTI/NYUv2 table entries
are explicitly non-zero-shot; the extracted ETH3D rows avoid that ambiguity.
The paper and README report different rounded/aggregate values, so this section
uses the paper. LiteDepth aggressively reduces the image internally and upsamples
its result. Its paper's stated decoder shape is inconsistent with its stated
downsampling factor; the inventory preserves that uncertainty rather than
claiming native full-resolution detail. No comparable peak-memory measurement
was established for these candidates.

## High-resolution refinement: quality is not monotonic with more work

[PatchFusion's CVPR 2024 paper](https://openaccess.thecvf.com/content/CVPR2024/papers/Li_PatchFusion_An_End-to-End_Tile-Based_Framework_for_High-Resolution_Monocular_Metric_Depth_CVPR_2024_paper.pdf)
Table 1 compares **target-trained** models on UnrealStereo4K. The coarse ZoeDepth
prediction supplies global scale/context; local estimates and learned fusion
supply spatial detail. RGB/output resolution is 2160×3840, with 540×960 patches.
No test-time ground-truth alignment is stated in the inspected evaluation text;
unknown crop/range details still limit comparisons outside this table.

| Table 1 U4K variant | RMSE ↓ (m) | SEE ↓ |
| --- | ---: | ---: |
| ZoeDepth coarse | 1.2887 | .9144 |
| ZoeDepth + PatchFusion P16 | 1.0878 | .8382 |
| ZoeDepth + PatchFusion P49 + R128 | 1.0655 | .8488 |

SEE evaluates disparity disagreement near depth edges. The extra random patches
improve RMSE here while worsening SEE relative to P16. The output grid is the
same. This is evidence against treating patch count, pixel count, or global
RMSE as interchangeable measures of player-boundary quality. Table 2 reports
P16 at 2.782 s/image on an A100, but does not settle precision, patch batching,
pre/postprocessing or coarse-base inclusion.

The newer [PatchRefiner V2 preprint, 2501.01121v1](https://arxiv.org/html/2501.01121v1)
Table 1 offers a useful controlled architectural comparison at P16 on U4K:

| Fine/refinement branch | RMSE ↓ (m) | SEE ↓ | Additional parameters | Refiner-only time ↓ |
| --- | ---: | ---: | ---: | ---: |
| PatchFusion † | 1.064 | .855 | 432.7M | 3.44 s |
| PatchRefiner † | .941 | .771 | 369.0M | 1.45 s |
| PRV2-M, MobileNet-Small | 1.003 | .832 | 47.0M | .32 s |
| PRV2-E, EfficientNet-B5 | .948 | .816 | 72.1M | .57 s |
| PRV2-C, ConvNeXt-Large | .884 | .787 | 245.8M | .62 s |

**Both parameter counts and timings exclude the coarse estimator.** The paper
states A100 for inference benchmarks; precision and patch batching are unknown.
The dagger means fine-branch pretraining was made comparable by removing
nonpublic MiDaS pretraining. It does not mean ground-truth depth alignment.
These retrained baselines are separate model IDs from the original PatchFusion
rows. PRV2-C has lower RMSE than PR† but higher SEE: even this controlled group
has no single quality winner. The released ICLR2026 checkpoint names do not yet
establish which artifacts reproduce each preprint M/E/C row.

The citation trail also inspected
[BoostingDepth CVPR2021](https://yaksoy.github.io/papers/CVPR21-HighResDepth.pdf),
[PatchRefiner ECCV2024](https://www.ecva.net/papers/eccv_2024/papers_ECCV/papers/08418.pdf),
and [PRO ICCV2025](https://openaccess.thecvf.com/content/ICCV2025/papers/Kwon_One_Look_is_Enough_Seamless_Patchwise_Refinement_for_Zero-Shot_Monocular_ICCV_2025_paper.pdf).
Original BoostingDepth's disparity RMSE is not metric RMSE. PatchRefiner's table
copies original PatchFusion baseline results; PRV2's dagger baselines are reruns.
PRO instead rebuilds the comparison around DA V2 and retrains the refiners on
U4K. Its Middle14 PRO row reports AbsRel .0287 and D³R .0803, but the exact
per-dataset evaluator path was not traced; these remain source-attributed values,
not a pooled ranking. D³R, SEE and DIS boundary recall measure different properties.

## Newer high-resolution routes and exact combinations

[InfiniDepth v1](https://arxiv.org/html/2601.03252v1) uses a DINOv3-L encoder and
queries an implicit depth decoder directly at the requested coordinates. Its
Synth4K RGB input is 504×896, while depth is queried at 3840×2160; comparison
baselines are bilinearly upsampled. Table 1's high-frequency-mask delta1 of
67.5% on Synth4K-1 provides an explicit detail observation, under ground-truth
scale-and-shift alignment. It does not prove metric scale. Table 6's .16 s
uses a 504×672 input, unknown hardware, and entire-model timing; the adjoining
15M parameter count is **decoder only**. It is not a measured full-4K pipeline cost.

The [current InfiniDepth release](https://github.com/zju3dv/InfiniDepth/blob/669a9b8354fb0f3f2f73814207ebdd519dc5c6d3/INSTALL.md)
adds MoGe-2 for RGB metric restoration, optional Gaussian/sky checkpoints, and
optional DA3 sequence alignment. The sparse-depth-assisted checkpoint and its
paper metric benchmark require additional sensor information. These routes
must not inherit the RGB-only paper's timing or be counted as calibrated-camera
video consistency evidence.

[PPD's release](https://github.com/gangweix/pixel-perfect-depth/blob/427a86f5882aa3f7233c1b94fbdccce87f1c8313/README.md)
separates DA2 semantics and MoGe2 semantics checkpoints. It predicts relative
depth; point-cloud export adds MoGe2 scale/intrinsics recovery. The inspected
entrypoint uses configurable diffusion steps and resizes output to the original
image. Its detailed relative-depth comparisons belong to issue #39; neither
larger output nor a video wrapper establishes temporal consistency.

The bounded final pass recorded OptiGeo, XiDepth, MoGe-3 SSR, HyDen-MoGeV2 and
YOLO26n-depth. MoGe-3's main evidence belongs to issue #38. HyDen has an author
release but noncommercial research terms; its headline speed multiplier was
not promoted to a measured comparison. YOLO's mutable official documentation
distinguishes relative log-depth calibration, augmented/aligned accuracy, and
inference-only speed; a historical cutoff pin is missing. These are explicit
follow-up gaps, not invisible exclusions. GraphDepth and aerial D³-RSMDE were
screened and excluded from detailed extraction because of unverified artifacts
and domain specialization, respectively.

## Release and commercial-use findings

The CSV separates code, weights, inference/output terms and explicit commercial
offers. “Unresolved” means no adequate grant was established, not a prohibition.
Pins identify inspected documentation; no weight was downloaded or executed.

| Exact candidate/combination | Code | Weights and combined inference | Outputs / commercial route |
| --- | --- | --- | --- |
| DA V2 Small relative / Hypersim Small | Apache-2.0 | Exact author Small cards Apache-2.0 | No separate output restriction or commercial negotiation offer found. |
| PatchFusion + released ZoeDepth combined checkpoint | MIT | Named HF combined artifact MIT; upstream pretrained provenance remains qualified | No output-specific restriction or commercial offer found; not a full dependency clearance. |
| PRV2 M/E/C + ZoeDepth coarse | No grant located | Drive release exists; exact variant mapping and weight grant unresolved | Output use unresolved; no offer found. |
| PatchRefiner + ZoeDepth | MIT | External checkpoint grant unresolved | Output use unresolved; no offer found. |
| PRO + DA V2 Large | MIT file conflicts with restrictive README | README restricts code and checkpoint to research/education; DA2-Large separately noncommercial | Formal PI permission explicitly required for commercial use; cannot clear upstream rights. |
| BoostingDepth + MiDaS | Academic-use restriction | Base and merge checkpoint terms must both apply | No output-specific grant or commercial offer located. |
| InfiniDepth RGB | Custom registration license | Apache-2.0 author checkpoint card; encoder and added model terms remain material | Organizational project registration required before code use, automatically granted without fee; no separate output restriction found. |
| PPD + DA2-Large | Apache-2.0 PPD code/card | Required DA2-Large is CC-BY-NC-4.0 | Combined commercial inference restricted despite PPD's permissive card; MoGe2 variant separately unresolved. |
| EfficientDepth / LiteDepth | Release or code grant unresolved | Exact tested weight grant unresolved | No verified inference/output grant or commercial offer. |

Sources: [DA V2 code/license declaration](https://github.com/DepthAnything/Depth-Anything-V2/blob/a561b849ebae10a6f5ef49e26c83cbbcd36c71bf/README.md),
[Small card](https://huggingface.co/depth-anything/Depth-Anything-V2-Small/blob/03876f8651c73a60fe4c2c48294e09fcb6838fcf/README.md),
[Hypersim Small card](https://huggingface.co/depth-anything/Depth-Anything-V2-Metric-Hypersim-Small/blob/3bc65d4e14a6786a61acec16453c50e12bf5f338/README.md),
[PatchFusion card](https://huggingface.co/Zhyever/patchfusion_zoedepth/blob/dd370f4b1231b32a6f5610e5089a420f55ddc268/README.md),
[PRV2 release](https://github.com/zhyever/PatchRefinerV2/blob/7f6341c58c12d98743edb8769d0471fbf9f17e62/README.md),
[PatchRefiner release](https://github.com/zhyever/PatchRefiner/blob/b2e747716a697a106e26ee6890b34ad7dcc89d10/README.md),
[PRO conflicting declaration](https://github.com/KAIST-VICLab/One-Look-is-Enough/blob/42aff9ab05c7a3e5e982892115941811ff262e8e/README.md),
[BoostingDepth license](https://github.com/compphoto/BoostingMonocularDepth/blob/fa16de03ec985c74aa4a0109b7235d78a4e598e7/LICENSE),
[InfiniDepth PRL](https://github.com/zju3dv/InfiniDepth/blob/669a9b8354fb0f3f2f73814207ebdd519dc5c6d3/LICENSE),
[InfiniDepth checkpoint card](https://huggingface.co/ritianyu/InfiniDepth/blob/b387ad877e922468fcd85190f24e5b78b28dcd66/README.md),
[PPD checkpoint card](https://huggingface.co/gangweix/Pixel-Perfect-Depth/blob/be33763bc1bc1c581869a20ffde66c36b304b1a7/README.md).

## Project fit and bounded next tests

For calibrated Basketball frames at 960×540, a small model could reduce repeated
camera-frame work. Whether it retains thin limbs, player/floor separation,
occluded boundaries and scene scale remains a project-specific question.
Tiling may have less benefit at this resolution than at paper 4K inputs and can
introduce inconsistency between overlapping patches. Independent per-frame
models have no established Basketball temporal consistency here; known camera
calibration does not remove their monocular scale ambiguity automatically.

1. **DA V2 Small relative and Hypersim Small, separately:** compare throughput,
   player boundaries and stability; determine whether the metric checkpoint's
   indoor scale transfers. Keep relative detail and unaligned metric accuracy
   separate.
2. **PatchFusion ZoeDepth as the released refinement reference:** test whether
   actual boundary gains survive downsampling to the workflow size and whether
   full base-plus-refiner cost is justified. Confirm upstream artifact terms
   before a commercial trial.
3. **PRV2 and InfiniDepth as conditional detail candidates:** first resolve PRV2
   checkpoint mapping/license and InfiniDepth component/registration conditions;
   then test boundary accuracy alongside calibration and full pipeline cost.
   This survey authorizes no execution.

EfficientDepth remains a paper lead until its artifact is identified. PRO and
PPD+DA2-Large are research candidates with explicit commercial constraints.
There is no demonstrated temporal winner or full-pipeline memory winner in this
category.

## Verification and acceptance assessment

The bounded category pass logged initial discovery, two genuine reference/table
expansions, later independent evaluation, and a final recent-paper/release pass.
Its **21 search records, 26 variant records, 39 numeric observations and 21
license records** include paper-only and screened-only dispositions. Central
issue #37 owns the all-supplied-list/topic coverage; this section does not claim
it independently screened every repository on those lists.

Numerical checks used the exact EfficientDepth v1 Tables 2–3, MiDaS v1 Table 1
and Figure 1, LiteDepth v1 Table 1, PatchFusion camera-ready Tables 1–2, PRV2 v1
Table 1/caption and §4.4, PRO camera-ready Table 1, and InfiniDepth v1 Tables 1/6
and Appendix C.1. Extracted PatchFusion PDF rows were re-read against their
headers. No absent score is encoded as zero. The CSV keeps unknown masks,
alignment details, precision, memory and inclusion boundaries explicit.

Pinned GitHub license/README text and author model-card metadata were inspected;
HF card access failures in the browser were resolved by read-only host retrieval.
No checkpoint bytes were fetched. The audit covers the named combinations and
identified material dependencies; it is not a complete transitive license audit.
Unresolved weight grants, historical cutoff pins for final leads, and
paper-to-release correspondence are findings requiring resolution before later
adoption. CSV parsing, model references, numerical types, Markdown links and
`git diff --check` were checked before committing. No application tests or GPU
experiments were run for this documentation-only change.
