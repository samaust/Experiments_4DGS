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

#19 is complete as one audited failed recovery005 outcome, not successful S1 calibration. E5 recovery001 failed native imports; its FFmpeg binding correction is implemented but E5/D2 remain unresolved. D3/D4 fit/check completed. The final CPU source qualification timed out at 240 seconds and is pending further authorization. These engineering gates are not removed by the qualitative amendment.

## Scope and authority

The user explicitly replaced independent annotation-based scoring with human qualitative comparison of generated results, and confirmed frames, clips and diagnostics. This changes the comparison protocol prospectively. Existing results, annotations, metrics, model settings, source pins, accepted inputs and ledger charges remain historical evidence. This specification update launches no model, setup, training or rendering job and grants no new allocation.

The active comparison is defined by [the qualitative amendment](qualitative-comparison-amendment.md) and [Plan 067](../../../plans/plan_067.md). One host GPU remains exclusive; current execution, qualification, cleanup and resource-budget gates apply. Synthetic reviews are test fixtures, never human judgments. The external annotation bundle, contributor attestations, blind annotation review, adjudication, masks and 232-image labeling workload are no longer completion requirements.
