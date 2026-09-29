# Plan049 correction014 — preserve process ancestry while permitting ancestor task-list drift

Prepared 2026-09-23 UTC under the [explicit authorization](authorization-049-ancestor-process-001.md) conveyed by Main. This narrowly changes which **non-root ancestor thread-list values** participate in live equality. It preserves full driver-root identity/census, all ancestor process identities and terminated-chain checks, and every other proof/limit. No source edit, runtime launch or acceptance occurs during this Plan stage. Independent implementation source review precedes any new runtime.

## Observed failure and historical disposition

Diagnostic004/session12134 received `ADMIT` and exited1 before note/exec-start/capture/output-directory creation. Its actual failure was `ValueError: Main prospective identity changed` at stage `before_note`, check `prospective_identity`. Correction012's diagnostic listed only `/preexisting_ancestors/0/threads`, `/threads_before`, `/threads_after` and their descendants. No root/process-identity difference was listed in that comparison. The complete observed list remains in [Main terminal](main-launch-terminal-049-diagnostic-004.json) and [tool terminal](main-session-049-diagnostic-004-terminal-001.json).

The saved first ancestor is PID92352/PPID35854/PGID92352/start_ticks5497285, **not PID1**. Positions44–51 in the difference paths are list indices, not literal TIDs. The original snapshot's positions44–47 contain TIDs124978,124993,124994,124995. New values were not fully emitted; do not invent them. This corrects the earlier shorthand while preserving the actual observation and user's general non-root-ancestor authorization.

004 remains an admitted/rejected pre-capture driver attempt with zero tests;001/003 remain separately retired and002 remains failed. Never reuse their sessions, paths or identities. A permitted future ancestor-thread difference does not retroactively turn004 into a success.

## Exact role-based identity rules

The sole equality exception applies only to records reached through the **actual non-root preexisting ancestor chain**, starting at the independently bound driver's PPID and terminating at the original PPID0 endpoint. Determine this role from the trusted caller/chain, never a caller-supplied JSON flag, environment setting, process name or arbitrary PID. The root cannot appear in that chain; cycles and substituted/truncated/reordered chains reject. An owned wrapper/worker/helper/sentinel/detached descendant cannot be relabeled an ancestor to escape census or charge.

| Record role | Equality and schema requirements |
| --- | --- |
| Driver root / capture root, and every task-owned process in creation/census/retirement records | All existing fields, full task lists, before/after process snapshots and before/after task snapshots remain exact/stable. Default validation stays strict. Root PID/start/PPID/PGID/boot or any root task change still rejects at its original check. |
| Non-root preexisting ancestor | Retain exact fields and strict primitive/nested types. Require `boot_id,pid,ppid,pgid,start_ticks` unchanged, and `process_before == process_after ==` that exact base at every sample. Compare these bases and nested process snapshots exactly across all live rechecks. Only equality of `threads`, `threads_before`, `threads_after` is excluded. |

For ancestor records keep the existing three observational task-list fields and current enumeration cadence; do not delete or forge them. Each list independently retains its current structural validation: exact task keys/types, positive PID/TID/start fields, correct boot/PID/process-start binding, sorted unique TIDs, leader membership and nonempty list. Only comparisons **between those three lists or between ancestor lists sampled at different times** may differ. No new tolerance for missing proc entries, failed reads, malformed lists, PID reuse, empty ancestry, ambiguous roles or exceptions is authorized. Such errors still fail closed; this change does not promise all possible host-thread churn is survivable.

Define a strict ancestor comparison projection by validating the record and excluding exactly the top-level keys `threads`, `threads_before`, `threads_after`; everything else remains present and equal. Never recursively strip arbitrary `threads` keys or ignore unknown fields. Root comparison uses the full original record without projection. Typed checks precede comparison, preserving bool/int/float rejection. Original authoritative serialized request/admission/note bytes **remain exact immutable snapshots**, including their observational ancestor lists: byte/hash and cross-document equality must not become projection-only or tolerate tampering. Live observations compare with the appropriate projection; published authority documents continue to agree exactly with the original snapshot.

## Narrow implementation scope and recheck coverage

Allowed files are R/`launch-049-exec.py`, `scripts/vipe_benchmark/s1_validation_contract.py`, and `tests/test_vipe_benchmark_s1_recovery.py`; R is this resolver directory. No helper-session/source/runner/capture/clock/backend/transport/environment expansion is needed. Existing `s1_helper_session.owned_workload` already checks current ancestor boot/PID/PPID/PGID/start fields and termination; leave it unchanged and verify its strict root/owned-task behavior remains effective through the contract.

1. **Driver sampler:** keep full stable root process and task sampling. Only actual ancestor calls use a narrowly internal role that skips `threads!=again` rejection; retain their process-before/after rejection, task observations and all other existing failure checks. No requery/retry/fallback or extra process/thread creation.
2. **Driver local stability:** `local_identity` still resamples and compares the full root exactly and samples every same ancestor PID in the same order. Compare ancestor process projections rather than full observational task lists. Root PPID starts the actual chain; verify each unchanged ancestor PPID points to the next and the same terminal endpoint remains. Never substitute a newly found process for the recorded PID/start pair.
3. **All prospective rechecks:** use full-root plus ancestor-process equality at `before_note`, `before_exec_record` and `immediate_pre_exec`, each against the original pre-admission snapshot. Preserve both pre-exec checks and their placement. This satisfies the requested exact same root/ancestry process IDs at the admission and pre-exec boundaries and retains the additional existing final check. No required check is removed or consolidated. Capture/runner later binds the same actual root and original chain.
4. **Contract:** keep `identity_record` strict by default for root, child, owned creation/census and retirement. Use a dedicated/internal ancestor validator or explicit trusted-call-site role only for `preexisting_ancestors` in session proof, note, Main binding and request validation. It permits list inequality only after checking every list's schema/binding. Preserve full exact authority-document matching and all terminated-chain/age/no-cycle checks. No external permissive switch is added.
5. **Diagnostics:** keep correction012's deterministic paths and original primary failures. For a rejection involving authoritative process equality, derive rejected-field paths from the actual compared full root/process projections so an allowed ancestor task-list change is not reported as the rejection reason. Do not hide rejected process fields. Retain the original observational lists in the saved request; no new observer or success-path dump is required.
6. **Authority bookkeeping:** align the exact ordered driver/contract/positive-test fixture addenda lists to001–014, including013's fixture-scope amendment. Bind the fixed new authorization record in note/driver/contract authority records and fresh Main dispatch/handoff; re-read/hash it with the existing fresh authority checks. Preserve the existing session-proof schema and its named correction008/session authorization, exact require_escalated-only start contract and all remaining fields. Mechanical fixture propagation must keep every positive graph valid before its negative mutation.

## Preserved negative control and additive evidence

Inside the existing `test_execution_mutations` nested-identity controls, the `thread_identity_substitution` fault currently changes `selected['preexisting_ancestors'][0]['threads_after'][0]['start_ticks']` and expects `stable thread identities around enumeration`. Under the authorized ancestor exception, that is no longer the proper target for this strict rejection.

Main explicitly authorizes moving **only that fault's mutated target** to `selected['ownership_root']['threads_after'][0]['start_ticks']`, retaining the original expected rejection string, assertion, fault name and all three enclosing locations (`note`, `main_binding`, `identity_request`). Use the original valid root thread's start tick plus1 as the substituted value: blindly retaining ancestor literal2 would be earlier than this fixture root's process start20 and hit `thread birth identity` instead of the preserved stable-thread predicate. This necessary fixture-value adaptation preserves the same single-field identity-substitution fault and its exclusive expected rejection; no declaration/parameter/expected assertion changes. Rehash the complete affected graph exactly as before. Other ancestor malformed-type/missing-key/extra-key/process-identity controls stay ancestor controls and must still reject.

Add controls within the existing methods/callbacks, without new declarations or counts, covering:

- Valid non-root ancestor task addition/removal/start-tick change across lists/rechecks is allowed while root and all process fields/chain stay identical.
- The same change in the root remains rejected; owned child/wrapper/detached task accounting remains unchanged.
- Each ancestor base/process-before/process-after field mutation, changed PID/start pair, reparenting/PGID/boot change, added/removed/reordered ancestor, cycle and terminal change rejects.
- Ancestor task malformed types/keys/binding, empty list, failed sample, or attempting to apply ancestor mode to the root rejects.
- Cross-document ancestor task-list tampering still rejects even though a separately sampled valid live ancestor list may differ.

Re-use pure source/fixture seams; do not create threads or processes to force ancestor churn. Preserve all original assertions, methods and literal callback IDs/order; save the exact one fault-target relocation and additive controls separately from earlier authorized assertion exceptions. No production/internal timing assertion changes.

## Independent review and next action

Implementer saves exact before/after source hashes, scoped diff, role/call-site map, preserved declaration/assertion evidence, aligned authority graph and static findings. The distinct validator must inspect every role dispatch and ensure only ancestor-list equality changed, root/owned defaults stayed strict, authority byte comparisons remain exact, and every live recheck still checks the same original root/process chain. Missing or ambiguous evidence blocks readiness.

After independent implementation source review, Main may prepare **fresh diagnostic005**, confirming vacancy/high-water and prior retirement, binding actual new source/authority/session/output records and retaining same-session live polls/ADMIT. No launch occurs under this planning assignment. If another identity predicate fails, preserve its exact paths/primary and review; do not expand this exception. Full unchanged no-timeout diagnostic/aggregate and all B1–B4 gates remain pending. No old runtime failure is reinterpreted.

All other requirements remain exact:78 source members,249 methods/1028 callbacks,42 real scenarios/six scripts/full510/340/170 guards; full root and owned-task census; B+max(1,H)≤8; one active subagent; ≤64MiB memo; ≤150GiB artifacts; original W/C/equality-is-late/internal scenario assertions; no operational time/attempt ceilings. No GPU/device/model/production/real-ledger/setup/download/scientific work, prompts, topology substitution, new thread/process or unapproved permission workaround. Main owns status/integration/commits.

## Bound inputs

| Input | SHA-256 |
| --- | --- |
| `main-launch-terminal-049-diagnostic-004.json` | `b860e4a9d21e5dc518d300de4d013e4c84cd437e97e1c87cacbda600dcf814ac` |
| `main-session-049-diagnostic-004-terminal-001.json` | `335e784b0cf8e098a3d5b3d6f8ee2388696426cc3e273135bf4e62a847165493` |
| `launch-identity-049-diagnostic-004.json` | `b7e9ab829fe0faa8d1ccf9d9cb3cbd44ffad9642d6a2b4e6c881a52eb33dc5e0` |
| Driver before014 | `ab319bc745be1fbaaa071e9f6228e52928f81ba8a2289e0f4a14f581788d57dc` |
| Contract before014 | `cc7f210956d0ac7b078ffd6e502390e4e3229cfd00c317956a4661ae845b98ad` |
| Recovery tests before014 | `ec0ed0f7283d7bd5cd52025c6b2fc1501a0903283e200797f659aa64f3052abf` |

Planning first observed UTC `2026-09-23 19:19:14 UTC`; earlier overhead unknown. Static reads and new planning/authorization artifacts only; no source edit/test/probe/session action/launch/git mutation.
