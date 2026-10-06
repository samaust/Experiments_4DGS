"""Whole-stack final-render licence gate shared by qualification and DO admission.

Status `allowed` requires every permission allowed. Status `research_use` binds an
approved human decision (2026-10-05) to run the stack for non-commercial research;
it never claims commercial clearance. Prohibited permissions are always refused.
"""
from .files import read_json, verify_record

SCHEMA = 'plan069-final-render-commercial-assessment/v1'
DECISION = 'plan069-final-render-research-use-decision/v1'
PERMISSIONS = frozenset(('code', 'weights', 'dependencies', 'inference_outputs'))
RESEARCH_PERMISSIONS = frozenset(('allowed', 'research_only', 'unverified'))


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _bound(record):
    _require(type(record) is dict and set(record) == {'path', 'sha256', 'bytes'} and
        verify_record(record) == record, 'exact unchanged licence evidence required')
    return read_json(record['path'])


def validate_commercial(record, runtime, sources):
    """Return the bound assessment after checking its permissions and lineage."""
    assessment = _bound(record)
    _require(assessment.get('schema') == SCHEMA and assessment.get('record_kind') == 'actual' and
        type(assessment.get('reviewer')) is str and bool(assessment['reviewer'].strip()),
        'actual reviewed licence assessment required')
    _require(assessment.get('runtime') == runtime and assessment.get('source_files') == sources,
        'licence assessment must bind exact runtime/sources')
    permissions = assessment.get('permissions')
    _require(type(permissions) is dict and set(permissions) == PERMISSIONS, 'all four licence permissions required')
    status = assessment.get('status')
    if status == 'allowed':
        _require(all(value == 'allowed' for value in permissions.values()),
            'allowed status requires all permissions allowed')
    else:
        _require(status == 'research_use', 'licence status must be allowed or research_use')
        _require(all(value in RESEARCH_PERMISSIONS for value in permissions.values()),
            'research-use permissions cannot include prohibited terms')
        _require(assessment.get('commercial_clearance') is False, 'research use cannot claim commercial clearance')
        decision = _bound(assessment.get('research_use'))
        _require(decision.get('schema') == DECISION and decision.get('record_kind') == 'human' and
            decision.get('status') == 'approved' and decision.get('decision') == 'research_use' and
            type(decision.get('reviewer')) is str and bool(decision['reviewer'].strip()) and
            type(decision.get('approved_at')) is str and bool(decision['approved_at'].strip()) and
            decision.get('commercial_clearance') is False and decision.get('runtime') == runtime,
            'approved human research-use decision for this runtime required')
    primary = assessment.get('primary_sources')
    _require(type(primary) is list and bool(primary), 'primary licence sources required')
    for source in primary:
        _require(type(source) is dict and set(source) == {'path', 'sha256', 'bytes'} and
            verify_record(source) == source, 'exact unchanged primary licence source required')
    return assessment
