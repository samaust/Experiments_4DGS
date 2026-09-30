"""Immutable human qualitative observations and engineering choice handoff.

Validation checks structure and provenance, not whether a person truly authored
an opinion. Fixtures remain explicitly marked and cannot satisfy actual review.
"""
from datetime import datetime
import math

from .files import file_record, read_json, verify_record, write_json

SCHEMA = 'plan067-qualitative-review/v1'
CRITERIA = ('frozen_frame', 'motion', 'artifacts', 'sharpness', 'overall')
OUTCOMES = ('preferred', 'tie', 'unclear', 'unjudgeable', 'not_applicable')


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _bound(record):
    _require(isinstance(record, dict), 'file record required')
    _require(verify_record(record) == record, 'file record bytes/path mismatch')
    return read_json(record['path'])


def _verify_nested(value):
    if isinstance(value, dict):
        if {'path', 'sha256', 'bytes'} <= value.keys():
            _require(verify_record(value) == value, 'changed package artifact')
        else:
            for child in value.values():
                _verify_nested(child)
    elif isinstance(value, list):
        for child in value:
            _verify_nested(child)


def _package(record, actual):
    package = _bound(record)
    _require(package.get('schema') == 'plan067-qualitative-package/v1', 'package schema')
    _require(package.get('mode') == 'qualitative', 'qualitative package required')
    _require(package.get('record_kind') in ('actual', 'fixture'), 'package origin required')
    if actual:
        _require(package['record_kind'] == 'actual', 'fixture package is not actual evidence')
        from .qualitative_package import validate_package
        validate_package(package)
    _verify_nested(package)
    return package


def blank_review(package_record):
    """Return an unfilled form; exporting this never counts as human review."""
    package = _package(package_record, False)
    return {'schema': SCHEMA, 'record_kind': 'human',
        'reviewer': {'name': '', 'reviewed_at': ''}, 'package': package_record,
        'candidate_ids': [candidate['id'] for candidate in package['candidates']],
        'criteria': {key: {'observation': '',
            'preference': {'outcome': 'unjudgeable', 'candidate_ids': []},
            'examples': []} for key in CRITERIA}, 'tradeoffs': ''}


def _reviewer(value):
    _require(isinstance(value, dict) and _text(value.get('name')), 'human name/handle required')
    _require(_text(value.get('reviewed_at')), 'review date required')
    try:
        datetime.fromisoformat(value['reviewed_at'].replace('Z', '+00:00'))
    except ValueError as error:
        raise ValueError('ISO review date required') from error


def _example(example, candidates):
    _require(isinstance(example, dict), 'example reference required')
    candidate = candidates.get(example.get('candidate_id'))
    _require(candidate is not None and candidate['status'] == 'available', 'example candidate unavailable/unknown')
    media = [item for item in candidate['media'] if item['selection_id'] == example.get('selection_id')]
    _require(media, 'unknown candidate selection')
    if 'frame_id' in example:
        _require(set(example) == {'candidate_id', 'selection_id', 'frame_id'}, 'frame reference fields')
        _require(type(example['frame_id']) is int, 'integer frame ID required')
        _require(any(example['frame_id'] in item['frame_ids'] for item in media), 'unknown frame')
        return 'frame'
    _require(set(example) == {'candidate_id', 'selection_id', 'start_time', 'end_time'}, 'clip reference fields')
    start, end = example['start_time'], example['end_time']
    _require(all(type(value) in (int, float) and math.isfinite(value) for value in (start, end)) and start <= end, 'clip time range')
    _require(any(item['kind'] == 'clip' and item['timestamps'] and
        min(item['timestamps']) <= start <= end <= max(item['timestamps']) for item in media), 'unknown clip interval; sparse sequences are not motion clips')
    return 'clip'


def validate_review(value, *, actual=True):
    """Validate a submission and all bound artifacts. Actual is the default."""
    _require(isinstance(value, dict) and value.get('schema') == SCHEMA, 'review schema')
    _require(value.get('record_kind') in ('human', 'fixture'), 'review origin required')
    if actual:
        _require(value['record_kind'] == 'human', 'synthetic review cannot count as human review')
    _reviewer(value.get('reviewer'))
    package = _package(value.get('package'), actual)
    candidates = {candidate['id']: candidate for candidate in package['candidates']}
    _require(len(candidates) == len(package['candidates']), 'duplicate package candidates')
    ids = value.get('candidate_ids')
    _require(isinstance(ids, list) and len(ids) == len(set(ids)) and set(ids) == set(candidates), 'review must cover exact declared candidates')
    criteria = value.get('criteria')
    _require(isinstance(criteria, dict) and set(criteria) == set(CRITERIA), 'all five criteria required')
    _require(_text(value.get('tradeoffs')), 'overall tradeoffs required')
    for key, criterion in criteria.items():
        _require(isinstance(criterion, dict) and _text(criterion.get('observation')), 'criterion observation/reason required')
        preference = criterion.get('preference', {})
        outcome = preference.get('outcome')
        selected = preference.get('candidate_ids')
        _require(outcome in OUTCOMES and isinstance(selected, list), 'preference outcome/candidates required')
        _require(len(selected) == len(set(selected)) and set(selected) <= set(candidates), 'unknown/duplicate preference candidates')
        _require(all(candidates[candidate]['status'] == 'available' for candidate in selected), 'unavailable preference candidate')
        _require((outcome == 'preferred' and len(selected) >= 1) or
            (outcome == 'tie' and len(selected) >= 2) or
            (outcome in ('unclear', 'unjudgeable', 'not_applicable') and not selected), 'outcome candidate membership')
        examples = criterion.get('examples')
        _require(isinstance(examples, list), 'examples list required')
        kinds = [_example(example, candidates) for example in examples]
        if outcome in ('preferred', 'tie'):
            _require(examples, 'quality preference needs exact visual examples')
            _require(set(selected) <= {example['candidate_id'] for example in examples}, 'each preferred/tied candidate needs an exact example')
            if key == 'motion':
                _require('clip' in kinds, 'motion preference requires actual clip evidence')
                _require(all(any(media['kind'] == 'clip' for media in candidates[candidate]['media']) for candidate in selected), 'selected motion candidate has no continuous clip')
    return value


def import_review(package_record, submission_record, output, *, actual=True):
    """Publish an immutable accepted submission, preserving the original fields."""
    submission = _bound(submission_record)
    _require(submission.get('package') == package_record, 'submission belongs to another package')
    validate_review(submission, actual=actual)
    write_json(output, {'schema': 'plan067-qualitative-review-result/v1',
        'mode': 'qualitative', 'actual_human_review': actual,
        'submission': submission_record, 'package': package_record, 'review': submission})
    return file_record(output)


def _load_review(record, actual):
    document = _bound(record)
    if document.get('schema') == 'plan067-qualitative-review-result/v1':
        submission = _bound(document['submission'])
        _require(document['review'] == submission and document['package'] == submission['package'], 'imported review substitution')
        _require(document['actual_human_review'] == actual, 'review result mode mismatch')
        document = submission
    return validate_review(document, actual=actual)


def _decision(review_record, engineering_eligibility, choice, actual):
    review = _load_review(review_record, actual)
    _require(set(engineering_eligibility) == set(review['candidate_ids']), 'eligibility must cover exact candidates')
    _verify_nested(engineering_eligibility)
    for eligibility in engineering_eligibility.values():
        _require(type(eligibility.get('eligible')) is bool and _text(eligibility.get('reason')), 'engineering gate disposition required')
    preference = review['criteria']['overall']['preference']
    selected = []
    reason = 'Missing explicit human choice; tied or incomplete evidence remains blocked'
    if choice is not None:
        _require(choice.get('reviewer') == review['reviewer'] and _text(choice.get('reason')), 'choice requires original human reviewer and reason')
        selected = choice.get('candidate_ids')
        _require(isinstance(selected, list) and selected and len(selected) == len(set(selected)) and set(selected) <= set(review['candidate_ids']), 'explicit choice candidates')
        reason = choice['reason']
    elif preference['outcome'] == 'preferred':
        selected = preference['candidate_ids']
        reason = review['criteria']['overall']['observation']
    package = _package(review['package'], actual)
    available = {candidate['id'] for candidate in package['candidates'] if candidate['status'] == 'available'}
    ready = bool(selected) and all(candidate in available and engineering_eligibility[candidate]['eligible'] for candidate in selected)
    if selected and not ready:
        reason = 'Human choice is engineering-ineligible or unavailable: ' + reason
    decision = {'schema': 'plan067-qualitative-decision/v1', 'mode':'qualitative',
        'actual_human_review': actual, 'review': review_record, 'package': review['package'],
        'reviewer': review['reviewer'], 'human_choice': choice,
        'engineering_eligibility': engineering_eligibility,
        'selected_candidate_ids': selected if ready else [], 'requested_candidate_ids': selected,
        'status': 'ready' if ready else 'blocked', 'reason': reason}
    return decision


def freeze_decision(review_record, engineering_eligibility, output, *, choice=None, actual=True):
    """Freeze a human choice, or an explicit blocked disposition for ties."""
    decision = _decision(review_record, engineering_eligibility, choice, actual)
    write_json(output, decision)
    return decision


def build_report(review_record, decision_record, output, *, resource_costs=None, actual=True):
    """Bind original judgments and costs without inventing perceptual metrics."""
    review = _load_review(review_record, actual)
    decision = _bound(decision_record)
    _require(decision.get('schema') == 'plan067-qualitative-decision/v1' and decision.get('review') == review_record and decision.get('package') == review['package'], 'decision provenance mismatch')
    _require(decision.get('actual_human_review') == actual, 'decision mode mismatch')
    _require(decision == _decision(review_record, decision.get('engineering_eligibility', {}), decision.get('human_choice'), actual), 'decision contents do not match human choice and engineering gates')
    package = _package(review['package'], actual)
    _verify_nested(resource_costs)
    report = {'schema': 'plan067-qualitative-report/v1', 'mode':'qualitative',
        'actual_human_review': actual, 'package': review['package'], 'review': review_record,
        'decision': decision_record, 'human_review': review,
        'candidates': package['candidates'],
        'unavailable_candidates': [candidate for candidate in package['candidates'] if candidate['status'] != 'available'],
        'resource_costs': resource_costs if resource_costs is not None else {'status':'not_provided'},
        'measured_accuracy': False,
        'claim_limits': 'These are the named reviewer’s visual opinions on the bound outputs. They do not establish measured accuracy, physical depth accuracy, statistical significance, or unseen downstream quality.'}
    write_json(output, report)
    return report
