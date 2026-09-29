# S1 execution lookup requalification

The pre-dispatch controller block consumed no attempt and appended no ledger events. The corrected lookup accepts only the ordered prefix of reviewed identities 001–004. Terminal S1 resolution checks the full ledger hash chain and validates the attempt through its own finish, allowing subsequent allocated setup events. A routing regression reproduced the post-finish failure before the correction; all thirteen focused execution tests now pass. Historical fixture tests use the immutable post-003 ledger snapshot and retain the live-prefix preservation check. The historical REVIEW document continues to refuse dispatch.

CPU qualification 005 passed 279 tests and 1030 subtests within the 240-second invocation cap, with the exact current 79-source set unchanged across execution. Timed-mode owned-note preconditions remain explicitly recorded in the receipt; this does not claim a real model outcome. Independent Standards and Spec reviews found no concerns; the Spec follow-up also reviewed the terminal snapshot correction.

The user explicitly approved one calibration recovery 004 attempt, capped at 3,600 seconds with one GPU. DO-002 refreshes the validation/review bindings for the same unconsumed identity. It grants no additional attempt, reconstruction, or reset. Live admission remains required.
