# Iteration 12 REVIEW — Preserve clock acceptance and reduce repeated declaration parsing

The trusted reservation-clock milestone in commit **422b216** is supported by
current source and the saved passing aggregate. Preserve the completed receipt,
numerical-envelope, direct-script and clock milestones. Strict **Plan 041
acceptance remains false** for its two documented procedural exceptions.
S1 recovery admission remains **not ready**.

Recommend **R12-1: bounded reuse of static declaration parsing for identical
source text**, a small CPU validation prerequisite before R9-2 helper bounds.
This keeps the existing 120-second diagnostic and 300-second aggregate caps,
all real admission/evidence guards and the full substantive test collection.
Do not start the larger helper/progress/finalization changes in this milestone.

This direct REVIEW follows the continuous-improvement-loop skill and AGENTS.md.
It read the objective, status, assessment-025, review-011, Plan 041, applicable
Plan 031/036 constraints, current source/tests and saved validation/audit/launch/
timing/staged-check evidence. No tests, diagnostics, production controller or
ledger APIs, GPU/device operations, models, setup/download/smoke jobs, source
edits, status edits, git writes or delegation occurred. Inspection used
standard-library file/hash/JSON/AST and ledger bytes. Only this review and
[assessment-026-review.json](assessment-026-review.json) are created; main owns
status transitions and commits.

## Independent reconciliation

The detailed read-only reconciliation is embedded in assessment-026. It supports:

- All **75** current source/config/test records match validation-010 and the
  inner/outer aggregate's four source snapshots.
- AST collection matches **169 methods**, **37 parameterized methods** and
  **426 declared typed callbacks**, in the saved executed order. Every method
  and callback passed; failures/errors/skips/discovery errors are zero.
- Aggregate-011-002 records actual exit 0, completed wait, no timeout and
  **258.0717323209974 seconds**. Exact stdin, runner, capture, interpreter,
  environment, inner/outer logs and the independent tool-completion observation
  are bound to the matching bytes. All six direct-script children passed.
  This REVIEW reconciles saved process evidence; it did not rerun or independently
  observe that historical process.
- All **38** frozen records and the original ledger match. The ledger retains
  **447 events**, **332,437 bytes**, SHA-256
  2a0f66e38911b0ed029eb9dd0cf4bbd5da4a3b67abb577fbfe9ad67e6a888990,
  and chain head
  00cab019d73b6a3205f676b54cfb2f745f492fa5cca5c69b4567087cea62172b.
  There is no S1 recovery event. Saved matching ledger evidence retains no active
  job, 30 historical GPU attempts, 4,374.044265462899 elapsed GPU seconds and
  zero reserved. Original events 250, 255 and 256 remain preserved.
- There are no uncommitted source/test/config/plan changes. Main's pending
  bookkeeping artifacts are the actual postcommit REVIEW transition and snapshots.

The clock source now derives effective T, cleanup C, total D and work W from the
actual reserve; explicit authority resolution covers worker bootstrap, helpers,
acceptance and historical resolution. The first-result path verifies persisted
bytes and observes the work clock after qualification/publication/reuse;
the segment loop gates the next input before loading it. The new literal tests
cover real full/reduced reservation authority, typed/time mutations, failure
preservation, bootstrap, actual first-row publication barriers and coherently
rebound historical mutations. No new defect in that completed narrow milestone
was established by this inspection.

The raw S1_CLOCK_BARRIER completion_observation is the final controlled test
observation after invocation/cleanup. In the pre_input case it reaches W after
earlier successful publication; it is not a universal first-publication timestamp.
The real wrapped operations, qualification observations, publication records
and loader/adapter assertions support the intended barrier. Short segment cases
still do not establish complete 510-row worker progression.

Preserve these historical dispositions:

1. Diagnostic-011-001 launched after AST/prelaunch preparation failed and has no
   prospective launch note. Its retrospective note and actual timestamps remain
   truthful; no backdated record can repair it.
2. Diagnostic-011-002's pass-only synthetic worker inherited the former
   OMP/OpenBLAS value 4. Final supervisor transport enforces all four thread
   variables at 1 and has a real disposable-reservation assertion. The prior
   violation remains a limitation; final behavior does not erase it.
3. All three focused invocations failed; aggregate-011-001 failed one old
   supervisor fixture. Only aggregate-011-002 supports the current passing source.
4. Staged-review-011's full staged whitespace check exited **2**, solely for
   four findings in immutable failed/partial diagnostic raw logs. Its scoped
   source/document check exited **0**. Preserve raw bytes and both results.
5. Historical P31-5 and unavailable older status/inspection-inclusive timing
   evidence remain unclosed.

Plan 041 consumed all three focused and both aggregate invocations. Its timing
record ends at 1,861.1947769800026 seconds of 2,400; unused wall time grants no
new invocation. Its allocation must not be reused.

Correction-009's endpoint is the frozen IMPLEMENT status, now durably preserved
as s1-recovery-status-implement-011.md (985 bytes, SHA-256 664012df…).
The canonical [post-011 transition](s1-recovery-bookkeeping-transition-post-011.json)
joins that exact endpoint to s1-recovery-status-review-012.md (912 bytes,
SHA-256 68d0742a…). Both snapshot paths are durable. A successor correction can
append this existing transition directly, followed by actual PLAN/IMPLEMENT
changes; it needs no replacement of the post-011 record. Keep correction-009,
validation-010 and all historical snapshots immutable.

## Concrete next finding and scope

**R12-1 — Repeated exact-source parsing consumes avoidable validation work
(S1-2/S1-3 prerequisite; preserves S1-1/S1-4).**

The current complete aggregate leaves only **41.9282676790026 seconds** below
the hard 300-second capture limit. The recovery suite uses
**252.30142017400067 seconds**. These are measured suite totals, not per-method
profiling; this review does not claim that parsing accounts for all of that time.

Source inspection establishes an avoidable repeated operation:
s1_validation_contract.collection (lines 125–138) rereads and fully parses all
nine suite texts on every call. parse_suite (lines 62–121) performs multiple AST
walks and typed declaration checks for every unchanged input. ReceiptFixture
reconstructs this collection (recovery tests lines 128–129), and each real
validate_inner invocation collects it again (contract line 218).
ReceiptContractTests creates and validates a positive graph for each mutation;
admission/registration/reservation/acceptance fixtures also invoke those real
guards repeatedly. Source text stays unchanged within a prescribed invocation.
The exact total cost and savings must be measured by implementation evidence.

The next unused plan is currently **Plan 042**. Finalize this narrow change:

1. Factor the existing pure text-to-methods/declarations parse into a private,
   bounded cache keyed by the **entire exact source text and module name**.
   A 16-entry LRU is sufficient for nine suites plus small fixture churn.
   Cache successful parse results only. Preserve all parser validation and
   rejection behavior.
2. Keep public parse_suite behavior and output shapes. Return independent
   mutable copies of successful cached results, or use an immutable internal
   representation and reconstruct fresh results. Callers must never be able to
   poison the cache by editing nested parameter dictionaries/lists.
3. collection must still read every current suite file on every call.
   Never key authority by pathname, mtime, size or a remembered hash alone.
   A same-path/same-size/same-mtime source edit must be parsed and validated.
   Do not cache source membership, file records, strict_record, sources_check,
   receipts/wrapper results, canonical admission, ledger state, reservation
   checks, row/runtime checks or historical resolution.
4. Limit production edits to s1_validation_contract.py. Limit test edits to
   a small literal DeclarationCacheTests class in the recovery suite.
   s1_validation_runner.py may change only its focused selector to that class.
   Keep capture.py, execution schema/caps, aggregate launcher/order, environment,
   source membership algorithm and existing methods/callbacks/assertions intact.
   No fixture bypasses, reduced image sizes, omitted 510-row checks, relaxed
   mutation assertions or per-suite splitting are part of this milestone.
5. Keep the mechanism model-free and process-local. It introduces no child,
   thread, persistent cache file, external dependency or import of test modules.
   Do not share parsed authority across spawned processes or persist it between
   source versions.

The optimization is justified as a small prerequisite to fitting remaining
required validation under the existing cap. It closes no live-monitor, progress
or finalization defect. If measured savings are small, retain that result
truthfully and make a later explicit capacity decision. Do not silently raise
the cap or add performance probes after consuming this plan's invocations.

Required collected validation should be cheap and call the real parser:

| Boundary | Required evidence |
| --- | --- |
| Work reuse | Spy on the real ast.parse operation: repeated identical valid text/module parses once; returning the exact original collection and typed values. A spy wraps real parsing and never supplies a fabricated pass. |
| Exact key | Changed text under one module is parsed; changed module under identical text cannot reuse an incompatible declaration. Include same-size text changes and restored original text. |
| Fresh file reads | Build nine tiny real suite files in a disposable fixture root. Calling real collection, changing one file while preserving its size and mtime, and calling collection again must observe the change or reject its invalid declaration. Read failure/deletion must still fail after a warm parse. |
| Mutation isolation | Mutating returned method lists, declaration mappings, case lists and nested parameter dictionaries cannot affect later results or another call; preserve bool/int/float/null/string distinctions. |
| Invalid source | Repeated malformed or semantically invalid declaration inputs are rejected through real guards; a corrected text subsequently succeeds. Existing complete adversarial declaration and receipt matrices still execute in the aggregate. |
| Bound/eviction | More than 16 distinct valid text/module keys do not grow the cache beyond its declared maximum; an evicted input is safely reparsed. Separate modules cannot exchange results. |
| Integration | One real complete current-source aggregate retains all previous 169 methods/426 callbacks and adds exactly the AST-derived new cases. No skipped/removed declarations or guard bypass. Record raw outer/suite elapsed and headroom against the prior 258.071732-second outer / 252.301420-second recovery values. |

Use small pure fixtures for cache cases, not a fresh full controller or 510-row
fixture per mutation. Preserve existing controller/semantic/clock tests in the
aggregate. A structural reduction in repeated real parsing is the deterministic
performance evidence; a faster saved full aggregate is observed timing, not a
new scientific threshold. Report actual savings and headroom without promising
capacity for the entire remaining plan.

## New resources and handoff

Recommend a **new 1,800 wall-second IMPLEMENT allocation**, beginning with UTC
and monotonic timestamps before inspection. Execution/refinement cutoff is
**1,620 seconds**; reserve the last **180 seconds** for evidence/handoff.
Allow at most **three focused invocations of 120 seconds** and **two full
aggregates of 300 seconds**, inside that one wall allocation.

Before every launch, durably record actual elapsed, requested timeout and
remaining attempt/execution allocations. The entire requested timeout must fit
before 1,620. Preserve capacity for one full final aggregate: a 120-second
diagnostic preceding it requires at least 420 execution seconds remaining.
Do not launch if prelaunch preparation failed. An optional second aggregate
requires a saved source change or concrete concern invalidating the first;
do not repeat an unchanged passing aggregate for performance measurement.
Every process launch, including failed discovery, consumes an invocation.
Permission-retry time counts; a newly launched test process consumes an invocation.

Use at most **eight CPU workers including owned processes and native/helper
threads**, serial suites and all four thread settings at 1. Retain the six
collected direct-script children, serial and each at most 10 execution + 2
cleanup seconds, 72 seconds total inside the aggregate. No standalone probes.
Allocate **zero** GPU/device attempts, model evaluations, production controller
calls/dry runs, production ledger API calls/mutations, production job directories,
setup/download/smoke jobs or scientific reruns. Only existing disposable fixture
API calls inside collected CPU tests remain permitted.

The skill's standing approval covers these new saved plan allocations after
main compares them with unchanged applicable ceilings. It does not reset Plan
041 or any historical consumption, launch a live recovery, or relax scientific
gates. Apply the repository's one safe permission retry and stop/report rules;
main retains staging/commit ownership.

Use unchanged exact nine-suite launcher/stdin/order and capture/receipt contract.
Derive final source/method/typed-callback membership from AST, not historic counts.
Bind complete pre/post source snapshots, exact invocation/interpreter/environment,
closed raw logs, actual process wait/exit and independent tool completion.
Source edits after a pass invalidate that pass. Independently reconcile final
evidence without simply trusting the production validator.

Main preserves actual current REVIEW and subsequent PLAN/IMPLEMENT snapshots.
The next correction is currently **correction-010**; append the existing canonical
post-011 transition and actual subsequent status transitions while preserving the
full predecessor prefix, 38 frozen records and 447-event ledger. The next wrapper,
audit and implementation review are currently validation-011, audit-011 and
implementation-review-010; use iteration-012 launch/timing/process/staged records.
Check vacancy before creation. Never repair history by overwriting old artifacts.
Main inspects, stages explicit task paths, records full/scoped staged checks and
commits the validated milestone, then continues fresh REVIEW.

Acceptance requires correct bounded parse reuse, intact authoritative fresh reads
and rejection/mutation isolation, and a fresh complete passing aggregate with
independent preservation audit within 300 seconds. Keep cache-milestone, plan,
whole-implementation, live-readiness and objective flags separate. The last three
remain false.

## Remaining gates and criteria

| Gate | Disposition and next dependency |
| --- | --- |
| Receipt / numerical / scripts / reservation clock | Completed narrow milestones remain supported. Preserve all current tests and history. |
| R9-2 helper bounds and fresh samples | Next production milestone after R12-1. Synchronous Process.start and framed Connection.recv remain at supervisor lines 104/122; ready handling precedes sample timeout at lines 246–265; validate_sample has no sample-time contract. Plan a fixed bounded-ready helper set, nonblocking complete transport, real owned startup/partial-frame/descendant failures and fresh samples within Plan 036 limits. |
| R9-4 durable progress | reconcile_rows lines 229–279 keeps verified identities locally; monitored_call returns only after a later sample. An interrupted helper or failed final sample loses already verified progress. Persist incremental bounded summaries before W and use only the last verified summary during cleanup. |
| R9-5 finalization and remaining R9-3 ordering | supervisor lines 414–497 still reduce primary exceptions to text, overwrite classification, clean up without continuous sampling, measure elapsed before final reap and directly call ledger.finish. Implement structured primary/ordered secondary failures, C/2+C/4+C/4 phases, monitored conservative final charge and acknowledgment together. Full first/result/native/receipt/finish/acknowledgment consistency remains open. |
| Native/runtime/first matrices | Remaining A1–A3 mutations, actual zero-detection and oversized-box cases remain unverified. Existing numerical and semantic evidence remains credited; no new S0 assignment defect was found. |
| Full worker progression | Controller run_controller synthesizes 510 row entries; actual segment tests stop around the first/second input. Require a future real successful stages.segment path through all 510 identities and exact 340/170 split, with publication/reuse/later-failure preservation. |
| Applicable boundaries / contention / replay / lifecycle | Full synchronized S1 contenders, continuation/consumed replay, dependency matrix and typed path/cache/PID/PGID/reservation-reference lifecycle coverage remain open. Missing tests do not alone establish duplicate execution. |
| Current production binding and recovery | Only after complete CPU acceptance, produce current authorization/registration and review the separately authorized single recovery. No live work in this next plan. |

**S1-1: met** — source-bound amendment/native/S0 preservation and the current
complete CPU semantic evidence remain supported.
**S1-2: not met** — helper/progress/finalization/matrix prerequisites and current
production authorization/registration are still open.
**S1-3: not met** — no live recovery reservation or terminal outcome exists.
**S1-4: met** — frozen evidence/ledger and the actual durable status lineage match.

The later calibration remains one attempt at
min(3600, 93600 - gpu_elapsed_seconds - gpu_reserved_seconds) > 0, with cleanup
min(30, effective_seconds/4) inside it; reservation consumes the attempt even
without launch. Preserve one exclusive GPU group, 22 GiB device memory, eight
CPU workers, 150 GiB artifacts, 60 GiB downloads and existing 57,600-second
preparation/setup ceilings. Reconstruction needs separate later authorization.
No stop condition was encountered. Next stage: fresh direct PLAN.
