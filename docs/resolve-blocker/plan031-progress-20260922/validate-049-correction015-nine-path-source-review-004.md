# Correction015 nine-path source review 004

**Verdict: NEEDS_CORRECTION. NO EXECUTION CLEARANCE.** This is an independent static review of the nine current source paths at the exact hashes below. The reviewed implementation draft was identified as `e48fd8eae293bc2276b1ae52d17005ff0122fff7aa9de99911a7fadc5b3f9c0e`; that identifier does not replace the individual source hashes. I performed source and diff reads only. I did not import or compile project code, run tests or fixtures, open pidfds, inspect live processes, or run a diagnostic or aggregate. I did not read `prompts`.

| Path | SHA-256 |
| --- | --- |
| `scripts/vipe_benchmark/supervisor.py` | `2d04eea77a507392feda918c4003bd9ec599fe8d9325cb1e9feafdba143257ad` |
| `scripts/vipe_benchmark/s1_helper_session.py` | `c3326fe0c738e0180b42289f03c52ff8586e9eef86fd242dc3ea3a013a72e106` |
| `tests/test_vipe_benchmark_supervisor.py` | `c1f74f4fb121afb6a7639043a61fff81775b41e6de23ab3a66bfa039f7917188` |
| `tests/test_vipe_benchmark_s1_helper_fixtures.py` | `202f20d1b4108680d802394ccd89c2a46da66abaa4108bc421fdd8b59a8a3b7a` |
| `docs/resolve-blocker/plan031-progress-20260922/launch-049-exec.py` | `be9cdd762b866204eb77aa58e18ca8ed4e48b68df625313fda52610caa90bc1e` |
| `scripts/vipe_benchmark/s1_validation_contract.py` | `72f8a853bb1f6893045e26e3f77a76c0cfb3c351d749b79ac4332aeb0f2b5a0e` |
| `tests/test_vipe_benchmark_s1_recovery.py` | `da27052c9e70c3defe02b9bba3d670a456af1034fb86b5e116346737b5f37018` |
| `scripts/vipe_benchmark/s1_validation_capture.py` | `478b20b2c8b00931ac7dc9db5ef65a9ca767ea8734ea7df070908c0daf40aa52` |
| `tests/test_vipe_benchmark_budgets.py` | `566f8599355b48c62d9d375b8cb9454472305820295065091445a2c56d178a2c` |

## Blocking finding: root/group identity can lapse before signaling

In `supervisor.py:76-79`, ledger-enabled `stop_group` checks the B root's `/proc` identity. It then loops over descendant records and obtains pidfds (`:95-117`), which can take unbounded time relative to the root's lifetime. It sends `killpg(process.pid, SIGTERM)` at `:123` and later `SIGKILL` at `:130` without rechecking the root identity or proving that the numeric PGID still belongs to the selected tree. The descendant pidfds bind descendants only; no root pidfd or retained process-group identity bridges that gap. A concurrent caller can reap the root after the earlier check, permitting PID/PGID reuse before either group signal. The same race exists between TERM and KILL. The ledger path therefore cannot establish the addendum006 requirement that no unrelated reused process group be signaled. A fresh check alone narrows the race but does not close a check-to-kill gap; the correction needs a concrete safe signaling invariant and explicit behavior when the group identity is uncertain. Keep the legacy path's existing behavior scoped separately.

## Other reviewed transitions

The initial pin set is published only after all requested acquisitions and rechecks succeed; failure before publication closes acquired descriptors and leaves ledger roots charged. A later `signals='started'` retry refuses to send another signal. Following a completed signal phase, a nonempty group census is returned with root and pins retained. A descendant retirement readback failure is retried from freshly replayed ledger state; already retired descendants are skipped, and retained pidfds remain available for unresolved descendants. L35 keeps its separate marker, live census, acknowledgment and pin-before-release sequence. The exact same retained handle can take the retired-root path without a second retirement event, while different handles and unresolved trees fail closed. `root-wait` and `root-retired` append failures leave a replayable `live` or `waited` state; the retry paths avoid a second group signal after a completed signal phase. These are static control-flow conclusions, not execution evidence.

The driver and contract append addendum006 after existing addenda001–003 and preserve the prior correction pointer. The new start frame, same session handle, readiness, two live polls and `ADMIT` handoff are visible in the source. The capture runner is charged as B while the outer live session is H; root/descendant transitions retain the `B+max(1,H)≤8` ledger bound. The nine-path diff retains the existing legacy `stop_group` branch when `S1_JOB_LEDGER` is unset and adds bounded closure checks to the two named supervisor tests. I found no separate blocking discrepancy in the other retry, capacity, authority or handoff paths from static inspection. Original assertion/deadline/count preservation and live operation remain subject to the distinct validation gate; this review does not certify executed behavior.

The relevant prior plan review is `plan049-correction-015-source-scope-addendum-006-independent-review-001.md`. Its PASS was plan-only and explicitly required exact-source review. The earlier addendum005 review's same-handle objection is addressed in source, but the new signal identity gap blocks source clearance. Do not use this document as fixture, test, admission, diagnostic, aggregate, or launch clearance.
