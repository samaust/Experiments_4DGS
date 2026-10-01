## Current depth extension — Plan 069

The user chose to review the new depth models before further depth-dependent final-render runs. This issue retains downstream ownership and gains native blocker #45, which depends on generation #44. Closed #33 remains the completed initial-review dependency.

### Additional acceptance criteria

- [ ] Continue reusable CPU/native-adapter preparation while #45 is pending, but require its actual package-bound, commercially eligible metric-depth choice D* before new depth-dependent geometry, initialization, training or rendering.
- [ ] Produce a fresh versioned downstream proposal binding the new decision, exact passing fit/check, accepted inputs and full similarity normalization. Reject stale D4 bindings in the new mode; preserve the original S2/D4 proposal and historical validators.
- [ ] Keep five controlled arms: S2/D*/M0/N0, S2/D*/M1/N0, S2/D*/M2/N0, S2/D*/M0/N1 and S2/D*/M0/N2. Hold D* fixed across them and preserve the applicable five-arm coverage, equal training endpoint and render settings.
- [ ] Recheck current source qualification, actual runtime/scale/geometry/license eligibility, fresh identities, approved allocations and live single-GPU admission. Existing CPU acceptance or an earlier proposal is not new execution authority.
- [ ] Publish actual final renders and obtain separately bound human feedback on M/N effects. Carry the expanded depth decision and exact outcome lineage to #35.

#45 may choose D2/D5/D6/D7/D8/D10 only after eligibility passes; relative D9/D11 can be visual favorites but cannot supply scale. A blocked choice cannot silently fall back to D4. S2 remains the existing segmentation choice.

S1 follows its separate standing fix-and-retry amendment and is not an artificial prerequisite for the S2 comparison. Any required reconstruction evidence and common live admission gates still apply. This amendment grants no extra setup/GPU/training/render allocation and does not alter existing resource ceilings.

These requirements supersede earlier D4-choice or annotation-dependent instructions below for future work. Preserve historical outcomes and completed #33.

## Earlier issue scope and checkpoints (preserved)

## Current comparison scope — user correction, 2026-09-30

The initial isolated viewer comparison covers **segmentation and depth**. Motion (M0–M2) and neighbors (N0–N2) are excluded from that isolated pictures/videos comparison. Their effects **must still be compared on final renders**, under downstream #34/#35. The user explicitly clarified that their effects can only be evaluated on the final render.

See `docs/specs/plan031-execution/qualitative-comparison-scope-amendment-001.md` and Plan067. Preserve the original hash-pinned amendment, packages, scientific/runtime/ledger records and historical completion. Applicable motion criteria/segmentation clips remain supported. Downstream acceptance must include matched final renders exposing motion and neighbor method effects, with real human feedback bound to those outputs. Engineering prerequisites and explicit allocations still apply; no new M/N winner, experiment, training or rendering is authorized. Parent closure still requires every child complete.

## Parent

#23; execution workstream #18. Related completed preparation: #3.

## What to build

Resolve downstream prerequisites, generate matched combined/final output packages when authorized, and record follow-up human review.

## Acceptance criteria

- [ ] Check frozen human choices, actual source results, runtime/scale/geometry eligibility, stage order, current admission and unconsumed allocations before any generation.
- [ ] Define identical output/render/training settings across comparisons and a concrete bounded budget proposal for missing final-render stages. Execute only already authorized jobs or separately approved new allocations, with one GPU and confirmed cleanup.
- [ ] Keep S1 calibration separate from reconstruction; refuse missing reconstruction/other prerequisites. Record blocked/skipped/unavailable/consumed outcomes without automatic retries or silent scope disposal.
- [ ] Publish actual matched frames/clips/diagnostics with exact lineage; label intermediate diagnostics and absent final renders explicitly.
- [ ] Capture actual human follow-up observations/preferences on the new package using #32; initial component preferences cannot substitute for reviewing unobserved downstream output.

## Blocked by

- #33

## Amendment and preservation

User-authorized qualitative comparison supersedes the annotation-bundle/independent metric-scoring requirement. See `docs/specs/plan031-execution/qualitative-comparison-amendment.md` and `plans/plan_067.md`. Code generates matched frames, synchronized clips and component diagnostics; an actual human records appearance/motion/artifact/sharpness preferences. No external annotation bundle is required. Preserve historical results/metrics/proxy classifications, model/input contracts, engineering eligibility and resource charges. This issue update grants no additional setup/GPU/training/rendering attempt.
