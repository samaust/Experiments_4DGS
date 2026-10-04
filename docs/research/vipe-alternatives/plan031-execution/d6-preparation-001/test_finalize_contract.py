import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('finalwrapper002',Path(__file__).parent/'finalize_wrapper.py')
wrapper=importlib.util.module_from_spec(spec);spec.loader.exec_module(wrapper)
EXPECTED='cfd509169b491162d74685792dcab28afa7e126230080f58e013f2dd13a6909e'


class SeparateMethodBindingsTests(unittest.TestCase):
    def config(self,root):
        def save(name,value):
            p=root/(name+'.json');p.write_text(json.dumps(value));return wrapper.record(p)
        finalize_method=save('method003',{'fixture':'finalize only; not executed'})
        capture_method=save('method002',{'fixture':'successful historical capture; not executed'})
        recipe=save('recipe',{'fixture':'original recipe'})
        dependencies=save('dependencies',{'fixture':'manifest'})
        report=save('permission-report',{'fixture':'report'})
        archive=save('source-archive',{'fixture':'archive not parsed'})
        tree=[dict(relative_path='native.py',record=save('source-file',{'fixture':'source'}))]
        setup=dict(save('setup',dict(source_archive=archive,source_tree=tree)),sha256=EXPECTED)
        native=save('native-cpu',dict(schema='plan069-moge-native-cpu-qualification/v1',candidate='D6',status='passed',strict_cpu_loads=2,inference=False,cuda_initialized=False,
            dependency_manifest=dependencies,setup=setup,source_revision='source',weights_revision='weights',local_sources=[]))
        capture=save('capture',dict(schema='plan069-moge-cpu-capture/v1',candidate='D6',status='passed',cleanup_confirmed=True,native_cpu=native,method=capture_method))
        assessment=save('assessment',dict(schema='plan069-depth-commercial-assessment/v1',candidate='D6',dependency_manifest=dependencies,permission_report=report,source_revision='source',weights_revision='weights',
            code='allowed',weights='allowed',dependencies='allowed',inference_outputs='allowed',primary_sources=['primary1','primary2'],independent_review={'status':'passed'}))
        review=save('review',dict(schema='plan069-depth-source-review/v1',candidate='D6',status='passed',root_source_commit='b8e63680',local_sources=[],runtime_recipe=recipe,source_archive=archive,source_files=tree))
        config=dict(accepted_setup_sha256=EXPECTED,root_source_commit='b8e63680',method=finalize_method,bindings=dict(capture=capture,native_cpu=native,dependency_manifest=dependencies,commercial_assessment=assessment,permission_report=report,runtime_recipe=recipe,source_review=review,capture_method=capture_method))
        original=wrapper.record
        def record(path):return setup if str(path)==setup['path'] else original(path)
        return config,record

    def validate(self,config,record):
        with patch.object(wrapper,'record',side_effect=record):return wrapper.validate_finalize_inputs(config)

    def mutate(self,config,role,key,value):
        p=Path(config['bindings'][role]['path']);d=json.loads(p.read_text());d[key]=value;p.write_text(json.dumps(d));config['bindings'][role]=wrapper.record(p)

    def test_distinct_capture002_and_finalize003_methods_pass(self):
        with tempfile.TemporaryDirectory() as temporary:
            config,record=self.config(Path(temporary));self.assertNotEqual(config['method'],config['bindings']['capture_method']);self.validate(config,record)

    def test_self_consistent_substitute_capture_method_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            config,record=self.config(Path(temporary));config['bindings']['capture_method']=config['method']
            with self.assertRaisesRegex(ValueError,'retained method'):self.validate(config,record)

    def test_capture_method_role_missing_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            config,record=self.config(Path(temporary));config['bindings'].pop('capture_method')
            with self.assertRaisesRegex(ValueError,'binding role'):self.validate(config,record)

    def test_postsetup_archive_substitution_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            config,record=self.config(Path(temporary));self.mutate(config,'source_review','source_archive',{})
            with self.assertRaisesRegex(ValueError,'accepted archive/tree'):self.validate(config,record)

    def test_postsetup_tree_omission_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            config,record=self.config(Path(temporary));self.mutate(config,'source_review','source_files',[])
            with self.assertRaisesRegex(ValueError,'accepted archive/tree'):self.validate(config,record)

    def test_failed_capture_cannot_finalize(self):
        with tempfile.TemporaryDirectory() as temporary:
            config,record=self.config(Path(temporary));self.mutate(config,'capture','status','failed')
            with self.assertRaisesRegex(ValueError,'passed capture'):self.validate(config,record)


class WrapperAdmissionTests(unittest.TestCase):
    def test_d5_request_cannot_start_d6_capture(self):
        spec = importlib.util.spec_from_file_location('capturewrapper', Path(__file__).parent / 'capture_wrapper.py')
        capture = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(capture)
        with tempfile.TemporaryDirectory() as temporary:
            p = Path(temporary)
            request = p / 'request.json'
            request.write_text(json.dumps(dict(schema='plan069-moge-parent-cpu-request/v1', candidate='D5', output=str(p/'out'))))
            with self.assertRaisesRegex(ValueError, 'D6 only'):
                capture.run(request)
            self.assertFalse((p/'out').exists())

    def test_d5_native_capture_cannot_finalize_d6(self):
        with tempfile.TemporaryDirectory() as temporary:
            config,record=SeparateMethodBindingsTests().config(Path(temporary))
            SeparateMethodBindingsTests().mutate(config,'native_cpu','candidate','D5')
            SeparateMethodBindingsTests().mutate(config,'capture','native_cpu',config['bindings']['native_cpu'])
            with patch.object(wrapper,'record',side_effect=record):
                with self.assertRaisesRegex(ValueError,'setup/native evidence'):
                    wrapper.validate_finalize_inputs(config)

    def test_unreviewed_setup_substitution_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            config,record=SeparateMethodBindingsTests().config(Path(temporary))
            config['accepted_setup_sha256']='not-the-admitted-setup'
            with patch.object(wrapper,'record',side_effect=record):
                with self.assertRaisesRegex(ValueError,'setup/native evidence'):
                    wrapper.validate_finalize_inputs(config)


class FullD6FinalizationTests(unittest.TestCase):
    def test_d6_worker_result_is_accepted_with_cleanup(self):
        import sys
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            helper=SeparateMethodBindingsTests()
            config,record=helper.config(root)
            native=json.loads(Path(config['bindings']['native_cpu']['path']).read_text())
            review=json.loads(Path(config['bindings']['source_review']['path']).read_text())
            runtime=dict(schema='plan069-depth-runtime-qualification/v1',candidate='D6',record_kind='actual',status='passed',
                setup=native['setup'],native_cpu=config['bindings']['native_cpu'],capture=config['bindings']['capture'],
                source_review=config['bindings']['source_review'],local_sources=native['local_sources'],
                source_archive=review['source_archive'],source_files=review['source_files'],
                dependency_manifest=config['bindings']['dependency_manifest'],gpu_model_load='not_performed')
            qualified=dict(schema='plan069-depth-D6-qualification/v1',candidate='D6',record_kind='actual',status='passed',
                setup=native['setup'],source_review=config['bindings']['source_review'],source_archive=review['source_archive'],
                source_files=review['source_files'],commercial={'assessment':config['bindings']['commercial_assessment']})
            method=root/'fixture-producer.py'
            method.write_text('import pathlib,json,sys,hashlib\n' +
                "out=pathlib.Path(sys.argv[sys.argv.index('--output')+1]);out.mkdir()\n" +
                'runtime='+repr(runtime)+'\nqualified='+repr(qualified)+'\n' +
                "p=out/'runtime-qualification.json';p.write_text(json.dumps(runtime))\n" +
                "qualified['runtime']={'receipt':dict(path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())}\n" +
                "(out/'qualification.json').write_text(json.dumps(qualified))\n")
            config.update(schema='plan069-moge-parent-finalize-request/v2',candidate='D6',bootstrap=wrapper.record(Path(sys.executable).resolve()),
                interpreter_invocation=sys.executable,seconds=10,cleanup_seconds=5,cpu_workers=7,admitted=True,charge_owner='root',
                method=wrapper.record(method),root=str(root),output=str(root/'wrapper'),
                command=[sys.executable,'-B',str(method),'finalize','--root',str(root),'--candidate','D6',
                    '--capture',str(root),'--commercial-assessment',config['bindings']['commercial_assessment']['path'],
                    '--source-review',config['bindings']['source_review']['path'],'--output',str(root/'qualification')],
                disk_roots=[dict(role=role,path=str(root),maximum_total_bytes=100000000,maximum_delta_bytes=100000000)
                    for role in ('global','candidate','runtime-cache')])
            request=root/'request.json';request.write_text(json.dumps(config))
            with patch.object(wrapper,'record',side_effect=record):wrapper.run(request)
            result=json.loads((root/'wrapper/result.json').read_text())
            self.assertEqual(result['status'],'passed')
            self.assertTrue(result['cleanup_confirmed'])


if __name__=='__main__':unittest.main()
