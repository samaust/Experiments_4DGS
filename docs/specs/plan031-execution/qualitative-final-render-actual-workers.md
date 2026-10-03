# Guarded native final-render stage workers (#34)

The actual entry is the exact pinned interpreter followed by
`scripts/final-render-actual-worker.py --invocation PATH --release-file PATH`.
The wrapper binds numerical CPU thread defaults before importing NumPy. It waits at most 30 seconds for the
parent's exact `plan069-final-render-actual-release/v1` record binding that
immutable invocation. Before constructing a model, `execute(invocation_record)`
requires actual request/record kinds and `worker_binding`: qualified DO evidence,
exact reserved allocation, registered child PID/process group, bound argv,
interpreter and control source hashes. Fixture labels cannot grant this authority.

Factories are fixed: `NativeGeometryBackend` for geometry and
`NativeFreeTimeRuntime` for training/render. No injected runtime, observation
loader, matcher, clock or caller-supplied guard is accepted on the actual path.
The dispatcher owns ledger mutations, external deadlines, peak monitoring and
confirmation that the entire process group has been cleaned up.

## Stage contracts

Every invocation binds `request`, `arm`, `phase`, `parent_result`, `output`, and
`initializer` (null for geometry and initializer). Initializer also binds an exact
`voxel_width` file record; its accepted basis/source rule remains unchanged.
Geometry uses the envelope's qualified matcher runtime. Native checkout derives
from the request's exact preset file, and the constructor checks its inventory.

- Geometry executes all 810 edges, closes its native matcher, and publishes the
  immutable geometry and archive artifacts.
- Initializer validates the completed actual geometry, calls the real full-rig
  assembly and native-input conversion, and publishes `initializer.npz`,
  `assembly.json`, `native-input.json`, and `initializer.json`. Prepared arrays
  and assembly receipts remain nonauthorizing; their actual worker result binds
  the separately authorized invocation.
- Train performs exactly 5,000 sequential native updates and saves
  `checkpoint-005000.pt` with exact request/arm/initializer provenance.
- Render constructs a fresh native runtime, restores the entire checkpoint
  state, saves the restored snapshot and reload evidence, then publishes 200
  distinct lossless RGB PNGs on the frozen held-out camera/frame set.

## Results and accounting

`validate_actual_worker_result(request, arm, phase, result)` accepts only
`plan069-final-render-actual-worker-result/v1` records and rechecks immutable
admission, exact same-arm preceding actual result, phase-specific complete
coverage, initializer/archive/native-input receipts, checkpoint endpoint,
restoration evidence, RGB media dimensions and resource limits. Fixture result
schemas and receipts cannot be promoted. Validation recursively checks the
published predecessor chain. `published=False` is used only during the worker's
own final validation before publication.

Results appear in the bound output directory as `result.json`. The separate
`completion.json` uses `plan069-final-render-actual-worker-completion/v1`, binds
the exact result bytes, confirmed worker cleanup and publication-inclusive
elapsed time. Failure or missing completion makes the candidate unusable.
Terminal validation and publication share the deadline/failure checks used by
training/render; partial artifacts are preserved and failures bind invocation
and request. One MiB is reserved for terminal records. The supervisor must still
independently accept measured process resources and group cleanup; a worker
completion alone is not a successful ledger finish or final human review.

CPU tests verify fixture refusal and unchanged fixture worker behavior. They do
not establish actual qualification, DO admission, native matcher correctness,
CUDA execution or successful final renders. No actual job is launched here.

The native numerical pool uses at most `cpu_workers_limit - 1` threads (seven
under the eight-worker contract), reserving one worker for bounded monitoring.
Prelaunch numerical defaults and control helpers use one thread. CUDA housekeeping
threads are reported separately from numerical workers; spawned worker processes
consume the same ceiling. Current-source qualification must measure this policy.
