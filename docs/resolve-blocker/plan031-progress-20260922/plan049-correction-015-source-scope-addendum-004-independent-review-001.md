# Plan049 Correction015 source-scope addendum004 — independent plan review 001

**Verdict: NEEDS_REVISION. NO LAUNCH CLEARANCE.** This is a static review of the exact addendum004 bytes below. The proposed ninth path is justified by the two existing descendant-cleanup cases and is narrow in principle, but the descendant acknowledgment and root-retirement order are not yet implementable as written against the current ledger. Main should revise this plan before adopting its hash. This review is neither source approval nor permission to run a fixture, diagnostic, or aggregate.

## Exact inputs

All paths are repository-relative. SHA-256 values were computed from the bytes read for this review; source files have concurrent working changes and these hashes describe this snapshot only.

| Input | SHA-256 |
| --- | --- |
| `plans/plan_049.md` | `89d1f634ad2407b02558ff9c030d4a4f12f8f4ab010c93e2cf532876564afe7e` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-014.md` | `f874eb395b61a5c05f83418ab26c938d65884fed71e18c978f748ec47a13d557` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015.md` | `a3242ed06131aa9ca00bc05180805c8d5bf5ea8d965919b92054154f10a00bab` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-source-scope-addendum-001.md` | `f08fad270dcea9596d1a4c45a41d13f2f5675f7d51fe464699a1ec4046f0b45e` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-source-scope-addendum-002.md` | `9a175afcdce5b31c6fa17543f1fe7be6183095cb2f5c6beec0621ce7ad33511e` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-source-scope-addendum-003.md` | `92e69b78659baa45da6e74c439a0bc18d14450c3d88592aa46ba8d8495d3dd8a` |
| **`docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-source-scope-addendum-004.md`** | **`e56795a0b241c3d0a0e11622d8daa828e151227199ce536d111cf4a9e7663b26`** |
| `docs/resolve-blocker/plan031-session-proof-wrapper-20260923/correction-014.md` | `3eba8a015cdd31e8c386e44cb8bb44f9e3bd6840f86898da38e475d687fcc36f` |
| `docs/resolve-blocker/plan031-session-proof-wrapper-20260923/correction-014-source-scope-review-002.md` | `c59b2202611b390b1d96d37fed6db8b511df95ae7341473905ff659be0222c31` |
| `scripts/vipe_benchmark/supervisor.py` | `5532610e247d2d8f858a646706fa187cf7c249e8cb6dce1b4db78458e4405ec3` |
| `scripts/vipe_benchmark/s1_helper_session.py` | `ef6aafffd9ea6cc695079e37d625b107649d469e8dd03d5b70d2d317e5166edd` |
| `tests/test_vipe_benchmark_supervisor.py` | `b8387537580a2200b8f3e48d28d1270238f0354794158a04a238c4599bd35f08` |
| `tests/test_vipe_benchmark_s1_helper_fixtures.py` | `15b684d5377d15ed4cceb6cbd44ca0a004184e847c14d9a13ab40ed8d811ff88` |

## Findings

1. **Durable descendant acknowledgment is missing from the proposed sequence.** The current ledger accepts `descendant-retired` with method `identity-bound pidfd terminal` only if that exact descendant has an earlier `descendant-ack` and the retirement identity equals its bound identity (`s1_helper_session.py`, `_job_state`). `retire_job_descendant_pidfd` enforces the same prerequisite. Addendum004 specifies census, pidfd opening and immediate identity reconciliation, then terminal retirement, but never calls for durable acknowledgment of these two non-L35 descendants. The L35 acknowledgment is specific to its own PID-marker/release race and cannot stand in for them. Require an exact root/descendant-token selection, live ancestry/census identity match, durable ledger acknowledgment/readback before pinning or retirement, and the same pinned identity at terminal. A changed or ambiguous identity must remain charged. This is a plan gap, not a request to loosen the validator.

2. **The stop/retirement order needs an explicit single owner.** Current `stop_group` sends TERM/KILL, waits for the worker, calls `retire_owned(process.pid)`, and only then returns `group_processes(pgid)`. `retire_owned` calls `wait_job_root`, which emits the worker's `root-wait` and retires the root only if every descendant is already retired. Addendum004 says to require group-empty/worker-wait/pidfd readiness “after it returns” and then retire descendants and the root. If “it” means `stop_group`, that is too late for the function's own root transition; if it means the signal/wait sequence, the plan should say so. Specify within the existing `stop_group` boundary: select and pin before TERM; preserve TERM/KILL and original deadline; observe group-empty and the exact worker wait; retire acknowledged descendants from their pinned pidfds; then make one root-tree retirement transition, without a second `retire_owned`/wait or duplicate root-retired event. Define the unresolved path for wait, pidfd, readback, group-empty, and deadline failures. Keep the original return value and primary/secondary cleanup behavior.

3. **The ninth path is proportionate, with one scope clarification needed.** `supervisor.py` contains the shared `stop_group` boundary used by the two named existing tests. Reopening only that source path, together with the already scoped helper-session ledger, can address the gap without adding a module, method, callback, worker, or deadline. The proposal also requests new bounded checks in those two `tests/test_vipe_benchmark_supervisor.py` methods. State explicitly that this is a narrow expansion inside that already scoped test file; addendum001 had described L35 and relevant ownership assertions, so a reader should not have to infer that these two methods are included. Preserve every original assertion in order and multiplicity. Review the effect of the shared `stop_group` path on its other callers during source review, including runs without a current ledger.

The proposed live census, exact boot/PID/start/PGID and creator/ancestry checks, pidfd-before-signal rule, fail-closed handling of missing/out-of-group descendants, and refusal to claim kernel-wide containment are sound constraints. `group_processes` excludes zombies, so a group-empty result alone cannot establish each tracked descendant's terminal state; the additional identity-bound pidfd readiness is necessary. The plan correctly retains the existing cleanup deadline, scenario assertions, `B+max(1,H)≤8` logical-root semantics and H reserve, 78/249/1,028 counts, CPU-only scope, artifact and memo caps, serial selection, and historical diagnostic dispositions. No plan wording should turn a failed original timing assertion into a pass or treat an unregistered descendant as retired.

The proposed fixed-authority order is coherent: Corrections001–015 unchanged, addenda001–003 as records16–18, then addendum004 as record19. Driver, contract, positive recovery fixture, Main admission, launch note, source manifest where applicable, and terminal report must carry the exact path/byte-count/SHA-256 record; earlier proof correction pointer and indices stay fixed. The revised addendum will have a new hash and needs independent plan review before Main adopts it. After adoption, distinct exact-source review and fresh source/artifact/process/capacity/path/high-water checks remain prerequisites to separate runtime clearance.

No source was edited; no project code was imported; no test, fixture, pidfd operation, probe, diagnostic, aggregate, admission or runtime was run. No `prompts` content was read. This review artifact is the only write from this assignment.
