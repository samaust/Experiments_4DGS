# Verify the D0–D4 reference comparison and discovery map

## Parent

[Issue #36 — Survey depth estimation models and compare published evidence](https://github.com/samaust/Experiments_4DGS/issues/36)

## What to build

Give the reader a verified reference section explaining what D0–D4 represent,
which published comparisons apply to their exact variants, and what code,
weights and commercial permissions are available. Alongside that complete
reference section, screen all supplied discovery entry points and record an
initial map of additional candidates to the survey categories.

Deliver readable findings, supporting evidence records and source checks using
the parent's existing evidence contract. Other category sections can begin
from that contract and the existing reconnaissance while this section proceeds.
This is literature and release review within the parent's scope.

## Acceptance criteria

- [ ] D0 historical ViPE/UniDepth, D1 standalone UniDepth V2-L, D2 DA3METRIC-LARGE, D3 Metric3Dv2 ViT-L and D4 Depth Pro have exact identity and role records. D0/D1 are implementation controls within one family; wrapper-specific performance is not invented from a model paper.
- [ ] All discovery entry points specified by the parent are screened in an initial pass, with query/source, date, search coverage, access problems, inclusion/exclusion reasons and cross-category leads recorded. This goes beyond checking whether a URL opens.
- [ ] Relevant reference-paper comparisons are extracted with exact versions, table/page-or-section/row, variant, dataset, protocol, metrics and copied-versus-rerun provenance. Unsupported mappings between paper variants and selected checkpoints are explicit.
- [ ] The reference comparison groups compatible settings and preserves incompatible or missing results as separate or unresolved evidence. Training regime, inputs, depth meaning and scale/alignment conditions are visible.
- [ ] Official implementations and exact checkpoint releases have availability, access, environment and paper-versus-release dispositions supported by primary sources.
- [ ] Each reference has separate findings for commercial code use, weight use, inference/output use and any explicit licensing offer, including relevant wrapper/dependency qualifications and uncertainty.
- [ ] Readable reference findings are accompanied by search, model, benchmark and license records with documented identifiers, units and missing-value conventions compatible with the parent contract.
- [ ] Every reported number and material release/license claim is checked against its cited source. The verification note records contradictions and limitations without claiming new local measurements or final-render improvements.

## Blocked by

None (can start immediately).
