# Qualification timeout amendment 001

## Authorization and scope

The user authorized: “Increasing the qualification timeout to a reasonable
value.” This prospectively increases the bounded aggregate CPU qualification
capture default and maximum from 240 to **600 seconds**. The execution receipt
validator uses the same shared limit. Diagnostic captures retain their
120-second maximum; the diagnostic CLI default now respects that maximum.
The separately authorized no-timeout mode retains its existing requirements.

The corrected full discovery took 340.484 seconds. That is a different test
selection from canonical qualification and provides sizing evidence, not proof
that canonical qualification will pass. The new limit gives practical headroom
while retaining a finite stop and process cleanup. A passing complete receipt
remains required before any model/setup dispatch.

## Preservation and next capture

Captures 005 and 006 remain immutable failed attempts. This amendment does not
turn a timeout into success, suppress tests, resolve the six existing full-suite
errors, or consume another GPU attempt. Qualification 007 is the fresh output
identity for the authorized CPU rerun with `--timeout 600`.

Focused validation passed three tests: a synthetic 300-second completed receipt
with a 600-second cap is accepted, a 601-second cap is rejected, the capture
passes and records the 600-second default, and diagnostic excess is rejected
before creating output. Synthetic receipts never establish actual qualification.

Historical 240-second receipts remain structurally valid when their other
source/provenance requirements hold. Current-source matching still prevents old
receipts from qualifying changed code.
