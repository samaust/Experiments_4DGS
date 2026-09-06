# Experiment 009: ATGS

Status: **Native dependency smoke tests passed; full-model and training adapter pending**.

Use the selected hash encoder and exact short windows from the shared manifests.
Record support for calibration, held-out rendering, offline reload, and required
output dimensions before adapting the implementation.

## Pinned source audit, 2026-09-06

The clean local checkout `.local/ATGS` is pinned to
`10388ebf973658a1cee219901a74128148bca051`. This audit reads source only; no ATGS
training or GPU build was launched, so both scene training budgets remain unused.

- `arguments/vru/basketball.py` selects `hash=True`, 100,000 iterations,
  13 temporal encoder levels, balanced gradient accumulation, a twofold image
  downsample and `llffhold=10`. Its absolute initial-cloud path is author-local
  and cannot be reused as training-only initialization evidence.
- `scene/spacetime_hash.py` implements the hash representation with
  `tinycudann.NetworkWithInputEncoding`; it is not missing model code. The
  README requests tiny-cuda-nn 1.7 and gsplat, while `env.yml` pins legacy MMCV
  and torch-scatter. These need an isolated Python 3.14/Torch-cu130 build audit,
  not replacement by the plane configuration.
- `Scene` autodetects COLMAP/Blender/DyNeRF/Nerfies layouts, not the shared
  manifest. Its default camera construction uses FOV-based centered projection.
  The adapter must retain the manifest's off-center intrinsics, explicit held-out
  IDs and per-camera corrected times rather than exporting images alone.
- `Scene.save()` writes the anchor PLY, four appearance/deformation MLPs,
  voxel-grid state/bounds, and `FDHash.pth`, plus both optimizers when configured.
  `--restore_iteration` loads the directory-based model and optimizer files.
  This path must be tested before calling the checkpoint complete/resumable.
- The separate legacy `capture()` returns ten tuple items, but `restore()`
  unpacks eleven (including `active_sh_degree`). It also omits hash/MLP state
  from that tuple. Do not use `--start_checkpoint` as the complete model route.
  This does **not** establish that the directory-based restore path is broken.
- Training flushes accumulated gradients at explicit save boundaries, but a
  deadline adapter must also preserve sampler/RNG, optimizer-update and warmup
  bookkeeping. Existing optimizer files alone do not establish exact resumption.
- Upstream documented rendering emits JPEGs and its evaluator reports DSSIM;
  the matched adapter must export PNGs and use this repository's shared evaluator.

SelfCap remains an implementation task, not an unavailable-source failure.
Basketball additionally requires calibration matching the DG archive: the
README's Long-sequence camera download is not verified as DG calibration.

## Python environment and configuration validation

`bash scripts/setup-environment.sh atgs` completed successfully. The isolated
`.local/envs/atgs` uses Python 3.14.6, Torch 2.13.0+cu130 and torchvision
0.28.0+cu130. Candidate imports and `uv pip check` pass. Dependency resolution,
installed versions and setup output are in
`.local/runs/environment-atgs-aAhoxTYj/`. This is not a native CUDA build result.

`patches/atgs-mmengine-config.patch` replaces only the two `mmcv.Config`
calls with MMEngine's Config loader. The CPU-only `verify-atgs-config.py`
independently compares every inherited configuration value with the pinned
source dictionaries and checks explicit CLI iteration precedence and hash/3dgs
selection. It passed, writing `.local/runs/atgs-config-20260906.json` with source
hashes. The patch reverse-apply check passes; it is already applied locally.

The pinned checkout has neither the `submodules/` directory referenced by
`env.yml` nor a `.gitmodules` file. Native dependency sources must be recovered
and explicitly pinned, not merely initialized with recursive submodule update.
No ATGS training budget has been consumed.

### tiny-cuda-nn source selection

The official tag listing has no `v1.7` tag. The cloned source is pinned at
`32507f059d7abc8c13f5df81ea9597b70923ee44`, whose CMake project declares
version 1.7, immediately before the 2.0/JIT change. This is an explicit local
dependency choice, not an author-pinned release tag. Source directory:
`.local/tiny-cuda-nn-atgs`.

The PyTorch build requires CUTLASS
`1eb6355182a5124639ce9d3ff165732a94ed9a70` and fmt
`b0c8263cb26ea178d3a5df1b984e1a61ef578950`. The tree also has an unmapped
`dependencies/cmrc` gitlink; generic submodule status fails on it. The PyTorch
setup script does not use cmrc, so initialize the two required mapped paths
explicitly. Native build/forward/backward validation remains pending.

Both required submodules were downloaded at those hashes. The tracked build
patch replaces unavailable `pkg_resources`, selects C++20 for the current
Torch headers, and disables fmt 9's NVCC-incompatible C++20 consteval format
check consistently in all translation units. The first compile failed on that
format check (`atgs-tcnn-build-1EMh1G6W/build.log`); this was a compiler error,
not a permission failure. Build logs are separate from the training ledger.

The patched offline build succeeded and installed `tinycudann==1.7` into the
ATGS environment. Build/package preparation took 4m 41s according to uv;
the 95-package environment passes `uv pip check`. Successful build log:
`.local/runs/atgs-tcnn-build-qyA44eOe/build.log`. Compilation targeted SM89 with
two jobs. This completes compilation only; the synthetic CUDA verifier and
remaining rasterizer/scatter dependencies are separate gates.

The approved CUDA retry passed on the RTX 4090. The synthetic ATGS-shaped
single encoder/MLP produced finite outputs and gradients; in-process reload
output difference, resumed loss difference and next-step parameter difference
were all zero in this test. Framework peak allocation was 2,475,975,168 bytes.
Report: `.local/runs/atgs-tcnn-cuda-20260906.json`. This validates the dependency,
not the complete ATGS representation, renderer or offline checkpoint contract.

### Recovered native dependencies

The LocalDyGS clone succeeded at `39dacdcd8ef6d2b93824df79041713b4a29fb828`.
Its bundled `submodules/diff-gaussian-rasterization` exposes the two-output
forward and `visible_filter` API expected by ATGS; `submodules/simple-knn`
contains its initialization kernel. These are explicit recovered dependency
candidates, not verified original ATGS submodule revisions. The checkout's
Gaussian-Splatting license limits use to non-commercial research/evaluation.

The initial offline build failed on missing integer definitions in
`rasterizer_impl.h` (`atgs-rasterizer-build-E7d0J5oJ/build.log`). The tracked
`localdygs-cstdint.patch` adds the missing standard include without changing
kernel math. `build-atgs-rasterizer.sh` checks the source pin and patch before
building for SM89. This source error was not a sandbox/permission failure.

The patched build succeeded: both native packages installed and the 97-package
environment passed `uv pip check`. Build log:
`.local/runs/atgs-rasterizer-build-BFXvYYVo/build.log` (29.32 seconds package
preparation). Compilation alone does not validate the GPU kernels. Shell/Python
syntax checks, both ATGS patch reverse-checks and all 45 existing unit tests pass.

The approved GPU retry passed on the RTX 4090, producing
`.local/runs/atgs-rasterizer-cuda-20260906.json`. Synthetic rasterization and
backpropagation are finite with nonzero position/color gradients; visibility
filter radii exactly match forward radii `[6, 5, 5, 4]`. KNN mean squared
three-neighbour distances differ from the brute-force reference by at most
`5.960464477539063e-08`. The verifier's measured section took 0.406 seconds.
This establishes a dependency smoke test, not complete ATGS rendering or
quality/throughput evidence. The prior sandbox attempt reported CUDA unavailable;
the approved retry needed no source change.

`atgs-optional-imports.patch` now reverse-checks successfully: gsplat loads only
inside the unused 2DGS functions, while Open3D loads only for debug exports.
The configured 3DGS/hash representation is unchanged. Full ATGS import,
torch-scatter, manifest camera adaptation and complete checkpoint validation
remain pending; no ATGS scene training has run.

### Scatter and manifest-camera integration

Torch-scatter 2.1.2 source was recovered from its official repository at
`140d3ad677aae615767412873b90982cbf97d35d` (MIT license), matching ATGS's
requested version. `build-atgs-scatter.sh` builds offline with `FORCE_CUDA=1`
and SM89 so CPU-only build-host visibility cannot silently omit CUDA operators.
`verify-atgs-imports.py` checks scatter-max values and gradients with repeated
groups, negative features and an empty group, then imports the model and
renderer entry points. The training entry point is deliberately excluded:
it initializes LPIPS-VGG at import time and can trigger a weight download.

The unmodified torch-scatter 2.1.2 source built and installed successfully in
6m 03s package preparation; `uv pip check` passes for all 98 packages. Log:
`.local/runs/atgs-scatter-build-OEs47Tz8/build.log`. No compatibility patch was
required. CUDA scatter behavior and model imports remain a separate gate.

The approved retry of `verify-atgs-imports.py` passed on the RTX 4090:
scatter-max values and backward gradients match the exact expected tensors,
including negative features and an empty group. The pinned ATGS GaussianModel,
renderer and render entry point import successfully. Source hashes and results
are in `.local/runs/atgs-imports-cuda-20260906.json`. No training entry point
was imported and no weights were downloaded by this test.

`scripts/atgs_scene.py` reuses the shared SelfCap manifest reader's splits,
image hashes, dimensions, synchronization and sweep cameras. It maps corrected
`timestamp` to ATGS's `time`, retains off-center x/y projection, and applies
ATGS's depth convention. Author filename-based synchronization must remain
disabled to avoid correcting time twice. CPU projection/validation tests were
added. Anchor lifetime mapping, model initialization and resumable training
remain separate implementation tasks; this camera interface is not a completed
method adapter.

The camera interface also passed a CPU check against the actual processed
manifest (`f9cbfe6b1f01eba1a6b284579985356bc8497955bd18d696a31e4eb166a48199`):
1,440 cameras, 1,380 training views excluding camera 0015, and all 20 sweep
poses constructed successfully. A hash-checked held-out frame 4150 loaded as
RGB `[3, 1061, 1890]` with corrected time `0.5002984601802468`.
All 47 unit tests pass, including the two new ATGS camera tests.

### Full-model gate preparation

`scripts/atgs_config.py` merges upstream parser defaults and the inherited
basketball config without importing training or allocating GPU state. It follows
upstream's treatment of config keys without parser attributes and records those
ignored keys. Shared-profile overrides disable repeated downsampling and time
synchronization and use local frame indices `[0, 60)`.

Important correction to the nominal config audit: `auto_encoder_levels=True`
and `clip_size=20` make the effective encoder count **3** for 60 frames, not the
literal `levels=13`. The CPU config check confirms 128 feature channels and the
unchanged 100,000-iteration schedule. Preserve this upstream automatic behavior.

`verify-atgs-model.py` prepares a synthetic complete-model forward/backward
test at times 0.1, 0.5 and 0.9, covering all three routed encoders, with the
native rasterizer, MLPs and static voxel grid. It uses 64 synthetic anchors and
64×64 images only for dependency integration, not matched-scene evidence.
It takes no optimizer steps; scene training and checkpoint validation remain
pending. The smoke test must pass before this is considered integrated.

The approved forward/backward retry passed on the RTX 4090. All 64 synthetic
anchors were visible at each timestamp; each of the three routed encoders
received nonzero gradients and all 21 participating gradient tensors were
finite. Framework peak allocation was 3,436,662,784 bytes. Report:
`.local/runs/atgs-model-cuda-20260906.json` (0.603 seconds measured section).
This report predates the inference check and does not establish eval-mode
rendering or checkpoint reload.

Source inspection then found a 3DGS inference unpacking bug: the generator
returns five values when the color MLP is in eval mode, but the caller always
unpacks seven. `atgs-render-eval-unpack.patch` distinguishes those cases,
preserving the training path. Its reverse-apply check passes. CPU regression
tests reproduce the original inference exception, accept the patched five-value
output and check unchanged training values. The GPU verifier now additionally
switches to inference mode and checks exact image equality at all three times;
that extended check remains pending.

The approved extended check subsequently passed, writing
`.local/runs/atgs-model-eval-cuda-20260906.json`. Inference and training-mode
images were exactly equal at all three timestamps (maximum absolute difference
zero). Peak framework allocation was 3,436,723,200 bytes; the measured section
took 0.615 seconds. This is still synthetic evidence, with no optimizer steps.

### Native checkpoint probe

`scripts/atgs_checkpoint.py` adds a strict nonempty-file preflight for the
native PLY, four MLPs, voxel state and hash state, optionally requiring both
optimizer files. Missing voxel state now fails this preflight instead of being
accepted as an upstream warning. Unit tests also reject linked components.

The full-model verifier accepts `--native-checkpoint` for a new-directory
save/reload probe. It reloads through the native loader and compares an
inference image in-process, then records auxiliary tensor shapes/equality and
anchor gradient eligibility. This is not an implemented resume contract: it
supplies the synthetic cloud for lifetime reconstruction, does not restore
optimizers, and does not enforce a fresh offline process. These limitations
are explicit in its report. Source inspection shows the native PLY omits
lifetimes, offsets and opacity; the training adapter must account for these
before resumption is accepted. The earlier claim that the loader disables
anchor gradients was incorrect: wrapping the tensor in `nn.Parameter` defaults
to `requires_grad=True`, as the runtime probe confirms.

The approved native probe passed with exactly equal inference images:
`.local/runs/atgs-native-reload-cuda-20260906.json`, with retained files in
`.local/runs/atgs-native-checkpoint-20260906/`. Offsets changed from `[64,10,3]`
to `[0]`, opacity from `[64,1]` to `[0]`, and lifetimes matched only through
the supplied initialization cloud. Optimizers were not restored. This is
positive inference evidence, not complete model-state resumption.

The optional `--restore-auxiliary` probe now saves plain model tensor attributes,
their Parameter/gradient flags, the time embedding and initialization scalars
in a weights-only-loadable supplemental file. It restores them before optimizer
construction to avoid stale parameter references. CPU tests check deep-copy
behavior, lifetime dtype, gradient flags, missing state, and restoration order.
The extended GPU probe is pending. Since no optimizer steps occur in these
smoke tests, their Adam state is empty; populated-state resumption, accumulated
gradients, sampler/RNG and fresh offline reload remain unverified.

The approved auxiliary retry passed:
`.local/runs/atgs-auxiliary-reload-cuda-20260906.json` and retained checkpoint
`.local/runs/atgs-auxiliary-checkpoint-20260906/`. Offsets, opacity and lifetime
tensors restored exactly, gradient flags passed, and inference image difference
remained zero. Native optimizers rebuilt/restored, with empty Adam state as
expected. This does not establish populated-moment or next-update equivalence.

The next probe adds `--populate-optimizer-state`: three synthetic Adam updates,
one per temporal encoder, using upstream learning-rate functions and gradient
clipping. These are small synthetic integration updates, not matched-scene
training or an implementation of its accumulation/warmup loop. Both restored
optimizer state dictionaries must match exactly, including moments, counters
and parameter-group settings. The auxiliary file is now included in the
checkpoint inventory and hashes. Populated-state GPU validation is pending.

The first approved populated-state run reached native reload but failed with
`_pickle.UnpicklingError`: NumPy scalar learning rates in the optimizer groups
are rejected by Torch's restricted loader (`numpy._core.multiarray.scalar`).
This was not a GPU permission failure. Its synthetic checkpoint is retained at
`.local/runs/atgs-adam-checkpoint-20260906/`; no passing JSON report was written.

`atgs-lr-python-float.patch` makes the scheduler return a builtin float, leaving
its numeric result unchanged. Restricted loading stays enabled; no pickle
allowlist or `weights_only=False` fallback is introduced. CPU regression tests
cover delayed/undelayed scheduler values and populated Adam serialization.
The retry uses a new checkpoint directory to preserve the failed-run evidence.

The patched retry passed on the RTX 4090:
`.local/runs/atgs-adam-reload-cuda-20260906.json`, with the successful checkpoint
in `.local/runs/atgs-adam-checkpoint-retry-20260906/`. After three synthetic
updates, both populated Adam state dictionaries restored exactly (moments,
step counters and parameter-group settings), auxiliary tensors matched, and
the reloaded inference image had zero maximum absolute difference. Synthetic
losses were 0.057536, 0.055714 and 0.052932; these are not scene quality metrics.
The measured section took 9.226 seconds with peak framework allocation of
8,732,693,504 bytes. All 57 unit tests pass. Neither the failed nor successful
synthetic check is a matched-scene training run.

Remaining resume gates: identical next-update behavior, saved gradients at
accumulation boundaries, warmup/update counters, RNG/sampler continuation,
constructor/config/source provenance and fresh-process offline reload. The
training adapter must satisfy these before any resumable scene run is claimed.

### Next-update probe preparation

The model verifier now accepts `--check-next-update` together with populated
optimizer-state validation. After exact checkpoint-state restoration it runs
the same synthetic fourth update on the original and restored models, comparing
pre-update loss, post-update parameters, optimizer state and inference images.
Nonfinite values or structural mismatches fail; finite numerical differences
are reported explicitly with an `exact` flag rather than assumed to be zero.
This test is in-process, uses a fixed camera and no stochastic sampler, and
does not establish the production training loop's accumulation or RNG contract.
GPU execution of the new probe remains pending.

The first GPU next-update probe completed:
`.local/runs/atgs-next-update-cuda-20260906.json`, with the saved pre-update
checkpoint at `.local/runs/atgs-next-update-checkpoint-20260906/`. Both
pre-update losses were `0.04807592183351517`. After the same fourth update,
the shared optimizer's maximum parameter difference was
`2.0801089704036713e-06` and its optimizer state was not exact; dynamic-encoder
parameters and optimizer state were exact. The post-update image difference
was `1.7881393432617188e-07`. Accordingly `next_update.exact` is **false**:
the top-level passed status denotes finite execution, not exact resumption.

The measured section took 10.751 seconds, with peak framework allocation
13,409,336,832 bytes. All 58 unit tests pass. The cause of these small
differences has not been established: a same-model repeated-backward control
and per-parameter-group diagnostics are needed before attributing them to
CUDA reduction variability. No scene training or fresh offline reload has run.

### Repeated-backward control

The expanded probe passed finite-execution checks on the RTX 4090:
`.local/runs/atgs-backward-control-cuda-20260906.json`, with retained checkpoint
`.local/runs/atgs-backward-control-checkpoint-20260906/`. Before the next-update
comparison, it runs two backward passes on the same model without optimizer
updates, restores Torch RNG state between passes, and checks that parameter
version counters did not change. Gradient snapshots are copied to CPU and
labelled by optimizer/group/parameter; missing-gradient mismatches fail.

The control losses were identical, but gradients were not: the largest
difference was `5.005858838558197e-09` in anchors, versus
`5.587935447692871e-09` for original-versus-restored gradients. Dynamic-encoder
gradients matched exactly in both comparisons. The largest next-update
parameter difference was `2.975575625896454e-06` in the covariance MLP;
image difference remained `1.7881393432617188e-07`. The native backward source
uses floating-point `atomicAdd` for color, projected means, covariance and
opacity gradients. The control demonstrates backward non-repeatability
independent of reload, consistent with reduction-order variability; it does
not isolate a single kernel or prove all resume state correct.

No renderer math or determinism settings were changed. Exact resumption is
still not claimed; the report preserves both control and reload differences.
Runtime was 13.966 seconds and peak allocated memory 13,409,336,832 bytes.
All 59 unit tests pass. Fresh-process offline reload and complete training-loop
state remain next implementation gates.
