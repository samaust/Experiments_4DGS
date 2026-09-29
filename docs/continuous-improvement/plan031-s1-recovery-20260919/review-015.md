# Iteration 15 REVIEW — Retain verified progress through interruption

Proceed to a fresh bounded CPU plan for **R15-1: durable incremental S1 evidence,
with a bounded handoff that survives helper loss and a failed final sample**.
This advances R9-4 and the S1-2/S1-3 prerequisites. The next unused plan number
observed is **045**. Plan044's committed technical changes are supported; its
strict acceptance, live admission, and the main objective remain incomplete.
A later successful plan cannot repair a historical procedural exception.

This review follows AGENTS.md, the explicitly resumed
continuous-improvement-loop skill, and the unchanged [objective](objective.md).
It read the current status, assessment034, handoff014, remaining-gates014,
Plan044, review014, implementation review012, validation013/audit014, the
relevant Plan036 contract, and current helper, supervisor, worker/evidence,
runner and test source. Main owns status and commits. This stage ran no tests,
production controller/ledger APIs, GPU/device/model operations, setup jobs or
scientific reruns, made no source/status/git changes, and did not delegate.

Its new artifacts are this review, [assessment035](assessment-035-review.json),
and [observations015](s1-recovery-review-observations-015.json). Two guessed source
filenames were absent. The first inline observation builder assumed the ordinary
scenario schema for L36 and stopped with KeyError before any output write; the
corrected builder explicitly checks L36's separate production-return evidence.
These were inspection errors, with no permission or sandbox failure.

## Evidence and disposition

The fresh observation passes **2,282 read-only checks** at HEAD
**ebf9d9ad39c25b5732fadefcdc36cb71e0bde613**. It did not execute an old audit with
obsolete HEAD/status assumptions or rerun any saved test.

- All **77 source/config/test records** match current committed bytes and all
  four final aggregate source snapshots. Independent AST collection and typed
  callback comparison recover **221 methods**, **37 parameterized methods**,
  and **426 callbacks**, with exact recorded order and passing outcomes.
  A fresh comparison with Plan043's committed source preserves all **205 prior
  methods and 771 substantive assertion calls**, by method and AST multiset.
- The final aggregate's bound interpreter, stdin, runner, unchanged capture and
  paired closed logs agree. Actual captured completion is successful without
  timeout, with **213.69664305300103 seconds** outer elapsed,
  **213.54975955199916 seconds** inner elapsed, and
  **86.30335694699897 seconds** of headroom below the unchanged 300-second cap.
  The saved audit's **1,811 checks** remain passing and source-applicable.
  No performance causality is claimed.
- The 36 final real-child scenario records meet their 2-second execution,
  1-second safety cleanup and 3-second total bounds. L01–L35 retain observations
  at their tighter original production deadlines; L36 separately records its
  timely production return with ambiguous ownership and later safety retirement.
  The real disposable controller phase trace keeps one exact work/sample pair
  through all nine phases. Its active worker census is seven; saved ordinary
  and maximum fixture topologies are six, seven and eight workers.
- **A44-1 through A44-5 remain technically met.** The fresh S decision before
  reserve, combined 16-KiB transport budget, conservative early same-turn reply
  rejection, immutable bracketed census with the original sample deadline,
  pinned unreaped worker authority, partial-constructor state, bounded traces,
  and collected phase/deadline evidence are present in current source and saved
  tests. No concrete new defect found here requires reopening that milestone.
  The census and native timing observations retain their measured scope.
- **A44-6 and strict Plan044 acceptance remain false.** Diagnostic001 L31
  skipped worker safety cleanup after retirement raised. Its 10-second sleeper
  could overlap L35, implying a possible nine-worker maximum; neither timely
  retirement nor the eight-worker ceiling can be certified for that invocation.
  Its original outer tool completion observation is unavailable. The saved
  captured runner wait and failed receipt remain evidence, and the later
  successful runs do not repair these actions. All three focused and two
  aggregate slots are consumed; the recorded stage duration is
  **2,096.4664815470023 / 3,600 seconds**. Remaining wall time is not transferable.
- All **38 frozen records** and the original ledger remain exact:
  **447 events / 332,437 bytes**, SHA-256
  `2a0f66e38911b0ed029eb9dd0cf4bbd5da4a3b67abb577fbfe9ad67e6a888990`,
  head `00cab019d73b6a3205f676b54cfb2f745f492fa5cca5c69b4567087cea62172b`,
  **30 historical GPU reservations**, **4,374.044265462899 GPU seconds**,
  zero reserved, no active job and no recovery event. Original events
  250/255/256 are unchanged.
- Correction012 preserves its complete predecessor transition prefix and ends
  at the actual 1,019-byte IMPLEMENT014 status. Canonical post014 binds that
  `b04262f5…` endpoint to the actual 1,127-byte
  `30fdef41…` REVIEW015 status, with both durable snapshots
  rehashed. Correction012 and validation013 stay immutable.

Historical Plan041 and Plan043 strict acceptance stays false, including their
thread/CPU/prospective-note exceptions. Plan041's immutable-log whitespace exit2
remains beside its scoped check; later full staged-diff success is separate
evidence. P31-5 and unavailable older snapshots remain historical limitations.
This review did not rewrite their evidence or reset allocations.

## The remaining source gap

**R15-1a — Save verified progress before the operation and W end.**
`scripts/vipe_benchmark/s1_evidence.py:221` builds candidates,
sources, variants, errors, and verified identity lists in process-local memory.
It returns them only at the end. Deadlines checked between operations can cause
an incomplete return, but cannot preserve state when a row inspection blocks or
the helper is killed. `s1_recovery.py:495` similarly waits
for all row, runtime and first-result work before returning its summary.
`s1_cpu_helper.py:52` writes the immutable helper summary only
after that return. These are concrete remaining R9-4 defects.

Saving only at the end of reconciliation is insufficient for the worker-deadline
case: `supervisor.py:378` does not even start reconciliation
when W is already reached. The next plan must arrange incremental verification
and durable publication while work time remains, including during actual worker
progress. The worker already publishes produced/qualified partials and runs the
real qualification guard (`stages.py:177` onward). These bytes
are useful inputs; a file's existence or a worker-declared count alone must not
be promoted into a verified summary. Use the existing real structural/semantic
guards and source-bound authority. A narrow progress hook may be added to the
real worker; this does not establish the still-open full 510-row traversal gate.

**R15-1b — Keep the handoff independent of task completion and final sampling.**
`supervisor.py:154` releases a work result only after a
subsequent accepted resource sample. A failing sample therefore discards even a
completed reconciliation reference. It also poisons the retained lifecycle and
retires helpers (`supervisor.py:197` onward).
`HelperLifecycle.acquire` correctly refuses a poisoned
session, so a later publication call cannot simply reuse it. Replacing that
helper would violate the established no-replacement contract.

The next plan must retain a separately bound progress reference/outcome before
the final sample, with a durable recovery path that does not need the failed
work helper to answer. Merely adding a callback, an in-memory field, an end-only
file, or another call to the poisoned lifecycle leaves the gate open. A failed
resource/ownership sample remains a failure requiring stop; preserved progress
must never turn its task or calibration into success.

**R15-1c — Preserve exact conservative evidence semantics when checkpointing.**
The current reconciler collects duplicate variants before counting an identity.
A naïve per-file cumulative counter can credit an identity before discovering
a conflicting variant. Preserve the Plan036 contract: byte-equivalent duplicates
count once; conflicting variants are excluded unless a uniquely bound accepted
version establishes authority, and always prevent complete acceptance. Credit
only identities whose authority is settled for the bound input set. The planner
must choose and test an explicit closed-candidate-set or authoritative-version
rule; do not leave a provisional count labeled a verified lower bound.

Preserve admitted ordering, exact membership and fit/selection categories.
Qualified identities are a subset of produced identities. In incomplete work,
production and qualification totals remain unknown; zero lower bound does not
mean zero production. Only complete acceptance establishes 510 and 340/170.
Preserve already verified first-result/runtime references and raw evidence,
including after a later failed row. Large candidate/source/error lists also
need explicit finite bounds; a finite number of admitted identities does not
bound arbitrary directory entries, duplicate files or diagnostic strings.

## Required next scope and validation

Recommend one cohesive CPU milestone implementing the following contract:

1. **Durable bounded checkpoints.** Define one strict progress schema and
   publisher/consumer protocol. Bind reservation sequence/hash, trusted request
   and authorization, boot/session and operation or producer identity,
   generation/previous reference, original W, observed verification time, and
   exact underlying evidence references. Include produced/qualified identities
   and category counts, scan/coverage status, bounded errors and the available
   first/runtime states. Separate verified partial progress from complete
   acceptance. Finish each committed generation before W, with fresh time
   checks around qualification and durable publication; equality is late.
2. **Atomic publication and bounded recovery.** Prefer immutable checkpoint
   generations plus a small atomically advanced bound head/manifest, retaining
   the previous good reference through interrupted writes. Specify finite
   serialized byte, generation, entry and diagnostic limits, directory
   durability/readback requirements, and an explicit overflow outcome. No
   growing queue or repeated whole-history serialization belongs on the
   monitor. All checkpoint hashing, parsing, fsync and raw qualification run
   outside the monitor, inside the original deadlines. The existing frame,
   combined-I/O and one-outstanding-request limits continue to apply.
3. **Independent progress handoff.** Preserve the best trusted committed
   progress even if the work response never arrives or a following sample
   fails. Use compact correlated notices and/or a bounded durable manifest
   observation by an already retained external owner; the saved plan must
   choose the exact mechanism and its ownership/cancellation ordering. Do not
   create replacement helpers or add an uncounted watchdog. A blocked manifest
   read/write must leave the monitor responsive and retain the previous good
   snapshot plus explicit uncertainty. Treat a torn optional newest generation
   differently from a conflicting or tampered previously accepted binding:
   never silently downgrade an integrity failure to a healthy old result.
4. **Terminal integration without new expensive work.** The failed outcome must
   carry the preserved compact progress reference even when ordinary publication
   through the work role is unavailable. Healthy terminal publication consumes
   only the already verified summary. A poisoned path retains its durable
   summary/reference and explicit publication-unavailable status for the later
   finalizer; it cannot claim a receipt that was never written. After W, perform
   no recursive evidence discovery, array loading/decompression, raw-file
   requalification, first-result verification or 510-row acceptance. Reading
   bounded already prepared metadata is distinct from repeating those checks.
   Full loss-path receipt/finish/ack success stays subject to R9-5.
5. **Collected evidence at the actual boundaries.** Use small shared disposable
   numerical/input fixtures and real produced/qualified guards for mixed
   fit/selection rows. Cover incomplete reconciliation, worker W expiry after
   known progress, real helper death after at least one durable checkpoint,
   complete work followed by failed final sampling, and interrupted checkpoint
   publication with a previous good generation. Record durable bytes, exact
   counts/identities, original cutoffs, tick gaps, cleanup and actual CPU census.
   Cold readback must recover the surviving metadata without executing a raw
   evidence scan. Exercise current supervisor integration, not only a standalone
   serializer. Keep the full real 510-row success test for its later gate.

Use pure collected tables for strict primitive types, duplicates/conflicts,
out-of-set/aliased paths, changed request/reservation/session/generation,
regression/replay, truncated/malformed/oversized head or checkpoint, referenced
metadata mutation, missing/corrupt row artifacts, result-only partials, unknown
totals, and write/flush/fsync/publication/readback failures. Include a failure
after a verified produced row but before semantic qualification, and a later
conflict that tests the chosen authority rule. Instrument prohibited expensive
operations to fail if called at/after W. Do not allocate a child or regenerate a
510-row fixture per mutation. A checkpoint committed after W remains preserved
raw evidence and cannot be promoted to timely verified progress.

The final aggregate must retain every existing method and all meaningful
assertions, exact old typed callback rows, all 36 helper scenarios, the six
direct-script children, source collection, capture semantics, and scientific
inputs. Add literal declarations for new parameterized cases and recompute
the exact new method/callback/source totals from current source. All original
77 source members remain present; any legitimate new module joins the manifest.
The planner should select a small collected diagnostic subset for the new
progress cases. The current focused runner selects only HelperSessionTests;
an explicit source-bound selector or placing relevant collected cases there
must be decided before execution, while full aggregate discovery stays intact.

## Recommended fresh allocation and handoff

Recommend **3,600 wall seconds for the new IMPLEMENT stage**, from actual
UTC/monotonic readings before implementation inspection, with source/test work
ending at **3,300** and **300** reserved for evidence/handoff. Permit **three
focused invocations of 120 seconds** and **two full aggregates of 300 seconds**,
all inside that allocation. Reserve one full final aggregate. A second aggregate
requires a prospectively saved source change or concrete invalidating concern;
an unchanged passing timing rerun is not allocated. Unused Plan044 allowance
and consumed slots are not reused.

Allow at most **six additional real-child scenarios per invocation**, serial,
each **2 execution + 1 cleanup seconds**, or **18 additional scenario seconds**.
Existing L01–L36 keep their 108-second combined maximum, so at most 42 such
scenarios / 126 scenario seconds are allowed inside the tighter invocation and
stage limits. Preserve the six serial direct-script children at
10 execution + 2 cleanup / 72 combined seconds. Prefer small fixtures and pure
tables; no standalone probes, profiling, longevity run, split aggregate, shortened
scientific fixture, increased capture cap, or extra full 510-row build per
mutation is allocated.

Keep **eight total CPU workers** including capture/wrapper/runner,
controller/owner threads, helpers, job workers, descendants, sentinels and native
threads. Use the corrected exec driver and OMP_NUM_THREADS, OPENBLAS_NUM_THREADS,
MKL_NUM_THREADS, NUMEXPR_NUM_THREADS, OPENCV_FOR_THREADS_NUM all at 1 from the first
invocation. Preserve actual census at ordinary and maximum topology, and
unconditional fixture safety cleanup even when retirement or observation raises.
Do not advance to another child scenario with known retained live work.

Allocate **zero** GPU/device probes or attempts, model evaluations, production
controller calls/dry runs, production ledger API calls/mutations, production job
directories, setup/download/smoke jobs, and scientific reruns. Collected tests may
use disposable fixture APIs only. Read-only source/artifact/git/ledger-byte
inspection is evidence work. Before every invocation exclusively write, flush,
fsync, close, read back and hash a prospective note containing actual elapsed,
remaining allocations, exact command/environment, paths and reason. Then make a
fresh full-timeout fit check against 3,300. Capture the actual outer tool session
identifier and terminal result from the first launch. A launched permission retry
consumes a slot. Follow AGENTS.md's single safe escalation and stop/report rules.

These are **new plan-scoped allocations** under the skill's standing approval.
The fresh PLAN finalizes them and main compares them with applicable remaining
overall/method ceilings before dispatch. No routine budget confirmation is
required for a fitting saved plan. No whole-loop budget exhaustion or permission
stop was found here.

The next correction/validation must extend correction012's complete immutable
history through canonical post014 and main's actual durable PLAN015/IMPLEMENT015
transitions. Never substitute reconstructed status text or overwrite
correction012, validation013, failed runs or historical limitations. Main inspects
the completed milestone and staged task-only diff, commits under AGENTS.md, and
continues the loop. A local commit or a consumed individual allocation does not
end the authorized review/plan sequence.

**S1-1 and S1-4 remain met; S1-2 and S1-3 remain not met.** After R15-1, keep
R9-5/remaining R9-3 open: structured primary and ordered secondary failures;
continuous cleanup/publication/finalization monitoring; C/2+C/4+C/4; conservative
charged cutoff and timely durable acknowledgment; complete first/native/receipt/
finish/ack ordering. Also retain the remaining native/runtime/reference matrices,
real 510-row worker and first/later-failure progression, synchronized admission/
registration/reservation and lifecycle matrices, and current production binding.

Only after those gates are reviewed can the existing later calibration
authorization be considered: **one reservation-consuming attempt**, at most
**3,600 GPU seconds**, effective
`min(3600,93600-gpu_elapsed-gpu_reserved)>0`, with cleanup
`min(30,effective_seconds/4)` inside it. The exclusive device,
22-GiB memory, eight-worker, 150-GiB artifacts, 60-GiB downloads and existing
57,600-second applicable ceilings remain binding. This review grants no live
admission or device readiness. Reconstruction requires separate later
authorization after calibration review.
