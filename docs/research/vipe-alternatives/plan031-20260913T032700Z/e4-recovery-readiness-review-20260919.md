# E4 recovery readiness review — 2026-09-19

Reviewed HEAD `df868f77b3e6096e26488e2e7154caa4aa9243bf`, repository instructions,
Plan 031, status, continuation audit002, recovery authorization005 and validation015.
Scope: local source/evidence review and disposable CPU fixtures only. No delegation,
external network request, installation, GPU probe/job, admission, recovery registration,
aggregation, reporting, staging or commit. This document is the only path changed
by this reviewer; a concurrent authorization file appeared during final checks.

## Finding

No additional setup-source repair was demonstrated by this review. The routing and
initial-scan repairs in df868f7 pass the focused fixtures, and the existing recovery
mechanism can represent a fresh explicitly authorized E4 attempt without resetting
history. **Setup is not yet ready to dispatch:** updated domain policy is user-reported,
not verified here; fresh source-bound repair evidence and an actual new bounded
authorization bound to that evidence are still required. A policy change does not
replenish attempts. Concurrent `e4-recovery-authorization-006.json` now names
recovery005 and the correct previous failure, but still references stale
validation015; source verification should reject its registration as written.
That untracked file was neither created nor edited by this reviewer.

`runtime.setup` copies the original environment for each command, selects its inherited
HTTPS route before installing the local metering proxy, and sets UV/PIP retries to
zero. `transfer_proxy` chains HTTP CONNECT (including metered handshake bytes), rejects
unsupported proxy schemes and rejected CONNECT responses without direct fallback,
and scans accounting before yielding control to uv. `budgets` still inventories all
files and retains receipt accounting/inode deduplication. Later scans remain synchronous;
the fix does not guarantee handshake latency under arbitrary filesystem stalls.
Direct mode still chooses one resolved address and one connection; no multi-address
fallback was added. Local fixtures do not prove package-host or wheel availability.

## Recovery and admission gates

1. `Ledger._authorize_e1_recovery` checks exact E4-only cu130 amendment scope,
   numbered sequential identity, original and latest cleaned-up failure hashes,
   no active reservation, source-file hashes in passing repair evidence, and the
   cumulative setup ceiling. Reservation rejects consumed identities. The checked
   recipe retains Python 3.11, torch/torchaudio 2.13.0+cu130, torchvision
   0.28.0+cu130, NumPy 2.1.3 and xformers>=0.0.26 under exact constraints.
   No new authorization was constructed. Authorization005/recovery004 is consumed.
2. Validation015 is **stale**: its runtime.py hash no longer matches df868f7.
   It also supplies `source_files`, whereas model `common_admission` requires
   nonempty `sources`. Create a new record binding the full relevant current
   implementation/tests and actual test outcomes; supply both fields if sharing
   that record between setup and model admission. Preserve validation015 unchanged.
   These readers verify supplied entries, not completeness of the source manifest;
   the coordinator must include the proxy, budget, runtime and recovery changes.
3. The controlled dispatch requires host PID visibility before reservation for
   setup as well as GPU jobs. Use the supervised `setup-recovery` controller,
   not a manual worker or package install. The manual directory now exists,
   superseding audit002's absence finding, but still has no result.json. Its
   failure/evidence and any manual installation consumption need reconciliation
   before claiming complete resource accounting; ledger totals alone exclude an
   unregistered manual worker. Do not adopt partial installed metadata as qualification.
4. D1 common admission has a separate reproducible provenance blocker:
   `auto_annotations.check_policy` verifies the old policy's `original_plan` against
   the amended live file. Expected SHA-256 is
   `27f3f284886f1af7e19602d0b21a2494ac1c5cbab1878b8e73b25874d43db74b`;
   actual is `5b2c3eec431337e720cad0dae60738b4040045d25815a790f8534e79eaa6dcd8`.
   This affects real admission, not merely synthetic fixtures. Before D1, preserve
   and verify original plan bytes through an explicit amendment-aware provenance
   record/path and validate that chain. Do not replace the historical hash or
   disable verification. This is not a prerequisite for import-only setup, whose
   CLI does not call common admission; no downstream provenance repair was made here.
5. E4 success still requires lock/wheel hashes, inventory/licenses, exact versions,
   UniDepthV2 and xformers.ops imports with zero forwards, and a completed ledger-bound
   result. Actual native/CUDA qualification belongs inside the allocated D1 job.
   Reopen only explicitly authorized unstarted slots: D1-fit, then R-D immediately
   after a complete fit source, then D1-check only after passing fit. C1 depends on
   D1 gates; C3 additionally lacks S1 reconstruction; C2 requires D2 and license
   evidence and is not unlocked by E4. Preserve all original stage/resource caps.
6. Aggregate/report already completed at sequences 400/404. Do not rerun them or
   broad `execute`; new reporting requires an explicit reporting amendment.

Conditional controller form, **not executed or authorized by this review**:

```sh
.local/envs/stg-colmap/bin/python scripts/basketball_vipe_benchmark.py --run-id plan031-20260913T032700Z setup-recovery --authorization <new-explicit-authorization-json>
```

## Validation and preserved evidence

```sh
.local/envs/stg-colmap/bin/python -m unittest tests.test_vipe_benchmark_transfer_proxy tests.test_vipe_benchmark_runtime tests.test_vipe_benchmark_budgets tests.test_vipe_benchmark_setup_recovery tests.test_vipe_benchmark_execution tests.test_vipe_benchmark_annotations -q
```

**121 tests passed in 4.785 seconds.** Setup-looking fixture output uses mocked
commands/disposable directories; no package installation occurred.

```sh
.local/envs/stg-colmap/bin/python -m unittest tests.test_vipe_benchmark_auto_annotations -q
```

**5 tests in 0.076 seconds: 3 passed, 2 errors.** Both review tests fail with
`ValueError: changed file: .../plans/plan_031.md`, at the hashes above. This is an
application provenance rejection, not a sandbox/permission failure. No escalation
or retry was needed. The full suite was not run and full admission is not claimed.

A read-only Python check parsed all 420 ledger rows, verified each sequence,
previous hash and canonical event hash, and computed states/totals without calling
admission or adding events. Latest sequence 419 remains recovery004 failed,
56.68333473900202 seconds, cleanup confirmed, event SHA-256
`a8fafe42ccda1c3a4b11d32e0aa17bef42ec3adafe1ae4808e47c0de300184c3`.
Ledger SHA-256: `0e847ebfedae931e3f2ff2b7106f9abc5e1a849cf8ce6316b58e2408db190ba7`.
No active ledger reservations; this is not a fresh host-process inspection.
Ledger setup consumption is 12 attempts / 5015.895450629825 seconds, with zero
reserved seconds. This is historical accounting, not a grant of remaining retries.
D1-fit/check are blocked; R-D skipped; C1–C3 blocked.

Study and protocol hashes still match their frozen originals:
`6fbb6e55dedf444766c75e946c3d5099426839e0df158706d98d28b635353e8e` and
`6d32683e3d351f8f19afffa11fe5664c5a15515f84a2b9380f86a39a757072f5`.
No historical records, source files, runtime versions or allocations were edited.
`git diff --check` passed; changes remain unstaged.
