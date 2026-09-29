# Plan049 correction011 — one authorized expired-entry callback correction

Prepared 2026-09-23 UTC. Main reports the user's **explicit authorization** for the single closed-inventory `deadline=0` callback change: preserve `deadline=0`, expect `TimeoutError` at entry, and assert the inventory/structural suffix is unentered. This append-only addendum resolves only the incompatible expectation documented in the [correction010 implementation report](implement-049-correction010-report-001.md). It does not authorize a production gate change, altered deadline, runtime launch or acceptance claim.

## Exact target and finding

The sole newly authorized test-expectation change is in `tests/test_vipe_benchmark_supervisor.py`, method:

```text
test_vipe_benchmark_supervisor.HelperSessionTests.test_progress_closed_inventory_and_faults
```

Its exact existing typed callback ID is:

```text
test_vipe_benchmark_supervisor.HelperSessionTests.test_progress_closed_inventory_and_faults::[["kind","str","deadline"]]
```

Current inspected branch:

```python
if kind=='deadline':
    result=e.reconcile_rows(output,fixture['request'],deadline=0)
    self.assertFalse(result['scan_complete']);self.assertEqual(result['counts']['produced_lower_bound'],0)
```

The real public `scripts/vipe_benchmark/s1_evidence.py:reconcile_rows` calls `s1_progress.operation(_reconcile_rows, ..., deadline=deadline)`. `operation` invokes `before(active)` before entering `_reconcile_rows`; `before(0)` raises `TimeoutError('progress original work deadline')` when monotonic time is ≥0. Therefore this callback cannot both preserve the required expired-entry gate and receive the result object its two existing assertions require. This is an explicit expectation correction, not a claim that the old expectation was satisfied. No change to the production functions is necessary or authorized by this addendum.

## Authorized replacement and preserved semantics

1. Keep the same callback ID, literal `{'kind': 'deadline'}` declaration, order, fixture/output/request and **exact `deadline=0` argument**. Do not advance the deadline, move the call into an earlier clock window, catch the timeout in production or manufacture an incomplete result.
2. Replace only the two impossible returned-result assertions in this branch—`self.assertFalse(result['scan_complete'])` and `self.assertEqual(result['counts']['produced_lower_bound'],0)`—with an assertion that the **real public `e.reconcile_rows`** raises `TimeoutError` at its original entry gate. Prefer a message-specific assertion for `progress original work deadline` to prevent an unrelated timeout from satisfying the test. The assignment may become the direct call inside the exception assertion; no result is expected.
3. Within this call's scoped observation, instrument the actual `_reconcile_rows` entry and its real suffix seams (`e.input_loader`, `p.candidate_inventory`, `e.produced_row`, `e.qualify_row`) with fail-fast tripwires or spies. Assert each is **unentered** and that the ordered suffix observation list is empty. A tripwire must raise an unmistakable assertion failure, not the expected TimeoutError. Keep the actual `reconcile_rows`, `operation` and `before` execution intact; no guard/operation/clock stub may manufacture the expected timeout. Scope patches only to this callback so the method's valid baseline and other cases still execute their real paths.
4. Fixture setup before the call and the wrapper's existing local memo cleanup are not inventory/structural entry. Do not assert that the entire enclosing test performs no I/O or that local cleanup is forbidden. The claim is precise: the expired call never enters `_reconcile_rows`, opens an inventory through it or creates structural/semantic progress authority. Preserve any existing in-memory/acknowledged state; do not invent or credit a returned fallback snapshot.
5. Retain every assertion and branch outside this one callback, including real successful/conflict controls before it, the nine other case declarations/paths, final unknown-total assertions and source check. No new method, callback, scenario or fixture-size change. Preserve exact 78-source membership, 249 methods/1,028 callbacks and all original deadlines/numeric/resource bounds.

The allowed assertion-preservation delta is exactly the two removed expressions above in this callback, plus the additive timeout/entry/suffix assertions and necessary local instrumentation. Save their old/new normalized ASTs and source context, identifying this as **D49-2 / correction011** alongside the previously authorized exceptions. No further old assertion removal, weakened exception class, broad generic exception success or altered expectation follows from this authorization. If additional changes appear necessary, stop that change and report the concrete conflict.

## Reconciliation with correction010 and validation

[Correction010](plan049-correction-010.md) expressly required a separate decision for an incompatible old assertion. The user has now supplied that decision for this callback alone. Its permission amendment (`require_escalated` only), exact canonical command/justification/prefix, session-bound proof, all other diagnostic002 finding groups, preserved failures and required independent review remain unchanged. Diagnostic001 stays aborted; diagnostic002 stays failed. The next runtime diagnostic remains003 subject to the existing vacancy/high-water rules; this plan does not launch it.

The implementer first checks the bound baseline, performs only this callback correction, and saves a fresh scoped diff, assertion/declaration maps, syntax/static findings, source hashes and handoff. A distinct validator must inspect the exact D49-2 delta and target-specific tripwires together with the remaining correction010 source changes before Main claims readiness. The preserved collected runtime path must later execute this callback with the real public gate, exact0, expected timeout and empty suffix. Static inspection alone does not prove it passed. Every remaining B1–B4/whole-aggregate/scenario/script/ownership requirement stays pending until independently verified.

Main records the user's authorization in the correction dispatch and binds this addendum into new source/admission evidence through the already authorized authority-bookkeeping workflow. Any mechanical driver/contract addendum-list binding uses that existing scope; it cannot alter the proof, transport, permission or production semantics. This addendum grants no broader source change. Main owns all runtime launches, status, integration and task-only commits; no code/test/runtime/session/git mutation occurs during this Plan stage.

Plan049 continues **without operational time or attempt ceilings**. No budget or timeout is introduced here. Original W/C, equality-is-late, all internal behavior assertions, B+max(1,H)≤8, ≤64MiB memo, ≤150GiB artifacts, one active subagent and all CPU-only/prohibited-work/permission-stop rules remain exact. No GPU/device/model/production/real-ledger/setup/download/scientific work or prompts.

## Inspected baseline hashes

| Input | SHA-256 |
| --- | --- |
| `tests/test_vipe_benchmark_supervisor.py` | `faffcc1a9070ad31aaadf4b2367ba97c7cea5ca56cb8f8ba57394932ddd2b256` |
| Target method normalized `ast.dump(..., include_attributes=False)` | `b5ad6f77a88a7c5d13d5dd7614d0b637c4eca16a9c7d575fd3a2e6631bc7cc58` |
| `scripts/vipe_benchmark/s1_evidence.py` | `14ea47c7cc56418ae7a8e0e7aa442fb7664774d8a8f15b27c558ddcf69c679db` |
| `scripts/vipe_benchmark/s1_progress.py` | `d53a203c64c1b78a19a720ba72aaa28efbe427333c704f81166a4151e485b89d` |
| `plan049-correction-010.md` | `ac9a4d3f392ad60dfa308622d25f0fe8c7dc07d0dab7139b8275be96050f9d6a` |
| `implement-049-correction010-report-001.md` | `3b2522d507422aa902ff8020cbae375dcdfb620fbc87cd3a894ffcb9dbb87191` |

Planning first observed UTC: `2026-09-23 17:34:05 UTC`; earlier commentary/start overhead unknown. This record is static planning and source inspection only. No callback has been executed by this stage and no criterion is newly accepted.
