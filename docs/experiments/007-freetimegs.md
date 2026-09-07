# Experiment 007: FreeTimeGS

Status: **SelfCap dense-initialized training stopped cleanly at the budget reserve
at 42,061 steps; native 70,000-step schedule unfinished. Final evaluation complete.
Basketball synchronization remains blocked.**

## Current Basketball continuation — 2026-09-07

[Plan 006](basketball-calibration-alternatives.md) accepted all 34 static cameras;
[revision 2](basketball-rev2.md) verified provenance/conventions and passed the
training-view estimated scale check (1.31506947 estimated metres per calibration
unit, 3.13% reserved disagreement).
Synchronization is now the shared blocker: only 24/71 dynamic timing edges pass,
leaving 19 cameras disconnected from camera 1. No timing selection/final validation,
1,700-image preparation, Gaussian initialization or Basketball training/evaluation
was launched. Held-outs remain 0, 10, 20, 30, with 30 training cameras. The
original per-method two-hour Basketball allocation is unchanged and uncharged.

## Prior implementation and experiment evidence


The author-linked EasyVolcap framework was inspected at
`4cb3c000a31b8764834c79792b355f110d947e75` in `.local/EasyVolcap` on
2026-09-06. No FreeTimeGS-named model/configuration was found in its `main`
checkout. The linked fast Gaussian rasterizer alone is not a complete dynamic
training implementation. The explicitly identified reproduction below has since
been integrated and measured on SelfCap.

Identify the author implementation and any vanilla reproduction separately.
Record commit, license, checkpoint format, rasterizer, and adaptations to the
shared scene manifest before training. Local results below are reproduction results.

## Third-party reproduction audit (2026-09-06)

Cloned [OpsiClear-4DGS/FreeTimeGsVanilla](https://github.com/OpsiClear-4DGS/FreeTimeGsVanilla)
at `911dcf4157a3ddf5c96d9147f97627480268fe0f` into
`.local/FreeTimeGsVanilla`. Its LICENSE is GNU AGPL version 3. This is an
existing third-party reproduction, **not the author's implementation**.
An EasyVolcap remote-head check exposed `main` and `custom_viewer`, not a
FreeTimeGS-specific branch; this does not prove no other author release exists.

The executable entry point is
`src/simple_trainer_freetime_4d_pure_relocation.py`. Audit executable values,
not its stale introductory examples: `Config.max_steps` is 70,000, and the
actual CLI presets are `default_keyframe` and `default_keyframe_small`.
Both disable ordinary strategy refinement and enable custom relocation.
Both override 4D regularization to `1e-4` and duration regularization to
`1e-3`. The small preset actually caps samples at 5,000,000 despite its
4M description. Matched training below uses `default_keyframe`.

The model stores means, scales, quaternions, opacities, SH DC/rest, canonical
times, durations, and velocities. Rendering uses gsplat. Saved checkpoints
contain step, splats and optimizer state, but omit scheduler, random-generator,
sampler, strategy and gradient-accumulator state. Loading resets strategy and
gradient accumulation and merely warns if optimizer restoration fails.
Consequently upstream checkpoint loading is not yet a validated exact training
resume; the adapter must add complete state and fail closed on mismatch.

`environments/freetimegs.in` stages isolated candidate Python dependencies under
the existing Python 3.14 / Torch cu130 policy. It does not install the upstream
package: its NumPy `<2` pin needs compatibility validation, native gsplat and
fused-ssim need pinned builds, and optional viewer/compression/COLMAP dependencies
are outside the shared-manifest adapter path. Environment setup, native kernels,
training-only temporal initialization, camera/time adaptation, budget supervision
and offline checkpoint evaluation remain unvalidated. Neither scene has incurred
FreeTimeGS training time. Basketball also retains its matching-calibration gate.

Candidate setup subsequently passed with
`bash scripts/setup-environment.sh freetimegs`: Python 3.14.6, Torch
2.13.0+cu130, torchvision 0.28.0+cu130, NumPy 2.5.2; all candidate imports and
`uv pip check` passed. Full resolved inventory and setup log are in
`.local/runs/environment-freetimegs-WuxlCoTY`. This validates the dependency
profile only, not upstream imports, CUDA kernels or training.

## Locked native dependencies

Use the reproduction's `uv.lock`, not the current renderer HEAD:

| Component | Revision | License |
| --- | --- | --- |
| gsplat 1.5.3 | `b60e917c95afc449c5be33a634f1f457e116ff5e` | Apache-2.0 |
| gsplat GLM submodule | `33b4a621a697a305bc3a7610d290677b96beb181` | MIT or Happy Bunny |
| fused-ssim | `1272e21a282342e89537159e4bad508b19b34157` | MIT |

Checkouts live in `.local/gsplat-freetimegs` and
`.local/fused-ssim-freetimegs`. `scripts/build-freetimegs-native.sh` verifies
these revisions and builds offline with CUDA 13.0, architecture 8.9 and two
compiler jobs. `scripts/verify-freetimegs-native.py` separately checks packed
and unpacked rasterization, finite backward gradients, identical/perturbed
fused SSIM and selective Adam visibility updates. Neither check is a matched
scene training result. gsplat's Python dependencies `jaxtyping` and `rich`
were added to the isolated environment; refreshed setup and imports passed in
`.local/runs/environment-freetimegs-H5dfjqo7`.

Additional resume incompatibility found by inspecting the locked sources:
fresh initialization creates ordinary `torch.optim.Adam`, whereas
`load_checkpoint` replaces it with `SelectiveAdam` and omits that pinned class's
required `betas` argument. An exact-resume adapter must preserve the original
optimizer type and settings rather than adopting this upstream reload path.

The offline build passed without source compatibility patches in
`.local/runs/freetimegs-native-build-PzZiBfzi` (3m30s package preparation).
Both native packages installed and `uv pip check` passed. GPU kernel execution
remains pending; a successful compilation is not evidence of device access.

`scripts/freetimegs_source.py` extracts the three native temporal methods by AST
without executing trainer imports or initialization. Two CPU tests passed for
linear motion, static mode, temporal Gaussian opacity, finite gradients, and
the regularizer's stop-gradient behavior. This reuses the reproduction equations;
it is not a new implementation from the paper or a complete training adapter.

The synthetic GPU gate subsequently passed on the NVIDIA GeForce RTX 4090:
`.local/runs/freetimegs-native-cuda-20260906.json`. Packed/unpacked render
maximum absolute difference was zero; fused SSIM was 1.0 for identical images
and 0.9519809484 for the deliberately perturbed pair. Native render/SSIM
backward gradients and selective Adam visibility updates passed. The report
records the two extension binary hashes and Torch version. This supersedes the
pending GPU status above, but does not validate a complete reproduction model,
training resume, scene training, or offline scene evaluation. All 94 CPU tests
also passed before this device check.

## Shared camera adapter

`scripts/freetimegs_scene.py` wraps the validated SelfCap scene loader and exposes
batched camera-to-world/world-to-camera matrices, unchanged continuous pinhole
intrinsics, corrected time, and contiguous batch/height/width/RGB pixels in
`[0,1]`. It performs no additional resizing or coordinate recentering. Training
camera requests explicitly reject the held-out split, while evaluation requests
can load it. The shared sweep, lazy loading and source-image hash checks are
preserved.

Three tests cover nonidentity pose conversion and off-center projection, RGB
layout, split exclusion, corrected times, sweep poses and image tampering.
The real manifest check loaded held-out camera 0015/frame 4150 at corrected time
`0.5002984601802468`, with shape `1 x 1061 x 1890 x 3`, confirmed 1,380 training
samples, and converted all 20 sweep poses. No model was trained or evaluated in
this check. Temporal initialization and complete native training/resume remain
the next adapter gates.

## Native initialization loader

`freetimegs_source.load_initializer` now extracts the reproduction's native
`create_splats_with_optimizers_4d`, KNN and RGB-to-SH functions without importing
the full trainer. It returns an AST digest alongside the callable. A synthetic
CPU test in the FreeTimeGS environment passed for all nine parameter groups,
KNN-derived scales, SH layout, duration clamping, scene-scale-adjusted position
learning rate and an ordinary Adam update for every group. The test supplies
explicit synthetic inputs/settings; it does not select a scene-training preset.

This adds native model construction support, not training-only temporal
reconstruction. The existing midpoint cloud has not been relabeled as a
multi-time initialization or assigned unverified velocities. Choosing and
validating temporal geometry, complete training-state resume and the native
loss/relocation loop remain unfinished.

`scripts/freetimegs_model.py` now binds the native initializer, temporal methods
and renderer to the shared camera layout. The extended GPU verifier passed in
`.local/runs/freetimegs-model-cuda-20260906.json`: four synthetic Gaussians,
two distinct time renders, finite gradients for all nine groups and one ordinary
Adam update per group. Initializer/render AST hashes and extension binary hashes
are recorded. Its scale `0.3` is a diagnostic setting, not a selected scene
preset. No native loss schedule, relocation or scene training is claimed.

The shared CPU triangulation helper now accepts `--frame-id` while retaining
4150 as its default. Its first-frame integration test produced 5,256 points from
all 23 training cameras, mean reprojection error 0.5564470705 pixels, in 8.04s:
`.local/data/selfcap/dance1-initialization-frame4120-20260906`. Fixed calibration
checks passed. Three added frame-selection tests reject invalid windows,
duplicate training camera IDs and missing/duplicate frames. This is preprocessing,
not charged training time. Temporal pair generation is not yet complete.

Temporal pair generation subsequently completed for keyframes 4120, 4125, ...,
4175 and each next frame. All 24 clouds use the 23 training cameras and fixed
calibration; the existing frame-4150 cloud was reused with validated provenance.
`prepare-freetimegs-initialization.py` assembled
`.local/data/selfcap/dance1-freetimegs-sparse-initialization-20260906`:
61,905 keyframe points, 61,486 valid KNN displacement estimates, archive SHA-256
`f3315b4d1b5066f9deeb34493ed85c27ded3d13e613e15474f7c00474c5b0914`.

The assembler reuses the native KNN helper (distance threshold 0.5, k=1), uses
all available keyframe points, and preserves the combiner's three-gap duration.
Velocities are converted from displacement per source frame to displacement per
manifest-normalized unit. Canonical cloud time is the mean corrected time of its
training images; each input time range and each PLY/evidence hash are recorded.
This cannot eliminate fractional-camera-offset geometry errors. Sparse COLMAP
instead of dense ROMA geometry is an explicit adaptation, not an equivalent
initialization claim; KNN displacement is not a tracked motion correspondence.
The four assembler tests cover displacement validity, normalized units/durations,
missing successors, wrong source frames and held-out provenance rejection.
Initial model coverage inspection and training-state integration remain pending.

### Untrained initialization coverage inspection

`preview-freetimegs-initialization.py` rendered held-out frames 4120, 4150 and
4179 at 1890x1061 on the RTX 4090 into
`.local/runs/freetimegs-initialization-preview-20260906`. All three PNGs were
visually inspected: mostly black with sparse specks outlining scene structure
and several isolated blurred blobs; the moving person is not reconstructed as
a coherent surface. Mean alpha is respectively 0.0100876, 0.0173847 and
0.00806307 (not a thresholded pixel-coverage statistic). Peak allocated GPU
memory was 124,926,976 bytes. No optimization steps were taken.

This is a significant initialization limitation with the keyframe preset's
scale 0.03 and the sparse cloud, not evidence that trained FreeTimeGS would fail.
The default relocation-only preset assumes a much denser starting representation.
Before committing scene training budget, choose whether to explicitly accept a
sparse-initialization pilot or prioritize a released dense training-only
initializer. Increasing splat scale or enabling densification has not been
silently substituted. Native training-state integration is still unfinished.

## Released dense-initializer investigation

Following the user's choice to prioritize dense initialization, audited
RoMa `77f8d68803526dcddfd9b7a46bc76125bdc25f15` in `.local/RoMa` and EDGS
`f90b022445fc88368f75e66e8fb34aea88372cac` in `.local/EDGS`. EDGS exposes a
correspondence-based initializer but permits only non-commercial academic or
personal use. On 2026-09-06 the user confirmed the intended use qualifies as
non-commercial academic research and/or non-commercial personal use. This clears
the intended-use gate for evaluating EDGS, not the separate dependency and asset
audits or redistribution-notice requirements.
Its native RoMa submodule pin differs from the standalone checkout; do not claim
the standalone installation reproduces EDGS's locked runtime.

The isolated `roma` candidate environment passed Python 3.14.6 / Torch
2.13.0+cu130 setup and dependency import checks in
`.local/runs/environment-roma-hiaGTxDE`. Standalone RoMa 0.1.2 installed offline
from the inspected checkout with `--no-deps --no-build-isolation`. This is
matcher preparation only: no matcher/backbone checkpoints were downloaded and
no dense matching or triangulation has run. The separate license and asset
provenance audit is maintained in [research.md](../research.md#licenses-and-asset-provenance).

The standalone `romatch`, `roma_outdoor`, and `roma_indoor` imports passed
without loading weights. `uv pip check` verified all 85 installed packages are
compatible; its cache-lock check required the approved outside-sandbox retry.
These checks establish installation compatibility, not GPU matcher correctness.

Reproduce the candidate preparation after cloning RoMa at the pin above:

```bash
bash scripts/setup-environment.sh roma
uv pip install --offline --no-deps --no-build-isolation --python /home/auss/git_repos/samaust/Experiments_4DGS/.local/envs/roma/bin/python .local/RoMa
/home/auss/git_repos/samaust/Experiments_4DGS/.local/envs/roma/bin/python -c 'import romatch; from romatch import roma_outdoor, roma_indoor; print(romatch.__file__)'
uv pip check --python /home/auss/git_repos/samaust/Experiments_4DGS/.local/envs/roma/bin/python
```

### Released geometry compatibility check

The matching EDGS RoMa revision `370117431ffc5dc000fb46f6e581b74bdb2c3ff8`
is now checked out separately in `.local/RoMa-edgs`; its `roma_indoor` import
passed in the prepared environment without loading weights. This preserves the
standalone candidate installation. Upstream reports optional xFormers unavailable;
no replacement attention package has been installed.

`scripts/edgs_source.py` loads four unchanged EDGS geometry helpers from the
external checkout and records source, extracted-AST, and license hashes. It does
not import the Gaussian-Splatting trainer or redistribute its source. Three CPU
tests passed: malformed calibration rejection, calibrated triangulation with
non-identity extrinsics and an off-center principal point, and self-excluding
native nearest-neighbor selection.

The thin projection adapter packs `K[R|t]` for row-vector use, with camera depth
in both columns 2 and 3: the native solver uses the former and its error routine
uses the latter. This deliberately uses processed-image pixel coordinates, not
graphics clip-space near/far depth. The native error calculation adds `1e-4` to
depth, so its reported residual is slightly nonzero even for exact observations.
Dense matching, match-coordinate conversion, positive-depth filtering, scene
coverage, and complete initializer integration remain unvalidated.

```bash
/home/auss/git_repos/samaust/Experiments_4DGS/.local/envs/roma/bin/python -m unittest discover -s tests -p test_edgs_geometry.py -v
```

### Pinned matcher CUDA smoke check

After the preparation-only checks above, the released indoor matcher and standard
DINOv2 backbone were downloaded into `.local/weights/roma-edgs`; official URLs and
SHA-256 hashes are in the research provenance table. `verify-roma-edgs.py` requires
those hashes and a clean pinned source checkout, loads with `weights_only=True`,
blocks Python socket connections, and prohibits CPU fallback. Using the EDGS fast
settings (560 coarse resolution, no upsampling, asymmetric matching), an identical
synthetic image pair passed on RTX 4090 / Torch 2.13.0+cu130. Wall time was 4.781 s,
peak allocated memory 2,738,577,408 bytes, mean certainty 0.83114, and mean absolute
identity error 0.000638 in normalized coordinates. Report:
`.local/runs/roma-edgs-cuda-20260906.json`. Sandbox device access failed; the single
approved host retry succeeded. This is not scene-quality or training evidence.

```bash
/home/auss/git_repos/samaust/Experiments_4DGS/.local/envs/roma/bin/python scripts/verify-roma-edgs.py --checkout .local/RoMa-edgs --weights .local/weights/roma-edgs --output .local/runs/roma-edgs-cuda-20260906.json
```

The full CPU regression suite discovered 108 tests: 107 passed and one existing
optional-dependency test skipped in the STG environment. All three new EDGS
geometry tests passed independently in the RoMa environment.

### Training-only dense temporal initialization and coverage

`initialize-edgs-selfcap.py` generated all 24 required keyframe/successor clouds
using the released EDGS geometry helpers and pinned RoMa. This is an explicitly
adapted geometry-only **fast** path, not EDGS's default three-neighbor pipeline:
all 23 training references, one native nearest neighbor, 15,000 weighted samples
per reference, indoor matcher, no upsampling, and unchanged 560 coarse matching.
RoMa's continuous pixel mapping matches the shared calibration; the EDGS helper's
`W-1`/`H-1` color-index remapping is not used. Nonfinite or negative-depth points
and points exceeding 0.01 L1 normalized reprojection error in either image are
dropped, rather than assigned EDGS's near-zero opacity. EDGS scale/SH/opacity
construction is omitted; FreeTimeGS constructs those natively from the geometry.
All differences and source/asset/input hashes are recorded per cloud. The EDGS
copyright, conditions, and disclaimer are retained in `docs/licenses/EDGS.txt`.

All 24 clouds completed sequentially with 339,785–343,430 points each. The sum of
their reported matcher/geometry wall times is 206.700 seconds (excludes process
startup and initial input validation), and peak allocated GPU memory per frame
was 2,752,895,488 bytes. The midpoint retained 342,669 of 345,000 sampled matches.
The dense loader rejects wrong frames/splits, changed input/archive hashes,
invalid dimensions/types/colors, and nonfinite data. Regression suite: 112 tests,
111 passed and one existing optional-dependency skip; all seven EDGS tests passed
separately in the FreeTimeGS environment.

The `--dense-edgs` assembly produced 4,106,783 temporal points, including 4,100,548
with native nearest-neighbor displacement estimates. Archive:
`.local/data/selfcap/dance1-freetimegs-edgs-initialization-20260906/initialization.npz`,
SHA-256 `e2753700453c55fa59f30fe5d9c14ba74627016445cefb6bc5176019d57de6b4`.
Keyframe spacing, duration multiplier, and velocity-unit conversion are unchanged
from the audited sparse assembly. Camera-time spread and estimated, untracked
velocities remain limitations.

Native start/middle/end previews at 1890×1061 are in
`.local/runs/freetimegs-edgs-initialization-preview-20260906`. Mean alpha was
0.267991, 0.386303, and 0.229530 respectively, versus 0.010088, 0.017385, and
0.008063 for sparse initialization. These are average alpha values, not pixel
coverage percentages. Peak allocated memory was 2,972,953,600 bytes. All three
images were inspected: shelves and background are much more recognizable, but
the images remain dark/grainy and the moving person is poorly represented in
these unoptimized temporal Gaussian previews. Scale 0.03 and opacity 0.5 were
not changed to improve appearance.

A separate quarter-resolution, nearest-depth point diagnostic at the midpoint
(`.local/runs/edgs-midpoint-points-20260906.png`, 472×265) shows the dancer's torso
and legs in the per-frame cloud. It uses held-out calibration, not held-out RGB;
the held-out RGB was inspected separately for qualitative comparison. This rules
out complete foreground omission at that frame, but does not validate temporal
motion or trained quality. The diagnostic is not a reduced-resolution benchmark.
Reproduction commands are in [the creation guide](../local-creation.md).

### Native optimization and checkpoint groundwork

`freetimegs_training.py` fails closed on trainer source SHA-256
`fc3e4320da73a470d0a16bcb5803f84d1bda5bdeafb000fcc39e022fbcfaaeb4` and extracts the
released `default_keyframe` preset and complete optimization-step statements.
Only camera inputs and the iteration-boundary metrics return are adapted; loss,
annealing, optimizer update, gradient accumulation, relocation, strategy, and
pruning statements remain native. The preset resolves to 70,000 steps, relocation
starting at 100 and stopping at 63,000, and standard densification disabled until
100,000. The native `init_duration=-1` sentinel is preserved, including its use as
the duration-regularization target; this is not silently repaired to the positive
duration computed by the upstream data loader.

`freetimegs_checkpoint.py` records all nine parameter groups, ordinary-Adam
states, position scheduler, strategy state, relocation accumulator/count, caller
loop/sampler state, RNG, configuration, and provenance. It rejects uncleared
gradients, malformed parameter shapes and changed configuration/source identity,
and publishes new checkpoints without overwriting previous ones. CPU tests verify
exact next-update equality and rejection of incomplete updates/wrong provenance.

Synthetic CUDA verification at
`.local/runs/freetimegs-training-state-cuda-20260906.json` passed native L1,
valid-padding fused SSIM, LPIPS-Alex, duration regularization and relocation.
It restored a checkpoint into a newly constructed model **in the same process**:
next loss difference was zero, with maximum parameter difference
`1.7881393432617188e-7` in quaternions (all other groups exact). Four-point diagnostic
overrides were scale 0.3 and relocation ratio 0.5; these are not scene-training
settings. CPU suite: 116 discovered, 113 passed, three optional-dependency skips;
both native training-source tests also passed in the FreeTimeGS environment.

The subsequent scene integration below adds fresh-process reload and supervised
training with the reproduction's coordinate normalization and loader duration
override (two keyframe gaps); the earlier world-space previews used the
combiner's three-gap archive durations.

```bash
/home/auss/git_repos/samaust/Experiments_4DGS/.local/envs/freetimegs/bin/python scripts/verify-freetimegs-training.py --torch-cache .local/cache/torch --output .local/runs/freetimegs-training-state-cuda-20260906.json
```

### Supervised scene integration and fresh-process evaluation

`train-freetimegs-manifest.py` now uses the shared two-hour ledger and process-group
deadline supervisor. It checkpoints at cleared-gradient iteration boundaries with
120 seconds reserved for checkpointing and a further 30-second step allowance.
Its synchronous shuffled-epoch sampler reuses the existing balanced sampler with
one bucket, preserving uniform training-view sampling without prefetch ambiguity.
All initialization, loss, optimizer, scheduler, relocation and pruning settings
are native except the documented shared-profile adaptations.

`freetimegs_normalization.py` fits the released similarity/PCA normalization to
23 training cameras and the audited training-only midpoint SfM cloud. Projection
and linear-motion invariance tests passed. The native five-extent distance filter
retained 4,101,912 of 4,106,783 points; normalized scene scale is 1.10000013.
The two-gap loader duration is 0.16264537 in corrected manifest time units. The
negative duration-regularizer target remains native, as documented above.
The native loader's velocity-norm cap of 10 is a no-op for this archive: the
maximum normalized velocity norm is 5.407525, with zero points above the cap.

Five initial scene steps and a separate-process five-step resume succeeded:

| Segment | Completed iteration | Measured command wall | Sampled peak GPU memory |
| --- | ---: | ---: | ---: |
| `.local/runs/freetimegs-selfcap-5-20260906` | 5 | 25.421 s | 7,936 MiB |
| `.local/runs/freetimegs-selfcap-10-20260906` | 10 | 26.817 s | 7,696 MiB |

Both baselines were 850 MiB. The ledger charged **49.677513 seconds total**;
measurement includes additional command startup outside the supervised worker.
Each checkpoint is 3,166,716,200 bytes and includes optimizer state. The latest
checkpoint SHA-256 is `265fda2ee8c9530e1643a90a020d8401bfd115d6900e3d39c79c3edc513fabd5`.

`render-freetimegs-manifest.py` reconstructs the complete native rendering state
without reloading initialization clouds or optimizer buffers onto the GPU. It
validates configuration, normalization, source, binary and checkpoint provenance.
The FreeTimeGS evaluation wrapper reuses the matched evaluator and packaging
pipeline; ATGS's default dispatch is unchanged. Two fresh, network-disabled
processes rendered all 60 held-out frames and 20 sweep poses with **exact PNG and
float hashes**. Evidence and fixed crops are in
`.local/runs/freetimegs-selfcap-10-evaluation-20260906/evidence`.

Iteration-10 diagnostics: PSNR 8.38402, SSIM 0.0816383, LPIPS-Alex 1.143195,
131.212 FPS (10 warmups, 100 synchronized renders), evaluation wall 180.069 s.
These intentionally tiny integration segments are not a quality comparison with
the other 5,000-step pilots. Rendering uses the learned active SH degree (zero at
this early checkpoint); the unused higher-degree coefficients remain zero.
CPU regression suite: 117 tests, 114 passed, three optional-dependency skips.

### 5,000-step SelfCap pilot

The fresh-process continuation from iteration 10 completed another 4,990 native
steps without changing the 70,000-step schedule. All losses remained finite;
native relocation ran every 100 steps and retained 4,101,912 Gaussians. Periodic
complete checkpoints were saved at iterations 1,000 through 5,000.

| Measurement | Result |
| --- | ---: |
| Continuation command wall | 519.042032 s |
| Total charged training, including integration segments | 567.387962 s / 7,200 s |
| Device baseline / sampled peak | 851 / 7,843 MiB |
| Framework peak allocated / reserved | 5,612,892,672 / 6,824,132,608 bytes |
| Final checkpoint size | 3,199,531,938 bytes |
| Held-out PSNR / SSIM / LPIPS-Alex | 19.153970 / 0.682328 / 0.528610 |
| Warm throughput (10 warmups, 100 synchronized renders) | 162.731 FPS |
| Evaluation command wall | 176.102405 s |

Training and measurement directories are
`.local/runs/freetimegs-selfcap-5000-20260906` and
`.local/runs/freetimegs-selfcap-5000-measurement-20260906`.
The final `checkpoint-005000.pt` SHA-256 is
`d964bc3ce2758be7c57e324d3f2343553d507a8df0048d2c79dbdf7c2852620f`.
Evaluation and packaged evidence are in
`.local/runs/freetimegs-selfcap-5000-evaluation-20260906`.
Two fresh network-disabled processes produced exact PNG bytes and raw float
hashes for all 60 held-out images and 20 sweep poses. SH degree is three here.

Inspected start/middle/end frames 4120, 4150 and 4179, the fixed body-boundary and
book-text crops, and sweep poses 0, 10 and 19. The dancer is now recognizable,
but head/hair and body edges remain strongly blurred/ghosted; frame 4120 has
particularly washed-out upper-body detail. Thin colored streaks/floaters appear
over the torso and background. Static book text is unreadable in the inspected
crop. The frozen-time sweep retains blur and streaks; it has no matched ground
truth. These sampled sheets do not establish a quantified flicker claim.

Checked aggregate and per-frame deltas are
`.local/runs/freetimegs-vs-lite-selfcap-5000-20260906.json` and
`.local/runs/freetimegs-vs-full-selfcap-5000-20260906.json`. All three metrics trail
both STG pilots, but initialization, update counts and charged time differ.
This is a third-party reproduction with an adapted released EDGS initializer,
not an author checkpoint or a completed native-schedule comparison.

### Final budget-limited SelfCap continuation

The continuation from 5,000 steps stopped cleanly at **42,061 / 70,000** with
reason `deadline`. No forced kill or budget overrun occurred. Native loss,
learning-rate schedule, relocation and initialization were unchanged; periodic
checkpoints were spaced every 5,000 steps to limit disk use. All logged losses
were finite, with 4,101,912 Gaussians retained. The remaining 173.892210 seconds
are below the trainer's restart/reserve requirement and are not a new segment.

| Measurement | Result |
| --- | ---: |
| Continuation command wall | 6,460.046399 s |
| Total charged training, including earlier attempts | 7,026.107790 s / 7,200 s |
| Device baseline / sampled peak | 825 / 7,532 MiB |
| Framework peak allocated / reserved | 5,542,404,096 / 6,387,924,992 bytes |
| Final checkpoint size / save wall | 3,199,531,938 bytes / 2.901995 s |

Run: `.local/runs/freetimegs-selfcap-final-20260906`;
measurement: `.local/runs/freetimegs-selfcap-final-measurement-20260906`.
The final `checkpoint-042061.pt` SHA-256 is
`49d732ee75bbc85863acf4eb4b621683b3df51720a69d9e536197fa2a66f7856`.
Reproduce the continuation with the command in [the training guide](../local-creation.md).
This is the final checkpoint within the allocated budget, **not native-schedule
completion or full-paper convergence**.

Final evaluation: `.local/runs/freetimegs-selfcap-final-evaluation-20260906`.
All 60 held-out camera-0015 frames and 20 midpoint sweep poses reload exactly
in PNG bytes and raw-float hashes across two fresh network-disabled processes.
PSNR is **25.496026 dB**, SSIM **0.881698**, LPIPS-Alex **0.137213**;
warm throughput is **182.781 FPS** (10 warmups, 100 synchronized renders).
Evaluation wall time is **181.371234 seconds**, separate from training.

Checked comparisons against the completed 30,000-step STG checkpoints are
`.local/runs/freetimegs-vs-lite-selfcap-final-20260906.json` and
`.local/runs/freetimegs-vs-full-selfcap-final-20260906.json`. Deltas in
PSNR / SSIM / LPIPS are +3.077277 / +0.030494 / -0.082150 versus Lite and
+0.999274 / +0.017485 / -0.077399 versus Full. These are observed budget-limited
results with different initialization, update counts and charged time, not a
converged author-implementation ranking.

Inspected `evidence/prediction-contact.png`, matching ground truth, fixed
`prediction-hands_body_boundary-contact.png` and
`prediction-static_book_text-contact.png`, plus `sweep-contact.png`:

- Frame 4120 still has severe face/hair and forearm smearing relative to the
  sharper ground truth. Frame 4150 retains excess hair blur despite motion blur
  also being present in the source image. Frame 4179 has clearer facial features,
  but fine hair remains oversmoothed.
- Shelves and the dancer are much more coherent than in the 5,000-step pilot;
  the prominent colored streaks are not evident in these sampled views. Small
  book-spine text is still soft, and hands/skin boundaries are oversmoothed.
  This does not establish the absence of floaters throughout the sequence.
- Sweep poses 0, 10 and 19 retain hair/hand blur; there is no ground truth for
  this path. The sampled contact sheets do not establish a flicker ranking.

All PNGs, MP4s, crops, camera/time records and sequence-analysis output are
retained in that evaluation directory. **Investigate rendering further** for
motion artifacts: the improvement supports closer inspection, not an unqualified
quality win or permission to extend the agreed training budget.

## Plan 005 Basketball calibration update — 2026-09-06

The [ViPE pilot](basketball-calibration-20260906.md) audited all 34 videos but
stopped at camera 4 intrinsic instability: 20.2948% focal range relative to the
median, above the 20% pilot threshold fixed before inference. No accepted
estimated calibration or synchronization was produced. Basketball training and
evaluation remain blocked; this task charged zero training seconds and left
the existing method allocations unchanged.

The subsequent user-authorized **25%** pilot passed. The
[all-camera continuation](basketball-calibration-20260906.md#all-camera-continuation-outcome-blocked-at-camera-5)
then stopped at camera 5 (**26.0539% > 25%**); the other 33 cameras passed the
intrinsic check. This supersedes camera 4 as the current calibration blocker.
Shared geometry, synchronization and Basketball training remain unexecuted.
Cumulative calibration charge is 323.0525 seconds; training charge remains zero.


### Current 23-camera variant after camera 19 removal

The user also removed camera 19. The current variant has 23 cameras: 20
training and held-outs 0, 10, 30; 1,150 expected images (150 held-out).
[The rebuilt 23-camera search](basketball-no-camera19.md) completed 32 independent
reconstruction commands. Its best result is **5.8807 degrees / 7.1892% of rig
diameter**, failing the unchanged pose gates. All retained priors and full focus
screens pass, but calibration and downstream training/evaluation remain blocked.
No new GPU inference was used; cumulative calibration charge remains 1,056.0873
seconds and the original training budgets are unchanged.
