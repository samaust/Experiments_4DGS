"""Prespecified finalist rankings; incomplete evidence is never an implicit win."""
import math


def _value(row, field):
    value = row.get(field)
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'missing/nonfinite selection evidence: {field}')
    return round(value, 12)


def select(family, rows, *, missing_semantic_class=False):
    if family == 'S' and missing_semantic_class:
        return dict(status='unverified', selected='S2', ranking=[],
                    reason='predeclared S2 default: selection lacks person or ball truth')
    allowed = {'S': ['S1', 'S2', 'S3', 'S4'], 'M': ['M0', 'M1', 'M2'], 'N': ['N0', 'N1', 'N2']}[family]
    if set(rows) != set(allowed):
        raise ValueError('every finalist candidate needs evidence or an explicit failure record')
    eligible, rejected = [], {}
    for name in allowed:
        row = rows[name]
        if row.get('status') != 'complete':
            rejected[name] = row.get('reason', 'incomplete evidence')
            continue
        if family == 'N' and not row.get('all_references_have_three_neighbors'):
            rejected[name] = 'fewer than three neighbors for a tested reference'
            continue
        try:
            if family == 'S':
                score = (-min(_value(row, 'person_dice'), _value(row, 'ball_dice')),
                         _value(row, 'leakage'), -_value(row, 'retained_static_features'),
                         -_value(row, 'boundary_f1'), name)
            elif family == 'M':
                score = (-_value(row, 'static_dice'), _value(row, 'leakage'),
                         -_value(row, 'retained_static_features'), name)
            else:
                score = (-_value(row, 'foreground_reference_cells'), -_value(row, 'accepted_foreground_fraction'),
                         _value(row, 'matching_wall_seconds'), name)
            eligible.append((score, name))
        except ValueError as error:
            rejected[name] = str(error)
    eligible.sort()
    return dict(status='complete' if eligible else 'blocked', selected=eligible[0][1] if eligible else None,
                ranking=[dict(id=name, score=list(score)) for score, name in eligible], ineligible=rejected)


def combined(finalists, depth_gates, components):
    s, m, n = (finalists[k].get('selected') for k in ('S', 'M', 'N'))
    configs = {'C0': ['S0', 'D0', 'M0', 'N0'], 'C1': [s, 'D1', m, n],
               'C2': ['S4', 'D2', m, n], 'C3': ['S1', 'D1', 'M0', 'N0']}
    result = {}
    for slot, ids in configs.items():
        reasons = []
        if any(c is None for c in ids):
            reasons.append('missing eligible frozen finalist evidence')
        gate = depth_gates.get(ids[1], {})
        if gate.get('fit') != 'passed' or gate.get('check') != 'passed' or not gate.get('fit_hash') or not gate.get('check_hash'):
            reasons.append(f'{ids[1]} needs current hash-bound passing fit and frozen check')
        for component in ids:
            if component is not None and components.get(component, {}).get('status') != 'qualified':
                reasons.append(f'{component}: runtime/provenance not qualified')
        if slot == 'C2':
            for component in ids:
                record = components.get(component, {})
                if record.get('commercial_permission') != 'verified' or record.get('non_agpl') != 'verified':
                    reasons.append(f'{component}: exact code/weights/dependency license preferences unverified')
        result[slot] = dict(components=ids, status='blocked' if reasons else 'eligible', reasons=reasons)
    return result
