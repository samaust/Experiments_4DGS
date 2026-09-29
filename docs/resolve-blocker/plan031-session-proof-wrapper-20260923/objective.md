# Plan031 session proof wrapper blocker

Calling plan: [`plans/plan_031.md`](../../../plans/plan_031.md), authorized CPU-only work under [`plans/plan_049.md`](../../../plans/plan_049.md).

## Blocker

Diagnostic007 returned exact Main exec session handle `50794`. The wrapper stored it in process memory, then raised `ReferenceError: btoa is not defined` before persisting event000. Main recovered the exact handle, wrote it to diagnostic007 launch state, and sent `ABORT\n` using that same handle; the driver returned exit1 with its expected pre-admission error. No admission, tests, capture, or launch note occurred. Diagnostic007 is retired. No user data or prior attempt artifacts are to be deleted.

## Criteria

- C1: A Main-owned evidence wrapper can persist the exact returned tool session ID before any dependent operation can fail.
- C2: The wrapper's event records preserve the exact tool envelope/output hash without relying on unavailable JS globals.
- C3: An independent reviewer confirms the correction is sufficient for the existing Plan049 session-proof contract without changing runner, capture, deadlines, assertions, resource bounds, or authorization.
- C4: A fresh attempt008 preflight verifies current source/authority hashes, storage cap, process and thread ownership/capacity, output vacancy, and high-water index before any launch.

## Safeguards

CPU-only. No prompts access. Do not reuse diagnostic007's identity request or admit it. No driver admission or signal by self-reported PID. Retain all Plan049 behavioral deadlines, caps and scope. Main owns runtime execution and evidence. Use one active subagent at a time. No operational time ceiling. No deleting historical evidence. No source implementation changes are planned unless review proves they are necessary and separately validated.
