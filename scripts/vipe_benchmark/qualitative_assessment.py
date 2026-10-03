"""Immutable qualitative assessment of observed evidence, including missing work.

This reports human opinions and execution dispositions; it performs no scoring,
selection, execution, issue closure or independent commercial clearance.
"""
from datetime import datetime
import json
import math

from .files import read_json, verify_record, write_json, safe_path, object_hash
from .qualitative_review import validate_review

SCHEMA = 'plan069-qualitative-assessment-request/v1'
HISTORY = ('segmentation', 'depth', 'supplemental_d2')
DEPTH = tuple(f'D{i}' for i in range(12))


def _bound(record):
    if not isinstance(record, dict) or set(record) != {'path', 'sha256', 'bytes'}:
        raise ValueError('exact immutable file record required')
    if verify_record(record) != record:
        raise ValueError('file record bytes/path mismatch')
    return read_json(record['path'])



def _review(record, actual, *, extended=False):
    value = _bound(record)
    if value.get('schema') in ('plan067-qualitative-review-result/v1', 'plan069-depth-review-result/v1'):
        submission = _bound(value['submission'])
        if value.get('review') != submission or value.get('package') != submission.get('package') or value.get('actual_human_review') != actual:
            raise ValueError('imported human review substitution/mode mismatch')
        value = submission
    if extended:
        from .depth_review import validate_review as validate_depth_review
        return validate_depth_review(value, actual=actual)
    return validate_review(value, actual=actual)



def _supplement(record, actual):
    value = _bound(record)
    if value.get('schema') != 'plan067-human-observation-supplement/v1' or value.get('record_kind') != ('human' if actual else 'fixture'):
        raise ValueError('authentic observation supplement required')
    reviewer = value.get('reviewer', {})
    if not isinstance(reviewer.get('name'), str) or not reviewer['name'].strip():
        raise ValueError('supplement reviewer required')
    datetime.fromisoformat(reviewer['reviewed_at'].replace('Z', '+00:00'))
    if value.get('candidate_ids') != ['D2'] or not isinstance(value.get('observation'), str) or not value['observation'].strip():
        raise ValueError('D2 supplemental observation required')
    package = _bound(value['package'])
    if package.get('schema') != 'plan067-qualitative-package/v1' or package.get('record_kind') != ('actual' if actual else 'fixture'):
        raise ValueError('supplement package origin/schema mismatch')
    if actual:
        from .qualitative_package import validate
        validate(package)
    candidates = {item['id']: item for item in package['candidates']}
    for candidate in value.get('explicit_comparisons', []):
        if candidate not in candidates:
            raise ValueError('supplement comparison unknown')
    examples = value.get('examples')
    if not isinstance(examples, list) or not examples:
        raise ValueError('confirmed supplement examples required')
    for example in examples:
        if set(example) != {'candidate_id', 'selection_id', 'frame_id'} or example['candidate_id'] != 'D2' or type(example['frame_id']) is not int:
            raise ValueError('exact D2 frozen-frame example required')
        candidate = candidates.get('D2', {})
        media = candidate.get('media', [])
        if candidate.get('status') != 'available' or not any(item['selection_id'] == example['selection_id'] and example['frame_id'] in item['frame_ids'] for item in media):
            raise ValueError('supplement example unavailable/unknown')
        for item in media:
            if 'record' in item:
                verify_record(item['record'])
    previous = _bound(value['previous_observation'])
    for key in ('schema', 'record_kind', 'reviewer', 'package', 'candidate_ids', 'observation'):
        if previous.get(key) != value.get(key):
            raise ValueError('supplement changed original observation')
    return value

def _closure(snapshot):
    if snapshot.get('schema') != 'plan069-issue-snapshot/v1' or snapshot.get('repository') != 'samaust/Experiments_4DGS' or snapshot.get('roots') != [3, 18, 23]:
        raise ValueError('complete repository issue snapshot required')
    datetime.fromisoformat(snapshot['captured_at'].replace('Z', '+00:00'))
    issues = snapshot['issues']
    required = {18: [19, 20, 21, 22, 23, 44], 23: [34, 35, 45], 44: [56, 57, 58, 59], 45: [60, 61, 62]}
    for parent, children in required.items():
        if str(parent) not in issues or not set(children) <= set(issues[str(parent)]['children']):
            raise ValueError('omitted known child dependency')
    for key, item in issues.items():
        if not key.isdigit() or str(int(key)) != key or item.get('state') not in ('OPEN', 'CLOSED') or not isinstance(item.get('children'), list):
            raise ValueError('invalid issue state/identity/children')
        if any(type(child) is not int or str(child) not in issues for child in item['children']) or len(set(item['children'])) != len(item['children']):
            raise ValueError('missing/duplicate child issue')
    def descendants(key, visiting):
        if key in visiting:
            raise ValueError('cyclic issue hierarchy')
        result = set()
        for child in issues[key]['children']:
            result.add(str(child))
            result.update(descendants(str(child), visiting | {key}))
        return result
    closures = {}
    for key in issues:
        children = descendants(key, set())
        unfinished = sorted(int(child) for child in children if issues[child]['state'] != 'CLOSED')
        closures[key] = dict(state=issues[key]['state'], all_descendants_closed=not unfinished,
                             unfinished_descendants=unfinished)
    for root in snapshot['roots']:
        if str(root) not in closures:
            raise ValueError('missing root issue')
    return closures


def _accounting(record):
    value = _bound(record)
    if value.get('schema') != 'plan069-assessment-accounting/v1':
        raise ValueError('execution accounting schema')
    ledger_record = value['ledger']
    if verify_record(ledger_record) != ledger_record:
        raise ValueError('ledger bytes/path mismatch')
    events = [json.loads(line) for line in safe_path(ledger_record['path']).read_text().splitlines()]
    previous = None
    states = {}
    outcomes = []
    for index, row in enumerate(events):
        payload = {key: item for key, item in row.items() if key != 'event_sha256'}
        if row.get('sequence') != index or row.get('previous_sha256') != previous or object_hash(payload) != row.get('event_sha256'):
            raise ValueError('ledger hash-chain corruption')
        previous = row['event_sha256']
        if row.get('event') in ('reserve', 'finish', 'account', 'checkpoint', 'checkpoint_resume'):
            states[row['job_id']] = row
        if row.get('event') == 'finish':
            elapsed = row.get('elapsed_seconds')
            if type(elapsed) not in (int, float) or not math.isfinite(elapsed) or elapsed < 0:
                raise ValueError('invalid consumed attempt elapsed time')
            outcomes.append(row)
    return dict(record=record, ledger=value['ledger'], event_count=len(events),
                ledger_head=previous, attempt_outcomes=outcomes,
                active_allocations=[key for key, row in states.items() if row['event'] in ('reserve', 'checkpoint', 'checkpoint_resume')],
                resource_record=value['resources'], resource_observation=_bound(value['resources']),
                budget_authorization=value['budget_authorization'], budget_document=_bound(value['budget_authorization']))


def _verification(record, actual):
    value = _bound(record)
    if value.get('schema') != 'plan069-assessment-verification/v1':
        raise ValueError('verification evidence schema required')
    documents = {key: _bound(value[key]) for key in
                 ('tests', 'qualification', 'standards_review', 'spec_review')}
    qualification = documents['qualification']
    if qualification.get('schema') != 's1-cpu-aggregate/v2':
        raise ValueError('recognized immutable qualification receipt required')
    for key in ('tests_run', 'subtests_run', 'failures', 'errors', 'skipped'):
        if type(qualification.get(key)) is not int or qualification[key] < 0:
            raise ValueError('exact qualification counts required')
    if not qualification.get('sources_before'):
        raise ValueError('qualification source inventory required')
    for source in qualification['sources_before']:
        verify_record(source)
    for key in ('stdout', 'stderr', 'runner'):
        if key in qualification:
            verify_record(qualification[key])
    blockers = []
    if not (qualification.get('passed') is True and qualification['tests_run'] > 0 and qualification['skipped'] == 0 and qualification['failures'] == qualification['errors'] == 0 and
            qualification.get('sources_before') == qualification.get('sources_after')):
        blockers.append('qualification did not pass unchanged sources')
    for axis in ('standards', 'spec'):
        audit = documents[axis + '_review']
        if audit.get('schema') != 'plan069-assessment-code-review/v1' or audit.get('axis') != axis or audit.get('record_kind') != ('actual' if actual else 'fixture') or not isinstance(audit.get('reviewer'), str) or not audit['reviewer'].strip() or not isinstance(audit.get('blocking_findings'), list):
            raise ValueError('exact independent review result required')
        for source in audit['sources']:
            verify_record(source)
        if not audit['sources']:
            raise ValueError('reviewed source inventory required')
        if audit['blocking_findings']:
            blockers.append(axis + ' review has unresolved findings')
    tests = documents['tests']
    # Preserve the original whole-suite output, including known unrelated errors.
    # No arbitrary status string is interpreted as a passing suite.
    if not isinstance(tests, dict) or not all(type(tests.get(key)) is int and tests[key] >= 0 for key in ('tests_run', 'failures', 'errors', 'skipped')):
        raise ValueError('exact full-suite counts required')
    return dict(record=record, documents=documents, full_suite_passed=tests['failures'] == tests['errors'] == 0), blockers


def _final_review(record, decision_record, depth, actual):
    review = _review(record, actual)
    package = _bound(review['package'])
    arms = {item['id']: item for item in package['candidates'] if item.get('output_type') == 'final-render'}
    required = {'QF-B': ('M0', 'N0'), 'QF-M1': ('M1', 'N0'), 'QF-M2': ('M2', 'N0'),
                'QF-N1': ('M0', 'N1'), 'QF-N2': ('M0', 'N2')}
    if set(arms) != set(required):
        raise ValueError('exact five final-render arms required; component reviews cannot substitute')
    blockers = []
    if depth is None or decision_record is None:
        blockers.append('final-render comparison lacks ready frozen metric-depth choice')
    else:
        if package.get('bindings', {}).get('depth_decision') != decision_record:
            raise ValueError('final renders bind another depth choice')
        for key, (motion, neighbors) in required.items():
            if arms[key].get('composition') != dict(segmentation='S2', depth=depth, motion=motion, neighbors=neighbors):
                raise ValueError('final-render isolation composition changed')
    for key, arm in arms.items():
        if arm['status'] != 'available':
            blockers.append(key + ': final-render arm ' + arm['status'])
    if actual:
        # Existing package validators cover component diagnostics only. A future
        # native publication validator must establish actual QF outputs before
        # this reporter can accept them as completed experiment evidence.
        blockers.append('native final-render publication validation is not implemented')
    return dict(record=record, human_review=review, package=review['package'], arms=arms), blockers

def build_assessment(request_record, output, *, actual=True):
    """Preserve a partial evidence inventory; missing work remains blocked."""
    request = _bound(request_record)
    if request.get('schema') != SCHEMA or request.get('record_kind') not in ('actual', 'fixture'):
        raise ValueError('assessment request schema/origin')
    if actual and request['record_kind'] != 'actual':
        raise ValueError('fixture request cannot establish actual assessment')
    blockers = [] if actual else ['fixture evidence cannot establish completion']
    report = {'schema': 'plan069-qualitative-assessment/v1', 'request': request_record,
              'record_kind': request['record_kind'], 'mode': 'qualitative',
              'history': {}, 'issue_closure': {}, 'metric_depth_choice': None, 'depth_dispositions': {
                  key: {'status': 'missing', 'reason': 'extended package not provided'} for key in DEPTH}}
    for name in HISTORY:
        if not request.get('history', {}).get(name):
            blockers.append('missing historical ' + name + ' observation')
        else:
            record = request['history'][name]
            document = _bound(record)
            review = _supplement(record, actual) if name == 'supplemental_d2' and document.get('schema') == 'plan067-human-observation-supplement/v1' else _review(record, actual)
            required = {'segmentation': 'S2', 'depth': 'D4', 'supplemental_d2': 'D2'}[name]
            if required not in review['candidate_ids']:
                raise ValueError('wrong historical review role: ' + name)
            report['history'][name] = {'record': record, 'human_review': review, 'scope': 'historical component observation; not current metric-depth selection'}
    for field, reason in [('depth_review', 'missing extended-depth human review'),
                          ('depth_decision', 'missing frozen metric-depth choice'),
                          ('final_review', 'missing final-render human review'),
                          ('execution_accounting', 'missing execution/resource accounting'),
                          ('verification', 'missing tests/qualification/independent reviews'),
                          ('issue_snapshot', 'missing recursive issue snapshot')]:
        if not request.get(field):
            blockers.append(reason)
    if request.get('depth_review'):
        review = _review(request['depth_review'], actual, extended=True)
        report['depth_review'] = dict(record=request['depth_review'], human_review=review)
        package = _bound(review['package'])
        aggregate = _bound(package['bindings']['depth_aggregate_request'])
        slots = aggregate['candidates']
        if set(slots) != set(DEPTH):
            raise ValueError('all D0–D11 dispositions required')
        for name, slot in slots.items():
            if slot.get('status') not in ('available', 'failed', 'blocked', 'unavailable', 'missing') or not isinstance(slot.get('reason'), str):
                raise ValueError('invalid depth disposition')
            report['depth_dispositions'][name] = dict(slot, evidence_documents={key: _bound(record) for key, record in slot.get('evidence', {}).items()})
        if any(slot['status'] == 'missing' for slot in slots.values()):
            blockers.append('extended depth has unresolved generation dispositions')
    if request.get('depth_decision'):
        from .depth_review import validate_decision
        decision = validate_decision(request['depth_decision'], actual=actual)
        if not request.get('depth_review') or decision['review'] != request['depth_review']:
            raise ValueError('depth decision belongs to another review')
        report['depth_decision'] = dict(record=request['depth_decision'], decision=decision)
        if decision['status'] != 'ready':
            blockers.append('frozen metric-depth choice is blocked')
        else:
            report['metric_depth_choice'] = decision['selected_candidate_ids'][0]
    if request.get('final_review'):
        report['final_review'], final_blockers = _final_review(request['final_review'], request.get('depth_decision'), report['metric_depth_choice'], actual)
        blockers.extend(final_blockers)
    if request.get('verification'):
        report['verification'], verification_blockers = _verification(request['verification'], actual)
        blockers.extend(verification_blockers)
    if request.get('execution_accounting'):

        report['execution_accounting'] = _accounting(request['execution_accounting'])
        if report['execution_accounting']['active_allocations']:
            blockers.append('active allocations remain in accounting snapshot')
    if request.get('issue_snapshot'):
        snapshot = _bound(request['issue_snapshot'])
        report['issue_snapshot'] = {'record': request['issue_snapshot'], 'snapshot': snapshot}
        report['issue_closure'] = _closure(snapshot)
        preparation = {str(issue): snapshot['issues'].get(str(issue), {'state': 'MISSING'})
                       for issue in range(4, 18)}
        unfinished_preparation = [int(issue) for issue, item in preparation.items()
                                  if item['state'] != 'CLOSED']
        report['historical_preparation_dependencies'] = dict(
            scope='Historical referenced preparation dependencies; not synthetic native child edges',
            issues=preparation, unfinished=unfinished_preparation)
        if unfinished_preparation:
            blockers.append('unfinished historical preparation dependencies: ' +
                            ', '.join(map(str, unfinished_preparation)))
        pending = [issue for issue in (34, 44, 45, 60, 61, 62) if snapshot['issues'][str(issue)]['state'] != 'CLOSED' or not report['issue_closure'][str(issue)]['all_descendants_closed']]
        if pending:
            blockers.append('unfinished required issues: ' + ', '.join(map(str, pending)))
    report.update(status='blocked' if blockers else 'complete', blockers=blockers,
                  completion_established=not blockers,
                  parent_closure_eligible=not blockers and bool(report['issue_closure']) and all(report['issue_closure'][str(root)]['all_descendants_closed'] for root in (3, 18, 23)),
                  measured_accuracy=False, physical_depth_accuracy='unverified',
                  commercial_stack_clearance='unverified')
    write_json(output, report)
    return report


def render_markdown(report):
    """Render saved observations without selecting winners or inventing metrics."""
    def cell(value):
        return str(value).replace('|', r'\|').replace('\n', ' ')
    def record_link(record):
        return '[bound evidence](<' + record['path'] + '>)'
    lines = ['# Final qualitative benchmark assessment', '',
             '**Status: ' + report['status'] + '**', '',
             'Human observations concern only their bound outputs and named examples.',
             'Physical depth accuracy: unverified.',
             'Full reconstruction stack commercial clearance: unverified.',
             'Component commercial permission does not establish full-stack clearance.',
             'No annotation accuracy, statistical significance or unseen final-render quality is inferred.', '',
             '## Remaining requirements', '']
    lines.extend('- ' + cell(item) for item in report['blockers'])
    for section, title in [('history', 'Historical component observations')]:
        lines.extend(['', '## ' + title, ''])
        for role, item in report[section].items():
            review = item['human_review']
            reviewer = review['reviewer']
            lines.extend(['### ' + role, '', record_link(item['record']), '',
                          'Reviewer: ' + cell(reviewer['name']) + '; ' + cell(reviewer['reviewed_at']), '',
                          item['scope'], ''])
            if 'observation' in review:
                lines.extend([review['observation'], '', 'Examples: ' + cell(json.dumps(review['examples']))])
            else:
                _review_markdown(lines, review, cell)
    lines.extend(['', '## Extended depth generation dispositions', '',
                  '| Candidate | Disposition | Reason | Evidence |',
                  '| --- | --- | --- | --- |'])
    for key, slot in report['depth_dispositions'].items():
        evidence = ', '.join(name + ': ' + record_link(record) for name, record in slot.get('evidence', {}).items())
        lines.append('| ' + ' | '.join(map(cell, (key, slot['status'], slot['reason'], evidence))) + ' |')
    if 'depth_review' in report:
        lines.extend(['', '## New depth visual preference and metric choice', '',
                      record_link(report['depth_review']['record']), ''])
        _review_markdown(lines, report['depth_review']['human_review'], cell)
    lines.extend(['', 'Frozen eligible metric D*: ' + (report['metric_depth_choice'] or 'not established'), ''])
    if 'final_review' in report:
        lines.extend(['## Final renders: motion and neighbor effects', '',
                      record_link(report['final_review']['record']), ''])
        _review_markdown(lines, report['final_review']['human_review'], cell)
        for key, arm in report['final_review']['arms'].items():
            lines.append('- ' + key + ': ' + cell(arm['status']) + '; ' + cell(arm.get('reason', '')))
    else:
        lines.extend(['## Final renders: motion and neighbor effects', '',
                      'Missing actual five-arm matched final renders and their human review.', ''])
    if 'execution_accounting' in report:
        accounting = report['execution_accounting']
        lines.extend(['## Execution and resource accounting', '',
                      record_link(accounting['record']), '',
                      'Preserved ledger events: ' + str(accounting['event_count']), '',
                      '| Attempt | Status | Consumed seconds | Cleanup |',
                      '| --- | --- | --- | --- |'])
        for item in accounting['attempt_outcomes']:
            lines.append('| ' + ' | '.join(map(cell, (item['job_id'], item['status'], item['elapsed_seconds'], item.get('cleanup_confirmed', 'not supplied')))) + ' |')
        lines.extend(['', 'Resource observation: ' + record_link(accounting['resource_record']),
                      '', 'Budget authorization: ' + record_link(accounting['budget_authorization'])])
    if 'verification' in report:
        lines.extend(['', '## Tests, qualification and independent review', '',
                      record_link(report['verification']['record']), ''])
        for key, document in report['verification']['documents'].items():
            counts = {name: document[name] for name in ('tests_run', 'subtests_run', 'failures', 'errors', 'skipped', 'passed', 'blocking_findings') if name in document}
            lines.append('- ' + key + ': ' + cell(json.dumps(counts)))
        lines.extend(['', 'Full suite passed: ' + str(report['verification']['full_suite_passed'])])
    lines.extend(['', '## Recursive issue completion snapshot', '',
                  'This saved snapshot does not close issues or prove current GitHub state.', ''])
    if 'historical_preparation_dependencies' in report:
        preparation = report['historical_preparation_dependencies']
        lines.extend(['Historical preparation references #4–17 are separate from the native child graph.',
                      'Unfinished historical preparation references: ' +
                      (', '.join('#' + str(issue) for issue in preparation['unfinished']) or 'none'), ''])
    for key, closure in report['issue_closure'].items():
        if closure['unfinished_descendants']:
            lines.append('- #' + key + ': unfinished descendants ' + ', '.join('#' + str(item) for item in closure['unfinished_descendants']))
    return '\n'.join(lines) + '\n'


def _review_markdown(lines, review, cell):
    lines.extend(['| Criterion | Human observation | Preference | Named examples |',
                  '| --- | --- | --- | --- |'])
    for key, value in review['criteria'].items():
        lines.append('| ' + ' | '.join(map(cell, (key, value['observation'],
            json.dumps(value['preference']), json.dumps(value['examples'])))) + ' |')
    lines.extend(['', 'Tradeoffs: ' + review['tradeoffs'], ''])
    if 'metric_choice' in review:
        lines.extend(['Separate metric choice: ' + cell(json.dumps(review['metric_choice'])), ''])


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--fixture', action='store_true')
    args = parser.parse_args()
    from .files import file_record
    report = build_assessment(file_record(args.request), args.output, actual=not args.fixture)
    print(render_markdown(report), end='')


if __name__ == '__main__':
    main()
