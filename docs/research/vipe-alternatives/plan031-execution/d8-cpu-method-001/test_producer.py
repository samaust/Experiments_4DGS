"""Synthetic D8 finalization through the actual completed metric evidence seam."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0,str(ROOT/'scripts'))
from vipe_benchmark.files import file_record, read_json, write_json
from vipe_benchmark.depth_source_integrity import source_manifest
from vipe_benchmark.depth_review import _completed_qualification
spec=importlib.util.spec_from_file_location('d8_cpu_method',Path(__file__).with_name('producer.py'))
method=importlib.util.module_from_spec(spec)
spec.loader.exec_module(method)


class QualificationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        def artifact(name,data):
            path=self.root/name; path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(data); return file_record(path)
        self.helper=artifact('helper.py',b'fixture helper')
        self.archive=artifact('archive.tar.gz',b'fixture source archive')
        artifact('source/model.py',b'fixture native model')
        self.python=artifact('python',b'fixture prepared interpreter')
        self.asset=artifact('student_pointmap.pt',b'fixture checkpoint')
        self.inventory=artifact('inventory.json',b'{}')
        self.config=artifact('config.json',b'{}')
        self.dependency=artifact('dependency.so',b'fixture installed library')
        self.assets=[dict(repository='metricanything',path='student_pointmap.pt',record=self.asset)]
        self.setup=dict(source_dir=str(self.root/'source'),source_archive=self.archive,
                        source_manifest=source_manifest(self.root/'source'),assets=self.assets,
                        runtime=dict(python=self.python,python_executable=self.python['path']))
        self.save('setup.json',self.setup)
        self.files=method.source_files(self.setup,file_record,lambda r:r if file_record(r['path'])==r else (_ for _ in ()).throw(ValueError('changed')))
        self.save('dependencies.json',dict(candidate='D8',setup=file_record(self.root/'setup.json'),
                  source_revision='source-pin',files=[self.dependency]))
        self.dependencies=file_record(self.root/'dependencies.json')
        self.capture=self.root/'capture'; self.capture.mkdir()
        native=dict(status='passed',candidate='D8',strict_cpu_loads=2,inference=False,cuda_initialized=False,
                    local_sources=[self.helper],source_archive=self.archive,source_files=self.files,
                    setup=file_record(self.root/'setup.json'),setup_request=self.config,setup_dispatch=self.config,
                    assets=self.assets,python=self.python,
                    python_executable=self.python['path'],inventory=self.inventory,config=self.config,
                    dependency_manifest=self.dependencies,source_revision='source-pin',weights_revision='weight-pin',
                    profile=dict(mode='frozen-profile'))
        self.save('capture/native-cpu.json',native)
        self.save('capture/capture.json',dict(status='passed',cleanup_confirmed=True,
                  native_cpu=file_record(self.capture/'native-cpu.json')))
        permission=artifact('permission-report.md',b'fixture reviewed terms')
        self.save('assessment.json',dict(schema='plan069-depth-commercial-assessment/v1',candidate='D8',
                  source_revision='source-pin',weights_revision='weight-pin',dependency_manifest=self.dependencies,
                  code='allowed',weights='allowed',dependencies='allowed',inference_outputs='allowed',
                  primary_sources=['fixture-source','fixture-weights'],independent_review=dict(status='passed'),
                  permission_report=permission))
        self.save('source-review.json',dict(schema='plan069-depth-source-review/v1',candidate='D8',status='passed',
                  reviewer='independent fixture reviewer',source_revision='source-pin',local_sources=[self.helper],
                  source_archive=self.archive,source_files=self.files,profile_inventory=self.config))
        expected=dict(repository='metricanything',path='student_pointmap.pt',bytes=self.asset['bytes'],
                      lfs_sha256=self.asset['sha256'],git_oid=None)
        self.save('assets.json',dict(candidates={'D8':dict(files=[expected])}))
        self.proposal=dict(profile=dict(mode='frozen-profile'),profile_inventory=self.config,
                           required_assets=file_record(self.root/'assets.json'))
        self.args=SimpleNamespace(root=str(ROOT),capture=str(self.capture),candidate='D8',
                 commercial_assessment=str(self.root/'assessment.json'),source_review=str(self.root/'source-review.json'),
                 output=str(self.root/'final'))

    def tearDown(self): self.temp.cleanup()
    def save(self,name,value):
        path=self.root/name
        if path.exists(): path.unlink()
        write_json(path,value)

    def finalize(self):
        with patch.object(method,'install_guards'), \
             patch('vipe_benchmark.depth_admission.local_source_records',return_value=[self.helper]), \
             patch('vipe_benchmark.depth_authorization.execution_authorization',return_value=(None,None,self.proposal,None)):
            method.finalize(self.args)

    def completed(self):
        runtime=file_record(self.root/'final/runtime-qualification.json')
        qualification=file_record(self.root/'final/qualification.json')
        source=file_record(self.root/'source-review.json')
        commercial=file_record(self.root/'assessment.json')
        self.save('generation.json',dict(job_id='fixture-D8-maps',candidate='D8',context=self.config))
        generation=file_record(self.root/'generation.json')
        self.save('admission.json',dict(schema='plan069-depth-admission-result/v1',status='passed',candidate='D8',
                  qualification=qualification,source_review=source,runtime=dict(receipt=runtime),
                  commercial=dict(assessment=commercial)))
        self.save('request.json',dict(job_id='fixture-D8-maps',candidate='D8',context=self.config,
                  admission=file_record(self.root/'admission.json'),qualification=qualification,source_review=source))
        self.save('finish.json',dict(event='finish',status='complete',job_id='fixture-D8-maps',result=generation))
        slot=dict(provenance=dict(configuration=file_record(self.root/'request.json'),ledger_outcome=file_record(self.root/'finish.json')),
                  evidence=dict(generation=generation,runtime=runtime,commercial=commercial))
        return _completed_qualification('D8',slot,read_json(generation['path']),False)

    def test_finalized_receipts_pass_completed_metric_chain(self):
        self.finalize()
        result=self.completed()
        self.assertIsNotNone(result)
        self.assertEqual(result['source_archive'],self.archive)
        self.assertEqual(result['source_files'],self.files)
        self.assertTrue(all(Path(row['path']).is_absolute() for row in self.files))
        for key,wrong in [('source_archive',None),('source_files',[])]:
            with self.subTest(key=key):
                doc=read_json(self.root/'final/qualification.json')
                original=doc[key];doc[key]=wrong
                self.save('final/qualification.json',doc)
                self.assertIsNone(self.completed())
                doc[key]=original;self.save('final/qualification.json',doc)

    def test_two_strict_cpu_loads_never_infer_or_select_cuda(self):
        calls=[]
        tensor=SimpleNamespace(device=SimpleNamespace(type='cpu'),numel=lambda:3)
        class Model:
            training=True
            def __init__(self,**config): calls.append(('construct',config))
            def load_state_dict(self,state,*,strict):
                calls.append(('load',strict,state));self.assert_strict=strict
                if not strict or state!={'weight':1}: raise ValueError('bad strict state')
            def to(self,device):
                if device!='cpu': raise ValueError('selected CUDA')
                return self
            def eval(self): self.training=False;return self
            def parameters(self): return [tensor]
            def buffers(self): return []
            def infer(self,*a,**k): raise AssertionError('inference forbidden')
        def load(path,**kwargs):
            self.assertEqual(kwargs,dict(map_location='cpu',weights_only=True))
            return dict(model_config=dict(width=1),model={'weight':1})
        torch=SimpleNamespace(cuda=SimpleNamespace(is_initialized=lambda:False),load=load)
        self.assertEqual(len(method.strict_cpu_loads(self.setup,torch,Model)),2)
        self.assertEqual(len(calls),4)
        with self.assertRaises(PermissionError): torch.cuda._lazy_init()

    def test_old_presetup_review_cannot_finalize(self):
        doc=read_json(self.root/'source-review.json');doc.pop('source_files')
        self.save('source-review.json',doc)
        with self.assertRaisesRegex(ValueError,'fresh postsetup source review'):
            self.finalize()
        self.assertFalse(Path(self.args.output).exists())

    def test_changed_source_or_dependency_cannot_finalize(self):
        (self.root/'source/model.py').write_bytes(b'changed')
        with self.assertRaises(ValueError): self.finalize()
        self.assertFalse(Path(self.args.output).exists())
        (self.root/'source/model.py').write_bytes(b'fixture native model')
        (self.root/'dependency.so').write_bytes(b'changed')
        with self.assertRaises(ValueError): self.finalize()
        self.assertFalse(Path(self.args.output).exists())


if __name__=='__main__': unittest.main()
