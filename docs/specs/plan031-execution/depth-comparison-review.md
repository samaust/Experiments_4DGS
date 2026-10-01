# Review the extended depth comparison and freeze the downstream depth choice

## Problem Statement

The previous human review selected S2/D4 for its declared research scope. Seven
new depth candidates and a commercial-use requirement create a new comparison.
The original preference cannot select an unreviewed addition or clear a model's
engineering and commercial eligibility. Pending final-render work #34 needs an
explicit new depth choice before spending depth-dependent allocations.

The user wants qualitative comparison of generated images and motion, including
player boundaries, distant people, artifacts and sharpness. Relative-depth detail,
physical-scale consistency and final rendered quality are different outcomes and
must remain distinguishable in both the review and the final assessment.

## Solution

Use the existing immutable package/review handoff to collect one real human's
observations on the extended depth package. Preserve a visual preference and
separately freeze a commercially eligible metric-depth choice, D*, supported by
passing scale fit/check and runtime evidence. Bind that decision to a fresh
downstream proposal under #34, then carry the findings into #35.

This is a new child of #23, blocked by the extended-depth generation workstream
under #18. The completed #33 review retains its original acceptance scope.

## User Stories

1. As a reviewer, I want the seven additions clearly named, so that I know which outputs I am comparing.
2. As a reviewer, I want the same RGB and camera/frame selections across candidates, so that observations refer to matching content.
3. As a reviewer, I want historical D0–D4 frozen-frame references, so that I can relate the new comparison to my earlier observations.
4. As a reviewer, I want synchronized clips for every addition and D2, so that I can compare temporal stability directly.
5. As a reviewer, I want shared zoom and crops, so that close-object edges and distant players are easy to inspect.
6. As a reviewer, I want metric and relative displays labeled, so that color differences are not mistaken for physical-distance differences.
7. As a reviewer, I want fixed clip normalization and clipping information, so that display processing does not hide flicker or saturation.
8. As a reviewer, I want unavailable results explained, so that I can distinguish missing evidence from poor quality.
9. As a reviewer, I want observations linked to exact frames or times, so that another reader can revisit the example.
10. As a reviewer, I want ties, unclear and not-applicable judgments supported, so that I am not forced to invent a preference.
11. As a reviewer, I want to name a visual favorite independently of scale eligibility, so that useful detail in a relative model remains visible.
12. As a project owner, I want a separate eligible metric-depth choice, so that downstream generation receives a valid physical-scale input.
13. As a commercial evaluator, I want exact commercial permission findings attached to the choice, so that visual quality alone cannot establish usability.
14. As a researcher, I want failed engineering gates visible alongside attractive images, so that the tradeoff is explicit.
15. As a maintainer, I want review and choice records bound to exact package bytes, so that later generation cannot silently change their meaning.
16. As a maintainer, I want incomplete feedback kept pending, so that synthetic or empty records cannot count as performed human review.
17. As a project owner, I want the original S2/D4 review preserved, so that the expanded decision does not rewrite earlier conclusions.
18. As a downstream implementer, I want #34's preparation to continue while review is pending, so that useful CPU work can progress.
19. As a downstream implementer, I want new depth-dependent dispatch blocked until the new choice is ready, so that the old D4 binding cannot bypass the expanded review.
20. As a researcher, I want the same D* across the five motion/neighbor render arms, so that each contrast changes only its declared method.
21. As a reviewer, I want final renders reviewed separately after generation, so that depth-map judgments are not treated as observations of unseen renderings.
22. As a report reader, I want the new observations, engineering results and costs reconciled in #35, so that the final account covers the expanded experiment.
23. As a project owner, I want explicit blocked decisions when no model is eligible, so that execution cannot silently fall back to a restricted or unreviewed model.
24. As a project owner, I want dependency and child completion verified before closure, so that published specs are not confused with completed experiments.

## Implementation Decisions

- **Ownership:** #45 is a child of #23 with a native blocked-by link to generation #44. Add #45 as a blocker of #34. Keep #35 blocked by #34 and require the extended-depth evidence in its final assessment. Preserve the existing parent hierarchy and closed #33.
- **Review set:** consume the exact immutable package delivered by the generation spec: D5–D11, historical D0–D4 anchor references and source RGB; motion coverage is all seven additions plus D2 at cameras 1/11/21/31, frames 150–199, 25 fps. Candidate availability and display-domain limitations are part of the review context.
- **Human evidence:** one actual human is sufficient. Capture reviewer identity, review date, package/media bindings, frozen-frame detail, depth-map motion, artifacts, sharpness, overall preference and tradeoffs. Require exact frame/time examples for substantive preferences. Existing valid not-applicable, unjudgeable, unclear and tie outcomes remain supported with reasons. Observations on depth maps do not establish final-render sharpness or artifact quality.
- **Separate decisions:** preserve the visual preference among available candidates and a distinct justified metric-depth choice. The eligible downstream set is D2/D5/D6/D7/D8/D10 after exact runtime, complete fit/check and commercial gates pass. D9/D11 may be visual favorites but cannot provide D*. D0/D1/D3/D4 remain research references in this commercial-depth extension. S2 remains the existing segmentation choice; depth permission does not establish commercial clearance for the entire reconstruction stack.
- **Eligibility handoff:** the generation workstream supplies immutable per-candidate runtime, code/weight/dependency/output-term findings, scale results, actual generation receipts and resource lineage. The choice binds those records and the actual human submission. Changed eligibility or artifacts require a new record. Engineering diagnostics do not automatically rank human quality.
- **Incomplete evidence:** preserve observations when choices remain unresolved. Ties require an explicit reasoned human selection before downstream use. No eligible model or missing human input produces a blocked decision, not an automatic D2/D4 fallback. A blocked decision is reportable but does not release #34 or make unfinished required comparison work complete.
- **Downstream scope:** #34 continues reusable CPU/native-adapter preparation while the new review is pending. New depth-dependent geometry, initialization, training or rendering requires this completed choice and a fresh proposal binding D* and its exact passing fit/check. The original D4 proposal remains historical and cannot be edited or relabeled into the new scope. Revalidate scale, full similarity normalization, camera/time/velocity units, source qualification and allocation authority for the new proposal.
- **Final-render matrix:** use S2 and the same frozen D* for all five arms below. Preserve the existing method-isolation design, source coverage, training endpoint and render settings in the applicable five-arm proposal; changes require an explicit subsequent amendment. Each arm receives fresh execution identities under #34.

| Arm | Segmentation | Depth | Changing regions | Neighbors |
| --- | --- | --- | --- | --- |
| QF-B | S2 | D* | M0 | N0 |
| QF-M1 | S2 | D* | M1 | N0 |
| QF-M2 | S2 | D* | M2 | N0 |
| QF-N1 | S2 | D* | M0 | N1 |
| QF-N2 | S2 | D* | M0 | N2 |

- **Existing work:** keep #34's geometry/initializer/supervisor implementation and #35's reporting ownership. Accepted CPU work may be adapted through the new versioned proposal contract; its old qualification is not automatically current after source changes. Keep S1 continuation independent; neither successful S1 calibration nor its retry authority substitutes for the new depth decision or missing reconstruction evidence.
- **Report and closure:** #35 links old and new human observations separately, all D0–D11 dispositions, commercial findings, scale consistency, runtime/memory/cost evidence and actual final-render review. State that physical accuracy remains unverified without independent metric references. This review completes only with actual package-bound feedback, a justified ready D* handoff and required child completion. Any authorized scope reduction must be explicit. #23/#18 close only after all their children are complete.

## Testing Decisions

- **Confirmed seam:** the user confirmed the existing package/review handoff together with worker request/result and admission/ledger checks. Test observable import, decision and downstream-admission behavior using labeled CPU fixtures; human visual judgment itself requires actual feedback.
- **Prior art:** existing qualitative-review tests reject synthetic-as-human acceptance, blank forms, changed artifacts and sparse motion evidence. They cover ties and engineering-ineligible preferences. Existing final-render tests reject changed proposals, stale choices, substituted prerequisites and nonmatching scale/scene bindings.
- **Review cases:** accept genuine package-bound observations and justified uncertainty; reject wrong reviewer metadata, unknown candidates, invalid frame/time references, changed media, missing generation receipts and synthetic submissions presented as actual.
- **Choice cases:** allow a relative visual favorite together with a different eligible metric D*. Reject D9/D11 as scale providers, unavailable/restricted/scale-failed candidates, automatic tie resolution and a ready decision with missing evidence. Test blocked/no-eligible-model outcomes without releasing #34.
- **Downstream cases:** reject the historical D4 decision in the new proposal mode, fit/check substitutions, different scale manifests, mixed D* across QF arms and altered component combinations. Retain historical-mode validation and verify that review readiness alone grants no GPU allocation.
- **Integration and reporting:** verify native parent/blocking links, continuation of reusable preparation, complete candidate disposition coverage and separation of component feedback from actual final-render review. Check exact record hashes and live child states before closure.

## Out of Scope

- Pixel annotations, independent annotator/adjudicator bundles, automatic quality rankings or agent-authored human opinions.
- Selecting relative depth as physical scale, fitting new relative-to-metric anchors or bypassing commercial/engineering gates.
- Replacing the accepted segmentation choice, adding depth-by-motion-by-neighbor combinations or claiming that depth-map appearance proves rendered quality.
- Launching setup, GPU, training or rendering from a review record without the existing concrete allocation and admission requirements.
- Reopening completed initial review or changing historical decisions, media, proposals and receipts.

## Further Notes

Published specification: [#45](https://github.com/samaust/Experiments_4DGS/issues/45),
parent [#23](https://github.com/samaust/Experiments_4DGS/issues/23), blocked by
[#44](https://github.com/samaust/Experiments_4DGS/issues/44) and blocking
[#34](https://github.com/samaust/Experiments_4DGS/issues/34).

The user explicitly chose review of the new models before #34's further
depth-dependent final-render experiments. This is a new review of expanded
evidence, not a correction to the prior human's valid S2/D4 research judgment.
The user also confirmed matched clips for all seven additions plus D2 and the
existing test seams.

See [Plan 069](../../../plans/plan_069.md),
[extended generation](depth-comparison-extension.md),
[current execution index](README.md) and
[scale-input ADR](../../adr/0002-bind-future-scale-checks-to-input-manifest.md).
The original scope amendment still requires motion and neighbor effects to be
reviewed on actual final renders under #34/#35. Depth-motion clips added here
do not satisfy that downstream requirement.
