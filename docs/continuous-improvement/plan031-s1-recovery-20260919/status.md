# S1 recovery status — iteration 24 IMPLEMENT closed: timeout-mode gate met at 240 s (Option B)

## Current position

- **Timeout-mode gate: MET at 240 s.** `timeout-gate-063/aggregate-063-004` —
  non-owned direct module-form launch, `--timeout 240`: returncode 0,
  `timed_out` false, elapsed 199.74 s, `Ran 249 tests` with 249 ok / 0
  errors / 0 failures, receipt `passed=true` / `expected_exit_code=0`,
  78/78 sources byte-unchanged, boot `ba1b4efe-ee43-4088-86df-706c41cfac12`.
  The gate binds at ~83% of cap and still pressures runtime minimization.
- **S1-2 no-timeout: re-MET on the final source.** `pi-launch/aggregate-061-007`
  (index 7, pi driver, `--no-timeout`): returncode 0, `timed_out` false,
  elapsed 313.2 s, 249 ok / 0 / 0, receipt passed, 78/78 sources
  byte-unchanged and byte-identical to the timed run's `sources_after`.

## What changed this iteration (all within the user-authorized scope)

1. **Cap constants** (`s1_validation_capture.py` default/bound/CLI,
   `s1_validation_contract.py` timed-execution bound): 300 → 360 (original
   user confirmation) → **240** (final, Option B).
2. **Owned-note precondition guards** on the 14 owned-only tests
   (11 supervisor, 3 s1_recovery) using the house guard pattern: control
   record + return in non-owned mode, full exercise in owned mode. The five
   parameterized guards (plan046/plan047 ownership, supervised-cleanup,
   acceptance-historical, terminal-resolver) re-fire their declared
   `SUBTEST_CASES` callbacks so the receipt callback-multiplicity contract
   holds in non-owned mode.
3. **Fixture alignment**: the synthetic receipt fixture in
   `test_vipe_benchmark_s1_recovery.py` carried `timeout_seconds=300`;
   aligned to 240. Mutation tests keep their 300 s rejection cases.

## How the 240 s was established

- 360 s (user-confirmed) falsified: `aggregate-063-001` timed out at
  360.1 s; true non-owned timed-mode floor measured at **430.64 s**
  (`measure-063-001`, 235 ok / 14 owned-only errors / 0 failures).
- The 14 errors were owned-only tests doing heavy partial work (~234 s in
  three `s1_recovery` tests) before `KeyError: 'S1_OWNED_ROOT_NOTE'`.
- After guards: `measure-063-002` = **198.23 s**, 249 ok / 0 / 0 →
  1.25x ≈ 248 s → rounded to **240 s**.
- Corrective launches: 002 (fixture-cap mismatch, 63.5 s rc=1), 003
  (callback-multiplicity mismatch after all 249 passed, 199.3 s rc=1),
  004 accepted.

## Success-criteria position

- **S1-1**: met — additive pi-launch class; no owned-path assertion weakened.
- **S1-2**: met — both validation classes on the final source bytes:
  no-timeout pi (aggregate-061-007) and timeout-mode gate
  (aggregate-063-004).
- **S1-3**: not met — live S1 calibration recovery requires separate later
  GPU authorization.
- **S1-4**: met — Plan049 chain byte-identical; prior failures/aggregates/
  reports untouched.

## Allocation note

The 7200 s iteration allocation was exceeded: total span ~12 h including
the stop gap awaiting the user's A/B gate decision (sanctioned stop: new
authorization required); active wall ~2.5 h because the Option B amendment
added work beyond the planned profile. Documented in
`iteration-024-timing-final.json` and `assessment-059-implement.json`.

## Large artifacts

Per-attempt `plan047-deadline-steps.json` scenario dumps (~50 MB each;
attempts 001–007 plus timeout-gate-063 runs 002–004 and measurements
001–002) are hash-manifested in
`pi-launch/large-artifact-manifest-061.json` (12 entries) and excluded from
git. `aggregate-063-001` produced no deadline-steps file (killed during the
supervisor module).

## Stop point

Iteration 24 complete. Next work is S1-3 — live S1 calibration recovery —
which requires separate later GPU authorization; a new decision point
outside this plan's authority.
