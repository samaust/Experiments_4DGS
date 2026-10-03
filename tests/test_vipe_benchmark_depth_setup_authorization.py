"""Approved depth setup consumes one ledger identity and blocks overlap."""

from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.config import ROOT, load
from vipe_benchmark.files import file_record, read_json, write_json
from vipe_benchmark.ledger import Ledger
from vipe_benchmark.depth_admission import local_source_records
from unittest.mock import patch


REVIEW = ROOT / 'docs/specs/plan031-execution/depth-execution-review-001.json'
DO = ROOT / 'docs/research/vipe-alternatives/plan031-execution/depth-approval-001.json'
REVIEW = Path(read_json(DO)['review']['path'])


def source_review(root, candidate):
    proposal = next(row for row in read_json(REVIEW)['proposals']
                    if row['candidate'] == candidate)
    path = root / (candidate + '-review.json')
    write_json(path, dict(schema='plan069-depth-source-review/v1',
        status='passed', candidate=candidate, reviewer='independent fixture reviewer',
        source_revision=proposal['candidate_config']['code']['revision'],
        profile_inventory=proposal['profile_inventory'],
        local_sources=local_source_records(candidate)))
    return file_record(path)


class DepthSetupAuthorizationTests(unittest.TestCase):
    def test_depth_gpu_slot_requires_fresh_head_and_is_one_use(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger = Ledger(root / 'ledger.jsonl', load())
            review, approved = file_record(REVIEW), file_record(DO)
            source = source_review(root, 'D7')
            proposal = next(row for row in read_json(REVIEW)['proposals']
                            if row['candidate'] == 'D7')
            from vipe_benchmark.files import object_hash
            def admit(head, path):
                write_json(path, dict(schema='plan069-depth-admission-result/v1',
                    status='passed', candidate='D7', proposal_sha256=object_hash(proposal),
                    review=review, authorization=approved, source_review=source,
                    commercial={}, assets=[], runtime={},
                    live=dict(ledger_head_sha256=head)))
                return file_record(path)
            def binding(admission):
                request_path = root / 'requests/plan069-D7-maps-001.json'
                request_path.unlink(missing_ok=True)
                write_json(request_path, dict(candidate='D7', job_id='plan069-D7-maps-001',
                    record_kind='actual', review=review, authorization=approved,
                    source_review=source, admission=admission))
                worker = file_record(ROOT / 'scripts/basketball_vipe_depth_d7_maps.py')
                executable = file_record(sys.executable)
                return dict(command=[sys.executable, worker['path'], '--request',
                    str(request_path), '--output', str(root / 'jobs/plan069-D7-maps-001')],
                    request=file_record(request_path), worker=worker, executable=executable)
            stale = admit('f' * 64, root / 'stale.json')
            current = admit('0' * 64, root / 'current.json')
            reading = dict(gpu_pids=[], download_bytes=0, artifact_bytes=0,
                           device_bytes=0)
            with patch('vipe_benchmark.depth_admission.review', return_value=[]), \
                 patch('vipe_benchmark.execution.resources', return_value=reading):
                with self.assertRaisesRegex(ValueError, 'ledger head is stale'):
                    ledger.authorize_depth_attempt('D7', review, approved, source, stale, **binding(stale))
                self.assertEqual(ledger.events(), [])
                bad_command = binding(current)
                bad_command['command'] = ['unreviewed-worker']
                with self.assertRaisesRegex(ValueError, 'command binding'):
                    ledger.authorize_depth_attempt('D7', review, approved, source,
                        current, **bad_command)
                for field, record in [('review', review), ('authorization', approved)]:
                    changed = read_json(record['path'])
                    changed['status'] = 'passed'
                    path = root / (field + '-invalid-status.json')
                    write_json(path, changed)
                    with self.assertRaisesRegex(ValueError, 'exact approved depth attempt'):
                        ledger.authorize_depth_attempt('D7',
                            file_record(path) if field == 'review' else review,
                            file_record(path) if field == 'authorization' else approved,
                            source, current, **binding(current))
                self.assertEqual(ledger.events(), [])
                with patch('vipe_benchmark.execution.resources', return_value=dict(reading, gpu_pids=[123])):
                    with self.assertRaisesRegex(ValueError, 'GPU owner active before depth allocation'):
                        ledger.authorize_depth_attempt('D7', review, approved, source,
                                                       current, **binding(current))
                self.assertEqual(ledger.events(), [])
                ledger.authorize_depth_attempt('D7', review, approved, source, current, **binding(current))
                self.assertEqual(ledger.jobs['plan069-D7-maps-001']['seconds'], 3600)
                with self.assertRaisesRegex(ValueError, 'already authorized'):
                    ledger.authorize_depth_attempt('D7', review, approved, source, current, **binding(current))
                exact = binding(current)
                evidence = dict(exact, admission=current, review=review,
                    authorization=approved, source_review=source)
                evidence.pop('command')
                with self.assertRaisesRegex(ValueError, 'command differs'):
                    ledger.reserve('plan069-D7-maps-001', ['fixture'], evidence)
                ledger.reserve('plan069-D7-maps-001', exact['command'], evidence)
                ledger.finish('plan069-D7-maps-001', 'failed', 1)
                with self.assertRaisesRegex(ValueError, 'already consumed'):
                    ledger.reserve('plan069-D7-maps-001', ['no-retry'], current)

    def test_established_worker_names_are_bound_to_exact_candidate_commands(self):
        from vipe_benchmark.files import object_hash
        workers = dict(D2='basketball_vipe_d2_maps.py',
            D9='basketball_vipe_video_actual.py', D10='basketball_vipe_video_actual.py')
        for candidate, name in workers.items():
            with self.subTest(candidate=candidate), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                ledger = Ledger(root / 'ledger.jsonl', load())
                review, authorization = file_record(REVIEW), file_record(DO)
                source = source_review(root, candidate)
                proposal = next(row for row in read_json(REVIEW)['proposals']
                                if row['candidate'] == candidate)
                admission_path = root / 'admission.json'
                write_json(admission_path, dict(schema='plan069-depth-admission-result/v1',
                    status='passed', candidate=candidate, proposal_sha256=object_hash(proposal),
                    review=review, authorization=authorization, source_review=source,
                    commercial={}, assets=[], runtime={}, live=dict(ledger_head_sha256='0' * 64)))
                admission = file_record(admission_path)
                job = f'plan069-{candidate}-maps-001'
                request_path = root / 'requests' / (job + '.json')
                write_json(request_path, dict(candidate=candidate, job_id=job, record_kind='actual',
                    review=review, authorization=authorization, source_review=source, admission=admission))
                worker = file_record(ROOT / 'scripts' / name)
                binding = dict(request=file_record(request_path), worker=worker,
                    executable=file_record(sys.executable), command=[sys.executable,
                        worker['path'], '--request', str(request_path), '--output', str(root / 'jobs' / job)])
                reading = dict(gpu_pids=[], download_bytes=0, artifact_bytes=0, device_bytes=0)
                with patch('vipe_benchmark.depth_admission.review', return_value=[]), \
                     patch('vipe_benchmark.execution.resources', return_value=reading):
                    substituted = dict(binding, command=[sys.executable, worker['path'],
                        '--request', str(request_path), '--output', str(root / 'other-output')])
                    with self.assertRaisesRegex(ValueError, 'command binding'):
                        ledger.authorize_depth_attempt(candidate, review, authorization, source,
                                                       admission, **substituted)
                    self.assertEqual(ledger.events(), [])
                    ledger.authorize_depth_attempt(candidate, review, authorization, source,
                                                   admission, **binding)
                    reservation = dict(binding, review=review, authorization=authorization,
                        source_review=source, admission=admission)
                    reservation.pop('command')
                    self.assertEqual(ledger.reserve(job, binding['command'], reservation)['event'], 'reserve')

    def test_exact_approval_allocates_once_and_reservation_blocks_overlap(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory) / 'ledger.jsonl', load())
            review, approved = file_record(REVIEW), file_record(DO)
            d7_review = source_review(Path(directory), 'D7')
            ledger.authorize_depth_setup('D7', review, approved, d7_review)
            self.assertEqual(ledger.jobs['plan069-D7-setup-001']['seconds'], 1800)
            with self.assertRaisesRegex(ValueError, 'unstarted depth setup'):
                ledger.authorize_depth_setup('D5', review, approved,
                    source_review(Path(directory), 'D5'))
            with self.assertRaisesRegex(ValueError, 'already authorized'):
                ledger.authorize_depth_setup('D7', review, approved, d7_review)
            ledger.reserve('plan069-D7-setup-001', ['bounded-setup'], approved)
            with self.assertRaisesRegex(ValueError, 'unreconciled active attempt'):
                ledger.reserve('S1-calibration', ['forbidden-overlap'], approved)
            ledger.finish('plan069-D7-setup-001', 'failed', 1)
            with self.assertRaisesRegex(ValueError, 'already consumed'):
                ledger.reserve('plan069-D7-setup-001', ['forbidden-retry'], approved)

    def test_changed_grant_cannot_allocate_setup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger = Ledger(root / 'ledger.jsonl', load())
            altered = read_json(DO)
            altered['candidate_approvals'][3]['proposal_sha256'] = '0' * 64
            write_json(root / 'altered.json', altered)
            with self.assertRaisesRegex(ValueError, 'exact approved depth setup'):
                ledger.authorize_depth_setup('D7', file_record(REVIEW),
                    file_record(root / 'altered.json'), source_review(root, 'D7'))
            self.assertEqual(ledger.events(), [])

    def test_amended_caps_must_match_approved_record_and_live_headroom(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = dict(load(), new_download_gib_limit=110,
                          new_artifact_disk_gib_limit=210)
            ledger = Ledger(root / 'ledger.jsonl', config)
            review = file_record(REVIEW)
            approval = read_json(DO)
            from vipe_benchmark.depth_admission import CAP_AMENDMENT
            approval['cap_amendment'] = file_record(CAP_AMENDMENT)
            write_json(root / 'approved.json', approval)
            approved = file_record(root / 'approved.json')
            d7_review = source_review(root, 'D7')
            altered = read_json(DO)
            altered['cap_approval']['amendment_sha256'] = '0' * 64
            write_json(root / 'invalid-cap.json', altered)
            with self.assertRaisesRegex(ValueError, 'exact approved depth cap amendment'):
                ledger.authorize_depth_setup('D7', review,
                    file_record(root / 'invalid-cap.json'), d7_review)
            with patch('vipe_benchmark.execution.resources', return_value=dict(
                    download_bytes=110 * 2**30, artifact_bytes=0)):
                with self.assertRaisesRegex(ValueError, 'download_bytes setup allocation'):
                    ledger.authorize_depth_setup('D7', review, approved,
                        d7_review)
            self.assertEqual(ledger.events(), [])


if __name__ == '__main__':
    unittest.main()
