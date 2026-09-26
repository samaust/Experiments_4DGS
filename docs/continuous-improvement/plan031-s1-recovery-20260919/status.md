# S1 recovery status — iteration 22 IMPLEMENT closed (Plan061 pi-launch owned mode)

## Current position

- **Iteration 22 / Plan061 — IMPLEMENT CLOSED.** The user-authorized additive
  `pi-launch` provenance class is implemented and was exercised by three
  no-timeout full aggregates (plan061 allocation: max 3, now exhausted).
  No GPU/model/production work; Plan049 chain byte-identical; all mandated
  gate work preserved (510/340/170 acceptance guard, full parser case,
  114 deadline_steps callbacks).

## Implementation (committed)

- `scripts/vipe_benchmark/s1_validation_contract.py`: additive
  `plan061-pi-launch/v1` support — `PI_RUN`, `pi_launch_output_paths()`,
  `pi_launch()`, module-level `typed_identity_binding()`; schema dispatch in
  `no_timeout_launch()`; pi branch in `validate_execution()` (requires
  `job_ledger is None` and `runner_job is None`); schema-conditional
  authority in `validate_creation()`.
- `scripts/vipe_benchmark/s1_helper_session.py`: `LAUNCH_LAYOUTS` for both
  plan049 and pi layouts; `_launch_anchor()` generalized to select the layout
  from the live stdin parent and the `-049-`/`-061-` directory names;
  `owned_workload()` schema-aware (accepts both note schemas, preserves every
  plan049 re-verification, adds the fixed pi authority check).
- `scripts/vipe_benchmark/s1_validation_capture.py`: `creation['authority']`
  binds the note's `admission` (plan049) or `authorization` (pi-launch).
- `docs/.../pi-launch/pi_launch_driver.py` (new, outside the 78-member source
  set): writes + self-verifies the launch note via `pi_launch`, publishes the
  exec-start event, redirects fds, and `execve`s the official module-form
  capture command.
- Tests (user-authorized test changes):
  - `tests/test_vipe_benchmark_supervisor.py::test_progress_plan047_ownership`
    is schema-aware: pi notes use the authorization record for the
    forged-authority case and the bindings tuple for the stale-projection
    case; plan049-only projection is skipped for pi notes; the kernel-anchor
    note correlation update applies to both schemas.
  - `tests/test_vipe_benchmark_s1_helper_fixtures.py::named_creation_controls`
    now fakes `os.kill` like `os.killpg` (synthetic pids must not be
    real-signaled; real-pid semantics are signal-then-reap).

## Attempt record (all no-timeout, boot ba1b4efe, sources 78/78 unchanged)

| attempt | evidence | result | root cause fixed next |
|---|---|---|---|
| 1 | `pi-launch/aggregate-061-001` | 177 ok / 57 error / 23 fail | `owned_workload` early schema gate rejected the pi schema (one line) |
| 2 | `pi-launch/aggregate-061-002` | 247 ok / 11 error / 3 fail | missed `typed_binding`→`typed_identity_binding` rename; plan049-only `admission` projection in the test |
| 3 | `pi-launch/aggregate-061-003` | 248 ok / 0 error / 13 fail | all 13 in `test_progress_plan047_ownership`: exec-start/note correlation guard (test) + `os.kill` not faked for synthetic pids (fixture, latent owned-environment bug) |

The two residual fixes (test files only) are applied and committed with this
milestone. The three per-attempt `plan047-deadline-steps.json` scenario dumps
(~50 MB each) are recorded by hash in
`pi-launch/large-artifact-manifest-061.json` and excluded from git to keep
the evidence tree comparable to prior run directories.

## Success-criteria position

- **S1-1**: met (narrow) so far — additive class; no owned-path assertion
  weakened; plan049 receipts unchanged.
- **S1-2**: not yet met — 248/249 under pi; one further aggregate attempt is
  needed to validate the two residual fixes.
- **S1-3**: not met — separate later GPU authorization still required.
- **S1-4**: met — Plan049 chain byte-identical; prior failures/aggregates/
  reports untouched.

## Next (iteration 23 / Plan062)

Fresh allocation: at most 3 no-timeout pi aggregate attempts (expected: one).
Launch: `./.local/envs/stg-colmap/bin/python -B docs/continuous-improvement/plan031-s1-recovery-20260919/pi-launch/pi_launch_driver.py aggregate <index> "<reason>"`
from the repository root. Acceptance: `Ran 249 tests`, `FAILED (errors=0)`
or `OK`, runner returncode 0, `timed_out false`, 78/78 sources unchanged.
