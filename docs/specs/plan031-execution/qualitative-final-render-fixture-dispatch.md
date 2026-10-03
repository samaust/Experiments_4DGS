# Supervised final-render fixture dispatch (#34)

`FixtureDispatcher(request, root)` accepts only a validated Plan069 fixture REVIEW
request and owns a fresh private directory and append-only ledger. It rejects
actual requests before creating output. It does not open the shared execution
ledger, authorize a DO proposal, instantiate native models or acquire the GPU.

`dispatch(arm, phase, worker, parent=None, arguments=(), seconds_limit=None,
resource_samples=())` consumes an exact Python worker file record. The script
receives its fresh output directory, frozen request path and literal extra
arguments. Its complete result must match the existing worker contract and exact
predecessor. Result artifacts must resolve inside the owned output. A script may
return normally or exit zero; a zero exit alone cannot establish acceptance.

The invocation freezes request, script, interpreter/entry records, control source
hashes, predecessor, arguments and explicit disposable resource samples. Control
and request files are rechecked before and after worker execution. All invocation,
acceptance and dispatch authority/qualification flags remain false.

## Supervision and accounting

Reuse `supervisor.supervise` and `Ledger` for owned process groups, serial locked
reservations, finite phase deadlines including cleanup, child-survival rejection,
cleanup confirmation and terminal accounting. Fixture identities use the separate
`fixture/<request>/<arm>/<phase>` namespace and charge CPU time, including phases
that would require a GPU in an actual run. The historical CPU cumulative cap and
the narrower caller deadline apply; prospective phase caps are never increased.

Worker processes hide CUDA devices, use offline flags and constrain numerical
thread settings to the request's CPU allowance. Limits are set before process
launch and before any numerical imports, via the supervisor's
optional bounded `cpu_workers_limit`; other callers retain their existing defaults.
Device/download values are
explicit simulated fixture readings; artifact bytes include real private files,
logs and temporary caches. CPU process-group counts and simulated CPU usage must
fit the request. No resource callback or live device probe is supplied by this API.

Full result validation executes inside the supervised worker before its exit.
The parent accepts only a small bound acceptance proof and result record, then
requires complete terminal ledger accounting and certain cleanup. Application,
deadline, resource and acceptance failures retain logs, partial outputs and the
supervisor's primary/secondary failure evidence. Existing output is never replaced;
no automatic retry occurs. A corrected retry needs fresh immutable inputs and a
new fixture identity, within the applicable budgets.

## Remaining actual gates

These are CPU control fixtures, not native qualification or actual admission.
The inherited synchronous filesystem census and small parent acceptance checks
are not proof against blocked host I/O. Actual dispatch still needs qualified
bounded resource monitoring and acceptance, exact current runtime/source/license
evidence, measured viability, approved DO transition under the shared ledger lock,
live GPU exclusivity and cumulative experiment budgets. The integration owner
retains those operations. #34/#35 remain open for actual renders and human feedback.
