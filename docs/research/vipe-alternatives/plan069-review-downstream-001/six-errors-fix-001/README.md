# Six-error diagnosis and correction

Diagnosed using `diagnosing-bugs`, with independent GPT-6 Astra High diagnosis
and review. Base commit: `f0aa339138bc1351244e60c658c98ec78ad27e46`.

## Causes and fixes

| Original errors | Cause | Correction |
| --- | --- | --- |
| Dense report: one | matplotlib absent | Private CPU dependency overlay |
| Three pytest module imports | pytest absent | Same overlay; execute their function tests with pytest |
| v6 malformed-control test | Historical investigation window had expired | Freeze that test branch's clock within the original window |
| S1 no-timeout synthetic graph | Historical dispatch paths refer to original checkout | Copy dispatch into disposable fixture and route its three consumed paths through the existing logical-file seam |

The S1 fixture retains original digests and strict byte/hash validation, rebinding
its copied dispatch record. Production source, authority and deadline validators
and immutable historical evidence were not edited. Existing failing tests exercise
the regression seams. No debug instrumentation was added.

The overlay leaves shared experiment environments intact and preserves the base
NumPy, Pillow and packaging versions. The successful CPython 3.14 Linux resolution
is hash-pinned in `environments/locks/cpu-validation-py314-linux.txt`. See
[CPU validation instructions](../../../../experiments/cpu-validation.md).

## Verification

- Original focused reproduction: six unittest errors in 11.832 seconds.
- Corrected reproduction: three unittest cases passed in 38.132 seconds; the three
  pytest modules imported successfully. They contain function tests, so separately
  **22 pytest tests passed** in 2.09 seconds.
- Whole-suite capture: **1,350 unittest cases**, 22 skips, 880.870 seconds elapsed,
  no timeout. None of the six original errors recurred. This capture has 37 errors
  and 34 failure entries caused by a new launcher mistake: the configured disposable
  output directory was not created. The earlier 1,353 count included three failed
  pytest imports; those are no longer counted as unittest cases.
- Astra confirmed the launcher cause with a 0.001-second missing-directory/existing-
  directory probe. 69 entries contain FileNotFoundError; two cascade from the missing
  earlier fixture record. These entries represent **65 distinct test methods**.
- A corrected replay precreated a fresh output directory, collected the same full
  suite and selected those 65 methods in discovery order. **All 65 passed** in
  196.070 seconds, with no timeout. Remaining original whole-suite cases had already
  passed or skipped. Successful writes and both immutable captures were preserved.
- Independent review found no issues with the two fixture changes. `git diff --check`
  passed; no `[DEBUG-...]` instrumentation remains.

Verification covers the suite through the full capture plus targeted recovery.
A passing single whole-suite invocation or current-source qualification receipt
is not claimed. No GPU run, model setup or shared-ledger mutation was performed.

## Integration

Apply this correction commit after `f0aa3391`, or merge the current
`plan069-review-downstream` branch into `plan069-depth-extension`. The destination
owner performs integration; main remains the final destination. Qualify the merged
source before downstream execution. The #34/#35 actual-render and human-review
gates remain required.
