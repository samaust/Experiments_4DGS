# S1-011 monitor recovery diagnosis

## Preserved outcome

Reservation 593 consumed identity `S1-calibration-recovery-011` once. Finish
596 has SHA256
`20f29555782e12b9acfe8120d24b935f46a44d7e9c7d1ab3594890ee675ca236`.
It failed after 977.925689 seconds with 211 of 510 rows individually qualified,
confirmed cleanup, no survivors and `stop_required: true`. No aggregate result
or terminal receipt was published. Its work allocation did not expire:
`deadline_exceeded` is false. The primary exception occurred in `worker_sample`:
`TimeoutError: S1 monitor recovery deadline reached`. The poisoned retained
helper subsequently could not publish terminal evidence.

The controller traceback identifies the 15-second monitor recovery window,
which repeatedly discards readings that miss the original two-second
dispatch-to-decision freshness deadline. The actual failed request's acquisition,
pre/post census and pending-stage timings were not preserved. Consequently the
exact reason all eligible readings were unavailable in that window is unproven.
Neither slow resource accounting nor progress-lock contention is established
as the exact S1-011 cause.

## Read-only measurements

The retained tree contains 538,848 regular files and 55,708 directories; 412,750
files are under `jobs`. Full fresh storage accounting is substantial work near
the two-second sampling limit. Host measurements must be distinguished from
sandbox measurements: the sandbox measured approximately 2.71 seconds for disk
accounting, while direct host CPU pre-census/accounting/post-census measured
1.655 and 1.627 seconds. Sandbox timing therefore does not prove the production
deadline was exceeded.

The production retained `Session`, using its explicit Python 3.14 interpreter,
real helper IPC, fresh resource accounting and read-only device queries, returned
three idle-host samples in 1.762, 1.693 and 1.708 seconds with no expiries and
confirmed cleanup. Their helper acquisitions took 1.732, 1.657 and 1.657 seconds.
The exact retained 211-row checkpoint's read and validation took approximately
0.018–0.019 seconds. These runs do not reproduce the timeout under active model
and output-writing load.

## Relevant correction

Fresh accounting now accumulates physical and logical totals during its single
non-following scan. General file paths retain their fresh lengths instead of
all full stat objects; accounting scopes and partial-file identity checks retain
full stat records. This reduces retained allocation and repeated traversal work.
Every regular-file alias still receives a fresh no-follow stat. Physical storage
retains the maximum logical/allocated observation per `(device, inode)` across
all aliases, including growth and shrinkage within one scan. Nothing is cached
across calls and no historical subtree is skipped.

All actual-tree totals remained identical: physical artifacts 121,493,725,184
bytes, logical artifacts 197,992,719,727 bytes, downloads 37,864,969,113 bytes.
The compact scan measured 1.486, 1.445 and 1.444 seconds on the host. Complete
retained-helper samples measured 1.689, 1.593 and 1.621 seconds, all fresh with
zero expiries and confirmed cleanup. This is measured sampling-headroom
improvement, not a claim that the exact S1-011 failure has been reproduced or
that a new attempt will succeed under all loads.

The accompanying bounded failure-capture correction preserves first-failure
sample stages, acquisition/census/wire timings, expiry counts and recent events
before helper retirement. It is needed because those observations were absent
from the S1-011 outcome. Independent review and qualification must include both
corrections before a fresh identity is reserved.

## CPU validation and limits

All 33 CPU accounting tests passed in 0.073 seconds. The new differential test
grows an inode between fresh alias observations, shrinks it before the final
tree inspection, then replaces an alias before the next snapshot. It verifies
maximum observed physical storage, logical per-path bytes and no cross-call
reuse. Existing tests cover hardlinks, symlinks, forbidden trees, concurrent
renames, partials, acquisition receipts, reservations and download locking.

The two-second sample deadline, 15-second recovery window, 3600-second immutable
attempt deadline, resource ceilings, process ownership and cleanup rules remain
unchanged. No model/GPU computation, live ledger writes or environment changes
were performed. S1-011 remains failed; its partial progress cannot be promoted
to an accepted calibration result or replayed under the same identity.
