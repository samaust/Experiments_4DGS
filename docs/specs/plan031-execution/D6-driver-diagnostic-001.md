# Proposed D6 driver-only syscall diagnostic

Status: REVIEW; a separate explicit user DO is required. The failed driver001
qualification remains consumed and is not reopened.

Allocate one new `plan069-D6-driver-diagnostic-001` GPU job: 60 seconds including
the stock 30-second cleanup reserve, 2 GiB device memory and 16 MiB total output
including its separate syscall trace. Zero downloads, model or weight loading,
scientific inference, benchmarks or GPU tensor allocation. Global caps remain
unchanged. This is a conservative ceiling, not a measured runtime estimate.

The exact accepted D6 runtime and the unchanged producer network filter are
bound to the failed, cleanup-confirmed driver001 predecessor. Verify the retained
installed dependency closure before importing Torch2.6.0+cu124; initialize only
its CUDA driver. Stock supervision proves owned-process/GPU cleanup and enforces
the fresh one-use checked ledger allocation. A captured CUDA error is a valid
diagnostic result, not a passing model qualification.

Trace socket-family creation, Unix/Internet endpoints and ioctl returns under
the unchanged filter with the installed `/usr/bin/strace`. Send/receive and ioctl
arguments are raw pointers, avoiding payload or ioctl-buffer capture. Do not dump
environment variables. Tracing these operations can identify a relevant denied
socket operation; if the cause lies in an untraced OS operation, report that
limitation rather than inventing causation. No Unix policy relaxation is included.

## Required gates

- Exact new REVIEW and separate matching DO; one approved diagnostic attempt.
- Fresh independent source review covering the three new diagnostic files and
  current common helpers, plus a passing CPU delta with matching source records.
- Accepted setup, retained installed dependency manifest, exact strace/interpreter
  bytes and exact failed/clean predecessor finish in the actual hash-chained ledger.
- No active reservation or GPU owner; remaining global time/disk/download bounds.
- Fresh worker output and sibling trace path; preserve any partial evidence.

`Ledger.note` cannot mint authority. Checked authorization verifies the failed
predecessor, distinct one-use identity and live resources; reservation checks fresh
authority and exact trace command. Retry approval cannot create another diagnostic
attempt or reopen the original qualification. A ptrace/host denial must be reported
under AGENTS.md; do not substitute an untraced GPU run.

## Request and execution

Create an immutable `plan069-D6-driver-diagnostic-request/v1` JSON after approval
with `record_kind=actual` and these file records: `review`, `authorization`,
`source_review`, `cpu_validation`, `setup`, `predecessor_finish`, `dependencies`
(the retained failed-driver installed-dependencies.json), `worker`, `guard`,
`strace`, and resolved interpreter `executable`. Also bind `interpreter_invocation`
to accepted setup.python_executable, `ledger_path`, fresh `output`, and `command`.
The worker is `scripts/basketball_vipe_depth_driver_diagnostic_worker.py`; the guard
is the unchanged `moge-driver-method-004/producer.py`. `validate_request` defines
the exact strace command; its trace path is `output.with_suffix('.syscalls.log')`.

Execute only after all gates and approval:

```bash
python3 -B <canonical>/docs/research/vipe-alternatives/plan031-execution/moge-driver-304-diagnosis/prepare_request.py \
  --root <canonical> --run <shared-run> --authorization <new-diagnostic-DO.json> \
  --source-review <fresh-passed-source-review.json> --cpu-validation <passing-delta.json> \
  --worker-output <fresh-shared-run-output> --output <immutable-approved-diagnostic-request.json>
<bootstrap-interpreter> -B <canonical>/scripts/basketball_vipe_depth_driver_diagnostic.py \
  --request <immutable-approved-diagnostic-request.json>
```

Root must meter CPU preparation and retain the supervised finish, result and
`trace-record.json`. Inspect the trace's denied syscall/family/endpoint and compare
it with the captured initialization outcome. A network-policy correction and a
new qualification attempt require separate review and approval after diagnosis.

## CPU validation

Four public request/ledger fixture cases passed in 0.336 seconds. They cover
new DO, exact clean failed predecessor, checked transition, one-use allocation,
original consumed slot preservation, altered command, substituted dependency
manifest and dangling trace symlink rejection. Mypy passed
all three new modules and the immutable request builder. No actual GPU, model,
tracer dispatch or shared ledger was used. Standards PASS and Spec PASS; no
remaining findings. Review corrections bind the predecessor-owned full dependency
manifest and accepted inventory and reject dangling trace symlinks. The immutable
builder grants no authorization. Fresh canonical source review and CPU delta
remain required before requesting new actual diagnostic approval.
The combined scoped driver, admission, review, setup and video selector suite
passed 54 cases in 1.942 seconds.
