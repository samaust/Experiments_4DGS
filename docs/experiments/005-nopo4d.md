# Experiment 005: NoPo4D bundled four-camera reconstruction

Status: **completed, offline repeat verified**. Date: 2026-09-05.

## Purpose and reproduction

Question: can the patched Python 3.14 stack reconstruct and replay the supplied
multi-view example, and does its apparent quality justify testing novel views?
Inputs are `.local/NoPo4D/assets/examples/cam{0..3}_t{0..3}.png`: 16 RGB images,
448×448, four cameras × four frames, in camera-major order. No preprocessing or
training was performed. Physical capture rate/window and dataset split for this
bundled example were not established; normalized input timestamps are
0, 1/3, 2/3, 1. This example visibly differs from the STG/Mango scene window.

Source revisions, submodules, licenses and base environment are in the
[shared record](section6-evidence.md). Setup is `bash scripts/setup-nopo4d.sh`;
it applies `nopo4d-python314.patch` and `da3-python314.patch`, declares the missing
`addict` dependency, permits NumPy 2/Python 3.14, and makes Open3D benchmarks
optional. No inference math was changed. Environment:
`.local/envs/nopo4d/bin/python`, xFormers 0.0.35, gsplat 1.5.3, NumPy 2.5.2;
full inventory in `evidence-inventory-20260905/nopo4d-installed.txt`.

Weights, recorded from the local Hugging Face cache:

| Model | Revision | Weight bytes / SHA-256 |
| --- | --- | --- |
| [bralani01/nopo4d](https://huggingface.co/bralani01/nopo4d) | `21791fbf73c63b5e96f0ae95d21097bd643a8b11` | 2,102,246,744 / `61e1fba95686d3efdf879835a3aca3ecadd853a2a5859140be90c0f935c724bc` |
| [DA3-LARGE-1.1](https://huggingface.co/depth-anything/DA3-LARGE-1.1) | `0e109ae307c5982f319a67cf6f9f99ccdc0ec97c` | 1,643,843,860 / `739905c423cf0d6ccaf9e61a8401d82ba1ac32d7f4d3ee6dca8f92b377633f64` |

Both model configs and safetensor hashes are in `evidence-inventory-20260905/results.json`.
Cache roots are `.local/cache/huggingface/hub/models--bralani01--nopo4d/` and
`models--depth-anything--DA3-LARGE-1.1/`. Keep their recorded snapshots/refs for
the verified offline replay; transferred download bytes were not measured.

From `.local/NoPo4D`, both runs execute:

```bash
"$GS_WORK/envs/nopo4d/bin/python" src/inference.py \
  --image_dir assets/examples --num_cameras 4 \
  --output_dir "$GS_WORK/runs/evidence-nopo4d-20260905/output" --render_timestamps 10
```

The second run substitutes `evidence-nopo4d-offline-20260905` and exports
`HF_HUB_OFFLINE=1`. Both use `TORCH_EXTENSIONS_DIR=$GS_WORK/cache/torch_extensions/
nopo4d-py314-torch213-cu130` (one uninterrupted path), `CUDA_HOME=/usr/local/cuda-13.0`,
`TORCH_CUDA_ARCH_LIST=8.9`, GCC 13.3 and `MAX_JOBS=8`. Exact commands and boundaries
are in the two run directories. The first gsplat build's `build.ninja` records
`-O3`, `-use_fast_math`, `-std=c++20`, and `compute_89/sm_89`. Resolution,
imports, source build, CUDA kernels, checkpoint loading, encoder and renderer
all pass. Open3D benchmark paths and training remain outside this validation.

## Measurements

| Observation | Value | Boundaries |
| --- | --- | --- |
| Setup failures resolved | Python/NumPy metadata, Open3D dependency scope, missing addict | Historical effort not timed |
| Initial command | 106.21 s | Model loading, encoder, first JIT compilation, renderer and file saving |
| gsplat initial compilation | 95.40 s | Time reported by gsplat within initial command |
| Cached offline command | 10.04 s | Fresh process; full model load/reconstruction/render/save, reused compiled extension |
| Initial GPU memory | 16,810 MiB peak / approximately 1,128 MiB baseline | Device-wide, 200 ms samples |
| Offline GPU memory | 16,578 MiB peak / approximately 897 MiB baseline | Same sampling method; different desktop baseline |
| Outputs | 40 RGB + 16 forward-flow + 16 backward-flow PNGs | RGB is 448×448, ten times per camera |
| Initial evidence directory | 11,713,884 bytes | Snapshot including clips/sheets/logs |
| Offline evidence directory | 8,580,309 bytes | Snapshot including output PNGs/logs |
| Repeatability | 40/40 RGB PNGs byte-identical | Initial versus offline rerun |
| Encoder-only / warm render-only throughput | Not measured | Do not label 10.04 s as isolated model inference or kernel time |

Each `camera-{0..3}.mp4` contains ten frames at 10 FPS. Encoding uses
`ffmpeg -framerate 10 -start_number <camera*10> -i output/images/view_%04d.png
-frames:v 10 -c:v libx264 -pix_fmt yuv420p camera-<camera>.mp4`.
This is a one-second playback choice, not source timing. Frame numbering is
camera-major: camera 0 = 0000–0009, camera 1 = 0010–0019, etc.

## Visual inspection

Sheets for [camera 0](../../.local/runs/evidence-nopo4d-20260905/camera0.png),
[camera 1](../../.local/runs/evidence-nopo4d-20260905/camera1.png),
[camera 2](../../.local/runs/evidence-nopo4d-20260905/camera2.png), and
[camera 3](../../.local/runs/evidence-nopo4d-20260905/camera3.png)
show output times 0, 5/9 and 1. The room and figure remain recognizable from all
four replay cameras and the stirring hand changes position. Background blinds,
window and countertop are largely stable in the inspected samples.

The [camera-0 inputs](../../.local/runs/evidence-nopo4d-20260905/input-camera0.png)
show why this is not a clean novel-view quality test: these are the input views.
Its middle input is at 2/3, not output time 5/9. Endpoints are temporally matched;
predicted camera calibration may still differ. No pixel-wise reconstruction
accuracy or held-out score is claimed. Hand/utensil motion and occlusion boundaries
show noticeable translucent smearing/ghosting, especially camera 0 and camera 3.
Fine textures are softened. These defects matter even though the overall scene
is coherent and the offline output repeats exactly.

The CLI reuses one predicted pose per input camera. It provides no interactive
frozen-time orbit, and no unseen-surface viewpoint range was tested. It saves
rendered images and flow, not a portable dynamic-Gaussian viewer asset. No severe
scene-wide collapse is visible in the sampled states; a perceptual flicker score
and seamless looping were not established. Camera boundaries in the combined
40-image sequence must not be counted as temporal flicker; play the four clips
separately. Optical-flow images exist, but their numerical accuracy was not evaluated.

## Decision

**Investigate rendering further.** This is the first-priority next experiment:
test a small novel-view sweep at fixed times on the existing example, concentrating
on moving hands and newly revealed regions. The verified 10.04-second cached
workflow makes iteration practical on this machine, but input-camera replay
does not establish usable free-viewpoint geometry. Training and new input
preparation were not started.
