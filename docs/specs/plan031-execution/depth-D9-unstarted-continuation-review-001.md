# D9 grant851 continuation contract

This is a review of a code path, not execution authority or a new allocation.
The scope is the original `plan069-D9-maps-001` allocation at sequence 851,
event hash `4a65c3191857d999f1134bc98446aff435edfa9e5486252b9b44383235e250b6`.

The original grant, actual request, command, worker entry script, interpreter
invocation, proposal, setup lineage, native profile, workload, allocation, and
whole-slot byte budget remain immutable. No additional attempt is allocated and
no reserve, start, finish, or accounted state may be reopened. The command keeps
the qualified virtual environment path; executable evidence records the resolved
interpreter bytes. `validate_runtime_interpreter` checks these separately.

## Additional evidence

A `plan069-D9-unstarted-continuation/v1` sidecar binds `candidate`, `job_id`,
`original_grant_sha256`, `original_request`, `command`, `config_sha256`, and the
current `ledger_head_sha256`, with `new_allocations: 0` and
`reset_previous_consumption: false`. It references fresh `source_review`,
`admission`, `cpu_validation`, and `mypy_validation` file records.

The current admission must pass the existing source, commercial, asset, native
runtime, recovery setup, profile, and live-cap gates for the original proposal.
The current source review and qualification must cover the current D9 source
closure, including the continuation implementation. The original admission
continues to identify the original allocation and accounting lineage; the new
admission supplies additional current source/runtime evidence.

CPU evidence uses the existing actual integrated or delta CPU capture schema.
It must contain unchanged before/after sources covering every current D9 source,
successful tests, unchanged environment/head, the passed/within-wall flags,
successful commands with no timeout, hash-bound command logs, and confirmed
cleanup. `mypy_validation` deliberately references a combined tests-and-mypy
capture using the same schema. Both references may select the same combined
capture. A tests-only full capture plus a short mixed tests-and-mypy delta capture
is also supported. Fixture captures cannot grant production continuation.

## Checked transitions and boundaries

`Ledger.continue_depth_d9_attempt` rechecks the exact unstarted grant and current
evidence under the ledger lock. It obtains a fresh physical GPU/byte sample,
requires the original GPU UUID and no GPU owner, checks the unchanged cumulative
and per-slot limits, and appends one protected continuation event. The event
does not allocate a new job. Generic `Ledger.note` cannot create this event.

`dispatch_continued(sidecar_path)` invokes the existing supervisor with the
original command/request/output and original evidence plus the sidecar. It
creates no replacement request or allocation. Reserve requires the latest
continuation within 30 seconds, an absent worker output, and the exact combined
evidence. The sidecar's original passing admission is rehashed against its bound
prefix; fresh physical resources are sampled again under the lock. The initial
admission freshness check is made at validation entry, before hashing can age a
valid snapshot.

Worker entry rechecks the protected continuation before native model loading.
Existing video workload, completed setup, accepted recovery lineage, runtime
interpreter, and whole-slot guards remain active. Active recovery ancestry selects
the additional source/runtime phase proof from the protected sidecar while
retaining original accounting evidence.

Completion rechecks the additional proof and charges validation time through the
terminal transition. Changed evidence produces a failed terminal event instead
of leaving a cleaned attempt unresolved. A validation overrun is recorded as a
failed deadline disposition. The dispatcher checks the final recorded outcome
before reporting success. Publication rechecks the sidecar and requires clean,
complete, within-deadline finish evidence before writing package artifacts.

The byte guard accepts an optional already-locked event list so these checks do
not reacquire the ledger lock. Other callers retain its existing behavior.

## Validation limits

The run-specific CPU fixture uses the literal protected grant and a private
filesystem ledger adapter, simulated current qualification evidence, a small
fixture dependency, and a substituted physical resource sample. It exercises
checked continuation, reserve, worker admission, finish and publication rejection
without native imports, GPU use, or writes to the shared run. If the original
run's immutable ancestry is unavailable, that fixture is explicitly skipped;
the portable rejection and interpreter tests still run. These fixtures do not
establish actual source/runtime qualification or execution readiness.

Root review, current actual evidence, the fresh physical samples, and the existing
authorization boundaries are still required before an actual continuation.
