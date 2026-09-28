# Plan066 — exact resource sampling and append-only source requalification

The user approved expanding Plan065 to optimize and requalify the sampler and
revise its registered source binding. The existing authorization for one S1
calibration GPU attempt (3600 seconds, no reconstruction) remains in force.

1. Profile the real storage snapshot and preserve exact accounting semantics.
   Replace per-file Path construction and repeated classification with a fresh
   string-keyed inventory and indexes collected in the same traversal. Keep
   inode deduplication, all receipt/progress charges, concurrent-change retries,
   symlink/prompts exclusion, and fresh metadata on every request.
2. Validate accounting fixtures and equivalence against preserved old code.
   Measure the actual host helper path, including startup, resource queries,
   IPC, ownership and cleanup, against the unchanged one-second sample deadline.
3. Add a single append-only source-requalification event after the existing
   registration and before any reservation. Preserve the original authorization,
   admission, registration and request. Bind old/new validation, changed source
   records and old source snapshots, explicit user approval, and registration
   identity. Reject duplicate, late, unrelated or incomplete amendments. Bind
   the new event into reservation evidence and terminal receipts.
4. Run the complete timed source-validation aggregate and the owned no-timeout
   validation on final bytes. Preserve actual tool/session provenance; do not
   manufacture a pi-session or Codex-session receipt.
5. Commit validated implementation, append the requalification event only after
   all checks pass, then run the single approved allocation once. Audit its
   terminal evidence and cleanup and commit the observed result. Do not replay
   a consumed attempt or reset any historical budget.

The original 447-event ledger prefix and the existing 449-event admission/
registration history remain intact. The model algorithm, assets, inputs,
annotations, GPU limits, monitor deadlines and scientific recipe do not change.
This plan is the explicit source-change exception to Plan064/Plan065.

## Sampler validation milestone

The original snapshot took 2.98–3.06 seconds. Profiling identified Path
construction/hashing and repeated whole-inventory classification as avoidable
costs. Fresh string paths and traversal-time indexes reduce direct host resource
calls (including GPU queries) to 0.8595–0.8824 seconds with identical byte totals.
Five consecutive full supervised initial samples passed the unchanged request
deadline; total calls including setup/cleanup took 1.0525–1.0917 seconds.
All 32 accounting tests passed, including nested scopes and fresh mutation
charges. The host timed aggregate passed 252 tests in 209.96 seconds at a
240-second cap; the preceding sandbox run is preserved as a socket-denial
failure, not treated as validation.

## Codex validation compatibility correction

The original Codex owned-session driver was invoked with real bootstrap,
readiness, and same-handle tool observations. Its first owned aggregate exposed
an existing rejection of `subprocess.PIPE`/`DEVNULL`/`STDOUT` sentinels as negative
file descriptors and a byte-versus-text argv assertion inconsistent with the
owned launcher's intentional byte normalization. Correcting this descriptor
boundary and its tests is necessary for the requested Codex requalification.
The additional changed source is `s1_helper_session.py`; retain real-FD identity
checks and rejection of arbitrary negative descriptors. No process ownership,
resource ceiling, session provenance, or deadline checks may be weakened.

The owned aggregate also exposed a creator check that rejected a registered
child's own helper thread. Validate creators against the live anchored process
incarnation graph, including creation order, PID birth identity and retirement,
instead of restricting them to two top-level PIDs. Keep the rest of the typed
root/descendant and parent checks. Synthetic worker fixtures decode the frozen
OS argv at the Python boundary and emit the runtime records a real worker emits.

The third owned run reached the controller but stalled during retirement:
`Owner.signal_group` was still using the expired three-second startup deadline
after reservation. `supervise` now binds the reservation cleanup deadline to that owner,
capped by the existing fixture safety deadline. `Session.close` bounds its own
wait without shortening the owner's active cleanup budget. No
reservation, startup, sample, work, or total deadline is extended. That failed
run required recorded manual pidfd cleanup of its exact helper and runner;
all bound processes were subsequently confirmed absent. Its failed logical
sidecar is preserved, never certified as a successful retirement.

The fourth owned run passed the controller and then exposed descendant pidfd
retirement selecting the ancestor root's owner handle, unavailable in the
child process. Close with the descendant's own retained token, matching the
owner recorded when it pinned the descriptor. The real nested helper probe is
the regression check. Preserve the failed run and its exact manual cleanup
records; neither failed aggregate qualifies the implementation.

The fifth aggregate confirmed the descendant owner fix but exposed fixture
checks that selected both a process and its thread by PID alone, plus a race
between `/proc` visibility and descendant creator acknowledgement. Select
process handles explicitly and wait for acknowledgement within the same test
deadline. Include those two existing fixture/test files in source requalification.
Repeated parsing and validation of unchanged ownership-ledger lines also took
about 28–31 ms per read, contributing to the 100 ms monitor tick overruns.
Memoize successful validation by exact line bytes (bounded cache); always reread
the ledger, return newly decoded rows, and check sequence/hash links every time.
Changed bytes, malformed JSON, mutations and incomplete chains still fail closed.
Warm reads of the preserved failing ledger took 3.8–5.7 ms after this change.

The sixth aggregate passed the nested probe and initial monitor scenarios.
Its remaining first failures identify parent retirement before closing its own
pidfd, repeated cleanup consulting already-closed descriptors, and helper tree
cleanup signalling only the leader. Correct ordering and include only explicitly
registered, acknowledged descendants in identity-bound tree signalling and
terminal pidfd checks before reaping their direct parent. Include `supervisor.py`
in the source amendment. Another injected worker assertion now compares OS argv
bytes consistently. The late-return fixture uses 0.5/0.6/0.7-second internal
cutoffs and holds the actual spawn return beyond cleanup, so the real Codex
creation gate can run; the production 1/2/3-second caps and the scenario's
2-second action/1-second cleanup limits remain unchanged.

The focused owned diagnostic confirmed tree cleanup and exposed short waits
incorrectly shortening the active cleanup budget. Bind that budget once at
reservation; leave short close calls as wait windows. The admission-boundary
fixtures use 0.5/1.0/1.5-second internal cutoffs so they reach the intended
post-sample injected delay, all within unchanged production/scenario caps.
Temporarily narrow diagnostic collection to the affected six cases to shorten
the debugging loop; this is not qualification, and restore the original runner
before final full aggregate/source validation.

The narrowed diagnostic passed all six affected cases (owned diagnostic019).
L35 now passes an actual stable full process identity after matching the census
incarnation; L36 restores and binds only the exact native handle retained by its
fault injector, preserving the production ambiguous-start failure. L36 uses the
same 0.5/0.6/0.7-second fixture cutoffs. The temporary runner filter is removed;
final qualification must collect the complete original suite.

## Final ownership corrections and qualification requirements

Native `NativeNotStarted` failures now retire only the unbound H reservation
with a typed creator-bound non-start event. Ambiguous starts remain charged.
`Popen.poll()` may have already reaped an exact retained child; record its
same-handle wait before logical retirement. Keep cleanup pin state in a module
registry so test instrumentation cannot accidentally replace it with a mock.
The serial final-sample facade bypasses kernel creation at the actual creation
boundary and must not register its own PID as a child.

Production cleanup remains bounded by the original reservation. Fault fixtures
record the end of action before releasing their injected block and reclaiming
retained owners. Their existing two-second action, one-second cleanup and
three-second total limits remain enforced. Owned diagnostic025 passed all
eight constructor/progress/final-sample cases; all payload processes and handles
were retired. The temporary diagnostic filter has been removed byte-for-byte.

Only a passing full owned aggregate, a passing 240-second timed aggregate,
exact historical/current sampler and ledger-reader comparisons, five successful
host supervised samples, and the full prospective binding validation qualify
the final implementation. Earlier failed runs remain diagnostic evidence;
the earlier 252-test timed pass does not qualify later source changes.
Final source records and observed results are recorded in
`docs/continuous-improvement/plan031-s1-recovery-20260919/requalification-066/review.md`.

The full owned aggregate007 exposed replay costs that grew with historical
ownership events. Its first cleanup waits timed out; later capacity/descriptor
failures followed retained owners, so the run does not qualify the sources.
After suite completion, exactly two still-present bound processes were stopped
through identity-checked pidfds. All bound processes are absent; the unsuccessful
logical sidecar remains unchanged.

State replay now reuses a private immutable serialized snapshot only when freshly
read ledger bytes match its exact prefix. New suffix lines still receive full
canonical/hash/chain and state-transition validation; truncation, changed prefixes,
and invalid suffixes never inherit the cached state. Returned states are freshly
decoded and mutation-isolated. Appends retain locking, exact readback, rollback,
and poison handling. All 1449 successive states of aggregate007 matched full
replay exactly; repeated complete-state reads fell from 17.18 ms to 3.37 ms.

Aggregate008 confirmed the earlier cleanup-cascade correction but did not pass.
Pure creation-fault fixtures were still reserving real B slots for intentionally
fake syscalls; disable the logical kernel-handle ledger only inside those existing
synthetic controls, retaining their common dispatch/registry assertions and all
real owned scenarios. Generic production spawn failures remain conservatively
charged. Correct the one state-reader mock for its new state-returning interface.
The private replay cache serializes its validated primitive graph with `marshal`
to reduce copying costs; it never loads binary state from a file or a caller.
Aggregate008 exited with no surviving bound processes; its six synthetic,
unbound reservations remain in its failed sidecar and are not certified retired.

Aggregate009 reached the final supervisor tests with two failures. Preserve the
unreaped parent with `waitid(WNOWAIT)` in the owned non-S1 monitor path so its
registered descendants can be pinned/signalled before the existing matching-wait
rules prohibit further signals. Defer the supervisor's interruption exception
only across creation/binding until its returned handle is retained, then deliver
it immediately; otherwise an interruption in that interval can orphan a bound
child from the supervisor's cleanup variable. Keep signal masks unchanged.
Remove P04's redundant post-reconciliation publication (the inventory already
has an acknowledged durable final checkpoint) before its injected sample fault.
One more pure prelaunch deadline fixture gets the same synthetic-ledger isolation.
Diagnostic026 passed the three actual regressions and retired every payload
process/handle; restore the original runner before full qualification.

Aggregate010 passed all 258 tests in 342.93 seconds with all payload processes
and handles retired. Its final execution validator rejected the candidate hash
already emitted by the fixed capture script, because `validate_creation` still
required the older field set. Require that hash, validate its exact type/format,
and compare it with the durable runner reservation's candidate hash. Add null,
malformed and mismatched-hash rejection to the existing full receipt-graph test.
The preserved aggregate010 creation, creator graph and terminal state pass those
targeted checks, but final qualification must rerun on the corrected validator.

Aggregate011 was rejected by the unchanged 100 ms monitor-tick guard during
the synthetic controller's reconciliation. Idle phase boundaries already reset
the timer; no guard change or inferred cause is justified by that observation.
All its payload processes and handles retired. Keep this failure visible and
rerun the unchanged final sources after the independent timed and host checks.
The final timed aggregate003 passed 258 tests in 206.99 seconds (240-second cap)
and both receipt validators passed. Three complete sampler snapshots matched
the preserved original implementation exactly. Five direct host resource reads
took 0.793–0.804 seconds; five complete supervised calls took 0.989–1.011 seconds
including setup/cleanup, each passing the unchanged one-second request deadline.
The live ledger remained at its original 449-event registered state.

Aggregate012 passed the previously affected controller but P04's disposable
1.4-second allocation expired after producing both rows and qualifying only one,
before its intended final-sample fault. Give that fixture 1.6 seconds within the
same two-second action/one-second cleanup/three-second total caps. All other
fixture allocations, production monitor deadlines and the 3600-second GPU cap
remain unchanged. Requalify the changed test bytes; timed003 is historical until
replaced by the final timed004 pair. The sampler and replay implementations did
not change after their completed differential/host audits.

Aggregate013 passed the revised P04 fixture but again hit the unchanged 100 ms
monitor-tick guard in acceptance/historical-authority reconciliation. All
payload processes and handles retired; the original live ledger was unchanged.
Diagnostic027 failed before launching a test payload because its recorded
sources differed after temporary timing instrumentation was added. Diagnostic028
passed the isolated acceptance fixture (33.07 seconds), and diagnostic029 passed
all 49 recovery tests (138.63 seconds). Timing instrumentation found no monitored
call exceeding 25 ms in either diagnostic, so no cause for the intermittent
aggregate guard failure is established. Preserve those failures and do not claim
that diagnostics prove timing reliability. The original full runner is restored
byte-for-byte before final qualification; no runtime guard was relaxed.

Timed004 passed 258 tests in 227.064 seconds and both receipt validators passed,
but aggregate014 failed acceptance's monitor guard plus L07, P04/P06 timing and
native-cache accounting. All payloads retired. Diagnostic030 reproduced the
monitor failure: a generation-2 collection in the helper-owner thread reclaimed
717,359 objects in 191.72 ms, matching a 192.27 ms monitor gap. Receipt mutation
fixtures leave large cyclic mock/exception graphs; collect them after their
registered fixture cleanups rather than inheriting them in the timed controller.
This is test cleanup, not runtime GC suppression or a monitor deadline change.

The native-cache failure exposed a separate sample/exit race. A non-S1 worker
can write after the resource sample and exit before the next exit observation.
Require a post-exit sample through the existing ceilings/ownership checks before
acceptance. The existing cache test now deterministically releases the writer
only after the first worker sample and observes its exit without reaping it;
it passed with the fix. Give the held-spawn fixture 0.6 seconds total instead of
0.3 for its real registered-child cleanup, within the unchanged outer caps.
Restore the original runner and requalify these final source bytes. Timed004 is
preserved historical evidence; the final wrapper will use timed005 or later.

Aggregate015 passed acceptance, held-spawn cleanup and deterministic final-cache
accounting. P01/P04/P06 reached their intended faults but exceeded the fixture's
action timer because it started cleanup timing only after supervise had already
retired helpers. Record the first actual Session.close invocation as the action
end; all subsequent supervisor and safety retirement remains charged to the
unchanged one-second cleanup and three-second total caps. A later finally block
cannot move that boundary forward. Diagnostic031 passed P04/P06 with all payloads
retired. Aggregate015's failed observations remain preserved, and the full runner
is restored before aggregate016. No production deadline or GPU budget changed.

Aggregate016 passed all 258 tests in 357.242 seconds; validate_inner and
validate_execution passed, all payload processes/handles retired, B=0/H=1 at
capture, and all bound payload PIDs were absent. Timed005 then exposed a
non-owned-only regression: Popen.poll reaped the worker before the new final
sample, losing its GPU ownership identity. Extend the existing owned WNOWAIT
exit path to non-owned workers too; cleanup still performs the actual wait.
Both deterministic post-exit tests passed in a non-owned host invocation and
in Codex-owned diagnostic032, which retired all payloads. The edit does not
change the owned branch that passed aggregate016. Final qualification combines
that full owned result, targeted diagnostic032, and the complete timed006 suite
on final bytes; no redundant full owned rerun is needed for that branch extension.

Final timed006 passed all 258 tests with zero failures, errors or skips in
218.019 seconds under the unchanged 240-second cap. Both receipt validators
passed. The final review records owned aggregate016 plus targeted diagnostic032,
final timed006, exact sampler comparisons, replay differential checks and host
samples. Freeze this plan/review before preparing the 78-source wrapper and
10-source amendment. The original 449-event ledger remains byte-identical;
registration and the single approved dispatch will be recorded separately.
