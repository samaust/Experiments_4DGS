# Iteration 002 implementation — Plan 018

The Plan 018 diagnostic implementation and its one allowed scientific pass are
finished. Overall diagnostic verification **failed**; this is not objective
attainment. The complete outcome is retained in
[the v11 report](../../experiments/basketball-shared-timing-v11.md),
[decision](../../experiments/basketball-shared-timing-v11/decision.json),
[verification](../../experiments/basketball-shared-timing-v11/verification.json), and
[component failures](../../experiments/basketball-shared-timing-v11/verification-failures.json).

Read [objective](objective.md), [Plan 018](../../../plans/plan_018.md),
[resume assessment](iteration-002-assessment-03-resume.md), [recommendations](iteration-002-recommendations.md),
and [authorization](iteration-002-plan018-authorization.json) before execution.
Current AGENTS.md standing approval explicitly covers Plan 018; historical
awaiting-approval artifacts were preserved. Parent owns status and criteria assessments.
No subagent was spawned by this implementation stage.

## Implemented and retained

- Standard-library admission verified twelve v10 records, 48 exact selected
  callbacks, returned-state bytes, all multipliers, problem identities, complete
  journal chains, receipts, policies and source identities. Inputs are immutable.
- Constructor-free primary reconstruction uses the saved physical coefficient
  bytes. It evaluates depth before objective and records original and transformed
  KKT using saved actual multipliers. No initialization, optimization, Hessian,
  support/SVD reconstruction, triangulation or numerical finite differences ran.
- Twenty-four fixed metric displacement rays and their exact bytes were frozen
  before the fixed 23-amplitude probes and analytical limits.
- Separate scalar-coefficient spline arithmetic independently reconstructed all
  states and limits. A supervisor enforced a single worker, process-group cleanup,
  single-thread libraries, fixed slots and a hard numerical deadline.
- The CLI rejects existing output admission, consumed runs and direct worker
  invocation without its supervisor/atomic claim. Final sources froze at readiness;
  the earlier admission-source hash is retained separately.

## Results and plan acceptance

| Acceptance | Outcome | Evidence |
| --- | --- | --- |
| A1 | met | 12 admitted cases, 48 snapshot slots, 24 exact independently matching rays; all physical identities match. |
| A2 | failed | All scheduled measurements exist, but 63 probe gradient comparisons fail. Missing arithmetic confidence is not relabeled as mathematical uncertainty. |
| A3 | failed | Journal/identity/count audits pass; 63 of 600 finite-slot checks fail inherited componentwise gradient tolerances. All 24 analytical-limit checks pass. |
| A4 | met for the retained failed diagnostic | Historical gates remain unchanged, report provides per-case interpretation and a concrete next investigation, toy/package checks pass, local milestone committed. This does not imply A2/A3 success. |

Every saved snapshot agrees with its applicable archived objective, depth,
solver-coordinate KKT and matching returned forces/multipliers. All 48 paired
snapshots verify. All twelve weight-zero displacement rays are eventually depth
infeasible; none establishes a feasible competitive escape. The controls have
nine eventually infeasible rays and three with divergent acceleration cost.
The 24 limit classifications agree independently. These results neither prove a
finite minimizer nor exclude other directions or establish timing identifiability.

The 63 failures occur on three regularized rays, at every even amplitude exponent
4 through 44. They involve 367 gradient components in coefficient rows 0 and 1.
All other compared fields, identities and classifications pass. The largest
component error/tolerance ratio is 2,036,763.2. Numerical cancellation in equivalent
acceleration-gradient expressions is a hypothesis from retained evidence and
source inspection, not a newly verified explanation. No tolerance changed and
no scientific rerun or post-run arithmetic correction was made.

## Exact consumption and chronology

| Milestone | Recorded UTC | Elapsed from original T0 |
| --- | --- | ---: |
| Original phase start | 2026-09-08T08:13:03.607105+00:00 | 0 s |
| Input admission | 2026-09-08T08:16:53.966138+00:00 | 230.359033 s |
| Final execution source/readiness freeze | 2026-09-08T08:29:05.738409+00:00 | 962.131304 s |
| Numerical start | 2026-09-08T08:29:05.740374+00:00 | 962.133269 s |
| Numerical completion | 2026-09-08T08:29:13.585597+00:00 | 969.978492 s |
| This handoff written after implementation commit | 2026-09-08T08:37:14.833729+00:00 | 1451.226624 s |

Admission, readiness and numerical work completed before their fixed deadlines.
The phase remains governed by the original 2026-09-08T08:43:03.607105+00:00
commit/handoff deadline. No clock reset occurred. Parent records final stage-close
elapsed time after the handoff commit, rather than rewriting immutable budget evidence.

The single numerical pass used 7.84522387 of 120 seconds.
Each pass completed all 624 owned slots (600 finite-state slots and 24 limits),
with 600 depth and 166 residual/gradient entries. Of each pass's 552 probe slots,
118 were feasible and 434 skipped objective evaluation after failing depth.
There were zero degenerate, nonfinite, entry-error or interrupted outcomes here.
Combined totals: 1,200 depth entries, 332 residual/gradient entries, 48 limits.
All optimizer/GPU/training/rendering/download/install/Hessian/finite-difference
counts are zero. The one pass is consumed; unused wall time and skipped residual
capacity do not permit additional execution. Historical allocations and the
24-hour training ledger were not touched.

## Validation, commits and handoff

[Validation](iteration-002-validation.md) records the focused tests and artifact checks.
The implementation/evidence/resume checkpoint is `b6422ad4084dcc1438db3f5e4e35c28ca79f41c7`.
Staging and committing used separate escalated commands and an inspected staged
diff, with only explicit task paths. No push, amend or history rewrite occurred.
The two handoff files are a subsequent local documentation checkpoint; its ID is
reported to the orchestrator after commit.

The scientific supervisor tool session 70939 exited with status zero. The worker
was waited/reaped and `worker_stopped=true`; no stage commands or jobs remain.
PID 2 (supervisor) and PID/PGID 3 were sandbox namespace values, never host kill
targets. No sandbox/permission or git failure occurred.

Recommend a fresh Review/Plan to isolate the regularized acceleration-gradient
arithmetic disagreement at the six already saved states (three failed rays ×
amplitudes 1e4 and 1e44). Proposed allocation: 20-minute implementation/validation/
commit phase including 60 numerical seconds, one single-thread worker plus
supervisor, six fixed states per implementation, at most 12 residual/gradient and
12 depth entries, zero fresh rays/limits/optimizers/GPU/training. Add a hand-authored
cancellation regression and preserve inherited tolerances. This follow-on has not
been launched and cannot use the spent Plan 018 pass.

SC-01 and SC-03 remain not met. No fresh model/reload claim changes SC-02/04's
historical evidence. SC-05 gains reproducible bounded evidence of a failed diagnostic,
not a claim of passed scientific arithmetic. All Plan 015 scientific gates remain;
accepted timing, production candidate and final-validation protocol remain null,
and `ready_for_full_screens=false`. The overall loop may continue to authorized
Review/Plan; this plan's used allocation is not a whole-loop exhaustion.
