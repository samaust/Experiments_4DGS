"""D8/D11 setup preserves exact source/assets and measured failed transfers."""

from io import BytesIO
import hashlib
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.depth_setup_other import run_setup, SOURCE
from vipe_benchmark.files import file_record, object_hash, read_json, write_json


class OtherDepthSetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.revision = 'a' * 40
        self.weights = b'exact fixture weights'

    def tearDown(self):
        self.temp.cleanup()

    def request(self, candidate, assets):
        inventory = self.root / 'inventory.json'
        write_json(inventory, dict(candidates={candidate: dict(files=assets)}))
        repo, _ = SOURCE[candidate]
        config = dict(code=dict(url='https://github.com/' + repo,
                                revision=self.revision),
                      weights=dict(url='https://huggingface.co/example',
                                   revision=self.revision))
        if candidate == 'D11':
            config['base'] = dict(url='https://huggingface.co/qwen',
                                  revision=self.revision)
        proposal = dict(candidate=candidate, required_assets=file_record(inventory),
            allocation=dict(setup_seconds=1800, download_bytes=300 * 2**20),
            candidate_config=config)
        review = self.root / 'review.json'
        write_json(review, dict(schema='plan069-depth-execution-review/v1',
                                status='REVIEW', proposals=[proposal]))
        approval = self.root / 'approval.json'
        write_json(approval, dict(schema='plan069-depth-user-authorization/v1',
            status='DO', review=file_record(review),
            candidate_approvals=[dict(candidate=candidate, status='approved',
                                      proposal_sha256=object_hash(proposal))]))
        return dict(schema='plan069-depth-setup-request/v1', record_kind='fixture',
            candidate=candidate, job_id=f'plan069-{candidate}-setup-001',
            review=file_record(review), authorization=file_record(approval))

    def archive(self, candidate):
        buffer = BytesIO()
        _, required = SOURCE[candidate]
        data = b'# pinned native source\n'
        with tarfile.open(fileobj=buffer, mode='w:gz') as archive:
            item = tarfile.TarInfo(f'upstream-{self.revision}/{required}')
            item.size = len(data)
            archive.addfile(item, BytesIO(data))
        return buffer.getvalue()

    def acquire(self, candidate, corrupt=False):
        def take(url, path, *, max_bytes, deadline, run_root,
                 download_limit, artifact_limit):
            payload = self.archive(candidate) if 'codeload.github.com' in url else (
                b'corrupt' if corrupt else self.weights)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
            transfer_dir = run_root / 'transfers'
            transfer_dir.mkdir(exist_ok=True)
            write_json(transfer_dir / ('transfer-' + path.name + '.json'), dict(
                transfer_id=path.name, output=str(path), bytes_received=len(payload)))
            return file_record(path)
        return take

    def test_d8_exact_source_and_weights(self):
        asset = dict(repository='metricanything', path='student_pointmap.pt',
                     bytes=len(self.weights),
                     lfs_sha256=hashlib.sha256(self.weights).hexdigest())
        request = self.request('D8', [asset])
        output = self.root / request['job_id']
        result = run_setup(request, output, acquire=self.acquire('D8'))
        self.assertEqual(result['assets'][0]['record'],
                         file_record(output / 'assets/MetricAnything/student_pointmap.pt'))
        self.assertTrue((output / 'source/models/student_pointmap/moge/model/v2.py').is_file())
        self.assertEqual(result['source_manifest']['files'][0]['path'],
                         'models/student_pointmap/moge/model/v2.py')
        self.assertEqual(len(result['source_manifest']['sha256']), 64)
        with self.assertRaisesRegex(ValueError, 'immutable'):
            run_setup(request, output, acquire=self.acquire('D8'))

    def test_d11_checks_small_git_blob_and_preserves_failure(self):
        oid = hashlib.sha1(b'blob ' + str(len(self.weights)).encode() + b'\0' +
                           self.weights).hexdigest()
        assets = [dict(repository='marigold', path='depth/Log-stage2/trainables.safetensors',
                       bytes=len(self.weights),
                       lfs_sha256=hashlib.sha256(self.weights).hexdigest()),
                  dict(repository='qwen', path='transformer/config.json',
                       bytes=len(self.weights), lfs_sha256=None, git_oid=oid)]
        request = self.request('D11', assets)
        result = run_setup(request, self.root / request['job_id'],
                           acquire=self.acquire('D11'))
        self.assertEqual(len(result['assets']), 2)
        self.assertEqual(result['candidate'], 'D11')

        other = self.root / 'failed' / request['job_id']
        with self.assertRaisesRegex(ValueError, 'pinned asset byte count'):
            run_setup(request, other, acquire=self.acquire('D11', corrupt=True))
        self.assertEqual(read_json(other / 'failure.json')['status'], 'failed')
        self.assertFalse((other / 'result.json').exists())


if __name__ == '__main__':
    unittest.main()
