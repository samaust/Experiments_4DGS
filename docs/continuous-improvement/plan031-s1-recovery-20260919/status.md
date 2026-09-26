# S1 recovery status — iteration 23 PLAN (Plan062 pi-launch residual validation)

## Current position

- **Iteration 22 (Plan061) IMPLEMENT committed as `186e2e4`.** The additive
  `pi-launch` provenance class is implemented; its 3-attempt allocation is
  exhausted at 248 ok / 0 error / 13 fail, with all 13 residual results in
  `test_progress_plan047_ownership` root-caused and fixed (test files only):
  1. `start_doc` kernel-anchor note correlation now applies to both note
     schemas.
  2. `named_creation_controls` fakes `os.kill` like `os.killpg` (synthetic
     pids follow real-pid signal-then-reap semantics; latent
     owned-environment fixture bug).
- **Iteration 23 / Plan062 — PLAN.** Fresh allocation to validate the fixes:
  at most 3 no-timeout pi aggregate attempts (evidence series
  `aggregate-061-004..006`), 7200s wall clock, 6000s source/test cutoff,
  1200s evidence reserve, zero GPU/model/production work.

## Acceptance (S1-2)

First aggregate with: `Ran 249 tests`, 0 errors, 0 failures, runner
returncode 0, `timed_out` false, 78/78 source members byte-unchanged,
stable boot id.

## Success-criteria position

- **S1-1**: met (narrow) so far — additive class; no owned-path assertion
  weakened.
- **S1-2**: pending this allocation (248/249 after iteration 22 attempt 3).
- **S1-3**: not met — separate later GPU authorization still required.
- **S1-4**: met — Plan049 chain byte-identical.

## Next

Launch: `./.local/envs/stg-colmap/bin/python -B docs/continuous-improvement/plan031-s1-recovery-20260919/pi-launch/pi_launch_driver.py aggregate 4 "Plan062 pi-launch residual validation attempt 1: note-correlation + os.kill fixture fixes"`
then verify and commit the milestone.
