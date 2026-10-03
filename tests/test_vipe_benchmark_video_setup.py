"""Native video setup keeps exact source/weights and failed transfer evidence."""

from io import BytesIO
import hashlib
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.files import file_record, object_hash, read_json, write_json
from vipe_benchmark.video_native import REQUIRED_SOURCE, native_source_records, setup_environment
from vipe_benchmark.video_setup import run_video_setup
from vipe_benchmark.video_environment import RECIPE, environment_request


REVISION = '4f5ae23172ba60fd7bc11ef671cca678842c7072'


def source_archive(*, traversal=False):
    buffer = BytesIO()
    with tarfile.open(fileobj=buffer, mode='w:gz') as archive:
        for relative in REQUIRED_SOURCE:
            name = f'Video-Depth-Anything-{REVISION}/{relative}'
            if traversal and relative == 'run.py':
                name = f'Video-Depth-Anything-{REVISION}/../escape.py'
            payload = relative.encode()
            if relative == 'requirements.txt':
                payload = ('\n'.join(read_json(RECIPE)['upstream_requirements']) + '\n').encode()
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            archive.addfile(info, BytesIO(payload))
    return buffer.getvalue()


class VideoSetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.weights = b'pinned video small fixture'
        self.candidate = 'D9'
        asset = dict(repository='vda', path='video_depth_anything_vits.pth',
            bytes=len(self.weights),
            lfs_sha256=hashlib.sha256(self.weights).hexdigest())
        inventory = self.root / 'inventory.json'
        write_json(inventory, dict(candidates={'D9': dict(files=[asset])}))
        proposal = dict(candidate='D9', max_attempts=1,
            required_assets=file_record(inventory),
            allocation=dict(setup_seconds=2400, download_bytes=100000),
            candidate_config=dict(
                code=dict(url='https://github.com/DepthAnything/Video-Depth-Anything',
                          revision=REVISION),
                weights=dict(url='https://huggingface.co/depth-anything/'
                             'Video-Depth-Anything-Small', revision='weight-rev')))
        review = self.root / 'review.json'
        write_json(review, dict(schema='plan069-depth-execution-review/v1',
                                proposals=[proposal]))
        approval = self.root / 'approval.json'
        write_json(approval, dict(review=file_record(review),
            candidate_approvals=[dict(candidate='D9', status='approved',
                                      proposal_sha256=object_hash(proposal))]))
        self.request = dict(schema='plan069-depth-setup-request/v1',
            record_kind='fixture', candidate='D9', job_id='plan069-D9-setup-001',
            review=file_record(review), authorization=file_record(approval))

    def tearDown(self):
        self.temp.cleanup()

    def acquire(self, url, path, *, max_bytes, deadline, run_root,
                download_limit, artifact_limit):
        payload = source_archive() if 'codeload.github.com' in url else self.weights
        if len(payload) > max_bytes:
            raise ValueError('fixture transfer exceeds bound')
        path.write_bytes(payload)
        transfers = run_root / 'transfers'
        transfers.mkdir(exist_ok=True)
        write_json(transfers / ('transfer-' + path.name + '.json'), dict(
            transfer_id=path.name, output=str(path), bytes_received=len(payload)))
        return file_record(path)

    def test_exact_source_checkpoint_and_one_use_output(self):
        output = self.root / self.request['job_id']
        result = run_video_setup(self.request, output, acquire=self.acquire)
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(result['checkpoint']['sha256'], hashlib.sha256(self.weights).hexdigest())
        self.assertEqual(result['source_files'], native_source_records(output / 'source'))
        self.assertEqual(result['bytes_received'], len(source_archive()) + len(self.weights))
        with self.assertRaisesRegex(ValueError, 'immutable video setup'):
            run_video_setup(self.request, output, acquire=self.acquire)

    def test_bad_weight_preserves_failure_and_transfer_bytes(self):
        def bad_acquire(url, path, **kwargs):
            original = self.weights
            if 'huggingface.co' in url:
                self.weights = b'bad'
            try:
                return self.acquire(url, path, **kwargs)
            finally:
                self.weights = original
        output = self.root / self.request['job_id']
        with self.assertRaisesRegex(ValueError, 'checkpoint differs'):
            run_video_setup(self.request, output, acquire=bad_acquire)
        self.assertFalse((output / 'result.json').exists())
        self.assertEqual(read_json(output / 'failure.json')['bytes_received'],
                         len(source_archive()) + 3)

    def test_source_traversal_rejected_before_checkpoint(self):
        def bad_source(url, path, **kwargs):
            if 'codeload.github.com' not in url:
                self.fail('checkpoint transfer followed unsafe source')
            payload = source_archive(traversal=True)
            path.write_bytes(payload)
            transfers = kwargs['run_root'] / 'transfers'
            transfers.mkdir(exist_ok=True)
            write_json(transfers / 'transfer-source.tar.gz.json', dict(
                transfer_id='source.tar.gz', output=str(path),
                bytes_received=len(payload)))
            return file_record(path)
        with self.assertRaisesRegex(ValueError, 'unsafe video source archive'):
            run_video_setup(self.request, self.root / self.request['job_id'],
                            acquire=bad_source)

    def runtime_request(self):
        seed, uv = self.root / 'seed/bin/python', self.root / 'uv'
        seed.parent.mkdir(parents=True)
        seed.write_bytes(b'fixture Python 3.11')
        uv.write_bytes(b'fixture uv')
        return environment_request('D9', self.root, seed_executable=seed,
            uv_executable=uv, record_kind='fixture')

    def environment_runner(self, command, *, environment, cwd, timeout, log):
        self.assertGreater(timeout, 0)
        self.assertEqual(environment['CUDA_VISIBLE_DEVICES'], '')
        log.write_text('fixture command only\n')
        if '-c' in command:
            log.write_text('{"python_version":"3.11"}\n')
        if 'venv' in command:
            python = Path(command[-1]) / 'bin/python'
            python.parent.mkdir(parents=True)
            python.write_bytes(b'fixture isolated Python')
        if 'compile' in command:
            Path(command[command.index('--output-file') + 1]).write_text('fixture immutable hash lock\n')
        if '--output' in command:
            versions = dict(torch='2.1.1+cu121', torchvision='0.16.1+cu121', numpy='1.24.0',
                **{'opencv-python': '4.8.1.78', 'matplotlib': '3.7.5', 'pillow': '10.4.0',
                   'imageio': '2.37.0', 'imageio-ffmpeg': '0.4.7', 'decord': '0.6.0',
                   'einops': '0.4.1', 'easydict': '1.13', 'tqdm': '4.67.1', 'OpenEXR': '3.3.1'})
            write_json(command[command.index('--output') + 1], dict(
                executable=str(self.root / self.request['job_id'] / 'runtime/environment/bin/python'),
                versions=dict(python='3.11'), inventory_only=True, model_imports=False,
                gpu_operations=False, packages=[dict(name=name, version=version, files=[])
                                               for name, version in versions.items()]))

    def test_frozen_environment_is_provisioned_inside_the_setup_deadline(self):
        request = dict(self.request, runtime_environment=self.runtime_request())
        output = self.root / request['job_id']
        result = run_video_setup(request, output, acquire=self.acquire,
                                 environment_runner=self.environment_runner)
        runtime = read_json(result['runtime_environment']['path'])
        self.assertEqual(result['python_executable'], str(output / 'runtime/environment/bin/python'))
        self.assertEqual(result['dependency_lock'], runtime['dependency_lock'])
        self.assertEqual(result['inventory'], runtime['inventory'])
        self.assertEqual(result['media_tools'], request['runtime_environment']['media_tools'])
        self.assertIn(file_record(output / 'source/requirements.txt'), runtime['requirement_sources'])
        self.assertNotIn('xformers==0.0.23', read_json(output / 'runtime/request.json')['requirements'])
        with self.assertRaisesRegex(ValueError, 'environment interpreter'):
            setup_environment(result)
        with patch.object(sys, 'executable', result['python_executable']):
            self.assertEqual(setup_environment(result), runtime)

    def test_changed_environment_recipe_is_rejected_before_checkpoint(self):
        runtime = self.runtime_request()
        runtime['constraints'] = ['torch==2.5.1+cu124']
        calls = []
        def acquire(url, path, **kwargs):
            calls.append(url)
            return self.acquire(url, path, **kwargs)
        output = self.root / self.request['job_id']
        with self.assertRaisesRegex(ValueError, 'frozen native recipe'):
            run_video_setup(dict(self.request, runtime_environment=runtime), output, acquire=acquire,
                            environment_runner=self.environment_runner)
        self.assertEqual(len(calls), 1)
        self.assertFalse((output / 'runtime').exists())
        self.assertTrue((output / 'failure.json').is_file())

    def test_environment_failure_preserves_checkpoint_and_command_evidence(self):
        request = dict(self.request, runtime_environment=self.runtime_request())
        output = self.root / request['job_id']
        def failing_runner(command, **kwargs):
            raise RuntimeError('fixture seed interpreter failure')
        with self.assertRaisesRegex(RuntimeError, 'seed interpreter failure'):
            run_video_setup(request, output, acquire=self.acquire, environment_runner=failing_runner)
        self.assertEqual(file_record(output / 'video_depth_anything_vits.pth')['sha256'],
                         hashlib.sha256(self.weights).hexdigest())
        self.assertFalse((output / 'result.json').exists())
        failure = read_json(output / 'runtime/failure.json')
        self.assertEqual(len(failure['command_receipts']), 1)
        self.assertEqual(read_json(output / 'failure.json')['bytes_received'],
                         len(source_archive()) + len(self.weights))


if __name__ == '__main__':
    unittest.main()
