# S1 aggregate result capacity correction — independent review

## Exact failure and relevant correction

S1-010 consumed one immutable standing-authority allocation and qualified510
rows. The35,338,620-byte aggregate and1,726,556 parser nodes exceeded progress
metadata limits. Local acceptance passed, then progress publication failed;
the finish is failed, stopped, with absent accepted result and terminal receipt.
Cleanup is confirmed and no GPU compute processes remain. Outcome69f7884d and
its diagnosis preserve this history; no intermediate artifact is promoted.

Isolated correction6ded12a3658a38f7f3a825b5f2aca57f737ca911 is integrated as
273d80a1. All affected result publication, decoding, candidate inventory and
closure recheck paths now share finite aggregate bounds derived from510 rows
at256KiB plus the32MiB envelope allowance, with corresponding finite node
accounting. Independent row256KiB/65,536-node and envelope32MiB/1,048,576-node
limits are enforced. Accepted results still require exactly510 rows. Forensic
candidate count2048, no-follow/identity/hash/deadline/control/checkpoint guards
remain enforced. Inventory accounting has an explicit finite derived ceiling.

## Standards review

Independent pinned audit b1b43c58..6ded12a3658a38f7f3a825b5f2aca57f737ca911:
zero documented violations and zero new optional smells. Read-only inspection;
no GPU, native imports, tests or edits by the reviewer.

## Spec review

Independent pinned audit of the same range: zero remaining blocking findings.
The audit identified and resolved aggregate node capacity and forensic-candidate
compatibility before integration. It verified shared bounds, independent row/
envelope limits, exact accepted count and preservation of failed010 history.
Read-only inspection; no GPU or live writes by the reviewer.

## Focused validation

Three new public aggregate regressions and the existing closed-inventory/fault
method passed in7.143 seconds. Existing capacity endpoints passed in15.588
seconds. Regressions use a real510-row aggregate above35MiB and the former node
limit, exercise publication/cold recovery/inventory/recheck, and reject hash
mutations, finite-bound overflow and row/envelope byte/node overflow. The actual
failed010 result decoded read-only in1.835 seconds; it remains unaccepted.

The new test module is required in the13-suite qualification and104-source
inventory. Full root integration015 ran1185 tests in574.005 seconds (outer575.685),
within600 seconds, with no failures, six known unrelated errors and five skips.
This is not a passing whole-repository claim. Required current qualification016 passed342 tests/1063 subtests in
475.427413 seconds within600 seconds, zero failures/errors/skips. Strict inner
receipt, host execution record and wrapper passed with matching current104-source
inventories. Wrapper SHA256 ce21a33039649f2cf6c1727fd8278e756512418699c6af22cbaa52d1cceaba21.
These final receipts support preparation of the reviewed fresh011. No new
GPU, setup, download, depth or final-render allocation occurred during review.
