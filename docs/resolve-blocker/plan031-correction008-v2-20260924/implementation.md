# Correction008 v2 implementation report

Plan054 / Correction008 trust amendment 001 is adopted; this report records the bounded implementation candidate before independent validation. It does not establish live C1–C3, B1–B4, diagnostic clearance, or any measured ledger size.

## Changed paths and hashes

Only three of the nine authorized paths changed:

| Path | SHA-256 |
| --- | --- |
| `docs/resolve-blocker/plan031-progress-20260922/launch-049-exec.py` | `45f817336d5eb8c41404336d0c497aced3eca1f8087fd07e5814fb6e589aca9f` |
| `scripts/vipe_benchmark/s1_validation_contract.py` | `6ac5c3335a73aebccf4ad70be582fd4d827db677d4c48d24101dca5199778323` |
| `tests/test_vipe_benchmark_s1_recovery.py` | `8e4739d123679df7262426a83a6d331f78ab40593464f4d3dbccafa21a7b7f70` |

The six unchanged authorized paths hash to: capture `62359a258543731b96690d3abc7bd3ddede4809ae76ae4ec2ff83e5c4ce95fd7`; helper session `ff6ad2373e9ed4501f7bfb55afd75891f3e17899ce47c10ff7d6bc6665788587`; supervisor `1f8fb109c48ab121a232d3348ecaec1644b651119742c1d6339c6ce87faf2878`; helper fixtures `faccb5561ad8373d6805b50b0326f0eff8d00e9c9d9760d5829096fca917732b`; supervisor tests `03e41c199a63c21cf754f0ec3f571a85f79ac417457344d83220f31399b9ce36`; budgets tests `6bac13ad5582f4bd28a86ea5c42989d08d8932f236e3797a288807100edcefa6`.

## Behavior implemented

The validator now requires `plan049-session-proof/v2` and `plan049-session-tool-event/v2`, exact authority file records for Plan054 and amendment001, UTC-only event stamps with causal ordering, strict original tool-result liveness/error/truncation fields, exact session-handle correlation, and unchanged proof/admission/note binding. The driver validates the exact v2 start-event keys/role/index/ordinal, UTC objects, start result and output hash, and binds both adopted authority records into admission and launch-note verification. The existing recovery mutation method now builds a v2 proof and covers valid maximum-width handles plus negative cases for v1/mixed schemas, UTC order/rollback/timezone, errors/truncation/hash, stale or missing authority, and handle mismatch/width. The implementation uses Python's integer-string conversion guard at 20,000 digits so the authorized ≤16,384-digit handle can be parsed; the exact v2 validator rejects wider handles. The process-wide effect of this interpreter guard is specifically assigned for independent review.

## Focused validation

- `.local/envs/stg-colmap/bin/python -B -m unittest tests.test_vipe_benchmark_s1_recovery.ReceiptContractTests.test_execution_mutations` — PASS, one test, latest reported elapsed time 10.239 s. This is synthetic contract validation only.
- `git diff --check` — PASS.
- AST parsing and `collection()` — PASS, unchanged at 78 source members, 249 methods, 1,028 callbacks, and nine suites.
- Main independently reran `git diff --check` and SHA-256 verification over all nine authorized paths; these matched the hashes above.

## Gates still open

Independent exact-source review must verify the full v2 schema and sequencing, exact visible-return versus checked-copy contract, authority hashes, handle bound, logical `B+max(1,H)≤8` accounting, preserved assertions/deadlines/error precedence/counts and the process-wide integer conversion setting. Fresh Main source/authority/artifact/ownership/capacity/output/high-water preflight and separate live proof clearance remain. No process/admission/diagnostic/aggregate was launched, and ledger bytes/content have not been measured. Model/CPU use beyond the stated focused-test elapsed time was not measured.
