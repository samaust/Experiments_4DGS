# Independent exact-source review 001 — Plan055 PTY echo

**Verdict: PASS for the bounded source correction and focused control.** This review does not clear a Plan049 launch, admission, diagnostic, aggregate, or runtime proof. Attempt008 remains terminal, unadmitted, and consumed.

## Exact inputs and scope

I independently rehashed adopted `plans/plan_055.md` as `18506f655e7a2c95492fa88a038c869a4c993fa06d3ba628725158eaea77242f`, `correction-001.md` as `89271f7ee1156326a4edce7079ad812ecb93f7674b9522d1233f6e7927d20136`, and the independent plan PASS report as `9f454e6468f53770ed3702eaa889b5f204e93f941aeecb5518034daa8ad26949`. Plan054 remains `91d0ac7191d944b8cf2175b74c74aff3d70d4dba4a530431f223cb8aab2df62d`. I reviewed the blocker diagnosis, implementation report, current two-file diff, current source, existing method, saved attempt008 proof/events, and saved readback records. No historical file was edited.

Fresh SHA-256 of every Plan054 reviewed path:

| Path | SHA-256 |
| --- | --- |
| `docs/resolve-blocker/plan031-progress-20260922/launch-049-exec.py` | `e28b3874d1830c934fae624eee254a25d25517fcc22cb6fa41f4da5191d62af7` |
| `scripts/vipe_benchmark/s1_validation_capture.py` | `62359a258543731b96690d3abc7bd3ddede4809ae76ae4ec2ff83e5c4ce95fd7` |
| `scripts/vipe_benchmark/s1_validation_contract.py` | `860a18d066b8b13999f1cf21b6b89c1a1e9003ce06e00e6f013dbd3fca782a55` |
| `scripts/vipe_benchmark/s1_helper_session.py` | `bb6ea896a73ab3bbdf98e4ac4a9e15edf769a4484995dae44e2d4fca3e34f44d` |
| `scripts/vipe_benchmark/supervisor.py` | `1f8fb109c48ab121a232d3348ecaec1644b651119742c1d6339c6ce87faf2878` |
| `tests/test_vipe_benchmark_s1_helper_fixtures.py` | `faccb5561ad8373d6805b50b0326f0eff8d00e9c9d9760d5829096fca917732b` |
| `tests/test_vipe_benchmark_supervisor.py` | `03e41c199a63c21cf754f0ec3f571a85f79ac417457344d83220f31399b9ce36` |
| `tests/test_vipe_benchmark_s1_recovery.py` | `205a76a29bf43b38d440638f4123a76509ed5003d3f77ae121d62fb50ffe430b` |
| `tests/test_vipe_benchmark_budgets.py` | `6bac13ad5582f4bd28a86ea5c42989d08d8932f236e3797a288807100edcefa6` |

I rehashed all nine paths directly; the hashes match the corrected implementation report. For `s1_validation_capture.py`, both the working tree and `HEAD` yield the `...c4ce...` digest above. `git diff` has only the contract's 8 added lines/1 removed line and 87 added test lines. AST comparison with `HEAD` found exactly two changed functions: `session_proof` and existing `ReceiptContractTests.test_execution_mutations`. The top-level/class function-member counts remain 33/62 in those files. No new method, path, callback, selector, process/thread creator, wrapper, writer, or source-side runtime action appears in the diff. `git diff --check` passed.

## Trust and transcript findings

The attempt008 proof SHA-256 is `0f806e0459248c1125f49c76ddfd8bd4fcccc7b047a0fee6709e2dfed995cfe1`. All four event records match their declared byte counts and SHA-256, and each `output_sha256` matches its result's UTF-8 output. The records are, in ordinal order: 1741 bytes/`7156b656c69195f23aca29873af66fb58d847b63a1be5a3c97499b312a614069`; 4999/`ddb3ada83cd4c051fed520a39bce64d0a5ebb1889d8924cec7ce9f3650a9bf13`; 635/`704f51e57a90c162fb3b045d100e3c863c4216cf255af444da7dd06812ed575d`; 634/`34e0a65f7df98ff039dba0ebd40923706c724deb18fff284115d43c7827a2202`. The saved all-event readback's values and records equal these checked copies. The blocker review reports comparison with Main's original visible results; those original live tool objects are not independently available as a new tool return in this source review, so the readback is supporting historical evidence, not a new live attestation.

The saved ordinal-1 sent string has a final LF and no preceding literal CR/LF. Its 2236-character saved result output equals `sent[:-1] + '\r\n' + readiness_line + '\r\n'` exactly. Ordinal 0 is the sole 466-character bootstrap, ordinals 2 and 3 are empty, all four result handles are 76028, and the complete concatenation equals `bootstrap + echo + readiness_line + '\r\n'`; the proof readiness ordinal is 1. The saved pre-correction validation failed with the expected unexplained-output error. These observations support only the compatibility correction, not reuse of attempt008.

In current `session_proof`, `sent` is captured only after the preexisting parsed frame equals the exact event-0 object and same session handle. For the added branch the body must contain no literal CR/LF; its sole transformed byte is the terminal LF rendered as CRLF. Both `readiness_output` at ordinal 1 and the entire concatenated output must equal exact echo plus readiness with its existing LF or CRLF ending. The prior result hash, live/terminal/truncation, tool/event ordering, handle, bootstrap, authority/record and complete-readiness checks still run before the new comparison or remain unchanged afterward. The final readiness-completion check requires ordinal 1 for an echoed result. Full ordinal-1 and whole-output equality exclude echo at another event, duplicates and unexplained later output. There is no output normalization, substring acceptance or reserialization.

The existing no-echo and split-readiness positives remain in the same method. The added controls accept exact echo with LF or CRLF readiness endings and a semantically equal reserialized *sent* frame whose echo matches its actual bytes. They reject partial/changed/duplicate echo, changed JSON spelling/spacing/order/handle in echo alone, altered echo terminators, prefix/suffix/repeated readiness, later output, embedded sent CR/LF, invalid sent frame/handle, failed/terminal/truncated/wrong-handle results, bad hashes, and missing/duplicate/reordered events or wrong readiness ordinal. Prior assertion-call order is a subsequence of the current method: 126 existing AST `assert*` calls remain in order, with five new call sites. Existing expected-error assertions and behavioral deadline code are unchanged. The six literal direct-script selectors at the unchanged declaration table and all nine suite names remain intact.

The wholly omitted echo nuance is handled correctly: a checked copy containing exact bare readiness is a valid no-echo transcript, so `session_proof` accepts it. For the observed echo-bearing Main result, omission is rejected only by original-result versus checked-copy equality. The new test constructs that mismatch explicitly; it does not claim that a validator can infer a missing echo from an otherwise valid no-echo transcript. Live acceptance must compare the original full Main result object, including non-output fields, with the checked copy.

## Verification and remaining gates

I ran `.local/envs/stg-colmap/bin/python -B -m unittest tests.test_vipe_benchmark_s1_recovery.ReceiptContractTests.test_execution_mutations` once independently: **PASS**, one test in 10.101 seconds (tool wall time 10.308 seconds). Static collection returned exactly **78 source members, 249 methods, 1,028 typed callbacks, nine ordered suites**. The six direct-script selector declarations remain unchanged. No new operational duration ceiling, assertion/deadline shift, or resource-cap change appears in the two-function diff. Plan049/Plan054 still require serial CPU-only `B+max(1,H)≤8`, 150 GiB artifacts, one ≤64 MiB memo entry, the 8,388,608-byte ledger cap, and unchanged W/C, equality-is-late, protocol and scenario deadlines.

Source correction and focused static/synthetic checks: **met**. Fresh Main preflight, independent review of a newly captured original live result and checked copies, admission, diagnostic005 follow-up, B1–B4, and final aggregate: **pending**. This PASS supplies exact-source review only; it grants no runtime clearance. Focused wall time is measured. Process-tree CPU use, token use and other unmeasured overhead are **unknown**.
