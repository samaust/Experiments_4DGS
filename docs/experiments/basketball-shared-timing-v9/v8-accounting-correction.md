# V8 accounting correction supplement

V8 remains a rejected experiment. Its files and earlier verification reports are unchanged.
This supplement corrects the scope of their accounting claims; it does not qualify timing.

The v8 adapter exported physical-state keys, but its v6 inner cache keyed dimensionless
original coordinates. Objective requests used `q_roundtrip = ((P @ y) * scale) / scale`;
Hessian requests used `q_direct = P @ y`. The offset scaling is 25. Floating-point
round trips can change exact q bytes even when both q values map to identical physical bytes.

An observation-only derivative sequence added **two inner cache states and one exported
state**, without any optimization. All **22 affected historical attempts** have saved
callback witnesses: **474 pairs** with distinct q bytes and identical physical bytes.
The largest recorded q difference is `2.7755575615628914e-17`. These are exact identity
mismatches, not a justification to merge approximately equal parameters.

The exception owner is `basketball_shared_solver_v6.ConstrainedProblem.evaluate`, whose
counter reached 200. V8 exported 171–193 states for those attempts. Its saved records do
not contain the complete inner cache keys, request ordering, rejected states, or initialization
and constraint-only entry ledgers. **Exact historical all-entry totals remain unknown.**
Neither a cap breach nor a passing repaired conditioning screen follows from this discrepancy.

The earlier verifier checked `nfev == len(state_ledger) <= 200` and at most 200 callbacks.
It did not observe the inner numerical-entry arguments or reconcile initialization and
constraint-only states. This was the verifier's blind spot.

Two separate coordinate-contract deviations also exist. Plan 013 prescribed
`q = q_cold + P y` with symmetric coefficient block `V diag(t) V.T`; v8 used zero origin
and coefficient block `V diag(t)`. Both retain full coordinates, but comparisons must label
the contract repair independently of accounting. V9 tests the symmetric transform, cold
origin, identity nuisance block, exact derivative chain rules and unchanged original-q
stationarity gate. It does not attribute baseline changes solely to conditioning.

V9 assigns exact canonical bytes and a mathematical-problem identity before every numerical
entry. Objective, gradient, Hessian, constraints, cold construction, sanitation/support trials,
callbacks and returned states share one local ledger. Source-support probes have explicit
source-problem scopes in that ledger. Adjacent doubles remain distinct. Subordinate caches
have no independent stopping counter. Actual residual/depth/Hessian entry arguments are
observed and reconciled separately. A 201st state is rejected before entry; the 200-iteration
limit is also unchanged.

These properties passed observation-only and unit regressions. The first scientific baseline
lost its detailed ledgers during serialization, so their scientific-run verification remains
incomplete. No historical or baseline scientific solve was replayed to replace missing evidence.

Evidence: [affected attempts](prepare-resumed/affected-attempts.json),
[callback witnesses](account/counter-correction.json.gz),
[accounting regressions](account/accounting-regressions.json), and
[terminal report](../basketball-shared-timing-v9.md).
