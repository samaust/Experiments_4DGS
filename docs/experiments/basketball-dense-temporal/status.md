# Plan 026 final execution state

The fixed study has stopped with all available sparse-arm work complete.
**The full study is incomplete:** the dense initialization prerequisite failed,
so three of nine planned trajectories and the dense comparisons remain blocked.
The continuous-improvement loop is inactive. No study job remains running.

Specification: [plan 026](../../../plans/plan_026.md).
Results and limitations: [final report](report.md).
Browse outputs: [artifacts](artifacts.md).
Research and implementation ancestry: [shared code provenance](../basketball-code-provenance.md).

- All six historical 5,000-update parents were verified and preserved.
- All six sparse trajectories reached 50,000, totaling 270,000 new updates.
- All 30 available curve results contain exactly 350 targets and finite metrics.
- All 24 new curve snapshots pass all 13 fresh-process PNG/raw-float probes.
- Both endpoint bundles contain 48 comparison PNGs and 12 videos at 25 fps.
- All 49 recorded GPU segments completed successfully; peak concurrency was one.
- Both dense pilots executed successfully but failed scientific acceptance.
  No dense production initializer was frozen or trained.

[Final independent audit](final-validation.json),
[training audit](resources-final/trajectories.json),
[render validation](curve-render-validation.json),
[visual validation](visual-validation.json), and
[implementation validation](implementation-validation.md) retain the evidence.
Exact state restoration is verified; bitwise GPU training reproducibility is
not established. The failed comparisons remain recorded.

Validated local milestones: preflight `8657f61`, pilot/adapters `94a498f`,
evaluation pipeline `f55805d`, first endpoint `9f098ec`, both seed-0 endpoints
`2400649`, STG seed 1 `739c134`, FreeTimeGS seed 1 `1f5e764`, STG seed 2
`8737232`, all six endpoints `53f1c4c`, and endpoint visual validation `8e6fa3e`.
Earlier partial analyses and audits remain historical evidence; final conclusions
use `analysis-final/` and `resources-final/`.

The stop reason is the failed dense prerequisite after completing all remaining
authorized work. Further dense recipe variants or synchronization changes are
outside this plan. Local machine handoff state is retained in
`.local/basketball-dense-temporal/run-state.json`.
