# Plan065 — Codex host launch and completion of Plan064

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
