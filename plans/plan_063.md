# Plan063 — Timeout-mode gate duration amendment (iteration 24)

## Status

Active. Implements decision point A (scope amendment of the timeout-mode
gate) on explicit user confirmation (see
`docs/continuous-improvement/plan031-s1-recovery-20260919/timeout-gate-063/timeout-gate-authorization.md`).
Scope: raise the aggregate timeout-mode cap 300 s → 360 s, declare the
owned-note precondition of the owned-only ownership test, and validate the
amended gate with one timed-mode aggregate and one no-timeout pi
re-validation.

## Context

The 300 s timeout-mode cap sat below the floor of the mandated work. Four
post-R18-1 full-suite wall times (boot `ba1b4efe-ee43-4088-86df-706c41cfac12`):

| run | elapsed s |
|---|---|
| aggregate-061-003 | 321.24 |
| aggregate-061-004 | 320.28 |
| aggregate-061-005 | 320.79 |
| aggregate-061-006 | 326.65 |

The R18-1 reducible pool is already removed; the remainder (~320–327 s) is
mandated (full-510 guard work plus 114 mandated re-qualifications). The
old cap could therefore never pass — it was unachievable by construction,
not tight. The user authorized a new cap that keeps the
"optimize toward minimizing duration" pressure while being realistic:
**360 s** (= worst measured + ~10%). The diagnostic cap (120 s) is
unchanged.

## Source changes (exactly four cap sites + one test precondition)

1. `scripts/vipe_benchmark/s1_validation_capture.py`:
   - `capture()` default `timeout_seconds=300` → `360`
   - aggregate bound `0 < timeout_seconds <= (120 if diagnostic else 300)`
     → `... else 360)`
   - CLI default `300 if args.timeout is None else args.timeout` → `360 ...`
2. `scripts/vipe_benchmark/s1_validation_contract.py`:
   - timed-execution bound `0 < timeout_seconds <= 300` → `<= 360`
3. `tests/test_vipe_benchmark_supervisor.py`
   `HelperSessionTests.test_progress_plan047_ownership`: declare the
   owned-note environment precondition via the house `control_record`
   pattern (control note + return) when `S1_OWNED_ROOT_NOTE` is unset.
   This is the only test that unconditionally reads the owned-note
   environment; in the owned no-timeout environment it is exercised in
   full, unchanged. The cap mutation test is unaffected (it forces
   `timeout_seconds = 1`, so the `elapsed <= timeout` clause fires; the
   300 literal is not hardcoded in any test).

No other source references the aggregate cap (verified by grep; the
`backends.py` 300 values are depth clips).

## Validation

Run directories: `docs/continuous-improvement/plan031-s1-recovery-20260919/timeout-gate-063/`.

1. **Timed-mode gate (attempts 1–2, max 2)** — direct module-form launch
   from the repository root (same non-owned environment as all prior 300 s
   measurements; timed mode is ledger-free):

   ```
   PYTHONPATH=scripts ./.local/envs/stg-colmap/bin/python -B -u -m vipe_benchmark.s1_validation_capture docs/continuous-improvement/plan031-s1-recovery-20260919/timeout-gate-063/aggregate-063-00N --timeout 360
   ```

   Acceptance (attempt 1 or 2): `timed_out` false, `elapsed_seconds <=
   360`, runner returncode 0, `Ran 249 tests` with 0 errors and 0
   failures (ownership test passes via its declared precondition),
   78/78 source members byte-unchanged. Adjudication rule: if the
   timed-mode run lands above ~350 s, the gate value is reconsidered at
   390 s rather than accepted flake-thin (recorded, not self-applied).
2. **No-timeout pi re-validation (1 attempt)** — the source set changes,
   so the pi-launch acceptance is re-validated on the new bytes:

   ```
   ./.local/envs/stg-colmap/bin/python -B docs/continuous-improvement/plan031-s1-recovery-20260919/pi-launch/pi_launch_driver.py aggregate 7 "<reason>"
   ```

   Acceptance: `Ran 249 tests`, 0 errors / 0 failures, returncode 0,
   `timed_out` false, 78/78 unchanged.

## Allocation (fresh, iteration 24)

- 7200s wall clock total for the iteration
- 6000s source/test cutoff; 1200s evidence reserve
- at most 2 timed-mode 360 s aggregate attempts + 1 no-timeout pi
  aggregate attempt
- zero GPU / model / production work
- `B+max(1,H) <= 8` unchanged

## Invariants

- no suite/fixture/gate shrink — raising the cap weakens no test
  assertion; the cap mutation test still enforces the cap at the new value
- Plan049 chain byte-identical; pi-launch chain unchanged (the re-
  validation only re-proves it on new source bytes)
- pi receipts carry `provenance='pi-launch'`; timed-mode gate runs are
  non-owned, ledger-free measurements and are never presented as
  session-bound or pi-launch evidence
- no session-proof or tool-event fabrication

## Stop conditions

1. Both validations pass -> S1-2 timeout-mode gate recorded met at 360 s;
   S1-2 overall met; stop at the separate later GPU-authorization decision
   point (S1-3).
2. Timed-mode attempts exhausted without acceptance -> record the exact
   residual and stop; no further launches without new authorization.
