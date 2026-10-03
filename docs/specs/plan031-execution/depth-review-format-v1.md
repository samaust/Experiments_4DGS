# Extended depth review and metric decision

Issue #60 adds `plan069-depth-review/v1` for an extended aggregate package. It
preserves the five Plan 067 observation criteria, exact frame/time examples,
reviewer identity/date and tradeoffs. The overall visual preference is separate
from `metric_choice`:

```json
{
  "outcome": "selected",
  "candidate_ids": ["D5"],
  "reason": "Human justification for this metric choice",
  "examples": [{"candidate_id": "D5", "selection_id": "camera1-selection-175", "frame_id": 175}]
}
```

The other metric outcomes are `tie` (at least two candidates), `unclear`,
`unjudgeable` and `not_applicable` (no candidates); every outcome needs a reason.
A relative visual favorite such as D11 can coexist with another metric choice.

`depth_review.import_review` verifies the exact package, submission and media.
`freeze_decision` publishes an immutable `plan069-depth-decision/v1`.
`validate_decision` recomputes the decision before downstream consumption.
Existing files cannot be overwritten; changes require new package/review records.

Only D2/D5/D6/D7/D8/D10 can become D*. They need completed actual generation,
exact commercial and runtime receipts, accepted input lineage and passing frozen
fit/check scale receipts. Missing engineering gates or failed scale gates retain
the requested choice in a **blocked** decision. They never create a fallback.
D9/D11 are visual-only; D0/D1/D3/D4 are historical references. D2's CPU preflight
alone is insufficient for metric eligibility.

The extended viewer exports this version only for packages bound to a depth
aggregate request. Historical reviews and their validator remain unchanged.
CPU fixtures use `record_kind: fixture` and explicit `actual=False`; their
reviews and decisions never satisfy actual human feedback or authorize execution.
A ready human metric decision is evidence, not an execution reservation.
