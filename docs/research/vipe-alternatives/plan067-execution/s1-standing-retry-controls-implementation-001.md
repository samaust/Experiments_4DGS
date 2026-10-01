# Standing S1 retry controls

## Authority and limits

The standing retry approval and policy amendment committed at `6d2c9f03`
authorize sequential fresh calibration identities starting at
`S1-calibration-recovery-010`. The new
`vipe-benchmark-s1-standing-calibration-recovery/v1` schema pins both authority
files by SHA256. `attempts_limit` remains one per immutable identity;
`total_attempts_limit` is null. Each reservation retains the 3600-second
deadline, 93600-second cumulative GPU ceiling, 57600-second CPU and setup
ceilings, and existing configuration, recipe, resource and metadata contracts.

Admission rejects gaps, reused identities, any successful predecessor, active
attempts, uncertain cleanup, surviving processes, exhausted budgets and stale
qualification. A next attempt must link the exact failed predecessor and a
nonempty source correction, diagnosis, independent review and current source
qualification. Exact source membership comparisons include added and removed
files. Semantic relevance remains a responsibility of independent review;
the controls bind the actual diagnosis, review, qualification and source diff.

## Preparation interface

`s1_retry.build_correction` takes the failed finish, previous authorization,
diagnosis record, new qualification record, implementation review record and
immutable failed-ledger snapshot. Persist its returned mapping once.

`s1_retry.build_review_proposal` takes the local directory, frozen configuration,
new qualification, implementation review, request date and correction record.
It derives the next sequential identity and returns a read-only REVIEW mapping.
Persist that mapping once, then call `s1_retry.approve_review` with its strict
file record to create the exact DO mapping under standing authority. Existing
public admission, request, reservation, clock, progress, evidence, acceptance
and terminal interfaces continue to enforce their original contracts.

Each preparation checks the captured live ledger prefix and recursively
preserves predecessor history. It performs no allocation or live ledger write.
No fresh approval prompt or finite pool of preapproved identities is required.

## Historical preservation

Identities 001 through 009 retain their historical schemas and receipt bytes.
The ninth finish remains sequence 578 with SHA256
`db47dacfcb3e35f0e35f677af39390677404e5c361ec50a24d7ad72146470fd4`,
failed status, confirmed cleanup, `stop_required: true`, absent terminal and
`poisoned_helper` publication reason. Its raw result and the stopped seventh
result are not accepted or promoted. A standing stop-resolution record grants
only a fresh identity while preserving the original stopped finish.

## CPU validation

Six public standing controls tests passed in 20.045 seconds with the final
downstream worker integration. They exercise 010 REVIEW/DO and actual public
registration, admission, dispatch, reservation and immutable bound clock;
consumed-identity rejection; authority and policy drift; skipped identity;
scientific scope and deadline guards; stale qualification; success, active
attempt, cleanup and cumulative budget blockers; unchanged correction rejection;
and 011 after a failed, cleaned 010 with a new qualified source correction.
Fifteen literal subcases are declared for strict qualification collection.

`s1_standing_retry` and `s1_identity` are required qualification suites. The
identity suite also covers downstream worker routing using fake CPU-only clocks.
Fixtures use captured immutable history and disposable source and ledger trees;
their synthetic qualification receipts are test evidence only. This milestone
does not execute a GPU attempt or modify the live ledger or environment.

Independent Spec and Standards reviewers inspected the controls and downstream
identity changes. Both reported no blocking findings. Standards noted optional
duplication of budget checks across preparation and admission; both checks are
retained as validation at the two public seams.
