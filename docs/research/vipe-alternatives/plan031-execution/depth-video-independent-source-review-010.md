# D9 source010 / D10 source011 independent review

Canonical HEAD: `a520ea38d76bcc1d90c83e86659dbbb96fcaea1d`. The only helper change
since D9 source009 and D10 source010 is
`scripts/vipe_benchmark/depth_video_frame_authorization.py` (commits `789f2c9a`,
`c69e5389`; tests in `a520ea38`), which is in both closures. It lets the D10
prerequisite accept a protected D9 qualification successor when the DO-bound
record is stale, under identical setup, native source, interpreter, profile and
dependency bytes, with every existing check applied to the successor. The user
approved this approach on 2026-10-04.

## Standards — PASS (after one fix round)

Initial review: FAIL. A stale bound record under the caller-owned exclusive
ledger lock took a second flock and deadlocked the protected grant path, and
malformed records escaped as non-ValueError exceptions. `c69e5389` reuses the
caller's locked events, ignores malformed charge rows and raises ValueError for
missing manifests or prefixes. Re-review: PASS. Remaining judgement calls (an
untested duplicate-bound-charge case; a deleted evidence file surfacing as an OS
error, as elsewhere in the module) are non-blocking.

## Spec — PASS (after one fix round)

Initial review: FAIL on the same deadlock, plus successor charge/prefix checks
relying on the recovery-only lineage path. `c69e5389` checks the successor's cpu
charge and requires its own finalization prefix ending at that charge (which the
hash chain makes a true ledger prefix), confines successors to the run's
`prepare/` directory and requires the DO-bound prefix to contain the bound
charge. Re-review: PASS; no new authority, attempts or budget. `a520ea38` adds a
mutation-checked test that a successor outside `prepare/` is never selected.

Validation: 47 tests across the frame authorization, frame ledger and D10 wrapper
modules pass; scoped mypy is clean. These reviews grant no execution authority.
