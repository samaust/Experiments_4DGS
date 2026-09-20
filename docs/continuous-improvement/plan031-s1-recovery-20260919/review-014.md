# Iteration 14 REVIEW — Complete the remaining helper boundaries

Proceed to a new bounded CPU plan for **R14-1: complete the fixed helper
session's setup, transport, census and construction contract, with collected
deadline and phase evidence**. The next unused plan number observed is **044**.
The committed Plan043 subset is supported; the helper milestone, strict
Plan043 acceptance, live admission and the main objective remain incomplete.
This is the remaining R9-2 prerequisite, with the minimum active-monitor
ownership integration needed to make its census authoritative. Keep the later
durable-progress and terminal-finalization work separate in the saved gate list.

This REVIEW follows AGENTS.md, the explicitly resumed
continuous-improvement-loop skill and the unchanged [objective](objective.md).
It read the current status, assessment031, handoff013, remaining-gates013,
Plan043/review013, implementation review011, validation012/audit013, and current
helper, supervisor, runner, fixture and relevant recovery source. It ran no
tests, production controller/ledger APIs, GPU/device/model operations or setup
jobs, and made no source/status/git changes or delegation. Its new files are
this review, [assessment032](assessment-032-review.json), and
[observations014](s1-recovery-review-observations-014.json). Main owns status
transitions and commits. No permission failure occurred; an unavailable `python`
executable was followed by standard-library inspection using `python3`.

## Evidence retained

The fresh observation passes **904 read-only reconciliation checks** against
HEAD **8ce3b5736852a49220f5f2cbd91c799785e0dce7**. This did not rerun the old audit
with its obsolete HEAD/status preconditions or execute the historical tests.

- All **77 current source/config/test records** match the committed files,
  validation012, and all four aggregate source snapshots. Independent AST
  collection and typed callback comparison recover **205 methods**, **37
  parameterized methods**, and **426 callbacks**, in the prescribed order with
  passing results and no skips, errors or discovery errors.
- The final aggregate's exact stdin, interpreter/argv/environment, runner,
  unchanged capture, paired closed logs and saved actual completion agree.
  Outer elapsed is **206.1460901590035 seconds**, recovery suite elapsed is
  **197.00130676600384 seconds**, and headroom below 300 is
  **93.8539098409965 seconds**. There is no causal performance claim.
- Audit013's **1,921 checks**, preservation of **176 previous methods / 674
  substantive assertions / 426 callbacks**, and six-source change boundary
  remain applicable because the audited source bytes are current. These are
  preserved audit results; this REVIEW independently checked current hashes,
  committed bytes and collection rather than claiming to repeat all 1,921 checks.
- All 24 final lifecycle scenario records satisfy their recorded 2-second
  execution / 1-second cleanup limits. Saved census is **6 ordinary workers**
  and **8 with descendant plus foreign sentinel**. The next plan must preserve
  exec replacement of the waiting driver and `OPENCV_FOR_THREADS_NUM=1` before
  imports, alongside all four required native-thread variables at 1.
- **Plan043 historical CPU compliance stays false**: focused001/002 derive a
  nine-worker L18 peak; aggregate001 observed 30 workers, including 25 controller
  threads. The corrected final invocation cannot repair those actions. Its
  three focused and two aggregate slots are consumed. Saved IMPLEMENT elapsed
  through evidence is **1,917.37397633199 / 3,600 seconds**; unused wall time
  grants no additional invocation or transferable allocation.
- All **38 frozen records** and the original ledger are exact. Independent
  chain/accounting inspection finds **447 events / 332,437 bytes**, SHA-256
  `2a0f66e38911b0ed029eb9dd0cf4bbd5da4a3b67abb577fbfe9ad67e6a888990`, head
  `00cab019d73b6a3205f676b54cfb2f745f492fa5cca5c69b4567087cea62172b`, **30**
  historical GPU reservations, **4,374.044265462899 GPU seconds**, zero reserved,
  no active job and no S1 recovery event. Original events 250/255/256 match.
- Correction011 retains its complete predecessor prefix and ends at the durable
  IMPLEMENT013 snapshot. Canonical post013 joins its 1,042-byte
  `4b4de2f5…` endpoint to the actual 967-byte `0ccb03a0…` REVIEW014 status,
  with both durable snapshots verified. Correction011 and validation012 remain
  immutable; main's later transitions must append from this real endpoint.

Strict Plan041 remains false, including its missing prospective note and former
OMP/OpenBLAS 4 inheritance; its failed diagnostics/aggregate and full staged
whitespace exit 2 on immutable logs remain visible beside scoped exit 0.
Historical P31-5, unavailable older status/timing snapshots and short-worker
evidence limits also stay recorded. Current full staged-diff success recorded
by main is a separate observation, not retrospective repair.

## Source findings and required changes

These are source-grounded gaps and coverage limits, not new reproductions.
Source line references below identify the reviewed committed bytes.

**R14-1a — Make the final setup decision immediately before reservation.**
`supervisor.py:243–257` validates an initial sample and resource limits, chooses
the reserve callable, then calls it without a fresh check of S. A delayed caller
can cross S after the valid sample. Add a fresh monotonic decision directly at
the S1 reserve boundary after all preparatory checks; require a healthy session,
both retained ready identities and `now < S`. Preserve the original t0/R/S/P;
do not start another setup clock. Failure consumes no reservation and retires
acquired resources within P, or records retained uncertainty.

Strengthen the real disposable reserve case. Its current positive call verifies
ready roles and a sample, but does not insert delay between sample validation
and reserve. Collect the delayed and exact-equality rejection plus a timely
positive case using actual `supervise` and an instrumented disposable reserve.
Do not substitute a separate validator call for the actual decision boundary.

**R14-1b — Finish the combined transport and transmission contract.**
`s1_helper_session.py:154–223` gives sends and reads separate IO_SLICE budgets;
one role can transfer 32 KiB in a tick. Use one **16,384-byte combined per-role
I/O allowance**, with explicit accounting for any peek, and preserve incremental
encoding/validation bounds, frame/schema limits and fairness between roles.
`Session.tick:479–491` correlates a response to the outstanding request but does
not require completed request encoding/transmission. Retain a per-request
transmission state/time and reject response data received before the complete
request is transmitted, including when the final request bytes would be sent
later in the same tick. Delaying response acceptance until writes eventually
finish must not launder an early response into a valid reply.

Collect deterministic duplex-budget cases with both directions ready, a real
backpressured writer with an early correlated child response, and busy/replay
cases through production Wire/Session. Assert transferred bytes per tick and
the premature-response decision, not only eventual timeout. Include both
encoder-in-progress and partially sent request states. Keep maximum frame,
depth/items/scalars, strict primitive/duplicate-key validation and the actual
summary-reference protocol unchanged. No arbitrary import/callable production
operation or bulk evidence parsing may enter the monitor.

**R14-1c — Prove completed response rejection at the actual deadline.**
The production tick refreshes time after Wire processing and before acceptance
(`s1_helper_session.py:436–487`), and typed interval checks are sound for the
tested fields. Current L15/L16 show timeout while a child still sleeps;
their saved records contain only ready bytes for the sample role and no accepted
sample response. They do not establish the required fully readable late frame.

Use real framed child responses plus a deterministic receive/clock seam to
place a complete valid sample in readable state at the one-second cutoff and
at a shorter enclosing phase cutoff. Preserve evidence that the whole frame
was ready, its correlation and acquisition interval, the fresh decision time,
and the rejection before result release or reserve. Cover equality directly
through the production decision path; do not rely on scheduler coincidence.
Keep the monitor ticking within 100 ms: pausing it for a full second would test
tick-overrun handling instead of the intended readable-response boundary.
Retain the current actual old-in-flight sample drain and post-task acquisition
case, which already establishes useful positive ordering.

**R14-1d — Give the asynchronous census authority and remove active S1 scans.**
`Owner.maintain:327–346` publishes mutable group-to-integer-PID lists before
later ownership validation. There is no census generation/acquisition/completion
time. `monitored_call:186` authorizes sampled GPU PIDs solely by this group list.
An owner blocked in census leaves a previously valid snapshot indefinitely
available; errors fail closed once reported, but a blocked call reports none.
Worker/descendant start identities are absent from this acceptance decision.

Publish one immutable completed snapshot only after validation, including a
monotonic generation, finite acquisition/completion times, status, boot/session,
and PID/start/PGID identities for relevant worker/helper lineages. Retain the
last successful observation separately from an in-progress or failed census.
The plan must define an explicit correlation rule tying each accepted sample's
interval to a completed census and captured worker start identity, inside the
same one-second/phase deadline. Do not let an indefinitely old snapshot or the
same numeric PID with a different start time grant ownership. If a new PID's
membership during the sampled interval cannot be established, fail closed or
obtain the required bounded observation; do not infer it from a later integer
match. Census acquisition and complete validation stay off the monitor, with
bounded publication/handoff. A stalled owner must leave the monitor responsive
and produce explicit cleanup uncertainty at the original deadline.

There is an additional directly relevant source gap: the active S1 worker loop
still invokes synchronous `/proc` scans at `supervisor.py:324` and `:340`, after
the asynchronous sample and around `process.poll()`. That can block the monitor
and repeat ownership decisions without the new identity authority. Replace the
**S1 active-phase** checks with the same validated snapshot protocol, including
the child-survival decision and safe ordering of leader observation/reap.
Capture worker identity while its unreaped PID pins it; a retired worker or a
reused group number must not authorize foreign GPU PIDs during acceptance or
publication. Keep non-S1 behavior and the later terminal `stop_group` redesign
outside this change. This narrow integration does not establish the full job
lifecycle or continuously sampled cleanup contract.

Collected evidence must include a healthy owned live and unreaped-exited worker,
foreign PID rejection, actual blocked census after an earlier valid snapshot,
enumeration error, and deterministic PID/start/PGID/session/timestamp mismatch
and reuse cases. Distinguish foreign/no-members from unknown/stale census. An
empty GPU PID sample must not hide a failed required ownership observation.
Verify active S1 checks no longer execute recursive `/proc` work on the monitor.

**R14-1e — Represent partial construction and retain the primary failure.**
`Session.__init__:383–420` may fail before owner creation, during channel setup,
on missing native-thread capability, or while creating its native handle.
`HelperLifecycle.acquire` already retains the partially initialized object, but
`close:525–537` assumes an owner and later calls handle methods even when
`handle is None`. A known never-started owner can wait needlessly to the caller
deadline and remain unretired; `HelperLifecycle.reap:129` also assumes an owner
exists, which can replace the constructor failure with AttributeError.

Initialize explicit lifecycle states before fallible setup. Track only acquired
channels/descriptors; distinguish known no-native-start from a genuinely
unresolved native launch. Known no-start failures can close acquired resources
without waiting for a nonexistent thread or pretending a census occurred.
Unknown launch state remains retained and stop-required. Guard cleanup/reporting
for absent owner/handle and preserve the constructor exception as primary with
ordered secondary cleanup observations. Keep the existing canceled late-return
owner path; no replacement role or helper retry is authorized.

Collect capability-unavailable, native-create failure, first/second socketpair
failure, Wire/setup failure after descriptors exist, and owner-construction
failure. These are injected at actual construction boundaries, with descriptor
accounting, no reserve, bounded return and repeat-cleanup behavior. Most need no
new child. Preserve a real acquired-child/unknown-start case for the retained
ownership distinction. Never equate `ownership=[]` with confirmed cleanup.

**R14-1f — Bound tracing and prove phase identity/lifetime.**
`events`, `ticks` and `signals` append without limits (`s1_helper_session.py:255,
368,397–398,439,477,489,523`; supervisor resume also appends). Repeated cleanup
errors can be distinct, so diagnostic error storage also needs a bound. Use
fixed-capacity recent trace storage plus cumulative counters, first/last and
maximum-gap facts; preserve authoritative outstanding requests, primary failure,
owned identities and unresolved-cleanup state independently. Explicitly record
truncation/overflow. The plan should select concrete capacities. No growing
in-memory event list or synchronous durable trace writer belongs in the monitor.
Keep role alternation and deadline decisions on independent counters/timestamps:
using a bounded list's saturated length for parity would freeze role order.

Use deterministic collected control cases to exceed each capacity without a
3,600-second longevity run, and prove that eviction cannot erase a deadline,
primary error, outstanding request or ownership. Preserve short-scenario raw
evidence through explicit bounded snapshots. Add a phase trace to the existing
successful disposable controller fixture (`S1RecoveryTests.run_controller` and
its already collected success test): it already exercises real session calls
across initial sample, reserve, prelaunch, worker sample, acceptance,
reconciliation, publication and retirement. Capture each phase's exact session,
both PID/start/PGID identities, request range and terminal cleanup result while
delegating to actual production operations. Assert one unchanged work/sample
pair and no replacement. L01 constant reuse and L24 patched summary adapters
remain credited for their existing boundaries; neither substitutes for that
controller trace. Do not add repeated 510-row builds per transport mutation or
claim this synthetic controller worker proves real `stages.segment` traversal.

Strengthen the common real-child fixture at `test_vipe_benchmark_supervisor.py:
495–526`: record its clock before construction, establish fixed absolute action
and cleanup cutoffs, put partial construction inside cleanup protection, and
clamp every call/wait/release to the applicable cutoff. Record/assert return at
each tighter production P/phase/total deadline plus at most one 100-ms tick,
separately from a later fixture safety cleanup. Today most assertions only
check 2/1/3-second outer durations after the fact and helper calls can choose
fresh relative timeouts. Do not restart the fixture cleanup clock or classify
late eventual retirement as timely production cleanup. Native/kernel operations
remain measured boundaries, not hard-real-time guarantees; an overrun is a
failed boundedness observation, not an excluded interval.

## New resources, validation and handoff

Recommend **3,600 wall seconds for the new IMPLEMENT stage**, timed from actual
UTC/monotonic readings before inspection; end source/test activity at **3,300**
and reserve **300** for evidence/handoff. Permit **three focused invocations of
120 seconds** and **two complete aggregates of 300 seconds**, all inside that
allocation. A second aggregate requires a prospectively saved source change or
concrete invalidating concern. Do not repeat an unchanged passing run for timing.
This is a new skill-authorized allocation for R14-1; it transfers none of the
unused Plan043 wall allowance and changes no overall or method/scene ceiling.

Preserve all **205 existing methods and 426 exact callbacks**, including all
24 Plan043 child scenarios and their meaningful assertions. Strengthen existing
cases when that directly closes a gap. Allow at most **12 additional real-child
scenarios per invocation**, serial, each **2 execution + 1 cleanup seconds**,
**36 additional scenario seconds**. Existing L01–L24 retain their 72-second
combined allowance; maximum 36 recorded scenarios and 108 scenario seconds
per invocation remain inside the tighter focused/aggregate/plan limits.
Pure constructor, frame/census mutation and trace-capacity cases create no child
per row. Phase instrumentation uses the existing collected controller success
case under its existing enclosing allocation. Preserve six serial direct-script
children at 10 execution + 2 cleanup seconds each / 72 total. No standalone
helper probes, uncollected tests, profiling, longevity run, split aggregate,
shortened scientific fixtures or increased 300-second capture cap is allocated.

Keep at most **eight total CPU workers**, including wrapper/capture/runner,
controller/owner thread, helper processes, job worker, descendants, sentinels,
support processes and native threads. Use the corrected exec launch driver and
all four native variables plus `OPENCV_FOR_THREADS_NUM=1` from the first
invocation. Collect actual census at ordinary and maximum fixture topology;
include active worker phase where relevant. Add no persistent watchdog thread
or process without fitting this same count. Existing L18 with both descendant
and sentinel already reaches eight; do not add a worker alongside it.

Allocate **zero** GPU/device probes or attempts, model evaluations, production
controller calls/dry runs, production ledger API calls/mutations, production job
directories, setup/download/smoke jobs or scientific reruns. Only disposable
fixture APIs in collected CPU tests are allowed. Source/artifact/ledger-byte/git
inspection is evidence work. Honor AGENTS.md's single safe escalated retry and
stop/report rules; a new launched retry consumes an invocation. Main retains
git staging/commit ownership and stops on failure.

Before every launch finish preparation, exclusively write/flush/fsync/close a
prospective note with actual elapsed, remaining limits, exact command and
environment, output paths and reason; verify readback/hash, then freshly check
that the entire requested timeout fits before 3,300. Reserve one full 300-second
final aggregate until current-source acceptance is established. A 120-second
diagnostic before it requires at least 420 execution seconds plus preparation.
Failed preparation blocks launch; all launches, including failed discovery and
launched permission retries, consume their own slot. Never backdate a note.

Confine source changes to the existing session/supervisor/helper modules,
collected helper fixtures and the small required controller-trace adaptation
in recovery tests. Runner focus/record plumbing may change only as required.
Do not refactor cache, declaration membership, capture, scientific acceptance,
admission schemas or receipt semantics for this milestone. Keep exact aggregate
stdin/argv/suite order and source/glob binding. Derive new method/callback counts
from final AST; compare all prior 205 methods/assertions and 426 callbacks to
8ce3b57. A final-source edit invalidates the prior aggregate and needs a remaining
justified aggregate slot. Passing narrow checks is insufficient for the helper
milestone without the collected production-boundary evidence above.

Save closed logs, actual wait/exit observations, all scenario/phase/transport/
census records, and an independent standard-library audit of current sources,
AST/callbacks/assertion preservation, receipt/capture/invocation, all consumed
attempts, frozen records, original ledger and real status lineage. Reconcile
reported timing/census violations truthfully even if later corrected. A new
plan may achieve its own acceptance; strict Plan043 and Plan041 remain false.

Expected vacant successors are plan044, assessment033-plan, assessment034-
implement, validation013, correction012, audit014, implementation-review012 and
iteration014 launch/timing/process artifacts; check vacancy before writing.
Correction012 must preserve correction011's full prefix and append canonical
post013 directly, then main's actual durable REVIEW -> PLAN -> IMPLEMENT
transitions. Do not rewrite validation012/correction011 or canonical post013.
Main compares the finalized plan against ceilings, records its skill standing-
approval basis and limits, and dispatches the next fresh IMPLEMENT without
routine budget confirmation. No stop condition was encountered in this REVIEW.

## Remaining objective gates

| Gate | Disposition |
| --- | --- |
| R9-2 / R14-1 helper boundaries | Next plan above. Technical completion requires all six groups and their collected evidence; source changes alone do not establish it. |
| R9-4 incremental durable progress | `prepare_terminal_evidence` / `reconcile_rows` still collect local summaries before the helper publishes its final reference. Later preserve verified counts/identities incrementally before W, surviving helper loss or a failed final sample, with explicit unknown totals and no expensive cleanup rescan. |
| R9-5 / remaining R9-3 terminal finalization | Supervisor still flattens/replaces errors, performs `stop_group` without continuous sampling, charges elapsed captured before final helper reap and calls ledger.finish directly. Later implement structured primary/ordered secondary failures, continuous cleanup/publication/finalization monitoring, C/2+C/4+C/4, conservative charge and timely durable acknowledgment together, including first-result/native/receipt/finish/ack temporal consistency. |
| Native/runtime/first-envelope matrices | Preserve remaining mutation matrices and actual zero-detection and oversized-box execution; do not infer complete coverage from current semantic/numerical passes. |
| Complete real worker | Actual successful `stages.segment` must traverse all 510 admitted identities in order with 340/170 split, first publication/reuse and later-failure preservation. Existing synthesized controller rows and short real barriers remain scoped evidence. |
| Contention/replay/dependencies/lifecycle | Synchronized S1 admission/registration/reservation contenders, registered continuation and consumed replay, dependency/path/cache/PID/PGID/reservation-reference/controller-death matrices remain open. Next active-monitor census work does not complete this matrix. |
| Current production admission and calibration | After complete CPU acceptance, bind amendment/current validation/original cleaned-up failure/E1 qualification and assets/single-attempt authority/original resource ceilings in current authorization and registration. Then separately execute bounded recovery with raw first-result and terminal evidence. No live operation belongs to the next plan. |

**S1-1 met:** unchanged semantic amendment/native/S0 rule is supported by current
source hashes and complete CPU evidence. **S1-2 not met:** helper/later CPU gates
and production binding/authorization remain. **S1-3 not met:** there is no recovery
reservation or terminal result. **S1-4 met:** frozen plans/results/failures,
original ledger/allocations and truthful durable status lineage remain preserved.

Later calibration remains exactly one attempt at
`min(3600, 93600 - gpu_elapsed_seconds - gpu_reserved_seconds) > 0`, with
`min(30, effective_seconds/4)` cleanup inside that allocation. Reservation
consumes the attempt even without worker launch. Preserve one exclusive GPU
group, 22 GiB device memory, eight CPU workers, 150 GiB new artifacts, 60 GiB
downloads and existing 57,600-second preparation/setup ceilings. Ledger
arithmetic currently permits 3,600 seconds; it is no evidence of live readiness
or device availability. Reconstruction requires separate later authorization.
