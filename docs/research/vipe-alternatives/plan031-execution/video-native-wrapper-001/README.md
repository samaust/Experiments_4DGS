# Accepted D9 recovery002 CPU qualification wrapper

Root owns admission, actual dispatch and final CPU accounting. This milestone
supports accepted D9 recovery002 only. It preserves the existing method003:
exactly two strict CPU model loads, no inference, no GPU and no download.

Before use, integrate these three producers and their fixture test, publish a
fresh passed D9 source review declaring all three producers as supplementals,
and obtain a fresh passing focused CPU capture binding every declared helper,
supplemental and current producer byte. Historical source006/CPU014 alone do
not qualify this new wrapper. No DO or attempt allocation is created here.

The outer wrapper enforces 180 seconds including 20 seconds for descendant
cleanup and guarded terminal assembly. The inner method receives 140 seconds.
Capture artifacts and each observed disk increase are capped at 64 MiB;
existing global disk cap remains210GiB. Seven CPU threads match unchanged
method003. Network syscalls are denied by an inherited libseccomp filter;
Python audit guards remain additional controls. Subreaper adoption and pidfds
track observed descendants, including SIGTERM cancellation. PID reuse is
rejected. Observation cannot prove ownership of short-lived unobserved
processes between100ms polls. SIGKILL cannot execute cleanup; root must retain
its independent host verification.

Both preparation producers have ten-second self deadlines. Named admission
reserves180seconds for capture and20seconds for their combined preparation,
within cumulative D9/global CPU budgets. Immutable event785 is attributed once
through its exact clarification. Preparation and outer execution must each be
metered and charged once by root; child elapsed is a subset of outer elapsed.

## Root commands after final source and CPU qualification

Use the explicit hostpython3 only for preparation. Substitute reviewed fresh
SOURCE and CPU evidence paths, existing matching DO path, and fresh private
output paths. No ledger mutation may intervene from admission through capture:
the protected prefix is rechecked before and after. Preserve and apply measured
preparation charges after capture, within its already reserved20seconds.

```text
python3 -B <canonical>/prepare_admission.py --checkout <root> --run <RUN>
  --output <fresh-admission> --source-review <SOURCE>
  --setup <RUN/jobs/plan069-D9-setup-recovery-002/result.json>
  --cpu-qualification <CPU>

python3 -B <canonical>/prepare_request.py --root <root> --run <RUN>
  --source-review <SOURCE> --cpu-qualification <CPU>
  --cpu-admission <fresh-admission/admission.json> --authorization <DO>
  --output <fresh-request> --wrapper-output <fresh-wrapper-output>
  --capture-output <fresh-capture-output>
```

Request preparation prints the exact explicit native interpreter command.
Root reviews and runs it outside the sandbox under existing task authority.
The wrapper verifies accepted002 protected ancestry, clean current ledger,
exact DO/setup/runtime/source/CPU bindings and fresh named admission. No wrapper
or producer writes the production ledger. Finalization and commercial
qualification remain separate existing method003 phases after actual passing
capture; this milestone does not manufacture qualification evidence.

## Validation

CPU fixtures test accepted ancestry boundary, stale prefix/source/generator
rejection, cumulative budget protection, extra arguments, prompts guards,
pidfd identity ownership/PID reuse and external termination cleanup. Fixtures
use mocked processes and filters; they never load models or install a filter.
All three producers pass scoped mypy check-untyped-defs. Independent standards
and specification reviews found issues that were corrected and rechecked.
Unique measured local validation captures are retained privately and handed to
root for accounting. No actual native capture or shared ledger write occurred.
