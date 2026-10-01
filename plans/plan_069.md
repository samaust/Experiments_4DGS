# Plan 069 — Extend the depth comparison and update pending work

## Authority and objective

The user approved seven additional depth models, chose **scale and depth-map
comparison first**, chose **review new models before further depth-dependent
#34 runs**, and confirmed **matched clips for all seven additions plus D2**.
The user then requested specification publication accounting for open
`ready-for-agent` work and confirmed the existing test seams.

Implement the [generation specification](../docs/specs/plan031-execution/depth-comparison-extension.md)
([#44](https://github.com/samaust/Experiments_4DGS/issues/44)) and
[human-review specification](../docs/specs/plan031-execution/depth-comparison-review.md)
([#45](https://github.com/samaust/Experiments_4DGS/issues/45)).
This is a prospective extension of Plan 031 and the active Plan 067 comparison.
Keep the original hash-bound Plan 031, protocol/configuration, accepted results,
initial S2/D4 decision and D4-specific REVIEW proposal intact. These documents
allocate no new execution attempt or resource increase.

## Candidate matrix

| ID | Model | Configuration | Evaluation |
| --- | --- | --- | --- |
| D5 | MoGe-2 ViT-L | Original checkpoint; supplied horizontal FoV | Metric scale, frames, clips |
| D6 | MoGe-3 ViT-L | Supplied FoV; three refinement steps | Metric scale, frames, clips |
| D7 | Depth Anything V2 Metric Hypersim Small | Indoor checkpoint; native 518 processing size and 20 m range | Metric scale, frames, clips |
| D8 | MetricAnything Student PointMap | PointMap checkpoint; supplied FoV | Metric scale, frames, clips |
| D9 | Video Depth Anything Small | Relative checkpoint; native offline sequence mode | Relative frames, clips |
| D10 | Metric Video Depth Anything Small | Metric checkpoint; native offline sequence mode | Metric scale, frames, clips |
| D11 | Marigold V2 Log-stage2 | Required Qwen base; native single-step four-bit inference | Relative frames, clips |

Use the exact source/checkpoint revisions in the completed survey and verify
actual required assets. Audit code, weights, inference dependencies and commercial
inference/output terms separately. Permission uncertainty remains a blocker to
commercial eligibility. This depth assessment does not establish commercial
clearance for every component in the reconstruction workflow.

## Workload and comparison

- Generate the 60 frame-100/frame-175 anchors per addition using the same 30
  training cameras, accepted RGB/K, masks, footprints and sparse samples.
- D5/D6/D7/D8/D10 use the existing frozen scale estimator/gates. Establish D10's
  coordinate convention before metric admission. Keep exact fit/check input
  manifest binding; retain failed cameras and unverified physical accuracy.
- D9/D11 retain explicit relative inverse/log-depth output domains. A relative
  visual preference cannot become the scale choice. Scale-ineligible but otherwise
  valid maps remain available for qualitative review under their admitted scope.
- Publish four 50-frame, 25-fps clips per addition and D2: cameras 1/11/21/31,
  frames 150–199. Single-image models process frames independently. Video models
  use separate 50–149 fit and 150–199 check contexts per camera, with native
  overlap behavior and no cross-role state.
- Bind additional context to the accepted scale-grid remap and original scale
  manifest; verify the anchor images still match. Reuse accepted matching outputs.
  Each addition has 256 unique displayed maps at most; D2 needs at most 196 new
  clip frames. Video context/window computation is charged in addition to the
  published map count. Complete success yields 32 candidate clips.
- Publish source RGB, historical D0–D4 anchors, matched views, diagnostics and
  all failed/unavailable dispositions. Metric colors use 0–20 m with clipping
  indicators; relative views use explicit units and clip-fixed normalization.
  Collect real human observations and freeze both visual preference and eligible
  metric choice D* from D2/D5/D6/D7/D8/D10.

## Implementation milestones and issue coordination

1. **Specify and reconcile.** Publish the two linked specs; generation #44 is a
   child of #18 and review #45 a child of #23 blocked by #44. Add #45 as a native
   blocker of #34. Update #18/#23/#34/#35 prospectively and
   retain their open states and all existing children.
2. **Implement and qualify.** Extend versioned configuration, workers and result
   contracts for metric/relative/temporal outputs and explicit candidate packages.
   Reuse existing scale, ledger and review boundaries. Prepare exact commercial,
   asset and runtime inventories; complete CPU qualification and independent review.
3. **Prepare bounded execution.** Reconcile live consumption and reservations;
   produce concrete setup/download/inference/context/publication/storage budgets
   and obtain the required allocation authority. Retain one GPU, 22 GiB device
   memory and existing CPU/resource controls. Loading, quantization, first-result
   validation, publication and cleanup belong in job accounting.
4. **Generate and review.** Execute admitted jobs, publish actual outcomes/media
   and obtain the new human depth choice. Missing evidence or an unresolved choice
   remains a blocker. Apply AGENTS fix-and-retry rules within actual scope/budgets;
   S1's standing retry grant remains separate from these new depth allocations.
5. **Continue #34/#35.** Reuse their CPU preparation. A fresh downstream proposal
   binds the new decision, passing scale receipts and complete scene transform.
   Use the same D* in QF-B, QF-M1, QF-M2, QF-N1 and QF-N2, preserving S2 and the
   existing M/N isolation design. #34 still owns native generation, actual final
   renders and their human review; #35 integrates all depth and render findings.

Closed #3/#20/#21/#22/#32/#33 and the completed survey retain their original
completion scopes; the addition does not reopen them. #18 and #23 close only
after every child is complete. S1 work follows its latest standing retry amendment
and does not become an artificial prerequisite for the S2/depth extension.
Re-read live issue comments and working-tree state before implementing shared
interfaces; preserve concurrent task changes and current GPU ownership.

## Validation and completion

Use the user-confirmed worker request/result boundary with admission/ledger
checks and the package/review handoff. CPU fixtures cover known geometry,
conversion/validity, supplied FoV, sequence resets and boundaries, exact frame
membership, scale-manifest binding, relative-output rejection, clip normalization,
historical compatibility and stale downstream choices. Real runtime qualification
and human feedback remain distinct required evidence.

The specification milestone is complete when both specs are published, their
native parent/blocking relationships and amended open issues agree with local
documents, protected historical hashes remain unchanged and document checks pass.
Implementation completion requires the actual extended comparison, justified
eligible depth handoff, required final-render comparisons and reconciled final
assessment. Specification publication alone completes none of those experiments.
