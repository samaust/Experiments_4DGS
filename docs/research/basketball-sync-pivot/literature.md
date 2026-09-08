# Synchronization pivot: literature and protocol audit

Audit cutoff: 2026-09-08. This report supports Plan 024; it does not establish
Basketball synchronization accuracy or reconstruction benefit. Eleven seed works
were inspected, deduplicating arXiv/conference versions. Additional papers were
screened for citation provenance, without expanding the experiment scope or
exceeding the 20-paper detailed-reading cap. See [citation map](citation-map.md).

## Evidence matrix

“Unresolved” means the inspected sources do not establish the field; it does not
mean the authors failed scientifically. Published aggregate metrics are not raw
per-camera distributions. Unless listed, medians, tails, excluded pairs and
camera-level failure records remain unavailable for independent reanalysis.

| Work and source | Assumptions, method and initialization | Benchmark evidence and limitations |
| --- | --- | --- |
| [VisualSync](https://arxiv.org/html/2512.02017v1), NeurIPS 2025 | Estimated poses, dynamic masks, CoTracker/MASt3R correspondences; pairwise Sampson search then robust global alignment. Moving cameras supported through time-varying geometry. | Per-video mean/median ms: EgoHumans 122.1/46.6, CMU 112.6/41.5, 3D-POP 114.7/77.8, UDBD 20.2/5.9. No views excluded; difficult tails matter. GT-pose EgoHumans ablation 72.4/28.6 ms still leaves correspondence error. |
| [Sync-NeRF](https://arxiv.org/html/2310.13356v2), AAAI 2024 | Known calibration; additive continuous camera offset jointly learned with photometric field; small random offset initialization. K-Planes time range scaled to ±0.8. | UDBD synthetic timing MAE: hybrid 0.0156 s, explicit 0.0229 s, MixVoxels 0.0154 s. Random video translations, first 270 overlapping frames; longer perturbation experiments use 255/240. Test-view offset optimization is separate from training. |
| [SyncTrack4D](https://arxiv.org/html/2512.04315v1), CVPR Findings 2026 | Dense 4D motion tracks, fused Gromov–Wasserstein matching, coarse DTW and motion-spline Gaussian refinement; requires initial geometry. | Panoptic: six scenes, 150 frames, 31 cameras, 30 train/one test. Basketball timing error 13.355 initial, 13.416 Sync-NeRF, 9.689 DTW, 0.260 refined frames. Exact basketball release/start/split unresolved; see audit checkpoint. |
| [Humans as a Calibration Pattern](https://arxiv.org/html/2412.19089v2), ICCV 2025 | Independently recovered human motion initializes global alignment and camera poses; progressive K-Planes refinement. Depends on successful SLAHMR motion recovery. | Panoptic mean timing 1.343 initial/0.028 refined frames; 29–30 training views and one test. Mobile-Stage and EgoBody extend person/camera diversity; EgoBody only initialization evaluated. Rendering evaluation also fits test camera pose/time. Full moving-camera refinement remains future work. |
| [Freely Moving People calibration](https://arxiv.org/html/2502.12546v1), RA-L 2025 | Known intrinsics; monocular 3D poses, directional registration and soft person association; rotation/time/association followed by translation and global refinement. Near-simultaneous start assumption bounds search. | Four cameras per scene, 300–1000-frame clips; Panoptic, ZJU-MoCap and MMPTRACK. Table II final timing errors 0–1 frames across nine scenes; initialization failures in comparison methods explicitly marked. Pose similarity and occlusion can cause association errors. |
| [MultiViewUnsynch trajectory paper](https://arxiv.org/pdf/2003.04784), IROS 2020 | Single detected moving target; known intrinsics and approximate corresponding frames; joint pose/time/spline trajectory, optional rolling shutter and motion priors. | Mixed cameras about 25–59.94 fps; RTK trajectory truth approximately ±1 cm, independent radio LED timing truth for dataset 3. Trajectory centimeters are not timing milliseconds. Single-target assumptions require a defensible ball/player track before Basketball use. |
| [Dynamic Gaussian Scene Reconstruction from Unsynchronized Videos](https://arxiv.org/html/2511.11175v1), AAAI 2026 | Foreground geometric matches choose coarse integer shifts; residual continuous shifts learned photometrically. Direct 4D representations may require finite-difference time gradients. | DyNeRF perturbation experiments with 3/5/10-frame maxima; compares SC-GS/4DGaussians and Sync-NeRF. Improved rendering does not independently certify physical fractional timing. Exact released code/benchmark manifest not established. |
| [Sync-4DRF](https://openreview.net/pdf/2adf84139e687f06c457b0f1817efab3f4159c0e.pdf), ECCV workshop 2024 | Extends additive time offsets to Gaussian deformation; discrete temporal embeddings replaced by continuous functions or grid interpolation. | Synthetic 14-camera, 30-fps, 10-second assets; rounded normal perturbations (SD five frames). Table 3 MAE: MixVoxels 15.4, K-Planes 15.6, 4DGaussians 6.8 ms. Test offset fitting: 200/1000 iterations. User-supplied PDF hash retained in source provenance. |
| [FreeTimeGS](https://arxiv.org/html/2506.05348v1), CVPR 2025 | Local space-time Gaussian primitives and motion; representation with supplied camera/time coordinates, not a clock estimator. | SelfCap Table 8 full/dynamic PSNR 27.41/29.38, LPIPS 0.204/0.080; 467 fps on 4090. Dynamic metric uses a mask bounding-box crop with black exterior. These are author results; this repository uses the separately identified FreeTimeGsVanilla reproduction. |
| [MoRel](https://arxiv.org/html/2512.09270v1), CVPR 2026 | Anchor relay, bidirectional deformation/opacity blending, hierarchical densification and loading temporal chunks on demand. Anchor temporal parameters are not camera clock estimates. | SelfCap long-range reconstruction and temporal consistency motivate checking chunk transitions. Longer-range representation comparisons do not establish a synchronization advantage on the two-second Basketball controls. Official implementation exists; outside this campaign's training allocations. |
| [IFID / InSynFormer](https://ojs.aaai.org/index.php/AAAI/article/download/28174/28346), AAAI 2024 | Five-frame pose features and inter/intra-frame classification. Ten physical 10-fps cameras; timer precision 10 ms, exposure 1 ms. | Mean error 0.83 frame; fractional labels do not imply 10-ms mean accuracy. Dataset group-count discrepancy and split arithmetic retained in audit checkpoint. Current data/code accessibility unresolved; do not call inaccessible data a failed algorithm. |

## Reconciliation and practical implications

VisualSync's Table 1 reports Sync-NeRF UDBD mean/median 0.4/0.2 ms, whereas the
original Sync-NeRF hybrid table gives 15.6 ms mean error. These are different
evaluation campaigns: offset sampling, selected intervals, reference alignment,
training schedules and potentially rendered source phases must match before a
numerical comparison is valid. Available released metadata does not fully
reconcile them. Retain both with their provenance; neither silently replaces the
other. The discrepancy remains unresolved, rather than evidence that one result
is erroneous. [VisualSync](https://arxiv.org/html/2512.02017v1),
[Sync-NeRF](https://arxiv.org/html/2310.13356v2).

Sync-NeRF, Sync-4DRF and HCP permit test-view timing fitting in their rendering
evaluation. Plan 024 prohibits that optimization and instead estimates held-out
camera timing on separate windows. Our rendering numbers therefore require that
protocol label. Short bounded pilots also cannot reproduce the authors' long
training schedules. [Sync-NeRF appendix B](https://arxiv.org/html/2310.13356v2),
[HCP evaluation](https://arxiv.org/html/2412.19089v2).

The calibrated learned approach remains a conditional candidate. Good static
calibration cannot make weak dynamic correspondences observable. Graph
connectivity cannot certify physical timing, and clock-rate mismatch is a
hypothesis requiring measured cadence/window disagreement. Neither an incomplete
implementation nor an inaccessible benchmark is a negative scientific result.
Zero offsets remain an operational control until paired held-out reconstruction
provides repeatable evidence for a correction.

## Implementation availability

Pinned revisions/hashes are in [source pins](source-pins.json), with exact
installed packages in the runtime and Sync-NeRF locks.

| Baseline | Audited entrypoint and current status | Missing requirements / scope |
| --- | --- | --- |
| VisualSync | GitHub preprocessing plus original archive pair/global scripts; original global estimator CPU control passed. | Pair script has unfinished assignments; matching imports absent `match_utils.process_image`, including essential crop-coordinate mapping. Full released pipeline is not currently runnable. Do not rebuild missing unpublished components or relabel the custom fixture as VisualSync. |
| Sync-NeRF K-Planes | `plenoxels/main.py --help` passes in the isolated image after two compatibility attempts. | Scientific training, data adapter, timing export and numerical CUDA execution remain to validate. `--test-optim` must stay disabled. |
| MultiViewUnsynch | `multiviewunsynch/main.py`; core import passed. MPL-2.0 checkout. | Requires supplied single-target tracks, intrinsics and initial frame correspondence. No full trajectory run yet. |
| HCP | Official repository promises code release. | No released full implementation established. |
| SyncTrack4D / Dynamic Gaussian Unsynchronized | Paper inspected; no official executable release established in bounded discovery. | Do not reconstruct these unpublished pipelines. |
| Sync-4DRF | Official repository redirects NeRF to Sync-NeRF and promises Gaussian code. | Not an independently runnable Gaussian baseline. |

For unaudited licenses/weights, record “unresolved,” not permission implied by a
paper or a download. No new model weights have been used in a scientific run.
