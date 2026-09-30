# Plan 031 execution assessment after fresh attempts

## Actual outcomes

The user's approval was consumed by exactly one E5 setup recovery001 and one S1 calibration recovery005. E5 failed native import qualification after 74.80530964198988 seconds; its editable build succeeded. S1 reached one model forward and failed first-row numerical qualification after 29.81751602998702 charged seconds. Zero of 510 calibration rows qualified. Both attempts published/retained their actual failures, confirmed cleanup, left no surviving ownership or reserved allocations, and did not automatically retry. S1 reconstruction was not authorized.

All 283 previously inventoried historical evidence hashes remain unchanged. The canonical ledger chain contains 520 events with head SHA256 0eb907e0a3e6509c6863309f289b35aff6d317d48553b1900f33d7f741f64a5f.

## Observed defects

S1's pinned GroundingDINO deliberately pads six caption-token logits to 256 columns with negative infinity. The actual first row contains exactly 900x250 such padding values, zero padded probabilities, finite active logits and no NaN or positive infinity. The validator rejected this native representation because it required every raw logit to be finite. Any correction must preserve raw evidence and recognize only frozen native padding while retaining all other numerical checks.

E5 already contains the imageio-ffmpeg wheel's bundled executable. Imageio's discovery tries to execute its version probe; the isolation guard correctly rejects subprocess execution and the library converts that rejection into a misleading missing-executable message. The repair must bind and verify the managed wheel binary before imports while keeping the guard intact, then bind downstream D2 imports to qualified setup evidence.

## Human evidence

The user confirmed: "I don't have human annotation bundle". The workflow and exact handoff template are complete, but #31 cannot import independent truth. The saved model-assisted proxy labels cannot become independent human annotations through relabeling. Accuracy scoring, finalist selection and final assessment remain blocked.

## Issue assessment

Preparation children #4–#17 are closed; their preparation parent #3 is now closed. Execution parent #18 remains open. Completed execution tickets are #24, #25 (audited bounded failed outcome), #26, #29, #30 and #32. E5 qualification #27 and D2 #28 remain open. Independent annotation #31 and downstream #33–#35 remain open. S1 successful calibration remains unresolved; the bounded failed outcome must not be reported as calibration success.

## Validation limits

Before the attempts, integrated source qualification002 passed 288 tests and 1030 subtests. The full repository suite ran once: 1037 tests, 1026 passed, five skipped and six existing unrelated errors (missing matplotlib, pytest and plyfile, plus the existing Basketball v6 deadline fixture). No current changed-path error appeared. No configured mypy/pyright was available; AST/syntax checks and strict source-bound receipt validation were used. Further source corrections require a new qualification before any future dispatch.

## Corrections and remaining execution gates

S1's strict native-padding correction is committed as 541b68f2, and E5's managed FFmpeg correction as e41d8950. Focused CPU regressions passed; independent Standards and Spec reviews each found zero issues. See correction-review-001.md and the individual correction audits.

Final current-source qualification is pending: sandbox capture003 failed AF_UNIX helper fixtures, and the host retry stopped before tests on an existing output directory after a failed preparatory `python` alias command. A corrected CPU-only capture requires user authorization under the repository's retry policy. Qualification002 remains valid historical pre-attempt evidence, not a receipt for changed sources. No additional S1/E5 attempt, reconstruction, D2 forward or independent annotation/scoring job has been launched.

The user subsequently authorized corrected CPU qualification; capture004 is running in a fresh directory outside sandbox. Capture003 and the failed host retry are retained intact.

Capture004 finished in 229.21659047697904 seconds without timeout: 288 tests, 1030 subtests, one failure and three errors. All four were REVIEW fixture cases reading the now-consumed live recovery005 state. Production consumed-identity refusal remained correct. A test-only immutable-fixture correction is in progress; no passing current qualification is claimed yet. The user-requested host `python3`/explicit virtual-environment guidance was committed separately in 196584f.
