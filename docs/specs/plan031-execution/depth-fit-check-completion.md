## Problem Statement

D2 has no fit/check evidence because E5 is unqualified. E6 and E7 now qualify D3 and D4, and both candidates have completed 30-input fits with passed scale gates, but their frame-175 checks remain pending. The maintainer needs complete, correctly ordered depth evidence without repeating consumed work.

## Solution

Reuse the completed D3/D4 fits and qualified E6/E7 environments, run the remaining original checks after live admission, and run the unstarted D2 fit/check only after E5 recovers and the required resume is recorded. Bind every check to its candidate’s frozen fit and exact accepted inputs.

## User Stories

1. As an operator, I want current depth-slot states checked, so that consumed fits cannot be repeated.
2. As an operator, I want qualified E6 and E7 reused, so that successful setup is not rebuilt.
3. As a research reviewer, I want D3 and D4 completed fits reused, so that the checks test their originally frozen scales.
4. As an operator, I want D2 blocked until E5 qualifies, so that an incomplete runtime cannot enter inference.
5. As an operator, I want unstarted D2 slots resumed through the checked ledger, so that new work has explicit provenance.
6. As an operator, I want protocol stage order enforced, so that dependency checks cannot be bypassed.
7. As an operator, I want one GPU stage at a time, so that the host remains exclusive.
8. As a research reviewer, I want frame-100 fitting and frame-175 checking kept separate, so that selection observations cannot influence fitting.
9. As a research reviewer, I want the prescribed 30-camera membership verified, so that missing or substituted inputs cannot pass.
10. As a research reviewer, I want camera intrinsics and accepted image footprints preserved, so that depth conversion uses the intended geometry.
11. As a research reviewer, I want candidate camera-z metre conversions retained, so that a second focal correction cannot distort units.
12. As a research reviewer, I want validity and clamp diagnostics retained, so that invalid native outputs remain visible.
13. As a maintainer, I want every fit/check artifact bound to the exact input manifest, so that a check cannot substitute another accepted dataset.
14. As a maintainer, I want the candidate and scale protocol bound to the frozen fit, so that a check cannot borrow another candidate’s result.
15. As an operator, I want a failed fit gate blocked before check inference, so that ineligible fitting cannot spend a later allocation.
16. As an operator, I want result counts and output hashes checked, so that partial or orphaned results cannot qualify.
17. As a research reviewer, I want passed consistency gates distinguished from physical accuracy, so that engineering results do not imply independent ground truth.
18. As an operator, I want failures and cleanup recorded once, so that a candidate failure cannot create an automatic retry.
19. As a maintainer, I want existing D0/D1 evidence preserved, so that future provenance fields do not rewrite historical receipts.
20. As a maintainer, I want a per-candidate completion assessment, so that the remaining scoring work sees validated or explicitly blocked evidence.

## Implementation Decisions

- Parent: #18. Related preparation: #3 and #10–#13. D2 completion depends on the E5 recovery child; D3/D4 checks can progress independently of that repair.
- Use existing component requests, runtime qualification resolution, stage-order checks, scale evaluation and immutable result/artifact handoffs.
- Preserve the prescribed source/model pins, float32 behavior, native camera-z conversion, masks, intrinsics, image footprints, fit/check roles and protocol gates for each candidate.
- Future scale fits carry the verified input-manifest record in provenance. A check requires the identical manifest, candidate and scale protocol plus a successfully qualified frozen fit. Preserve historical D0/D1 receipts and their request-level audits.
- Run frame-100 fits and frame-175 checks with the prescribed 30-input membership. Reuse D3/D4 fits already completed under the original allocation.
- Account an unavailable runtime or failed fit as blocked before inference. Reopen only unconsumed accounted slots after their dependency is resolved and the applicable explicit resume is recorded.
- Each actual stage uses its original remaining allocation, live source-bound admission, single-GPU supervision and exact result membership/hash validation. A failure does not authorize a new model attempt.
- Acceptance requires ledger-frozen successful fit/check artifacts and gate assessments for each qualified candidate, preserved earlier evidence, and explicit unresolved dependency/failure accounting. Do not close while a required candidate stage remains unstarted or blocked without a user-approved scope disposition.

## Testing Decisions

- Test through component request/result and frozen scale handoff boundaries; reuse the existing backend conversion and scale/motion fixtures.
- Use independently calculated focal, crop, canonical-depth, clamp and validity examples. Test changed input manifests, altered frozen fits, wrong candidate/role, missing membership and corrupted output hashes.
- Cover no-inference dependency blocks, no check after a failed fit, consumed-stage refusal and reuse of completed fits.
- After real stages, verify exactly 30 accepted inputs, actual frozen-fit reuse, passed or failed protocol gates, allocation charges and cleanup.
- Independent physical-depth accuracy requires separate reference evidence; consistency fixtures and proxy masks cannot establish it.

## Out of Scope

- Re-running D0/D1, completed D3/D4 fits or consumed failed stages.
- Additional model/setup allocations, scientific tuning, alternate models, changed input roles or aligning predictions to held-out check observations.
- Annotation production, finalist selection, geometry/combined benchmark execution or unsupported physical-depth accuracy claims.

## Further Notes

- At the 499-event snapshot, D3 fit scale is 1.1601640249426506 and D4 fit scale is 1.707435779412766; both fit gates passed and all 30 outputs were recorded.
- E6 target qualification is Python 3.10 / torch 2.0.1+cu118 / torchvision 0.15.2+cu118 / NumPy 1.23.1. E7 target qualification is Python 3.11 / torch 2.5.1+cu124 / torchvision 0.20.1+cu124 / NumPy 1.26.4.
- D2 fit/check have blocked accounts and no consumed model attempt. D3/D4 check allocations are unstarted after the explicitly recorded resume.
