# Plan 036 — Close the five remaining S1 recovery safety packages

Iteration 5 PLAN, 2026-09-19. **CPU implementation acceptance incomplete; live
S1 calibration recovery NOT READY.**

## Authority and scope

Continue the [objective](../docs/continuous-improvement/plan031-s1-recovery-20260919/objective.md)
from [review-005](../docs/continuous-improvement/plan031-s1-recovery-20260919/review-005.md),
[assessment-008](../docs/continuous-improvement/plan031-s1-recovery-20260919/assessment-008.json),
[Plan 035](plan_035.md),
[validation-004](../docs/continuous-improvement/plan031-s1-recovery-20260919/s1-recovery-validation-004.json),
[implementation-review-003](../docs/continuous-improvement/plan031-s1-recovery-20260919/s1-recovery-implementation-review-003.md)
and [current loop status](../docs/continuous-improvement/plan031-s1-recovery-20260919/status.md).
This replaces only the unfinished CPU implementation sequence. Earlier plans,
reviews, validations, corrections, failures and scientific records stay immutable.

This PLAN stage writes only this file and `plan-link-005.md`. Do not edit source,
run tests or GPU/device/model work, stage, commit, delegate, or mutate any ledger.
Never read `prompts`, including through aliases. The explicit user restrictions
override standing commit and delegation guidance in AGENTS.md and the objective.

The subsequent implementation is CPU-only, at most **1,800 wall seconds from
before inspection**, and at most **eight CPU workers**, including helpers and
their native thread pools. Reserve the final 180 seconds for honest evidence and
handoff. Do not extend the cap to finish a suite. On exhaustion or explicit stop,
save incomplete evidence with actual coverage, timing and remaining work.
Use disposable test ledgers/job roots only. Keep the production ledger unchanged
throughout CPU implementation, validation and preparation, including after CPU
tests pass. Production mutation additionally requires a later authorized DO
stage. No production controller dry runs, authorization, registration or job
directory creation belong to this plan. No staging, commits or delegation.

Preserve the approved S0 token-sum assignment rule, native phrases/boxes/scores,
strict `>0.35` box and `>0.5` text thresholds, weights, precision, preprocessing,
resolution, SAM refinement, tracking, environment pins and annotation policy.
Exclude reconstruction, R-S, scientific aggregate/report reruns, scoring,
final-window evaluation, other arms, historical accounting repairs, regenerated
inputs/annotations/calibration, model forwards, setup, downloads and smoke jobs.
The CPU unittest aggregate below is validation, not a scientific rerun.

Abbreviations: `C = docs/continuous-improvement/plan031-s1-recovery-20260919`,
`D = docs/research/vipe-alternatives/plan031-20260913T032700Z`,
`L = .local/vipe-alternatives/plan031-20260913T032700Z`,
`J = S1-calibration-recovery-001`.

## Starting evidence and preservation

Retain the real disposable controller/admission/registration/reservation/
prelaunch/supervisor/acceptance/publication/finish/resolution positive fixture,
correction propagation, ordered lifecycle checks and locked admission recheck.
Retain the numerical first-failure fixture, malformed-label/serialization cases,
native capture reset, semantic/refinement tests, and the serialized positive row
with empty phrase, exact tie and ambiguity. Retain protected explicit S1 CLI
selection, guarded worker failure directory creation, and acceptance/publication
before finish. Extend these implementations; do not redo credited work.

Validation-004 is incomplete. Its recorded focused run passed **13 methods,
zero failures/errors/skips, exit 0, 42.534 seconds**; exact subtest outcomes are
unknown. The current static 135-method collection is not an executed aggregate.
Older 135/79 results do not validate current source. Review-005's eight disposable
probes establish specific defects, not integration, race or live readiness.

The PLAN read-only audit verified exact membership and hashes of **70 source/
config/test records**, **38 frozen scientific records**, four bookkeeping
transition files and 38 previously recorded loop files against assessment-008.
The full production ledger parses as **447 chained events**, **332,437 bytes**,
SHA-256 `2a0f66e38911b0ed029eb9dd0cf4bbd5da4a3b67abb577fbfe9ad67e6a888990`,
head `00cab019d73b6a3205f676b54cfb2f745f492fa5cca5c69b4567087cea62172b`.
It matches the reviewed snapshot: no active reservation or S1 recovery event;
original failed finishes 250/255 and R-S skip 256 remain. Historical GPU use is
30 attempts, 4,374.044265462899 seconds and zero reserved seconds. These records
make no claim about current hardware availability.

Correction-003 is the current predecessor. Keep its original baseline, ledger
prefix, frozen records and bookkeeping lineage. The latest status bytes are
bound by transition-004-1. Do not rewrite status in this PLAN stage. Historical
P31-5 limitations, unavailable older status bytes, iteration 4's missing
inspection-inclusive timer, the two measurements excluding inspection
(642.618033546998 and 518.3559243239979 seconds), and the 848.010818-second bound
with unknown exact start remain explicit; do not repair or reset them.

## Implementation order and completion contract

| Package | Review coverage | Principal code and tests |
| --- | --- | --- |
| 1. Canonical lifecycle and races | F5-1, L1/L2 | `s1_recovery.py`, `execution.py`, `ledger.py`, supervisor prelaunch; recovery tests |
| 2. Durable failure publication | F5-2, P1 | CLI, worker, `s1_evidence.py`, `s1_recovery.py`; recovery/worker tests |
| 3. Truthful partial evidence | F5-3, P1 | `s1_evidence.py`, `s1_recovery.py`, narrow `stages.py` changes; recovery tests |
| 4. Bounded monitoring and accounting | F5-4, P2 | `supervisor.py`, dispatch, S1 ledger finalization and resolver; supervisor/budget/recovery tests |
| 5. Exact receipts and worker progression | F5-5, A1–A4 | receipt guards, literal case tables, evidence/segment guards; prescribed suites |

Implement in this order, adding each package's collected cases with its fix.
Define the literal case-table format before adding parameterized cases; finalize
membership in package 5. Then perform V1 once on the final source. Do not defer
failing guards to documentation or equate test count with coverage completion.
Limit edits to these existing paths and necessary test/CPU-helper support.
Backend/contracts changes require a demonstrated intended-guard failure.
Keep generic S1 rejection and S2 recovery regressions passing.

Every negative starts from a passing fixture, changes one declared dependency,
rehashes outer records where necessary, and asserts the exact error category,
boundary reached and operation prevented. Unexpected fixture failures do not
count as rejection coverage. Record method IDs and literal parameter tuples for
each requirement; no uncollected helper option or manual probe closes a case.

### 1. Bind the canonical request throughout the lifecycle; prove races

Extract the canonical comparison currently in `reservation_binding` into a
read-only shared validator. Inputs are the caller's event snapshot, verified
authorization and historical request, canonical request file record, worker
record and, when present, captured reservation and launch argv. Derive the one
expected request from the historical request plus J, recovery authorization and
configuration; compare complete decoded contents and exact file records.
Enforce calibration branch, typed scope, original request digest, all BINDINGS,
admission/registration event references, worker bytes, interpreter, operation,
request path and output path. A hash-valid reconstruction request must fail.

Call it at reservation, consumed lifecycle validation, prelaunch, acceptance and
resolution. At prelaunch/acceptance compare the current active reservation's
sequence/hash/evidence/command with the supervisor's captured reservation and
actual argv; checking a newly read request alone is insufficient. Pass already
verified historical inputs into lifecycle validation to avoid recursion through
`validate_binding`, `result_record` or ledger locks. Lock owners pass snapshots;
validators never acquire another lock. Missing trusted identity fails closed.

Keep the lifecycle: blocked admissions before successful admission; one admitted
record; one registration; one reservation; optional temporary-directory then
start; phase-bound ownership diagnostics; one terminal finish. No unrelated,
orphan, duplicate, reordered or post-finish append. A failed prelaunch finish may
have no start; success requires start, accepted evidence and durable publication.
Registration without reservation may continue only with the identical authority
and fresh checks. Reservation consumes J even if Popen never occurs.

Use this explicit applicable-boundary matrix. `A/G/R/P/X/Z` mean admission,
registration, reservation, prelaunch, acceptance and historical resolution.
Each listed component within a row gets its own stable mutation tuple.

| Dependency family | Applicable boundaries | Explicitly inapplicable |
| --- | --- | --- |
| Amendment/parents; config; source membership/bytes; validation; correction/predecessor; authorization | A,G,R,P,X,Z | None |
| E1 qualification/assets/runtime; input records; annotation policy/review/amendment event | A,G,R,P,X,Z | None |
| Original failure artifact/event/cleanup and historical request | A,G,R,P,X,Z | None |
| Baseline prefix/head/chain/snapshot; frozen science; bookkeeping transition continuity/current status | A,G,R,P,X,Z | None |
| Successful admission reference | G,R,P,X,Z | A: reference does not yet exist |
| Registration event reference | R,P,X,Z | A,G: validate registration at creation, not a future reference |
| Canonical dispatched request and worker/argv binding | R,P,X,Z | A,G: dispatch record not yet created |
| Captured active reservation and its launch command | P,X,Z | A,G,R: reservation is not yet durable |
| Start, acceptance, terminal receipt and finalization evidence | X,Z as each becomes available; all at Z | A,G,R,P: future evidence; X cannot require a future finish |

For the last row mutate available start/request bindings at X, and independently
mutate acceptance/receipt/finish references at Z. Include byte, validly rehashed
semantic, wrong-type, missing and substituted-reference variants where the
underlying guard differs. Include broken/missing bookkeeping transitions,
unrecorded status edits and scientific mutation independently of chain mutation.

Add synchronized CPU process contenders with barriers at the decision boundary,
real disposable file locks and bounded joins: simultaneous admission followed
by registration, direct registration contenders after one admission, and
reservation contenders after one registration. Assert one winning successful
admission/registration/reservation at most, at most one launch, losers reporting
the intended duplicate/consumed rejection, valid chain and no deadlock. Do not
replace concurrency with sequential calls or mocks of the lock. Retain active,
reduced, exhausted, typed-scope and second-identity cases. Add registered-but-
unreserved block then identical continuation, changed-authority continuation
rejection, and replay after reservation including prelaunch failure.

### 2. Preserve primary failures and publish minimal durable outcomes

Keep explicit `--job J` routing before authorization decoding. Move decoded
type/field checks into the generic protected parse path as well: lists, scalars,
null and invalid field types are rejected without calling `.get`/`.startswith`
on unchecked values. Exercise the actual CLI entry with disposable roots and
fake external boundaries. Missing, unreadable, truncated, malformed, wrong-type
or changed authorization must produce an immutable unconsumed block when storage
permits. Untyped generic input supplies no S1 authority. Block records use their
own content-addressed path and never occupy J's consumed terminal path.

Separate minimal terminal construction from optional evidence reconciliation.
Capture trusted reservation/registration identity, canonical bindings and clock
context before launching the worker. After consumption, construct the outcome
from that context even if authorization/request/runtime/result files later break.
Type-check each optional JSON layer before field access. Catch ordinary evidence
inspection exceptions at the optional boundary, preserving type/message/phase;
do not swallow interrupts or trusted-identity failures as benign missing data.
Corrupt optional evidence cannot erase attempt consumption or replace the primary
failure. Pass the package-3 verified summary into publication rather than doing
new qualification there.

Use structured primary and secondary errors across worker/helper/supervisor:
class, message, phase, failure kind, stop requirement, and available traceback.
Keep the original exception primary even when raw/first/failure/terminal
publication also fails. Permission/access, resource/sample, ownership, deadline
and cleanup failures require stop; ordinary result-contract failure must not
absorb their classification. Finish records reference the same primary failure
and ordered secondary errors, including observations after receipt preparation.

Pass trusted reservation start, boot identity, effective seconds and work deadline
explicitly to first-result functions and supervisor-generated `not_reached`
evidence. Worker environment values may transport this context but are not its
authority. Replace hardcoded 3,600-second evidence checks with the effective
allocation. A pass must be durable and validated before the work deadline and
before advancement. Failed/not-reached evidence may describe cleanup within the
total deadline; it never permits advancement. Reject nonfinite/negative timing,
wrong boot/start, and inconsistent first/result/native/receipt/finish time order.

Preserve a verified worker failed/not-reached record's phase/time/error exactly.
Preserve an earlier verified pass and raw evidence after a later failure. An
identical verified pass may be reused; stale/conflicting/failed/not-reached
records cannot be promoted. Missing first evidence generated by the supervisor
uses its trusted clock, not an unset worker-only environment variable.

Required tables cover explicit and generic CLI variants; first adapter failure;
the retained numerical failure; later-row failure; absent/truncated/scalar/list/
wrong-object authorization, result, each partial and initial/partial/final
runtime; abrupt worker death; controller/supervisor death without finish; and
cleanup uncertainty. Parameterize mkdir, serialization, write, hash and immutable
conflict at raw, first-result, `failure.json` and terminal publication boundaries.
Assert the primary survives and secondaries are reported. Totally unwritable
storage yields publication-unavailable evidence in any remaining log/ledger
channel, never a claimed durable receipt. Missing finish remains consumed and
unresolved. No retry, renamed attempt or inferred cleanup is allowed.

### 3. Count verified unique evidence, independently of semantic success

Add a produced-row structural validator separate from full `qualify_row`.
Require a mapping with the exact admitted identity, parent input bindings,
required serialized row fields and valid referenced instances/static/diagnostic
file records. Verify artifact bytes and basic readable type/shape contracts;
do not require that semantic/numerical qualification already passed. Preserve
invalid numeric arrays without pickle as failure evidence. Empty dictionaries,
unreadable artifacts, aliases, out-of-set identities and forged filenames do not
establish a produced row. Structural evidence and semantic success are distinct.

Within the work deadline, reconcile produced partials, qualified partials and
readable result rows into a map keyed by the admitted `(camera, frame,
pair_start)` identity. Check original result order; partials are reconciled into
admitted order, never filename order. Byte-equivalent duplicates count once.
Conflicting duplicate identity variants are recorded and excluded from trusted
counts unless a uniquely bound accepted version proves which is authoritative;
they always block complete acceptance. Full qualification must use actual guards.
A valid result row can establish produced/qualified evidence when its partial
filename is absent; invalid whole-envelope status does not automatically discard
independently verified row evidence.

Define counts explicitly: `produced_lower_bound` is the unique structurally
verified identity count, including qualified identities; `qualified` is the
unique fully verified row count. In incomplete evidence, production and qualified
totals remain `unknown`; zero verified rows means a zero lower bound, not proof
that nothing was produced. `complete` is 510 only after all ordered membership,
runtime, envelope and acceptance guards pass; otherwise zero denotes no complete
calibration, not zero production. Report fit/selection lower bounds and qualified
counts using admitted category membership, capped at 340 and 170. Total counts
must equal their two category counts. Exact complete totals require 510 unique
ordered rows and the 340/170 split.

Prepare a bounded evidence summary incrementally while work time remains. On
timeout publication uses only the verified summary already available, marks
incomplete scans/totals unknown and starts no recursive scan, decompression,
first-row verification or 510-row qualification in the cleanup reserve.

Collect the two-`{}` reproducer (lower bound zero), duplicate identical and
conflicting rows, mismatched identity/parent, corrupt/missing artifacts, lexical
filename ordering, reordered/extra result identities, partially qualified rows,
structurally valid but semantically failing rows, qualified result without partial
file, and interrupted reconciliation. Assert exact identities, counts, categories,
unknown totals and retained evidence, not only the final exception.

### 4. Bound monitoring, cleanup and durable finalization together

Retain an external monitor and separate CPU work/sample helpers; remove direct
`os.fork()` from the potentially multithreaded controller. Use explicit spawned
CPU helpers with top-level operation entry points and serializable operation
arguments/results, replacing local closure transport at these boundaries only.
Create the small fixed helper set before reservation with bounded readiness;
no native/model imports in helpers. Track each PID, process start identity and
owned descendants. No new GPU process or job is introduced. Limit all helper
native thread pools to one and lower worker thread allowance as needed so the
whole owned workload remains within eight CPU workers.

The monitor never hashes, parses, decompresses, samples, recursively scans,
waits for a blocking reap, or acquires a blocking ledger lock. Its tick is at
most 100 ms in prelaunch, worker, acceptance, reconciliation, publication,
cleanup and finalization. Remove S1's `poll_seconds=2.` dispatch override.
Allow one sample in flight; each sample timeout is at most one second or remaining
phase time, whichever is smaller. Require all `device_bytes`, `artifact_bytes`,
`download_bytes` and `gpu_pids` fields with correct types, finite nonnegative
values, valid unique PIDs and sample timing. Missing fields, `{}`, malformed,
stale, failed or timed-out samples stop work; never default them to healthy zero.
Initial sampling uses this same strict contract, not a fake empty monitor sample.

Let `T` be effective reservation seconds, `C=min(30,T/4)`, total deadline
`D=start+T`, and work deadline `W=D-C`. Check live ownership/resources and deadline
after slow prelaunch checks and immediately before Popen. No launch at/after W.
No new expensive work at/after W. Work includes loading, inference, first-result
checks, serialization, all row/runtime acceptance and partial reconciliation.
Keep sampling after worker exit and through cleanup/publication/finalization.
Foreign PIDs cause a stop; only owned processes may be signaled.

Use nonblocking reap/join and TERM then KILL with deadlines clamped to the phase's
remaining allocation. A failed enumeration, kill, helper startup or reap records
cleanup uncertainty independently of the survivor list. An empty fallback list
does not prove cleanup. Include helper descendants; never wait indefinitely for
an uninterruptible child. If cleanup cannot be established before D, leave an
unresolved consumed stop with surviving/unknown ownership evidence.

Divide C deterministically: first C/2 for owned-work termination, next C/4 for
minimal receipt publication, final C/4 for durable finalization. Early phases
may finish early; unused time stays inside D and never authorizes more work.
Continue deadline/resource checks during all phases. Heavy qualification must
not be repeated by terminal publication or historical resolution.

Finalization must cover ledger lock acquisition, append, flush/fsync and helper
reaping. Use nonblocking lock attempts under monitor control and a terminable
writer operation; do not measure elapsed and then perform an unmonitored finish.
Preserve the chain on append interruption; a partial/corrupt tail is unresolved
and requires explicit later reconciliation, never automatic truncation/replay.

Avoid the circular claim that a finish can contain its own exact post-fsync
timestamp. At finalization entry `f`, set a fixed cutoff
`F=min(D, f+min(1,C/4))`; reject an exhausted interval. All finalization work,
including the acknowledgment below, must finish before F. Record measured
elapsed through f separately from the conservative finalization allowance F-f.
For J charge `F-start`, at most T, explicitly as a charged upper bound with at
most one second of finalization padding, not as measured runtime. Retain actual
observed elapsed separately and never hide an overrun by clipping it. This
preserves the cumulative cap without leaving final I/O uncharged or rewriting
historical accounting. Tests must verify the charge and cutoff calculation.

Add a small immutable S1 finalization acknowledgment in the disposable/job
evidence protocol, binding reservation, terminal receipt and exact finish event.
It records the writer's durable completion acknowledgment, final observed
resources/errors and cleanup outcome; publish it before F under the same monitor.
It is no extra ledger allocation or success event. A finish lacking a verified
acknowledgment, or with a failed/late/uncertain acknowledgment, cannot resolve
as success. Treat a timed-out writer with possibly appended bytes as unresolved,
even if a finish line is visible. This closes the late-write/crash window without
rewriting the immutable terminal receipt or relying on an after-the-fact flag.

Receipt outcome is explicitly scoped through its preparation; finish and
acknowledgment bind that snapshot and carry subsequent observations. Preserve
primary error identity and monotonic resource peaks across all three. A later
stop supersedes a prepared success and prevents resolution; it must not leave a
success-looking resolvable receipt. Read-only resolution requires matching
successful receipt, acceptance, finish and timely acknowledgment, current bound
bytes and confirmed cleanup. It performs no new model/row computation.

Collect real controllable CPU-child tests with fake device readings and short
allocations for: expiry immediately before Popen; blocked helper startup, hash,
decompression, sample, write, ledger lock, fsync and reap; slow/invalid samples
without reentry; foreign PIDs before launch, after worker exit and in acceptance,
publication, cleanup and finalization; each changing memory/artifact/download
cap; reduced allocation; worker/controller/supervisor death; publication failure;
cleanup errors with an empty PID fallback; and late/partial/missing finalization.
Assert no prohibited launch or post-W expensive operation, bounded joins and
return by D plus at most one 100-ms monitor tick, no foreign signals, at most
eight workers, exact failure/stop classification, conservative charge and measured
elapsed, and no successful resolution without every durable condition. Scheduler
overruns are failures to report, not grounds to widen the acceptance tolerance.

### 5. Enforce exact aggregate membership and real worker advancement

Declare literal ordered required parameter tuples beside the tests for every
parameterized method in all nine suites. Use a mapping from full method ID to
ordered dictionaries of primitive typed parameters, including stable case and
boundary IDs. Parameterize tests from these same tables; flatten nested subtests
to the declared full tuple. Static `required_cases` uses AST/literal evaluation,
never test/model imports, and rejects missing/dynamic/duplicate declarations.
Canonicalize typed parameter dictionaries for receipt IDs; arbitrary unique
strings are insufficient. Methods without subtests must have an empty list.

Create a fixed source-bound CPU runner, invoked by the prescribed stdin command,
which discovers suites in the exact order below and records actual outcomes via
the unittest result callbacks. Bind runner bytes in `source_paths()` if a new
helper file is introduced outside the existing globs. The stdin is the exact
fixed runner invocation, not arbitrary code claiming suite names. Record launcher
argv separately from Python `sys.argv` for `python -B -`; reconcile both rather
than pretending they are identical. Bind full stdin and output logs by bytes/hash.

`validation_record` requires one aggregate, exact ordered discovery/method IDs
and parameter tuples, all passing method/subtest outcomes, zero failures/errors/
skips, per-suite and aggregate counters derived from those outcomes, and matching
actual execution metadata. Check expected interpreter and `-B -` invocation,
fixed stdin, environment thread limits, zero exit, parseable ordered UTC times,
finite monotonic start/end and nonnegative elapsed equal to their difference
(allow only documented clock serialization precision). Reject missing metadata,
boolean counts, nonfinite times and fabricated zero aggregates. A method with a
failed subtest cannot pass the aggregate. Do not hardcode 135 methods or 79
subtests. Do not combine multiple disjoint receipts to fake one execution.

Use a known-good synthetic receipt first in adversarial tests, then independently
mutate zero/missing/extra/duplicate/aliased/stale sources and cases; failed/error/
skipped methods/subtests; parent pass with failed subtest; missing/substituted/
duplicate tuples; wrong suite/method/subtest order, totals and metadata; argv vs
command vs stdin mismatch; null stdin; negative/nonfinite elapsed; one-test
command merely naming all suites; and disjoint receipts. These rejection cases
must themselves run in the final aggregate. Synthetic receipts stay explicitly
fixture-only in disposable roots. Coherent execution claims cannot prove their
own authenticity: the implementation review must independently reconcile the
actual runner invocation, log, source hashes and emitted outcomes.

Complete the remaining A1–A3 tables using real guards and valid outer fixtures:

| Table | Required collected cases |
| --- | --- |
| Numerical/native | Collect existing `zero=True` and `skip=True`; overwritten survivors; unresolved/disagreeing/below-text-threshold ambiguity in addition to retained tie/empty phrase. Mutate processed RGB shape/finiteness/resize/normalization; logits/sigmoid/nonfinite arrays; retained query order/threshold alignment; normalized/pixel boxes; UTF-8/offsets; every detection index/id/score/assignment and surviving semantic index/id/box/class. Keep native ID remapping, never identify object IDs with query indices. |
| Runtime | Rehashed admitted-to-loaded GroundingDINO/SAM tree changes; E1 import file/symbol/source; inventory/correlation build identity; required `groundingdino._C` mapping versus unrelated native library; nested/missing file records; wrong interpreter; aliases/duplicate paths/modules; empty manifests; forbidden roots/modules. No native imports/builds required. |
| Envelope/time/resources | Schema/status/job; exact first camera 0/frame 50/pair_start null; count/order/identity; amendment/authorization/request/runtime/checks/raw references; finite nonnegative timing/memory, allocated versus reserved memory and native versus total timing; reduced effective deadline and coherent reservation/first/result/receipt/finish relationships. |
| Real worker progression | Call real `stages.segment` with fake backend, fake device calls and valid serialized diagnostics/runtime; preserve actual input loader observations and row/first-result guards. Assert durable verified first pass before loading frame 62, exactly 510 ordered identities and 340/170 split, identical reverified pass reuse only, stale/conflicting/failed/not-reached evidence stopping advancement, later-row failure retaining earlier pass/raw bytes. First adapter/numerical/serialization failures make exactly one adapter call and never load a second input. |

The positive controller fixture still fakes the external worker; the real segment
fixture independently closes worker progression. Neither substitutes for the
other. Unexpected early guards do not validate an intended numerical/runtime
mutation. Correct only demonstrated gaps while keeping the scientific amendment
and native behavior unchanged.

## V1: final CPU validation, preservation and immutable handoff

After all source/test/case-table/runner changes, run one ordered aggregate with:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .local/envs/stg-colmap/bin/python -B -
```

Its recorded stdin runs `tests/test_vipe_benchmark_<suite>.py` in this order:
`s1_semantics`, `s1_recovery`, `backends`, `contracts`, `component_recovery`,
`execution`, `budgets`, `supervisor`, `review_annotations`. Capture full runner
stdin, actual launcher/Python argv, stdout/stderr, exit, UTC and monotonic times,
ordered discovery, every method and exact subtest outcome, per-suite and total
counters. Focused iteration runs are diagnostic only. Any later source, test,
case table or runner edit invalidates the aggregate and requires a fresh one
within the existing CPU cap, otherwise report incomplete.

Recompute exact resolved duplicate-free `source_paths()` membership and hashes;
bind current amendment/parents, baseline/correction, original failure/event,
historical request, config, E1/assets/runtime, inputs and annotation evidence.
Audit frozen bytes, full ledger bytes/prefix/chain/head/totals and absence of new
production recovery events, bookkeeping continuity and unchanged index. Run:

```sh
git diff --check -- . ':(exclude)prompts/**' ':(exclude)**/prompts/**'
```

Before validation, finalize successor correction-004 from correction-003 with
Plan 036/review-005/assessment-008 provenance, unchanged original scientific/
ledger baseline and all verified bookkeeping transitions. Prefer leaving status
unchanged; if final implementation status changes, preserve old bytes and create
an immutable old/new hash/byte/reason transition before finalizing correction.
Never rebaseline history or reconstruct unavailable old status bytes.

Use the following next unused artifacts; if occupied, advance the suffix and
record actual paths rather than replace anything:

| Artifact under C | Required contents |
| --- | --- |
| `s1-recovery-baseline-correction-004.json` | Existing schema, predecessor correction-003, original baseline/prefix/frozen records, verified bookkeeping lineage and Plan 036/review-005/assessment-008 |
| `s1-recovery-validation-005.json` | Truthful overall completion, package/case coverage, exact current-source aggregate and metadata, correction/plan/amendment/config binding, preservation/diff/index audit, inspection-inclusive time, zero GPU/device/model/production mutations |
| `s1-recovery-implementation-review-004.md` | Exact validation record; F5-1–F5-5, L1/L2/P1/P2/A1–A4/V1 dispositions tied to actual methods/tuples; independent receipt reconciliation; timing/limitations and readiness decision |
| `s1-recovery-preparation-005.md` | Non-executable handoff binding correction/validation/review, tested explicit CLI selection, sole identity/budget, fresh live gates and any unresolved blockers |

Record file references as resolved absolute path, SHA-256 and integer byte
count; events as sequence/hash. Reject aliases, forbidden paths, immutable
conflicts and JSON NaN/Infinity. Finalize correction, then validation, then
review, then preparation. Save actual logs and any declaration/runner artifacts
with those records. CPU completion requires every package and V1 to pass; an
incomplete result must name the smallest remaining cases and remain NOT READY.
Do not run more tests after successful final validation without a new failure,
change or unresolved concern justifying them.

## Conditional later calibration; no allocation expansion

This plan grants no production authority. Only a separately authorized DO stage,
after all CPU gates close and current bindings/resources are freshly verified,
may create/register the existing typed amendment authorization for J. Bind Plan
036, the actual successor correction, final validation/review, amendment/config,
original cleaned-up failure/event, E1 qualification/assets/runtime, inputs and
annotation policy/review/amendment event, historical/canonical request and ledger
baseline. Recheck applicable bindings under registration/reservation locks and
at prelaunch/acceptance. A synthetic receipt or preparation is not authority.

There is still **one attempt and one 3,600-GPU-second calibration cap**, within
the unchanged 93,600-second cumulative GPU ceiling:

`effective_seconds = min(3600, 93600 - gpu_elapsed_seconds - gpu_reserved_seconds)`

Reject nonpositive time and unrelated active attempts. Cleanup/finalization
reserve `min(30,effective_seconds/4)` is inside the same allocation. Charge
loading/inference, qualification, hashing, acceptance, serialization, publication,
cleanup and finalization. Preserve one exclusive GPU process group, 22 GiB total
device memory, eight CPU workers, 150 GiB artifacts, 60 GiB cumulative new
downloads and existing 57,600-second preparation/setup ceilings. New setup,
download and extra smoke jobs stay zero. Reservation consumes J without launch;
no replay, renamed identity, reset counters or silent CPU fallback.

The later outcome is one fully qualified, durably finalized 510-row calibration
or a truthful failed/unresolved consumed outcome with primary/secondary errors,
verified partial/unknown counts and cleanup status. Receipt alone never proves
completion. Stop after this calibration outcome and its review. Reconstruction
requires separate later authorization after calibration review; R-S and
scientific aggregation/report reruns remain excluded.

S1-1 retains semantic CPU support pending remaining adversarial coverage. CPU
completion alone does not satisfy S1-2's production admission or S1-3's live
outcome. S1-4 remains an audited preservation claim with historical limitations.
