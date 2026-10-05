# S1 monitoring corrections — independent review

## Preserved failure and relevant corrections

S1-011 failed after977.925689 seconds and211 qualified rows when the15-second
monitor recovery window expired. It did not reach the3600-second job deadline.
Cleanup is confirmed; no result or terminal receipt is accepted. Exact finish596,
stopped/poisoned-helper history and charges are preserved in outcome92fb54bf.
The exact failed sample stage and timings were not retained, so its active-load
cause remains unproven.

Accounting correction6b8a0d8cbdc2b3f02ff26c15b48f3f836739a0f5 is integrated as
29325ff3. It accumulates physical/logical observations in the same fresh traversal
and retains full stats for accounting scopes/partials and fresh path lengths
elsewhere. Every regular alias still receives a non-following stat; physical
accounting retains the maximum observed size/blocks per inode. No cross-call
cache, tree exclusion, ceiling or deadline change. Actual totals are identical.
Production retained-helper samples improved from1.762/1.693/1.708 seconds to
1.689/1.593/1.621 seconds, all without expiries and with confirmed cleanup.
These idle measurements add headroom, not proof of exact011 causation.

Diagnostic correction8f705168303f94254631c84cb0276d71bccee93a is integrated as
a838d39d. Neutral bounded scalar-only diagnostics capture pending request stage,
dispatch/deadline/acquisition/census/transport/latest-lock timing, detached last
expired sample and16 recent events before poisoning and cleanup. They persist
under primary_failure.monitor_diagnostic without replacing the primary error or
adding I/O, waits or authority. Latest lock state is observational, not complete
contention history. Two-second sample freshness,15-second recovery, ownership,
acceptance, cleanup and resource ceilings remain enforced.

## Independent reviews

Pinned Spec audit of both commits: zero blocking findings. It verifies fresh
accounting/path consumers, alias growth/shrink/replacement behavior, neutral
bounded diagnostics, detached data, first-error preservation, cleanup and retry
history compatibility. Pinned Standards audit of both commits against68c262af reports zero documented
violations and zero optional findings; both isolated worktrees were clean.
Reviews use read-only CPU inspection, no model/GPU operations or live writes.

## Focused validation

33 budget tests passed in0.073 seconds, including fresh alias growth/shrink and
replacement. Eight focused diagnostic/deadline/recovery/resource/ownership tests
passed in14.304 seconds, including two red-to-green failure regressions and real
CPU-helper timeout/cleanup. AST, strict qualification declarations and diff checks
passed. No configured static typechecker is claimed.

Full root integration016 ran 1,186 tests in 544.791 seconds (outer 546.508),
within 600 seconds, with no failures, six known unrelated errors and five skips.
This is not a passing whole-repository claim. Required current qualification017 passed 343 tests / 1,063 subtests in
449.187741 seconds within 600 seconds, zero failures/errors/skips. Strict inner
receipt, host execution record and wrapper validation passed with matching
104-source inventories. Wrapper SHA256
63a97643fe11679451c21bf8f40ba60e7316bb66635c7baa56cea2139ad045a3.
These receipts support preparation of the reviewed fresh012. No failed result is
promoted or replayed; standing correction authority grants no new setup, depth,
download or final-render allocation.
