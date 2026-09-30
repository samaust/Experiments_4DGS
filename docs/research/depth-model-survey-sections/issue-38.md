# Additional monocular metric depth — issue #38

Research/access cutoff: **2026-09-30**. This section supports physical-scale
candidate selection beyond D0–D4; it contains published evidence, not Basketball
measurements. The most useful next comparison is MoGe-2 with predicted versus
supplied FoV, followed by MoGe-3 for the cost of improving geometry detail.
UniDAC adds a materially different calibrated-camera route, but its exact weight
license is unresolved. MetricAnything warrants a separate focal-contract test.
These are proposed experiments, not a universal ranking.

Evidence: [searches](../depth-model-survey-data/issue-38/search-log.csv),
[variants](../depth-model-survey-data/issue-38/models.csv),
[observations](../depth-model-survey-data/issue-38/benchmarks.csv), and
[licenses](../depth-model-survey-data/issue-38/licenses.csv).

## Inputs, geometry and availability

| Candidate | Camera information and output | Release finding at cutoff |
| --- | --- | --- |
| **MoGe-2 ViT-L** | Predicts focal/FoV and metric camera point map; depth is its **z-channel**. Optional horizontal FoV is a separate inference mode, not arbitrary distorted-camera calibration. | Original `Ruicheng/moge-2-vitl` and later `moge-2-vitl-normal` are separate public artifacts. The normal release must not silently replace the original paper model. [Paper][M2], [code][MC]. |
| **MoGe-3 ViT-L / ViT-G** | Same family, with sparse volumetric refinement of camera-space geometry. Predicted-camera input; paper default uses three refinement iterations. | Both public `moge-3-vitl` and `moge-3-vitg` checkpoints exist. Paper v2 is dated July 21, 2026; HF metadata lists September 2 updates. Paper's future-release wording is superseded by the inspected release. [Paper][M3], [code][MC]. |
| **ZoeD-M12-N / K / NK** | RGB-only metric depth, without a camera-estimation output. N/K are indoor/outdoor heads; NK routes between two heads. | Exact original `ZoeD_M12_N.pt`, `K.pt`, `NK.pt` assets are in GitHub v1.0. These are variants of one family. Legacy MiDaS/BEiT environment; code is archived. [Paper][Z], [release][ZR]. |
| **DAC Swin-L indoor / outdoor** | Full camera model for mapping to ERP; predicts **Euclidean ray distance**, not camera-z. | Both exact `dac_swinl_{indoor,outdoor}.pt` files and ResNet alternatives are listed on the author hub. DAC-U in the UniDAC comparison is an author-retrained baseline, not these domain-specific releases. [Paper][D], [release][DH]. |
| **UniDAC ViT-L** | Calibrated ERP route; separate AnyCalib-assisted route predicts intrinsics. KITTI-360 prediction approximates UCM as MEI and is not the known-camera condition. | Public `girish1511/UniDAC/unidac.pt`; exact mapping to every paper training ablation remains unknown. DINOv3 and optional AnyCalib add dependencies. [Paper][U], [code][UC]. |
| **UniK3D ViT-L** | Predicts general camera rays and radial metric distance; also accepts supplied camera models/rays. Convert radial distance to camera-z where required. | Public author ViT-L weights; smaller variants exist. Predicted-ray evaluation is separate from supplied-ray inference. [Paper][K], [code][KC]. |
| **MetricAnything students** | DepthMap uses **focal length**; PointMap is explicitly a fine-tuned MoGe-2 with RGB-only camera prediction. | Two public checkpoints, not two independent architectures. Sparse-depth teacher remains marked TBD/coming soon. [Paper][MA], [code][MAC]. |
| **ZeroDepth unified** | RGB and full intrinsics; geometric embedding provides a distinct older route. | Official VIDAR hub identifies `ZeroDepth_unified.ckpt`; no binary download or integrity check. Noncommercial code limits the commercial shortlist. [Official implementation][V]. |

The MetricAnything depth interface needs special care: its CLI takes an override,
JSON `fx`, or image width; its direct `infer` API instead has a fixed focal default.
Neither fallback estimates the camera. The paper describes viewing-ray distance,
whereas the release computes depth from focal-scaled canonical inverse depth.
That leaves the exact radial-versus-z contract unresolved for an adapter.
[Release documentation][MAD], [implementation][MAI].

## What the accuracy evidence supports

**Original MoGe-2 metric depth**, author evaluation, [Appendix A.3 and Table B.4][M2].
AbsRel and delta1 are percentages; lower/higher is better respectively. These
outputs are explicitly evaluated **without GT alignment or additional range
clamping**, except postprocessing hardcoded inside each model. Supplied-FoV rows
are a different input condition. Exact accuracy-table resolution, crop and GT
valid-range settings are not fully specified in the inspected paper.

| MoGe-2 ViT-L input mode | NYUv2 AbsRel / delta1 | iBims-1 AbsRel / delta1 |
| --- | --- | --- |
| Predicted camera | 7.33 / 96.1 | 13.6 / 83.0 |
| Supplied camera FoV | 6.46 / 96.9 | 9.92 / 92.4 |

This is evidence for testing calibrated input. It is not a promise of the same
benefit on the Basketball cameras. The paper's point-map scores use optimal GT
**translation**; aligned relative-depth scores use scale or scale-and-shift.
Neither should be substituted for the unaligned depth numbers above.

**Later same-family comparison**, [MoGe-3 v2 Table C.1, metric-depth block][M3].
All methods use their own predicted cameras. Values below are AbsRel percentages.
The section labels this metric evaluation; exact crop, cap and metric-alignment
implementation are not independently established by its text. These are
source-local comparisons, not a merged leaderboard.

| Paper row | NYUv2 | KITTI | iBims-1 |
| --- | ---: | ---: | ---: |
| MoGe-2 | 6.90 | 17.6 | 14.6 |
| MoGe-3 ViT-L, step 3 | 8.43 | 12.6 | 11.7 |
| MoGe-3 ViT-G, step 3 | 10.5 | 10.7 | 11.0 |

MoGe-3 improves KITTI/iBims in this table but regresses on NYUv2. A larger
backbone therefore is not uniformly better for metric scale. MoGe-2's later
NYUv2/iBims values differ from the original paper above; exact baseline
checkpoint and preprocessing changes are not identified. Both observations are
retained. The aggregate benchmark also changes, adding Synth4K and omitting
DDAD; aggregate values across these papers are not interchangeable. The local
fine-detail evaluation fits GT scale and segment shifts, and establishes shape
detail rather than absolute scale. [Evaluation sections and appendix][M3].

**Cross-camera transfer**, [UniDAC v1 Table 7][U], delta1 as a fraction. The UniDAC
rows below are specifically the full-mixture **+A2D2** rows, not its smaller
training ablations. Reported metric evaluation has no described GT-depth fitting;
exact crop/cap and test image counts remain unknown. UniK3D had large-FoV training,
while UniDAC trained on perspective data; this is not a controlled data ablation.

| Input condition | Method | ScanNet++ | KITTI-360 |
| --- | --- | ---: | ---: |
| Predicted camera | UniK3D ViT-L | 0.651 | 0.817 |
| Predicted camera | UniDAC + AnyCalib | 0.917 | 0.815 |
| Ground-truth camera — separate condition | UniDAC | 0.918 | 0.836 |

The predicted-camera comparison favors UniDAC on ScanNet++, while KITTI-360
shows no such advantage in delta1. Camera prediction and projection conversion
are part of the method, and should be evaluated separately from known-camera
inference. UniDAC's training-image totals conflict between its prose and tables;
the table's **Dataset Size** is not a parameter count. Its DAC-U checkpoint was
retrained by the authors; UniDepth/Metric3Dv2 comparison numbers in its main
setup are inherited from DAC. [Sections 5.1 and 8][U].

**Older and newer transfer evidence with separate protocols.** ZoeDepth's own
SUN RGB-D comparison evaluates the same unseen images, Eigen crop, capped metric
depth and matched input resolution; its N and NK models report AbsRel **0.119**
and **0.123**, respectively. The specialist head thus remains informative as an
older transfer baseline. [ZoeDepth v1 Tables 3/7/8][Z]. MetricAnything's DepthMap
student reports AbsRel **0.147** on ETH3D, **0.085** on SUN RGB-D, and **0.792** on
Sintel. These are explicitly unseen by its authors, but missing crop, resolution,
cap, focal-source and alignment details prevent direct ranking against ZoeDepth
or MoGe. [MetricAnything v1 Tables 3/4, §4.2.1][MA].

**Independent adverse evidence**, [AerialMetric v1 Table 3][A], Oblique-City
held-out scenes, no GT intrinsics. AbsRel/delta1 are percentages. The authors
rerun public code, exclude invalid GT and clip predictions to the reported
range. These aerial results do not measure Basketball or indoor transfer.

| Released baseline or adapted model | AbsRel ↓ | delta1 ↑ | Training distinction |
| --- | ---: | ---: | --- |
| ZoeDepth-NK | 97.1 | 0.0 | Original; zero-shot aerial |
| MoGe2-L (README: normal release) | 48.4 | 5.1 | Original; zero-shot aerial |
| UniDepthV2-L reference | 31.0 | 34.1 | Original; zero-shot aerial |
| MoGe2-Aerial | 10.3 | 89.3 | Adapted on aerial training data |

This reverses the temptation to treat an open-domain average as universal scale
reliability. The adapted model is a fine-tuning of MoGe, not a new independent
family or an independent evaluation of itself. Its improved in-domain result
also does not establish superiority on an unseen indoor court.

## Availability and four commercial-use findings

The following records inspect author code texts, exact model cards or original
release listings. **Allowed** refers to the inspected grant and its conditions;
missing weight terms are not silently filled in from a software license. Output
rights are separate from permission to run inference. No affirmative commercial
licensing offer or negotiation process was found in these inspected sources;
a generic research contact is not recorded as an offer.

| Candidate | Code commercially usable? | Exact weights commercially usable? | Inference and outputs | Explicit commercial offer |
| --- | --- | --- | --- | --- |
| MoGe-2 / MoGe-3 releases above | MIT; DINOv2 code Apache-2.0 | MIT in each exact author HF card | Grants support commercial inference; no separate output restriction stated | None found |
| DAC indoor/outdoor | MIT | MIT author hub metadata | Same; third-party notices remain | None found |
| MetricAnything released students | Apache-2.0 top level | Apache-2.0 author cards | Grants support inference; no separate output restriction stated; inherited source notices matter | None found |
| ZoeDepth N/K/NK | MIT | **Unresolved**: original v1.0 assets lack a distinct explicit weight grant | Software grant alone does not establish commercial weight use; no independent output restriction identified | None found |
| UniDAC; DAC-U retraining | MIT software | **Unresolved**: UniDAC card lacks license; DAC-U artifact unidentified | Weight scope unresolved; DINOv3 custom terms and AnyCalib require separate review | None found |
| UniK3D | **Noncommercial**: LICENSE says CC-BY-NC-SA-4.0; README says BY-NC-4.0 | **Unresolved** exact weight scope; HF card lacks license | Commercial code restriction is clear; output copyrights are not inferred from it | None found |
| ZeroDepth | **Noncommercial**, VIDAR CC-BY-NC-4.0 | Separate S3 weight grant unresolved | Not commercially cleared; no independent output terms established | None found |
| MoGe2-Aerial | MIT original modifications, with stated academic citation condition | README applies MIT to model, subject to inherited MoGe/DINOv2 terms | Qualified commercial path; model-specific text describes modifications and inherited obligations | None found |

Sources and full pins are in [licenses.csv](../depth-model-survey-data/issue-38/licenses.csv):
[MoGe license][ML], [MoGe HF cards][MH], [DAC card][DH],
[MetricAnything cards][MAH], [Zoe original release][ZR], [UniDAC card][UH],
[UniK3D license][KL], [VIDAR license][VL], [AerialMetric terms][AL].
This is not a full dependency clearance: DINOv3 has a custom grant; MetricAnything
DepthMap acknowledges Depth Pro, and PointMap retains MoGe/DINOv2 dependencies.
[UniDAC training instructions][UC], [DINOv3 terms][D3L], [student sources][MAC].

## Project fit and next-test questions

| Proposed future test | Evidence-based purpose | Question the experiment must answer |
| --- | --- | --- |
| MoGe-2 original ViT-L, predicted versus calibrated FoV | Direct unaligned depth evidence and permissive exact-card licensing | Does using resized camera FoV improve stable physical scale across cameras, players and occlusions? |
| MoGe-3 ViT-L versus MoGe-2 | Later metric/detail evidence, with visible NYUv2 regression | Does refinement improve useful player/court boundaries without worsening scale or frame-to-frame variation? |
| UniDAC known-camera, conditional on weight clarification | Different projection treatment and strong wide-camera evidence | Does radial-to-z conversion and ERP processing help calibrated court views enough to justify the added pipeline? |
| MetricAnything DepthMap, conditional on geometry-contract check | Distinct focal-conditioned student and broad transfer evidence | Are fx, resizing and depth semantics correct, and does native scale survive camera changes? |

No temporal-consistency shortlist is established by these single-image papers.
MoGe-3's aligned local detail evidence alone cannot prove stable moving-player
geometry. A future test should keep physical-scale estimation distinct from
using dense depth as a reconstruction prior.

For compute context, MoGe-3 [Table C.4][M3] reports **39 / 121 / 177 ms** for
MoGe-2 ViT-L / MoGe-3 ViT-L / MoGe-3 ViT-G at the same native resolution, FP16,
batch-one, single-A100 setting; the latter models use three refinement steps.
CSV records preserve the exact resolution and sampling context. This is not host
latency or memory evidence; model loading, I/O and compilation inclusion is not
stated, and v3 peak memory is not supplied there.

## Coverage and verification

The bounded category search produced **21 search records, 22 variant/input-mode
records, 59 numeric observations and 21 licensing records**. The remaining model
record is the D1-family benchmark reference audited in issue #37. All supplied
lists and three topic pages were screened; eight paper full texts were read in
detail (MoGe-2, MoGe-3, ZoeDepth, DAC, UniK3D, UniDAC, MetricAnything,
AerialMetric), with additional abstract/project/release screens. Search round one
followed MoGe-2 and UniDAC comparison rows; round two followed ZoeDepth, DAC and
MetricAnything originals and their baselines. Later AerialMetric and MoGe-3
checks plus a final 2026 gap pass are logged separately.

Exclusions remain explicit: original MoGe is relative; MASt3R/DUSt3R/MapAnything
are routed to multiview; PatchFusion, HyDen-MoGeV2 and YOLO26 to efficiency/detail;
Marigold/Pixel-Perfect Depth/InfiniDepth to relative/detail. MetricAnything's
teacher requires sparse depth. DMD is an FoV-conditioned metric diffusion lead
whose exact usable release was not identified. SM4Depth's paper-linked fork
combines a release-pending notice with inference instructions; the exact usable
artifact remains unresolved. Older BTS/AdaBins/LocalBins/NeWCRFs/iDisc were
screened through comparison tables and deferred from the immediate shortlist,
not declared unavailable. Wrappers, normal checkpoints and MoGe-derived
adaptations are not counted as new independent families.

Source verification re-read each imported row against its exact version:
ZoeDepth Tables 3/7; MoGe-2 B.4 and A.3; MoGe-3 C.1/C.4 and §4.2; UniDAC Table 7
and §8; MetricAnything Tables 3/4 and §4.2.1; AerialMetric Table 3 and §4.1.
Headers, units, camera conditions and missing settings were checked. Browser
PDF retrieval failed for UniDAC (cache miss) and MoGe-3 (size limit); HTML tables
were readable, with no ambiguous numerical cell used. Exact HF file listings,
card revisions and seven author-code commit records through cutoff were checked;
weight bytes were neither downloaded nor executed. CSV parsing, unique IDs,
model references, numeric values and task-only diff checks passed. No application
tests, installation, inference or experiment-state changes were performed.

Remaining limitations are substantive findings: absent preprocessing details,
uncertain historical checkpoint mapping, conflicting training totals and license
scope, incomplete independent indoor-camera evaluation, and no Basketball or
motion/temporal evidence. They limit recommendations rather than justify filling
in missing facts. Coverage is dated and bounded, not exhaustive.

[M2]: https://arxiv.org/html/2507.02546v1
[M3]: https://arxiv.org/html/2607.17967v2
[MC]: https://github.com/microsoft/MoGe/tree/74fbce054ebed49800de42d0ad0e83495065719a
[Z]: https://arxiv.org/html/2302.12288v1
[ZR]: https://github.com/isl-org/ZoeDepth/releases/tag/v1.0
[D]: https://arxiv.org/html/2501.02464v2
[DH]: https://huggingface.co/yuliangguo/depth-any-camera/blob/06560ec524cfaf867dc097012543dd0e152a36c1/README.md
[U]: https://arxiv.org/html/2603.27105v1
[UC]: https://github.com/girish1511/UniDAC/tree/9ddfc1f4cea68e08273ec9bca037f2ef9e1aa90e
[UH]: https://huggingface.co/girish1511/UniDAC/blob/97339d315fb2eab216586fee9a213de5ed20ba95/README.md
[K]: https://arxiv.org/html/2503.16591v1
[KC]: https://github.com/lpiccinelli-eth/UniK3D/tree/29f7862f3c3ee79c53ef0153dfc901ce511df575
[KL]: https://github.com/lpiccinelli-eth/UniK3D/blob/29f7862f3c3ee79c53ef0153dfc901ce511df575/LICENSE
[MA]: https://arxiv.org/html/2601.22054v1
[MAC]: https://github.com/metric-anything/metric-anything/tree/616a5e6762f5fc40d1a4ef990fee04c800532f59
[MAD]: https://github.com/metric-anything/metric-anything/blob/616a5e6762f5fc40d1a4ef990fee04c800532f59/models/student_depthmap/README.md
[MAI]: https://github.com/metric-anything/metric-anything/blob/616a5e6762f5fc40d1a4ef990fee04c800532f59/models/student_depthmap/depth_model.py
[MAH]: https://huggingface.co/yjh001/metricanything_student_depthmap/blob/cae9b4eb052e827048c9b385366c6d0dce83fb01/README.md
[A]: https://arxiv.org/html/2606.29716v1
[AL]: https://github.com/kuieless/AerialMetric/blob/2ec0e6c6d252796ab3b454ebecf60ab53df87fd3/MoGe2-Aerial%2BBenchmark_LICENSE.md
[V]: https://github.com/TRI-ML/vidar/blob/main/hubconf.py
[VL]: https://github.com/TRI-ML/vidar/blob/main/LICENSE.md
[ML]: https://github.com/microsoft/MoGe/blob/74fbce054ebed49800de42d0ad0e83495065719a/LICENSE
[MH]: https://huggingface.co/Ruicheng/moge-2-vitl/blob/39c4d5e957afe587e04eec59dc2bcc3be5ecd968/README.md
[D3L]: https://github.com/facebookresearch/dinov3/blob/main/LICENSE.md
