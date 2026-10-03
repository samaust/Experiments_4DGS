# Selected-depth training and reload/render preparation (#34)

This implements the agreed worker request/result boundary using CPU fake runtimes
and adds lazy native FreeTimeGS bindings for later qualification. It performs no
actual model job, GPU operation, setup/download or ledger mutation during CPU tests.

## Public fixture workers

`final_render_workers.train(request, arm, parent, initializer, output, runtime)`
and `render(...)` accept only Plan069 fixture REVIEW requests and fresh runtimes
with `record_kind=fixture`. Actual requests and native runtimes are rejected before
output creation. They return and exclusively publish the existing
`plan069-final-render-worker-result/v1` contract; the existing pipeline validator
accepts those complete outcomes. All authority/qualification flags remain false.

The initializer argument is an exact file record for
`plan069-final-render-prepared-initializer/v1`, containing record_kind, arm,
request_sha256, archive, initializer_receipt, execution_authorized=false and
native_adapter_qualified=false. The immutable NPZ retains all assembler arrays.
Both bundle and archive must occur in the complete initializer predecessor's
artifacts. Rehash the archive and run the existing selected-depth initializer and
native input validators. Do not change historical Plan027 loaders or contracts.

The runtime boundary supplies prepare_training, training_step, save_checkpoint,
checkpoint_metadata, reload_checkpoint, render_frame, resource_usage and close.
Training performs exactly 5,000 sequential native update calls, rejects nonfinite
losses, and verifies the published endpoint's exact iteration/provenance. Provenance
binds request, arm/composition, exact initializer, native input hash, seed, original
request bindings and full normalization. Pass independent provenance copies to the
runtime so it cannot change the expected checkpoint identity.

Rendering consumes the exact complete training checkpoint, rehashes its bytes,
uses a fresh runtime, saves a restored-state snapshot and requires an exact
5,000-step/provenance/full-state restoration result before any PNG. The runtime's
native implementation uses the existing complete checkpoint state comparison.
The fixture reload receipt cannot establish actual fresh-process qualification.

Render exactly four held-out cameras × frames0–49, at 960×540 and 25fps metadata.
Each runtime image must be finite float32 H×W×RGB. Freeze conversion to clamp[0,1],
nearest-even uint8 rounding and lossless RGB PNG. No interpolation, sparse subset,
repeat render, metric pass or video encoding is added by these workers. Later
authorized package publication must encode the already generated frames into clips.

## Bounds and failure evidence

Injected finite nondecreasing monotonic clocks enforce the existing 3,600-second
training and 900-second render ceilings between operations. Reserve 120 seconds
for checkpoint/reload work and 30 seconds for cleanup; retain the latter during
frame generation. Resource observations and actual output storage are checked
between operations under the request's device/CPU/artifact limits. Reserve 1MiB
within that artifact limit for the final control receipt; storage claims include
that reserve and every published artifact. These are conservative control reserves,
not measured native runtime/retention estimates or new allowances.

On application, resource, deadline or cleanup failure, close the owned runtime,
retain partial outputs and publish `plan069-final-render-worker-failure/v1` when
storage permits. It records exact artifacts, progress, reason, finite elapsed time,
resource observations and cleanup confirmation; it never passes the complete
pipeline gate. The raised original exception also carries `worker_failure` in
memory if a failure file cannot fit. PermissionError remains a host-access failure.
Never overwrite output, manufacture completion, retry automatically or delete
successful partial writes. A failure JSON is not ledger terminal accounting.

These cooperative checks cannot interrupt a hung callback. A separately qualified
DO dispatcher must enforce finite process termination, device monitoring, cleanup
confirmation, cumulative accounting and live admission before native execution.

## Native runtime candidate

`final_render_native.prepare_camera(request, camera, frame)` prepares CPU camera
inputs through the worker boundary, retaining accepted continuous intrinsics,
frame/50 time, target physical camera scale and full rotated similarity. Apply
scale to camera centers and remove it from orientation; do not add a second pixel
shift or normalize velocity again. Held-out calibration receives the same transform.

`NativeFreeTimeRuntime` accepts actual REVIEW prerequisites only; its constructor
performs CPU binding checks. Its GPU methods are low-level adapters for a future
admitted, supervised fresh worker process. Fixture entrypoints reject this class.
The class supplies native model construction, unchanged audited default_keyframe
training steps, complete checkpoint save/restore and native render methods.
Restore constructs a fresh model skeleton without another initializer or update.
No historical checkpoint can substitute for the selected initializer.

The exact `bindings.runtime` payload must use
`plan069-final-render-native-runtime/v1`, record_kind=actual, status=prepared,
environment_prefix, interpreter, source_files, binaries (gsplat/fused_ssim),
resolved_config and lpips_checkpoint. File records bind all current adapters and
native helpers, the exact preset checkout, installed modules and offline AlexNet
checkpoint. The resolved config binds the unchanged full native schedule with
start/end0/50, exact normalization and verified historical normalized scene_scale.
Network is disabled before library/model preparation. Missing CUDA fails without
CPU fallback. No runtime inventory or qualified actual result is fabricated here.

## Remaining gates

Actual D* decision, geometry source loading/model qualification, native runtime
inventory generation and compatibility/license verification, measured viability,
current-source qualification and approved supervised DO admission remain required.
The native GPU paths have not been executed or qualified by these CPU fixtures.
Actual final renders, clips and their bound human M/N comparison remain unfinished;
#34/#35 stay open. The other agent retains integration and GPU execution ownership.
