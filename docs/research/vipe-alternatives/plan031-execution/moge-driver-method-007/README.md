# D6 guard007 — CUDA initialization fixed

This version preserves method006 and allows `listen` after the same pre-import
descriptor check. The actual guarded `torch.cuda.init()` now passes with D6's
PyTorch 2.6.0+cu124 environment. Qualification004 remains at REVIEW: the diagnostic
loaded no model weights and does not establish full model readiness.

## Evidence

Qualification003 finish842 is failed, cleanup confirmed, no surviving owned PID.
Its trace shows the abstract UNIX `bind` succeeding and the next `listen(16,128)`
returning EPERM. CUDA initialization still returned error304. The earlier MPS
`connect` denial was also present; that trace alone did not isolate the cause.
Guard007's fresh trace shows that bind and listen both succeed while the MPS
connection remains denied. Initialization passed in 1.51 seconds (1.77 seconds
including supervision), with cleanup confirmed and no surviving owned process.
The existing idle MPS service was left running; it had no clients before or after.
See [the preserved diagnostic evidence](../depth-D6-guard007-cuda-outcome-001.json).

The proposal binds the immutable003 finish and trace alongside001/002/diagnostic
ancestry. Failed attempts are preserved and cannot be reused or reset.

## Permission and trust boundary

The only allowed socket creation remains AF_UNIX/domain1, type524293, protocol0.
Before filter installation the fresh process must have one thread, no numerical
imports, and zero socket descriptors; its descriptor identities must remain
unchanged across installation. Signal masking covers this interval. `socketpair`,
`connect`, `accept`, `accept4`, explicit send/receive message operations,
`pidfd_getfd` and io_uring remain denied. Duplicating an owned descriptor does not
create an INET socket. Under this boundary an owned listening socket has UNIX
provenance, and accepting a peer or obtaining its descriptor is still denied.

This relies on the reviewed launcher, libseccomp native ABI filtering, trusted
CUDA libraries, and the bound strace supervisor. Hostile external ptrace or
seccomp notification descriptor injection is outside this boundary. It is not a
complete sandbox against arbitrary malicious native code. The guard does not
restrict UNIX names or listen backlog. Kernel connection queuing can occur even
though accept is denied. Selected traces omit close/dup and cannot establish a
complete descriptor history. No claim of zero network-related side effects or
of pointer/FD inspection is made.

[Kernel seccomp documentation](https://docs.kernel.org/userspace-api/seccomp_filter.html)
explains scalar-argument filtering, ABI checks, and external descriptor injection.
[listen(2)](https://man7.org/linux/man-pages/man2/listen.2.html) describes passive
socket/backlog behavior. These support the assumptions; they do not validate CUDA.

## Contract and integration gates

The REVIEW004 proposal is not execution ready. Versioned v4 worker, public
request/result authority and dispatcher implement job
`plan069-D6-driver-qualification-004`. The protected ledger validates exact
consumed003 grant/reservation/failed finish and its trace through the unchanged
v3 checker, preserving all earlier ancestry. The result requires the new
`unix_listen_allowed` startup proof and exact listen exception. Historical006
worker and v3 authority remain unchanged. Fixture approvals grant no actual authority.

Limits stay: one attempt,180 seconds including30 cleanup,2GiB device,64MiB owned
artifacts, zero downloads, two strict CPU weight loads; no inference, benchmarks,
GPU model load, setup or native map qualification. Review current source closure,
CPU qualification and fresh live slot/global resource checks before obtaining a
new exact v4 DO. This proposal grants no new attempt.

Changed proposed source closure now contains007/network_guard.py and007/startup.py.
The v4 worker, authority, dispatcher and protected ledger/admission changes
join the exact reviewed CPU/source closure. Earlier source receipts remain
historical; future execution requires qualification of the integrated sources.
