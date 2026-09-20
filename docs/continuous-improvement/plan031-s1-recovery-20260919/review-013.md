# Iteration 13 REVIEW — Bound the S1 helper session and resource samples

The Plan 042 declaration-cache milestone in **fdf3461** remains supported by
current committed source and its complete saved aggregate. Its outer elapsed
time is **206.6836401239998 seconds**, leaving **93.3163598760002 seconds** under
the unchanged 300-second capture cap. Proceed to a new CPU-only plan for
**R13-1: a fixed, ready helper session with bounded startup, complete transport,
and fresh correlated samples**, advancing the remaining **R9-2** prerequisite.
S1 admission is not ready. The objective remains incomplete.

This REVIEW follows AGENTS.md and the explicitly resumed
continuous-improvement-loop skill. It read the authoritative objective, status,
assessment-028, review-012, relevant Plans 031–042, current helper/supervisor/
evidence/test source, and the latest saved validation, audit and process records.
It used standard-library file/hash/JSON/AST inspection and read-only git. It ran
no tests, production controller or ledger APIs, GPU/device/model operations,
setup/download/smoke jobs or delegation. It changed no source, status or git
state. Its only repository additions are this review,
[assessment-029-review.json](assessment-029-review.json), and
[review observations](s1-recovery-review-observations-013.json).
Main retains status transitions and commit ownership.

## Reconciled evidence and its limits

The independent observation records **1,683 successful checks**. It does not
invoke the production validator or reuse its result as the only authority.

- All **75** current source/config/test records match validation-011, all four
  inner/outer source snapshots, and HEAD's corresponding file contents.
- Fresh AST inspection recovers **176 methods**, **37 parameterized methods**,
  and **426 exact typed callbacks** in the saved executed order. All pass with
  zero failures, errors, skips or discovery errors. All 169 previous methods
  and their 426 callback/result records remain preserved; the seven cache
  methods are the only additions. The previous-to-current source changes are
  exactly the contract, focused runner selector and recovery test file.
- The exact stdin, argv, interpreter, environment, current runner/capture
  snapshots and closed inner/outer raw logs agree. The saved aggregate records
  actual exit 0, completed wait and no timeout. All six direct-script children
  passed within their existing caps. The separate saved tool-completion record
  matches the execution record. This is reconciliation of historical execution;
  REVIEW did not independently observe or rerun that process.
- Recovery suite elapsed is **201.52797767700395 seconds**. The outer time is
  51.388092196997604 seconds lower than the prior accepted aggregate. That is
  one observed comparison, not a controlled causal cache speedup or a guarantee
  that all remaining work fits in the available headroom.
- All **38 frozen records** and the ledger remain exact. The ledger has
  **447 events**, **332,437 bytes**, SHA-256
  `2a0f66e38911b0ed029eb9dd0cf4bbd5da4a3b67abb577fbfe9ad67e6a888990`,
  and chain head
  `00cab019d73b6a3205f676b54cfb2f745f492fa5cca5c69b4567087cea62172b`.
  Independent chain/accounting inspection finds 30 historical GPU reservations,
  **4,374.044265462899 GPU seconds**, zero reserved and no active job. Original
  events 250, 255 and 256 match. No S1 recovery event exists.
- Correction-010 preserves its predecessor prefix and frozen records. Its
  IMPLEMENT endpoint is durably preserved as status-implement-012; canonical
  post-012 joins it to status-review-013 and the actual current status. Their
  hashes are respectively `b8fbcacf…` / 1,026 bytes and `123fe27d…` / 808 bytes.
  No unavailable historical snapshot has been invented.
- Plan 042's saved elapsed through final evidence is **720.2812564579945
  seconds** of 1,800. It consumed one focused and one aggregate invocation;
  both have matching prospective launch notes and completion records. That
  completed allocation is historical: its unused time/attempts are not the
  authority for the next plan.

Source inspection agrees with the accepted cache mechanism: a successful pure
parse is keyed by entire text plus module in a 16-entry LRU; the public wrapper
deep-copies results; collection still rereads each file. The focused cases and
complete aggregate support this narrow milestone. No new cache regression was
established by this review.

Preserve the existing distinctions. Strict Plan 041 acceptance remains **false**:
diagnostic-011-001 lacks a successful prospective note after failed preparation;
diagnostic-011-002's synthetic worker inherited the former OMP/OpenBLAS value 4.
Later corrected source and receipts cannot repair those historical actions.
Its three focused failures, failed first aggregate, and full staged whitespace
exit 2 on immutable raw logs remain recorded alongside the scoped check's exit
0. Historical P31-5 and unavailable older status/inspection-inclusive timing
evidence remain open. Clock-barrier completion observations are scoped to their
controlled invocation/cleanup; short segment cases do not prove 510-row worker
progression.

## Current R9-2 defects

These are source-grounded findings, not newly executed reproductions. Exact
supervisor/helper source hashes and the local Python 3.14 multiprocessing source
files used below are bound in the observation.

**Startup can occupy the monitor before its timeout loop resumes.**
`supervisor._Helper.__init__`, lines 99–110, constructs a spawned process and
calls synchronous `Process.start()` with the entire operation in its arguments.
`HelperLifecycle.start`, lines 173–177, calls that constructor synchronously.
Python's `BaseProcess.start` assigns `_popen` only after constructing it;
`popen_spawn_posix._launch` serializes preparation/arguments and writes them to
the child bootstrap pipe before returning. A deadline checked after this call
does not bound that serialization, bootstrap write, or the interval after an OS
child exists but before the outer Process object exposes it. Current ownership
assignment follows `start()`, and the child calls `setsid()` only after entering
the operation entry point. A partial startup must not be reported as cleaned up
merely because the parent has no returned PID.

**Readable transport can still block on an incomplete frame.**
`_Helper.poll`, lines 117–122, calls `connection.recv()` after `poll()`.
The installed Python connection implementation reads a frame header, then loops
until the entire advertised payload arrives, then unpickles it. Readability
only establishes some available input. A helper that writes a header or part
of a payload and stalls can hold the monitor inside `recv()`. Request submission
currently has the analogous bootstrap write path. Bounded receive alone will
not solve a new session implementation if it adds a blocking request `send()`
or unbounded result decoding to the monitor.

**There is no fixed ready helper set.**
`monitored_call`, lines 247–269, creates fresh sample and work helpers and
settles them per result. `s1_cpu_helper.entry`, lines 38–57, runs once and exits;
it has no separate readiness handshake or persistent request loop. Initial
sampling itself uses this one-shot monitor before reservation. Once a reserve
exists, all later phases can still trigger fresh startup. Repeated spawn is
also avoidable overhead, but this review makes no performance claim for its
replacement.

**Sample timing has no authority and timeout ordering admits a late ready path.**
`validate_sample`, lines 212–225, checks the required resource values and PIDs
but no acquisition interval, boot/session identity, request sequence or age.
`s1_cpu_helper.run` returns resource values without those fields. In
`monitored_call`, a ready sample is handled before the timeout branch, and the
`now` used for timeout came from before startup/poll/settlement. A sample that
becomes readable after its deadline can therefore be consumed without a fresh
receipt-time check. The code intends to require a sample after task completion,
but an untimed constant payload cannot prove that its measurement followed the
task. Preserve the already-correct strict value/PID checks, peak accumulation,
real worker-group context and foreign-PID rejection while adding time authority.

Current tests prove real ordinary spawn under the prescribed stdin launcher,
immediate startup exception handling, EOF, owned/foreign GPU PID cases and
ownership retention across controlled cleanup failures. They do not prove a
blocked start or incomplete pipe frame. The cleanup matrix substitutes a fake
helper; the descendant test creates a worker group separately from the spawned
helper. Both sets remain useful evidence for their stated boundaries. The next
tests must exercise actual helper children and their actual descendants.

## Recommended next implementation scope

The next unused plan number observed is **043**. Finalize R13-1 as one cohesive
CPU helper-session milestone. Map its acceptance to S1-2/S1-3 prerequisites and
preservation of S1-1/S1-4; passing it alone completes neither S1-2 nor S1-3.

1. **Create the fixed session before reservation.** Use one persistent work
   role and one persistent sample role, with a bounded ready handshake. Ready
   must identify the expected role, protocol/session, process start identity,
   owned process group and all four native-thread settings at 1. Reuse these
   roles across initial sampling, prelaunch, worker checks, acceptance,
   reconciliation and publication; do not restart a failed role during an
   allocated attempt. Keep at most one work request and one sample in flight.
   Give the session one explicit owner and lifetime; successful individual
   requests must not destroy the shared helpers.
2. **Make startup isolation a real design decision.** The plan must name the
   component that remains responsive while all helper startup work occurs and
   how it retains/signals a partially started child before readiness. A small
   independently owned bootstrap supervisor may be appropriate, but its own
   launch boundary must be included in the argument and tests. Moving an
   unchanged blocking `Process.start()` immediately before reserve, adding a
   readiness timeout after it, or abandoning an untracked starter thread is
   insufficient. Preserve spawn/importable entry points and avoid direct fork
   from the multithreaded controller. If any launcher/ownership boundary remains
   unbounded, record it explicitly and keep R9-2 incomplete. Do not redefine
   the start of the measured interval to exclude the blockage.
3. **Use complete, bounded request and response transport.** Define versioned
   small control envelopes, role/session identity, unique monotonic request
   numbers and a fixed frame-size bound justified against the real operation
   shapes. Bulk evidence stays in the existing verified artifact protocol.
   Use nonblocking incremental reads and writes with a bounded amount of work
   per monitor tick. Retain partial-frame state without blocking or treating it
   as completion. Reject oversized lengths before allocation, malformed frames,
   EOF mid-frame, duplicate/out-of-order/wrong-role/wrong-session replies and
   unsolicited data. Do not move arbitrary pickling, source/evidence parsing,
   hashing or recursive scans into the monitor. Plan must cover encoding and
   decoding costs as well as pipe readiness; a timeout around one read is not
   end-to-end bounded transport.
4. **Bind every sample to the measurement and request.** Capture a finite
   acquisition start/end in the helper immediately around the real sampling
   operation, together with the trusted session/boot and request sequence.
   The monitor records dispatch and complete-receipt monotonic times. Require
   `dispatch <= acquisition_start <= acquisition_end <= received`, correct
   identity/sequence, and receipt strictly before both the one-second sample
   deadline and the enclosing phase deadline. Validate all fields with exact
   primitive types and reject missing, bool, nonfinite, negative, reversed,
   future, stale, replayed or mismatched timing. Payload-supplied timestamps
   cannot override the helper-captured interval. Refresh `now` after complete
   receive and before acting; a ready message at/after its deadline fails.
   After observing task completion, request and accept a new sample whose
   acquisition begins after that observation before returning the task result.
   A previously in-flight sample cannot satisfy that final condition.
5. **Integrate ownership and failure cleanup for this session.** Fail before
   reserve on missing/late/invalid readiness or initial sample; no calibration
   attempt is consumed. After reserve, failure stops work and retains the
   existing consumed identity. Do not submit work at/after W or let sample
   polling suppress the parent deadline. Keep ticks at most 100 ms and each
   sample deadline at most `min(1 second, remaining phase time)`. Track owned
   helper descendants, TERM/KILL with bounded nonblocking reap, and distinguish
   an empty survivor list from confirmed cleanup. Retain ownership until the
   relevant children/group are accounted for; avoid reap/PID reuse assumptions
   when checking the group. Preserve primary failures plus cleanup uncertainty.
   Failed enumeration, startup identity capture, signal or reap must not become
   success. Signal only proven owned identities. Unexpected session loss must
   not manufacture a new helper or GPU attempt.

Production changes should be confined to `supervisor.py`, `s1_cpu_helper.py`
and a small dedicated helper-session/transport module if required. Change
`execution.py` only for necessary session construction/ownership plumbing.
Limit tests to the real helper/supervisor cases and mechanical operation-shape
adaptation in existing recovery fixtures. The focused runner selector may point
to those collected cases. New importable CPU fault fixtures must be source-bound
and inaccessible as live operations; fake hardware and controlled blocking are
the test seams. Preserve all existing semantic/evidence/admission/clock guards,
all prior methods/callbacks, the exact aggregate launcher/order and receipt/capture
caps. Do not modify the completed cache for this task. No arbitrary operation
import path or fixture bypass may enter production admission.

This scope does not claim continuous monitored finalization or durable partial
progress. Persisting a fixed session changes ownership integration, so record
how the current terminal path tears it down; retain the later Plan 036 finalization
gate instead of describing the whole cleanup protocol as complete.

## Required collected evidence

Use small deterministic control fixtures and real owned CPU children, retaining
the complete existing aggregate. Avoid rebuilding a 510-row controller fixture
for each transport or timestamp mutation.

| Boundary | Evidence required for this milestone |
| --- | --- |
| Ready/session positive | Actual importable helper startup under the prescribed stdin/runpy launcher; both fixed roles ready before an instrumented disposable reserve; multiple work/sample operations reuse exact identities; one in-flight request per role; all four thread variables 1 and total owned concurrency at most eight. |
| Startup and cancellation | Actual child blocked before ready, failure after an OS child exists, and readiness arriving after the deadline. Observe monitor ticks from before the startup boundary, no reserve on failure, exact child/group ownership and confirmed cleanup or an explicit unresolved stop. An immediate mocked start exception alone is insufficient. |
| Partial transport | Actual child writes partial header, complete header with stalled body, and EOF mid-frame; an owned reader stalls request consumption. The monitor keeps ticking, rejects by the bound, does not launch prohibited work and cleans the actual group. Include oversized/invalid frames and identity/replay mutations through the real decoder. |
| Sample timing and order | Deterministic direct checks for typed/finite/ordering/session/sequence fields plus a real delayed ready response. A response received at/after the one-second or phase deadline fails even if poll reports ready. Old measurement values cannot be relabeled as fresh. Actual post-task sampling must begin after task completion; in-flight older samples never release the result. |
| Ownership and failure | Spawned helper leaves a real descendant, exits during transport, or ignores TERM. Verify descendant cleanup, bounded nonblocking reap, primary failure retention, and no signal to a foreign sentinel group. Inject enumeration/kill/reap faults at the actual boundary and assert uncertainty, not a fabricated empty successful cleanup. |
| Integration and preservation | Existing positive/adversarial helper and S1 fixtures use the actual session where this scope changes it. Preserve prior assertions, including worker clock transport and consumed cleanup stops. One complete fresh aggregate retains all old 176 methods/426 typed callbacks and adds the exact new AST-derived cases. Independent audit binds current sources, closed logs, wait/exit, 38 frozen records, ledger and actual status lineage. |

Document the exact production startup bound in Plan, including whether it has
separate setup/cleanup portions and where its first timestamp is captured. For
the new collected real child fixtures, recommend at most **24 lifecycle
scenarios per invocation**, serial, each with at most **2 execution + 1 cleanup
seconds** (**72 seconds total**). These are outer fixture limits, not permission
to exceed the tested production deadline: the Plan 036 assertion remains return
by the relevant total deadline plus at most one 100-ms tick, and scheduler
overruns are reported failures. Pure timestamp/framing mutation cases need no
new process per row. Existing tests retain their established allocations.

The saved 93.316-second aggregate headroom motivates this scope; it does not
waive the 300-second cap. The new plan must keep the complete final aggregate
within 300 seconds. If actual tests or remaining architecture cannot fit, retain
the failed/incomplete result for review. Do not shorten scientific fixtures,
omit old cases, split the aggregate or silently increase a cap.

## New allocation and handoff

Recommend a new **3,600 wall-second IMPLEMENT allocation**, measured from UTC
and monotonic timestamps before inspection. End source refinement and test
execution at elapsed **3,300 seconds**; reserve **300 seconds** for evidence and
handoff. Allow up to **three focused invocations of 120 seconds** and **two full
aggregates of 300 seconds**, inside that same allocation. This larger allocation
is for the cohesive helper lifecycle change; it is not a reset or transfer of
Plan 042, Plan 041 or earlier consumption.

Before every launch, finish preparation and create an exclusive durable
prospective note with actual observed elapsed, requested timeout, remaining
time/attempts, exact command/environment, output path and reason. Flush/fsync,
close and verify its readback/hash, then recheck that the entire requested timeout
fits before 3,300. Failed preparation or note publication blocks launch. Reserve
one full 300-second final aggregate while it remains unsupported; a 120-second
diagnostic before that aggregate needs at least 420 execution seconds, plus actual
preparation time. A second aggregate requires a prospectively saved source change
or concrete concern invalidating the first. Every focused/aggregate launch,
including failed discovery or a newly launched permission retry, consumes its
invocation; collected child scenarios have their separate limits. No unchanged
passing aggregate is repeated for timing.

At most **eight CPU workers**, counting the controller, bootstrap/session roles,
fixture children, multiprocessing support processes and native/helper threads;
all four thread settings remain 1. Plan must budget the actual process topology,
not just the two nominal helper roles. Keep suites and new lifecycle scenarios
serial. Retain the six existing direct-script children and their 10 execution +
2 cleanup seconds each / 72 seconds total, inside tighter parent/plan limits.
No standalone helper probes or uncollected tests are allocated.

Allocate **zero GPU/device probes or attempts, model evaluations, production
controller calls/dry runs, production ledger API calls/mutations, production job
directories, setup/download/smoke jobs or scientific reruns**. Only disposable
fixture API calls inside the collected CPU tests are allowed. Read-only source,
artifact, ledger-byte and git inspection remains evidence work. Apply AGENTS.md's
single safe outside-sandbox retry and stop/report rules. Main owns staging and
commits and stops on their failure.

The explicitly resumed skill supplies standing approval for a new allocation
recommended here and finalized in Plan after main compares applicable ceilings
and records its dispatch basis. Routine budget confirmation is not needed.
The next CPU plan cannot authorize a live attempt or change scientific criteria.
Original preparation/setup ceilings and ledger consumption remain intact.

Use new iteration-13 launch/timing/process artifacts. Next expected successors
are correction-011, validation-012, audit-012 and implementation-review-011;
check vacancy before creation. Preserve canonical post-012 and append it to a
successor correction, followed by actual REVIEW -> PLAN -> IMPLEMENT transitions
with durable snapshots. Keep correction-010, validation-011 and this review
observation immutable. Do not rerun the old audit unchanged against a later HEAD
or later status and mislabel the resulting historical-precondition mismatch as a
source regression. Fresh audit code must understand its own predecessor and
actual current endpoint.

Acceptance requires the ready/session contract, startup bound and ownership,
nonblocking complete transport, fresh samples and their required collected
failure cases, plus a fresh complete aggregate and preservation audit. Keep
technical milestone, strict plan, whole implementation, live readiness and
objective flags separate. Passing this plan leaves the last three false.

## Remaining gates and criteria

| Gate | Disposition |
| --- | --- |
| Receipt, numerical envelope, direct scripts, reservation clock, exact-source cache | Completed narrow milestones remain supported by the current aggregate. Preserve their checks and documented historical limitations. |
| R9-2 helper startup/transport/freshness | Next bounded implementation scope above. Source shows concrete remaining defects; current passing tests do not establish their required bounds. |
| R9-4 durable progress | `reconcile_rows` still accumulates verified identities locally; a killed helper or failed final sample can lose the summary. Later persist incremental verified counts/evidence before W and use only that summary during cleanup, with unknown totals where appropriate. |
| R9-5 and remaining R9-3 finalization/order | Supervisor lines 414–497 still flatten/replace failures, clean up without continuous sampling, measure elapsed before final reap and call ledger.finish directly. Later implement structured primary/ordered secondary errors, C/2 + C/4 + C/4 phases, monitored conservative charge and durable acknowledgment together, including first/result/native/receipt/finish/ack ordering. |
| Native/runtime/first-envelope matrices | Remaining Plan 035/036 A1–A3 cases, actual zero-detection and oversized-box paths, and referenced evidence failures remain open. Existing semantic/numerical evidence stays credited. |
| Actual complete worker | Controller synthesis of 510 rows and short real segment barriers do not establish a real successful `stages.segment` traversal of all 510 admitted identities, exact order and 340/170 categories, with reuse and later-failure preservation. |
| Contention/replay/dependencies/lifecycle | Synchronized S1 admission/registration/reservation contenders, registered continuation/consumed replay and the full typed path/cache/PID/PGID/reservation-reference/death matrix remain open. Fixing this session's ownership does not complete that entire lifecycle matrix. |
| Current production binding and recovery | After all CPU gates pass, current admission must bind amendment, validation, original cleaned-up failure, E1 assets/qualification, single-attempt authority and resource ceilings, followed by the separately bounded recovery and raw terminal evidence. No live operation belongs to the next plan. |

**S1-1: met**, scoped to the unchanged source-bound semantic amendment/native/S0
preservation and complete current CPU evidence.
**S1-2: not met**, because the helper and later CPU/admission gates plus current
production authorization/registration are incomplete.
**S1-3: not met**, because there is no live recovery reservation or terminal
outcome; a CPU pass or an unconsumed block cannot satisfy it.
**S1-4: met**, scoped to the 38 frozen records, preserved original ledger/failures,
source diff and truthful durable status lineage; historical exceptions remain
visible rather than being retrospectively reclassified.

The later calibration still has one attempt at
`min(3600, 93600 - gpu_elapsed_seconds - gpu_reserved_seconds) > 0`;
cleanup `min(30, effective_seconds/4)` is inside it. The present ledger permits
the full 3,600-second ceiling numerically, but establishes no fresh device
availability or live readiness. Reservation consumes the attempt even without
launch. Preserve one exclusive GPU group, 22 GiB device memory, eight CPU workers,
150 GiB artifacts, 60 GiB downloads and the existing 57,600-second preparation/
setup ceilings. Reconstruction requires separate later authorization.

No required stop condition was encountered in this review. Next stage: a fresh
direct PLAN for R13-1; no live GPU work is authorized by this review.
