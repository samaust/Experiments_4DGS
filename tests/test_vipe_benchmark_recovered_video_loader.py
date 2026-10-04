"""Recovery native loader admission uses real lineage before fake CPU models."""
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch
from vipe_benchmark.files import file_record,write_json


class RecoveredVideoLoaderTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.source=self.root/'source';self.source.mkdir()
        self.checkpoint=self.root/'weights.pth';self.checkpoint.write_bytes(b'fixture only')
        self.setup=dict(schema='plan069-video-setup-recovery-result/v1',status='complete',candidate='D9',
            record_kind='actual',source_dir=str(self.source),source_files=[],checkpoint=file_record(self.checkpoint))
        self.path=self.root/'result.json';self.save()
        self.events=[{'fixture_event':True}];self.ledger=SimpleNamespace(path=self.root/'ledger.jsonl',events=lambda:self.events)
        self.model=Mock();self.model.to.return_value=self.model;self.model.eval.return_value=self.model
        self.native=SimpleNamespace(__file__=str(self.source/'video_depth_anything/video_depth.py'),VideoDepthAnything=Mock(return_value=self.model))
        self.util=SimpleNamespace(__file__=str(self.source/'utils/util.py'))
        self.modules={'torch':SimpleNamespace(load=Mock(return_value={'fixture':'state'}))}

    def save(self):
        if self.path.exists():self.path.unlink()
        write_json(self.path,self.setup)
        return file_record(self.path)

    def load(self,**options):
        from vipe_benchmark.video_native import load_native_video
        original=list(sys.path)
        try:
            with patch.dict(sys.modules,self.modules),patch('vipe_benchmark.video_native.setup_environment'), \
                    patch('vipe_benchmark.video_native.native_source_records',return_value=[]), \
                    patch('vipe_benchmark.video_native.installed_dependency_versions',return_value={'xformers':None}), \
                    patch('vipe_benchmark.video_native.importlib.import_module',side_effect=[self.native,self.util]):
                return load_native_video('D9',file_record(self.path),device='cpu',**options)
        finally:sys.path[:]=original

    def test_recovery_requires_explicit_ledger_before_imports(self):
        with self.assertRaisesRegex(ValueError,'ledger'):self.load()
        self.native.VideoDepthAnything.assert_not_called()

    def test_completed_accepted_lineage_is_required_before_model_construction(self):
        with patch('vipe_benchmark.depth_recovery_lineage.accepted_setup_lineage',return_value={'accepted_result':self.setup}) as accepted:
            self.assertIs(self.load(ledger=self.ledger),self.model)
        accepted.assert_called_once_with(file_record(self.path),self.events,self.root)
        self.model.load_state_dict.assert_called_once_with({'fixture':'state'},strict=True)

    def test_repair_v2_requires_checked_lineage_before_cpu_model_construction(self):
        self.setup['schema'] = 'plan069-video-setup-recovery-result/v2'; self.save()
        with patch('vipe_benchmark.depth_recovery_lineage.accepted_setup_lineage',return_value={'accepted_result':self.setup}) as accepted:
            self.assertIs(self.load(ledger=self.ledger),self.model)
        accepted.assert_called_once_with(file_record(self.path),self.events,self.root)

    def test_checked_active_map_admission_is_explicitly_forwarded(self):
        admission={'fixture_checked_map':True}
        with patch('vipe_benchmark.depth_recovery_lineage.accepted_setup_lineage',return_value={'accepted_result':self.setup}) as accepted:
            self.load(ledger=self.ledger,active_map_admission=admission)
        accepted.assert_called_once_with(file_record(self.path),self.events,self.root,active_map_admission=admission)

    def test_failed_or_foreign_active_lineage_never_constructs_model(self):
        with patch('vipe_benchmark.depth_recovery_lineage.accepted_setup_lineage',side_effect=ValueError('foreign active attempt')):
            with self.assertRaisesRegex(ValueError,'foreign'):self.load(ledger=self.ledger)
        self.native.VideoDepthAnything.assert_not_called()

    def test_recovery_does_not_extend_d10_or_fixture_acceptance(self):
        from vipe_benchmark.video_native import load_native_video
        for changes in ({'candidate':'D10'},{'record_kind':'fixture'},{'status':'failed'}):
            with self.subTest(changes=changes):
                prior=dict(self.setup);self.setup.update(changes);record=self.save()
                with patch('vipe_benchmark.depth_recovery_lineage.accepted_setup_lineage') as accepted:
                    with self.assertRaises(ValueError):load_native_video(self.setup['candidate'],record,device='cpu',ledger=self.ledger)
                    accepted.assert_not_called()
                self.setup=prior

    def test_lineage_must_describe_the_exact_bound_setup(self):
        with patch('vipe_benchmark.depth_recovery_lineage.accepted_setup_lineage',return_value={'accepted_result':dict(self.setup,candidate='D10')}):
            with self.assertRaisesRegex(ValueError,'lineage'):self.load(ledger=self.ledger)
        self.native.VideoDepthAnything.assert_not_called()

    def test_actual_worker_forwards_checked_ledger_and_admission(self):
        import importlib.util
        from vipe_benchmark.config import ROOT
        admitted=Mock();run=Mock();adapter=Mock();depth=SimpleNamespace(
            MetricVideoDepthAdapter=adapter,VideoDepthAdapter=adapter,admitted_video_request=admitted,run_video_actual=run)
        spec=importlib.util.spec_from_file_location('actual_video_worker',ROOT/'scripts/basketball_vipe_video_actual.py')
        module=importlib.util.module_from_spec(spec)
        request=dict(ledger_path=str(self.ledger.path),component='D9',setup=file_record(self.path),admission={'checked':True})
        with patch.dict(sys.modules,{'vipe_benchmark.video_depth':depth}):spec.loader.exec_module(module)
        loader=Mock(return_value=self.model)
        with patch.dict(module.__dict__,dict(read_json=Mock(return_value=request),load=Mock(return_value={}),
                Ledger=Mock(return_value=self.ledger),load_native_video=loader)), \
                patch.object(sys,'argv',['worker','--request','fixture-request','--output','fixture-output']):
            module.main()
        admitted.assert_called_once()
        loader.assert_called_once_with('D9',request['setup'],device='cuda',ledger=self.ledger,active_map_admission=request['admission'])
        run.assert_called_once()
