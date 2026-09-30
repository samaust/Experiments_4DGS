"""CPU-only E5 proposal and checked setup recovery fixtures."""
from contextlib import contextmanager
import io
import json
import subprocess
from types import SimpleNamespace
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark import e5_recovery, runtime, setup_recipes
from vipe_benchmark.backends import SOURCE_PINS, SNAPSHOT_PINS
from vipe_benchmark.config import ROOT, load
from vipe_benchmark.execution import setup_result_record
from vipe_benchmark.files import file_record, read_json, write_json
from vipe_benchmark.ledger import Ledger
from vipe_benchmark.s1_validation_contract import source_paths


class E5RecoveryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.config = load()
        self.ledger = Ledger(self.root / 'ledger.jsonl', self.config)
        self.ledger.reserve('E5-setup', [], {})
        self.failure = self.ledger.finish('E5-setup', 'failed', 109.466,
            cleanup_confirmed=True, cleanup_uncertain=False, surviving_pids=[])
        original = self.root / 'jobs/E5-setup'
        archive = original / 'archives/da3.tar.gz'
        archive.parent.mkdir(parents=True)
        revision = SOURCE_PINS['da3_source']
        with tarfile.open(archive, 'w:gz') as stream:
            member = tarfile.TarInfo('da3-' + revision + '/module.py')
            member.size = 10
            stream.addfile(member, io.BytesIO(b'VALUE = 1\n'))
        source = runtime.extract_source(archive, original / 'sources/da3_source', revision)
        source['archive'] = file_record(archive)
        snapshot = original / 'snapshots/da3_snapshot'
        snapshot.mkdir(parents=True)
        (snapshot / 'config.json').write_text('{}')
        (snapshot / 'model.safetensors').write_bytes(b'fixture model')
        self.assets = dict(da3_source=source,
            da3_snapshot=runtime.tree_record(snapshot, SNAPSHOT_PINS['da3_snapshot']))
        write_json(original / 'assets-before-build.json', self.assets)
        self.asset_record = file_record(original / 'assets-before-build.json')
        write_json(self.root / 'qualification/historical-assets.json',
            dict(assets={'vipe_source': {'path': str(self.root / 'vipe')}}, parent={}))
        write_json(self.root / 'validation.json', dict(status='passed',
            sources=[file_record(p) for p in source_paths()]))
        self.validation = file_record(self.root / 'validation.json')

    def proposal(self):
        output = self.root / ('proposal-' + str(len(list(self.root.glob('proposal-*')))))
        return e5_recovery.propose(self.root, self.config, self.validation, self.asset_record, output)

    def dispatch_contract(self):
        registered = [e for e in self.ledger.events()
            if e['event'] == 'setup_recovery_authorized' and e['environment'] == 'E5'][-1]
        job_id = registered['job_id']
        with patch('vipe_benchmark.setup_recipes.shutil.which', return_value='/fixture/uv'):
            request = dict(setup_recipes.recovery_request(self.root, registered['authorization']),
                configuration=file_record(ROOT / 'configs/vipe-alternatives/benchmark-v1.json'))
        path = self.root / 'requests' / (job_id + '.json')
        if not path.exists():
            write_json(path, request)
        worker = file_record(ROOT / 'scripts/basketball_vipe_worker.py')
        command = [str(ROOT / '.local/envs/stg-colmap/bin/python'), worker['path'],
            '--operation', 'setup', '--config', request['configuration']['path'],
            '--request', str(path), '--output', str(self.root / 'jobs' / job_id)]
        return command, dict(request=file_record(path), worker=worker)

    def reserve(self):
        command, evidence = self.dispatch_contract()
        with patch('vipe_benchmark.setup_recipes.shutil.which', return_value='/fixture/uv'):
            return self.ledger.reserve('E5-setup-recovery-001', command, evidence)

    def test_second_review_binds_cleaned_first_failure_without_reopening_it(self):
        first = e5_recovery.approve(self.proposal(), 'Synthetic first attempt', self.root / 'do-first.json')
        self.ledger.authorize_setup_recovery(first)
        self.reserve()
        failure = self.ledger.finish('E5-setup-recovery-001', 'failed', 74.805,
            cleanup_confirmed=True, cleanup_uncertain=False, surviving_pids=[])
        before = self.ledger.path.read_bytes()
        review = e5_recovery.propose(self.root, self.config, self.validation,
            self.asset_record, self.root / 'second-review', job_id='E5-setup-recovery-002')
        document = read_json(review['path'])
        self.assertEqual(document['schema'], 'vipe-benchmark-e5-packaging-recovery/v2')
        self.assertEqual(document['previous_failure_event_sha256'], failure['event_sha256'])
        self.assertEqual(document['attempt_wall_seconds_limit'], 3600.)
        self.assertEqual(self.ledger.path.read_bytes(), before)
        with self.assertRaisesRegex(ValueError, 'explicit DO approval'):
            self.ledger.authorize_setup_recovery(review)
        approval = e5_recovery.approve(review, 'Synthetic exactly one second attempt', self.root / 'do-second.json')
        self.ledger.authorize_setup_recovery(approval)
        self.assertEqual(self.ledger.jobs['E5-setup-recovery-002']['seconds'], 3600.)
        self.assertEqual(self.ledger.states()['E5-setup-recovery-001'], failure)
        command, evidence = self.dispatch_contract()
        before_reserve = self.ledger.path.read_bytes()
        with patch('vipe_benchmark.setup_recipes.shutil.which', return_value='/fixture/uv'):
            with self.assertRaisesRegex(ValueError, 'canonical E5'):
                self.ledger.reserve('E5-setup-recovery-002', [], evidence)
            self.assertEqual(self.ledger.path.read_bytes(), before_reserve)
            self.ledger.reserve('E5-setup-recovery-002', command, evidence)
        self.ledger.finish('E5-setup-recovery-002', 'failed', 3., cleanup_confirmed=True)
        self.assertAlmostEqual(self.ledger.totals()['setup']['elapsed_seconds'], 187.271)
        with self.assertRaisesRegex(ValueError, 'already allocated'):
            e5_recovery.propose(self.root, self.config, self.validation, self.asset_record,
                self.root / 'third-review', job_id='E5-setup-recovery-002')
        with self.assertRaisesRegex(ValueError, 'already allocated'):
            self.ledger.authorize_setup_recovery(approval)

    def test_second_review_refuses_skipped_active_or_unclean_predecessor(self):
        before = self.ledger.path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'failed E5-setup-recovery-001'):
            e5_recovery.propose(self.root, self.config, self.validation, self.asset_record,
                self.root / 'skipped', job_id='E5-setup-recovery-002')
        self.assertEqual(self.ledger.path.read_bytes(), before)
        with self.assertRaisesRegex(ValueError, 'exact E5 recovery'):
            e5_recovery.propose(self.root, self.config, self.validation, self.asset_record,
                self.root / 'unknown', job_id='E5-setup-recovery-004')
        approval = e5_recovery.approve(self.proposal(), 'Synthetic first attempt', self.root / 'do-first.json')
        self.ledger.authorize_setup_recovery(approval)
        self.reserve()
        before = self.ledger.path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'failed E5-setup-recovery-001'):
            e5_recovery.propose(self.root, self.config, self.validation, self.asset_record,
                self.root / 'active', job_id='E5-setup-recovery-002')
        self.assertEqual(self.ledger.path.read_bytes(), before)
        self.ledger.finish('E5-setup-recovery-001', 'failed', 1., cleanup_confirmed=False,
            cleanup_uncertain=True, surviving_pids=[123])
        with self.assertRaisesRegex(ValueError, 'failed E5-setup-recovery-001'):
            e5_recovery.propose(self.root, self.config, self.validation, self.asset_record,
                self.root / 'unclean', job_id='E5-setup-recovery-002')

    def test_second_review_refuses_successful_predecessor(self):
        approval = e5_recovery.approve(self.proposal(), 'Synthetic first attempt', self.root / 'first.json')
        self.ledger.authorize_setup_recovery(approval)
        self.reserve()
        self.ledger.finish('E5-setup-recovery-001', 'complete', 1., cleanup_confirmed=True)
        before = self.ledger.path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'failed E5-setup-recovery-001'):
            e5_recovery.propose(self.root, self.config, self.validation, self.asset_record,
                self.root / 'success-refusal', job_id='E5-setup-recovery-002')
        self.assertEqual(self.ledger.path.read_bytes(), before)

    def third_proposal(self, *, second_cleanup=True, skip_second=False):
        for index, job in enumerate(('E5-setup-recovery-001', 'E5-setup-recovery-002')):
            if index == 1 and skip_second:
                break
            review = e5_recovery.propose(self.root, self.config, self.validation, self.asset_record,
                self.root / f'predecessor-{index}', job_id=job)
            approval = e5_recovery.approve(review, 'Synthetic predecessor approval', self.root / f'do-{index}.json')
            self.ledger.authorize_setup_recovery(approval)
            command, evidence = self.dispatch_contract()
            with patch('vipe_benchmark.setup_recipes.shutil.which', return_value='/fixture/uv'):
                self.ledger.reserve(job, command, evidence)
            self.ledger.finish(job, 'failed', 75. + index, cleanup_confirmed=second_cleanup if index else True,
                cleanup_uncertain=not second_cleanup if index else False,
                surviving_pids=[123] if index and not second_cleanup else [])
        return e5_recovery.propose(self.root, self.config, self.validation, self.asset_record,
            self.root / 'third-review', job_id='E5-setup-recovery-003')

    def test_third_review_and_canonical_reservation_preserve_two_consumed_failures(self):
        review = self.third_proposal()
        before = self.ledger.path.read_bytes()
        document = read_json(review['path'])
        self.assertEqual(document['schema'], 'vipe-benchmark-e5-packaging-recovery/v3')
        self.assertEqual(document['previous_job_id'], 'E5-setup-recovery-002')
        self.assertEqual(document['previous_failure_event_sha256'],
            self.ledger.states()['E5-setup-recovery-002']['event_sha256'])
        self.assertEqual(len(document['preserved_recovery_failures']), 2)
        self.assertEqual(document['attempt_wall_seconds_limit'], 3600.)
        with self.assertRaisesRegex(ValueError, 'explicit DO approval'):
            self.ledger.authorize_setup_recovery(review)
        self.assertEqual(self.ledger.path.read_bytes(), before)
        approval = e5_recovery.approve(review, 'Synthetic approved exactly one third E5 attempt', self.root / 'do-third.json')
        self.ledger.authorize_setup_recovery(approval)
        command, evidence = self.dispatch_contract()
        before = self.ledger.path.read_bytes()
        with patch('vipe_benchmark.setup_recipes.shutil.which', return_value='/fixture/uv'):
            with self.assertRaisesRegex(ValueError, 'canonical E5'):
                self.ledger.reserve('E5-setup-recovery-003', [], evidence)
            self.assertEqual(self.ledger.path.read_bytes(), before)
            self.ledger.reserve('E5-setup-recovery-003', command, evidence)
        self.ledger.finish('E5-setup-recovery-003', 'failed', 3., cleanup_confirmed=True)
        self.assertAlmostEqual(self.ledger.totals()['setup']['elapsed_seconds'], 263.466)
        with self.assertRaisesRegex(ValueError, 'already allocated'):
            self.ledger.authorize_setup_recovery(approval)

    def test_third_review_refuses_skipped_second_identity(self):
        with self.assertRaisesRegex(ValueError, 'failed E5-setup-recovery-002'):
            self.third_proposal(skip_second=True)
        self.assertNotIn('E5-setup-recovery-003', self.ledger.jobs)

    def test_third_review_refuses_uncertain_second_cleanup(self):
        with self.assertRaisesRegex(ValueError, 'failed E5-setup-recovery-002'):
            self.third_proposal(second_cleanup=False)
        self.assertNotIn('E5-setup-recovery-003', self.ledger.jobs)

    def test_third_allocation_rejects_changed_prefix_scope_and_prior_failure_binding(self):
        review = self.third_proposal()
        approval = e5_recovery.approve(review, 'Synthetic third attempt', self.root / 'third-do.json')
        events = self.ledger.events()
        changed_events = [dict(e) for e in events]
        changed_events[0]['event_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'ledger prefix'):
            e5_recovery.validate(self.root, self.config, approval, changed_events)
        document = read_json(review['path'])
        for index, changes in enumerate((dict(recovery_attempts_limit=2),
                dict(previous_job_id='E5-setup-recovery-001'), dict(preserved_recovery_failures=[]),
                dict(attempt_wall_seconds_limit=3601.))):
            with self.subTest(changes=changes):
                path = self.root / f'changed-third-review-{index}.json'
                write_json(path, dict(document, **changes))
                changed_do = e5_recovery.approve(file_record(path), 'Synthetic third attempt', self.root / f'changed-third-do-{index}.json')
                before = self.ledger.path.read_bytes()
                with self.assertRaises(ValueError):
                    self.ledger.authorize_setup_recovery(changed_do)
                self.assertEqual(self.ledger.path.read_bytes(), before)
        validation_path = Path(self.validation['path'])
        original = validation_path.read_bytes()
        validation_path.write_text('{}')
        before = self.ledger.path.read_bytes()
        with self.assertRaises(ValueError):
            self.ledger.authorize_setup_recovery(approval)
        self.assertEqual(self.ledger.path.read_bytes(), before)
        validation_path.write_bytes(original)

    def test_review_binds_failure_recipe_sources_and_charges_without_allocation(self):
        before = self.ledger.path.read_bytes()
        review = self.proposal()
        document = read_json(review['path'])
        self.assertEqual(document['mode'], 'REVIEW')
        self.assertEqual(document['job_id'], 'E5-setup-recovery-001')
        self.assertEqual(document['original_failure_event_sha256'], self.failure['event_sha256'])
        self.assertEqual(document['cumulative_totals']['setup']['elapsed_seconds'], 109.466)
        self.assertIn('editables~=0.3', document['recipe']['requirements'])
        with self.assertRaisesRegex(ValueError, 'explicit DO approval'):
            self.ledger.authorize_setup_recovery(review)
        self.assertEqual(self.ledger.path.read_bytes(), before)


    def test_approved_recovery_preserves_history_and_extracts_private_source(self):
        review = self.proposal()
        approval = e5_recovery.approve(review, 'Synthetic explicit fresh E5 attempt approval', self.root / 'do.json')
        before = self.ledger.path.read_bytes()
        self.ledger.authorize_setup_recovery(approval)
        self.assertTrue(self.ledger.path.read_bytes().startswith(before))
        with patch('vipe_benchmark.setup_recipes.shutil.which', return_value='/fixture/uv'):
            request = setup_recipes.recovery_request(self.root, approval)
        output = self.root / 'jobs/E5-setup-recovery-001'
        with patch('vipe_benchmark.runtime.download', side_effect=AssertionError('asset downloads forbidden')):
            assets = runtime.acquire_assets(request, output, self.config)
        self.assertEqual(assets['da3_snapshot'], self.assets['da3_snapshot'])
        self.assertNotEqual(assets['da3_source']['path'], self.assets['da3_source']['path'])
        (Path(assets['da3_source']['path']) / 'module.py').write_text('generated by private build')
        self.assertEqual((Path(self.assets['da3_source']['path']) / 'module.py').read_text(), 'VALUE = 1\n')
        self.reserve()
        self.assertEqual(self.ledger.totals()['setup']['attempts'], 2)
        self.assertEqual(self.ledger.states()['E5-setup'], self.failure)



    def test_only_ledger_frozen_import_qualified_recovery_admits_e5(self):
        review = self.proposal()
        approval = e5_recovery.approve(review, 'Synthetic one fresh E5 attempt', self.root / 'do.json')
        self.ledger.authorize_setup_recovery(approval)
        output = self.root / 'jobs/E5-setup-recovery-001'
        write_json(output / 'imports.json', dict(status='complete', forwards=0, cuda_context_initialized=False))
        evidence = file_record(output / 'imports.json')
        write_json(output / 'result.json', dict(status='complete', environment='E5', components=['D2'],
            runtime=dict(versions=runtime.TARGETS['E5'], imports=evidence, inventory=evidence,
                         dependency_lock=evidence, build_inputs=evidence)))
        self.assertIsNone(setup_result_record(self.root, 'E5'))
        reservation = self.reserve()
        self.assertEqual(reservation['seconds'], 3600.)
        self.ledger.finish('E5-setup-recovery-001', 'complete', 2., cleanup_confirmed=True,
            result=file_record(output / 'result.json'))
        self.assertEqual(setup_result_record(self.root, 'E5'), file_record(output / 'result.json'))
        self.assertEqual(self.ledger.states()['E5-setup'], self.failure)
        self.assertEqual(self.ledger.totals()['setup']['elapsed_seconds'], 111.466)



    def test_complete_fake_package_setup_qualifies_only_its_finished_ledger_result(self):
        approval = e5_recovery.approve(self.proposal(), 'Synthetic fresh E5 attempt', self.root / 'do.json')
        self.ledger.authorize_setup_recovery(approval)
        with patch('vipe_benchmark.setup_recipes.shutil.which', return_value='/fixture/uv'):
            request = setup_recipes.recovery_request(self.root, approval)
        output = self.root / 'jobs/E5-setup-recovery-001'
        installed_editables = False
        @contextmanager
        def proxy(*args, **kwargs):
            yield SimpleNamespace(environment={}, check=lambda: None)
        def package(command, **kwargs):
            nonlocal installed_editables
            if 'venv' in command:
                (Path(command[-1]) / 'bin').mkdir(parents=True)
            elif 'compile' in command:
                required = Path(command[-1]).read_text()
                self.assertIn('editables~=0.3', required)
                self.assertIn('--generate-hashes', command)
                Path(command[command.index('--output-file') + 1]).write_text('editables==0.5 --hash=sha256:' + 'a' * 64)
            elif '--require-hashes' in command:
                installed_editables = 'editables==0.5' in Path(command[command.index('-r') + 1]).read_text()
            elif '-e' in command:
                if not installed_editables:
                    raise ModuleNotFoundError("No module named 'editables'")
                self.assertEqual(kwargs['env']['UV_OFFLINE'], '1')
                self.assertIn('--no-deps', command)
                self.assertIn('--no-build-isolation', command)
                (Path(command[-1]) / 'generated.py').write_text('fixture build artifact')
            elif '--qualify-imports' in command:
                normalize_source = Path(command[-1]).parent / 'environment/lib/python3.11/site-packages/torchvision/transforms/transforms.py'
                normalize_source.parent.mkdir(parents=True, exist_ok=True)
                normalize_source.write_text('fixture pinned Normalize source')
                write_json(command[-1], dict(status='complete', forwards=0, cuda_context_initialized=False,
                    native_model_constructors_called=False, preprocessing_constructors=dict(
                        class_name='torchvision.transforms.transforms.Normalize', count=1, file=file_record(normalize_source)),
                    import_only_environment={
                        'XFORMERS_FORCE_DISABLE_TRITON': '1', 'XFORMERS_ENABLE_TRITON': '0'}))
            elif 'runtime_inventory.py' in command[1]:
                packages = [dict(name=r.split('==')[0], version=r.split('==')[1])
                            for r in request['requirements'] if '==' in r]
                packages.append(dict(name='editables', version='0.5'))
                write_json(command[-1], dict(versions=runtime.TARGETS['E5'], packages=packages))
            return subprocess.CompletedProcess(command, 0)
        self.reserve()
        with patch('vipe_benchmark.setup_recipes.shutil.which', return_value='/fixture/uv'), \
             patch('vipe_benchmark.runtime.subprocess.run', side_effect=package), \
             patch('vipe_benchmark.transfer_proxy.uv_proxy', side_effect=proxy), \
             patch('vipe_benchmark.runtime.download', side_effect=AssertionError('asset download')):
            runtime.setup(request, output, self.config)
        self.assertIsNone(setup_result_record(self.root, 'E5'))
        self.ledger.finish('E5-setup-recovery-001', 'complete', 3., cleanup_confirmed=True,
            result=file_record(output / 'result.json'))
        result = read_json(setup_result_record(self.root, 'E5')['path'])
        self.assertEqual(result['runtime']['versions'], e5_recovery.TARGET)
        self.assertIn('editables==0.5', Path(result['runtime']['dependency_lock']['path']).read_text())
        self.assertFalse((Path(self.assets['da3_source']['path']) / 'generated.py').exists())

    def test_scope_recipe_and_approval_tampering_cannot_allocate_or_admit(self):
        review = self.proposal()
        approval = e5_recovery.approve(review, 'Synthetic fresh E5 attempt', self.root / 'do.json')
        document = read_json(approval['path'])
        before = self.ledger.path.read_bytes()
        for changes in (dict(job_id='E5-setup-recovery-002'), dict(recovery_attempts_limit=2),
                        dict(attempt_wall_seconds_limit=7200), dict(authorization=''),
                        dict(reset_previous_consumption=True), dict(mode='REVIEW')):
            path = self.root / ('changed-' + str(len(list(self.root.glob('changed-*')))) + '.json')
            write_json(path, dict(document, **changes))
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.ledger.authorize_setup_recovery(file_record(path))
            self.assertEqual(self.ledger.path.read_bytes(), before)
        self.ledger.authorize_setup_recovery(approval)
        with patch('vipe_benchmark.setup_recipes.shutil.which', return_value='/fixture/uv'):
            request = setup_recipes.recovery_request(self.root, approval)
        request['requirements'].remove('editables~=0.3')
        with self.assertRaisesRegex(ValueError, 'prescribed dependency'):
            runtime.setup(request, self.root / 'changed-build', self.config)
        self.assertFalse((self.root / 'changed-build').exists())
        Path(approval['path']).write_text('{}')
        with self.assertRaisesRegex(ValueError, 'changed file'):
            self.reserve()

    def test_changed_archive_snapshot_and_stale_sources_reject_review(self):
        for asset in ('archive', 'snapshot', 'qualification'):
            with self.subTest(asset=asset):
                if asset == 'archive':
                    path = Path(self.assets['da3_source']['archive']['path'])
                elif asset == 'snapshot':
                    path = Path(self.assets['da3_snapshot']['files'][0]['path'])
                else:
                    path = Path(self.validation['path'])
                original = path.read_bytes()
                path.write_bytes(b'changed')
                with self.assertRaises(ValueError):
                    self.proposal()
                path.write_bytes(original)



    def test_reviewed_repair_cannot_drift_and_consumed_recovery_cannot_reopen(self):
        approval = e5_recovery.approve(self.proposal(), 'Synthetic fresh E5 attempt', self.root / 'do.json')
        before = self.ledger.path.read_bytes()
        extras = [r for r in setup_recipes.EXTRAS['E5'] if not r.startswith('editables')]
        with patch.dict(setup_recipes.EXTRAS, E5=extras):
            with self.assertRaisesRegex(ValueError, 'exact editables'):
                self.ledger.authorize_setup_recovery(approval)
        self.assertEqual(self.ledger.path.read_bytes(), before)
        self.ledger.authorize_setup_recovery(approval)
        self.reserve()
        self.ledger.finish('E5-setup-recovery-001', 'failed', 2., cleanup_confirmed=True)
        with self.assertRaisesRegex(ValueError, 'already allocated'):
            self.ledger.authorize_setup_recovery(approval)
        for job in ('E5-setup', 'E5-setup-recovery-001'):
            with self.subTest(job=job), self.assertRaisesRegex(ValueError, 'consumed'):
                self.ledger.resume_unstarted([job], 'Synthetic resume')
        with self.assertRaisesRegex(ValueError, 'already allocated'):
            self.proposal()



    def test_reservation_rejects_changed_request_path_command_runtime_assets_and_evidence(self):
        approval = e5_recovery.approve(self.proposal(), 'Synthetic fresh E5 attempt', self.root / 'do.json')
        self.ledger.authorize_setup_recovery(approval)
        command, evidence = self.dispatch_contract()
        original_request = read_json(evidence['request']['path'])
        before = self.ledger.path.read_bytes()
        wrong_path = self.root / 'requests/orphan.json'
        write_json(wrong_path, original_request)
        wrong_commands = [[], ['unrelated command'], command[:-1] + [str(self.root / 'wrong-output')],
            ['/wrong/python'] + command[1:], command[:3] + ['component'] + command[4:]]
        with patch('vipe_benchmark.setup_recipes.shutil.which', return_value='/fixture/uv'):
            for changed in wrong_commands:
                with self.subTest(command=changed), self.assertRaisesRegex(ValueError, 'canonical E5'):
                    self.ledger.reserve('E5-setup-recovery-001', changed, evidence)
                self.assertEqual(self.ledger.path.read_bytes(), before)
            for changed in ({}, dict(evidence, request=file_record(wrong_path)),
                            dict(evidence, worker=file_record(__file__)), dict(evidence, unrelated=True)):
                with self.subTest(evidence=changed), self.assertRaisesRegex(ValueError, 'canonical E5'):
                    self.ledger.reserve('E5-setup-recovery-001', command, changed)
                self.assertEqual(self.ledger.path.read_bytes(), before)
            for changes in (dict(runtime={'python': '/wrong/python'}), dict(reuse_assets={}),
                            dict(reuse_source_archives={}), dict(requirements=['editables~=0.3']),
                            dict(configuration=file_record(__file__)), dict(environment='E4')):
                path = Path(evidence['request']['path'])
                path.write_text(json.dumps(dict(original_request, **changes)))
                changed = dict(evidence, request=file_record(path))
                with self.subTest(request=changes), self.assertRaisesRegex(ValueError, 'canonical E5'):
                    self.ledger.reserve('E5-setup-recovery-001', command, changed)
                self.assertEqual(self.ledger.path.read_bytes(), before)
            Path(evidence['request']['path']).write_text(json.dumps(original_request))
            reserved = self.ledger.reserve('E5-setup-recovery-001', command,
                dict(evidence, request=file_record(evidence['request']['path'])))
        self.assertEqual(reserved['seconds'], 3600.)



if __name__ == '__main__':
    unittest.main()
