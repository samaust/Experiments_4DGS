# Independent Correction012/013 exact-source review

Reviewer `/root/blocker_review`; 2026-09-23 UTC. **source_launch_ready=true, narrowly for Main's next fresh driver attempt at diagnostic004 after its actual vacancy/high-water, freshness, resource and admission checks. No blocking source finding. Runtime acceptance=false/pending; aggregate clearance is not supplied.** This is the distinct source review required after the [combined plan verdict](validate-049-correction012-013-plan-review-001.md).

No test, project import, probe, function execution, session contact, launch, production ledger/API access, source edit or git mutation occurred. Standalone standard-library source/byte/AST inspection and in-memory syntax compilation were used. Only this report and its independent static audit were written.

## Exact source and authority

| Bound artifact/source | Bytes | SHA-256 |
| --- | ---: | --- |
| [Current driver](launch-049-exec.py) | 18105 | `ab319bc745be1fbaaa071e9f6228e52928f81ba8a2289e0f4a14f581788d57dc` |
| `scripts/vipe_benchmark/s1_validation_contract.py` | 44382 | `cc7f210956d0ac7b078ffd6e502390e4e3229cfd00c317956a4661ae845b98ad` |
| `tests/test_vipe_benchmark_s1_recovery.py` | 196488 | `ec0ed0f7283d7bd5cd52025c6b2fc1501a0903283e200797f659aa64f3052abf` |
| [Correction012](plan049-correction-012.md) | 9951 | `2cdf540e39fccb28a63b7b385b2f67f13f09fb9cd7b3697e5b2ee6cf162d02e9` |
| [Correction013](plan049-correction-013.md) | 3633 | `9e64e2b088822ba886c529b4482b4b00c7061ed1b1c43de2a3c449ffda279126` |
| [Combined independent plan verdict](validate-049-correction012-013-plan-review-001.md) | 4362 | `0529119a90b5446fd1dea2a70206affdccd7aedd2810042e6f4d95dc497dc471` |
| [Implementation manifest](implement-049-correction012-artifact-manifest-001.json) | 70588 | `983363d0c8882d56c291e83b584b7e318deb5cfe397daca839c294b8fb2649da` |
| [Incremental diff](implement-049-correction012-incremental-diff-001.patch) | 14594 | `005264178b3bf3532e69e3c5338fcf50c2f33055130ca40d799db367d7d6e5db` |
| [Final AST map](implement-049-correction012-after-ast-001.json) | 4186671 | `3c007a952ea80d36af2f0eca12d8ba316ab8eb19cda7a44576a235dd03c9308d` |
| [Implementation identity-preservation map](implement-049-correction012-identity-preservation-map-001.json) | 3004 | `4e8da7ccbacf941c33e654c6380468dced153112ae4d1236429162b958f9f2b9` |
| [Independent static audit](validate-049-correction012-013-static-audit-001.json) | 18620 | `e24a9774b6694b533756d9fc703f06f735cffa64f2dc8897e74966784da0c40c` |

All248 distinct records in the implementation manifest were independently rehashed with exact byte lengths: no mismatch/conflict. This includes current sources, before/after snapshots, reports/maps and separately bound012/013/plan-review authority. The static audit contains all78 current source records and the driver record. Membership was independently enumerated; only the contract and recovery fixture differ from011 among those78 members. The76 other members are unchanged. The separately tracked driver changed as reviewed below.

Both contract and recovery fixture were independently checked byte-for-byte against their pre012 snapshots: each differs by **only one** `,'plan049-correction-012.md'` insertion. AST inspection finds the same exact ordered001–012 literal tuple in driver, contract and fixture. Correction013 is separately hash-bound in the handoff and this review, as authorized, not inserted into runtime lists. Correction008 remains the named proof amendment. Every other proof, canonical command, exact require_escalated/justification/prefix, source-membership and admission check is untouched.

All622 current class-method normalized AST/assertion maps were independently recomputed and match the final saved map. All prior ordered assertions match011 exactly; there are zero new assertion removals or changes. The sole method AST change is the authorized literal append inside `test_execution_mutations`. Collected249 methods,1028 ordered typed callbacks and literal declarations remain identical. All77 Python members and the driver parsed/compiled to memory without execution. The prior reviewed discovery contract is unchanged; these observations are static preservation, not a runtime discovery/test receipt.

## Driver branch review

The incremental diff was inspected against the exact13117-byte baseline driver `b858d3a3787537ed3f58c6167066740c5f5de885379e3591162edc5572d298b0`.

| Original operation/predicate | Final behavior |
| --- | --- |
| `process`: row, tasks, tasks, row | The nested row/tasks ASTs and four sample-assignment ASTs are exact. No additional `/proc`, file, OS or process observation is introduced. |
| `first!=last or threads!=again or not threads` | Three ordered rejecting `if` branches use the exact original predicate ASTs. The first true branch raises the same `ValueError('unstable driver identity')`; subsequent predicates remain unevaluated, exactly as the original OR. All four samples still precede the first comparison. |
| Root census, complete ordered ancestry loop, cycle/missing ancestry rejection | Same calls/order/loop and original rejection messages. No matching by PID, truncation, field omission or normalized identity replaces the original records. |
| Root recheck OR full ancestry-list recheck | The root result is retained once and compared with the same inequality. A failure raises immediately and does not evaluate the ancestor-list comprehension. Otherwise that same ordered comprehension is sampled once, retained and compared with the original list. Both failures retain `ValueError('unstable full driver ancestry')`. |
| Initial identity | One call at the original location. Default stage `initial` sets only in-memory function metadata for an inner failure note. |
| Before prospective note | One original full local census retained by a named expression in the original inequality. Failure remains `ValueError('Main prospective identity changed')` before note/capture. |
| Before exec-start record | One full census at the original position after fresh authority/source checks and before exec-start. Failure remains `ValueError('driver identity changed')`. |
| Immediate pre-exec | One full census after original descriptor redirection and immediately before unchanged execve. Failure remains `ValueError('driver full identity changed immediately before exec')`. |

There are exactly four `local_identity` call sites. The extra stage argument/metadata does not observe external state or change census meaning. Only the existing census return is retained. Each outer failure branch is entered only after its local census completed and the original tuple comparison failed. An inner census exception propagates directly, without inventing a completed outer snapshot. Cycle and missing-ancestry rejections remain unchanged; extra labeling there was optional under012.

The original success path does not call `identity_difference`, create diagnostic dictionaries/notes, or render JSON. There is no catch that authorizes continuation. Each new failure branch constructs the original ValueError, attaches its note in a guarded block, and unconditionally raises that error. A BaseException during diagnostic construction/attachment is contained only to preserve the primary rejection and attempt a minimal unavailable note; it cannot reach exec. Sampling errors retain their original failure rather than being turned into incomplete accepted identity.

## Recursive diagnostic semantics

`identity_difference` reads only passed retained dictionaries/lists/scalars. It has no I/O or observation calls. Exact-type mismatches record their path; same-type dictionaries compare the sorted key union and stop at missing-key paths; same-type lists/tuples recurse in original common-index order and add container plus unmatched indices on length mismatch. JSON Pointer escaping handles `~` before `/`. A set deduplicates paths, and final paths are lexicographically sorted. No values/full records are emitted, and no differing path is intentionally dropped or truncated. Actual identity keys are strings and values are the existing built-in types.

Type-aware recursion is called only after the unchanged Python predicate rejects, so it cannot make equal values newly fail. The empty-thread branch reports `threads_nonempty` and `/threads_before_after` as an invariant instead of fabricating a nonempty expected snapshot. The process-first failure's `not_sampled=['threads_before_after']` means the later **comparison** was short-circuited; the raw task samples already exist, as the unchanged row/tasks/tasks/row sequence requires. The local-root failure's `not_sampled=['preexisting_ancestors']` refers to the unperformed ancestry **recheck**, not the initial ancestry baseline. This is consistent with012's explicit allowance for a prevented comparison, and must not be interpreted as a new census result.

Exception notes carry the prescribed schema, fixed stage/check, pointer list, not_sampled and invariant fields. They reach the original tool output before redirection and existing driver stderr afterward. The implementation report's input/output table is correctly labeled static design examples; no executed diagnostic-function result is claimed. Whether a real failing attempt yields complete collected note output remains a runtime observation obligation.

## Narrow next action and limits

Main may now prepare a **fresh diagnostic004 driver attempt** using these exact current source/driver hashes, actual vacant outputs and high-water checks, unchanged resource/storage checks, and entirely fresh identity/admission/same-session proof. Bind012,013 and this review in the appropriate Main evidence. Preserve the existing exact escalated start arguments and all pre-admission/at-admission/ADMIT/terminal reconciliation controls. This verdict supplies no reuse of003's identity, admission, session or index.

The purpose is to obtain informative evidence if the unchanged identity check fails again and, only if every existing admission/identity check passes, allow the originally pending collected diagnostic to run. A repeated mismatch still rejects capture and must be reviewed using its actual note plus terminal/partial-effect records. Preserve tool output and, when redirection occurred, driver stderr. Exec-start remains intent, not evidence of exec or capture.

Diagnostic003 remains retired as an admitted pre-capture rejection with zero capture/tests and unknown differing fields. No cause was inferred or repaired by these diagnostics. Corrections010/011 runtime timing, ownership/acquisition, protocol and acceptance obligations remain unresolved. B1–B4 remain unaccepted; original W/C/equality-is-late,42 scenarios/six scripts, full510/340/170 obligations, ≤8 charge,64MiB memo and150GiB artifacts remain. Whole-tree CPU time for this review is unknown. No operational time/attempt cap or additional work scope is introduced.
