# Implementation001 — bounded ordinal-1 PTY echo comparison

The adopted exact bytes are Plan055 SHA-256 `18506f655e7a2c95492fa88a038c869a4c993fa06d3ba628725158eaea77242f`, Correction001 `89271f7ee1156326a4edce7079ad812ecb93f7674b9522d1233f6e7927d20136`, and independent plan-review PASS `9f454e6468f53770ed3702eaa889b5f204e93f941aeecb5518034daa8ad26949`. Plan054 remains `91d0ac7191d944b8cf2175b74c74aff3d70d4dba4a530431f223cb8aab2df62d`.

`session_proof` now accepts one additional exact transcript: bootstrap, the validated ordinal-1 sent frame body with only its final LF rendered as CRLF, and the readiness line with its preexisting LF or CRLF terminator. The new branch requires no earlier literal CR/LF in the sent frame, the entire ordinal-1 output to equal echo plus readiness, and the whole concatenated output to equal the expected transcript. The existing readiness-completion correlation then requires ordinal 1. The original no-echo and split-readiness forms, event/result/file hashes, exact handle and event order, live/truncation checks, authority bindings, and original-result versus checked-copy trust boundary remain in force. No historical evidence was edited.

Only `scripts/vipe_benchmark/s1_validation_contract.py` and the existing `ReceiptContractTests.test_execution_mutations` in `tests/test_vipe_benchmark_s1_recovery.py` changed. The latter adds synthetic exact-echo LF/CRLF positives, a semantically equal reserialized sent-frame positive, whole-output echo and event negatives, and an internally rehashed checked-copy omission that passes the valid no-echo contract but fails the original-result equality boundary. The prior no-echo and split-readiness positives and prior failure assertions remain.

Fresh SHA-256 for the nine reviewed paths:

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

Before implementation, the contract hash was `69058bc74765caa17aa877fc1cbeb7c2b9e892f4304daf273ff96a3c5b78fd78`; the other seven reviewed paths were not edited by this change. The two-path `git diff` contains no unrelated source changes, and `git diff --check` passed. AST comparison with `HEAD` found only `session_proof` and `test_execution_mutations` changed, with no new function or method. All 126 prior AST assertion calls in the test method remain in order, with five new call sites for echo controls. Static collection via `s1_validation_contract.collection()` and `source_paths()` returned exactly 78 source members, 249 methods, 1,028 typed callbacks, nine ordered suites, and six direct-script selector declarations.

Focused command: `.local/envs/stg-colmap/bin/python -B -m unittest tests.test_vipe_benchmark_s1_recovery.ReceiptContractTests.test_execution_mutations` — PASS, one test in 10.154 seconds. A read-only check of the saved attempt008 proof and four event copies confirmed every file byte count/SHA-256 and per-event output hash, one final sent LF with no earlier CR/LF, exact ordinal-1 echo/readiness output, exact whole transcript, and empty later polls. This checks saved copies only; the independent blocker review separately records their original Main/readback equality. The first two focused runs failed due to synthetic fixture mistakes and were corrected before the passing run. No Plan049 session, admission, diagnostic, aggregate, or live-proof validation was launched.

Scoped implementation and focused control criteria: **met**. Independent exact-source review: **pending**. Fresh Main preflight, independently reviewed new live proof, later diagnostic and aggregate gates: **pending**. Attempt008 remains terminal, unadmitted, consumed and unchanged. Focused test wall time was measured; process-tree CPU, token use and unmeasured overhead are unknown. No resource-cap relaxation or new operational duration ceiling was introduced.
