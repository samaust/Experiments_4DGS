# Independent exact-source review — implementation 001, revision 002

**Disposition: NEEDS_REVISION. NO RUNTIME/TEST CLEARANCE.** This is a static review of the current nine-path draft identified by `implementation-001.md`. I did not read `prompts`, import or compile project code, run tests or fixtures, inspect processes, open pidfds, run diagnostics, or grant admission or launch clearance.

## Exact reviewed bytes

I independently calculated SHA-256 for all nine current source files. They match the draft's revised after-hashes:

| Path | SHA-256 |
| --- | --- |
| `docs/resolve-blocker/plan031-progress-20260922/launch-049-exec.py` | `be9cdd762b866204eb77aa58e18ca8ed4e48b68df625313fda52610caa90bc1e` |
| `scripts/vipe_benchmark/s1_validation_capture.py` | `478b20b2c8b00931ac7dc9db5ef65a9ca767ea8734ea7df070908c0daf40aa52` |
| `scripts/vipe_benchmark/s1_validation_contract.py` | `72f8a853bb1f6893045e26e3f77a76c0cfb3c351d749b79ac4332aeb0f2b5a0e` |
| `scripts/vipe_benchmark/s1_helper_session.py` | `83ad62cfca98fc5ffd6948c5f608cbb92cd380d1ee6885f5a44bbfca0931ba1a` |
| `scripts/vipe_benchmark/supervisor.py` | `e5976ce64c0f0fea6b09124205cb9cb663e98181805f5cfc1df8154341629573` |
| `tests/test_vipe_benchmark_s1_helper_fixtures.py` | `202f20d1b4108680d802394ccd89c2a46da66abaa4108bc421fdd8b59a8a3b7a` |
| `tests/test_vipe_benchmark_supervisor.py` | `c1f74f4fb121afb6a7639043a61fff81775b41e6de23ab3a66bfa039f7917188` |
| `tests/test_vipe_benchmark_s1_recovery.py` | `da27052c9e70c3defe02b9bba3d670a456af1034fb86b5e116346737b5f37018` |
| `tests/test_vipe_benchmark_budgets.py` | `566f8599355b48c62d9d375b8cb9454472305820295065091445a2c56d178a2c` |

The draft's before-hashes remain its pre-edit map; the pre-existing helper-session changes make its before byte state distinct from `HEAD`.

## Earlier findings

The previous three findings are repaired at their stated sites. `stop_group` now returns on a nonempty post-wait group census before descendant or root retirement (`supervisor.py:107–118`). `_job_state` requires every `root-retired.terminal` to equal the prior `root-wait.terminal` (`s1_helper_session.py:141–146`). Descendant reservation selects only a live B parent with matching boot ID, PID, start ticks, and PGID; the reducer and final contract repeat that binding (`s1_helper_session.py:147–152,223–235`; `s1_validation_contract.py:492–500`). These checks address the three examples in review 001.

## Blocking finding

The revised `stop_group` still cannot safely retry a partially prepared or partially retired tree. It inserts `stop_group._pinned[job_token]=[]` **before** checking or pinning descendants (`supervisor.py:65–90`). If a descendant census, `pidfd_open`, or post-open identity recheck then fails, the charged root remains live but the next call enters the retry branch. That branch requires the pinned token set to equal the complete descendant set (`:70–77`); an empty or partial set fails permanently. If failure happens after the first of multiple descendants was retired, the loop has closed that descriptor (`:115–117`) but left it in `_pinned`; retry rejects the retired child and can also `fstat` a closed descriptor. L35 can independently retire a child with its retained pidfd between calls (`s1_helper_session.py:291–310`), producing the same retry rejection. Thus ordinary uncertain cleanup cannot resume on the exact same live-root handle, despite addendum006's charged-tree and same-object retry requirements. Keep the tree charged on uncertainty, but make retry state account for each pin/retirement stage and retain usable descriptors until cleanup is complete; require a fresh independent source review of that correction.

## Remaining scope observations and limits

The driver, contract, and positive recovery fixture visibly use the same ordered Corrections001–015 plus addenda001/002/003/006 authority lists. The launch note and admission bind the sidecar, and the no-timeout contract requires the ledger and exact Main handle. The ledger uses exclusive sidecar creation, checksummed canonical lines, locked appends, and readback. Root reservation precedes `Popen`, and the reducer charges unresolved roots under `B+max(1,H)≤8` with the outer session as H=1. The three existing budget threads are labeled H, reserve before `start()`, and retain their original objects and `join(3)`/`join(2)` calls. The L35 change retains the PID marker and adds live census, acknowledgment, pidfd-before-release, and terminal polling against `fixture_safety_end`. The four visible `stop_group` callers are supervisor cleanup, fixture callback, direct repeated close, and scenario-worker cleanup. The legacy no-ledger branch retains TERM, grace, KILL, group census, matching wait, and `retire_owned` sequencing.

Static comparison found no changed `def test_` declarations or selector names in the nine-path diff. The original budget join arguments, L35 safety deadline reference, and supervisor cleanup deadline expressions remain. The source still expresses 150 GiB artifact and 64 MiB memo caps. I did not independently collect the 78 source members, 249 methods, 1,028 callbacks, run the six scripts or nine suites, or verify timing, artifact capacity, process ownership, or runtime behavior. Diagnostic005 remains failed, 006 lost, and 007 aborted before admission; none supplies evidence for this draft. The current blocker prevents a PASS and grants **no runtime, test, fixture, import, compilation, pidfd, diagnostic, aggregate, admission, or launch clearance**.
