# Iteration 11 PLAN — Trusted first-result clocks and advancement

Created [Plan 041](../../../plans/plan_041.md) from [review-011](review-011.md),
[assessment-023-review](assessment-023-review.json), current source and the saved
[objective](objective.md). Current assessment: [assessment-024-plan](assessment-024-plan.json).

Scope is R11-1 only: context derived from the real captured admitted reservation,
worker bootstrap against active ledger authority, explicit helper/failure/result
plumbing, historical recorded-reservation verification, and real checks after
qualification/publication/read-back/reuse and before the next input. Preserve
produced evidence, earlier verified first/raw bytes, numerical contracts and
canonical requests. Broader helper/progress/finalization and full 510-row worker
coverage remain separate milestones; live admission is not ready.

New IMPLEMENT allocation is **2,400 wall seconds before inspection**, **240
seconds reserved for evidence**, execution cutoff **2,160 seconds**, at most
**three 120-second focused invocations** and **two 300-second aggregates**.
These caps explicitly narrow Review's proposed 180/360 seconds to the unchanged
capture/receipt limits (diagnostic max 120; aggregate max 300). Reserve one full
aggregate before optional refinement; each full timeout must fit before cutoff.
A second aggregate needs an invalidating change or concrete recorded concern.
Eight CPU workers maximum including native/helper threads, pools one, serial
suites; existing bounded six script children remain inside parent invocations.
Zero GPU/model/production/setup/download/smoke allocation. Historical consumed
resources and cumulative/method ceilings remain unchanged. The active skill's
standing approval covers the finalized new CPU allocation after main's ceiling
check and saved dispatch authorization.

Main preserves PLAN before freezing IMPLEMENT. Correction-009 must retain
correction-008's lineage, canonicalize post-010 into a new transition with durable
snapshots (its old schema is canonical but its new snapshot points to changed
status.md), then append actual REVIEW/PLAN/IMPLEMENT transitions. Validation-010
and a fresh independent audit bind the new correction and aggregate. Prior raw
logs and staged whitespace disposition remain immutable. Main owns status and
local milestone commits, then continues fresh REVIEW.

Read-only PLAN reconciliation matches all **74 source records**, **38 frozen
records**, and the **447-event / 332,437-byte ledger** with its intact hash chain.
No tests, source edits, production APIs, GPU/model work or git writes occurred.
S1-1/S1-4 retain met support; S1-2/S1-3 remain not met. Plan completion will close
only the specified clock milestone, with whole implementation acceptance,
live readiness and objective completion still false.
