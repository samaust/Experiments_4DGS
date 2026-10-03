# Final qualitative assessment evidence boundary (#35)

The reporter produces an immutable JSON evidence inventory and Markdown. It
preserves partial work and actual failures. It neither runs experiments nor
closes issues. Missing depth choices, final renders, human review, accounting,
verification or recursive child completion keep the assessment blocked.

## Public interfaces

- `qualitative_assessment.build_assessment(request_record, output, actual=True)`
  rechecks immutable records and writes a new report once.
- `qualitative_assessment.render_markdown(report)` renders the saved report.
- `PYTHONPATH=scripts <explicit-interpreter> -m vipe_benchmark.qualitative_assessment --request request.json --output report.json`
  prints Markdown after publishing JSON. `--fixture` is explicitly nonauthorizing.

A request uses `plan069-qualitative-assessment-request/v1`, `record_kind: actual`
(or `fixture` for CPU tests), and these fields. Each supplied artifact uses
exact `path`, `sha256`, `bytes`; optional missing sections use null.

| Field | Evidence |
| --- | --- |
| `history.segmentation` | Original S2 human submission or immutable import |
| `history.depth` | Original D4 human submission or immutable import |
| `history.supplemental_d2` | Confirmed `plan067-human-observation-supplement/v1`, retaining the exact earlier observation and named frame; a full historical submission also works |
| `depth_review` | #60 extended human submission or immutable import |
| `depth_decision` | #60 validated frozen decision from exactly `depth_review` |
| `final_review` | Human review of a package containing QF-B, QF-M1, QF-M2, QF-N1, QF-N2 final-render candidates; isolated components cannot substitute |
| `execution_accounting` | Accounting document described below |
| `verification` | Verification document described below |
| `issue_snapshot` | Complete recursive issue snapshot described below |

The original S2/D4 observations and supplemental D2 findings retain their
separate packages and scopes. The new visual favorite is preserved separately
from the eligible metric D*. D9/D11 do not become metric candidates by being
visually preferred. D0–D11 dispositions and their original generation, variant,
commercial, scale, runtime and resource evidence remain in the JSON inventory.
Failed, unavailable and missing outcomes are not promoted to successful runs.

## Current native limitation

The current #34 code prepares CPU model input. It does not validate native
training/render publication. The reporter therefore explicitly blocks actual
final experiment completion until that publication validator exists and is
integrated. Five labels, fixture media or a historical package relabeled as a
final render cannot establish completion. No current report closes #35.

## Accounting

`plan069-assessment-accounting/v1` contains:

- `ledger`: immutable JSONL ledger snapshot. Every event sequence, previous
  hash and event hash is checked without writing or locking the live ledger.
- `resources`: immutable resource observation JSON, preserved unchanged.
- `budget_authorization`: immutable applicable budget authorization JSON,
  preserved unchanged.

All terminal attempts, including failures, retain their elapsed consumption
and cleanup fields. Active allocations keep the assessment blocked. Resource
observations are labeled as snapshots, not assertions of current host state.

## Verification

`plan069-assessment-verification/v1` contains immutable `tests`,
`qualification`, `standards_review`, and `spec_review` JSON records.

The full-suite document retains exact nonnegative `tests_run`, `failures`,
`errors`, `skipped` counts, including known unrelated errors; the reporter
does not call an errored suite passing. Qualification uses the existing
`s1-cpu-aggregate/v2` receipt, counts, nonempty verified source inventory,
unchanged before/after sources, and original logs/runner. A failed
qualification blocks the assessment.

Each independent review uses `plan069-assessment-code-review/v1`, its
`axis` (`standards` or `spec`), `record_kind` (`actual` or `fixture`),
named `reviewer`, nonempty immutable `sources` inventory, and a
`blocking_findings` list. Unresolved findings block completion. A bare
`status: passed` object is not accepted as verification.

## Recursive issue snapshot

`plan069-issue-snapshot/v1` contains `repository:
samaust/Experiments_4DGS`, ISO `captured_at`, `roots: [3,18,23]`, and
`issues` keyed by canonical decimal issue number. Each issue has
`state: OPEN|CLOSED` and a `children` list of integer numbers.

Include all actual children and descendants. The reporter rejects missing
children, cycles and omitted known native relationships:
#18 → #19–23/#44, #23 → #34/#35/#45, #44 → #56–59,
#45 → #60–62. A closed parent with an open descendant is still ineligible.
Required unfinished #34/#44/#45/#60/#61/#62 work blocks final assessment.
Historical preparation references #4–17 must also appear as closed dependencies
in the snapshot. Missing or reopened preparation issues keep the assessment
blocked. These references are reported separately from native child edges:
#3 currently has no native subissues, and its child list must remain faithful
to GitHub rather than acquiring invented #4–17 edges.

An offline saved snapshot cannot establish current GitHub state or authorize
closure; live recursive checks remain necessary when closing issues.

## Claim limits

These are named humans' visual judgments of bound outputs, not annotation
accuracy, measured physical depth accuracy, statistical significance or
unseen downstream quality. Component commercial eligibility does not establish
commercial clearance for the full reconstruction stack.
