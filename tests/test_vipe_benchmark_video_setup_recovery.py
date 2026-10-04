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


class RecoveryAcceptanceTests(unittest.TestCase):
    runner=VideoRecoveryTests.runner

    def setUp(self):
        VideoRecoveryTests.setUp(self)
        from vipe_benchmark.video_setup_recovery import run_video_setup_recovery
        import json
        self.result=run_video_setup_recovery(self.request,self.output,environment_runner=self.runner)
        self.request.update(record_kind='actual',review={},authorization={},source_review={})
        self.request_path=self.root/'request.json';write_json(self.request_path,self.request)
        self.request_record=file_record(self.request_path)
        self.binding=dict(request=self.request_record,original=self.request['original_setup'],
            runtime_environment=self.request['runtime_environment'],review={},authorization={},source_review={},
            map_proposal=dict(candidate_config=dict(code=dict(revision='source-rev'),weights=dict(revision='weight-rev'))))
        self.result.update(record_kind='actual',request=self.request_record,review={},authorization={},source_review={},
            source_revision='source-rev',weight_revision='weight-rev',offline_guard=dict(
                policy='seccomp: Unix-domain sockets only; io_uring_setup denied',probes=dict(
                    AF_INET='EPERM (expected offline self-test)',AF_INET6='EPERM (expected offline self-test)',AF_UNIX='allowed local IPC')))
        runtime=read_json(self.result['runtime_environment']['path']);runtime['record_kind']='actual'
        receipts=[]
        for record in runtime['command_receipts']:
            value=read_json(record['path']);value['record_kind']='actual'
            Path(record['path']).write_text(json.dumps(value));receipts.append(file_record(record['path']))
        runtime['command_receipts']=receipts
        Path(self.result['runtime_environment']['path']).write_text(json.dumps(runtime))
        self.result['runtime_environment']=file_record(self.result['runtime_environment']['path'])
        self.save_result()

    def save_result(self):
        import json
        (self.output/'result.json').write_text(json.dumps(self.result))
        return file_record(self.output/'result.json')

    def validate(self):
        import sys,types
        from unittest.mock import Mock,patch
        from vipe_benchmark.video_setup_recovery import validate_recovery_result
        authority=Mock(return_value=self.binding)
        module=types.SimpleNamespace(validate_recovery_request=authority)
        with patch.dict(sys.modules,{'vipe_benchmark.depth_setup_recovery':module}):
            value=validate_recovery_result(self.save_result(),self.request_record,[],self.root)
        authority.assert_called_once_with(self.request_record,[],self.root,require_reservation=True)
        return value

    def test_active_reservation_acceptance_checks_real_scope_without_finish(self):
        self.assertEqual(self.validate()['status'],'complete')

    def test_scope_and_approval_mutations_rejected(self):
        for key,value in [('record_kind','fixture'),('bytes_received',1),('authorization',{'changed':True}),
                          ('source_revision','other'),('original_failure_preserved',False),('automatic_retries',1)]:
            with self.subTest(key=key):
                previous=self.result[key];self.result[key]=value
                with self.assertRaises(ValueError):self.validate()
                self.result[key]=previous

    def test_copied_checkpoint_rejected_even_with_same_bytes(self):
        path=Path(self.result['checkpoint']['path']);data=path.read_bytes();path.unlink();path.write_bytes(data)
        with self.assertRaisesRegex(ValueError,'inode'):self.validate()

    def test_receipt_without_offline_dependency_check_rejected(self):
        import json
        runtime=read_json(self.result['runtime_environment']['path'])
        record=runtime['command_receipts'][4];value=read_json(record['path']);value['command'][2]='install'
        Path(record['path']).write_text(json.dumps(value));runtime['command_receipts'][4]=file_record(record['path'])
        Path(self.result['runtime_environment']['path']).write_text(json.dumps(runtime))
        self.result['runtime_environment']=file_record(self.result['runtime_environment']['path'])
        with self.assertRaisesRegex(ValueError,'command'):self.validate()

    def test_retained_failure_markers_prevent_result_acceptance(self):
        for marker in (self.output/'failure.json',self.output/'runtime/failure.json'):
            with self.subTest(marker=marker):
                marker.write_text('{"status":"failed"}')
                with self.assertRaisesRegex(ValueError,'failure'):self.validate()
                marker.unlink()
