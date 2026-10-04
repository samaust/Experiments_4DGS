"""CPU fakes exercise version003 acceptance context and exact two-load contract."""
import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch
from vipe_benchmark.config import ROOT
from vipe_benchmark.files import file_record,read_json,write_json

PATH=ROOT/'docs/research/vipe-alternatives/plan031-execution/video-cpu-method-003/producer.py'
spec=importlib.util.spec_from_file_location('video_method003',PATH)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class VideoCpuMethod003Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.job=self.root/'jobs/recovery';(self.job/'runtime').mkdir(parents=True)
        self.source=self.root/'jobs/failed/source';self.source.mkdir(parents=True)
        for name in ('review.json','approval.json','recipe.json'):write_json(self.root/name,{})
        self.review=file_record(self.root/'review.json');self.authorization=file_record(self.root/'approval.json')
        self.recipe=dict(recipe=file_record(self.root/'recipe.json'),fixture_only=True)
        self.runtime=self.job/'runtime/result.json';write_json(self.runtime,dict(status='complete',candidate='D9'))
        self.runtime_request=self.job/'runtime/request.json';write_json(self.runtime_request,self.recipe)
        self.request=self.root/'requests/recovery.json'
        write_json(self.request,dict(schema='plan069-video-setup-recovery-request/v1',candidate='D9',record_kind='actual',
            job_id='plan069-D9-setup-recovery-001',review=self.review,authorization=self.authorization,
            ledger_path=str(self.root/'ledger.jsonl'),runtime_environment=self.recipe))
        self.setup=dict(schema='plan069-video-setup-recovery-result/v1',job_id='plan069-D9-setup-recovery-001',candidate='D9',status='complete',record_kind='actual',
            source_dir=str(self.source),review=self.review,authorization=self.authorization,source_revision='source',weight_revision='weight',
            runtime_environment=file_record(self.runtime))
        self.setup_path=self.job/'result.json';write_json(self.setup_path,self.setup)
        self.args=SimpleNamespace(root=str(ROOT),candidate='D9',setup=str(self.setup_path),setup_request=str(self.request),
            setup_dispatch=None,ledger=str(self.root/'ledger.jsonl'),authorization=str(self.root/'approval.json'))
        self.events=[dict(sequence=5,event_sha256='prefix')]
        self.ledger=SimpleNamespace(path=self.root/'ledger.jsonl',events=lambda:self.events)
        self.accepted=dict(accepted_result=self.setup,request=file_record(self.request),
            grant={'event_sha256':'grant'},reserve={'event_sha256':'reserve'},finish={'event_sha256':'finish'})
        self.proposal=dict(candidate_config=dict(code={'revision':'source'},weights={'revision':'weight'}))

    def context(self,*,failure=None):
        accepted=Mock(return_value=self.accepted,side_effect=failure)
        with patch('vipe_benchmark.ledger.Ledger',return_value=self.ledger), \
                patch('vipe_benchmark.depth_recovery_lineage.accepted_setup_lineage',accepted), \
                patch('vipe_benchmark.depth_authorization.execution_authorization',return_value=(self.review,self.authorization,self.proposal,{})), \
                patch('vipe_benchmark.video_environment.bind_source_environment',side_effect=lambda recipe,*args,**kw:recipe):
            result=module.setup_context(self.args)
        if self.setup['schema'] in ('plan069-video-setup-recovery-result/v1','plan069-video-setup-recovery-result/v2'):
            accepted.assert_called_once_with(file_record(self.setup_path),self.events,self.root)
        return result

    def test_recovered_setup_uses_protected_request_and_raw_runtime_recipe(self):
        result=self.context()
        self.assertIs(result['ledger'],self.ledger)
        self.assertEqual(result['dispatch_record'],None)
        self.assertEqual(result['setup']['source_dir'],str(self.source))
        self.assertEqual(result['recovery_lineage']['finish_event_sha256'],'finish')

    def test_recovery_requires_ledger_and_forbids_original_dispatch_shortcut(self):
        self.args.ledger=None
        with self.assertRaisesRegex(ValueError,'ledger'):self.context()
        self.args.ledger=str(self.root/'ledger.jsonl');self.args.setup_dispatch='old-dispatch'
        with self.assertRaisesRegex(ValueError,'ledger'):self.context()

    def test_active_or_unaccepted_lineage_cannot_qualify(self):
        with self.assertRaisesRegex(ValueError,'active attempt'):self.context(failure=ValueError('active attempt'))

    def test_wrong_protected_request_or_augmented_runtime_recipe_rejected(self):
        self.accepted['request']={'wrong':True}
        with self.assertRaisesRegex(ValueError,'protected request'):self.context()
        self.accepted['request']=file_record(self.request)
        self.runtime_request.unlink();write_json(self.runtime_request,dict(self.recipe,setup_request=file_record(self.request)))
        with self.assertRaisesRegex(ValueError,'raw reviewed environment'):self.context()

    def test_ordinary_d10_keeps_dispatch_and_setup_request_runtime_binding(self):
        import json
        self.args.candidate='D10';self.args.ledger=None
        self.source=self.job/'source';self.source.mkdir()
        self.setup.update(schema='plan069-video-setup-result/v1',candidate='D10',source_dir=str(self.source))
        self.setup_path.write_text(json.dumps(self.setup))
        request=read_json(self.request);request.update(schema='plan069-depth-setup-request/v1',candidate='D10',job_id='plan069-D10-setup-001')
        self.request.write_text(json.dumps(request))
        self.runtime_request.write_text(json.dumps(dict(self.recipe,setup_request=file_record(self.request))))
        dispatch=self.root/'dispatch.json';write_json(dispatch,dict(schema='plan069-video-setup-dispatch/v1',status='complete',result=file_record(self.setup_path)))
        self.args.setup_dispatch=str(dispatch)
        self.assertEqual(self.context()['dispatch_record'],file_record(dispatch))
        self.args.setup_dispatch=None
        with self.assertRaisesRegex(ValueError,'ordinary setup dispatch'):self.context()

    def test_two_strict_cpu_loads_forward_exact_accepted_ledger(self):
        model=Mock();model.parameters.return_value=[SimpleNamespace(device=SimpleNamespace(type='cpu'))]
        model.buffers.return_value=[];torch=SimpleNamespace(cuda=SimpleNamespace(is_initialized=lambda:False))
        record={'fixture_setup':True}
        with patch('vipe_benchmark.video_native.load_native_video',return_value=model) as loader:
            module.strict_cpu_loads('D9',record,self.ledger,torch)
        self.assertEqual(loader.call_count,2)
        for call in loader.call_args_list:self.assertEqual(call.kwargs,dict(device='cpu',ledger=self.ledger))
        model.parameters.return_value=[SimpleNamespace(device=SimpleNamespace(type='cuda'))]
        with patch('vipe_benchmark.video_native.load_native_video',return_value=model):
            with self.assertRaisesRegex(ValueError,'escaped CPU'):module.strict_cpu_loads('D9',record,self.ledger,torch)


class VideoCpuRepair002Tests(VideoCpuMethod003Tests):
    def setUp(self):
        super().setUp()
        import json
        self.setup.update(schema='plan069-video-setup-recovery-result/v2',job_id='plan069-D9-setup-recovery-002')
        self.setup_path.write_text(json.dumps(self.setup))
        request=read_json(self.request)
        request.update(schema='plan069-video-setup-recovery-request/v2',job_id='plan069-D9-setup-recovery-002')
        self.request.write_text(json.dumps(request));self.accepted['request']=file_record(self.request)

    def test_wrong_job_schema_pair_cannot_qualify(self):
        import json
        self.setup['job_id']='plan069-D9-setup-recovery-003'
        self.setup_path.write_text(json.dumps(self.setup))
        with self.assertRaisesRegex(ValueError,'actual complete'):self.context()
