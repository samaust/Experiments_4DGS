# Plan 057 — R18-1: fix the S1 progress regression, make existing cases relevant, and fit the unchanged whole aggregate in 300 seconds

Prepared 2026-09-26 UTC by Main for the [S1 recovery objective](../docs/continuous-improvement/plan031-s1-recovery-20260919/objective.md), finalizing [Review018](../docs/continuous-improvement/plan031-s1-recovery-20260919/review-018.md) R18-1 as one integrated CPU development milestone. Plan057 was created exclusively at the next unused plan number after Plan056. [Assessment044](../docs/continuous-improvement/plan031-s1-recovery-20260919/assessment-044-review.json) and [observations018](../docs/continuous-improvement/plan031-s1-recovery-20260919/s1-recovery-review-observations-018.json) are the fixed review inputs. This plan does not accept Plan047 or complete Plan031; it is the bounded next CPU prerequisite.

## 1. Scope and preserved baseline

One milestone, in order: (a) fix findings F1–F5; (b) make every existing callback relevant to its declared fault; (c) implement the bounded removal of redundant pure work so the **unchanged whole aggregate can finish within 300 seconds**. No new scientific scope, no split aggregates, no smaller fixtures, no relaxed assertion, deadline, limit, selector, or suite order.

Preserved without change:

- All 248 collected methods, 1012 logical callbacks, every ordered old assertion expression, the six explicitly migrated declaration values, every original fixture, and all scientific checks (Review018 §Concrete findings).
- The reviewed source baseline: Review018 read HEAD `ebf9d9ad39c25b5732fadefcdc36cb71e0bde613`. The current working baseline additionally contains the reviewed Plan049-thread commits `5ce0d53`, `db485e9`, `4ffb007`, `ead8b7c`, `653f51b`, `965e120` and the defect fixes `5a456bd`, `232d8f0` (Correction019 pidfd API). Those later commits already added the call-local `BoundedArrays`/`PureMemo`/`numerical_snapshot` machinery in `s1_evidence.py`, the `plan049-prospective-launch/v1` owned-root contract, and the reviewed runtime fixes. IMPLEMENT must recompute the current source manifest (78 contract source members via `s1_validation_contract.source_paths()`) and hash it as the implementation baseline; no historical hash is rewritten.
- All historical records, failed receipts, partial sets 015/016/017, frozen38, correction015 transition prefix, and the raw 447-event ledger remain untouched.

## 2. Findings to fix (from Review018)

### F1 — Required-clock regression and incomplete operation boundaries

1. `stages.py:98` dereferences `clock.work_deadline` before `require_clock(clock)`: require the clock first, derive W second, preserving existing expected exceptions/assertions.
2. Extend the original work deadline W through the compound operations Review018 names: `s1_progress.py` context/request reads and source hashing around line 592, `read_record` read/hash/decode combination, `candidate_inventory` decode/append/serialize steps, `ClosedInventory.recheck` loop-entry checks, `publish_segment_row` read-then-hash and qualified-row write, `first_record`/`reconcile_first`/`preserve_failure` compound branches, `s1_recovery.py::accept_result` and `prepare_terminal_evidence`, and `stages.segment` Publisher construction. Checks go immediately before and after real reads, hashes, parses, guards, serialization and publication. On lateness only already-open descriptors are retired and already-acknowledged metadata preserved; metadata diagnostics may use the original cleanup allowance only. Require actual read-return-at-W tests including accepted/reused/cleanup paths. Never replace the original primary with an observation/cleanup failure.

### F2 — Invocation authority and persistent ownership

1. `owned_workload` sets `anchor['validated_bytes']` after one verification and thereafter omits source/driver/dispatch/status byte validation: re-read/hash mutable authority at each required predispatch. Only immutable pure parsing of exact freshly obtained bytes may be memoized.
2. Integrate every creation site with the process-local registry: `test_l18_descendant_and_foreign_sentinel` spawns without its own predispatch check/immediate registration; `scenario_worker` registers after a fallible check whose failure precedes its retirement `try`; the supervisor and Owner must retain the PID and guarantee retirement even when full-identity registration fails, with a conservatively unresolved record before the first fallible identity read and a block on the next spawn until resolved. Register actual thread identities and before/after process identity, not merely numeric TIDs.
3. Ownership cases that write a different temporary note path then call an already pinned anchor reject at the common path/raw mismatch before the named checks: keep their IDs and old assertions, add target-specific reachability and a positive control, and exercise the relevant existing entrypoints through pure syscall seams. No extra real processes. B+max(1,H) stays ≤8.

### F3 — Deadline, capacity and alias row relevance

1. `test_progress_plan047_deadline_steps` maps distinct operations to shared entry calls and sets the clock before invoking guarded functions: keep all 114 callbacks and reach each distinct internal start/completion, including archive exception-finalization writes and the second raw array; tripwire the next operation, preserve actual partial bytes, and record descriptor retirement separately.
2. `test_progress_plan047_limits` routes every generic `*_bytes` row through one decoder call: keep the factored genuine large-storage preallocation tests and exact-limit values; use fixtures that reach each actual counter/parser and explicitly assert that lower limits or semantic membership did not mask it.
3. The `*_after_publish` alias cases never establish a provisional acknowledged fallback and its invalidation; `foreign_candidate_root` mutates an in-root field instead of supplying a foreign root; `row_replace_after_publish` changes bytes instead of replacing the descriptor/path: retain all 22 cases and implement the named construction, exact pointer/history assertion and stop/unusable result; keep the current generic checks as controls.

### F4 — State, provenance, parser and cancellation coverage

1. `produced_then_semantic_failure` and `first_identity_semantics` start from a qualified fixture and mutate a different in-memory row: start from actual produced-only first identity, persist the same invalid semantic row, acknowledge structural success, then fail its real semantic guard.
2. `worker_future_reference`/`worker_self_reference` substitute an all-zero hash; `worker_detached_identity` only asserts current PID binding equality; `fallback_invalidated` never acknowledges fallback: construct the distinct validly shaped references and states; keep existing worker-stale-interleave and exact-reuse checks.
3. `recover` builds the result from errors and counts without carrying checkpoint diagnostics/coverage into `stop_required`: preserve immutable lower bounds while retaining sticky bad state and dropped/first/last/primary diagnostics. `validate_diagnostics` null alternatives and `summary_adapter` uncertainty handling are tested at enclosing checkpoint/Consumer/recovery entrypoints.
4. `test_progress_plan047_recovery` has no dedicated `late_recovery` action; successor-body cases must distinguish intended metadata only from actually observed successor bodies, require uncertainty where provenance cannot establish optionality, and validate every retained previous/intended record's required binding without reading untrusted history.
5. Nested tests that permit `KeyError`/`TypeError` as generic success must prove the named exact validator executed before indexing; `result_duplicate_*` get enclosing result-inventory and protocol reachability; cancellation rows assert the forbidden suffix is empty, freeze the pointer before further read/retain/send, and keep visible-but-late ack explicit uncertainty. Owner acknowledgment and producer ack-receipt semantics stay distinct.

### F5 — P evidence correction and timing

1. Correct the addendum statement prospectively: P05/P06 do use the actual supervisor path (`progress_scenario` defaults `supervised=True`); the historical addendum is preserved and the correction recorded.
2. P01's exact primary is the scenario timing assertion (`observe_call:1108`, phase `worker_sample`): timing assertions inside the wrapper must not replace a pending primary exception during `finally`; record timing violations as separate failed evidence, preserve the original exception, and fix the underlying progress timing without relaxing the assertion or converting the historical record to a pass. Require explicit P01 original-deadline classification and tripwires for every forbidden late entry.
3. P06 records the original `TimeoutError` but finish/final handling changes `failure_kind` to `cleanup`: preserve original primary class/text/kind/phase/first occurrence independently and keep cleanup/publication errors ordered as secondary.
4. Persist bounded child boundary traces through already permitted artifact/transport seams (no new observer/helper/process) so P traces contain worker/helper raw guard, write, flush, fsync, close and readback events correlated with the owner trace. P05's exact attained point and bytes are recorded rather than a later claimed fault.

### F6 — Runtime reduction (enables the 300-second fit)

Observed costs (Review018 §F6, final017 controller trace): acceptance 34.2 s after worker_sample; the complete pair 67.9 s cumulative; final failed sample at 296.0 s; aggregate killed at 300 s inside deadline_steps. The current baseline already contains the call-local `BoundedArrays` (one immutable materialization per verified open snapshot) and `PureMemo` (one input/archive pair, 64 MiB ceiling, fresh anchored bytes/descriptor re-validation before every hit). IMPLEMENT must verify those mechanisms are actually exercised on the hot paths and then remove the remaining repeated work:

1. **No repeated decompression inside a guard.** Every NPZ member is materialized once per verified archive snapshot; no-object checks remain for every member; every raw open/read/hash and first materialization stays individually W-gated; buffers are local and discarded on guard exit/failure.
2. **Bounded memoization of deterministic transforms only.** Decoded numerical content and exact frozen RGB preprocessing are keyed by the full freshly obtained bytes plus shape/dtype and unchanged preprocessing inputs; a fresh anchored raw-file read/hash/identity check precedes every hit; every row's identity, provenance, native query, logits, class-assignment, instance/static, runtime, first-result and numerical-envelope checks still execute; only pure derived arrays/transform output are cached — never a row qualification, authorization, clock, request, acceptance, checkpoint or "validation passed" decision. The unchanged `processed_rgb` numerical function runs on misses; the memo clears on call exit and caps at one input/archive pair with the 64 MiB retention ceiling; larger inputs use the unchanged uncached path. A freshly observed changed byte must miss and re-evaluate or reject its authoritative record.
3. **Redundant fixture setup removed where the case does not depend on it.** RGB/valid records are computed once while constructing the immutable synthetic input document, keeping all original image dimensions, rows and bytes; a method-local real numerical fixture and a genuinely validated baseline document are shared for independent schema/primitive mutations; cases requiring actual publication, production entrypoints, state transitions, damage after ack or deadline crossings still create their real isolated state. No accepted-pointer copying or whole-guard stubbing. Record which setup is reused and which operation remains under test.
4. **Validation inside collected invocations.** Finite controls for same-path same-size byte changes with restored timestamps, path/inode replacement, request/context/identity/source changes, fresh-lookup deadlines, cache-byte cap/eviction and failure cleanup; compare optimized and uncached real guard checks/rejections over the original small fixture without doubling full 510-row runs; preserve every full 510-row guard already required, including both actual supervisor outcomes and the full parser acceptance case; save operation counts/trace and elapsed observations inside existing tests.
5. **Complete ownership and P evidence, then run the original full aggregate** (section 4).

## 3. Execution environment and the owned-root blocker

Strict final acceptance requires the Plan049 owned-root launch environment: a genuine `launch-049-exec.py` driver admitted through the frozen `session_proof()` transcript correlation (real Main `exec_command`/`write_stdin` tool events), which the 14 owned-root tests (`record_census`, `test_l18_descendant_and_foreign_sentinel`, ownership cases, `test_vipe_benchmark_s1_recovery.py:433`) validate. The current harness has no Codex PTY session tools, so those tool events cannot be produced here; fabricating them is forbidden and will not be attempted. Plan047's driver is stale against the current contract (it writes `plan047-prospective-launch/v1`, which `no_timeout_launch`/`owned_workload` reject).

Consequently this milestone validates under **timeout-mode capture** (the unchanged `s1_validation_capture` outer wait with 120 s/300 s caps and receipts), the same execution shape the recovery loop has always used. Under it, the 14 owned-root tests error environmentally (missing/invalid `S1_OWNED_ROOT_NOTE`); that is recorded as environment, not code defect, exactly as the direct-runner triage at commit `6f3b733` did. The milestone's pass decision covers every non-owned case; strict zero-error acceptance remains the later owned-environment gate and is not claimed by this plan. No assertion, deadline, or validation in the owned path is weakened to make the non-owned run pass.

## 4. Resource and execution limits (new plan-specific CPU allocation)

| Resource | Limit |
| --- | --- |
| Wall clock | 7200 s total for the milestone, including all inspection, editing, failed commands, waiting, test execution, cleanup and completed handoff |
| Source/test cutoff | 6000 s; 1200 s reserved for durable evidence and full readback/final answer |
| Focused collected invocations | At most 4; unchanged HelperSessionTests selector; 120 s outer timeout each |
| Whole aggregates | At most 2; unchanged 300 s outer timeout; one reserved for final current-source acceptance; a second launch requires a recorded source change or concrete invalidating concern |
| Real scenarios | Existing L01–L36 and P01–P06 only, serial; 2 s execution + 1 s safety-cleanup each; 126 s combined maximum inside the tighter outer timeout; zero additional real-child scenarios |
| Direct scripts | All existing six, serial; 10 s execution + 2 s cleanup each; 72 s combined maximum inside aggregate |
| Owned CPU work | B+max(1,H) ≤ 8 counted as in the existing contract; no extra thread/process/observer/helper |
| GPU/model/device | Zero invocations, probes, forwards, evaluations or GPU seconds |
| Production/scientific work | Zero controller/dry-run, production ledger API/write/reservation, production job directory, setup/download/smoke rerun, standalone profile or probe; disposable collected CPU fixtures only |

Before each exec: `elapsed + 120 + 300 < 6000` for focus, `elapsed + 300 + 300 < 6000` for a nonfinal aggregate, `elapsed + 300 < 6000` for the final aggregate; equality cannot launch. All launched invocations consume attempts, including failed launches. Capture UTC/monotonic time with the available Python at IMPLEMENT's first shell command; preserve any actual exception rather than backdating.

## 5. Acceptance

**Milestone gate (achievable in this environment):**

1. F1 ordering fix and F2 authority re-verification land with focused evidence; the missing-clock case raises the original expected exception.
2. Focused diagnostic (HelperSessionTests, 120 s outer timeout) passes all non-owned cases with no new failures/errors versus the recorded baseline (14 owned KeyErrors + the P01 timing assertion disposition documented).
3. The whole aggregate (300 s outer timeout) either completes with zero non-owned failures/errors/skips/discovery errors, exact source before/after agreement and `elapsed_seconds ≤ 300`, or the measured failed result is retained, the allocation closed, and the review/planning continuation recorded. Silent relaxation of the 300-second cap or the suite is forbidden.
4. The 14 owned-root cases are reported as environment-blocked with the exact error and the Plan049 owned-environment prerequisite; no owned-path assertion is weakened.

**Final gate (later, owned-environment only):** unchanged strict acceptance — all scenarios/direct scripts, zero failures/errors/skips/discovery errors overall, exact source before/after agreement, actual successful outer completion and elapsed ≤ 300 s — under a genuine Plan049 driver admission. This plan grants no permission for it and no candidate index.

## 6. Integrity and continuation

- No session-proof, launch-note, admission, identity-request, or census evidence is synthesized; the owned path runs only from genuine driver-produced records.
- Every committed change is task-scoped; Main owns staging and commits; commits occur only on completed validated milestones.
- If the milestone gate's aggregate cannot fit, the measured failed result is preserved and the next iteration plans from it; no extra wall timeout, split aggregate, or invented permission blocker.
- S1-2/S1-3 live calibration remains gated on strict acceptance plus separate later GPU authorization; nothing here touches GPU or production state.
