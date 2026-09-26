# Plan 059 — R18-1 continuation: callback relevance (F3), coverage rework (F4), and the bounded redundant-work removal (F6 items 1–4), then the final whole aggregate

Prepared 2026-09-26 UTC by Main for the [S1 recovery objective](../docs/continuous-improvement/plan031-s1-recovery-20260919/objective.md). Plan059 is the next unused plan number after Plan058 and implements the recorded continuation of [assessment048](../docs/continuous-improvement/plan031-s1-recovery-20260919/assessment-048-implement.json) at the close of the [Plan058](plan_058.md) allocation (commit `f28d86c`). This plan does not accept Plan047 or complete Plan031; it is the bounded next CPU prerequisite.

## 1. Scope and preserved baseline

One milestone, in order: (a) land F6 R18-1 items 1–2 in source (NPZ single materialization per guard; bounded validation-call-local memoization of deterministic transforms of freshly verified content); (b) land F6 item 3 (redundant fixture setup removal) together with F3 (every deadline/capacity/alias row reaches its named distinct internal start/completion, all 114 callbacks preserved) and F6 item 4 (finite mutation/deadline/eviction controls inside collected invocations, no standalone profile); (c) land F4 (the five state/provenance/parser/cancellation sub-reworks); (d) re-verify with one focused diagnostic and, if the launch inequalities allow, one final whole aggregate on the updated source, retaining the measured result either way.

Measured basis (iteration 19, receipts in the Plan058 commit): in the official timeout-mode environment the whole aggregate hits the unchanged 300 s cap at 300.0 s with 199 ok, exactly the 14 owned-root errors, 0 failures, 78/78 sources unchanged, killed inside the supervisor suite; per-test profiling of the four slow plan047 tests (deadline_steps 82.4 s, complete_final_sample 35 s, result_summary 16 s, limits 13 s unprofiled) attributes the dominant cost to repeated pure qualification work — 3741 `qualify_row` calls across the four tests (≈110 s), each re-running `validate_result` (single call 16–17 s: numpy `isclose` over the sample arrays plus `contracts.instances`/`np.unique`), plus test-side `observe_operation` instrumentation wrapping 52k+ operations in `deadline_steps`. This is the concrete redundant work R18-F6 names; no timeout, cap, suite, or fixture size is touched.

Preserved without change (superset of Plan058 §1): all 248 collected methods, 1012 logical callbacks, every ordered old assertion expression, the six migrated declaration values, every original fixture (including the full 510/340/170 acceptance guard and the full parser acceptance case), all scientific checks, the historical records, failed receipts, partial sets 015/16/17, frozen38, correction015 transition prefix, raw 447-event ledger, and the committed Plan057/058 evidence. The iteration-19 landed changes (F1.2 fine-grained work-deadline gates in `s1_progress.py`) remain the implementation baseline; the 78-member contract source manifest is recomputed at IMPLEMENT start against `f28d86c` and hashed as the Plan059 baseline; no historical hash is rewritten.

## 2. Findings to implement (from Review018, continuing R18-1)

### F6 items 1–2 — Redundant-work removal (source, `s1_evidence.py` / helpers)

1. Materialize each NPZ member once per open, verified archive snapshot; preserve the no-object check for every member; reuse that same immutable array within that guard. Every raw open/read/hash and every first materialization stays individually W-gated; buffers local, retained bytes bounded, discarded on guard exit/failure. An already completed local array operation is not permission to start another operation at W.
2. One validation-call-local memo entry for decoded numerical content and exact frozen RGB preprocessing, keyed by the full freshly obtained bytes plus shape/dtype and the relevant unchanged preprocessing inputs. Before every hit: fresh anchored raw-file read/hash/identity checks and exact byte comparison to the retained immutable key, then execute every row's identity, provenance, native query, logits, class-assignment, instance/static, runtime, first-result and numerical-envelope checks. Cache only pure derived arrays/transform output — never a row qualification, authorization, clock, request, acceptance, checkpoint or “validation passed” decision. Use the unchanged `processed_rgb` numerical function on misses. Clear on call exit; cap the optional memo to one input/archive pair with an explicit 64 MiB retention ceiling and use the unchanged uncached path for larger inputs. No global/path/mtime cache; no reuse between controller outcomes or rows with different freshly observed bytes; a fresh observed changed byte must miss and re-evaluate or reject its authoritative record immediately.

### F3 — Callback relevance (test side, `tests/test_vipe_benchmark_supervisor.py`)

Make every deadline, capacity and alias row test its declared fault: `array_npy`/`array_hash` and `npz_member`/`npz_finalize`/`cleanup_next_array` must each reach their distinct named internal start/completion instead of a shared entry call; the clock may not be set before invocation in a way that lets an unrelated preceding metadata read stand in for the named operation; publication cases advance time by having the immediately preceding real I/O return late, not by a pre-operation boundary hook. Keep all 114 callbacks. Tripwire the next operation, preserve actual partial bytes, and record descriptor retirement separately. Instrumentation narrows to the named operations (the broad `observe_operation` wrapping is replaced by per-row targeted observation) without dropping any old assertion expression.

### F4 — State/provenance/parser/cancellation coverage (test side, five sub-reworks)

1. `produced_then_semantic_failure` and `first_identity_semantics`: start from an actual produced-only first identity, persist the same invalid semantic row, acknowledge structural success, then fail its real semantic guard; fail on the same sealed version/same identity inside the publication path.
2. `worker_future_reference`/`worker_self_reference`/`worker_detached_identity`/`fallback_invalidated`: construct the distinct validly shaped future/self-issued references (not an all-zero hash substitution), assert the actual authority/state binding, and acknowledge fallback. Existing worker-stale-interleave and exact-reuse checks remain.
3. `recover` (accepted bodies/head provenance): carry checkpoint diagnostics/coverage into `stop_required` so a trusted checkpoint with coverage conflict/overflow cannot recover as integrity-verified with `stop_required=false`; preserve immutable lower bounds while retaining sticky bad state and dropped/first/last/primary diagnostics; test the `validate_diagnostics` primary/first/last null alternatives at the enclosing checkpoint/Consumer/recovery entrypoints; `summary_adapter` retains the uncertainty and diagnostics rather than only a truncated errors list.
4. `test_progress_plan047_recovery`: a dedicated `late_recovery` action with real clock advancement (distinct from `accepted_exact`/`history_tripwire`); explicitly distinguish intended metadata-only from actually observed successor bodies; require uncertainty where provenance cannot establish optionality; validate every retained previous/intended record's required binding without reading untrusted history.
5. Nested-validator and cancellation rows: prove the named exact validator executed before indexing (no `KeyError`/`TypeError` generic success); give `result_duplicate_*` enclosing result-inventory and protocol reachability for their existing callbacks; cancellation rows assert the forbidden suffix is empty, freeze the pointer before further read/retain/send, keep visible-but-late ack explicit uncertainty, and keep owner acknowledgment versus producer ack-receipt semantics distinct.

Prospective additive cases, only if needed for the mutation controls above, require exact literal IDs and an explicit relevance map; a callback total alone never suffices.

### F6 item 3 — Redundant fixture setup (test side)

Compute rgb/valid records once while constructing the immutable synthetic input document (all original dimensions, rows and bytes preserved); share one method-local real numerical fixture and one genuinely validated baseline document for independent schema/primitive mutations. Cases requiring actual publication, production entrypoints, state transitions, damage after ack, or deadline crossings still create their real isolated state and traverse those paths. No copying an accepted pointer or whole-guard stub. Record which setup is reused and which operation remains under test.

### F6 item 4 — Optimization and relevance controls (inside collected invocations)

Finite controls: same-path same-size byte changes with restored timestamps; path/inode replacement; request/context/identity/source changes; fresh-lookup deadlines; cache-byte cap/eviction and failure cleanup. Compare the optimized and uncached real guard's checks/rejections over the original small fixture without doubling full-510 runs. Preserve every full-510 guard already required, including both actual supervisor outcomes and the full parser acceptance case. Save operation counts/trace and elapsed observations inside existing tests; use real immediately preceding operations for before/equal/after deadline tests; do not force the desired exception by changing only entry time.

### R18-1.5 — Final aggregate

Rebind launch authority to the current dispatch/status/plan and current 78-member source membership (the capture's per-launch census does this). Save exact named-boundary reachability, control/fault result, fixture/hash, pointer, original W, counter values and ordered primary/secondary events for every required row.

## 3. Execution environment and the owned-root blocker

Unchanged from Plan058 §3: strict final acceptance requires the Plan049 owned-root launch environment (genuine driver admission through real `exec_command`/`write_stdin` tool-event correlation). This harness has no Codex PTY session tools; those events cannot be produced here and fabricating them is forbidden. This milestone validates under timeout-mode capture (unchanged `s1_validation_capture`, 120 s/300 s caps and receipts). The 14 owned-root tests error environmentally (missing/invalid `S1_OWNED_ROOT_NOTE`); recorded as environment, not code defect. No owned-path assertion, deadline, or validation is weakened to make the non-owned run pass.

## 4. Resource and execution limits (new plan-specific CPU allocation)

| Resource | Limit |
| --- | --- |
| Wall clock | 7200 s total for the milestone, including all inspection, editing, failed commands, waiting, test execution, cleanup and completed handoff |
| Source/test cutoff | 6000 s; 1200 s reserved for durable evidence and full readback/final answer |
| Focused collected invocations | At most 4; unchanged HelperSessionTests selector; 120 s outer timeout each |
| Whole aggregates | At most 2; unchanged 300 s outer timeout. The first launch is the post-change verification aggregate on the updated source; a second (final) launch requires a recorded further source change plus `elapsed + 300 < 6000` |
| Real scenarios | Existing L01–L36 and P01–P06 only, serial; 2 s execution + 1 s safety-cleanup each; 126 s combined maximum inside the tighter outer timeout; zero additional real-child scenarios |
| Direct scripts | All existing six, serial; 10 s execution + 2 s cleanup each; 72 s combined maximum inside aggregate |
| Owned CPU work | B+max(1,H) ≤ 8 counted as in the existing contract; no extra thread/process/observer/helper; the memo is working memory inside the existing process, not a new cache service |
| GPU/model/device | Zero invocations, probes, forwards, evaluations or GPU seconds |
| Production/scientific work | Zero controller/dry-run, production ledger API/write/reservation, production job directory, setup/download/smoke rerun, standalone profile or probe; disposable collected CPU fixtures only |

Before each exec: `elapsed + 120 + 300 < 6000` for focus, `elapsed + 300 + 300 < 6000` for the first (nonfinal) aggregate, `elapsed + 300 < 6000` for the final aggregate; equality cannot launch. All launched invocations consume attempts, including failed launches. Capture UTC/monotonic time with the available Python at IMPLEMENT's first shell command; preserve any actual exception rather than backdating.

## 5. Acceptance

**Milestone gate (achievable in this environment):**

1. F6 items 1–2 land in source with the bounded memo exactly as specified (call-local, one input/archive pair, 64 MiB ceiling, unchanged uncached path otherwise, cleared on exit; no decision/row-qualification caching; no global/path/mtime cache); the finite controls of F6 item 4 pass inside collected invocations, including same-path same-size mutation with restored timestamps and path/inode replacement.
2. F3 lands: all 114 callbacks preserved, each declared deadline/capacity/alias row reaches its named distinct internal start/completion, tripwired next operation, actual partial bytes preserved, descriptor retirement recorded separately; every ordered old assertion expression retained.
3. F4 lands for all five sub-reworks with the stated construction (produced-only first identity, validly shaped future/self references, coverage-conflict `stop_required`, `late_recovery` clock advancement, exact-validator reachability and empty-forbidden-suffix cancellation).
4. A focused diagnostic (HelperSessionTests, 120 s outer timeout) on the updated source passes all non-owned cases that complete, with no new failures/errors versus diagnostic-019-001; the 11 owned-root KeyErrors are the only environmental errors.
5. The post-change whole aggregate is launched when the inequality holds; its measured result is retained (zero non-owned failures and `elapsed ≤ 300` s with exact 78/78 source agreement, or the measured failed result with the continuation recorded). The 14 owned-root cases are reported environment-blocked. No owned-path assertion weakened; no cap/suite/fixture change.

**Final gate (later, owned-environment only):** unchanged strict acceptance — all scenarios/direct scripts, zero failures/errors/skips/discovery errors overall, exact source before/after agreement, actual successful outer completion and elapsed ≤ 300 s — under a genuine Plan049 driver admission. This plan grants no permission for it and no candidate index.

## 6. Integrity and continuation

- No session-proof, launch-note, admission, identity-request, or census evidence is synthesized; the owned path runs only from genuine driver-produced records.
- Every committed change is task-scoped; Main owns staging and commits; commits occur only on completed validated milestones.
- If the optimized aggregate still exceeds 300 s, the measured result is preserved, the allocation closed at budget, and the next iteration plans the remaining reduction from the saved per-test operation/elapsed observations; no extra wall timeout, split aggregate, or invented permission blocker.
- Recorded continuation after this milestone: Plan049 owned-environment strict acceptance (the 14 owned-root cases), then S1-2/S1-3 live calibration recovery under separate later GPU authorization.
