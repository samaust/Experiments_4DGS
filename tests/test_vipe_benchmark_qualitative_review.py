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

    def test_motion_tie_needs_clip_example_for_each_selected_candidate(self):
        self.package['candidates'][1]['media'].append(copy.deepcopy(self.package['candidates'][0]['media'][1]))
        write_json(self.root/'clips.json',self.package)
        self.form['package']=file_record(self.root/'clips.json')
        self.form['criteria']['motion'].update(preference={'outcome':'tie','candidate_ids':['a','b']}, examples=[
            {'candidate_id':'a','selection_id':'c','start_time':6.0,'end_time':6.04},
            {'candidate_id':'b','selection_id':'f','frame_id':150}])
        with self.assertRaisesRegex(ValueError, 'each selected motion candidate'): self.validate()
        self.form['criteria']['motion']['examples'][1]={'candidate_id':'b','selection_id':'c','start_time':6.0,'end_time':6.04}
        self.validate()

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

class ActualModeReviewIntegrationTests(unittest.TestCase):
    """Temporary fabricated media/opinions exercise actual-mode validation only.

    They are never published outside this test directory or claimed as a real
    human review. Marking this test manifest actual exercises the production
    schema path; production artifacts must truthfully use their origin.
    """
    def setUp(self):
        from PIL import Image
        from unittest.mock import patch
        from test_vipe_benchmark_qualitative_generation import GenerationTests
        from vipe_benchmark.config import ROOT
        from vipe_benchmark.files import read_json
        from vipe_benchmark.qualitative_generation import generate, publish_generation
        # Reuse the generation seam fixture, then construct its real charged
        # graph. Everything remains temporary, including simulated authority.
        fixture=GenerationTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        self.root=fixture.root
        self.ledger=fixture.ledger
        request=fixture.request
        request.update(record_kind='actual',max_new_artifact_bytes=2**20,
            reconstruction_frames=[0,1],detail_regions=[{'id':'center','crop':[4,3,8,6]}])
        config=self.root/'config.json';write_json(config,self.ledger.config)
        inputs_value=read_json(request['bindings']['inputs']['path'])
        inputs_value['rgb'].append(dict(fixture.input,identity=dict(fixture.identity,frame=1,pair_start=0)))
        inputs=self.root/'prepare/inputs.json';write_json(inputs,inputs_value)
        approval=self.root/'test-only-approval.json'
        write_json(approval,{'schema':'plan067-implementation-approval/v1','record_kind':'user-authorization',
            'instruction':'Simulated fixture authorization, never a real approval',
            'scope':{'qualitative_preparation':'Implement and generate immutable matched diagnostic packages from valid existing results within remaining CPU and artifact ceilings.'}})
        request['bindings'].update(config=file_record(config),inputs=file_record(inputs),approval=file_record(approval),
            amendment=file_record(ROOT/'docs/specs/plan031-execution/qualitative-comparison-amendment.md'))
        mask=self.root/'test-only-mask.png';Image.new('L',(16,12),0).save(mask)
        worker=self.root/'test-only-worker.json'
        write_json(worker,{'component':'S2','configuration':file_record(config),'inputs':file_record(inputs)})
        row=dict(fixture.input,source_rgb_sha256=fixture.input['rgb']['sha256'],semantic_static=file_record(mask))
        source=self.root/'test-only-source-result.json'
        write_json(source,{'status':'complete','component':'S2','configuration':file_record(worker),'rows':[row]})
        self.events=[{'event':'finish','status':'complete','result':file_record(source)}]
        self.ledger.events=lambda:self.events[:]
        self.ledger.charge_cpu_preparation=lambda seconds,evidence:self.events.append({'event':'cpu_preparation_charge','evidence':evidence})
        ledger_patch=patch('vipe_benchmark.qualitative_generation.Ledger',return_value=self.ledger)
        ledger_patch.start();self.addCleanup(ledger_patch.stop)
        with patch('vipe_benchmark.qualitative_generation.resources',return_value={'artifact_bytes':0}), patch(
                'vipe_benchmark.qualitative_generation.result_record',side_effect=lambda local,job:file_record(source) if job=='S2-reconstruction' else None):
            self.generated=generate(request,self.root/'generated',ledger=self.ledger)
            published=publish_generation(self.generated['manifests']['segmentation'],self.root/'package',ledger=self.ledger)
        self.package_record=published['package']
        self.manifest=read_json(self.package_record['path'])
        self.candidate=next(candidate for candidate in self.manifest['candidates'] if candidate['id']=='S2')
        self.image=Path(self.candidate['media'][0]['record']['path'])
        selection_id=self.candidate['media'][0]['selection_id']
        self.form=review.blank_review(self.package_record)
        self.form.update(reviewer={'name':'Test-only simulated reviewer','reviewed_at':'2026-09-29'},tradeoffs='Simulated tradeoff; not an actual opinion')
        for criterion in self.form['criteria'].values():
            criterion.update(observation='Simulated test observation; not human feedback',
                preference={'outcome':'preferred','candidate_ids':['S2']},
                examples=[{'candidate_id':'S2','selection_id':selection_id,'frame_id':0}])
        self.form['criteria']['motion'].update(preference={'outcome':'unjudgeable','candidate_ids':[]},examples=[],observation='S2 has no complete matched continuous clip in this temporary test package')

    def test_actual_mode_full_package_import_choice_and_report(self):
        write_json(self.root/'test-only-submission.json',self.form)
        accepted=review.import_review(self.package_record,file_record(self.root/'test-only-submission.json'),self.root/'accepted.json')
        eligibility={key:{'eligible':True,'reason':'Test-only eligibility'} for key in self.form['candidate_ids']}
        decision=review.freeze_decision(accepted,eligibility,self.root/'decision.json')
        self.assertEqual(decision['selected_candidate_ids'],['S2'])
        report=review.build_report(accepted,file_record(self.root/'decision.json'),self.root/'report.json')
        self.assertEqual(report['human_review'],self.form)
        self.assertTrue(report['actual_human_review'])
        self.assertFalse(report['measured_accuracy'])
        self.image.write_bytes(b'changed after import')
        with self.assertRaises(ValueError): review.freeze_decision(accepted,eligibility,self.root/'changed.json')
        with self.assertRaises(ValueError): review.build_report(accepted,file_record(self.root/'decision.json'),self.root/'changed-report.json')

    def test_available_candidate_without_selected_media_refused(self):
        # S2 has a bound output at frame 0, but no native row for frame 1.
        missing_selection=next(selection for selection in self.manifest['selections'] if selection['frame_ids']==[1])
        self.form['criteria']['overall']['examples']=[{'candidate_id':'S2','selection_id':missing_selection['id'],'frame_id':1}]
        with self.assertRaisesRegex(ValueError,'unknown candidate selection'): review.validate_review(self.form)

    def test_readiness_inventory_cannot_count_as_actual_comparison(self):
        from unittest.mock import patch
        from vipe_benchmark.qualitative_generation import publish_generation
        with patch('vipe_benchmark.qualitative_generation.resources',return_value={'artifact_bytes':0}):
            published=publish_generation(self.generated['manifests']['depth'],self.root/'inventory',ledger=self.ledger)
        self.assertEqual(published['readiness'],'readiness-inventory')
        self.form['package']=published['package']
        with self.assertRaisesRegex(ValueError,'readiness inventory'): review.validate_review(self.form)

    def test_missing_generation_charge_invalidates_actual_review(self):
        self.events[:]=[event for event in self.events if event['event']!='cpu_preparation_charge']
        with self.assertRaisesRegex(ValueError,'charge'): review.validate_review(self.form)

if __name__ == '__main__': unittest.main()
