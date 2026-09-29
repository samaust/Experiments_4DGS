# Plan049 correction012 — report exact rejected driver identity differences

Prepared 2026-09-23 UTC. **Correction012 is not a launch authorization:** this is a narrow append-only diagnostic-output correction to Plan049's existing driver identity checks. No field is tolerated, ignored, relabeled or removed. No identity mismatch becomes acceptable. Main owns implementation dispatch, distinct source review and any later fresh runtime launch.

## Failed attempt and unresolved fact

Diagnostic003 in session11551 received Main's session-bound admission and `ADMIT\n`, then exited1 at current driver line129:

```python
if local_identity()!=(root,ancestors):raise ValueError('Main prospective identity changed')
```

This was the second full local census, before prospective note publication. [Main terminal evidence](main-launch-terminal-049-diagnostic-003.json) and [actual send/terminal result](main-session-049-diagnostic-003-terminal-001.json) record no launch note, exec-start record, output directory, capture exec or suite invocation. Preserve003 as an **admitted, rejected pre-capture driver attempt with zero capture/tests**, not a retryable same-index slot or a test result. Preserve001's pre-admission abort and002's failed test invocation separately. No permission failure is recorded for003.

The exact changed fields are unknown: the error preserves the fact of inequality but not its operands. Do not infer thread churn, ancestry turnover, a root mutation, host behavior or a harmless cause from the message. No new observation here can reconstruct003's missing second snapshot. This correction enables the actual next failing check to describe its already-observed differences.

## Exact permitted implementation

The only behavioral edit is diagnostic enrichment in `docs/resolve-blocker/plan031-progress-20260922/launch-049-exec.py`, baseline SHA-256 `b858d3a3787537ed3f58c6167066740c5f5de885379e3591162edc5572d298b0` (13,117 bytes). Do not change any existing comparison, its operands' meaning, census order, short-circuit behavior, truth condition, deadline, capacity/ancestry/thread requirement, success branch or rejection exception class/message.

Store each **existing** census result in a local variable at the same operation point so it is available when its existing equality check fails. Do not take a fresh diagnostic census, retry an unstable sample or introduce a new `/proc` read. Preserve short-circuiting: when the original root comparison fails before the ancestor comparison, report only the root operands actually sampled and explicitly mark ancestor comparison not sampled. When `local_identity()` itself fails, report that inner failure; do not fabricate a complete outer observed identity.

Cover every existing identity comparison with a stable enclosing stage label:

- `initial`: initial prospective local identity, including its internal stability comparisons.
- `before_note`: post-admission full local identity compared to the original `(root, ancestors)` before note publication (003's failure site).
- `before_exec_record`: existing recheck inside driver log preparation before publishing exec-start.
- `immediate_pre_exec`: existing full local recheck after descriptor redirection, directly before `execve`.

Within each stage use fixed check labels for `process_before_after`, `threads_before_after`, `threads_nonempty`, `local_root_stability`, `local_ancestry_stability`, and `prospective_identity` as applicable. Passing labels generate no output and never become authority. Cycle/missing-ancestry failures retain their existing rejection; identify the invariant/stage if useful but do not pretend an unsampled value is a field difference.

On a failed comparison, construct a compact diagnostic from the **already retained expected and observed operands**, rooted under the relevant semantic names (`ownership_root`, `preexisting_ancestors`, `process_before_after`, or `threads_before_after`). The diagnostic uses this exact shape:

```text
{schema:"plan049-identity-diff/v1",stage:<fixed stage>,check:<fixed check>,
 different_paths:[<JSON Pointer strings>],not_sampled:[<semantic field names>],
 invariant:<null or fixed invariant name>}
```

Define recursive path comparison deterministically:

1. Use JSON Pointer escaping (`~`→`~0`, `/`→`~1`) for dict keys and decimal list indices. Sort string dictionary keys; compare the union. A missing key records its path once, without enumerating the absent subtree.
2. For lists/tuples of the same type, compare corresponding common indices in order. If lengths differ, record the container path plus each unmatched index path once; common indices still recurse. Do not match threads by PID/TID or reorder/reconcile lists, since that would obscure the original exact comparison.
3. A type difference records that path; differing scalar values record that path. Do not dump values, source contents or full identity records. Deduplicate and lexicographically sort the final pointer strings. Equality diagnostics are subordinate to the **unchanged original predicate**: a type-aware diagnostic must not turn a formerly equal comparison into a new failing check.
4. For the existing empty-thread rejection, use `invariant:"threads_nonempty"` and the corresponding threads path; label this an invariant failure, not a fabricated expected snapshot. `not_sampled` is empty unless original short-circuiting or an earlier error prevented that comparison. Do not silently truncate/drop changed paths; missing observability remains explicit.

Attach the compact JSON as an exception note prefixed `plan049-identity-diff/v1 ` to the **original ValueError**, then raise it through the unchanged failure path. Preserve original class and primary message such as `Main prospective identity changed`; the standard actual traceback includes the note. Before redirection this reaches the tool session output; after redirection it reaches the existing driver stderr file. Main must collect the relevant actual channel and original outer terminal result. No new log/file/observer/process is needed. If diagnostic construction unexpectedly fails, retain the original rejection and attach only a minimal diagnostic-unavailable note when possible; never replace the primary, swallow the error or continue to exec.

Mechanical authority bookkeeping may append correction012 to the existing exact addenda list in this driver and `scripts/vipe_benchmark/s1_validation_contract.py`; this is the sole permitted contract edit. Keep correction008 as the proof's named trust amendment and010's exact require_escalated-only start mode. Bind current driver/source hashes in fresh evidence. No change to proof schemas, source membership, test methods/callbacks/assertions, comparator semantics, capture/runner or any other source is authorized.

## Implementation, independent review and next attempt

Save a before/after driver diff and hashes. Static inspection must account for every original census call/branch and show: same sequence/count and short-circuit behavior; same predicates/error classes/messages; actual sampled operands reused; root/ancestor/thread/length/missing-field paths deterministic; no success-path diagnostics; failure cannot be converted to success; no new OS observation. Include a small documented input→path-output example table for unchanged, scalar, nested-thread, added/removed key, list-length and short-circuited ancestry cases, clearly marked static design examples rather than executed checks. No standalone probe, source import, test, socket operation, session action or launch is authorized during this correction's preparation.

A distinct reviewer inspects the changed source and exact preservation before Main may prepare a fresh launch. **Reserve diagnostic index004 only after implementation and independent source readiness**, then confirm all paths vacant and apply the existing high-water rule. Never reuse003's admission/session/identity record. The purpose of the next unchanged collected invocation is to observe the original identity checks with informative failure evidence and, only if they pass unchanged, run the pending suite. A repeated identity mismatch still blocks capture and requires review of the recorded differing paths; this addendum does not authorize a subsequent relaxation.

Main preserves tool/session and driver-stderr failures, whether or not note/exec-start files were created. An exec-start file records intent, not successful exec/capture. Distinguish pre-capture retirement from capture/tests and keep elapsed/unknown CPU accounting. B1–B4 remain unaccepted pending original independent runtime gates. No operational time or attempt ceiling is introduced; original W/C, internal assertions, B+max(1,H)≤8, ≤64MiB memo, ≤150GiB artifacts and all CPU-only/prohibited-work/permission/one-active-agent requirements remain unchanged. No prompts, production/ledger, GPU/device/model/setup/download/scientific work or git mutation by this Plan stage.

## Bound failed-attempt records

| Input | SHA-256 |
| --- | --- |
| `main-launch-terminal-049-diagnostic-003.json` | `34fe0b0cc38457e91154c16a4d71eb8cbb80681536cd59e055e04b0657d10786` |
| `main-session-049-diagnostic-003-terminal-001.json` | `40c9d6f12e0ac42155d70ea95637e409ba7dfa797e987e43124d0c86a0c333d1` |
| `launch-identity-049-diagnostic-003.json` | `57979b5a6a7b93852020756d527e6916f3b048c07ab5ac83a5feb3e1420f9365` |
| `launch-admission-049-diagnostic-003.json` | `69a4b5973bbc4fb9a093f0f9770cb71d495b959cc2e7a472b6a5cebdb8b164ce` |
| `main-session-proof-049-diagnostic-003.json` | `e48055ed4eea785753bcd4f7cc43799c28dfa88213376ee026ca5f0ced92a69d` |
| `main-session-049-diagnostic-003-send-001.json` | `b448af67d725068eea773edeca7dc26e3f52dfc3df3777cbb301365f80c70010` |

Planning first observed UTC: `2026-09-23 17:59:07 UTC`; prior overhead unknown. This is static planning only; no source change or new runtime observation occurred.
