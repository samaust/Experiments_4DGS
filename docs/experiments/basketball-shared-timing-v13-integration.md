# V13 source-only integration and timing-gate map

[Plan 020](../../plans/plan_020.md) produced a
[six-state qualified kernel](basketball-shared-timing-v13/decision.json), with
six acceleration costs and 36 selected partials. This report inspects existing
source only. No production integration, full evaluator, constraint, Hessian,
solver or GPU execution occurred. SC-01 and SC-03 remain not met.

## Evidence boundaries

The twelve fixed toy cases establish their analytic fixtures and dummy allocation,
deadline and process-cleanup behavior. The six retained states establish only
acceleration cost and coefficient rows 0/1 derivatives. All 54 physical coefficient
operands participate in acceleration. The other 48 gradient components are
unvalidated. The six partials equal full-objective partials because saved corrected
observation times are at least 2, strictly beyond both selected rows' supports;
saved depths exceed 1e-8. No new image/depth calculation established that fact.

Historical v10/v11 journals contain actual callback/entry evidence. They do not
establish accuracy of a future integrated candidate. V11 A2/A3 remain failed;
v12 preserves 25/36 primary and 17/36 independent selected gradient failures,
while both historical costs passed 6/6. The other 57 failed v11 states remain
unadjudicated. No six-state result repairs a historical check retrospectively.

## Required changes at each source surface

| Surface and inspected functions | Current formula and future coherent change | Still-required evidence |
| --- | --- | --- |
| [SplineProblem setup/evaluate](../../scripts/basketball_shared_spline_v2.py), lines 97–148 | Setup stores rounded `A=spline.derivative(2)(quadrature)`. Evaluation appends `sqrt(weight/nacc)*(A@C)` and the matching scaled A Jacobian block. A future acceleration cost/full-gradient interface must consume original knot, quadrature, weight and coefficient operands. Replacing six outputs or subtracting an old rounded gradient from an already rounded full gradient loses information and is insufficient. Separate data/acceleration cost and derivative ownership coherently. | Full components, all groups/offset blocks, supported observation rows, finite domains and cost/gradient agreement on actual retained operating states. The current six-partial result covers none of the image contribution or free-offset derivatives. |
| [CanonicalAdapter and accounting](../../scripts/basketball_shared_accounting_v10.py), Ledger 42–87, NumericalEntries 90–119, adapter 123–185 | Residual cache stores `(r,J@D)` by canonical state identity; fun is `r@r`, jac is `P.T@(2*J.T@r)`. Hessian owns another cache entry. Add one coherent full objective/gradient result at that same owned state, retaining exact physical input bytes. Ledger consumption and independently observed numerical entry must precede computation. `set_transform` still obtains residual J and uses its coefficient SVD; a new cost/gradient interface alone does not qualify this transform. | Objective-first, gradient-first, cold transform-first, Hessian-first and constraint-first request orders; cold/repeated cache hits, exceptions and interrupted entries; transforms/origin, canonical/physical identity and both 200 caps. Historical accounting and v13 dummy tests are prerequisites, not tests of the future interface. |
| [solve returned-state reporting](../../scripts/basketball_shared_solver_v10.py), lines 25–59 | Callback retains the exact owned canonical state and multipliers. Return independently forms `G=2*J.T@r` and `objective=r@r`; `Cd=depth_J.T@vd`, `Cb=inverse.T@bound_multiplier`, and KKT combines them. Both solver callbacks and returned-state reporting must use the same qualified objective/gradient at their actual owned state, including interrupted return without an x→q round trip. | Actual callback and returned-state cost/full-gradient/KKT agreement, multiplier ownership, independent returned-state verification and interrupted-state provenance. Six partials do not cover full stationarity. |
| [exact_objective_hessian and depth](../../scripts/basketball_shared_solver_v6.py), raw_depth 75–102, depth/transform 105–124, Hessian 262–296 | Acceleration curvature is a separate `kron(2*weight/nacc*(A.T@A),I3)` block. Data curvature includes robust image loss and projection second derivatives, coefficient/offset cross terms and offset curvature. This function receives physical x but already returns q-coordinate Hessian; scaling it by D again would be wrong. Raw and bounded depth have separate first/second chain rules. A future full-component candidate needs a consistent Hessian, not an assumed derivative of the seven v13 outputs. | Full Hessian symmetry and objective/gradient/Hessian consistency, physical/q/y transforms, data and mixed curvature, raw/bounded depth derivatives and multiplier-weighted constraint curvature. V13 supplies no Hessian evidence. |
| [direct_gradient/verify_row](../../scripts/basketball_shared_verify_v9.py), lines 15–69, and [Direct objective/depth/forces](../../scripts/basketball_shared_trajectory_verify_v11.py), lines 15–64 | V9 uses direct point-loss derivatives plus `2*weight/nacc*A.T@(A@C)`; its offsets follow the canonical time convention. V11 separately evaluates trajectory acceleration and multiplies it by independently built rounded A transpose. Both verify data/depth and constraint forces separately; v11 constructs `vd=vg*gp`, `Cdepth=depth_J.T@vd`, `Cb=inverse.T@vb`, `KKT=G+Cdepth+Cb`. Preserve genuinely independent arithmetic and actual low-level entry observation; calling the candidate twice is not independent verification. | Full-state actual operating-point reference checks for costs, all derivatives, depth, constraints, KKT, coordinate conventions and canonical ownership. Existing direct floating arithmetic failed these retained cancellation cases and must not become an unquestioned oracle. |

## Coordinate and constraint contract

Use `x=Dq`, `q=origin+Py`. For a physical full gradient and Hessian:
`Gq=D.T Gx`, `Gy=P.T Gq`, `Hq=D.T Hx D`, and `Hy=P.T Hq P`.
D scales free camera offsets by 25 and coefficient coordinates by one. The v6
objective Hessian already returns q coordinates; the adapter applies only P at
its Hessian interface. Preserve all coefficient and null directions, including
inactive support directions and identity nuisance blocks.

For raw depth z and `s=z-MARGIN`, bounded depth uses
`g=s/sqrt(1+s²)`, `gp=(1+s²)^(-3/2)`,
`gpp=-3s*(1+s²)^(-5/2)`. Its weighted curvature is
`sum_i(v_i*gp_i*H_z_i) + J_z.T diag(v*gpp) J_z`, transformed into y by P.
Original-depth multipliers are `vd=vg*gp`; conditioned bound multipliers return
through `P^(-T)`. Original-coordinate stationarity and complementarity require
consistent coordinate conventions for every term. Raw-depth code and the adapter's
unit scale wrapper must be checked independently on free-offset states: comments
or toy-only evidence do not establish that chain rule. Preserve underflow/nonfinite
rejections. No raw-depth or multiplier convention is changed here.

## Unchanged timing gates

[Plan 015 sections 6 and 8](../../plans/plan_015.md) remain authoritative. A kernel
pass does not authorize a full screen or timing selection.

| Gate | Required future evidence and present gap | Criteria |
| --- | --- | --- |
| Applicable evaluator integrity | Full cost/gradient/Hessian/constraints/KKT consistency on actual benchmark states and all coordinate/request paths. Six partials do not qualify it; v11 remains failed. | SC-01/05 |
| Focused solver qualification | Every required target and dependency qualifies within both 200 iterations and 200 distinct canonical states; qualified controls and costs preserved; all three target paths agree. No missing seed or unresolved transform, support, growth, initialization or stopping failure. V10 failed. | SC-01/03 |
| Full conditioning | Original 144 attempts on 48 problems and three paths; preserve 94 v6 qualifications/costs, recover at least 25/50 across groups, median KKT ratio <=0.1. No qualified new policy or screen exists. | SC-01/03 |
| Independent scalar screen | Original 48 problems, 7344 initial path attempts, frozen inclusive 0.05/0.01 refinements; all conditional fits/paths and nine basin/cost comparisons pass. | SC-01/03 |
| Combined pilot/evaluator qualification | Both full screens pass before a fresh combined pilot; all 144 complete outer paths, transfers/basins and historical cost controls qualify; evaluator, selection and final-validation gates then require separately planned evidence. | SC-01/03 |
| Basketball reconstruction/comparison | Accepted timing, shared validated preparation/split, training-only initialization, complete saved/reloaded supported models, time/view renders and measured quality/motion/speed/resources within remaining method/scene ceilings. Basketball results are absent. | SC-01/02/03/04/05 |

Keep KKT <=1e-6, qualification depth >1e-7 and objective agreement
`1e-6 + 1e-4*max(abs(F1),abs(F2))`, all original partitions and scientific gates.
V10 still has six missing directional seeds and eight path disagreements.
Conditioning's median KKT ratio is 0.2419725969, above 0.1. Final policy's 50/81
qualifications, preserved 47 controls and repaired feasibility coexist with
unqualified cold starts, including weight-zero cold failures in all three groups.
Acceleration weight zero makes this candidate inactive; improved acceleration
arithmetic cannot solve those strata.

## One outcome-linked next action

Because all 42 v13 comparisons pass, next Review should select a finite coherent
full-component integration/evaluator-qualification experiment on retained actual
v10/v11 operating states, with cost, full gradient, Hessian, constraints, KKT and
ownership validation, including an explicit weight-zero control stratum. The next
Plan must freeze concrete state counts, interface changes, independent validation,
request orders and resource limits before execution. This advances the still-failed
applicable evaluator-integrity gate. No integration evaluation or solver fit is
allocated here; another extreme-state or precision ladder is not the next action.
