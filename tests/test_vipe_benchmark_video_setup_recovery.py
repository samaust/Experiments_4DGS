"""CPU fixture recovery creates a fresh environment without acquiring assets."""
from pathlib import Path
import tempfile
import unittest
from vipe_benchmark.files import file_record,read_json,write_json


class VideoRecoveryTests(unittest.TestCase):
    recovery_job='plan069-D9-setup-recovery-001'
    recovery_version='v1'
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
        from vipe_benchmark.video_environment import FRAME_RECIPE, environment_request, bind_source_environment
        recipe=read_json(FRAME_RECIPE)
        for relative in [recipe['source_requirement'],*recipe['fallback_sources']]:
            path=self.source/relative;path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text('\n'.join(recipe['upstream_requirements'])+'\n' if relative==recipe['source_requirement'] else '# CPU fixture source only\n')
        tools={}
        for name in ('ffmpeg','ffprobe'):
            path=self.root/name;path.write_bytes(b'CPU fixture media tool');tools[name]=str(path)
        runtime=environment_request('D9',self.root,seed_executable=str(self.seed),uv_executable=str(self.uv),
            record_kind='fixture',media_tools=tools,recipe_path=FRAME_RECIPE)
        runtime=bind_source_environment(runtime,self.source,recipe['source_revision'],candidate='D9',record_kind='fixture')
        self.request=dict(schema='plan069-video-setup-recovery-request/'+self.recovery_version,record_kind='fixture',candidate='D9',
            job_id=self.recovery_job,original_setup=dict(source_archive=file_record(self.old/'source.tar.gz'),
            source_files=[file_record(path) for path in sorted(self.source.rglob('*')) if path.is_file()],checkpoint=file_record(self.old/'video_depth_anything_vits.pth')),
            runtime_environment=runtime,
            fixture_allocation=dict(setup_seconds=120,download_bytes=0,artifact_bytes=10**7))
        self.output=self.root/'jobs'/self.recovery_job;self.commands=[]
        if self.recovery_version=='v2':
            self.request['failed_recoveries']=[dict(job_id='plan069-D9-setup-recovery-001',fixture_ancestor=True)]

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
        self.assertEqual(result['job_id'],self.recovery_job)
        self.assertEqual(result['bytes_received'],0)
        self.assertEqual(result['runtime_profile'],self.request['runtime_environment']['runtime_profile'])
        self.assertIsInstance(result['runtime_profile'],dict)
        self.assertEqual(read_json(result['runtime_environment']['path'])['runtime_profile'],result['runtime_profile'])
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

    def test_offline_cache_expansion_uses_remaining_bytes_without_network_acquisition(self):
        from vipe_benchmark.video_setup_recovery import run_video_setup_recovery
        self.request['fixture_allocation']['download_bytes']=1000
        def expanded(command,**kwargs):
            self.runner(command,**kwargs)
            if 'compile' in command:
                cache=self.root/'setup-cache/resolver-metadata';cache.parent.mkdir()
                cache.write_bytes(b'x'*100)
        result=run_video_setup_recovery(self.request,self.output,environment_runner=expanded)
        self.assertEqual(result['bytes_received'],0)
        self.assertEqual(result['status'],'complete')

    def test_direct_acquisition_is_rejected_even_within_remaining_byte_cap(self):
        from vipe_benchmark.video_setup_recovery import run_video_setup_recovery
        self.request['fixture_allocation']['download_bytes']=1000
        def acquired(command,**kwargs):
            self.runner(command,**kwargs)
            if 'compile' in command:
                path=self.root/'transfers/transfer-fixture.json';path.parent.mkdir()
                write_json(path,dict(transfer_id='fixture',bytes_received=1,error=None))
        with self.assertRaisesRegex(ValueError,'acquired new downloads'):
            run_video_setup_recovery(self.request,self.output,environment_runner=acquired)
        self.assertFalse((self.output/'result.json').exists())

    def test_failed_dependency_check_is_retained_without_rewriting_original(self):
        from vipe_benchmark.video_setup_recovery import run_video_setup_recovery
        before={p:p.read_bytes() for p in self.old.rglob('*') if p.is_file()}
        def fail(command,**kwargs):
            self.runner(command,**kwargs)
            if 'check' in command:raise RuntimeError('fixture dependency conflict')
        with self.assertRaisesRegex(RuntimeError,'dependency conflict'):
            run_video_setup_recovery(self.request,self.output,environment_runner=fail)
        self.assertTrue((self.output/'failure.json').exists())
        failure=read_json(self.output/'failure.json')
        self.assertEqual(failure['schema'],'plan069-video-setup-recovery-failure/'+self.recovery_version)
        self.assertEqual(failure['job_id'],self.recovery_job)
        if self.recovery_version=='v2':
            self.assertEqual(failure['failed_recoveries'],self.request['failed_recoveries'])
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

    def test_full_recipe_profile_is_required_before_any_fixture_command(self):
        from vipe_benchmark.video_setup_recovery import run_video_setup_recovery
        original=self.request['runtime_environment']['runtime_profile']
        for changed in (original['id'],dict(original,distribution='modified runtime')):
            with self.subTest(profile=changed):
                self.request['runtime_environment']['runtime_profile']=changed
                # Each immutable failed fixture needs its own isolated output.
                with tempfile.TemporaryDirectory() as scratch:
                    output=Path(scratch)/'jobs/plan069-D9-setup-recovery-001'
                    # The profile rejection occurs before output/runtime creation
                    # at _environment; test that deep boundary directly.
                    from vipe_benchmark.video_setup_recovery import _environment
                    with self.assertRaisesRegex(ValueError,'profile dictionary'):
                        _environment(self.request['runtime_environment'],output,dict(run_root=str(self.root),record_kind='fixture'),
                            __import__('time').monotonic()+30,lambda:None,self.runner)
                self.assertEqual(self.commands,[])
                self.request['runtime_environment']['runtime_profile']=original


class RecoveryAcceptanceTests(unittest.TestCase):
    runner=VideoRecoveryTests.runner
    recovery_job=VideoRecoveryTests.recovery_job
    recovery_version=VideoRecoveryTests.recovery_version

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
        value=self.validate()
        self.assertEqual(value['status'],'complete')
        self.assertEqual(value['runtime_profile'],self.request['runtime_environment']['runtime_profile'])

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

    def test_runtime_profile_string_or_modified_dictionary_is_rejected(self):
        from copy import deepcopy
        from vipe_benchmark.video_setup_recovery import validate_recovery_result
        from unittest.mock import patch
        original=self.result['runtime_profile']
        for changed in (original['id'],dict(original,distribution='modified runtime')):
            with self.subTest(profile=changed):
                self.result['runtime_profile']=changed
                runtime=read_json(self.result['runtime_environment']['path'])
                runtime['runtime_profile']=changed
                Path(self.result['runtime_environment']['path']).write_text(__import__('json').dumps(runtime))
                self.result['runtime_environment']=file_record(self.result['runtime_environment']['path'])
                with patch('vipe_benchmark.depth_setup_recovery.validate_recovery_request',return_value=self.binding):
                    with self.assertRaisesRegex(ValueError,'runtime binding changed'):
                        validate_recovery_result(self.save_result(),self.request_record,[],self.root)
                self.result['runtime_profile']=deepcopy(original)


class RepairRecoveryTests(VideoRecoveryTests):
    recovery_job='plan069-D9-setup-recovery-002'
    recovery_version='v2'

    def test_repair_result_retains_exact_consumed_ancestor(self):
        from vipe_benchmark.video_setup_recovery import run_video_setup_recovery
        result=run_video_setup_recovery(self.request,self.output,environment_runner=self.runner)
        self.assertEqual(result['schema'],'plan069-video-setup-recovery-result/v2')
        self.assertEqual(result['failed_recoveries'],self.request['failed_recoveries'])

    def test_job_schema_and_ancestor_mismatches_rejected_before_commands(self):
        from vipe_benchmark.video_setup_recovery import run_video_setup_recovery
        for changes in ({'schema':'plan069-video-setup-recovery-request/v1'},
                        {'job_id':'plan069-D9-setup-recovery-003'},
                        {'failed_recoveries':[]},
                        {'failed_recoveries':[{'job_id':'plan069-D9-setup-recovery-002'}]}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                run_video_setup_recovery(dict(self.request,**changes),self.output,environment_runner=self.runner)
            self.assertFalse(self.output.exists())
            self.assertEqual(self.commands,[])


class RepairAcceptanceTests(RecoveryAcceptanceTests):
    recovery_job='plan069-D9-setup-recovery-002'
    recovery_version='v2'

    def test_repair_result_ancestry_cannot_be_omitted_or_changed(self):
        self.validate()
        original=self.result.pop('failed_recoveries')
        with self.assertRaisesRegex(ValueError,'ancestry'):self.validate()
        self.result['failed_recoveries']=[dict(job_id='other')]
        with self.assertRaisesRegex(ValueError,'ancestry'):self.validate()
        self.result['failed_recoveries']=original
