# Plan 042 — Reuse exact-source S1 declaration parsing with fresh file reads

Iteration 12 PLAN, 2026-09-20. Implement **R12-1** from
[review-012](../docs/continuous-improvement/plan031-s1-recovery-20260919/review-012.md):
bounded process-local reuse of successful static declaration parsing. This is a
CPU validation prerequisite for S1-2/S1-3; preserve S1-1/S1-4. The objective and
its definitions remain in the authoritative
[objective](../docs/continuous-improvement/plan031-s1-recovery-20260919/objective.md).
The current assessment is
[assessment-027-plan](../docs/continuous-improvement/plan031-s1-recovery-20260919/assessment-027-plan.json).

The explicitly resumed continuous-improvement-loop skill supplies standing
approval for the new plan allocation after main checks unchanged applicable
ceilings and records dispatch authority. Follow AGENTS.md; never read `prompts`.
Use one direct implementation agent, no nested delegation. Main owns status
transitions, staging and local commits. Plans 031–041 and historical evidence
remain immutable. Plan 041 technical acceptance is supported, but its strict
procedural acceptance remains false; this plan cannot repair that history.

## Allocation and launch gate

Finalize a new **1,800 wall-second IMPLEMENT allocation**, starting with actual
UTC and monotonic timestamps **before inspection**. Stop source refinement and
test execution by elapsed **1,620 seconds**. Reserve the last **180 seconds** for
evidence and handoff. Allow at most **three focused invocations, each at most
120 seconds**, and **two full aggregates, each at most 300 seconds**, within the
same wall allocation. These are maxima, not targets. Permission retries and
failed preparation consume elapsed time; every launched test process, including
failed discovery or a newly launched retry, consumes an invocation. Unused
historical time or attempts cannot be reused or transferred.

Before **every** launch, complete all preparation and write a new, exclusive,
durable launch note. Record actual UTC/monotonic observations relative to the
original stage start, elapsed and remaining execution/wall time, attempt index,
counts consumed and remaining before/after this launch, exact command/run
directory, requested timeout, reason, and whether one final aggregate is still
reserved. Flush and fsync the note, close it, read it back and verify its exact
bytes/hash. Recheck that the full timeout still fits before 1,620 immediately
before launch. If preparation, note publication or read-back fails, **do not
launch**. Never join failed preparation and launch with an unconditional shell
separator or continue from a failed assertion. Preserve the failure; an actual
later retry gets actual timestamps and a new note, never a backdated note.

A 120-second diagnostic before the required final aggregate needs at least
420 execution seconds remaining, plus time actually consumed by preparation.
If a final complete pass is not yet supported, reserve 300 seconds before any
optional refinement. A second aggregate needs a saved source change or concrete
concern invalidating the first. Record that reason prospectively. Do not repeat
an unchanged passing aggregate for timing. No extra profiling, standalone
parser benchmarks, helper probes, uncollected test invocations or suite splitting.
If a pass is invalidated when no aggregate remains, report incomplete acceptance.

Keep at most **eight CPU workers**, including owned processes and native/helper
threads, serial suites, and all four settings `OMP_NUM_THREADS`,
`OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS`, `NUMEXPR_NUM_THREADS` at **1** throughout
the invocation and its children. Existing six collected direct-script children
remain serial, each at most 10 execution + 2 cleanup seconds, 72 seconds total
inside the aggregate and its tighter parent/plan deadlines. Preserve exact child
argv, logs and completion evidence. No new processes or threads for the cache.

Allocate **zero** GPU/device probes or attempts, models/evaluations, production
controller calls (including dry runs), production ledger API calls/mutations,
production job directories, setup/download/smoke jobs or scientific reruns.
Existing disposable fixture APIs inside collected CPU tests remain allowed.
Standard-library file/hash/JSON/AST inspection and read-only git inspection are
evidence work. Apply AGENTS.md's single safe outside-sandbox retry and stop/report
rules; do not bypass a denial. Main stops on git add/commit failure. A plan or
invocation limit stops the work it governs; preserve its consumption for the
next authorized review instead of expanding it.

## Evidence and bounded implementation scope

Review reconciled **75 source/config/test records**, **169 methods**, **37
parameterized methods**, **426 typed callbacks**, **38 frozen records**, and
the original **447-event / 332,437-byte ledger**. The complete supported
aggregate-011-002 took **258.0717323209974 outer seconds**, with recovery suite
**252.30142017400067 seconds**, leaving **41.9282676790026 seconds** below 300.
These are suite/process measurements; parsing's individual cost is unmeasured.
The deterministic target is fewer real parse calls for repeated exact keys.
No percentage speedup or capacity promise is an acceptance threshold.

Change only:

- `scripts/vipe_benchmark/s1_validation_contract.py`: factor the existing pure
  parser into bounded successful-result reuse and return defensive copies.
- `tests/test_vipe_benchmark_s1_recovery.py`: add a small literal
  `DeclarationCacheTests` class and its required literal declarations, if any.
  Existing test methods, callback declarations and assertions stay intact.
- `scripts/vipe_benchmark/s1_validation_runner.py`: change only the focused
  selector from `ReservationClockTests` to `DeclarationCacheTests`.
- New immutable iteration-12 artifacts in the existing run directory; main
  separately owns actual status snapshots and transitions.

Keep capture.py, schemas, invocation caps, exact aggregate launcher/stdin/order,
environment transport, source membership algorithm, receipt validation and all
other production behavior intact. No smaller images, shortened 510-row fixtures,
weakened mutation checks, fabricated receipt passes or omitted old tests. An
unrelated failing test is a handoff finding, not authority to change its source.

## 1. Cache only the existing pure parse result

Use standard-library `functools.lru_cache(maxsize=16)` on a private helper such
as `_parse_suite_cached(text, module)`. Move the existing `parse_suite` body into
that helper, retaining its AST walks, declaration/typed checks, error messages,
exception translation, ordering and result shapes. Cache key is the **entire
exact source text and exact module name**, passed consistently as positional
arguments by the public wrapper. No normalization, digest-only identity,
pathname/mtime/size key, module-only key or source-version alias is acceptable.

The public `parse_suite(text, module)` returns
`copy.deepcopy(_parse_suite_cached(text, module))` on **both misses and hits**.
Never return the retained object to a caller. This isolates the method list,
declaration dictionary, case lists and nested parameter dictionaries, including
all primitive types. A failed parse raises through the real parser and stores
no entry; the standard decorator already does this. No negative cache, cached
exception, disk cache, external dependency, imported test module or cross-process
cache service. Private cache_info/cache_clear are sufficient for isolated tests;
no new CLI, configuration or production cache management API is needed.

`collection()` **must still read every current suite file on every call** using
the existing path construction and `read_text()`, then call the public parser
with freshly read text. Keep its cross-suite uniqueness and nonempty collection
checks. Successful cached syntax does not authorize a missing/changed file.
Read failures propagate normally. A file edit preserving pathname, byte length
and mtime must be observed through new text and validated; restoring original
bytes may legitimately hit an exact-text entry.

Do not cache `collection`, source membership, `source_paths`, file records or
hashes, `strict_record`, source checking, receipts, wrapper/validation results,
canonical admission, ledger state, reservations, rows/runtime/first results or
historical resolution. The fresh data/authority guards continue executing on
every call. Parser reuse changes neither their inputs nor their acceptance.

## 2. Cheap collected tests of the real parser and collection

Use seven ordinary `test_` methods in `DeclarationCacheTests`, with tiny literal
source strings and disposable files. Prefer ordinary assertions without subtests;
if typed subtests materially clarify a boundary, declare every case literally in
the existing single module `SUBTEST_CASES` mapping. Derive final counts from AST,
never from the planned number. Existing 169 methods and 426 callbacks must be
retained with the same typed identities, assertions and relative order.

Each cache test starts from a cleared private cache and registers cleanup to
clear it even on failure. Keep patches local. The real `ast.parse` spy uses
`wraps` on the saved real function, counts only the controlled parser calls, and
never returns a fake syntax tree or pass. Do not count AST work performed by
unrelated suite collection/discovery. No full controller or 510-row fixture is
needed for new cache cases.

| Method/boundary | Required observations through real code |
| --- | --- |
| `test_repeated_exact_key_reuses_parse` | Parse a valid typed declaration twice under identical text/module. Assert one actual `ast.parse` call, original method order and all declared typed values, value equality and distinct returned mutable objects. |
| `test_exact_text_and_module_keys` | Parse valid text, a same-byte-length valid text change under the same module, and restored original text. Assert the changed value and two real parses while restored text reuses its entry. Independently parse identical ordinary-method text with an empty declaration under two modules and get distinct module-qualified IDs. A warmed parameterized declaration under the wrong module must be rejected through its real missing/extraneous declaration guard. |
| `test_collection_rereads_same_size_same_mtime` | Build all nine tiny valid suite files in a temporary root with correct module names and literal declarations; patch only contract ROOT to that root. Warm real collection. Rewrite one primitive value with equal byte length and restore its original mtime using saved stat nanoseconds; assert both metadata facts and the changed declared value on the next collection. A wraps spy on real file reads should show each of the nine paths read again. Restore original bytes and verify original declarations. Never patch collection or file reads to fabricate results. |
| `test_collection_warm_cache_does_not_hide_deletion` | Warm real collection over nine fixture files, delete one known file, then require the real missing-file read failure on another collection. Restore it and require a valid collection. This supplies deterministic read-failure coverage without chmod-dependent permission behavior. |
| `test_returned_mutation_isolation` | Obtain independent results; mutate the method list, outer declaration map, case list and nested parameter dictionary of one result, then confirm the other and a later call remain exact. Cover bool/int/float/null/string values and verify exact types or typed identities, since Python equality alone collapses bool/int/float. Include mutation of the first miss result to prove it never exposed retained storage. |
| `test_invalid_inputs_are_not_cached` | Repeated malformed syntax and repeated syntactically valid but invalid declarations raise the expected real ValueError. Use the wraps spy and cache_info to prove both repeats execute real parsing, store no invalid entry and leave prior successful entries sound. Corrected text succeeds. Keep the existing complete adversarial parser/receipt tests untouched for the aggregate. |
| `test_lru_bound_and_eviction` | Fill 16 distinct valid text/module keys, verify maxsize/current size 16, touch an older entry, insert a 17th and confirm the least-recently-used unrefreshed key is reparsed while the refreshed key stays a hit. Assert reparsed output and size at most 16. Keep all fixtures tiny and parse counts deterministic. |

Existing aggregate cases remain the integration evidence that repeated parsing
does not suppress receipt/source/admission/clock checks. Use the new focused
selector for collected cache diagnostics. A focused pass alone cannot establish
plan acceptance. Do not modify existing fixtures to exploit cache internals.

## 3. Final aggregate and independent preservation audit

Use unchanged capture in new directories `s1-recovery-diagnostic-012-001`
through `003` and `s1-recovery-aggregate-012-001` through `002`; check vacancy and
never overwrite an attempt. The exact aggregate child remains
`.local/envs/stg-colmap/bin/python -B -`, repository cwd, diagnostic unset,
`VIPE_CPU_VALIDATION=1`, all four thread variables 1, and existing stdin bytes:

```python
import runpy
import sys
sys.path.insert(0, "scripts")
runpy.run_module("vipe_benchmark.s1_validation_runner", run_name="__main__", alter_sys=True, init_globals={"STDIN_PYTHON_ARGV": tuple(sys.argv)})
```

Preserve its final newline and suite order: `s1_semantics`, `s1_recovery`,
`backends`, `contracts`, `component_recovery`, `execution`, `budgets`,
`supervisor`, `review_annotations`. Derive the source set, ordered methods,
literal typed callback identities and parameterized method set from final AST.
Compare old method/declaration identities with the reviewed receipt; every old
method/callback must remain and execute. New cases must appear exactly once in
the correct collection. Require no failures, errors, skips or discovery errors.

Bind all complete inner/outer pre/post source snapshots, exact argv/interpreter,
environment, stdin/runner/capture snapshots, closed raw logs, timestamps, actual
wait/exit, timeout status and independent tool/session completion observation.
Reconcile all six direct-script child outcomes. No source changes after a pass;
such a change invalidates its current-source claim and needs a remaining
authorized aggregate. Keep acyclic source/logs -> inner -> outer -> wrapper
bindings. Do not validate the cache change by merely invoking its validator.

Create a standard-library independent audit script/output that checks raw inner
and outer records, current AST membership and typed declarations, old coverage
preservation, unchanged historical source/frozen records where applicable,
ledger bytes/chain and actual status lineage. Existing source membership remains
75 unless independently justified by existing glob semantics; no new source
module is planned. Inspect scoped diff to confirm only the permitted source
regions changed. Audit script is evidence tooling, not an extra test invocation.

Measure performance **only from the final accepted complete aggregate**. Report
its outer elapsed, recovery-suite elapsed, headroom `300 - outer_elapsed`, and
signed observed savings against 258.0717323209974 outer /
252.30142017400067 recovery seconds. A negative saving is valid evidence and
must be reported. This is one observation across changed suites/environment
timing, not a controlled causal speedup estimate. Acceptance needs real parse
reuse and the complete current-source passing aggregate within the unchanged
300-second limit, not a new speed threshold. If it does not fit, preserve the
timeout and remaining gaps without allocating extra probes or raising caps.

## 4. Immutable status lineage and evidence handoff

Main preserved REVIEW as `s1-recovery-status-before-plan-012.md`. Before dispatch,
main saves actual PLAN as `s1-recovery-status-before-implement-012.md`, updates
status to IMPLEMENT, and saves a durable `s1-recovery-status-implement-012.md`
snapshot. Freeze status through this implementation and supply its exact record
to the implementing agent. Main records saved-plan authority, approved limits,
budget scope and unchanged historical consumption before dispatch.

Create next-unused **s1-recovery-baseline-correction-010.json** from correction-009.
Preserve its full predecessor transition prefix, original baseline, bookkeeping
baseline/policy, all 38 frozen records and original ledger snapshot. Append the
existing canonical `s1-recovery-bookkeeping-transition-post-011.json` **directly**:
its old endpoint matches correction-009 and its old/new snapshots are durable
`s1-recovery-status-implement-011.md` and `s1-recovery-status-review-012.md`.
No replacement or repair of post-011 is required. Then append only actual
REVIEW -> PLAN and PLAN -> IMPLEMENT transitions, each canonical
`plan034-s1-bookkeeping-transition/v1`, each backed by exact durable before/after
snapshots. Any additional main status edit needs its own actual transition;
never invent an omitted snapshot or rewrite old status evidence.

Original ledger remains 447 events / 332,437 bytes / SHA-256
`2a0f66e38911b0ed029eb9dd0cf4bbd5da4a3b67abb577fbfe9ad67e6a888990`, chain head
`00cab019d73b6a3205f676b54cfb2f745f492fa5cca5c69b4567087cea62172b`.
Historical consumption remains 30 GPU attempts / 4,374.044265462899 seconds /
zero reserved; no active job or S1 recovery event. Preserve original events
250, 255, 256. Inspect bytes only; no production ledger API.

Create next-unused `s1-recovery-validation-011.json`, `s1-recovery-audit-011.json`,
`s1-recovery-independent-audit-011.py`, `s1-recovery-implementation-review-010.md`,
`s1-recovery-preparation-011.md`, `assessment-028-implement.json`, and iteration-012
launch/timing/process/ledger/bookkeeping/audit-observation records. Check all
vacancies before writing; use the next unused suffix if occupied and record the
actual links. Preserve every failed/partial run's bytes and consumption.
Record end-of-evidence UTC/monotonic time and actual total elapsed without
retroactively moving the start past inspection. Record the last source/test
activity against the cutoff and all remaining work. Main records any later
handoff/commit activity truthfully; it cannot repair an exceeded allocation.

Retain all historical limitations from assessment-026: diagnostic-011-001 lacked
a prospective note after failed prelaunch preparation; diagnostic-011-002's
synthetic child inherited OMP/OpenBLAS 4; all three focused invocations and the
first aggregate failed; only aggregate-011-002 supports the reviewed source.
Final thread transport fixed that behavior but does not erase it. Full staged
whitespace check 011 exited 2 for four immutable raw-log findings, while scoped
source/document check exited 0. Preserve both results and original raw logs.
Historical P31-5 and unavailable older timing/status evidence stay open.

Main inspects artifacts and scoped source diff, stages explicit task paths using
the existing escalated git approval, records full and scoped staged checks with
their actual outputs/exit codes, and commits only the validated milestone. No
push, amend or history rewrite. A local commit is a checkpoint; then continue a
fresh REVIEW under the active loop, unless a real stop condition applies.

## Acceptance and remaining objective

| Acceptance | Criterion mapping and evidence |
| --- | --- |
| A42-1 | S1-2/S1-3 prerequisite: exact `(text,module)` successful parse reuse, LRU bound 16 and defensive copies; real spy/key/eviction/isolation tests pass. |
| A42-2 | Preserve S1-1/S1-4 and current validation authority: real collection rereads all nine files, metadata-preserving changes are observed, deletion still fails, invalid parse never cached; no authority/file/receipt/result cache. |
| A42-3 | Preserve S1-1; advance S1-2 validation prerequisite: fresh complete nine-suite aggregate <=300 seconds, all previous substantive methods/typed callbacks plus exact new AST collection, no omitted/skipped checks, accurate timing comparison. |
| A42-4 | S1-4: independent current-source/receipt/frozen/ledger/lineage reconciliation, every launch preceded by successful durable note, resource/attempt/deadline compliance, immutable historical failures and truthful handoff. |

Only all four establish this plan's acceptance. Keep separate
`declaration_cache_milestone_complete`, `plan_acceptance_complete`,
`implementation_acceptance_complete`, `ready_for_live_admission`, and
`objective_complete`. The last three remain **false**. Keep supported receipt,
numerical-envelope, direct-script and reservation-clock milestone flags separate
from the new unverified cache milestone and Plan 041's false strict acceptance.

S1-1/S1-4 currently retain met support. S1-2/S1-3 remain not met. Next production
milestone is R9-2 bounded helper startup/transport and fresh sample timing after
review of measured validation headroom. Still open: R9-4 durable progress,
R9-5 structured failure/cleanup/final charge/acknowledgment and remaining R9-3
ordering, native/runtime/first-envelope matrices, real successful 510-row worker
progression with exact 340/170 split, synchronized contender/replay/lifecycle
coverage, current production admission/registration and the eventual live
calibration. Short worker barrier tests and synthesized controller rows do not
establish the missing full worker coverage.

The later calibration remains one attempt at
`min(3600, 93600 - gpu_elapsed_seconds - gpu_reserved_seconds) > 0`, cleanup
`min(30,effective_seconds/4)` inside it; reservation consumes the attempt even
without launch. Preserve one exclusive GPU group, 22 GiB device memory, eight
CPU workers, 150 GiB artifacts, 60 GiB downloads and existing 57,600-second
preparation/setup ceilings. No part of this plan authorizes that live work.
Reconstruction still requires separate later authorization.
