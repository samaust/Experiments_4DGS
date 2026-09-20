# Plan042 implementation review — exact-source declaration cache

A42-1 through A42-4 are supported by the completed aggregate and independent audit.
The bounded cache milestone is complete. Whole S1 implementation acceptance,
live admission readiness and objective completion remain false. S1-1/S1-4 retain
met support; S1-2/S1-3 remain not met.

## Changes and preservation

`parse_suite` returns a deepcopy of the private `lru_cache(maxsize=16)` result
on both hits and misses. Its exact full-text/module positional arguments are the
only cache key. The original parser body is AST-identical inside that helper;
failures propagate without entries. `collection` and every other contract function
are AST-identical and still read each current suite file. No source/hash/file,
receipt, ledger, runtime, row, admission or result authority is cached.

Seven new ordinary `DeclarationCacheTests` use real AST parsing with wraps spies,
tiny source strings and nine disposable suite files. They verify exact-key reuse,
text/module separation, fresh same-size/same-mtime reads, warm-cache deletion,
first-miss/nested return mutation isolation with exact primitive types, repeated
invalid syntax/declaration failures, and LRU16 eviction. Each test clears the
private cache at start and cleanup. Runner change is only the focused class name.
All 34 prior recovery test bodies/assertions and the entire literal callback
mapping are AST-identical. Only the three Plan042-permitted source files changed.

## Validation and observed timing

- Diagnostic `s1-recovery-diagnostic-012-001`: all 7 methods pass, no callbacks,
  failures, errors or skips. Tool completed exit0, chunk `0ebec9`.
- Aggregate `s1-recovery-aggregate-012-001`: all 176 methods and 426 typed callbacks
  pass across the unchanged nine-suite order, no failures, errors, skips or
  discovery errors. Tool session40850 completed exit0, chunk `3dd0bb`.
- All prior169 methods and426 typed callbacks execute in their original relative
  order; seven cache methods are the only additions. All six bounded direct-script
  children pass with preserved exact argv, raw outcomes, serial timing and caps.
- Outer elapsed206.6836401239998 seconds; recovery suite201.52797767700395;
  headroom93.3163598760002 under the unchanged300-second cap. Signed observed
  savings versus the prior accepted aggregate: +51.388092196997604 outer seconds
  and +50.77344249699672 recovery seconds. This is one complete-suite observation,
  not a controlled causal speedup estimate. No extra profiling or timing repeat.
- `s1-recovery-independent-audit-011.py` completed exit0. It independently reads
  ASTs, raw receipts/logs, source hashes, old coverage, six child records, exact
  invocation/environment/timing, launch notes,38 frozen files, the447-event ledger
  chain and actual status lineage. `s1-recovery-audit-011.json` reports75 sources.
- `s1-recovery-audit-observation-012.json` separately reconciles the new wrapper
  against raw inner/outer/audit records and all75 current sources without invoking
  the production validator. Source/log -> inner -> outer -> audit -> wrapper ->
  observation links are acyclic.
- Unstaged tracked `git diff --check` exited0. Main owns subsequent full and scoped
  staged checks; no staging or commit was attempted by IMPLEMENT.

## Allocation and procedure

The first action captured actual UTC2026-09-20T08:21:16.606625+00:00 and
monotonic76294.047193781 before inspection. New wall allocation1800 seconds,
execution cutoff1620, final evidence reserve180. One of three focused invocations
and one of two aggregate invocations were consumed. Each launch followed successful
AST preparation, vacancy/frozen-status checks, an exclusive fsync launch note,
closed-file exact readback/hash verification and an immediate full-timeout check.
The diagnostic reserved300 seconds for the final aggregate. No failed preparation
or launch occurred. All test/source activity ended by the aggregate driver's
completion at elapsed413.3133778939955 seconds; no source changed after its pass.
Final total evidence timing is recorded separately in `s1-recovery-timing-012.json`.

The cache creates no processes or threads. Suites and existing script children
were serial; all four native thread environment values were1 for capture and its
children under the eight-worker ceiling. No GPU/device/model operation, production
controller/ledger API, setup/download/smoke job, nested delegation, prompts read or
permission escalation occurred. Initial inspection requested nonexistent markdown
alternatives review-012.json/status.json; the actual markdown files were then read.
This was a path-name error, not a permission failure and not a test invocation.

## Immutable history and remaining work

Correction010 preserves correction009's full prefix, baseline/policy,38 frozen
records and ledger snapshot. It directly appends canonical post011 plus the actual
REVIEW->PLAN and PLAN->IMPLEMENT transitions, backed by durable main snapshots.
Status remains frozen at IMPLEMENT hash
b8fbcacf1d0cdf0efe7347d9e763a58f7988f63ee8f1f242e6eb5fdf942b253a /1026 bytes.
The ledger remains447 events/332437 bytes, original head and SHA unchanged;
historical consumption30 GPU attempts/4374.044265462899 seconds/zero reserved.
Original events250,255,256 remain exact. No S1 recovery event exists.

Plan041 strict acceptance remains false: missing prospective diagnostic001 note,
diagnostic002's prior synthetic worker OMP/OpenBLAS4, three failed focused runs,
and failed aggregate001 remain historical facts. Only aggregate011002 supported
its passing source. The full staged-review011 whitespace check exited2 on four
immutable raw-log findings; its scoped source/document check exited0. Clock barrier
completion_observation is a final controlled invocation/cleanup observation, not
universally first-publication completion. Short worker barriers and synthesized510
controller rows do not establish full510-row worker progression. Historical P31-5
and unavailable older status/inspection-inclusive timing evidence remain open.

After main's review and local milestone commit, the active loop proceeds to a
fresh REVIEW, with R9-2 bounded helper startup/transport/fresh samples as the next
production milestone to plan. Durable progress, conservative finalization/cleanup/
acknowledgment, remaining timing/native/runtime/first-envelope matrices, actual
510-row worker progression, synchronized contender/replay/lifecycle coverage,
current production binding and the separately bounded live calibration remain
open. Reconstruction still requires separate later authorization.
