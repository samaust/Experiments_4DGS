# Approved S1 recovery 002 dispatch result

The user approved the prepared `S1-calibration-recovery-002` identity. The host
`--check` gate reported GO, and `bash scripts/run_s1_calibration_recovery_002.sh
--run` was invoked once. The new request passed the 524,288-byte shared request
limit: its frozen file and worker copy are each 353,132 bytes. The earlier
request capacity failure did not recur.

The dispatch appended admission 453, authorization 454, reserve 455, temporary
directory 456, worker started 457, and failed finish 458. The live ledger now
contains 459 events. Its first 453 events are byte-identical to the consumed
recovery 001 ledger. Recovery 002 is consumed and cannot be redispatched:
`validate_binding(consumed=True)` passes, while unconsumed binding is rejected
with `consumed S1 identity or active attempt`.

The worker launched as PID and PGID 558824. Its runtime record identifies the
RTX 4090 and its log shows model initialization. The supervisor failed during
`worker_sample` with `TimeoutError: S1 phase deadline reached`, after
**10.944929263 seconds** of charged GPU allocation. The S1 helper bounds each
resource sample by one second (`s1_helper_session.py:2544`), and the supervisor
passes a one second phase deadline for the sample (`supervisor.py:481`). The
terminal record establishes which phase expired; it does not establish why that
particular sample took too long. No result, acceptance, or terminal receipt was
produced. The retained helper was unavailable for terminal publication, a
secondary failure recorded in the finish event.

The supervisor's exception text included an uncertain-cleanup note during
unwinding. The final ledger finish resolves the cleanup status as confirmed:
`cleanup_uncertain` is false, with no surviving PIDs, helper ownership, or
helper cleanup errors. A host check found worker PID 558824 absent, and
`nvidia-smi` listed no GPU compute apps. The temporary directory contains two
Python module/cache files from startup; it was not empty. Recorded GPU total
is **4,387.681799262877 seconds across 32 attempts**, with zero seconds
reserved.

[dispatch-outcome-002.json](dispatch-outcome-002.json) binds the reservation,
start, finish, live ledger, immutable [ledger snapshot](post-dispatch-ledger-002.jsonl),
worker log and runtime record. [audit-dispatch-002.py](audit-dispatch-002.py)
checks the prefix, terminal status, cleanup, request size, consumption and
binding refusal before writing the snapshot and outcome. The scientific inputs,
deadlines and consumption history remain unchanged. There was no retry, further
GPU dispatch, or new authorization.
