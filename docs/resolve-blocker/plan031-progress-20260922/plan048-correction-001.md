# Plan048 correction 001 — failure reconciliation after the total deadline

## Finding

The preserved `ReservationClockTests.test_failure_reconciliation` callback `kind='late'` fixes `time.monotonic()` at `clock.total_deadline + 1` with a 90-second reduced reservation and asserts that `preserve_failure` writes `failure-evidence.json` and `first-result-qualification.json` containing elapsed time91. `ReservationClock` defines `total_deadline = monotonic_start + effective_seconds`; for that case, 91 is strictly after the total deadline. The existing production branch writes multiple files at/after that point. Plan048 §3 requires metadata diagnostics to stay within the original cleanup allowance, which ends at the total deadline. These requirements cannot both be satisfied without changing this callback's late-case acceptance.

## Narrow correction to Plan048

For only `kind='late'` in this existing callback, change the expectation to require `preserve_failure` to retain the original exception in memory, perform no file open/read/hash/write or receipt publication after the total deadline, and return no new failure record. Confirm the output directory contains only the pre-existing `config.json`; retain the exact original exception class/text and mark unavailable evidence in memory. Keep `reconcile_first` rejected before any filesystem access when invoked after the same deadline. Preserve the callback identifier and all other original callback cases, method names, assertions, source identities, earlier failure artifacts and all other assertion expressions unchanged. The sole old assertion expression no longer applicable to this late subcase is the literal `assertEqual(value['elapsed_seconds_from_reservation'], 91)`; retain its historical form in the pre-edit baseline and record the one authorized after-map difference. Do not produce fictitious or backdated diagnostic records.

This correction advances B1 by enforcing the original hard total cutoff and avoids replacing the primary with a post-cutoff write. It does not relax the limit, cleanup reserve, production failure handling before the cutoff or scientific acceptance. The original test remains as a collected callback and is strengthened with no-post-C filesystem tripwires and preserved-primary checks. No Plan047 historical acceptance changes.

## Authorization and validation

This is within the user's explicit ≤7,200-second CPU-only blocker-resolution allocation and changes no GPU/model/production scope. The existing focused/aggregate slot ceilings and independent validator still apply. No test or execution slot is added. Implementer may apply only this exact callback correction after Main records this addendum; the independent validator must inspect the changed callback's named boundary and evidence. Main retains commit and final-acceptance ownership. All other Plan048 requirements remain unchanged.

Status: approved by Main as the minimal internally necessary correction after source and clock invariant inspection. No implementation of this disputed boundary is accepted until independent validation.
