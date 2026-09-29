# Independent Plan049 correction009 static recheck

**launch_ready: true for this exact source revision and the authorized session-bound admission workflow.** Both V008 findings are **met by source inspection**; no residual source blocker was identified. This does not establish a passing runtime or authenticate a real tool transcript. Final acceptance remains B1/B2/B3 **not met**, B4 **unverified**.

Reviewed correction009, both independent V008 findings, correction008 and its explicit user authorization/history, current driver/contract/control paths, exact before/after snapshots, incremental diff, manifests and preservation/function maps. No project tests/imports, extracted project-branch execution, launch, session contact, implementation/status edit, delegation or commit occurred. Standard-library inspection parsed source/AST, hashed files, reconstructed collection/assertion maps and diffs, and compared inert command strings only.

Wall duration through final manifest/source recheck: **169.061210 seconds**, 2026-09-23T16:44:52.481266+00:00 to 2026-09-23T16:47:41.542475+00:00. CPU time is **unknown**, not zero.

## V008-1 — exact sole-exec structure: met

`scripts/vipe_benchmark/s1_validation_contract.py:488–499` now constructs `shlex.join(['exec', absolute_python, '-B', fixed_driver, kind, str(index), reason])` and requires exact command-string equality. The previously admitted newline after `exec`, an appended `; true`, leading whitespace and altered `-B` differ from this canonical string and fail line491. There is no token-equivalence acceptance branch. Shell metacharacters/newlines inside a reason are safely quoted as argument data by the canonical representation; they do not license unquoted shell structure.

The start argument key set is exact: `cmd`, `shell`, `login`, `workdir`, `tty`, `sandbox_permissions`, `yield_time_ms`, `max_output_tokens`. Fixed values are `/bin/bash`, literal `false` login, ROOT workdir, literal `true` tty, `use_default`, and integer1000ms yield. Line498 checks both exact Python type and value, rejecting bool/int substitution. Output budget is a positive exact integer, bound verbatim in the event hash. Extra environment or execution options are rejected. Main must supply these exact explicit arguments when starting the driver; the yield is polling metadata, not an invocation timeout.

`tests/test_vipe_benchmark_s1_recovery.py:943–970` first checks a valid canonical proof, then exercises17 actual `session_proof` input mutations. Every changed event is rewritten/rehashed into the proof before calling the validator. Unchanged output hashes remain valid because these cases change only arguments. Each rejection is followed by exact error-text equality:

| Controls | Intended gate |
| --- | --- |
| newline, chain, prefix, changed command | `exact sole driver exec command` |
| missing shell, extra option | `exact start argument fields` |
| cwd, tty, permission, yield/value/type, shell/path/options, login/value/type | corresponding `exact start argument: <field>` |
| bool or zero output budget | `exact positive start output budget` |

All preceding proof/event/identity/stamp/output conditions remain valid in these constructions. Thus an unrelated stale-record or earlier schema failure cannot satisfy the asserted exact target message. The static audit independently records the legacy lexical collision and shows the strings differ under the current exact-comparison invariant. The project checker itself was not executed by this reviewer.

The new split-readiness control at973–989 supplies start/readiness/pre_admission/at_admission events, recomputes ordered stamps/output hashes/event records/proof, and completes the sole LF-delimited announcement in event1. The positive expects completion1; changing only that field to0 reaches the final `readiness event correlation` rejection. It restores the original three-event proof afterward. Existing production reconstruction accepts LF/CRLF, preserves all raw output and requires two live polls after readiness; CRLF execution remains unobserved.

## V008-2 — exclusive identity witnesses: met

At recovery1074–1115, each of the eight faults at each of three locations (24 cases) begins with a successful `no_timeout_launch` check of the restored original graph through the same logical router. It then deep-copies note/admission, rereads the original request, and changes only the selected representation. No physical fixture path is substituted into a logical authority record.

Lines1091–1107 rebuild every affected edge: logical identity file record → exact readiness JSON/hash → start output/hash → all event file records → proof request/event records and proof file hash → logical admission request/proof bindings and admission hash → note admission/list bindings and note file hash. For note-only/Main-binding faults the request bytes are unchanged but their graph is still reconstructed consistently. Lines1113–1115 restore original request/events/proof/admission/note bytes before the next positive control.

The retained `assertRaises(ValueError)` remains, and line1112 adds exact target-message equality. Independent source tracing of all fault paths agrees with these expectations:

| Fault at each of note/Main binding/request | Exact expected error | Current production check |
| --- | --- | --- |
| `process_ppid_bool` | `parent identity required` | contract345 rejects bool before nested equality |
| `process_extra`, `process_missing` | `exact nested process fields` | contract342 exact nested field set |
| `threads_before_bool` | `exact positive thread identity: pid` | contract355 exact integer field |
| `threads_after_missing`, `thread_extra` | `exact thread identity fields` | contract353 exact field set |
| `thread_identity_substitution` | `stable thread identities around enumeration` | contract360 compares the complete stable snapshots after valid field checks |
| `terminal_ppid_bool` | `typed ancestry terminal` | contract561 rejects bool before terminal equality |

`typed_binding(note)` and `typed_binding(command_bindings)` run at564 before cross-representation comparison; the request's typed binding runs at581 before its equality/proof checks. Earlier representations remain valid for each selected location. Unrelated hash/path/correlation rejection has different text and cannot satisfy the expected error. This closes the exclusive-attribution gap without removing old assertions. These are executable collected controls whose outcomes still require Main's aggregate; they were not run here.

## Preservation and inherited readiness

Independent audit confirms all78 current source records and exact before/after snapshots; correction009's before-set is exactly the correction008 after-set. Only the contract and recovery test change. Driver SHA remains `515e6832da0cbac4c8b1d19efa3a953bb1030f8ec9467f7508cabe4460992c29`; other76 source members, capture/runner/stdin/source enumeration/cache and scientific behavior remain byte-identical. The incremental diff reproduces exactly. All77 Python sources plus driver parse; six function maps match; scoped `git diff --check` passes.

All622 class methods,249 ordered collected methods,1028 exact typed callbacks and literal declaration/order remain. Every correction008 assertion remains as an ordered subsequence with multiplicity; no new assertion removal. Only `test_execution_mutations` changes method AST. This structural preservation is separately supported by the semantic control review above.

The unchanged driver still rejects preexisting admissions and retired/non-increasing indices, always requires ADMIT, and rechecks actual stable local root/thread/full terminated ancestry after ADMIT, before durable exec-start and immediately before exec. Source/authority/proof/output/capacity checks, no-timeout/legacy timed behavior and the explicitly authorized `session-bound/v1` trust distinction remain unchanged. Correction009 narrows source behavior within correction008; its evidence manifest binds correction009 while the unchanged launch schema retains correction008's exact authority/addenda set. No cross-namespace kernel attestation is claimed.

| Criterion | Static readiness | Final acceptance |
| --- | --- | --- |
| B1 | met | not met — current collected controls, numerical/deadline/ownership/recovery outcomes still needed |
| B2 | met for unchanged reviewed source | not met — six real P outcomes and correlated complete primary/secondary traces still needed |
| B3 | unverified | not met — one complete current-source249/1028 aggregate, all42 scenarios/six scripts/full guards, zero errors/failures/skips/discovery errors and actual outer exit0 still needed |
| B4 | met for source scope/preservation and admission mechanism | unverified — actual tool/session provenance, live resource bounds, full owned retirement and duration evidence still needed |

Main may proceed with fresh exact prospective admission and the preserved diagnostic workflow, using the next unused diagnostic index (002 if still vacant). New recovery/contract controls are outside the diagnostic selection and must execute in the unchanged whole aggregate. The validator must later correlate original actual tool results with copied events/proof/admission and ADMIT send/terminal evidence; on-disk graphs alone do not prove a live session or successful send. Ambiguous send, source drift, unresolved ownership or missing outer completion still blocks acceptance. No operational timeout/attempt cap is reinstated; original W/C and scenario limits remain.

## Hash-bound evidence

- Independent audit `validate-049-correction009-static-audit-001.json`: `fecb64ca281488de15ec31e505c34234a786cec3ba4d558fc2a2071075cd5627`.
- Contract: `3a13bf06ec6076306f766747a546bd2c1223d91748ad07c9e3da468b1d12f3bd`.
- Recovery tests: `e37dd54ea4f435daa96f006532e4a9383d1598e17e59ad72a66e235a704d4614`.
- After map: `4d1d215edc1c010dba6b4a4e18c7b51adf68c85fb1ff950fa686aaa358dbc1c3`.
- Correction009: `c4298d6c63f4c96ca416b583d98041e3b5f8c909feeea01c4885595616d82fa6`.

The audit contains every current source/authority hash, exact snapshot/diff/preservation derivation and source-function map. All268 manifest/map file-record occurrences were rehashed after inspection; no drift. The stored historical pre-edit git-diff artifact hash was checked, without reconstructing its historical git base. This verdict binds the recorded working-tree bytes, not git HEAD alone.
