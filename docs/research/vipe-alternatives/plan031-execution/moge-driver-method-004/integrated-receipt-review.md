# Integrated CPU receipt compatibility

The public driver request validator accepts the existing delta receipt and the
actual integrated full CPU receipt. Both require passing, unchanged exact source
inventories, matching record kind and the wall-limit checks. Integrated receipts
also bind reviewed HEAD/checkout/time, unchanged environment, exact CPU guards
and import/fixture/Matplotlib paths, and successful pytest/unittest cleanup.

The new public-request regression first failed because the integrated schema was
rejected. After the narrow fix, nine cases passed in 0.458 seconds. Cases reject
failed status, altered HEAD and unchanged flags, exposed GPU, substituted import
paths and command failure. Mypy `--check-untyped-defs --follow-imports=skip
--ignore-missing-imports` passed the changed module. Independent Standards and
Spec reviews passed the final delta without actionable findings.

Actual retained full008 field bindings were statically checked against HEAD
`0839217267f79cd8d725e25fd85c9a0eff006179`; its measured 953.608-second passing
capture is preserved. No model, GPU or shared ledger operation was performed
for this fix. Refresh the source review and bind a passing CPU delta to all
40 current D6 helpers after integration; this fix is not a fresh qualification.
