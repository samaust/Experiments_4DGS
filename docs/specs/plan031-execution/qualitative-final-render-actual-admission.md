# Selected-depth actual admission candidate (#34)

This module implements a guarded transition, not an execution approval. No GPU,
setup/download, shared live ledger mutation or native qualification is performed
by this implementation milestone. The native qualification producer/workflow and
its independently approved jobs remain unfinished; schema support here does not
claim those measurements exist. Missing human D*, licenses or measured native
qualification continue to block actual execution. Historical REVIEW contracts
remain unchanged.

## Public seams

`final_render_admission.reserve(envelope_record, ledger, arm, phase, command,
probe=..., parent_result=None)` rehashes exact authority and consumes one existing
allocation under the shared `Ledger.locked()` transaction. All current source,
runtime, licensing, qualification, prerequisite, predecessor, identity, live GPU,
storage, CPU and cumulative ceilings are checked before a ledger append.

The actual DO envelope schema is `plan069-final-render-do/v1`. Exact fields are
`schema`, `record_kind: actual`, `mode: DO`, `request`, `approval`,
`qualification`, `commercial`, `source_review`, `commands`, `interpreter`,
`checkout`, `source_files`, `ledger_head_sha256`, and `matcher_runtime`.
`request` is an immutable existing Plan 069 REVIEW request record, rather than a
rewritten REVIEW document. Commands map every arm/phase to its literal argv.
Interpreter, matcher runtime and all other evidence are exact path/hash/size file
records. Each command includes the already determined invocation pathname.
Publish approval/envelope before invocation bytes to avoid a hash cycle.

The separate human approval (`plan069-final-render-do-approval/v1`) binds the
canonical hash of the envelope excluding `approval`, the exact REVIEW request,
and all 21 existing allocations. It has `record_kind: human`, `status: approved`,
nonempty `reviewer` and `approved_at`. It creates no additional attempt or budget.
The first reservation requires the approved ledger head and appends a durable
`final_render_do_authorized` event immediately before the reservation. Later
phases reuse that exact grant after current locked rechecks; a head advance does
not itself require another human approval. Changed authority requires a new
review. `Ledger.note()` cannot manufacture this authorization event.

`invocation_binding(invocation_record, request, arm, phase, require_worker=False)`
validates immutable invocation, grant, reservation, source and argv provenance.
It permits finished history for result validation. `worker_binding(...)` also
requires the calling PID/PGID to equal the single `started` root of an active
reservation. The supervisor registers the exact `invocation` file record in that
started event before releasing the worker handshake. `validate_dispatch_invocation`
validates an exact reservation before launch without requiring a PID yet.
Returns include invocation/envelope payloads, their separate file records,
request/runtime/matcher runtime records, and the exact reservation.

Invocations have schema `plan069-final-render-actual-invocation/v1`,
`record_kind: actual`, and bind `envelope`, `request`, `arm`, `phase`,
`parent_result`, `output`, `initializer`, `worker`, `interpreter`, `source_files`,
and `ledger_path`; stage-specific settings are covered by immutable invocation
bytes. Worker entry must appear in the approved command and source inventory.

## Independent evidence

A prepared inventory alone is insufficient. Native qualification schema
`plan069-final-render-native-qualification/v1` requires `record_kind: actual`,
`status: passed`, exact request/runtime/source/interpreter/matcher-runtime
bindings, and positive measured `initializer_bytes`, `checkpoint_bytes`,
`checkpoint_seconds`, `cleanup_seconds`. Retention must fit the artifact cap and
checkpoint plus cleanup reserves must fit training's unchanged deadline.

`runs` binds one immutable `plan069-final-render-native-phase-qualification/v1`
receipt per geometry/initializer/train/render phase. Each contains actual status
passed, phase, runtime/request, job identity, literal command, elapsed seconds,
CPU workers, peak device bytes, artifact bytes, native qualification and cleanup.
Every run must have a successful cleaned shared-ledger finish binding its exact
receipt and an independently allocated actual reservation with role
`native-qualification` and matching runtime, source files and command. Production
allocation IDs cannot qualify themselves. Qualification execution must be
separately authorized under its own existing allocation; this module grants none.

Commercial assessment (`plan069-final-render-commercial-assessment/v1`) binds
actual allowed code, weights, dependencies and inference-output permissions,
current runtime/sources, named reviewer and immutable primary-source receipts.
Independent source review (`plan069-final-render-source-review/v1`) binds actual
passed status, reviewer, request and current sources. Native and matcher inventory
validators rehash their complete existing preparation contracts without model
imports or GPU operations.

## Live and cumulative accounting

The supplied live probe is a measurement seam, not an authorization callback.
Its exact snapshot fields are `artifact_bytes`, `download_bytes`,
`free_disk_bytes`, `device_bytes`, `gpu_pids`, `cpu_workers_used`,
`cleanup_confirmed`, and `observed_unix`. Readings are nonnegative typed integers;
GPU PID list must be empty, cleanup confirmed and observation age at most 30s.
All phase reservations are serial. No consumed identity or failed predecessor
can advance. A predecessor must be the exact same-arm previous phase's cleaned,
successful ledger result; bytes are rehashed.

Whole-scope REVIEW budget checks include unchanged historical charges and actual
charges for previously consumed scope. Only those completed slots' original
planned ceilings are deducted from the prospective whole-scope reservation to
avoid counting the same planned allocation twice. Each current phase additionally
checks its full ceiling against actual cumulative ledger totals. The public
reserve/finish event shapes remain compatible with existing accounting.

## CPU-only tests

`reserve_fixture(...)` uses `record_kind: fixture`, `mode: SIMULATE`, a private
request-adjacent `fixture-ledger.jsonl`, fixture-only history and CPU reservations
prefixed `fixture/`. It cannot consume the shared actual ledger, native runtime or
actual prospective identities. Flags remain false. Tests exercise atomic locking,
fresh identity, cumulative charging, predecessor order and live resource refusal
through the public admission/ledger seams. They fabricate no actual human
approval or native qualification.
