## Problem Statement

Prepared arms and bounded execution outcomes do not yet form an independently scored comparison. Some evidence is complete, some remains blocked or failed, and the current annotations are proxy truth. The maintainer needs a report that follows the frozen selection rules and clearly states which claims are supported.

## Solution

After validated execution and independent annotation import, score the eligible evidence through the existing aggregation/reporting pipeline, apply the frozen finalist and eligibility rules, and publish a reproducible assessment of completed, failed, blocked and unavailable arms. Preserve explicit limits on independent physical-depth accuracy.

## User Stories

1. As a research reviewer, I want validated ledger-frozen results used, so that orphaned artifacts cannot influence metrics.
2. As a research reviewer, I want independent reviewed truth bound to scores, so that proxy output cannot masquerade as an independent comparison.
3. As an operator, I want missing prerequisites blocked before aggregation, so that partial evidence cannot silently enter scoring.
4. As a research reviewer, I want fit and selection roles isolated, so that held-out observations cannot tune fitting.
5. As a research reviewer, I want prescribed mask and temporal metrics computed, so that the comparison evaluates the intended contracts.
6. As a research reviewer, I want depth consistency and physical accuracy distinguished, so that the report states what each metric establishes.
7. As a research reviewer, I want motion and neighbor metrics tied to frozen inputs, so that the fifteen-arm comparison retains its original membership.
8. As a research reviewer, I want failed and unavailable arms shown, so that the report cannot hide negative or incomplete outcomes.
9. As an operator, I want frozen aggregation checkpoints reused, so that completed scoring is not silently replaced.
10. As a research reviewer, I want eligibility gates applied exactly, so that an ineligible arm cannot enter finalist selection.
11. As a research reviewer, I want deterministic tie and finalist rules retained, so that selection cannot be tuned after seeing results.
12. As an operator, I want combined and repeat prerequisites checked, so that missing source branches cannot authorize downstream work.
13. As an operator, I want later model stages run only with existing valid allocations and explicit authority, so that reporting cannot grant new GPU attempts.
14. As an operator, I want CPU scoring time accounted, so that metrics and reports stay within the shared budget.
15. As a research reviewer, I want metric artifacts and lineage hash-bound, so that the report can be reproduced from accepted inputs.
16. As a research reviewer, I want independent reference measurements required for physical-depth claims, so that consistency against a scale fit cannot imply absolute accuracy.
17. As a user, I want a plain-language assessment of outcomes and limitations, so that engineering readiness is distinguishable from benchmark conclusions.
18. As a maintainer, I want historical reports preserved, so that new assessments cannot rewrite earlier outcomes.
19. As a maintainer, I want standards and spec reviews, so that the report follows both repository rules and study scope.
20. As a maintainer, I want the full final test result and its limitations recorded, so that known environment errors are not presented as a clean full-suite pass.
21. As a maintainer, I want child completion checked before parent closure, so that remaining scientific or execution blockers stay open.
22. As a research reviewer, I want a reproducible final report with unresolved claims explicit, so that future work has a trustworthy starting point.

## Implementation Decisions

- Parent: #18. Related preparation: #3. Completion depends on the other execution children providing their required outcomes and independently reviewed annotations.
- Use the existing aggregate request/result, checkpoint, eligibility/finalist and report interfaces. Score only hash-verified results admitted through their successful ledger state; retain separate failure and block accounting.
- Bind score artifacts to the exact accepted inputs, reviewed annotation bundle, candidate result records, configuration and frozen fit/check evidence. Keep proxy-only outputs distinct from independent scores.
- Follow the frozen mask, temporal, motion, neighbor, scale, geometry, repeat, tie and finalist rules. Preserve role separation and previous frozen checkpoints; never select by retrospectively changed thresholds.
- Do not infer S1 reconstruction readiness from calibration. Missing reconstruction or other dependencies block their downstream arms until a separately authorized result exists.
- This issue does not grant model or setup attempts. Any later allocated geometry, combined or repeat stage requires its existing prerequisites, unconsumed allocation and applicable explicit resume/approval before dispatch.
- Report every prescribed arm as supported by validated evidence, failed, blocked, skipped or unavailable, with precise reasons and ledger/resource lineage. A failed arm is not presented as a successful experiment.
- Claim physical-depth accuracy only where independent metric reference measurements and uncertainty/provenance support it. Otherwise retain an explicit unverified-accuracy limitation; camera-z conversion and scale consistency alone are insufficient.
- Acceptance requires reproducible metric/report artifacts under the frozen protocol, independently reviewed truth for independent scores, explicit dependency and accuracy limitations, final validation/review records, and no concealed unfinished prerequisite. Keep the issue open if required scoring truth is absent.

## Testing Decisions

- Prefer the aggregate/report request/result boundary and existing frozen checkpoint handoff fixtures.
- Test that missing, failed, corrupt, orphaned or proxy-only evidence cannot enter an independent score or finalist decision.
- Use hand-calculated small examples for metrics, eligibility, rankings and ties. Test role isolation, immutable input/truth bindings and refusal to alter frozen checkpoints.
- Validate the final report against actual ledger states and source artifacts, including failed/blocked arms and cumulative charges.
- Run affected single test files during implementation and the full suite once at completion, with exact failures/skips reported. Obtain independent Standards and Spec reviews before closure.

## Out of Scope

- Granting or resetting experiment allocations, extra smoke jobs, candidate tuning, alternative scoring definitions or changing finalist rules.
- Treating proxy evidence as human ground truth, fabricating metric reference measurements, or claiming independently measured accuracy without support.
- Completing the preparation tickets again, unrelated renderer comparisons, deployment or publication beyond the authorized project issue tracker and local artifacts.

## Further Notes

- E6/E7 qualification and D3/D4 fits are engineering evidence; their remaining checks and independent annotations are not yet complete.
- The most recent full CPU suite recorded 1,007 tests with six known environment/historical errors and five skips. The current source-bound S1 qualification separately passed 281 tests and 1,030 subtests.
- Independent physical-depth accuracy remains unverified. A report may explicitly describe that limitation, but must not convert scale/check consistency into an absolute-accuracy claim.
