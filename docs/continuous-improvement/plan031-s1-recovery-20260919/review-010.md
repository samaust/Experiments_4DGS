# Iteration 10 REVIEW — Preserve the receipt milestone; close numerical envelopes next

The committed receipt milestone is supported by the current bytes and saved
execution evidence. S1 recovery admission remains **not ready**. Recommend a
small CPU milestone for the result/row numerical envelope portion of **R9-6**,
plus the narrow direct-test-entrypoint regression found below. Keep R9-2–R9-5,
real 510-row worker progression, and the wider lifecycle/mutation matrices open.

This reviewer read the continuous-improvement-loop skill, AGENTS.md, objective,
current status, assessment-019, review-009, Plan 039, relevant Plan 032/034/035/036
requirements, final implementation evidence, and current source/tests. This is
a direct REVIEW with no nested delegation. No tests, diagnostics, controller or
ledger APIs, GPU/device operations, models, setup/download/smoke jobs, source
edits or git writes were performed. Read-only Python used only the standard
library for file hashes, JSON/AST and saved-evidence reconciliation. Only this
review and [assessment-020-review.json](assessment-020-review.json) are added.
Status belongs to main and was left untouched.

## Current milestone evidence

HEAD is `44686a2` (full hash in the assessment). Source, tests, configuration and
plans have no working-tree difference from that commit. Fresh read-only
reconciliation found:

- All **74** current source/config/test records match validation-008 and both
  source snapshots in final aggregate-009-002/execution.
- Static AST collection has **157 methods**, **25 parameterized methods** and
  **213 declared callbacks**. Saved executed method order and each callback's
  typed parameters, canonical ID and passing status match those declarations.
- The saved final aggregate reports zero failures/errors/skips/discovery errors;
  its outer execution reports actual return code 0 and
  **92.21503551599744 seconds**. Raw file bindings and separate saved process
  observation support that pass. This review did not rerun it or independently
  observe the historical process.
- All **38** frozen records and the exact original ledger match. The ledger is
  **447 events**, **332,437 bytes**, SHA-256
  `2a0f66e38911b0ed029eb9dd0cf4bbd5da4a3b67abb577fbfe9ad67e6a888990`.
  Its hash chain is intact, with no active job or S1 recovery event. Historical
  GPU accounting remains 30 attempts / 4,374.044265462899 seconds / zero reserved.
  Failed finishes 250/255 and account/skipped event 256 remain unchanged.

`s1_validation_contract.py:214–314` now checks the missing R9-1 contracts:
literal declarations, exact typed callbacks, counters, sources, metadata,
closed artifacts and the actual-wait record. `s1_recovery.validation_record`
delegates to that same contract. The complete synthetic fixture remains
explicitly synthetic and uses the real guards; the real capture/audit evidence
is separately bound. Do not repeat the old receipt repair or reuse the first
aggregate after its recorded source change. Plan 039's two aggregate attempts
are consumed; subsequent execution needs the next plan's new allocation.

## Source findings and coverage disposition

**R10-1 — Result and row numerical fields are still unguarded (R9-6; S1-2/S1-3
prerequisite).** `stages.segment` emits row `native_group_wall_seconds` and
`group_size` at lines 160–163 and result `native_wall_seconds`,
`peak_allocated_bytes`, `peak_reserved_bytes` at lines 211–217. In contrast,
`s1_evidence.qualify_row:250–346` and `validate_result:349–368` never validate
those fields. The current `synthetic_row:99–103` and controller positive result
at `test_vipe_benchmark_s1_recovery.py:402–404` omit them while passing the real
guards in the saved aggregate. This is a concrete contract gap: missing,
nonfinite/negative timing, wrong group size and incoherent allocator values
can evade the result guard. No numerical-tampering probe was executed here.

There is enough current information to close **local** consistency without
changing a clock protocol: calibration group size is exactly one; group/native
durations must be finite and nonnegative; native total must agree with the
ordered singleton-group durations; peak byte values must be exact nonnegative
integers, allocated cannot exceed reserved, and neither may exceed the existing
configured device ceiling. Preserve zero as a valid duration/memory observation
and distinguish booleans from numbers. The sampled total-device ceiling remains
a separate supervisor requirement. Trusted reservation-relative time and native
versus total charged time depend on R9-3/R9-5 and must stay open.

**R10-2 — Direct script test entrypoints regress after literal-table conversion
(receipt-maintenance regression; S1-2 evidence support).** The six parameterized
suite files use `SUBTEST_CASES[self.id()]`, whose literal keys start with
`test_vipe_benchmark_<suite>.`. Each still has a `unittest.main()` script
entrypoint. Running that entrypoint defines classes in `__main__`, so the
lookup requests `__main__.<Class>.<method>` and raises `KeyError` before its
subtests. Affected suites: s1_semantics, s1_recovery, backends, contracts,
component_recovery and supervisor. Normal discovery imports those files by
their declared module names; this finding does **not** invalidate the saved
prescribed aggregate. Restore canonical declaration lookup independently of
the execution module name, preserving table keys, callback parameters and
scientific assertions. Validate representative real script execution within
the next CPU allocation; do not launch it during REVIEW.

The newly exported `strict_record` also rejects extra record keys, so its
compatibility was reviewed. Current enriched structures are explicitly sliced
to `path/sha256/bytes` in `referenced_records`, correlation-build validation,
loaded-runtime validation, and baseline ledger-prefix handling. The saved
controller fixtures pass those paths. No concrete additional incompatibility
was established from current call sites; do not add a speculative global
relaxation or reopen R9-1 on that basis.

The remaining inherited findings were inspected against current source:

| Gate | Current evidence and classification |
| --- | --- |
| R9-2 helper readiness/transport/sample freshness | Concrete source gap remains: synchronous `Process.start` and framed `Connection.recv` run on the monitor path (`supervisor.py:104,122`); helpers are created per operation; `validate_sample:211–223` has no temporal fields, and ready handling precedes sample-timeout handling at 246–265. Existing spawn/cleanup tests are credited; they do not establish blocked startup or partial-message bounds. |
| R9-3 trusted clock/effective allocation | Concrete source gap remains: `s1_evidence.elapsed:25–30` reads only worker environment; absent evidence can be published by `reconcile_first:67–68` with null elapsed. Failure/pass guards still compare to 3,600 at 80/400. The supervisor passes the start only in worker Popen environment at 335. Reduced-allocation testing checks reserved seconds, not qualification timing. |
| R9-4 incremental reconciliation | Concrete source gap remains: `reconcile_rows:185–237` stores progress locally and returns once; helper loss/final sample failure loses that result. Durable verified progress is not yet available to terminal publication. Existing complete synthetic counts do not cover interruption. |
| R9-5 failure/cleanup/finalization | Concrete source gaps remain: supervisor exception handling retains strings and overwrites `failure_kind`; cleanup lacks continuous sampling; final elapsed precedes the last helper reap and direct blocking `ledger.finish` at 492. `resolved_result` has no durable finalization acknowledgment. Implement together only in a separately bounded lifecycle milestone. |
| R9-6 wider native/runtime/envelope tables | Missing coverage remains beyond R10-1. The valid `zero=True`/`skip=True` helper variants still have no collected invocation. Existing semantic algorithm and numerical first-failure cases remain credited. No new semantic assignment defect was found. |
| Real worker progression | Missing evidence: controller success fabricates 510 rows before a trivial child exits (`run_controller:394–405`). The actual segment fixture at 480–528 covers three first failures. It does not establish successful first publication before frame 62, actual 510 order/340–170 split, reverified reuse, or later failure preserving first evidence. |
| Admission/registration/reservation races and replay | Canonical request comparisons, lock-based reservation and generic concurrency tests exist. The full applicable-boundary, synchronized S1 contender and continuation/consumed replay matrices remain unverified; absence of those tests alone is not evidence of duplicate execution. |
| Typed lifecycle events | `lifecycle:262–269` principally checks temporary/start event order; it does not establish typed path/cache/PID/PGID/reservation-reference semantics. Keep that intended-boundary review and mutation coverage open. Do not claim the entire lifecycle is validated by event order. |

## Recommended next CPU scope

Recommend **R10-1** plus the narrow **R10-2** compatibility correction. This
closes an independently testable result contract while preserving the receipt
milestone. It is deliberately a partial R9-6 milestone, not completion of every
Plan 036 table or any live readiness gate.

1. Add small shared numerical envelope checks in `s1_evidence.py`. Apply row
   checks when a row is semantically qualified and result checks through the
   actual terminal result guard. Preserve the distinction between structurally
   produced evidence and qualified evidence: a serialized row that fails a
   new numerical qualification must still be representable as produced.
2. Require row duration and singleton group size, result native total and peak
   bytes, and the local consistency rules described in R10-1. Use existing
   configuration for the byte ceiling. Plan must specify a small explicit
   floating accumulation tolerance derived from serialization/arithmetic
   behavior, with inside/outside cases; do not introduce scientific thresholds.
   Apply the same local envelope check at recovered-result resolution as
   needed, without adding a new recursive evidence scan or changing clocks.
3. Upgrade existing positive serialized row/controller fixtures to contain the
   actual stage fields. New collected literal cases start from a positive
   fixture accepted by real guards, mutate one target field, and assert the
   intended numerical guard. Cover missing, boolean, string/null, nonfinite,
   negative, non-integer byte/group values, wrong group size, allocated greater
   than reserved, configured-cap excess, and inconsistent native/group sums.
   Include valid zero and a nonzero consistent case. Keep existing row/runtime/
   membership assertions; rehash outer records where required to reach the
   intended inner guard. Do not fake qualification or result acceptance.
4. Fix declaration lookup under the retained direct script entrypoints for the
   six affected suites. Add a bounded collected regression that exercises
   script behavior without hardcoded callback expectations derived from
   observed output. Avoid altering the prescribed aggregate launcher or
   weakening AST/typed receipt checks.
5. Run a fresh final nine-suite aggregate against final source/declarations.
   Save immutable v2 inner/outer/wrapper evidence and independently reconcile
   actual tool completion, source membership, methods, typed callbacks and
   preservation. Counts are computed from final source, not fixed at 157/213.
   Report numerical-envelope milestone completion separately from wider R9-6,
   implementation acceptance, live admission and objective completion.

Allowed source scope should be `s1_evidence.py`, the minimal
`s1_recovery.resolved_result` integration if required, the six affected tests,
and new run artifacts. Retain the existing stage emission format. Any narrow
fixture/capture support must be named in Plan before dispatch. No supervisor,
ledger, helper-process, scientific algorithm or configuration overhaul belongs
to this milestone. A newly exposed unrelated failure is a handoff finding,
not authority to absorb another package.

Recommend a **new plan-specific 1,800 wall-second allocation**, starting before
implementation inspection; reserve its final **180 seconds** for evidence and
stop execution/refinement at 1,620 seconds. At most **three focused diagnostic
invocations**, each **120 seconds**, and **two complete aggregates**, each
**300 seconds**. Their full timeout must fit before the cutoff. The second
aggregate requires a source change or recorded concrete concern that invalidates
the first, not routine repetition. Suites and any direct-script subprocesses
run serially, native/helper pools are one thread, and the whole owned workload
stays within **eight CPU workers**. Preserve each attempted invocation, including
discovery failures; permission retries obey AGENTS.md and consume wall time and
an additional invocation if a new test process launches.

This allocation uses the skill's standing approval once finalized by Plan;
historical time/attempts are neither reset nor reused. It authorizes zero GPU
attempts/evaluations, zero live controller or ledger API calls/mutations, zero
production job creation, zero setup/download/smoke jobs and zero scientific
reruns. The single eventual calibration attempt / 3,600 GPU-second ceiling and
all original cumulative/resource limits remain unchanged. Main should reconcile
the new plan with applicable remaining ceilings before dispatch.

## Bookkeeping and criteria handoff

Correction-007 and validation-008 remain immutable checkpoint evidence. Main
has preserved the old status bytes in `s1-recovery-status-implement-009.md` and
recorded the later transition in `s1-recovery-bookkeeping-transition-post-009.json`.
That record's old/new hashes match the actual preserved/current bytes. Its
schema is `s1-status-transition/v1`, while production `preservation:195`
requires `plan034-s1-bookkeeping-transition/v1`. The next correction must
preserve post-009 unchanged and add a canonical-schema transition carrying the
same actual old/new records and linking the post-009 evidence. Appending post-009
directly to `bookkeeping_transitions` would be rejected. Carry subsequent main
status transitions forward in the same append-only manner. This is preparation
for a future current binding, not a frozen scientific-byte failure.

| Criterion | Assessment |
| --- | --- |
| S1-1 | **met**: amendment/native/S0 parents and semantic implementation remain bound and unchanged; final current-source aggregate retains the semantic assertions. No live semantic output is claimed. |
| S1-2 | **not met**: receipt core is implemented, but R9-2–R9-6 and full matrices remain; no production authorization/registration is present. R10-1/R10-2 advance this prerequisite without completing it. |
| S1-3 | **not met**: no recovery reservation or calibration result/failure exists. Numerical evidence, trusted clocks, progress and lifecycle work are prerequisites. |
| S1-4 | **met**: fresh frozen-record and ledger-byte/chain reconciliation agrees; only current bookkeeping and new review evidence change. Historical unavailable timing/status evidence and P31-5 remain limitations. |

No stop condition was encountered. The next stage is a fresh PLAN for the bounded
scope above. Finishing this review or the prior local commit does not complete
the active objective.
