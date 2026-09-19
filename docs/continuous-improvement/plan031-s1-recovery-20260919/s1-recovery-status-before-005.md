# S1 recovery — iteration 4 IMPLEMENT stopped

Plan 035 is partially implemented. Work stopped on the user's explicit request
to finalize. **Live S1 calibration recovery is NOT READY and not safe to admit.**

The focused CPU suite `test_vipe_benchmark_s1_recovery.py` passed **13 tests,
0 failures, 0 errors, 0 skips, exit 0**, in **42.534 seconds**. It now exercises
real disposable admission, registration, reservation, prelaunch, supervised
acceptance/publication and result resolution, using synthetic worker/device
boundaries and real source membership. The numerical first-result failure case
reaches the intended logits/probabilities guard. Subtest outcomes were not
individually captured. The prescribed nine-suite aggregate was not rerun.

Changes bind baseline_correction in admission, add lifecycle ordering checks,
protect explicit S1 CLI selection, and move acceptance/terminal publication into
the reservation using monitored CPU helpers. These changes are not fully
validated. Required races, boundary mutations, durable-failure/resource tests,
exact receipt subtest membership and worker progression coverage remain open.
The monitor emitted a multithreaded-fork warning; helper cleanup and final ledger
write still need hard-bound review. No readiness claim follows from 13 passes.

No GPU/model job, device probe, production authorization/registration, production
ledger mutation, staging, commit, delegation or scientific report rerun occurred.
All 38 frozen scientific records and the 447-event production ledger were
rehashed unchanged. Prior records remain immutable; the old status bytes and its
explicit bookkeeping transition are retained. Historical P31-5 limitations and
unavailable older status-byte caveats remain. Inspection-inclusive timing was
not captured, so full timing compliance is not claimed.

See s1-recovery-validation-004.json, s1-recovery-implementation-review-003.md,
assessment-007.json and s1-recovery-preparation-004.md.
