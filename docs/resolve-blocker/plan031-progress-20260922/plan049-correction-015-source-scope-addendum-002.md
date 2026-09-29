# Plan049 Correction015 source-scope addendum 002 — existing budget-test threads

This is an append-only companion to [Correction015 source-scope addendum 001](plan049-correction-015-source-scope-addendum-001.md), which itself supplements Plan049 Correction015. It responds to a static implementation map finding that one member of the unchanged nine-suite selection, `tests/test_vipe_benchmark_budgets.py`, directly starts three `threading.Thread` objects that are outside addendum001's seven-path scope. This is a plan-only proposal; independent PASS and Main adoption with exact hashes are required before editing the newly listed file.

## Exact narrow extension

Add exactly this one source/test path to the scope in addendum001:

| Path | Authorized delta |
| --- | --- |
| `tests/test_vipe_benchmark_budgets.py` | Modify only the existing `BudgetTests.test_two_transfer_threads_cannot_spend_the_same_remaining_bytes` and `BudgetTests.test_cancelled_waiting_lock_does_not_enter_download_scope` methods to reserve each of their three current `threading.Thread` starts as a B logical root before `start()`, bind the exact returned `Thread` handle/native identity, and retire each root only after the same object is joined and observed stopped. Preserve thread topology, Barrier/Event/lock behavior, `join(3)`/`join(2)`, all original assertions and their order/multiplicity, outputs and exception semantics. Add no method, subtest, callback, process, thread, helper/observer, fixture scenario, deadline, selector or suite. |

The two transfer threads are two separate B roots, each reserved before its `start()` and retired only after its exact `join(3)` plus `is_alive()==False` evidence. The cancelled lock-wait thread is a third B root, reserved before `start()` and retired after its same `join(2)` and stopped assertion. A start/identity/join/census ambiguity remains charged and fails the run. Their creator process is the unchanged main test runner; these explicit threads follow Correction014's normative Main-thread-start rule and are not hidden native threads. The existing test runner remains its own B process root. The work stays serial with existing Plan049 tests; no concurrency lane is added.

No other test path or code is added. The ordered 78 source members, 249 methods, 1,028 typed callbacks, six scripts, nine suites, full selectors and exact aggregate remain unchanged. Every original assertion and the actual 2-/3-second join arguments remain byte-for-byte present, ordered, and behaviorally active. The extra ledger calls must fit the original test semantics without modifying them; if they cause assertion/deadline failures, preserve the failure and correct instrumentation without increasing those joins.

## Fixed-authority append order

Correction015 source-scope addendum001 remains authority record 16, immediately after the unchanged Corrections001–015. This addendum002 becomes record 17. The Plan049 driver, contract, positive recovery fixture, Main admission, launch note, and terminal report must carry the same ordered path/byte-count/SHA-256 record list:

1. Corrections001 through015 in their current exact order and hashes.
2. `plan049-correction-015-source-scope-addendum-001.md` at its fixed path and current reviewed byte/hash record.
3. This addendum002 at its fixed path and exact reviewed byte/hash record.

No earlier proof correction pointer or array index shifts; addendum001 is not renumbered. Reject omission, duplicate, reordering, path/hash/byte mismatch in any of the driver, contract, recovery fixture, admission, or report.

## Adoption, validation and retained constraints

This addendum must receive distinct independent plan review together with Correction014 and addendum001. Main adopts only if all three hashes match review. Implementation may then modify only the seven paths of addendum001 plus this added budgets test path. A distinct exact-source reviewer must verify all eight paths, both existing budgets methods, the no-extra-callback rule, source counts, ordered assertions/joins, sidecar binding, all direct thread/process creator classifications, and original deadlines. No fixture/test/diagnostic/aggregate starts until that review, fresh source/artifact/process/capacity/path/high-water preflight, and separate diagnostic clearance.

Keep CPU-only scope, no operational duration ceiling, all original W/C/equality/protocol/setup/scenario behavioral deadlines, 150 GiB artifact cap, 64 MiB memo cap, logical B/H cap and its reserve, all preserved scientific/selection constraints, and no prompt access. Diagnostic005 remains failed; Diagnostic006 remains lost without admission/tests and never reused; Diagnostic007 remains aborted before admission/tests. No implementation, imports, tests, fixture, thread start, runtime, commit, or launch is authorized by this plan alone.
