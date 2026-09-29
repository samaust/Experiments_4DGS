# Independent exact-source review — implementation 001

**Disposition: NEEDS_REVISION.** Static source review only. This review grants **no runtime, test, fixture, import, compilation, pidfd, diagnostic, aggregate, admission, or launch clearance**. I did not read `prompts` or run project code. The reviewed draft is `implementation-001.md`; authority is Plan049, Corrections014/015 and adopted source-scope addenda001/002/003/006. Addenda004/005 are historical rejected proposals.

## Exact reviewed source bytes

The nine modified tracked source paths are the authorized nine-path set. SHA-256 of the current bytes:

| Path | SHA-256 |
| --- | --- |
| `docs/resolve-blocker/plan031-progress-20260922/launch-049-exec.py` | `be9cdd762b866204eb77aa58e18ca8ed4e48b68df625313fda52610caa90bc1e` |
| `scripts/vipe_benchmark/s1_validation_capture.py` | `478b20b2c8b00931ac7dc9db5ef65a9ca767ea8734ea7df070908c0daf40aa52` |
| `scripts/vipe_benchmark/s1_validation_contract.py` | `96deed6c98161594c39df9d7ebc2150af394afe6716df44742dc556ab1f2b4f5` |
| `scripts/vipe_benchmark/s1_helper_session.py` | `5ba462d64f37061da1d8c63cef305fe4e298add8fe4d7ba2c19400bbb3e7b1c7` |
| `scripts/vipe_benchmark/supervisor.py` | `bbd1375f7c1d3404f2137276f7dcdfcce43f3c5c2604f045bf3b034fa8b66c03` |
| `tests/test_vipe_benchmark_s1_helper_fixtures.py` | `202f20d1b4108680d802394ccd89c2a46da66abaa4108bc421fdd8b59a8a3b7a` |
| `tests/test_vipe_benchmark_supervisor.py` | `c1f74f4fb121afb6a7639043a61fff81775b41e6de23ab3a66bfa039f7917188` |
| `tests/test_vipe_benchmark_s1_recovery.py` | `da27052c9e70c3defe02b9bba3d670a456af1034fb86b5e116346737b5f37018` |
| `tests/test_vipe_benchmark_budgets.py` | `566f8599355b48c62d9d375b8cb9454472305820295065091445a2c56d178a2c` |

Addendum006's SHA-256 is `d165e8412005fcbabdf610ad62840c569d7688e01a6f65e08722d8bff370351f`. The draft's after-hash table matches these bytes. Its before-hash table is a stated pre-edit map; the helper-session before hash intentionally includes pre-existing unstaged changes and is not reconstructible from `HEAD` alone. The three authority lists visibly append addenda001/002/003/006 as records16–19 after Corrections001–015, with no 004/005. The no-timeout validator requires the ordered list and unique entries.

## Blocking findings

1. `scripts/vipe_benchmark/supervisor.py:91–105`: the first ledger-enabled `stop_group` waits until its deadline for `group_processes(pgid)` to empty, but if it remains nonempty, it still calls `process.wait`, retires pinned descendants and the B root, and only then returns the nonempty group. The existing supervisor caller checks the returned list afterward (`supervisor.py:495–499`), and the direct and scenario-worker callers also check it afterward (`tests/test_vipe_benchmark_supervisor.py:1048`, `:1585`). Thus an untracked or surviving group member can leave a durable **retired** root before cleanup failure is recognized. This violates addendum006's group-empty-before-tree-retirement and unknown-descendant-fails-closed requirements. The legacy no-ledger branch's original sequence should remain unchanged.

2. `scripts/vipe_benchmark/s1_helper_session.py:142–145`: `_job_state` accepts a `root-retired` event with `method='matching wait and pidfd terminal'` even when its `terminal` differs from the root's recorded matching-wait terminal. The contract's `validate_job_ledger` delegates transition validity to this state reducer (`s1_validation_contract.py:460–461`) and checks final retired state, so the bypass can certify an inconsistent terminal reference. Addendum001/006 require exact terminal binding. This method-specific escape should validate the prior wait reference and pidfd descendant proof explicitly.

3. `scripts/vipe_benchmark/s1_helper_session.py:147–152,220–230`: `descendant-reserved` permits an attachment to a root in `reserved` or `waited` state, and `reserve_job_root` selects a parent by creator PID alone among every state except `retired`. It does not compare the creator's boot/start identity to that B root before grouping, and it skips a new B/H capacity charge whenever a parent PID matches. A stale or recycled PID can therefore classify an unrelated direct root as a descendant and evade capacity. The contract later checks child creator PID against root PID (`s1_validation_contract.py:492–497`) but likewise does not compare process start identity. Require a live, identity-matched B parent at reservation and validation; otherwise reserve a separately charged root or fail closed.

## Preserved elements and limits of this review

The source diff adds no `def test_` declaration or named scenario, and does not remove original assertion expressions or change the three budget-thread `join(3)`/`join(2)` arguments. The changed recovery positive fixture retains its existing mutation loop and adds a bootstrap/readiness event. The sidecar uses exclusive creation, lock transactions, canonical checksum-chained rows, and readback; the driver binds a Main start frame before creating capture. The explicit budgets threads reserve H before `start()` and retain the same `Thread` objects for join. The L35 code retains the PID marker, performs census and ledger acknowledgment before pidfd and release, and checks terminal against the original safety deadline. The four visible `stop_group` call sites are supervisor final cleanup, registered fixture cleanup, repeated direct close, and scenario-worker cleanup.

These observations are source comparisons, not an independently re-enumerated 78/249/1,028 collection or behavioral proof. Plan049's nine suites, six scripts, selectors and serial aggregate are textually unchanged in this patch, but no collection, execution, runtime deadline, artifact-cap, process-capacity, or cleanup behavior was verified. The draft accurately says it performed no runtime clearance; its positive implementation-intention statements must not be treated as established behavior until the findings are repaired and a fresh exact-source review passes.
