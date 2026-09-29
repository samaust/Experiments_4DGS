# Plan049 Correction015 source-scope addendum005 — independent plan review 001

**Verdict: NEEDS_REVISION. NO LAUNCH CLEARANCE.** This is a static review of the exact addendum005 bytes below. The revision resolves addendum004 review's missing durable acknowledgment and misplaced retirement transition, but its required live-root selection does not cover a second `stop_group` call on the same already-retired handle in one of its two named integration tests. Main must revise and independently review the plan before adopting its hash. This review is neither source approval nor authorization for a fixture, test, diagnostic, or aggregate.

## Exact inputs

All paths are repository-relative. SHA-256 values bind the bytes read for this review; source hashes describe this snapshot only.

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
| **`docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-source-scope-addendum-005.md`** | **`ae085276ea0b8a96b905ff7e53554464a578ae1dae69fa4f665509309c316cbb`** (6,956 bytes) |
| `docs/resolve-blocker/plan031-session-proof-wrapper-20260923/correction-014.md` | `3eba8a015cdd31e8c386e44cb8bb44f9e3bd6840f86898da38e475d687fcc36f` |
| `scripts/vipe_benchmark/supervisor.py` | `5532610e247d2d8f858a646706fa187cf7c249e8cb6dce1b4db78458e4405ec3` |
| `scripts/vipe_benchmark/s1_helper_session.py` | `ef6aafffd9ea6cc695079e37d625b107649d469e8dd03d5b70d2d317e5166edd` |
| `scripts/vipe_benchmark/s1_validation_capture.py` | `478b20b2c8b00931ac7dc9db5ef65a9ca767ea8734ea7df070908c0daf40aa52` |
| `tests/test_vipe_benchmark_supervisor.py` | `b8387537580a2200b8f3e48d28d1270238f0354794158a04a238c4599bd35f08` |
| `tests/test_vipe_benchmark_s1_helper_fixtures.py` | `15b684d5377d15ed4cceb6cbd44ca0a004184e847c14d9a13ab40ed8d811ff88` |

## Finding requiring revision

`HelperIntegrationTests.worker()` registers an unconditional cleanup that calls `stop_group` on its retained process handle (`tests/test_vipe_benchmark_supervisor.py:888`). The named `test_real_close_repeated_and_descendant_cleanup` also calls `stop_group(process, limit)` directly (`:1037`). Thus its normal path invokes `stop_group` twice on the **same handle**. The first call must retire the child and worker tree. On the second call, the root is already retired and `retire_owned` has removed its `JOB_PROCESSES` entry. Addendum005 step 1 nevertheless requires an exact **live** B-root token before any signal, and step 3 describes one root retirement for the call. As written, the required sequence cannot handle that existing caller while preserving its assertions and cleanup. The statement that every existing caller will be reviewed later does not settle this known case.

Specify a bounded idempotent path for an exact retained handle whose same ledger root and descendants are already durably retired. It should verify that terminal state, preserve the current final group census and deadline/cleanup-error behavior, and emit no second descendant or root retirement. Missing, mismatched, ambiguous, or still-live records must remain charged and fail closed. Keep the no-ledger legacy behavior unchanged. This is an existing repeated-call path, not a request for a new test method or a relaxed first-call check.

## Other reviewed constraints

The creator-time `descendant-ack` with fsync/readback now supplies the prerequisite enforced by `_job_state` and `retire_job_descendant_pidfd`; the separate L35 live-census acknowledgment remains required. The ordered `stop_group` transition now selects and pins before TERM, preserves TERM/grace/KILL/wait and the original deadline, demands group-empty and pinned pidfd terminal evidence, retires descendants before exactly one `retire_owned`, and retains uncertainty on failure. The capture runner is labelled `capture runner`, which `reserve_job_root` excludes as a descendant parent; the workers in the named tests therefore can be B roots with their nested children charged beneath them. The proposed ninth path and bounded assertions within the already-scoped supervisor test file are proportionate. The source reviewer still must inspect the shared `stop_group` callers, including no-ledger callers and the repeated-call path above.

The proposed authority order is coherent: unchanged Corrections001–015, addenda001–003 as records16–18, and this revised addendum as prospective record19. Rejected addendum004 is historical evidence, not authority. Driver, contract, positive recovery fixture, Main admission, launch note, source manifest, and final report must bind the exact adopted path/byte count/SHA-256 without shifting earlier records or the proof correction pointer. CPU-only scope, serial diagnostic and aggregate order, 78/249/1,028 counts, original assertions and behavioral deadlines, `B+max(1,H)≤8`, 150 GiB artifact cap, 64 MiB memo cap, and Diagnostic005/006/007 dispositions remain intact. A revised addendum needs a new exact hash and independent plan review, then explicit user authorization for the ninth path before implementation; distinct exact-source review and fresh preflight remain separate gates.

No source was edited or imported; no test, fixture, pidfd operation, probe, diagnostic, aggregate, admission, or runtime was run. No `prompts` content was read. This review artifact is the only write from this assignment. **No launch clearance.**
