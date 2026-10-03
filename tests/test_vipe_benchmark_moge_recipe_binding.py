"""Actual setup binds the independently reviewed recipe before side effects."""
from pathlib import Path
import json
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.files import file_record, read_json, write_json
from vipe_benchmark.moge_environment import environment_request
import basketball_vipe_moge_setup_dispatch as dispatch_cli
from vipe_benchmark.moge_setup import run_moge_setup
import test_vipe_benchmark_moge_environment as environment_fixtures


SETUP_SOURCES = (
    'scripts/vipe_benchmark/moge_setup.py', 'scripts/vipe_benchmark/moge_native.py',
    'scripts/vipe_benchmark/moge_environment.py', 'scripts/vipe_benchmark/moge_source_build.py',
    'scripts/vipe_benchmark/depth_environment.py', 'scripts/vipe_benchmark/depth_authorization.py',
    'scripts/vipe_benchmark/runtime_inventory.py', 'scripts/basketball_vipe_moge_setup.py',
    'scripts/basketball_vipe_moge_setup_dispatch.py')


class RecipeBinding(unittest.TestCase):
    def setUp(self):
        fixture = environment_fixtures.EnvironmentRecipeTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        self.root = fixture.root
        self.run_id = 'plan031-20260913T032700Z'
        self.local = self.root / '.local/vipe-alternatives' / self.run_id
        self.recipe = environment_request('D5', fixture.source,
            python_seed_executable=fixture.seed, uv=fixture.uv,
            dependency_sources=fixture.dependencies,
            runtime_directory=self.local / 'jobs/plan069-D5-setup-001/runtime')
        self.recipe_path = self.root / 'reviewed-runtime.json'
        write_json(self.recipe_path, self.recipe)
        for name in SETUP_SOURCES:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('fixture reviewed source')
        self.current_sources = [file_record(self.root / name) for name in SETUP_SOURCES]
        self.profile = self.root / 'profiles.json'
        write_json(self.profile, dict(profile='fixture'))
        source_review = self.root / 'docs/research/vipe-alternatives/plan031-execution/depth-D5-source-review-001.json'
        source_review.parent.mkdir(parents=True)
        self.source_review = source_review
        write_json(source_review, dict(schema='plan069-depth-source-review/v1', status='passed',
            candidate='D5', reviewer='independent fixture reviewer', source_revision='pinned-revision',
            profile_inventory=file_record(self.profile), local_sources=self.current_sources,
            setup_sources=self.current_sources, runtime_recipe=file_record(self.recipe_path)))
        self.proposal = dict(allocation=dict(artifact_bytes=1000000, setup_seconds=1800),
            candidate_config=dict(code=dict(revision='pinned-revision')), profile_inventory=file_record(self.profile))

    def dispatch(self, path, *, supervisor=None, source_review_path=None):
        ledger = MagicMock()
        self.ledger = ledger
        original_read = Path.read_text
        def read_path(path, *args, **kwargs):
            return 'systemd' if str(path) == '/proc/1/comm' else original_read(path, *args, **kwargs)
        with patch.object(dispatch_cli, 'ROOT', self.root), \
             patch.object(dispatch_cli, 'shared_run_root', return_value=self.root), \
             patch.object(dispatch_cli, 'execution_authorization', return_value=({}, {}, self.proposal, {})), \
             patch.object(dispatch_cli, 'Ledger', return_value=ledger), \
             patch('vipe_benchmark.depth_admission.local_source_records', return_value=self.current_sources), \
             patch.object(dispatch_cli, 'resources', return_value=dict(gpu_pids=[])), \
             patch.object(dispatch_cli, 'supervise', side_effect=supervisor or AssertionError('reservation reached')), \
             patch.object(Path, 'read_text', read_path):
            if source_review_path is None:
                dispatch_cli.dispatch('D5', self.run_id, path)
            else:
                dispatch_cli.dispatch('D5', self.run_id, path, source_review_path=source_review_path)
        return ledger

    def test_valid_self_consistent_substitutions_rejected_before_request_or_reservation(self):
        for field in ('python_seed', 'uv', 'requirement_metadata'):
            with self.subTest(field=field):
                alternate = dict(self.recipe)
                if field == 'python_seed':
                    seed = self.root / 'different-python'
                    seed.write_bytes(b'different valid seed')
                    alternate.update(python_seed=file_record(seed), python_seed_executable=str(seed))
                elif field == 'uv':
                    uv = self.root / 'different-uv'
                    uv.write_bytes(b'different valid uv')
                    alternate['uv'] = file_record(uv)
                else:
                    source = self.root / 'different-source'
                    source.mkdir()
                    (source / 'pyproject.toml').write_bytes((self.fixture.source / 'pyproject.toml').read_bytes())
                    alternate['requirement_sources'] = [file_record(source / 'pyproject.toml')] + alternate['requirement_sources'][1:]
                path = self.root / (field + '-runtime.json')
                write_json(path, alternate)
                with self.assertRaisesRegex(ValueError, 'reviewed.*recipe'):
                    self.dispatch(path)
                self.assertFalse((self.local / 'requests/plan069-D5-setup-001.json').exists())
                self.assertFalse((self.local / 'jobs/plan069-D5-setup-001').exists())
                self.ledger.authorize_depth_setup.assert_not_called()

    def test_exact_reviewed_recipe_is_saved_with_supervision_evidence(self):
        def supervise(ledger, job, command, output, **kwargs):
            saved = read_json(self.local / 'requests/plan069-D5-setup-001.json')
            self.assertEqual(saved['runtime_environment'], self.recipe)
            self.assertEqual(saved['runtime_environment_record'], file_record(self.recipe_path))
            self.assertEqual(kwargs['evidence']['runtime_recipe'], file_record(self.recipe_path))
            output.mkdir(parents=True)
            write_json(output / 'result.json', dict(status='complete'))
            return dict(status='complete')
        ledger = self.dispatch(self.recipe_path, supervisor=supervise)
        ledger.authorize_depth_setup.assert_called_once()

    def test_worker_refuses_inline_substitution_before_acquisition_or_reservation(self):
        acquire = MagicMock(side_effect=AssertionError('acquisition reached'))
        request = dict(record_kind='actual', candidate='D5', runtime_environment=dict(self.recipe),
            runtime_environment_record=file_record(self.recipe_path))
        alternate = self.root / 'worker-alternate-uv'
        alternate.write_bytes(b'other self consistent uv')
        request['runtime_environment']['uv'] = file_record(alternate)
        output = self.root / 'plan069-D5-setup-001'
        with patch('vipe_benchmark.moge_setup._active_reservation') as reservation:
            with self.assertRaisesRegex(ValueError, 'inline.*differs.*reviewed'):
                run_moge_setup(request, output, acquire=acquire)
        reservation.assert_not_called()
        acquire.assert_not_called()
        self.assertFalse(output.exists())

    def test_worker_accepts_exact_recipe_before_fake_acquisition(self):
        import test_vipe_benchmark_moge_setup as setup_fixtures
        setup = setup_fixtures.MoGeSetupTests()
        setup.setUp()
        self.addCleanup(setup.tearDown)
        request = dict(setup.requests['D5'], record_kind='actual', runtime_environment=self.recipe,
            runtime_environment_record=file_record(self.recipe_path))
        acquire = MagicMock(side_effect=RuntimeError('fake acquisition boundary'))
        config = dict(new_download_gib_limit=110, new_artifact_disk_gib_limit=210)
        output = setup.root / 'plan069-D5-setup-001'
        with patch('vipe_benchmark.moge_setup._active_reservation', return_value=(setup.root, config)):
            with self.assertRaisesRegex(RuntimeError, 'fake acquisition boundary'):
                run_moge_setup(request, output, acquire=acquire)
        acquire.assert_called_once()
        self.assertEqual(read_json(output / 'request.json')['runtime_environment_record'], file_record(self.recipe_path))

    def test_explicit_review002_is_bound_and_review001_remains_unchanged(self):
        selected = self.root / 'source-review002.json'
        write_json(selected, read_json(self.source_review))
        blocked = read_json(self.source_review)
        blocked['status'] = 'blocked'
        self.source_review.write_text(json.dumps(blocked) + '\n')
        before = file_record(self.source_review)
        def supervise(ledger, job, command, output, **kwargs):
            self.assertEqual(kwargs['evidence']['source_review'], file_record(selected))
            output.mkdir(parents=True)
            write_json(output / 'result.json', dict(status='complete'))
            return dict(status='complete')
        self.dispatch(self.recipe_path, source_review_path=selected, supervisor=supervise)
        self.assertEqual(file_record(self.source_review), before)

    def test_wrong_candidate_stale_or_substituted_review_rejected_before_request(self):
        for field in ('candidate', 'local_sources', 'source_revision', 'runtime_recipe', 'status'):
            with self.subTest(field=field):
                selected = self.root / ('selected-' + field + '.json')
                document = read_json(self.source_review)
                if field == 'candidate':
                    document[field] = 'D6'
                elif field == 'local_sources':
                    document[field][0]['sha256'] = '0' * 64
                elif field == 'source_revision':
                    document[field] = 'different-pinned-revision'
                elif field == 'status':
                    document[field] = 'blocked'
                else:
                    alternate = self.root / 'other-reviewed-runtime.json'
                    write_json(alternate, self.recipe)
                    document[field] = file_record(alternate)
                write_json(selected, document)
                with self.assertRaisesRegex(ValueError, 'current.*source review|reviewed.*recipe'):
                    self.dispatch(self.recipe_path, source_review_path=selected)
                self.ledger.authorize_depth_setup.assert_not_called()
                self.assertFalse((self.local / 'requests/plan069-D5-setup-001.json').exists())
                self.assertFalse((self.local / 'jobs/plan069-D5-setup-001').exists())


if __name__ == '__main__':
    unittest.main()
