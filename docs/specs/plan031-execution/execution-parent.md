## Current depth extension — Plan 069

This prospective amendment adds generation #44 as a child of #18 and extended human review #45 as a child of #23. Both new specs are ready for agent implementation. #45 is blocked by #44; #34 gains #45 as a blocker; #35 remains blocked by #34.

- Compare exactly D5 MoGe-2 ViT-L, D6 MoGe-3 ViT-L, D7 Depth Anything V2 Metric Hypersim Small, D8 MetricAnything Student PointMap, D9 Video Depth Anything Small, D10 Metric Video Depth Anything Small and D11 Marigold V2 Log-stage2.
- Generate matched anchors and four two-second depth clips per addition plus D2. Require actual new human feedback and an eligible metric-depth choice before further depth-dependent #34 dispatch. Reusable #34 CPU/native-adapter preparation may continue.
- #34 retains the five controlled S2/D*/M/N final-render arms and actual render review; #35 owns the expanded final assessment. No duplicate generation or reporting workstream is introduced.
- Closed #3/#20/#21/#22/#32/#33 and the completed survey keep their original completion scopes. #18/#23 remain open until every child, including #44/#45, is complete.
- Preserve historical Plan 031/protocol/configuration, old reviews, D4 proposal, results and resource charges. The current S1 standing fix-and-retry amendment remains independent and unchanged; it grants no new depth allocation.
- Concrete new depth/setup/download/publication budgets and allocation authority remain prerequisites. One GPU and the existing 22 GiB device limit apply. This specification publication starts no experiment and increases no resource cap.

This amendment supersedes earlier depth-choice and annotation-dependent instructions below for future work. Implementation details and the user-confirmed test seams are in #44/#45 and Plan 069.

## Earlier issue scope and checkpoints (preserved)

## Current comparison scope — user correction, 2026-09-30

The initial isolated viewer comparison covers **segmentation and depth**. Motion (M0–M2) and neighbors (N0–N2) are excluded from that isolated pictures/videos comparison. Their effects **must still be compared on final renders**, under downstream #34/#35. The user explicitly clarified that their effects can only be evaluated on the final render.

See `docs/specs/plan031-execution/qualitative-comparison-scope-amendment-001.md` and Plan067. Preserve the original hash-pinned amendment, packages, scientific/runtime/ledger records and historical completion. Applicable motion criteria/segmentation clips remain supported. Downstream acceptance must include matched final renders exposing motion and neighbor method effects, with real human feedback bound to those outputs. Engineering prerequisites and explicit allocations still apply; no new M/N winner, experiment, training or rendering is authorized. Parent closure still requires every child complete.

## Problem Statement

Preparation #3 is complete, while execution has bounded failed outcomes, unresolved runtime/depth work and generated results awaiting visual comparison. The user now wants code-generated frames, motion clips and diagnostics followed by human qualitative judgment.

## Solution

Coordinate the existing five execution workstreams: bounded S1 recovery (#19, complete as an audited failed outcome), E5 recovery (#20), depth fit/check (#21), qualitative package generation (#22), and human qualitative comparison/downstream reporting (#23). Apply the recorded comparison amendment and close this parent only after every child is complete with verified evidence.

## Implementation Decisions

- #18 remains the execution parent; #3 remains completed related preparation. Preserve the native child hierarchy and all historical outcomes.
- Follow the qualitative comparison amendment and Plan 067. Remove the external annotation bundle and annotation-based quality scoring as completion gates. One actual human reviews generated matched frames/clips/diagnostics using the stated criteria.
- Preserve accepted inputs, model/source/runtime pins, role boundaries, generation settings, engineering scale/geometry gates, consumed attempts and ledger charges. Qualitative selection replaces automatic metric-based quality ranking prospectively.
- Keep one GPU worker, serial setup, 22 GiB peak device ceiling, 93,600 cumulative GPU seconds, 57,600 setup seconds, 57,600 CPU seconds, at most eight CPU workers, 60 GiB downloads and 150 GiB artifacts. New training/rendering work needs a bounded reviewed allocation before execution; documentation edits grant none.
- Use immutable generated package and human review request/result interfaces with existing admission/ledger lineage. Publish matched review artifacts first, collect real human feedback, freeze choices, then resolve authorized downstream generation and follow-up review.
- Parent acceptance requires all child acceptance evidence, explicit failed/blocked/unavailable dispositions, actual human qualitative observations on the declared scope, final report and reconciled resource/cleanup evidence. Missing annotation files are no longer a blocker; missing generated comparisons or human review are distinct open work.

## Testing Decisions

CPU fixtures validate media identity/time/settings, immutable package/review binding, missing-result handling, actual-review requirements, tied choices and negative admission cases. Preserve runtime/supervision/scale checks. Obtain reviews and record final testing limitations honestly; verify every child before parent closure.

## Current outcomes

#19 remains complete as an audited failed bounded S1 outcome, not successful calibration. E5 recovery003 failed when import qualification rejected Normalize preprocessing. S1 recovery007 produced and individually qualified all510 rows but failed final acceptance after an owned temporary Torch source file had been deleted; no accepted calibration or terminal receipt exists. Both consumed attempts are preserved with confirmed cleanup. #27 remains open and D2 #28 remains blocked; D3/D4 fit/check are complete.

The user authorized CPU corrections under the clarified retry rules. Exact Normalize preprocessing exemption and immutable supported Torch-generated source capture are implemented in separate worktrees and integrated. Independent Standards/Spec reviews found no blocking issues. Integration fixture bugs were fixed and retried after validation, preserving failed captures. Qualification010 passed306 tests/1035 subtests in239.138 seconds under600 seconds; the old240-second qualification timeout is no longer the current blocker. The full suite still reports six known unrelated errors/five skips.

No new setup/GPU attempt was allocated during correction. The547-event ledger and consumed failures remain intact. New bounded E5 recovery004/S1 calibration recovery008 scope is proposed in `docs/research/vipe-alternatives/plan067-execution/fresh-runtime-attempts-proposal-002.md`; approval, reviewed fresh admission controls/current qualification and live checks are required before execution. Actual human feedback#33 and downstream#34/#35 remain pending. No incomplete issue is closed.

## Scope and authority

The user explicitly replaced independent annotation-based scoring with human qualitative comparison of generated results, and confirmed frames, clips and diagnostics. This changes the comparison protocol prospectively. Existing results, annotations, metrics, model settings, source pins, accepted inputs and ledger charges remain historical evidence. This specification update launches no model, setup, training or rendering job and grants no new allocation.

The active comparison is defined by `docs/specs/plan031-execution/qualitative-comparison-amendment.md` and `plans/plan_067.md`. One host GPU remains exclusive; current execution, qualification, cleanup and resource-budget gates apply. Synthetic reviews are test fixtures, never human judgments. The external annotation bundle, contributor attestations, blind annotation review, adjudication, masks and 232-image labeling workload are no longer completion requirements.


## Execution checkpoint — 2026-09-30

- E5 recovery004 succeeded in83.510 seconds, exact pinned native imports/inventory qualified, cleanup confirmed. Issues27/20 completed and closed after all children closed.
- Original D2 fit/check completed serially in18.507/14.602 seconds,30inputs each, both scale gates passed with identical frozen scale1.0899176481863033. Issues28/21 closed after all children closed; original earlier depth evidence preserved.
- S1 recovery008 consumed once and failed first-result generated-source temporary ownership in36.641 seconds, zero qualified rows. Cleanup confirmed, actual terminal receipt published, stop_required=false. No new S1 attempt is authorized. CPU correction now owns only the admitted Torch direct import constructor; focused19 tests and independent reviews pass, fullsuite retains six existing unrelated errors. Current qualification012 is running before a fresh bounded S1 proposal.
- Actual reviewer samaust's segmentation observations and confirmed overallS2 preference are imported and frozen for research component selection. Commercial/non-AGPL permission and unseen downstream generation remain separate gates. Playback is available for some selections; no defect is claimed.
- New immutable depth package002 exposes actualD2 from accepted outputs using27.420-second CPU generation and0.601-second publication. Old package001 and segmentation review remain unchanged. Human depth review submitted for package001 is being preserved with its original scope; motion/neighbors and newD2 judgment remain pending. Issues33–35/23/18 remain open.

Evidence: commits77159683/6b63ba5b; `docs/research/vipe-alternatives/plan067-execution/d2-fit-check-001/`, `human-review-001/`, `depth-package-refresh-002/`; S1 outcome at `docs/research/vipe-alternatives/plan031-execution/s1-recovery-008/outcome/`. No completed historical failure is rewritten or unaccepted row promoted.
