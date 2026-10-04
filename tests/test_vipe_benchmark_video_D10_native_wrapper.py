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

WRAPPER = Path(__file__).resolve().parents[1] / 'docs/research/vipe-alternatives/plan031-execution/video-native-wrapper-002/wrapper.py'
spec = importlib.util.spec_from_file_location('video_outer_wrapper', WRAPPER)
wrapper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wrapper)


class VideoD10NativeWrapperTests(unittest.TestCase):
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
        setup = retained('setup.json', dict(job_id='plan069-D10-setup-001', authorization=None))
        request = retained('request.json', {})
        authorization = retained('DO.json', dict(video_frame_amendment=dict(D9_runtime_qualification={},D9_qualification_ledger_prefix={})))
        authority_review = retained('authority-review.json', {})
        setup_doc = dict(job_id='plan069-D10-setup-001', authorization=authorization, schema='plan069-video-setup-result/v1',candidate='D10',record_kind='actual',status='complete',source_dir=str(root/'source'),source_revision='code',weight_revision='weights',review=authority_review)
        Path(setup['path']).rename(root/'result.json')
        setup = dict(setup,path=str(root/'result.json'))
        recipe = retained('recipe.json', {})
        request = retained('request.json', dict(schema='plan069-depth-setup-request/v1',candidate='D10',record_kind='actual',job_id=setup_doc['job_id'],review=authority_review,authorization=authorization,runtime_environment=dict(recipe=recipe)))
        runtime = retained('runtime.json', {})
        setup_doc['runtime_environment'] = runtime
        (root/'request.json').write_text(json.dumps(dict(schema='plan069-depth-setup-request/v1',candidate='D10',record_kind='actual',job_id=setup_doc['job_id'],review=authority_review,authorization=authorization,runtime_environment=dict(recipe=recipe),setup_request=request)))
        request=wrapper.record(root/'request.json')
        runtime_dir=root/'runtime';runtime_dir.mkdir()
        runtime=retained('runtime/result.json', {})
        retained('runtime/request.json',dict(setup_request=request))
        setup_doc['runtime_environment']=runtime
        Path(setup['path']).write_text(json.dumps(setup_doc))
        setup = wrapper.record(setup['path'])
        dispatch = retained('dispatch.json',dict(schema='plan069-video-setup-dispatch/v1',status='complete',result=setup))
        self.sources = [wrapper.record(WRAPPER.parent/name) for name in ('wrapper.py','prepare_admission.py','prepare_request.py')]
        method = retained('producer.py', {})
        cpu = retained('cpu.json', dict(schema='plan069-delta-cpu-test-capture/v1', passed=True, source_bytes_unchanged=True, commands=[dict(cleanup=dict(confirmed_no_surviving_observed_processes=True))], sources_after=self.sources + [method]))
        review_rec = retained('source.json', {})
        admission = retained('admission.json', dict(schema='plan069-video-native-cpu-admission/v1', candidate='D10', cpu_accounting_owner='D10', seconds=180, ledger_head_sequence=808, ledger_head_sha256='prefix', candidate_cpu_remaining_seconds=942, global_cpu_remaining_seconds=30000, source_review=review_rec, setup=setup))
        self.config = dict(root=str(root),candidate='D10',ledger=str(root/'ledger.jsonl'),seconds=180,cpu_workers=7,method=method, bindings=dict(setup=setup,setup_request=request,setup_dispatch=dispatch,runtime_environment=runtime,runtime_recipe=recipe,authorization=authorization,cpu_qualification=cpu,cpu_admission=admission,source_review=review_rec))
        self.config['command'] = ['/explicit/python', '-I', '-B', method['path'], 'capture', '--root', str(root), '--candidate', 'D10', '--setup', setup['path'], '--setup-request', request['path'], '--setup-dispatch', dispatch['path'], '--authorization', authorization['path'], '--ledger', str(root/'ledger.jsonl'), '--output', str(root/'capture'), '--seconds', '140', '--artifact-bytes', str(64*1024*1024)]
        self.review = dict(local_sources=[], supplemental_sources=self.sources)
        mods = {
            'vipe_benchmark.config': module('config', load=lambda: {}),
            'vipe_benchmark.ledger': module('ledger', Ledger=FakeLedger),
            'vipe_benchmark.depth_recovery_lineage': module('lineage', accepted_setup_lineage=lambda *args: dict(request=request)),
            'vipe_benchmark.depth_authorization': module('authorization', execution_authorization=lambda *args, **kwargs: (authority_review,authorization,dict(candidate_config=dict(code=dict(revision='code'),weights=dict(revision='weights'))),None)),
            'vipe_benchmark.depth_video_frame_authorization': module('prerequisite',validate_D9_prerequisite=lambda *args, **kwargs: None),
            'vipe_benchmark.video_environment': module('environment',bind_source_environment=lambda *args, **kwargs: {}),
        }
        self.patch = patch.dict('sys.modules', mods)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def change(self, role, **values):
        path = Path(self.config['bindings'][role]['path'])
        doc = json.loads(path.read_text())
        doc.update(values)
        path.write_text(json.dumps(doc))

    def test_ordinary_setup_and_qualified_wrapper_pass(self):
        wrapper.verify_admission(self.config, self.review)

    def test_failed_D9_prerequisite_denies_before_capture(self):
        with patch.object(sys.modules['vipe_benchmark.depth_video_frame_authorization'],
                          'validate_D9_prerequisite', side_effect=ValueError('actual D9 missing')):
            with self.assertRaisesRegex(ValueError, 'actual D9 missing'):
                wrapper.verify_admission(self.config, self.review)

    def test_D9_prerequisite_rechecked_against_live_events_without_active_exception(self):
        with patch.object(sys.modules['vipe_benchmark.depth_video_frame_authorization'],
                          'validate_D9_prerequisite') as validate:
            wrapper.verify_admission(self.config, self.review)
        self.assertEqual(validate.call_args.kwargs['current_events'], self.events)
        self.assertFalse(validate.call_args.kwargs['allow_owned_active'])

    def test_wrong_dispatch_result_denies(self):
        self.change('setup_dispatch', result={})
        with self.assertRaisesRegex(ValueError, 'supervised ordinary'):
            wrapper.verify_admission(self.config, self.review)

    def test_recovered_setup_is_not_ordinary_D10(self):
        self.change('setup', schema='plan069-video-setup-recovery-result/v2')
        with self.assertRaisesRegex(ValueError, 'ordinary D10 setup'):
            wrapper.verify_admission(self.config, self.review)

    def test_runtime_original_request_binding_denies(self):
        runtime_path=Path(self.config['bindings']['runtime_environment']['path']).parent/'request.json'
        runtime_path.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'original immutable setup recipe'):
            wrapper.verify_admission(self.config, self.review)

    def test_original_setup_request_authorization_differs(self):
        self.change('setup_request', authorization={})
        with self.assertRaisesRegex(ValueError, 'exact original setup request'):
            wrapper.verify_admission(self.config, self.review)

    def test_nonconditional_DO_denies(self):
        self.change('authorization', video_frame_amendment=None)
        with self.assertRaisesRegex(ValueError, 'conditional D10 frame DO'):
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
        self.config['command'] += ['--unexpected','other']
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
        self.config.update(schema='plan069-video-parent-cpu-request/v1', admitted=True, charge_owner='root', cpu_accounting_owner='D10', bootstrap=wrapper.record(Path(sys.executable).resolve()), interpreter_invocation=sys.executable, cleanup_seconds=20, accepted_setup_sha256=self.config['bindings']['setup']['sha256'], output=str(root/'outer'), disk_roots=[dict(role=role,path=str(root),maximum_total_bytes=10000000,maximum_delta_bytes=1000000) for role in ('global','candidate','runtime-cache')])
        recipe = root/'recipe.json'
        recipe.write_text('{}')
        self.config['bindings']['runtime_recipe']=wrapper.record(recipe)
        self.review.update(candidate='D10',status='passed',schema='plan069-depth-source-review/v1',runtime_recipe=wrapper.record(recipe))
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
