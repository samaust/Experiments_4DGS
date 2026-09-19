# Iteration 4 implementation review — incomplete

**Live S1 calibration recovery is NOT READY and not safe to admit.** Plan 035
was not completed before the user requested immediate finalization. No new
production authorization or registration was created.

Validation: `/home/auss/git_repos/samaust/Experiments_4DGS/docs/continuous-improvement/plan031-s1-recovery-20260919/s1-recovery-validation-004.json`, SHA-256 `fec02faa2241d3ebcb2b0c77961fcdc4e9d9b73d453ca8977168077c5b0de815`, 73753 bytes.
The validation status is `incomplete`; a focused success does not authorize use.

The exact command was:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .local/envs/stg-colmap/bin/python -B -m unittest discover -s tests -p test_vipe_benchmark_s1_recovery.py -v > /tmp/p35-focused.log 2>&1
```

It completed with **13 methods, zero failures/errors/skips, exit 0**, in
**42.534 seconds** reported by unittest. Full combined output and the 13 emitted
method identities are retained in validation and s1-recovery-focused-004.log.
Subtest counts/outcomes were not independently instrumented and are unknown.
The prescribed ordered nine-suite aggregate was **not run**. Prior 135/79 results
belong to previous source and are not current-source validation.

The test `S1RecoveryTests.test_result_requires_supervised_cleanup_and_exact_membership`
now calls execute_s1_recovery, real common_admission and annotation validation,
real registration/reservation, prelaunch, supervisor, acceptance, charged terminal
publication, finish and resolution. Source membership is no longer mocked.
Only host/device/resource/worker boundaries are faked; synthetic assets and rows
use actual guards. It checks 510 identities, 340/170 counts, correction propagation
and preservation of the failed original arm. The worker outputs are fabricated
at the external worker boundary; this does not establish real segment progression.

`FailureEvidenceTests.test_first_result_failure_stops_before_second_input` now
supplies valid diagnostics with deliberately corrupted probabilities. It reaches
`invalid raw S1 logits/probabilities/boxes`, preserves raw failure evidence and
stops after one adapter call. Its other two cases retain malformed-label and
serialization coverage. This closes the inherited numerical fixture defect only.

Changes in this pass:

- scripts/basketball_vipe_benchmark.py
- scripts/basketball_vipe_worker.py
- scripts/vipe_benchmark/execution.py
- scripts/vipe_benchmark/s1_recovery.py
- scripts/vipe_benchmark/supervisor.py
- tests/test_vipe_benchmark_s1_recovery.py

Finding dispositions:

- **F4-1 / L1** — Implemented correction propagation and real controller positive fixture; focused test passes. Full boundary-negative matrix remains unrun; partial.
- **F4-2 / L2** — Added read-only ordered lifecycle validator and locked admission recheck. No synchronized races or comprehensive lifecycle/preservation mutations collected; partial.
- **F4-3 / P1** — Explicit CLI selector, minimal block publication and optional consumed evidence parsing added; terminal rows now requalified on failure. CLI/corruption/storage/death matrix not run; partial.
- **F4-4 / A1-A3** — Numerical first-result failure fixed and passing. Full serialized numerical/runtime/envelope tables, zero/skip and successful real segment progression remain incomplete.
- **F4-5 / P2** — Acceptance and terminal receipt now precede finish; resolver verifies acceptance references. CPU fork helpers replace SIGALRM. Hard-bound/resource/ownership/cleanup/death tests absent; multithreaded-fork warning, synchronous cleanup/final ledger writes and repeated first-row reconciliation remain review concerns. Not closed.
- **F4-6 / A4** — Exact source-bound required subtest tuple tables and receipt metadata rejection guards not implemented; remains open.
- **F4-7 / V1** — Source-bound partial evidence and preservation audit saved; nine-suite aggregate and complete execution metadata absent. Inspection-inclusive timing missing; incomplete.

The supervisor emitted a DeprecationWarning about forking a multithreaded
process. No deadlock occurred in this focused run, but the warning is not
resolved and no blocking helper/resource regression matrix ran. Monitor helper
cleanup uses synchronous waitpid; process-group cleanup and final ledger writes
still need deadline/ownership review. Failure reconciliation can revalidate the
first row, and failed optional evidence is not a substitute for all required
durable accounting assertions. There is no basis for claiming P2 complete.

All 70 current source/config/test records are bound. `git diff --check`
returned 0. All 38 frozen scientific records, original 447-event
ledger bytes/chain/head, original failures 250/255, R-S skip 256 and index match
prior evidence. GPU elapsed remains 4374.044265462899 seconds;
there are no active reservations or production S1 recovery events. Bookkeeping
status changed only with preserved old bytes and an immutable transition.
Historical P31-5 limitations and unavailable first-two historical status bytes
remain; none were reconstructed or rebaselined.

Inspection-inclusive timing was not recorded, so the 1,800-second budget cannot
be independently certified from this receipt. The first captured clock was
20:28:47 UTC; it excludes earlier inspection and is not relabeled as the start.
Prior 642.618033546998/518.3559243239979-second durations retain their excluded-
inspection caveats; the prior 848.010818-second bound retains its unknown-start caveat.

S1-1 retains prior semantic scope with the focused numerical repair. S1-2 remains
unmet in production and incomplete in CPU acceptance; S1-3 has no live outcome.
S1-4 is met within the audited preservation scope. Resume only CPU implementation
and validation, with fresh timing and required tests; do not execute calibration.
