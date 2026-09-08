# Local dynamic reconstruction workflow

## User objective

Establish a reproducible local workflow for reconstructing dynamic scenes from
multi-view images into complete, saved 4D Gaussian models that can be reloaded
and rendered from different viewpoints over time. Evaluate the candidate methods
on reconstruction quality, motion fidelity, rendering speed, and resource cost,
and use the measured evidence to identify the most suitable workflow within the
approved budgets.

The user explicitly started this loop from the implementation results of
[Plan 016](../../../plans/plan_016.md). Basketball timing is a prerequisite,
not the main objective. Its scientific rejection is not objective attainment.

## Required success criteria

| ID | Observable required outcome | Validation / evidence |
| --- | --- | --- |
| SC-01 | Reproducible preparation and reconstruction procedures for the existing SelfCap and Basketball comparison profiles, with validated inputs and held-out exclusions. | Commands, pinned source/configuration and input manifests; applicable calibration, synchronization, camera/time and split validation records. |
| SC-02 | Successful supported method runs produce complete saved models that reload locally and render multiple times and viewpoints. | Model inventories and hashes, reproducible training/render commands, fresh offline reload comparisons, held-out renders and frozen-time sweeps. Record unavailable methods separately; their blockers are not successful runs. |
| SC-03 | Candidate comparison evaluates reconstruction quality, motion fidelity, speed and resource cost using applicable measured evidence. | Shared per-frame and aggregate metrics, timestamp/image-linked visual and temporal observations, rendering throughput, charged training time, memory and checkpoint measurements. Distinguish incomplete schedules and unsupported comparisons; no invented combined score. |
| SC-04 | A practical workflow recommendation follows from the measured tradeoffs and states its supported profile and limitations. | Traceable comparison and decision report covering the existing candidate set, specific unavailable-method blockers, and runnable instructions for the recommended workflow. A solver improvement or intermediate plan completion alone cannot satisfy this criterion. |
| SC-05 | The workflow and its evidence are reproducible within existing authorized resources and budgets. | Source/configuration provenance, complete retained experiment evidence, validation outcomes, reconciled budget records including failed work, and task-related local commits. |

Criteria are derived from the user objective and existing comparison scope;
no new numeric quality threshold is imposed. Preserve IDs and definitions;
record any user-directed changes here and reassess affected evidence.

## Constraints and authorization

- Follow repository AGENTS.md, including never reading prompts content, local
  commits, sandbox/permission retry and stop rules, and git-failure stops.
- Use the existing candidate set and scene profiles from Plan 004 and later
  authorized revisions. Do not substitute scenes or silently relax scientific
  gates. Record unsupported methods rather than implementing papers anew.
- Preserve Plan 016/v10 and historical evidence. Its 90-minute execution window
  and finite attempt allocations are historical, not reset by this loop.
  New numerical experiments or full-screen continuation need an applicable
  unspent authorization; identify any required budget decision before dispatch.
- Preserve the existing 24-hour training allocation and method/scene limits;
  do not redistribute unused allocations or restart budget-stopped runs without
  new authorization. Other historical phase limits remain applicable to their
  phases. No new overall loop compute budget was supplied.
- Initial review may inspect existing artifacts and identify feasible next work
  and concrete budget needs. Do not treat historical per-plan exclusions as
  permission to abandon the broader objective or as a reset of spent budgets.
- On explicit resume for iteration 002, apply the clarified AGENTS.md budget
  rule: consumed Plan 016 attempts restrict that experiment's execution, not
  subsequent authorized review and planning. Prepare a concrete next plan and
  proposed resource limits before requesting any additional execution budget.
  The user has not renewed or added numerical attempt/time allocations.
- Sequential fresh gpt-6-astra subagents: xhigh review, high planning, medium
  implementation; fork_turns=none; no further delegation. Reread this file and
  the latest assessment before every stage and after context loss.
- Stop and retain evidence under the existing loop rules; resume only on
  explicit user instruction. Do not mark blockers as objective completion.

## Initial evidence

- [Plan 016 implementation](../../experiments/basketball-shared-timing-v10.md)
- [Terminal decision](../../experiments/basketball-shared-timing-v10/package/terminal-decision.json)
- [Contender comparison](../../experiments/contender-summary.md)
- [Repository purpose](../../../README.md)

## Changes

- 2026-09-08: Initial objective and derived criteria saved before stage dispatch.
- 2026-09-08: User explicitly resumed the same objective after AGENTS.md commit
  `fd43f19` clarified budget scope. Objective and criterion definitions unchanged;
  iteration 002 review/planning may proceed without renewing Plan 016 execution.

- 2026-09-08: User explicitly resumed the same objective after standing-approval
  commit `b62f2ea`. The earlier budget-request statements above are historical:
  AGENTS.md now approves Review-recommended, Plan-finalized plan-specific limits,
  explicitly including Plan 018. Overall and method/scene ceilings, historical
  consumption, scientific gates and all criterion definitions remain unchanged.
  Subsequent eligible plans receive the same standing approval.
