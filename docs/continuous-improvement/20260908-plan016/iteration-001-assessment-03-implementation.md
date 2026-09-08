# Assessment after implementation — stopped for authorization

The orchestrator reread the unchanged [objective](objective.md), inspected
[Plan 017 results](iteration-001-implementation.md),
[validation](iteration-001-validation.md), the
[audit correction](../../experiments/selfcap-evidence-20260908/audit-02.md),
[visual findings](../../experiments/selfcap-evidence-20260908/inspection.md), and
[workflow guide](../../selfcap-workflow.md). Implementation commit:
`aade3fabdda415680ec39213a9de43ee0097db15`.

| Criterion | Status | Reason and applicable evidence |
| --- | --- | --- |
| SC-01 | not met | SelfCap inputs, splits, timestamps and training-only initialization are audited. Basketball still lacks accepted timing and final validated reconstruction inputs, as recorded in the [v10 terminal decision](../../experiments/basketball-shared-timing-v10/package/terminal-decision.json). |
| SC-02 | met | For the four successful supported SelfCap runs, the audit binds complete saved models, historical fresh offline reload records, all 60 held-out times and 20 shared poses to current files. STG establishes PNG equality; FreeTimeGS/ATGS additionally retain historical float-hash equality. No new reload is claimed. Blocked Basketball/unavailable methods are not counted as successes. |
| SC-03 | not met | The supported SelfCap comparison now includes verified recorded metrics/speed/resources and actual ground-truth-linked motion observations. Basketball has no reconstruction measurements, so the existing two-profile comparison remains incomplete. |
| SC-04 | met | The guide supplies a practical profile-qualified recommendation, exact complete-model procedures, all candidate tradeoffs and dated specific blockers. STG Full is a compact completed-schedule default, not a sharp-motion winner; FreeTimeGS is the measured aggregate-quality option. This qualified recommendation does not close SC-01/SC-03. |
| SC-05 | met | The completed supported workflow's provenance, retained evidence, checks and task commits are recorded, and budget charges reconcile without overruns. Historical STG binary attestations remain explicitly unavailable; the criterion does not assert an unrecorded fully attested historical runtime or a new GPU run. |

Plan 017 acceptance A1–A4 is complete. Effective audit: 6,701 passed, two
unavailable historical STG binary attestations, zero failed checks. Ten focused
tests passed; link/asset/sheet-hash and command syntax checks passed. The original
failed checker assumptions remain preserved with a targeted correction.

Parent checks: production auditor SHA-256 matches the supplement
`b0c22e947f46c76207650510981fab62a507400ded3205440cd762156cf04497`;
the training ledger remains
`d0b4daa1aee79361580af3a1bf8fbc597148db7775b26f169a0a1b2e6ac90957`.
Parent also independently viewed reference/Full frame 4150 and the midpoint
face and ending-book sheets; these support the reported blur/detail limitations.
These are spot checks, not a repeated full audit or full-sequence playback.

## Stop decision and explicit resume boundary

The main objective is **not attained**. Useful authorized saved-evidence work
from this iteration is complete. The remaining Basketball synchronization
prerequisite needs a new numerical phase with concrete scope, elapsed-time and
attempt limits. Plan 016's five 81-attempt policies and six preflight allocations
are consumed; its historical clock cannot restart. The separate remaining
training allocations cannot authorize timing experiments. Full screens and
final validation also remain scientifically gated.

Stop under AGENTS.md's missing-authorization/budget rule before spawning another
stage. This is an authorization blocker, not a git failure, permission denial,
or successful objective completion. No active subagent remains; all three
reported no background jobs, and the agent roster confirms completion. No
experiment process was started by the orchestrator, so no interruption was needed.

Resume only on explicit user instruction resolving the next phase's scope and
budget. Begin iteration 002 with a fresh xhigh review after rereading the
objective, latest assessment and user-authorized constraints; then plan and
implement sequentially. Preserve all historical evidence and scientific gates.
