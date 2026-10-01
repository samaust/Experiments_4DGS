"""CPU-only exact-evidence and live-cap gates for fresh depth allocations."""

from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark import depth_admission as admission
from vipe_benchmark.config import load
from vipe_benchmark.files import file_record, object_hash, read_json, write_json


class DepthAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.original_inventory = admission.INVENTORY
        self.asset = self.root / 'model.bin'
        self.asset.write_bytes(b'pinned model')
        self.expected = dict(repository='fixture', path='model.bin',
                             bytes=self.asset.stat().st_size,
                             lfs_sha256=file_record(self.asset)['sha256'], git_oid='fixture')
        self.inventory = self.root / 'inventory.json'
        write_json(self.inventory, dict(schema='plan069-required-inference-assets/v1',
            candidates={'D5': dict(files=[self.expected], expected_bytes=self.expected['bytes'])}))
        admission.INVENTORY = self.inventory
        self.config = load()
        candidate = read_json(admission.CONFIG)['candidates']['D5']
        self.proposal = dict(schema='plan069-depth-execution-proposal/v1',
            status='REVIEW', candidate='D5', candidate_config=candidate,
            required_assets=file_record(self.inventory), independent_review='passed',
            qualification='passed', max_attempts=1,
            workload=dict(anchor_maps=60, unique_published_maps=256,
                native_context_frames=256, clips=4, clip_frames=50, clip_fps=25),
            profile=read_json(admission.PROFILES)['profiles']['D5'],
            profile_inventory=file_record(admission.PROFILES),
            allocation=dict(download_bytes=20,
                artifact_bytes=100, gpu_seconds=100, cpu_seconds=100,
                setup_seconds=100, device_bytes=2**30))
        write_json(self.root / 'review.json', dict(
            schema='plan069-depth-source-review/v1', candidate='D5', status='passed',
            source_revision=candidate['code']['revision'],
            profile_inventory=file_record(admission.PROFILES)))
        self.proposal['review_receipt'] = file_record(self.root / 'review.json')
        self.commercial = dict(candidate='D5', code='allowed', weights='allowed',
            dependencies='allowed', inference_outputs='allowed',
            source_revision=candidate['code']['revision'],
            weights_revision=candidate['weights']['revision'])
        write_json(self.root / 'assessment.json', dict(
            schema='plan069-depth-commercial-assessment/v1', **self.commercial,
            primary_sources=['https://github.com/example/code',
                             'https://huggingface.co/example/weights']))
        self.commercial['assessment'] = file_record(self.root / 'assessment.json')
        self.assets = [dict(repository='fixture', path='model.bin',
                            record=file_record(self.asset))]
        self.runtime = dict(candidate='D5', status='passed',
            source_revision=candidate['code']['revision'],
            config=file_record(admission.CONFIG))
        write_json(self.root / 'qualification.json', dict(
            schema='plan069-depth-runtime-qualification/v1', **self.runtime,
            assets=self.assets, profile=self.proposal['profile']))
        self.runtime['receipt'] = file_record(self.root / 'qualification.json')
        self.live = dict(fresh=True, active_gpu_owner=None, active_reservations=[],
            device_peak_bytes=0, used={key: 0 for key in admission.LIMIT_KEYS},
            reserved={key: 0 for key in admission.LIMIT_KEYS})
        self.approval = dict(schema='plan069-depth-execution-approval/v1',
            status='approved', candidate='D5',
            proposal_sha256=object_hash(self.proposal))

    def tearDown(self):
        admission.INVENTORY = self.original_inventory
        self.temp.cleanup()

    def decide(self, **changed):
        state = dict(proposal=self.proposal, config=self.config,
            commercial=self.commercial, assets=self.assets, runtime=self.runtime,
            live=self.live, approval=self.approval)
        state.update(changed)
        return admission.review(**state)

    def test_complete_exact_evidence_and_live_capacity_can_pass(self):
        self.assertEqual(self.decide(), [])

    def test_missing_commercial_dependency_and_asset_blocks(self):
        self.assertIn('exact commercial permissions unresolved',
            self.decide(commercial=dict(self.commercial, dependencies='unverified')))
        self.assertTrue(any('missing asset' in reason for reason in self.decide(assets=[])))

    def test_stale_runtime_and_missing_approval_block(self):
        self.assertIn('exact runtime qualification missing or stale',
            self.decide(runtime=dict(self.runtime, status='stale')))
        self.assertIn('explicit applicable allocation approval missing',
            self.decide(approval=None))

    def test_owned_gpu_and_exhausted_live_cap_block(self):
        self.assertIn('single GPU or reservation already owned',
            self.decide(live=dict(self.live, active_gpu_owner='S1-010')))
        used = dict(self.live['used'], download_bytes=self.config['new_download_gib_limit'] * 2**30)
        self.assertTrue(any('download_bytes allocation' in reason for reason in
            self.decide(live=dict(self.live, used=used))))

    def test_workload_and_profile_substitution_block(self):
        changed = dict(self.proposal, workload=dict(self.proposal['workload'],
            native_context_frames=60))
        self.assertIn('bounded candidate workload or attempt count changed',
            self.decide(proposal=changed))
        changed = dict(self.proposal, profile=dict(self.proposal['profile'],
            precision='float16'))
        self.assertIn('frozen native preprocessing, precision or seed profile changed',
            self.decide(proposal=changed))


if __name__ == '__main__':
    unittest.main()
