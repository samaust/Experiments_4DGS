import argparse
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path('/home/auss/git_repos/samaust/Experiments_4DGS/.local/plan069-worktrees/depth-extension')
sys.path.insert(0,str(ROOT/'scripts'))
from vipe_benchmark.files import file_record, read_json, verify_record
from vipe_benchmark.depth_review import _completed_qualification
spec=importlib.util.spec_from_file_location('method003',Path(__file__).parent/'producer.py')
producer=importlib.util.module_from_spec(spec);spec.loader.exec_module(producer)


class FinalizeContractTests(unittest.TestCase):
    def fixture(self,root):
        def save(name,value):
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text(json.dumps(value));return file_record(p)
        archive=save('archive',{'synthetic':'source archive'})
        source=save('source/native.py',{'synthetic':'source file'})
        tree=[dict(relative_path='native.py',record=source)]
        config=save('config',{'synthetic':'config'})
        python=save('python',{'synthetic':'interpreter'})
        localsources=[save('helper.py',{'synthetic':'current helper'})]
        recipe=save('recipe',{'synthetic':'original recipe'})
        request=save('setup-request',dict(runtime_environment_record=recipe))
        checkpoint=save('model.pt',{'synthetic':'not a model'})
        setup=save('setup',dict(source_dir=str(root/'source'),source_tree=tree,source_archive=archive,checkpoint=checkpoint))
        runtime=save('runtime',dict(python=python,python_executable=str(root/'python')))
        manifest=save('manifest',dict(files=[source]))
        inventory=save('installed-inventory',{'synthetic':'inventory'})
        native=save('capture/native-cpu.json',dict(status='passed',candidate='D5',strict_cpu_loads=2,inference=False,cuda_initialized=False,
            local_sources=localsources,setup=setup,runtime_environment=runtime,python=python,python_executable=str(root/'python'),inventory=inventory,config=config,
            dependency_manifest=manifest,source_revision='sourcepin',weights_revision='weightpin',setup_request=request,profile={'synthetic':'profile'}))
        captured=save('capture/capture.json',dict(status='passed',cleanup_confirmed=True,native_cpu=native))
        report=save('permission-report',{'synthetic':'review'})
        assessment=save('assessment',dict(schema='plan069-depth-commercial-assessment/v1',candidate='D5',source_revision='sourcepin',weights_revision='weightpin',
            dependency_manifest=manifest,code='allowed',weights='allowed',dependencies='allowed',inference_outputs='allowed',primary_sources=['primary1','primary2'],independent_review={'status':'passed'},permission_report=report))
        review=save('source-review',dict(schema='plan069-depth-source-review/v1',candidate='D5',status='passed',source_revision='sourcepin',runtime_recipe=recipe,local_sources=localsources,source_archive=archive,source_files=tree))
        asset_inventory=save('asset-inventory',dict(candidates={'D5':dict(files=[dict(path='model.pt',bytes=checkpoint['bytes'],lfs_sha256=checkpoint['sha256'],repository='fixture')])}))
        args=argparse.Namespace(root=str(ROOT),candidate='D5',capture=str(root/'capture'),commercial_assessment=assessment['path'],source_review=review['path'],output=str(root/'qualification'))
        return dict(args=args,archive=archive,tree=tree,review=review,localsources=localsources,asset_inventory=asset_inventory,assessment=assessment,save=save)

    def finalize(self,fixture):
        with patch.object(producer,'helpers',return_value=(file_record,read_json,verify_record)), \
             patch('vipe_benchmark.depth_admission.local_source_records',return_value=fixture['localsources']), \
             patch('vipe_benchmark.depth_authorization.execution_authorization',return_value=(None,None,dict(profile={'synthetic':'profile'}),None)), \
             patch('vipe_benchmark.moge_setup.source_tree_records',return_value=fixture['tree']), \
             patch('vipe_benchmark.depth_admission.INVENTORY',fixture['asset_inventory']['path']):
            producer.finalize(fixture['args'])

    def completed(self,fixture):
        save=fixture['save'];out=Path(fixture['args'].output)
        qualification=file_record(out/'qualification.json');doc=read_json(qualification['path'])
        generation=dict(job_id='synthetic-job',context={'synthetic':'context'})
        generation_record=save('generation',generation)
        admission=save('admission',dict(schema='plan069-depth-admission-result/v1',candidate='D5',status='passed',qualification=qualification,source_review=fixture['review'],runtime=doc['runtime'],commercial=doc['commercial']))
        request=save('map-request',dict(job_id='synthetic-job',candidate='D5',context=generation['context'],admission=admission,qualification=qualification,source_review=fixture['review']))
        finish=save('finish',dict(event='finish',status='complete',result=generation_record,job_id='synthetic-job'))
        slot=dict(provenance=dict(configuration=request,ledger_outcome=finish),evidence=dict(generation=generation_record,runtime=doc['runtime']['receipt'],commercial=fixture['assessment']))
        return _completed_qualification('D5',slot,generation,False)

    def test_finalizer_outputs_satisfy_real_completed_qualification_contract(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture=self.fixture(Path(temporary));self.finalize(fixture)
            proof=self.completed(fixture)
            self.assertIsNotNone(proof);self.assertEqual(proof['source_archive'],fixture['archive']);self.assertEqual(proof['source_files'],fixture['tree'])

    def test_wrong_review_archive_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture=self.fixture(Path(temporary));p=Path(fixture['review']['path']);doc=read_json(p);doc['source_archive']={};p.write_text(json.dumps(doc))
            with self.assertRaisesRegex(ValueError,'post-setup source review'):self.finalize(fixture)
            self.assertFalse(Path(fixture['args'].output).exists())

    def test_missing_review_source_files_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture=self.fixture(Path(temporary));p=Path(fixture['review']['path']);doc=read_json(p);doc.pop('source_files');p.write_text(json.dumps(doc))
            with self.assertRaisesRegex(ValueError,'post-setup source review'):self.finalize(fixture)
            self.assertFalse(Path(fixture['args'].output).exists())

    def test_changed_tree_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture=self.fixture(Path(temporary));fixture['tree']=[]
            with self.assertRaisesRegex(ValueError,'extracted native source'):self.finalize(fixture)
            self.assertFalse(Path(fixture['args'].output).exists())

    def test_completed_contract_rejects_missing_top_source_fields(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture=self.fixture(Path(temporary));self.finalize(fixture);p=Path(fixture['args'].output)/'qualification.json';doc=read_json(p);doc.pop('source_files');p.write_text(json.dumps(doc))
            self.assertIsNone(self.completed(fixture))

    def test_completed_contract_rejects_missing_runtime_source_fields(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture=self.fixture(Path(temporary));self.finalize(fixture);p=Path(fixture['args'].output)/'runtime-qualification.json';doc=read_json(p);doc.pop('source_archive');p.write_text(json.dumps(doc))
            q=Path(fixture['args'].output)/'qualification.json';qual=read_json(q);qual['runtime']['receipt']=file_record(p);q.write_text(json.dumps(qual))
            self.assertIsNone(self.completed(fixture))


if __name__=='__main__':unittest.main()
