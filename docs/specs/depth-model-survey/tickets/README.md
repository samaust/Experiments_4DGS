# Proposed tickets for the depth model survey

Source: [issue #36](https://github.com/samaust/Experiments_4DGS/issues/36), Plan 068.
Status: **draft breakdown awaiting user approval; no child tickets published**.
Prepared 2026-09-30 after reading the live issue and all comments. The issue was
open, with no comments, blockers or children.

## Proposed breakdown

| Draft | Title | What it delivers | Blocked by |
| --- | --- | --- | --- |
| [T1](01-reference-comparison-and-discovery-map.md) | Verify the D0–D4 reference comparison and discovery map | A source-checked reference section, current artifact/license dispositions, and an initial category map from every supplied search entry point. | None |
| [T2](02-additional-monocular-metric-depth.md) | Compare additional monocular metric depth models | A complete comparison of further metric candidates, their camera/scale assumptions, releases and commercial terms. | None |
| [T3](03-relative-and-diffusion-depth.md) | Compare relative and diffusion depth models | A complete comparison of relative-depth quality, alignment assumptions, diffusion cost, releases and commercial terms. | None |
| [T4](04-video-depth-and-temporal-consistency.md) | Compare video depth and temporal consistency | A complete comparison of temporal evidence, motion/sequence assumptions, releases and commercial terms. | None |
| [T5](05-multi-view-depth-and-geometry.md) | Compare multi-view depth and geometric models | A complete comparison of camera/view requirements, depth/geometry evidence, dynamic-scene limits, releases and commercial terms. | None |
| [T6](06-efficient-and-high-resolution-depth.md) | Compare efficient and high-resolution depth methods | A complete comparison of reported quality/detail versus compute, with exact model combinations, releases and commercial terms. | None |
| [T7](07-consolidated-survey-report.md) | Publish the consolidated depth-model survey | One compact report, reconciled evidence inventories, coverage assessment and justified future-test shortlists. | T1–T6 |

The initial frontier is T1–T6. They can proceed in parallel because the parent
already defines the evidence fields, cutoff and confirmed report/source review
boundary, and source reconnaissance is available. T1 contributes an initial
cross-category discovery map; other tickets can search their own categories
without waiting for it. T7 genuinely needs all six completed sections.

No prefactoring or new application interface is needed for this documentation
and research work. Each T1–T6 ticket covers discovery, source extraction,
availability, licensing, readable findings and verification for one bounded
section. There is no separate horizontal ticket for collecting data, checking
licenses, or building a validator.

## Common handoff and ownership

- Each research ticket owns its named section and the supporting search, model,
  benchmark and license records. It can be reviewed on its own against primary
  sources. It does not wait for another section's draft or edit that section.
- Reuse issue #36's evidence contract: stable source/model/variant/protocol
  identifiers, exact versions and table locations, metric definitions and
  directions, input and alignment settings, reporting provenance, release
  dispositions, four commercial-use findings, and explicit missing evidence.
  Use scoped identifiers where needed; T7 reconciles aliases and duplicate
  observations rather than requiring a shared mutable registry during research.
- Keep D0–D4 reference rows distinct from newly discovered variants. A candidate
  may appear in several category tables for different capabilities. Cross-link
  the same exact variant; record discrepancies for final reconciliation.
- T1 screens all specified discovery entry points and records the initial
  category map. T2–T6 conduct category searches and two rounds of expansion from
  relevant paper comparison tables. Later cross-category leads are recorded
  for the owning section and T7's targeted gap review.
- The cutoff is 2026-09-30. Results are reported paper evidence. Review is the
  user-confirmed report/source boundary, with ordinary document/data checks.
  All work remains within the parent's literature-only scope.

## Coverage and review

| Parent requirement | Ticket ownership |
| --- | --- |
| All starting sources, baseline identity and initial category coverage | T1; T7 verifies combined coverage |
| Further monocular metric candidates and physical-scale assumptions | T2 |
| Relative/depth-alignment and diffusion candidates | T3 |
| Temporal evidence and moving scenes | T4 |
| Multi-view inputs and geometric foundation models | T5 |
| Efficiency, high-resolution and boundary/detail tradeoffs | T6 |
| Source traceability, exact variants, availability and four licensing findings | Every research slice; T7 reconciles |
| Compact report, consolidated evidence, project fit and shortlists | T7 |

Before publication, obtain approval of granularity and blocking edges as required
by the to-tickets skill. Then create one `ready-for-agent` issue per approved
draft, referencing #36 and using native child and blocking relationships.
Replace draft blocker names with actual issue numbers after creation. Preserve
the parent issue's title, body, labels and open state; do not add a parent comment
or close it as part of ticket publication. Verify all created relationships and
published bodies before recording the publication result here.
