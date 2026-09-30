# QF pure initializer assembly

Implementation: `scripts/vipe_benchmark/final_render_initializer.py`.
This implements the CPU geometry-to-native-array seam in
[proposal001](qualitative-final-render-review-proposal-001.md); it does not implement
native geometry, training, rendering, job registration or execution authority.

## Worker boundary

`assemble(request, arm, geometry_record, width_record)` returns `(arrays, receipt)`
without creating an output directory, publishing media or changing the ledger.
The request is the prospective QF REVIEW contract. A separately authorized caller
must own any eventual CPU allocation, deadlines, storage, publication and cleanup.
Fixture geometry stays labeled fixture. A successful CPU assembly always reports
`execution_authorized: false` and `native_adapter_qualified: false`; it cannot
establish successful native geometry or final-render qualification.

The new geometry schema is `plan067-final-render-geometry/v1` with exact request
hash, QF arm/composition, record kind, scene record and prerequisite records.
It contains 810 distinct ordered edges: nine keyframes, 30 training reference
cameras and three selected neighbors each. An old diagnostic subset is rejected,
including one wrapped in the new schema with incomplete coverage. Each edge binds
its NPZ and exact segmentation/motion source-row hashes for both pair frames in
all four participating cameras. Accepted RGB hashes, grid, intrinsics, manifest
camera calibration and native result identities must agree. Actual inputs also
verify their referenced RGB/mask/motion/valid artifact records.

## Scene, time and native arrays

The bound scene retains D4 passing fit/check records and the exact physical scale.
Its full 4×4 normalization supports rotation and must be a finite affine positive
isotropic similarity. Camera intrinsics add/remove the half pixel exactly once;
rotations remain unchanged and translations/centers scale together. Source and
normalized coordinate arrays must agree under that matrix.
Before deriving that geometry, the historical reference's declared scale must
equal the verified freeze's scale, and its complete normalization must equal the
verified normalization source's payload, including `scene_scale`. Fixture inputs
also supply these source records; consistent rewrites of the reference, scene and
voxel basis cannot alter their retained source bytes.

The accepted manifest must retain 34 cameras, original 25 fps, frames0–49, held-out
cameras0/10/20/30, and the union of corrected-time exclusions. Recompute the union
with the existing `sync_timing` functions and reject missing/unavailable pair keys.
Actual assembly first pins the accepted processed manifest's exact path, hash and
size through the same binding validator used by REVIEW admission. A substituted
comparison timing union is rejected even when its exclusions are recomputed.
Fixture records retain flexible manifest bindings and confer no execution authority.
`frame/50` is accepted only with zero offsets, origin0 and duration2seconds; other
manifest times require a new explicit contract, not implicit conversion.

Future geometry NPZs contain the audited native arrays plus `world_positions`,
`world_velocities` and ordered `camera_ids`. Validate
`positions = world_positions @ A.T + translation` and
`velocities = world_velocities @ A.T * 2seconds`. The latter binds metres/second
to normalized scene units per normalized time, including non-axis-aligned rotation.
Static and unmeasured velocities must be zero. Preserve duration0.2, semantic
regions and view-local identity limitations. Existing diagnostic NPZs lacking
physical velocity evidence cannot be silently relabeled as this future input.

## Shared voxel basis and audited fusion

The request's initializer contract additionally binds `voxel_basis` (NPZ record)
and `voxel_basis_source` (archive and original static-initialization receipt
records). The width record has schema `plan067-final-render-voxel-width/v1`, exact
request/scene/source/basis lineage, and the historical half-median-positive-nearest-
neighbor rule. Its static-prior origin must bind the accepted scene manifest,
freeze and exact source archive. Derive normalized positions from source-scale
physical prior points through target scale and the bound matrix, apply the
historical five-times-scene-scale cutoff, and verify the supplied normalized basis.
Recompute its width with `basketball_dense_fusion.voxel_width`; a caller-authored
width or different prior cannot substitute silently. The one request binds a
common basis across all five arms.

Reuse unchanged `basketball_dense_fusion.fuse` and `validate`: fuse static positions
and colors by deterministic voxel medians, create nine static time copies, and
retain every foreground observation with its measured velocity. Return physical
static IDs and foreground observation IDs. The receipt retains source edge offsets,
counts, matrix/units, exact array hash and static mapping hash. Its nested
`initializer_receipt` is accepted by the existing QF `validate_initializer` seam
and binds the complete initializer contract and prerequisite records. It invents no
cross-camera identities, foreground velocity or quality judgment.

## Readiness and validation

Real full-rig QF geometry and its physical-velocity/basis-origin receipts are not
available. The geometry generator must produce and independently qualify those
records; checked native runtime, storage/memory viability, finite supervised
allocation/DO authority and final human comparison remain open. CPU assembly
fixtures are not those missing native results. Historical validators, packages,
scientific records and consumed identities are unchanged.

CPU fixtures exercise full 810-edge assembly with rotated points/nonzero velocities,
static fusion and preserved foreground; missing/duplicate/held-out edges, altered
source identities/neighbors, wrong physical normalization/velocity/time/camera,
manifest exclusions/offsets and fixture/provenance/voxel substitution are rejected.
No model, CUDA import, GPU operation, runtime setup or live ledger write is used.

Focused qualification: ten adapter CPU fixtures and twelve contract fixtures
passed together (22 tests) with the explicit root `stg-colmap`
virtual-environment interpreter. The public actual-assembly regression first reached
later scene checks instead of rejecting a consistently rewritten manifest; the
shared binding gate now rejects it before geometry validation. Scene normalization
reuses the contract's similarity validator and tolerance. Historical-reference
regressions first assembled rewritten scale/transform/basis and scene-scale
declarations with original source records; both now fail the source-content gate.
AST parsing and diff
checks supplement the tests. No configured static typechecker
or native/GPU qualification is claimed.
