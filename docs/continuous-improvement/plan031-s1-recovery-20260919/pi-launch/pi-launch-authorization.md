# Pi-launch authorization (record)

**Date (UTC):** 2026-09-26
**Session:** pi harness, branch `qwen38`
**Authorizing party:** repository user (direct instruction in-session)

## Verbatim request

> I want to change the tests so they don't need to be launched from Codex.
> I want them to work when launched by pi.

## Decision semantics

1. The owned no-timeout acceptance path may be launched by pi (this harness's `bash` tool) via a dedicated pi driver, in addition to the preserved Plan049 Codex-PTY path.
2. The provenance class for pi-launched receipts is **pi-launch** (`plan061-pi-launch/v1` notes, `provenance='pi-launch'`), distinct from and never substitutable for Plan049 `session-bound/v2` session-proof evidence.
3. All launch-method-independent guarantees are preserved verbatim: live process census, owned closure from the launch root, per-thread identity verification, note digest vs kernel launch anchor, layout/file-descriptor identity, ancestry liveness to pid 0, and the `B+max(1,H)≤8` CPU bound.
4. The Codex-session-specific chain (dispatch, Main admission, `plan049-session-proof/v2` verbatim tool events) is replaced — for pi-launch notes only — by the pi authority chain (driver + authorization + plan file records, all live file-verified) plus the live ancestry walk.
5. No owned-path assertion is weakened, no timeout/cap/suite/fixture/gate is shrunk, no evidence is synthesized, and no prior failure/aggregate/report/allocation is rewritten or rerun.
6. Scope: `plans/plan_061.md` (iteration 22). Acceptance = one no-timeout whole-suite aggregate launched by pi at 0 errors / 249 ok / 78-of-78 sources unchanged, or a recorded stop after at most 3 aggregate attempts.

## Downstream effect on prior decision points

- Plan060 decision point **C** (Plan049 owned-environment strict acceptance in a Codex PTY environment) is superseded for the acceptance path by the pi-launch path; the Plan049 procedure remains documented and preserved for Codex-environment use.
- Decision points **A** (timeout-mode 300 s scope amendment), **B** (extra timeout-mode measurement), and **D** (later GPU authorization for S1-2/S1-3) are unaffected. Note the pi-launch path is no-timeout by construction, so the 300 s timeout-mode cap does not gate it.
