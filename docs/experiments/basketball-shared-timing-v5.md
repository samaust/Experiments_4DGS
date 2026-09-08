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

Results and unexecuted conditional stages will be recorded after the preregistered gate.
No timing candidate is currently qualified; `accepted_timing` is null.
