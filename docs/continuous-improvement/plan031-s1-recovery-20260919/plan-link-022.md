# Iteration022 plan — Plan061

[Plan061](../../../plans/plan_061.md) is the user-authorized scope amendment recorded in [pi-launch-authorization.md](pi-launch/pi-launch-authorization.md): the user directed that the owned tests **work when launched by pi**, removing the requirement of a Codex PTY launch for the acceptance path. It is planned from the [iteration-21 stop](assessment-053-implement.json) (decision point C, now superseded by direct user authorization).

Measured basis: the Codex-specific block is the Plan049 authority chain that `owned_workload` re-verifies on every owned call — `no_timeout_launch` requires the dispatch file, fixed `plan_049.md` digests, the Main admission, and the `plan049-session-proof/v2` record of verbatim Codex `exec_command`/`write_stdin` PTY tool events (structurally impossible under pi; synthesizing it is forbidden). The capture's no-timeout entry and `validate_creation`/`validate_execution` carry the same binding, and the run layout is hard-bound to the Plan049 directory and `-049-` naming.

Plan: an **additive** `pi-launch` provenance class — new note schema `plan061-pi-launch/v1`, new pi driver (outside the source set, so the 78-member source set is unchanged), schema dispatch in `no_timeout_launch`/`validate_execution`/`validate_creation`, and both-layout support in `_launch_anchor`/`owned_workload`. Every launch-method-independent guarantee (live census, owned closure, per-thread identities, note digest vs kernel anchor, layout/fd identity, ancestry liveness to pid 0, `B+max(1,H)≤8`) is preserved verbatim; the Plan049 chain stays byte-identical and remains the authority for `plan049-prospective-launch/v1` notes. **No test code changes** — the 14 owned tests already branch on the environment.

Acceptance: one no-timeout whole-suite aggregate launched by pi's bash tool, expected 249 ok / 0 errors / 78-of-78 sources unchanged (no cap applies; prior timeout-mode measurements estimated ~365 s wall). At most 3 aggregate attempts, wall budget 7200 s, zero GPU/model/production work. Pi receipts carry `provenance='pi-launch'` and are never presented as Plan049 session-bound evidence.

Environment record: this harness launches the driver directly (no PTY handoff, no job ledger, no bootstrap/ADMIT); S1-2's separate later GPU authorization is unaffected.

No tests or source edits occurred in PLAN. S1-1 narrowly met; S1-2 pending the acceptance run; S1-3 unmet; S1-4 met.
