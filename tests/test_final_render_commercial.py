"""Whole-stack licence gate: full commercial permission or a recorded research-use decision."""
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))

from vipe_benchmark.files import file_record, write_json
from vipe_benchmark.final_render_commercial import validate_commercial

PERMISSIONS = ('code', 'weights', 'dependencies', 'inference_outputs')


class CommercialGateTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        license_text = self.root/'LICENSE.txt'
        license_text.write_text('Non-commercial academic research use only.\n')
        self.primary = [file_record(license_text)]
        self.runtime = self.record('runtime', dict(schema='runtime'))
        self.sources = [self.record('source', dict(schema='source'))]

    def record(self, name, payload):
        path = self.root/f'{name}-{len(list(self.root.iterdir()))}.json'
        write_json(path, payload)
        return file_record(path)

    def research_decision(self, **overrides):
        decision = dict(schema='plan069-final-render-research-use-decision/v1', record_kind='human',
            status='approved', decision='research_use', reviewer='samaust', approved_at='2026-10-05',
            commercial_clearance=False, runtime=self.runtime)
        decision.update(overrides)
        return self.record('decision', decision)

    def assessment(self, **overrides):
        assessment = dict(schema='plan069-final-render-commercial-assessment/v1', record_kind='actual',
            status='research_use', runtime=self.runtime, source_files=self.sources, reviewer='independent reviewer',
            permissions=dict(code='research_only', weights='unverified', dependencies='allowed',
                             inference_outputs='research_only'),
            research_use=self.research_decision(), commercial_clearance=False, primary_sources=self.primary)
        assessment.update(overrides)
        return self.record('assessment', assessment)

    def test_fully_allowed_assessment_is_accepted_without_research_decision(self):
        record = self.record('allowed', dict(schema='plan069-final-render-commercial-assessment/v1',
            record_kind='actual', status='allowed', runtime=self.runtime, source_files=self.sources,
            reviewer='reviewer', permissions=dict.fromkeys(PERMISSIONS, 'allowed'), primary_sources=self.primary))
        self.assertEqual(validate_commercial(record, self.runtime, self.sources)['status'], 'allowed')

    def test_research_use_assessment_bound_to_human_decision_is_accepted(self):
        result = validate_commercial(self.assessment(), self.runtime, self.sources)
        self.assertEqual(result['status'], 'research_use')
        self.assertIs(result['commercial_clearance'], False)

    def test_research_use_requires_an_approved_human_decision(self):
        for decision in (self.research_decision(record_kind='fixture'), self.research_decision(status='pending'),
                         self.research_decision(reviewer=' '), self.research_decision(commercial_clearance=True),
                         self.research_decision(decision='commercial'),
                         self.research_decision(runtime=self.record('other-stack', dict(schema='other')))):
            with self.subTest(decision=decision), self.assertRaisesRegex(ValueError, 'research-use decision'):
                validate_commercial(self.assessment(research_use=decision), self.runtime, self.sources)

    def test_research_use_cannot_claim_commercial_clearance(self):
        with self.assertRaisesRegex(ValueError, 'commercial clearance'):
            validate_commercial(self.assessment(commercial_clearance=True), self.runtime, self.sources)

    def test_prohibited_or_missing_permission_is_rejected(self):
        for permissions in (dict(code='prohibited', weights='allowed', dependencies='allowed', inference_outputs='allowed'),
                            dict(code='research_only', weights='allowed', dependencies='allowed')):
            with self.subTest(permissions=permissions), self.assertRaisesRegex(ValueError, 'permissions'):
                validate_commercial(self.assessment(permissions=permissions), self.runtime, self.sources)

    def test_allowed_status_requires_every_permission_allowed(self):
        record = self.assessment(status='allowed')
        with self.assertRaisesRegex(ValueError, 'permissions'):
            validate_commercial(record, self.runtime, self.sources)

    def test_assessment_must_bind_exact_runtime_sources_and_primary_bytes(self):
        other = self.record('other-runtime', dict(schema='other'))
        with self.assertRaisesRegex(ValueError, 'runtime/sources'):
            validate_commercial(self.assessment(), other, self.sources)
        record = self.assessment()
        (self.root/'LICENSE.txt').write_text('changed\n')
        with self.assertRaisesRegex(ValueError, 'changed'):
            validate_commercial(record, self.runtime, self.sources)


if __name__ == '__main__':
    unittest.main()
