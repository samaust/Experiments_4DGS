# Native qualification supervision CPU preparation

Baseline: `23c468e3`. This preparation adds qualification-specific control and
supervision without changing production DO admission, workers or controls.
No GPU, model loading, dependency installation, shared ledger or GitHub writes
were used.

## Interfaces

`final_render_qualification_supervisor.supervise_reserved(ledger, reservation,
command, output, invocation_record, release_path=...)` requires an exact active
reservation whose evidence has schema `plan069-final-render-qualification-reservation-binding/v1`,
role `native-qualification`, actual record kind, authorized execution and
`native_adapter_qualified: false`. Production DO and fixture reservations fail
before process launch. The separate authority module supplies
`validate_dispatch_invocation`, `invocation_binding` and `validate_phase_result`.

The worker receives the immutable qualification release record. Its registered
PID/PGID must be checked by the authority gate. Fixed CPU-masked control helpers
sample resources or accept the retained phase receipt. They cannot use callbacks
or confer production authority. The supervisor checks resources before launch,
during execution and after process-group cleanup. Phase disk accounting includes
outputs, logs and owned Torch, Triton and CUDA caches. Terminal publication has
one second and 1 MiB reserved within phase and global bounds.

A completed finish denotes completion of a bounded compatibility probe only.
Its supervision receipt always retains `native_adapter_qualified: false`.
It does not claim that the probe scope is sufficient for production admission.

## Validation

CPU fake-process boundary: 12 unittest tests passed, including two terminal
publication subcases. Fixtures cover hung processes, surviving descendants,
oversized transport, fixture authority rejection, production DO rejection,
prelaunch foreign GPU observations, uncertain helper cleanup, retained caches,
near-limit disk publication and delayed terminal ledger append. Five Python files
passed syntax parsing. Both independent reviews have no unresolved local findings.

Host Python and the existing stg-colmap interpreter with the documented private
CPU overlay have no mypy installed; no dependency installation was attempted.
The parent must run its combined source validation after integration.

## Required before actual execution

The parent authority module and reviewed worker protocol remain prerequisites.
Acceptance must require exact successful supervision and finish evidence and
reject both `publication-failure.json` and `terminal-publication-failure.json`
from the bound controls directory. A terminal overrun never returns success.
The retained supervision receipt is immutable; a fresh failure marker supersedes
its provisional status.

Ledger finish elapsed is measured immediately before its terminal append; the
receipt states that measurement boundary. An outer supervising capture must
measure and account for terminal publication overhead. This preparation does
not add ledger correction events or authorize actual qualification dispatch.
