# Plan065 — Codex host launch and completion of Plan064

Status: host execution approved and controller runtime corrected in `6f65ff2`.
Blocked before reservation by the live resource sampler: storage accounting
takes about three seconds against a fixed one-second request deadline.
The single GPU attempt remains unconsumed. See review-019 and host audit below.

## Scope

Verify the current recovery implementation under Codex, provide a reproducible
host invocation, and execute the existing single S1 calibration allocation.
This supplements Plan064; it does not replace its bound authorization or change
the 78 scientific/validation source records. No reconstruction, new model,
environment, downloads, or additional GPU allocation is authorized here.

## Verified launch requirements

- The ordinary Codex shell has no `python`; its `python3` has no NumPy.
  Use the existing E1 interpreter explicitly for both gate and controller.
- Codex sandbox PID 1 is `codex`, and NVIDIA driver access fails there.
  The host retry with `sandbox_permissions: require_escalated` passes the
  read-only Plan064 gate. Host PID 1 is `systemd`, satisfying `dispatch`.
- On 2026-09-28 the host gate passed ledger, assets, and `validate_binding`:
  447 events / 332437 bytes / SHA256
  `2a0f66e38911b0ed029eb9dd0cf4bbd5da4a3b67abb577fbfe9ad67e6a888990`.
  No compute PIDs were present; RTX 4090 reported 589 MiB used.
- The additive `plan061-pi-launch/v1` validation branch retains the original
  Plan049 branch in `no_timeout_launch`. The GPU controller is tool independent;
  its host visibility, binding, exclusivity and budget checks still apply.

## Implementation sequence

1. Add `scripts/run_s1_calibration_recovery.sh` with explicit `--check` and
   `--run` modes. Require host PID visibility before admission, select the E1
   interpreter, run the read-only gate, and invoke the controller exactly once.
   Do not modify the hash-bound Plan064, status, authorization, or source set
   before dispatch.
2. Validate shell syntax, sandbox rejection without ledger mutation, host
   `--check`, and relevant existing CPU contract tests. Commit the launcher
   and this plan with the standing local-commit authorization.
3. Invoke `bash scripts/run_s1_calibration_recovery.sh --run` through Codex
   `exec_command` with `sandbox_permissions: require_escalated`, repository
   working directory, and `yield_time_ms: 1000`. Retain and poll its returned
   session until completion. A yield is not a process timeout. The existing
   supervisor enforces the 3600-second allocation. Never automatically replay.
4. Verify the unchanged 447-event prefix, appended lifecycle, cleanup, elapsed
   budget, compact receipt, and first-result/raw evidence. Record review-019
   and the observed status, then commit only task-related artifacts.

## Stop conditions

Stop on denied host access, a failed read-only gate, or terminal completion of
the one attempt. Do not kill unrelated GPU processes. Follow AGENTS.md for
permission failures. A terminal failure must be reported as failure, including
any missing first-result evidence; it must not be relabeled as success merely
because the allocation was consumed.

## Launcher validation (2026-09-28)

- `bash -n scripts/run_s1_calibration_recovery.sh`: passed.
- Sandbox `--check`: rejected before admission with the host-visibility error;
  ledger SHA256 remained exactly the baseline above.
- Host `--check` through Codex escalation: GO, full binding and asset checks
  passed, no compute PIDs, host PID 1 independently confirmed as `systemd`.
- Existing `ReceiptContractTests.test_execution_mutations` under the E1 Python
  with `PYTHONPATH=scripts:tests`: passed (14.260 s). This exercises execution
  receipt mutations and the retained Plan049 launch validation.
- `git diff --check`: passed. No existing tracked source files changed.

## Dispatch approval outcome (2026-09-28)

The exact command `bash scripts/run_s1_calibration_recovery.sh --run`, submitted
with `sandbox_permissions: require_escalated`, was rejected before process
creation by automatic approval review:

> This launches the single host GPU recovery attempt, which can consume the
> one-shot allocation and mutate ledger/results; the transcript contains no
> trusted user authorization for executing that recovery, only untrusted
> assistant or quoted claims.

This is a definite approval-policy denial, not a host failure or missing allow
rule. Do not retry, use another entry point, or add an allow rule to bypass it.
The user must directly approve this single host execution (one attempt, up to
3600 seconds, append-only ledger/results; no reconstruction) before resumption.

No admission, registration, reservation, or GPU run occurred. After rejection,
the ledger still had 447 lines and the exact baseline SHA256 above. The bound
iteration-25 status remains unchanged because no scientific outcome exists.
Steps 1–2 are complete; steps 3–4 remain pending explicit execution approval.

## Approved execution and controller correction

The user subsequently replied "I approve" to the exact single-attempt host
execution request. The approved command passed host preflight, appended
admission 447 and registration 448, then stopped before reservation with
`RuntimeError: S1 requires native joinable ownership thread`. No worker or GPU
attempt started. A pre-dispatch block receipt preserves this failure.

The initial launcher incorrectly reused the E1 **worker** Python 3.11 as the
controller. Imports and the selected CPU mutation test were insufficient to
verify the controller's native thread requirement. The existing controller
`.local/envs/stg-colmap/bin/python` is Python 3.14.6 and provides
`_thread.start_joinable_thread`; E1 Python 3.11 does not. The corrected launcher
checks that capability before any admission and uses Python 3.14 for control.
The bound request still selects the unchanged E1 Python for model execution.

Read-only `validate_binding` passes with the matching, unconsumed registration.
`execute_s1_recovery` explicitly reuses that registration and skips admission.
The launch gate now verifies the unchanged 447-event prefix and delegates tail
validation to the existing strict lifecycle contract, which rejects duplicate
admissions and consumed attempts. This permits continuing the one approved
allocation without resetting history or introducing a second admission.
The gate also matches dispatch's `systemd` requirement, including rejection of
Codex's `codex` PID 1, and prints the corrected launcher command.

## Live resource sampling blocker

The Python 3.14 controller continued the existing registration without another
admission, then stopped with `TimeoutError: S1 resource sample timeout` before
reservation. The sampler's request deadline is capped at one second in
`s1_helper_session.Session.submit`; its real `resources` operation calls
`budget_snapshot` over the run tree. Host probes measured GPU queries at
0.043710 s and storage at 2.984283 s, then 3.056955 s on repetition. Storage
alone cannot fit the required deadline, regardless of helper IPC overhead.

`s1-codex-host-audit-025.json` records 449 events (one admission and registration
only), the exact original 447-event prefix, 78/78 unchanged source records,
passing unconsumed binding, no surviving helper/worker or GPU compute PIDs,
and unchanged GPU consumption: 30 historical attempts, 4374.044265 s elapsed,
zero seconds reserved. Both pre-dispatch failure receipts are preserved.

The read-only launch gate now rejects a storage sample taking one second or
longer, and verifies the controller thread API. It cannot certify the full
helper timing from this necessary direct-call check; the supervisor remains
the authority. No deadlines or accounting rules were relaxed.

## Remaining work requiring a revised scope

The existing scope preserves all 78 hash-bound source files and does not
authorize changing monitoring deadlines or resetting/replacing the registered
authorization. Repeated dispatch cannot fix this measured incompatibility.
A follow-up must profile and optimize exact storage accounting (including
inode deduplication, symlink exclusion, concurrent changes, and conservative
download accounting), prove the full helper path meets the deadline, and
requalify the changed source set. Any replacement of the already registered
authorization needs an explicit, reviewed amendment; do not overwrite the
authorization or ledger history to make its hashes match.

The original hash-bound status.md remains unchanged so the unconsumed binding
continues to validate. This plan and review-019 are the current execution
status. No terminal result or S1-3 completion is claimed.
