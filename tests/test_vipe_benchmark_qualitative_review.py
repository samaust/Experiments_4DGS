"""CPU tests of immutable review and decision seams; judgments are fixtures."""
import copy
import tempfile
import unittest
from pathlib import Path
from vipe_benchmark.files import file_record, write_json
from vipe_benchmark import qualitative_review as review


class QualitativeReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.package = {'schema': 'plan067-qualitative-package/v1', 'record_kind':'fixture',
            'id':'p1', 'mode':'qualitative', 'candidates':[
                {'id':'a','status':'available','reason':'','media':[{'selection_id':'f','kind':'frame','frame_ids':[150],'timestamps':[6.0]}, {'selection_id':'c','kind':'clip','frame_ids':[150,151],'timestamps':[6.0,6.04]}]},
                {'id':'b','status':'available','reason':'','media':[{'selection_id':'f','kind':'frame','frame_ids':[150],'timestamps':[6.0]}]},
                {'id':'missing','status':'failed','reason':'runtime failure','media':[]}],
            'selections':[{'id':'f','kind':'frame','frame_ids':[150],'timestamps':[6.0]}, {'id':'c','kind':'clip','frame_ids':[150,151],'timestamps':[6.0,6.04]}]}
        write_json(self.root/'package.json', self.package)
        self.record = file_record(self.root/'package.json')
        self.form = review.blank_review(self.record)
        self.form.update(record_kind='fixture', reviewer={'name':'CPU fixture','reviewed_at':'2026-09-29'}, tradeoffs='Fixture tradeoff')
        for value in self.form['criteria'].values():
            value.update(observation='Fixture observation', examples=[{'candidate_id':'a','selection_id':'f','frame_id':150},{'candidate_id':'b','selection_id':'f','frame_id':150}], preference={'outcome':'tie','candidate_ids':['a','b']})

        self.form['criteria']['motion'].update(preference={'outcome':'unjudgeable','candidate_ids':[]}, examples=[])

    def validate(self, value=None):
        return review.validate_review(self.form if value is None else value, actual=False)

    def test_fixture_valid_but_not_actual(self):
        self.validate()
        with self.assertRaises(ValueError): review.validate_review(self.form)

    def test_blank_form_not_review(self):
        with self.assertRaises(ValueError): self.validate(review.blank_review(self.record))

    def test_changed_package_and_unknown_references(self):
        for mutation in [lambda f:f['candidate_ids'].append('x'), lambda f:f['criteria']['frozen_frame']['examples'][0].update(frame_id=151), lambda f:f['criteria']['artifacts']['examples'][0].update(candidate_id='missing'), lambda f:f['criteria']['sharpness']['preference'].update(candidate_ids=['a'])]:
            form=copy.deepcopy(self.form); mutation(form)
            with self.subTest(form=form), self.assertRaises(ValueError): self.validate(form)
        (self.root/'package.json').write_text('{}')
        with self.assertRaises(ValueError): self.validate()

    def test_motion_requires_clip_for_preference(self):
        self.form['criteria']['motion']['preference']={'outcome':'preferred','candidate_ids':['a']}
        with self.assertRaises(ValueError): self.validate()
        self.form['criteria']['motion']['examples']=[{'candidate_id':'a','selection_id':'c','start_time':6.0,'end_time':6.04}]
        self.validate()
        self.form['criteria']['motion']['examples'][0]['end_time']=6.1
        with self.assertRaises(ValueError): self.validate()

    def test_unjudgeable_and_not_applicable_with_reasons(self):
        self.form['criteria']['motion'].update(preference={'outcome':'unjudgeable','candidate_ids':[]}, examples=[])
        self.form['criteria']['sharpness'].update(preference={'outcome':'not_applicable','candidate_ids':[]}, examples=[])
        self.validate()

    def test_immutable_import_and_tie_blocks_choice(self):
        write_json(self.root/'submission.json',self.form)
        imported=review.import_review(self.record, file_record(self.root/'submission.json'), self.root/'review.json', actual=False)
        with self.assertRaises(FileExistsError): review.import_review(self.record, file_record(self.root/'submission.json'), self.root/'review.json', actual=False)
        eligibility={'a':{'eligible':True,'reason':'gates passed'},'b':{'eligible':True,'reason':'gates passed'},'missing':{'eligible':False,'reason':'failed'}}
        decision=review.freeze_decision(imported,eligibility,self.root/'decision.json',actual=False)
        self.assertEqual(decision['status'],'blocked')
        self.assertEqual(decision['selected_candidate_ids'],[])

    def test_human_choice_and_engineering_eligibility(self):
        write_json(self.root/'review.json',self.form)
        record=file_record(self.root/'review.json')
        eligibility={'a':{'eligible':False,'reason':'scale failure'},'b':{'eligible':True,'reason':'passed'},'missing':{'eligible':False,'reason':'failed'}}
        choice={'candidate_ids':['a'],'reason':'Explicit fixture choice','reviewer':self.form['reviewer']}
        decision=review.freeze_decision(record,eligibility,self.root/'decision.json',choice=choice,actual=False)
        self.assertEqual(decision['status'],'blocked')
        self.assertIn('ineligible',decision['reason'])
        choice['candidate_ids']=['b']
        decision=review.freeze_decision(record,eligibility,self.root/'decision2.json',choice=choice,actual=False)
        self.assertEqual(decision['status'],'ready')
        report=review.build_report(record,file_record(self.root/'decision2.json'),self.root/'report.json',actual=False)
        self.assertEqual(report['human_review'],self.form)
        self.assertEqual(report['unavailable_candidates'][0]['id'],'missing')
        self.assertFalse(report['measured_accuracy'])

    def test_changed_media_and_invalid_reviewer(self):
        media=self.root/'frame.png'; media.write_bytes(b'fixture media')
        self.package['candidates'][0]['media'][0]['record']=file_record(media)
        write_json(self.root/'package2.json',self.package)
        self.form['package']=file_record(self.root/'package2.json')
        self.validate()
        media.write_bytes(b'changed media')
        with self.assertRaises(ValueError): self.validate()
        self.form['package']=self.record
        for reviewer in ({'name':'','reviewed_at':'2026-09-29'}, {'name':'person','reviewed_at':'yesterday'}):
            self.form['reviewer']=reviewer
            with self.assertRaises(ValueError): self.validate()

    def test_fixture_package_cannot_be_labeled_as_actual_review(self):
        self.form['record_kind']='human'
        with self.assertRaisesRegex(ValueError, 'fixture package'): review.validate_review(self.form)

    def test_sparse_sequences_are_not_motion_evidence(self):
        self.package['candidates'][0]['media'][1]['kind']='sequence'
        write_json(self.root/'sparse.json',self.package)
        self.form['package']=file_record(self.root/'sparse.json')
        self.form['criteria']['motion'].update(preference={'outcome':'preferred','candidate_ids':['a']}, examples=[{'candidate_id':'a','selection_id':'c','start_time':6.0,'end_time':6.04}])
        with self.assertRaises(ValueError): self.validate()

    def test_report_rejects_automatic_tie_winner_and_changed_import(self):
        write_json(self.root/'submission.json',self.form)
        imported=review.import_review(self.record,file_record(self.root/'submission.json'),self.root/'imported.json',actual=False)
        eligibility={key:{'eligible':True,'reason':'fixture gates'} for key in self.form['candidate_ids']}
        decision=review.freeze_decision(imported,eligibility,self.root/'decision.json',actual=False)
        decision.update(status='ready',selected_candidate_ids=['a'])
        write_json(self.root/'forged.json',decision)
        with self.assertRaises(ValueError): review.build_report(imported,file_record(self.root/'forged.json'),self.root/'report.json',actual=False)
        (self.root/'submission.json').write_text('{}')
        with self.assertRaises(ValueError): review.freeze_decision(imported,eligibility,self.root/'changed.json',actual=False)

if __name__ == '__main__': unittest.main()
