# Depth model survey tickets

Source: [issue #36](https://github.com/samaust/Experiments_4DGS/issues/36), Plan 068.
Status: **research deliverables complete and independently reviewed** on
2026-09-30. Read the [consolidated report](../../../research/depth-model-survey.md)
and [verification record](../../../research/depth-model-survey-data/verification.md).
GitHub records final issue closure states.

The user approved the seven-ticket breakdown with “I approve.” At publication,
all seven issues were open with `ready-for-agent` and verified native parent and
blocking relationships. Their published bodies matched the local ticket documents.

## Published breakdown

| Ticket | Title | What it delivers | Blocked by |
| --- | --- | --- | --- |
| [#37](https://github.com/samaust/Experiments_4DGS/issues/37) | [Verify the D0–D4 reference comparison and discovery map](01-reference-comparison-and-discovery-map.md) | A source-checked reference section, current artifact/license dispositions, and an initial category map from every supplied search entry point. | None |
| [#38](https://github.com/samaust/Experiments_4DGS/issues/38) | [Compare additional monocular metric depth models](02-additional-monocular-metric-depth.md) | A complete comparison of further metric candidates, their camera/scale assumptions, releases and commercial terms. | None |
| [#39](https://github.com/samaust/Experiments_4DGS/issues/39) | [Compare relative and diffusion depth models](03-relative-and-diffusion-depth.md) | A complete comparison of relative-depth quality, alignment assumptions, diffusion cost, releases and commercial terms. | None |
| [#40](https://github.com/samaust/Experiments_4DGS/issues/40) | [Compare video depth and temporal consistency](04-video-depth-and-temporal-consistency.md) | A complete comparison of temporal evidence, motion/sequence assumptions, releases and commercial terms. | None |
| [#41](https://github.com/samaust/Experiments_4DGS/issues/41) | [Compare multi-view depth and geometric models](05-multi-view-depth-and-geometry.md) | A complete comparison of camera/view requirements, depth/geometry evidence, dynamic-scene limits, releases and commercial terms. | None |
| [#42](https://github.com/samaust/Experiments_4DGS/issues/42) | [Compare efficient and high-resolution depth methods](06-efficient-and-high-resolution-depth.md) | A complete comparison of reported quality/detail versus compute, with exact model combinations, releases and commercial terms. | None |
| [#43](https://github.com/samaust/Experiments_4DGS/issues/43) | [Publish the consolidated depth-model survey](07-consolidated-survey-report.md) | One compact report, reconciled evidence inventories, coverage assessment and justified future-test shortlists. | #37, #38, #39, #40, #41, #42 |

The initial frontier is #37–#42. They can proceed in parallel because the parent
already defines the evidence fields, cutoff and confirmed report/source review
boundary, and source reconnaissance is available. #37 contributes an initial
cross-category discovery map; other tickets can search their own categories
without waiting for it. #43 genuinely needs all six completed sections.

No prefactoring or new application interface is needed for this documentation
and research work. Each #37–#42 ticket covers discovery, source extraction,
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
  Use scoped identifiers where needed; #43 reconciles aliases and duplicate
  observations rather than requiring a shared mutable registry during research.
- Keep D0–D4 reference rows distinct from newly discovered variants. A candidate
  may appear in several category tables for different capabilities. Cross-link
  the same exact variant; record discrepancies for final reconciliation.
- #37 screens all specified discovery entry points and records the initial
  category map. #38–#42 conduct category searches and two rounds of expansion from
  relevant paper comparison tables. Later cross-category leads are recorded
  for the owning section and #43's targeted gap review.
- The cutoff is 2026-09-30. Results are reported paper evidence. Review is the
  user-confirmed report/source boundary, with ordinary document/data checks.
  All work remains within the parent's literature-only scope.

## Coverage and review

| Parent requirement | Ticket ownership |
| --- | --- |
| All starting sources, baseline identity and initial category coverage | #37; #43 verifies combined coverage |
| Further monocular metric candidates and physical-scale assumptions | #38 |
| Relative/depth-alignment and diffusion candidates | #39 |
| Temporal evidence and moving scenes | #40 |
| Multi-view inputs and geometric foundation models | #41 |
| Efficiency, high-resolution and boundary/detail tradeoffs | #42 |
| Source traceability, exact variants, availability and four licensing findings | Every research slice; #43 reconciles |
| Compact report, consolidated evidence, project fit and shortlists | #43 |

Publication verification confirmed that #37–#42 had no blockers and each
blocked #43; #43 was blocked by exactly those six issues. Issue #36 had exactly
the seven published children, all initially incomplete. Implementation used one
research subagent and isolated worktree per prerequisite, then consolidated the
six accepted sections. Separate Standards and Spec reviews passed after the
documented identity and source-locator corrections. Published scores and proposed
future experiments remain separate from local measurements and execution.
