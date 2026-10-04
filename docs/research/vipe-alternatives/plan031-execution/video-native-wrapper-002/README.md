# D10 ordinary setup CPU wrapper

This separate milestone preserves the reviewed D9 wrapper and common helpers.
No actual native qualification was executed here. D10 remains blocked until
actual D9 native qualification and the existing conditional D10 frame DO are
available, followed by original D10 supervised setup completion.

## Bounds and authority

The wrapper retains a 180 second outer deadline with 20 seconds for cleanup,
64 MiB capture allowance, seven CPU threads, inherited socket syscall denial,
PID identity/pidfd cleanup with subreaper adoption, and two strict method003 CPU
loads. It performs no inference, GPU work, downloads or ledger writes. Root
meters the entire command, including startup and terminal preservation.

The ordinary D10 setup must bind its dispatch, original request and runtime
request. Existing `execution_authorization` and `validate_D9_prerequisite`
validate conditional authority and actual qualified D9 ancestry against live
ledger events without an active-job exception. No approval is minted here.

Admission uses the applicable approved D10 proposal's CPU allocation, subtracts
existing evidence explicitly attributed to D10 and reserves 180 + 20 seconds.
D9 historical metadata charges and its owner-alias clarification are not charged
to D10. Shared CPU charges remain in the global budget. Private fixture capture
receipts must be settled once by root; unmetered preparation is not claimed zero.

## Integration and use

Integrate this commit only when the root source freeze permits. Bind all three
new Python files as supplemental sources in a fresh passed D10 source review
and actual clean combined CPU qualification before use. Regenerate inventories
if the helper closure changed. Keep issue #3 and actual rendering/review issues
open pending their actual outcomes.

Use explicit environment interpreter paths for the generators:

- `prepare_admission.py`: `--checkout --run --output --source-review --setup
  --cpu-qualification --authorization` (each flag takes its exact immutable path).
- `prepare_request.py`: `--root --run --source-review --cpu-qualification
  --cpu-admission --authorization --output --wrapper-output --capture-output
  --setup --setup-request --setup-dispatch`.

All output directories must be fresh. Request preparation prints the exact
root-owned wrapper command; root reviews admission and sources before execution.

## Validation and accounting handoff

20 CPU fixture tests passed; mypy passed for all three new Python files.
Independent Standards and Spec reviews report no actionable findings.

Unique fixture captures (outer interpreter invocation through return):

- `.local/d10-wrapper-fixture-001/receipt.json`: 0.096554461 seconds, 13 tests, return code 0.
- `.local/d10-wrapper-fixture-002/receipt.json`: 0.110790381 seconds, 20 tests, return code 0.

These captures are D10-owned, uncharged private receipts. Root should settle
them once; their unittest durations are subsets, not additional charges.
One type-check invocation reported tool wall time 0.300025255 seconds; its
outer process elapsed was not independently measured. Source inspection,
editing and independent reviews were unmetered and require conservative root
settlement. No actual native qualification, GPU use, installation, download,
filter execution or shared ledger mutation occurred.
