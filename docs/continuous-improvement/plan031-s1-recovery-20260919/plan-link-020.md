# Iteration020 plan — Plan059

[Plan059](../../../plans/plan_059.md) continues Review018 R18-1 from the [Plan058 measured milestone](status.md) (commit `f28d86c`): land F6 R18-1 items 1–2 in source (NPZ single materialization per guard; bounded validation-call-local memoization of deterministic transforms of freshly verified content); land F6 item 3 with F3 callback relevance (all 114 callbacks preserved; every deadline/capacity/alias row reaches its named distinct internal start/completion) and F6 item 4 finite controls inside collected invocations; land F4's five state/provenance/parser/cancellation sub-reworks; re-verify with one focused diagnostic and, if launch inequalities allow, one final whole aggregate, retaining the measured result either way. The plan was created exclusively at the next unused number after058.

- [Review018](review-018.md) and [assessment044](assessment-044-review.json) with [observations018](s1-recovery-review-observations-018.json) remain the fixed review inputs
- [Assessment048](assessment-048-implement.json) binds the completed Plan058 IMPLEMENT handoff; [assessment047](assessment-047-plan.json) and [Plan058](../../../plans/plan_058.md) remain the prior iteration's binding records
- [Authoritative objective](objective.md)

Measured basis:iteration019 whole aggregates (receipts `s1-recovery-aggregate-018-001`/`s1-recovery-aggregate-019-001`) hit the unchanged 300 s cap at 300.0 s with 199 ok, exactly the 14 owned-root errors, 0 failures, 78/78 sources unchanged, killed inside the supervisor suite; the four slow plan047 tests (82.4/35/16/13 s unprofiled) spend their dominant cost in repeated pure qualification work (3741 `qualify_row` calls, ≈110 s, each re-running a 16–17 s `validate_result`) plus broad test-side operation instrumentation — the concrete redundant work R18-F6 names. No timeout, cap, suite, or fixture size is touched.

Fresh allocation:7200 wall seconds,6000 source/test cutoff,1200 handoff reserve;at most4 focused120-second and2 whole-aggregate300-second launches (the first aggregate is the post-change verification aggregate on the updated source); existing42 scenarios and6direct scripts only; B+max(1,H)<=8. Zero GPU/model/probe/production work or old allocation transfer.

Continuation completed by this plan (not new scope):the F3 and F4 reworks recorded as deferred by Plan057/Plan058. After this milestone:Plan049 owned-environment strict acceptance, then S1-2/S1-3 live calibration recovery under separate later GPU authorization.

Environment record:the current harness has no Codex PTY session tools, so the Plan049 owned-root launch (and with it the 14 owned-root cases) is environment-blocked and cannot be produced here; synthesizing session-proof evidence is forbidden. Validation runs under the unchanged timeout-mode capture; the milestone gate covers all non-owned cases and strict zero-error acceptance remains the later owned-environment gate. The owned KeyErrors are reported as environment, not code defect.

No tests or source edits occurred in PLAN. S1-1/S1-4 remain narrowly met; S1-2/S1-3 unmet. Plan047 remains failed/unaccepted.

Plan059 SHA256 `61fbfeb486391fa93895f4e3d5b89487a4d0b14a6565ba6194c89ea7bff4dbd6` (15366 bytes). Assessment048 SHA256 `941b75897256dde53edf068c1aec1fe96e12e162a2f58c75aa45846f03f7f748`. Main owns status/git and records the timing start before implementation dispatch.
