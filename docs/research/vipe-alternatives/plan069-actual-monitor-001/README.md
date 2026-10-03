# Bounded actual monitoring and acceptance (#34)

The fixed `final-render-actual-control.py` entry performs resource sampling or
actual result acceptance inside an owned process group with a finite deadline.
No callable can substitute native authority. Acceptance receives the remainder
of the phase allocation; resource sampling has a 15 second ceiling. Both retain
root PID identity until cleanup, preserve logs and partial writes, and refuse
uncertain cleanup. Emergency cleanup after expiration remains charged.

`supervise_reserved` consumes the admission module's existing reservation,
records the actual root PID/PGID before publishing its immutable release gate,
and includes monitoring, cleanup, acceptance and supervision publication in the
original monotonic allocation. Failure ends the ledger allocation as failed;
a publication overrun has separate immutable failure evidence. No second
reservation or GPU fallback exists. Worker output remains fresh; control logs
and kernel caches live beside it and remain included in cumulative accounting.

Samples measure cumulative charged artifact/download storage through the
existing budget snapshot and total device use through the existing GPU query.
The pinned numerical pool, additional worker processes and one monitoring
helper count toward the CPU ceiling; CUDA housekeeping OS threads are reported
separately. The parent native runtime reserves one CPU slot for monitoring. GPU processes outside the owned worker group are refused.

The explicit CPU fixture process seam clamps all native authority flags false.
Focused tests cover a hung operation, preservation of partial evidence,
cleanup of a descendant after parent exit, bounded response transport, and
rejection of fixture reservations before process creation, and charged command
mismatch failures before launch. These tests do not
run a native GPU model or create an actual approval or shared ledger event.

Validation: eight focused unittest cases pass; new source files parse as Python.
Combined source review and full qualification belong to the parent milestone.

Review corrections require explicit `cleanup_uncertain` on every terminal
ledger event, preserve helper cleanup uncertainty after worker cleanup, and
reject helper success after cleanup or response transport crosses its deadline.
A final fixed sample after worker cleanup and acceptance checks GPU idleness and
cumulative resource ceilings, including control artifacts, with a 1 MiB reserve
for supervision publication. Failed-only CPU process fixtures cover uncertain
monitor cleanup; a real SIGTERM-ignoring descendant demonstrates cleanup
overrun rejection. No passing actual native receipt is produced by these tests.
