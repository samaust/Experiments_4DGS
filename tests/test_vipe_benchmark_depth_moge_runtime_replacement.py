"""D6 runtime replacement over its completed setup (CPU fixtures; no install, model or GPU)."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vipe_benchmark.config import ROOT, load
from vipe_benchmark.files import file_record, object_hash, read_json, write_json

ORIGINAL = 'plan069-D6-setup-001'
JOB = 'plan069-D6-setup-recovery-001'
CLEAN = dict(cleanup_confirmed=True, cleanup_uncertain=False, surviving_pids=[], deadline_exceeded=False)


class RuntimeReplacementFixture(unittest.TestCase):
    def setUp(self):
        from vipe_benchmark import depth_moge_runtime_replacement as module
        from vipe_benchmark.depth_admission import local_source_records
        from vipe_benchmark.moge_setup import source_tree_records
        self.module = module
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.run_root = Path(temp.name).resolve() / 'run'
        job = self.run_root / 'jobs' / ORIGINAL
        (job / 'source/moge/model').mkdir(parents=True)
        (job / 'source/moge/model/v3.py').write_text('fixture v3\n')
        (job / 'source/LICENSE').write_text('fixture licence\n')
        (self.run_root / 'requests').mkdir()
        authority = self.write('authority.json', dict(schema='plan069-D6-runtime-replacement-authority/v1', status='approved'))
        pin = patch.object(module, 'AUTHORITY', Path(authority['path']))
        pin.start()
        self.addCleanup(pin.stop)
        self.maps = dict(candidate='D6', max_attempts=1, candidate_config=dict(
            code=dict(url='https://github.com/microsoft/MoGe', revision='74fbce054ebed49800de42d0ad0e83495065719a'),
            weights=dict(url='https://huggingface.co/Ruicheng/moge-3-vitl', revision='1' * 40)),
            allocation=dict(setup_seconds=1800, download_bytes=7923784338, artifact_bytes=9663676416, gpu_seconds=3600))
        from vipe_benchmark import depth_map_allowance
        amendment = self.write('slot-amendment.json', dict(schema=depth_map_allowance.SLOT_ARTIFACT_AMENDMENT_SCHEMA,
            status='approved', candidate='D6', proposal_sha256=object_hash(self.maps),
            additional_artifact_bytes=8 * 2**30, approval_basis='fixture'))
        pins = patch.dict(depth_map_allowance.SLOT_ARTIFACT_AMENDMENTS, {'D6': Path(amendment['path'])})
        pins.start()
        self.addCleanup(pins.stop)
        review002 = self.write('review002.json', dict(schema='plan069-depth-execution-review/v1', status='REVIEW', proposals=[self.maps]))
        do002 = self.write('do002.json', dict(schema='plan069-depth-user-authorization/v1', status='DO', review=review002,
            candidate_approvals=[dict(candidate='D6', status='approved', max_attempts=1, proposal_sha256=object_hash(self.maps))]))
        self.recipe0 = dict(schema='plan069-depth-environment-request/v1', candidate='D6', record_kind='actual',
            requirements=['torch>=2.4', 'triton>=3.2.0'], constraints=['torch==2.6.0+cu124', 'triton==3.2.0'],
            indexes=['https://pypi.org/simple', 'https://download.pytorch.org/whl/cu124'],
            flex_cache_path=str(job / 'runtime/flex-cache/autotune_cache.json'), python_version='3.11')
        request = self.write('requests/' + ORIGINAL + '.json', dict(schema='plan069-depth-setup-request/v1',
            record_kind='actual', candidate='D6', job_id=ORIGINAL, ledger_path=str(self.run_root / 'ledger.jsonl'),
            review=review002, authorization=do002, runtime_environment=self.recipe0))
        flex = self.raw('jobs/%s/runtime-source-build/flex-gemm-derived.tar.gz' % ORIGINAL)
        dependency_sources = [dict(name='flex-gemm', revision='f' * 40, record=flex, install_local_offline=True)]
        runtime = self.write('jobs/%s/runtime/result.json' % ORIGINAL, dict(status='complete', candidate='D6'))
        self.original_setup = dict(schema='plan069-depth-setup-result/v1', status='complete', candidate='D6',
            job_id=ORIGINAL, record_kind='actual', review=review002, authorization=do002,
            source_revision=self.maps['candidate_config']['code']['revision'],
            weight_revision=self.maps['candidate_config']['weights']['revision'],
            source_archive=self.raw('jobs/%s/source.tar.gz' % ORIGINAL), checkpoint=self.raw('jobs/%s/model.pt' % ORIGINAL, b'ckpt'),
            source_dir=str(job / 'source'), source_tree=source_tree_records(job / 'source'), bytes_received=1501445303,
            runtime_environment=runtime, python_executable='/old/python', dependency_sources=dependency_sources)
        setup = self.write('jobs/%s/result.json' % ORIGINAL, self.original_setup)
        failure = self.write('jobs/plan069-D6-maps-001/failure.json', dict(completed_map_rows=0, status='failed'))
        self.rows: list[dict] = []
        self.append(dict(event='depth_setup_authorized', candidate='D6', review=review002, authorization=do002,
                         proposal_sha256=object_hash(self.maps), resource_snapshot=dict(download_bytes=10, artifact_bytes=20)))
        self.append(dict(event='reserve', job_id=ORIGINAL, resource='setup', seconds=1800, evidence=dict(request=request)))
        self.append(dict(event='finish', job_id=ORIGINAL, resource='setup', status='complete', elapsed_seconds=204.8,
                         result=setup, **CLEAN))
        self.append(dict(event='finish', job_id='plan069-D6-maps-001', resource='gpu', status='failed',
                         failure_kind='worker_failure', elapsed_seconds=38., **CLEAN))
        self.maps_rows = len(self.rows)
        self.original = dict(setup=setup, setup_finish_event_sha256=self.rows[2]['event_sha256'], request=request,
                             maps_failure=dict(finish_event_sha256=self.rows[3]['event_sha256'], failure=failure))
        self.recipe = module.replacement_recipe(self.recipe0, self.run_root)
        self.proposal = dict(schema=module.PROPOSAL_SCHEMA, kind=module.KIND, candidate='D6', job_id=JOB, max_attempts=1,
            recovery_seconds=module.RECOVERY_SECONDS, downloads=0, user_authority=authority, original_setup=self.original,
            map_proposal_sha256=object_hash(self.maps), runtime_recipe=self.recipe)
        self.worker = file_record(ROOT / 'scripts/basketball_vipe_moge_runtime_replacement.py')
        self.sources = local_source_records('D6')
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
        row = dict(data, sequence=len(self.rows), recorded_unix=1., previous_sha256=self.rows[-1]['event_sha256'] if self.rows else None)
        row['event_sha256'] = object_hash(row)
        self.rows.append(row)
        (self.run_root / 'ledger.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in self.rows))

    def approve(self, *, proposal_changes=None, approval_changes=None, request_changes=None):
        proposal = dict(self.proposal, **(proposal_changes or {}))
        review = self.write('recovery-review.json', dict(schema='plan069-depth-execution-review/v1', status='REVIEW',
                                                          setup_recovery_proposal=proposal))
        granted = dict(dict(candidate='D6', job_id=JOB, status='approved', max_attempts=1,
                            proposal_sha256=object_hash(proposal)), **(approval_changes or {}))
        self.do = self.write('recovery-do.json', dict(schema='plan069-depth-user-authorization/v1', status='DO',
                                                      review=review, setup_recovery_approval=granted))
        source = self.write('source-review.json', dict(schema='plan069-depth-source-review/v1', status='passed', candidate='D6',
            reviewer='fixture', local_sources=self.sources, setup_recovery_proposal_sha256=object_hash(proposal)))
        request = dict(schema='plan069-depth-setup-recovery-request/v1', record_kind='actual', candidate='D6', job_id=JOB,
            ledger_path=str(self.run_root / 'ledger.jsonl'), review=review, authorization=self.do, source_review=source,
            original_setup=self.original, runtime_environment=proposal['runtime_recipe'])
        request.update(request_changes or {})
        self.request = self.write('requests/' + JOB + '.json', request)

    def ledger(self):
        from vipe_benchmark.ledger import Ledger
        return Ledger(self.run_root / 'ledger.jsonl', dict(load(), new_download_gib_limit=110, new_artifact_disk_gib_limit=210))

    def authorize(self):
        command = [sys.executable, self.worker['path'], '--request', self.request['path'], '--output', str(self.run_root / 'jobs' / JOB)]
        with patch('vipe_benchmark.execution.resources', return_value=dict(download_bytes=10, artifact_bytes=20, gpu_pids=[])):
            return self.ledger().authorize_depth_setup_recovery(self.request, command=command, worker=self.worker,
                                                                 executable=file_record(sys.executable))

    def assert_refused(self, pattern):
        before = (self.run_root / 'ledger.jsonl').read_bytes()
        with self.assertRaisesRegex(ValueError, pattern):
            self.authorize()
        self.assertEqual((self.run_root / 'ledger.jsonl').read_bytes(), before)


class RuntimeReplacementAuthorityTests(RuntimeReplacementFixture):
    def test_completed_setup_and_failed_maps_authorize_one_offline_replacement(self):
        grant = self.authorize()
        self.assertEqual((grant['candidate'], grant['job_id'], grant['seconds']), ('D6', JOB, 900))
        self.assertEqual(grant['byte_limits'], dict(download_bytes=110 * 2**30, artifact_bytes=210 * 2**30))
        with self.assertRaisesRegex(ValueError, 'already authorized or consumed'):
            self.authorize()

    def test_recipe_changes_only_runtime_pins_indexes_and_owned_cache(self):
        changed = {key for key in self.recipe if self.recipe[key] != self.recipe0.get(key)}
        self.assertEqual(changed, {'constraints', 'indexes', 'flex_cache_path'})
        self.assertIn('triton==3.8.0', self.recipe['constraints'])
        self.assertEqual(Path(self.recipe['flex_cache_path']).parents[1], self.run_root / 'jobs' / JOB / 'runtime')

    def test_changed_recipe_downloads_or_unpinned_authority_are_refused(self):
        bad = dict(self.recipe, constraints=['torch==2.6.0+cu124'])
        self.approve(proposal_changes=dict(runtime_recipe=bad))
        self.assert_refused('replacement runtime recipe')
        self.approve(proposal_changes=dict(downloads=1))
        self.assert_refused('explicit separately approved')
        self.approve(proposal_changes=dict(user_authority=dict(self.proposal['user_authority'], sha256='0' * 64)))
        self.assert_refused('explicit separately approved')
        self.approve(approval_changes=dict(proposal_sha256='0' * 64))
        self.assert_refused('explicit separately approved')

    def test_replacement_requires_the_clean_zero_output_failed_maps(self):
        failure = read_json(self.original['maps_failure']['failure']['path'])
        Path(self.original['maps_failure']['failure']['path']).write_text(json.dumps(dict(failure, completed_map_rows=3)))
        self.original = dict(self.original, maps_failure=dict(self.original['maps_failure'],
                                                              failure=file_record(self.original['maps_failure']['failure']['path'])))
        self.proposal['original_setup'] = self.original
        self.approve()
        self.assert_refused('zero-output failed D6 maps')

    def test_maps_failure_gate_matches_the_retry_rule(self):
        (self.run_root / 'jobs/plan069-D6-maps-001/result.json').write_text('{}')
        self.assert_refused('zero-output failed D6 maps')
        (self.run_root / 'jobs/plan069-D6-maps-001/result.json').unlink()
        rows = [{k: v for k, v in row.items() if k not in ('sequence', 'recorded_unix', 'previous_sha256', 'event_sha256')}
                for row in self.rows]
        rows[3]['cleanup_uncertain'] = True
        self.rows = []
        for row in rows:
            self.append(row)
        self.original = dict(self.original, setup_finish_event_sha256=self.rows[2]['event_sha256'],
                             maps_failure=dict(self.original['maps_failure'], finish_event_sha256=self.rows[3]['event_sha256']))
        self.proposal['original_setup'] = self.original
        self.approve()
        self.assert_refused('zero-output failed D6 maps')

    def test_replacement_requires_the_completed_original_setup(self):
        rows = [{k: v for k, v in row.items() if k not in ('sequence', 'recorded_unix', 'previous_sha256', 'event_sha256')}
                for row in self.rows]
        rows[2]['status'] = 'failed'
        self.rows = []
        for row in rows:
            self.append(row)
        self.original = dict(self.original, setup_finish_event_sha256=self.rows[2]['event_sha256'],
                             maps_failure=dict(self.original['maps_failure'], finish_event_sha256=self.rows[3]['event_sha256']))
        self.proposal['original_setup'] = self.original
        self.approve()
        self.assert_refused('completed setup|original D6 setup')


class RuntimeReplacementRunTests(RuntimeReplacementFixture):
    def fake_provision(self, request, output, config, **kwargs):
        self.provisioned = dict(request=request, kwargs=kwargs)
        output.mkdir(parents=True)
        write_json(output / 'request.json', request)
        result = dict(status='complete', candidate='D6', python_executable=str(output / 'environment/bin/python'),
                      source_packages=request['sources'], flex_cache_path=request['flex_cache_path'])
        write_json(output / 'result.json', result)
        return result

    def run_replacement(self, *, downloads=(10, 10), owned=12 * 2**30):
        self.authorize()
        output = self.run_root / 'jobs' / JOB
        config = dict(load(), new_download_gib_limit=110, new_artifact_disk_gib_limit=210)
        snapshots = iter([dict(download_bytes=value, artifact_bytes=20) for value in downloads] * 2)
        with patch('vipe_benchmark.moge_setup._active_reservation', return_value=(self.run_root, config)), \
                patch('vipe_benchmark.depth_environment.provision_depth_environment', side_effect=self.fake_provision), \
                patch('vipe_benchmark.budgets.budget_snapshot', side_effect=lambda root: next(snapshots)), \
                patch('vipe_benchmark.depth_map_allowance.owned_slot_bytes', return_value=owned):
            return self.module.run_runtime_replacement(read_json(self.request['path']), output, request_path=self.request['path'])

    def test_transferred_bytes_or_slot_overrun_fail_the_replacement(self):
        with self.assertRaisesRegex(ValueError, 'transferred bytes'):
            self.run_replacement(downloads=(10, 11))
        failure = read_json(self.run_root / 'jobs' / JOB / 'failure.json')
        self.assertEqual(failure['status'], 'failed')
        self.assertIn('transferred bytes', failure['error'])

    def test_amended_slot_overrun_fails_the_replacement(self):
        with self.assertRaisesRegex(ValueError, 'whole-slot artifact allocation'):
            self.run_replacement(owned=18 * 2**30)

    def test_output_escaping_the_recovery_job_is_rejected(self):
        result = self.run_replacement()
        normalized = self.module.validate_recovery_request(self.request, self.ledger().events(), self.run_root, historical=True)
        for key, value in (('checkpoint', self.original_setup['checkpoint']),
                           ('python_executable', '/elsewhere/python')):
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'changed original|escaped the owned'):
                self.module.validate_recovery_result(dict(result, **{key: value}), normalized)

    def test_offline_replacement_links_sources_and_checkpoint_without_new_bytes(self):
        result = self.run_replacement()
        output = self.run_root / 'jobs' / JOB
        self.assertTrue(self.provisioned['kwargs']['offline'])
        self.assertEqual(self.provisioned['kwargs']['download_limit'], 10)
        self.assertEqual(self.provisioned['request']['constraints'], self.recipe['constraints'])
        self.assertEqual(os.stat(output / 'model.pt').st_ino, os.stat(self.original_setup['checkpoint']['path']).st_ino)
        self.assertEqual(os.stat(output / 'source/moge/model/v3.py').st_ino,
                         os.stat(Path(self.original_setup['source_dir']) / 'moge/model/v3.py').st_ino)
        self.assertEqual((result['new_bytes_received'], result['bytes_received']), (0, 1501445303))
        self.assertEqual(result['source_archive'], self.original_setup['source_archive'])

    def test_completed_replacement_is_the_accepted_setup_for_D6(self):
        from vipe_benchmark.setup_recovery_core import accepted_setup
        self.run_replacement()
        self.rows.append(json.loads((self.run_root / 'ledger.jsonl').read_text().splitlines()[-1]))
        result = file_record(self.run_root / 'jobs' / JOB / 'result.json')
        self.append(dict(event='reserve', job_id=JOB, resource='setup', seconds=900, evidence=dict(request=self.request)))
        self.append(dict(event='finish', job_id=JOB, resource='setup', status='complete', elapsed_seconds=60., result=result, **CLEAN))
        accepted, job = accepted_setup('D6', result, self.ledger().events(), self.run_root)
        self.assertEqual((job, accepted['kind']), (JOB, 'runtime_replacement'))
        lineage = self.module.accepted_setup_lineage(result, self.ledger().events(), self.run_root)
        self.assertEqual(lineage['map_proposal'], self.maps)

    def test_changed_linked_source_is_rejected(self):
        result = self.run_replacement()
        target = self.run_root / 'jobs' / JOB / 'source/LICENSE'
        target.unlink(); target.write_text('changed\n')
        normalized = self.module.validate_recovery_request(self.request, self.ledger().events(), self.run_root, historical=True)
        with self.assertRaisesRegex(ValueError, 'changed original sources'):
            self.module.validate_recovery_result(result, normalized)


class OfflineProvisioningTests(unittest.TestCase):
    def test_offline_mode_passes_offline_to_every_uv_resolver_and_installer_step(self):
        import inspect
        from vipe_benchmark import depth_environment
        source = inspect.getsource(depth_environment.provision_depth_environment)
        self.assertIn("cached = ['--offline'] if offline else []", source)
        self.assertIn("'resolve', offline=offline", source)
        self.assertIn("'locked-dependencies',\n            offline=offline", source)
        self.assertIn("'venv', offline=offline", source)

    def test_D6_recovery_job_is_in_the_table_and_closure(self):
        from vipe_benchmark.setup_recovery_core import RECOVERY_CANDIDATES, candidate_for_job
        from vipe_benchmark.depth_admission import local_source_records
        self.assertEqual(candidate_for_job(JOB), 'D6')
        self.assertIsNone(candidate_for_job(ORIGINAL))
        self.assertFalse(RECOVERY_CANDIDATES['D6']['legacy_lineage'])
        with patch('vipe_benchmark.depth_admission.file_record', side_effect=lambda path: dict(path=str(path))):
            paths = {r['path'] for r in local_source_records('D6')}
        for suffix in ('depth_moge_runtime_replacement.py', 'basketball_vipe_moge_runtime_replacement.py',
                       'basketball_vipe_moge_runtime_replacement_dispatch.py'):
            self.assertTrue(any(p.endswith(suffix) for p in paths), suffix)


if __name__ == '__main__':
    unittest.main()


class AmendmentChainTests(unittest.TestCase):
    def test_a_budget_keeps_the_superseded_amendment_it_was_bound_to(self):
        from vipe_benchmark import depth_map_allowance as allowance
        proposal = dict(candidate='DX', allocation=dict(download_bytes=100, artifact_bytes=200))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def amendment(name, extra, previous=None):
                write_json(root / name, dict(schema=allowance.SLOT_ARTIFACT_AMENDMENT_SCHEMA, status='approved',
                    candidate='DX', proposal_sha256=object_hash(proposal), additional_artifact_bytes=extra,
                    approval_basis='fixture', **({'previous_amendment': previous} if previous else {})))
                return file_record(root / name)
            first = amendment('a1.json', 50)
            second = amendment('a2.json', 80, previous=first)
            foreign = amendment('a3.json', 99)
            with patch.dict(allowance.SLOT_ARTIFACT_AMENDMENTS, {'DX': root / 'a2.json'}):
                self.assertEqual(allowance.slot_allocation(proposal)['artifact_bytes'], 280)
                self.assertEqual(allowance.budget_slot_allocation(proposal, dict(artifact_amendment=first))['artifact_bytes'], 250)
                self.assertEqual(allowance.budget_slot_allocation(proposal, dict(artifact_amendment=second))['artifact_bytes'], 280)
                for bound in (foreign, None):
                    with self.subTest(bound=bound), self.assertRaisesRegex(ValueError, 'amendment differs'):
                        allowance.budget_slot_allocation(proposal, dict(artifact_amendment=bound))
            self.assertEqual(allowance.budget_slot_allocation(proposal, {})['artifact_bytes'], 200)

    def test_retained_D6_maps001_budgets_still_validate_under_amendment001(self):
        from vipe_benchmark.depth_authorization import execution_authorization
        from vipe_benchmark.depth_map_allowance import approved_amendments, budget_slot_allocation
        _, _, proposal, _ = execution_authorization('D6')
        chain = approved_amendments(proposal)
        self.assertEqual([extra for _, extra in chain], [8 * 2**30, 4 * 2**30])
        self.assertEqual(budget_slot_allocation(proposal, dict(artifact_amendment=chain[1][0]))['artifact_bytes'],
                         proposal['allocation']['artifact_bytes'] + 4 * 2**30)
