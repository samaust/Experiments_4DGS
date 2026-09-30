## Problem Statement

The user wants to compare generated outputs visually instead of supplying an external human annotation bundle. The code must produce comparable frames, motion clips and diagnostics, with clear provenance and unavailable-result states.

## Solution

Implement and publish an immutable qualitative review package and local viewer. Preserve the exact generated result lineage and prepare a simple human review form; no human labeling or annotation import is required.

## User Stories

1. As a reviewer, I want the reference and candidates at the same frame/time/viewpoint, so that appearance differences are comparable.
2. As a reviewer, I want synchronized clips and common zoom/crop controls, so that motion and detail can be judged fairly.
3. As a reviewer, I want component diagnostics labeled separately from final rendered output, so that I can interpret what I see.
4. As a maintainer, I want each displayed artifact hash-bound to its source result/configuration and ledger state, so that the comparison is reproducible.
5. As a reviewer, I want explicit failed/unavailable items and a simple preference form, so that missing evidence cannot masquerade as quality.

## Implementation Decisions

- Parent #18, workstream #22; tickets #30 and #31. Issue #3 remains completed preparation context.
- Follow the qualitative amendment's frozen presentation and review contract. Code generates the package, manifest and viewer; the human supplies judgments later under #33.
- #30 implements the package contract/viewer and CPU fixtures; #31 publishes actual generated packages. Reopen #30 because its previously completed annotation workflow does not implement this new deliverable. Preserve that former completion as history.
- Package all available declared candidates and show exact reasons for missing arms. Required model stages remain governed by #20/#21 and their current allocations; unavailable arms cannot be silently dropped.
- Acceptance requires the tested package workflow and an actual immutable matched-output package ready for human review. A template alone does not satisfy #31. Human feedback itself belongs to #33.

## Testing Decisions

Test the package request/result boundary with CPU artifacts: shared frame/time/view settings, synchronized clip metadata, result/hash substitution, corrupt media, unavailable candidate states, original-size/full-frame/detail access and read-only viewer behavior. Synthetic artifacts demonstrate engineering behavior only.

## Out of Scope

External annotation production/import, automatic quality judgments, invented human reviews, unapproved new jobs and changing model settings to favor a display.

## Scope and authority

The user explicitly replaced independent annotation-based scoring with human qualitative comparison of generated results, and confirmed frames, clips and diagnostics. This changes the comparison protocol prospectively. Existing results, annotations, metrics, model settings, source pins, accepted inputs and ledger charges remain historical evidence. This specification update launches no model, setup, training or rendering job and grants no new allocation.

The active comparison is defined by [the qualitative amendment](qualitative-comparison-amendment.md) and [Plan 067](../../../plans/plan_067.md). One host GPU remains exclusive; current execution, qualification, cleanup and resource-budget gates apply. Synthetic reviews are test fixtures, never human judgments. The external annotation bundle, contributor attestations, blind annotation review, adjudication, masks and 232-image labeling workload are no longer completion requirements.
