# Independent Correction012 plan review

Reviewer `/root/blocker_review`; 2026-09-23 UTC. Read-only source/artifact review, with this report as the sole write. No source edits, project imports, tests, probes, sessions, launches, production ledger/API access or git mutation.

**plan_ready=false; launch_ready=false. One narrow blocking plan finding: the exact addenda012 bookkeeping scope omits the existing recovery fixture.** The diagnostic design itself needs no weaker identity criterion. Diagnostic004 remains blocked until the plan omission is corrected, implementation is complete, and a distinct exact-source review declares readiness.

## Blocking finding C012-P1

[Correction012](plan049-correction-012.md) permits append-only addenda012 bookkeeping only in the driver and `scripts/vipe_benchmark/s1_validation_contract.py`, and explicitly prohibits any other source change. The contract at line585 constructs the exact addenda list; line586 requires equality with `command_bindings['addenda']`. However, `tests/test_vipe_benchmark_s1_recovery.py:810` constructs the positive admission fixture's literal001–011 list. Extending the contract to012 while retaining that fixture yields the `current correction authority` rejection in a previously valid fixture. This follows directly from the unequal lists; no test was run.

Required plan correction: also authorize **only appending `plan049-correction-012.md` to the existing fixture addenda list** in `tests/test_vipe_benchmark_s1_recovery.py`. Preserve `correction=addenda[7]` (Correction008), exact proof semantics, every assertion/method/callback/declaration and all other fixture behavior. This is authority bookkeeping, not new diagnostic behavior or a broadened test repair. Save/hash the corrected plan/planning record and obtain plan recheck before dependent implementation. Do not omit012 from actual authority merely to avoid the fixture discrepancy.

## Diagnostic003 evidence

The actual session result and send result are identical, correlate session11551 with diagnostic003, and record outer exit1 after `ADMIT\n`. The recorded output hash matches the exact output; Main's terminal summary carries the same traceback. It fails at driver line129, `if local_identity()!=(root,ancestors)`, with `ValueError: Main prospective identity changed`. The earlier checks and second full census returned sufficiently to reach that outer comparison; the saved records do not reveal which fields differed. No thread/ancestry churn, host cause or harmless mismatch is established.

The saved partial-effect record reports identity/admission/preparation/proof/session records present and launch-note, exec-start and diagnostic output directory absent. Read-only path checks still show those last three paths absent, with no symlink. The current driver places note publication, driver log opening, exec-start and execve strictly after the failed comparison. Thus this is an **admitted, rejected pre-capture attempt, with zero capture or test invocations**, not a suite failure and not a vacant index. The terminal summary's own path was recorded absent before that summary was written; its present existence is expected, not a contradictory partial effect. No permission failure is shown, and no retry of session11551 or index003 is justified.

Retain001's pre-admission abort,002's actual failed suite invocation and003's pre-capture rejection separately. The saved terminal tool-call wall time and synthetic summary timestamps are not whole-attempt CPU usage; whole-tree CPU time remains unknown.

## Identity preservation required by the plan

The plan's stated design is consistent with the current source's checks:

- `process(pid)` always samples `row`, tasks, tasks, `row` in that order before the short-circuit predicate `first!=last or threads!=again or not threads`. Enrichment must preserve both sampling and predicate order, distinguishing unperformed comparison from unavailable operands.
- `local_identity()` samples the root and full ordered ancestor chain, rejecting cycles and absent ancestry. Its stability expression samples the root again first; the ancestor-list comprehension is reached only if that root equals the original. In this failure case, `not_sampled` must describe ancestry accurately without issuing another read.
- The initial local identity and three later complete identities retain their current positions: before_note, before_exec_record and immediate_pre_exec. Their exact root/thread/full-ancestry comparisons remain authoritative. The first outer mismatch may expose already sampled differences from both root and ancestry; it must not pretend unsampled inner observations exist when `local_identity()` raises earlier.
- The compact path algorithm is a diagnostic only. JSON Pointer escaping, sorted key union, sequence order, missing keys, type differences and unmatched list indices are specified. Type-aware reporting may not change Python equality or cause a previously passing predicate to fail. Empty threads retain their real invariant failure. No PID matching, sorting away differences, snapshot retry, additional `/proc` read, tolerance or field omission is authorized.
- Failure attaches a JSON exception note to the same ValueError class and primary message. Diagnostic construction failure must leave the original rejection intact. Success produces no diagnostic output. The post-redirection channel remains the already open driver stderr; earlier failures remain in actual tool output. Exec-start continues to mean intent, not successful exec.

These are **plan constraints**, not proof of a source implementation that has not occurred. The requested static sample table is explicitly design documentation; it must not be presented as executed test evidence. A source reviewer must account for each original syscall/census call, boolean branch and exception path and verify no success-path diagnostic work or observation was added.

All prior admission/canonical command/same-session proof controls and010's exact require_escalated-only arguments remain. Correction008 stays the named trust amendment. Source membership, W/C, equality-is-late, local assertions, resource caps and prohibited work remain. No operational time or attempt ceiling is created. B1–B4 remain unaccepted.

## Checked bytes and readiness boundary

Thirteen plan/input/proof-event/authority file records were independently rehashed with matching byte lengths and SHA-256; no mismatch was found. Exact principal inputs:

| Input | SHA-256 |
| --- | --- |
| [Correction012, 9951 bytes](plan049-correction-012.md) | `2cdf540e39fccb28a63b7b385b2f67f13f09fb9cd7b3697e5b2ee6cf162d02e9` |
| [Planning012, 2938 bytes](planning-049-correction012.json) | `60e0dc7c8ba405ed4c9cba4b907fb0a6a0612a2348fb37d724e602dab084f5b7` |
| [Driver, 13117 bytes](launch-049-exec.py) | `b858d3a3787537ed3f58c6167066740c5f5de885379e3591162edc5572d298b0` |
| `scripts/vipe_benchmark/s1_validation_contract.py`, 44354 bytes | `7f9ec0b2938966216d00caaa22c2f8fe770207bf2c75fd7798e7fc1da5806d6b` |
| `tests/test_vipe_benchmark_s1_recovery.py`, 196460 bytes | `acf65b86b42ae2720bee17977ada9fe06a33f74ace2c01c7ef7cff09f95db5c7` |
| [Main terminal summary](main-launch-terminal-049-diagnostic-003.json) | `34fe0b0cc38457e91154c16a4d71eb8cbb80681536cd59e055e04b0657d10786` |
| [Actual terminal result](main-session-049-diagnostic-003-terminal-001.json) | `40c9d6f12e0ac42155d70ea95637e409ba7dfa797e987e43124d0c86a0c333d1` |
| [Identity request](launch-identity-049-diagnostic-003.json) | `57979b5a6a7b93852020756d527e6916f3b048c07ab5ac83a5feb3e1420f9365` |
| [Admission](launch-admission-049-diagnostic-003.json) | `69a4b5973bbc4fb9a093f0f9770cb71d495b959cc2e7a472b6a5cebdb8b164ce` |
| [Session proof](main-session-proof-049-diagnostic-003.json) | `e48055ed4eea785753bcd4f7cc43799c28dfa88213376ee026ca5f0ced92a69d` |
| [Actual send result](main-session-049-diagnostic-003-send-001.json) | `b448af67d725068eea773edeca7dc26e3f52dfc3df3777cbb301365f80c70010` |

After the narrow plan correction, implementation and distinct source readiness, Main may consider reserving004 using actual vacancy/high-water checks and entirely fresh source/identity/admission/session proof. Until then **no index004 preparation/reservation or launch is cleared by this review**. A later repeated mismatch remains a rejection requiring review of actual recorded paths; no relaxation is preauthorized.
