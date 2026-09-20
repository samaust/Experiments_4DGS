# Plan043 implementation handoff — partial milestone validated

The final complete aggregate passes, but the full helper milestone and strict
Plan043 acceptance remain **false**. This stage consumed all three focused and
two aggregate invocations. Unused wall time does not authorize additional runs.
Main owns status and commits; neither was changed by this implementation agent.

## Changes and supported scope

The supervisor now shares one work/sample session across S1 operations. A
retained native joinable owner thread performs fixed POSIX-spawn launch,
identity/census work and child reaping. The monitor uses bounded primitive JSON
frames over nonblocking sockets, correlates role/session/request identity,
validates helper-acquired sample intervals and requires a newly dispatched
sample after observed work completion. Failure poisons a session; late launcher
returns remain owned and cannot start a replacement role.

Reconciliation writes its complete summary to an immutable owned artifact.
Publication verifies its strict record, correlation and reservation before
expanding it inside the work helper. The monitor carries an explicit
`evidence_summary_record`. This is final-summary transport, not incremental
progress or the later complete monitored-finalization protocol.

Only supervisor/helper/runner focus and supervisor test sources changed, plus
one dedicated session module and one importable disposable fixture module.
Scientific recovery fixtures, cache, validation contract, capture and suite
order remain unchanged. Existing operation/cleanup fixtures were mechanically
adapted, preserving all176 methods,426 typed callbacks and674 substantive
assertions checked independently against the explicit reviewed commit.

## Validation and actual limits

- Focused001:27 methods,3 errors. Its immutable logs show timeout classification
  and ready-before-owner-PID publication defects. These were corrected.
- Focused002:27 methods passed.
- Aggregate001:203 methods/426 callbacks; one new census failure. All176 old
  methods/callbacks passed. The census observed30 total workers, including25
  controller threads after OpenCV use.
- Focused003:29 methods passed after exec replacement of the waiting driver,
  OpenCV thread limit1 before imports, stronger reserve/census and framing cases.
- Aggregate002:205 methods/426 callbacks, zero failures/errors/skips/discovery
  errors, exit0 and completed actual tool wait. Outer206.146090159 seconds,
  recovery197.001306766 seconds;93.853909841 seconds of outer headroom.

All24 literal lifecycle scenarios ran serially per invocation, with their actual
execution/cleanup timestamps, ownership, signals, requests and sample intervals
saved alongside the receipts. Current final census is6 workers for the ordinary
session and8 with a real descendant and foreign sentinel. All four required
native thread settings remain1; the remaining invocations additionally used
`OPENCV_FOR_THREADS_NUM=1`. The exact stdin interpreter, capture and300-second
aggregate cap were preserved. There is no causal performance claim.

**Historical Plan043 CPU compliance remains false.** The original wrapper,
waiting driver, capture, runner, owner thread and roles totaled7 workers; L18
added a descendant and sentinel, deriving9 for focused001/002. Aggregate001's
actual census observed30. The final corrected topology cannot repair these
past invocations. Plan041's earlier strict exceptions and failed raw logs also
remain unchanged.

## Remaining helper acceptance

The latest assessment, assessment-031-implement.json, is authoritative for this
handoff. A43-4 preservation is met. A43-1/A43-3 and strict allocation acceptance
are not met. A43-2's passing tested subset in validation012 is refined to
**unverified for the full plan contract** by late source review:

1. Recheck S immediately before reserve after initial-value checks, and prove
   the adversarial delay between valid initial sample and reservation.
2. Prove actual completed responses that are readable at/after sample and phase
   deadlines. Current delayed-response cases time out before completion.
3. Resolve/enforce the combined per-role16KiB I/O budget: current Wire applies
   separate16KiB send and receive slices. Check response acceptance against
   completion of request transmission.
4. Strengthen persisted identity evidence across all actual controller phases
   and review fixture outer-deadline enforcement. L01 proves reuse; L24 proves
   summary adapter verification, not a complete per-phase controller PID trace.

Root native/kernel scheduling is measured, not claimed hard real time. Unknown
or failed cleanup is retained explicitly; no observed empty list is promoted to
confirmed retirement. Escaped/unobserved descendant limitations and the later
full lifecycle matrix still require review. No live readiness is claimed.

The remaining Plan036 progress/finalization, native/runtime/first-envelope,
real510-identity worker traversal, contention/replay/dependency, current
production binding and eventual separately bounded calibration gates remain.
S1-1/S1-4 are met on scoped evidence; S1-2/S1-3 remain not met.

## Evidence and preservation

- s1-recovery-validation-012.json: current sources and aggregate wrapper.
- s1-recovery-audit-013.json and independent-audit-013.py:1921 successful
  byte/AST/receipt/ledger/status reconciliation checks;77 source records.
- s1-recovery-audit-observation-013.json: current real census and sample trace
  checks, while explicitly retaining allocation noncompliance.
- correction011 retains correction010's full prefix, then canonical post012,
  PLAN013 and IMPLEMENT013 durable transitions. Frozen status stayed at its
  dispatched1042 bytes/hash throughout this stage.
- ledger-audit013:447 events/332437 bytes, original hash/head,30 historical GPU
  attempts/4374.044265462899 seconds, zero reserved/active, no S1 recovery event.
  All38 frozen records and events250/255/256 were preserved.
- process-observation013 records all five actual completed tool sessions;
  prospective notes, original/exec launch drivers, closed raw logs and scenario
  records remain available. No standalone probes or uncollected tests ran.

No GPU/device/model/setup/production controller/production ledger API operation
was performed. No permission restriction was encountered. Tracked task-source
`git diff --check` passed; main must inspect/stage explicit paths and accurately
record its full/scoped staged checks. Do not clean immutable failed-log whitespace.
Continue with a fresh authorized REVIEW/PLAN; do not reuse this plan's attempts.
