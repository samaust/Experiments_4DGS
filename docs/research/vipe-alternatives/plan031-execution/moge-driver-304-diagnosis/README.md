# D6 driver001 error304: static and CPU diagnosis

## Preserved outcome

Root reports the consumed driver001 GPU slot failed after 11.664995492 seconds,
with cleanup confirmed (ledger finish750), peak device bytes926941184, no model
load and no inference. The preserved log is
`.local/vipe-alternatives/plan031-20260913T032700Z/prepare/plan069-D6-driver-qualification-001.log`.
Its traceback ends at `producer.py:236`, `torch.cuda.init()`, with
`cudaGetDeviceCount` error304. Installed dependency/license manifests were
already written; do not delete, overwrite or reinterpret them as a passing
qualification. This diagnosis did not inspect or mutate the shared ledger.

NVIDIA documents error304 only as a failed OS call; it does not identify the
syscall or cause. [CUDA Runtime API](https://docs.nvidia.com/cuda/archive/12.9.0/cuda-runtime-api/group__CUDART__TYPES.html).

## Feedback-loop limitation and hypotheses

The original CUDA failure cannot be reproduced within this CPU-only assignment:
the explicit one-attempt GPU allocation is consumed. Accordingly, no CUDA root
cause or verified CUDA fix is claimed. CPU fixtures exercise the actual guard
function, giving a precise signal for socket denial only.

Ranked falsifiable hypotheses sent to root before probes:

1. The blanket seccomp socket policy denies required local driver IPC. If causal,
   an independently approved Unix IPC correction would remove the error; the CPU
   prediction is that the current guard rejects Unix socket operations.
2. Another denied syscall or OS operation causes the failure. A socket-policy
   change alone would leave error304.
3. A separate driver/runtime/host condition causes it. The error would persist
   without the guard under a separately approved diagnostic.

## Findings

The producer installs its filter before imports and `torch.cuda.init()`. Its
unconditional deny list covers `socket`, `socketpair`, `connect`, `bind`, `listen`,
`accept`, send/receive socket syscalls and io_uring. It does not distinguish
AF_UNIX from Internet families. The Python audit layer separately prohibits
Python socket operations except construction. The successful native D5 map
worker path has no equivalent native seccomp filter; this is a meaningful
control difference, not proof of causation.

The CPU probe loads only the retained producer's Python definitions, never Torch,
CUDA or a model. The actual old guard rejected AF_UNIX/AF_INET/AF_INET6 creation
and Unix socketpair with EPERM in 0.000320867 seconds. A diagnostic family filter
allowed Unix creation and pair exchange, rejected IPv4/IPv6 creation with EPERM,
and retained io_uring denial in 0.000313706 seconds. No external connection was
attempted. Commands:

```bash
python3 -B docs/research/vipe-alternatives/plan031-execution/moge-driver-304-diagnosis/probe.py \
  --producer '<canonical>/docs/research/vipe-alternatives/plan031-execution/moge-driver-method-004/producer.py' --mode old
python3 -B docs/research/vipe-alternatives/plan031-execution/moge-driver-304-diagnosis/probe.py \
  --producer '<canonical>/docs/research/vipe-alternatives/plan031-execution/moge-driver-method-004/producer.py' --mode unix-prototype
```

The prototype initially failed inside the sandbox. A baseline confirmed that
`socket(AF_UNIX)` itself is denied there, while socketpair and Internet socket
creation are allowed. One scoped outside-sandbox retry then passed. This host
restriction is distinct from the production filter; the old socketpair denial
remains attributable to its guard because baseline socketpair succeeded. The
prototype is explicitly diagnostic and never changed a production filter.
Libseccomp's argument comparisons support family-specific rules; its header
defines SCMP_CMP_NE=1. [libseccomp API](https://man7.org/linux/man-pages/man3/seccomp_rule_add.3.html),
[primary header](https://github.com/seccomp/libseccomp/blob/main/include/seccomp.h.in).

## Confidence and required next evidence

High confidence: the current native guard rejects local Unix IPC. Moderate
confidence: this is a plausible explanation for an OS-call initialization error.
Unproven: that CUDA actually attempted one of those syscalls, or that permitting
Unix sockets resolves error304. No claim is made that the host driver is broken.

Do not promote the prototype to production: allowing arbitrary Unix sockets can
reach local proxies or receive existing Internet descriptors, so denying new
Internet sockets alone does not establish the existing no-external-network
contract. The Python audit policy would also need a consistent narrow design.
Keep production unchanged until a newly reviewed, approved bounded diagnostic
identifies the actual denied syscall (and required local IPC endpoint, if any).
The next GPU diagnostic must retain no model/inference/benchmark execution and
explicitly account for its new attempt, time, device and cleanup bounds. Any
subsequent qualification retry needs a separately reviewed proposal/approval;
standing bug-fix retry approval cannot revive driver001's consumed max1 slot.

## Independent review

Standards PASS and Spec PASS; no actionable findings. Reviewers performed no
probes, model imports, GPU commands or network operations. Mypy passed the
diagnostic module with `--check-untyped-defs --follow-imports=skip
--ignore-missing-imports` after explicit module-spec/loader checks were added.
