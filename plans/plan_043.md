# Plan 043 — Fixed S1 helper sessions with bounded startup and fresh samples

Iteration 13 PLAN, 2026-09-20. Implement **R13-1**, the remaining R9-2
startup/transport/sample prerequisite identified in
[review-013](../docs/continuous-improvement/plan031-s1-recovery-20260919/review-013.md).
The authoritative [objective](../docs/continuous-improvement/plan031-s1-recovery-20260919/objective.md)
and S1-1 through S1-4 definitions remain unchanged. This plan advances S1-2/S1-3
prerequisites and preserves S1-1/S1-4; it does not authorize admission or a live
calibration. Latest assessment: [assessment-030-plan](../docs/continuous-improvement/plan031-s1-recovery-20260919/assessment-030-plan.json).

Follow AGENTS.md and the explicitly resumed continuous-improvement-loop skill.
One direct implementation agent, no nested delegation; main owns status,
staging and commits. Never read `prompts`. New CPU allocation receives the
skill's standing approval after main records its comparison with applicable
ceilings. Historical allocations, plans and evidence stay consumed and immutable.

## Allocation and prospective launch gate

New IMPLEMENT scope: **3,600 wall seconds**, measured with actual UTC and
monotonic timestamps **before inspection**. Source refinement and test execution
end at **3,300 seconds**; the final **300 seconds** are evidence/handoff reserve.
At most **three focused invocations of 120 seconds** and **two complete aggregate
invocations of 300 seconds**, all inside that allocation. Every actual launched
invocation counts, including failed discovery and a newly launched permission
retry. Preparation failures consume elapsed time; no launch means no invocation.
Do not reset a historical clock, transfer unused allocation or create extra probes.

Before each launch finish preparation, then create an exclusive prospective
launch note recording observed UTC/monotonic elapsed, requested timeout,
remaining execution/wall time, consumed/remaining attempt counts, exact command,
environment, cwd, stdin identity, output paths, reason and final-aggregate reserve.
Flush/fsync, close, read back and verify exact bytes/hash. Recheck immediately
before launch that its **entire timeout** fits before 3,300. Failed preparation,
publication or readback blocks launch. Never backdate a note or proceed through a
failed command using an unconditional separator. Each retry gets a new note.

While a final complete pass remains unsupported, reserve a full 300-second
aggregate. A 120-second diagnostic then needs at least 420 execution seconds
remaining, plus actual preparation time. A second aggregate requires a saved
source change or concrete concern invalidating the first, recorded before launch.
No unchanged passing repeat for timing, suite splitting, standalone helper probe,
uncollected tests, parser benchmark or profiling run. An exhausted plan stops its
implementation allocation; retain results for the next authorized review.

At most **24 new real-child lifecycle scenarios per invocation**, serial, each
at most **2 seconds execution plus 1 second cleanup**, **72 seconds total**.
These outer fixture caps never extend a tighter tested production deadline.
Keep the six existing serial direct-script children at their existing 10-second
execution + 2-second cleanup caps, 72 seconds total, inside parent deadlines.
All old collected cases remain; do not relabel old processes to evade a cap.

At most **eight total CPU workers**, counting wrapper/capture/runner processes,
controller, owner thread, helper processes, workers, fixture descendants and any
support process/thread. All `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`,
`MKL_NUM_THREADS`, `NUMEXPR_NUM_THREADS` values are **1**, inherited before child
imports. Suites and scenarios remain serial. The new topology uses no
multiprocessing resource tracker or native pool. Ordinarily the session is
controller + one ownership thread + two helper interpreters; one job worker is
additional. In collected tests budget the actual outer ancestors as well. A
descendant/foreign-sentinel scenario has no simultaneous synthetic worker when
that would exceed eight; never create an extra helper session to obtain a test
seam. Record an actual process/thread census, not only nominal role counts.

Allocate **zero** GPU/device probes or attempts, model evaluations, production
controller calls/dry runs, production ledger API calls/mutations, production job
directories, setup/download/smoke jobs or scientific reruns. Disposable APIs
inside collected CPU fixtures are permitted. Standard-library file/hash/JSON/AST
and read-only git inspection are evidence work. Apply AGENTS.md's one safe
outside-sandbox retry and stop/report rules. Main stops on staging/commit failure.

## Baseline and edit boundary

Reviewed HEAD is `fdf34611c36c2480d22b156238f38c51ca0fe64b`. Validation-011
supports 75 source/config/test records, **176 methods**, **37 parameterized
methods**, **426 typed callbacks**, all passing. The complete aggregate took
**206.6836401239998 outer seconds**, recovery suite **201.52797767700395 seconds**,
leaving **93.3163598760002 seconds** below 300. This motivates the bounded
72-second new scenario ceiling; it does not guarantee a final aggregate fits.

Production changes are limited to `scripts/vipe_benchmark/supervisor.py`,
`s1_cpu_helper.py`, and one new small `s1_helper_session.py` for transport,
ownership and session state. `execution.py` may change only necessary session
construction/context plumbing. Change `tests/test_vipe_benchmark_supervisor.py`
for collected session cases and mechanical adaptation of its existing helper
fixtures; `tests/test_vipe_benchmark_s1_recovery.py` only for necessary operation
shape/ownership adaptation preserving assertions. Runner changes are limited to
the focused selector and its existing collected helper-probe cleanup plumbing.
If importable faults require a new file, use
`tests/test_vipe_benchmark_s1_helper_fixtures.py`: no independently discovered
tests there; the existing source glob must bind it. All fault entry points live
in that test module, accessible only through an explicitly injected disposable
session factory, never through a production operation/import-path option.

Keep the declaration cache, source-membership algorithm, receipt/capture
contracts, exact aggregate launcher/stdin/order, scientific fixtures and all
semantic/evidence/admission/clock guards intact. No shortened 510-row fixture,
omitted callback, weaker assertion, schema acceptance bypass or arbitrary callable
transport. New module count is derived from actual globs, not a fixed new total.

## 1. Responsive launcher and retained ownership

Replace S1's per-operation `multiprocessing.Process.start()` boundary with
**fresh-interpreter POSIX spawn into fixed importable module entry points**.
Do not call Process.start or Popen from the session monitor. Use a single retained
native joinable ownership thread to call `os.posix_spawn` for the two roles,
perform their startup identity reads, and service process census/cleanup
observations. It runs only these fixed ownership operations; arbitrary work and
sampling remain in the two independently terminable child interpreters.

The prescribed validation interpreter resolves to `/usr/bin/python3.14`.
Use its `_thread.start_joinable_thread` directly and retain the returned handle;
do not use `threading.Thread.start`, whose installed implementation waits on
`_started`. The direct primitive creates a native thread without waiting for
its Python bootstrap. Use a non-daemon joinable handle plus a session registry
that retains unfinished handles after the caller reports failure. Check this
capability before reservation; unsupported runtime fails closed, with no
fallback to blocking launch. Do not use private multiprocessing serialization,
direct Python `fork`, an untracked daemon thread, or a launcher started outside
the measured interval.

Capture `t0` **before** creating the session's channels, cancellation state,
native handle or child resources. The controller remains the monitor. Its
first and subsequent ticks cover owner-thread bootstrap, both spawn calls,
exec/import, identity establishment and ready messages. Monitor access to owner
state is nonblocking: bounded immutable records and try-lock/single-slot
handoffs, never a blocking queue/join or a lock held during a syscall. Exactly
one launch record per role exists before any OS creation:
`pending -> spawning -> pid_owned -> ready -> stopping -> reaped`, with separate
`failed`/`ownership_unknown` facts. A canceled session is permanently poisoned.

Each spawn uses fixed `sys.executable -B -m vipe_benchmark.s1_cpu_helper` argv,
the existing canonical scripts path, role/session arguments and one explicitly
inherited socket descriptor. No operation payload travels in argv, environment,
or Python bootstrap pickle. Use `setsid=True` in `os.posix_spawn` so the kernel
establishes the child's group before module imports; use explicit descriptor
dup/close actions, close unrelated descriptors, and no shell or preexec callback.
The launcher records the returned PID immediately, before fallible identity
reads, readiness, further spawn or test seam. It is the sole owner/reaper of
these direct children. Retain the unreaped leader to pin the group identity.
Record boot ID, PID, `/proc` start ticks and PGID; compare parent-observed identity
with child ready identity. Ready alone never authorizes signals to a claimed PID.

Cancellation is checked before each spawn and immediately after its return.
A canceled pending role is never spawned. If cancellation occurs during a spawn,
the returned child is immediately retained and stopped; the second role is not
started. If a spawn call has not returned by the cleanup deadline, retain the
pending record/handle as **ownership unknown**, report `cleanup_uncertain=true`
and stop-required even with no known PID. A late return must still publish its
PID and enter owned cleanup; it cannot revive readiness, reserve, run work or
start a replacement. No retry/replacement of a failed role within the attempt.

Root-boundary limitation is explicit: native thread creation, descriptor setup,
kernel scheduling and OS signal syscalls are not a hard-real-time service.
Measure their time from t0 and every monitor-tick gap. A primitive that blocks
the monitor beyond 100 ms or an unresolved launcher at the total deadline is a
**failed boundedness observation**, never an excluded startup interval or a
successful clean return. There is no claim that Python can preempt a stuck
kernel/GIL operation. Collected cases must establish responsiveness while the
actual isolated launch/bootstrap is blocked. If the chosen native primitive or
target runtime cannot support that measured contract, retain incomplete R9-2
acceptance and hand off the exact boundary; do not substitute a post-start timer.

Ownership enumeration runs in the ownership thread, not recursive `/proc` work
on the monitor. It tracks each actual helper group and descendants with their
start identities, including descendants observed before leader exit. Census
completion, errors and unknown state are explicit. Unsupported/unknown escaped
descendants are unresolved, never treated as absent. Signals target only retained
unreaped direct-child/group identities or independently verified owned descendants;
never trust a helper-reported foreign PGID. Retain the leader until descendant
accounting finishes; avoid `poll`/`wait` calls that reap it early. Use nonblocking
`waitid(..., WNOHANG|WNOWAIT)` observations and a final nonblocking reap, or an
equivalent explicit implementation preserving that order.

## 2. Fixed ready roles, lifetime and exact deadlines

One work role and one sample role are created per S1 supervision call and ready
**before reserve**. Ready carries protocol version, random session token, role,
boot ID, PID/start ticks/PGID, and the exact four thread values. Both independently
validated ready records and a valid initial sample are required before the
disposable/production reserve boundary. Readiness is separate from an operation
result. Helpers loop serially over requests; at most one work request and one
sample request, including encoded-but-unsent requests, may be outstanding.

Production pre-reservation timing is fixed:

| Bound | Definition |
| --- | --- |
| Ready cutoff | `R = t0 + 1.0`; both roles completely ready strictly before R. |
| Setup cutoff | `S = t0 + 2.0`; initial sample requested after readiness, complete and valid strictly before `min(dispatch+1.0, S)`. |
| Failed-setup cleanup cutoff | `P = t0 + 3.0`; the final second is reserved for cleanup. No reserve at/after S or after any setup failure. |
| Monitor ticks | At most 100 ms gap; default sleep at most 20 ms, clamped to earliest pending deadline. Return/report by relevant total deadline + at most one 100-ms tick; report overruns as failures. |

Fixture injection may shorten these intervals, preserving ordered absolute
cutoffs and separate cleanup reserve. It cannot increase them. A ready frame
arriving at R is late even when the descriptor is readable. Initial-sample
failure consumes no reservation; unresolved setup ownership blocks further work.

After reserve preserve the exact captured clock: `T=reservation.seconds`,
`C=min(30,T/4)`, `D=start+T`, `W=D-C`. Pass the same session across prelaunch,
worker samples, acceptance, reconciliation and publication. Initial and worker
sampling are sample-only requests; do not execute the sampler redundantly on the
work role to implement `monitored_call(sampler, ..., sampler)`.

Each work request captures a fresh dispatch time before encoding/transmission.
Reject work at/after W and any request with exhausted enclosing phase time.
Keep current publication semantics and its existing deadline inside D; this plan
does not authorize later heavy reconciliation in cleanup. All sampled phases
use the same resource peaks and real worker group for GPU ownership checks.
No helper exception is translated to permission to reserve or launch again.

Successful requests leave the fixed helpers ready for reuse. An explicitly
passed session belongs to supervise and is closed once at its terminal boundary;
`monitored_call` closes a session it created for a standalone collected call.
Mechanical existing-test adaptation must still assert eventual complete cleanup.
Any fatal session failure cancels both roles, preserves the primary exception
and attaches ordered cleanup observations; later calls on the poisoned session
fail immediately without starting new helpers.

For the existing terminal path, keep a healthy session alive through permitted
reconciliation and publication; remove its earlier unconditional reap that would
force publication to respawn. Stop the job worker using existing accounting, then
publish with the same ready roles if still healthy and within its deadline,
then retire helpers/ownership thread before returning final evidence. A failed
session cannot publish through a replacement; preserve publication failure and
the consumed stop. Helper cleanup uses TERM then KILL, with TERM grace at most
`min(0.2, remaining_cleanup/2)`, nonblocking observations and reap, all within
the applicable P/D bound. Preserve primary failure plus cleanup uncertainty.
Ledger finish's currently unmonitored I/O and full C/2+C/4+C/4 finalization are
explicit later gates; changing lifetime here does not establish their completion.

## 3. Complete bounded control transport

Use one nonblocking Unix stream socketpair per role. Both monitor reads **and
writes** are incremental; no `Connection.recv/send`, `sendall`, pickle, blocking
file operation or arbitrary callback on the monitor. Frame format is a
**4-byte unsigned big-endian payload length**, followed by strict UTF-8 JSON.
Reject length 0 or greater than **65,536 bytes** before allocating a body.
Per role retain at most one incoming frame and one outgoing frame plus a header.
Read/write at most **16,384 bytes per role per monitor tick**, one complete
message decoded per role/tick; alternate roles so a busy peer cannot starve the
other role or deadline checks. Partial header/body and EAGAIN preserve state.
EOF with any incomplete frame or an outstanding request is fatal.

Use exact primitive input types only, maximum depth **16**, maximum **4,096
nodes/items**, strings at most **2,048 code points**, integer tokens at most
20 decimal digits, and number tokens at most 64 characters. Reject duplicate
object keys, NaN/Infinity, invalid UTF-8/JSON, unknown envelope fields, excess
nesting/items and trailing messages. Enforce aggregate encoded size while
encoding, never by serializing an arbitrary object first. Preflight/encoding and
incremental lexical/depth checks have bounded steps (at most 256 nodes or 16 KiB
per tick); once the guarded complete <=64 KiB frame exists, one bounded JSON
decode and fixed schema check is allowed. This is only control decoding; never
load evidence/source JSON or hash/scan/decompress in the monitor. Measure tick
gaps including encode, decode and schema checks, and fail on observed overruns.

Every envelope has `version=1`, `session`, `boot_id`, `role`, positive monotonic
per-role `request_id` (ready uses 0), fixed `kind`, and its exact kind payload.
Request kinds are the closed operation set `resources`, `prelaunch`, `accept`,
`reconcile`, `publish`, plus controlled CPU constant injection in disposable
fixtures. Responses bind the exact outstanding request/operation. Require exact
role/session/boot/sequence equality; reject duplicates, old/future replies,
unsolicited messages, second ready and cross-role data. Do not permit operations
on the wrong role. No more than one request can occupy a role even if its socket
is currently unwritable. Timeout covers encoding, queued write, helper operation,
complete receive, validation and the fresh receipt-time decision.

Actual control shapes: config is currently 2,625 source bytes; captured
reservation/config/command and scalar/path/file-record results fit the bounded
channel subject to the collected actual-shape checks. Prelaunch returns null;
accept returns two strict file records; publication returns one. Resource data
has the existing three numeric sizes, unique positive PID list and optional
device UUID, plus trusted timing metadata. Do not send result rows, masks,
referenced-record tables or reconciliation identity/error arrays in this channel.
If actual bounded shapes do not fit, fail closed and report the exact offending
shape; do not raise frame limits or truncate evidence within implementation.

For reconciliation, the work helper runs existing `prepare_terminal_evidence`
unchanged, then writes its **entire unchanged summary** through existing immutable
`write_json`/`file_record` helpers into the existing owned job evidence directory.
Use a unique `helper-summary-<session>-<request_id>.json` envelope binding schema,
session, role, request ID and exact reservation event identity, with `summary`
holding all existing counts/identities/errors/runtime/first-result fields.
Return only its strict record plus matching correlation fields. This happens
before W and within the same work request; no new directory/allocation/controller
API. A large raw error similarly stays in an owned evidence artifact, with a
bounded control error code and verified record; do not lose its original bytes.

The supervisor carries the reference explicitly as `evidence_summary_record`;
it must not masquerade as a materialized `evidence_summary`. The same work
helper's publish adapter checks exact expected session/request/reservation and
fresh strict file bytes, expands the summary into a copy of the publication
outcome, then calls unchanged `terminal_receipt`. Finish evidence retains the
reference; receipt retains the original full summary and the reference binding.
No changes to scientific acceptance or resolver guards, and no monitor read of
the file. Tamper/missing/wrong-session/wrong-reservation records fail publication.
This final-summary transport artifact is not incremental durable progress:
a killed reconciliation before publication or failed final sample remains an
R9-4 gap. Do not claim that this step completes R9-4.

## 4. Trusted sample acquisition and post-task freshness

The sample helper wraps the real sampling call with its own monotonic readings
immediately before/after the call. It constructs acquisition metadata itself;
never accept timestamps/session/request copied from a sampler's returned value.
Raw resource values remain subject to existing strict finite nonnegative size,
unique positive PID, resource-ceiling and real-worker/foreign-PID validation.
CPU constants/fault samplers are injected only by disposable fixtures; live
`resources` retains its validation-mode guard and cannot construct a model.

For each request the monitor retains dispatch time `d` before encoding, phase
deadline `E`, sample deadline `Q=min(d+1.0,E)`, and outstanding role identity.
On full receipt and after decode record fresh receipt/decision time `r`; check
deadlines before accepting anything. Require exact finite primitive numeric
timestamps (bool/string/null rejected), nonnegative values and
`d <= acquisition_start <= acquisition_end <= r`, identity/sequence matches,
and `r < Q` and `r < E`. This makes age at receipt less than one second without
a helper-supplied age override. Check fresh monotonic time again before dispatch
or returning a task result. Readability never takes precedence over timeout.

On observing a work completion at `f`, retain its result but do not return it.
If an older sample is outstanding, drain and validate it within its original
Q/E for resource/ownership safety, but it cannot satisfy post-task sampling.
When the role is idle, dispatch a **new** sample with new request ID and dispatch
time `d_new >= f`; require `acquisition_start >= d_new >= f`. Only that complete,
timely, valid response releases the work result. A failed/late old sample still
fails the session; do not silently cancel it and relabel the old measurement.
Do not overlap samples or restart a sampler to obtain a newer value.

## 5. Collected validation and evidence

Use a literal `HelperSessionTests` class in the supervisor suite as the focused
selector. Preserve all 176 old methods/426 typed callbacks and substantive
assertions, including reservation clock/env transport, ownership peaks and
consumed cleanup stops. Adapt obsolete per-request constructor/fake cleanup
seams mechanically to the explicit owner/session interfaces. A fake cleanup
matrix remains unit evidence; real cases below supply actual lifecycle evidence.
Keep the old collected helper-probe script case; do not run it standalone.

Use **24 maximum new lifecycle scenarios** with one session each, all serial.
Do not spawn a new child for each pure framing/timestamp mutation. Assign literal
IDs and count them prospectively in the fixture; record t0/cutoffs, ticks,
dispatch/acquisition/receipt, PID/start/PGID, signals and actual cleanup result.
The exact final AST and literal callback declarations determine counts; the
following scenario IDs fix requirements, not an excuse to omit an old method.

| Scenarios | Required observations |
| --- | --- |
| L01 ready/reuse; L02 ready-before-reserve integration | Actual fresh importable interpreters under the prescribed stdin/runpy runner; both roles and all four thread values verified; repeated operations preserve exact PIDs/start identities; one outstanding request per role; initial sample before instrumented disposable reserve; no extra helper spawn. |
| L03 blocked owner bootstrap; L04 child blocked before ready; L05 failure after real spawn; L06 late ready | Tick measurement starts at t0. Block the actual isolated launcher before its spawn, and separately an actual child after exec but before ready. Inject an error only after a real returned PID exists, then late readiness at/after R. No reserve, correct retained ownership, bounded stop. Immediate fake start failure alone is insufficient. |
| L07 cancellation while spawn wrapper holds a created child; L08 late launcher completion | A wraps seam runs real posix_spawn and deliberately delays its return; the monitor must remain responsive before PID publication. Cancellation cannot lose the child or start role two. One case releases within cleanup and confirms cleanup; the other records explicit unknown ownership/stop at deadline, then releases and verifies the retained late-return cleanup path without converting the prior failure to success. Its release/retirement is inside the scenario's outer 1-second cleanup reserve. |
| L09 partial header; L10 stalled body; L11 EOF mid-frame; L12 stalled request reader | Actual child socket writes split length/body or closes mid-frame. Backpressure case uses a tiny actual socket send buffer and a legal near-limit request to a child that does not read, so the request really remains partial/EAGAIN. No send/recv blocks the monitor; tick/deadline and cleanup assertions hold. |
| L13 oversized frame; L14 malformed/replay correlation | Actual child sends oversized length before body allocation, then a separate scenario drives invalid protocol/correlation through the real decoder. Remaining malformed/typed/replay combinations use bounded in-memory decoder tests. No unsolicited message becomes readiness/work/sample success. |
| L15 sample deadline; L16 phase deadline; L17 post-task sample | Actual delayed helper response ready at/after the one-second bound and a shorter phase bound fail even if poll reports readable. L17 holds an old in-flight sample across actual work completion, verifies it never releases result, and observes a new request/acquisition after f. Valid payload-provided old/future metadata cannot override helper timestamps. |
| L18 real descendant; L19 TERM-resistant helper; L20 exit during transport | Actual helper owns a descendant and is cleaned as one retained lineage; TERM-ignore requires KILL. Child death/EOF preserves primary error. Use a real foreign sentinel group in a compatible scenario and assert no foreign signal plus sentinel survival; respect eight-worker census. |
| L21 enumeration failure; L22 signal failure; L23 reap failure | Inject at actual ownership boundaries around real owned children. Failure/unknown state is independent of survivors=[]; retain identities and primary errors. After the assertion, release the seam and perform actual bounded cleanup, recording its separate outcome. No patched empty result counts as successful cleanup. |
| L24 artifact/phase integration | One disposable session reuses work/sample roles across allowed phase-shaped operations and complete-summary reference publication. Assert exact summary counts/identities retained; missing/tampered/cross-session/cross-reservation references fail before a valid receipt. Use tiny existing evidence fixtures or existing integration fixture once, not a 510-row rebuild per mutation. |

Pure collected mutation methods cover frame bounds (0, max, max+1), split decoder
state, invalid UTF-8/JSON/duplicate keys/depth/item/scalar lengths, wrong
version/session/boot/role/request and replay, both role busy guards, encode bounds,
sample missing/bool/string/null/nonfinite/negative/reversed/future/stale/late
times, field-level resource/PID guards and exact deadline equality. Exercise
actual production validators; never patch a validator into a pass. Include real
operation-shape sizes at limits and ensure no arbitrary object serialization or
bulk evidence reaches the monitor. Controlled ticks include encoding/decoding.

Keep real scenarios quick; the maximum 72 seconds is an allowance, not a sleep
target. Collected overrun/tick failure is a failed result; do not widen tolerance,
increase caps or remove cases to fit the aggregate. Failed diagnostics are
preserved. No full controller/scientific test is rerun outside collected limits.

Final acceptance requires one fresh complete aggregate using unchanged capture
and new vacant `s1-recovery-aggregate-013-001`/`002` directories; focused
directories are `s1-recovery-diagnostic-013-001` through `003`. Exact child argv
is `.local/envs/stg-colmap/bin/python -B -`, repository cwd, diagnostic unset,
`VIPE_CPU_VALIDATION=1`, all four thread vars 1, and these exact stdin bytes
including the final newline:

```python
import runpy
import sys
sys.path.insert(0, "scripts")
runpy.run_module("vipe_benchmark.s1_validation_runner", run_name="__main__", alter_sys=True, init_globals={"STDIN_PYTHON_ARGV": tuple(sys.argv)})
```

Suite order remains `s1_semantics`, `s1_recovery`, `backends`, `contracts`,
`component_recovery`, `execution`, `budgets`, `supervisor`, `review_annotations`.
Require all AST-derived methods/callbacks exactly once, zero failures/errors/
skips/discovery errors, actual exit 0/completed wait and outer elapsed <=300.
Bind exact interpreter/argv/environment/stdin/runner/capture, complete source
pre/post snapshots, closed raw logs, receipt/wrapper chain and separate actual
tool/session completion observation. Reconcile six existing script children and
all new scenario records. No source edits after a pass without invalidating it
and using a remaining justified aggregate. Measure final outer/recovery elapsed
and headroom; no causal performance claim or speedup threshold.

## 6. Immutable lineage, audit and handoff

The PLAN transition already exists as
`s1-recovery-bookkeeping-transition-plan-013.json`, joining actual durable
status-review-013 to status-plan-013. Main owns any additional real PLAN edit and
the PLAN -> IMPLEMENT transition; preserve a durable IMPLEMENT snapshot before
dispatch, freeze its bytes during implementation and pass its exact record.

Create next-vacant correction-011 from correction-010, preserving its entire
predecessor transition prefix, original baseline/bookkeeping policy, all 38
frozen records and original ledger snapshot. Append canonical post-012 directly,
then existing actual plan-013, then actual subsequent transitions supplied by
main, each backed by exact before/after durable snapshots. No invented endpoint,
rewritten historical correction or replacement of canonical transitions.

Independent standard-library audit checks current source membership/hashes,
final AST collection, all 176 prior methods/426 typed callback identities and
preserved assertions, all complete receipts/logs/process outcomes, allocation/
prospective-note compliance, 38 frozen records, original ledger chain/accounting
and actual status lineage. Do not invoke the production validator as the only
authority or rerun an old audit against its now-false historical HEAD/status
preconditions. Fresh audit has its own predecessor and actual frozen endpoint.

Ledger remains **447 events / 332,437 bytes**, SHA-256
`2a0f66e38911b0ed029eb9dd0cf4bbd5da4a3b67abb577fbfe9ad67e6a888990`, chain head
`00cab019d73b6a3205f676b54cfb2f745f492fa5cca5c69b4567087cea62172b`, 30 prior
GPU attempts / **4,374.044265462899 GPU seconds**, zero reserved/no active job,
no S1 recovery event; preserve events 250/255/256. Inspect ledger bytes only.

Vacancy check takes precedence over review's suggested suffixes: existing
audit-012 and independent-audit-012 artifacts are already occupied. Expected
new records are validation-012, correction-011, **audit-013**,
**independent-audit-013.py**, implementation-review-011, preparation-012,
assessment-031-implement, and new iteration-013 launch/timing/process/ledger/
bookkeeping/audit-observation files. Verify each path immediately before writing;
if occupied choose the next unused suffix and link the actual record. Preserve
validation-011, correction-010, review observations-013 and every failed raw log.

Record actual stage end and evidence end UTC/monotonic timestamps, last source/
test action versus 3,300, elapsed/attempt/scenario consumption and remaining gaps.
Main separately records later handoff/commit activity; never move the start past
inspection or rewrite consumed timings. Main inspects scoped changes and artifacts,
stages explicit paths using standing escalated git approval, records full/scoped
staged checks accurately, commits the validated milestone with title/description,
then continues the active loop's next fresh REVIEW unless a true stop applies.

Retain Plan 041 strict acceptance **false**: diagnostic-011-001 lacked a successful
prospective note after failed preparation; diagnostic-011-002's synthetic worker
inherited former OMP/OpenBLAS 4. Preserve its three failed focused invocations,
failed first aggregate, immutable-log full staged whitespace exit 2 and scoped
exit 0. Corrected source does not repair historical actions. Historical P31-5,
unavailable older status/timing snapshots and short-worker evidence limits remain.

## Acceptance and remaining objective

| Acceptance | Required evidence and criterion mapping |
| --- | --- |
| A43-1 fixed startup/ownership | R13-1a/c; S1-2/S1-3 prerequisite. Responsive launch from t0, pre-reserve ready roles/initial sample, exact ownership/cancellation/late-return behavior, no replacement, measured limits and honest unknown cleanup. Actual isolated child/start cases pass; an unbounded root boundary leaves this unmet. |
| A43-2 bounded complete transport | R13-1b; S1-2/S1-3 prerequisite. Both directions, encode/decode bounds, strict correlation, actual partial frame and stalled reader cases; full evidence retained behind verified references. |
| A43-3 fresh samples/lifetime | R13-1d; S1-2/S1-3 prerequisite. Helper-acquired interval, typed identity/timing, fresh deadline decisions, one outstanding sample and actual post-task measurement; same roles through healthy publication and bounded actual retirement. |
| A43-4 complete preservation | S1-1 preservation and S1-2 validation prerequisite. All old substantive methods/callbacks plus exact new collection pass in one unchanged <=300-second aggregate; no scientific/evidence/cache weakening. |
| A43-5 truthful allocation/evidence | S1-4. Independent source/frozen/ledger/lineage/closed-process audit, actual launch notes and budget compliance, no prohibited execution, immutable prior failures and accurate handoff. |

All five are required for strict plan acceptance. Keep separate
`helper_session_milestone_complete`, `plan_acceptance_complete`,
`implementation_acceptance_complete`, `ready_for_live_admission`,
`objective_complete`; the last three remain **false** after this plan alone.
Do not infer whole R9-2/full lifecycle completion from a narrower passing subset.

S1-1 and S1-4 remain met on currently unchanged reviewed evidence; S1-2 and
S1-3 remain not met. Later gates: R9-4 incremental durable progress; R9-5 and
remaining R9-3 structured primary/secondary failures, continuous cleanup samples,
C/2+C/4+C/4 finalization, conservative charge and durable acknowledgment;
native/runtime/first-envelope and referenced-evidence matrices; actual successful
`stages.segment` progression of 510 ordered identities with 340/170 categories,
reuse and later-failure preservation; synchronized contenders, consumed replay,
registration/dependencies and full path/PID/PGID/lifecycle matrices; current
production amendment/validation/original cleaned-up failure/E1/single-attempt
authorization and registration; eventual bounded calibration and terminal evidence.

Later calibration remains one attempt at
`min(3600,93600-gpu_elapsed_seconds-gpu_reserved_seconds)>0`, with cleanup
`min(30,effective_seconds/4)` inside it; reservation consumes the attempt even
without worker launch. Preserve one exclusive GPU group, 22 GiB device memory,
eight CPU workers, 150 GiB artifacts, 60 GiB downloads, and existing 57,600-second
preparation/setup ceilings. Current ledger arithmetic permits 3,600 seconds but
is no live availability evidence. Reconstruction requires separate later
authorization. None of that live work belongs to this plan.
