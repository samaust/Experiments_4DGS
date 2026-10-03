"""Public assessment seam: fixtures never establish experiment completion."""
import tempfile
import unittest
from pathlib import Path

from vipe_benchmark.files import file_record, write_json, object_hash
from vipe_benchmark.qualitative_assessment import build_assessment, render_markdown


class AssessmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.request = {'schema': 'plan069-qualitative-assessment-request/v1',
                        'record_kind': 'fixture', 'history': {},
                        'depth_review': None, 'depth_decision': None,
                        'final_review': None, 'execution_accounting': None,
                        'verification': None, 'issue_snapshot': None}

    def put(self, name, document):
        path = self.root / name
        write_json(path, document)
        return file_record(path)

    def test_absent_evidence_is_explicitly_blocked_and_fixture_never_complete(self):
        report = build_assessment(self.put('request.json', self.request),
                                  self.root / 'report.json', actual=False)
        self.assertEqual(report['status'], 'blocked')
        self.assertFalse(report['completion_established'])
        self.assertFalse(report['parent_closure_eligible'])
        self.assertIn('fixture evidence cannot establish completion', report['blockers'])
        self.assertIn('missing final-render human review', report['blockers'])
        self.assertEqual(set(report['depth_dispositions']), {f'D{i}' for i in range(12)})
        self.assertEqual(report['depth_dispositions']['D11']['status'], 'missing')

    def review(self, prefix, candidate):
        package = {'schema': 'plan067-qualitative-package/v1', 'id': prefix,
                   'record_kind': 'fixture', 'mode': 'qualitative',
                   'candidates': [{'id': candidate, 'status': 'available', 'media': [
                       {'selection_id': 'camera1-selection-175', 'kind': 'frame',
                        'frame_ids': [175], 'timestamps': [7.0]}]}],
                   'selections': []}
        record = self.put(prefix + '-package.json', package)
        criteria = {}
        for key in ('frozen_frame', 'motion', 'artifacts', 'sharpness', 'overall'):
            criteria[key] = {'observation': 'Original fixture observation',
                             'preference': {'outcome': 'preferred', 'candidate_ids': [candidate]},
                             'examples': [{'candidate_id': candidate,
                                           'selection_id': 'camera1-selection-175', 'frame_id': 175}]}
        criteria['motion'].update(preference={'outcome': 'not_applicable', 'candidate_ids': []}, examples=[])
        return self.put(prefix + '-review.json', {
            'schema': 'plan067-qualitative-review/v1', 'record_kind': 'fixture',
            'reviewer': {'name': 'fixture reviewer', 'reviewed_at': '2026-09-30'},
            'package': record, 'candidate_ids': [candidate], 'criteria': criteria,
            'tradeoffs': 'Original fixture tradeoff'})

    def test_historical_observations_preserved_separately_without_current_choice(self):
        self.request['history'] = {name: self.review(name, candidate) for name, candidate in
                                   [('segmentation', 'S2'), ('depth', 'D4'), ('supplemental_d2', 'D2')]}
        report = build_assessment(self.put('request.json', self.request), self.root / 'report.json', actual=False)
        self.assertEqual(report['history']['depth']['human_review']['criteria']['overall']['preference']['candidate_ids'], ['D4'])
        self.assertEqual(report['history']['supplemental_d2']['human_review']['candidate_ids'], ['D2'])
        self.assertIsNone(report['metric_depth_choice'])
        self.assertIn('missing frozen metric-depth choice', report['blockers'])

    def snapshot(self):
        issues = {str(i): {'state': 'CLOSED', 'children': []} for i in
                  (*range(3, 24), 34, 35, 44, 45, 56, 57, 58, 59, 60, 61, 62)}
        for parent, children in [(3, list(range(4, 18))), (18, [19, 20, 21, 22, 23, 44]), (23, [34, 35, 45]),
                                 (44, [56, 57, 58, 59]), (45, [60, 61, 62])]:
            issues[str(parent)]['children'] = children
        return {'schema': 'plan069-issue-snapshot/v1', 'repository': 'samaust/Experiments_4DGS',
                'captured_at': '2026-10-03T12:00:00Z', 'issues': issues,
                'roots': [3, 18, 23]}

    def test_recursive_open_child_blocks_parent_closure_even_if_parent_closed(self):
        snapshot = self.snapshot()
        snapshot['issues']['58']['state'] = 'OPEN'
        self.request['issue_snapshot'] = self.put('issues.json', snapshot)
        report = build_assessment(self.put('request.json', self.request), self.root / 'report.json', actual=False)
        self.assertFalse(report['issue_closure']['18']['all_descendants_closed'])
        self.assertIn(58, report['issue_closure']['18']['unfinished_descendants'])
        self.assertFalse(report['parent_closure_eligible'])

    def test_cycle_or_omitted_dependency_is_rejected(self):
        for defect in ('cycle', 'omitted'):
            snapshot = self.snapshot()
            if defect == 'cycle': snapshot['issues']['58']['children'] = [44]
            else: snapshot['issues']['45']['children'].remove(62)
            self.request['issue_snapshot'] = self.put(defect + '-issues.json', snapshot)
            with self.subTest(defect=defect), self.assertRaises(ValueError):
                build_assessment(self.put(defect + '-request.json', self.request), self.root / (defect + '-report.json'), actual=False)

    def test_accounting_keeps_failed_consumption_and_rejects_hash_chain_tampering(self):
        rows = []
        for fields in ({'event': 'reserve', 'job_id': 'failed-run'},
                       {'event': 'finish', 'job_id': 'failed-run', 'status': 'failed',
                        'elapsed_seconds': 123.5, 'cleanup_confirmed': True}):
            row = dict(fields, sequence=len(rows), previous_sha256=rows[-1]['event_sha256'] if rows else None)
            row['event_sha256'] = object_hash(row)
            rows.append(row)
        ledger = self.root / 'ledger.jsonl'
        import json
        ledger.write_text(''.join(json.dumps(row) + '\n' for row in rows))
        resources = self.put('resources.json', {'artifact_disk_allocated_bytes': 1000, 'download_bytes': 500})
        self.request['execution_accounting'] = self.put('accounting.json', {
            'schema': 'plan069-assessment-accounting/v1', 'ledger': file_record(ledger),
            'resources': resources, 'budget_authorization': self.put('caps.json', {'artifact_cap_bytes': 2000})})
        report = build_assessment(self.put('request.json', self.request), self.root / 'report.json', actual=False)
        self.assertEqual(report['execution_accounting']['attempt_outcomes'][0]['elapsed_seconds'], 123.5)
        self.assertEqual(report['execution_accounting']['attempt_outcomes'][0]['status'], 'failed')
        self.assertEqual(report['execution_accounting']['resource_observation']['artifact_disk_allocated_bytes'], 1000)
        ledger.write_text('{}\n')
        with self.assertRaises(ValueError):
            build_assessment(file_record(self.root / 'request.json'), self.root / 'changed-report.json', actual=False)

    def test_relative_visual_preference_does_not_become_metric_choice(self):
        from vipe_benchmark import depth_review
        evidence = self.put('d11-evidence.json', {'variant': 'Log-stage2', 'commercial': 'allowed',
                                                'scale': 'relative log', 'resource': 'retained fixture observation'})
        slots = {name: {'status': 'missing', 'reason': 'not yet generated', 'evidence': {}} for name in (f'D{i}' for i in range(12))}
        slots['D11'] = {'status': 'available', 'reason': 'fixture visual result', 'evidence': {'commercial': evidence}}
        aggregate = self.put('aggregate.json', {'candidates': slots})
        package = {'schema': 'plan067-qualitative-package/v1', 'id': 'extended-fixture',
                   'record_kind': 'fixture', 'mode': 'qualitative',
                   'bindings': {'depth_aggregate_request': aggregate},
                   'candidates': [{'id': name, 'status': slots[name]['status'], 'reason': slots[name]['reason'],
                                   'media': [{'selection_id': 'camera1-selection-175', 'kind': 'frame',
                                              'frame_ids': [175], 'timestamps': [7.0]}] if name == 'D11' else []}
                                  for name in slots]}
        package_record = self.put('extended-package.json', package)
        form = depth_review.blank_review(package_record)
        form.update(record_kind='fixture', reviewer={'name': 'fixture reviewer', 'reviewed_at': '2026-10-03'}, tradeoffs='Visual appearance alone does not establish metric scale.')
        for criterion in form['criteria'].values():
            criterion.update(observation='Not applicable for fixture.', preference={'outcome': 'not_applicable', 'candidate_ids': []})
        form['criteria']['overall'].update(observation='D11 looks best in fixture.',
            preference={'outcome': 'preferred', 'candidate_ids': ['D11']},
            examples=[{'candidate_id': 'D11', 'selection_id': 'camera1-selection-175', 'frame_id': 175}])
        form['metric_choice'].update(reason='No eligible metric result yet.')
        self.request['depth_review'] = self.put('extended-review.json', form)
        depth_review.freeze_decision(self.request['depth_review'], self.root / 'depth-decision.json', actual=False)
        self.request['depth_decision'] = file_record(self.root / 'depth-decision.json')
        report = build_assessment(self.put('request.json', self.request), self.root / 'report.json', actual=False)
        self.assertEqual(report['depth_review']['human_review']['criteria']['overall']['preference']['candidate_ids'], ['D11'])
        self.assertEqual(report['depth_dispositions']['D11']['evidence_documents']['commercial']['variant'], 'Log-stage2')
        self.assertIsNone(report['metric_depth_choice'])
        self.assertIn('frozen metric-depth choice is blocked', report['blockers'])

    def test_component_review_cannot_establish_final_render_comparison(self):
        self.request['final_review'] = self.review('component', 'S2')
        with self.assertRaisesRegex(ValueError, 'five final-render arms'):
            build_assessment(self.put('request.json', self.request), self.root / 'report.json', actual=False)

    def test_arbitrary_verification_assertions_cannot_establish_a_pass(self):
        self.request['verification'] = self.put('verification.json', {'status': 'passed'})
        with self.assertRaises(ValueError):
            build_assessment(self.put('request.json', self.request), self.root / 'report.json', actual=False)

    def test_supplement_preserves_original_observation_without_invented_criteria(self):
        record = self.review('d2-component', 'D2')
        from vipe_benchmark.files import read_json
        review = read_json(record['path'])
        previous = self.put('previous-observation.json', {
            'schema': 'plan067-human-observation-supplement/v1', 'record_kind': 'fixture',
            'reviewer': review['reviewer'], 'package': review['package'],
            'candidate_ids': ['D2'], 'observation': 'D2 has worse edges than D0/D1 and misses a far player.'})
        supplement = self.put('confirmed-observation.json', dict(read_json(previous['path']),
            previous_observation=previous,
            examples=[{'candidate_id': 'D2', 'selection_id': 'camera1-selection-175', 'frame_id': 175}],
            selection_confirmation='camera1-selection-175'))
        self.request['history']['supplemental_d2'] = supplement
        report = build_assessment(self.put('request.json', self.request), self.root / 'report.json', actual=False)
        preserved = report['history']['supplemental_d2']['human_review']
        self.assertEqual(preserved['observation'], 'D2 has worse edges than D0/D1 and misses a far player.')
        self.assertNotIn('criteria', preserved)
        self.assertIsNone(report['metric_depth_choice'])

    def test_markdown_names_original_examples_blockers_and_claim_limits(self):
        self.request['history']['depth'] = self.review('depth', 'D4')
        report = build_assessment(self.put('request.json', self.request), self.root / 'report.json', actual=False)
        text = render_markdown(report)
        self.assertIn('camera1-selection-175', text)
        self.assertIn('Original fixture observation', text)
        self.assertIn('missing final-render human review', text)
        self.assertIn('Physical depth accuracy: unverified', text)
        self.assertIn('Full reconstruction stack commercial clearance: unverified', text)
        with self.assertRaises(FileExistsError):
            build_assessment(file_record(self.root / 'request.json'), self.root / 'report.json', actual=False)

    def test_zero_test_qualification_is_not_a_passing_receipt(self):
        source = self.put('source.json', {'fixture': 'source'})
        qualification = self.put('qualification.json', {
            'schema': 's1-cpu-aggregate/v2', 'tests_run': 0, 'subtests_run': 0,
            'failures': 0, 'errors': 0, 'skipped': 0, 'passed': True,
            'sources_before': [source], 'sources_after': [source]})
        audits = {axis: self.put(axis + '-review.json', {
            'schema': 'plan069-assessment-code-review/v1', 'axis': axis,
            'record_kind': 'fixture', 'reviewer': 'independent fixture reviewer',
            'sources': [source], 'blocking_findings': []}) for axis in ('standards', 'spec')}
        tests = self.put('tests.json', {'tests_run': 10, 'failures': 0, 'errors': 1, 'skipped': 0})
        self.request['verification'] = self.put('verification.json', {
            'schema': 'plan069-assessment-verification/v1', 'tests': tests,
            'qualification': qualification, 'standards_review': audits['standards'],
            'spec_review': audits['spec']})
        report = build_assessment(self.put('request.json', self.request), self.root / 'report.json', actual=False)
        self.assertFalse(report['verification']['full_suite_passed'])
        self.assertIn('qualification did not pass unchanged sources', report['blockers'])
