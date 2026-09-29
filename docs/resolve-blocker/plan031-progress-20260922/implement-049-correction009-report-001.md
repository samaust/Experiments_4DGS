# Plan049 correction009 implementation — static handoff

Implemented V008-1 and V008-2 within correction008's authorized scope. **Independent recheck pending; launch readiness is not claimed.** No test/project invocation, launch, admission creation, process/session action, commit, GPU/model/production/ledger/setup action or prompts read occurred. Static standard-library source work only.

## V008-1 — exact shell structure

The contract now requires byte equality to `shlex.join(['exec', absolute_python, '-B', fixed_driver, kind, str(index), reason])`. It no longer treats tokenized equality as shell structure. Exactly one canonical quoted exec command is admitted. A newline after exec, chain, leading whitespace or changed argv fails the exact command gate.

The start event must retain exactly these argument keys: `cmd`, `shell`, `login`, `workdir`, `tty`, `sandbox_permissions`, `yield_time_ms`, `max_output_tokens`. Fixed values are shell `/bin/bash`, login `false`, workdir ROOT, tty `true`, permission `use_default`, yield1000 milliseconds. Primitive types are exact, including bool versus int. `max_output_tokens` is a required positive exact integer whose chosen value remains bound verbatim by the event hash. No unknown option/environment override is admitted. Main confirmed these fixed values are suitable. This is polling metadata, not an execution timeout. Driver bytes and the no-timeout mode are unchanged.

Inside the existing cap callback, canonical valid proof remains the positive control. Seventeen new targeted start mutations cover newline, command chain, whitespace structure, altered command, cwd, tty, permission, yield/value/type, shell path/options, login/value/type, omitted shell, extra option, and invalid output budgets. Every event/proof mutation is rehashed, and rejection asserts the exact intended gate message. Added split-readiness positive and wrong-completion-event negative controls also rehash all event/proof records. No new method/subTest declaration/callback was introduced.

## V008-2 — exclusive nested identity witnesses

All24 retained nested identity mutations (eight faults at note, Main binding and request locations) now start by validating the restored unmutated graph through the same logical R routing. They retain logical fixed identity/admission references and rebuild identity bytes → readiness line/hash → event output/hash → event file record → proof/request/events → proof file record → admission bindings/hash → note bindings/hash. Original graph bytes are restored after each case.

The existing `assertRaises(ValueError)` expressions remain, capturing the exception, followed by exact expected-message assertions: parent identity required; exact nested process fields; exact positive thread identity: pid; exact thread identity fields; stable thread identities around enumeration; or typed ancestry terminal, as appropriate. An unrelated stale file, physical fixture path, proof/readiness correlation or later equality failure cannot satisfy those target messages. Each fault remains local to the selected representation, so its validator must reject before cross-representation equality; valid hash/path edges cannot mask that requirement.

## Static checks and unchanged scope

Standard-library AST/compile checks pass for all78 current source members plus driver. All622 class methods,249 collected methods,1028 typed callbacks, literal declarations/order, and every correction008 assertion in order/multiplicity are preserved. Only the contract and recovery test changed. Driver and all other76 source members, including capture/runner, remain byte-identical to correction008. Scoped `git diff --check` passes. Exact before/after source snapshots, incremental diff, AST/declaration/assertion map, preservation result and source-function map accompany this report. No operational timer or mode changed.

All new/retained controls were **source-inspected only**, not executed synthetically or observed against a real tool session. This is implementation evidence, not a runtime pass. External failed/ambiguous ADMIT-send reconciliation remains Main's duty as in correction008. No known source defect is intentionally left unresolved; distinct validation must inspect both corrected witnesses and all current hashes before declaring static launch readiness. B1–B4 runtime acceptance remains unestablished.

## Changed-file hashes

- `scripts/vipe_benchmark/s1_validation_contract.py`: `3a13bf06ec6076306f766747a546bd2c1223d91748ad07c9e3da468b1d12f3bd`
- `tests/test_vipe_benchmark_s1_recovery.py`: `e37dd54ea4f435daa96f006532e4a9383d1598e17e59ad72a66e235a704d4614`

Unchanged driver: `515e6832da0cbac4c8b1d19efa3a953bb1030f8ec9467f7508cabe4460992c29`.

## Duration

Pre-edit snapshot start 2026-09-23T16:41:06.711434+00:00, monotonic 75028.354528432; report end 2026-09-23T16:44:18.289603+00:00, monotonic 75219.932697875; measured interval 191.578169 wall seconds. Earlier handoff/inspection overhead unknown. CPU time unknown. No operational ceiling used.
