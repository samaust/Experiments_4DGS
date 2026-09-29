# Plan049 correction001 — S1 backend deadline hook seam

This append-only implementation-scope correction is issued by Main under the user's CPU-only authorization to complete Plan031's current S1 blocker without operational time limits. Plan049 remains otherwise immutable. No runtime/model/device/production/ledger/scientific action is authorized.

## Finding

The implementer's source-only call-graph audit (implement-049-backend-scope-question-001.md) shows `stages._segment` enters frozen `backends.build_backend`; within it `AssetBundle`, `_build_native`, and `_grounding` perform S1 asset verification, settings/config reads, checkpoint selection/loading and then call opaque third-party/native model, SAM, AOT and tracker constructors. A single outer `operation()` gate cannot enforce the original S1 W/C checks around the backend's own nested reads. Global monkeypatching or copying scientific constructor logic would be unsafe and is not authorized.

## Authorized narrow correction

Authorize one S1-only deadline-hook seam in `scripts/vipe_benchmark/backends.py`, limited to the existing S1 call path through `AssetBundle`, `build_backend`, `_build_native`, `_grounding`, and the S1 tracker-construction handoff. Pass a local optional gate/callback from the already-authorized S1 stages path. When present, invoke it immediately before and after every S1-owned path resolution/stat/open/read/hash/JSON/config parse/checkpoint preparation operation and every opaque third-party/native constructor call. Opaque native/third-party work is one indivisible operation: the gate checks W/C immediately before entry and immediately after return; it makes no claim of preemption of internal C++ or library I/O while that call is executing. If the call returns at/after the deadline, no next S1 operation may begin.

The hook defaults to absent and is never selected by environment configuration. Every non-S1 caller follows the exact existing code path and retains its calculations, settings, assets, constructor order and outputs. Do not change scientific values, backend selection, model/config contents, pinned dependencies, asset bytes, generic read helpers, or non-S1 signatures/behavior. Do not import or run production models/devices to test the seam. Use existing synthetic CPU fixtures and injected constructor seams. Add no module, process, thread, observer, scenario or collected test method; preserve existing method/callback/declaration contracts except the already authorized D49-1 assertion correction.

Allowed changed-file list is amended by adding exactly `scripts/vipe_benchmark/backends.py`; no other Plan049 file lock changes. Record before/after bytes/hashes, full relevant call graph, per-interior-gate evidence, absence of non-S1 behavior changes, and exact synthetic test reachability. The independent validator must review this backend seam separately and may reject if the optional path alters non-S1 behavior or leaves owned interior operations ungated.

This correction authorizes an implementation seam only. It does not mark B1 met or permit skipping any deadline boundary, ownership, trace, complete aggregate, independent validation or B1–B4 acceptance requirement.
