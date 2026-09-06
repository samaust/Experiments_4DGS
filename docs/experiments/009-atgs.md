# Experiment 009: ATGS

Status: **source audited; native environment and matched-scene adapter pending**.

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
