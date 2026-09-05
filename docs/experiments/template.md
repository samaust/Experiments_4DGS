# Experiment: replace with ID and scene

Status: **not run**. Date:

## Purpose and reproduction

- Question and method:
- Scene, source URL, asset license, model revision, archive SHA-256:
- Upstream URL, full commit, submodule commits, tracked patches:
- Input source/version, preparation commands, camera IDs and coordinate convention:
- Source frame rate/window, normalized-time mapping, image dimensions:
- Local checkpoint, input, output, and raw-log paths under `.local/`:
- Exact setup, rendering/inference, and video encoding commands:
- Environment prefix, uv version, Python executable/version and standard GIL build:
- Candidate specification, base constraints, resolved lock path/hash and package inventory:
- Source-built dependencies: full revisions, compiler flags, build logs and patches:
- CUDA_HOME, nvcc/host compiler, TORCH_CUDA_ARCH_LIST and per-method extension cache:
- Validation stages (separate evidence): resolution / imports / build / kernel / checkpoint render:
- Base Torch/torchvision cu130 assertions repeated after final dependency installation:
- OS, GPU, driver, compiler path/version, Python, PyTorch/CUDA runtime:

## Measurements

| Observation | Value | Measurement boundaries |
| --- | --- | --- |
| Setup effort and failures | not measured | Include dependency/build fixes |
| Download / installed / output bytes | not measured | Include supporting networks and caches |
| First-load wall time | not measured | Include model load and compilation where applicable |
| Warm rendering throughput | not measured | Resolution, frame count, warmup, synchronization; exclude encoding |
| Reconstruction wall time | not measured | Separate encoder, renderer, saving, and downloads |
| Peak GPU memory | not measured | Sampling interval; device-wide versus process/framework allocation |
| Browser frame rate | not measured | Browser, GPU backend, viewport, device pixel ratio, scene |
| Video playback rate | not measured | Encoding choice, not rendering throughput |

## Visual inspection

- Fixed-camera motion at start/middle/end:
- Frozen-time camera movement and useful viewpoint range:
- Edges, fine texture, fast motion, transparency, floaters, newly exposed surfaces:
- Temporal flicker, background stability, loop discontinuity:
- Original/browser comparison: matched camera matrices, intrinsics, resolution, background, time:
- Export/color/opacity/sorting differences:
- Ground truth and split provenance (all-camera checkpoints are not held-out tests):
- Representative local PNG/video paths and camera/time for each:
- Checkpoint reload and local/offline playback:
- Unsupported controls or missing outputs:

## Decision

Choose **investigate training**, **investigate rendering further**, or **defer**.
Explain the observed reason, remaining uncertainty, and next experiment.
Do not rank methods by unmatched scenes, time windows, or resolutions.
