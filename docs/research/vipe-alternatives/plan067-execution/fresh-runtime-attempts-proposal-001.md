# Fresh runtime attempt scope — REVIEW only

## Why new approval is needed

The recorded implementation approval authorizes exactly one
`E5-setup-recovery-002` and one `S1-calibration-recovery-006` attempt. Both were
consumed, failed application qualification and confirmed cleanup. Reusing that
approval would exceed its scope. All results, charges and identities remain
immutable.

## Concrete correction evidence

Reviewed fixes are integrated in `a199de1c`, `b34c36e2` and `76b16288`:
temporary supported Triton suppression only during E5 import qualification;
strict S1 file identity with independent permission checks; both pinned required
attention aliases. Combined focused validation passed99 CPU tests. Independent
Standards and Spec reviews found zero findings. Current qualification008 passed
295 tests/1,030 subtests in232.302 seconds under the600-second cap.

## Proposed additional scope

| Identity | Additional attempts | Maximum wall seconds | Purpose |
| --- | ---: | ---: | --- |
| `E5-setup-recovery-003` | 1 | 3,600 | Qualify the unchanged prescribed native runtime with the reviewed import-only correction. |
| `S1-calibration-recovery-007` | 1 | 3,600 | Validate the corrected native runtime provenance and complete510 calibration rows. |

Run serially with one host GPU owner. E5 finishes and confirms cleanup before
S1 starts. No S1 reconstruction or automatic subsequent retry is included.
Reuse the original model/source pins, precision, thresholds, accepted inputs,
source assets and cumulative GPU/setup/CPU/storage/download limits. Preserve
the two-second resource sampler bound and256KiB row metadata cap.

At the536-event terminal ledger snapshot, consumed GPU time is4,635.927 seconds
of93,600 and setup time5,896.481 seconds of57,600. The proposed maxima fit those
unchanged cumulative ceilings. Actual live resources and ledger state must be
rechecked immediately before admission.

## Admission status and required preparation

This is a scope proposal, not a DO document or admission-ready request. No new
identity has been registered, reserved or dispatched. Fresh identity-specific
controls must bind the preserved predecessor failures and be independently
reviewed before execution. Their source changes require another passing current
qualification capture. Only then can immutable exact REVIEW/DO artifacts bind
the new explicit approval and current live-state checks.

Original unconsumed D2 fit/check slots retain their existing authority and remain
gated on successful E5 qualification. Real human feedback under#33 remains a
separate requirement; these attempts do not invent preferences or authorize
downstream training/rendering independently of frozen human choices.
