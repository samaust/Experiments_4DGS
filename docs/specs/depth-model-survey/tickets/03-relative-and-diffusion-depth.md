# Compare relative and diffusion depth models

## Parent

[Issue #36 — Survey depth estimation models and compare published evidence](https://github.com/samaust/Experiments_4DGS/issues/36)

## What to build

Give the reader a complete comparison section for relative depth methods,
including diffusion approaches: reported depth/detail quality, the alignment
used to measure it, inference cost, release availability and commercial terms.
Explain what extra information would be needed before a relative result could
support physical-scale estimation in this project.

Use the parent evidence contract and existing discovery sources, including
Marigold as a lead. Metric variants and shared families can be cross-referenced
without requiring another category's findings before this section starts.
Deliver readable conclusions, source records and verification within the
parent's literature-only scope.

## Acceptance criteria

- [ ] Category searches and two rounds of expansion from relevant paper comparison tables are logged through the 2026-09-30 cutoff, including older baselines, later/independent evaluations, screened variants and gaps.
- [ ] The inventory distinguishes relative depth, inverse depth/disparity, metric variants, base models and fine-tuned releases. Paper-only, gated and available checkpoints have explicit dispositions.
- [ ] Comparison records specify scale-only or scale-and-shift alignment, the domain in which alignment is performed, per-image or sequence scope, dataset/split, preprocessing, depth range, training regime and exact source-table provenance.
- [ ] Quality and boundary/detail comparisons are grouped by compatible protocols; unknown alignment and copied-versus-rerun baselines are visible. Relative accuracy is not described as proof of metric-scale recovery.
- [ ] Diffusion/runtime evidence records hardware, resolution, steps, ensembling and other reported inference settings. Missing cost or temporal evidence stays unknown; still-image detail is not assumed to imply stable video depth.
- [ ] Official implementations and exact weight variants are checked. Each serious candidate has distinct code, weight, inference/output and commercial-offer findings, including unresolved terms and documented dependency qualifications.
- [ ] The readable section identifies useful detail/depth-ordering capabilities, limitations for calibrated Basketball footage and concrete future-test questions, with author claims separated from report inferences.
- [ ] Supporting search, model, benchmark and license records follow the parent contract. Every reported number and shortlist release/license claim is source-checked, with a concise verification record.

## Blocked by

None (can start immediately).
