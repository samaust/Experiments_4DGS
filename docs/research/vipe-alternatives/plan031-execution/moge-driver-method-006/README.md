# D6 guard006 proposal — REVIEW only

This candidate has no dispatch entry point, DO authorization or fresh attempt
allocation. Guard004/005 and the failed qualification002 remain unchanged.
The approved qualification002 attempt ended with protected finish801, cleanup
confirmed, after 20.271626626 seconds; no CPU weights were loaded.

## Evidence and proposed boundary

The retained qualification002 syscall trace shows the guard005 creation exception
working, then these denials:

- Line26458: connect to `/tmp/nvidia-mps/control` returned EPERM.
- Line26562: bind of the newly created Unix sequence-packet socket to an abstract
  `cuda-uvmfd-*` name returned EPERM.

This proves denied operations during initialization. It does not prove that the
bind denial alone caused CUDA304, or that this proposal makes CUDA initialization
succeed. The MPS connection remains denied.

Guard006 preserves the exact `socket(1, 524293, 0)` creation exception, removes
only the unconditional bind denial, and adds `pidfd_getfd` denial. `recvmmsg`
and `sendmmsg` denials remain explicit alongside the other receive/send calls.
Connect, listen, accept, socketpair and io_uring remain denied.

The Unix bind allowance applies to **any Unix socket name**. Seccomp cannot
inspect the pointed-to sockaddr or restrict the CUDA name. This candidate must
not be described as allowing only that abstract name.

## Startup proof and integration requirements

`startup.install_before_helpers` is a proposed hook for a future producer. Its
exact guard bytes are checked using standard-library operations, then the guard
must be installed **before** importing `depth_admission`, NumPy, BLAS, Torch,
Triton or other native/model helpers. The existing method005 producer is not
modified and must not be used as the integration template without this ordering
correction. Full request/authority validation still precedes any driver action.

The worker must be a fresh exec child with a private descriptor table and one
main thread. During installation, catchable signals are blocked. Own-proc task
and FD enumeration must succeed, every inherited socket fails the proof, and
FD identities are rechecked. No unknown descriptor is closed. Stable inspection
directory descriptors are recognized as non-sockets and omitted from cross-scan
comparison. Disappearance, replacement, changed descriptor sets, multiple threads,
numeric imports or inaccessible own-proc state cause failure before driver use.

The scope is socket API provenance in this trusted startup sequence, not a
general adversarial sandbox or a guarantee against every possible IPC channel.
The proof does not tolerate concurrent untrusted code modifying descriptors.
Linux exec unshares the file descriptor table; the future dispatcher must preserve
the fresh exec launch and pipe/file standard streams. A socket standard stream
also causes failure. Native child syscalls inherit the installed filter.

After installation, new sockets have the approved Unix domain; socket import
through pidfd_getfd, recvmsg/recvmmsg, accept or socketpair is blocked. Thus bind
cannot target an Internet socket acquired through these APIs. Bind alone cannot
establish a sequence-packet peer while connect/listen/accept remain blocked.
There is no actual CUDA or runtime Internet isolation verification in this milestone.

## CPU fixture evidence

`test_guard.py` ran 12 fake-only tests successfully in 0.05287221300386591 seconds
(parent subprocess time). The tests call neither the real installation function
nor actual socket/bind/connect operations. They check policy predicates, startup
ordering, inherited socket rejection, descriptor/thread races, unavailable
inspection state and numeric import rejection. This validates construction and
fail-closed control flow; it does not establish actual kernel enforcement or
CUDA compatibility. The private capture is `.local/guard006-cpu-001`.

## Required next authority

A future qualification003 requires a concrete reviewed producer and checked
one-use authority that binds these bytes, the failed qualification002 and clean
diagnostic ancestry, fresh source and CPU receipts, and a **new explicit GPU DO**.
No attempt duration/allocation is approved here. A native map must also bind the
accepted guard/profile explicitly; passing qualification alone must not change
its existing guard selection.

## Independent review and static checks

Standards: PASS, no actionable findings. Spec: PASS, no actionable findings
within the explicitly trusted startup scope. Both reviews inspected source only;
neither performed runtime operations. Their findings confirmed that concrete
producer/authority integration and actual kernel/CUDA verification remain future
work. Review baseline: task-start `c1a74d51`.

Private mypy reported no issues in the two proposed source modules, taking
0.37166395199892577 seconds. This static check did not import the candidate.

Primary references: [kernel seccomp documentation](https://www.kernel.org/doc/html/latest/userspace-api/seccomp_filter.html),
[pidfd_getfd](https://man7.org/linux/man-pages/man2/pidfd_getfd.2.html), and
[execve](https://man7.org/linux/man-pages/man2/execve.2.html).
