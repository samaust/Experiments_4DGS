from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import basketball_vipe_depth_single_dispatch as dispatch
import test_vipe_benchmark_d2_actual as fixture
from vipe_benchmark.files import file_record, read_json
from vipe_benchmark.moge_setup import source_tree_records
from vipe_benchmark.depth_source_integrity import source_manifest


class SingleDispatchTest(unittest.TestCase):
    record = staticmethod(fixture.D2ActualTest.record)
    read_text = staticmethod(fixture.D2ActualTest.read_text)

    def setUp(self):
        fixture.D2ActualTest.setUp(self)
        self.checks = []
        for name, value in (('shared_run_root', lambda: self.root),
                            ('CONTEXT_RECEIPT', self.receipt_path),
                            ('Ledger', lambda path, config: self.ledger),
                            ('_live', lambda ledger, local: dict(ledger_head_sha256='head')),
                            ('admit', lambda *args, **kwargs: []),
                            ('local_source_records', lambda candidate: [])):
            patcher = patch.object(dispatch, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def candidate(self, candidate, *, interpreter=None, review_candidate=None):
        proposal = dict(candidate=candidate, allocation=dict(gpu_seconds=1800),
            candidate_config=dict(code=dict(revision='code-pin'), weights=dict(revision='weight-pin')))
        review = self.record(self.root / (candidate + '-review.json'), dict(proposals=[proposal]))
        do = self.root / (candidate + '-DO.json')
        approved = self.record(do, dict(review=review, candidate_approvals=[dict(candidate=candidate)],
            cap_amendment={}, cap_approval={}))
        source_review = self.root / (candidate + '-source-review.json')
        self.record(source_review, dict(schema='plan069-depth-source-review/v1',
            candidate=review_candidate or candidate, status='passed', source_revision='code-pin', local_sources=[]))
        source = self.root / candidate / 'source'
        source.mkdir(parents=True)
        (source / 'model.py').write_text('frozen native source')
        setup_path = self.local / 'jobs' / f'plan069-{candidate}-setup-001/result.json'
        assets = [dict(path='model.pt', record=self.prediction)]
        setup = self.record(setup_path, dict(schema='plan069-depth-setup-result/v1',
            candidate=candidate, status='complete', record_kind='actual',
            job_id=f'plan069-{candidate}-setup-001', review=review, authorization=approved,
            source_revision='code-pin', weight_revision='weight-pin', source_archive=self.rgb,
            source_dir=str(source), source_tree=source_tree_records(source), checkpoint=self.prediction,
            native_source=file_record(source / 'model.py'), source_manifest=source_manifest(source), assets=assets))
        self.ledger.current[f'plan069-{candidate}-setup-001'] = dict(event='finish', status='complete', result=setup)
        runtime_receipt = self.record(self.root / (candidate + '-runtime.json'),
            dict(schema='plan069-depth-runtime-qualification/v1', candidate=candidate,
                 status='passed', setup=setup, python_executable=interpreter or sys.executable))
        qualified_path = self.root / (candidate + '-qualification.json')
        self.record(qualified_path, dict(schema=f'plan069-depth-{candidate}-qualification/v1',
            candidate=candidate, setup=setup, commercial={}, assets=assets,
            runtime=dict(receipt=runtime_receipt)))
        return do, qualified_path, setup_path, source_review

    def supervise(self, ledger, job, command, output, **kwargs):
        candidate = job.split('-')[1]
        request = read_json(command[3])
        self.assertEqual(request['candidate'], candidate)
        self.assertEqual(request['schema'], 'plan069-depth-single-maps-request/v1')
        self.assertEqual(command[0], sys.executable)
        self.assertTrue(command[1].endswith('basketball_vipe_depth_single_maps.py'))
        binding = ledger.authorizations[-1][1]
        self.assertEqual(binding['command'], command)
        self.assertEqual(binding['executable'], file_record(sys.executable))
        self.assertEqual(binding['worker'], file_record(command[1]))
        self.assertEqual(binding['request'], kwargs['evidence']['request'])
        self.record(output / 'result.json', dict(marker=candidate))
        kwargs['validate_result'](output)
        ledger.current[job] = dict(event='finish', status='complete', cleanup_confirmed=True,
            cleanup_uncertain=False, surviving_pids=[])
        return dict(status='complete')

    def test_all_candidates_bind_command_qualification_and_finished_validator(self):
        for candidate in ('D5', 'D6', 'D8'):
            with self.subTest(candidate=candidate):
                do, qualified, setup, source = self.candidate(candidate)
                with patch.object(dispatch, 'DO', do), \
                     patch.object(dispatch, 'supervise', side_effect=self.supervise), \
                     patch.object(dispatch, 'validate_result') as validate:
                    self.assertEqual(dispatch.dispatch(candidate, self.context_path, qualified, setup, source),
                                     dict(status='complete'))
                    validate.assert_called_once()
                    result, request = validate.call_args.args
                    self.assertEqual(result['marker'], candidate)
                    self.assertEqual(request['setup'], file_record(setup))
                    self.assertEqual(request['qualification'], file_record(qualified))
                    self.assertEqual(request['source_review'], file_record(source))
                    self.assertEqual(request['context'], self.context)
                    self.assertEqual(request['inputs'], self.inputs)

    def test_admission_uses_refreshed_live_snapshot_after_evidence_validation(self):
        do, qualified, setup, source = self.candidate('D5')
        order = []
        def live(*_args):
            order.append('live')
            return dict(ledger_head_sha256='refreshed' if len(order)>1 else 'initial')
        def admit(*_args, **kwargs):
            order.append('admit')
            self.assertEqual(kwargs['live']['ledger_head_sha256'], 'initial')
            return []
        with patch.object(dispatch, 'DO', do), patch.object(dispatch, '_live', side_effect=live), \
             patch.object(dispatch, 'admit', side_effect=admit), \
             patch.object(dispatch, 'supervise', side_effect=self.supervise), \
             patch.object(dispatch, 'validate_result'):
            dispatch.dispatch('D5', self.context_path, qualified, setup, source)
        self.assertEqual(order, ['live', 'admit', 'live'])
        admission = read_json(self.local / 'requests/plan069-D5-maps-001-admission.json')
        self.assertEqual(admission['live']['ledger_head_sha256'], 'refreshed')

    def test_uncharged_context_blocks_before_authorization(self):
        do, qualified, setup, source = self.candidate('D5')
        self.ledger.history.clear()
        with patch.object(dispatch, 'DO', do), patch.object(dispatch, 'supervise') as supervise:
            with self.assertRaisesRegex(ValueError, 'ledger-charged'):
                dispatch.dispatch('D5', self.context_path, qualified, setup, source)
            supervise.assert_not_called()
        self.assertFalse(self.ledger.authorizations)

    def test_wrong_candidate_source_review_blocks_before_authorization(self):
        do, qualified, setup, source = self.candidate('D6', review_candidate='D5')
        with patch.object(dispatch, 'DO', do), patch.object(dispatch, 'supervise') as supervise:
            with self.assertRaisesRegex(ValueError, 'candidate source review'):
                dispatch.dispatch('D6', self.context_path, qualified, setup, source)
            supervise.assert_not_called()
        self.assertFalse(self.ledger.authorizations)

    def test_unqualified_interpreter_blocks_before_authorization(self):
        do, qualified, setup, source = self.candidate('D8', interpreter='/missing/venv/bin/python')
        with patch.object(dispatch, 'DO', do), patch.object(dispatch, 'supervise') as supervise:
            with self.assertRaisesRegex(ValueError, 'qualified setup runtime'):
                dispatch.dispatch('D8', self.context_path, qualified, setup, source)
            supervise.assert_not_called()
        self.assertFalse(self.ledger.authorizations)

    def test_setup_ledger_result_must_match(self):
        do, qualified, setup, source = self.candidate('D5')
        self.ledger.current['plan069-D5-setup-001']['result'] = {}
        with patch.object(dispatch, 'DO', do), patch.object(dispatch, 'supervise') as supervise:
            with self.assertRaisesRegex(ValueError, 'ledger-bound'):
                dispatch.dispatch('D5', self.context_path, qualified, setup, source)
            supervise.assert_not_called()
        self.assertFalse(self.ledger.authorizations)

    def test_failed_fresh_admission_never_authorizes(self):
        do, qualified, setup, source = self.candidate('D5')
        with patch.object(dispatch, 'DO', do), \
             patch.object(dispatch, 'admit', return_value=['stale ledger head']), \
             patch.object(dispatch, 'supervise') as supervise:
            with self.assertRaisesRegex(ValueError, 'stale ledger head'):
                dispatch.dispatch('D5', self.context_path, qualified, setup, source)
            supervise.assert_not_called()
        self.assertFalse(self.ledger.authorizations)
        self.assertFalse((self.local / 'requests/plan069-D5-maps-001.json').exists())

    def test_qualitative_admission_binds_candidate_and_inputs(self):
        do, qualified, setup, source = self.candidate('D5')
        qualitative = self.root / 'qualitative.json'
        self.record(qualitative, dict(schema='plan069-depth-qualitative-admission/v1',
            record_kind='actual', component='D5', inputs=self.inputs,
            purpose='qualitative-only', status='admitted'))
        with patch.object(dispatch, 'DO', do), \
             patch.object(dispatch, 'supervise', side_effect=self.supervise), \
             patch.object(dispatch, 'validate_result'):
            dispatch.dispatch('D5', self.context_path, qualified, setup, source,
                              qualitative_admission=qualitative)
        request = read_json(self.local / 'requests/plan069-D5-maps-001.json')
        self.assertEqual(request['qualitative_admission'], file_record(qualitative))

    def test_added_d8_source_file_blocks_before_model_authorization(self):
        do, qualified, setup, source = self.candidate('D8')
        (self.root / 'D8/source/added.py').write_text('unreviewed native import')
        with patch.object(dispatch, 'DO', do), patch.object(dispatch, 'supervise') as supervise:
            with self.assertRaisesRegex(ValueError, 'source tree changed'):
                dispatch.dispatch('D8', self.context_path, qualified, setup, source)
            supervise.assert_not_called()
        self.assertFalse(self.ledger.authorizations)

    def test_prepared_attempt_cannot_be_authorized_twice(self):
        do, qualified, setup, source = self.candidate('D5')
        with patch.object(dispatch, 'DO', do), \
             patch.object(dispatch, 'supervise', side_effect=self.supervise), \
             patch.object(dispatch, 'validate_result'):
            dispatch.dispatch('D5', self.context_path, qualified, setup, source)
            with self.assertRaisesRegex(ValueError, 'already prepared or consumed'):
                dispatch.dispatch('D5', self.context_path, qualified, setup, source)
        self.assertEqual(len(self.ledger.authorizations), 1)

    def test_uncertain_cleanup_blocks_completed_dispatch(self):
        do, qualified, setup, source = self.candidate('D5')
        with patch.object(dispatch, 'DO', do), patch.object(dispatch, 'supervise', return_value={}):
            with self.assertRaisesRegex(ValueError, 'cleanup not confirmed'):
                dispatch.dispatch('D5', self.context_path, qualified, setup, source)


if __name__ == '__main__':
    unittest.main()
