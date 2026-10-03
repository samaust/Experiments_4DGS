"""Actual worker boundary refuses fixture promotion before native work."""
import importlib
import unittest


class ActualResultTests(unittest.TestCase):
    def setUp(self):
        self.fixture = importlib.import_module('test_vipe_benchmark_final_render_pipeline').PipelineTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def test_actual_result_validator_rejects_fixture_request(self):
        from vipe_benchmark.final_render_actual_result import validate_actual_worker_result
        from vipe_benchmark.files import read_json
        with self.assertRaisesRegex(ValueError, 'actual'):
            validate_actual_worker_result(self.fixture.request, 'QF-B', 'geometry',
                read_json(self.fixture.records['geometry']['path']))

    def test_worker_entry_rejects_fixture_invocation_without_creating_output(self):
        from vipe_benchmark.final_render_actual_worker import execute
        record = self.fixture.record('invocation', dict(record_kind='fixture'))
        with self.assertRaisesRegex(ValueError, 'actual'):
            execute(record)

    def test_actual_request_with_fake_runtime_is_rejected_before_output(self):
        import copy
        from vipe_benchmark.final_render_workers import train
        from test_vipe_benchmark_final_render_workers import FakeFreeTimeRuntime
        request = copy.deepcopy(self.fixture.request)
        request['record_kind'] = 'actual'
        output = self.fixture.fixture.base.root/'forbidden-actual'
        with self.assertRaisesRegex(ValueError, 'actual.*invocation|invocation.*actual'):
            train(request,'QF-B',self.fixture.records['initializer'],None,output,FakeFreeTimeRuntime())
        self.assertFalse(output.exists())

    def test_actual_label_on_fixture_invocation_cannot_import_or_construct_native_runtime(self):
        from vipe_benchmark.final_render_actual_worker import execute
        request = self.fixture.record('request', self.fixture.request)
        invocation = self.fixture.record('relabeled-invocation',dict(record_kind='actual',request=request,arm='QF-B',phase='train'))
        with self.assertRaisesRegex(ValueError, 'actual request'):
            execute(invocation)

    def test_actual_worker_rejects_injected_clock_before_output(self):
        import copy
        from vipe_benchmark.final_render_workers import train
        from test_vipe_benchmark_final_render_workers import FakeFreeTimeRuntime
        request = copy.deepcopy(self.fixture.request);request['record_kind']='actual'
        output = self.fixture.fixture.base.root/'injected-clock'
        with self.assertRaisesRegex(ValueError,'monotonic clock'):
            train(request,'QF-B',self.fixture.records['initializer'],None,output,
                FakeFreeTimeRuntime(),clock=lambda:0.)
        self.assertFalse(output.exists())

    def test_pinned_cli_release_does_not_promote_fixture_invocation(self):
        import subprocess
        import sys
        from pathlib import Path
        invocation = self.fixture.record('fixture-cli-invocation',dict(record_kind='fixture'))
        release = self.fixture.record('release',dict(schema='plan069-final-render-actual-release/v1',invocation=invocation))
        script = Path(__file__).resolve().parents[1]/'scripts/final-render-actual-worker.py'
        completed = subprocess.run([sys.executable,str(script),'--invocation',invocation['path'],
            '--release-file',release['path']],capture_output=True,text=True,timeout=15)
        self.assertNotEqual(completed.returncode,0)
        self.assertIn('actual invocation required; fixtures cannot be promoted',completed.stderr)

    def test_pinned_cli_rejects_substituted_release_invocation(self):
        import subprocess
        import sys
        from pathlib import Path
        invocation = self.fixture.record('fixture-gate-invocation',dict(record_kind='fixture'))
        replacement = self.fixture.record('other-invocation',dict(record_kind='fixture',different=True))
        release = self.fixture.record('wrong-release',dict(schema='plan069-final-render-actual-release/v1',invocation=replacement))
        script = Path(__file__).resolve().parents[1]/'scripts/final-render-actual-worker.py'
        completed = subprocess.run([sys.executable,str(script),'--invocation',invocation['path'],
            '--release-file',release['path']],capture_output=True,text=True,timeout=15)
        self.assertNotEqual(completed.returncode,0)
        self.assertIn('exact immutable invocation release required',completed.stderr)
