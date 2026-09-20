# Plan 044 — Complete S1 helper admission, transport and census boundaries

Finalize Review014 R14-1a–f as one bounded CPU implementation milestone. The
milestone advances S1-2/S1-3 prerequisites and preserves S1-1/S1-4. It does not
complete the recovery objective or authorize a production reservation. Technical
acceptance requires all six groups below and their collected evidence; a passing
aggregate alone is insufficient.

Authoritative objective: [objective](../docs/continuous-improvement/plan031-s1-recovery-20260919/objective.md).
Review: [review014](../docs/continuous-improvement/plan031-s1-recovery-20260919/review-014.md).
Prior criteria: [assessment032](../docs/continuous-improvement/plan031-s1-recovery-20260919/assessment-032-review.json).
The PLAN handoff and read-only reconciliation are
[plan-link014](../docs/continuous-improvement/plan031-s1-recovery-20260919/plan-link-014.md)
and [observations014](../docs/continuous-improvement/plan031-s1-recovery-20260919/s1-recovery-plan-observations-014.json).
In this document C denotes that run directory. Follow repository AGENTS.md and
`/home/auss/.codex/skills/continuous-improvement-loop/SKILL.md`. Never read
`prompts`. One fresh Astra IMPLEMENT follows main's comparison/dispatch; no nested
delegation. Main owns status transitions, staging and commits.

## 1. Allocation and launch gates

This is new allocation **Plan044-R14-1**, receiving the skill's standing approval
for Review-recommended, Plan-finalized resources after main verifies applicable
ceilings and saves dispatch basis. It transfers no Plan043 resources. Start an
actual UTC/monotonic clock **before IMPLEMENT inspection** and exclusively persist
`C/iteration-014-timing-start.json`. The entire IMPLEMENT stage has **3,600 wall
seconds**, with source/test activity ending at **3,300**, leaving **300** for
closed evidence and handoff. Never reset this clock, exclude blocking time or
start a fresh allocation after an error. Inspection, editing, preparation,
launched executions, cleanup and audit all count against the wall allocation.

| Resource | Final limit and scope |
| --- | --- |
| Focused collected invocations | At most 3, each complete outer timeout 120 seconds, within this IMPLEMENT allocation. |
| Complete aggregates | At most 2, each unchanged outer timeout 300 seconds. Second needs a prospectively saved source change or concrete invalidating concern. |
| Existing child scenarios | Preserve L01–L24, 24 serial scenarios per invocation, 2 execution + 1 cleanup seconds each, 72 seconds total. |
| Additional child scenarios | L25–L36 below, at most 12 serial scenarios per invocation, 2 execution + 1 cleanup each, 36 seconds total. Maximum combined 36 scenarios / 108 seconds, within enclosing invocation. |
| Existing direct-script children | Preserve 6 serial children, 10 execution + 2 cleanup each, 72 seconds total within enclosing aggregate. |
| CPU workers | 8 total, including wrapper/capture/runner, controller and native owner threads, helpers, worker, descendants, sentinels and support/native threads. |
| GPU/device probes and attempts; model evaluations | 0. |
| Production controller calls/dry runs, ledger API calls/mutations, job directories | 0. Disposable fixture APIs are allowed only inside collected CPU tests. |
| Setup/download/smoke jobs, scientific reruns, standalone probes/profiling/longevity runs | 0. |

The launch topology is fixed before the first invocation: exec driver replaces
itself with unchanged capture; capture and runner each count one process; runner
main + sole native owner count two threads; two helpers count two processes.
The ordinary helper fixture total is **6**, a worker raises it to **7**, and one
worker descendant raises it to **8**. L18's helper descendant plus foreign
sentinel already totals **8** and must have no additional worker. A serial
constructor/clock/duplex/census mutation row creates no child. No watchdog
thread/process may be added. Account any actual shell/support ancestor in the
same eight; use shell exec replacement where necessary, not a waiting wrapper.
Record ordinary, worker-active and maximum topology censuses with actual thread
counts. A source-topology estimate alone does not establish compliance.

Set **before imports and from the first launch** `OMP_NUM_THREADS=1`,
`OPENBLAS_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `NUMEXPR_NUM_THREADS=1`,
`OPENCV_FOR_THREADS_NUM=1`, `VIPE_CPU_VALIDATION=1`, and PYTHONPATH to repository
`scripts`. Explicitly carry the OpenCV value into helper and worker launch envs;
keep the existing four-field ready protocol unchanged. Use the corrected
`C/s1-recovery-launch-013-exec.py` architecture in a new iteration014 driver,
never the old waiting driver. Bind iteration014's actual durable IMPLEMENT status
instead of carrying forward its hardcoded iteration013 status hash. No CPU/GPU
ceiling or native-thread permission is increased.

Before **every** launch: complete AST/source/target-vacancy preparation; establish
all output paths; exclusively write, flush, fsync and close a prospective note;
verify exact readback/hash; create/verify the exec-start evidence and open outputs;
then take a fresh clock reading **after every fallible preparation step**. Launch
only if full timeout fits before 3,300. Reserve one full final aggregate until
current-source acceptance exists: a focused 120-second run before that requires
`elapsed + 120 + 300 < 3300`, including actual preparation before final check.
An aggregate requires `elapsed + 300 < 3300`. Final 300 seconds remain reserved
for evidence through 3,600. Store reason, observed times, remaining wall/execution,
all consumed/reserved attempt counts, exact command/env/unsets/stdin identity,
status/plan/source bindings and output paths. Missing/failed durability or
readback blocks launch; never backdate a note or chain launch after failed prep.

Every launched run consumes one appropriate slot, including failed discovery,
timeouts and launched permission retries. An unlaunched prepared slot is not
silently reused: retain its note as not launched and conservatively retire its
index; never overwrite notes. Apply AGENTS.md's one safe escalated retry policy
if a suspected permission restriction occurs, after checking partial effects.
A launched retry needs a remaining slot and a new prospective note. Stop affected
work on a failed/denied escalated retry; do not bypass or change application
configuration to compensate. Main stops on staging/commit failure.

The final committed baseline aggregate took **206.1460901590035 seconds**,
leaving **93.8539098409965 seconds** below 300. Added scenarios have at most 36
seconds, leaving **57.8539098409965 seconds of baseline arithmetic headroom** for
added census/trace/controller overhead. This is planning arithmetic, not a
runtime promise: all work must fit the actual full aggregate, and no timeout cap
increase, scientific shortening, split aggregate or separate hidden probe is
allowed. Use focused results to address actual overhead inside existing slots.
If the final run cannot fit/pass, report partial acceptance and exhausted/remaining
allocations truthfully for the next Review.

## 2. Baseline, boundaries and preserved semantics

Baseline HEAD is **8ce3b5736852a49220f5f2cbd91c799785e0dce7**. Review014 independently
reconciled 904 checks, **77 sources**, **205 collected methods**, **37 parameterized
methods / 426 exact typed callbacks**, final logs/receipt/actual completion and
all 38 frozen records. Audit013's 1,921 checks and preservation of the older 176
methods / 674 substantive assertions remain historical applicable evidence.
Preserve every current method and substantive assertion, including newer helper
assertions, not just that older floor. Preserve exact 426 callback identities,
types, values and order. Add collected literal methods for pure mutations rather
than changing old callback declarations. Record all intentional assertion moves
as equivalent-or-stronger mappings; deleting an assertion or substituting a weaker
stub is not preservation.

Confine production edits to `scripts/vipe_benchmark/s1_helper_session.py`,
`supervisor.py`, and minimal required `s1_cpu_helper.py` compatibility. Tests belong
in `tests/test_vipe_benchmark_supervisor.py`, its existing importable
`s1_helper_fixtures` module, and minimal phase instrumentation in
`test_vipe_benchmark_s1_recovery.py`. Runner changes may only add necessary focus
or record plumbing. Preserve exact capture, source membership/declaration cache,
receipt/admission schemas, semantic/native assignment, scientific fixtures,
summary-reference protocol and operation whitelist. No monitor-side bulk parsing,
arbitrary import/callable operation or durability writer is introduced.

R=t0+ready_seconds, S=t0+setup_seconds and P=t0+total_seconds remain anchored to
one session t0 captured before fallible initialization, with the exact existing constructor bounds
`0 < ready_seconds <= 1`, `ready_seconds < setup_seconds <= 2`, and
`setup_seconds < total_seconds <= 3`. The reservation
clock stays `T=reservation.seconds`, `C=min(30,T/4)`, total=start+T, W=total-C.
No fresh setup/sample/phase/cleanup clock may hide previously spent time.
The monitor's maximum measured tick gap and turn duration remain 100 ms. Native,
kernel, GIL and scheduler operations are measured boundaries; overruns are
failures/unknown cleanup, not hard-real-time guarantees or excluded time.

## 3. R14-1a — Fresh admission immediately before reserve

At `supervisor.supervise`, after initial sample, resource/checkpoint checks and
reserve-callable selection, invoke one S1-only admission guard as the last
operation immediately before calling that callable. Capture fresh monotonic now
inside this guard; require `now < session.setup_deadline`, healthy unpoisoned
lifecycle/session/owner, both ready roles, retained exact PID/start/PGID and
boot/session identities, no ownership/census fatal state, and the completed
initial accepted sample. The guard reads bounded retained state only; it does not
scan `/proc`, wait, resample or reset S. A completed sample cannot independently
authorize admission after S. If owner state changes or now reaches S, no call to
reserve occurs. Equality rejects. Failures retire acquired resources by original
P, or attach explicit retained cleanup uncertainty to the primary failure.

Strengthen L02's actual disposable `supervise` positive path to record the guard
and instrumented reserve times, ready identities, accepted initial request and
no-replacement count. L25 and L26 delay the exact boundary after valid initial
sampling using a disposable ledger property/guard observation seam; respectively
cross S and return exactly S at the production guard. Assert zero reserve calls,
no reservation/worker and timely cleanup/retained uncertainty. The clock seam
applies to the guard's observation, not the entire process or owner clock. A
standalone validator invocation is insufficient. Preserve old no-reserve and
resource-ceiling assertions; adapt older fake-session fixtures to supply explicit
admission facts rather than bypassing the new production guard.

## 4. R14-1b — Combined transport budget and early-response rejection

`Wire.tick` receives an explicit turn-local allowance **16,384 bytes total** for
actual send + receive + successful peek bytes. Keep cumulative sent/received and
add peek/combined per-turn facts. Failed nonblocking reads/writes transfer zero.
Peeking the same byte twice costs twice. Header bytes count. Encoding and primitive
validation remain separate bounded CPU work: no more than existing 256 token
advances and 16,384 encoded bytes per turn, preserving MAX_FRAME=65,536, depth,
item, scalar, strict JSON primitive/duplicate-key limits. Parsing stays limited
to one complete bounded frame. Keep at most one in-flight request/response per
role and one decoded candidate; no queue of messages.

Track request generation, queued/encoding/partially-sent/transmitted state,
first-send and final-send entry/completion timestamps. Queue only after installing request
identity. Supply explicit request/response context to Wire from Session; the
shared Wire in the helper must still send its ready/response frames correctly. Treat wire readiness exchange separately from request/response state.
At the start of a role turn freeze whether its request was fully transmitted.
Before writing any remaining request bytes, make a bounded nonblocking read/peek
for unexpected response data. Any observed inbound byte while that turn began
with unfinished transmission permanently rejects that request, even if the
request encoder could finish or its final bytes could be sent later in the turn.
Do not store early bytes to accept after transmission. Also check immediately
after a send in that turn: a final-send turn must reserve at least one I/O byte
for this check. Conservatively reject inbound data observed then even if an
extremely fast honest helper sent it after final transmission; this conservative
case is preferable to granting ambiguous same-turn authority and must be tested
and documented. Responses first observed on a later turn require the recorded
completed transmission and correlation. No claim is made to timestamp unseen
kernel arrival; the evidence is the actual observed ordering and conservative
same-turn rule.

For productive bounded duplex work, alternate the direction given first service
using an independent turn counter, give each ready direction a bounded share
(up to 8,192 initially), and use remaining allowance only after preserving the
required premature/trailing peeks. Avoid starving receive/validation behind a
large send. One role cannot spend 16 KiB in each direction. Session alternates
role order with an independent cumulative counter, never trace length. Trailing
frame detection consumes allowance and defers acceptance if it cannot be checked
this turn; never perform an unaccounted peek. A frame whose validation completes
with exhausted I/O waits for the next bounded trailing check, still under its
original request deadline.

Pure collected socketpair controls exercise both directions ready, exact budget
exhaustion, validation/peek rollover and fair progress; assert per-turn measured
combined bytes <=16,384. Preserve max-frame positive and oversized/trailing
negative cases. Add real L27 encoder-in-progress early correlated reply and L28
backpressured partial-write reply, including the final-bytes-later-same-tick
branch. Child fault logic is importable test-only code. Record outstanding ID,
encoder/out lengths, preturn transmitted state, observed early bytes, final-send
ordering and explicit early-response error. Retain busy/replay/malformed
production Session/Wire controls. A timeout alone cannot pass these cases.

## 5. R14-1c/d — Sample deadlines and authoritative asynchronous census

### Immutable authority and handoff

Replace `Owner.groups` as S1 authority with immutable completed census records.
Use a frozen record with immutable row tuples, not a frozen object containing
mutable dictionaries. Each record contains session token, boot ID, monotonically
increasing generation, request/worker-generation binding, finite acquisition_start
and completion timestamps, success/failure status, exact helper roots, optional
captured worker root and relevant PID/start_ticks/PGID/PPID/state identities.
A success record is assigned atomically to the bounded completion mailbox only
**after** enumeration, identity validation and lineage construction finish.
In-progress metadata and the last successful record remain separate. Failure
publishes bounded failure state and never leaves an old success current.

Only the retained owner thread scans `/proc` or reads process identities. Bound
one census to **16,384 scanned process entries** and a published relevant lineage
to **64 identities**; exceeding either fails closed as census-capacity uncertainty.
Build lineage with a visited set/worklist and stop at the64-identity bound; do
not repeatedly rescan the entire map until a fixed point. Reject sample GPU PID
lists longer than64 before membership comparison. These are storage/work limits,
not permission for additional CPU workers. Host
processes are scanned off-monitor, one bounded local map discarded after each
pass. The monitor reads one immutable pointer and compares at most 64 identities.
No lock acquisition/wait on owner progress belongs in its turn. Use one outstanding
census request mailbox and one completed reply mailbox with increasing generation;
retain at most two bracket snapshots per outstanding sample plus last-success
for diagnostics. No unbounded history or queue. Owner may service existing helper
cleanup between requests; cancellation takes priority. No second owner/thread is
added. A blocked scan remains retained; monitor timeouts do not assert it stopped.

Capture worker identity through an owner mailbox after `Popen` returns and before
worker sampling: monitor supplies the unreaped direct-child PID and a new worker
generation, not a trusted PGID. Owner validates direct parent is this controller,
PGID equals PID, finite/typed PID/start, boot/session and observes the identity
while the direct child is unreaped. Capture even a zombie worker; never call
`Popen.poll`, `waitpid` or another reap before this capture. A failure to capture
is unknown ownership, not an empty group. Helper cleanup ownership and worker
ownership remain separate: the helper owner must not signal or reap the job
worker merely because it appears in a census.

### Implementable sample/census ordering

Every sample request, including initial/empty-GPU and post-work samples, follows
this state machine, within one fixed `d=min(phase_deadline, dispatch+1)`:

1. On sample submit, record dispatch and d immediately; install the sample ID and
   census request generation. Request a **pre** census acquired no earlier than
   dispatch. Keep the sample wire unqueued until this fresh successful census
   arrives and its session/boot/worker-generation/retained helper roots match.
   The waiting/encoding/transmission time is charged to the same d.
2. Queue/send the actual sample request; retain pre snapshot on that request.
   Require `dispatch <= pre.acquisition_start <= pre.completed <=
   final_send_entered <= acquisition_start <= acquisition_end <= response_observed`
   and `final_send_entered <= transmitted_observed <= response_observed`. Record
   both sides of the final send: a fast child may start acquisition before the
   parent records the send-completion observation, so do not incorrectly require
   transmitted_observed <= acquisition_start. No absolute
   cross-process clock shim is introduced: real monotonic and same boot apply.
3. Wire/Session validate complete response, schema, transmission and acquisition
   times. A decoded sample is a **candidate**, not a released reading. Preserve
   its full bounded value, acquisition interval and original d. Request a **post**
   census whose acquisition starts at or after that acquisition_end. It must be
   explicitly bound to this sample/request generation and same captured worker.
4. Require `acquisition_end <= post.acquisition_start <= post.completed <= decision
   < d`, pre-generation < post-generation and typed finite timestamps. Both
   observations must succeed and validate helper roots. No outstanding/error or
   expired generation may use last-success as a substitute. Match the worker root
   and each sampled GPU PID by exact `(pid,start_ticks,pgid)` in **both** bracket
   records, with legitimate worker-group/descendant lineage anchored to the pinned
   root. A PID seen only after sampling, changed start/group, wrong boot/session
   or retired worker generation cannot authorize the reading. Reject unresolved
   membership; do not retry/resample to launder the same candidate.
5. Capture a fresh final decision time, reject equality or later, then mark that
   one request accepted and release the reading with its bounded census/interval
   authority record. Until then the sample role is busy; no next request is queued.
   The exposed resource mapping remains the existing shape: attach correlation
   evidence to session state/events rather than adding untrusted authority keys
   to resource values. Session.tick must not expose candidate values as accepted
   sample responses before these checks. Work response delivery remains bounded;
   monitored_call still releases work only after a sample dispatched at or after
   work completion, with a corresponding fresh bracket.

When no worker exists, fresh successful helper census is still mandatory and
GPU PIDs must be empty. After worker retirement, require a fresh explicitly
worker-absent generation and empty GPU PIDs; a lingering integer group cannot
authorize publication. Distinguish successful no-members/no-GPU from unknown,
blocked, failed, stale or identity-mismatched census in error evidence. The last
valid empty reading never suppresses later census failure. On a pending pre/post
scan, continue ticks and fail at d; clean up using the applicable original P,
phase or total deadline, keeping unresolved owner state when it cannot retire.
No fresh one-second window is granted when the post snapshot is requested.

### Active S1 worker and leader observation

Replace both S1 active `group_processes(process.pid, include_zombies=True)` and
post-poll `group_processes(process.pid)` calls in supervise with the validated
snapshot authority. Preserve non-S1 behavior. The worker loop consumes the
accepted sample's authority for GPU exclusion; it must not independently rebuild
integer group membership. In owner census acquisition, observe direct worker exit
with `waitid(P_PID,...,WEXITED|WNOHANG|WNOWAIT)` **before** scanning; save exit code
and observation time. Publish an exit-qualified census only if the leader was
already observed exited no later than census acquisition and its pinned identity
still validates. If the leader exits after a scan began, obtain the next fresh
census inside the unchanged active deadline; that scan cannot decide child
survival. A live descendant/escaped tracked lineage in an exit-qualified snapshot
fails child-survival. Unknown/error/stale state fails closed.

For successful S1 exit, preserve the unreaped leader through acceptance and
reconciliation so its group remains pinned for their samples. Read saved WNOWAIT
exit status for control flow; do not call poll/wait to release the pin prematurely.
At the existing terminal cleanup boundary, explicitly retire/invalidate worker
sample authority before `stop_group` may reap; subsequent publication passes no
active worker authority and requires empty GPU ownership under fresh helper-only
census. This small integration does not redesign stop_group or establish later
continuous cleanup/finalization. No signals may be justified by a retired PGID.
Existing terminal cleanup behavior and remaining deficiencies stay reported.

### Deadline evidence without tick-overrun masking

Keep L15/L16 sleeping-child timeout cases and L17 real old-in-flight drain plus
post-task acquisition positive ordering. Add L29/L30 actual valid framed child
sample responses fully readable at respectively the one-second and a shorter
phase deadline. Do not sleep the monitor for a second. Use a scoped injectable
**decision-clock observer** on Session, defaulting to real monotonic, while tick
gap/turn-duration and owner timestamps continue using real monotonic. The test
queues and completely receives/validates actual child bytes under normal short
ticks, verifies complete frame length/hash/correlation and candidate acquisition,
then returns exactly d from the final production acceptance observation. For the
receipt-time boundary, similarly inject the receipt decision only after the
complete response is known readable, and assert its specific deadline branch.
Use pure replay of captured bounded frames for immediately-before/after numerical
boundary permutations; do not spawn per mutation. Evidence must show the whole
frame was present at the decision and the rejection was deadline equality,
not `monitor tick overrun`, malformed/census failure or a sleeping producer.

If Session checks equality at turn entry, arm the seam after that entry, at the
real receipt/final decision point; never alter global time or disable the gap
check. Record real turn gap <=100 ms, injected decision, original dispatch/d,
complete frame bytes/hash, actual acquisition interval, matched census generations,
zero accepted sample/result/reserve and exact exception. A timely positive using
the same production path is required. Tests cannot directly invoke only
validate_acquisition and claim this boundary.

Census controls include L31 live owned worker then foreign-PID rejection; L32
owned unreaped-exited worker; L33 blocked observation after an earlier valid
snapshot; L34 actual enumeration error even with empty GPU sample; L35 exited
leader with live descendant. Pure collected immutable-record mutations cover
PID/start/PGID/session/boot/worker generation, typed/finite times, interval ordering,
pre/post generations, empty-but-failed, changed/reused PID, retired root and
new-member-only-post. Test that publication of a later unrelated snapshot cannot
mutate an already-held candidate and that monitor active S1 call paths contain
no recursive `/proc` scans. A stubbed integer membership list cannot satisfy it.

## 6. R14-1e — Safe partial construction and primary error

Before any fallible validation/owner/channel/native work, initialize t0, absolute
cutoffs where valid, channels/wires dictionaries, owner=None, handle=None,
construction state, first primary error and cleanup/ownership markers. Initialize
the safe no-start cleanup cutoff to t0 before validating supplied durations;
invalid durations therefore still permit immediate acquired-descriptor cleanup.
Guard supervisor cleanup-deadline retrieval with the original caller deadline
when initialization never published its valid cutoff, without inventing a new
relative timeout. Lifecycle
acquire continues retaining the allocated Session before invoking its constructor.
Track each acquired socket endpoint immediately after socketpair returns and before
Wire setup, including the pair whose Wire construction fails.

Use explicit states `not_started`, `launch_entered`, `running`, `retiring`,
`retired`, `launch_unknown`. Owner construction failure, absent native capability,
first/second socketpair or Wire failure before native entry are known no-start.
Close only acquired descriptors; set confirmed no-start retirement without waiting
for a nonexistent thread or claiming a successful census. Native factory known
pre-entry failure follows the same rule. Mark launch_entered and retain owner in
OWNERS **before** entering native creation. Any failure whose no-start guarantee
is unavailable is launch_unknown even with handle=None. It stays retained,
canceled and stop-required; missing handle alone is never proof of no thread.
A successfully returned handle records running immediately. Keep the existing
late-spawn-return path and publication of returned PID before fallible identity
work. No retry/replacement role launch is allowed.

`Session.close/ownership` and `HelperLifecycle.reap/ownership` must safely handle
absent owner/handle and partially built channels. Known-no-start close is bounded
and idempotent with no thread join/owner scan. Running close clamps waits and join
observations to supplied original deadline; unknown launch returns unconfirmed
by that deadline while retaining strong references. A zero-length ownership list
never overrides unknown launch. Guard owner error retrieval and cleanup failure
reporting so AttributeError cannot replace constructor failure. Save constructor
exception type/message/cause as primary; attach ordered bounded secondary cleanup
facts. Do not refactor the broader terminal primary/secondary gate here.

Collected pure cases inject unavailable capability, known native-create failure,
owner constructor failure, first/second socketpair failure and first/second Wire
setup failure at actual boundaries; count descriptors before/after, no owner/native
start where applicable, no reserve, bounded return and repeat cleanup. At most one
real L36 injects native creation returning/raising ambiguously after an actual owner
starts. Verify production cleanup uncertainty with absent handle, no replacement,
and retained ownership at original P. A test-controlled saved native handle can
be revealed only during later fixture safety cleanup, explicitly separate from
the earlier production failure; do not rewrite that outcome as timely success.
Existing L08 supplies independent late-return retention evidence.

## 7. R14-1f — Bounded traces, phase identity and fixture deadlines

Select capacities: **256 recent session events**, **128 recent tick records**,
**128 recent owner signal records**, **32 recent owner errors**, and **32 recent
lifecycle cleanup errors**. Use deque/ring snapshots converted to bounded lists
only when recording test evidence. Bound error message to 1,024 characters and
stored secondary metadata to the existing primitive/control limits. Retain first
primary error and first cleanup error separately; recent eviction cannot erase
them. Track total/dropped counts, first/last monotonic times, maximum tick gap/turn,
per-role dispatch/response counts, total I/O/peek bytes, census requests/failures,
signal attempts and cleanup errors independently. Repeated distinct errors cannot
create an unbounded deduplication set. Counters use fixed-width saturating unsigned
64-bit values with explicit saturation flag; use a separate toggled role/direction
bit for fairness so saturation does not freeze order. Request/generation IDs must
fail closed before unsigned 64-bit exhaustion rather than wrap or replay.

Outstanding requests, transmission status, candidate/pre/post records, owned
identities, cancellation/unknown cleanup state and primary failure live outside
evictable trace. Bound those by the fixed two roles, one worker generation and
64-identity census limit. Preserve short scenario records through explicit bounded
snapshots before additional activity evicts necessary facts; do not expand trace
capacity to make a test pass. No synchronous durable writer in monitor/owner.
Pure collected controls exceed each ring/error capacity and saturate counters
through injected near-limit values; prove dropped/saturation counts, first/last,
maximum gap, alternation, outstanding request/primary/ownership retention and
continued deadline enforcement. No real 3,600-second longevity run.

Instrument the **existing** successful `S1RecoveryTests.run_controller` collected
fixture while delegating to actual Session/monitored_call/supervise operations.
Capture initial sample, reserve guard/call, prelaunch, worker sample, acceptance,
reconciliation, publication and retirement. Each phase includes token, boot,
both exact ready PID/start/PGID identities, worker identity/generation or explicit
retired state, request sequence range, relevant accepted census/sample reference
and terminal cleanup result. Assert one unchanged two-role pair through all
phases, monotonic request IDs, zero replacements and final confirmed retirement.
Instrumentation may wrap production methods to snapshot bounded state; it may
not replace operations or validations with fabricated phase records. Write the
phase artifact from the test after monitored work. Reuse the existing synthetic
510-row controller build once; this does not prove real stages.segment traversal.
Keep L24 summary-reference assertions and scientific first-result/native order.

Change the common scenario context manager to acquire its real clock **before
Session construction**, with fixed fixture action_end=start+2 and safety_end=start+3.
Place allocation/constructor inside try/finally using retained partial Session so
constructor errors also clean up. A fixture end is never recomputed as now+1.
Every await, work call, barrier release, child wait and safety close clamps to its
original applicable deadline and these outer cutoffs; on action_end, no new work
starts and cleanup uses only remaining safety time. Use injected absolute fixture
cutoffs/test helper wrappers, not a persistent watchdog. Native nonpreemptible
calls may still overrun: record and fail rather than exclude them.

Record and assert each tighter production R/S/P/phase/request/total return bound
separately: no later than that bound plus at most **one 100-ms monitor tick**;
this tolerance measures return/cleanup scheduling, never acceptance at equality.
A subsequent fixture safety cleanup must not convert a late/unconfirmed
production close into a timely one. L08/L21–23/L36 keep both production failure
and later safety-cleanup records. Outer execution<=2, cleanup<=1 and total<=3
remain assertions, now enforced prospectively by clamping all owned operations.
Record constructor entry/end, each deadline/call/return, cleanup primary and
secondary outcomes. No full-second monitor pause or fresh-clock helper wrapper.

## 8. Collected matrix and acceptance

Keep all old methods/callbacks/assertions and L01–L24. Add at most the following
12 serial real scenarios; constructor/duplex/census/capacity mutation methods use
no extra children. Their helpers/workers/sentinels all count in their one scenario
and are cleaned before the next scenario begins.

| Scenario | Boundary and evidence | Maximum total workers |
| --- | --- | --- |
| L25 | actual supervise delayed pre-reserve decision after valid initial sample, zero reserve | 6 |
| L26 | actual supervise equality S, zero reserve | 6 |
| L27 | correlated early response during request encoding, explicit rejection | 6 |
| L28 | real backpressure/partial transmission and same-turn final-send early response rejection | 6 |
| L29 | actual fully readable sample, equality at one-second request cutoff with real ticks | 6 |
| L30 | actual fully readable sample, equality at shorter phase cutoff with real ticks | 6 |
| L31 | live worker positive identity bracket then foreign-PID failure | 7 |
| L32 | exited unreaped owned worker positive bracket/acceptance and retained pin | 7 |
| L33 | census actually blocks after valid snapshot; stale authority refused, bounded uncertainty | 7 |
| L34 | actual enumeration failure, empty GPU reading cannot pass | 6 |
| L35 | exited leader plus live descendant, child-survival failure without monitor scan | 8 |
| L36 | actual ambiguous native-start/absent-handle ownership retained; separate safety cleanup | 6 |

If an extra real-child case is needed, it must fit inside these 12 (document its
replacement coverage without dropping a required group), not silently become L37.
Prefer pure no-child captured-frame/mutation variants. Preserve all old real
scenarios and their limits. Verify source-derived final method/callback counts
and exact execution records; do not guess counts in the validation artifact.

| Acceptance ID | Required result | Objective relation |
| --- | --- | --- |
| A44-1 admission | R14-1a actual positive, delayed and equality reserve decisions pass with original S/P and healthy retained identities. | S1-2/S1-3 prerequisite |
| A44-2 transport | R14-1b combined budget, transmission state and early same-turn rejection pass with all old frame/schema/summary controls. | S1-2/S1-3 prerequisite |
| A44-3 deadline/census | R14-1c/d fully readable equality evidence, fresh immutable bracket, PID/start/group authority, no active S1 monitor scan, pinned exit/child checks all pass. | S1-2/S1-3 prerequisite |
| A44-4 construction/trace | R14-1e/f all partial states, primary retention, capacities/counters, actual phase trace and enforced fixture deadlines pass. | S1-2/S1-3 prerequisite |
| A44-5 aggregate/preservation | All prior205 methods/426 callbacks/substantive assertions plus new exact collection pass once on final sources through unchanged <=300s capture, no scientific/cache/receipt weakening. | Preserves S1-1; validates prerequisite |
| A44-6 procedural/evidence | All launches prospectively durable, full timeouts fit allocation, every consumed run/census/overrun truthfully accounted, eight-worker/thread limits hold from first launch, 38 frozen/ledger/status lineage preserved. | Preserves S1-4 |

Complete helper milestone means A44-1 through A44-6 all met. Keep technical and
strict acceptance distinct if a procedural violation occurs. Plan041 and Plan043
strict acceptance remain false forever; later passing evidence does not repair
those actions. Narrow passing assertions cannot set overall/helper completion.

## 9. Exact aggregate and evidence handoff

Use new `s1-recovery-diagnostic-014-001..003` and
`s1-recovery-aggregate-014-001..002` directories, checking actual vacancy. Corrected
exec driver launches `.local/envs/stg-colmap/bin/python -B -m
vipe_benchmark.s1_validation_capture <absolute directory> --timeout 120|300`
(with `--diagnostic` only for focused). Capture remains byte-unchanged and sends
child argv `.local/envs/stg-colmap/bin/python -B -`, repository cwd and these
exact stdin bytes including final newline:

```python
import runpy
import sys
sys.path.insert(0, "scripts")
runpy.run_module("vipe_benchmark.s1_validation_runner", run_name="__main__", alter_sys=True, init_globals={"STDIN_PYTHON_ARGV": tuple(sys.argv)})
```

Suite order stays `s1_semantics`, `s1_recovery`, `backends`, `contracts`,
`component_recovery`, `execution`, `budgets`, `supervisor`, `review_annotations`.
Focused runner executes the collected HelperSessionTests class through current
receipt diagnostic mode. Aggregate unsets both diagnostic environment variables.
Require all methods/callbacks exactly once, zero failures/errors/skips/discovery
errors, actual wait/completion exit0 and outer elapsed<=300. Record inner/outer
elapsed and remaining headroom without claiming causal performance improvement.
Source edits after a pass invalidate it and require a remaining justified
aggregate; an exhausted allocation cannot validate further source changes.

Keep paired closed stdout/stderr, receipt, execution, actual tool completion,
prospective notes/exec evidence, source pre/post snapshots, AST callback/method
order, assertion preservation map, scenario/phase/transport/census/capacity
records and every launch including failures. Independent standard-library audit
must read files/AST and git bytes without importing production or launching
fixtures. Derive current sources via existing membership; baseline 77 is a
comparison record, not permission to omit a new required source. Verify unchanged
capture/contract/cache/scientific bytes and allowed source edits, all attempts,
resource topology, 38 frozen records and original ledger bytes/chain/accounting.

Original ledger is **447 events / 332,437 bytes**, SHA256
`2a0f66e38911b0ed029eb9dd0cf4bbd5da4a3b67abb577fbfe9ad67e6a888990`, head
`00cab019d73b6a3205f676b54cfb2f745f492fa5cca5c69b4567087cea62172b`, 30 historical GPU
reservations, **4,374.044265462899 GPU seconds**, zero reserved, no active job and
no S1 recovery event. Preserve original failure events250/255/256. No ledger API
runs even for validation; byte/JSON inspection is sufficient here.

Expected vacant outputs: `s1-recovery-validation-013.json`,
`s1-recovery-baseline-correction-012.json`, `s1-recovery-audit-014.json`,
`s1-recovery-implementation-review-012.md`, `assessment-034-implement.json`, and
iteration014 launch/timing/process/preparation/limitations/remaining-gates/handoff
artifacts. Recheck before exclusive writes; never overwrite historical evidence.
Correction012 copies correction011's complete predecessor prefix and appends
canonical post013 **directly**, then main's actual durable REVIEW014 -> PLAN014
transition and later PLAN -> IMPLEMENT transition. Confirm old/new snapshot hashes
at every link. Current PLAN endpoint is the durable 971-byte status snapshot
SHA256 `2a5f86054e8f756b8a5b546ac830dc7679d040e8b2d55c18ecb1ffe6be384704`.
Never rewrite validation012, correction011 or canonical post013; never claim a
bookkeeping transition whose durable predecessor did not exist.

Retain Plan043's consumed3 focused+2 aggregate, closed execution allocation,
1,917.37397633199 wall seconds through evidence, historical nine-worker L18 and
30-worker/25-controller-thread aggregate violations, final corrected6/8 census,
and strict=false. Retain Plan041's missing prospective note, former OMP/OpenBLAS4,
failed runs/full immutable-log whitespace exit2 beside scoped exit0. Keep older
P31-5, unavailable historical snapshots and short-worker limitations. Record new
exceptions truthfully; no historical repair through a new baseline.

Main reviews saved implementation/evidence/criteria, stages explicit task paths
with escalated git add, inspects staged diff, and commits with title/body under
standing repository authorization. Commit is a checkpoint; active loop continues
to fresh Review unless a stop condition applies. No subagent status/git writes.

## 10. Gates that remain after this milestone

Preserve the existing criteria definitions: S1-1 met and S1-4 met on current
applicable evidence; S1-2 and S1-3 not met. Reassess each after implementation,
using unverified for missing/contradictory current evidence. Even all A44 checks
passing leaves these later gates:

- R9-4: incremental durable verified progress before W, surviving helper loss or
  failed final sample, with explicit unknown totals and no costly cleanup rescan.
- R9-5 / remaining R9-3: structured primary/ordered secondary terminal failures;
  continuously sampled cleanup/publication/finalization; C/2+C/4+C/4 allocation;
  conservative charge and timely durable acknowledgment; complete first-result,
  native/receipt/finish/ack ordering. Existing stop_group is not redesigned here.
- Remaining native/runtime/first-envelope/referenced-evidence mutation matrices,
  actual zero-detection and oversized-box execution.
- Real `stages.segment` success over all510 ordered admitted identities and340/170
  split, first publication/reuse and later-failure preservation. Synthetic
  controller rows and short worker barriers are not complete real-worker evidence.
- Synchronized admission/registration/reservation contenders, registered
  continuation/consumed replay, complete dependency/path/cache/PID/PGID/reservation
  reference/controller-death lifecycle matrix.
- Current production authorization/registration binding amendment, current complete
  CPU validation, original cleaned-up failure, E1 qualification/assets, one
  calibration attempt and original resource ceilings; later separate live gate.
- Later bounded calibration and first-result/raw/terminal evidence. No live action
  is authorized by this plan, assessment or skill resource approval.

Later calibration remains one attempt, consumed by reserve even without launch,
with effective seconds `min(3600,93600-gpu_elapsed-gpu_reserved)>0` and cleanup
`min(30,effective_seconds/4)` inside that allowance. Preserve one exclusive GPU
group,22GiB device memory,eight CPU workers,150GiB new artifacts,60GiB downloads,
and existing57,600-second preparation/setup ceilings. Current arithmetic permits
3,600 but establishes neither live readiness nor device availability.
Reconstruction requires separate later authorization. Completing this plan is
not completing the objective; no permission confirmation is needed for the
CPU allocation after main's required comparison and durable dispatch basis.
