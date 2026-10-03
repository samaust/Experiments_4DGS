"""Extended human depth review with an independently justified metric D*.

The historical Plan 067 review format is unchanged. Fixture mode can exercise
this boundary but never establishes an actual human decision or execution right.
"""
from . import qualitative_review as historical
from .depth_admission import D2_SPEC, INVENTORY, PROFILES, HISTORICAL
from .depth_extension import CONFIG
from .files import file_record, read_json, verify_record, write_json

SCHEMA = 'plan069-depth-review/v1'
RESULT_SCHEMA = 'plan069-depth-review-result/v1'
DECISION_SCHEMA = 'plan069-depth-decision/v1'
METRIC_CANDIDATES = ('D2', 'D5', 'D6', 'D7', 'D8', 'D10')
OUTCOMES = ('selected', 'tie', 'unclear', 'unjudgeable', 'not_applicable')


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _verify_file(record):
    _require(type(record) is dict and set(record) == {'path','sha256','bytes'}, 'exact file record required')
    _require(verify_record(record) == record, 'file record bytes/path mismatch')
    return record


def _record(record):
    _verify_file(record)
    return read_json(record['path'])


def _legacy(value):
    return {key: child for key, child in dict(value, schema=historical.SCHEMA).items()
            if key != 'metric_choice'}


def _package(record, actual):
    package = historical._package(record, actual)
    _require('depth_aggregate_request' in package.get('bindings', {}), 'extended depth aggregate package required')
    if actual:
        from .depth_aggregate import validate_actual_package
        validate_actual_package(package)
    return package


def blank_review(package_record):
    """Return an empty extended form; it cannot satisfy human review."""
    _package(package_record, False)
    form = historical.blank_review(package_record)
    form.update(schema=SCHEMA, metric_choice=dict(outcome='unjudgeable', candidate_ids=[], reason='', examples=[]))
    return form


def _metric_evidence(candidate, slot, package, actual):
    evidence = slot.get('evidence', {})
    _require('generation' in evidence, candidate + ': generation receipt missing')
    generation = _record(evidence['generation'])
    _require(generation.get('status') == 'complete' and
        generation.get('record_kind') == ('actual' if actual else 'fixture') and
        generation.get('candidate', generation.get('component')) == candidate and
        generation.get('context') == package['bindings']['context'] and
        (candidate == 'D2' or generation.get('inputs', generation.get('original_inputs')) == package['bindings']['inputs']),
        candidate + ': exact completed generation required')
    _require(_record(package['bindings']['context']).get('inputs') == package['bindings']['inputs'],
        candidate + ': generated context inputs changed')
    if candidate == 'D2':
        results = {role: _record(evidence['historical_' + role]) for role in ('fit','check')}
        scales = {role: results[role]['scale'] for role in ('fit','check')}
    else:
        scales = generation.get('scales', generation.get('scale', {}))
    _require(set(scales) == {'fit','check'}, candidate + ': exact fit/check evidence required')
    fit, check = (_record(scales[key]) for key in ('fit','check'))
    _require(fit.get('component') == check.get('component') == candidate and
        fit.get('role') == 'fit' and check.get('role') == 'selection' and
        check.get('frozen_fit') == scales['fit'], candidate + ': frozen fit/check lineage required')
    _require(all(scale.get('provenance', {}).get('inputs') == package['bindings']['inputs']
        for scale in (fit, check)), candidate + ': scale input binding changed')
    _require(evidence.get('scale') == scales['check'], candidate + ': package scale binding changed')
    normalized = dict(evidence, fit=scales['fit'], check=scales['check'], inputs=package['bindings']['inputs'])
    blockers = []
    if fit.get('status') != 'passed' or check.get('status') != 'passed':
        blockers.append('frozen fit/check scale gates blocked')
    blockers.extend(_qualification_blockers(candidate, evidence, generation, actual))
    return dict(eligible=not blockers, reason='; '.join(blockers) if blockers else
        'Exact commercial/runtime/generation and frozen fit/check gates passed', evidence=normalized)


def _qualification_blockers(candidate, evidence, generation, actual):
    """Missing/failed engineering gates block D*, not visual observations."""
    blockers = []
    def check(condition, message):
        if not condition:
            blockers.append(candidate + ': ' + message)
    missing = [key for key in ('commercial','runtime') if key not in evidence]
    if missing:
        return [candidate + ': ' + '/'.join(missing) + ' qualification missing']
    commercial, runtime = (_record(evidence[key]) for key in ('commercial','runtime'))
    spec = dict(read_json(CONFIG)['candidates'], D2=D2_SPEC)[candidate]
    revision = spec['code']['revision']
    check(commercial.get('schema') == 'plan069-depth-commercial-assessment/v1' and
        commercial.get('candidate') == candidate and commercial.get('source_revision') == revision and
        commercial.get('weights_revision') == spec['weights']['revision'] and
        all(commercial.get(key) == 'allowed' for key in ('code','weights','dependencies','inference_outputs')),
        'exact commercial permission unresolved')
    check(type(commercial.get('primary_sources')) is list and len(commercial['primary_sources']) >= 2,
        'commercial primary evidence missing')
    if runtime.get('schema') != 'plan069-depth-runtime-qualification/v1':
        return blockers + [candidate + ': actual native runtime qualification missing; CPU preflight is insufficient']
    if 'dependency_manifest' not in commercial:
        return blockers + [candidate + ': commercial dependency closure missing']
    dependencies = _record(commercial['dependency_manifest'])
    check(dependencies.get('schema') == 'plan069-depth-installed-dependencies/v1' and
        dependencies.get('candidate') == candidate and dependencies.get('source_revision') == revision and
        bool(dependencies.get('files')), 'installed dependency closure required')
    for record in dependencies.get('files', []):
        _verify_file(record)
    check(runtime.get('candidate') == candidate and runtime.get('source_revision') == revision and
        runtime.get('status') == 'passed' and
        runtime.get('dependency_manifest') == commercial['dependency_manifest'] and
        runtime.get('profile') == read_json(PROFILES)['profiles'][candidate],
        'exact passing runtime qualification required')
    runtime_config = _record(runtime['config'])
    check(runtime_config == read_json(HISTORICAL if candidate == 'D2' and actual else CONFIG),
        'runtime configuration changed')
    check(bool(runtime.get('local_sources')), 'runtime source evidence missing')
    for record in runtime.get('local_sources', []):
        _verify_file(record)
    for row in runtime.get('assets', []):
        _verify_file(row['record'])
    if actual:
        expected = read_json(INVENTORY)['candidates'][candidate]['files']
        assets = runtime.get('assets', [])
        by_key = {(row['repository'], row['path']): row for row in assets}
        check(len(by_key) == len(assets) == len(expected), 'exact runtime asset inventory required')
        for row in expected:
            asset = by_key.get((row['repository'],row['path']), {}).get('record', {})
            check(asset.get('bytes') == row['bytes'] and
                (row['lfs_sha256'] is None or asset.get('sha256') == row['lfs_sha256']),
                'runtime asset revision changed')
    if 'source_archive' in runtime:
        _verify_file(runtime['source_archive'])
    if 'setup' in generation:
        check(runtime.get('setup') == generation['setup'], 'generated setup differs from qualified runtime')
        _record(generation['setup'])
    return blockers


def engineering_eligibility(package_record, *, actual=True):
    """Recompute metric gates from the immutable aggregate's native receipts."""
    package = _package(package_record, actual)
    request = _record(package['bindings']['depth_aggregate_request'])
    result = {}
    for item in package['candidates']:
        candidate = item['id']
        if candidate not in METRIC_CANDIDATES:
            result[candidate] = dict(eligible=False, reason='Visual-only or historical reference for this extension', evidence={})
        elif item['status'] != 'available':
            result[candidate] = dict(eligible=False, reason='Candidate unavailable: ' + item.get('reason',''), evidence={})
        else:
            result[candidate] = _metric_evidence(candidate, request['candidates'][candidate], package, actual)
    return result


def validate_review(value, *, actual=True):
    """Validate exact visual observations and a separate explicit metric choice."""
    _require(type(value) is dict and value.get('schema') == SCHEMA, 'extended depth review schema')
    historical.validate_review(_legacy(value), actual=actual)
    package = _package(value['package'], actual)
    candidates = {item['id']: item for item in package['candidates']}
    choice = value.get('metric_choice', {})
    _require(type(choice) is dict and set(choice) == {'outcome','candidate_ids','reason','examples'}, 'explicit metric choice fields required')
    outcome, selected = choice['outcome'], choice['candidate_ids']
    _require(outcome in OUTCOMES and historical._text(choice['reason']), 'metric choice outcome/reason required')
    _require(type(selected) is list and len(selected) == len(set(selected)) and set(selected) <= set(METRIC_CANDIDATES), 'metric choice must use eligible metric candidates')
    _require((outcome == 'selected' and len(selected) == 1) or
        (outcome == 'tie' and len(selected) >= 2) or
        (outcome in ('unclear','unjudgeable','not_applicable') and not selected), 'metric outcome candidate membership')
    _require(type(choice['examples']) is list, 'metric examples required')
    for example in choice['examples']:
        historical._example(example, candidates)
    if selected:
        _require(set(selected) <= {example['candidate_id'] for example in choice['examples']}, 'each metric candidate needs exact visual examples')
    engineering_eligibility(value['package'], actual=actual)
    _require(all(candidates.get(key, {}).get('status') == 'available' for key in selected), 'metric choice unavailable')
    return value


def import_review(package_record, submission_record, output, *, actual=True):
    """Accept a submission once, preserving its original human fields."""
    submission = _record(submission_record)
    _require(submission.get('package') == package_record, 'submission belongs to another package')
    validate_review(submission, actual=actual)
    write_json(output, dict(schema=RESULT_SCHEMA, actual_human_review=actual,
        submission=submission_record, package=package_record, review=submission))
    return file_record(output)


def _load_review(record, actual):
    value = _record(record)
    if value.get('schema') == RESULT_SCHEMA:
        submission = _record(value['submission'])
        _require(value.get('actual_human_review') == actual and value.get('package') == submission.get('package') and
            value.get('review') == submission, 'imported review substitution or mode mismatch')
        value = submission
    return validate_review(value, actual=actual)


def _decision(review_record, actual):
    review = _load_review(review_record, actual)
    choice = review['metric_choice']
    eligibility = engineering_eligibility(review['package'], actual=actual)
    ready = choice['outcome'] == 'selected' and all(eligibility[key]['eligible'] for key in choice['candidate_ids'])
    return dict(schema=DECISION_SCHEMA, actual_human_review=actual, mode='qualitative',
        review=review_record, package=review['package'], reviewer=review['reviewer'],
        visual_preference=review['criteria']['overall']['preference'], metric_choice=choice,
        engineering_eligibility=eligibility,
        selected_candidate_ids=choice['candidate_ids'] if ready else [],
        requested_candidate_ids=choice['candidate_ids'], status='ready' if ready else 'blocked',
        reason=choice['reason'] if ready or not choice['candidate_ids'] else
            'Metric choice blocked: ' + '; '.join(eligibility[key]['reason'] for key in choice['candidate_ids']))


def freeze_decision(review_record, output, *, actual=True):
    """Freeze ready or blocked D* with no visual fallback or tie resolution."""
    decision = _decision(review_record, actual)
    write_json(output, decision)
    return decision


def validate_decision(decision_record, *, actual=True):
    """Recheck all artifacts and eligibility before consuming a frozen D*."""
    decision = _record(decision_record)
    _require(decision.get('schema') == DECISION_SCHEMA, 'extended depth decision schema')
    _require(decision == _decision(decision['review'], actual), 'depth decision contents changed')
    return decision
