# Proposed D6 method005: exact socket creation only

Status: REVIEW, CPU implementation only. Method004 and its actual failed
qualification/diagnostic evidence remain unchanged. No GPU attempt is authorized
by this directory or by standing bug-fix retry approval.

## Actual evidence and remaining uncertainty

The completed, cleanup-confirmed driver diagnostic captured CUDA error304 and
two denied calls at trace lines26052/26155:

```text
socket(AF_UNIX, SOCK_SEQPACKET|SOCK_CLOEXEC, 0) = -1 EPERM
```

Exact result, finish, trace and guard records are retained in `evidence.json`.
This establishes an OS call denied by the guard during initialization. It does
not establish that allowing it alone fixes CUDA initialization; later connection
or transfer requirements may remain blocked. No CUDA initialization was performed
by this preparation.

## Narrow proposed rule

`network_guard.py` allows only native `socket(1, 524293, 0)` creation: AF_UNIX,
SOCK_SEQPACKET with SOCK_CLOEXEC, protocol0. Each differing argument has a deny
rule; those rules form OR, not a conjunction that could admit partial matches.
All other socket creation remains denied, including IPv4, IPv6, Unix stream and
datagram sockets, missing CLOEXEC, extra NONBLOCK and nonzero protocol.
Socketpair, connect, bind, listen, accept/accept4, all send/receive message syscalls
and io_uring remain unconditionally denied. Existing Python audit guards remain
unchanged. There is no broad Unix exception or additional local endpoint access.

The newly created socket is unconnected. The retained connection/binding/accept
and socketpair denials prevent it acquiring a peer through those operations;
sendmsg/recvmsg denials retain descriptor-transfer restrictions. Ordinary file
read/write remain unchanged; writing this unconnected socket fails ENOTCONN.
This is an incremental creation exception, not a new claim about inherited
connected descriptors or arbitrary host IPC. Existing launcher descriptor and
guard controls remain required. If the runtime needs communication after this
creation, this proposal cannot satisfy it: preserve the failure and request
separate evidence/review rather than broadening permission.

Libseccomp defines argument comparison operators and combines rules as a union.
The code uses SCMP_CMP_NE=1 from its primary header.
[libseccomp API](https://man7.org/linux/man-pages/man3/seccomp_rule_add.3.html),
[libseccomp header](https://github.com/seccomp/libseccomp/blob/main/include/seccomp.h.in).

## CPU verification

The fixture failed on method004's actual guard with EPERM at the observed creation
call. The proposed guard also hit the known independent sandbox Unix creation
restriction; one scoped outside-sandbox retry passed in 0.000363804 seconds.
A second meaningful fixture check including retained Python auditing and native
io_uring denials passed in 0.016706101 seconds. Both runs attempted no external
connection, model loading or CUDA calls. Native negative fixtures use invalid
addresses/buffers so an accidentally allowed operation cannot connect to a peer.

```bash
python3 -B docs/research/vipe-alternatives/plan031-execution/moge-driver-method-005/test_guard.py \
  --guard docs/research/vipe-alternatives/plan031-execution/moge-driver-method-005/network_guard.py \
  --audit-guard <canonical>/docs/research/vipe-alternatives/plan031-execution/moge-driver-method-004/producer.py
```

The fixtures cover seven denied creation variants, eleven native connection and
transfer operations, socketpair, io_uring, retained Python connection auditing
and unconnected write failure. Mypy passed both modules. Diagnostic-only raw
Unix allow prototypes from the earlier investigation are not used here.

## Proposed next qualification

`review.json` proposes a distinct `plan069-D6-driver-qualification-002`, max1,
180 seconds including explicit30 cleanup, device2GiB/output64MiB/zero downloads,
driver-aware imports and exactly two strict actual CPU weight loads. Native map
attempt limits and global caps remain unchanged. No GPU model or inference or
benchmark is requested. This REVIEW is not a DO or a checked ledger allocation.

Before requesting approval, integrate a separately reviewed producer/checked
allocation using this guard, preserve scientific/runtime pins, refresh exact
source and CPU qualification, and regenerate canonical proposal bindings.
The CPU fixture source paths are immutable preparation evidence, not a command
to run a model from this worktree. A fresh explicit user approval and live state
checks are required for the new max1 job. The consumed original qualification
and completed diagnostic are never reopened.

## Independent review

Standards PASS and Spec PASS; no actionable findings. Both reviewers verified
the five physical evidence bindings, both trace lines and the unchanged remaining
native deny list. No review probes, GPU, model or connection operations occurred.
