# Selected-depth full-rig geometry worker (#34)

Implementation: `scripts/vipe_benchmark/final_render_geometry.py`.
The public seam is `run(request, arm, output, backend, observation_loader,
tracker=None, clock=time.monotonic)`. This is CPU qualification of computation
through fixture runtime boundaries. It rejects actual requests and backends lacking
`record_kind=fixture`; it loads no model, imports no Torch, consumes no admission
identity and changes no ledger. It does not qualify native model execution.

## Inputs and computation

The request is the exact extended Plan069 REVIEW request. Source RGB, S2, arm M/N,
D* decision/fit/check, scene, calibrated cameras and corrected-time training
exclusions retain their existing hash-bound contracts. Before creating output,
reject missing/duplicate sources, altered RGB/calibration, incomplete neighbors
and held-out membership. A diagnostic camera/keyframe subset cannot replace the
30-camera, nine-keyframe, three-neighbor rig: all 810 directed edges are computed.

The injected backend supplies `sample_thresh` and the existing diagnostic
`match`, `crop` and `triangulate` interfaces. Each returns its numeric outputs and
wall/CUDA measurement dictionary; fixture CUDA time must be zero. Crop records
retain the 255-instance cap, distinct source people and person-only semantic IDs.
`observation_loader(source, S2_row, M_row)` supplies exactly uint8 RGB, boolean
validity, int32 instances and boolean changing arrays on the accepted 960x540 grid.
Semantic metadata comes from the exact S2 row. These supplied arrays are explicitly
fixture data; a future actual loader must independently verify every source
artifact and runtime pin before native execution can be admitted.

The worker loads only the audited `balanced_samples`/`query_warp` function ASTs
and literal RoMa pin assignments from their source files. It executes no historical
module imports; this preserves those exact algorithms without importing Torch.
Complete source records identify the extracted code.

Keep person-cropped RoMa, balanced 5000-sample requests, seed0 and canonical
pair/reference/neighbor order. Record actual sample shortages; never fill them
with fabricated samples. Reuse the existing camera half-pixel conventions,
triangulation/evaluate_edge numerical, positive depth, two-pixel reprojection,
one-degree parallax, semantic support, three-camera foreground support and
pair-union static-clearance gates. The default tracker is unchanged OpenCV LK,
including forward/backward and same-view instance agreement. CPU fixtures may
inject analytically known endpoints at this system boundary.

Physical velocity is independently computed from supported world endpoints as
`(endpoint-start)/0.04seconds`, using the unchanged three-camera geometry gate.
Keep unsupported and static velocity zero. Publish world positions and physical
metres/second velocity, then derive normalized position with the full similarity
and normalized velocity with its linear map times two seconds. These records do
not establish cross-camera person identity.

## Publication and limits

Publish exclusive per-edge NPZ archives and one immutable geometry JSON accepted
by `final_render_initializer.assemble`. Each edge binds the exact eight S2 and
eight M source-row hashes for its participating cameras/pair, sampled/gated
counts, crops, LK support and physical velocity validity. Recipe provenance
retains current producer/sampling/gate/source hashes, the historical RoMa revision
and expected weight hashes. `native_model_verified=false` states that fixture
backends do not prove those native weights were loaded.

The `plan069-final-render-geometry-worker/v1` result binds its exact request, arm,
composition, prospective geometry allocation, output record and all 810 edges.
It reports CPU workers1, device bytes0 and measured fixture wall/storage totals;
`execution_authorized` and `native_adapter_qualified` remain false. No device or
native CPU-thread usage qualification is inferred from this fixture metadata.

An injected finite monotonic clock checks the unchanged 5400-second geometry
ceiling. Check cumulative artifact size before publishing each NPZ or geometry
JSON; never overwrite output or exceed the request storage limit. Resource and
backend errors retain existing artifacts and raise `GeometryFailure`, whose
`receipt` has a failed disposition, exact partial artifacts and resource values.
Its `result` binds an immutable failure JSON when remaining storage permits it;
otherwise it is `None` and the full receipt stays available in memory, avoiding
an extra write beyond the ceiling. Published-byte accounting includes this control
receipt. Host permission denials keep their original `PermissionError` class so
callers apply the repository permission rules. No complete result substitutes
for a failure.
The caller must supervise/terminate native subprocesses independently; checks
between operations cannot interrupt a hung model operation.

## Remaining actual gates

Actual package-bound eligible metric D*, exact verified RGB/mask/motion loading,
native RoMa/runtime/license/source qualification, resource viability, supervised
worker termination, current DO admission and single-GPU ledger coordination are
still required. This worker alone grants none of those authorities. Actual native
training/reload/final renders and human M/N feedback remain separate #34/#35
acceptance requirements. Historical Plan027 validators and consumed artifacts
are unchanged.
