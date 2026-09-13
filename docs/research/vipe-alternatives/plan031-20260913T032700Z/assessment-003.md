Stopped-run assessment, 2026-09-13 07:20 UTC.

**Plan 031 execution is blocked by an upstream network failure.** The
implementation and 288 CPU fixtures are committed, but the bounded comparison
is incomplete and no replacement-quality conclusion is supported. This
assessment supersedes assessment002 for current status; historical assessments
and all consumed work remain preserved.

| Criterion | Status | Evidence and limitation |
| --- | --- | --- |
| P31-1: Reproducibility | unverified | Frozen input/configuration/protocol checks pass; all 63 validation006 source/test hashes were reverified at the stop. Original inputs, annotations, S0 outputs and implementation snapshots remain intact. E5–E7 assets/dependencies and remaining model outputs are unqualified. |
| P31-2: Engineering | unverified | All 288 benchmark fixtures pass and both S0 branches qualify actual execution. E1/E2 implementation failures, E3 upstream HTTP 403 and E4 upstream connection reset are explicit. Standalone forward execution and diagnostic geometry have not qualified. |
| P31-3: Independent scoring | not met | All 232 proxy annotation images have independent review under the user-authorized amendment. Genuine independent truth and unsupported roles/temporal labels remain unverified. No staged metric aggregation ran. |
| P31-4: Controlled experiments | not met | All 53 planned slots are accounted for, but only preparation, annotation checking and the two S0 branches completed. Four setup attempts failed; 42 slots are blocked and three repeats skipped. No depth, motion, neighbor, geometry or combined comparison was executed. |
| P31-5: Accounting and integrity | not met | The ledger reconciles 2 GPU attempts/506.489 seconds, 4 setup attempts/3,099.948 seconds and 6,735.913 CPU preparation seconds, with no active reservations. All started-attempt cleanup is confirmed. Plan-wide time/download/storage ceilings remain unexhausted, but the internal E4 source review exceeded its 600-second cap by 17.570 seconds during report publication. That exception is retained without refund/reset. |
| P31-6: Supported conclusions | not met | The formal staged aggregation and final report remain unstarted. Dependency removal, measured replacement quality and physical accuracy remain unverified. Existing license reviews retain their exact scopes and restricted/unverified findings; no commercial-use combination is endorsed. |

Stop validation and complete slot reasons are in
[matrix-accounting003](matrix-accounting-003.json). Current retained storage is
21,986,656,256 bytes and conservative download accounting is 3,632,993,923 bytes;
E4's higher recorded peaks are preserved in its failure evidence. Pending reads
from the failed proxy remain charged. Differences between live peaks and final
retained footprints do not create additional attempts.

The approved host command was:

```text
.local/envs/stg-colmap/bin/python scripts/basketball_vipe_benchmark.py --run-id plan031-20260913T032700Z setup --environment E4
```

The root failure was `ConnectionResetError: [Errno 104] Connection reset by
peer` during an upstream proxy receive. UV subsequently reported
`Connection refused (os error 111)` after the listener stopped. The exact
underlying UV command, logs, transfer receipt and cleanup are retained in
[E4 failure evidence](E4-setup-failure.json).

This is not a confirmed Codex permission denial; an upstream network/access
problem remains unresolved. The outside-sandbox invocation was approved and
no missing allow rule was reported. A duplicate rule would not repair the
reset. [AGENTS.md](../../../../AGENTS.md) states: “A command already attempted
outside the sandbox does not get another permission retry.” Its required
failure stop applies. No E5–E7 acquisition, consumed-build retry or substitute
network route was attempted afterward.

Resume requires explicit user instruction after the network issue is resolved.
Only unstarted accounted slots can reopen under the existing allocations;
E1–E4 have no remaining setup attempts. Their reruns require a new explicit
allocation. The unused staged aggregation/report allocation is preserved so
later authorized execution need not repeat scored comparisons. This stop
record is not the formal benchmark report and performs no scoring.

Key evidence: [validation006](implementation-validation-006.json),
[S0 outputs](baseline-segmentation-results.json),
[reviewed proxy labels](automated-review-results.md),
[E1 failure](E1-setup-failure.json), [E2 failure](E2-setup-failure.json),
[SAM3 access failure](E3-setup-failure.json),
[repair and review-time exception](execution-repair-results-002.md), and
[D1 asset license review](license-review-E4-assets-20260913T065749Z.md).
