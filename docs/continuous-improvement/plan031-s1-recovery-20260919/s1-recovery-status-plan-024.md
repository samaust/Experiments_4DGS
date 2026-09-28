# S1 recovery status — iteration 24 PLAN: timeout-mode gate amendment to 360 s

## Current position

- **S1-2 no-timeout: MET.** `pi-launch/aggregate-061-006` — `Ran 249 tests`,
  0 errors, 0 failures, returncode 0, `timed_out` false, 78/78 sources
  byte-unchanged, boot `ba1b4efe-ee43-4088-86df-706c41cfac12`.
- **Timeout-mode gate**: the 300 s cap sat below the floor of the mandated
  work (four post-R18-1 full-suite wall times: 320.28 / 320.79 / 321.24 /
  326.65 s) and was unachievable by construction. The user authorized a
  new cap: **360 s** (= worst measured + ~10%, ~9% headroom so the gate
  still binds). Diagnostic cap (120 s) unchanged. Authorization recorded
  verbatim in `timeout-gate-063/timeout-gate-authorization.md`.

## Iteration 24 (Plan063) — planned

- Source: four cap sites (300 → 360) in `s1_validation_capture.py`
  (default, aggregate bound, CLI default) and `s1_validation_contract.py`
  (timed-execution bound); owned-note precondition declared in
  `test_progress_plan047_ownership` via the house `control_record`
  pattern (non-owned timed runs report the suite cleanly; owned no-timeout
  runs exercise the test in full, unchanged).
- Validation: up to 2 timed-mode aggregates at `--timeout 360` (non-owned
  direct module form, same environment as all prior 300 s measurements)
  under `timeout-gate-063/`, then 1 no-timeout pi re-validation
  (`aggregate-061-007`) because the source set changes.
- Fresh allocation: 7200 s wall; 2 timed + 1 no-timeout attempts;
  zero GPU/model/production work; `B+max(1,H)≤8`.

## Success-criteria position

- **S1-1**: met — additive pi-launch class; no owned-path assertion weakened.
- **S1-2**: met (no-timeout pi); timeout-mode gate pending the 360 s
  amendment validation.
- **S1-3**: not met — live S1 calibration recovery requires separate later
  GPU authorization.
- **S1-4**: met — Plan049 chain byte-identical; prior failures/aggregates/
  reports untouched.

## Large artifacts

Per-attempt `plan047-deadline-steps.json` scenario dumps (~50 MB each,
attempts 001–006) are hash-manifested in
`pi-launch/large-artifact-manifest-061.json` and excluded from git.

## Stop point

Iteration 24 stops when both validations pass (S1-2 timeout-mode gate met
at 360 s → stop at the S1-3 GPU-authorization decision point) or when the
2 timed-mode attempts are consumed without acceptance (record residual and
stop).
