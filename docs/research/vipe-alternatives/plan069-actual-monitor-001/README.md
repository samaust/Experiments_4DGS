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
Concurrent worker processes are counted separately from diagnostic OS thread
counts: the native runtime and result contract independently enforce their
numeric worker limit. GPU processes outside the owned worker group are refused.

The explicit CPU fixture process seam clamps all native authority flags false.
Focused tests cover a hung operation, preservation of partial evidence,
cleanup of a descendant after parent exit, bounded response transport, and
rejection of fixture reservations before process creation. These tests do not
run a native GPU model or create an actual approval or shared ledger event.

Validation: five focused unittest cases pass; new source files parse as Python.
Combined source review and full qualification belong to the parent milestone.
