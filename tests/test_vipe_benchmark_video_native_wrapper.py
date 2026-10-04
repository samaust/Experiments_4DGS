"""CPU fixtures for the root-owned outer wrapper; never install real filters/models."""
import importlib.util
import json
from pathlib import Path
import tempfile
import signal
import sys
from types import SimpleNamespace
from types import ModuleType
import unittest
from unittest.mock import patch

WRAPPER = Path(__file__).resolve().parents[1] / 'docs/research/vipe-alternatives/plan031-execution/video-native-wrapper-001/wrapper.py'
spec = importlib.util.spec_from_file_location('video_outer_wrapper', WRAPPER)
wrapper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wrapper)


class VideoNativeWrapperTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.events = [dict(sequence=808, event_sha256='prefix')]
        self.states = {}
        class FakeLedger:
            path = root / 'ledger.jsonl'
            def __init__(inner, *args): pass
            def events(inner): return self.events
            def states(inner, events): return self.states
        def module(name, **values):
            result = ModuleType(name)
            result.__dict__.update(values)
            return result
        def retained(name, value):
            path = root / name
            path.write_text(json.dumps(value))
            return wrapper.record(path)
        setup = retained('setup.json', dict(job_id='plan069-D9-setup-recovery-002', authorization=None))
        request = retained('request.json', {})
        authorization = retained('DO.json', {})
        setup_doc = dict(job_id='plan069-D9-setup-recovery-002', authorization=authorization)
        Path(setup['path']).write_text(json.dumps(setup_doc))
        setup = wrapper.record(setup['path'])
        self.sources = [wrapper.record(WRAPPER.parent/name) for name in ('wrapper.py','prepare_admission.py','prepare_request.py')]
        method = retained('producer.py', {})
        cpu = retained('cpu.json', dict(schema='plan069-delta-cpu-test-capture/v1', passed=True, source_bytes_unchanged=True, commands=[dict(cleanup=dict(confirmed_no_surviving_observed_processes=True))], sources_after=self.sources + [method]))
        review_rec = retained('source.json', {})
        admission = retained('admission.json', dict(schema='plan069-video-native-cpu-admission/v1', candidate='D9', cpu_accounting_owner='D9', seconds=180, ledger_head_sequence=808, ledger_head_sha256='prefix', candidate_cpu_remaining_seconds=942, global_cpu_remaining_seconds=30000, source_review=review_rec, setup=setup))
        self.config = dict(root=str(root),candidate='D9',ledger=str(root/'ledger.jsonl'),seconds=180,cpu_workers=7,method=method, bindings=dict(setup=setup,setup_request=request,authorization=authorization,cpu_qualification=cpu,cpu_admission=admission,source_review=review_rec))
        self.config['command'] = ['/explicit/python', '-I', '-B', method['path'], 'capture', '--root', str(root), '--candidate', 'D9', '--setup', setup['path'], '--setup-request', request['path'], '--authorization', authorization['path'], '--ledger', str(root/'ledger.jsonl'), '--output', str(root/'capture'), '--seconds', '140', '--artifact-bytes', str(64*1024*1024)]
        self.review = dict(local_sources=[], supplemental_sources=self.sources)
        mods = {
            'vipe_benchmark.config': module('config', load=lambda: {}),
            'vipe_benchmark.ledger': module('ledger', Ledger=FakeLedger),
            'vipe_benchmark.depth_recovery_lineage': module('lineage', accepted_setup_lineage=lambda *args: dict(request=request)),
            'vipe_benchmark.depth_authorization': module('authorization', execution_authorization=lambda *args, **kwargs: (None,authorization,None,None)),
        }
        self.patch = patch.dict('sys.modules', mods)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def change(self, role, **values):
        path = Path(self.config['bindings'][role]['path'])
        doc = json.loads(path.read_text())
        doc.update(values)
        path.write_text(json.dumps(doc))

    def test_current_accepted002_and_qualified_wrapper_pass(self):
        wrapper.verify_admission(self.config, self.review)

    def test_active_protected_job_denies(self):
        self.states['job'] = dict(event='reserve')
        with self.assertRaisesRegex(ValueError, 'active job'):
            wrapper.verify_admission(self.config, self.review)

    def test_prompts_ledger_denied_before_any_ledger_read(self):
        self.config['ledger']=str(Path(self.temp.name)/'prompts'/'ledger.jsonl')
        with self.assertRaisesRegex(ValueError,'prompts ledger'):
            wrapper.verify_admission(self.config,self.review)

    def test_stale_admission_prefix_denies(self):
        self.change('cpu_admission', ledger_head_sequence=807)
        with self.assertRaisesRegex(ValueError, 'prefix'):
            wrapper.verify_admission(self.config, self.review)

    def test_cumulative_budget_cannot_be_reset(self):
        self.change('cpu_admission', candidate_cpu_remaining_seconds=179)
        with self.assertRaisesRegex(ValueError, 'budget'):
            wrapper.verify_admission(self.config, self.review)

    def test_missing_wrapper_source_proof_denies(self):
        self.change('cpu_qualification', sources_after=[self.config['method']])
        with self.assertRaisesRegex(ValueError, 'qualified source'):
            wrapper.verify_admission(self.config, self.review)

    def test_changed_generator_cannot_use_stale_qualification(self):
        self.change('cpu_qualification',sources_after=[self.sources[0],self.sources[1],self.config['method']])
        with self.assertRaisesRegex(ValueError,'qualified source'):
            wrapper.verify_admission(self.config,self.review)

    def test_unclean_cpu_capture_denies(self):
        self.change('cpu_qualification', commands=[dict(cleanup={})])
        with self.assertRaisesRegex(ValueError, 'clean focused'):
            wrapper.verify_admission(self.config, self.review)

    def test_unauthorized_extra_command_flag_denies(self):
        self.config['command'] += ['--setup-dispatch','other']
        with self.assertRaisesRegex(ValueError, 'command flags'):
            wrapper.verify_admission(self.config, self.review)

    def test_prompts_symlink_denies_before_read(self):
        target = Path(self.temp.name) / 'prompts'
        target.mkdir()
        linked = Path(self.temp.name) / 'link'
        linked.symlink_to(target / 'secret')
        with self.assertRaisesRegex(ValueError, 'prompts prohibited'):
            wrapper.record(linked)

    def test_descendant_observation_retains_identity_and_pidfd(self):
        observed = {}
        parent = dict(pid=11,ppid=5,start_ticks=20,state='S')
        child = dict(pid=12,ppid=11,start_ticks=21,state='S')
        with patch.object(wrapper.os,'getpid',return_value=5), patch.object(wrapper,'census',return_value={11:parent,12:child}), patch.object(wrapper.os,'pidfd_open',side_effect=[101,102]):
            wrapper.observe_descendants(observed)
        self.assertEqual(set(observed), {(11,20),(12,21)})
        self.assertEqual(observed[(12,21)]['pidfd'],102)

    def test_external_termination_enters_owned_cleanup(self):
        root = Path(self.temp.name)
        self.config.update(schema='plan069-video-parent-cpu-request/v1', admitted=True, charge_owner='root', cpu_accounting_owner='D9', bootstrap=wrapper.record(Path(sys.executable).resolve()), interpreter_invocation=sys.executable, cleanup_seconds=20, accepted_setup_sha256=self.config['bindings']['setup']['sha256'], output=str(root/'outer'), disk_roots=[dict(role=role,path=str(root),maximum_total_bytes=10000000,maximum_delta_bytes=1000000) for role in ('global','candidate','runtime-cache')])
        recipe = root/'recipe.json'
        recipe.write_text('{}')
        self.config['bindings']['runtime_recipe']=wrapper.record(recipe)
        self.review.update(candidate='D9',status='passed',schema='plan069-depth-source-review/v1',runtime_recipe=wrapper.record(recipe))
        Path(self.config['bindings']['source_review']['path']).write_text(json.dumps(self.review))
        self.config['bindings']['source_review']=wrapper.record(self.config['bindings']['source_review']['path'])
        self.config['command'][0]=sys.executable
        request=root/'outer-request.json'
        request.write_text(json.dumps(self.config))
        process=SimpleNamespace(poll=lambda: None,returncode=None)
        libc=SimpleNamespace(prctl=lambda *args:0)
        def terminate_signal(*args):
            signal.raise_signal(signal.SIGTERM)
        with patch.object(wrapper,'verify_admission'), patch.object(wrapper.ctypes,'CDLL',return_value=libc), patch.object(wrapper,'disk_bytes',return_value=0), patch.object(wrapper.subprocess,'Popen',return_value=process), patch.object(wrapper,'observe_descendants',return_value={}), patch.object(wrapper.os,'waitpid',side_effect=ChildProcessError), patch.object(wrapper.time,'sleep',side_effect=terminate_signal):
            with self.assertRaisesRegex(ValueError,'externally terminated'):
                wrapper.run(request)
        result=json.loads((root/'outer/result.json').read_text())
        self.assertEqual(result['status'],'failed')
        self.assertTrue(result['cleanup_confirmed'])
        self.assertIn('InterruptedError',result['error'])

    def test_pid_reuse_is_rejected_without_signal(self):
        old = dict(pid=11,ppid=5,start_ticks=20,state='S')
        new = dict(old,start_ticks=99)
        with patch.object(wrapper.os,'getpid',return_value=5), patch.object(wrapper,'census',side_effect=[{11:old},{11:new}]), patch.object(wrapper.os,'pidfd_open',return_value=101), patch.object(wrapper.os,'close') as close:
            with self.assertRaisesRegex(ValueError,'PID identity changed'):
                wrapper.observe_descendants({})
            close.assert_called_once_with(101)


if __name__ == '__main__':
    unittest.main()
