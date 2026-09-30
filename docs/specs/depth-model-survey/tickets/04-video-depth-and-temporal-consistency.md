# Compare video depth and temporal consistency

## Parent

[Issue #36 — Survey depth estimation models and compare published evidence](https://github.com/samaust/Experiments_4DGS/issues/36)

## What to build

Give the reader a complete comparison section for video-depth models, showing
what published evidence says about temporal consistency, depth quality and
moving objects, alongside practical sequence requirements, releases and
commercial terms. Explain which evidence could inform a future comparison of
Basketball sequences and which motion questions remain untested.

Start from the parent contract and existing discovery sources, including
DepthCrafter as a lead. Deliver the section, its evidence records and source
verification independently. This ticket covers literature and release review.

## Acceptance criteria

- [ ] Category searches and two rounds of comparison-table/reference expansion are logged through the 2026-09-30 cutoff, including later or independent temporal evaluations and explicit gaps.
- [ ] Each variant records metric versus relative output, required frames/poses/intrinsics, clip-length limits, chunking or stitching, and reported online/offline or future-frame requirements where documented.
- [ ] Image-quality and temporal metrics are defined and kept distinct. Record temporal evaluation datasets/splits, frame selection, alignment scope, visibility masks and any flow/warping dependency when disclosed.
- [ ] Comparison tables preserve exact variants, paper/table/row provenance, training settings and copied-versus-rerun status. Per-frame scale fitting is not confused with sequence-consistent metric scale.
- [ ] Published evidence for moving objects, occlusions and long-sequence stability is distinguished from demonstrations or unsupported assumptions. Missing temporal evidence is explicitly unknown.
- [ ] Reported runtime and memory include frame/clip size, hardware, precision, inference steps and ensembling when available; performance on this host is not inferred.
- [ ] Official code/checkpoint availability and release differences are verified. Each serious candidate has all four commercial-use dispositions and documented material dependency qualifications, with sources or explicit uncertainty.
- [ ] The readable section presents tradeoffs and future-test questions with supporting search, model, benchmark and license records. Every reported number and shortlist release/license claim is source-checked and verification limitations are recorded.

## Blocked by

None (can start immediately).
