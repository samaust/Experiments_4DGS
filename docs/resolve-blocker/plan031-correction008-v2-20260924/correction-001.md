# Correction001 — close independent review001 findings

## Evidence and affected criteria

Independent exact-source review001 (`independent-source-review-001.md`, SHA-256 `b59d051820ee162744283a1bce5d32f90f86e0990746f429db98550ba3afce93`) returns NEEDS_CORRECTION for P4/C4/C5. It confirms P2/P3 source structure only, but identifies missing synthetic controls for original tool-result versus checked-copy mismatch, failed/ambiguous/duplicate `ADMIT` send and outer terminal, and overlapping target/readback H accounting. It also identifies import-time process-wide `sys.set_int_max_str_digits(20000)` as an uncontained side effect. Live C1–C3 and B1–B4 remain later independent gates.

## Bounded correction

Keep the exact Plan054/adopted amendment authority, nine-path scope, method/callback/suite counts, original assertions, deadlines, order, error precedence, selectors and resource caps. Correct only within the already modified authorized paths:

1. Remove or contain the interpreter-wide digit-limit mutation while retaining native positive integer handles through 16,384 decimal digits and rejecting wider handles. Add a focused noninterference check showing unrelated default JSON numeric conversion is unchanged outside any necessary bounded operation. Do not change the handle contract or rely on a changed global interpreter setting.
2. Extend the existing `ReceiptContractTests.test_execution_mutations` only, with clearly synthetic controls that distinguish an exact original nested result from a divergent checked copy, and reject missing/ambiguous/duplicate send or outer-terminal evidence. These controls must not be described as live Main/tool attestation; the live comparison still uses the original visible tool transcript and checked file copy.
3. Add an existing-method synthetic transition case for target H plus a serial readback H overlap (`H=2`), successful retirement back to target-only H (`H=1`), and terminal retirement to `H=0`, verifying `B+max(1,H)≤8` at each transition. Keep Main's actual outer-session evidence obligation explicit.

Focused validation: rerun the existing synthetic mutation test and applicable safe static checks; confirm collection remains 78 sources/249 methods/1,028 callbacks/nine suites; independently refresh all nine path hashes. If supporting the 16,384-digit native value without a global side effect cannot be done within current source/path/member limits, stop with a concrete design blocker rather than weakening the value bound or adding a path/member. No Plan049 workload, diagnostic, admission, aggregate, process/pidfd operation, staging or commit is part of this correction.

## Allocation and recheck

Use the existing `gpt-6-sol` high-effort implementer for one focused correction, no nested delegation. A different existing `gpt-6-sol` high-effort validator must independently recheck the final exact bytes and these findings. No operational or token ceiling exists; unmeasured resource use remains unknown. The validator's review001 and the implementation report remain immutable history.
