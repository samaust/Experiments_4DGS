# Iteration 11 REVIEW — Bind first-result qualification to the reservation clock

Plan 040's numerical-envelope and direct-script milestones are supported by the
committed source and saved execution evidence. Preserve those completed fixes
and the Plan 039 receipt milestone. Recommend one new CPU milestone: **R11-1,
trusted first-result reservation context and the work-deadline advancement
barrier**, addressing the first-result portion of R9-3. S1 recovery admission is
still **not ready**. Full timing/accounting acceptance also depends on R9-5;
do not mark that package complete through this narrower change.

This direct REVIEW follows the continuous-improvement-loop skill and AGENTS.md.
It read the objective, current status, assessment-022, review-010, Plan 040,
relevant inherited Plan 031/032/034/035/036 requirements, current source/tests,
and saved validation/audit/implementation evidence. No tests, diagnostics,
production controller or ledger APIs, GPU/device operations, models,
setup/download/smoke jobs, source edits, git writes or delegation occurred.
Standard-library file/hash/JSON/AST inspection was read-only. Only this review
and [assessment-023-review.json](assessment-023-review.json) are created; main
owns status transitions and commits.

## Reconciled milestone and preservation

HEAD is `91b13b5fb8ce460c065f6f8fa9972d98c43437ad`, following the receipt
milestone `44686a2`. There is no source/test/configuration/plan difference from
HEAD. Fresh read-only reconciliation established:

- All **74** current source/config/test records match validation-009 and the
  inner/outer aggregate's four source snapshots.
- Static AST collection matches **162 methods**, **30 parameterized methods**
  and **310 declared typed callbacks**, in the saved executed order. Every
  method and callback has passing status; counters report zero failures,
  errors, skips and discovery errors.
- Aggregate-010-001's saved outer capture reports actual return code 0,
  completed wait, no timeout, and **182.62408705499547 seconds**. Its raw
  stdin/runner/capture/interpreter/log/receipt bindings and the separate process
  observation match current bytes. Audit-009 remains a matching saved passing
  audit. This review did not rerun the aggregate or independently observe that
  historical process.
- All **38** frozen records and the original ledger match. The ledger has
  **447 events**, **332,437 bytes**, SHA-256
  `2a0f66e38911b0ed029eb9dd0cf4bbd5da4a3b67abb577fbfe9ad67e6a888990`, and intact
  chain head `00cab019d73b6a3205f676b54cfb2f745f492fa5cca5c69b4567087cea62172b`.
  There is no active job or S1 recovery event. Historical GPU accounting is
  30 attempts / 4,374.044265462899 seconds / zero reserved. Original failed
  finishes 250/255 and account/skipped event 256 remain unchanged.

`s1_evidence.py:250–300,408–424` and `s1_recovery.py:402–404` contain the local
numerical guards at row, terminal and recovered-result boundaries. The six
suites retain canonical literal-table lookup for direct script execution.
The saved current-source aggregate and audit support the declared numerical
matrices and six script children. No new defect was established in those fixes.
Keep the three failed/partial focused attempts as failed/partial evidence;
only the final aggregate supports completed acceptance.

Plan 040 consumed three focused invocations and one aggregate, with recorded
implementation elapsed 1,094.9941463669966 seconds of its 1,800-second allocation.
That plan is complete; its unused time or aggregate slot does not fund new work.
Recommend a separate allocation below without resetting historical consumption.

The full staged whitespace check in **staged-review-010** exited **2**, with
four findings exclusively in immutable failed/partial diagnostic logs. Its
scoped source/document check exited 0. Preserve that disposition and all raw
bytes. Validation-009's earlier unstaged check is not a clean full staged check.

Correction-008 correctly ends at frozen IMPLEMENT status `dd088a81…` (969 bytes),
now preserved as `s1-recovery-status-implement-010.md`. The canonical
`s1-recovery-bookkeeping-transition-post-010.json` joins it to current REVIEW
status `b9d5a779…` (860 bytes). Both snapshots and the transition match. Thus
source-bound milestone evidence remains valid, while a new current admission
binding must append this transition and subsequent real PLAN/IMPLEMENT status
transitions in a successor correction. Do not rewrite correction-008,
validation-009 or the staged review.

## Concrete clock finding

**R11-1 — First-result qualification lacks trusted effective clock context and
a completion-time advancement barrier (R9-3; S1-2/S1-3 prerequisites).** This is
a source contract gap, not an inference from missing tests:

1. `s1_evidence.elapsed:25–30` reads only `VIPE_RESERVATION_START`; its request
   argument is unused. `supervisor.supervise:335` adds this variable only to the
   worker's Popen environment. CPU reconciliation helpers inherit the controller
   environment, although their operation already carries the real reservation.
   `prepare_terminal_evidence:487–488` discards that clock when calling
   `reconcile_first`. The missing-record branch at `s1_evidence:67–68` may
   therefore publish `not_reached` with null elapsed and return its file record
   without verifying the new failure envelope.
2. Failure and passed-envelope checks at `s1_evidence:80,456` still compare
   elapsed with **3,600**, although `Ledger.reserve:128–143` can return a lower
   effective allocation. Neither first-result envelope binds the reservation
   event, boot identity, effective seconds or derived work deadline. The
   recovered-result check at `s1_recovery:405–406` supplies only a later partial
   inequality; it cannot stop the worker advancing with a first pass that used
   the wrong allocation.
3. `first_record:39–44` samples elapsed before `verify_first` performs runtime
   and row qualification, and before immutable publication/hash at `:57–60`.
   Existing-pass reuse also performs qualification without a current deadline
   check. `stages.segment:191–192` then returns to its input loop with no
   post-publication clock check. A pre-work-deadline timestamp alone does not
   establish that expensive qualification/publication finished before the work
   deadline or before frame 62 was loaded.

The saved reduced-budget cases at recovery tests `:374–382` assert reserved
seconds. The controller positive passes only the old start environment value
to a fabricated first result (`:385–407`). The real segment cases (`:480–528`)
cover three first failures. These are useful existing checks; none establishes
the missing trusted-context and publication-deadline behavior. No new runtime
probe was performed in REVIEW.

## Recommended bounded implementation

Create the next unused plan (currently **Plan 041**) for R11-1 only. Retain the
existing helper architecture during this clock milestone; its boundedness and
finalization defects remain explicit. Plan should finalize one clock protocol
and its authority/transport choices before implementation, with these required
outcomes:

1. Derive a small typed clock context from the **captured, admitted reservation**:
   reservation sequence/hash, job/request binding, boot identity, monotonic
   start, effective seconds `T`, cleanup reserve `C=min(30,T/4)`, total deadline
   `D=start+T`, and work deadline `W=D-C`. Compare supplied context with the
   appropriate trusted active or historical reservation. Worker environment
   values may transport the context; they cannot independently supply its
   authority. Keep runtime clock context outside the deterministic canonical
   request. No extra attempt, ledger allocation or model work is needed.
2. Pass context explicitly through worker bootstrap/segment, failure evidence,
   first-result construction/verification/reconciliation, and helper acceptance.
   Bootstrap it before model setup so pre-result failures can carry the same
   reservation identity. Existing accept/reconcile helper arguments already
   carry the captured reservation; use it. There must be no S1 fallback to a
   bare environment start, null elapsed or a default 3,600-second window.
3. Validate exact numeric types excluding bool, finite/nonnegative start and
   observations, positive bounded T, same live boot, and exact derived deadlines.
   Passed first evidence must lie strictly before W; failed/not-reached evidence
   may describe cleanup through D and never permits advancement. Preserve a
   verified worker failure's original elapsed/error/phase. Missing first evidence
   must use supervisor context and a verified minimal envelope. If trusted
   context is unavailable or an observation is late, preserve the actual error
   and time as unqualified evidence; never clip, backdate or claim verification.
4. Check the live deadline after runtime/row qualification, after immutable first
   publication and hash/read-back, on identical-pass reuse, and immediately
   before the next input is loaded. A write/check crossing W blocks advancement.
   Re-read/reverify the published pass through real guards and preserve it on a
   later failure. Distinguish the timestamp stored during record construction
   from the observation that publication completed; do not label a pre-write
   timestamp as a post-write completion time. Failed/not-reached/stale/conflicting
   evidence cannot be promoted to a pass.
5. Carry the same reservation identity into acceptance and historical resolution
   so a coherently rehashed wrong-start/boot/allocation first record is rejected
   at the intended guard. Historical reads validate the recorded boot against
   their recorded reservation; they must not compare an old monotonic timestamp
   with today's boot/clock. Preserve already implemented numerical envelopes.
   Shared local consistency may compare first/native timing with trustworthy
   enclosing observations, but do not assume `first_elapsed <= native_total`:
   loading and first qualification legitimately lie outside native inference.
   Full receipt/finish/acknowledgment ordering and conservative final charges
   remain R9-5 work.

Keep new clock helpers small and model-free. Candidate source scope is
`s1_evidence.py`, `s1_recovery.py`, `s1_cpu_helper.py`, `supervisor.py`,
`stages.py`, the worker entrypoint and, only for narrow signature plumbing,
`execution.py`; a dedicated `s1_clock.py` is reasonable if it clarifies the
single contract. Restrict tests to the recovery/supervisor suites and any
explicitly necessary worker-entry fixture. A diagnostic-selector adjustment is
permitted only to select the new collected clock class. No scientific/backend
algorithm, configuration, receipt-contract or generic ledger-accounting change
is indicated by this finding. Plan should reduce this candidate set to its
actual required edits.

Required collected coverage starts from positives accepted by real guards:

| Boundary | Required evidence |
| --- | --- |
| Typed context and phase clocks | Full and reduced allocations; missing/invalid/bool/nonfinite/negative context values; wrong reservation/start/boot/T/W/D; just before/at/after W for passes and at/after D for failure evidence; live versus historical verification distinction. |
| Failure reconciliation | Controller environment without the old start variable; missing first evidence receives finite actual supervisor-relative time and matching reservation; verified failed/not-reached evidence keeps exact bytes/time/error/phase; invalid or unavailable context never becomes a verified null-clock record. |
| First publication barrier | Real segment with a fake backend/device/runtime boundary and real serialized first-row qualification/publication. Clock crossing during qualification, publication, read-back, or verified reuse prevents loading frame 62 or a second adapter call. A valid before-W first pass is durably visible and reverified before the second input. |
| Preservation and acceptance | Identical pass reuse succeeds only under matching context and a valid live deadline; stale/conflicting/failed/not-reached records block advancement; later-row failure preserves the earlier first-result/raw hashes; coherently rebound first-record clock mutations reach acceptance/resolution clock guards. |

Use literal typed case declarations, exact error/boundary assertions and fake
clock values instead of real sleeps. Keep external model/device/clock capture
patches explicit; do not patch row/runtime/first/result acceptance into passing.
A short actual segment fixture may stop deliberately at the second input to
prove the barrier. That fixture does **not** close full 510-row progression.
Do not fabricate the 510 rows and count that as worker execution. The complete
ordered worker run remains a later independent acceptance milestone.

## Resources, validation and handoff

Recommend a **new plan-specific 2,400 wall-second IMPLEMENT allocation**, starting
before inspection, with the last **240 seconds** reserved for evidence/handoff
and execution cutoff at **2,160 seconds**. The explicit context crosses worker,
helper and historical evidence boundaries, so this allows careful integration
without the prior plan's short diagnostic deadline forcing broad fixture runs.
Allow at most **three focused invocations of 180 seconds each** and **two full
aggregates of 360 seconds each**, all inside that one wall allocation. Reserve
one complete final aggregate before optional refinement. A second aggregate
requires a saved source change or concrete concern invalidating the first;
never repeat an unchanged pass routinely. The full timeout must fit before the
cutoff; each launch, including discovery failure, consumes an invocation.

Use at most **eight CPU workers including native/helper threads**, serial suites
and one-thread native/helper pools. Retain the existing bounded six direct-script
children inside prescribed invocations: serial, at most ten seconds execution
plus two seconds cleanup each, 72 seconds total, with no standalone probes or
recursion. Allocate **zero** GPU/device attempts, model evaluations, production
controller calls/dry runs, production ledger API calls/mutations, production job
directories, setup/download/smoke jobs or scientific reruns. Disposable fixture
controller/ledger calls inside collected CPU tests are the only execution of
those APIs in this milestone. Apply AGENTS.md's one safe permission retry/stop
rules; count a newly launched test invocation and its elapsed time.

The skill's standing approval covers a new saved plan allocation when main checks
it against applicable ceilings. This review does not launch implementation or
reuse any completed plan's resources. Existing scientific ceilings and the sole
future calibration attempt remain unchanged; there is no new model/evaluation
allocation.

Keep the exact nine-suite launcher/stdin/order and current capture/receipt
contracts. Derive final source/method/callback membership from AST, not historical
counts. Bind complete pre/post source snapshots, actual subprocess completion,
closed raw logs and current source to a new validation wrapper. Independently
reconcile that evidence using a read-only audit. Preserve every failed/partial
attempt and truthful staged versus unstaged diff-check scope. Source edits after
the passing aggregate invalidate it. Focused passes alone do not complete the
plan.

Append the canonical post-010 transition and main's actual REVIEW/PLAN/IMPLEMENT
snapshot changes into the next unused correction, carrying the existing lineage
and 38 frozen records/447-event ledger unchanged. Main must snapshot the current
REVIEW status before changing it because the post-010 new snapshot currently
points to `status.md`. Save new validation/audit/implementation-review/preparation/
timing/assessment artifacts; never overwrite the current checkpoint. Main owns
inspection, task-only staging and local commit, then continues fresh REVIEW.

Acceptance for this next plan is the clock/context/barrier milestone plus a fresh
passing complete aggregate and preservation audit. Use distinct flags for that
milestone, plan acceptance, whole implementation acceptance, live readiness and
objective completion. The final three stay false while the remaining gates are
open.

## Remaining gates and criteria

| Gate | Disposition after this review |
| --- | --- |
| R9-1 receipts; R10-1 numerical envelopes; R10-2 scripts | Completed milestones remain supported. Do not repeat them. |
| R9-2 helper startup/transport/sample freshness | Concrete gaps remain: synchronous `Process.start` and framed `Connection.recv` on the monitor path, per-operation helper creation, no sample-time contract, and ready handling before sample timeout (`supervisor:104,122,211–265`). Existing spawn/error/cleanup tests remain credited. |
| R9-3 clock/effective allocation | R11-1 is the recommended next subset. Full first/result/native/receipt/finish timing consistency must also be reconciled with later R9-5 finalization. |
| R9-4 incremental progress | Concrete gap remains: `reconcile_rows:179–237` holds verified progress locally, and `monitored_call` returns only after a final sample. Interruption or final-sample failure can discard verified progress; terminal fallback reports conservative zero lower bounds/unknown totals. Durable progress remains required. |
| R9-5 structured failures and finalization | Concrete gaps remain: primary exception reduced to text and later classifications overwrite it; cleanup lacks continuous sampling; elapsed precedes final reap and blocking `ledger.finish`; resolver has no finalization acknowledgment. Implement its reserve subdivision, monitoring, conservative charge and acknowledgment together. |
| Remaining A1/A2/A3 matrices | Missing coverage remains for native/runtime/first-envelope mutations, zero detections and skipped oversized boxes. No new S0 assignment defect was found. Numerical timing/memory coverage from Plan 040 is credited separately. |
| Actual 510-row worker progression | Unverified. Controller success synthesizes 510 rows; real segment currently has three first-failure cases. Next clock/barrier tests may advance part of this evidence but cannot establish the full exact 510 order and 340/170 split. |
| Applicable-boundary/race/replay matrices | Full synchronized S1 contender, continuation/consumed replay and applicable dependency coverage remain unverified. Existing canonical comparisons, reservation lock and generic concurrency tests do not prove every cell; missing tests alone do not demonstrate duplicate execution. |
| Typed lifecycle events | `lifecycle:262–269` principally checks temporary/start ordering. Complete typed path/cache/PID/PGID/reservation-reference semantics remain an intended-boundary source/test task. |

**S1-1 remains met** for its source-bound amendment/native/S0 preservation and
current CPU semantic assertions. **S1-4 remains met** for byte-preserved frozen
evidence/ledger and the actual canonical status transition. **S1-2 remains not
met** because CPU admission prerequisites and current production authorization/
registration are open. **S1-3 remains not met** because no calibration recovery
reservation or terminal result/failure exists.

Historical P31-5 and unavailable older status/inspection-inclusive timing
evidence remain explicit limitations. Only a later authorized DO after all CPU
gates close may consider the one `S1-calibration-recovery-001` attempt, at
`min(3600,93600-gpu_elapsed_seconds-gpu_reserved_seconds)>0`, with inclusive
cleanup reserve `min(30,effective_seconds/4)`. Reservation consumes the attempt
without launch. One exclusive GPU group, 22 GiB device memory, eight CPU
workers, 150 GiB artifacts, 60 GiB downloads and existing 57,600-second
preparation/setup ceilings remain. Reconstruction requires separate later
authorization. No stop condition was encountered in this REVIEW; next stage is
PLAN under the resumed loop.
