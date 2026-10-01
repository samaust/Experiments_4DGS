"""A bounded D7 setup preserves exact source, checkpoint and failure bytes."""

from io import BytesIO
import hashlib
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.depth_setup import run_d7_setup
from vipe_benchmark.files import file_record, object_hash, read_json, write_json


def archive_bytes(name='Depth-Anything-V2-abc/metric_depth/depth_anything_v2/dpt.py'):
    buffer = BytesIO()
    payload = b'class DepthAnythingV2: pass\n'
    with tarfile.open(fileobj=buffer, mode='w:gz') as archive:
        member = tarfile.TarInfo(name)
        member.size = len(payload)
        archive.addfile(member, BytesIO(payload))
    return buffer.getvalue()


class DepthSetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.weight = b'pinned fixture checkpoint'
        asset = dict(repository='dav2metric',
            path='depth_anything_v2_metric_hypersim_vits.pth',
            bytes=len(self.weight), lfs_sha256=hashlib.sha256(self.weight).hexdigest())
        inventory = self.root / 'inventory.json'
        write_json(inventory, dict(candidates={'D7': dict(files=[asset])}))
        proposal = dict(candidate='D7', required_assets=file_record(inventory),
            allocation=dict(setup_seconds=1800, download_bytes=1000),
            candidate_config=dict(code=dict(revision='abc'),
                                  weights=dict(url='https://huggingface.co/example', revision='def')))
        review = self.root / 'review.json'
        write_json(review, dict(schema='plan069-depth-execution-review/v1',
                                proposals=[proposal]))
        approval = self.root / 'approval.json'
        write_json(approval, dict(review=file_record(review),
            candidate_approvals=[dict(candidate='D7', status='approved',
                                      proposal_sha256=object_hash(proposal))]))
        self.request = dict(schema='plan069-depth-setup-request/v1',
            record_kind='fixture', candidate='D7', job_id='plan069-D7-setup-001',
            review=file_record(review), authorization=file_record(approval))

    def tearDown(self):
        self.temp.cleanup()

    def test_exact_fixture_bytes_publish_once_without_gpu(self):
        def acquire(url, path, *, max_bytes, deadline, run_root,
                    download_limit, artifact_limit):
            payload = archive_bytes() if 'codeload.github.com' in url else self.weight
            self.assertLessEqual(len(payload), max_bytes)
            path.write_bytes(payload)
            transfer_dir = run_root / 'transfers'
            transfer_dir.mkdir(exist_ok=True)
            write_json(transfer_dir / ('transfer-' + path.name + '.json'), dict(
                transfer_id=path.name, output=str(path), bytes_received=len(payload)))
            return file_record(path)
        output = self.root / self.request['job_id']
        result = run_d7_setup(self.request, output, acquire=acquire)
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(result['bytes_received'],
                         len(archive_bytes()) + len(self.weight))
        self.assertEqual(result['checkpoint'], file_record(output /
            'depth_anything_v2_metric_hypersim_vits.pth'))
        self.assertTrue((output / 'source/metric_depth/depth_anything_v2/dpt.py').is_file())
        with self.assertRaisesRegex(ValueError, 'immutable D7 setup output'):
            run_d7_setup(self.request, output, acquire=acquire)

    def test_bad_checkpoint_preserves_failed_attempt_and_received_bytes(self):
        def acquire(url, path, *, max_bytes, deadline, run_root,
                    download_limit, artifact_limit):
            payload = archive_bytes() if 'codeload.github.com' in url else b'bad'
            path.write_bytes(payload)
            transfer_dir = run_root / 'transfers'
            transfer_dir.mkdir(exist_ok=True)
            write_json(transfer_dir / ('transfer-' + path.name + '.json'), dict(
                transfer_id=path.name, output=str(path), bytes_received=len(payload)))
            return file_record(path)
        output = self.root / self.request['job_id']
        with self.assertRaisesRegex(ValueError, 'checkpoint bytes differ'):
            run_d7_setup(self.request, output, acquire=acquire)
        failure = read_json(output / 'failure.json')
        self.assertEqual(failure['bytes_received'], len(archive_bytes()) + 3)
        self.assertFalse((output / 'result.json').exists())

    def test_source_archive_traversal_is_rejected(self):
        def acquire(url, path, *, max_bytes, deadline, run_root,
                    download_limit, artifact_limit):
            payload = archive_bytes('Depth-Anything-V2-abc/../escape.py') if (
                'codeload.github.com' in url) else self.weight
            path.write_bytes(payload)
            transfer_dir = run_root / 'transfers'
            transfer_dir.mkdir(exist_ok=True)
            write_json(transfer_dir / ('transfer-' + path.name + '.json'), dict(
                transfer_id=path.name, output=str(path), bytes_received=len(payload)))
            return file_record(path)
        with self.assertRaisesRegex(ValueError, 'unsafe source archive'):
            run_d7_setup(self.request, self.root / self.request['job_id'], acquire=acquire)


if __name__ == '__main__':
    unittest.main()
