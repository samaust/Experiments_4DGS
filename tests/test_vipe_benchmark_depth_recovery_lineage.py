"""Producer-independent accepted recovery fixtures; no runtime execution."""
from copy import deepcopy
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import ANY, Mock, patch

from vipe_benchmark.depth_recovery_lineage import accepted_setup_lineage, recovery_map_allocation, JOB
from vipe_benchmark.files import file_record, object_hash, read_json, write_json


class RecoveryLineageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.old = self.root / 'jobs/plan069-D9-setup-001'
        self.job = self.root / 'jobs' / JOB
        self.old.mkdir(parents=True)
        self.job.mkdir(parents=True)
        def content(path, text):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
            return file_record(path)
        self.old_checkpoint = content(self.old / 'model.bin', 'paid')
        source = content(self.old / 'source/model.py', 'source')
        archive = content(self.old / 'source.tar.gz', 'archive')
        self.original = dict(checkpoint=self.old_checkpoint, source_archive=archive, source_files=[source])
        os.link(self.old_checkpoint['path'], self.job / 'model.bin')
        self.checkpoint = file_record(self.job / 'model.bin')
        self.authority = {}
        for key in ('review', 'authorization', 'source_review'):
            self.authority[key] = self.document(self.root / (key + '.json'), {'fixture': key})
        tools = dict(ffmpeg=content(self.root / 'media/ffmpeg', 'fixture tool'))
        recipe = self.document(self.root / 'recipe.json', {'fixture': 'recipe'})
        self.environment = dict(media_tools=tools, recipe=recipe, runtime_profile='reviewed frame runtime', xformers=False)
        required = self.document(self.root / 'required.json', dict(candidates={'D9': dict(files=[
            dict(repository='fixture/model', path='model.bin', bytes=4, lfs_sha256=self.checkpoint['sha256'])])}))
        self.maps = dict(candidate='D9', max_attempts=1, required_assets=required,
            candidate_config=dict(code=dict(revision='code'), weights=dict(revision='weights')),
            allocation=dict(setup_seconds=100, download_bytes=60, artifact_bytes=90, cpu_seconds=100))
        self.proposal = dict(candidate='D9', job_id=JOB, max_attempts=1, original_setup=self.original)
        self.request = self.document(self.root / 'requests' / (JOB + '.json'),
            dict(self.authority, original_setup=self.original))
        self.grant = dict(event='depth_setup_recovery_authorized', sequence=4, event_sha256='grant',
            candidate='D9', job_id=JOB, request=self.request, proposal_sha256=object_hash(self.proposal), **self.authority)
        self.reserve = dict(event='reserve', sequence=5, event_sha256='reserve', job_id=JOB,
            resource='setup', seconds=20, evidence=dict(request=self.request, **self.authority))
        self.finish = dict(event='finish', sequence=6, event_sha256='finish', job_id=JOB,
            resource='setup', status='complete', cleanup_confirmed=True, cleanup_uncertain=False,
            surviving_pids=[], deadline_exceeded=False)
        self.normalized = dict(proposal=self.proposal, map_proposal=self.maps, original=self.original,
            lineage=dict(proposal=self.maps, grant=dict(resource_snapshot=dict(download_bytes=10)),
                finish=dict(peak=dict(download_bytes=14)), checkpoint=dict(files={})), runtime_environment=self.environment,
            request=self.request, allocation=dict(self.maps['allocation'], setup_seconds=20), **self.authority)
        python = content(self.root / 'seed-python', 'fixture executable')
        self.environment.update(python_seed=python, requirement_sources=[recipe])
        lock = content(self.job / 'runtime/requirements.lock', 'locked')
        executable = str(self.job / 'runtime/environment/bin/python')
        Path(executable).parent.mkdir(parents=True)
        Path(executable).symlink_to(python['path'])
        inventory = self.document(self.job / 'runtime/inventory.json', dict(inventory_only=True,
            model_imports=False, gpu_operations=False, executable=executable, packages=[]))
        runtime = self.document(self.job / 'runtime/result.json', dict(
            schema='plan069-depth-environment-result/v1', status='complete', record_kind='actual',
            candidate='D9', python_executable=executable, python=python, dependency_lock=lock, inventory=inventory,
            runtime_recipe=recipe, runtime_profile=self.environment['runtime_profile'], python_seed=python,
            requirement_sources=[recipe], excluded_distributions=['decord', 'xformers'], offline=True,
            model_imports=False, gpu_operations=False, automatic_retries=0))
        self.result = dict(schema='plan069-video-setup-recovery-result/v1', record_kind='actual',
            status='complete', candidate='D9', job_id=JOB, request=self.request, **self.authority,
            original_setup=self.original, source_revision='code', weight_revision='weights',
            source_archive=archive, source_files=[source], source_dir=str(self.old / 'source'),
            checkpoint=self.checkpoint, runtime_environment=runtime, python_executable=executable,
            python=python, dependency_lock=lock, inventory=inventory, runtime_recipe=recipe,
            runtime_profile=self.environment['runtime_profile'], excluded_distributions=['decord', 'xformers'],
            media_tools=tools, xformers=False, bytes_received=0, original_failure_preserved=True,
            model_imports=False, gpu_operations=False, automatic_retries=0)
        self.publish()
        self.events = [self.grant, self.reserve, self.finish]
        info = Path(self.old_checkpoint['path']).stat()
        self.paid = dict(transfer_id='fixture-model', output=self.old_checkpoint['path'], error=None,
            bytes_received=4, output_identity=dict(device=info.st_dev, inode=info.st_ino,
                size=info.st_size, mtime_ns=info.st_mtime_ns))
        self.paid_path = self.root / 'transfers/transfer-fixture-model.json'
        self.document(self.paid_path, self.paid)
        self.module = types.ModuleType('vipe_benchmark.depth_setup_recovery')
        self.validator = Mock(return_value=self.normalized)
        setattr(self.module, 'validate_recovery_request', self.validator)
        mocked = patch.dict(sys.modules, {'vipe_benchmark.depth_setup_recovery': self.module})
        mocked.start()
        self.addCleanup(mocked.stop)

    def document(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json(path, value)
        return file_record(path)

    def publish(self):
        path = self.job / 'result.json'
        path.unlink(missing_ok=True)
        self.setup = self.document(path, self.result)
        self.finish['result'] = self.setup

    def accepted(self):
        return accepted_setup_lineage(self.setup, self.events, self.root)

    def assets(self):
        return [dict(repository='fixture/model', path='model.bin', record=self.checkpoint)]

    def repair(self):
        old_job = self.job
        self.job = self.root / 'jobs/plan069-D9-setup-recovery-002'
        self.job.mkdir()
        import shutil
        shutil.copytree(old_job / 'runtime', self.job / 'runtime', symlinks=True)
        os.link(self.old_checkpoint['path'], self.job / 'model.bin')
        self.checkpoint = file_record(self.job / 'model.bin')
        failed_request = self.request
        failure = self.document(old_job / 'failure.json', dict(schema='plan069-video-setup-recovery-failure/v1',
            record_kind='actual', status='failed', job_id=JOB, original_setup=self.original,
            error='fixture failure', automatic_retries=0, gpu_operations=False))
        failed_grant = deepcopy(self.grant)
        failed_reserve = deepcopy(self.reserve)
        failed_finish = dict(self.finish, status='failed', result=None, failure=failure)
        descriptor = dict(job_id=JOB, grant_event_sha256='grant', failed_finish_event_sha256='finish',
                          request=failed_request, failure=failure)
        self.proposal = dict(self.proposal, job_id=self.job.name, failed_recoveries=[descriptor])
        self.request = self.document(self.root / 'requests' / (self.job.name + '.json'),
            dict(self.authority, schema='plan069-video-setup-recovery-request/v2', job_id=self.job.name,
                 original_setup=self.original, failed_recoveries=[descriptor]))
        self.grant = dict(self.grant, sequence=7, event_sha256='repair-grant', job_id=self.job.name,
                          request=self.request, proposal_sha256=object_hash(self.proposal))
        self.reserve = dict(self.reserve, sequence=8, event_sha256='repair-reserve', job_id=self.job.name,
                            evidence=dict(request=self.request, **self.authority))
        self.finish = dict(self.finish, sequence=9, event_sha256='repair-finish', job_id=self.job.name)
        for key in ('runtime_environment', 'dependency_lock', 'inventory'):
            path = self.job / Path(self.result[key]['path']).relative_to(old_job)
            if key != 'dependency_lock':
                doc = read_json(path)
                if key == 'inventory':
                    for package in doc['packages']:
                        for index, record in enumerate(package['files']):
                            native = self.job / Path(record['path']).relative_to(old_job)
                            native.unlink(); os.link(record['path'], native)
                            package['files'][index] = file_record(native)
                for name in ('python_executable', 'executable'):
                    if name in doc:
                        doc[name] = str(self.job / 'runtime/environment/bin/python')
                for name in ('dependency_lock', 'inventory'):
                    if name in doc:
                        doc[name] = file_record(self.job / Path(doc[name]['path']).relative_to(old_job))
                path.unlink(); self.document(path, doc)
            self.result[key] = file_record(path)
        # Inventory hash changed after the runtime was copied.
        runtime_path = Path(self.result['runtime_environment']['path'])
        runtime = read_json(runtime_path); runtime['inventory'] = self.result['inventory']
        runtime_path.unlink(); self.result['runtime_environment'] = self.document(runtime_path, runtime)
        self.result.update(schema='plan069-video-setup-recovery-result/v2', job_id=self.job.name, request=self.request, checkpoint=self.checkpoint,
                           failed_recoveries=[descriptor],
                           python_executable=str(self.job / 'runtime/environment/bin/python'))
        self.normalized.update(job_id=self.job.name, proposal=self.proposal, request=self.request,
                               failed_recoveries=[descriptor])
        self.publish()
        self.events = [failed_grant, failed_reserve, failed_finish, self.grant, self.reserve, self.finish]
        return descriptor

    def test_second_recovery_preserves_failed_first_and_credits_original_only(self):
        descriptor = self.repair()
        accepted = self.accepted()
        self.assertEqual(accepted['job'], self.job.name)
        stage = recovery_map_allocation(self.maps, self.setup, self.events, self.root, self.assets())
        self.assertEqual(stage['recovery_lineage']['failed_recoveries'], [descriptor])
        self.assertEqual(stage['credited_assets_bytes'], 4)

    def test_repair_rejects_old_schema_and_unapproved_failed_chain(self):
        self.repair()
        self.result['schema'] = 'plan069-video-setup-recovery-result/v1'; self.publish()
        with self.assertRaisesRegex(ValueError, 'completed D9 recovery'):
            self.accepted()
        self.result['schema'] = 'plan069-video-setup-recovery-result/v2'; self.publish()
        self.normalized['failed_recoveries'][0]['job_id'] = 'plan069-D9-setup-recovery-003'
        with self.assertRaisesRegex(ValueError, 'failed recovery chain'):
            self.accepted()

    def test_repair_rejects_unclean_or_changed_historical_failure(self):
        descriptor = self.repair()
        self.events[2]['cleanup_confirmed'] = False
        with self.assertRaisesRegex(ValueError, 'clean failed recovery'):
            self.accepted()
        self.events[2]['cleanup_confirmed'] = True
        Path(descriptor['failure']['path']).write_text('{}')
        with self.assertRaisesRegex(ValueError, 'changed file'):
            self.accepted()

    def test_accepted_recovery_normalizes_without_failed_setup_promotion(self):
        result = self.accepted()
        self.assertEqual(result['accepted_result'], self.result)
        self.assertEqual(result['job'], JOB)
        self.assertEqual(result['setup'], self.setup)
        self.validator.assert_called_once_with(self.request, self.events, self.root,
            require_reservation=False, verifier=ANY)

    def test_maps_credit_paid_model_once_and_preserve_original_caps(self):
        original = deepcopy(self.maps)
        stage = recovery_map_allocation(self.maps, self.setup, self.events, self.root, self.assets())
        self.assertEqual(stage['credited_assets_bytes'], 4)
        self.assertEqual(stage['allocation']['download_bytes'], 56)
        self.assertEqual(stage['allocation']['artifact_bytes'], 86)
        self.assertEqual(stage['allocation']['setup_seconds'], 100)
        self.assertEqual(stage['recovery_lineage']['finish_event_sha256'], 'finish')
        self.assertEqual(self.maps, original)

    def test_failed_fixture_or_original_result_cannot_qualify(self):
        for key, value in [('status', 'failed'), ('record_kind', 'fixture'),
                           ('schema', 'plan069-video-setup-result/v1'), ('job_id', 'plan069-D9-setup-001')]:
            with self.subTest(key=key):
                previous = self.result[key]
                self.result[key] = value; self.publish()
                with self.assertRaisesRegex(ValueError, 'completed D9 recovery'):
                    self.accepted()
                self.result[key] = previous

    def test_unclean_failed_or_duplicate_completion_rejected(self):
        for key, value in [('status', 'failed'), ('cleanup_confirmed', False),
                           ('cleanup_uncertain', True), ('surviving_pids', [123]), ('deadline_exceeded', True)]:
            with self.subTest(key=key):
                previous = self.finish[key]; self.finish[key] = value
                with self.assertRaisesRegex(ValueError, 'clean independently'):
                    self.accepted()
                self.finish[key] = previous
        self.events.append(dict(self.finish))
        with self.assertRaisesRegex(ValueError, 'unique accepted recovery finish'):
            self.accepted()

    def test_active_foreign_reservation_rejected(self):
        self.events.append(dict(event='reserve', job_id='other', sequence=7))
        with self.assertRaisesRegex(ValueError, 'active attempt'):
            self.accepted()

    def test_authority_substitution_rejected(self):
        for field in ['request', 'proposal_sha256', 'source_review']:
            with self.subTest(field=field):
                previous = self.grant[field]; self.grant[field] = 'substitution'
                with self.assertRaises(ValueError): self.accepted()
                self.grant[field] = previous

    def test_same_bytes_different_checkpoint_inode_rejected(self):
        path = self.job / 'model.bin'
        path.unlink(); path.write_bytes(b'paid')
        self.result['checkpoint'] = file_record(path); self.publish()
        with self.assertRaisesRegex(ValueError, 'share original retained inode'):
            self.accepted()

    def test_download_source_and_runtime_substitutions_rejected(self):
        for field, value in [('bytes_received', 1), ('source_dir', str(self.job / 'source')),
                             ('source_files', []), ('python_executable', 'foreign'),
                             ('media_tools', {}), ('inventory', self.request)]:
            with self.subTest(field=field):
                previous = self.result[field]; self.result[field] = value; self.publish()
                with self.assertRaises(ValueError): self.accepted()
                self.result[field] = previous

    def test_changed_or_unpaid_map_asset_receives_no_credit(self):
        for field, value in [('bytes_received', 3), ('error', 'failed'), ('output_identity', {})]:
            with self.subTest(field=field):
                previous = self.paid[field]; self.paid[field] = value
                self.paid_path.unlink(); self.document(self.paid_path, self.paid)
                with self.assertRaisesRegex(ValueError, 'newly paid approved acquisition'):
                    recovery_map_allocation(self.maps, self.setup, self.events, self.root, self.assets())
                self.paid[field] = previous
        self.paid_path.unlink(); self.document(self.paid_path, self.paid)
        for field, value in [('repository', 'wrong'), ('record', self.old_checkpoint)]:
            asset = self.assets(); asset[0][field] = value
            with self.assertRaisesRegex(ValueError, 'accepted native model'):
                recovery_map_allocation(self.maps, self.setup, self.events, self.root, asset)

    def test_changed_proposal_rejected(self):
        proposal = deepcopy(self.maps); proposal['allocation']['download_bytes'] += 1
        with self.assertRaisesRegex(ValueError, 'approved recovered map proposal'):
            recovery_map_allocation(proposal, self.setup, self.events, self.root, self.assets())

    def test_changed_retained_source_revokes_acceptance(self):
        Path(self.original['source_files'][0]['path']).write_text('edited')
        with self.assertRaises(ValueError): self.accepted()

    def test_missing_or_baseline_receipt_and_inode_cannot_mint_credit(self):
        before = self.normalized['lineage']['checkpoint']['files']
        before['transfers/transfer-fixture-model.json'] = {}
        with self.assertRaisesRegex(ValueError, 'newly paid approved acquisition'):
            recovery_map_allocation(self.maps, self.setup, self.events, self.root, self.assets())
        before.clear()
        info = Path(self.old_checkpoint['path']).stat()
        before['baseline-model'] = dict(device=info.st_dev, inode=info.st_ino)
        with self.assertRaisesRegex(ValueError, 'newly paid approved acquisition'):
            recovery_map_allocation(self.maps, self.setup, self.events, self.root, self.assets())
        before.clear(); self.paid_path.unlink()
        with self.assertRaisesRegex(ValueError, 'unique original'):
            recovery_map_allocation(self.maps, self.setup, self.events, self.root, self.assets())

    def test_baseline_model_path_with_other_inode_has_no_credit(self):
        before = self.normalized['lineage']['checkpoint']['files']
        before[str(Path(self.old_checkpoint['path']).relative_to(self.root))] = dict(device=-1, inode=-1)
        with self.assertRaisesRegex(ValueError, 'newly paid approved acquisition'):
            recovery_map_allocation(self.maps, self.setup, self.events, self.root, self.assets())

    def test_missing_or_retargeted_native_interpreter_revokes_acceptance(self):
        executable = Path(self.result['python_executable'])
        executable.unlink()
        with self.assertRaisesRegex(ValueError, 'native recovery executable'):
            self.accepted()
        other = self.root / 'other-python'; other.write_text('foreign executable')
        executable.symlink_to(other)
        with self.assertRaisesRegex(ValueError, 'native recovery executable'):
            self.accepted()

    def test_runtime_recipe_or_offline_scope_substitution_rejected(self):
        path = Path(self.result['runtime_environment']['path'])
        original = read_json(path)
        for field, value in [('runtime_recipe', self.request), ('python_seed', self.request),
                             ('requirement_sources', []), ('offline', False), ('excluded_distributions', [])]:
            with self.subTest(field=field):
                document = dict(original); document[field] = value
                path.unlink(); self.result['runtime_environment'] = self.document(path, document); self.publish()
                with self.assertRaisesRegex(ValueError, 'reviewed offline recipe'): self.accepted()
