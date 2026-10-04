# Missing acceptance result correction

Baseline: `8b0aa921`. Branch: `plan069-qualification-acceptance`.

A scoped `mypy --check-untyped-defs` check identified indexing an optional
acceptance result. A public `supervise_reserved` regression reproduced the
`NoneType` error after a harmless successful CPU worker when the acceptance
helper returned no result. The supervisor now classifies this as `RuntimeError`
before terminal publication, retains failed supervision evidence and records one
failed ledger finish with confirmed cleanup and no accepted result. Success-only
indexing is guarded explicitly; production and ledger implementations are unchanged.

## Validation

- Red regression reproduced the previous `NoneType` error; green regression passed.
- 21 qualification admission/control/supervision CPU tests passed in 9.024 seconds.
- Scoped mypy passed for three qualification modules with `--follow-imports=skip`,
  `--ignore-missing-imports`, and `--check-untyped-defs`, using the root's private
  existing checker and CPU dependency overlay plus a private cache. No dependency
  installation occurred.
- Independent Standards and Spec reviews found no remaining findings.

The full combined qualification remains with the integration owner. This correction
runs no GPU/model, alters no production ledger, grants no attempt or readiness and
closes no issue. Actual producer/protocol/approval and outer accounting remain pending.
