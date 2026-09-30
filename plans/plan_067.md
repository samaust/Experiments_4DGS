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

## Execution checkpoint — 2026-09-30

The newly approved E5 recovery003 and S1 recovery007 were each consumed once, serially, after qualification009 passed298 tests/1030 subtests under the600-second cap. E5 failed import qualification at the blanket constructor guard's rejection of Normalize preprocessing. S1 produced and individually qualified all510 calibration rows, then failed final runtime acceptance because a recorded generated Torch source file had been deleted with its temporary directory. S1 terminal publication is unavailable and stop_required remains true. Both cleaned up; neither timed out.

Affected E5/S1 execution is stopped under AGENTS.md pending user resolution. No repeat or reconstruction is authorized. D2 remains blocked by E5. Actual human feedback remains pending. Exact outcomes and proposed CPU corrections are in [fresh runtime attempts assessment](../docs/research/vipe-alternatives/plan067-execution/fresh-runtime-attempts-assessment-001.md). No incomplete issue was closed.

## CPU correction checkpoint — 2026-09-30

The user approved E5/S1 CPU corrections and clarified AGENTS.md to permit retries after relevant validated fixes within existing scope/budgets/attempt limits. E5 now allows only exact pinned Normalize preprocessing initialization during native import qualification; models, forwards, network/subprocess and CUDA guards remain. S1 retains only the admitted generated Torch module before temporary cleanup, with exact generator/template, owner and byte provenance; ordinary runtime checks remain strict. Neither earlier attempt is rewritten or retroactively accepted.

Both fixes were implemented in separate worktrees, integrated and independently reviewed with zero blocking findings. Focused73 tests passed. Full integration exposed two fixture issues (missing parameter declaration and mutable historical AGENTS input); both were fixed, validated, reviewed and retried under the new rules, preserving failed captures. The final full suite retains six known unrelated errors/five skips. Qualification010 passed306 tests/1035 subtests in239.138 seconds under600 seconds.

No setup or GPU attempt was allocated during CPU correction; ledger remains547 events. The old E5/S1 limits are consumed. [Fresh attempt proposal002](../docs/research/vipe-alternatives/plan067-execution/fresh-runtime-attempts-proposal-002.md) requests separate bounded identities after reviewed admission controls and live checks. Actual human review#33 and downstream#34/#35 remain pending; no incomplete issue is closed.

## Native runtime, depth and human-review checkpoint — 2026-09-30

The user approved proposal002. Reviewed identity controls and process amendment003 were implemented in parallel isolated worktrees, committed and independently reviewed with zero findings. Qualification011 passed311 tests/1035 subtests in255.011 seconds. Full suite ran1132 tests with six existing unrelated errors/five skips; no passing full-suite claim.

E5 recovery004 succeeded in83.510 seconds with qualified native imports/inventory and confirmed cleanup. Original unconsumed D2 fit/check then completed serially in18.507/14.602 seconds,30 rows each atframes100/175, with passed gates and identical frozen scale1.0899176481863033. No repeated model attempt. Issues27/20 and28/21 are closed only after all their child issues were verified closed. Earlier failures and D0/D1/D3/D4 evidence remain unchanged.

S1 recovery008 failed first-result generated-source temporary ownership in36.641 seconds, zero qualified rows; cleanup confirmed, no survivors, stop_required=false and actual terminal receipt published. Its one attempt is consumed and preserved. CPU diagnosis/correction proceeds under revised AGENTS standing approval; no unchanged replay or new GPU attempt is granted. A fresh S1 proposal requires validated correction/review/current qualification and separate bounded authority.

Actual reviewer samaust submitted segmentation observations, confirmedcamera1-reconstruction-0 and overallS2preference. Raw/corrected/confirmed submissions and actual imports are preserved. A scope-limited research component choiceS2 is frozen with runtime/result evidence; commercial/non-AGPL and unseen downstream generation remain separate gates. The user clarified playback is available for some selections and is not broken; no viewer change was made. Other motion/depth/neighbor human feedback remains pending, so33/23/18 remain open. A new immutable depth package will expose actual D2 without changing package001 or the reviewed segmentation.
