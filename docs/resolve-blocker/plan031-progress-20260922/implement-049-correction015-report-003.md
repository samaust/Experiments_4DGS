# Correction015 S15-1 cleanup correction — static handoff

Addressed the independent S15-1 finding in tests/test_vipe_benchmark_s1_helper_fixtures.py only. This is a narrow follow-up to report002; the other five Correction015 source paths are unchanged. No test, project import/execution, probe, session, launch, staging or commit occurred. Independent exact-source re-review remains required; launch readiness is not claimed.

An outer try/finally now begins before owned acquisition and covers resource observation, evidence assembly/persistence and every original assertion. The existing fixture_cleanup runs after leaving production clock/fault patches on every exit from this block. No extra production retirement attempt was introduced. Cleanup completion is recorded only after actual return; cleanup errors cannot overwrite an already-pending primary.

A bounded in-memory handoff is attached to the enclosing test before acquisition (at most14 cases). It retains original exception objects, owner/temporary objects, strongly retained iterator objects, resource generations, every operation, selected-resource attempts and any owners present before fixture retirement. An escaping acquisition/observation/persistence/assertion error and subsequent cleanup error are retained in chronological order. If a primary already exists, that exact object is re-raised with the later error recorded as secondary and cause; genuine persistence failure always fails validation. The same handoff is attached to the raised primary if durable evidence is unavailable. Failed/uncertain production retirement is not retried through owner.cleanup, and the unchanged fixture cleanup is not presented as successful until it returns.

All original fault targets, selected/all-resource semantics, expected-one assertions, primary/secondary assertions, declarations and timer expressions remain. The exact S15-1 before/after diff and AST audit show that only the existing backend_retirement_transition_controls function changed. Every other current78-member source record and the driver match manifest002. Full baseline015-to-current diff/source snapshots are also refreshed for complete independent review.

Static syntax, scoped diff checks, all-source ordered assertion preservation and original timer-expression multiplicity checks passed. Counts remain78 source members,622 top-level test-class methods,249 collected methods and1028 typed callbacks with exact declarations/order. No assertion or timer exception was added. S15-1-specific AST inspection establishes that acquisition, persistence and assertions are inside the cleanup-guaranteeing outer try.

The prior F1/F10 timing and F7/F8 runtime hypotheses remain unresolved and unchanged; this repair removes the identified static cleanup gap, not those runtime acceptance requirements. Correction015 report002 remains historical. Use report003, source-after003, after-ast003 and manifest003 as the current combined handoff. No other plan scope was expanded.

Current helper-fixture SHA256: `52596b820bff2344f66c02139f7898a50aa12a33ce1608f488a590e455671379`.
S15-1 audit SHA256: `c76e5d7d6080df168cfae58a4cb9dcbc49485571740b2c6ca351d514922be725`.

Elapsed baseline015-to-handoff wall time: 1665.479847s; baseline UTC 2026-09-23T20:09:51.133287+00:00 / monotonic 87552.776379987; handoff UTC 2026-09-23T20:37:36.613130+00:00 / monotonic 89218.256226655. The separately saved s15-1-start003 records this follow-up's own start. Earlier overhead and CPU remain unknown; no operational ceiling.
