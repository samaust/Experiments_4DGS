# Benchmark and executable-code status

This matrix separates an unavailable release from a scientific failure. Code
identities are pinned in [source pins](source-pins.json); license-file identities
are in the [license inventory](source-license-inventory.json). Native environment
inventories and the isolated container dependency locks are retained alongside
the [training protocol](training-protocol.json).

| Item | Established evidence | Remaining limitation |
| --- | --- | --- |
| VisualSync | Official checkout and original archive inspected; original global-estimator CPU control executes. | Original pair script contains unfinished assignments. Matching imports absent `process_image` with essential crop-to-original mapping. Full preprocessing/pair pipeline is unavailable under the no-missing-core-reconstruction rule. No learned pair pass was run. |
| Sync-NeRF K-Planes | Released training implementation executes numerically on the RTX 4090 through the calibrated eight-camera adapter. Three seeds reached 43,049 / 42,944 / 42,999 steps; update 42,000 is compared across seeds. Seed 0 fresh CPU reload matches its timing export. | Three-seed results are in the separately updated result artifact. Every pilot is capped below the 90,001-step author schedule. The native checkpoint lacks RNG/AMP-scaler state, so exact training continuation is not established. |
| MultiViewUnsynch | Official core imports in the isolated runtime. | Single-target trajectory inputs and initial correspondence are required. An import is not a successful end-to-end trajectory reconstruction. No fabricated multi-player correspondence is supplied. |
| UDBD Box | Original README download link returns 404; separately linked official project folders resolve. Transforms describe 14 cameras at 512×512. The first visible cam00 listing contains 50 PNGs, which is a pagination result, not the sequence length. | Exact supplied offset labels and source phase are unresolved. Filenames alone do not establish synchronization truth. No accuracy run or truth/zero error comparison was manufactured. The 1800-second benchmark slot remains unused. |
| SyncTrack4D Panoptic basketball | Paper identifies 150 frames, 31 cameras and a 30/1 train/test split; its dataset citation points to Dynamic Gaussian Marbles. | Exact release, starting frame, camera IDs and offset labels remain unresolved. No similarly named basketball recording is substituted. The 1800-second benchmark slot remains unused. |
| Independent analytic controls | Known fractional motion, stationary/epipolar ambiguity, outliers, occlusion, disconnected graphs, dropped frames and clock-rate mismatch tested on CPU. | These validate our timing/observability contracts. They are not VisualSync/Sync-NeRF benchmark scores, and interpolated video is not presented as physical fractional truth. |
| Basketball reconstruction | Frozen 34-camera calibration, original IDs, accepted scale, 25-fps PTS audit, 1,350 training keys and 350 held-out evaluation keys are prepared. Existing STG Full and FreeTimeGsVanilla code is adapted. | No full-rig correction is available; only the three zero controls per method are authorized by the fallback branch. Runtime/result status is recorded separately. |

The additional loader audit reads the pinned
`Sync-K-Planes/plenoxels/datasets/video_datasets.py`: its Blender path opens
`transforms.json`, sorts per-camera MP4s, reserves the first camera for testing,
and normalizes frame-index timestamps by `num_frames-1`. The retrieved transforms
contain camera angle, image dimensions and pose records; they do not contain
offset labels. Neither the loader nor the inspected calibration JSON establishes
the source clips' synchronization phase. Basketball deliberately supplies its
own calibrated rays and original camera-ID mapping for eight **training** cameras,
with test-image optimization disabled; it is not a reproduction of the Box split.

HCP, SyncTrack4D, Dynamic Gaussian Unsynchronized and Sync-4DRF's Gaussian extension
remain literature comparisons without established executable releases in this
bounded audit. FreeTimeGsVanilla is explicitly a separate reproduction; it is not
relabeled as the FreeTimeGS authors' implementation. MoRel is a representation
candidate outside the allocated training methods. IFID's accessibility and label
interpretation remain unresolved as recorded in [the literature matrix](literature.md).

Read [the retained results](syncnerf-results.json), [GPU ledger](gpu-budget.json)
and [status](status.md) for current execution status. This source/benchmark matrix
alone does not assert completion of Plan 024 or a successful reconstruction.
