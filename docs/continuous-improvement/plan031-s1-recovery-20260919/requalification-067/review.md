# Second S1 calibration recovery: source and authorization review

Status: source qualification and new attempt authorization are separate. The
consumed `S1-calibration-recovery-001` identity remains terminal. This review
prepares `S1-calibration-recovery-002`; it grants no GPU attempt.

## Failure and correction

The registered request is 353,132 bytes. Prelaunch rejected it at the former
262,144-byte read cap before a model worker started. The same cap also appeared
in publisher and row qualification reads. The shared `REQUEST_BYTES` contract
is 524,288 bytes. `read_request_record` checks the declared size, reads the
regular file with a bounded read, verifies its exact hash and byte count, then
checks the decoded request against the expected object where supplied. The
pre-reservation dispatch check uses it on the saved canonical request. The
read-only host gate verifies the frozen consumed request and the serialized
size of the proposed new request before any admission or reservation.

The regression covers the actual 353,132-byte request, an exact-boundary copy,
an oversized copy, and a mismatched request body. The 453-event consumed ledger
prefix and previous authorization are bound by the new identity validator.
The new clock, helper, worker, supervisor, and result paths accept only the two
enumerated recovery identities. An unrecognized third identity is rejected.

## Qualification and preservation

The source qualification record is [validation-002.json](validation-002.json).
Its full CPU receipt and execution capture are in `aggregate-timed-003`:
262 tests passed in 208.521 seconds under the 240-second cap; `validate_inner`
and `validate_execution` passed on the exact captured bytes.
The first capture in `aggregate-timed-001` failed in the Codex sandbox because
AF_UNIX datagram creation was denied; the host retry in `aggregate-timed-002`
passed 260 tests on the first request-size milestone. Both captures are kept.

The new validation binds the complete current 78-file source set. The prior
Plan066 validation and source amendment remain historical evidence for the
consumed identity. No source requalification event is appended to that identity.
The second identity binds its own current passing validation in its new
authorization and registration. No historical source snapshot, scientific
input, annotation, asset, configuration, semantic amendment, or deadline is
rewritten.

Compared with Plan066, exactly 12 source records changed: the benchmark CLI,
worker, execution, ledger, S1 clock, CPU helper, evidence, progress, recovery,
stages, supervisor, and S1 recovery tests. `validation-002.json` binds their
current hashes and all 66 unchanged source records. The new authorization
itself binds that validation; it does not reuse the old source amendment as
authority for the second attempt.

The read-only host gate was exercised against the draft authorization. It
reported the 453-event ledger prefix unchanged, the E1 environment and S1
assets present, no GPU compute PIDs, and both the consumed and proposed
serialized requests at 353,132 bytes under the 524,288-byte bound. It reported
NO-GO solely because the proposed authorization has not been approved. A
temporary synthetic authorization with the approval bit and `DO` stage set
passed `validate_binding` against the live ledger without modifying it. That
synthetic record is not the proposed authorization and grants no attempt.

The live ledger is 453 events, 342,703 bytes, SHA-256
`68412ed6711f31552d8ae3f849dc03636336c781045a14eae902c68109cb7ba3`.
The immutable post-dispatch snapshot has the same bytes. The second identity
requires that exact live prefix, the consumed failed finish event, confirmed
cleanup, no surviving PIDs, and the old authorization record. The cumulative
GPU tally remains 4,376.736869999875 seconds over 31 attempts with no reserved
seconds. A new attempt would have its own one-attempt, 3,600-second ceiling
within the unchanged 93,600-second cumulative cap, exclusivity check, 30-second
maximum cleanup reserve, and existing work deadlines. It would not authorize
reconstruction, setup, downloads, or a consumption reset.

## Proposed approval and dispatch

The review copy of the proposed authorization is
`docs/research/vipe-alternatives/plan031-20260913T032700Z/s1-calibration-recovery-authorization-002.json`.
Its `additional_attempt_approved` value remains false and its stage remains
`REVIEW` until the user expressly approves one new S1 calibration attempt.
The read-only `--check` gate must report GO on the host after the approved
authorization is recorded. Only then would this command be eligible to run:

```bash
bash scripts/run_s1_calibration_recovery_002.sh --run
```

The command invokes the new identity once. It does not rerun `...-001`.
