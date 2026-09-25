# Candidate011 corrections proposal 001

**State: proposed; no implementation, test, or launch clearance.** This follow-on keeps the Plan049/Correction015 behavioral contract and resource limits, and addresses the exact failures in the independently audited Candidate011 receipt. Diagnostic005 and Candidate011 remain failed historical evidence. This proposal does not edit or reinterpret either attempt, its ledger, or its dispatch, status, launch note, admission, or driver artifacts.

## Evidence and authority

This proposal is based on the independent static triage [candidate011-static-correction-triage-001.md](candidate011-static-correction-triage-001.md), SHA-256 `4cea6a58f1ebf0cb261f1466d97362b99de258e054a7343fda8c5f930f7d477d`, and the post-admission audit [candidate011-post-admission-audit-001.md](candidate011-post-admission-audit-001.md), SHA-256 `37c347c6028a41b2c995569653b0419513c97009af58228e4c1e65784a33fd0a`. The triage's five frozen source hashes and referenced failure-evidence hashes, plus the three additional authority-propagation source hashes below, are controlling inputs; any difference before implementation requires a refreshed static assessment and independent plan review. Candidate011's live operational B/H and Main-session charges have separately passed bounded retirement review, but that finding does not clear the older diagnostic006/candidate009 native-H=1 charges and does not authorize a new launch.

| Additional authority-propagation source | SHA-256 |
| --- | --- |
| `docs/resolve-blocker/plan031-progress-20260922/launch-049-exec.py` | `e28b3874d1830c934fae624eee254a25d25517fcc22cb6fa41f4da5191d62af7` |
| `scripts/vipe_benchmark/s1_validation_contract.py` | `860a18d066b8b13999f1cf21b6b89c1a1e9003ce06e00e6f013dbd3fca782a55` |
| `tests/test_vipe_benchmark_s1_recovery.py` | `205a76a29bf43b38d440638f4123a76509ed5003d3f77ae121d62fb50ffe430b` |

The implementation path list in Correction015 cannot be expanded by inference. This proposal is the necessary reviewed follow-on to add only the exact source portions below. The existing user instruction permits autonomous selection of a recommended future option; after distinct independent plan review, Main may adopt a passing recommendation as Plan049 Correction017, recording this proposal/review hash pair in a new authority record. A reviewer NEEDS_REVISION verdict requires correction and a new independent review. No source edit begins before PASS review and explicit Main adoption.

## Candidate011 findings and fixed requirements

The primary failure is in `scripts/vipe_benchmark/s1_helper_session.py`: the owned-workload predicate requires the adopted Plan049 SHA to equal the older immutable dispatch's embedded original Plan049 SHA. The validator contract intentionally requires two linked identities: verify the original Plan049 record inside the immutable dispatch, and verify that the launch note binds the exact dispatch file record plus the adopted current Plan049 file record. Correct the predicate to enforce that graph; do not require a second direct original-Plan049 binding in the note. Keep the complete status-record equality and subsequent `no_timeout_launch` validation. Do not rewrite any historical authority artifact.

The receipt also establishes three separate correctable defects. The next-input observer in `tests/test_vipe_benchmark_supervisor.py` converts text writes with `bytes(str)`, raising `TypeError`; restrict instrumentation to the intended production stream and record text using the actual stream encoding while preserving exact writes, byte offsets, and the `load_rgb(frame62)` target. In `tests/test_vipe_benchmark_s1_helper_fixtures.py`, the acknowledgement-receipt witness treats every `s1_progress.encode` as the named successor; identify the exact publisher diagnostics object and causal stage/return, recording unrelated encodes separately. If a true post-ack encode is at/after W, preserve the failure and correct production behavior rather than exempting it. In `scripts/vipe_benchmark/s1_progress.py`, an injected scandir-close error is incorrectly treated as a secondary to ambient primary while cleanup marks an iterator owner resolved despite `closed=false`; preserve primary/secondary ordering and retain uncertain ownership after any unconfirmed close, with no retry.

The L03 owner-block fixture sleeps before production publishes its native joinable-thread identity. In `tests/test_vipe_benchmark_s1_helper_fixtures.py`, publish the real current native identity before only this intentional sleep, using the existing kernel-derived identity representation; retain the sleep and every ready/setup/cleanup deadline. Plan046's before-deadline failure appears downstream of the primary authority mismatch; make no Plan046 timing or assertion change under this proposal. Recheck through the authorized full diagnostic after the authority fix; if it persists, save exact branch/terminal side effects and seek a separately reviewed follow-on before changing anything.

## Exact source scope

Only these source portions are proposed:

| Path | Proposed portion |
| --- | --- |
| `scripts/vipe_benchmark/s1_helper_session.py` | Correct the dual original/adopted Plan049 owned-workload predicate; retain exact dispatch, status, note, and current-plan record checks. |
| `scripts/vipe_benchmark/s1_progress.py` | Preserve uncertain iterator/owner state after unconfirmed close in the selected runtime-guard cleanup path; preserve primary and ordered secondary errors and one-attempt/no-blind-retry semantics. |
| `tests/test_vipe_benchmark_supervisor.py` | Correct only next-input stream instrumentation for text and binary writes; preserve write-through behavior, exact target and all W/equality assertions. |
| `tests/test_vipe_benchmark_s1_helper_fixtures.py` | Correct only the ack-receipt successor witness and L03 native-identity-before-block ordering; add distinguishing evidence/negative controls inside existing fixture methods. |
| `docs/resolve-blocker/plan031-progress-20260922/launch-049-exec.py` | Mechanically propagate the fixed ordered Correction017/addendum authority record into the future-candidate authority list. No session identity, admission, transport, resource, sampling, command, environment, deadline, or ledger behavior change. |
| `scripts/vipe_benchmark/s1_validation_contract.py` | Mechanically propagate the same record in the same order; no schema or predicate relaxation. |
| `tests/test_vipe_benchmark_s1_recovery.py` | Mechanically propagate the same record in the existing positive current-authority fixture and its negative controls. |

The source manifest and snapshots may name these seven paths only within the existing source-member count and closure. No new method, callback, scenario, selector, test, process, thread, sidecar, path domain, or input/output authority is added. Existing Correction015 source constraints, including the 73-method HelperSessionTests selector, 602 declared callbacks and 114 named deadline controls, 42 L/P scenarios, six P outcomes, and final aggregate dimensions, remain fixed. No other test assertion, expected exception, clock, W/C boundary, setup/cleanup budget, timeout, resource cap, or ordering may change.

## Review, implementation, and validation gates

1. A distinct reviewer checks this exact proposal and source/evidence mapping. PASS is required before adoption.
2. Main records adoption as Correction017, then takes a fresh source/authority hash and exact impact map. The future candidate must bind this correction in the same ordered authority list in driver, contract, positive fixture, and launch records. Historical candidates remain immutable.
3. Implementation is limited to the exact portions above. Preserve all original failing evidence. No focused test or diagnostic may run on the changed source before independent exact-source review.
4. A distinct independent source reviewer verifies exact final source and authority hashes, positive and negative original/adopted-plan controls, text/binary write fidelity, named ack successor identity and causal order, real L03 native identity, uncertain-close ownership retention, and unchanged assertions/declarations/timers. Any scope or semantic mismatch returns to planning; no test or launch is implied.
5. After source-review PASS, run only the focused existing methods/callbacks needed for the fixes, under fresh applicable CPU/process/thread/artifact accounting. Preserve every original deadline/assertion and record focused results as development evidence only; no focused result replaces the complete diagnostic.
6. Before any full diagnostic, perform fresh source/authority hash, artifact-capacity, process/thread ownership and capacity, output-path vacancy, and attempt-index/high-water checks. Use the next vacant higher attempt index (Candidate012 is the earliest possible only if every gate confirms it); do not reuse 006 or 011. Rebuild Main's proof with the exact `exec_command` session handle and persist it immediately. Do not admit based on a driver's self-reported PID. If the returned handle cannot be retained or trusted retirement is unavailable, stop that launch and record the blocker.
7. Only after independent source review, authorized focused verification, and all fresh gates, run the authorized full CPU-only diagnostic in serial order, preserving the unchanged complete selection and every behavioral deadline. Preserve exit status, all assertions, receipt, stderr, ledger and resource measurements. Do not start the final aggregate unless diagnostic and independent acceptance checks pass. Then run the unchanged final aggregate in original order and obtain independent closure review.

All runs remain CPU-only and serial with `B+max(1,H)≤8`, artifact storage ≤150 GiB, memo ≤64 MiB, and the hard whole-ledger cap of 8,388,608 bytes (with the existing per-append guard retained), complete ownership accounting, no operational time ceiling, and every original behavioral deadline intact. No GPU/device, production workload, real ledger, download/setup, or scientific work is authorized. Candidate011 remains failed; no assertion or deadline may be weakened to turn it green.
