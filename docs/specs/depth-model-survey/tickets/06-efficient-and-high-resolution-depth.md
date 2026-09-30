# Compare efficient and high-resolution depth methods

## Parent

[Issue #36 — Survey depth estimation models and compare published evidence](https://github.com/samaust/Experiments_4DGS/issues/36)

## What to build

Give the reader a complete comparison section for efficient models and
high-resolution depth/refinement methods, showing reported quality, detail and
compute tradeoffs, exact released model combinations and commercial terms.
Explain their relevance to processing many camera frames and preserving player
boundaries in the existing workflow.

Use the parent evidence contract and source reconnaissance, including
PatchFusion as a lead. A method already examined in another category can be
cross-referenced by exact variant; this section independently verifies its
efficiency or resolution claims. Deliver findings, evidence and source review
within the parent's literature-only scope.

## Acceptance criteria

- [ ] Category searches and two rounds of comparison-table/reference expansion are logged through the 2026-09-30 cutoff, with small/efficient variants and high-resolution/refinement methods both covered or evidence gaps documented.
- [ ] Each method distinguishes native input/output resolution, resizing or upsampling, base estimator, refinement stages, checkpoint combination and output scale semantics.
- [ ] Reported depth, boundary/detail and robustness metrics are tied to exact dataset/split, crop/mask/range, alignment, input settings and paper/table/row provenance; copied versus rerun baselines remain visible.
- [ ] Efficiency records retain hardware, precision, batch/resolution/clip/view count, parameter counts and whether preprocessing, refinement or ensembling is included. Missing or unmatched settings prevent a direct speed or memory ranking.
- [ ] Quality-versus-compute conclusions use compatible observations and distinguish additional pixels from demonstrated additional detail. Published timing is not converted into an unmeasured estimate for this host.
- [ ] Release and license checks cover the complete stated base/refinement combination rather than assigning one component's terms to the whole method. Each serious candidate has the four commercial-use dispositions and documented dependency qualifications.
- [ ] The readable section explains usefulness for camera-frame throughput and player boundaries, tradeoffs, limits and concrete questions for later experiments.
- [ ] Supporting search, model, benchmark and license records follow the parent contract. Every reported number and shortlist release/license claim is source-checked, with a verification note that identifies remaining limitations.

## Blocked by

None (can start immediately).
