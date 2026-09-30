# Fresh S1 calibration attempt — scope REVIEW only

## Completed correction

Recovery008 failed because Torch's import-time direct TemporaryDirectory
constructor bypassed ownership tracking. Correction a34f325e narrowly admits the
exact pinned instantiator constructor into the existing supervised ownership
lifecycle. Retained-source provenance, cleanup, deadlines and ordinary checks
remain strict. Independent Standards and Spec reviews found zero findings;
19 focused CPU tests passed.

Qualification012 passed313 tests/1035 subtests in253.036 seconds under600 seconds.
Validation SHA256 f40a359edb7731d6d94317b73ab09791ff3cca557fe5a67125c83477e87e376d
binds the complete corrected source inventory. Full integration has six known
unrelated errors/five skips, preserved in source-owner-fullsuite-003/.

## Requested allocation

Exactly one **S1-calibration-recovery-009** attempt, maximum **3600 seconds**, to
generate and accept all510 calibration rows. No reconstruction or automatic
further attempt is included. Root alone owns the single GPU.

Preserve source/model/input/precision/threshold contracts, two-second resource
sample deadline,256KiB row metadata limit,22GiB device cap, eight CPU workers,
60GiB downloads,150GiB artifacts and original cumulative ceilings:
93600 GPU seconds,57600 setup seconds and57600 CPU seconds. Final rendering and
training require separate concrete proposals if not already allocated.

## Preserved state and remaining gates

Recovery008 failed after36.640664215025026 seconds, zero qualified rows; finish558
SHA256 518054576325370a9bbfb13ab662f1e0d116a9990cf1a1edc30e6fe83b038514.
Cleanup confirmed, no survivors, stop_required=false and terminal receipt
published. Preserve all earlier failures, including recovery007's unaccepted510
rows and historical stop/absent terminal receipt. Neither is retroactively accepted.
The earlier one-attempt approval is consumed; this proposal is not DO authority.

Latest recorded ledger has573 events, head
1c4a11d7b2d40c8db890330d648e44d2f5e2a677043358272bc5c14f9c72eddc.
Consumed GPU6730.367168940893 seconds; setup6055.783853152872 seconds; CPU
13792.196516173037 seconds plus separately recorded preparation charges. The
requested maximum fits original ceilings; authoritative totals and resources
must be checked again live before admission.

Recovery009 controls and DO are not yet prepared. After explicit approval,
implement identity-specific controls binding consumed008 and prior histories;
independently review and qualify their complete current source. Bind approval,
current passing qualification and exact ledger prefix in immutable REVIEW/DO.
Recheck ownership, cleanup, active allocations, assets, downloads/storage/device
caps and cumulative budgets immediately before dispatch. Any failed gate stops
dispatch. No identity has been registered, reserved or dispatched by this proposal.
