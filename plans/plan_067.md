# Plan 067 — Qualitative comparison of Plan 031 generated results

## Authority and objective

The user explicitly replaces the external human annotation bundle and handoff with code-generated results followed by human qualitative comparison. The confirmed display set is matched frozen-frame images, synchronized motion clips and component diagnostics. Implement the [comparison amendment](../docs/specs/plan031-execution/qualitative-comparison-amendment.md) and revised #18/#22/#23 execution specs.

This is the active continuation plan for comparison work. Historical Plan 031/protocol v1 remain immutable run contracts. Their annotation workload, independent accuracy metrics, bootstrap/significance requirements, metric-based quality finalist rankings, and P31-3 independent-scoring completion criterion are superseded prospectively by the human qualitative-review criterion below. Earlier S1 recovery plans retain their bounded histories; this plan grants no additional attempt.

## Milestones and dependencies

1. **#30: package infrastructure.** Implement immutable matched frame/clip/diagnostic manifests and a local viewer with shared playback/zoom/crop, result provenance and explicit unavailable states. CPU-test the request/result seam. Reopen the old annotation infrastructure ticket under this new scope.
2. **#31: actual packages.** Publish the declared isolated comparison set from valid existing or separately authorized generated results. Include controls and all candidate dispositions, frozen selections/settings, source lineage and media hashes. No external annotation bundle is required. Blocks on #30; unresolved generation outcomes remain explicit.
3. **#32: review/decision infrastructure.** Implement a simple human observation/preference form, immutable record validation and decision handoff. Test ties, unclear/not-applicable outcomes, changed artifacts and refusal to count empty/synthetic records as human review. Reopen the old metric-fixture ticket under this new scope.
4. **#33: real initial review and choices.** A human compares actual packages (#31) using #32 and records frozen-frame appearance, motion, artifacts, sharpness and overall preference with exact examples. Freeze justified choices and practical/engineering eligibility. Blocks on #31/#32; code does not invent a review or automatic quality winner.
5. **#34: downstream generation and follow-up review.** Resolve actual pipeline/reconstruction/combined prerequisites and available allocations, define identical output/render settings, generate only authorized results, publish matched frames/clips/diagnostics, then record human review of those new packages. Blocks on #33. Final trained-render comparisons require their own concrete generation/budget proposal if absent from existing allocations. No incomplete artifact is presented as a final render.
6. **#35: final assessment.** Bind actual media and human observations/choices, report strengths/tradeoffs and all missing/failed arms, engineering feasibility, resource costs and claim limits. Blocks on #34. Verify child completion before closing #23/#18.

Runtime and depth work #20/#21 retain their unresolved engineering requirements. #19's bounded failed outcome and #3's preparation completion remain complete. Generated packages may expose missing candidates for early review; full execution completion still requires explicit dispositions for every required arm.

## Human-review completion criterion

Replace P31-3 with **P67-3: Qualitative comparison**: code publishes reproducible matched frames/clips/diagnostics, one real human records observations/preferences or justified ties/unclear/unjudgeable dispositions for the declared available comparison set, and the report binds those records to exact artifacts. No pixel annotations, masks, temporal associations, attestations, blind annotation review or adjudication are required. Missing human feedback remains awaiting review. Other Plan 031 engineering, provenance/accounting and execution-completeness criteria remain applicable, with quality conclusions expressed as human visual preferences rather than measured accuracy/significance.

## Execution and preservation

Keep source/model pins, accepted data/roles, component precision/thresholds, engineering scale/geometry constraints, historical results and consumed allocations. One GPU at a time; reuse original cumulative ceilings and stop/cleanup rules. Every changed request/result mode must bind this amendment before execution. A consumed output/account needs a new explicitly authorized identity; this plan creates no retry pool. Model/setup/training/render jobs are not launched by the present documentation/issue amendment.

Existing annotation validators and independent-scoring code retain their original contracts. Future implementation adds qualitative package/review paths and removes annotation presence from qualitative admission only; it must not make proxy annotations qualify as human ground truth or overwrite historical metric/finalist checkpoints.

## Validation and deliverables

Test package/review request/result and admission/ledger boundaries with small CPU media fixtures and explicit fake human records. Check synchronized membership/time, media integrity, immutable lineage, absent evidence, actual-review distinction, tied/blocked choices and downstream eligibility. Review changes and preserve exact validation outcomes. Actual human judgment cannot be replaced by synthetic tests.

Deliver immutable manifests, comparison viewer/media, human review records, choice records, downstream output dispositions, final qualitative report and an issue-by-issue completion assessment. Existing pending CPU qualification and runtime failures remain explicit engineering gates.
