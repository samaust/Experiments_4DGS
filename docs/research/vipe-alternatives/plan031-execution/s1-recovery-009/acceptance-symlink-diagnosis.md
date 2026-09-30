# S1-009 acceptance symlink diagnosis

The S1-009 helper failed during final acceptance after numerical qualification.
The captured helper error is
`.local/vipe-alternatives/plan031-20260913T032700Z/jobs/S1-calibration-recovery-009/helper-error-b807c87d770a4e40a559fb317f1e56e6-2.json`.
Its traceback reaches `accept_result`, `referenced_records`, `strict_record`,
`verified_bytes`, and `read_bytes`: `os.open` with `O_NOFOLLOW` raises `ELOOP`
on `model.safetensors`.

Read-only inspection of the captured configuration confirms the cause. Both
`bert_snapshot` and `unidepth_snapshot` contain legitimate Hugging Face snapshot
aliases to adjacent regular blob files. All seven listed snapshot files use
`../../blobs/<blob-name>` targets. Weight blob names have 64 hexadecimal
characters; small Git blob names have 40. The admitted manifest carries the
payload SHA256 independently of the blob name. The snapshot aliases are neither
dangling nor cyclic at inspection. Their original request records deliberately
retain their lexical paths. The generic recursive evidence collector incorrectly
sent those admitted aliases through the regular-file reader.

A disposable CPU fixture reproduces the exact failure through public
`accept_result`, using real admission, reservation, first-result qualification,
and a synthetic 510-row result. The regression was run before the fix and failed
with the same `ELOOP` traceback in 17.944 seconds. No model implementation or
native Torch runtime is imported by the fixture.

The fix collects canonical regular target records and records snapshot aliases
separately in acceptance `asset_aliases`. Each binding contains the admitted
asset role, snapshot directory, original lexical file record, raw link target,
and canonical target record. Only file objects within the bound request's known
snapshot asset roles receive this treatment. Ordinary result and evidence
records retain strict `O_NOFOLLOW` reads.

Alias verification anchors parent directories with `O_NOFOLLOW`, checks lexical
membership in the admitted revision directory, permits only relative targets in
that model cache's sibling `blobs` directory, verifies target bytes against the
admitted payload hash and size, then checks the alias and its parent spelling
again. The target must itself be regular: target links, linked parent directories,
escapes, dangling targets, cycles, and changed bytes fail. Historical result
resolution freshly computes these bindings and compares them with acceptance,
so retargeting an accepted alias to identical bytes in a different blob also
fails. Historical acceptances without aliases keep their previous records and
may omit the new empty field.

The new `s1_asset_acceptance` suite is part of the current qualification contract.
Root integration owns the complete current CPU qualification and independent
review. Historical qualification receipts remain untouched.

This diagnosis and CPU fix do not accept or promote S1-009 or S1-007, change the
live ledger, authorize a new identity, or execute a GPU attempt. S1-009 remains a
consumed failed allocation with its original cleanup and stop evidence.

## Focused CPU validation

Using the explicit root `.local/envs/stg-colmap/bin/python` interpreter in the
isolated `plan067-s1-symlink-fix` worktree:

- `PYTHONPATH=tests <interpreter> -m unittest test_vipe_benchmark_s1_asset_acceptance test_vipe_benchmark_s1_runtime_provenance -v`: 14 passed in 119.490 seconds.
- The additional relative escape case in `test_acceptance_rejects_escaped_target_even_with_admitted_payload`: passed in 43.214 seconds, covering both absolute and relative escapes with identical payload bytes.
- Existing `S1RecoveryTests.test_binding_historical_versus_canonical_and_no_mutation`: passed in 0.839 seconds with the disposable receipt fixture's launcher bound to the explicitly selected interpreter.
- Static qualification collection: ten current suites, including all seven new acceptance test methods.
- All three changed Python files parse successfully; `git diff --check` passes.

The complete qualification and independent review are integration gates owned by
the root agent; these focused results do not replace those gates.
