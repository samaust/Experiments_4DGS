# V13 fixed Decimal acceleration qualification

The Decimal80 candidate passed **all six costs and all 36 selected partials**
against the common saved v12 exact oracle under the unchanged tolerances.
[Decision](basketball-shared-timing-v13/decision.json) is
`qualified_on_six_retained_states`; package integrity passed. This is an
acceleration-kernel result, not timing acceptance or full evaluator qualification.
SC-01 and SC-03 remain not met, and the main objective remains unattained.

## Scope and arithmetic

[Plan 020](../../plans/plan_020.md) fixes groups 2/9/11, their original rays and
exponents 4/44, six exact 432-byte states, 22 original knot values and 150 saved
quadrature values. [Admission](basketball-shared-timing-v13/admission.json) checks
all 23 pinned v12 files, exact A/B oracle agreement including normalized signed
summands and totals, complete predecessor/source maps, support separation and
retained positive depths. [Minimal worker inputs](basketball-shared-timing-v13/inputs.json)
contain no oracle, rounded basis, old gradient or observations. Those remain in
the separately bound [oracle/admission manifest](basketball-shared-timing-v13/oracle.json).

The independent [candidate](../../scripts/basketball_acceleration_decimal_v13.py)
uses one fixed Decimal context: precision 80, ROUND_HALF_EVEN, Emin/Emax
−999999/+999999, capitals 1, clamp 0. InvalidOperation, DivisionByZero, Overflow,
Underflow and FloatOperation trap; Inexact/Rounded flags are retained. Exact
`Decimal.from_float` decodes original binary64 operands. Setup builds the two
control-difference factors and linear interpolation spans. Each bundle performs
the frozen sample/axis order and transpose accumulation, retaining all 150 signed
contributions per selected partial, Decimal strings/tuples and one binary64 export
per final scalar. No precision adaptation, snapping, alternative reference or
floating evaluator replay occurred. Eighty digits is an engineering choice,
not a proved error bound.

[Comparisons](basketball-shared-timing-v13/comparisons.json) use exact rational
forward error against the saved oracle and binary64 tolerance computed by a
separate multiplication then addition: `1e-10 + rtol*abs(v)`, with cost rtol
1e-9 and gradient rtol 1e-8. All 42 pass; near-zero tolerance was not relaxed.
The six partials are full-objective partials only because original observation
support makes their data/depth derivatives zero. Other 48 gradient components,
Hessian, constraints, transforms and full KKT remain unvalidated.

## Execution and validation

| Allocation | Consumption |
| --- | --- |
| Scientific invocation / setup / bundles | 1 / 1 / 6, all returned; no retries |
| Costs / selected partials | 6 / 36 finite, 42 comparisons passed |
| Fixed 12-case toy suites | 2/2 invocations; both passed all 12 |
| Supervised numerical wall time, including startup/imports/I/O | 0.122488987 seconds of 120 |
| Setup measured inside worker | 0.001455298 seconds |
| Bundle 0 / 1 / 2 seconds | 0.002914436 / 0.002897412 / 0.002951468 |
| Bundle 3 / 4 / 5 seconds | 0.002976786 / 0.004633326 / 0.003742061 |
| Phase elapsed at numerical end | 473.767418269 seconds of 1800 |
| New references, full residual/depth/Jacobian, Hessian, finite differences, solver/ray/screen entries | 0 |
| Training/rendering/GPU/network/download/install | 0 |

The setup/bundle subintervals include their documented entry/serialization work;
they do not sum to total supervised time. Total includes supervisor, process
startup, imports, repeated byte-hash checks and all worker I/O. This tiny workload
is not solver throughput evidence. Resolved interpreter is `/usr/bin/python3.14`
through `.local/envs/calibration-global/bin/python`; Decimal 1.70/libmpdec 2.5.1.
[Execution sources](basketball-shared-timing-v13/execution-sources.json) bind both
scripts, tests, interpreter, loaded standard-library files and Decimal extension.
No NumPy/SciPy or historical scientific evaluator was imported.

[Test source](../../tests/test_basketball_acceleration_candidate_v13.py) was frozen
before suite 1. [Suite 1](basketball-shared-timing-v13/toy-suite-01.log) and
[suite 2](basketball-shared-timing-v13/toy-suite-02.log) use the same exact twelve
fixtures. Between suites only harness ownership hardening changed: ordered
entries, source-bound records, immutable result collision checks and actual child
PGID/SID capture. Arithmetic and tests did not change. Both slots are consumed.
[Readiness](basketball-shared-timing-v13/readiness.json) binds the final source.
No arithmetic, ledger or supervisor change followed readiness or science.

The owning [supervisor](../../scripts/basketball_acceleration_candidate_v13.py)
durably wrote started/allocation records before launch and entry records before
calculation. Worker PID/PGID/SID were 3/3/3 in namespace `pid:[4026533042]`, not
host PID claims. [Process ownership](basketball-shared-timing-v13/processes.json)
and [budget](basketball-shared-timing-v13/budget.json) establish normal exit code
0, reaping and deadline compliance. No worker or job remains. Toy sleeping children
exercised timeout/interruption retention and process-group termination.

[Package checks](basketball-shared-timing-v13/package-validation.json) and
[supplementary retained-data checks](basketball-shared-timing-v13/retained-integrity.json)
validate source hashes, exact entry order/counts, deadlines, context metadata,
Decimal/byte serialization and retained comparisons, without replaying candidate
arithmetic or summing Decimal contributions. Admission source was snapshotted
before harness completion; it is preserved separately. No historical file changed.

## Preserved conclusions and next action

[V12](basketball-shared-timing-v12.md) retains 25/36 primary and 17/36 independent
gradient failures, both archived costs passing 6/6. The
[original v11 failures](basketball-shared-timing-v13/original-v11-failures.json)
are byte-identical; other 57 failed states remain unadjudicated and v11 A2/A3
remain failed. Accepted timing, production candidate and final-validation protocol
remain null; full-screen readiness and main-objective attainment remain false.

The mandatory [source integration and timing-gate map](basketball-shared-timing-v13-integration.md)
identifies all callback, returned-state, Hessian, constraint, transform and independent
verification surfaces. Next Review should select one finite full-component
integration/evaluator-qualification experiment on retained actual v10/v11 operating
states, including a weight-zero control stratum, and next Plan must freeze its
states, scope, independent checks and budget. This advances the still-failed
applicable evaluator-integrity gate. Acceleration cannot affect weight-zero cold
failures, and no integration/solver execution is authorized by this result.

Historical Plan 016/018/019 allocations remain consumed and unchanged. Training
remains 22523.417254 charged seconds of 24 hours with unchanged 7200-second
method/scene ceilings. This plan charged zero training seconds. Commands and their
outcomes are retained in [commands](basketball-shared-timing-v13/commands.json).
Reproduction requires a fresh planned allocation and immutable namespace; do not
remove consumed markers or rerun these commands in this namespace.

## Plan acceptance and checkpoint

A1 passed exact admission and provenance. A2 passed fixed readiness and complete
owned execution. A3 passed all retained exact comparisons. A4 passed package/source/
budget checks and published the required source-only integration report; local
commits and final phase time are recorded in the
[implementation handoff](../continuous-improvement/20260908-plan016/iteration-004-implementation.md)
and [validation handoff](../continuous-improvement/20260908-plan016/iteration-004-validation.md).
Plan acceptance, six-state qualification and main-objective attainment are distinct.
