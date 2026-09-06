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
