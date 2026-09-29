## Problem Statement

Preparation under issue #3 and tickets #4–#17 is complete, but preparation does not establish completed benchmark execution or independently validated accuracy. The maintainer needs a separate execution workstream that preserves existing results, resolves remaining dependencies, records bounded outcomes, and produces an honest assessment.

## Solution

Coordinate five execution follow-ups under this parent: S1 calibration recovery, E5 DA3 build recovery, remaining D2–D4 fit/check work, independent annotation import, and scoring/reporting. Link issue #3 as related preparation context. Close this parent only after every child is complete and its acceptance evidence is verified.

## User Stories

1. As a benchmark maintainer, I want a separate execution parent, so that completed preparation can be closed independently.
2. As a benchmark maintainer, I want issue #3 linked as related context, so that the preparation and execution acceptance criteria remain distinct.
3. As a coordinator, I want every execution follow-up attached as a child, so that parent completion can be checked against the actual hierarchy.
4. As a coordinator, I want a fresh live-state snapshot before work, so that current attempts and remaining allocations are known.
5. As a coordinator, I want the explicit resume recorded, so that reopened unstarted slots retain their authorization provenance.
6. As an operator, I want one GPU worker at a time, so that the single host GPU remains exclusive.
7. As an operator, I want serial environment setup, so that builds and downloads stay within the shared resource limits.
8. As a research reviewer, I want frozen inputs and scientific contracts preserved, so that later outcomes remain comparable to the recorded study.
9. As a research reviewer, I want historical results retained byte-for-byte, so that a later correction cannot rewrite earlier evidence.
10. As an operator, I want consumed attempts distinguished from unstarted slots, so that a resume cannot silently grant another attempt.
11. As an operator, I want additional attempts proposed for explicit approval, so that the available time cannot be mistaken for a retry pool.
12. As a maintainer, I want E6 and E7 qualifications reused, so that their completed builds are not repeated.
13. As a maintainer, I want completed D3 and D4 fits reused, so that their consumed fit allocations and outputs remain intact.
14. As a maintainer, I want E5 failure tracked separately, so that the missing build requirement receives a bounded repair.
15. As a maintainer, I want S1 calibration distinguished from reconstruction, so that calibration approval cannot authorize an unrelated branch.
16. As a research reviewer, I want proxy annotations distinguished from independent human evidence, so that engineering checks do not imply scored benchmark success.
17. As a research reviewer, I want physical-depth limitations stated, so that scale consistency cannot be reported as independently measured accuracy.
18. As an operator, I want required stops and cleanup recorded, so that a failed run cannot continue with unresolved ownership.
19. As a maintainer, I want source-bound qualification refreshed after changes, so that old test receipts cannot qualify new code.
20. As a maintainer, I want validated local milestone commits, so that implementation and evidence can be reviewed without a push.
21. As a research reviewer, I want a final assessment of eligible, failed, blocked and unavailable arms, so that the comparison explains what the evidence supports.
22. As a maintainer, I want parent closure only after verified child closure, so that unfinished execution work remains visible.

## Implementation Decisions

- This is a new execution parent. Issue #3 is related context and is not this parent or the parent of these execution children.
- The initial snapshot is the existing Plan 031 run, starting from commit 47f78cde823c2b7e4d3a88378de1a03aab874b17 and a verified 499-event ledger. Preserve its original prefixes and earlier artifacts.
- The user explicitly authorized resume and continuation on 2026-09-29. The recorded resume reopened only the original unstarted E5–E7 setup and D2–D4 fit/check slots. Additional consumed-arm attempts require a fresh reviewed authorization.
- Retain the frozen scientific configuration, source/model pins, accepted images, roles, precision, resolutions, thresholds and selection rules. The user-authorized S1 resource-sample limit is two seconds, capped by shorter phase/job deadlines.
- Keep one GPU worker, a 22 GiB peak device ceiling, 93,600 cumulative GPU seconds, 57,600 cumulative setup seconds, 57,600 CPU preparation/scoring/report seconds, at most eight CPU workers, 60 GiB new downloads and 150 GiB new artifacts. Preserve all prior charges.
- Use the existing controller, worker request/result, admission, ledger, runtime qualification, annotation import and aggregation/reporting interfaces. Each child must check current dependencies before dispatch.
- Review and commit completed implementation milestones locally. A commit is a checkpoint; continue authorized independent work while respecting required stops and budgets.
- Parent acceptance requires verified completion of all five child specs, preserved history, no unreconciled worker ownership, and a final evidence-based assessment. A stopped or blocked experiment is not silently converted into success.

## Testing Decisions

- Use the pre-agreed worker request/result contract and admission/ledger transitions as the primary engineering seams; use the annotation import boundary for external human evidence.
- Prefer CPU fixtures with fake runtimes, immutable inputs, independent numerical expectations and controlled failure injection. Test outcomes, memberships, hashes and state transitions rather than private implementation structure.
- Reuse existing setup recovery, supervision, backend, scale, annotation and aggregation fixtures. Give source-bound qualification a quiet CPU window.
- Check historical evidence hashes, ledger prefixes, allocation counters, source membership and cleanup at milestones. Run affected single test files and the full suite once at implementation completion; record environment limitations explicitly.
- Use independent Standards and Spec reviews for completed implementation. Verify the live issue hierarchy before parent closure.

## Out of Scope

- Repeating completed preparation or placing these follow-ups beneath issue #3.
- Resetting consumed allocations, automatic retries, unapproved extra setup/GPU jobs, scientific tuning, fallback runtimes or changes to frozen input membership.
- Treating proxy truth as human evidence, inventing physical reference measurements, contacting contributors without authorization, or claiming accuracy unsupported by independent evidence.
- Pushing commits, deployment, production migration or alteration of unrelated renderer experiments.

## Further Notes

- Related preparation: #3; all preparation tickets #4–#17 were verified closed. Execution outcomes are separately recorded.
- E5 setup failed because Hatchling could not import editables. E6 and E7 setup qualified successfully. D3 and D4 fits each completed 30 inputs and passed scale gates; their checks are pending. D2 fit/check remain blocked by E5.
- S1 recovery004 is consumed after a prelaunch sampling timeout, with confirmed cleanup but no model result or terminal receipt. The two-second sampler change passed 281 tests and 1,030 subtests. That source qualification grants no new attempt.
- The existing 232-image annotation bundle remains model-assisted proxy evidence. Independently reviewed human annotations and independent physical-depth accuracy evidence are unavailable in the current handoff.
- Execution children: #19 S1 calibration recovery; #20 E5 DA3 build recovery; #21 D2–D4 fit/check completion; #22 independent annotation import; #23 scoring/reporting. All five must be closed with verified evidence before parent closure.
