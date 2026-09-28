# Codex host dispatch result

The Codex host launcher passed preflight and executed the approved dispatch.
Calibration failed before the GPU worker started. The single authorized attempt
is consumed; do not rerun this identity or reset its consumption.

Implementation and qualification are committed at `8e88a90`. Final timed006
passed 258 tests in 218.019 seconds under its 240-second cap. Full Codex-owned
aggregate016 and final focused diagnostic032 passed with all payloads retired.
See [review.md](review.md) for the exact revision and evidence distinctions.

The source amendment was appended at event449. Dispatch then appended reserve450,
temporary_directory451 and failed finish452. The ledger now contains 453 events;
the original 449-event prefix is byte-identical. `validate_binding(consumed=True)`
passes, while a new unconsumed binding is rejected with
`consumed S1 identity or active attempt`.

The registered request is **353,132 bytes**. Prelaunch at
`scripts/vipe_benchmark/s1_progress.py:453` calls `read_record` with a
**262,144-byte** limit and fails with `ValueError: progress regular file capacity`.
The worker-side request check at line702 has the same limit. These are request
size checks, not disk capacity or GPU memory failures. CPU fixture requests did
not expose the registered request's size; the launch gate did not check this
prelaunch constraint before reservation.

The attempt charged **2.692604537 seconds** to the GPU allocation. Total recorded
GPU consumption is 4,376.736869999875 seconds across 31 attempts, with zero seconds
reserved. No `started` event exists for this recovery identity and no model
worker ran. The finish records confirmed process cleanup, no surviving PIDs and
no helper ownership. Host checks found no GPU compute apps or S1 helper/worker
processes. The temporary directory remains empty. Terminal receipt publication
was unavailable because the retained helper was poisoned after the prelaunch
failure; the ledger finish and captured helper traceback preserve the outcome.

[dispatch-outcome.json](dispatch-outcome.json) binds the live ledger, its preserved
snapshot, the exact helper traceback and the consumption/cleanup audit.
[host-dispatch-poll-001.json](host-dispatch-poll-001.json) preserves actual tool
output. No reconstruction or extra dispatch was performed.

## Proposed next work — requires a new authorization

1. Preserve this terminal identity and all existing source bindings. Define a new
   recovery authorization and reviewed source amendment without resetting any
   prior consumption; the original authorization has `attempts_limit: 1`.
2. Introduce a shared bounded request-size contract that accommodates the actual
   frozen request. Apply it consistently to prelaunch and publisher request reads;
   retain exact hashes, schema validation and all existing runtime deadlines.
3. Check the real bound request against that contract in read-only preflight,
   before any reservation. Add boundary rejection and full-size request coverage
   using the actual request structure, then requalify affected sources.
4. Only after that review and explicit new attempt authorization, register a new
   identity and dispatch once under the unchanged cumulative budget and GPU
   exclusivity checks.

No current source files were changed after the registered amendment, and no
additional attempt is authorized by the completed Plan066 work.
