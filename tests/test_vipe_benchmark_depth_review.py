"""CPU fixture tests through the extended review/import/decision boundary."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from vipe_benchmark import depth_review
from vipe_benchmark.depth_admission import D2_SPEC, PROFILES
from vipe_benchmark.depth_extension import CONFIG
from vipe_benchmark.files import file_record, read_json, write_json


class DepthReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.number = 0
        self.media = self.root / 'frame.png'
        self.media.write_bytes(b'explicit CPU fixture media')
        specs = dict(read_json(CONFIG)['candidates'], D2=D2_SPEC)
        self.inputs = self.record({'fixture': 'accepted inputs'})
        self.context = self.record({'inputs': self.inputs})
        self.slots = {}
        candidates = []
        for name in ('D2','D5','D6','D7','D8','D9','D10','D11','D4'):
            spec = specs.get(name, D2_SPEC)
            dependencies = self.record(dict(schema='plan069-depth-installed-dependencies/v1',
                candidate=name, source_revision=spec['code']['revision'], files=[file_record(self.media)]))
            commercial = self.record(dict(schema='plan069-depth-commercial-assessment/v1',
                candidate=name, source_revision=spec['code']['revision'], weights_revision=spec['weights']['revision'],
                dependency_manifest=dependencies, primary_sources=[{'url':'fixture-a'},{'url':'fixture-b'}],
                code='allowed', weights='allowed', dependencies='allowed', inference_outputs='allowed'))
            setup = self.record({'record_kind':'fixture','status':'complete','candidate':name})
            runtime = self.record(dict(schema='plan069-depth-runtime-qualification/v1',
                candidate=name, source_revision=spec['code']['revision'], status='passed',
                config=file_record(CONFIG), profile=read_json(PROFILES)['profiles'].get(name, {}),
                dependency_manifest=dependencies, setup=setup, assets=[], local_sources=[file_record(self.media)]))
            fit = self.record(dict(component=name, role='fit', status='passed', provenance={'inputs':self.inputs}))
            check = self.record(dict(component=name, role='selection', status='passed', frozen_fit=fit, provenance={'inputs':self.inputs}))
            result = self.record(dict(record_kind='fixture', status='complete', candidate=name,
                context=self.context, inputs=self.inputs, setup=setup, scales={'fit':fit,'check':check}))
            self.slots[name] = dict(status='available', evidence=dict(commercial=commercial,
                runtime=runtime, generation=result, scale=check))
            if name == 'D2':
                self.slots[name]['evidence'].update(historical_fit=self.record({'scale':fit}),
                    historical_check=self.record({'scale':check}))
            candidates.append(dict(id=name,status='available',media=[dict(selection_id='camera1-selection-175',
                kind='frame',frame_ids=[175],timestamps=[7.0],record=file_record(self.media))]))
        self.request = self.record(dict(candidates=self.slots))
        self.package = self.record(dict(schema='plan067-qualitative-package/v1',record_kind='fixture',
            mode='qualitative',id='CPU-fixture',candidates=candidates,
            bindings=dict(depth_aggregate_request=self.request,inputs=self.inputs,context=self.context)))
        self.form = depth_review.blank_review(self.package)
        self.form.update(record_kind='fixture',reviewer={'name':'CPU fixture','reviewed_at':'2026-10-03'},
            tradeoffs='Relative visual preference differs from metric choice.')
        for criterion in self.form['criteria'].values():
            criterion.update(observation='Not applicable to this fixture criterion.',
                preference={'outcome':'not_applicable','candidate_ids':[]})
        self.form['criteria']['overall'].update(observation='D11 visually preferred in fixture.',
            preference={'outcome':'preferred','candidate_ids':['D11']},examples=[self.example('D11')])
        self.form['metric_choice'] = dict(outcome='selected',candidate_ids=['D5'],
            reason='D5 has acceptable edges and passing metric evidence in fixture.',examples=[self.example('D5')])

    def record(self, value):
        self.number += 1
        path = self.root / f'{self.number}.json'
        write_json(path,value)
        return file_record(path)

    def example(self, candidate):
        return dict(candidate_id=candidate,selection_id='camera1-selection-175',frame_id=175)

    def freeze(self, form=None):
        submission = self.record(self.form if form is None else form)
        imported = depth_review.import_review(self.package,submission,self.root/'review.json',actual=False)
        return depth_review.freeze_decision(imported,self.root/'decision.json',actual=False)

    def test_relative_visual_favorite_and_separate_metric_choice(self):
        decision = self.freeze()
        self.assertEqual(decision['status'],'ready')
        self.assertEqual(decision['visual_preference'], {'outcome':'preferred','candidate_ids':['D11']})
        self.assertEqual(decision['selected_candidate_ids'],['D5'])
        self.assertFalse(decision['actual_human_review'])
        self.assertEqual(depth_review.validate_decision(file_record(self.root/'decision.json'),actual=False),decision)

    def test_metric_choice_rejects_changed_fit_inputs(self):
        slot = self.slots['D5']
        generation = read_json(slot['evidence']['generation']['path'])
        fit = dict(read_json(generation['scales']['fit']['path']),provenance={'inputs':self.record({'other':'inputs'})})
        changed_fit = self.record(fit)
        check = dict(read_json(generation['scales']['check']['path']),frozen_fit=changed_fit)
        changed_check = self.record(check)
        changed_generation = dict(generation,scales={'fit':changed_fit,'check':changed_check})
        slot['evidence'].update(generation=self.record(changed_generation),scale=changed_check)
        package = read_json(self.package['path'])
        package['bindings']['depth_aggregate_request'] = self.record({'candidates':self.slots})
        self.form['package'] = self.record(package)
        with self.assertRaisesRegex(ValueError,'scale input'):
            depth_review.validate_review(self.form,actual=False)

    def test_missing_qualification_blocks_candidate_without_inventing_fallback(self):
        self.slots['D6']['evidence'].pop('runtime')
        package = read_json(self.package['path'])
        package['bindings']['depth_aggregate_request'] = self.record({'candidates':self.slots})
        self.form['package'] = self.record(package)
        decision = depth_review.freeze_decision(self.record(self.form),self.root/'missing.json',actual=False)
        self.assertEqual(decision['status'],'ready')
        self.assertFalse(decision['engineering_eligibility']['D6']['eligible'])
        self.form['metric_choice'].update(candidate_ids=['D6'],examples=[self.example('D6')])
        decision = depth_review.freeze_decision(self.record(self.form),self.root/'blocked.json',actual=False)
        self.assertEqual(decision['status'],'blocked')
        self.assertEqual(decision['requested_candidate_ids'],['D6'])
        self.assertEqual(decision['selected_candidate_ids'],[])

    def test_no_visual_fallback_or_automatic_tie_resolution(self):
        for outcome, selected in [('unclear',[]),('unjudgeable',[]),('not_applicable',[]),('tie',['D5','D6'])]:
            with self.subTest(outcome=outcome):
                form = copy.deepcopy(self.form)
                form['metric_choice'].update(outcome=outcome,candidate_ids=selected,
                    examples=[self.example(key) for key in selected],reason='Reviewer has not selected one metric method.')
                decision = depth_review.freeze_decision(self.record(form),self.root/(outcome+'.json'),actual=False)
                self.assertEqual(decision['status'],'blocked')
                self.assertEqual(decision['selected_candidate_ids'],[])
                self.assertEqual(decision['requested_candidate_ids'],selected)

    def test_relative_historical_unknown_and_unavailable_metric_choices_reject(self):
        for candidate in ('D9','D11','D4','unknown'):
            form = copy.deepcopy(self.form)
            form['metric_choice'].update(candidate_ids=[candidate],examples=[self.example(candidate)])
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                depth_review.validate_review(form,actual=False)
        package = read_json(self.package['path'])
        next(item for item in package['candidates'] if item['id']=='D5').update(status='failed',media=[],reason='failed native run')
        self.form['package'] = self.record(package)
        with self.assertRaises(ValueError): depth_review.validate_review(self.form,actual=False)

    def test_failed_scale_does_not_become_metric_eligible(self):
        generation = read_json(self.slots['D5']['evidence']['generation']['path'])
        check = dict(read_json(generation['scales']['check']['path']),status='blocked')
        generation['scales']['check'] = self.record(check)
        self.slots['D5']['evidence'].update(generation=self.record(generation),scale=generation['scales']['check'])
        package = read_json(self.package['path'])
        package['bindings']['depth_aggregate_request'] = self.record({'candidates':self.slots})
        self.form['package'] = self.record(package)
        decision = depth_review.freeze_decision(self.record(self.form),self.root/'blocked.json',actual=False)
        self.assertEqual(decision['status'],'blocked')
        self.assertEqual(decision['requested_candidate_ids'],['D5'])
        self.assertEqual(decision['selected_candidate_ids'],[])

    def test_immutable_decision_and_artifact_changes_require_new_record(self):
        self.freeze()
        with self.assertRaises(FileExistsError):
            depth_review.freeze_decision(file_record(self.root/'review.json'),self.root/'decision.json',actual=False)
        changed = dict(read_json(self.root/'decision.json'),selected_candidate_ids=['D6'])
        with self.assertRaisesRegex(ValueError,'contents changed'):
            depth_review.validate_decision(self.record(changed),actual=False)
        self.media.write_bytes(b'changed frame')
        with self.assertRaises(ValueError):
            depth_review.validate_decision(file_record(self.root/'decision.json'),actual=False)

    def test_fixture_cannot_claim_actual_human_review(self):
        with self.assertRaisesRegex(ValueError,'synthetic'):
            depth_review.validate_review(self.form)
        form = dict(self.form,record_kind='human')
        with self.assertRaisesRegex(ValueError,'fixture package'):
            depth_review.validate_review(form)

    def test_missing_reason_or_invalid_exact_example_rejects(self):
        for mutation in [lambda f:f['metric_choice'].update(reason=''),
                         lambda f:f['metric_choice'].update(examples=[]),
                         lambda f:f['metric_choice']['examples'][0].update(frame_id=176),
                         lambda f:f['metric_choice'].update(candidate_ids=['D5','D6']),
                         lambda f:f['criteria']['motion'].update(observation='')]:
            form = copy.deepcopy(self.form)
            mutation(form)
            with self.subTest(form=form), self.assertRaises(ValueError):
                depth_review.validate_review(form,actual=False)

    def test_original_d2_context_inputs_and_cpu_preflight_do_not_qualify_metric_choice(self):
        generation = read_json(self.slots['D2']['evidence']['generation']['path'])
        generation.pop('inputs')
        generation.pop('setup')
        self.slots['D2']['evidence']['generation'] = self.record(generation)
        self.slots['D2']['evidence']['runtime'] = self.record(dict(
            schema='plan069-d2-cpu-preflight/v1',candidate='D2',status='cpu_preflight_passed'))
        package = read_json(self.package['path'])
        package['bindings']['depth_aggregate_request'] = self.record({'candidates':self.slots})
        self.form['package'] = self.record(package)
        self.form['metric_choice'].update(candidate_ids=['D2'],examples=[self.example('D2')])
        decision = depth_review.freeze_decision(self.record(self.form),self.root/'d2.json',actual=False)
        self.assertEqual(decision['status'],'blocked')
        self.assertIn('CPU preflight is insufficient',decision['reason'])
        self.assertEqual(decision['engineering_eligibility']['D2']['evidence']['inputs'],self.inputs)

    def test_missing_native_generation_receipt_rejects_submission(self):
        self.slots['D5']['evidence'].pop('generation')
        package = read_json(self.package['path'])
        package['bindings']['depth_aggregate_request'] = self.record({'candidates':self.slots})
        self.form['package'] = self.record(package)
        with self.assertRaisesRegex(ValueError,'generation receipt missing'):
            depth_review.validate_review(self.form,actual=False)

    def test_published_extended_viewer_exports_separate_metric_choice(self):
        from test_vipe_benchmark_qualitative_package import PackageTests
        from vipe_benchmark.qualitative_package import publish
        fixture = PackageTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        fixture.manifest['bindings']['depth_aggregate_request'] = self.request
        result = publish(fixture.manifest,fixture.root/'extended')
        html = Path(result['viewer']['path']).read_text()
        self.assertIn('plan069-depth-review/v1',html)
        self.assertIn('Separate metric depth choice D*',html)
        self.assertIn("review.metric_choice={outcome:",html)
        self.assertIn("m.record_kind==='fixture'?'fixture':'human'",html)

    def completed_fixture(self):
        """Model a completed admission chain, never an actual execution receipt."""
        slot = self.slots['D5']
        self.code = self.root/'publication.py'
        self.code.write_text('original qualified publication code')
        self.archive = self.root/'native.tar.gz'
        self.archive.write_bytes(b'immutable native source fixture')
        runtime = read_json(slot['evidence']['runtime']['path'])
        runtime.update(local_sources=[file_record(self.code)],source_archive=file_record(self.archive),
            source_files=[{'path':'native.py','sha256':'a'*64,'bytes':5}])
        slot['evidence']['runtime'] = self.record(runtime)
        source_review = self.record(dict(status='passed',candidate='D5',source_revision=runtime['source_revision'],
            local_sources=runtime['local_sources'],source_archive=runtime['source_archive'],source_files=runtime['source_files']))
        self.qualification = self.record(dict(candidate='D5',status='passed',
            runtime={'receipt':slot['evidence']['runtime']},commercial={'assessment':slot['evidence']['commercial']},
            source_review=source_review,source_archive=runtime['source_archive'],source_files=runtime['source_files']))
        admission = self.record(dict(schema='plan069-depth-admission-result/v1',status='passed',candidate='D5',
            runtime={'receipt':slot['evidence']['runtime']},commercial={'assessment':slot['evidence']['commercial']},
            source_review=source_review,qualification=self.qualification))
        generation = dict(read_json(slot['evidence']['generation']['path']),job_id='fixture-D5')
        slot['evidence']['generation'] = self.record(generation)
        request = self.record(dict(job_id='fixture-D5',candidate='D5',context=self.context,
            admission=admission,source_review=source_review,qualification=self.qualification))
        finish = self.record(dict(event='finish',status='complete',job_id='fixture-D5',
            result=slot['evidence']['generation'],cleanup_confirmed=True,cleanup_uncertain=False))
        slot['provenance'] = dict(configuration=request,ledger_outcome=finish)
        package = read_json(self.package['path'])
        package['bindings']['depth_aggregate_request'] = self.record({'candidates':self.slots})
        self.form['package'] = self.record(package)

    def test_completed_qualification_survives_later_publication_source_edit(self):
        self.completed_fixture()
        self.code.write_text('new publication UI after the completed fixture job')
        decision = depth_review.freeze_decision(self.record(self.form),self.root/'historical.json',actual=False)
        self.assertEqual(decision['status'],'ready')
        proof = decision['engineering_eligibility']['D5']['evidence']['completed_qualification']
        self.assertEqual(proof['qualification'],self.qualification)
        self.assertEqual(proof['local_sources'][0]['sha256'],
            read_json(self.slots['D5']['evidence']['runtime']['path'])['local_sources'][0]['sha256'])

    def test_completed_binding_rejects_tampered_qualification_and_native_archive(self):
        self.completed_fixture()
        self.archive.write_bytes(b'changed native source archive')
        with self.assertRaises(ValueError): depth_review.validate_review(self.form,actual=False)
        self.archive.write_bytes(b'immutable native source fixture')
        Path(self.qualification['path']).write_text('{}')
        with self.assertRaises(ValueError): depth_review.validate_review(self.form,actual=False)


class ActualReceiptIntegrationTests(unittest.TestCase):
    """Regressions from validating the first actual extended package (plan069-depth-comparison-002)."""

    def test_d6_review_uses_the_admission_per_attempt_driver_validator(self):
        import inspect
        import tempfile
        from vipe_benchmark import depth_admission, depth_review
        from vipe_benchmark.files import file_record, write_json
        self.assertIn('d6_driver_qualification_exception(runtime, events=events, run_root=root)',
                      inspect.getsource(depth_review._completed_qualification))
        self.assertIn('d6_driver_qualification_exception(qualification, events=setup_events, run_root=run_root)',
                      inspect.getsource(depth_admission.review))
        with tempfile.TemporaryDirectory() as directory:
            finish = Path(directory) / 'finish.json'
            write_json(finish, dict(event='finish', job_id='plan069-D6-driver-qualification-011'))
            qualification = dict(driver_qualification=dict(finish=file_record(finish)))
            with patch('vipe_benchmark.depth_driver_qualification_triton_cache.qualification_exception') as triton, \
                    patch('vipe_benchmark.depth_driver_qualification.qualification_exception') as original:
                depth_admission.d6_driver_qualification_exception(qualification, events=['e'], run_root='r')
            triton.assert_called_once_with(qualification, events=['e'], run_root='r')
            original.assert_not_called()

    def test_dependency_records_keep_inventory_path_spelling(self):
        import inspect
        import tempfile
        from vipe_benchmark import depth_review
        from vipe_benchmark.files import file_record, verify_record
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / 'bin').mkdir()
            (root / 'lib/site-packages').mkdir(parents=True)
            (root / 'bin/tool').write_text('console script')
            record = dict(file_record(root / 'bin/tool'), path=str(root / 'lib/site-packages/../../bin/tool'))
            self.assertEqual(verify_record(record)['sha256'], record['sha256'])
            with self.assertRaisesRegex(ValueError, 'bytes/path mismatch'):
                depth_review._verify_file(record)
        source = inspect.getsource(depth_review._qualification_blockers)
        self.assertIn("for record in dependencies.get('files', []):\n        verify_record(record)", source)

    def test_only_the_d2_control_may_omit_its_package_scale_record(self):
        import inspect
        from vipe_benchmark import depth_review
        source = inspect.getsource(depth_review._metric_evidence)
        self.assertIn("evidence.get('scale') == scales['check'] or (candidate == 'D2' and 'scale' not in evidence)", source)
