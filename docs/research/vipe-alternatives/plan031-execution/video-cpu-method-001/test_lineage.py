"""CPU fixtures at the completed metric-video review boundary; no model loads."""
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[5]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'tests')]
import test_vipe_benchmark_depth_review as fixtures
from vipe_benchmark.depth_review import _completed_qualification
from vipe_benchmark.files import read_json


class VideoLineageTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.DepthReviewTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        f = self.fixture
        f.completed_fixture()
        self.slot = copy.deepcopy(f.slots['D5'])
        runtime = read_json(self.slot['evidence']['runtime']['path'])
        runtime['candidate'] = 'D10'
        self.slot['evidence']['runtime'] = f.record(runtime)
        old_request = read_json(self.slot['provenance']['configuration']['path'])
        review = read_json(old_request['source_review']['path'])
        review['candidate'] = 'D10'
        self.review = f.record(review)
        qualification = read_json(old_request['qualification']['path'])
        qualification.update(candidate='D10', runtime={'receipt':self.slot['evidence']['runtime']},source_review=self.review)
        self.qualification = f.record(qualification)
        admission = read_json(old_request['admission']['path'])
        admission.update(candidate='D10',runtime=qualification['runtime'],source_review=self.review,qualification=self.qualification)
        self.admission = f.record(admission)
        generation = read_json(self.slot['evidence']['generation']['path'])
        generation.update(candidate='D10',job_id='fixture-D10')
        self.generation = generation
        self.slot['evidence']['generation'] = f.record(generation)
        request = dict(old_request,candidate='D10',job_id='fixture-D10',admission=self.admission,source_review=self.review,qualification=self.qualification)
        self.slot['provenance']['configuration'] = f.record(request)
        self.slot['provenance']['ledger_outcome'] = f.record(dict(event='finish',status='complete',job_id='fixture-D10',result=self.slot['evidence']['generation']))

    def proof(self):
        return _completed_qualification('D10',self.slot,self.generation,False)

    def test_exact_completed_metric_video_lineage(self):
        self.assertEqual(self.proof()['qualification'], self.qualification)

    def test_runtime_receipt_fallback_is_not_full_qualification(self):
        f = self.fixture
        request = read_json(self.slot['provenance']['configuration']['path'])
        request['qualification'] = self.slot['evidence']['runtime']
        self.slot['provenance']['configuration'] = f.record(request)
        self.assertIsNone(self.proof())

    def test_missing_or_changed_native_lineage_rejects(self):
        original = copy.deepcopy(self.slot)
        for where in ('runtime','qualification','source_review'):
            for key in ('source_archive','source_files'):
                for action in ('omit','change'):
                    with self.subTest(where=where,key=key,action=action):
                        self.slot = copy.deepcopy(original)
                        f = self.fixture
                        request = read_json(self.slot['provenance']['configuration']['path'])
                        rec = self.slot['evidence']['runtime'] if where == 'runtime' else request[where]
                        doc = read_json(rec['path'])
                        if action == 'omit': doc.pop(key)
                        else: doc[key] = [] if key == 'source_files' else f.record({'wrong':'archive'})
                        changed = f.record(doc)
                        if where == 'runtime': self.slot['evidence']['runtime'] = changed
                        else:
                            request[where] = changed
                            # Match admission binding so the native-lineage comparison is exercised.
                            admission = read_json(request['admission']['path'])
                            admission[where] = changed
                            request['admission'] = f.record(admission)
                            if where == 'source_review':
                                q = read_json(request['qualification']['path'])
                                q['source_review'] = changed
                                request['qualification'] = f.record(q)
                                admission['qualification'] = request['qualification']
                                request['admission'] = f.record(admission)
                            self.slot['provenance']['configuration'] = f.record(request)
                        self.assertIsNone(self.proof())

if __name__ == '__main__': unittest.main()
