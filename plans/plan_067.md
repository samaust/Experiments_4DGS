# Plan 067 — Qualitative comparison of Plan 031 generated results

**Current depth extension:** [Plan 069](plan_069.md), [generation #44](../docs/specs/plan031-execution/depth-comparison-extension.md)
and [review #45](../docs/specs/plan031-execution/depth-comparison-review.md) add D5–D11
and require the new commercially eligible metric-depth choice before further
depth-dependent #34 runs. Reusable #34 preparation continues. The original S2/D4
review and proposal remain historical; #35 includes the expanded comparison.
The standing S1 retry authority below remains separate and unchanged.

**Current scope:** [Scope amendment 001](../docs/specs/plan031-execution/qualitative-comparison-scope-amendment-001.md) takes precedence: isolated packages and initial review (#33) cover segmentation and depth only. Motion and neighbor method effects remain required comparisons on actual final renders (#34/#35); isolated M/N diagnostics are excluded from the current viewer. Applicable motion criteria and clip controls remain.

## Authority and objective

The user explicitly replaces the external human annotation bundle and handoff with code-generated results followed by human qualitative comparison. The confirmed display set is matched frozen-frame images, synchronized motion clips and component diagnostics. Implement the [comparison amendment](../docs/specs/plan031-execution/qualitative-comparison-amendment.md) and revised #18/#22/#23 execution specs.

This is the active continuation plan for comparison work. Historical Plan 031/protocol v1 remain immutable run contracts. Their annotation workload, independent accuracy metrics, bootstrap/significance requirements, metric-based quality finalist rankings, and P31-3 independent-scoring completion criterion are superseded prospectively by the human qualitative-review criterion below. Earlier S1 recovery plans retain their bounded histories; this plan grants no additional attempt.

## Milestones and dependencies

1. **#30: package infrastructure.** Implement immutable matched frame/clip/diagnostic manifests and a local viewer with shared playback/zoom/crop, result provenance and explicit unavailable states. CPU-test the request/result seam. Reopen the old annotation infrastructure ticket under this new scope.
2. **#31: actual packages.** Publish the declared isolated comparison set from valid existing or separately authorized generated results. Include controls and all candidate dispositions, frozen selections/settings, source lineage and media hashes. No external annotation bundle is required. Blocks on #30; unresolved generation outcomes remain explicit.
3. **#32: review/decision infrastructure.** Implement a simple human observation/preference form, immutable record validation and decision handoff. Test ties, unclear/not-applicable outcomes, changed artifacts and refusal to count empty/synthetic records as human review. Reopen the old metric-fixture ticket under this new scope.
4. **#33: real initial review and choices.** A human compares actual packages (#31) using #32 and records frozen-frame appearance, motion, artifacts, sharpness and overall preference with exact examples. Freeze justified choices and practical/engineering eligibility. Blocks on #31/#32; code does not invent a review or automatic quality winner.
5. **#34: downstream generation and follow-up review.** Resolve actual pipeline/reconstruction/combined prerequisites and available allocations, define identical output/render settings, generate only authorized results, publish matched frames/clips/diagnostics, then record human review of those new packages. Blocks on #33. Include motion and neighbor method effects in the concrete final-render comparison coverage, with other settings/components fixed when attributing individual effects. Isolated M/N diagnostic review is not required. Final trained-render comparisons require their own concrete generation/budget proposal if absent from existing allocations. No incomplete artifact is presented as a final render.
6. **#35: final assessment.** Bind actual media and human observations/choices, including M/N method effects on final renders, report strengths/tradeoffs and all missing/failed arms, engineering feasibility, resource costs and claim limits. Blocks on #34. Verify child completion before closing #23/#18.

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

S1 recovery008 failed first-result generated-source temporary ownership in36.641 seconds, zero accepted calibration rows; preserved progress records one individually qualified partial row. Cleanup confirmed, no survivors, stop_required=false and actual terminal receipt published. Its one attempt is consumed and preserved. CPU diagnosis/correction proceeds under revised AGENTS standing approval; no unchanged replay or new GPU attempt is granted. A fresh S1 proposal requires validated correction/review/current qualification and separate bounded authority.

Actual reviewer samaust submitted segmentation observations, confirmedcamera1-reconstruction-0 and overallS2preference. Raw/corrected/confirmed submissions and actual imports are preserved. A scope-limited research component choiceS2 is frozen with runtime/result evidence; commercial/non-AGPL and unseen downstream generation remain separate gates. The user clarified playback is available for some selections and is not broken; no viewer change was made. This checkpoint originally recorded other motion/depth/neighbor human feedback as pending. Under the latest scope amendment, initial review requires only S/D feedback. Isolated M/N diagnostics are excluded from the current viewer, while M/N method effects must be reviewed on final rendered results under #34/#35. Issues33/23/18 remain open until their current child acceptance criteria are complete. A new immutable depth package will expose actual D2 without changing package001 or the reviewed segmentation.

## Initial review and validated correction checkpoint — 2026-09-30

Actual segmentation/depth imports and evidence-bound initial S2/D4 research choices passed independent review. Issue33 meets its initial package001 review scope; new D2/package002 remains separately awaiting feedback under34/35. Current navigation is qualitative-packages-003/index.html, segmentation/depth only. The user clarified that motion and neighbor method effects remain required on final renders, with matched method coverage and concrete allocation authority. Their isolated pictures/videos do not supply that evaluation.

S1 source-owner correction a34f325e passed independent Standards/Spec reviews and19 focused CPU tests. Qualification012 passed313 tests/1035 subtests in253.036 seconds. Full integration1134 tests retains six known unrelated errors/five skips; no passing full-suite claim. Recovery008 remains failed and consumed. Fresh proposal003 requests exactly one3600-second S1-calibration-recovery-009 attempt, conditional on explicit approval, reviewed identity controls, their current passing qualification and live admission. No009 allocation or GPU dispatch has occurred. Issues34/35 and parents23/18 remain incomplete.

## S1 recovery009 and final-render CPU checkpoint — 2026-09-30

The user approved proposal003. Reviewed controls and exact REVIEW/DO bindings
passed qualification013 (318 tests/1035 subtests, 277.249 seconds). Recovery009
ran once and failed final acceptance after2209.498 seconds. All510 rows were
individually qualified, but the complete calibration was not accepted: strict
reference collection rejected an admitted model-cache snapshot symlink. Terminal
publication then failed because the retained helper was poisoned. Preserve
finish578, stop_required=true, absent terminal receipt and all unaccepted bytes
in [the immutable outcome](../docs/research/vipe-alternatives/plan031-execution/s1-recovery-009/outcome/OUTCOME.md).
Cleanup is confirmed; this was neither a timeout nor a sandbox denial. The
attempt is consumed and cannot be replayed or retroactively accepted.

CPU alias correction and independent review proceed under AGENTS standing
approval. [Proposal004](../docs/research/vipe-alternatives/plan067-execution/fresh-runtime-attempts-proposal-004.md)
requests one fresh3600-second calibration-only recovery010, subject to completed
correction/review, passing current-source qualification and live admission.
It grants no execution authority. Historical process/source/result records remain
unchanged.

Alias corrections d5545396/6cb9840a are now integrated and reviewed with zero
remaining blocking findings. Qualification014 passed328 tests/1035 subtests in
429.160 seconds under600 seconds, zero failures/errors/skips and unchanged source
inventory. Its validation SHA256 is
b5a9f028562f948ca17f05ac2a8cb38cfbdbf39633af75b1e254535500d3dd54.
Full integration ran1171 tests in535.669 seconds, zero failures, six known
unrelated errors and five skips, with no timeout. Exact evidence and independent
reviews are preserved in alias-final-render-fullsuite-001/ and
s1-alias-and-final-render-cpu-review-001.md. This is not a passing full-suite
claim. Seven changed Python files passed AST parsing; no configured static
typechecker is claimed. Qualification014 covers the correction; any subsequent
recovery010 control changes require a fresh complete-source qualification.

The final-render REVIEW contract and pure initializer assembly are integrated.
Their22 focused CPU tests pass; independent Standards/Spec reviews found no
remaining blocking findings. They bind the actual processed manifest, frozen
S2/D4 choices, complete similarity transform and verified historical scale and
normalization contents. Fixture assembly grants no native qualification or
execution authority. Native geometry, supervised native generation, measured
viability, actual matched renders and their human comparison remain unfinished.
The five-arm final-render budget proposal also needs separate allocation authority.

Actual D2 feedback is preserved at camera1-selection-175: worse close-object
edges than D0/D1 and difficulty capturing a distant player. It supplies no new
overall preference. Initial issue33 is complete within its original package001
scope; issues34/35 and parents23/18 remain open.

## Standing S1 retry authority — user correction

The user removes Proposal003's one-attempt limit and requests planning,
implementation, execution, analysis, correction and retries until S1 calibration
works. [Retry policy amendment001](../docs/specs/plan031-execution/s1-retry-policy-amendment-001.md)
and s1-standing-retry-approval-001.json supersede the numerical attempt cap and
Proposal004's pending approval prospectively. No additional user approval is
required for relevant validated corrections and subsequent fresh calibration
identities within the original resource ceilings. Every new attempt still has
reviewed controls, current qualification, live admission, confirmed cleanup and a
3600-second deadline. No unchanged failed replay, historical overwrite or
unrelated allocation is permitted. Continue until accepted complete calibration
or a concrete remaining budget/access/input blocker. Finishing a commit does not
pause the cycle.

### S1-010 standing retry checkpoint

Standing retry controls are integrated and independently reviewed. Qualification015
passed339 tests/1063 subtests in476.541 seconds, zero failures/errors/skips;
corrected full integration1182 tests has no failures, six known unrelated errors
and five skips. CPU evidence is committed as af603858; exact reviewed REVIEW/DO
and live resource/ledger binding as b1b43c58.

S1-010 consumed one fresh identity under standing authority. It generated and
individually qualified510 rows and wrote an intermediate passed acceptance,
then failed accepted-progress publication because the35,338,620-byte aggregate
result exceeded the32MiB progress metadata limit. No accepted finish result or
terminal receipt exists. Cleanup is confirmed, survivors empty, stop_required
true; exact failed/helper/unpublished acceptance evidence is preserved in
s1-recovery-010/outcome (69f7884d). The prior alias correction reached local
acceptance; this does not retroactively accept010. It was not a timeout.

Next: correct the finite aggregate result/inventory bounds while preserving
256KiB row and control/checkpoint caps, validate the actual aggregate-size paths,
obtain independent reviews and current qualification016, then review/admit a fresh
S1-011 under standing authority. No reset, duplicate replay or historical result
promotion. Current GPU charge11141.708 seconds, allocated artifacts115691421696
bytes, no active allocations; recheck live budgets before dispatch.

Aggregate correction273d80a1 is integrated with both independent reviews clear.
Full integration015 ran1185 tests, no failures, six known unrelated errors/five
skips. Qualification016 passed342 tests/1063 subtests in475.427 seconds under600
seconds with unchanged104-source inventory; wrapper SHA256
ce21a33039649f2cf6c1727fd8278e756512418699c6af22cbaa52d1cceaba21.
Fresh011 preparation/review/live admission follows under standing authority.
