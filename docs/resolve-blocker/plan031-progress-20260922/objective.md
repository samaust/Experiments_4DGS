# Resolve blocker: complete bounded S1 progress

Calling task: continue the implementation of [plan_031.md](../../../plans/plan_031.md), currently blocked by the incomplete Plan047 S1 progress implementation.

## Blocker evidence

Plan047 is closed and incomplete. Its three focused invocations and two aggregate invocations are exhausted; both aggregates timed out at 300 seconds without a passing receipt. The latest review and assessment are [Review018](../../continuous-improvement/plan031-s1-recovery-20260919/review-018.md) and [assessment044](../../continuous-improvement/plan031-s1-recovery-20260919/assessment-044-review.json). They identify repeated NPZ decoding and synthetic fixture setup as a plausible runtime cause, plus correctness and scenario-coverage gaps. Do not reuse Plan047 attempts or claim its historical strict acceptance.

## Resolution criteria

- **B1 — Progress authority and deadline correctness:** preserve the original S1 progress contract, including fresh per-operation deadline checks, immutable authoritative row versions, independently retained acknowledged progress, strict parsing and recovery. Validate affected boundaries and regression cases.
- **B2 — Failure-path evidence:** the required P01–P06 scenarios reach their named real supervisor boundaries and preserve original primary/secondary failures, timing, pointer and cleanup evidence; distinguish Plan047 historical gaps from current evidence.
- **B3 — Runtime integration:** the unchanged complete current-source aggregate passes within its 300-second outer timeout, with exact current source membership, all existing methods/callbacks/scenarios/scripts, zero failures/errors/skips/discovery errors, and actual successful outer completion.
- **B4 — Preservation and scope:** preserve frozen plans, old failures, raw ledger, previous partial sources and historical acceptance outcomes; do not run GPU/model/scientific/production work or exceed the parent plan's applicable ceilings.

The main plan objective remains incomplete until S1-1 through S1-4 and all applicable plan_031 experiment and reporting gates are verified. This resolver addresses only the current CPU progress blocker and does not authorize production admission or calibration.

## Constraints and allocations

Follow repository AGENTS.md. Never read `prompts`. The user explicitly requested the gpt-6-luna orchestrator and explicitly prohibited the continuous-improvement-loop and gpt-5-6-luna-orchestrator workflows; use only the gpt-6 orchestrator and this blocker companion. Main owns status, jobs, integration and commits. Use one Astra agent at a time, no nested delegation, and require a distinct independent validator. Plan047's allocations are closed. Any fresh work must first be justified against the parent plan's remaining resource ceilings and receive a new decision-complete plan; historical attempts and elapsed time do not transfer.

## Current state

Review018 already contains a fresh read-only diagnosis and a proposed remedy/allocation. The resolver Review must verify that evidence, inspect whether cumulative parent resource use can be reconciled, and recommend a concrete next step. No implementation, test, benchmark, GPU/device, model, production API, or ledger operation has been launched in this resolver run.
