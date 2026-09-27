# S1 recovery status — iteration 23 IMPLEMENT closed: S1-2 MET under pi-launch

## Current position

- **S1-2 is MET.** The full owned suite passes when launched by pi:
  `aggregate-061-006` — `Ran 249 tests`, **0 errors, 0 failures**, runner
  returncode 0, `timed_out` false, 78/78 source members byte-unchanged,
  boot `ba1b4efe-ee43-4088-86df-706c41cfac12`, `job_ledger`/`runner_job`
  None (pi branch). Per module: s1_semantics 5, s1_recovery 41, backends 35,
  contracts 15, component_recovery 3, execution 10, budgets 31, supervisor
  101, review_annotations 8 — all OK.
- This is the user-authorized pi-launch provenance class
  (`provenance='pi-launch'`); receipts are never presented as Plan049
  session-bound evidence. The Plan049 chain remains byte-identical.

## Iteration 23 attempt record (Plan062, all no-timeout, 78/78 sources unchanged)

| attempt | evidence | result | fix applied after |
|---|---|---|---|
| 1 (index 4) | `pi-launch/aggregate-061-004` | 247 ok / 1 error / 1 fail | `enclosing_creation_controls` real `os.kill` on synthetic pids; pi note not self-projected |
| 2 (index 5) | `pi-launch/aggregate-061-005` | 248 ok / 1 fail | latent `signal_module` NameError in the enclosing fixture's `stop` closure (name local to `named_creation_controls`) |
| 3 (index 6) | `pi-launch/aggregate-061-006` | **249 ok / 0 / 0 — acceptance** | — |

All three fixes were test-side only (`tests/test_vipe_benchmark_supervisor.py`,
`tests/test_vipe_benchmark_s1_helper_fixtures.py`); no owned-path assertion
was weakened. The `signal_module` NameError and the real-`os.kill` fixture
issues were latent: `test_progress_plan047_ownership` is owned-environment-only
and had never executed successfully anywhere before the pi-launch class.

## Success-criteria position

- **S1-1**: met — additive pi-launch class; no owned-path assertion weakened.
- **S1-2**: **MET** — 249 ok / 0 errors under pi-launch.
- **S1-3**: not met — live S1 calibration recovery requires separate later
  GPU authorization.
- **S1-4**: met — Plan049 chain byte-identical; prior failures/aggregates/
  reports untouched.

## Large artifacts

Per-attempt `plan047-deadline-steps.json` scenario dumps (~50 MB each,
attempts 001–006) are hash-manifested in
`pi-launch/large-artifact-manifest-061.json` and excluded from git.

## Stop point

Per Plan062 stop condition 1, iteration 23 stops here: the next step
(S1-3, live S1 calibration) requires separate later GPU authorization,
which is a decision point outside this plan's authority.
