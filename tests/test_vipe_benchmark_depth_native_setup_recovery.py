"""D8 setup-recovery authority at the ledger authorization seam (CPU fixtures only)."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vipe_benchmark.config import ROOT, load
from vipe_benchmark.files import file_record, object_hash, write_json

ORIGINAL = 'plan069-D8-setup-001'
JOB = 'plan069-D8-setup-recovery-001'
CLEAN = dict(cleanup_confirmed=True, cleanup_uncertain=False, surviving_pids=[], deadline_exceeded=False)
WHEELS = [dict(name='moderngl', version='5.12.0', url='https://files.example/moderngl.whl',
               sha256='7fc0f8788bc84433d2124e9a4893adbe40f93c7d213abb8ad7b909540cb0161f', bytes=293468),
          dict(name='glcontext', version='3.0.0', url='https://files.example/glcontext.whl',
               sha256='7fa413f4420abff2bbb5aa5770a3e1deffcdc13e0ef2f459b145fa79c36909e7', bytes=51680)]


class NativeSetupRecoveryAuthorityTests(unittest.TestCase):
    def setUp(self):
        from vipe_benchmark.depth_admission import local_source_records
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.run_root = Path(temp.name) / 'run'
        job = self.run_root / 'jobs' / ORIGINAL
        (job / 'runtime').mkdir(parents=True)
        (self.run_root / 'requests').mkdir()
        self.environment = dict(schema='plan069-depth-environment-request/v1', candidate='D8',
                                record_kind='actual', requirements=['moderngl==5.12.0', 'glcontext==3.0.0'])
        adapter = patch('vipe_benchmark.depth_native_runtime.recipe', return_value=self.environment)
        adapter.start()
        self.addCleanup(adapter.stop)
        self.maps = dict(candidate='D8', max_attempts=1, allocation=dict(
            setup_seconds=1800, download_bytes=7747448624, artifact_bytes=9663676416, gpu_seconds=3600))
        review002 = self.write('review002.json', dict(schema='plan069-depth-execution-review/v1',
                                                      status='REVIEW', proposals=[self.maps]))
        do002 = self.write('do002.json', dict(schema='plan069-depth-user-authorization/v1', status='DO',
            review=review002, candidate_approvals=[dict(candidate='D8', status='approved', max_attempts=1,
                proposal_sha256=object_hash(self.maps))]))
        request = self.write('requests/' + ORIGINAL + '.json', dict(schema='plan069-depth-setup-request/v1',
            record_kind='actual', candidate='D8', job_id=ORIGINAL, ledger_path=str(self.run_root / 'ledger.jsonl'),
            review=review002, authorization=do002))
        retained = dict(source_archive=self.raw('jobs/%s/source.tar.gz' % ORIGINAL),
            utils3d_archive=self.raw('jobs/%s/utils3d-source.tar.gz' % ORIGINAL),
            dependency_lock=self.raw('jobs/%s/runtime/requirements.lock' % ORIGINAL),
            setup_failure=self.write('jobs/%s/failure.json' % ORIGINAL, dict(
                schema='plan069-depth-setup-failure/v1', candidate='D8', job_id=ORIGINAL, status='failed')),
            runtime_failure=self.write('jobs/%s/runtime/failure.json' % ORIGINAL, dict(
                schema='plan069-depth-environment-failure/v1', candidate='D8', status='failed',
                record_kind='actual')))
        snapshot = dict(download_bytes=10, artifact_bytes=20)
        self.rows: list[dict] = []
        self.append(dict(event='depth_setup_authorized', candidate='D8', review=review002, authorization=do002,
                         proposal_sha256=object_hash(self.maps), resource_snapshot=snapshot))
        self.append(dict(event='reserve', job_id=ORIGINAL, resource='setup', seconds=1800,
                         evidence=dict(request=request)))
        self.append(dict(event='finish', job_id=ORIGINAL, resource='setup', status='failed',
                         elapsed_seconds=215.3, **CLEAN))
        self.original = dict(grant_event_sha256=self.rows[0]['event_sha256'],
                             failed_finish_event_sha256=self.rows[2]['event_sha256'], request=request, **retained)
        self.proposal = dict(schema='plan069-depth-setup-recovery-proposal/v1', candidate='D8', job_id=JOB,
            max_attempts=1, recovery_seconds=1200, original_setup=self.original,
            map_proposal_sha256=object_hash(self.maps), runtime_recipe=self.environment, acquisitions=WHEELS)
        self.worker = file_record(ROOT / 'scripts/basketball_vipe_depth_setup_recovery.py')
        self.sources = local_source_records('D8')
        self.approve()

    def raw(self, relative, data=b'retained'):
        path = self.run_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return file_record(path)

    def write(self, relative, value):
        path = self.run_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            path.unlink()
        write_json(path, value)
        return file_record(path)

    def append(self, data):
        row = dict(data, sequence=len(self.rows), recorded_unix=1.,
                   previous_sha256=self.rows[-1]['event_sha256'] if self.rows else None)
        row['event_sha256'] = object_hash(row)
        self.rows.append(row)
        (self.run_root / 'ledger.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in self.rows))

    def approve(self, *, status='DO', approval=None, request_changes=None):
        review = self.write('recovery-review.json', dict(schema='plan069-depth-execution-review/v1',
            status='REVIEW', proposals=[], setup_recovery_proposal=self.proposal))
        granted = dict(candidate='D8', job_id=JOB, status='approved', max_attempts=1,
                       proposal_sha256=object_hash(self.proposal))
        self.do = self.write('recovery-do.json', dict(schema='plan069-depth-user-authorization/v1', status=status,
            review=review, setup_recovery_approval=granted if approval is None else approval))
        source = self.write('source-review.json', dict(schema='plan069-depth-source-review/v1', status='passed',
            candidate='D8', reviewer='fixture', local_sources=self.sources,
            setup_recovery_proposal_sha256=object_hash(self.proposal)))
        request = dict(schema='plan069-depth-setup-recovery-request/v1', record_kind='actual', candidate='D8',
            job_id=JOB, ledger_path=str(self.run_root / 'ledger.jsonl'), review=review, authorization=self.do,
            source_review=source, original_setup=self.original, runtime_environment=self.environment,
            acquisitions=WHEELS)
        request.update(request_changes or {})
        self.request = self.write('requests/' + JOB + '.json', request)

    def authorize(self):
        from vipe_benchmark.ledger import Ledger
        ledger = Ledger(self.run_root / 'ledger.jsonl', dict(load(), new_download_gib_limit=110,
                                                         new_artifact_disk_gib_limit=210))
        command = [sys.executable, self.worker['path'], '--request', self.request['path'],
                   '--output', str(self.run_root / 'jobs' / JOB)]
        with patch('vipe_benchmark.execution.resources',
                   return_value=dict(download_bytes=10, artifact_bytes=20, gpu_pids=[])):
            return ledger.authorize_depth_setup_recovery(self.request, command=command, worker=self.worker,
                                                         executable=file_record(sys.executable))

    def assert_refused(self, pattern):
        before = (self.run_root / 'ledger.jsonl').read_bytes()
        with self.assertRaisesRegex(ValueError, pattern):
            self.authorize()
        self.assertEqual((self.run_root / 'ledger.jsonl').read_bytes(), before)

    def test_exact_failed_ancestry_and_explicit_do_authorize_one_d8_recovery(self):
        event = self.authorize()
        self.assertEqual((event['event'], event['candidate'], event['job_id'], event['seconds']),
                         ('depth_setup_recovery_authorized', 'D8', JOB, 1200))
        self.assertEqual(event['acquisitions'], WHEELS)
        with self.assertRaisesRegex(ValueError, 'already authorized or consumed'):
            self.authorize()

    def test_review_only_or_missing_approval_is_refused(self):
        self.approve(status='REVIEW')
        self.assert_refused('explicit separately approved one-attempt recovery')
        self.approve(approval={})
        self.assert_refused('explicit separately approved one-attempt recovery')

    def test_changed_recipe_or_acquisitions_are_refused(self):
        self.approve(request_changes=dict(runtime_environment=dict(self.environment, requirements=[])))
        self.assert_refused('reviewed amended recovery environment')
        extra = copy.deepcopy(WHEELS) + [dict(WHEELS[0], name='other')]
        self.approve(request_changes=dict(acquisitions=extra))
        self.assert_refused('exact reviewed acquisition allowlist')

    def test_unbound_or_completed_original_is_refused(self):
        self.original = dict(self.original, failed_finish_event_sha256='0' * 64)
        self.proposal['original_setup'] = self.original
        self.approve()
        self.assert_refused('confirmed cleanup')

    def test_active_reservation_is_refused(self):
        self.append(dict(event='reserve', job_id='foreign', resource='cpu', seconds=1))
        self.approve()
        self.assert_refused('active attempt')

    def test_recovery_time_must_fit_the_original_setup_allowance(self):
        self.proposal['recovery_seconds'] = 1700
        self.approve()
        self.assert_refused('original remaining candidate allowance')


if __name__ == '__main__':
    unittest.main()
