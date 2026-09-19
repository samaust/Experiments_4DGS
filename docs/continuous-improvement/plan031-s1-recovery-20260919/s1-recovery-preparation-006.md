# S1 recovery preparation 006 — non-executable, NOT READY

This is an incomplete CPU handoff. It creates no authorization, registration,
reservation or executable recovery instruction. Live admission is unsafe.

Bound records:

- `/home/auss/git_repos/samaust/Experiments_4DGS/plans/plan_037.md` — SHA-256 `b5d4679f7af28b5738dc3d593b7596313f35a5f5761138712fd56bd3a5a639af`, 19237 bytes.
- `/home/auss/git_repos/samaust/Experiments_4DGS/docs/continuous-improvement/plan031-s1-recovery-20260919/s1-recovery-baseline-correction-005.json` — SHA-256 `0c1d6a998876137ae5dbbb6eeb3435522906757a3bd1c1dacd6eb67e42247c26`, 14164 bytes.
- `/home/auss/git_repos/samaust/Experiments_4DGS/docs/continuous-improvement/plan031-s1-recovery-20260919/s1-recovery-validation-006.json` — SHA-256 `a97e8ba0e42ce69b107b0bc11aa8463bd14099d55d1f2a921b5f283413f6ccda`, 196764 bytes.
- `/home/auss/git_repos/samaust/Experiments_4DGS/docs/continuous-improvement/plan031-s1-recovery-20260919/s1-recovery-implementation-review-005.md` — SHA-256 `64b92c5b76366110b0187e0a92f1faca0fff5b74212cc555a3069153b7ceaa74`, 5949 bytes.
- `/home/auss/git_repos/samaust/Experiments_4DGS/docs/continuous-improvement/plan031-s1-recovery-20260919/assessment-011.json` — SHA-256 `adf9cd893323c0fc60e03bb65422ca221986a8f3ec910a47272a3fdbd68faf4a`, 74435 bytes.

Final current-source aggregate: 148 methods, 83 recorded subtest callbacks,
0 failures, 1 runner serialization error, 0 skips, exit 1, 48.213986296 seconds.
All 13 new helper methods passed. Missing Identity subtest serialization prevents
complete callback evidence. Fix that runner integration before a fresh complete
aggregate; retain this failed run. Finish F6-1/F6-3 bounds and fault/descendant
coverage, and all five inherited Plan 036 gates listed in validation/review.
No older pass can replace required current-source acceptance. Inspection-inclusive
timing is also unproven. The user requested finalization, so work stops here.

Only a separately authorized later DO stage after every CPU gate passes may
consider S1-calibration-recovery-001: one calibration attempt, positive effective
seconds min(3600,93600-gpu_elapsed_seconds-gpu_reserved_seconds). Loading,
qualification, acceptance, publication, cleanup and finalization stay inside the
cap, with reserve min(30,effective_seconds/4). Reservation consumes the identity
even without launch. No retry or renamed attempt. Fresh authority, source,
amendment, prerequisites, ledger and exclusive resource checks remain required.

Retain one exclusive GPU group, 22 GiB device memory, eight CPU workers,
150 GiB artifacts, 60 GiB downloads and existing 57600-second preparation/setup
ceilings. No new setup/download/smoke jobs, reconstruction, R-S or scientific
aggregation/report reruns. Production ledger and frozen records stay unchanged.
