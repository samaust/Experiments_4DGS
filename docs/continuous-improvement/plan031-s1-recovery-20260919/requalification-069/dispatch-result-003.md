# Approved S1 recovery 003 dispatch result

The user approved exactly one `S1-calibration-recovery-003` calibration GPU
attempt. The read-only host `--check` gate reported GO, then
`bash scripts/run_s1_calibration_recovery_003.sh --run` was invoked once. The
wrapper's own host gate also reported GO. No 001 or 002 redispatch occurred.

Admission 459, authorization 460, reserve 461, temporary directory 462 and
worker start 463 were followed by two `monitor_gap_recovered` notes at 464 and
465, and failed finish 466. The live ledger now contains 467 events. Its first
459 events are byte-identical to the consumed 002 snapshot. The new identity
is consumed: `validate_binding(consumed=True)` passes and unconsumed binding
is rejected with `consumed S1 identity or active attempt`.

The worker launched as PID and PGID 572263 and initialized the S1 model on the
RTX 4090. The two bounded monitoring recoveries each expired two samples and
took 2.084126931 and 1.935207914 seconds. The monitoring correction therefore
recovered both transient gaps in this attempt. The worker then exited with
status 1 at its first calibration output, camera 0, frame 50. Its traceback
identifies `ValueError: progress byte capacity` while encoding the produced
row with the 256 KiB limit in `s1_progress.py`. The row was not published; the
first-result record has count zero. The failure evidence is retained. The
captured artifacts do not report the row's exact encoded size.

The supervisor charged **25.151324003 GPU seconds**. The terminal finish has
`failure_kind=worker_failure`, confirmed cleanup, no surviving PIDs or helper
cleanup errors, and a published terminal receipt. There is no accepted result.
A host check found PID 572263 absent and `nvidia-smi` reported no compute apps.
Cumulative GPU allocation is **4,412.83312326588 seconds over 33 attempts**,
with zero seconds reserved. No retry or new GPU authorization occurred.

[dispatch-outcome-003.json](dispatch-outcome-003.json) binds the reservation,
monitor gaps, finish, immutable [467-event ledger snapshot](post-dispatch-ledger-003.jsonl),
worker log, failure record, first-result evidence and terminal receipt.
[audit-dispatch-003.py](audit-dispatch-003.py) checked the ledger prefix,
consumption refusal, cleanup and host process state before writing the outcome.
The scientific inputs, source qualification, deadlines and prior consumption
history remain unchanged. This failed attempt cannot be dispatched again.
