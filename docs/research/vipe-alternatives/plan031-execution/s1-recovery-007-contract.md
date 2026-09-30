# S1 calibration recovery 007 contract

The approved fresh-runtime-attempts-proposal-001 permits exactly one new S1
calibration identity, after the serial E5-003 attempt, with root alone using the
GPU. Recovery 007 has a 3,600-second ceiling within the unchanged cumulative
budget, with no reconstruction, reset, redispatch or additional calibration.

The REVIEW builder CLI now selects 007. The Python builder accepts explicit
`job_id='S1-calibration-recovery-007'`; historical 005/006 proposals still support
immutable CPU fixtures and reject consumed live identities. Generate REVIEW only
after other ledger work finishes, using current source qualification and review.

The proposal preserves the consumed 001–006 authorization chain and binds the
exact 006 failed finish at sequence 535, hash
`ca7f1cc0fbdeb0b065b5bc059b6f9901dd41ada81d1a7172aba819c7fe82f915`,
its immutable 536-event outcome snapshot, and its actual terminal receipt.
The first qualified row remains partial evidence: the 006 attempt failed runtime
qualification and is not a complete 510-row calibration.

Keep process-file amendment 002 and its pinned 001 predecessor unchanged. Keep the
frozen scientific request, source pins, role, precision, 510 rows, 256 KiB row
metadata limit and two-second sampler bounded by any earlier caller deadline.

DO changes only the approval flag, authorization text, REVIEW context to DO,
and adds the exact REVIEW record. Admission rejects any other changes. REVIEW
cannot allocate, duplicate registration cannot allocate again, and only the 007
lifecycle can follow its captured live prefix. Dispatch the authorization-only
controller route, omitting the historical optional `--job` selector.
