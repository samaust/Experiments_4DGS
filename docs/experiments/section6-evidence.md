# Pretrained experiment evidence — 2026-09-05

All five requested experiments ran successfully. No input preparation or training
was started. Existing datasets, environments and released checkpoints were reused;
new render outputs and measurements were written into separate directories.

## Results and next experiment

| Experiment | Observed result | Decision |
| --- | --- | --- |
| [001 — splaTV bundled scene](001-splatv.md) | Hardware WebGL2, animation and offline reload work; orbit reveals severe stretching/floaters | Investigate rendering further |
| [002 — STG in splaTV](002-stg-splatv.md) | Animated conversion works; matching native intrinsics exposes extra ghosting | Investigate rendering further |
| [003 — native STG](003-stg-native.md) | 50 frames reload exactly; coherent, stable inspected camera view | Investigate rendering further |
| [004 — Mango-GS](004-mango.md) | 300 frames reload exactly; soft silhouettes and background edges versus its reference | Defer |
| [005 — NoPo4D](005-nopo4d.md) | Full 16-input reconstruction succeeds; 40 output frames repeat exactly offline | Investigate rendering further |

The next experiment should be a **small novel-view camera sweep of the existing
NoPo4D reconstruction**, with fixed-time views and particular attention to the
hand, utensils, and newly exposed surfaces. Its stock CLI only replays predicted
input cameras, so the successful reconstruction has not yet answered whether its
geometry supports useful camera movement. Native STG remains the reference for
investigating splaTV conversion differences. These are next-step recommendations;
neither the sweep nor training was started.

This is not a quality ranking: STG and Mango have different time coverage and
checkpoint provenance. NoPo4D's example has a different cooking state and open
lower window blinds; it must not be treated as the same source window merely
because the room looks familiar.

## Shared environment and provenance

Host: Ubuntu 24.04, RTX 4090, 24,564 MiB, driver 595.84. Native environments use
standard-GIL CPython 3.14.6, Torch 2.13.0+cu130, torchvision 0.28.0+cu130,
CUDA toolkit `/usr/local/cuda-13.0`, GCC/G++ 13.3 at `/usr/bin/gcc` and
`/usr/bin/g++`, `TORCH_CUDA_ARCH_LIST=8.9`, `MAX_JOBS=8`. uv is 0.11.32;
Node is 24.16.0. Torch/torchvision assertions and `uv pip check` pass in all
three native environments after installation. See
[inventory.json](../../.local/runs/evidence-inventory-20260905/inventory.json).

| Source | Full checked-out commit | Local patch |
| --- | --- | --- |
| [splaTV](https://github.com/antimatter15/splaTV) | `8b313fea028d32f3c978f06b0a8bd2050b03ff28` | `splatv-time-controls.patch` and `time-controls.js` |
| [SpacetimeGaussians](https://github.com/oppo-us-research/SpacetimeGaussians) | `427abfc58309a4a5213843dd673fb22c4529306c` | `stg-python314-cu130.patch` |
| [Mango-GS](https://github.com/htx0601/Mango-GS) | `2a7a9238c1518c5770dc2952464bc71a4d3dba75` | `mango-cu130.patch` |
| [NoPo4D](https://github.com/bralani/NoPo4D) | `cb54c9349792d474aa541274842e0fadf1d807c7` | `nopo4d-python314.patch` |
| [Depth Anything 3](https://github.com/ByteDance-Seed/Depth-Anything-3) | `41736238f5bced4debf3f2a12375d2466874866d` | `da3-python314.patch` |
| [PyTorch3D](https://github.com/facebookresearch/pytorch3d) | `0a7d4c1a171e8b768c63f15b17564f9ad495f49b` | Source build |

Recursive submodules: STG MMCV `3ba02dfd35c326306346bd9d35a887efc2b30fb0`
(not needed for this rendering path); DA3 as above and nested salad
`6aede13a3f6c25750bf7fde10209c06cb73060bb`. splaTV and Mango return no Git
submodule entries in these checkouts. Native extension sources are still present.

The four top-level source LICENSE files say MIT; DA3's source metadata says
Apache-2.0. This is source-license provenance, not a separate audit of the release
weights, example imagery, dataset, or every native dependency. Asset-specific
licensing remains unverified where a report does not identify it separately.

Environment prefixes are `.local/envs/{stg-render,mango-render,nopo4d,downloads}`.
Exact installed versions are in `evidence-inventory-20260905/*-installed.txt`.
The candidate inputs are `environments/{stg-render,mango-render,nopo4d}.in`;
`environments/constraints-cu130.txt` has SHA-256
`a5b92b102db6c14d56a309f9882497eaa0693c6d9c6abdff6d8aec3884f1c74d`.
These inventories are resolved snapshots, not a complete hash-locked installer.
Patch and artifact SHA-256 values are in the inventory. Historical installation
and compiler logs remain in `.local/runs/pretrained-validation/` and
`.local/runs/nopo4d-install-pPSccZ92/`; setup effort in person-hours was not measured.

Browser checks used isolated headless Chromium 151.0.7922.34, Playwright 1.62.0,
1352×1014 viewport, device pixel ratio 1. The queried WebGL renderer was
`ANGLE (NVIDIA Corporation, NVIDIA GeForce RTX 4090/PCIe/SSE2, OpenGL 4.5.0)`.
Both scenes sampled 60 FPS ten times over approximately 2.5 seconds of playback.
That is a displayed, likely refresh-limited rate, not maximum rendering throughput.
Headless tab-switch behavior and a separate human desktop-browser session were
not evaluated. The automation did exercise actual controls and screenshots.
Both middle images reproduce pixel-for-pixel after cache-disabled local-only
reload, excluding the bottom control strip (RGB rows 0:950). The comparison is
saved in `evidence-inventory-20260905/browser-reload.json`.

## Measurement boundaries

| Run | Command wall time | Sampled device-wide peak / baseline MiB |
| --- | --- | --- |
| splaTV bundled automated inspection | 34.75 s | 1,198 / 1,116 |
| splaTV STG automated inspection | 41.12 s | 865 / 716 |
| Native STG, 50 PNGs | 12.27 s | 1,835 / 1,081 |
| Mango, 300 frames plus metrics and encoding | 228.61 s | 10,170 / approximately 1,148 |
| NoPo4D initial run, including first JIT build | 106.21 s | 16,810 / approximately 1,128 |
| NoPo4D cached offline rerun | 10.04 s | 16,578 / approximately 897 |

Each primary GPU experiment ran separately. The desktop and other host activity
were not disabled; varying baselines demonstrate why these totals are not
per-process allocations. `scripts/measure-experiment.py` sampled every 200 ms,
beginning two seconds before the command and stopping at command exit. Brief
peaks may be missed. No framework peak allocation or isolated warm kernel
benchmark was measured. The STG run's original measurement JSON reports a CSV
header parsing error; its complete CSV was reprocessed successfully in
[results.json](../../.local/runs/evidence-inventory-20260905/results.json).

Each run directory has `command.json`, `run.log`, `gpu.csv` and
`measurement.json`. They contain exact executed argv, working directory, UTC
boundaries, exit status and environment. `TORCH_EXTENSIONS_DIR` for both NoPo4D
runs was `.local/cache/torch_extensions/nopo4d-py314-torch213-cu130`; the initial
wrapper omitted this override from its JSON, corrected for the offline run.
The native STG and Mango runs used their already-installed extension binaries.
Command boundaries use UTC; NVIDIA CSV timestamps use the host's Toronto time.

Storage snapshot in `results.json` uses apparent bytes (`du -sb`): data
28,988,413,748; weights 163,143,753; environments 6,725,379,703; cache
4,780,761,231; runs 2,054,697,678; tools 685,353,578. These are shared workspace
totals, not per-method download costs. Cache hardlinks/reflinks and shared
dependencies prevent interpreting them as incremental physical disk consumption.
Transferred network bytes and cold installation time were not measured.

## Reproduction and inspection tools

Use the existing [setup guide](../pretrained-experiments.md) and its workspace
exports. The exact executed model commands are in each run's `command.json`;
choose new output paths before replaying them. To retain fresh measurements:

```bash
"$GS_WORK/envs/nopo4d/bin/python" scripts/measure-experiment.py \
  --output "$GS_WORK/runs/NEW-RUN" --cwd /absolute/upstream/checkout \
  -- /absolute/environment/bin/python script.py arguments
```

`inspect-splatv.py` starts and stops its own loopback server and browser.
`contact-sheet.py` produces labeled overview/crop sheets;
`analyze-sequence.py` records image hashes and descriptive pixel changes.
Visual observations below come from the captured start/middle/end, orbit, and
detail images, supported by full-sequence pixel checks. Still-frame inspection
does not establish a perceptual temporal-flicker score. MP4 files are provided
for continuous playback, and original PNGs remain the detail reference.
