# Plan049 Correction015 source-scope addendum006 — independent plan review 001

**Verdict: PASS for this exact plan proposal only. NO LAUNCH CLEARANCE.** Addendum006 closes the specific same-handle repeated `stop_group` gap identified in the independent addendum005 review. This review approves neither a source patch nor a fixture, test, pidfd operation, diagnostic, aggregate, admission, or commit. The ninth source path still requires the user's explicit authorization and Main's adoption of the reviewed hash before implementation.

## Exact inputs

Paths are repository-relative. These SHA-256 values bind the exact bytes read in this static review; the source hashes are context snapshots, not source approval.

| Input | SHA-256 |
| --- | --- |
| `plans/plan_049.md` | `89d1f634ad2407b02558ff9c030d4a4f12f8f4ab010c93e2cf532876564afe7e` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-014.md` | `f874eb395b61a5c05f83418ab26c938d65884fed71e18c978f748ec47a13d557` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015.md` | `a3242ed06131aa9ca00bc05180805c8d5bf5ea8d965919b92054154f10a00bab` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-source-scope-addendum-001.md` | `f08fad270dcea9596d1a4c45a41d13f2f5675f7d51fe464699a1ec4046f0b45e` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-source-scope-addendum-002.md` | `9a175afcdce5b31c6fa17543f1fe7be6183095cb2f5c6beec0621ce7ad33511e` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-source-scope-addendum-003.md` | `92e69b78659baa45da6e74c439a0bc18d14450c3d88592aa46ba8d8495d3dd8a` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-source-scope-addendum-004.md` | `e56795a0b241c3d0a0e11622d8daa828e151227199ce536d111cf4a9e7663b26` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-source-scope-addendum-004-independent-review-001.md` | `f926fc486963098e99159caec7f0a6e20de76bb420fa3f09c664e05d6d38867a` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-source-scope-addendum-005.md` | `ae085276ea0b8a96b905ff7e53554464a578ae1dae69fa4f665509309c316cbb` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-source-scope-addendum-005-independent-review-001.md` | `5c4486f78d1b8245df6740dc7eb35f38252303385a0218e1dc656f74bb8ccc94` |
| **`docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-source-scope-addendum-006.md`** | **`d165e8412005fcbabdf610ad62840c569d7688e01a6f65e08722d8bff370351f`** (5,711 bytes) |
| `scripts/vipe_benchmark/supervisor.py` | `5532610e247d2d8f858a646706fa187cf7c249e8cb6dce1b4db78458e4405ec3` |
| `scripts/vipe_benchmark/s1_helper_session.py` | `ef6aafffd9ea6cc695079e37d625b107649d469e8dd03d5b70d2d317e5166edd` |
| `tests/test_vipe_benchmark_supervisor.py` | `b8387537580a2200b8f3e48d28d1270238f0354794158a04a238c4599bd35f08` |
| `tests/test_vipe_benchmark_s1_helper_fixtures.py` | `15b684d5377d15ed4cceb6cbd44ca0a004184e847c14d9a13ab40ed8d811ff88` |

## Review result

The named `HelperIntegrationTests.test_real_close_repeated_and_descendant_cleanup` calls `stop_group(process, limit)` directly, then its registered cleanup calls `stop_group` on the same retained `Popen` object. Addendum005 required a live root on both calls, contradicting the first call's successful retirement. Addendum006 supplies the missing second path: resolve that exact handle object and stable process identity to one already-retired root, verify every descendant is retired, preserve the existing group cleanup, census return, `process.wait`, deadline and cleanup-error behavior, and emit no second descendant retirement or `retire_owned` call. A different handle, changed identity, ambiguous record, or unresolved tree fails closed. The current helper-session ledger retains exact handles in `JOB_HANDLES` and records root handle identity; the plan describes a bounded use of that authority rather than accepting PID equality alone. The fixture cleanup's subsequent direct `retire_owned` call is a separate existing caller and must remain ledger-idempotent under exact-source review.

For the first call, the proposed creator-time durable acknowledgment precedes helper return and supplies the `descendant-ack` prerequisite enforced by `_job_state` and pidfd retirement. L35 still needs its separate marker, live census, acknowledgment and pidfd-before-release witness. The stop order remains exact root/descendant selection, creator acknowledgment, fresh boot/PID/start-ticks/PGID census, pidfd with immediate identity recheck, original TERM/grace/KILL/group-empty/worker-wait sequence and deadline, pinned terminal readiness, durable descendant retirements, then exactly one existing `retire_owned` root transition. Uncertainty keeps the tree charged and cleanup fails closed. Source review must establish this order and ensure later same-handle cleanup cannot signal an unrelated reused process group.

The source scope is one added path, `scripts/vipe_benchmark/supervisor.py`, confined to `stop_group` and its existing ledger integration, plus bounded closure assertions in the two named existing supervisor tests. No new source member, declaration, method, callback, process, thread, observer, scenario or selector is authorized. The exact-source reviewer must enumerate every `stop_group` caller in both ledger and legacy modes, including the direct call, registered fixture cleanup, scenario call and supervisor cleanup; preserve each original assertion, return value, cleanup signal and behavioral deadline. With `S1_JOB_LEDGER` absent, legacy behavior remains unchanged.

The proposed authority chain leaves Corrections001–015 fixed, keeps addenda001–003 at records16–18, and appends only addendum006 as prospective record19. Rejected addenda004–005 stay historical. Driver, contract, positive recovery fixture, Main admission, launch note, source manifest and final report must agree on its exact path/byte count/SHA-256 without shifting any prior pointer or record. Plan049, Correction014 and Correction015 limits remain: CPU-only work, serial diagnostics and aggregate, exact 78/249/1,028 counts, original internal deadlines and assertions, `B+max(1,H)≤8`, 150 GiB artifacts and 64 MiB memo. Diagnostic005 remains failed, Diagnostic006 lost and never reused, and Diagnostic007 aborted before admission/tests. No kernel-wide containment claim follows from this logical ledger.

Before any implementation of the ninth path, Main needs the user's explicit scope authorization and must adopt this reviewed exact hash. A distinct independent exact-source review and fresh source, artifact, ownership/capacity, output-path and attempt-index/high-water checks remain necessary before separately cleared runtime work. Static documentation and source reads only were performed; no source was edited or imported, no test or runtime was run, and no `prompts` content was read. **NO LAUNCH CLEARANCE.**
