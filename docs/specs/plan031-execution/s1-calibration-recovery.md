## Problem Statement

S1 has no successful calibration result. Recovery004 consumed its allocation during prelaunch resource sampling, and terminal publication failed after the retained helper became unavailable. The maintainer needs a reviewed next action that preserves those failures and can produce a bounded, auditable outcome.

## Solution

Validate the user-requested two-second sampler behavior and terminal evidence handling, then prepare a fresh calibration-only recovery proposal against the live consumed history. Dispatch exactly one additional attempt only after its concrete proposal receives explicit approval and live admission passes.

## User Stories

1. As an operator, I want the original failure and recoveries 001–004 preserved, so that the next proposal cannot erase prior attempts.
2. As an operator, I want a fresh live ledger snapshot, so that the proposal binds current consumption and cleanup.
3. As a maintainer, I want the two-second sample limit applied consistently, so that a valid sample between one and two seconds is accepted.
4. As an operator, I want shorter phase and job deadlines retained, so that the sampler cannot extend the allocation.
5. As a maintainer, I want late sample and census replies rejected, so that stale observations cannot authorize work.
6. As an operator, I want GPU exclusivity checked before and during work, so that foreign compute processes trigger the required stop.
7. As a maintainer, I want prelaunch sampling exercised without a model allocation, so that control-path repairs can be checked before approval.
8. As a maintainer, I want terminal publication failure investigated, so that primary failure and cleanup evidence remain available.
9. As a reviewer, I want a current source-bound CPU qualification, so that earlier receipts cannot qualify changed source.
10. As a reviewer, I want an exact asset and request binding, so that a recovery cannot substitute the candidate, weights or inputs.
11. As an operator, I want a fresh recovery identity, so that consumed recovery004 cannot be redispatched.
12. As a user, I want a REVIEW proposal that cannot dispatch, so that review itself cannot consume an allocation.
13. As a user, I want one concrete bounded attempt to approve, so that authorization has an explicit scope and resource cap.
14. As an operator, I want at most 3,600 seconds for an approved calibration attempt, so that the recovery remains bounded.
15. As a research reviewer, I want the full 510-row calibration contract, so that a reduced cardinality cannot masquerade as completion.
16. As a maintainer, I want the existing 256 KiB progress-row bound retained, so that the accepted asset-hash row remains within its contract.
17. As an operator, I want first-result qualification or explicit unavailability recorded, so that the earliest completed stage is distinguishable from prelaunch failure.
18. As an operator, I want worker and helper cleanup confirmed, so that no orphaned ownership survives the attempt.
19. As a research reviewer, I want calibration and reconstruction states reported separately, so that a calibration outcome cannot imply reconstruction readiness.
20. As a maintainer, I want an immutable outcome and issue assessment, so that the experiment can be evaluated against its actual bounded result.

## Implementation Decisions

- Parent: #18. Related preparation: #3 and #5/#16; the preparation tickets remain complete.
- Retain the existing S1 semantic amendment, prescribed E1 runtime, source/model assets, frozen request, annotation policy, progress membership and process-file preservation amendment.
- Use two seconds for resource-sample dispatch and acquisition validation, with the earlier caller deadline taking precedence. Preserve monitor tick, resource-ceiling, exclusivity and cleanup checks.
- Check sampling and publication through the controller/helper and ledger boundary. Preserve the primary failure if terminal publication also fails; do not synthesize successful first-result evidence.
- A next numbered identity must bind the exact cleaned-up recovery004 failure, current ledger prefix, source qualification and reviewed authorization. Extend recognition only for that reviewed identity; reject skips, duplicates and unknown recoveries.
- A REVIEW document is fail closed. A DO document and registration require separately recorded explicit approval for exactly one new calibration attempt. The generic resume instruction does not reopen recovery004.
- Retain the 3,600-second attempt cap, one GPU, cumulative limits, full 510-row membership and unchanged scientific recipe. Calibration authorization grants no reconstruction or repeat allocation.
- Acceptance requires validated control-path changes, current qualification, an explicitly approved bounded attempt or a clearly recorded approval block, and exact outcome/cleanup evidence. Keep the issue open while a required authorization or outcome is missing.

## Testing Decisions

- Test through admission/ledger and the worker request/result seam using existing S1 recovery and supervisor fixtures.
- Cover samples between one and two seconds, rejection at two seconds, shorter deadlines, stale/late census replies, resource excess, foreign PIDs and primary/secondary failure preservation.
- Cover refusal of REVIEW, consumed identities, altered assets/requests, changed source and malformed approval; prove that read-only qualification cannot append an allocation.
- Retain independent membership, numerical, progress-row and first-result checks. Run source-bound CPU qualification on the final integrated source before any approved dispatch.
- After dispatch, verify the exact ledger append sequence, result or failure artifacts, cleanup, charges and preservation of all earlier hashes.

## Out of Scope

- Redispatching recoveries 001–004, approving the new attempt through this spec, or granting a general retry pool.
- S1 reconstruction, extra smoke jobs, semantic tuning, smaller inputs, changed precision/thresholds or an alternate model.
- Claiming independent benchmark accuracy from proxy annotations or completing a failed run through retrospective fabricated receipts.

## Further Notes

- Recovery004 failed in prelaunch after 1.031292362 recorded seconds. Cleanup is confirmed, surviving PIDs are empty, terminal publication is unavailable, and no model worker output exists.
- The current two-second sampler repair is committed and source-qualified; the separately observed terminal publication failure still requires an assessment.
- A new attempt is not authorized by publishing this issue. The reviewed proposal must identify any additional allocation before asking for approval.
