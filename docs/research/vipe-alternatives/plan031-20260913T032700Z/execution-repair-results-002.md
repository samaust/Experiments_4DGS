The second execution repair milestone passes all **288 benchmark fixtures** in
[validation006](implementation-validation-006.json). Its immutable snapshot
preserves 63 source/test files. These are CPU fixtures; native qualification and
model outcomes remain tied to the original allocated jobs.

The [exact SAM2 source review](actual-e2-source-review.md) identified a native
warning that returns masks after skipping required postprocessing. The
[focused guard](sam2-postprocessing-guard-repair.md) is now integrated around
the entire S2/S4 segmentation call, including lazy video iteration. An adapter
fixture confirms that the warning raises, no fallback mask is exported, and
pair state resets. Other warnings retain their existing behavior. E2 remains
failed and is not replayed.

The [UniDepth source review](actual-e4-source-review.md) establishes that the
native confidence array represents relative predicted error. D0 and D1 now
describe lower values as greater confidence, preserving the array and its
exclusion from scale support/weighting. The adapter records observed processed
camera K separately from image dimensions. D1 metadata discloses half-integer
native ray coordinates and scalar camera scaling before rounding raster sizes
to multiples of 14; no new image/camera conversion is applied. D0 retains its
historical centered, equal-focal K and does not claim a verified native pixel
convention.

A [read-only accounting measurement](../../../../.local/vipe-alternatives/plan031-20260913T032700Z/accounting-snapshot-timing-001.json)
took 1.184915 seconds. The previous cache timestamp was set before scanning,
so a scan longer than one second could expire its own reuse interval and cause
another whole-tree scan before every socket read. The timestamp now starts
the one-second interval after completion. A simulated slow-inventory fixture
checks reuse, subsequent refresh, and exact exhaustion from intervening bytes.
Pending reads, cumulative consumption, retained-file accounting and hard limits
are unchanged. This fixes cadence for subsequent workers; no live job is
restarted or patched in memory.

[E4 implementation preservation](active-E4-implementation-preservation.json)
binds its already loaded execution modules to validation005. Its native import
qualification subprocess sources remain unchanged. The three earlier failed
setups retain their original evidence and consumed allocations; [E3's upstream
HTTP 403](E3-setup-failure.json) blocks only SAM3-dependent work.

All charged preparation time is retained. The E4 review exceeded its internally
assigned 600-second cap by 17.570 seconds during report publication and stopped;
the full 617.570 seconds and the overrun are recorded in the append-only ledger.
The plan's overall CPU preparation allowance remains unexhausted. This exception
must remain visible in the final accounting assessment.
