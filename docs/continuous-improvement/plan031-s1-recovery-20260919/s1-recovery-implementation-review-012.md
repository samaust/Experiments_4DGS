# Plan044 implementation — collected helper boundaries

The final CPU aggregate passes **221 methods / 426 exact typed callbacks** in
**213.69664305300103 seconds**, with **86.30335694699897 seconds** below its
unchanged 300-second capture limit. Its inner elapsed is 213.54975955199916 seconds.
The independent standard-library audit passes **1,811 checks**. It preserves all
**205 previous methods / 771 substantive assertions / 77 source members**, all 38
frozen records, and the original 447-event ledger. There is no causal performance
claim. Source bytes were not edited after the final passing aggregate.

[Validation013](s1-recovery-validation-013.json),
[audit014](s1-recovery-audit-014.json),
[assessment034](assessment-034-implement.json), and
[final capture](s1-recovery-aggregate-014-002/execution.json) contain the closed
bindings and exact observations. Main owns the status transition and git work.
The IMPLEMENT status remained frozen. This subagent made no git writes.

## Implemented technical boundaries

| Acceptance | Implementation and collected evidence |
| --- | --- |
| A44-1 | The final S1 guard checks healthy retained helper identities and accepted initial sample, then captures fresh time directly before reserve. L02 delegates to actual supervise/reserve; L25 delays the actual boundary past S; L26 injects exact S at that guard. Both rejection cases make zero reserve calls and retire within original P. |
| A44-2 | Each role uses one 16384-byte combined send/receive/successful-peek allowance, with cumulative bounded counters and independent direction alternation. Request identity precedes encoding, and transmission start/final-send observations are retained. Any byte observed during a turn begun unfinished is rejected, including a post-final-send observation. L27/L28 use real early child replies; pure duplex/same-turn/exhaustion/rollover controls supplement the preserved framing/schema/reference cases. The same-turn rule intentionally rejects an ambiguously fast honest reply. |
| A44-3 | Every sample retains its original dispatch/deadline while obtaining fresh immutable pre/post census records. Records bind boot/session/request/worker generations, exact roots and bounded worker/helper lineages. Candidate readings are released only after bracket/identity checks and a fresh final decision. L29/L30 use complete real framed responses and a local decision-clock observer to reject equality without pausing real ticks. L31–35 cover live and unreaped workers, foreign ownership, a blocked census after success, enumeration failure even for empty GPU values, and child survival. Active S1 consumes WNOWAIT-qualified snapshots; it does not scan /proc or reap its pinned worker. Authority is retired before existing terminal stop_group. |
| A44-4 | Constructor state exists before fallible work. Known no-start closes acquired descriptors directly; ambiguous native launch remains retained even without a handle. Actual capability/owner/native/socket/Wire failures preserve the primary exception, and final L36 proves an acquired child before ambiguous failure and separates later safety cleanup. Events/ticks/signals/errors have the planned 256/128/128/32/32 capacities; counters saturate, request/generation identifiers fail before wrap, and fairness uses independent bits. The existing successful controller delegates actual operations while recording one exact helper pair through all nine phases. Fixture action/safety cutoffs are fixed before construction; final per-call records enforce tighter original deadlines plus one 100-ms tick. |
| A44-5 | Final full aggregate passes every original method/assertion/callback plus 16 collected methods. Five allowed source files changed; capture, contract/cache, scientific fixtures/implementation, admission schemas and receipt semantics remain unchanged. |

The [raw controller phase trace](s1-recovery-aggregate-014-002/controller-phase-trace.json)
and [derived request intervals](s1-recovery-phase-intervals-014.json) bind initial
sample, reserve guard/call, prelaunch, worker sample, acceptance, reconciliation,
publication and retirement. This remains the existing synthetic 510-row controller;
it does not establish full real `stages.segment` traversal.

## Procedural exception and consumption

**A44-6 is not met, and strict Plan044 acceptance remains false.** Diagnostic001
passed 44 of 45 methods but L31's failed outstanding sample caused worker retirement
to raise before its fixture safety stop. The 10-second sleeper could overlap later
L35, implying a possible 9-worker topology. Its per-scenario worker cleanup and
first-run eight-worker compliance cannot be certified. The initial saved census
omitted that carryover possibility. Terminal invalidation and unconditional fixture
safety stop were corrected; subsequent census includes all direct controller
children. Final observed totals are 6 ordinary, 7 with a worker, 8 for L18/L35, and 7
in the actual controller worker phase. Those later observations do not repair the
first execution.

The first diagnostic's outer tool-session identifier/completion was not retained;
its actual captured runner wait, returncode 1, closed logs and scenario records
remain saved. Every later invocation has retained actual tool exit observations.
[Procedural observations](s1-recovery-procedural-observations-014.json) and
[process observations](s1-recovery-process-observation-014.json) preserve the limits.

All **three focused120-second slots and two aggregate300-second slots are used**:
diagnostic001 failed; diagnostics002/003 and aggregates001/002 passed. Every launch
had an exclusive fsynced/readback-verified prospective note, exec-start evidence,
all five native thread settings at 1, and a fresh full-timeout fit check. The driver
exec-replaces capture from the first invocation. Aggregate002 was justified by
[saved concrete coverage concerns](s1-recovery-second-aggregate-concern-014.json)
after aggregate001 passed; it was not a timing rerun. Unused wall time authorizes
no extra invocation. All36 serial scenarios fit their 2-second action / 1-second
cleanup / 3-second total fixture limits; the failed diagnostic's skipped job-worker
cleanup is separately retained rather than inferred away from helper-only records.

There were zero GPU/device/model operations, production controller or ledger API
calls, setup/download jobs, scientific reruns, standalone probes, status writes,
git writes or nested delegation. Only collected disposable CPU fixtures ran.
No sandbox/permission failure occurred.

## Preservation and remaining work

[Correction012](s1-recovery-baseline-correction-012.json) preserves correction011's
entire prefix and directly appends canonical post013, actual PLAN014, then actual
IMPLEMENT014. Both durable snapshots at every new transition verify. Status remains
1019 bytes, SHA256 `b04262f59175ce0ba66e9fe97097b08968d8f67dd4a81d245621833087c9bdef`.
The ledger remains 332437 bytes  / 447 events, SHA256
`2a0f66e38911b0ed029eb9dd0cf4bbd5da4a3b67abb577fbfe9ad67e6a888990`, with 30 historical
GPU reservations, 4374.044265462899 GPU seconds, zero reserved and no active job or
S1 recovery event. Original events 250/255/256 are exact.

Historical Plan041 and Plan043 strict acceptance stays false. Plan043's 9/30-worker
violations, 25 controller threads, final 6/8 census, 1917.37397633199-second recorded
wall duration and consumed 3+2 slots remain unchanged. Plan041's missing prospective
note, earlier thread inheritance and full immutable-log whitespace exit 2 remain
beside scoped checks. Older P31-5 and unavailable historical snapshots remain
limitations. No allocations were reset or transferred.

S1-1 and S1-4 remain met; S1-2 and S1-3 remain not met. Technical A44-1–5 acceptance
is separate from the all-six helper milestone, which remains false because of
A44-6. The [remaining gates](s1-recovery-remaining-gates-014.json) preserve durable
progress, structured continuously monitored terminal finalization, full native
matrices, full real worker traversal, contention/lifecycle matrices, current
production binding, and later separately bounded calibration. No live readiness
or production admission is asserted. The next authorized activity is main review
of this evidence and a fresh REVIEW after its commit checkpoint.
