# Plan062 — Pi-launch residual validation (iteration 23)

## Status

Active. Continues the user-authorized pi-launch work from Plan061
(iteration 22). Scope: validate the two test-side residual fixes that
brought the pi-launched full aggregate from 248/249 to the expected
249/249, under a fresh iteration allocation.

## Context

Iteration 22 (Plan061) implemented the additive `pi-launch` provenance
class and consumed its 3-attempt allocation:

- attempt 1: 177 ok / 57 error / 23 fail (schema gate, fixed)
- attempt 2: 247 ok / 11 error / 3 fail (rename + projection, fixed)
- attempt 3: 248 ok / 0 error / 13 fail — all 13 results in
  `tests.test_vipe_benchmark_supervisor.HelperSessionTests.test_progress_plan047_ownership`

The two residual root causes are fixed in the working tree (test files
only):

1. `test_progress_plan047_ownership`: the kernel-anchor note correlation
   update (`start_doc['note']`) now applies for both note schemas.
2. `named_creation_controls` (s1 helper fixtures): fakes `os.kill` like
   `os.killpg`, so synthetic pids follow real-pid signal-then-reap
   semantics (latent owned-environment fixture bug; the fixture had never
   run in an owned environment before Plan061).

## Objective

One passing pi-launched no-timeout full aggregate:

- `Ran 249 tests`, `0 errors`, `0 failures`
- runner returncode 0
- `timed_out` false (no timeout mode; the 300s cap never applies)
- 78-of-78 source members byte-unchanged (`sources_before == sources_after`)
- stable boot id

## Allocation (fresh, iteration 23)

- 7200s wall clock total for the iteration
- 6000s source/test cutoff; 1200s evidence reserve
- at most 3 no-timeout pi aggregate attempts (continuing the `-061-`
  evidence series at indices 4, 5, 6)
- zero GPU / model / production work
- `B+max(1,H) <= 8` unchanged

## Launch form

From the repository root:

```
./.local/envs/stg-colmap/bin/python -B docs/continuous-improvement/plan031-s1-recovery-20260919/pi-launch/pi_launch_driver.py aggregate <index> "<reason>"
```

The launch note continues to bind `plans/plan_061.md` as the
class-establishing record (the pi-launch provenance class and its
acceptance are defined there); this plan is the active allocation record.

## Invariants (unchanged from Plan061)

- additive only; no owned-path assertion weakened
- Plan049 chain byte-identical
- no timeout/cap/suite/fixture/gate shrink
- full 510/340/170 acceptance guard, full parser acceptance case, and the
  114 deadline_steps callbacks all remain mandated
- pi receipts carry `provenance='pi-launch'` and are never presented as
  Plan049 session-bound evidence
- no session-proof or tool-event fabrication

## Stop conditions

1. Acceptance met -> S1-2 recorded met; stop at the separate later
   GPU-authorization decision point (S1-3).
2. All 3 attempts consumed without acceptance -> record the exact
   residual set and stop; no further launches without new authorization.
