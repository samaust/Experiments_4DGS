# Plan 016: durable persistence and focused benchmark

The focused benchmark is **scientifically rejected**. Persistence qualification passed, and all
405 scheduled scientific outcomes were published and independently verified. The final
initialization-only policy qualified 50 of 81 outcomes, retained six missing required seeds,
and disagreed across conditional paths at eight targets. All 47 archived qualified controls
retained acceptable costs. `ready_for_full_screens` is false.

Accepted timing, production candidate, and final-validation protocol remain null. No full
screens, production fitting, selection, final validation, downloads, GPU jobs, or training
were launched. The v9 directory, configuration, sources, empty baseline artifacts, corrections,
and verification reports were preserved unchanged. Its 50 reported qualifications were not
used as baseline costs, KKT denominators, or seeds.

## Evidence and execution

- [Admission and explicit historical source substitutions](basketball-shared-timing-v10/prepare/admission.json)
- [Frozen 81-attempt manifest](basketball-shared-timing-v10/prepare/benchmark-manifest.json),
  [policies](basketball-shared-timing-v10/prepare/policies.json), and
  [actual execution source hashes](basketball-shared-timing-v10/prepare/execution-sources.json)
- [Four actual-worker preflight outcomes](basketball-shared-timing-v10/persist/four-case-decision.json)
  and [interruption evidence](basketball-shared-timing-v10/persist/interruption-decision.json)
- [Fresh baseline denominators](basketball-shared-timing-v10/baseline/denominators.json)
- [Conditioning decision](basketball-shared-timing-v10/adapt/metric-decision.json),
  [initialization decision](basketball-shared-timing-v10/adapt/initialization-decision.json), and
  [stopping decision](basketball-shared-timing-v10/adapt/stopping-decision.json)
- [Frozen final union](basketball-shared-timing-v10/adapt/final-policy.json) and
  [final benchmark decision](basketball-shared-timing-v10/benchmark/decision.json)
- [Attempt index](basketball-shared-timing-v10/package/attempt-index.json),
  [dependency index](basketball-shared-timing-v10/package/dependency-index.json),
  [runtime comparisons](basketball-shared-timing-v10/package/runtime-comparisons.json), and
  [terminal decision](basketball-shared-timing-v10/package/terminal-decision.json)
- [Terminal hash manifest](basketball-shared-timing-v10/evidence.json)
- [Workflow verification](basketball-shared-timing-v10/verify/result.json) and
  [independent terminal report](basketball-shared-timing-v10/independent-report.json)

The existing 18 conditional targets, 20 conditional dependencies, four joint targets, and
three joint dependencies retain their IDs, diagnostic labels, ordering, and seed-selection
rules. Each of the five policies received fresh problems, starts, caches, and dependencies.
The unchanged limits are 200 iterations and 200 distinct canonical states per attempt,
including initialization and restoration. Qualification requires original-coordinate KKT
at most 1e-6 and normalized depth above 1e-7. Conditional omitted camera-offset derivatives
are retained as joint diagnostics and do not qualify a joint state.

## Scientific results

Every row in this table represents 81 scheduled, persisted, verified outcomes. “Invocations”
counts entry into SciPy's optimizer; initialization-only rejection and missing seeds are
separate outcomes. Policy wall time includes worker execution, persistence, and independent
cohort reload verification, at up to six single-thread scientific workers.

| Policy | Optimizer invocations | Initialization-only rejections | Missing seeds | Qualified | Policy wall seconds |
| --- | ---: | ---: | ---: | ---: | ---: |
| Baseline | 72 | 3 | 6 | 50 | 33.74 |
| Conditioning | 72 | 3 | 6 | 60 | 23.74 |
| Initialization | 75 | 0 | 6 | 50 | 33.26 |
| Stopping | 72 | 3 | 6 | 50 | 32.75 |
| Final: initialization only | 75 | 0 | 6 | 50 | 32.47 |

There were 366 optimizer invocations and 97,268 journaled numerical entries across the
405 scientific outcomes. These counts exclude preflight and read-only verification.
The 260 qualifications across policies are repeated comparisons, not 260 distinct targets.
The independent report also measures each cohort's solver/journal wall sum, the completion
path after the last numerical boundary (serialization, publication, and receipt verification),
and a separate full reverification. Those overlapping measurements are labeled separately;
policy wall times remain the end-to-end comparison.

Conditioning recovered three of the six frozen iteration-limit targets, with one recovery
in each of groups 2, 9, and 11. It nevertheless failed the required median new/baseline KKT
ratio: **0.2419725969**, against a maximum of 0.1. All six baseline denominators were
independently recomputed, positive, and frozen before the arm ran.

Initialization produced feasible, bounded cold parameters for all three frozen infeasible
cases, using the unchanged analytical depth target of 1e-6. It passed its initialization
screen; none of those three subsequent fits qualified. Stopping qualified two of its three
frozen xtol targets and failed its screen. All three arms preserved the 47 controls and
retained their support-change records, missing dependencies, and observable-growth checks.

Only initialization entered the final union. Its final benchmark had 31 nonqualifying
outcomes, including the six missing-seed records. Conditional path disagreements occurred
at targets 00, 01, 04, 07, 11, 13, 14, and 17. No focused-pass candidate or full-screen
continuation budget was issued. The existing Plan 015 full-screen gates still apply to any
separately authorized continuation.

## Durable attempt lifecycle

Each attempt directory contains an append-only `journal.jsonl`, an immutable
`attempt.json.gz` when publication succeeds, and a `receipt.json` after independent
verification. Job summaries reference these files and their hashes; they do not duplicate
full fitted records.

Publication validates finite NumPy-aware JSON, writes and fsyncs a temporary file, links it
without replacement, and synchronizes its directory. The worker reloads the artifact,
verifies identity, accounting, initialization depths, and available physical arithmetic,
publishes the hash-bound receipt, then appends and fsyncs completion. A warm dependency is
usable only after this transaction. Its record binds the source artifact, returned state,
policy, coordinate, and completion provenance.

Journals contain exact canonical/physical state bytes, problem and transform definitions,
sequence numbers, chained checksums, and numerical-entry start/return events written at
the numerical boundaries. The verifier compares those events with actual entry arguments
and the artifact's state ledger. It also reconstructs the frozen directional seed choices.
Missing seeds explicitly record no optimizer invocation. Unfinished work retains unknown
final counts and observed lower bounds; invalid journal suffixes never fabricate zero work.

The supervisor runs outside the scientific process group. A worker failure cancels further
dispatch; the supervisor sends SIGTERM to the whole group, waits two seconds, and sends
SIGKILL even if the leader has already exited. Absolute deadline expiry uses the same group
termination. A published artifact can have a missing receipt/completion reconstructed by
`recover_attempt`; that operation never reruns optimization. Genuine interrupted scientific
attempts cannot resume automatically.

The six preflight allocations were exhausted exactly as frozen. The regularized and
data-only controls qualified; the data-only nonqualifying case returned complete evidence;
the infeasible case retained its initialization evidence without invoking the optimizer.
In the two-allocation interruption test, a successful completed record survived SIGKILL of
the worker during the next attempt. The interrupted journal retained one initialization
depth-entry start and no return, with the final numerical and optimizer counts unknown.
Preflight records were never benchmark seeds.

## Validation and clock

The hard clock started at **2026-09-08 04:52 UTC**, before implementation inspection. Its
absolute scientific stop was 06:07 UTC and terminal deadline was 06:22 UTC; neither was
extended. Admission, inherited source substitutions, cases, and numerical policies were
frozen before minute 10. The added v10 execution source index was published immediately
before actual-worker preflight; the prepare stage's later terminal wrapper records the
original admission timestamp rather than claiming it was newly frozen then.

| Milestone | Completed elapsed minutes | Deadline minutes |
| --- | ---: | ---: |
| Historical admission, cases, and numerical policies | 2.04 | 10 |
| Persistence qualification | 12.81 | 20 |
| Fresh baseline and denominator freeze | 13.66 | 35 |
| All standalone decisions and final union | 15.75 | 60 |
| Final benchmark; scientific computation stopped | 16.67 | 75 |
| Terminal package | 19.35 | 90 |
| Workflow verification | 21.03 | 90 |
| Independent terminal audit | 22.11 | 90 |

The [Basketball suite](basketball-shared-timing-v10/basketball-tests.log) passed 253 tests
using the unchanged v7 scoped historical clock harness. The
[budget suite](basketball-shared-timing-v10/budget-tests.log) passed seven tests and
[SelfCap](basketball-shared-timing-v10/selfcap-tests.log) passed three. The Basketball count
includes 17 new storage/boundary regressions, also executed in
[preflight](basketball-shared-timing-v10/persist/persistence-tests.log).
Eight additional [saved-evidence and supervisor regressions](basketball-shared-timing-v10/validation-tests-final.log)
passed without optimization. These reject altered source hashes, counts, cross-policy
seeds, trace parameters, multiplier mappings, and support records, and verify that the
external supervisor packages a missing-result failure and terminates descendants.

Storage tests cover encoding/nonfinite metadata, failures before and after publication,
receipt/completion recovery, truncation/checksums, missing worker artifacts, duplicate IDs,
overwrite attempts, corrupt records, unsupported completion claims, cancellation of later
dispatch, and descendant termination. Boundary tests cover adjacent double states,
derivative/constraint-first requests, rejection before a 201st state, shared initialization
budgets, and explicit interrupted entry accounting. The independent terminal report adds
full saved-trace ownership, multiplier conversion, support recomputation, final-policy union,
scientific count reconciliation, and deadline checks.

Run the existing frozen stages with `.local/envs/calibration-global/bin/python
scripts/basketball_shared_workflow_v10.py <stage>`, where stages are `prepare`, `persist`,
`baseline`, `adapt`, `benchmark`, `package`, and `verify`. They refuse an already-terminal
stage and do not restart this run's clock. The independent read-only report is produced by
`scripts/basketball_shared_report_v10.py --output <fresh-path>` within the frozen deadline.
