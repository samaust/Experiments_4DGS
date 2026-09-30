# Compare additional monocular metric depth models

## Parent

[Issue #36 — Survey depth estimation models and compare published evidence](https://github.com/samaust/Experiments_4DGS/issues/36)

## What to build

Give the reader a complete comparison section for monocular metric depth
candidates beyond D0–D4: what they estimate, the camera information they need,
their reported accuracy, availability and commercial terms, and why they may
merit a future physical-scale experiment.

Use the existing parent evidence contract and source reconnaissance. Starting
leads such as MoGe-2 and ZoeDepth are search inputs, not predetermined finalists.
The section includes its own source records and verification and is reviewable
independently of the reference section. This is literature and release review.

## Acceptance criteria

- [ ] Category searches and two rounds of following relevant comparison-table rows/references are logged through the 2026-09-30 cutoff. Record discovered variants, exclusions, cross-category leads and coverage gaps, including later or independent evaluations.
- [ ] The section extends beyond the existing D0–D4 families or explains each unavailable/excluded discovery with evidence; it does not treat renamed wrappers or checkpoints as new independent families.
- [ ] Model records distinguish full-intrinsics, focal-conditioned, predicted-camera and other input requirements; metric camera-z depth, ray distance or point-map outputs; and released versus paper-only variants.
- [ ] Accuracy tables preserve dataset/version/split, crop/mask/resolution/depth range, training overlap/regime, alignment, exact paper table provenance and reporting party. Ground-truth-aligned results cannot establish absolute metric accuracy.
- [ ] Comparative statements use compatible protocols. Conflicting values, unreported settings and gaps in unseen-scene or physical-scale evidence remain visible.
- [ ] Official code and exact weights are checked for availability and paper/release differences. Each serious candidate has all four commercial-use dispositions with citations or explicit unresolved findings, plus documented material dependency qualifications.
- [ ] The readable section explains scale-estimation relevance, reported compute context, tradeoffs and concrete future-test questions without predicting measured Basketball or host performance.
- [ ] Supporting search, model, benchmark and license records follow the parent contract. Every reported number and shortlist release/license claim is source-checked; a verification note records remaining limitations.

## Blocked by

None (can start immediately).
