# Experiment 007: FreeTimeGS

Status: **pending source/data validation**.

The author-linked EasyVolcap framework was inspected at
`4cb3c000a31b8764834c79792b355f110d947e75` in `.local/EasyVolcap` on
2026-09-06. No FreeTimeGS-named model/configuration was found in its `main`
checkout. The linked fast Gaussian rasterizer alone is not a complete dynamic
training implementation. An explicitly identified reproduction remains an
option, but has not been integrated or measured for either matched scene.

Identify the author implementation and any vanilla reproduction separately.
Record commit, license, checkpoint format, rasterizer, and adaptations to the
shared scene manifest before training. No local result is claimed yet.

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
4M description. No preset has yet been selected for matched training.

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
