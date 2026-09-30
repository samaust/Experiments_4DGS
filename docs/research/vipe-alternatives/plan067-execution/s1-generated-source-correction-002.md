# Own the actual Torch import constructor

Recovery 008 failed at its first-result runtime capture with `S1 generated source
temporary ownership required`. It remains a consumed failed attempt: finish 558,
SHA-256 `518054576325370a9bbfb13ab662f1e0d116a9990cf1a1edc30e6fe83b038514`,
36.640664 seconds, confirmed cleanup. This correction does not accept its rows,
change historical evidence or authorize another GPU attempt.

## Diagnosis

The exact admitted Torch instantiator uses
`_TEMP_DIR = tempfile.TemporaryDirectory()` during import. That direct constructor
bypassed `backend_operation`; the previous CPU fixture instead supplied a gated
`OwnedTemporaryDirectory`. A deterministic canonical CPU regression using the
native direct constructor reproduced the exact ownership failure in 0.079 seconds.
An exact-parent, still-live directory ruled out path mismatch and early cleanup.

## Correction

Install a scoped constructor wrapper before `stages.segment` enters `_segment`,
which precedes its first Torch import. Only the admitted instantiator's exact
module name, code filename, `__file__`, verified source bytes, and argument-free
constructor enter the existing owned directory lifecycle. Its directory is created
under the supervised job temporary root and retains the existing work and cleanup
deadlines. Unrelated direct constructors retain ordinary stdlib behavior. Explicit
backend ownership uses the original constructor, preventing double ownership.
Restore the stdlib constructor on success or failure.

The generated-source module/template/hash/path checks remain unchanged. The
worker-boundary regression uses `stages.run`, a disposable trusted reservation
clock, a fake native import executing its exact admitted source filename, and
runtime evidence through capture, owned cleanup and final acceptance. It also
checks unrelated constructor behavior. An unadmitted constructor code path is
rejected and restores the original constructor. No real Torch or model import,
GPU access, live ledger write or inference is used by these tests.

## Validation

The 12 canonical `S1GeneratedSourceTests` and seven existing runtime provenance
tests passed (19 tests). Three changed Python files parsed successfully;
`git diff --check` passed. The root agent owns integrated independent review,
full-suite validation and a fresh current-source qualification. Any new GPU
identity remains subject to a separate reviewed proposal and explicit approval.
