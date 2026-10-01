# Plan 069 specification publication

Published from task-start commit `6b86bab0` using the to-spec skill. The user
approved the seven-model extension, review before new depth-dependent #34 runs,
all-seven-plus-D2 clip coverage, and the existing worker/admission/ledger and
package/review testing seams. This milestone specifies future work; it performs
no model installation, download, inference, training, rendering or ledger mutation.

## Published specs and native issue relationships

| Issue | Work | Parent | Blocked by |
| --- | --- | --- | --- |
| [#44](https://github.com/samaust/Experiments_4DGS/issues/44) | [Extended depth generation](../depth-comparison-extension.md) | #18 | None |
| [#45](https://github.com/samaust/Experiments_4DGS/issues/45) | [Human review and new metric-depth choice](../depth-comparison-review.md) | #23 | #44 |
| [#34](https://github.com/samaust/Experiments_4DGS/issues/34) | Existing downstream generation and final-render review | #23 | #33 (closed), #45 |
| [#35](https://github.com/samaust/Experiments_4DGS/issues/35) | Existing final assessment, expanded to include the new depth evidence | #23 | #34 |

#18 retains execution ownership and gains child #44. #23 retains human comparison
ownership and gains child #45. All six affected issues remain open and carry
`ready-for-agent`. #34 can continue reusable preparation while its new
depth-dependent dispatch waits for #45. No issue was closed or reopened.

## Reconciliation with existing work

The [before snapshot](before.json) preserves the four original open issue bodies,
native relationships and ten protected file hashes. The updated bodies retain
their earlier text below an explicit prospective amendment; local open-ticket
copies now match the live GitHub scope instead of their stale annotation-era
wording. The original ticket manifest remains a historical publication record.

The [after snapshot](after.json), verified at 2026-10-01 01:25:07 UTC, records all
six published body hashes and native relationships. GitHub body equality, labels,
open states, untruncated relationship lists, preserved original child sets and
37 completed issue states were checked against live reads. The graph is
generation #44 → review #45 → downstream #34 → assessment #35, with parents #18/#23
preserved. Completed preparation, D0–D4 work, initial review and survey work keep
their historical acceptance scopes.

The latest #18 comment confirms standing S1 correction/retry authority. The
new specs preserve that independent authority and its budgets. Existing D4
proposal contracts and source qualification remain evidence for their original
scope; future D* proposals require their own current bindings and admission.

## Validation and limits

- Both new specs follow all seven to-spec sections, with 36 generation and 24
  review user stories. Their Implementation Decisions contain no specific file
  paths or code snippets.
- Document checks passed for all 14 task documents, 29 new/changed local Markdown
  links, JSON readability, whitespace, seven pinned survey inventory rows, six
  published body hashes and ten protected files. `git diff --check` passed.
- Original Plan 031, original benchmark/component configurations, study/protocol,
  qualitative amendments, D4-specific proposal and S1 standing authority records
  retain their before-snapshot hashes.
- No executable source or test was changed. Runtime/CPU qualification and
  independent implementation review are future acceptance gates, not claims
  established by this documentation milestone.
- New depth budgets remain to be proposed and approved under current admission
  rules. The specs grant no resource increase or model attempt.

Navigation is updated in [Plan 069](../../../../plans/plan_069.md), the active
Plan 067, workflow README and [execution index](../README.md). Original human
reviews and media are preserved. Subsequent implementation must refresh live
issue, working-tree and allocation state before using shared interfaces.
