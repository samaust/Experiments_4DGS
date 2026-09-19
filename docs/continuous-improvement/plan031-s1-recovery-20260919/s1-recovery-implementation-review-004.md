# Iteration 5 implementation review — incomplete

**Live S1 calibration recovery is NOT READY and is not safe to admit.**
Implementation stopped on the user's explicit immediate-finalization request.
No safety package is closed. No production authority is created by these records.

Validation: `/home/auss/git_repos/samaust/Experiments_4DGS/docs/continuous-improvement/plan031-s1-recovery-20260919/s1-recovery-validation-005.json`, SHA-256 `f6092b89c9969b81659e5d8aeae6247bc0b7ad056d35551b9fabc8b3990a12f2`, 91240 bytes.

The exact focused command was:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .local/envs/stg-colmap/bin/python -B -m unittest discover -s tests -p test_vipe_benchmark_s1_recovery.py -v > /tmp/p36-focused.log 2>&1
```

It passed **13 methods, zero failures/errors/skips, exit 0, 41.147 seconds**.
The retained combined log and emitted method identities were independently
reconciled with the unittest footer and tool completion. Exact subtest outcomes
and per-process UTC/monotonic timing were not instrumented. The run exercised
intermediate source, before the spawned-helper and strict-sampling changes.
The final source is **not runtime-validated**. The prescribed ordered aggregate
(s1_semantics, s1_recovery, backends, contracts, component_recovery, execution,
budgets, supervisor, review_annotations) was **not run**. Earlier aggregate
results are not substituted. The fixed runner and exact tuple contract are absent.

The focused positive controller fixture still uses synthetic external worker and
device boundaries; it is not real successful segment progression. The inherited
numerical/serialization/contract cases remain in the focused log. No new race,
mutation, corruption, resource-bound or partial-count case is claimed. A
multithreaded-fork warning was emitted by the intermediate implementation.
The later spawned implementation removes that direct fork in source but has
not been tested, and spawned startup/transport/reaping remain open safety work.

- **F5-1 / L1-L2 — incomplete:** Shared canonical comparison and captured active reservation checks added. Focused intermediate fixture passed. Full applicable-boundary mutations, real synchronized contenders, continuations and replay cases remain uncollected; final source untested.

- **F5-2 / P1 — incomplete:** Generic CLI structural parse protection and secondary block-publication notes added; cleanup publication uses prepared evidence. Trusted first-result clock/effective allocation, structured primary/secondary propagation and complete corruption/storage/death/CLI tables remain incomplete.

- **F5-3 / P1 — incomplete:** Structural produced-row guard and unique identity reconciliation added; conflicting identities excluded, result rows included, unknown totals retained. No collected new count/duplicate/corruption/interruption cases; incremental durable summary on helper timeout is not implemented.

- **F5-4 / P2 — incomplete:** Direct fork helper replaced by spawned serializable CPU operations; strict required resource fields, 100-ms S1 polling, lower worker threads and cleanup uncertainty added. Spawn integration is untested. Fixed pre-reservation helper pool/readiness, bounded transport/reaping/descendants, sample timestamps, monitored cleanup/ledger fsync, conservative finalization charge and acknowledgment remain missing. No hard-bound safety claim.

- **F5-5 / A1-A4 — incomplete:** Exact literal tuple declarations, fixed source-bound aggregate runner and strict metadata validation were not implemented. Remaining numeric/runtime/envelope cases and full real segment progression remain uncollected.

- **V1 — incomplete:** Prescribed final current-source aggregate not run. Focused diagnostic used intermediate bytes; no test claim applies to final source. Static parse and diff check only. User requested immediate finalization.

All current Python source/test files parsed, and the prescribed git diff
check returned 0. These static checks do not validate spawning or monitor safety.
Source membership now includes the new s1_cpu_helper.py through the existing
package glob. Validation binds all 71 current source/config/test records.

All 38 frozen scientific records and prior loop artifacts were rehashed unchanged.
The ledger's 447-event chain, 332437 bytes, head and SHA-256 match assessment-008;
original failures 250/255 and R-S skip 256 remain. Historical GPU consumption
remains 4374.044265462899 seconds over 30 attempts, with no active reservation
or production S1 recovery event. Index is unchanged. Status old bytes are saved,
transition-005-1 extends the four verified prior transitions, and correction-004
retains the original baseline with Plan 036/review-005/assessment-008 provenance.
No historical status bytes or accounting were reconstructed/reset.

Inspection-inclusive timing was not captured. The separately saved first-clock
timing excludes initial inspection, so full 1800-second compliance is unknown.
Historical P31-5 and prior timing/status-byte caveats remain. No GPU/model/device
job, production authorization/registration/controller call, staging, commit,
delegation or scientific report/benchmark rerun occurred. No prompts were read.

S1-1 retains earlier semantic CPU support only; S1-2 remains unmet in production
and incomplete in CPU acceptance; S1-3 has no live recovery outcome. S1-4 holds
within the audited preservation scope. Resume CPU safety implementation and
collect all remaining Plan 036 cases before considering any later DO authority.
