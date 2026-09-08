# Iteration 005 implementation results

[Plan 021](../../../plans/plan_021.md) ends with **incomplete readiness**.
All 16 cases/32 original operating states passed read-only admission. Six new
versioned source modules and the fixed toy suite were implemented. Both frozen
suite invocations passed all implemented assertions, but Review found missing
required case-12 candidate offset/mixed assembly coverage and case-14 actual
cold-transform cache coverage. The test source was already frozen, preventing
correction under this plan. Subsequent static inspection found an additional
retained implementation defect: the `residual_only` parameter of
`projection_second` is unused, so transform-only projection still computes HP/H.
An earlier progress message incorrectly claimed that branch insertion succeeded;
source inspection corrected that claim before any scientific invocation.

Scientific entry was prohibited and never attempted. The
[readiness status](../../experiments/basketball-shared-timing-v14/readiness-status.json)
and [decision](../../experiments/basketball-shared-timing-v14/decision.json)
explicitly record incomplete readiness and unverified canonical/public numerical
qualification. No failure is recast as a scientific pass or rejection.

The [experiment report](../../experiments/basketball-shared-timing-v14.md) provides
source scope, all acceptance statuses and links to retained inputs, validation,
commands, source findings and budget records. [Validation](iteration-005-validation.md)
records the applicable checks and their limits. Parent-owned status and
[authorization](iteration-005-plan021-authorization.json) were preserved.

Admission took 285.503565367 seconds from T0. The two toy suites consumed
1.439400610 and 1.434029730 seconds; both use test hash
`4328425c083266f87fc38594d293a148becee179be4a8660cde777eefd834cdc`.
Scientific invocations/entries/time and all forbidden/training work remain zero.
All owned toy sessions ended and no scientific worker was launched. Final elapsed
phase time including commits and commit IDs are delivered to the parent handoff.

A1 passed. A2 remains incomplete; A3/A4 are unverified. The available A5 retention
milestone is complete after its local commits, while overall Plan021 acceptance
is incomplete. SC-01/SC-03 remain unmet. Parent reassesses all criteria; existing
SC-02/SC-04 evidence and historical limitations are unchanged. Finishing this
allocation does not stop the active loop: next Review must identify the exact
missing readiness/source prerequisites and Plan must allocate their finite repair.
No unused Plan021 scientific allocation can be reused after this handoff.
