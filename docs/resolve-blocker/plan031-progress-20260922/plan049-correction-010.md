# Plan049 correction010 — fixed escalated launch permission and diagnostic002 corrections

Prepared 2026-09-23 UTC. This append-only correction follows the failed diagnostic002, the independent review relayed by Main, and the successful single exact-operation permission retry. **A distinct reviewer must review this correction and the durable diagnostic review before implementation, and must independently review the resulting sources before any new runtime launch.** This document launches nothing, edits no implementation source, waives no acceptance criterion and does not convert diagnostic002 to a pass.

## 1. Preserve the exact failed outcome and evidence limits

Diagnostic002 was admitted through the authorized `session-bound/v1` proof in session64795. Its no-timeout capture took **22.85966287899646 wall seconds**, returned1 and produced an actual outer exit1 without timeout. Child PID3 was matched-waited with return1 and recorded absent afterward. The recorded after-creation owned census was B2/H0/charge3; this narrow observation does not by itself prove every scenario's lifetime/cleanup. Sources before/after agree. Preserve all command/session/proof/admission/exec-start/terminal files and original output bytes.

Counts use different granularities; never add them together or silently substitute one for another:

| Evidence unit | Total | Passed | Failed | Errored | Skipped |
| --- | ---: | ---: | ---: | ---: | ---: |
| Receipt methods | 73 | 43 | 11 | 19 | 0 |
| Receipt logical callbacks | 334 | 87 | 11 | 236 | 0 |
| unittest stderr result occurrences/sections | 265 | not an occurrence total | 20 | 245 | 0 reported |

Discovery errors are0. Receipt `passed=false`, `expected_exit_code=1`; expected failure exit means faithful reporting, not acceptance. It is a focused supervisor diagnostic, not the required whole aggregate. None of the 249-method/1028-callback aggregate obligation or 42-scenario/six-script/full-guard coverage is discharged by these totals.

The independent reviewer reports **240 of245 ERROR sections** are real `PermissionError: [Errno 1] Operation not permitted` at `s1_progress.mailbox`'s `socket.socket(AF_UNIX, SOCK_DGRAM)`. P02–P05 assertions explicitly retain that EPERM. The same cause for P01/P06 is plausible but **unproved**; all six final P outcome records are missing. Preserve the original failures and classify unsupported causal attribution as uncertain. Additional non-socket failures below remain even if sockets work.

Main's independent review currently exists as a conversation report, not a saved reviewer file. Before dependent implementation, Main must save the complete report faithfully as a fresh `review-049-diagnostic002-001.md` (or next vacant explicit successor), retaining reviewer identity, exact findings/locations, counts and uncertainty, and hash-bind it in the correction dispatch. The finding groups below are inherited from that relayed review, not a fresh independent audit by this planner. Existing durable receipt/execution/stderr/outcome bytes were inspected and rehashed; those records bind the diagnosis pending the required durable report.

## 2. One successful permission retry; fixed future mode

[main-permission-retry-001.json](main-permission-retry-001.json) records that Main first checked diagnostic002 terminal state and partial effects, then made the repository-mandated **one outside-sandbox retry of the exact failed socket-creation operation**:

```text
python3 -c 'import socket; s=socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM); s.close(); print("AF_UNIX datagram socket creation and close passed")'
```

It used `sandbox_permissions=require_escalated`, succeeded and immediately closed the socket. It ran no project test and contacted no service. The original invocation used `use_default`; this contrast supports the diagnosed sandbox restriction for socket creation. It does not establish bind/send/receive, entire protocol behavior, source correctness or a passing suite. No denial or missing allow rule is recorded. The `.json`-named retry artifact contains prose; preserve and hash its actual bytes rather than assuming JSON parsing.

For **new current Plan049 runtime invocations**, replace the exact fixed start argument `sandbox_permissions='use_default'` with **`sandbox_permissions='require_escalated'`**. Do not accept both values, omit the value, infer it from environment, or let the caller choose a permission mode. Do not rerun002; the next diagnostic is **003**, subject to vacancy/high-water checks. Aggregate uses its next vacant index (001 if still vacant). Retain001 as aborted pre-admission and002 as the first failed capture/test invocation, with separate driver-attempt and capture-exec accounting and all durations. Plan049 has no operational attempt or time cap.

Preserve the correction009 exact canonical shell command:

`shlex.join(['exec', absolute_original_interpreter, '-B', fixed_R_driver, kind, str(index), reason])`.

The exact execution-affecting start fields remain `/bin/bash`, `login=False`, repository absolute `workdir`, `tty=True`, `yield_time_ms=1000`, and positive exact-int `max_output_tokens`; command/cwd/environment/stdin/proof/identity/output/resource binding stays unchanged. For the escalated tool call, extend the exact start-argument key set with **required** `justification` and `prefix_rule` and bind them as follows:

- `justification` is exactly `Run the reviewed Plan049 CPU-only <kind> after the exact AF_UNIX datagram socket retry succeeded.` where `<kind>` is the already validated `diagnostic` or `aggregate`.
- `prefix_rule` is exactly `['exec', absolute_original_interpreter, '-B', fixed_R_driver]`, matching the actual command prefix. No broad `python`, shell or arbitrary executable prefix is introduced. If the tool/approval policy rejects this exact request or prefix, stop affected work and report the exact error; do not substitute a different mode or command without review.

These request fields are recorded verbatim in the start tool event, validated with exact primitive/list/string types, and correlated to the actual tool invocation by the independent reviewer. The contract checks the recorded requested mode; it does not pretend that a repository string proves platform enforcement. Require the actual successful tool start result, same-session live polls and normal driver local identity revalidation. Escalation may expose a different namespace/ancestry; bind its actual current identities without assuming002's PID values or relaxing terminated ancestry/ownership/cap checks. It does not restore independent cross-namespace kernel attestation.

Keep every existing `session-bound/v1` readiness/output-hash/path/source/authority/schema/liveness/ADMIT rule. No observer or transport substitution. Bind corrections001–010 in the exact ordered admission/driver/contract addenda records; correction008 remains the proof schema's named trust-model correction, while010 supplies the new permission requirement through the addenda. Preserve prior artifacts under their historical source/schema revisions; never rewrite002's `use_default` event into an escalated one or validate old failures retroactively under changed source.

Permission policy still applies at each real failure. A new already-escalated denial/failure gets no further permission retry. Record exact command/error and definite versus suspected restriction, inspect partial effects, stop affected work and retain ownership uncertainty. An approval pending is not a rejection. The successful socket retry supplies neither another generic probe allowance nor authorization to replay successful state changes.

## 3. Ordered evidence-supported implementation scope

First preserve the full diagnostic002 source/receipt/error baseline and Main's saved independent report, then have a distinct reviewer approve this narrow plan. After that, the implementer addresses the permission contract and the remaining finding groups in one bounded-to-scope correction. No source or transport semantics change is justified merely by EPERM.

Permission/proof edits are confined to `scripts/vipe_benchmark/s1_validation_contract.py`, R/`launch-049-exec.py`, and the existing admission mutation controls in `tests/test_vipe_benchmark_s1_recovery.py`. Add positive/negative controls for the single fixed escalated mode, rejected default/omitted/alternate mode, exact justification/prefix, and altered command/shell/options; retain every old assertion and literal callback. An existing permission-negative fixture that now equals the required value must change only its injected invalid value to keep the same negative predicate and callback identity, documenting the exact declaration/AST effect. If that would require an old expected assertion or declared callback change, obtain a concrete addendum first.

The following additional corrections remain within Plan049's existing allowed files, specifically `scripts/vipe_benchmark/{s1_progress,s1_helper_session,s1_cpu_helper,supervisor}.py` and `tests/test_vipe_benchmark_{supervisor,s1_helper_fixtures,s1_recovery}.py` where the actual call graph requires them. No automatic change to every listed file; record each finding→changed path→reached control. No runner/capture/clock/generic-file/API/environment/backend expansion, scientific behavior change or new method/scenario is authorized by010. Escalate a concrete necessary out-of-scope change through a separate addendum before editing it.

| Finding group inherited from independent diagnostic review | Required correction and evidence |
| --- | --- |
| Eight ownership mutation controls masked by stale records | Identify the eight exact existing IDs from the saved report/logs, distinct from V008's earlier set. Establish a valid routed baseline, mutate only the named authority field and rehash all dependent records. Require target-specific rejection/reachability; an unrelated stale hash/path must not satisfy the assertion. Keep identities, callbacks and original predicates. |
| Scenario secondary control observes2 opens versus expected1 | Determine whether extra acquisition is real redundant work or observation of the wrong seam. Fix the production redundancy or precisely target the intended real operation. Preserve expected1 and all primary/secondary/ownership assertions; do not change the count to2 or add dummy work. |
| L25/L26 and Plan046 deadline-boundary mismatches | Reproduce the exact existing boundary in collected seams, identify the immediately preceding real operation, and repair the gate or fixture attribution while preserving original W/C, injected values and equality-is-late. No later cutoff or relaxed timing comparison. |
| L08 late-owner result mismatch | Inspect actual owner acknowledgment/late-result/retained-pointer state; repair the behavior or faithful fixture construction against the original expected result. Preserve late-result rejection and independent retained lower bounds. Do not credit a late reply to satisfy the test. |
| L24 missing captured reserve event | Restore the genuine capture/observation of the existing reservation event at its real production seam, with exact identity/order. Do not synthesize a reserve event or infer it from a successful count. |
| L35 bootstrap import fixture defect and >2.0s assertion | Correct only the fixture's required import/bootstrap wiring with the original interpreter/environment contract and real existing child. Retain the original ≤2.0s internal assertion and report its subsequent measured result separately; fixing import does not establish timing compliance. |
| L36 acquired=false; UnboundLocalError masks primary; missing scenario artifact | Make acquisition/handle state explicit before fallible work, preserve original primary on the no-acquisition path and retire every actually acquired resource. Save the real outcome through existing permitted evidence handling even when startup fails; no invented success/acquired flag. Require original and secondary fault order plus artifact presence. |
| Closed-inventory deadline entry gate | Gate the actual enclosing entry before the first forbidden operation and retain before/equal/after behavior. Verify target entry and empty forbidden suffix, not a generic later TimeoutError. |
| Full-completion interpreter O_NOFOLLOW symlink ELOOP | Diagnose the actual interpreter-reference/fixture path and preserve no-follow protection for evidence. If it is a legitimate fixture interpreter symlink, bind the actual trusted executable target during permitted fixture preparation with exact original interpreter provenance; keep original launch argv/interpreter qualification. Do not globally follow symlinks, disable O_NOFOLLOW, replace the interpreter or relax alias/authority guards. If a safe scoped repair cannot be established, return the concrete path/contract conflict for review. |
| All six P final outcome records absent | Preserve002's absent records as a gap. Ensure existing P01–P06 execution paths persist genuine final primary/secondary/timing/pointer/cleanup outcomes through existing bounded seams on failures, without replacing the primary or performing forbidden post-W/C work. Retain actual real supervisor boundaries. P02–P05 EPERM is explicit; investigate P01/P06 without assuming the same root cause. |

No finding is deemed fixed by static intent or by socket creation succeeding. Keep the original tests/assertions/internal deadlines. If an existing assertion proves logically incompatible with its intended contract, document the exact contradiction and request a separate narrow plan decision; this correction authorizes no reflexive relaxation. Distinguish source defects, fixture defects, masked controls, permission failures and still-unproved hypotheses in the handoff.

## 4. Gates before implementation, launch and acceptance

1. **Plan review first:** save/hash Main's full independent diagnostic review; distinct reviewer checks010's permission/trust scope, exact start fields, finding coverage and absence of acceptance relaxation. No implementation until this review is complete.
2. **Implement and static handoff:** save before/after source records, exact scoped diff, literal callback and ordered assertion maps, per-finding correction/control map, permission argument fixtures, source syntax checks and duration/unknown-CPU journal. No runtime test/probe by the implementer; Main owns launches. Do not revisit the already successful socket retry.
3. **Distinct source recheck:** independent reviewer inspects all corrected paths and mutation relevance, exact require_escalated-only validation/command bindings and preservation. Mark launch readiness only for exact inspected hashes. Unresolved source/fixture findings block a speculative blanket rerun unless reviewer specifies which remaining uncertainty requires the next unchanged collected invocation and why the preserved tests will resolve it.
4. **Main fresh runtime:** after readiness, prepare diagnostic003 with fresh source/authority/output records, actual approved escalated start tool arguments, same-session pre-admission/at-admission polls and exact ADMIT proof. Preserve all no-timeout behavior and actual terminal results. Do not replay002 or reuse its proof. Failed/ambiguous effects follow original reconciliation and permission rules.
5. **Independent runtime validation:** assess actual new collected evidence by criterion, reusing only still-applicable checks. Any further correction follows the established implementer→distinct-validator loop without a fixed attempt/time ceiling; no unchanged passing rerun. Whole current-source aggregate, all249 methods/1028 callbacks, 42 scenarios, six scripts and all full510/340/170 guards remain required, with zero failures/errors/skips/discovery errors, unchanged source membership and actual successful outer completion. CPU ownership/retirement and storage bounds must also pass.

Retain B+max(1,H)≤8, one active subagent, no extra observer/process/thread/helper, serial real scenarios/scripts, ≤64MiB memo, ≤150GiB artifacts, original W/C and behavior deadlines, exact scientific settings and all historical nonacceptance. No GPU/device/model/production/real-ledger/setup/download/scientific work or prompts. No operational wall/CPU/invocation/attempt ceiling is reintroduced. Main owns status/dispatch/integration/commits. B1/B2/B3 remain unaccepted and B4 unverified until complete independent evidence; escalation alone changes none of those states.

## 5. Hash-bound input evidence

| Input | SHA-256 |
| --- | --- |
| [Main diagnostic outcome](main-diagnostic-outcome-049-diagnostic-002.json) | `8d91ee7128c63f29fd341721d8693dbf68c507d08cc372adf97eb8193db94cf6` |
| [Diagnostic002 receipt](diagnostic-049-002/receipt.json) | `037edb31baa726de6778ddd91c45204c899e99e4838dcd49ba2b64a238f7edd8` |
| [Diagnostic002 execution](diagnostic-049-002/execution.json) | `8eb45c586dd0128ca366e93e22b6db09af54a5ee9d0d73927315349e7f0b9ca6` |
| [Diagnostic002 stderr](diagnostic-049-002/process-stderr.log) | `5fc417373e37b5bbdf516f21fa72aa4bf0d86f3b3f2204208da9aa371afbd9bb` |
| [Single permission retry](main-permission-retry-001.json) | `33455675c84fb4a33be28ed43f6efbbb12806f1b0e5921a0b30b154a571d059f` |

Planning first observed UTC: `2026-09-23 17:02:02 UTC`; earlier start overhead unknown. This stage only inspected saved evidence/source and created planning artifacts: no source edit, test, socket retry, session action, launch or git mutation. Main retains the duration journal and all unknown whole-tree CPU usage.
