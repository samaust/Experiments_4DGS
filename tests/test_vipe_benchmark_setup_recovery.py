"""Synthetic recovery accounting/handoff fixtures; no network or model runs."""
import io
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.config import load
from vipe_benchmark.execution import result_record, setup_result_record
from vipe_benchmark.files import file_record, read_json, write_json
from vipe_benchmark.ledger import Ledger
from vipe_benchmark import runtime, setup_recipes


class SetupRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.config = load()
        self.ledger = Ledger(self.root / 'ledger.jsonl', self.config)
        self.ledger.reserve('E3-setup', ['fixture'], {})
        self.failure = self.ledger.finish('E3-setup', 'failed', 13.5, cleanup_confirmed=True)
        self.ledger.account('E4-setup', 'blocked', 'separate network stop')
        self.ledger.account('S3-calibration', 'blocked', 'original E3 failure')
        write_json(self.root / 'qualification/historical-assets.json',
                   dict(assets={'vipe_source': {'path': str(self.root / 'historical-vipe')}}, parent={}))
        archive = self.root / 'preparation/source.tar.gz'
        archive.parent.mkdir()
        revision = '660a5e9e1b8b4c02c0ad97229b88a09a6e4ff5b7'
        with tarfile.open(archive, 'w:gz') as stream:
            for name, data in [('module.py', b'VALUE = 1\n'),
                               ('sam3/assets/bpe_simple_vocab_16e6.txt.gz', b'fixture vocabulary')]:
                member = tarfile.TarInfo(f'sam3-{revision}/{name}')
                member.size = len(data)
                stream.addfile(member, io.BytesIO(data))
        source = runtime.extract_source(archive, self.root / 'preparation/source', revision)
        source['archive'] = file_record(archive)
        checkpoint = self.root / 'preparation/sam3.pt'
        checkpoint.write_bytes(b'fixture weights')
        self.assets = dict(sam3_source=source, sam3_checkpoint=file_record(checkpoint),
            bpe_vocabulary=file_record(self.root / 'preparation/source/sam3/assets/bpe_simple_vocab_16e6.txt.gz'))
        write_json(self.root / 'preparation/assets.json', self.assets)
        write_json(self.root / 'preparation/result.json', dict(status='complete',
            environment_builds=0, model_forwards=0, elapsed_seconds=20.,
            assets=file_record(self.root / 'preparation/assets.json')))
        self.document = dict(schema='vipe-benchmark-sam3-recovery/v1',
            job_id='E3-setup-recovery-001', original_job_id='E3-setup', environment='E3',
            recovery_attempts_limit=1, setup_wall_seconds_limit=self.config['setup_wall_seconds_limit'],
            reset_previous_consumption=False, changes_to_prescribed_runtime=False,
            sam3_access_resolved=True, unrelated_attempts_reopened=False,
            authorization='Synthetic explicit access-granted/continue instruction',
            asset_preparation=file_record(self.root / 'preparation/result.json'),
            original_failure_event_sha256=self.failure['event_sha256'])

    def authorization(self, **changes):
        path = self.root / f'authorization-{len(list(self.root.glob("authorization-*.json")))}.json'
        write_json(path, dict(self.document, **changes))
        return file_record(path)

    def test_recovery_keeps_failed_history_and_counts_new_process_and_acquisition(self):
        original_bytes = self.ledger.path.read_bytes()
        self.ledger.authorize_setup_recovery(self.authorization())
        restarted = Ledger(self.ledger.path, self.config)
        self.assertEqual(restarted.states()['E3-setup'], self.failure)
        self.assertTrue(self.ledger.path.read_bytes().startswith(original_bytes))
        self.assertEqual(restarted.states()['E4-setup']['status'], 'blocked')
        reservation = restarted.reserve('E3-setup-recovery-001', ['fixture'], {})
        self.assertEqual(reservation['seconds'], 57600. - 13.5 - 20.)
        restarted.finish('E3-setup-recovery-001', 'failed', 3., cleanup_confirmed=True)
        self.assertEqual(restarted.totals()['setup']['attempts'], 2)
        self.assertEqual(restarted.totals()['setup']['elapsed_seconds'], 36.5)
        self.assertEqual(restarted.totals()['gpu']['attempts'], 0)

    def test_no_unregistered_recovery_and_no_generic_note_bypass(self):
        with self.assertRaisesRegex(ValueError, 'unallocated'):
            self.ledger.reserve('E3-setup-recovery-001', [], {})
        with self.assertRaisesRegex(ValueError, 'checked ledger'):
            self.ledger.note('setup_recovery_authorized', job_id='E3-setup-recovery-001')

    def test_consumed_original_and_recovery_cannot_be_reopened(self):
        authorization = self.authorization()
        self.ledger.authorize_setup_recovery(authorization)
        with self.assertRaisesRegex(ValueError, 'already allocated'):
            self.ledger.authorize_setup_recovery(authorization)
        self.ledger.reserve('E3-setup-recovery-001', [], {})
        self.ledger.finish('E3-setup-recovery-001', 'failed', 1., cleanup_confirmed=True)
        for job in ('E3-setup', 'E3-setup-recovery-001'):
            with self.subTest(job=job), self.assertRaisesRegex(ValueError, 'consumed attempts'):
                self.ledger.resume_unstarted([job], 'fixture explicit resume')
            with self.assertRaisesRegex(ValueError, 'already consumed'):
                self.ledger.reserve(job, [], {})
        self.ledger.resume_unstarted(['S3-calibration'], 'fixture continue original unstarted branch')
        self.assertNotIn('S3-calibration', self.ledger.states())

    def test_other_environment_extra_attempts_time_reset_or_missing_resolution_rejected(self):
        for change in [dict(environment='E4'), dict(job_id='E3-setup-recovery-002'),
                       dict(recovery_attempts_limit=2), dict(setup_wall_seconds_limit=60000),
                       dict(reset_previous_consumption=True), dict(sam3_access_resolved=False),
                       dict(unrelated_attempts_reopened=True), dict(authorization='')]:
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'exact explicit SAM3'):
                self.ledger.authorize_setup_recovery(self.authorization(**change))

    def test_wrong_failure_or_incomplete_preparation_rejected(self):
        with self.assertRaisesRegex(ValueError, 'preserved, cleaned-up E3 failure'):
            self.ledger.authorize_setup_recovery(self.authorization(original_failure_event_sha256='0' * 64))
        write_json(self.root / 'bad-preparation.json', dict(status='failed', environment_builds=0, model_forwards=0))
        with self.assertRaisesRegex(ValueError, 'completed asset-only'):
            self.ledger.authorize_setup_recovery(self.authorization(
                asset_preparation=file_record(self.root / 'bad-preparation.json')))

    def test_cumulative_cap_includes_recovery_preparation(self):
        self.config['setup_wall_seconds_limit'] = 33.5
        with self.assertRaisesRegex(ValueError, 'cumulative setup allocation exhausted'):
            self.ledger.authorize_setup_recovery(self.authorization(setup_wall_seconds_limit=33.5))

    def test_active_process_prevents_recovery_registration(self):
        self.ledger.reserve('E5-setup', [], {})
        with self.assertRaisesRegex(ValueError, 'unreconciled active attempt'):
            self.ledger.authorize_setup_recovery(self.authorization())

    def test_authorization_tampering_prevents_reservation(self):
        record = self.authorization()
        self.ledger.authorize_setup_recovery(record)
        Path(record['path']).write_text('{}')
        with self.assertRaisesRegex(ValueError, 'changed file'):
            self.ledger.reserve('E3-setup-recovery-001', [], {})

    def test_orphan_recovery_result_never_qualifies_and_success_does_not_relabel_original(self):
        path = self.root / 'jobs/E3-setup-recovery-001/result.json'
        write_json(path.parent / 'imports.json', dict(status='complete', forwards=0))
        imports = file_record(path.parent / 'imports.json')
        write_json(path, dict(status='complete', environment='E3', components=['S3'],
            runtime=dict(versions=runtime.TARGETS['E3'], imports=imports, inventory=imports,
                         dependency_lock=imports, build_inputs=imports)))
        self.assertIsNone(setup_result_record(self.root, 'E3'))
        self.ledger.authorize_setup_recovery(self.authorization())
        self.assertIsNone(setup_result_record(self.root, 'E3'))
        self.ledger.reserve('E3-setup-recovery-001', [], {})
        self.ledger.finish('E3-setup-recovery-001', 'complete', 2., result=file_record(path))
        self.assertEqual(setup_result_record(self.root, 'E3'), file_record(path))
        self.assertIsNone(result_record(self.root, 'E3-setup'))
        self.assertIsNone(setup_result_record(self.root, 'E4'))

    def test_completed_wrong_environment_cannot_admit_sam3(self):
        path = self.root / 'jobs/E3-setup-recovery-001/result.json'
        write_json(path, dict(status='complete', environment='E4', components=['D1']))
        self.ledger.authorize_setup_recovery(self.authorization())
        self.ledger.reserve('E3-setup-recovery-001', [], {})
        self.ledger.finish('E3-setup-recovery-001', 'complete', 2., result=file_record(path))
        with self.assertRaisesRegex(ValueError, 'prescribed E3 qualification'):
            setup_result_record(self.root, 'E3')

    def test_recovery_reuses_weights_and_extracts_private_build_source_without_download(self):
        authorization = self.authorization()
        self.ledger.authorize_setup_recovery(authorization)
        with patch('vipe_benchmark.setup_recipes.shutil.which', return_value='/fixture/uv'):
            request = setup_recipes.recovery_request(self.root, authorization)
            runtime._validate_setup_request(request)
        with patch('vipe_benchmark.runtime.download', side_effect=AssertionError('no duplicate asset download')):
            assets = runtime.acquire_assets(request, self.root / 'jobs/E3-setup-recovery-001', self.config)
        self.assertEqual(assets['sam3_checkpoint'], self.assets['sam3_checkpoint'])
        self.assertNotEqual(assets['sam3_source']['path'], self.assets['sam3_source']['path'])
        (Path(assets['sam3_source']['path']) / 'module.py').write_text('build generated change')
        self.assertEqual((Path(self.assets['sam3_source']['path']) / 'module.py').read_text(), 'VALUE = 1\n')

    def test_recovery_recipe_and_archive_cannot_be_changed(self):
        authorization = self.authorization()
        self.ledger.authorize_setup_recovery(authorization)
        with patch('vipe_benchmark.setup_recipes.shutil.which', return_value='/fixture/uv'):
            request = setup_recipes.recovery_request(self.root, authorization)
            request['reuse_source_archives'] = {}
            with self.assertRaisesRegex(ValueError, 'authorized assets and recipe'):
                runtime._validate_setup_request(request)
            request.pop('recovery_authorization')
            with self.assertRaisesRegex(ValueError, 'requires explicit authorization'):
                runtime._validate_setup_request(request)

    def e1_authorization(self, **changes):
        if 'E1-setup' not in self.ledger.states():
            self.ledger.reserve('E1-setup', [], {})
            self.ledger.finish('E1-setup', 'failed', 207., cleanup_confirmed=True)
        validation = self.root / 'e1-validation.json'
        if not validation.exists():
            write_json(validation, dict(status='passed', source_files=[file_record(__file__)]))
        document = dict(schema='vipe-benchmark-e1-recovery/v1',
            job_id='E1-setup-recovery-001', original_job_id='E1-setup', environment='E1',
            original_failure_event_sha256=self.ledger.states()['E1-setup']['event_sha256'],
            repair_validation=file_record(validation))
        document.update(changes)
        return self.authorization(**document)

    def test_next_e1_retry_needs_new_authorization_bound_to_cleaned_up_failure(self):
        self.ledger.authorize_setup_recovery(self.e1_authorization())
        with self.assertRaisesRegex(ValueError, 'previous cleaned-up'):
            self.ledger.authorize_setup_recovery(self.e1_authorization(job_id='E1-setup-recovery-002'))
        self.ledger.reserve('E1-setup-recovery-001', [], {})
        failed = self.ledger.finish('E1-setup-recovery-001', 'failed', 12., cleanup_confirmed=True)
        with self.assertRaisesRegex(ValueError, 'previous cleaned-up'):
            self.ledger.authorize_setup_recovery(self.e1_authorization(job_id='E1-setup-recovery-002'))
        second = self.e1_authorization(job_id='E1-setup-recovery-002',
            authorization='Synthetic user instruction: retry',
            previous_recovery_failure_event_sha256=failed['event_sha256'])
        self.ledger.authorize_setup_recovery(second)
        self.ledger.reserve('E1-setup-recovery-002', [], {})
        self.assertEqual(self.ledger.totals()['setup']['attempts'], 4)
        self.assertEqual(self.ledger.states()['E1-setup-recovery-001'], failed)
        with self.assertRaisesRegex(ValueError, 'already allocated'):
            self.ledger.authorize_setup_recovery(second)

    def test_e1_and_e3_recoveries_coexist_with_independent_single_attempts(self):
        self.ledger.authorize_setup_recovery(self.authorization())
        authorization = self.e1_authorization()
        history = self.ledger.path.read_bytes()
        self.ledger.authorize_setup_recovery(authorization)
        self.assertTrue(self.ledger.path.read_bytes().startswith(history))
        self.assertIn('E3-setup-recovery-001', self.ledger.jobs)
        self.assertEqual(self.ledger.totals()['setup']['elapsed_seconds'], 240.5)
        with self.assertRaisesRegex(ValueError, 'already allocated'):
            self.ledger.authorize_setup_recovery(authorization)
        self.ledger.reserve('E1-setup-recovery-001', [], {})
        self.ledger.finish('E1-setup-recovery-001', 'failed', 2., cleanup_confirmed=True)
        with self.assertRaisesRegex(ValueError, 'already consumed'):
            self.ledger.reserve('E1-setup-recovery-001', [], {})
        self.assertEqual(self.ledger.states()['E4-setup']['status'], 'blocked')

    def test_e1_recovery_preserves_recipe_and_fresh_build_tree(self):
        authorization = self.e1_authorization()
        self.ledger.authorize_setup_recovery(authorization)
        with patch('vipe_benchmark.setup_recipes.shutil.which', return_value='/fixture/uv'):
            request = setup_recipes.recovery_request(self.root, authorization)
            runtime._validate_setup_request(request)
            self.assertEqual(request['components'], ['S1'])
            self.assertEqual(request['reuse_assets'], {})
            request['requirements'].append('unapproved-package')
            with self.assertRaisesRegex(ValueError, 'prescribed dependency'):
                runtime._validate_setup_request(request)

    def test_e1_recovery_rejects_expanded_scope_and_stale_validation(self):
        for change in [dict(recovery_attempts_limit=2), dict(reset_previous_consumption=True),
                       dict(unrelated_attempts_reopened=True), dict(authorization='')]:
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'exact explicit E1'):
                self.ledger.authorize_setup_recovery(self.e1_authorization(**change))
        authorization = self.e1_authorization()
        (self.root / 'e1-validation.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'changed file'):
            self.ledger.authorize_setup_recovery(authorization)

    def test_successful_e1_recovery_qualifies_s1_without_relabeling_failure(self):
        self.ledger.authorize_setup_recovery(self.e1_authorization())
        path = self.root / 'jobs/E1-setup-recovery-001/result.json'
        write_json(path.parent / 'imports.json', dict(status='complete', forwards=0))
        evidence = file_record(path.parent / 'imports.json')
        write_json(path, dict(status='complete', environment='E1', components=['S1'],
            runtime=dict(versions=runtime.TARGETS['E1'], imports=evidence, inventory=evidence,
                         dependency_lock=evidence, build_inputs=evidence)))
        self.assertIsNone(setup_result_record(self.root, 'E1'))
        self.ledger.reserve('E1-setup-recovery-001', [], {})
        self.ledger.finish('E1-setup-recovery-001', 'complete', 2., result=file_record(path))
        self.assertEqual(setup_result_record(self.root, 'E1'), file_record(path))
        self.assertEqual(self.ledger.states()['E1-setup']['status'], 'failed')


if __name__ == '__main__':
    unittest.main()
