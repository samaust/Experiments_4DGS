# Citation and discovery audit

Cutoff 2026-09-08. One backward-reference and forward-discovery pass per seed.
Forward discovery used exact titles, method names with `references`/`citations`,
and direct-comparison candidates; results are search-limited, not a complete
bibliometric census. Publication versions are one work, not independent support.
Eleven seed papers were read; additional items below were screened for citations
or release provenance, not added to scientific execution. The 20-paper ceiling
remains binding.

| Seed | Backward pass: verified in seed paper | Forward pass: verified citing source or search limitation |
| --- | --- | --- |
| VisualSync | [References 26, 31, 33](https://arxiv.org/html/2512.02017v1): Sync-NeRF, flight trajectories, IFID; dependencies include MASt3R/CoTracker3. | Exact-title/method searches found versions and summaries; no newer citing paper verified. |
| Sync-NeRF | [Paper references](https://arxiv.org/html/2310.13356v2): K-Planes, MixVoxels, Neural 3D Video. | VisualSync ref 26; [HCP ref 16](https://arxiv.org/html/2412.19089v2); [SyncTrack4D ref 16](https://arxiv.org/html/2512.04315v1); supplied Sync-4DRF PDF ref 15. |
| SyncTrack4D | [References](https://arxiv.org/html/2512.04315v1): HCP ref 4, Sync-NeRF ref 16, Dynamic Gaussian Marbles ref 36. | Exact-name searches found the paper/conference landing page, no verified newer citation. |
| HCP | [Ref 16 and limitations](https://arxiv.org/html/2412.19089v2): Sync-NeRF; SLAHMR motion prerequisite. | SyncTrack4D ref 4 verified. Other ICLR manuscript candidates remain unscreened. |
| Freely Moving People | [Refs 4, 11](https://arxiv.org/html/2502.12546v1): Extrinsic Calibration from a Moving Person; Spatiotemporal Bundle Adjustment. | [Multi-Camera Pairwise Calibration, related work](https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/ipr2.70404) explicitly describes Lee et al.'s joint extrinsics/time/person association and cites it as 34. |
| MultiViewUnsynch / flight trajectories | [PDF refs 19–20](https://arxiv.org/pdf/2003.04784): unsynchronized two-view geometry and spatiotemporal bundle adjustment. | VisualSync ref 31 verified. MAVREC and outdoor tracking candidates found, not read in detail. |
| Dynamic Gaussian Unsynchronized | [References and integration](https://arxiv.org/html/2511.11175v1): 4DGaussians, SC-GS, Neural 3D Video. | Exact-title search found publication versions; no newer citing work verified. A numerical Sync-NeRF comparison is not automatically a verified bibliography entry. |
| Sync-4DRF | Supplied PDF refs 15, 20: Sync-NeRF and Spacetime Gaussian Feature Splatting. | Thermal4D found as a candidate; publisher retrieval did not establish the edge. Do not include it as verified. |
| FreeTimeGS | [Refs 10, 21](https://arxiv.org/html/2506.05348v1): K-Planes and Spacetime Gaussian Feature Splatting. | [MoRel ref 30](https://arxiv.org/html/2512.09270v1) verified. |
| MoRel | [Refs 14/15, 17, 30](https://arxiv.org/html/2512.09270v1): STG, Scaffold-GS, FreeTimeGS. | Exact full-title and method/long-range searches found versions and unrelated name matches, no verified newer citation. |
| IFID / InSynFormer | [Paper related work/references](https://ojs.aaai.org/index.php/AAAI/article/download/28174/28346): SeSyn-Net, NTU RGB+D, Panoptic. | VisualSync ref 33 verified. Track-UGV-SYNC sports candidate found, not read in detail. |

VisualSync's flight-trajectory bibliography contains a 2003 year inconsistent
with its arXiv identifier 2003.04784 and the 2020 source. It is deduplicated by
title/authors/identifier. HCP title variations (“Humans as a Calibration” versus
“Humans as a Calibration Pattern”) likewise identify one work. MoRel duplicates
the STG citation as 14/15; count one edge.

Unscreened candidates are retained rather than silently discarded: SteerPose
(BMVC 2025), Track-UGV-SYNC (sports 2026), MAVREC (CVPR 2024), Thermal4D,
Large-scale Outdoor 3D Trajectory Measurements, and ICLR 2026 manuscripts returned
for HCP. None is used to claim a verified scientific comparison here.
