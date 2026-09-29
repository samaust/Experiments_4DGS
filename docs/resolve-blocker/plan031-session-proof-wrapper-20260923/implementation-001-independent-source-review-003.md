# Independent exact-source review — implementation 001, revision 003

**Disposition: NEEDS_REVISION. NO TEST/RUNTIME CLEARANCE.** I reviewed the revised nine-path draft and current source bytes only. I did not read `prompts`, import or compile project code, run tests or fixtures, inspect processes, open pidfds, or run a diagnostic or aggregate. This review grants no admission or launch clearance.

The reviewed `implementation-001.md` has SHA-256 `fb3321320b617bfcee51c9edc7822e647d8128fb2b77158cc5f37ebcf6df4e9d`. Independently calculated current SHA-256 values match all nine after-hashes in its table:

| Authorized source path | SHA-256 |
| --- | --- |
| `docs/resolve-blocker/plan031-progress-20260922/launch-049-exec.py` | `be9cdd762b866204eb77aa58e18ca8ed4e48b68df625313fda52610caa90bc1e` |
| `scripts/vipe_benchmark/s1_validation_capture.py` | `478b20b2c8b00931ac7dc9db5ef65a9ca767ea8734ea7df070908c0daf40aa52` |
| `scripts/vipe_benchmark/s1_validation_contract.py` | `72f8a853bb1f6893045e26e3f77a76c0cfb3c351d749b79ac4332aeb0f2b5a0e` |
| `scripts/vipe_benchmark/s1_helper_session.py` | `83ad62cfca98fc5ffd6948c5f608cbb92cd380d1ee6885f5a44bbfca0931ba1a` |
| `scripts/vipe_benchmark/supervisor.py` | `46f02f163cf56160c081ba4e03c3a74eae4e051fd312e6a8052fbd1e241e41b5` |
| `tests/test_vipe_benchmark_s1_helper_fixtures.py` | `202f20d1b4108680d802394ccd89c2a46da66abaa4108bc421fdd8b59a8a3b7a` |
| `tests/test_vipe_benchmark_supervisor.py` | `c1f74f4fb121afb6a7639043a61fff81775b41e6de23ab3a66bfa039f7917188` |
| `tests/test_vipe_benchmark_s1_recovery.py` | `da27052c9e70c3defe02b9bba3d670a456af1034fb86b5e116346737b5f37018` |
| `tests/test_vipe_benchmark_budgets.py` | `566f8599355b48c62d9d375b8cb9454472305820295065091445a2c56d178a2c` |

## Blocking retry finding

`stop_group` accepts an exact retained B handle only while its ledger root is `live` or fully `retired` (`supervisor.py:41–58`). After an empty post-wait group census and descendant retirement, it calls `retire_owned` (`:125–132`). That function calls `wait_job_root`, which durably appends `root-wait` and then separately appends `root-retired` (`s1_helper_session.py:251–265,728–747`). If the latter append, fsync, or readback fails after the former succeeds, the root is `waited` and still charged. The exact same `Popen` object cannot resume cleanup: the next `stop_group` call raises `stop_group unresolved root state` at `:58` before it can finish root retirement. L35 has the same partial boundary when it observes a waited root and separately appends its final `root-retired` (`s1_helper_session.py:303–310`). The existing helper-session reducer permits the waited state but exposes no retry transition through `stop_group` for it. This is a concrete partial-failure path within the addendum006 cleanup semantics; it needs a same-handle, identity-checked, group-empty recovery path that does not re-signal or repeat descendant retirement. Preserve the existing deadline and keep uncertainty charged until durable retirement.

## Other retry paths and preservation

The revision repairs review 002's two examples in source. Initial descendant pidfds are gathered locally and closed on any preparation failure before the retry map is published (`supervisor.py:65–98`), so a later call can prepare them again. Once published, pins remain open through partial descendant retirement; a retry validates their descriptors and identity, skips ledger-retired descendants, and pins newly observed live descendants. L35's separate retained pidfd permits its terminal check even if `stop_group` already retired that descendant (`s1_helper_session.py:291–306`). A completed signal phase is not repeated on retry; an interrupted signal phase fails closed. The already-retired same-handle path checks descendant retirement and group emptiness, waits the same handle, and adds no signal or ledger transition (`supervisor.py:48–57`). The first-call root identity check precedes signaling. These are static control-flow findings, not proof against every timing race.

The three findings in review 001 remain corrected: a nonempty post-wait group returns before any descendant/root retirement (`supervisor.py:117–121`); every `root-retired.terminal` must equal its prior root-wait terminal (`s1_helper_session.py:141–146`); and descendant reservation requires a live B parent matching creator boot ID, PID, start ticks, and PGID, with reducer and final-contract checks (`s1_helper_session.py:147–152,223–235`; `s1_validation_contract.py:492–500`). The driver, contract, and recovery fixture have the same ordered Corrections001–015 then addenda001/002/003/006; rejected 004/005 are absent. The contract requires a current ledger for no-timeout admission and binds the exact Main session handle. The no-ledger `stop_group` branch keeps its TERM/grace/KILL, group census, process wait, retirement, and return sequence; the four visible callers are supervisor final cleanup, registered fixture callback, direct repeated-close test, and scenario-worker cleanup.

The nine-path diff adds no test method or scenario name and textually retains existing assertion lines and deadline expressions apart from the recovery positive-control adjustment and added bounded closure assertions. The three budget threads reserve H before `start`, retain their original `Thread` objects, and keep their `join(3)`/`join(2)` calls. L35 retains its PID-only release marker and original safety deadline while adding census, acknowledgment and retained pidfd checks. The source still expresses `B+max(1,H)≤8`, the 150 GiB artifact cap, and 64 MiB memo cap. I did not re-enumerate the 78/249/1,028 collection or verify capacity or behavior at runtime.

**Next step:** repair the waited-root partial retry, then obtain a fresh independent exact-source review. This verdict supplies **NO TEST/RUNTIME CLEARANCE** for fixtures, imports, compilation, pidfds, diagnostics, aggregate, admission, or launch.
