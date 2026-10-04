"""Prospective PyPI selectors require exact distribution, budget and observations."""
import copy
import sys
from pathlib import Path
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark import video_environment as environment
from vipe_benchmark.config import ROOT
from vipe_benchmark.files import file_record, read_json, write_json, object_hash
from vipe_benchmark.depth_authorization import execution_authorization
from vipe_benchmark.depth_admission import VIDEO_PYPI_PROFILES, selected_profile_inventory
import test_vipe_benchmark_video_cu130 as fixtures

class VideoPyPITests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.VideoCu130Tests(); self.f.setUp(); self.addCleanup(self.f.tearDown)
        self.f.amended_authorization()
    def authority(self, mutate=None):
        fixture = fixtures.VideoCu130Tests(); fixture.setUp(); self.addCleanup(fixture.tearDown)
        path = fixture.amended_authorization()
        auth = read_json(path); review = read_json(auth['review']['path'])
        budget_path = ROOT / 'docs/research/vipe-alternatives/plan031-execution/video-pypi-budget-proposal-001/proposal.json'
        changes = {row['candidate']:row for row in read_json(budget_path)['changes']}
        for row in review['proposals']:
            if row['candidate'] in ('D9','D10'):
                row.update(profile=read_json(VIDEO_PYPI_PROFILES)['profiles'][row['candidate']],
                    profile_inventory=file_record(VIDEO_PYPI_PROFILES), runtime_recipe=file_record(environment.PYPI_RECIPE),
                    allocation=changes[row['candidate']]['proposed'])
        auth['video_amendment'] = dict(schema='plan069-video-distribution-budget-approval/v1', status='approved',
            distribution_approved=True, budget_approved=True, recipe=file_record(environment.PYPI_RECIPE), budget_review=file_record(budget_path))
        if mutate: mutate(review,auth)
        review_path=fixture.root / 'pypi-review.json'; write_json(review_path,review); auth['review']=file_record(review_path)
        for grant in auth['candidate_approvals']:
            grant['proposal_sha256']=object_hash(next(row for row in review['proposals'] if row['candidate']==grant['candidate']))
        path=fixture.root / 'pypi-authorization.json'; write_json(path,auth)
        return path
    def test_exact_pypi_recipe_and_49_package_pins(self):
        request=self.f.request(environment.PYPI_RECIPE)
        self.assertEqual(request['indexes'],['https://pypi.org/simple'])
        self.assertEqual(len(request['constraints']),49)
        self.assertIn('cuda-toolkit==13.0.3.0', request['constraints'])
        versions=dict(pin.split('==') for pin in request['constraints']);versions['xformers']=None
        environment.validate_runtime_versions(request,versions)
        with self.assertRaisesRegex(ValueError,'version differs'):
            environment.validate_runtime_versions(request,dict(versions,torch='2.14.1+cu130'))
    def test_runtime_observation_is_distinct_from_distribution_pin(self):
        request=self.f.request(environment.PYPI_RECIPE)
        observed=dict(schema='plan069-video-runtime-observation/v1',record_kind='actual',torch_version='2.14.1+cu130',torchvision_version='0.29.1+cu130',cuda_version='13.0')
        environment.validate_runtime_observation(request,observed)
        for key,value in [('cuda_version','12.1'),('record_kind','fixture'),('torch_version','2.14.0+cu130')]:
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'actual PyPI'):
                environment.validate_runtime_observation(request,dict(observed,**{key:value}))
        with self.assertRaisesRegex(ValueError,'actual PyPI'):
            environment.validate_runtime_observation(request,None)
    def test_module_observation_uses_imported_values(self):
        from types import SimpleNamespace
        modules={'torch':SimpleNamespace(__version__='2.14.1+cu130',version=SimpleNamespace(cuda='13.0')),'torchvision':SimpleNamespace(__version__='0.29.1+cu130')}
        with patch.dict(sys.modules,modules):
            result=environment.observe_runtime(self.f.request(environment.PYPI_RECIPE))
        self.assertEqual(result['cuda_version'],'13.0')
    def test_future_exact_approval_recognized_without_reset(self):
        _,_,proposal,_=execution_authorization('D9',root=self.f.root,authorization_path=self.authority())
        self.assertEqual(selected_profile_inventory(proposal),VIDEO_PYPI_PROFILES)
        self.assertEqual(proposal['allocation']['artifact_bytes'],9*2**30)
    def test_missing_distribution_or_budget_approval_rejected(self):
        for key in ('distribution_approved','budget_approved'):
            with self.subTest(key=key):
                path=self.authority(lambda review,auth:auth['video_amendment'].update({key:False}))
                with self.assertRaisesRegex(ValueError,'explicit PyPI'):
                    execution_authorization('D9',root=self.f.root,authorization_path=path)
    def test_one_byte_budget_drift_rejected(self):
        def mutate(review,auth):
            next(row for row in review['proposals'] if row['candidate']=='D9')['allocation']['artifact_bytes']+=1
        with self.assertRaisesRegex(ValueError,'exact bounds'):
            execution_authorization('D9',root=self.f.root,authorization_path=self.authority(mutate))
    def test_nonbudget_or_scientific_changes_rejected(self):
        def mutate(review,auth):
            next(row for row in review['proposals'] if row['candidate']=='D10')['workload']['clips']+=1
        with self.assertRaisesRegex(ValueError,'scope or lineage'):
            execution_authorization('D10',root=self.f.root,authorization_path=self.authority(mutate))
    def test_v3_setup_reaches_fixture_provisioner_under_exact_approval(self):
        import test_vipe_benchmark_video_setup as setup_fixtures
        from vipe_benchmark.video_setup import run_video_setup
        f=setup_fixtures.VideoSetupTests(); f.setUp(); self.addCleanup(f.tearDown)
        path=self.authority(); auth=read_json(path)
        original=f.runtime_request()
        runtime=environment.environment_request('D9', f.root, seed_executable=original['python_seed_executable'],
            uv_executable=original['uv']['path'],record_kind='fixture',recipe_path=environment.PYPI_RECIPE)
        canonical=next(row for row in read_json(auth['review']['path'])['proposals'] if row['candidate']=='D9')
        fixture_review=read_json(f.request['review']['path']); proposal=fixture_review['proposals'][0]
        for key in ('allocation','profile','profile_inventory','runtime_recipe'):
            proposal[key]=canonical[key]
        review_path=f.root/'v3-fixture-review.json';write_json(review_path,fixture_review)
        fixture_auth=read_json(f.request['authorization']['path']);fixture_auth['review']=file_record(review_path)
        fixture_auth['candidate_approvals'][0]['proposal_sha256']=object_hash(proposal)
        fixture_auth_path=f.root/'v3-fixture-authority.json';write_json(fixture_auth_path,fixture_auth)
        request=dict(f.request,review=file_record(review_path),authorization=file_record(fixture_auth_path),runtime_environment=runtime)
        def runner(command,**kwargs):
            f.environment_runner(command,**kwargs)
            if '--output' in command:
                import json
                p=Path(command[command.index('--output')+1]);inventory=read_json(p)
                packages=inventory['packages']
                for pin in runtime['constraints']:
                    name,version=pin.split('==')
                    row=next((row for row in packages if row['name'].lower()==name.lower()),None)
                    if row is None:
                        row=dict(name=name,version=version,files=[original['uv']]);packages.append(row)
                    row['version']=version
                p.write_text(json.dumps(inventory)+'\n')
        # Authority validation is covered against immutable DO001 above; here the
        # fixture seam binds its tiny checkpoint while exercising real provisioning.
        with patch('vipe_benchmark.depth_authorization.execution_authorization',return_value=(request['review'],request['authorization'],proposal,fixture_auth['candidate_approvals'][0])):
            result=run_video_setup(request,f.root/request['job_id'],acquire=f.acquire,environment_runner=runner)
        self.assertEqual(result['runtime_recipe'],file_record(environment.PYPI_RECIPE))

    def test_reset_rejected(self):
        with self.assertRaisesRegex(ValueError,'scope or lineage'):
            execution_authorization('D9',root=self.f.root,authorization_path=self.authority(lambda review,auth:auth.update(reset_previous_consumption=True)))

if __name__=='__main__':unittest.main()
