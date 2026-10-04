"""CPU fixture recovery creates a fresh environment without acquiring assets."""
from pathlib import Path
import tempfile
import unittest
from vipe_benchmark.files import file_record,read_json,write_json


class VideoRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.old=self.root/'jobs/plan069-D9-setup-001'
        self.old.mkdir(parents=True)
        self.source=self.old/'source';self.source.mkdir()
        (self.source/'run.py').write_bytes(b'original source')
        (self.old/'source.tar.gz').write_bytes(b'original archive')
        (self.old/'video_depth_anything_vits.pth').write_bytes(b'original checkpoint')
        (self.old/'failed-env-file').write_bytes(b'unchanged failed environment')
        self.seed=self.root/'seed-python';self.seed.write_bytes(b'python fixture')
        self.uv=self.root/'uv';self.uv.write_bytes(b'UV fixture')
        recipe=self.root/'recipe-v4.json'
        pins=['torch==2.14.1','torchvision==0.29.1']+[f'fixture-package-{i}==1.0' for i in range(46)]
        write_json(recipe,dict(schema='plan069-video-environment-recipe/v1',constraints=pins,
            requirements=pins,python_version='3.11'))
        self.request=dict(schema='plan069-video-setup-recovery-request/v1',record_kind='fixture',candidate='D9',
            job_id='plan069-D9-setup-recovery-001',original_setup=dict(source_archive=file_record(self.old/'source.tar.gz'),
            source_files=[file_record(self.source/'run.py')],checkpoint=file_record(self.old/'video_depth_anything_vits.pth')),
            runtime_environment=dict(recipe=file_record(recipe),runtime_profile='D9-D10-torch-2.14.1-pypi-frame-input',
                constraints=pins,requirements=pins,python_seed_executable=str(self.seed),python_seed=file_record(self.seed),
                uv=file_record(self.uv),python_version='3.11',requirement_sources=[file_record(recipe)],indexes=['https://pypi.org/simple']),
            fixture_allocation=dict(setup_seconds=120,download_bytes=0,artifact_bytes=10**7))
        self.output=self.root/'jobs/plan069-D9-setup-recovery-001';self.commands=[]

    def runner(self,command,*,environment,cwd,timeout,log):
        self.commands.append(command)
        self.assertEqual(environment['UV_OFFLINE'],'1')
        self.assertEqual(environment['CUDA_VISIBLE_DEVICES'],'')
        log.write_text('fixture command\n')
        if '-c' in command:log.write_text('{"python_version":"3.11"}\n')
        if 'venv' in command:
            path=Path(command[-1])/'bin/python';path.parent.mkdir(parents=True);path.write_bytes(b'fresh fixture python')
        if 'compile' in command:Path(command[command.index('--output-file')+1]).write_text('fixture lock\n')
        if '--output' in command:
            pins=self.request['runtime_environment']['constraints']
            write_json(command[command.index('--output')+1],dict(executable=str(self.output/'runtime/environment/bin/python'),
                versions={'python':'3.11','torch':'2.14.1','torchvision':'0.29.1'},
                packages=[dict(name=pin.split('==')[0],version=pin.split('==')[1],files=[]) for pin in pins],
                inventory_only=True,model_imports=False,gpu_operations=False))

    def test_reuses_exact_assets_and_keeps_original_failure_in_fresh_offline_runtime(self):
        from vipe_benchmark.video_setup_recovery import run_video_setup_recovery
        before={p:p.read_bytes() for p in self.old.rglob('*') if p.is_file()}
        result=run_video_setup_recovery(self.request,self.output,environment_runner=self.runner)
        self.assertEqual(result['status'],'complete')
        self.assertEqual(result['job_id'],'plan069-D9-setup-recovery-001')
        self.assertEqual(result['bytes_received'],0)
        self.assertEqual(result['source_archive'],self.request['original_setup']['source_archive'])
        self.assertEqual(Path(result['checkpoint']['path']).parent,self.output)
        self.assertEqual(before,{p:p.read_bytes() for p in self.old.rglob('*') if p.is_file()})
        for command in self.commands:
            if 'compile' in command or 'install' in command:self.assertIn('--offline',command)

    def test_actual_recovery_cannot_use_fixture_runner_or_create_output(self):
        from vipe_benchmark.video_setup_recovery import run_video_setup_recovery
        with self.assertRaisesRegex(ValueError,'cannot inject'):
            run_video_setup_recovery(dict(self.request,record_kind='actual'),self.output,
                request_path=str(self.root/'request.json'),environment_runner=self.runner)
        self.assertFalse(self.output.exists())
        self.assertEqual(self.commands,[])

    def test_failed_dependency_check_is_retained_without_rewriting_original(self):
        from vipe_benchmark.video_setup_recovery import run_video_setup_recovery
        before={p:p.read_bytes() for p in self.old.rglob('*') if p.is_file()}
        def fail(command,**kwargs):
            self.runner(command,**kwargs)
            if 'check' in command:raise RuntimeError('fixture dependency conflict')
        with self.assertRaisesRegex(RuntimeError,'dependency conflict'):
            run_video_setup_recovery(self.request,self.output,environment_runner=fail)
        self.assertTrue((self.output/'failure.json').exists())
        self.assertFalse((self.output/'result.json').exists())
        self.assertEqual(before,{p:p.read_bytes() for p in self.old.rglob('*') if p.is_file()})

    def test_existing_recovery_output_is_not_reused_or_overwritten(self):
        from vipe_benchmark.video_setup_recovery import run_video_setup_recovery
        self.output.mkdir();(self.output/'retained.txt').write_text('previous failed recovery')
        with self.assertRaisesRegex(ValueError,'immutable'):
            run_video_setup_recovery(self.request,self.output,environment_runner=self.runner)
        self.assertEqual((self.output/'retained.txt').read_text(),'previous failed recovery')
        self.assertEqual(self.commands,[])

    def test_decord_in_installed_inventory_stops_acceptance(self):
        from vipe_benchmark.video_setup_recovery import run_video_setup_recovery
        def contaminated(command,**kwargs):
            self.runner(command,**kwargs)
            if '--output' in command:
                path=Path(command[command.index('--output')+1]);value=read_json(path)
                value['packages'].append(dict(name='decord',version='0.6.0',files=[]))
                path.write_text(__import__('json').dumps(value))
        with self.assertRaisesRegex(ValueError,'must be absent'):
            run_video_setup_recovery(self.request,self.output,environment_runner=contaminated)
        self.assertFalse((self.output/'result.json').exists())
