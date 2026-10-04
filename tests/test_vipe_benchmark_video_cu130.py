"""Versioned video runtime selection preserves old evidence and strict pins."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.files import file_record, read_json, write_json, object_hash
from vipe_benchmark import video_environment as environment

class VideoCu130Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.seed = self.root / 'python'; self.seed.write_bytes(b'fixture')
        self.uv = self.root / 'uv'; self.uv.write_bytes(b'fixture')
    def tearDown(self): self.temp.cleanup()
    def request(self, recipe=None):
        return environment.environment_request('D9', self.root,
            seed_executable=self.seed, uv_executable=self.uv,
            record_kind='fixture', recipe_path=recipe)
    def test_default_remains_original_recipe(self):
        request = self.request()
        self.assertEqual(request['recipe'], file_record(environment.RECIPE))
        self.assertNotIn('runtime_profile', request)
    def test_new_recipe_is_explicit_and_exact(self):
        request = self.request(environment.CU130_RECIPE)
        self.assertEqual(request['constraints'], ['torch==2.14.1+cu130', 'torchvision==0.29.1+cu130', 'numpy==1.24.0'])
        self.assertEqual(request['runtime_profile']['upstream_supported'], False)
    def test_unknown_recipe_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'versioned video recipe'):
            self.request(self.root / 'arbitrary.json')
    def test_upstream_requirements_and_profile_are_bound(self):
        request = self.request(environment.CU130_RECIPE)
        source = self.root / 'source'; source.mkdir()
        recipe = read_json(environment.RECIPE)
        (source / 'requirements.txt').write_text('\n'.join(recipe['upstream_requirements']) + '\n')
        for name in recipe['fallback_sources']:
            p = source / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_text('# native fixture\n')
        bound = environment.bind_source_environment(request, source, recipe['source_revision'], candidate='D9', record_kind='fixture')
        self.assertEqual(bound['runtime_profile'], request['runtime_profile'])
        bad = copy.deepcopy(request); bad['runtime_profile']['upstream_supported'] = True
        with self.assertRaisesRegex(ValueError, 'frozen native recipe'):
            environment.bind_source_environment(bad, source, recipe['source_revision'], candidate='D9', record_kind='fixture')
        (source / 'requirements.txt').write_text('torch==2.14.1\n')
        with self.assertRaisesRegex(ValueError, 'pinned source'):
            environment.bind_source_environment(request, source, recipe['source_revision'], candidate='D9', record_kind='fixture')
    def test_native_versions_require_exact_selected_cuda_build(self):
        request = self.request(environment.CU130_RECIPE)
        good = dict(torch='2.14.1+cu130', torchvision='0.29.1+cu130', numpy='1.24.0', xformers=None)
        environment.validate_runtime_versions(request, good)
        for key, value in [('torch', '2.14.1'), ('torchvision', '0.29.0+cu130'), ('numpy', '2.0.0'), ('xformers', '0.0.23')]:
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'video runtime'):
                environment.validate_runtime_versions(request, dict(good, **{key:value}))
    def test_old_profile_rejects_new_versions(self):
        with self.assertRaisesRegex(ValueError, 'video runtime'):
            environment.validate_runtime_versions(self.request(), dict(torch='2.14.1+cu130', torchvision='0.29.1+cu130', numpy='1.24.0', xformers=None))

    def amended_authorization(self, mutate=None):
        from vipe_benchmark.config import ROOT
        from vipe_benchmark.depth_admission import VIDEO_PROFILES
        prior_path = ROOT / 'docs/research/vipe-alternatives/plan031-execution/depth-approval-001.json'
        prior = read_json(prior_path)
        review = copy.deepcopy(read_json(prior['review']['path']))
        profiles = read_json(VIDEO_PROFILES)['profiles']
        for proposal in review['proposals']:
            if proposal['candidate'] in ('D9', 'D10'):
                proposal.update(profile=profiles[proposal['candidate']],
                    profile_inventory=file_record(VIDEO_PROFILES), runtime_recipe=file_record(environment.CU130_RECIPE))
        if mutate: mutate(review)
        review_path = self.root / 'review.json'; write_json(review_path, review)
        local_prior = self.root / 'docs/research/vipe-alternatives/plan031-execution/depth-approval-001.json'
        local_prior.parent.mkdir(parents=True, exist_ok=True); local_prior.write_bytes(prior_path.read_bytes())
        approval = dict(schema='plan069-depth-user-authorization/v1', status='DO',
            review=file_record(review_path), previous_authorization=file_record(prior_path),
            reset_previous_consumption=False, cap_amendment=prior['cap_amendment'],
            cap_approval=prior['cap_approval'], candidate_approvals=[dict(
                schema='plan069-depth-execution-approval/v1', status='approved',
                candidate=row['candidate'], proposal_sha256=object_hash(row), max_attempts=1)
                for row in review['proposals'] if row['candidate'] in ('D9', 'D10')])
        path = self.root / 'authorization.json'; write_json(path, approval)
        return path
    def test_versioned_profile_selection_is_video_only(self):
        from vipe_benchmark.depth_admission import VIDEO_PROFILES, selected_profile_inventory
        proposal = dict(candidate='D10', profile_inventory=file_record(VIDEO_PROFILES), runtime_recipe=file_record(environment.CU130_RECIPE))
        self.assertEqual(selected_profile_inventory(proposal), VIDEO_PROFILES)
        with self.assertRaisesRegex(ValueError, 'exact video runtime'):
            selected_profile_inventory(dict(proposal, candidate='D8'))
    def test_explicit_authorization_preserves_original_scope_and_attempts(self):
        from vipe_benchmark.depth_authorization import execution_authorization
        path = self.amended_authorization()
        _, authorization, proposal, _ = execution_authorization('D10', root=self.root, authorization_path=path)
        self.assertEqual(authorization, file_record(path))
        self.assertEqual(proposal['runtime_recipe'], file_record(environment.CU130_RECIPE))
        with self.assertRaisesRegex(ValueError, 'video-only'):
            execution_authorization('D8', root=self.root, authorization_path=path)
    def test_runtime_amendment_cannot_change_budgets_or_workload(self):
        from vipe_benchmark.depth_authorization import execution_authorization
        def change(review):
            next(row for row in review['proposals'] if row['candidate']=='D9')['allocation']['download_bytes'] += 1
        path = self.amended_authorization(change)
        with self.assertRaisesRegex(ValueError, 'scope or lineage'):
            execution_authorization('D9', root=self.root, authorization_path=path)
    def test_cli_authorization_selection_is_explicit(self):
        import basketball_vipe_video_setup_dispatch as setup
        with patch.object(sys, 'argv', ['video-setup', '--candidate', 'D9', '--authorization', '/tmp/new-do.json']), patch.object(setup, 'dispatch') as launch:
            setup.main()
        launch.assert_called_once_with('D9', 'plan031-20260913T032700Z', source_review_path=None, authorization_path='/tmp/new-do.json')

    def test_setup_keeps_original_source_and_new_profile_binding(self):
        import test_vipe_benchmark_video_setup as fixtures
        from vipe_benchmark.depth_admission import VIDEO_PROFILES
        from vipe_benchmark.video_setup import run_video_setup
        from vipe_benchmark.video_native import setup_environment
        fixture = fixtures.VideoSetupTests(); fixture.setUp(); self.addCleanup(fixture.tearDown)
        original = fixture.runtime_request()
        runtime = environment.environment_request('D9', fixture.root,
            seed_executable=original['python_seed_executable'], uv_executable=original['uv']['path'],
            record_kind='fixture', recipe_path=environment.CU130_RECIPE)
        review = read_json(fixture.request['review']['path']); proposal = review['proposals'][0]
        proposal.update(runtime_recipe=file_record(environment.CU130_RECIPE),
            profile=read_json(VIDEO_PROFILES)['profiles']['D9'], profile_inventory=file_record(VIDEO_PROFILES))
        new_review = fixture.root / 'cu130-review.json'; write_json(new_review, review)
        fixture.request['review'] = file_record(new_review)
        approval = read_json(fixture.request['authorization']['path'])
        approval.update(review=fixture.request['review']); approval['candidate_approvals'][0]['proposal_sha256'] = object_hash(proposal)
        new_approval = fixture.root / 'cu130-approval.json'; write_json(new_approval, approval)
        fixture.request['authorization'] = file_record(new_approval)
        def runner(command, **kwargs):
            fixture.environment_runner(command, **kwargs)
            if '--output' in command:
                path = command[command.index('--output') + 1]; inventory = read_json(path)
                for package in inventory['packages']:
                    if package['name'] == 'torch': package['version'] = '2.14.1+cu130'
                    if package['name'] == 'torchvision': package['version'] = '0.29.1+cu130'
                Path(path).write_text(json.dumps(inventory) + "\n")
        result = run_video_setup(dict(fixture.request, runtime_environment=runtime),
            fixture.root / fixture.request['job_id'], acquire=fixture.acquire, environment_runner=runner)
        self.assertEqual(result['runtime_recipe'], file_record(environment.CU130_RECIPE))
        self.assertEqual((Path(result['source_dir']) / 'requirements.txt').read_text().splitlines(), read_json(environment.RECIPE)['upstream_requirements'])
        with patch.object(sys, 'executable', result['python_executable']):
            setup_environment(result)
            stripped = dict(result); stripped.pop('runtime_profile')
            with self.assertRaisesRegex(ValueError, 'profile binding'):
                setup_environment(stripped)

if __name__ == '__main__': unittest.main()
