# S1 calibration recovery 003 preparation

Status: `S1-calibration-recovery-003` is a proposed, separate one-attempt identity.
Its authorization has `additional_attempt_approved=false` and stage `REVIEW`.
This review grants no GPU attempt. Recovery 001 and 002 remain consumed.

## Bound predecessor and unchanged inputs

The live ledger is exactly 459 events, 351,609 bytes, SHA-256
`97e55b9ab1d1651dfdfda227ead2a697352c1e445ec352902f53685b7e030a3b`.
It is byte-identical to the immutable recovery 002 post-dispatch snapshot. The
002 terminal event at sequence 458 is a failed, cleaned-up finish with no
surviving PIDs and 10.944929263 seconds charged. The cumulative GPU total is
4,387.681799262877 seconds over 32 attempts, with no reserved seconds.
The 003 validator requires the exact 459-event prefix, the 002 authorization,
its failed finish hash and confirmed cleanup, plus the historical 001 lifecycle.
It rejects 001 or 002 redispatch, another identity, any consumption reset and
unrelated appended events.

The proposed document retains the original calibration request hash, S1 input
and annotation records, semantic amendment, frozen configuration, E1 runtime
and assets, baseline correction, 3,600-second per-attempt ceiling,
93,600-second cumulative GPU ceiling, and at most 30 seconds of cleanup
reserve. It permits no reconstruction, new setup or downloads. The proposed
request is 353,132 bytes under the 524,288-byte shared request bound.

## Monitor policy and remaining risk

The worker-sample correction from requalification 068 remains unchanged. Each
resource reading expires after one second and a late reading never certifies
safety. Only worker monitoring can spend up to 15 seconds obtaining a later
fresh reading, capped by the original work deadline. That limit budgets the
two existing five-second `nvidia-smi` query timeouts plus five seconds for
storage, census and transport. It is a policy bound, not a measured latency
from the consumed 002 failure. The ordinary supervisor poll sleep remains
100 milliseconds for S1. A recovered gap can still exceed 100 milliseconds
between certifying readings; the 15-second window is an explicit exceptional
monitoring gap, not a 100-millisecond sampling guarantee. A ceiling breach or
foreign GPU PID seen in a late reading stops work, while sustained uncertainty,
transport failure and the original work deadline still fail closed.

## CPU qualification and host preflight

The sandbox CPU capture failed because AF_UNIX datagram creation returned
`PermissionError: [Errno 1] Operation not permitted`. The single host retry
passed 268 tests and 1,028 subtests in 211.35 seconds under its 240-second
cap, with zero failures, errors or skips. Its inner receipt, outer execution
record and validation wrapper passed against the same current 78-file source
set. [validation.json](validation.json) is the current source binding for 003;
requalification 068 remains the qualified predecessor source correction.
A focused CPU test also validated the proposed 003 binding against the live
prefix using a temporary synthetic approval, without modifying the ledger.
That synthetic record is not an authorization.

The read-only host gate checked the 459-event ledger, E1 import chain, 11 S1
asset records, current source qualification, both 353,132-byte requests,
0.762-second storage sample, and an RTX 4090 with no compute PIDs. It returned
NO-GO solely for the two expected approval checks: the draft is at `REVIEW`
and `validate_binding` is withheld until explicit approval. The 0.762-second
storage observation leaves limited margin under each one-second sample
freshness deadline; the 15-second recovery window does not make a stale sample
safe. A fresh host check is required immediately before any future dispatch.

## Proposed authorization and dispatch

Approve exactly one additional calibration attempt under
`S1-calibration-recovery-003`, with the unchanged scientific inputs and limits
above, the exact 459-event consumed prefix, and the current source validation.
On approval, record that approval in
`docs/research/vipe-alternatives/plan031-20260913T032700Z/s1-calibration-recovery-authorization-003.json`
by changing `additional_attempt_approved` to `true`, stage to `DO`, and the
proposed authorization text to the user's explicit approval. Then run the
read-only host gate:

```bash
bash scripts/run_s1_calibration_recovery_003.sh --check
```

Only if it reports GO, the proposed single dispatch command is:

```bash
bash scripts/run_s1_calibration_recovery_003.sh --run
```

Neither command has launched a GPU attempt during this preparation.
