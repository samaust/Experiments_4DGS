# Extend the depth comparison with seven commercial-use candidates

## Problem Statement

The current Basketball comparison covers D0–D4. The user wants to evaluate seven
additional models identified through the completed depth-model survey, with
commercial use of code, weights and inference outputs as an eligibility
requirement. Published paper results do not establish their scale consistency,
player-boundary detail or temporal behavior on this footage.

The previous experiment version still has open agent work: #18 coordinates
execution, #23 owns qualitative comparison, #34 owns downstream generation and
#35 owns the final assessment. Its initial S2/D4 research choice and D4-specific
final-render proposal cannot silently become a choice for the expanded scope.
The user wants the new depth review before further depth-dependent final-render
experiments, while reusable preparation continues.

## Solution

Extend the existing worker, admission, scale and qualitative-package interfaces
to produce a reproducible comparison of D5–D11. Use matched frozen frames for
all additions and matched two-second depth clips for all additions plus D2.
Evaluate physical-scale consistency for metric models and retain relative models
for visual comparison. Publish the exact results, eligibility and resource
lineage for a separate human-review child of #23.

This is a prospective execution workstream under #18. It reuses completed
infrastructure and historical controls, preserves existing evidence, and supplies
the new review dependency for #34. Depth continues to provide global scene
scale; dense geometry continues through the existing triangulation workflow.

## User Stories

1. As a researcher, I want all seven approved additions included, so that the experiment reflects the agreed shortlist.
2. As a researcher, I want stable D5–D11 identities, so that results from different checkpoints cannot be confused.
3. As a researcher, I want exact source and weight revisions recorded, so that a later release cannot silently change a comparison.
4. As a commercial evaluator, I want code permissions checked, so that I can identify usable implementations.
5. As a commercial evaluator, I want exact weight permissions checked separately, so that permissive repository code does not conceal restricted models.
6. As a commercial evaluator, I want inference-output terms recorded, so that commercial inference and output use are assessed explicitly.
7. As a commercial evaluator, I want required inference dependencies included, so that a permissive adapter does not conceal a restricted base model.
8. As a researcher, I want the same accepted RGB, cameras and sparse samples used, so that input changes do not explain apparent depth improvements.
9. As a researcher, I want supplied camera information used where the selected model supports it, so that the test reflects the calibrated workflow.
10. As a researcher, I want metric and relative depth clearly distinguished, so that attractive relative maps are not treated as metre estimates.
11. As a researcher, I want frame-100 scale fitting followed by a frozen frame-175 check, so that later observations do not refit the chosen scale.
12. As a researcher, I want failed cameras and scale gates retained, so that weak support is not hidden by dropping inconvenient observations.
13. As a reviewer, I want visually valid maps available even when scale eligibility fails, so that appearance and engineering suitability can be considered separately.
14. As a reviewer, I want all additions compared at identical frozen frames, so that player and court boundaries can be inspected fairly.
15. As a reviewer, I want all additions and D2 shown in matched motion clips, so that temporal stability can be compared across image and video methods.
16. As a researcher, I want each single-image method applied independently to clip frames, so that its actual temporal behavior remains visible.
17. As a researcher, I want video context and resets recorded, so that fitting, checking and different cameras do not share hidden state.
18. As a reviewer, I want genuine consecutive frames at their original rate, so that sparse images are not presented as continuous motion.
19. As a reviewer, I want consistent metric colors and explicit clipping, so that display scaling does not conceal depth differences.
20. As a reviewer, I want relative-depth units and clip normalization visible, so that arbitrary values are not interpreted as metres.
21. As a reviewer, I want matching zoom and crop controls, so that close-object edges and distant players can be compared directly.
22. As a reviewer, I want every candidate's unavailable or failed status explained, so that missing panels do not suggest successful evaluation.
23. As a maintainer, I want accepted D0–D4 results reused with their original provenance, so that historical comparisons remain inspectable.
24. As a maintainer, I want new requests and outputs to have fresh identities, so that completed attempts cannot be replayed or overwritten.
25. As a maintainer, I want a new versioned result contract for relative and temporal outputs, so that existing metric consumers keep their guarantees.
26. As a maintainer, I want tests through existing request/result boundaries, so that behavior can be verified without downloading or running models.
27. As a host operator, I want exclusive GPU ownership, so that the new work cannot overlap another agent's GPU job.
28. As a host operator, I want loading, processing, publication and cleanup included in resource accounting, so that execution limits describe the complete job.
29. As a maintainer, I want setup and runtime failures preserved, so that validated corrections can follow the repository's retry rules without losing evidence.
30. As a maintainer, I want the current S1 continuation preserved independently, so that adding depth models does not revoke or expand its authority.
31. As a project owner, I want the new work linked to existing execution issues, so that parallel agents do not duplicate generation or reporting responsibilities.
32. As a project owner, I want the new human depth choice before downstream runs, so that costly generation uses the expanded comparison.
33. As a project owner, I want completed preparation, survey and initial-review issues retained as completed, so that new scope does not rewrite their acceptance history.
34. As a report reader, I want costs, scale diagnostics and visual evidence reported separately, so that practical tradeoffs remain understandable.
35. As a report reader, I want component-map conclusions distinguished from final-render observations, so that depth detail is not presented as proven rendering improvement.
36. As a project owner, I want parents closed only after all their children are complete, so that remaining work stays visible.

## Implementation Decisions

- **Ownership and precedence:** #44 is a new child workstream of #18. Extended-depth review #45 is a separate child of #23, blocked by #44. #34 keeps downstream implementation and generation and is blocked by #45; #35 keeps final reporting. The depth extension takes precedence for future depth comparison and depth-choice handoff. Existing segmentation, motion/neighbor final-render coverage and S1 continuation remain under their existing scopes.
- **Historical compatibility:** preserve the original Plan 031/protocol/configuration bytes, D0–D4 results, consumed allocations, initial S2/D4 decision and original D4-specific REVIEW proposal. Add a versioned extension configuration and request/result modes. Historical records remain valid under their original contracts; old choices cannot authorize the new scope.
- **Candidate matrix:** add exactly the following seven identities. Each row is one configuration; predicted-camera ablations, alternate sizes and alternate checkpoints require later scope changes.

| ID | Exact model | Primary inference mode | Evaluation role |
| --- | --- | --- | --- |
| D5 | MoGe-2 ViT-L, original checkpoint | Supplied horizontal FoV | Metric scale, frames, clips |
| D6 | MoGe-3 ViT-L | Supplied horizontal FoV; three refinement steps | Metric scale, frames, clips |
| D7 | Depth Anything V2 Metric Hypersim Small | Indoor checkpoint; native 518 processing size and 20 m range | Metric scale, frames, clips |
| D8 | MetricAnything Student PointMap | PointMap checkpoint; supplied horizontal FoV | Metric scale, frames, clips |
| D9 | Video Depth Anything Small | Relative checkpoint; native offline sequence mode | Relative frames and clips |
| D10 | Metric Video Depth Anything Small | Metric checkpoint; native offline sequence mode | Metric scale, frames, clips |
| D11 | Marigold V2 Log-stage2 | Log-stage2 adapter, required Qwen base, native single-step four-bit inference | Relative frames and clips |

- **Asset baseline:** use the exact source and checkpoint revisions identified in the dated survey, including the Qwen base for D11. Freeze the required artifact inventory, hashes, native preprocessing, precision, seed policy and dependency lock before execution. A metadata revision is not a verified weight-byte receipt. Download only required inference assets; training datasets and optional checkpoints are excluded.
- **Commercial eligibility:** audit code, exact weights, commercial inference/output terms and required inference dependencies separately. Preserve notices and conflicting declarations. Missing or conflicting permission blocks commercial eligibility; it cannot be inferred from repository metadata alone. Record the finding's scope without claiming ownership of generated images or commercial clearance for the entire S2/FreeTimeGS stack. Newly added inference requires this eligibility and actual asset/runtime qualification.
- **Input membership:** reuse all 30 training cameras, accepted 960×540 undistorted scale-grid images, intrinsics, valid footprints, static-mask parents and sparse point/UV/camera-z samples at frames 100 and 175. Preserve exclusions for cameras 0/10/20/30. Additional context images use the same accepted source videos and scale-grid remap; the anchor frames must match existing accepted bytes. Keep added context in a separate immutable manifest linked to the original scale-input manifest.
- **Camera handling:** derive supplied horizontal FoV from accepted scale-grid intrinsics and image width for D5/D6/D8. Preserve resize/pad/crop transformations and centered-pinhole assumptions; reject incompatible input geometry. Predicted cameras never replace accepted reconstruction calibration. Retain native point/depth outputs and avoid extra focal or scale multiplication.
- **Scale contract:** only D5/D6/D7/D8/D10 may enter the existing metric estimator. Require verified float32 camera-z metres, boolean validity and NaN invalid pixels on the accepted grid. Establish D10's camera-z/ray convention from its exact release and validate any required conversion before scale admission. Unresolved convention leaves scale eligibility blocked. Keep existing per-camera support, coverage, positivity, dispersion, bootstrap and fit/check gates unchanged.
- **Frozen fit/check:** fit at frame 100 and evaluate frame 175 against that frozen fit, binding the same exact scale-input manifest as required by ADR 0002. A failed camera remains a failure. No per-image affine fitting, confidence-based support replacement or frame-175 refit is introduced. Physical accuracy remains unverified without independent metric references.
- **Relative outputs:** represent D9 as relative inverse depth and D11 as relative log depth, with explicit domain, validity, original grid and raw output lineage. The relative result variant must be rejected by metric-scale and downstream scale admission. Do not apply sparse-map or ground-truth alignment to manufacture a metric candidate in this scope.
- **Image workload:** all seven additions produce the 60 anchor maps. Metric scale failure does not itself suppress separately admitted qualitative maps at frame 175; record the scale check as blocked when no passing fit exists. Runtime, commercial eligibility and resource failures still apply.
- **Temporal workload:** all seven additions plus D2 expose four complete 50-frame clips at 25 fps for cameras 1/11/21/31, frames 150–199. Single-image methods infer independently. D9/D10 process each of the 30 cameras with separate fitting context 50–149 and checking context 150–199, reset at every camera/role boundary, and preserve native offline windowing, padding, overlap interpolation and metric-versus-relative alignment behavior. Bind all context frames and processing costs, even when only anchors and the four selected camera clips are published. No frame 200–249 or new reconstruction/training input is admitted.
- **Deduplication and D2 control:** reuse matching accepted outputs with exact asset, settings, grid and source lineage, including D2 frame 175. Generate only missing D2 clip frames under fresh scope/identities. Each new candidate contributes at most 256 unique published map identities: 60 anchors plus 196 additional clip frames. The comparison contains 32 candidate clips if every arm succeeds. Video context computation and native overlap processing are additional workload, not 256-frame inference jobs.
- **Display and package contract:** extend the existing package generator to consume an explicit candidate set and continuous depth clips. Publish source RGB, D0–D4 historical anchor references, new outputs, shared full/center/left/right views and provenance. Metric colors retain the shared 0–20 m range with invalid and out-of-range diagnostics. Relative views state their domain and increasing/decreasing distance direction; freeze a deterministic display normalization per clip, never independently per frame. Store its parameters in the package. Display normalization never changes raw outputs or engineering diagnostics. Missing historical clips remain explicitly unavailable.
- **Resources and authority:** produce concrete, reviewed fresh allocations for setup, transfers, inference including video context and D11 first-load quantization, CPU packaging and retention. Reconcile the live ledger, existing cumulative limits and concurrent reservations before approval/admission. One GPU process group, the 22 GiB device ceiling and existing CPU limits apply. This specification grants no numerical allocation, reset or resource increase. Apply AGENTS retry rules within the actual approved scope, budgets and attempt limits; S1's standing calibration retry authority does not authorize new depth attempts.
- **Handoff and completion:** complete CPU qualification and independent review, execute only admitted allocations, and publish an immutable package plus per-candidate runtime/license/scale/resource dispositions. Every required slot needs actual accepted results or an authorized terminal disposition; an unstarted blocked slot is not silently dropped to complete the workstream. Deliver the package to the extended-depth review child of #23. Its new choice is required before new depth-dependent #34 execution.

## Testing Decisions

- **Confirmed seams:** the user selected “Use these existing seams.” Test the existing worker request/result boundary, including admission and ledger checks, and the existing package/review handoff. Prefer complete externally observable transactions over new lower-level test APIs.
- **Good tests:** independently constructed CPU fixtures establish expected outputs, accepted/rejected requests, immutable published artifacts and resource outcomes. They must detect wrong behavior without mirroring internal branches. Synthetic model and human records are labeled fixtures and cannot satisfy actual qualification or review.
- **Prior art:** existing benchmark execution tests cover first-result validation, immutable outcomes and consumed identities; backend/coordinate fixtures cover supplied intrinsics and single focal conversion; scale tests cover failed-camera retention and identical input manifests; qualitative generation/review tests cover media hashes, sparse sequences and actual-human requirements; final-render admission tests reject substituted choices and proposals.
- **Adapter behavior:** cover known-z planes, off-axis ray distance, supplied FoV, resize/pad restoration, invalid interpolation contributors, native clamps, nonfinite values, wrong domains and double conversion. Keep D9/D11 outside scale admission; require explicit evidence for D10's convention.
- **Temporal behavior:** exercise independent single-image processing, camera and role resets, 32-frame window boundaries, native padding/overlap bookkeeping, original timestamps, missing frames and context changes. Changing hidden context must invalidate the result binding.
- **Scale behavior:** verify all 30 cameras, unchanged sample membership/gates, missing/failed cameras, frozen-fit reuse, changed manifest/candidate rejection and absence of frame-175 refitting. Verify that an engineering-ineligible map can remain labeled qualitative evidence without becoming an eligible choice.
- **Package behavior:** verify seven stable identities, 60 anchors per addition, four 50-frame clips per available addition/D2, overlap deduplication, historical-reference reuse, common metric range, clip-fixed relative normalization and explicit unavailable states. Relative colors cannot imply metre values; sparse or interpolated frames cannot satisfy the clip contract.
- **Admission and preservation:** reject missing commercial evidence, stale qualification, reused identities, stale D4 choice bindings, active GPU ownership and insufficient cumulative resources. Check that new modes leave historical request/receipt validation intact and that fixture success grants no native execution authority.
- **Acceptance evidence:** report focused tests, current-source qualification, independent review findings, actual generated counts, hashes, elapsed costs and cleanup. Resource caps and actual-model compatibility require execution evidence; CPU tests alone cannot establish them.

## Out of Scope

- Additional model families, sizes, checkpoints, camera-mode ablations or automatic substitutes.
- Dense-depth reconstruction priors, recalibration, fine-tuning, hyperparameter searches or a new triangulation method.
- External human annotation bundles, independent pixel scoring, fabricated reviews or automatic perceptual winners.
- Reopening completed D0–D4, preparation, initial-review or survey work because the comparison grew.
- New training/rendering performed by this generation workstream; #34 owns that work after the new decision.
- Unallocated GPU/setup jobs, borrowing S1 retry authority, automatic resource-cap increases or changes to historical receipts.

## Further Notes

Published specification: [#44](https://github.com/samaust/Experiments_4DGS/issues/44),
parent [#18](https://github.com/samaust/Experiments_4DGS/issues/18), supplying
[review #45](https://github.com/samaust/Experiments_4DGS/issues/45).

This specification implements the approved Plan 069 discussion. The user chose
“Review new models first” for #34 and “All seven + D2” for motion coverage, then
confirmed the existing testing seams during specification preparation.

Related documents: [Plan 069](../../../plans/plan_069.md),
[extended human review](depth-comparison-review.md),
[completed survey](../../research/depth-model-survey.md) and
[scale-input ADR](../../adr/0002-bind-future-scale-checks-to-input-manifest.md).

Source baseline: the survey's pinned inventory rows `i38-moge2-vitl-fov`,
`i38-moge3-vitl`, `i42-dav2-small-hypersim`, `i38-metricanything-pointmap`,
`i40-vda-small`, `i40-vda-metric-small` and `i39-marigold-v2-log-stage2`.
D6/D8 use the supplied-FoV mode specified here even where the survey's reference
paper row used predicted cameras. That is a declared experiment condition, not
a claim that those published scores measure this mode. D11's required Qwen base
is pinned to `d3968ef930e841f4c73640fb8afa3b306a78167e` in the survey's license inventory.

At drafting, the four related open `ready-for-agent` issues were #18, #23, #34
and #35. E5/depth preparation and the original initial review were complete;
native downstream generation, final-render review and final assessment remained
unfinished. S1 has a separate standing fix-and-retry amendment within its existing
budgets. Re-read live issue comments, source state and allocation state before
implementation; historical issue prose is not a current admission receipt.
