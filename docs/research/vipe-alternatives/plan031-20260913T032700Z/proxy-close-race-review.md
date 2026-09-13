Proxy close race review, 2026-09-13 05:47 UTC

E1's base-package command failed because the local proxy attempted
`client.shutdown(SHUT_WR)` after the client endpoint had disconnected. Linux
returned `ENOTCONN` (errno 107). The uncaught exception stopped the proxy thread
and closed its listener; UV subsequently reported a refused CONNECT connection.
The exact traceback is retained in the [worker failure record](../../../../.local/vipe-alternatives/plan031-20260913T032700Z/jobs/E1-setup/failure.json)
and [job log](../../../../.local/vipe-alternatives/plan031-20260913T032700Z/jobs/E1-setup.log).
The [command receipt](../../../../.local/vipe-alternatives/plan031-20260913T032700Z/jobs/E1-setup/commands/01-base.json)
records 183.56227130698971 seconds and zero automatic retries; its
[UV log](../../../../.local/vipe-alternatives/plan031-20260913T032700Z/jobs/E1-setup/commands/01-base.log)
records the subsequent refusal. This evidence identifies a local socket
lifecycle defect. It does not establish an upstream access or permission denial.

[The proxy fix](../../../../scripts/vipe_benchmark/transfer_proxy.py) handles only
`ENOTCONN` during a drained half-close triggered by opposite-direction EOF.
It marks that endpoint's read and write directions closed and retires the tunnel
when both queues have drained. Already received response bytes remain queued
for delivery. Selector notifications for directions already marked closed are
ignored, preventing another send or receive on stale readiness information.

The adjacent send/receive audit preserves failure propagation: other shutdown
errors, unconfirmed send failures, upstream receive failures, permission errors,
and accounting failures still abort the proxy. There is no connection retry,
fallback, or broad `OSError` suppression. The close handling does not alter
received counters or pending read reservations.

Validation used only disposable CPU fixtures and localhost sockets:

- `.local/envs/stg-colmap/bin/python -m unittest discover -s tests -p test_vipe_benchmark_transfer_proxy.py -v`
  passed all **21 tests** in 0.306 seconds, including eight new tests.
- Deterministic fixtures inject errno 107 at each drained shutdown direction.
  A localhost integration fixture injects E1's client-shutdown error and then
  completes a second tunnel through the same listener, with exact received-byte
  accounting, zero remaining reservation, and zero retries.
- Other fixtures verify buffered-response preservation, stale-event handling,
  propagation of `EACCES`, `EPERM`, `ENETUNREACH`, `ECONNRESET`, `EBADF`, and
  `EPIPE` where applicable, and retained reservations after receive failures.
- `git diff --check -- scripts/vipe_benchmark/transfer_proxy.py tests/test_vipe_benchmark_transfer_proxy.py`
  passed.

Validated source SHA-256 values:

| File | SHA-256 |
| --- | --- |
| `scripts/vipe_benchmark/transfer_proxy.py` | `b7b1ef3556b5cfcff3fe6976e734c2abb9a29aeed7fe856bee70126642be59fc` |
| `tests/test_vipe_benchmark_transfer_proxy.py` | `7530c5046244b4ce9d677079edf4ef8c7039b4042a6686283f244d51fe810be4` |

This bounded repair supports Plan 031's P31-2 engineering and P31-5 accounting
requirements. No download, build, or model job was executed for this review,
and no existing run artifact or ledger was modified. E1 remains failed with its
one allocated attempt consumed; it cannot be rerun. Real qualification of the
revised proxy remains to be established within untouched E2–E7 allocations.
