# Basketball shared timing v5: bounded depth barrier pilot

Plan [011](../../plans/plan_011.md) changes only the independent evaluator's depth
inequality representation. Production continues to use immutable v2. The investigation
clock starts at 2026-09-08 00:24:00 UTC, conservatively rounded down before the first
implementation action. The pilot deadline is 00:54 UTC; exact retest deadline 01:54 UTC;
scientific computation ends by 04:04 UTC and packaging by 04:24 UTC.

## Mechanism and scope of the argument

The immutable synthetic generator uses identity camera rotations and translations only
along x. At fixed offsets, adding a common positive z translation to every cubic spline
coefficient translates the entire trajectory by partition of unity. The second derivative
of a constant translation is zero in exact arithmetic, so acceleration is unchanged.
Every depth increases; normalized image coordinates tend to zero and projections tend to
the principal point, including the fixed radial distortion. The original robust data
objective has a finite limit. Thus the original objective F has a finite ray limit while
SciPy's raw-depth barrier F − μ Σ log(d − m) tends to negative infinity for each fixed
μ > 0. The installed implementation and source hash are recorded in baseline.json.

This proves an unbounded raw barrier subproblem in this exact fixture. It does not prove
that the original objective lacks a finite minimum, explain every stalled v4 solve, or
establish a recession direction for the real rig. Finite precision spline multiplication
can produce nonzero acceleration from large constant coefficients. Those probe costs are
reported separately from the exact analytical limit.

## Frozen numerical change

With normalized depth d, m = 1e-8 and s = d − m, v5 supplies g = s/hypot(1,s) ≥ 0.
The transformation scale is fixed at one rig diameter; there is no upper constraint or
added prior. For finite real s, its sign matches s, preserving the feasible set. At
positive slack, −μ log(g) ≥ 0 tends to zero as depth increases. This removes the
unbounded negative barrier reward, but does not eliminate finite-depth bias or guarantee
convergence. Numerical saturation and derivative underflow are recorded explicitly.

The analytic Jacobian is diag(g′) J_s. The full sparse constraint Hessian is
Σ v_i [g′_i H_s_i + g″_i J_s_iᵀ J_s_i], including coefficient–coefficient entries.
Here g′ = hypot(1,s)^−3 and g″ = −3(s/hypot(1,s)) hypot(1,s)^−4. Inverse powers avoid
squaring extreme diagnostic amplitudes. Original-depth multipliers are v_g g′; bound
multipliers remain in dimensionless optimization coordinates. Returned objective,
stationarity, bounds and strict original depth are independently checked. The unchanged
200-iteration limit and separate 200-distinct-objective limit are both enforced.

## Predetermined audit and continuation gates

The pilot manifest binds all 48 group/lag/objective problems: groups 2/9/11, lags
−25, −20, −19, −7, −6, −0.10, 0, 25, weights 1 and 0, with cold, ascending and descending
attempts only. The audit binds uniform positive-z rays from each cold state and every
nonzero saved suspect-block direction in all twelve v3 rejection records, at source and
destination lags, with both signs. Offsets stay fixed. Amplitudes are 10^0, 10^2, …, 10^44.

Exactly unsupported motion is resolved only using compact spline support and the absence
of an acceleration penalty on those historical data-only problems. Its original objective
is attained at every finite ray point; timing cost is unchanged at those fixed offsets.
Source support may activate at another lag, which is why unchanged v4 sanitation replaces
weak source blocks with destination-cold values before transfer. Observable rays require
an analytical feasible limit worse than an available feasible finite state by the existing
objective tolerance. A finite comparison state need not be a certified optimum to establish
that a worse ray limit cannot beat that available value. Infeasible rays are identified by
negative depth slopes. Any unresolved ray blocks continuation. This finite audit is not a
global minimum certificate.

## Result: numerical failure at the fixed pilot gate

The single pilot decision completed 807.96 seconds (13.47 minutes) after the conservative
clock start. **93/144 attempts qualified; 51/144 failed**, all on the data-only objective.
All 72 regularized attempts qualified. The unchanged all-attempts gate therefore stops
continuation. Five of 48 problems also failed three-start objective agreement, nine failed
the no-worse-than-qualified-v4 comparison, and all three required data-only directional
transfers lacked qualifying evidence. The regularized transfers passed. No unexplained
large observable growth was flagged; that finding does not certify global optimality.

| Objective | Group 2 | Group 9 | Group 11 | Total qualified |
| --- | ---: | ---: | ---: | ---: |
| Regularized, weight 1 | 24/24 | 24/24 | 24/24 | 72/72 |
| Data-only, weight 0 | 7/24 | 8/24 | 6/24 | 21/72 |

SciPy reports “maximum number of function evaluations” on the 51 failed returns; the
saved iteration and distinct-objective counts in [resources](basketball-shared-timing-v5/resources.json)
show that every failed return reached 200 iterations with only 192–197 distinct objective
evaluations (median 196). Thus these were iteration-limit stops, not exhaustion of the
independent 200-objective ceiling. The minimum failed original depth was 3.21545 rig
diameters.
No cap, tolerance, solver, transformation scale or scientific prior was changed after
observing these results. The full exact retest, independent control matrix, benchmark,
production fitting, assessment and selection were not executed. Their results, bootstrap
intervals, workload projections, candidate and final-validation protocol remain null.
`accepted_timing` remains null. Selection frames 150–199 were not read by this investigation;
final frames 200–249 remain untouched.

The corrected finite audit resolves 172 rays: 64 exactly unsupported invariant rays,
78 observable rays with limits worse than available feasible finite states, and 30
analytically infeasible rays. It contains 3,956 fixed-amplitude probes. Large-amplitude
regularized probes exhibit finite-precision acceleration effects; their enormous arithmetic
costs do not contradict the exact constant-translation argument. Eight feasible saved-block
rays have not reached their analytical image limit even at 10^44: individual near-knot
samples have extremely small depth slopes. Verification records the finite endpoint gaps
and the analytically derived depth-transition amplitude rather than claiming those finite
probes already equal their limits.

Preparation recomputed the v4 baseline: 1,774/1,836 data-only attempts failed, median
197 distinct objective evaluations, and every failed state had normalized depth above
3.59. V4 optimization was not rerun as a baseline. The required regression suite includes
unit tests of the historical implementations.

Before the first pilot, verification corrected an audit-reference bug: the initial audit
omitted feasible stalled v4 states and falsely flagged 24 directions. Feasible stalled
states provide finite objective comparisons even though they are not certified minima.
All 24 flagged limits were worse than these already-saved feasible values. The initial
records and source-inspection/configuration-hash corrections are preserved in
[corrections](basketball-shared-timing-v5/corrections.json). The same prescribed rays were
reanalyzed before the first and only pilot; no extra optimization starts were introduced.

## Evidence and validation

- [Terminal result](basketball-shared-timing-v5/result.json),
  [pilot decision](basketball-shared-timing-v5/pilot/pilot-decision.json),
  [fixed manifest](basketball-shared-timing-v5/diagnose-final/pilot-manifest.json).
- [Escape decision](basketball-shared-timing-v5/diagnose-final/escape-decision.json),
  [compressed analytical limits and probes](basketball-shared-timing-v5/diagnose-final/escape-audit.json.gz).
- [Separate sparse directional costs](basketball-shared-timing-v5/pilot-profiles.json),
  [v4 comparison states](basketball-shared-timing-v5/v4-comparisons.json),
  [baseline and installed SciPy source hash](basketball-shared-timing-v5/prepare-final/baseline.json).
- [Evidence hashes and portable references](basketball-shared-timing-v5/evidence.json).
  Full attempt records, original/transformed multipliers and complementarity, original
  depth and KKT checks, coefficient/support diagnostics, observable first/intermediate/final
  coordinates, warnings and seed provenance are stored once per attempt in six compressed
  group files under `pilot/`.

Validation runs 166 Basketball, 7 budget and 3 SelfCap regressions. Independent verification
reconstructs the 667/667 partition and 72 edges, checks 1,890 immutable production recipes,
recomputes saved physical objectives/depths and original-unit stationarity, verifies seed
provenance, historical hashes, documentation links and unchanged consumption markers.
The [verification record](basketball-shared-timing-v5/verification-final.json) reports the completed
checks and elapsed budget. Production remains immutable v2. Earlier v2/v3/v4 failures are
preserved; the bounded barrier is a numerical change, not timing qualification.
