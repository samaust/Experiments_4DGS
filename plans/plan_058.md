# Plan 058 — R18-1 continuation: retain the measured whole aggregate and complete the F1.2/F5.3/F5.4 corrections

Prepared 2026-09-26 UTC by Main for the [S1 recovery objective](../docs/continuous-improvement/plan031-s1-recovery-20260919/objective.md). Plan058 is the next unused plan number after Plan057 and implements the continuation recorded by [assessment046](../docs/continuous-improvement/plan031-s1-recovery-20260919/assessment-046-implement.json) at the close of the [Plan057](plan_057.md) allocation (commit `343d067`). This plan does not accept Plan047 or complete Plan031; it is the bounded next CPU prerequisite.

## 1. Scope and preserved baseline

One milestone, in order: (a) launch the unchanged whole aggregate on the committed `343d067` source and retain the measured result; (b) implement Review018 F1.2 (work-deadline extension through the named compound operations); (c) implement F5.3 (P06 original-primary preservation) and F5.4 (bounded child boundary traces through already-permitted seams); (d) re-verify with one focused diagnostic and, if the launch inequalities allow, one final whole aggregate on the updated source. No new scientific scope, no split aggregates, no smaller fixtures, no relaxed assertion, deadline, limit, selector, or suite order.

Preserved without change (superset of Plan057 §1): all 248 collected methods, 1012 logical callbacks, every ordered old assertion expression, the six migrated declaration values, every original fixture, and all scientific checks; the historical records, failed receipts, partial sets 015/016/017, frozen38, correction015 transition prefix, raw 447-event ledger, and the committed Plan057 evidence (source manifest, baselines, diagnostic-018-001 receipt). The Plan057 landed changes (stages F1.1 clock ordering, s1_progress primitives fast path, contracts direct static comparison) remain as the implementation baseline; the 78-member contract source manifest is recomputed at IMPLEMENT start and hashed as the Plan058 baseline; no historical hash is rewritten.

Explicitly deferred to the following iteration (recorded continuation, not dropped): F3 callback-relevance rework (deadline_steps 114 callbacks, limits generic decoders, 22 alias cases) and F4 state/provenance/parser/cancellation coverage rework.

## 2. Findings to implement (from Review018, continuing R18-1)

### F1.2 — Work-deadline extension

Extend the original work deadline W through the compound operations Review018 names: `s1_progress.py` context/request reads and source hashing, `read_record` read/hash/decode combination, `candidate_inventory` decode/append/serialize steps, `ClosedInventory.recheck` loop-entry checks, `publish_segment_row` read-then-hash and qualified-row write, `first_record`/`reconcile_first`/`preserve_failure` compound branches, `s1_recovery.py::accept_result` and `prepare_terminal_evidence`, and `stages.segment` Publisher construction. Checks go immediately before and after real reads, hashes, parses, guards, serialization and publication. On lateness only already-open descriptors are retired and already-acknowledged metadata preserved; metadata diagnostics may use the original cleanup allowance only. Require actual read-return-at-W tests including accepted/reused/cleanup paths. Never replace the original primary with an observation/cleanup failure.

### F5.3 — P06 original primary

P06 records the original `TimeoutError` but finish/final handling changes `failure_kind` to `cleanup`: preserve original primary class/text/kind/phase/first occurrence independently and keep cleanup/publication errors ordered as secondary.

### F5.4 — Bounded child boundary traces

Persist bounded child boundary traces through already permitted artifact/transport seams (no new observer/helper/process) so P traces contain worker/helper raw guard, write, flush, fsync, close and readback events correlated with the owner trace. P05's exact attained point and bytes are recorded rather than a later claimed fault.

## 3. Execution environment and the owned-root blocker

Unchanged from Plan057 §3: strict final acceptance requires the Plan049 owned-root launch environment (genuine `launch-049-exec.py` driver admitted through the frozen `session_proof()` transcript correlation of real Main `exec_command`/`write_stdin` tool events). This harness has no Codex PTY session tools, so those events cannot be produced here; fabricating them is forbidden and will not be attempted. This milestone validates under timeout-mode capture (unchanged `s1_validation_capture`, 120 s/300 s caps and receipts). The 14 owned-root tests error environmentally (missing/invalid `S1_OWNED_ROOT_NOTE`); that is recorded as environment, not code defect. No assertion, deadline, or validation in the owned path is weakened to make the non-owned run pass.

## 4. Resource and execution limits (new plan-specific CPU allocation)

| Resource | Limit |
| --- | --- |
| Wall clock | 7200 s total for the milestone, including all inspection, editing, failed commands, waiting, test execution, cleanup and completed handoff |
| Source/test cutoff | 6000 s; 1200 s reserved for durable evidence and full readback/final answer |
| Focused collected invocations | At most 4; unchanged HelperSessionTests selector; 120 s outer timeout each |
| Whole aggregates | At most 2; unchanged 300 s outer timeout. The first launch is the mandatory milestone step (a) on the committed `343d067` source and is the first launched exec of IMPLEMENT. A second launch (final, on the updated source) requires the recorded F1.2/F5.3/F5.4 source change and the `elapsed + 300 < 6000` inequality |
| Real scenarios | Existing L01–L36 and P01–P06 only, serial; 2 s execution + 1 s safety-cleanup each; 126 s combined maximum inside the tighter outer timeout; zero additional real-child scenarios |
| Direct scripts | All existing six, serial; 10 s execution + 2 s cleanup each; 72 s combined maximum inside aggregate |
| Owned CPU work | B+max(1,H) ≤ 8 counted as in the existing contract; no extra thread/process/observer/helper |
| GPU/model/device | Zero invocations, probes, forwards, evaluations or GPU seconds |
| Production/scientific work | Zero controller/dry-run, production ledger API/write/reservation, production job directory, setup/download/smoke rerun, standalone profile or probe; disposable collected CPU fixtures only |

Before each exec: `elapsed + 120 + 300 < 6000` for focus, `elapsed + 300 + 300 < 6000` for the first (nonfinal) aggregate, `elapsed + 300 < 6000` for the final aggregate; equality cannot launch. All launched invocations consume attempts, including failed launches. Capture UTC/monotonic time with the available Python at IMPLEMENT's first shell command; preserve any actual exception rather than backdating.

## 5. Acceptance

**Milestone gate (achievable in this environment):**

1. The whole aggregate on the committed `343d067` source is launched as the first IMPLEMENT exec and its measured result is retained: either it completes with zero non-owned failures/errors/skips/discovery errors, exact source before/after agreement and `elapsed_seconds ≤ 300`, or the measured failed result is retained and the continuation recorded. Silent relaxation of the 300-second cap or the suite is forbidden.
2. F1.2, F5.3 and F5.4 land with focused evidence: read-return-at-W tests including accepted/reused/cleanup paths pass; P06 preserves the original primary class/text/kind/phase/first occurrence with secondary errors ordered; P traces contain correlated child boundary events and P05's exact attained point/bytes. The missing-clock case still raises the original expected exception (F1.1 regression check).
3. A focused diagnostic (HelperSessionTests, 120 s outer timeout) on the updated source passes all non-owned cases that complete with no new failures/errors versus diagnostic-018-001; owned KeyErrors are the only environmental errors.
4. The 14 owned-root cases are reported as environment-blocked with the exact error and the Plan049 owned-environment prerequisite; no owned-path assertion is weakened.

**Final gate (later, owned-environment only):** unchanged strict acceptance — all scenarios/direct scripts, zero failures/errors/skips/discovery errors overall, exact source before/after agreement, actual successful outer completion and elapsed ≤ 300 s — under a genuine Plan049 driver admission. This plan grants no permission for it and no candidate index.

## 6. Integrity and continuation

- No session-proof, launch-note, admission, identity-request, or census evidence is synthesized; the owned path runs only from genuine driver-produced records.
- Every committed change is task-scoped; Main owns staging and commits; commits occur only on completed validated milestones.
- If the milestone gate's aggregate cannot fit or a later source change cannot be re-verified inside the allocation, the measured results are preserved, the allocation closed, and the next iteration plans from them; no extra wall timeout, split aggregate, or invented permission blocker.
- Recorded continuation after this milestone: F3 callback-relevance rework and F4 state/provenance/parser/cancellation coverage rework (iteration 20), then Plan049 owned-environment strict acceptance.
- S1-2/S1-3 live calibration remains gated on strict acceptance plus separate later GPU authorization; nothing here touches GPU or production state.
