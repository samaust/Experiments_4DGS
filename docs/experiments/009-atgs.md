# Experiment 009: ATGS

Status: **SelfCap training stopped cleanly at its budget reserve at 61,008
microsteps; native 100,000-microstep schedule unfinished. Final evaluation complete.
Basketball remains blocked on synchronization.**

## Current Basketball continuation — 2026-09-07

[Plan 009](basketball-shared-timing-v3.md) repairs the independent solver's
previous evaluation-cap failures, but timing remains blocked: the exact noiseless
control has only 11/12 complete ascending and 10/12 complete descending data-only
group profiles because some fits converge with negative depth. The best-of-three
estimate recovers −0.10 frames but cannot qualify without both sweep directions.
No real fitting, selection reevaluation, final validation or Basketball training
was performed. The unchanged 1,890 production controls and Plan 008 admission
were hash-verified; all six real configurations remain unassessed.

[Plan 008](basketball-shared-timing-v2.md) resolves the multiview admission
failure: all 72 edges pass with 667 whole groups per half and at least 19 groups
per edge per half. Timing remains blocked at independent synthetic validation:
71/612 data-only nuisance fits hit the 200-evaluation cap on a noiseless
100-frame direction-change control, leaving 0/12 complete group profiles.
The spline optimizer and evaluator are implemented; no real offsets were fitted
or selection reevaluated. Final frames 200–249 and Basketball training remain
untouched.

The earlier [Plan 007 shared-trajectory investigation](basketball-shared-timing-v1.md)
recorded an admission blocker for the revised method: 16/72 fixed edges lack
12 multiview groups in both deterministic halves. The estimator audit and
all-camera native fitting extraction are complete; spline fitting and selection
reevaluation did not start. The previous failed selection remains evidence.
Final frames 200–249 and all Basketball training allocations remain untouched.

[Plan 006](basketball-calibration-alternatives.md) accepted all 34 static cameras;
[revision 2](basketball-rev2.md) verified provenance/conventions and passed the
training-view estimated scale check (1.31506947 estimated metres per calibration
unit, 3.13% reserved disagreement).
[Fine native fitting](basketball-cycle-refinement.md) yields a qualified 72-edge,
bridge-free graph covering all 34 cameras at the unchanged 0.25-frame cycle gate.
[Separately frozen timing selection](basketball-timing-selection.md) then passes
only 36/72 connections on frames 150–199; the passing graph is disconnected.
Uncertainty/ambiguity and temporal-half checks block acceptance. No final timing
validation,
1,700-image preparation, Gaussian initialization or Basketball training/evaluation
was launched. Held-outs remain 0, 10, 20, 30, with 30 training cameras. The
original per-method two-hour Basketball allocation is unchanged and uncharged.

## Prior implementation and experiment evidence


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

### Offline inference gate preparation

`verify-atgs-offline.py` now supports independent process reload from the saved
synthetic checkpoint. It validates all model/optimizer/auxiliary component
hashes against the recorded evidence, installs the existing seccomp guard
before Torch import, and obtains lifetime data from the auxiliary file rather
than external initialization geometry. Three float-image hashes are recorded;
a second independent invocation can require identical hashes and matching
checkpoint/source metadata. CPU tests reject changed or incomplete inventories.
GPU/offline execution is pending; this does not implement training-loop resume.

Both approved offline invocations subsequently passed on the RTX 4090:
`.local/runs/atgs-offline-a-20260906.json` (PID 376034) and
`.local/runs/atgs-offline-b-20260906.json` (PID 376215). All three float32
64×64 image hashes matched exactly; the second report has `reference_exact=true`.
The network guard's IPv4/IPv6 denial self-tests and Unix IPC check passed.
Neither process needed the original initialization cloud: lifetimes came from
the hash-verified auxiliary checkpoint file. This establishes independent
offline inference repeatability, not equality to an image saved by the original
training process, nor optimizer/sampler continuation.

### RNG state preparation

`scripts/training_rng.py` adds weights-only-loadable Python, NumPy and Torch
RNG snapshots. NumPy keys are encoded as integer tensors, preserving its cached
Gaussian value. CUDA capture/restore is explicit and fails if GPU access or
the saved device count does not match; CPU-only restore rejects saved CUDA
state rather than silently dropping it. State validation precedes global RNG
restoration. CPU regression tests reproduce all three CPU streams after a
Torch serialization round trip and reject malformed state. CUDA RNG behavior
and integration into ATGS sampler/accumulation checkpoints remain pending.

`verify-training-rng.py` now exercises a weights-only serialization round trip
for all four RNG families, including every visible CUDA generator. It compares
samples exactly after deliberately advancing the streams. GPU execution of
this verifier remains pending.

The training-loop audit identifies additional adapter requirements:

- `EncoderBalancedSampler` derives buckets from raw frame index, not corrected
  per-camera timestamps. Manifest adaptation must bucket by the actual encoder
  routing time, preserving explicit train-only membership.
- `train_long.py` forces balanced accumulation on. With three active encoders,
  completion requires visits to all three; the nominal eight-step config is
  not the effective update rule. Shared gradients divide by microstep count;
  routed gradients divide by per-encoder visits.
- Warmup depends on optimizer-update count, and save/test/densification
  boundaries can force a partial update and sampler restart. A resumable
  adapter must record update count/iteration and the chosen boundary behavior.
- Upstream uses a 16-worker prefetched DataLoader. Saving only generator state
  does not recover the consumed sample position: checkpointable sampling needs
  bucket permutations, consumption cursor, encoder order and sampler RNG state.

These findings are implementation requirements, not a claim that sampler or
accumulation resumption is already implemented.

The approved RNG GPU retry passed exactly on the RTX 4090:
`.local/runs/training-rng-cuda-20260906.json`. Python, NumPy (including its
cached Gaussian), Torch CPU and every visible Torch CUDA stream reproduced
the expected samples after weights-only serialization and stream advancement.

### Checkpointable corrected-time sampler

`scripts/atgs_sampler.py` implements synchronous encoder-balanced sampling over
the shared manifest's training keys. Buckets use corrected normalized times,
not source frame numbers. Each logical batch visits every encoder once in
random order; smaller shuffled buckets cycle as in upstream. Sampling uses a
dedicated CPU generator and eagerly records the epoch order, an explicit local
adaptation that preserves the sampling policy but not upstream's global-RNG
draw timing. No held-out view is admitted.

The saved state contains manifest/routing identity, epoch order, cursor, epoch
number and generator state. Tests verify weights-only round trips mid-batch
and across epochs, global RNG isolation, and rejection of held-out membership,
empty buckets, invalid cursors, changed identities and unbalanced saved batches.
All 66 unit tests pass.

On the actual processed SelfCap manifest, corrected-time bucket sizes are
`[469, 467, 444]`; cycling yields 1,407 samples per epoch from 1,380 training
views. Restoring after 17 samples reproduced the next 3,000 keys exactly,
including epoch transitions, with camera 0015 excluded throughout. Routing
identity: `2548f4210b39a9465b82f7c79fcf3c9277ae5360ccd5aabcee83859eb787a689`.
This sampler must be consumed synchronously without worker prefetch; checkpoint
the cursor together with model/accumulation state after the corresponding
microstep completes. It is not yet wired into the ATGS training adapter.

### Combined loop-state component

`scripts/atgs_loop_state.py` now captures sampler state, Python/NumPy/Torch RNG,
unaveraged pending gradients, per-encoder visit counts, completed iteration,
optimizer-update count/iteration and EMA loss in one weights-only-loadable
supplement. Gradients are labelled by optimizer/group/parameter and retain
`None` for unused parameters. Restore validates parameter topology and gradient
shape/dtype/finiteness, prepares a validated sampler copy, restores RNG, then
attaches gradients to the already restored model/optimizer parameters.

Checkpoint calls must occur after a complete microstep, before averaging or
stepping; an update-boundary snapshot instead requires cleared gradients and
zero pending visits. Restore must run after native and auxiliary model state
and both optimizer states are loaded, since upstream training setup clears
gradients. No standalone model checkpoint or file-commit transaction is supplied
by this component.

CPU tests serialize a checkpoint halfway through a two-microstep toy update,
restore into new parameters/optimizers, and reproduce the next sampled key,
Python/NumPy/Torch-generated target and final parameter values exactly. Tests
also reject inconsistent visit counts, changed topology and uncleared boundary
gradients. All 68 tests pass. This demonstrates the combined component on a
CPU fixture, not actual ATGS partial-accumulation resume; training-loop wiring,
GPU validation and model/loop bundle provenance remain pending.

### Native GPU partial-accumulation probe

`scripts/verify-atgs-accumulation.py` now exercises the combined loop-state
component with the actual native model and both optimizers. It uses the
hash-verified three-update synthetic checkpoint, saves pending gradients after
one microstep, and compares uninterrupted completion with a newly loaded model
that restores the supplement before consuming the remaining two encoder views.
The supplement is serialized through a weights-only Torch round trip in memory.

The upstream averaging, clipping, warmup and stepping helpers are extracted by
`scripts/atgs_update.py` without importing the full training module (and its
LPIPS initialization). Their AST SHA-256 is
`1b5c9b2b79dc0b955be6de8826b7fc4a931b11b23b22e5a275bf4a0135fcc5e4`.
A CPU test checks averaging divisors, warmup, restored learning rates and
cleared gradients. The suite passes all 69 tests.

GPU evidence: `.local/runs/atgs-accumulation-cuda-20260906.json`, RTX 4090.
The resumed sample keys, random targets, losses, gradient norms, warmup factor
(`0.10360000000000001`) and final loop state matched exactly. Both paths reached
iteration 6, update count 4, with no pending gradients/encoder visits after the
update. Maximum parameter difference was `2.176966518163681e-08` (covariance
MLP); dynamic optimizer parameters matched exactly. The report passes finite
execution but explicitly records `parameters_exact: false`.

This is a same-process synthetic test, not a bit-exact guarantee, fresh-process
training resume, atomic model/loop bundle, or SelfCap training. Production loop
wiring, checkpoint provenance and deadline integration remain pending.

### Commit-marked model/loop bundle component

`scripts/atgs_bundle.py` now writes all eleven native/optimizer/auxiliary/loop
components together, with SHA-256 inventories and explicit manifest, source,
resolved-configuration and helper-AST provenance. It reserves a new directory,
syncs the component files and publishes a completion marker last. Failed writes
leave diagnostic directories without an accepted marker; existing checkpoints
are never overwritten. Readers verify provenance and every component before
weights-only loading supplements, and cross-check iteration/update counters.

Four CPU fixture tests cover successful publication and loading, interrupted
writes, overwrite refusal, wrong provenance, corrupt bytes, mismatched counters
and linked checkpoint directories. This adds a checkpoint transaction component,
not a native GPU bundle-resume result or production training adapter. The caller
must pause training throughout capture and restore model/auxiliary state before
optimizers, followed by the loop supplement. GPU round-trip, fresh-process
training resumption and deadline integration remain pending.

### Native GPU on-disk bundle round trip

The accumulation verifier now accepts `--bundle` to save after the first
microstep and load all native model, optimizer and supplemental files from that
new bundle. Without the flag, the earlier in-memory supplement mode remains
available. Bundle provenance hashes the synthetic camera/time fixture and
resolved argparse configuration; it is not SelfCap provenance.

The RTX 4090 run passed:
`.local/runs/atgs-bundle-cuda-20260906.json`, with checkpoint directory
`.local/runs/atgs-accumulation-bundle-20260906`. Its eleven components include
a 791,606,203-byte loop supplement containing pending gradients. The checkpoint
captures iteration 4 / update count 3; both continuations finish at iteration 6
/ update count 4. Sample keys, random targets, losses, gradient norms, warmup
and final loop state matched exactly. Maximum parameter difference was
`6.332993507385254e-08` in the covariance MLP; dynamic parameters matched
exactly. The report explicitly records non-exact parameter equality.

All 73 unit tests pass, syntax compilation and diff checks pass. This establishes
a native same-process bundle round trip, not fresh-process or offline training
resumption. Production scene training and deadline integration remain pending.

### Fresh-process offline accumulation resume

The verifier's `--resume-bundle` mode installs the seccomp network guard before
Torch import, loads the bundle without the original checkpoint/initialization
files, restores optimizer/gradient/RNG/sampler state, and completes the pending
synthetic update. `--reference` requires matching successful bundle evidence.
Sample keys, targets, discrete loop counters and warmup must match; numerical
loss differences and parameter hashes are reported independently.

Two RTX 4090 processes passed with intentional offline socket-denial self-tests:

- `.local/runs/atgs-resume-offline-a-20260906.json`, PID 398018, compared with
  the original on-disk bundle probe.
- `.local/runs/atgs-resume-offline-b-20260906.json`, PID 398391, compared with
  the first fresh-process run.

Both loss differences were zero in both comparisons. Both processes reached
iteration 6 / update count 4 with zero pending microsteps. The first reference
had no parameter hashes (`reference_parameters_exact: null`). Between the two
fresh processes, parameter hashes were not identical
(`reference_parameters_exact: false`); dynamic-parameter hashes matched. Hashes
do not quantify the numerical differences, and these results do not establish
bit-exact training resumption.

Two regression tests cover JSON key normalization, numerical loss reporting,
and rejection of changed sample sequences/counters. All 75 tests pass; syntax
and diff checks pass. Production scene training, full source/patch provenance
coverage and deadline integration remain pending.

### Deadline-aware loop control component

`scripts/atgs_train_control.py` adds synchronous callback-based control for
microsteps, encoder-balanced updates and periodic/final/deadline bundle saves.
It preserves pending unaveraged gradients when stopping for checkpoint time,
checks remaining time before starting another microstep, and reports exhausted
budgets before or during checkpoint I/O. Failed microsteps/updates propagate
without saving partially executed work. The caller remains responsible for a
durable budget reservation and external hard-deadline enforcement.

Five CPU fixture tests exercise balanced updates, periodic partial snapshots,
deadline continuation without an extra update, callback failure, exhausted
budgets and checkpoint overrun. This component is not yet connected to native
scene losses, densification or special-boundary update flushing. Checkpoint and
step reserves require measurement before production use; no ATGS scene training
or training-budget charge was performed for these CPU tests.

The controller now also implements full-schedule-end flushing and explicit
native special-update boundaries, with balanced-sampler restart after a forced
partial update. A post-microstep callback runs after optimizer stepping and
restart, before any checkpoint, to support densification/buffer cleanup in native
order. Extra deadline/periodic bundle saves still preserve partial accumulation.
Three additional CPU tests cover final partial flushing, callback/restart order
and post-update callback failure. Native scene callbacks remain the next gate.

### Native loss and statistics callbacks

`atgs_native_step.NativeTrainingStep` supplies hash/3DGS forward/backward with
the upstream weighted L1/SSIM loss plus 0.01 scaling-volume regularization,
gradient sanitization, statistics, post-update densification and buffer cleanup.
L1/SSIM helpers are AST-extracted without the unused module-level CUDA MS-SSIM
allocation. Three CPU tests cover loss composition and callback guards; the
suite passes 86 tests.

Audit correction: the selected config has `start_stat=150000000`,
`update_from=1600`, `update_until=30000`, `iterations=100000`. Consequently
statistics and densification never activate under these defaults. Preserve this
configuration for production; do not silently turn growth on. The first probe
`.local/runs/atgs-native-step-cuda-20260906.json` passed native loss evaluation
but did **not** exercise active statistics despite its intended purpose.

The corrected synthetic probe explicitly sets a copied `start_stat=0` and
allocates diagnostic statistics buffers matching native fine-setup shapes.
The first corrected attempt exposed empty CPU buffers left by normal setup
(tensor-device mismatch, not a sandbox denial); the diagnostic-only allocation
resolved that failure. No production configuration was changed.

`.local/runs/atgs-native-statistics-cuda-20260906.json` passes on the RTX 4090
at iteration 1 for three synthetic timestamps, with active statistics, 21 finite
gradient tensors per view, and exactly matching training/evaluation renders.
Loss is approximately 0.3715705; peak allocated memory is 3,565,699,584 bytes.
No optimizer updates, real scene training or actual anchor growth were performed.
Loss-helper AST SHA-256:
`faafee3fdcf5a90065fbda709a99e27da182dbb21b7ee856f4e127f41c27a476`.

### Executable SelfCap training integration

`train-atgs-manifest.py` now wires the native callbacks, synchronous controller,
manifest sampler and commit-marked bundles into the shared budget ledger and
external deadline supervisor. Integration-step limits pause rather than shorten
the optimization schedule. Initial geometry uses the existing training-only
midpoint PLY with native always-active initial-anchor lifetime markers. New
initialization validation matches the manifest, exact training split and image
hashes; it passed on the actual SelfCap initialization (PLY SHA-256
`13f1131ccca5f91868999deac74ff8fce1b98661ddf79085ce136c6808222d09`).

All 88 CPU tests pass, with syntax and diff checks clean. The executable's GPU
scene integration remains pending; no ATGS scene result is claimed. Native
binary provenance, device-wide sampling and held-out evaluation integration
remain required for final experiment evidence.

### SelfCap scene training and partial resume executed

Three budget-counted RTX 4090 attempts passed with 5,077 training-only initial
anchors at the unchanged shared image resolution:

| Run directory under `.local/runs/` | Final iteration | Pending microsteps | Optimizer updates | Charged seconds |
| --- | ---: | ---: | ---: | ---: |
| `atgs-selfcap-integration-20260906` | 3 | 0 | 1 | 9.369208 |
| `atgs-selfcap-partial-20260906` | 4 | 1 | 1 | 13.777042 |
| `atgs-selfcap-resumed-20260906` | 6 | 0 | 2 | 13.430548 |

Each later process restored the preceding committed bundle. The last process
resumed the pending gradient/encoder state and completed the second update.
These are successful continuation checks, not uninterrupted-vs-resumed numerical
comparisons on the real scene. Total charged time is 36.576797 seconds of the
7,200-second ATGS/SelfCap allocation. The full 100,000-step schedule remains
unchanged; `--max-steps` only paused each attempt.

Checkpoint writes took 5.999, 7.191 and 5.673 seconds. Maximum reported allocated
memory across these attempts was 6,355,890,688 bytes; reserved memory peaked at
7,637,827,584 bytes. These are Torch allocator measurements, not device-wide
sampled peaks. The final bundle is
`.local/runs/atgs-selfcap-resumed-20260906/checkpoint-000006-000`.
No final quality, throughput or matched-budget ranking is claimed.

### Iteration-6 offline rendering and evidence

`render-atgs-manifest.py` rendered the final integration bundle in two independent
network-disabled processes. All 60 held-out frames and 20 sweep poses match in
both PNG bytes and raw floating-point image hashes. Bundle component bytes total
3,904,978,683. Evidence directories/reports under `.local/runs/`:

- `atgs-selfcap-render-a-20260906` and `atgs-selfcap-render-b-20260906`;
- `atgs-selfcap-reload-frames-20260906.json` and
  `atgs-selfcap-reload-sweep-20260906.json` (all 80 PNGs byte-exact);
- `atgs-selfcap-metrics-20260906.json` (60 held-out frames);
- `atgs-selfcap-evidence-20260906` (videos, sheets and fixed GT-selected crops).

Shared metrics: PSNR **12.735074 dB**, SSIM **0.588788**, LPIPS-Alex **0.818783**.
Ten warmups plus 100 timed renders measured **311.553 FPS**. Inspection of the
start/middle/end prediction contact sheet shows essentially uniform gray images,
with no discernible scene or person detail. This two-update checkpoint is an
integration result, not usable reconstruction quality; its near-blank rendering
speed is not representative of a trained scene. Do not rank it against the
5,000-step STG baselines. Scene training must continue within the existing budget.

The renderer passed syntax checks; the existing 88-test suite passes. Rendering,
CPU metrics and packaging were not charged as training. Device-wide sampled
resource measurement and native binary provenance remain outstanding gates.

### Iteration-1,000 measured continuation

Using the absolute STG interpreter path allowed the measurement wrapper and its
GPU sampler to run on the host. The failed relative-path measurement remains
preserved; it stopped before launching training and charged no training time.
The successful run is `.local/runs/atgs-selfcap-1000-measurement-retry-20260906`.

Training resumed iteration 6 and reached iteration 1,000 / update count 333,
preserving one pending microstep in
`.local/runs/atgs-selfcap-1000-20260906/checkpoint-001000-001`. The ledger charged
140.155569 seconds, totaling **176.732366 seconds** for ATGS/SelfCap so far.
Measured command wall time was 140.269063 seconds. Device-wide 200 ms sampling
recorded an 849–854 MiB baseline and **8,763 MiB peak** (711 samples).
Torch peak allocated/reserved memory was 6,355,923,968 / 7,646,216,192 bytes.
Periodic and pause snapshots coincided at iteration 1,000, producing two
equivalent boundary saves (6.625 and 6.826 seconds); both costs were charged.
The controller's duplicate-save avoidance does not currently cover this pause
case. No checkpoint files were deleted.

Offline outputs under `.local/runs/atgs-selfcap-1000-render-{a,b}-20260906`
match exactly for all 60 held-out frames and 20 sweep poses, both PNG bytes and
raw float hashes. Both current-runtime extension inventories match. The complete
bundle contains 4,698,024,951 component bytes, including pending gradients.
Reports are `atgs-selfcap-1000-reload-{frames,sweep}-20260906.json`;
fixed crops, videos and sheets are in `atgs-selfcap-1000-evidence-20260906`.

`atgs-selfcap-1000-metrics-20260906.json` measures PSNR **17.396115 dB**,
SSIM **0.678128**, LPIPS-Alex **0.617919** across 60 held-out images. Warm rendering
measured **326.448 FPS**. Inspection of frame 4150 now shows shelves and objects,
but with severe smoothing, distorted edges and no clearly reconstructed moving
person. This is an unfinished intermediate result, not a matched-budget ranking.
The current runtime records extension hashes and package versions, but does not
retroactively certify training binaries or all dynamically loaded system libraries.

### Iteration-5,000 evaluation and baseline comparison

The measured continuation `.local/runs/atgs-selfcap-5000-measurement-20260906`
completed 4,000 further microsteps in 500.058923 seconds. The ledger charged
499.921410 seconds, for **676.653776 seconds total** of the 7,200-second scene
allocation. Device-wide sampling recorded an 837 MiB baseline and 9,010 MiB peak.
Torch allocated/reserved peaks were 6,355,966,464 / 7,671,382,016 bytes.
The final bundle is
`.local/runs/atgs-selfcap-5000-20260906/checkpoint-005000-004`: 1,666 optimizer
updates completed, with two pending microsteps. Full native schedule: 100,000
microsteps; no growth was enabled. Equal iteration counts across methods do not
imply equal optimizer-update counts or charged time.

`evaluate-atgs-checkpoint.py` completed both offline reloads, all comparisons,
shared metrics and fixed-crop/video packaging in 170.957888 seconds under
`.local/runs/atgs-selfcap-5000-evaluation-20260906`. All 80 PNG and raw-float hashes
match exactly; native extension/runtime and bundle inventories also match.
Bundle component size is 4,951,878,833 bytes.

| Measurement | ATGS at 5,000 | Difference from Lite at 5,000 | Difference from Full at 5,000 |
| --- | ---: | ---: | ---: |
| PSNR dB | 21.637782 | -0.444821 | -1.815171 |
| SSIM | 0.802142 | -0.024997 | -0.030719 |
| LPIPS-Alex | 0.341477 | +0.071270 | +0.062324 |

Warm rendering is 281.242 FPS. Checked per-frame/aggregate comparisons are
`.local/runs/atgs-vs-lite-selfcap-5000-20260906.json` and
`.local/runs/atgs-vs-full-selfcap-5000-20260906.json`. The comparison helper now
supports ATGS bundle/runtime metadata alongside STG file checkpoints.

Frame 4150 shows a reconstructed person, unlike the near-empty early output,
but face, hair, arms and body boundaries remain heavily blurred. Bookshelf
structure is more recognizable than at iteration 1,000, with persistent smeared
book spines and doubled/soft shelf edges. No final quality winner is established;
all three runs remain unfinished and well below their allocated limits.

All 92 tests pass, including evaluation launch-failure handling, retained virtualenv
interpreter paths, runtime/hash mismatches and ATGS-vs-STG comparison validation.

### Final budget-limited SelfCap continuation

The continuation from 5,000 microsteps stopped with reason `deadline` at
**61,008 / 100,000 microsteps**, with **20,336 optimizer updates** and no pending
microsteps. Its resumed partial accumulation was preserved; the final boundary
naturally completed an update rather than flushing a partial batch. All 56,008
new logged microsteps were consecutive and had finite loss. Native no-growth
settings were unchanged. Periodic bundles were spaced every 5,000 microsteps
to reduce disk use, without changing optimization.

| Measurement | Result |
| --- | ---: |
| Continuation command wall | 6,349.703736 s |
| Total charged training, including earlier attempts | 7,026.233249 s / 7,200 s |
| Device baseline / sampled peak | 792 / 8,633 MiB |
| Framework peak allocated / reserved | 6,356,892,160 / 7,711,227,904 bytes |
| Final bundle save wall | 5.471593 s |

There was no forced kill or budget overrun. The remaining 173.766751 seconds
are below the trainer's restart/reserve requirement, not an additional segment.
Training and measurement directories are
`.local/runs/atgs-selfcap-final-20260906` and
`.local/runs/atgs-selfcap-final-measurement-20260906`.
The final bundle is `checkpoint-061008-011`; its commit marker `bundle.json`
SHA-256 is `7e4d1157c133e7ec57b53aeeb11ef4b66c7cd38aec82ed956021941a39e3f621`.
That marker inventories component hashes; it is not the hash of one model file.
See [the training guide](../local-creation.md) for the exact continuation command.
This is final-budget evidence, not native-schedule completion or full-paper convergence.

The complete final bundle contains **3,904,977,664 component bytes**. Its smaller
size than the 5,000-microstep bundle reflects the absence of pending accumulated
gradients at this boundary, not a compressed or incomplete inference model.
Evaluation is in `.local/runs/atgs-selfcap-final-evaluation-20260906`:

| Measurement | ATGS final | Difference from final Lite | Difference from final Full |
| --- | ---: | ---: | ---: |
| PSNR dB | 22.180802 | -0.237948 | -2.315951 |
| SSIM | 0.842141 | -0.009063 | -0.022072 |
| LPIPS-Alex | 0.239707 | +0.020344 | +0.025096 |

Warm rendering measured **256.625 FPS** with 10 warmups and 100 synchronized
renders. Evaluation wall time was **169.002520 seconds**, separate from training.
Both fresh network-disabled reloads matched exactly for all 60 held-out frames
and 20 sweep poses in PNG bytes and raw-float hashes, with matching runtime and
bundle inventories. Checked comparisons are
`.local/runs/atgs-vs-lite-selfcap-final-20260906.json` and
`.local/runs/atgs-vs-full-selfcap-final-20260906.json`.

Inspected start/middle/end prediction and ground-truth sheets, the fixed
hands/body-boundary and book-text crops, and sweep poses 0, 10 and 19 under
`evidence/`. Frame 4120 has severe face, torso and leg smearing/ghosting; frame
4150 has strong head/hair and arm blur beyond the source motion blur. The slower
4179 face is recognizable, but hair, shoulder and hands remain soft/distorted.
Static book spines are considerably clearer than in the pilot, with some larger
lettering legible, while shelf edges and the left plant retain blur. The sampled
views do not establish the absence of floaters elsewhere. Frozen-time sweeps
retain the foreground blur, with no matched ground truth. Adjacent-difference
statistics and sampled sheets do not isolate flicker from actual motion.

**Defer as an artifact-quality upgrade for this tested profile**: the completed
budget run improves on the pilot but does not resolve foreground ghosting or
beat either final STG baseline's aggregate metrics. This is a qualified local
result with native no-growth settings and an unfinished schedule, not a general
claim about ATGS or permission to extend the training budget.

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
