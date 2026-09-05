# Native STG: published quality comparisons

[Research guide](research.md) · [Native STG experiment](experiments/003-stg-native.md) · [Five-experiment evidence](experiments/section6-evidence.md)

Research date: **2026-09-05**. This report records a bounded literature search of
arXiv papers, conference publications, and author project pages. Numbers below
are paper-reported results; the repository has not reproduced these benchmarks.

STG remains a strong baseline, but newer methods report better quality on several
benchmarks. FreeTimeGS and MoE-GS are promising candidates when perceptual quality
matters more than rendering speed. There is no defensible single global STG rank:
the ordering changes with dataset, training protocol, model variant, and metric.

## What “Native STG” means here

The repository uses “native STG” for the original renderer of **Spacetime Gaussian
Feature Splatting for Real-Time Dynamic View Synthesis** (Li et al., CVPR 2024).
Papers also call the method STG, STGS, or SpaceTimeGS. “Native” distinguishes this
rendering path from the splaTV conversion; it is not a separate published method.

Experiment 003 used `n3d_sear_steak_lite_allcam.zip`, a lite checkpoint trained
with all cameras. Its fixed-camera preview does not measure held-out view quality.
Most literature comparisons below concern the full model.

| Variant | PSNR ↑ | LPIPS-Alex ↓ | Reported FPS ↑ |
| --- | ---: | ---: | ---: |
| STG Lite | 31.59 | 0.047 | 310 |
| STG Full | 32.05 | 0.044 | 140 |

These are Neural 3D Video averages at 1352×1014. The authors describe lite output
as slightly blurrier. Source: [STG paper, Table 6 and qualitative comparisons](https://arxiv.org/html/2312.16812v2).
They are not scores for our downloaded checkpoint or measured workstation FPS.

## Better and worse results on Neural 3D Video

PSNR measures pixel reconstruction accuracy; higher is better. LPIPS measures
perceptual difference; lower is better. Neither counts ghosting, floaters, or
temporal flicker directly.

The following selected rows come from **FreeTimeGS: Free Gaussian Primitives at
Anytime and Anywhere for Dynamic Scene Reconstruction**, CVPR 2025. The benchmark
includes `sear_steak` and uses the first 300 frames at half resolution.

| Method | PSNR ↑ | LPIPS ↓ | Relative to full STG |
| --- | ---: | ---: | --- |
| FreeTimeGS | 33.19 | 0.036 | Better on both measures |
| STG Full | 32.05 | 0.044 | Reference |
| Ex4DGS | 32.11 | 0.048 | Higher PSNR, worse perceptual similarity |
| 4DGS — Yang et al. | 32.01 | 0.055 | Worse on both |
| MixVoxels-X | 31.73 | 0.064 | Worse on both |
| HyperReel | 31.10 | 0.096 | Worse on both |

Source: [FreeTimeGS, Table 1](https://arxiv.org/html/2506.05348v2#S4.T1).
This table includes published baselines, not a controlled rerun of every method.
FreeTimeGS improves by 1.14 dB and approximately 18% lower LPIPS; that percentage
does not mean 18% fewer artifacts. Its qualitative comparisons cover moving hands,
clothing, and bicycle pedals. See the [authors' comparison videos](https://zju3dv.github.io/freetimegs/).

## Newer comparisons available in 2026

Keep these comparisons within their respective papers rather than merging them
into one leaderboard.

### MoE-GS and its July 2026 follow-up

[MoE-GS: Mixture of Experts for Dynamic Gaussian Splatting](https://arxiv.org/html/2510.19210v2)
and [On the Design of Mixture-of-Experts for Dynamic Gaussian Splatting](https://arxiv.org/html/2607.08250v1)
combine independently trained models through a learned router. STG is itself one
of the experts; this is a larger combined system rather than a replacement kernel.

| N3V result in the follow-up, Table III | PSNR ↑ |
| --- | ---: |
| STG, trained in 150-frame segments | 31.92 |
| MoE-GS, three experts | 33.23 |
| MoE-GS, four experts | 33.27 |

The altered STG training window prevents treating this as the original STG
benchmark protocol. The follow-up's Technicolor appendix comparison reports
LPIPS of 0.087 for STG and 0.083 for three-expert MoE-GS. Its separate two-expert
efficiency study reports 44 FPS versus STG's 88.5 FPS; these rates do not describe
the four-expert model. Quality gains come with extra inference and memory cost.

### ATGS, August 2026

[ATGS: Anchored Temporal Gaussian Splatting for Long Volumetric Video Representation](https://arxiv.org/abs/2608.30184)
was submitted to arXiv on August 31, 2026; its record identifies ACM ToG/SIGGRAPH
2026. It addresses long sequences and complex motion.

| N3DV result, Table 2 | PSNR ↑ | LPIPS ↓ | Reported FPS ↑ |
| --- | ---: | ---: | ---: |
| STG | 32.05 | 0.044 | 140 |
| LocalDyGS | 32.28 | 0.044 | 105 |
| ATGS | 32.56 | 0.043 | 70 |

Source: [ATGS, Table 2](https://arxiv.org/html/2608.30184v1).
STG ranks third of twelve rows by PSNR and joint second by LPIPS among reporting
methods in this table. This is a table-specific rank, not its position across
the literature. ATGS's LPIPS improvement is only 0.001; it does not establish a
large visible artifact reduction. Reported FPS should not be assumed to use
identical hardware or timing boundaries.

### FreeTimeGS++, May 2026 preprint

[FreeTimeGS++: Secrets of Dynamic Gaussian Splatting and Their Principles](https://arxiv.org/html/2605.03337v1)
illustrates why PSNR alone is insufficient. Its fixed B variant reports
33.45 dB and LPIPS-Alex 0.062 on DyNeRF/Neural 3D Video (Table S4), while its STG
reference is 32.05 dB and 0.044 (Table S2). Higher PSNR accompanies worse LPIPS.
The headline 33.51 dB uses scene-wise configuration selection. The paper's
reproduced FreeTimeGS baseline and its proposed ++ variants are distinct results;
their scores must not be interchanged.

## Where STG still leads perceptually

**7DGS: Unified Spatial-Temporal-Angular Gaussian Splatting**, ICCV 2025, reports
the following Technicolor comparison:

| Method | PSNR ↑ | LPIPS-Alex ↓ |
| --- | ---: | ---: |
| STG | 33.23 | 0.085 |
| Ex4DGS | 33.49 | 0.094 |
| 7DGS | 33.58 | 0.101 |
| 4DGS — Yang et al. | 33.25 | 0.110 |

Source: [7DGS, Table 2](https://arxiv.org/html/2503.07946v1#S5.T2).
STG has the lowest LPIPS among all seven methods in the source table, despite
ranking fourth by PSNR. The table identifies Ex4DGS and Yang et al.'s 4DGS as
reproductions using official code. A newer method or higher PSNR does not
necessarily imply fewer perceptual defects.

## Implications for this repository

The following is an investigation order based on the evidence, not a measured
ranking of our local outputs:

1. **STG Full:** investigate the closest quality upgrade from the lite experiment.
2. **FreeTimeGS:** investigate its improvements on both PSNR and LPIPS, especially
   for moving details.
3. **MoE-GS:** investigate when additional model and rendering cost is acceptable.
4. **ATGS:** investigate for long sequences and complex motion.

Implementation availability, checkpoint availability, and compatibility with our
environment still need checking before scheduling these runs. This literature
report does not execute or authorize new training, and does not replace the
existing [next experiment decision](experiments/section6-evidence.md#results-and-next-experiment).

For a local quality comparison, use identical held-out cameras, frame windows,
resolution, and metric implementations. Keep LPIPS-Alex and LPIPS-VGG separate.
Inspect matched moving-region crops and continuous videos for ghosting, floaters,
blur, and flicker; include novel camera positions to expose geometry failures.
Measure rendering throughput separately from model loading and image saving.

The earlier conversational 0–10 artifact scores were informal visual judgments,
not standardized measurements, and should not be used as research rankings.
Our five existing experiments differ in checkpoint provenance, camera coverage,
and source imagery. This search establishes neither a Mango-GS nor a NoPo4D
ranking relative to STG for those local runs.
