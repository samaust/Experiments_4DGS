"""Extended human depth review with an independently justified metric D*.

The historical Plan 067 review format is unchanged. Fixture mode can exercise
this boundary but never establishes an actual human decision or execution right.
"""
from pathlib import Path

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
    proof = _completed_qualification(candidate, slot, generation, actual)
    if proof is not None:
        normalized['completed_qualification'] = proof
    blockers.extend(_qualification_blockers(candidate, evidence, generation, actual, proof))
    return dict(eligible=not blockers, reason='; '.join(blockers) if blockers else
        'Exact commercial/runtime/generation and frozen fit/check gates passed', evidence=normalized)


def _completed_qualification(candidate, slot, generation, actual):
    """Bind historical source inventories to completed, admitted native output.

    Local worktree paths are mutable. Their hashes remain metadata inside the
    immutable reviewed receipts; native archives and all receipt files are still
    rehashed. This grants no current-source or active-execution authorization.
    """
    provenance = slot.get('provenance', {})
    if not {'configuration','ledger_outcome'} <= provenance.keys():
        return None
    request = _record(provenance['configuration'])
    finish = _record(provenance['ledger_outcome'])
    evidence = slot['evidence']
    if (finish.get('event') != 'finish' or finish.get('status') != 'complete' or
        finish.get('result') != evidence['generation'] or
        finish.get('job_id') != generation.get('job_id', generation.get('id')) or
        request.get('job_id', request.get('id')) != finish['job_id'] or
        request.get('candidate',request.get('component')) != candidate or
        request.get('context') != generation.get('context') or
        not {'admission','qualification','source_review'} <= request.keys()):
        return None
    admission = _record(request['admission'])
    qualification = _record(request['qualification'])
    source_review = _record(request['source_review'])
    runtime = _record(evidence['runtime']) if 'runtime' in evidence else {}
    if (admission.get('schema') != 'plan069-depth-admission-result/v1' or
        admission.get('status') != 'passed' or admission.get('candidate') != candidate or
        admission.get('qualification') != request['qualification'] or
        admission.get('source_review') != request['source_review'] or
        admission.get('runtime', {}).get('receipt') != evidence.get('runtime') or
        admission.get('commercial', {}).get('assessment') != evidence.get('commercial') or
        qualification.get('status') != 'passed' or qualification.get('candidate') != candidate or
        qualification.get('runtime', {}).get('receipt') != evidence.get('runtime') or
        qualification.get('commercial', {}).get('assessment') != evidence.get('commercial') or
        qualification.get('source_review') != request['source_review'] or
        source_review.get('status') != 'passed' or source_review.get('candidate') != candidate or
        source_review.get('source_revision') != runtime.get('source_revision') or
        not runtime.get('local_sources') or source_review.get('local_sources') != runtime['local_sources'] or
        not runtime.get('source_archive') or
        qualification.get('source_archive') != runtime['source_archive'] or
        source_review.get('source_archive') != runtime['source_archive'] or
        not runtime.get('source_files') or
        qualification.get('source_files') != runtime['source_files'] or
        source_review.get('source_files') != runtime['source_files']):
        return None
    if candidate == 'D6' and ('qualification_kind' in runtime or
            'driver_qualification' in runtime or runtime.get('cuda_initialized') is True):
        from .depth_driver_qualification import qualification_exception
        qualification_exception(runtime)
    _verify_file(runtime['source_archive'])
    if actual:
        from .config import load
        from .ledger import Ledger
        root = Path(evidence['generation']['path']).resolve().parents[2]
        events = Ledger(root/'ledger.jsonl', dict(load(),new_download_gib_limit=110,
            new_artifact_disk_gib_limit=210)).events()
        reserves = [event for event in events if event.get('event') == 'reserve' and
            event.get('job_id') == finish['job_id']]
        if finish not in events or len(reserves) != 1:
            return None
        reserved_request = reserves[0].get('evidence', {}).get('request')
        if (reserved_request is None or
            reserves[0].get('evidence', {}).get('admission') != request['admission'] or
            any(reserved_request[key] != provenance['configuration'][key] for key in ('sha256','bytes')) or
            _record(reserved_request) != request):
            return None
    return dict(request=provenance['configuration'],finish=provenance['ledger_outcome'],
        admission=request['admission'],qualification=request['qualification'],
        source_review=request['source_review'],source_archive=runtime['source_archive'],
        source_files=runtime['source_files'],local_sources=runtime['local_sources'])


def _qualification_blockers(candidate, evidence, generation, actual, completed):
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
    if candidate == 'D10' and runtime.get('profile', {}).get('runtime_profile', {}).get('id') == 'D9-D10-torch-2.14.1-pypi-cuda13':
        from .video_environment import PYPI_RECIPE, validate_runtime_versions, validate_runtime_observation
        from .files import file_record
        try:
            environment = dict(recipe=file_record(PYPI_RECIPE), runtime_profile=runtime['profile']['runtime_profile'])
            validate_runtime_versions(environment, dependencies.get('versions', {}))
            validate_runtime_observation(environment, dependencies.get('runtime_observation'))
            check(dependencies.get('runtime_recipe') == file_record(PYPI_RECIPE), 'PyPI dependency recipe binding changed')
        except (KeyError, TypeError, ValueError, OSError):
            check(False, 'actual PyPI video runtime observation required')
    expected_profile = read_json(PROFILES)['profiles'][candidate]
    if candidate == 'D10' and completed is not None and runtime.get('profile') != expected_profile:
        from .depth_admission import selected_profile_inventory
        from .files import object_hash
        request = _record(completed['request'])
        review = _record(request['review'])
        authorization = _record(request['authorization'])
        admission = _record(completed['admission'])
        qualification = _record(completed['qualification'])
        proposals = [row for row in review['proposals'] if row.get('candidate') == candidate]
        if len(proposals) != 1:
            return blockers + [candidate + ': exact completed runtime proposal missing']
        proposal_hash = object_hash(proposals[0])
        grants = [row for row in authorization.get('candidate_approvals', [])
                  if row.get('candidate') == candidate]
        if (authorization.get('schema') != 'plan069-depth-user-authorization/v1' or
                authorization.get('status') != 'DO' or authorization.get('review') != request['review'] or
                review.get('schema') != 'plan069-depth-execution-review/v1' or review.get('status') != 'REVIEW' or
                len(grants) != 1 or grants[0].get('schema') != 'plan069-depth-execution-approval/v1' or
                grants[0].get('status') != 'approved' or grants[0].get('max_attempts') != 1 or
                grants[0].get('proposal_sha256') != proposal_hash or proposals[0].get('max_attempts') != 1 or
                any(document.get('review') != request['review'] or
                    document.get('authorization') != request['authorization'] or
                    document.get('proposal_sha256') != proposal_hash
                    for document in (admission, qualification))):
            return blockers + [candidate + ': completed versioned runtime authority lineage differs']
        profile_inventory = selected_profile_inventory(proposals[0])
        expected_profile = read_json(profile_inventory)['profiles'][candidate]
        check(proposals[0]['profile'] == expected_profile,
              'completed versioned runtime profile differs from reviewed proposal')
    check(runtime.get('candidate') == candidate and runtime.get('source_revision') == revision and
        runtime.get('status') == 'passed' and
        runtime.get('dependency_manifest') == commercial['dependency_manifest'] and
        runtime.get('profile') == expected_profile,
        'exact passing runtime qualification required')
    runtime_config = _record(runtime['config'])
    check(runtime_config == read_json(HISTORICAL if candidate == 'D2' and actual else CONFIG),
        'runtime configuration changed')
    check(bool(runtime.get('local_sources')), 'runtime source evidence missing')
    if completed is None:
        if actual:
            blockers.append(candidate + ': completed historical source qualification binding missing')
        else:
            # CPU fixtures without completed-job lineage still exercise fresh-file checks.
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
