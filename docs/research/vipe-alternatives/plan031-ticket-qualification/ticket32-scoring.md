# Ticket #32: scoring fixture qualification

This milestone qualifies scoring interfaces with CPU fixtures only. It publishes
no scientific scores, finalist decisions or experiment allocations and modifies
no live ledger or historical checkpoint.

## Behavior

Independent aggregate requests explicitly select `scoring_mode=independent`.
Request construction resolves successful ledger-bound parents and validates them
before dispatch. The worker independently repeats validation. Human mask scoring
uses the existing annotation validator. Finalist and final stages require
independent parent evidence and identical frozen input/truth records; finalist
selection also verifies the raw count artifact and its source request bindings.
Proxy parent checkpoints, proxy comparisons and proxy raw counts are rejected.

The default remains the historical legacy path. Previously frozen proxy policy
and checkpoints are not relabeled or overwritten. New evidence records include
the scoring mode and input/truth lineage. Actual scoring ticket #33 must request
independent mode explicitly; this fixture qualification does not authorize it.

## Validation

The tests use literal count examples: person/ball Dice 0.8, foreground leakage
0.2, retained features 0.8, and a weaker boundary F1 of 0.4. Equal scores select
the lower prescribed ID. Failed candidates cannot enter rankings. The worker
result is admitted into a temporary ledger, resolved through the checkpoint
handoff, and read through the reporting interface. A pre-checkpoint orphan is
unavailable; changed checkpoint bytes are rejected; a second publication cannot
replace the frozen checkpoint. Fit-domain evidence cannot become selection-domain
evidence, and swapped scale roles cannot pass eligibility. Input/truth changes
and raw-count source mismatches are rejected. Physical accuracy remains unverified.

Affected files validated in the dedicated CPU environment:

- Aggregation: 23 tests passed.
- Reporting: 4 tests passed.
- Execution: 13 tests passed.
- Metrics: 12 tests passed.
- Python compilation and `git diff --check`: passed.

Full-suite validation and independent review are performed after integration by
the coordinating agent. The small finalist fixtures stand in for an already
validated human mask checkpoint; external human annotation acceptance is owned
by ticket #30, and this milestone supplies no human annotation bundle.
