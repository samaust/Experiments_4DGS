"""Plan 012 fixed saved-state curvature probes. This module never optimizes."""
import hashlib
import time
import numpy as np
from scipy.sparse import diags
from basketball_shared_solver_v5 import ConstrainedProblem, transform, support, MARGIN
from basketball_shared_spline_v2 import project_jacobian

POLICY = dict(namespace='v6-diagnostic-only', steps=[1e-3, 1e-4, 1e-5, 1e-6],
              halvings=20, stability_atol=1e-7, stability_rtol=1e-3,
              minimum_rho=.1, error_multiplier=10., groups=[2, 9, 11],
              objective_hessian='independent central differences of immutable analytic gradient',
              approximation='2 J_r.T J_r', offset_scale=25., coefficient_scale=1.,
              states=['first', 'middle', 'returned'], weak_directions=4)


def parameter_hash(x):
    return hashlib.sha256(np.asarray(x, dtype='<f8').tobytes()).hexdigest()


def snapshots(row):
    trace = row.get('solver_trace')
    if not trace or 'x' not in row:
        raise ValueError('missing required callback/returned state')
    result = []
    for label, index in [('first', 0), ('middle', len(trace)//2), ('returned', None)]:
        state = row if index is None else trace[index]
        x = np.asarray(state['x'], float)
        if x.ndim != 1 or not np.isfinite(x).all():
            raise ValueError('missing/nonfinite required parameters')
        if index is None and any(row.get(k) is None for k in
                                ['multipliers_transformed', 'multipliers_depth', 'bound_multipliers']):
            raise ValueError('missing returned multipliers')
        result.append(dict(label=label, index=index, x=x.tolist(), sha256=parameter_hash(x)))
    return result


def canonical(v):
    v = np.asarray(v, float).copy()
    if v[np.argmax(np.abs(v))] < 0:
        v *= -1
    return v


def deterministic_svd(J):
    """Canonical coordinate-pivot basis of each numerically repeated subspace.

    Projectors are invariant to LAPACK's arbitrary basis in repeated/null spaces.
    The grouping tolerance is explicitly recorded, separate from the rank rule.
    """
    _, s, vt = np.linalg.svd(J, full_matrices=False)
    n = J.shape[1]
    if len(s) != n:
        _, _, vt = np.linalg.svd(J, full_matrices=True)
        s = np.r_[s, np.zeros(n-len(s))]
    tol = max(J.shape)*np.finfo(float).eps*(s[0] if len(s) else 0.)
    groups = []; vectors = []; i = 0
    while i < n:
        end = i+1
        while end < n and abs(s[end]-s[i]) <= tol:
            end += 1
        sub = vt[i:end]; P = sub.T@sub; basis = []
        for j in range(n):
            v = P[:, j].copy()
            for _ in range(2):
                for b in basis:
                    v -= b@v*b
            norm = np.linalg.norm(v)
            if norm > 1e-10:
                basis.append(canonical(v/norm))
            if len(basis) == end-i:
                break
        if len(basis) != end-i:
            raise ArithmeticError('unresolved deterministic singular subspace')
        vectors.extend(basis)
        groups.append(dict(indices=list(range(i, end)), projector=P.tolist() if end-i > 1 else None, basis=[b.tolist() for b in basis],
                           singular_values=s[i:end].tolist()))
        i = end
    return s, np.asarray(vectors), tol, groups


class DiagnosticProblem:
    """Separate unlimited probe ledger: never touches a scientific fit cache."""
    def __init__(self, problem):
        self.p = problem
        self.a = ConstrainedProblem(problem)
        self.scale = self.a.scale
        self.calls = 0; self.distinct = set(); self.seconds = 0.

    def evaluate(self, q):
        self.p.check(); start = time.monotonic()
        r, J = self.p.evaluate(np.asarray(q)*self.scale)
        J = (J@diags(self.scale)).toarray()
        self.calls += 1; self.distinct.add(parameter_hash(q))
        self.seconds += time.monotonic()-start
        self.p.check()
        return r, J, 2*J.T@r

    def feasible(self, q):
        self.p.check()
        if not np.isfinite(q).all() or np.any(np.abs(q[:self.p.n_offsets]) > 1):
            return False
        d, _ = self.a.raw_depth(q)
        return bool(np.isfinite(d).all() and np.min(d) > MARGIN)


def recent_steps(row, index, scale):
    trace = row['solver_trace']
    states = [np.asarray(t['x'])/scale for t in trace[:index+1]] if index is not None else [
        *[np.asarray(t['x'])/scale for t in trace], np.asarray(row['x'])/scale]
    distinct = []
    for q in states:
        if not distinct or not np.array_equal(q, distinct[-1]):
            distinct.append(q)
    return [distinct[i]-distinct[i-1] for i in range(len(distinct)-1, max(0, len(distinct)-3), -1)]


def directions(J, gradient, steps, n_offsets):
    s, basis, tol, subspaces = deterministic_svd(J)
    raw = [(f'singular_{i}', basis[i]) for i in range(len(s)-1, max(-1, len(s)-5), -1)]
    if np.linalg.norm(gradient):
        raw.append(('gradient', gradient))
    raw.extend((f'saved_step_{i}', v) for i, v in enumerate(steps))
    z = np.zeros(J.shape[1]); z[n_offsets+2::3] = 1
    raw.append(('uniform_z', z))
    chosen = []
    for label, v in raw:
        norm = np.linalg.norm(v)
        if not norm:
            continue
        v = canonical(v/norm)
        prior = next((r for r in chosen if np.array_equal(r['vector'], v)), None)
        if prior is not None:
            prior['labels'].append(label)
        else:
            chosen.append(dict(labels=[label], vector=v))
    return chosen, dict(singular_values=s.tolist(), rank=int(np.sum(s > tol)),
                       rank_threshold=float(tol), nullspace_dimension=int(len(s)-np.sum(s > tol)),
                       repeated_subspace_tolerance=float(tol), subspaces=subspaces)


def probe(a, q, v, GN, gradient, steps, Jdata, Jacc):
    levels = []; selected = None; previous = None
    for nominal in POLICY['steps']:
        a.p.check(); h = nominal; reason = None
        for halvings in range(POLICY['halvings']+1):
            plus, minus = q+h*v, q-h*v
            if np.array_equal(plus, q) or np.array_equal(minus, q):
                reason = 'unchanged perturbation'; break
            if a.feasible(plus) and a.feasible(minus):
                break
            if halvings == POLICY['halvings']:
                reason = 'infeasible after 20 halvings'; break
            h /= 2
        row = dict(nominal_step=nominal, actual_step=h, halvings=halvings, rejected=reason)
        if reason is None:
            rp, _, gp = a.evaluate(plus); rm, _, gm = a.evaluate(minus)
            u = (gp-gm)/(2*h)
            # Forward-error floor: cancellation must be resolved before interpretation.
            floor = np.finfo(float).eps*(np.abs(gp)+np.abs(gm))/(2*h)
            if not np.isfinite(u).all():
                row['rejected'] = 'nonfinite Hessian action'
            elif np.max(np.abs(u)) <= 10*np.max(floor) and np.any(gp != gm):
                row['rejected'] = 'unresolved cancellation'
            elif np.array_equal(gp, gm) and np.any(Jdata@v != 0):
                row['rejected'] = 'unresolved identical gradients in non-null direction'
            else:
                row.update(action=u.tolist(), cancellation_floor_inf=float(np.max(floor)),
                           objective_directional_fd=float((rp@rp-rm@rm)/(2*h)),
                           objective_gradient_projection=float(gradient@v),
                           directional_quadratic=float(v@u))
                if previous is not None and max(h, previous[0])/min(h, previous[0]) >= 2:
                    E = float(np.max(np.abs(u-previous[1])))
                    stable = E <= 1e-7+1e-3*max(np.max(np.abs(u)), np.max(np.abs(previous[1])))
                    row.update(predecessor_level=previous[2], stability_error=E, stable=bool(stable))
                    if stable:
                        discrepancy = u-GN@v; M = float(np.max(np.abs(discrepancy)))
                        rho = M/max(np.max(np.abs(u)), np.max(np.abs(GN@v)), 1e-12)
                        def cosine(w):
                            den = np.linalg.norm(w)*np.linalg.norm(discrepancy)
                            return float(w@discrepancy/den) if den else None
                        selected = dict(level=len(levels), E=E, M=M, rho=float(rho),
                                        discrepancy=discrepancy.tolist(), gradient_alignment=cosine(gradient),
                                        step_alignments=[cosine(w) for w in steps],
                                        missing_curvature_screen=bool(rho >= .1 and M > 10*E+1e-7))
                previous = (h, u, len(levels))
        if row['rejected']:
            previous = None
        levels.append(row)
    return dict(levels=levels, selected=selected, GN_action=(GN@v).tolist(),
                GN_quadratic=float(v@GN@v), data_motion=(Jdata@v).tolist(),
                acceleration_motion=(Jacc@v).tolist(),
                exactly_data_null=bool(np.all(Jdata@v == 0)),
                data_motion_norm=float(np.linalg.norm(Jdata@v)))


def stationarity(a, q, gradient, row, label, index):
    depth, Dz = a.a.raw_depth(q)
    g, gp, _, flags = transform(depth-MARGIN); Jg = diags(gp)@Dz
    mu = row['solver_trace'][-1 if index is None else index]['barrier_parameter']
    result = dict(barrier_parameter=mu, transformation_flags=flags,
                  original_depths=depth.tolist(), offset_bounds_satisfied=bool(np.all(np.abs(q[:a.p.n_offsets]) <= 1)))
    def vector(name, value):
        result[name] = value.tolist(); result[name+'_inf'] = float(np.max(np.abs(value)))
    vector('G', gradient)
    if np.any(g <= 0) or not np.isfinite(g).all() or flags['derivative_underflow']:
        result.update(barrier_available=False, barrier_reason='boundary/nonfinite/underflow')
    else:
        vector('B_depth', np.asarray(-mu*Jg.T@(1/g)).ravel())
        result['central_multipliers_transformed'] = (-mu/g).tolist()
        result['barrier_available'] = True
    free = q[:a.p.n_offsets]
    if np.all(np.abs(free) < 1):
        b = np.zeros_like(q); b[:len(free)] = mu*(1/(1-free)-1/(1+free)); vector('B_bounds', b)
    else:
        result['B_bounds'] = None; result['bounds_barrier_reason'] = 'offset on boundary'
    if label != 'returned':
        result.update(multiplier_KKT_available=False, multiplier_KKT_reason='callback trace does not save multipliers')
    else:
        vg = np.asarray(row['multipliers_transformed']); vd = np.asarray(row['multipliers_depth'])
        vb = np.asarray(row['bound_multipliers'])
        np.testing.assert_allclose(vd, vg*gp, rtol=1e-10, atol=1e-12)
        cd = np.asarray(Dz.T@vd).ravel(); vector('C_depth', cd); vector('C_bounds', vb)
        vector('KKT', gradient+cd+vb)
        result.update(multiplier_KKT_available=True,
                      multiplier_conversion_error=float(np.max(np.abs(vd-vg*gp))),
                      representation_error=float(np.max(np.abs(cd-Jg.T@vg))),
                      dual_sign_transformed=float(max(0., max(vg))), dual_sign_original=float(max(0., max(vd))),
                      complementarity_original=(vd*(depth-MARGIN)).tolist(),
                      complementarity_transformed=(vg*g).tolist(),
                      central_path_multiplier_error_inf=float(np.max(np.abs(vg+mu/g))) if np.all(g > 0) else None)
        np.testing.assert_allclose(result['KKT_inf'], row['optimality'], rtol=1e-8, atol=1e-10)
    return result


def analyze(problem, row, snap):
    a = DiagnosticProblem(problem); q = np.asarray(snap['x'])/a.scale
    r, J, G = a.evaluate(q); nd = problem.n*2; Jdata, Jacc = J[:nd], J[nd:]
    steps = recent_steps(row, snap['index'], a.scale)
    chosen, spectrum = directions(Jdata, G, steps, problem.n_offsets)
    offsets, coefficients = problem.unpack(q*a.scale)
    observations = []; knot_distances = []; continuity = []
    for gi, group in enumerate(problem.groups):
        for obs in group['observations']:
            t = (np.asarray(obs['frames'])-offsets[obs['camera_id']])/25
            xyz = problem.spline(t)@coefficients[gi]
            pred, _, _ = project_jacobian(xyz, problem.cameras[obs['camera_id']], problem.center, problem.diameter)
            observations.append(dict(camera_id=obs['camera_id'], normalized_xyz=xyz.tolist(), residual_pixels=(pred-obs['xy']).tolist()))
            knot_distances.extend(np.min(np.abs(t[:, None]-problem.spline.t), axis=1))
    for knot in np.unique(problem.spline.t)[1:-1]:
        left = problem.spline.derivative(2)(np.nextafter(knot, -np.inf))
        right = problem.spline.derivative(2)(np.nextafter(knot, np.inf))
        continuity.append(float(np.max(np.abs(left-right))))
    out = dict(parameter_sha256=snap['sha256'], objective=float(r@r), data_objective=float(r[:nd]@r[:nd]),
               acceleration_objective=float(r[nd:]@r[nd:]), residual=r.tolist(), analytic_gradient=G.tolist(),
               spectrum=spectrum, data_column_norms=np.linalg.norm(Jdata, axis=0).tolist(),
               coefficient_max=float(np.max(np.abs(coefficients))), coefficient_norm=float(np.linalg.norm(coefficients)),
               support=support(problem, q*a.scale), observations=observations,
               nearest_knot_seconds=float(min(knot_distances)), second_derivative_knot_jump_max=max(continuity),
               stationarity=stationarity(a, q, G, row, snap['label'], snap['index']), probes=[])
    for direction in chosen:
        v = direction['vector']
        out['probes'].append(dict(labels=direction['labels'], vector=v.tolist(),
                                  **probe(a, q, v, 2*J.T@J, G, steps, Jdata, Jacc)))
    out['ledger'] = dict(namespace=POLICY['namespace'], calls=a.calls, distinct_states=len(a.distinct), seconds=a.seconds,
                         scientific_objective_evaluations=0, scientific_solves=0)
    return out


def gate(rows, verified, account_supported):
    witnesses = {}; counterexamples = []
    for row in rows:
        if row['label'] != 'returned' or row['saved_valid']:
            continue
        qualifying = [i for i, p in enumerate(row['analysis']['probes']) if
                      any(s == 'gradient' or s.startswith('saved_step') for s in p['labels']) and
                      not p['exactly_data_null'] and p['selected'] is not None and p['selected']['missing_curvature_screen']]
        entry = dict(reference=row['reference'], group_id=row['group_id'], probes=qualifying)
        if qualifying:
            witnesses.setdefault(str(row['group_id']), []).append(entry)
        else:
            counterexamples.append(entry)
    missing = [g for g in POLICY['groups'] if str(g) not in witnesses]
    blockers = []
    if not verified:
        blockers.append('saved-state arithmetic, derivative or provenance evidence unresolved')
    if missing:
        blockers.append('no stable observable gradient/saved-step curvature witness in groups '+str(missing))
    if not account_supported:
        blockers.append('support/barrier/stationarity account does not substantiate missing objective curvature')
    return dict(passed=not blockers, terminal_kind='numerical_failure' if blockers else None,
                blockers=blockers, witnesses=witnesses, counterexamples=counterexamples, missing_groups=missing,
                timing_qualification=False, thresholds=POLICY)
