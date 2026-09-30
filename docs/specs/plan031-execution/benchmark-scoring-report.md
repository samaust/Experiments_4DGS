**Current scope:** [Scope amendment 001](qualitative-comparison-scope-amendment-001.md) takes precedence: human comparisons and the active viewer cover segmentation and depth only. Motion and neighbors remain historical engineering groups and require no human review for completion. The motion criterion and clip diagnostics remain available where applicable.

## Problem Statement

Generated component and pipeline outputs need a human qualitative comparison with traceable evidence. Automatic annotation-based accuracy rankings no longer match the user's objective.

## Solution

Collect real human observations on matched frames, synchronized clips and diagnostics, freeze justified preferences for downstream choices, and report visual strengths, motion behavior, artifacts and sharpness with execution limitations.

## User Stories

1. As a reviewer, I want to compare actual generated results and record preferences, ties and uncertainty without drawing masks or assigning temporal identities.
2. As a reviewer, I want each observation linked to a frame or clip time, so that strengths and defects can be revisited.
3. As a maintainer, I want review records bound to immutable packages and exact candidates, so that substitutions cannot alter a decision.
4. As a user, I want qualitative choices justified by visual evidence and practical constraints, so that tradeoffs are explicit.
5. As a maintainer, I want downstream and final outputs reviewed separately, so that a component preference does not imply an unobserved combined result is better.
6. As a reader, I want failed/unavailable arms and execution costs reported, so that comparison scope and feasibility remain honest.

## Implementation Decisions

- Parent #18, workstream #23; tickets #32–#35. #32 implements/tests human-review records and decision handoff, #33 collects actual human feedback and freezes initial choices, #34 executes only authorized downstream generation and publishes/reviews its actual output packages, #35 produces the final assessment.
- Reopen #32 for the new qualitative contract. Historical metric fixtures and checkpoints remain evidence of the old scope and cannot satisfy the new acceptance criteria.
- Follow the qualitative amendment's review schema and criteria. One actual human is sufficient; capture appearance, motion, artifacts, sharpness, overall preference, tradeoffs and ties/unjudgeable outcomes with package/candidate/frame references.
- Existing runtime, scale, geometry and license rules remain engineering eligibility. Freeze quality choices from actual human preference records rather than historical metric ranks or automatic ID tie-breaks.
- Staged review avoids dependency cycles: initial isolated packages/reviews and choices precede downstream generation; combined/final results receive a separately bound follow-up review before the final report.
- Run no new model/setup/training/rendering allocation through this spec. #34 must first identify prerequisites, exact generation settings, available existing allocation or a separately approved bounded proposal. Preserve unavailable results when prerequisites or authority are absent.
- Acceptance requires real human feedback on the declared available comparison set, immutable choice provenance, required downstream dispositions, and a report linking actual media, observations, engineering costs and limitations. Empty forms/synthetic reviews cannot count as performed review.

## Testing Decisions

Use the package/review request/result and admission/ledger seams. CPU fixtures reject changed package/media/configuration, unknown candidate/frame IDs, missing reviewer/observations, fabricated synthetic acceptance and replay. Cover ties, not-applicable/unclear judgments, blocked choices, frozen selection preservation and engineering eligibility independent of human taste. Final report reconciliation checks exact ledger states and original human records.

## Out of Scope

Pixel/instance/temporal human annotation bundles, required annotation accuracy metrics or statistical significance, fabricated opinions, automatic perceptual rankings and unsupported measured physical accuracy claims.

## Scope and authority

The user explicitly replaced independent annotation-based scoring with human qualitative comparison of generated results, and confirmed frames, clips and diagnostics. This changes the comparison protocol prospectively. Existing results, annotations, metrics, model settings, source pins, accepted inputs and ledger charges remain historical evidence. This specification update launches no model, setup, training or rendering job and grants no new allocation.

The active comparison is defined by [the qualitative amendment](qualitative-comparison-amendment.md) and [Plan 067](../../../plans/plan_067.md). One host GPU remains exclusive; current execution, qualification, cleanup and resource-budget gates apply. Synthetic reviews are test fixtures, never human judgments. The external annotation bundle, contributor attestations, blind annotation review, adjudication, masks and 232-image labeling workload are no longer completion requirements.
