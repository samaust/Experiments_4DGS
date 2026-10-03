"""Video dispatch binds the exact command before authorizing a GPU attempt."""
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import basketball_vipe_video_actual_dispatch as dispatcher
from vipe_benchmark.config import load, training_cameras
from vipe_benchmark.files import file_record, read_json, write_json
from vipe_benchmark.ledger import Ledger
from vipe_benchmark.video_depth import admitted_video_request


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
            allocation=dict(gpu_seconds=12000)) for candidate in ('D9', 'D10')]))
        self.approval = self.root / 'approval.json'
        write_json(self.approval, dict(review=file_record(self.review_path)))
        self.qualification = self.root / 'qualification.json'
        write_json(self.qualification, dict(status='passed'))
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
        write_json(admission, dict(schema='plan069-depth-admission-result/v1',
            status='passed', candidate=candidate, source_review=file_record(source_review),
            runtime=dict(receipt=file_record(self.qualification))))
        setup = self.local / 'jobs' / f'plan069-{candidate}-setup-001' / 'result.json'
        setup.parent.mkdir(parents=True)
        write_json(setup, dict(status='complete'))
        ledger = Mock(path=self.local / 'ledger.jsonl')
        ledger.states.return_value = {f'plan069-{candidate}-setup-001': dict(
            event='finish', status='complete', result=file_record(setup))}
        captured = {}

        def authorize(candidate, review, authorization, source_review, admission, *,
                      command, request, worker, executable):
            saved = read_json(request['path'])
            self.assertEqual(saved['candidate'], candidate)
            self.assertEqual(saved['component'], candidate)
            self.assertEqual(saved['source_review'], source_review)
            self.assertEqual(saved['qualification'], file_record(self.qualification))
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
        ledger.authorize_depth_attempt.side_effect = authorize

        def supervise(ledger_arg, job_id, command, output, *, evidence, **kwargs):
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
             patch.object(dispatcher, 'resources', return_value=dict(gpu_pids=[])), \
             patch.object(dispatcher, 'supervise', side_effect=supervise), \
             patch.object(Path, 'read_text', read_text):
            result = dispatcher.dispatch(candidate, admission, self.context)
        self.assertEqual(result['status'], 'fixture-supervision-not-executed')
        ledger.authorize_depth_attempt.assert_called_once()

    def test_d9_authorization_and_supervision_share_exact_bindings(self):
        self.run_dispatch('D9')

    def test_d10_authorization_and_supervision_share_exact_bindings(self):
        self.run_dispatch('D10')

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
            self.assertEqual(admitted_video_request(request, self.local / 'jobs' / job,
                config, ledger=ledger, request_path=self.root / 'request.json'), setup_document)
            for key in ('qualification', 'source_review'):
                with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'binding changed'):
                    admitted_video_request(dict(request, **{key: admission}),
                        self.local / 'jobs' / job, config, ledger=ledger,
                        request_path=self.root / 'request.json')


if __name__ == '__main__':
    unittest.main()
