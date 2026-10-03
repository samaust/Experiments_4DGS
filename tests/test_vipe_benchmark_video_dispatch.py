"""Video dispatch binds the exact command before authorizing a GPU attempt."""
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import basketball_vipe_video_actual_dispatch as dispatcher
import basketball_vipe_video_publish as publisher
from vipe_benchmark.config import load, training_cameras
from vipe_benchmark.files import file_record, read_json, write_json
from vipe_benchmark.ledger import Ledger
from vipe_benchmark.video_depth import admitted_video_request, validate_runtime_interpreter


class VideoDispatchBindingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.local = self.root / '.local/vipe-alternatives/plan031-20260913T032700Z'
        (self.local / 'requests').mkdir(parents=True)
        self.worker = self.root / 'scripts/basketball_vipe_video_actual.py'
        self.worker.parent.mkdir()
        self.worker.write_text('# CPU-only fixture worker\n')
        config = self.root / 'configs/vipe-alternatives/benchmark-v1.json'
        config.parent.mkdir(parents=True)
        write_json(config, load())
        self.review_path = self.root / 'review.json'
        write_json(self.review_path, dict(proposals=[dict(candidate=candidate,
            allocation=dict(gpu_seconds=12000, download_bytes=10000, artifact_bytes=10000)) for candidate in ('D9', 'D10')]))
        self.approval = self.root / 'approval.json'
        write_json(self.approval, dict(review=file_record(self.review_path),
            candidate_approvals=[dict(candidate=candidate) for candidate in ('D9', 'D10')],
            cap_amendment=file_record(self.review_path), cap_approval=dict(status='approved')))
        self.qualification = self.root / 'qualification.json'
        write_json(self.qualification, dict(status='passed',
            python_executable=str(Path(sys.executable).absolute())))
        self.context = self.root / 'context.json'
        write_json(self.context, dict(schema='plan069-depth-context/v1',
            rows=[dict(camera=camera, frame=frame)
                  for camera in training_cameras(load()) for frame in range(50, 200)]))

    def tearDown(self):
        self.temp.cleanup()

    def run_dispatch(self, candidate):
        source_review = self.root / ('docs/research/vipe-alternatives/'
            f'plan031-execution/depth-{candidate}-source-review-001.json')
        source_review.parent.mkdir(parents=True, exist_ok=True)
        write_json(source_review, dict(status='passed'))
        admission = self.root / 'admission.json'
        proposal = next(row for row in read_json(self.review_path)['proposals']
                        if row['candidate'] == candidate)
        write_json(admission, dict(schema='plan069-depth-admission-result/v1',
            status='passed', candidate=candidate, source_review=file_record(source_review),
            review=file_record(self.review_path), authorization=file_record(self.approval),
            proposal_sha256=dispatcher.object_hash(proposal), commercial={}, assets=[],
            live=dict(sampled_unix=1000., ledger_head_sha256='0' * 64),
            runtime=dict(receipt=file_record(self.qualification))))
        original_admission = file_record(admission)
        setup = self.local / 'jobs' / f'plan069-{candidate}-setup-001' / 'result.json'
        setup.parent.mkdir(parents=True)
        write_json(setup, dict(status='complete'))
        ledger = Mock(path=self.local / 'ledger.jsonl')
        ledger.events.return_value = []
        ledger.states.return_value = {f'plan069-{candidate}-setup-001': dict(
            event='finish', status='complete', result=file_record(setup))}
        ledger.events.return_value = []
        ledger.totals.return_value = {resource: dict(elapsed_seconds=0, reserved_seconds=0)
                                     for resource in ('gpu', 'cpu', 'setup')}
        captured = {}
        clock = [2000.]

        def review_evidence(*args, **kwargs):
            self.assertEqual(kwargs['completed_setup'], file_record(setup))
            self.assertEqual(kwargs['setup_events'], [])
            self.assertEqual(kwargs['run_root'], self.local)
            self.assertEqual(kwargs['now_unix'], 1000.)
            self.assertEqual(kwargs['live']['sampled_unix'], 1000.)
            clock[0] += 10.  # Rehashing old qualification outlasts the live window.
            return []

        def authorize(candidate, review, authorization, source_review, admission, *,
                      command, request, worker, executable):
            saved = read_json(request['path'])
            self.assertEqual(saved['candidate'], candidate)
            self.assertEqual(saved['component'], candidate)
            self.assertEqual(saved['source_review'], source_review)
            self.assertEqual(saved['qualification'], file_record(self.qualification))
            refreshed = read_json(admission['path'])
            self.assertEqual(refreshed['completed_setup'], file_record(setup))
            self.assertEqual(refreshed['input_admission'], original_admission)
            self.assertEqual(refreshed['live']['sampled_unix'], 2010.)
            self.assertEqual(file_record(original_admission['path']), original_admission)
            clock[0] += 2.9  # The locked allocator rechecks the complete evidence.
            self.assertLessEqual(clock[0] - refreshed['live']['sampled_unix'], 5.)
            self.assertEqual(executable, file_record(sys.executable))
            self.assertEqual(worker, file_record(self.worker))
            self.assertEqual(command, [sys.executable, str(self.worker), '--request',
                request['path'], '--output', str(self.local / 'jobs' / saved['job_id'])])
            captured.update(command=command, request=request, worker=worker,
                            executable=executable)
            Ledger._depth_command(SimpleNamespace(path=ledger.path), candidate,
                dict(review=review, authorization=authorization,
                     source_review=source_review, admission=admission),
                dict(local_sources=[worker]), captured, command)
            return dict(slot_byte_budget=dict(schema='plan069-depth-slot-byte-budget/v1',
                candidate=candidate, proposal_sha256=dispatcher.object_hash(proposal),
                shared_setup_artifact_bytes=0, setup_baseline=dict(download_bytes=0,artifact_bytes=0),
                absolute_limits=dict(download_bytes=10000,artifact_bytes=10000)))
        ledger.authorize_depth_attempt.side_effect = authorize

        def supervise(ledger_arg, job_id, command, output, *, evidence, **kwargs):
            self.assertEqual(kwargs['sample_resources']()['artifact_bytes'], 0)
            with patch.object(dispatcher, 'resources', return_value=dict(artifact_bytes=10001,download_bytes=0)), self.assertRaisesRegex(ValueError, 'whole-slot allocation exceeded'):
                kwargs['sample_resources']()
            self.assertEqual(command, captured['command'])
            for key in ('request', 'worker', 'executable'):
                self.assertEqual(evidence[key], captured[key])
            self.assertEqual(evidence['qualification'], file_record(self.qualification))
            return dict(status='fixture-supervision-not-executed')

        original_read = Path.read_text
        def read_text(path, *args, **kwargs):
            return 'systemd\n' if str(path) == '/proc/1/comm' else original_read(path, *args, **kwargs)
        with patch.object(dispatcher, 'ROOT', self.root), \
             patch.object(dispatcher, 'DO', self.approval), \
             patch.object(dispatcher, 'shared_run_root', return_value=self.root), \
             patch.object(dispatcher, 'Ledger', return_value=ledger), \
             patch.object(dispatcher, 'resources', return_value=dict(gpu_pids=[],
                 download_bytes=0, artifact_bytes=0, device_bytes=0)), \
             patch.object(dispatcher, 'admit', side_effect=review_evidence), \
             patch.object(dispatcher.time, 'time', side_effect=lambda: clock[0]), \
             patch.object(dispatcher, 'supervise', side_effect=supervise), \
             patch.object(Path, 'read_text', read_text):
            result = dispatcher.dispatch(candidate, admission, self.context)
        self.assertEqual(result['status'], 'fixture-supervision-not-executed')
        ledger.authorize_depth_attempt.assert_called_once()

    def test_d9_authorization_and_supervision_share_exact_bindings(self):
        self.run_dispatch('D9')

    def test_d10_authorization_and_supervision_share_exact_bindings(self):
        self.run_dispatch('D10')

    def test_publication_without_slot_proof_fails_before_any_receipt_or_output(self):
        candidate = 'D9'
        job = 'plan069-D9-maps-001'
        result_path = self.local / 'jobs' / job / 'result.json'
        context = file_record(self.context)
        write_json(result_path, dict(schema='plan069-video-depth-result/v1',
            record_kind='actual', component=candidate, context=context,
            rows=[{}] * 256, anchor_rows=[{}] * 60, sequences=[{}] * 60))
        setup_path = self.local / 'jobs/plan069-D9-setup-001/result.json'
        write_json(setup_path, dict(status='complete'))
        write_json(self.local / 'requests' / (job + '.json'),
            dict(component=candidate, context=context, admission={}, setup=file_record(setup_path)))
        ledger = Mock(path=self.local / 'ledger.jsonl')
        ledger.events.return_value = []
        ledger.states.return_value = {job: dict(event='finish',status='complete',result=file_record(result_path))}
        ledger.totals.return_value = dict(cpu=dict(elapsed_seconds=0))
        with patch.object(publisher, 'shared_run_root', return_value=self.root), \
             patch.object(publisher, 'Ledger', return_value=ledger), \
             patch.object(publisher, 'setup_environment'), \
             patch.object(publisher, 'resources', return_value=dict(artifact_bytes=0)), \
             self.assertRaisesRegex(ValueError, 'whole-slot byte proof'):
            publisher.publish(candidate)
        self.assertFalse((self.local / 'receipts').exists())
        self.assertFalse((self.local / 'jobs/plan069-D9-clips-001').exists())
        ledger.charge_cpu_preparation.assert_not_called()

    def test_qualified_environment_invocation_path_must_match(self):
        runtime = dict(receipt=file_record(self.qualification))
        validate_runtime_interpreter(runtime, sys.executable)
        with self.assertRaisesRegex(ValueError, 'interpreter differs'):
            validate_runtime_interpreter(runtime, self.root / 'another-env/bin/python')

    def test_worker_rechecks_admission_qualification_and_source_bindings(self):
        job = 'plan069-D9-maps-001'
        source_path = self.root / 'source-review.json'
        write_json(source_path, dict(status='passed'))
        source = file_record(source_path)
        qualification = file_record(self.qualification)
        admission_path = self.root / 'admission.json'
        write_json(admission_path, dict(candidate='D9', status='passed',
            schema='plan069-depth-admission-result/v1', source_review=source,
            runtime=dict(receipt=qualification)))
        admission = file_record(admission_path)
        review, approval = file_record(self.review_path), file_record(self.approval)
        setup_path = self.root / 'setup.json'
        setup_document = dict(schema='plan069-video-setup-result/v1', status='complete',
            record_kind='actual', candidate='D9', review=review, authorization=approval)
        write_json(setup_path, setup_document)
        setup = file_record(setup_path)
        config = dict(load(), new_download_gib_limit=110, new_artifact_disk_gib_limit=210)
        ledger = Mock(path=self.local / 'ledger.jsonl')
        ledger.events.return_value = []
        ledger.states.return_value = {
            job: dict(event='reserve', resource='gpu', seconds=12000,
                      evidence=dict(admission=admission)),
            'plan069-D9-setup-001': dict(event='finish', status='complete', result=setup)}
        request = dict(schema='plan069-video-depth-request/v1', record_kind='actual',
            component='D9', candidate='D9', id=job, job_id=job,
            ledger_path=str(ledger.path), admission=admission, source_review=source,
            qualification=qualification, setup=setup, review=review, authorization=approval,
            max_seconds=12000)
        with patch('vipe_benchmark.depth_setup._active_reservation',
                   return_value=(self.local, config)):
            with self.assertRaisesRegex(ValueError, 'whole-slot'):
                admitted_video_request(request, self.local / 'jobs' / job,
                    config, ledger=ledger, request_path=self.root / 'request.json')
            self.assertFalse((self.local / 'jobs' / job).exists())
            for key in ('qualification', 'source_review'):
                with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'binding changed'):
                    admitted_video_request(dict(request, **{key: admission}),
                        self.local / 'jobs' / job, config, ledger=ledger,
                        request_path=self.root / 'request.json')


if __name__ == '__main__':
    unittest.main()
