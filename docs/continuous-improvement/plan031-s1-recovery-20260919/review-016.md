# Iteration 16 REVIEW — Complete owned S1 progress within the original ceiling

Proceed to a fresh plan for **R16-1: explicit owned-workload accounting and
cohesive completion of the durable S1 progress path**. The next unused plan
number observed is **046**. The original eight-worker ceiling permits this
prospective design. Plan045's literal ancestor-count violations remain failures;
its partial source is uncommitted and unaccepted. This review grants neither
current integration acceptance nor permission to raise a ceiling.

The review follows AGENTS.md, the explicitly resumed
continuous-improvement-loop skill, and the unchanged [objective](objective.md).
It read current status/assessment037, handoff015 and its completion record,
permission/process/limitations/gates015, Plans031/036/045, Review015, the immutable
partial-source snapshot, correction013/validation014/audit015-003, and the current
progress, row, helper, supervisor and fixture source. Main owns status and git;
there was no delegation. Only saved-file/source inspection and new review
evidence writes occurred. No tests, process/device probes, model/setup/GPU work,
production controller or ledger API calls, source/status/git changes occurred.

New [observations016](s1-recovery-review-observations-016.json) bind the evidence
and source findings. Their **243 read-only consistency checks** rehash all
**78 current sources**, all **10 partial-source copies**, **38 frozen records**,
the original ledger, launch evidence and the complete saved transition prefix.
These checks establish evidence consistency, not implementation acceptance.
[Assessment038](assessment-038-review.json) records every objective criterion.

## Scope disposition comes before execution

Plan031:423 says **“At most eight workers.”** Plan036:278–279 requires the
**“whole owned workload”** to remain within eight, including monitor/helper work
and native thread allowance. These constraints support an invocation-owned
process/thread boundary. They do not impose an eight-thread limit on every
pre-existing ancestor of the execution tool, terminal and operating system.
The skill authorizes new Review-recommended, Plan-finalized plan-specific
resources within these original constraints.

Plan045 explicitly used the unchanged full-ancestor census. Its escalated
diagnostics measured **59/61** and **60/62** ordinary/maximum workers. The saved
records include Codex with **44/45 threads**, gnome-terminal-server with **7**,
and bash, user systemd and init with **1 each**. That ancestor contribution is
**54/55** threads. The remaining saved census entries total **5 ordinary,
6 with a job worker, and 7 at the observed maximum**. The in-sandbox records
show the same 5/6/7 remainder plus one sandbox wrapper, hence 6/7/8.

This decomposition is a feasibility observation. The old launch did not bind a
prospective ownership root under a new accounting policy, so subtraction cannot
retroactively certify Plan045 or prove a new run's maximum. Keep the original
records, original totals and failed assertions byte-for-byte. No new live census
ran in this review.

The fresh plan should require all of the following before allowing the new
accounting to establish acceptance:

1. Bind the invocation's root PID, start identity, process group, boot identity,
   plan/source records and output directory in the durable launch evidence.
   The exec driver becomes the unchanged capture process, retaining its PID and
   start identity. Bind any separately retained wrapper too. An executable name,
   PID alone, arbitrary environment value or current parent link is insufficient
   authority for excluding a process.
2. Count every actual thread in capture, runner, the existing owner, both
   helpers, job worker, direct-script child, descendants, fixture sentinel and
   any invocation-created wrapper/support process. Follow recursive descendants
   and retain discovered identities across reparenting or exit races. Account
   for task-created work outside the currently visible parent tree. A fixture's
   deliberately foreign sentinel is still created by validation and is counted.
3. Preserve a separate raw full-ancestor observation and explicit exclusion
   reasons for proven pre-existing control-plane ancestors above the root.
   Never exclude a task-created process by command name or because it detached.
   Preserve one conservative orchestration slot **inside eight** in addition to
   the measured owned total: the supported design is 5+1 ordinary, 6+1 with a
   worker, and 7+1 at maximum. A real wrapper's measured threads consume that
   allowance; extra retained work consumes further capacity. The plan must make
   this accounting exact so the allowance cannot hide an additional worker.
4. Treat failed enumeration, changed PID/start identity, unresolved ownership,
   unexpected thread growth or inability to prove the boundary as uncertainty
   that prevents further child dispatch. Keep retained ownership charged until
   its retirement is established. Count native/support threads using actual
   task enumeration as well as the five configured one-thread limits.
5. Observe ordinary, worker-active and maximum cases in the collected suite,
   including L18, L31/L35, all P scenarios and direct-script lifetimes. Use the
   existing owner/fixture mechanism; add no observer thread, watchdog, longevity
   run or standalone probe. Add pure negative boundary cases for forged roots,
   omitted descendants/sentinels, PID reuse, ambiguous retained work and thread
   overflow. Preserve the existing monitor's ownership and resource checks.

This is a prospective definition of the original owned workload, explicitly
saved in a new plan. It does not authorize more than eight workers and does not
repair Plan045. If the new observed owned workload plus its conservative
allowance exceeds eight, reduce actual owned concurrency within the authorized
design or stop affected execution. If ownership cannot be established, retain
that uncertainty and return it to Review. Do not hide a process or change socket
configuration to make the measurement pass.

The socket failure is separately resolved. Diagnostic001 reached
`socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)` and raised
`PermissionError: [Errno 1] Operation not permitted`. Exactly one approved safe
escalated retry of the collected operation, with unchanged source and a fresh
exclusive output index, resolved socket creation. It still failed validation;
diagnostic003 after fixture corrections still failed the CPU assertions. No
missing allow rule is identified, and no duplicate is recommended. Future
execution may request normal scoped escalation using this evidence; it is not
another retry of the old allocation. Preserve the Unix datagram protocol and
follow AGENTS.md for any newly encountered permission failure. Socket approval
does not authorize a ceiling change.

## What the partial implementation establishes

The partial source contains the actual segment row hook, structural then
semantic publication, a bounded inventory, immutable checkpoint/head writes,
credentialed notices and acknowledgments, the retained owner cache and
supervisor reference plumbing. The stopped source matches all 78 handoff
records and the ten immutable copies in
[manifest015](s1-recovery-partial-source-015/manifest.json).

Plan045 consumed **three focused invocations and zero aggregates**. The final
focused run collected **54 methods / 40 callbacks**, with **10 failures and
zero errors**. Three pure progress methods pass. All six P01–P06 instances stop
at the census assertion before their intended progress/loss boundary. Their
saved wrappers report cleanup, but that does not establish the planned failure
behavior. No source changed after diagnostic003.

Completion timing is **1,596.4484101209964 / 3,600 seconds** in
[handoff completion015](s1-recovery-handoff-completion-015.json); the earlier
timing artifact's 1,570.499571495995 seconds ended before final handoff readback.
Both observations remain. The Plan045 allocation is closed. Its unused wall
time and two unused aggregate slots cannot be reused by a successor plan.

All **221 old methods / 426 old callbacks** and every actual old assertion are
preserved; partial current source has **230 methods / 466 callbacks**. Preserve
these new tests too and strengthen inadequate cases. The supplied Plan045
planning count **840** differs from the independently observed **836 unittest
assertion calls + 2 bare asserts = 838** inside test methods. Counting all class
methods gives **891 + 5 = 896**. No old assertion was lost. Retain both the
supplied figure and its measured correction, with per-method AST evidence;
do not fabricate two assertions to reconcile the totals.

HEAD `ebf9d9ad39c25b5732fadefcdc36cb71e0bde613` and Plan044's passing
221-method/426-callback aggregate at **213.69664305300103 seconds** are historical
baseline evidence. Changed source invalidates a claim that this aggregate
accepts current whole-suite integration. Historical Plan041/043/044 strict
acceptance remains false, with its recorded prospective/thread/CPU/log-whitespace
and cleanup/outer-completion exceptions. Plan045 strict and technical acceptance
also remain false. Preserve older P31-5 and unavailable snapshots.

## Finish the actual path, including concrete source gaps

R16-1 advances the existing R15-1/R9-4 prerequisite for **S1-2 and S1-3**, while
preserving **S1-1 and S1-4**. The new plan should complete the following connected
work under the original Plan045 progress contract; a census-only pass would
leave the main source defects open.

- **R16-1a — Bind worker authority and the closed inventory.**
  `s1_evidence.py:235` does not consume an acknowledged worker snapshot. Its
  fallback always seals a unique variant as reconcile authority.
  `s1_progress.py:272` validates only the record shape of a claimed worker
  reference; the consumer does not resolve it against the exact acknowledged
  worker seal. Pass an independently trusted worker checkpoint/seal into this
  path, reuse only the same version, and record conflicts without erasing a
  uniquely established authority. Conflicts always prevent complete acceptance;
  without authority, exclude all conflicting variants. At
  `s1_progress.py:537`, bind the supplied result rows to the exact result bytes
  and close a bounded inventory snapshot. Final readback currently covers only
  row-file records. Define how observed membership/content changes invalidate
  that closed coverage. Retain acknowledged worker progress when closure fails.
- **R16-1b — Carry acceptance, first-result and runtime state through the
  independent cache.** The real `accept` operation in `s1_cpu_helper.py:20`
  returns without a progress publisher. The complete branch in
  `s1_recovery.py:512` builds an ordinary summary but does not populate publisher
  rows or its acceptance reference. Finish this state flow after the existing
  real guards and before the final sample. A failed final sample remains a
  failed operation even if complete row verification finished. Define one
  bounded summary adapter and merge rule: `s1_cpu_helper.py:72` currently
  recovers independent progress and then unconditionally overwrites it with the
  ordinary helper-summary document. `recover` supplies raw first/runtime
  references while the receipt path expects status/value envelopes. Ordinary
  compatibility metadata must preserve acknowledged progress and cannot erase
  first/runtime evidence, weaken unknown totals or invent complete acceptance.
- **R16-1c — Complete strict metadata and bounded publication behavior.**
  Finish exact primitive and enum validation for nested context, checkpoint,
  head, notice, ack and compact reference fields. Current equality comparisons
  alone do not enforce all required types; runtime keys are open-ended and cold
  recovery does not check the head schema value. Distinguish damage to optional
  unacknowledged newest evidence from changed accepted metadata or conflicting
  authority. Use actual bounded write/flush/fsync/install/directory-fsync/readback/
  notice/ack boundaries in the fault matrix. Preserve current/previous accepted
  references, cancellation priority, source/request/reservation/producer binding,
  queue/generation/byte limits and the absence of extra processes or threads.
- **R16-1d — Preserve original deadlines and actual failed outcomes.**
  `supervisor.py:320` has no fresh W check after mailbox installation and before
  Popen. `stages.segment` can return from native work and start row serialization
  before the progress hook observes W. Add the required checks before new launch
  or expensive serialization and collect before/equal/after-W behavior. Verify
  independent cache retention through helper death, publication interruption,
  blocked owner read and failed final sampling, including the actual supervisor
  exception/outcome. Freeze prevents late cache advancement. Poisoned publication
  stays explicitly unavailable with no fabricated receipt and no replacement
  helper. Full R9-5 finalization remains a later gate.

The exact source records and line references for these findings are in
observations016. They are source findings, not newly executed failure results.
The planner must preserve Plan045's finite candidate/checkpoint/generation/
control/diagnostic bounds and first/native scientific guards when finishing them.

## Bounded validation and fresh resources

Recommend **5,400 wall seconds** for the new IMPLEMENT stage, beginning with
actual UTC/monotonic readings before its inspection. End source/test work at
**4,800 seconds** and reserve **600 seconds** for evidence and full handoff.
The larger stage allowance covers the enumerated unfinished integration and
fault/authority matrix. It is a fresh development-stage allocation under the
skill's standing approval; it does not extend Plan045, change an invocation
deadline or move a scientific allocation. The new PLAN must finalize the scope,
and main must compare it with all remaining applicable ceilings before dispatch.

| Resource | Recommended new plan limit |
| --- | --- |
| Focused collected invocations | At most 3, each complete outer timeout 120 seconds |
| Full aggregates | At most 2, each unchanged complete outer timeout 300 seconds |
| Existing scenarios | L01–L36, serial, each 2 execution + 1 safety cleanup seconds |
| Existing partial progress scenarios | P01–P06, serial, same 2 + 1 seconds; no additional real-child scenarios |
| Combined scenario allowance | 42 scenarios / 126 seconds inside the tighter invocation limit |
| Existing direct-script children | All 6, serial, each 10 execution + 2 cleanup seconds / 72 combined |
| Total owned CPU workers | At most 8, including actual support/native threads and conservative orchestration allowance |
| GPU/device probes or attempts, model evaluations | 0 |
| Production controller/dry-run/ledger APIs or writes, production job directories | 0 |
| Setup/download/smoke/scientific reruns, profiling, longevity, standalone probes or split aggregate | 0 |

Reserve one aggregate for final current-source acceptance. Another aggregate
requires a prospectively saved source change or concrete invalidating concern;
an unchanged passing timing rerun is not allocated. Require full-timeout fit
checks against the 4,800-second execution cutoff after all durable launch
preparation, retaining the final aggregate and 600-second handoff reserves.
Every launched invocation, including a launched permission retry, consumes a
slot. Unused time does not create more attempts.

Use the unchanged collected HelperSessionTests diagnostic selector. Complete
the missing pure cases in that class with literal typed callback declarations:
strict primitive/binding changes, authority reuse and late conflicts, result-only
and interrupted inventory, aliases/foreign paths, every finite capacity,
credentials/replay/regression/queue behavior, accepted versus optional metadata
damage, semantic failure after produced authority, runtime/first/complete state,
publication faults and exact deadline equality. Reuse small numerical fixtures
and the real guards; do not build a full 510-row fixture per mutation.

Reach **each** P01–P06 boundary: real worker progress then W, interrupted
reconciliation after an acknowledgment, real helper death before response,
completed work then failed final sample, interrupted second publication after
generation one, and blocked owner read with freeze before late return. Record
the real original cutoff, guard/durability/notice/ack ordering, exact identities
and category counts, cache and failed outcome, tick/census observations and
unconditional cleanup. Neither a method being collected nor its scenario
wrapper's cleanup proves it reached that boundary. No next scenario starts
while known owned work remains live or ownership is unresolved.

Preserve the capture, runner, discovery/order, control-frame budgets, scientific
configuration, native behavior and the complete old aggregate. Set
OMP_NUM_THREADS, OPENBLAS_NUM_THREADS, MKL_NUM_THREADS, NUMEXPR_NUM_THREADS and
OPENCV_FOR_THREADS_NUM to 1 before imports from the first invocation. Update
only the new exec-driver/fixture accounting and the enumerated progress paths
as required; retain all old substantive assertions and the new partial tests.
Require the final whole current-source aggregate to pass without failures,
errors, skips or discovery failures, with actual outer completion, unchanged
pre/post sources and elapsed at most 300 seconds. Historical timing is not a
guarantee that the new work will fit. A failure or exhausted allocation requires
an honest partial handoff rather than smaller scientific fixtures or extra runs.

Before every launch exclusively write, fsync, close, read back and hash the
prospective command/environment/stdin/source/status/time/attempt/root evidence.
Preserve actual outer tool start and completion from the first invocation,
closed paired logs, failed launches, declarations, source maps, ownership and
cleanup. A fresh read-only evidence audit may inspect file/AST/git bytes without
importing production or executing old stale audit scripts. Main handles any
completed, validated local milestone commit and continues the loop.

## Objective assessment and preserved later gates

**S1-1 remains met in its narrow preserved semantic scope.** The amendment and
native assignment/threshold/model source remain bound; old direct guards and
assertions remain intact. Current progress integration and runtime readiness
are unverified. **S1-4 remains met** for preserved frozen artifacts, ledger and
history. **S1-2 and S1-3 remain not met**: no current production authorization,
admission or calibration recovery exists, and the progress prerequisite is
incomplete.

The ledger remains **447 events / 332,437 bytes**, SHA-256
`2a0f66e38911b0ed029eb9dd0cf4bbd5da4a3b67abb577fbfe9ad67e6a888990`,
head `00cab019d73b6a3205f676b54cfb2f745f492fa5cca5c69b4567087cea62172b`.
Its 30 historical GPU reservations consumed **4,374.044265462899 seconds**;
zero are reserved, no job is active and no recovery event exists. Original
failure/accounting events 250/255/256 and all 38 frozen records remain exact.
The saved cleanup scope reports no known live task-owned work; this review did
not run a fresh host census.

Correction013 and validation014 remain immutable. Preserve their complete
28-transition prefix and append the actual canonical
[IMPLEMENT015-to-REVIEW016 transition](s1-recovery-bookkeeping-transition-review-016.json).
There is no Plan045 postcommit transition. The next correction must use this
real branch and then main's actual durable PLAN016/IMPLEMENT016 transitions;
never reconstruct a status snapshot or relabel a failed plan as committed.

After this CPU milestone, retain full R9-5/remaining R9-3: primary and ordered
secondary failures; continuously monitored cleanup, publication and finalization;
C/2+C/4+C/4; conservative charged cutoff and timely durable acknowledgment;
complete first/native/receipt/finish/ack ordering, including actual loss paths.
Also retain the remaining native/runtime/reference mutation matrices, real
510-row worker traversal and 340/170 split, first/later-failure progression,
synchronized admission/registration/reservation and lifecycle matrices, and
current production authorization bound to the amendment, current validation,
original cleaned-up failure and E1 qualification/assets.

Later calibration is still one reservation-consuming attempt, at most
3,600 GPU seconds, with effective
`min(3600,93600-gpu_elapsed-gpu_reserved)>0` and
`min(30,effective_seconds/4)` cleanup inside it. Preserve exclusive device use,
22 GiB memory, eight CPU workers, 150 GiB artifacts, 60 GiB downloads and
applicable 57,600-second preparation/setup ceilings. Reconstruction requires
separate later authorization after calibration review.

There is a concrete authorized next PLAN step; no new user scope or ceiling
approval is required for the fitting recommendation. Implementation waits for
that saved decision-complete plan and main's ceiling comparison. Objective
completion and live readiness remain false.
