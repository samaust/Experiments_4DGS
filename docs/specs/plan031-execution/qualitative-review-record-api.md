# Qualitative review records

Implementation: `scripts/vipe_benchmark/qualitative_review.py`.
These are new Plan 067 contracts; historical annotation validators remain unchanged.

## Human submission

`blank_review(package_record)` returns an unfilled `plan067-qualitative-review/v1`
form. Complete reviewer `name` (a name or handle), ISO `reviewed_at`, and
`tradeoffs`. `candidate_ids` covers every declared package candidate, including
failed/unavailable arms. `record_kind` is `human`; tests use `fixture`.

The `package` is its exact immutable `{path, sha256, bytes}` record. Each of
`frozen_frame`, `motion`, `artifacts`, `sharpness`, and `overall` contains:

- `observation`: a nonempty observation, or explanation of inability to judge.
- `preference`: `outcome` (`preferred`, `tie`, `unclear`, `unjudgeable`, or
  `not_applicable`) and `candidate_ids`. Preferred outcomes name one or more
  available candidates; ties name at least two. Other outcomes name none.
- `examples`: exact `{candidate_id, selection_id, frame_id}` references or
  `{candidate_id, selection_id, start_time, end_time}` continuous clip intervals.
  Preferences/ties cite each named candidate. Motion preferences require
  an exact continuous clip reference for each selected candidate; sparse
  sequences or still-frame examples are insufficient.

Missing evidence can be explained with `unjudgeable` and no examples. A blank
form never satisfies review. Validation cannot independently establish that an
arbitrary person authored a submitted opinion; provenance must honestly identify
the actual human. Fixture records and fixture packages are rejected for actual
review even when their fields are filled.

## Immutable APIs

All output paths must be new: publication refuses replacement/replay.

- `validate_review(submission, actual=True)` verifies the package, its nested
  artifact records, human identity/date, comparison membership and examples.
- `import_review(package_record, submission_record, output, actual=True)` returns
  the immutable result's file record. The result retains the untouched original
  submission and its file record.
- `freeze_decision(review_record, engineering_eligibility, output, choice=None,
  actual=True)` returns the immutable decision. Eligibility maps every candidate
  to `{eligible: bool, reason: string}`; optional nested evidence records are
  verified. Overall preferences can supply the choice. Ties/unclear outcomes
  remain blocked unless the human gives an explicit `choice` with candidate IDs,
  reason and the same reviewer identity/date. Ineligible/unavailable choices stay
  blocked. No ID or historical metric resolves ties.
- `build_report(review_record, decision_record, output, resource_costs=None,
  actual=True)` retains original observations, decision provenance, candidate
  lineage and unavailable arms. It rechecks decision contents against the human
  record and engineering gates. Missing resource costs are explicitly marked.

`actual=False` exists solely for CPU fixture qualification; such results remain
marked synthetic and cannot satisfy the actual-review ticket. Reports describe
visual opinions and explicitly disclaim measured accuracy, physical depth
accuracy, statistical significance and unseen downstream quality.

## Focused validation

Sixteen CPU tests cover blank/synthetic refusal, identity/date, package/media
substitution, frame/time bounds, sparse motion, not-applicable/unjudgeable
outcomes, immutable replay, blocked ties, engineering exclusion, explicit human
choice, altered imported submissions and automatic winner substitution. Temporary
PNG fixtures also exercise the complete actual-mode package/import/choice/report
path, reject missing candidate selections and readiness inventories, and verify
that media changes after import invalidate later decisions/reports and that
missing generation charges prevent actual review import. These test
records never leave their temporary directories or count as actual feedback. AST
parsing checks the module and tests. Full suite and independent review are
coordinated by the root implementation agent after combining the worktrees.
