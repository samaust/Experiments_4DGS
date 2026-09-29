import copy
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.config import load
from vipe_benchmark.files import read_json
from vipe_benchmark.ledger import Ledger
from vipe_benchmark.supervisor import group_processes, supervise, SupervisionFailure


class SupervisorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.config = copy.deepcopy(load())
        self.config['cpu_prepare_score_report_seconds_limit'] = 3.
        self.ledger = Ledger(self.root / 'ledger.jsonl', self.config)

    def tearDown(self):
        self.temporary.cleanup()

    def command(self, code):
        return [sys.executable, '-c', code, str(self.root / 'output')]

    @staticmethod
    def validate(output):
        if read_json(output / 'result.json').get('status') != 'complete':
            raise ValueError('incomplete result')

    def run_worker(self, code, **kwargs):
        return supervise(self.ledger, 'prepare', self.command(code), self.root / 'output',
                         evidence={'kind': 'disposable CPU fixture; not a model evaluation'},
                         validate_result=self.validate, poll_seconds=.02, **kwargs)

    def test_completed_worker_is_not_dispatched_again(self):
        code = "import sys,json; from pathlib import Path; p=Path(sys.argv[1]); p.mkdir(); (p/'result.json').write_text(json.dumps({'status':'complete'}))"
        self.assertEqual(self.run_worker(code)['status'], 'complete')
        with self.assertRaises(ValueError):
            self.ledger.reserve('prepare', ['false'], {})
        state = self.ledger.states()['prepare']
        self.assertTrue(state['cleanup_confirmed'])
        self.assertLess(state['elapsed_seconds'], 3.)
        self.assertEqual(self.ledger.totals()['cpu']['attempts'], 1)

    def test_native_kernel_caches_stay_in_monitored_attempt_and_override_external_paths(self):
        from vipe_benchmark.supervisor import directory_bytes
        keys = ['TRITON_HOME', 'TRITON_CACHE_DIR', 'TRITON_DUMP_DIR', 'TRITON_OVERRIDE_DIR',
                'TORCHINDUCTOR_CACHE_DIR', 'CUDA_CACHE_PATH']
        outside = self.root / 'outside-run'
        code = ('import os,sys,json; from pathlib import Path; '
                'p=Path(sys.argv[1]); p.mkdir(); '
                f'caches={{k:os.environ[k] for k in {keys!r}}}; '
                '[(Path(v).mkdir(parents=True,exist_ok=True), '
                '(Path(v)/"kernel.bin").write_bytes(b"x"*4096)) for v in caches.values()]; '
                '(p/"result.json").write_text(json.dumps(dict(status="complete",caches=caches)))')
        with patch.dict('os.environ', {key: str(outside) for key in keys}):
            self.run_worker(code, sample_resources=lambda: dict(artifact_bytes=directory_bytes(self.root)))
        result = read_json(self.root / 'output/result.json')
        temporary = self.root / 'output-temporary'
        self.assertTrue(all(Path(value).is_relative_to(temporary) for value in result['caches'].values()))
        self.assertFalse(outside.exists())
        event = next(row for row in self.ledger.events() if row['event'] == 'temporary_directory')
        self.assertEqual(event['native_caches'], result['caches'])
        self.assertGreaterEqual(self.ledger.states()['prepare']['peak']['artifact_bytes'], 6 * 4096)

    def test_timeout_kills_sigterm_ignoring_group_within_allocation(self):
        self.config['cpu_prepare_score_report_seconds_limit'] = .8
        self.ledger = Ledger(self.root / 'ledger.jsonl', self.config)
        code = 'import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(20)'
        with self.assertRaisesRegex(RuntimeError, 'deadline'):
            self.run_worker(code)
        state = self.ledger.states()['prepare']
        self.assertEqual(state['status'], 'failed')
        self.assertTrue(state['cleanup_confirmed'])
        self.assertLess(state['elapsed_seconds'], .85)
        start = next(r for r in self.ledger.events() if r['event'] == 'started')
        self.assertEqual(group_processes(start['pgid']), [])

    def test_child_survival_invalidates_parent_success_and_is_cleaned_up(self):
        code = "import subprocess,sys; subprocess.Popen([sys.executable,'-c','import time; time.sleep(20)'])"
        with self.assertRaisesRegex(RuntimeError, 'live child'):
            self.run_worker(code)
        state = self.ledger.states()['prepare']
        self.assertTrue(state['cleanup_confirmed'])
        self.assertEqual(state['surviving_pids'], [])

    def test_missing_result_and_nonzero_exit_consume_attempts(self):
        with self.assertRaisesRegex(RuntimeError, 'FileNotFoundError'):
            self.run_worker('pass')
        self.assertEqual(self.ledger.states()['prepare']['status'], 'failed')
        with self.assertRaises(ValueError):
            Ledger(self.root / 'ledger.jsonl', self.config).reserve('prepare', [], {})

    def test_interruption_cleans_owned_process_group(self):
        code = 'import os,signal,time; os.kill(os.getppid(),signal.SIGTERM); time.sleep(20)'
        with self.assertRaisesRegex(RuntimeError, 'InterruptedError'):
            self.run_worker(code)
        self.assertEqual(self.ledger.states()['prepare']['status'], 'failed')
        self.assertTrue(self.ledger.states()['prepare']['cleanup_confirmed'])
        self.assertTrue(self.ledger.states()['prepare']['stop_required'])
        self.assertEqual(self.ledger.states()['prepare']['failure_kind'], 'interrupted')

    def test_simulated_storage_cap_stops_worker(self):
        samples = iter([{}, dict(artifact_bytes=151 * 2**30)])
        with self.assertRaisesRegex(RuntimeError, 'storage ceiling'):
            self.run_worker('import time; time.sleep(20)', sample_resources=lambda: next(samples))
        self.assertTrue(self.ledger.states()['prepare']['cleanup_confirmed'])
        self.assertTrue(self.ledger.states()['prepare']['stop_required'])

    def test_preexisting_resource_cap_never_spends_an_attempt(self):
        with self.assertRaisesRegex(ValueError, 'already exhausted'):
            self.run_worker('pass', sample_resources=lambda: dict(artifact_bytes=151 * 2**30))
        self.assertEqual(self.ledger.totals()['cpu']['attempts'], 0)

    def test_simulated_memory_and_foreign_gpu_process(self):
        with self.assertRaisesRegex(ValueError, 'already in use'):
            self.run_worker('pass', sample_resources=lambda: dict(gpu_pids=[999999]))
        self.assertEqual(self.ledger.totals()['cpu']['attempts'], 0)
        samples = iter([{}, dict(device_bytes=23 * 2**30)])
        with self.assertRaisesRegex(SupervisionFailure, 'memory ceiling') as failure:
            self.run_worker('import time; time.sleep(20)', sample_resources=lambda: next(samples))
        self.assertEqual(self.ledger.totals()['cpu']['attempts'], 1)
        self.assertTrue(failure.exception.stop_required)
        self.assertEqual(failure.exception.kind, 'device_memory')

    def test_gpu_sample_of_exited_unreaped_worker_keeps_true_group_ownership(self):
        import time
        code = "import sys,json; from pathlib import Path; p=Path(sys.argv[1]); p.mkdir(); (p/'result.json').write_text(json.dumps({'status':'complete'}))"
        def sample():
            events = [e for e in self.ledger.events() if e['event'] == 'started']
            if not events:
                return {}
            pid = events[-1]['pid']
            deadline = time.monotonic() + 1.
            while time.monotonic() < deadline:
                fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
                if fields[0] == 'Z':
                    self.assertNotIn(pid, group_processes(pid))
                    self.assertIn(pid, group_processes(pid, include_zombies=True))
                    return dict(gpu_pids=[pid])
                time.sleep(.005)
            self.fail('fixture worker did not reach zombie state')
        self.assertEqual(self.run_worker(code, sample_resources=sample)['status'], 'complete')
        self.assertTrue(self.ledger.states()['prepare']['cleanup_confirmed'])

    def test_foreign_gpu_pid_still_fails_and_preserves_ownership_evidence(self):
        samples = iter([{}, dict(gpu_pids=[99999999])])
        with self.assertRaisesRegex(SupervisionFailure, 'exclusive GPU access lost'):
            self.run_worker('import time; time.sleep(20)', sample_resources=lambda: next(samples))
        evidence = next(e for e in self.ledger.events() if e['event'] == 'gpu_ownership_failure')
        self.assertEqual(evidence['foreign_pids'], [99999999])
        self.assertTrue(self.ledger.states()['prepare']['cleanup_confirmed'])

    def test_restart_does_not_relaunch_unfinished_attempt(self):
        self.ledger.reserve('prepare', [], {})
        restarted = Ledger(self.root / 'ledger.jsonl', self.config)
        self.assertEqual(restarted.totals()['cpu']['reserved_seconds'], 3.)
        with self.assertRaisesRegex(ValueError, 'unreconciled'):
            restarted.reserve('annotations', [], {})
        self.ledger.finish('prepare', 'failed', 3., reason='fixture consumed full allocation')
        with self.assertRaisesRegex(ValueError, 'exhausted'):
            restarted.reserve('annotations', [], {})

    def test_append_chain_detects_changed_history(self):
        self.ledger.note('fixture', value=1)
        self.ledger.path.write_text(self.ledger.path.read_text().replace('"value":1', '"value":2'))
        with self.assertRaisesRegex(ValueError, 'corruption'):
            self.ledger.events()

    def test_explicit_resume_reopens_unstarted_slots_only(self):
        self.ledger.account('annotations', 'blocked', 'missing independently reviewed labels')
        with self.assertRaisesRegex(ValueError, 'already consumed or accounted'):
            self.ledger.reserve('annotations', [], {})
        with self.assertRaises(ValueError):
            self.ledger.resume_unstarted(['annotations'], '')
        self.ledger.resume_unstarted(['annotations'], 'synthetic explicit user resume instruction')
        self.ledger.reserve('annotations', [], {})
        self.ledger.finish('annotations', 'failed', .1)
        with self.assertRaisesRegex(ValueError, 'consumed attempts'):
            self.ledger.resume_unstarted(['annotations'], 'another explicit instruction')
        self.assertEqual(self.ledger.totals()['cpu']['attempts'], 1)

    def test_concurrent_reservation_has_one_winner(self):
        code = ('import sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); '
                'from vipe_benchmark.ledger import Ledger; from vipe_benchmark.config import load; '
                'Ledger(Path(sys.argv[2]),load()).reserve("prepare",[],{})')
        command = [sys.executable, '-c', code, str(Path(__file__).resolve().parents[1] / 'scripts'), str(self.root / 'race.jsonl')]
        workers = [subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) for _ in range(2)]
        self.assertEqual(sorted(p.wait(timeout=10) for p in workers), [0, 1])





SUBTEST_CASES = {
    'test_vipe_benchmark_supervisor.HelperSessionTests.test_progress_plan046_worker_authority': [{'kind':'reuse'}, {'kind':'conflict'}, {'kind':'forged_seal'}, {'kind':'resume'}, {'kind':'publish_adapter'}],
    'test_vipe_benchmark_supervisor.HelperSessionTests.test_progress_plan046_launch_deadline': [{'kind':'before','offset':-0.001}, {'kind':'equal','offset':0.0}, {'kind':'after','offset':0.001}],
    'test_vipe_benchmark_supervisor.HelperSessionTests.test_progress_plan046_ownership': [
        {'kind':'hash'}, {'kind':'root_bool'}, {'kind':'pid_reuse'}, {'kind':'output'}, {'kind':'plan'}, {'kind':'omitted_source'}, {'kind':'overflow'}, {'kind':'enumeration'}, {'kind':'unproven_detached'}],
    'test_vipe_benchmark_supervisor.HelperSessionTests.test_progress_plan046_protocol': [{'kind': 'notice_bool_request'},
 {'kind': 'notice_bool_pid'},
 {'kind': 'notice_bad_record'},
 {'kind': 'ack_bool_sequence'},
 {'kind': 'ack_bad_record'},
 {'kind': 'head_schema'},
 {'kind': 'head_bool_sequence'},
 {'kind': 'head_bad_previous'},
 {'kind': 'reference_bool_frozen'},
 {'kind': 'checkpoint_bool_deadline'},
 {'kind': 'runtime_alias'},
 {'kind': 'numeric_overflow'}],
    'test_vipe_benchmark_supervisor.HelperSessionTests.test_progress_plan046_inventory': [{'kind': 'result_mismatch'},
 {'kind': 'result_mutation'},
 {'kind': 'membership_add'},
 {'kind': 'membership_remove'},
 {'kind': 'parent_replace'}],
    'test_vipe_benchmark_supervisor.HelperSessionTests.test_progress_plan046_summary': [{'kind': 'absent'},
 {'kind': 'same'},
 {'kind': 'lower_counts'},
 {'kind': 'first_conflict'},
 {'kind': 'runtime_conflict'},
 {'kind': 'runtime_alias'}],
    'test_vipe_benchmark_supervisor.HelperSessionTests.test_progress_plan046_publication_faults': [{'kind': 'write'},
 {'kind': 'flush'},
 {'kind': 'file_fsync'},
 {'kind': 'close_readback'},
 {'kind': 'generation_install'},
 {'kind': 'generation_directory_fsync'},
 {'kind': 'head_install'},
 {'kind': 'head_directory_fsync'},
 {'kind': 'final_readback'},
 {'kind': 'notice_send'},
 {'kind': 'notice_receive'},
 {'kind': 'owner_retention'},
 {'kind': 'ack_send'},
 {'kind': 'ack_receipt'}, {'kind':'short_write'}, {'kind':'generation_collision'}, {'kind':'notice_full'}, {'kind':'receive_truncated'}, {'kind':'receive_credentials'}, {'kind':'ack_wrong'}],
    'test_vipe_benchmark_supervisor.HelperSessionTests.test_progress_closed_inventory_and_faults': [
        {'kind': 'deadline'},
        {'kind': 'symlink'},
        {'kind': 'candidate'},
        {'kind': 'entries'},
        {'kind': 'sources'},
        {'kind': 'bytes'},
        {'kind': 'traversal'},
        {'kind': 'write'},
        {'kind': 'fsync'},
        {'kind': 'readback'},
    ],
    'test_vipe_benchmark_supervisor.HelperSessionTests.test_progress_metadata_mutations': [
        {'kind': 'schema'},
        {'kind': 'bool_sequence'},
        {'kind': 'generation_overflow'},
        {'kind': 'qualified_type'},
        {'kind': 'count'},
        {'kind': 'count_bool'},
        {'kind': 'identity'},
        {'kind': 'category'},
        {'kind': 'order'},
        {'kind': 'seal'},
        {'kind': 'source'},
        {'kind': 'context'},
        {'kind': 'late'},
        {'kind': 'pid'},
        {'kind': 'request'},
        {'kind': 'errors'},
        {'kind': 'error_bytes'},
        {'kind': 'runtime'},
        {'kind': 'unclosed'},
        {'kind': 'complete'},
    ],
    'test_vipe_benchmark_supervisor.HelperSessionTests.test_progress_strict_primitives': [
        {'kind': 'duplicate'},
        {'kind': 'nonfinite'},
        {'kind': 'depth'},
        {'kind': 'oversize'},
        {'kind': 'truncated'},
        {'kind': 'string'},
        {'kind': 'bool'},
        {'kind': 'equal_deadline'},
        {'kind': 'after_deadline'},
        {'kind': 'before_deadline'},
    ],
    'test_vipe_benchmark_supervisor.HelperIntegrationTests.test_cleanup_matrix': [
        {'role': 'task', 'outcome': 'success'},
        {'role': 'sample', 'outcome': 'success'},
        {'role': 'task', 'outcome': 'error'},
        {'role': 'sample', 'outcome': 'error'},
        {'role': 'task', 'outcome': 'timeout'},
        {'role': 'sample', 'outcome': 'timeout'},
    ],
    'test_vipe_benchmark_supervisor.HelperIntegrationTests.test_cleanup_failures': [
        {'mode': 'false_then_reaped'},
        {'mode': 'false'},
        {'mode': 'close_exception'},
        {'mode': 'enumeration_exception'},
        {'mode': 'kill_exception'},
        {'mode': 'reap_exception'},
    ],
}


class HelperIntegrationTests(unittest.TestCase):
    def setUp(self):
        import time
        from vipe_benchmark import supervisor as sup
        self.sup = sup
        self.time = time
        self.config = load()
        self.reading = dict(device_bytes=3, artifact_bytes=5, download_bytes=7, gpu_pids=[])
        self.operation = dict(operation='constant', args=dict(value=37))
        self.sampler = dict(operation='constant', args=dict(value=self.reading))
        self.life = sup.HelperLifecycle()

    def call(self, **kwargs):
        return self.sup.monitored_call(self.operation, self.time.monotonic()+kwargs.pop('seconds', 2),
            self.sampler, self.config, kwargs.pop('peak', {}), lifecycle=self.life, **kwargs)

    def test_spawn_constant_reaped_under_actual_runner(self):
        self.assertEqual(self.call(), 37)
        self.assertEqual(self.life.helpers, [])

    def test_importable_guarded_file_control(self):
        command = [sys.executable, '-B', '-m', 'vipe_benchmark.s1_validation_runner', '--helper-probe']
        import os
        env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]/'scripts'))
        result = subprocess.run(command, capture_output=True, text=True, timeout=5, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('37; reaped', result.stdout)

    def test_bootstrap_failure_and_eof_preserve_child(self):
        from unittest.mock import patch
        import multiprocessing.process
        import signal
        with patch('vipe_benchmark.s1_helper_session.Owner.spawn', side_effect=OSError('bootstrap failed')):
            with self.assertRaises(self.sup.HelperFailure) as caught:
                self.call()
        self.assertEqual(caught.exception.failure['phase'], 'startup')
        self.assertEqual(self.life.helpers, [])
        self.life = self.sup.HelperLifecycle()
        helper = self.life.acquire()
        helper.await_ready()
        killed_pid = helper.owner.records['work']['pid']
        os.kill(killed_pid, signal.SIGKILL)
        limit = self.time.monotonic()+2
        try:
            with self.assertRaises(self.sup.HelperFailure) as caught:
                while self.time.monotonic() < limit:
                    self.call()
                    self.time.sleep(.005)
            self.assertEqual(caught.exception.failure['phase'], 'transport')
            self.assertEqual(caught.exception.failure['ownership']['pid'], killed_pid)
        finally:
            self.assertTrue(self.life.reap(limit))

    def worker(self, code):
        process = subprocess.Popen([sys.executable, '-c', code], start_new_session=True)
        self.addCleanup(lambda: self.sup.stop_group(process, self.time.monotonic()+1))
        return process

    def owned(self, exited=False):
        worker = self.worker('pass' if exited else 'import time; time.sleep(10)')
        if exited:
            limit = self.time.monotonic()+2
            while self.time.monotonic() < limit:
                if Path(f'/proc/{worker.pid}/stat').read_text().rsplit(')',1)[1].split()[0] == 'Z':
                    break
                self.time.sleep(.005)
            self.assertNotIn(worker.pid, self.sup.group_processes(worker.pid))
        self.reading['gpu_pids'] = [worker.pid]
        peak = dict(device_bytes=11, artifact_bytes=2, download_bytes=13)
        self.assertEqual(self.call(worker=worker, peak=peak, phase='worker_sample'),37)
        self.assertEqual(peak,dict(device_bytes=11,artifact_bytes=5,download_bytes=13))

    def test_owned_live_pid(self):
        self.owned()

    def test_owned_unreaped_exited_pid(self):
        self.owned(exited=True)

    def rejected(self, worker=None, pids=None, phase='worker_sample'):
        self.reading['gpu_pids'] = pids or [os.getpid()]
        from unittest.mock import patch
        original = os.killpg
        signaled = []
        def kill(pgid, sig):
            signaled.append(pgid)
            return original(pgid,sig)
        with patch.object(os,'killpg',side_effect=kill):
            with self.assertRaises(self.sup.HelperFailure) as caught:
                self.call(worker=worker,phase=phase)
        self.assertEqual(caught.exception.failure['error_class'],'GPUOwnershipError')
        self.assertEqual(caught.exception.failure['phase'],phase)
        self.assertNotIn(os.getpgrp(),signaled)
        self.assertEqual(self.life.helpers,[])

    def test_foreign_only_pid(self):
        self.rejected()

    def test_mixed_owned_foreign_pid(self):
        worker = self.worker('import time; time.sleep(10)')
        self.rejected(worker,[worker.pid,os.getpid()])

    def test_prelaunch_empty_ownership(self):
        self.assertEqual(self.call(phase='prelaunch'),37)
        self.rejected(phase='prelaunch')

    def fake_class(self, role='task', outcome='success', mode='normal'):
        reading, sup = self.reading, self.sup
        import types
        import time
        class Fake:
            def __init__(self):
                self.owner = types.SimpleNamespace(errors=[], groups={})
                self.accepted_initial=False; self.last_sample=None
                self.ready = {'work':{},'sample':{}}
                self.requests = {'work':None,'sample':None}
                self.ticks = []
                self.events = []
                self.setup_deadline = self.cleanup_deadline = time.monotonic()+3
                self.calls = 0
                self.selected = False
                self.closed = False
            def install_progress(self,reference,deadline): self.progress_context=reference
            def resume(self): self.ticks.append(time.monotonic())
            def set_worker(self,worker): self.worker=worker
            def retire_worker(self): self.worker=None
            def admission_guard(self):
                if not self.accepted_initial or time.monotonic()>=self.setup_deadline: raise ValueError('fixture admission unavailable')
            def await_ready(self): return self
            def submit(self, which, operation, deadline):
                self.requests[which] = dict(value=operation['args']['value'], dispatch=time.monotonic())
            def tick(self, deadline):
                if time.monotonic() >= deadline: raise TimeoutError('fixture deadline')
                result=[]
                self.owner.groups = {pid:sup.group_processes(pid,include_zombies=True) for pid in reading['gpu_pids']}
                for which in ('sample','work'):
                    request=self.requests[which]
                    if request is None: continue
                    selected = which == ('sample' if role == 'sample' else 'work')
                    self.selected |= selected
                    if selected and outcome == 'error': raise ValueError('primary fixture error')
                    if selected and outcome == 'timeout': continue
                    self.requests[which]=None
                    result.append((which,request['value'],time.monotonic(),request['dispatch']))
                return result
            def ownership(self):
                return [] if self.closed else [dict(pid=987654321,phase='fixture')]
            def close(self, deadline):
                self.calls += 1
                if self.selected:
                    if mode == 'false' or (mode=='false_then_reaped' and self.calls==1): return False
                    if mode.endswith('exception'): raise OSError(mode)
                self.closed=True
                return True
        return Fake

    def test_cleanup_matrix(self):
        from unittest.mock import patch
        for case in SUBTEST_CASES[f"{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}"]:
            with self.subTest(**case):
                self.life = self.sup.HelperLifecycle()
                start = self.time.monotonic()
                with patch.object(self.sup,'Session',self.fake_class(**case)):
                    if case['outcome']=='success':
                        self.assertEqual(self.call(seconds=.12),37)
                    else:
                        expected = ValueError if case['outcome']=='error' else TimeoutError
                        with self.assertRaises(expected): self.call(seconds=.12)
                self.assertEqual(self.life.helpers,[])
                self.assertLess(self.time.monotonic()-start,.25)

    def test_cleanup_failures(self):
        from unittest.mock import patch
        for case in SUBTEST_CASES[f"{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}"]:
            with self.subTest(**case):
                self.life = self.sup.HelperLifecycle()
                with patch.object(self.sup,'Session',self.fake_class(mode=case['mode'])):
                    if case['mode']=='false_then_reaped':
                        self.assertEqual(self.call(seconds=.12),37)
                        self.assertEqual(self.life.helpers,[])
                    else:
                        with self.assertRaises(self.sup.HelperCleanupFailure): self.call(seconds=.12)
                        self.assertTrue(self.life.helpers)
                        if case['mode'].endswith('exception'):
                            self.assertEqual(self.life.errors[0]['error_class'],'OSError')
                        with patch.object(self.life.helpers[0],'close',return_value=True):
                            self.assertTrue(self.life.reap(self.time.monotonic()+.1))

    def test_primary_survives_secondary_cleanup_error(self):
        from unittest.mock import patch
        with patch.object(self.sup,'Session',self.fake_class(outcome='error',mode='close_exception')):
            with self.assertRaisesRegex(ValueError,'primary fixture error') as caught:
                self.call(seconds=.12)
        self.assertTrue(caught.exception.cleanup_uncertain)
        self.assertEqual(caught.exception.helper_cleanup_errors[0]['message'],'close_exception')
        self.assertTrue(self.life.helpers)

    def test_real_close_repeated_and_descendant_cleanup(self):
        # A real group with a descendant exercises enumeration and group termination.
        process = self.worker('import subprocess,sys,time; subprocess.Popen([sys.executable,"-c","import time; time.sleep(10)"]); time.sleep(10)')
        limit = self.time.monotonic()+2
        while len(self.sup.group_processes(process.pid))<2 and self.time.monotonic()<limit:
            self.time.sleep(.005)
        self.assertGreaterEqual(len(self.sup.group_processes(process.pid)),2)
        self.assertEqual(self.sup.stop_group(process,limit),[])
        helper = self.life.acquire()
        helper.await_ready()
        self.assertTrue(self.life.reap(self.time.monotonic()+2))
        self.assertTrue(helper.close(self.time.monotonic()+1))
        self.assertTrue(helper.close(self.time.monotonic()+1))

    def test_supervisor_worker_context_and_consumed_cleanup_stop(self):
        from unittest.mock import patch
        import json
        from test_vipe_benchmark_s1_recovery import S1RecoveryTests
        from vipe_benchmark.s1_clock import ReservationClock
        with tempfile.TemporaryDirectory() as temp:
            fixture=S1RecoveryTests(); fixture.setUp(); self.addCleanup(fixture.doCleanups)
            root=fixture.root
            _,request,evidence=fixture.register()
            command=fixture.command(evidence)
            events = []
            captured=[]; transported=[]
            class Disposable:
                path = root/'ledger.jsonl'
                jobs = {'S1-calibration-recovery-001':dict(resource='gpu')}
                config = self.config
                def reserve(inner,*args,**kwargs):
                    events.append('reserve')
                    kwargs['seconds_limit']=.6
                    actual=fixture.ledger.reserve(*args,**kwargs)
                    captured.append(actual)
                    return actual
                def note(inner,*args,**kwargs): pass
                def finish(inner,job,status,elapsed,**evidence):
                    events.append(dict(status=status,**evidence))
            actual = self.sup.monitored_call
            peaks=[]
            def monitor(function,deadline,sampler,config,peak,**kwargs):
                peaks.append(peak)
                if kwargs['phase']=='initial_sample':
                    helper=self.fake_class(mode='false')(); helper.accepted_initial=True
                    kwargs['lifecycle'].helpers=[helper]
                    return self.reading
                if kwargs['phase']=='worker_sample':
                    self.assertIsNotNone(kwargs['worker'])
                    self.reading['gpu_pids']=[kwargs['worker'].pid]
                    with patch.object(self.sup,'Session',self.fake_class(mode='false')):
                        return actual(self.operation,deadline,self.sampler,config,peak,**kwargs)
                return None
            popen=self.sup.subprocess.Popen
            def worker(argv,**kwargs):
                self.assertEqual(argv,command)
                value=json.loads(kwargs['env']['VIPE_S1_RESERVATION_CLOCK'])
                ReservationClock.from_reservation(captured[0]).match(value)
                self.assertTrue(all(kwargs['env'][key]=='1' for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')))
                transported.append(value)
                return popen([sys.executable,'-c','import time; time.sleep(10)'],**kwargs)
            with patch.object(self.sup,'monitored_call',side_effect=monitor), patch.object(self.sup.subprocess,'Popen',side_effect=worker):
                with self.assertRaises(self.sup.SupervisionFailure) as caught:
                    self.sup.supervise(Disposable(),'S1-calibration-recovery-001',
                        command,root/'jobs'/'S1-calibration-recovery-001',evidence=evidence,
                        sample_resources=self.sampler,terminal_publisher=True,terminal_docs=root)
            self.assertEqual(len(transported),1)
            self.assertEqual(events[0],'reserve')
            self.assertEqual(events[-1]['status'],'failed')
            self.assertFalse(events[-1]['cleanup_confirmed'])
            self.assertTrue(events[-1]['cleanup_uncertain'])
            self.assertTrue(events[-1]['stop_required'])
            self.assertEqual(events[-1]['surviving_pids'],[])
            self.assertTrue(events[-1]['helper_ownership'])
            self.assertTrue(all(p is peaks[0] for p in peaks))
            self.assertTrue(caught.exception.stop_required)



class HelperSessionTests(unittest.TestCase):
    """Twenty-four serial real-child scenarios; pure mutations add no children."""
    def setUp(self):
        import time
        self.time = time
        self.reading = dict(device_bytes=0, artifact_bytes=0, download_bytes=0, gpu_pids=[])
        self.sampler = dict(operation='constant', args=dict(value=self.reading))
        self.operation = dict(operation='constant', args=dict(value=37))

    def scenario(self, label, mode='normal', **bounds):
        from test_vipe_benchmark_s1_helper_fixtures import session
        from vipe_benchmark.s1_helper_session import census
        import json
        import contextlib
        @contextlib.contextmanager
        def owned():
            from vipe_benchmark.s1_helper_session import Session,Trace
            from dataclasses import asdict, is_dataclass
            started=self.time.monotonic(); action_cutoff=started+2.; safety_cutoff=started+3.
            current=Session.__new__(Session)
            record=dict(scenario=label,mode=mode,constructor_entry=started,action_cutoff=action_cutoff,safety_cutoff=safety_cutoff)
            try:
                session(mode,instance=current,**bounds)
                current.fixture_action_end=action_cutoff; current.fixture_safety_end=safety_cutoff
                observed_calls=Trace(128)
                def observe_call(name,operation):
                    def observed(*args,**kwargs):
                        deadline=args[0] if name in ('tick','close') else current.ready_deadline
                        effective=min(deadline,safety_cutoff if name=='close' else action_cutoff)
                        if name=='tick' and current.requests['sample'] is not None:
                            effective=min(effective,current.requests['sample']['deadline'])
                        entered=self.time.monotonic();result=None;error=None
                        try:
                            result=operation(*args,**kwargs);return result
                        except BaseException as exc:
                            error=type(exc).__name__+': '+str(exc);raise
                        finally:
                            returned=self.time.monotonic()
                            observed_calls.append(dict(operation=name,entered=entered,deadline=effective,returned=returned,
                                confirmed=result if name=='close' else None,error=error))
                            self.assertLessEqual(returned,effective+.1)
                    return observed
                current.tick=observe_call('tick',current.tick)
                current.close=observe_call('close',current.close)
                current.await_ready=observe_call('await_ready',current.await_ready)
                record.update(constructor_end=self.time.monotonic(),t0=current.t0,
                    ready_deadline=current.ready_deadline,setup_deadline=current.setup_deadline,setup_cleanup_deadline=current.cleanup_deadline)
                yield current
            finally:
                action_end=self.time.monotonic()
                if current.owner is not None: current.owner.released=True
                cleaned=current.close(safety_cutoff)
                ended=self.time.monotonic()
                owner=current.owner
                record.update(action_end=action_end,end=ended,execution_seconds=action_end-started,
                    cleanup_seconds=ended-action_end,cleanup_confirmed=cleaned,
                    records={} if owner is None else owner.records,errors=[] if owner is None else list(owner.errors),
                    signals=[] if owner is None else list(owner.signals),ticks=list(current.ticks),events=list(current.events),
                    trace_facts=current.events.facts(),tick_facts=current.ticks.facts(),
                    owner_error_facts=None if owner is None else owner.errors.facts(),owner_signal_facts=None if owner is None else owner.signals.facts(),
                    request_counts={role:dict(dispatch=current.dispatch_counts[role].value,response=current.response_counts[role].value) for role in current.requests},
                    census_request_count=current.census_requests.value,max_gap=current.max_gap,max_turn=current.max_turn,
                    call_observations=list(observed_calls),call_observation_facts=observed_calls.facts(),
                    last_sample=current.last_sample,requests=current.requests,
                    ownership=current.ownership(),wire={role:dict(sent=w.sent_bytes,received=w.received_bytes,blocked_writes=w.blocked_writes,peek=w.peek_bytes.value,combined=w.combined_bytes.value,last_frame=w.last_frame) for role,w in current.wires.items()})
                directory=Path(os.environ['S1_VALIDATION_RUN_DIRECTORY'])
                with (directory/('scenario-'+label+'.json')).open('x') as stream:
                    json.dump(record,stream,indent=2,default=lambda v:asdict(v) if is_dataclass(v) else list(v)); stream.write('\n')
                self.assertTrue(cleaned,record)
                self.assertLessEqual(action_end-started,2)
                self.assertLessEqual(ended-action_end,1)
                self.assertLessEqual(ended-started,3)
        return owned()

    def work(self, session, operation=None, sampler=None, seconds=1.5):
        from vipe_benchmark import supervisor as sup
        life=sup.HelperLifecycle(retain=True)
        life.helpers=[session]
        return sup.monitored_call(operation or self.operation,min(session.fixture_action_end,self.time.monotonic()+seconds),
            sampler or self.sampler,load(),{},lifecycle=life)

    def reject_ready(self, label, mode):
        with self.scenario(label,mode,ready_seconds=.08,setup_seconds=.18,total_seconds=.3) as session:
            with self.assertRaises((ValueError,RuntimeError,TimeoutError,EOFError)):
                session.await_ready()
            self.assertFalse(len(session.ready)==2)
            self.assertTrue(session.close(session.cleanup_deadline))
            self.assertLessEqual(max(b-a for a,b in zip(session.ticks,session.ticks[1:])),.1)

    def record_census(self, session, extra=()):
        from vipe_benchmark.s1_helper_session import owned_workload
        if not hasattr(session,'owned_retained'):session.owned_retained={}
        observed=owned_workload(os.environ['S1_OWNED_ROOT_NOTE'],extra=extra,retained=session.owned_retained)
        threads=observed['process_threads'][os.getpid()]
        session.events.append(dict(event='census',controller_threads=threads,
            opencv_threads=os.environ.get('OPENCV_FOR_THREADS_NUM'),**observed))
        return observed['total_workers'],threads

    def test_l01_ready_reuse(self):
        from vipe_benchmark.s1_helper_session import census, THREADS
        with self.scenario('L01') as session:
            session.await_ready()
            identities=dict(session.ready)
            self.assertEqual(self.work(session),37)
            self.assertEqual(self.work(session),37)
            self.assertEqual(session.ready,identities)
            self.assertEqual(len(session.owner.records),2)
            for row in identities.values():
                self.assertEqual(row['threads'],{key:'1' for key in THREADS})
            count,threads=self.record_census(session)
            self.assertLessEqual(count,8)
            self.assertEqual(threads,2)
            session.submit('work',self.operation,self.time.monotonic()+.2)
            with self.assertRaisesRegex(ValueError,'busy'): session.submit('work',self.operation,self.time.monotonic()+.2)
            session.submit('sample',self.sampler,self.time.monotonic()+.2)
            with self.assertRaisesRegex(ValueError,'busy'): session.submit('sample',self.sampler,self.time.monotonic()+.2)

    def test_l02_ready_and_sample_before_reserve(self):
        from vipe_benchmark import supervisor as sup
        with self.scenario('L02') as session:
            life=sup.HelperLifecycle(retain=True); life.helpers=[session]
            value=sup.monitored_call(self.sampler,session.setup_deadline,self.sampler,load(),{},lifecycle=life,phase='initial_sample')
            self.assertEqual(value,self.reading)
            reserve_observed=self.time.monotonic()
            self.assertEqual(len(session.ready),2)
            samples=[e for e in session.events if e['event']=='response']
            self.assertEqual(len(samples),1)
            self.assertLess(samples[0]['received'],reserve_observed)
            self.assertLess(reserve_observed,session.setup_deadline)
            session.events.append(dict(event='disposable_reserve_boundary',monotonic=reserve_observed))
            with tempfile.TemporaryDirectory() as temp:
                class Disposable:
                    path=Path(temp)/'ledger.jsonl'
                    config=load()
                    jobs={'S1-calibration-recovery-001':dict(resource='gpu')}
                    def reserve(inner,*args,**kwargs):
                        self.assertEqual(len(session.ready),2)
                        self.assertTrue(any(e['event']=='response' and e['role']=='sample' for e in session.events))
                        session.events.append(dict(event='actual_disposable_reserve_call',monotonic=self.time.monotonic()))
                        raise RuntimeError('stop at instrumented disposable reserve')
                with patch.object(sup,'HelperLifecycle',return_value=life):
                    with self.assertRaisesRegex(RuntimeError,'instrumented disposable reserve'):
                        sup.supervise(Disposable(),'S1-calibration-recovery-001',['unused'],Path(temp)/'out',evidence={},sample_resources=self.sampler)
                self.assertEqual(len([e for e in session.events if e['event']=='actual_disposable_reserve_call']),1)
                self.assertEqual(len(session.owner.records),2)


    def test_l03_owner_bootstrap_block(self): self.reject_ready('L03','owner_block')
    def test_l04_child_before_ready_block(self): self.reject_ready('L04','child_block')
    def test_l05_error_after_spawn(self): self.reject_ready('L05','identity_failure')
    def test_l06_late_ready(self): self.reject_ready('L06','late_ready')
    def test_l07_cancel_during_spawn(self): self.reject_ready('L07','held_spawn')

    def test_l08_late_owner_retained(self):
        from vipe_benchmark.s1_helper_session import OWNERS
        with self.scenario('L08','late_spawn',ready_seconds=.06,setup_seconds=.12,total_seconds=.2) as session:
            with self.assertRaises(TimeoutError): session.await_ready()
            self.assertFalse(session.close(session.cleanup_deadline))
            self.assertIn(session.owner,OWNERS)
            self.assertTrue(session.ownership()[0]['ownership_unknown'])
            session.events.append(dict(event='cleanup_uncertain_at_deadline',monotonic=self.time.monotonic(),ownership=session.ownership()))
            self.assertTrue(session.close(self.time.monotonic()+.7))
            self.assertEqual(session.owner.records['sample']['state'],'pending')
            self.assertNotIn(session.owner,OWNERS)
            with self.assertRaises(ValueError): session.submit('work',self.operation,self.time.monotonic()+.1)

    def test_l09_partial_header(self): self.reject_ready('L09','partial_header')
    def test_l10_stalled_body(self): self.reject_ready('L10','stalled_body')
    def test_l11_eof_midframe(self): self.reject_ready('L11','eof_frame')

    def test_l12_stalled_request_reader(self):
        import socket
        with self.scenario('L12','stalled_reader') as session:
            session.await_ready()
            session.wires['work'].channel.setsockopt(socket.SOL_SOCKET,socket.SO_SNDBUF,1024)
            operation=dict(operation='constant',args=dict(value=['x'*1900]*32))
            deadline=self.time.monotonic()+.15
            session.submit('work',operation,deadline)
            with self.assertRaises(TimeoutError):
                while True:
                    session.tick(deadline); self.time.sleep(.005)
            self.assertTrue(session.wires['work'].out)
            self.assertGreater(session.wires['work'].blocked_writes,0)

    def test_l13_oversized_frame(self): self.reject_ready('L13','oversized')
    def test_l14_wrong_correlation(self): self.reject_ready('L14','wrong_role')

    def test_l15_sample_deadline(self):
        with self.scenario('L15','sample_late') as session:
            session.await_ready()
            with self.assertRaises(TimeoutError): self.work(session,seconds=1.2)
            self.assertFalse(any(e['event']=='response' and e['role']=='sample' for e in session.events))

    def test_l16_phase_deadline(self):
        with self.scenario('L16','phase_late') as session:
            session.await_ready()
            with self.assertRaises(TimeoutError): self.work(session,seconds=.12)

    def test_l17_post_task_acquisition(self):
        with self.scenario('L17','post_task') as session:
            session.await_ready()
            self.reading.update(acquisition_start=-100,acquisition_end=1e99)
            self.assertEqual(self.work(session),37)
            responses=[e for e in session.events if e['event']=='response']
            finish=next(e['received'] for e in responses if e['role']=='work')
            samples=[e for e in responses if e['role']=='sample']
            self.assertTrue(any(e['dispatch'] < finish for e in samples))
            self.assertGreaterEqual(samples[-1]['dispatch'],finish)
            self.assertGreaterEqual(samples[-1]['acquisition_start'],samples[-1]['dispatch'])
            self.assertLessEqual(samples[-1]['acquisition_end'],samples[-1]['received'])

    def test_l18_descendant_and_foreign_sentinel(self):
        import signal
        from vipe_benchmark.s1_helper_session import census
        with self.scenario('L18','descendant') as session:
            session.await_ready()
            sentinel=os.posix_spawn(sys.executable,[sys.executable,'-B','-c','import time; time.sleep(10)'],os.environ,setsid=True)
            try:
                deadline=self.time.monotonic()+.2
                while len(session.owner.members)<3 and self.time.monotonic()<deadline: self.time.sleep(.005)
                self.assertGreaterEqual(len(session.owner.members),3)
                count,_=self.record_census(session,extra=(sentinel,))
                self.assertLessEqual(count,8)
                self.assertTrue(session.close(self.time.monotonic()+.4))
                self.assertNotIn(sentinel,[e['pid'] for e in session.owner.signals])
                os.kill(sentinel,0)
                session.events.append(dict(event='foreign_sentinel_survived',pid=sentinel))
            finally:
                os.killpg(sentinel,signal.SIGKILL)
                limit=self.time.monotonic()+.3
                while self.time.monotonic()<limit:
                    if os.waitpid(sentinel,os.WNOHANG)[0]: break
                    self.time.sleep(.005)
                else: self.fail('sentinel reap deadline')

    def test_l19_term_resistance(self):
        import signal
        with self.scenario('L19','ignore_term') as session:
            session.await_ready()
            self.assertTrue(session.close(self.time.monotonic()+.5))
            self.assertIn(int(signal.SIGKILL),[e['signal'] for e in session.owner.signals])

    def test_l20_exit_during_transport(self):
        from vipe_benchmark.supervisor import HelperFailure
        with self.scenario('L20','exit_transport') as session:
            session.await_ready()
            with self.assertRaises(HelperFailure) as caught: self.work(session)
            self.assertEqual(caught.exception.failure['phase'],'transport')

    def failed_cleanup(self,label,mode):
        with self.scenario(label,mode) as session:
            session.await_ready()
            self.assertFalse(session.close(self.time.monotonic()+.12))
            self.assertTrue(session.ownership())
            self.assertTrue(session.owner.errors)
            session.events.append(dict(event='cleanup_uncertain_injected',ownership=session.ownership(),errors=list(session.owner.errors)))
            session.owner.released=True
            self.assertTrue(session.close(self.time.monotonic()+.4))
            self.assertTrue(session.owner.errors)

    def test_l21_enumeration_failure(self): self.failed_cleanup('L21','enumeration_failure')
    def test_l22_signal_failure(self): self.failed_cleanup('L22','signal_failure')
    def test_l23_reap_failure(self): self.failed_cleanup('L23','reap_failure')

    def test_l24_summary_reference_adapter(self):
        with tempfile.TemporaryDirectory() as temp:
            local=Path(temp); (local/'jobs'/'S1-calibration-recovery-001').mkdir(parents=True)
            with self.scenario('L24','artifact') as session:
                session.await_ready()
                operation=dict(operation='constant',args=dict(value=dict(local=str(local))))
                result=self.work(session,operation=operation)
                self.assertEqual(result['rejected'],['session','reservation','missing','tamper'])
                self.assertEqual(result['counts'],dict(complete=510))
                self.assertEqual(result['identities'],510)
                self.assertEqual(result['reference']['session'],session.token)

    def sample(self, session, *, worker=None, seconds=.5):
        from vipe_benchmark import supervisor as sup
        life=sup.HelperLifecycle(retain=True); life.helpers=[session]
        return sup.monitored_call(self.sampler,min(session.fixture_action_end,self.time.monotonic()+seconds),
            self.sampler,load(),{},worker=worker,lifecycle=life,phase='worker_sample')

    def admission_rejected(self,label,equality):
        from vipe_benchmark import supervisor as sup
        with self.scenario(label,ready_seconds=.15,setup_seconds=.3,total_seconds=.5) as session:
            life=sup.HelperLifecycle(retain=True);life.helpers=[session]
            calls=[]
            with tempfile.TemporaryDirectory() as temp:
                class Disposable:
                    jobs={'S1-calibration-recovery-001':dict(resource='gpu')}
                    config=load()
                    @property
                    def reserve(inner):
                        self.assertTrue(session.accepted_initial)
                        self.assertIsNotNone(session.last_sample)
                        if equality: session.decision_clock=lambda:session.setup_deadline
                        else:
                            self.time.sleep(max(0.,session.setup_deadline-self.time.monotonic()+.005))
                        return lambda *a,**kw:calls.append('reserve')
                with patch.object(sup,'HelperLifecycle',return_value=life):
                    with self.assertRaisesRegex(TimeoutError,'setup admission deadline'):
                        sup.supervise(Disposable(),'S1-calibration-recovery-001',['unused'],Path(temp)/'out',evidence={},sample_resources=self.sampler)
                returned=self.time.monotonic()
                session.events.append(dict(event='rejected_admission',decision=session.decision_clock(),deadline=session.setup_deadline,returned=returned,calls=list(calls)))
                self.assertEqual(calls,[])
                self.assertLessEqual(returned,session.cleanup_deadline+.1)
                self.assertTrue(session.closed)

    def test_l25_delayed_actual_reserve(self): self.admission_rejected('L25',False)
    def test_l26_equal_actual_reserve(self): self.admission_rejected('L26',True)

    def early_response(self,label,mode):
        import socket
        with tempfile.TemporaryDirectory() as temp:
            barrier=Path(temp)/'release'
            with patch.dict(os.environ,S1_EARLY_BARRIER=str(barrier)),self.scenario(label,mode) as session:
                session.await_ready(); wire=session.wires['work']
                wire.channel.setsockopt(socket.SOL_SOCKET,socket.SO_SNDBUF,1024)
                operation=dict(operation='constant',args=dict(value=['x'*1900]*32))
                end=min(session.fixture_action_end,self.time.monotonic()+.3)
                session.submit('work',operation,end)
                if mode=='early_partial':
                    while not wire.blocked_writes and self.time.monotonic()<end:
                        session.tick(end);self.time.sleep(.001)
                    self.assertTrue(wire.out);self.assertGreater(wire.sent_bytes,0)
                else: self.assertIsNotNone(wire.encoder)
                before=dict(encoder=wire.encoder is not None,out_bytes=len(wire.out),sent=wire.sent_bytes)
                barrier.write_text('release')
                while not barrier.with_suffix('.sent').exists() and self.time.monotonic()<end: self.time.sleep(.001)
                self.assertTrue(barrier.with_suffix('.sent').exists())
                with self.assertRaisesRegex(ValueError,'premature helper response'):
                    session.tick(end)
                request=session.requests['work']
                self.assertEqual(request['early_bytes'],1)
                self.assertNotIn('transmitted_observed',request)
                session.events.append(dict(event='early_response_rejected',before=before,request_id=request['id'],early_observed=request['early_observed']))

    def test_l27_encoder_early_response(self): self.early_response('L27','early_encoder')
    def test_l28_partial_early_response(self): self.early_response('L28','early_partial')

    def readable_equal(self,label,seconds):
        with self.scenario(label) as session:
            session.await_ready()
            end=min(session.fixture_action_end,self.time.monotonic()+seconds)
            session.submit('sample',self.sampler,end)
            request=session.requests['sample']; observed=[]
            def decision():
                snap=session.owner.census_reply
                if request.get('stage')=='post' and snap is not None:
                    observed.append(dict(decision=request['deadline'],real=self.time.monotonic(),frame=dict(session.wires['sample'].last_frame),
                        dispatch=request['dispatch'],deadline=request['deadline'],payload=request['candidate'],pre=request['pre'],post=snap))
                    return request['deadline']
                return self.time.monotonic()
            session.decision_clock=decision
            with self.assertRaisesRegex(TimeoutError,'sample timeout at census decision'):
                while self.time.monotonic()<end:
                    session.tick(end);self.time.sleep(.001)
            self.assertEqual(len(observed),1)
            self.assertGreater(observed[0]['frame']['bytes'],4)
            self.assertEqual(observed[0]['decision'],request['deadline'])
            self.assertLess(observed[0]['payload']['acquisition_end'],observed[0]['real'])
            self.assertLess(observed[0]['pre'].generation,observed[0]['post'].generation)
            self.assertIsNone(session.last_sample)
            self.assertFalse(any(e['event']=='response' and e['role']=='sample' for e in session.events))
            self.assertLessEqual(session.max_gap,.1)
            session.events.append(dict(event='readable_deadline_equality',observation=observed[0]))

    def test_l29_readable_sample_equality(self): self.readable_equal('L29',1.2)
    def test_l30_readable_phase_equality(self): self.readable_equal('L30',.2)

    def scenario_worker(self,session,code):
        import contextlib
        from vipe_benchmark import supervisor as sup
        @contextlib.contextmanager
        def managed():
            worker=subprocess.Popen([sys.executable,'-B','-c',code],start_new_session=True,env=dict(os.environ,OPENCV_FOR_THREADS_NUM='1'))
            try: yield worker
            finally:
                try: session.retire_worker()
                finally: self.assertEqual(sup.stop_group(worker,session.fixture_action_end),[])
        return managed()

    def test_l31_live_worker_bracket_and_foreign(self):
        from vipe_benchmark.supervisor import HelperFailure
        with self.scenario('L31') as session:
            session.await_ready()
            with self.scenario_worker(session,'import time; time.sleep(10)') as worker:
                self.reading['gpu_pids']=[worker.pid]
                self.assertEqual(self.sample(session,worker=worker),self.reading)
                before=session.last_sample
                self.assertEqual(before['pre'].worker.pid,worker.pid)
                self.assertEqual(before['pre'].worker.start_ticks,before['post'].worker.start_ticks)
                count,_=self.record_census(session,extra=(worker.pid,));self.assertLessEqual(count,8)
                self.reading['gpu_pids']=[worker.pid,os.getpid()]
                with self.assertRaises(HelperFailure) as caught: self.sample(session,worker=worker)
                self.assertEqual(caught.exception.failure['error_class'],'GPUOwnershipError')
                self.assertEqual(before['pre'].worker.pid,worker.pid)

    def test_l32_unreaped_worker_pin(self):
        with self.scenario('L32') as session:
            session.await_ready()
            with self.scenario_worker(session,'pass') as worker:
                end=min(session.fixture_action_end,self.time.monotonic()+.2)
                while os.waitid(os.P_PID,worker.pid,os.WEXITED|os.WNOHANG|os.WNOWAIT) is None and self.time.monotonic()<end: self.time.sleep(.001)
                self.reading['gpu_pids']=[worker.pid]
                self.assertEqual(self.sample(session,worker=worker),self.reading)
                self.assertIsNone(worker.returncode)
                self.assertEqual(session.worker_exit(),0)
                self.assertEqual(session.last_sample['post'].worker.state,'Z')
                self.assertTrue(Path('/proc',str(worker.pid)).exists())

    def test_l33_blocked_census_refuses_stale(self):
        with self.scenario('L33','census_block') as session:
            session.await_ready()
            with self.scenario_worker(session,'import time; time.sleep(10)') as worker:
                self.assertEqual(self.sample(session,worker=worker),self.reading)
                previous=session.last_sample
                session.owner.armed=True
                started=self.time.monotonic(); deadline=started+.12
                with self.assertRaises(TimeoutError) as caught: self.sample(session,worker=worker,seconds=.12)
                returned=self.time.monotonic()
                self.assertTrue(getattr(session.owner,'block_entered',None))
                self.assertEqual(session.last_sample,previous)
                self.assertTrue(caught.exception.cleanup_uncertain)
                self.assertFalse(session.closed)
                self.assertLessEqual(returned,deadline+.1)
                self.assertLessEqual(session.max_gap,.1)
                session.events.append(dict(event='blocked_census_production_return',deadline=deadline,returned=returned,cleanup_uncertain=True))
                session.owner.released=True
                # Do not change worker authority while the failed request remains outstanding.
                session.requests['sample']=None

    def test_l34_enumeration_error_empty_sample(self):
        with self.scenario('L34','census_error') as session:
            session.await_ready();session.owner.armed=True
            with self.assertRaisesRegex((RuntimeError,ValueError),'enumeration|census'):
                self.sample(session,seconds=.15)
            self.assertIsNone(session.last_sample)
            self.assertEqual(self.reading['gpu_pids'],[])
            self.assertTrue(session.owner.errors)
            session.owner.released=True

    def test_l35_exited_leader_live_descendant(self):
        with self.scenario('L35') as session, tempfile.TemporaryDirectory() as temp:
            session.await_ready()
            marker=Path(temp)/'ready';release=Path(temp)/'release'
            code=f'import subprocess,sys,time;from pathlib import Path;p=subprocess.Popen([sys.executable,"-B","-c","import time; time.sleep(10)"]);Path({str(marker)!r}).write_text(str(p.pid));end=time.monotonic()+1;exec("while not Path({str(release)!r}).exists() and time.monotonic()<end:time.sleep(.001)")'
            with self.scenario_worker(session,code) as worker:
                while not marker.exists() and self.time.monotonic()<session.fixture_action_end:self.time.sleep(.001)
                self.record_census(session,extra=(worker.pid,int(marker.read_text())))
                release.write_text('creation ancestry retained')
                end=min(session.fixture_action_end,self.time.monotonic()+.3)
                while os.waitid(os.P_PID,worker.pid,os.WEXITED|os.WNOHANG|os.WNOWAIT) is None and self.time.monotonic()<end:self.time.sleep(.001)
                self.assertEqual(self.sample(session,worker=worker),self.reading)
                rows=session.last_sample['post'].rows
                self.assertGreaterEqual(len(rows),2)
                count,_=self.record_census(session,extra=tuple(r.pid for r in rows));self.assertLessEqual(count,8)
                with self.assertRaisesRegex(RuntimeError,'live child'):session.worker_exit()
                self.assertIsNone(worker.returncode)

    def test_l36_ambiguous_native_start_retained(self):
        import _thread
        from vipe_benchmark.s1_helper_session import Session,OWNERS
        original=_thread.start_joinable_thread; handles=[];acquired=[]
        def ambiguous(*args,**kwargs):
            handles.append(original(*args,**kwargs))
            owner=args[0].__self__;limit=started+.15
            while not any(r.get('pid') for r in owner.records.values()) and self.time.monotonic()<limit:self.time.sleep(.001)
            acquired.extend(dict(r) for r in owner.records.values() if r.get('pid'))
            raise RuntimeError('ambiguous native creation after start')
        started=self.time.monotonic();action_end=started+2;safety_end=started+3
        session=Session.__new__(Session)
        try:
            with patch.object(_thread,'start_joinable_thread',side_effect=ambiguous):
                with self.assertRaisesRegex(RuntimeError,'ambiguous native creation'):
                    session.__init__(ready_seconds=.05,setup_seconds=.1,total_seconds=.2)
            session.fixture_action_end=action_end;session.fixture_safety_end=safety_end
            self.assertTrue(acquired)
            self.assertEqual(session.state,'launch_unknown')
            self.assertFalse(session.close(session.cleanup_deadline))
            returned=self.time.monotonic()
            self.assertLessEqual(returned,session.cleanup_deadline+.1)
            self.assertTrue(session.ownership()[0]['ownership_unknown'])
            self.assertIn(session.owner,OWNERS)
            production=dict(deadline=session.cleanup_deadline,returned=returned,state=session.state,ownership=session.ownership(),primary=session.primary,actually_acquired=acquired)
        finally:
            session.handle=handles[0];session.owner.handle=handles[0]
            cleaned=session.close(safety_end)
            ended=self.time.monotonic()
            import json
            record=dict(scenario='L36',constructor_entry=started,action_cutoff=action_end,safety_cutoff=safety_end,
                production=production,cleanup_confirmed=cleaned,execution_seconds=returned-started,cleanup_seconds=ended-returned,end=ended,
                ownership=session.ownership(),records=session.owner.records,events=list(session.events),ticks=list(session.ticks),errors=list(session.owner.errors))
            with (Path(os.environ['S1_VALIDATION_RUN_DIRECTORY'])/'scenario-L36.json').open('x') as stream:json.dump(record,stream,indent=2)
            self.assertTrue(cleaned);self.assertLessEqual(ended-started,3);self.assertLessEqual(ended-returned,1)
            self.assertNotIn(session.owner,OWNERS)

    def progress_scenario(self,label,mode,*,supervised=True):
        import json,shutil
        from vipe_benchmark import supervisor as sup,s1_progress as p
        from vipe_benchmark.files import write_json,file_record
        from vipe_benchmark.s1_clock import ReservationClock
        from test_vipe_benchmark_s1_helper_fixtures import progress_fixture,progress_reservation
        with self.scenario(label,mode) as session, tempfile.TemporaryDirectory() as temp:
            session.await_ready()
            root=Path(temp);fixture=progress_fixture(root/'fixture',states=label=='P04')
            write_json(root/'progress-fixture.json',fixture)
            marker=root/'sample-fail'
            life=sup.HelperLifecycle(retain=True);life.helpers=[session]
            session.resume();self.assertLessEqual(self.record_census(session)[0],8)
            pair={k:p.process_binding(v) for k,v in session.owner.records.items()}
            outcome={};caught=None;observed=[];consumer=None
            if label=='P06':
                install=session.install_progress
                def install_held(*args,**kwargs):
                    result=install(*args,**kwargs)
                    consumer=session.owner.progress_consumer;original_read=consumer.read
                    def held(rec,limit=p.CHECKPOINT_BYTES):
                        if rec['path'].endswith('/0002.json') and not session.owner.released:
                            session.owner.progress_block_entered=self.time.monotonic()
                            while not session.owner.released:self.time.sleep(.001)
                        return original_read(rec,limit)
                    consumer.read=held
                    return result
                session.install_progress=install_held
            try:
                if supervised:
                    class Disposable:
                        path=root/'ledger.jsonl';config=load();jobs={'S1-calibration-recovery-001':dict(resource='gpu')}
                        def reserve(inner,job,command,evidence,**kwargs):
                            reservation=progress_reservation(fixture,1.4);reservation['command']=command
                            observed.append(reservation);return reservation
                        def note(inner,*a,**k):pass
                        def finish(inner,job,status,elapsed,**evidence):outcome.update(status=status,elapsed=elapsed,**evidence)
                    if label=='P01':
                        command=[sys.executable,'-B','-c',"import sys;sys.path.insert(0,'tests');from test_vipe_benchmark_s1_helper_fixtures import progress_worker;progress_worker(sys.argv[1],sys.argv[2])",str(root/'progress-fixture.json'),str(root/'jobs'/'S1-calibration-recovery-001')]
                    else:command=[sys.executable,'-B','-c','pass']
                    # Helpers are already running; give the sample fixture its
                    # path through the existing operation payload, no extra process.
                    sampler=dict(operation='constant',args=dict(value=dict(self.reading,progress_fail_marker=str(marker))))
                    original=sup.monitored_call
                    def monitored(*args,**kwargs):
                        result=original(*args,**kwargs)
                        if kwargs.get('worker') is not None:self.assertLessEqual(self.record_census(session,[kwargs['worker'].pid])[0],8)
                        return result
                    with patch.object(sup,'HelperLifecycle',return_value=life),patch.object(sup,'monitored_call',side_effect=monitored):
                        try:sup.supervise(Disposable(),'S1-calibration-recovery-001',command,root/'jobs'/'S1-calibration-recovery-001',
                            evidence={},sample_resources=sampler,validate_result=lambda _:None,terminal_publisher=True,terminal_docs=root)
                        except sup.SupervisionFailure as exc:caught=exc
                    self.assertIsNotNone(caught)
                    self.assertEqual(outcome['status'],'failed')
                    self.assertEqual(outcome['terminal_publication_status'],'unavailable')
                    self.assertIsNone(outcome['terminal_receipt'])
                    reference=caught.verified_progress_reference
                    self.assertEqual(reference,outcome['verified_progress_reference'])
                else:
                    reservation=progress_reservation(fixture,1.3);clock=ReservationClock.from_reservation(reservation)
                    (root/'jobs').mkdir()
                    reference=p.prepare_context(root,clock,fixture['request'],fixture['request']['recovery_authorization'],session.token,
                        session.owner.records['work'],load(),owner_pid=os.getpid())
                    session.install_progress(reference,min(session.fixture_action_end,clock.work_deadline))
                    consumer=session.owner.progress_consumer
                    if label=='P06':
                        original_read=consumer.read
                        def held(rec,limit=p.CHECKPOINT_BYTES):
                            if rec['path'].endswith('/0002.json') and not session.owner.released:
                                session.owner.progress_block_entered=self.time.monotonic()
                                while not session.owner.released:self.time.sleep(.001)
                            return original_read(rec,limit)
                        consumer.read=held
                    session.owner.progress_request_id=session.sequences['work']+1
                    data=dict(progress_fixture=fixture,progress_context=reference,output=str(root/'output'))
                    operation=dict(operation='constant',args=dict(value=data))
                    try:sup.monitored_call(operation,min(session.fixture_action_end,clock.work_deadline),self.sampler,load(),{},lifecycle=life)
                    except BaseException as exc:caught=exc
                    self.assertIsNotNone(caught)
                    reference=getattr(caught,'verified_progress_reference',None)
                    self.assertEqual(reference,life.progress.reference())
                self.assertIsNotNone(reference,dict(outcome=outcome,errors=list(session.owner.errors),progress_error=session.owner.progress_error))
                self.assertEqual(reference['counts']['produced'],'unknown')
                self.assertEqual(reference['counts']['qualified_total'],'unknown')
                self.assertTrue(reference['frozen'])
                self.assertEqual(reference['counts']['produced_lower_bound'],2 if label in ('P01','P04') else 1)
                self.assertEqual(reference['counts']['qualified'],2 if label in ('P01','P04') else (1 if label=='P02' else 0))
                self.assertEqual(reference['counts']['fit_produced_lower_bound'],1)
                self.assertEqual(reference['counts']['selection_produced_lower_bound'],1 if label in ('P01','P04') else 0)
                from vipe_benchmark import s1_evidence
                with patch.object(s1_evidence,'produced_row',side_effect=AssertionError('cold raw scan')),patch.object(s1_evidence,'qualify_row',side_effect=AssertionError('cold qualification')):
                    recovered=p.recover(reference)
                self.assertEqual(recovered['counts'],reference['counts'])
                if label=='P04':
                    self.assertIsNotNone(recovered['first_result'])
                    self.assertIn('partial-runtime.json',recovered['runtime'])
                self.assertEqual({k:p.process_binding(v) for k,v in session.owner.records.items()},pair)
                self.assertTrue(life.poisoned)
                saved=Path(os.environ['S1_VALIDATION_RUN_DIRECTORY'])/('progress-'+label)
                shutil.copytree(reference['context']['path'].rsplit('/',1)[0],saved)
                copied=[file_record(path) for path in sorted(saved.rglob('*')) if path.is_file()]
                session.events.append(dict(event='progress_outcome',label=label,reference=reference,recovered=recovered,exception=type(caught).__name__,
                    publication=outcome.get('terminal_publication_status'),durable_copies=copied,original_pair=pair,original_clock=observed[0] if observed else reservation,
                    production_return=self.time.monotonic(),owner_block_entered=getattr(session.owner,'progress_block_entered',None)))
            finally:
                frozen=life.progress.snapshot
                session.owner.released=True
                try:
                    if not life.reap(session.fixture_safety_end):raise AssertionError('progress helpers not retired')
                finally:
                    self.assertIs(life.progress.snapshot,frozen)
            self.assertLessEqual(self.time.monotonic(),session.fixture_safety_end)

    def test_progress_p01_worker_deadline(self):self.progress_scenario('P01','progress_worker',supervised=True)
    def test_progress_p02_reconcile_interruption(self):self.progress_scenario('P02','progress_block')
    def test_progress_p03_helper_death(self):self.progress_scenario('P03','progress_death')
    def test_progress_p04_failed_final_sample(self):self.progress_scenario('P04','progress_final',supervised=True)
    def test_progress_p05_interrupted_publisher(self):self.progress_scenario('P05','progress_torn')
    def test_progress_p06_blocked_owner(self):self.progress_scenario('P06','progress_normal')

    def test_progress_strict_primitives(self):
        from vipe_benchmark import s1_progress as p
        import json
        for case in SUBTEST_CASES[f'{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}']:
            with self.subTest(**case):
                kind=case['kind']
                invalid={'duplicate':b'{"a":1,"a":2}','nonfinite':b'{"a":NaN}',
                    'depth':b'['*13+b'0'+b']'*13,'oversize':b' '* (p.CHECKPOINT_BYTES+1),
                    'truncated':b'{"a":','string':json.dumps('x'*2049).encode()}
                if kind in invalid:
                    with self.assertRaises((ValueError,RecursionError)):p.decode(invalid[kind])
                elif kind=='bool':
                    with self.assertRaises(ValueError):p.integer(True)
                elif kind=='equal_deadline':
                    with patch.object(p.time,'monotonic',return_value=10),self.assertRaises(TimeoutError):p.before(10)
                elif kind=='after_deadline':
                    with patch.object(p.time,'monotonic',return_value=11),self.assertRaises(TimeoutError):p.before(10)
                else:
                    with patch.object(p.time,'monotonic',return_value=9):self.assertEqual(p.before(10),9)
        self.assertEqual(p.decode(p.encode({'ok':[True,None,1,1.5,-1]})),{'ok':[True,None,1,1.5,-1]})

    def test_progress_metadata_mutations(self):
        import copy,json
        from vipe_benchmark import s1_progress as p
        from vipe_benchmark.s1_clock import ReservationClock
        from vipe_benchmark.s1_evidence import input_loader,produced_row,qualify_row
        from vipe_benchmark.files import write_json,file_record
        from test_vipe_benchmark_s1_helper_fixtures import progress_fixture,progress_reservation,inline_progress
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);fixture=progress_fixture(root);(root/'jobs').mkdir()
            clock=ReservationClock.from_reservation(progress_reservation(fixture,30))
            with inline_progress(root,clock,fixture['request'],load()) as (reference,cache):
                publisher=p.Publisher(reference,'worker',1,clock=clock,request=fixture['request'])
                try:
                    row=fixture['rows'][0];path=root/'row.json';write_json(path,row)
                    produced_row(row,fixture['request']);publisher.seal(row,file_record(path))
                    raw=p.read_bytes(publisher.previous['path'],p.CHECKPOINT_BYTES);original=p.decode(raw)
                    self.assertEqual(original['counts']['produced_lower_bound'],1)
                    self.assertEqual(original['counts']['qualified'],0)
                    for case in SUBTEST_CASES[f'{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}']:
                        with self.subTest(**case):
                            value=copy.deepcopy(original);kind=case['kind']
                            if kind=='schema':value['extra']=0
                            elif kind=='bool_sequence':value['sequence']=True
                            elif kind=='generation_overflow':value['sequence']=1025
                            elif kind=='qualified_type':value['rows'][0]['qualified']=1
                            elif kind=='count':value['counts']['qualified']=1
                            elif kind=='count_bool':value['counts']['qualified']=False
                            elif kind=='identity':value['rows'][0]['identity']['camera']=34
                            elif kind=='category':value['rows'][0]['identity']['frame']=51
                            elif kind=='order':value['rows']*=2
                            elif kind=='seal':value['rows'][0]['authority']['version']='b'*64
                            elif kind=='source':value['rows'][0]['source_indices']=[999]
                            elif kind=='context':value['context']['sha256']='b'*64
                            elif kind=='late':value['verified_at']=clock.work_deadline
                            elif kind=='pid':value['binding']['pgid']+=1
                            elif kind=='request':value['request_id']=2
                            elif kind=='errors':value['errors']=['x']*33
                            elif kind=='error_bytes':value['errors']=['x'*1025]
                            elif kind=='runtime':value['runtime']={str(i):path for i in range(5)}
                            elif kind=='unclosed':value['rows'][0]['authority']['producer']='reconcile'
                            elif kind=='complete':value['acceptance']=file_record(path)
                            with self.assertRaises((ValueError,TypeError)):p.validate_checkpoint(value,publisher.context,reference)
                    accepted=cache.reference();self.assertEqual(p.recover(accepted)['counts']['qualified'],0)
                    saved=Path(publisher.previous['path']);saved.write_bytes(b'{}')
                    with self.assertRaises(ValueError):p.recover(accepted)
                    saved.write_bytes(raw)
                    head=saved.parent/'head.json';head.write_bytes(b'{')
                    self.assertEqual(p.recover(accepted)['counts']['produced_lower_bound'],1)
                    changed=copy.deepcopy(row);changed['metadata']['extra']='later conflict'
                    with self.assertRaisesRegex(ValueError,'conflicting authority'):publisher.seal(changed,file_record(path))
                finally:publisher.close()

    def test_progress_closed_inventory_and_faults(self):
        import copy
        from vipe_benchmark import s1_progress as p,s1_evidence as e
        from vipe_benchmark.files import write_json
        from test_vipe_benchmark_s1_helper_fixtures import progress_fixture
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);fixture=progress_fixture(root/'fixture');output=root/'output';output.mkdir()
            row=fixture['rows'][0];write_json(output/'one-produced-row.json',row);write_json(output/'two-qualified-row.json',row)
            good=e.reconcile_rows(output,fixture['request']);self.assertEqual(good['counts']['produced_lower_bound'],1);self.assertEqual(good['counts']['qualified'],1)
            conflict=copy.deepcopy(row);conflict['metadata']['later']='conflict';write_json(output/'three-produced-row.json',conflict)
            bad=e.reconcile_rows(output,fixture['request']);self.assertEqual(bad['counts']['produced_lower_bound'],0)
            self.assertTrue(any('conflicting' in v['error'] for v in bad['verification_errors']))
            for case in SUBTEST_CASES[f'{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}']:
                with self.subTest(**case):
                    kind=case['kind']
                    if kind=='deadline':
                        result=e.reconcile_rows(output,fixture['request'],deadline=0)
                        self.assertFalse(result['scan_complete']);self.assertEqual(result['counts']['produced_lower_bound'],0)
                    elif kind=='symlink':
                        link=output/'alias-produced-row.json';link.symlink_to(output/'one-produced-row.json')
                        try:
                            with self.assertRaises(ValueError):p.candidate_inventory(output,None,None)
                        finally:link.unlink()
                    elif kind=='candidate':
                        with patch.object(p,'MAX_CANDIDATES',1),self.assertRaises(ValueError):p.candidate_inventory(output,None,None)
                    elif kind=='entries':
                        with patch.object(p,'MAX_ENTRIES',1),self.assertRaises(ValueError):p.candidate_inventory(output,None,None)
                    elif kind=='sources':
                        with patch.object(p,'MAX_SOURCES',1),self.assertRaises(ValueError):p.candidate_inventory(output,None,None)
                    elif kind=='bytes':
                        with patch.object(p,'MAX_METADATA',1),self.assertRaises(ValueError):p.candidate_inventory(output,None,None)
                    elif kind=='traversal':
                        with self.assertRaises(ValueError):p.read_bytes(str(root)+'/output/../output/one-produced-row.json',1024)
                    elif kind=='write':
                        with patch.object(p.os,'open',side_effect=OSError('write failed')),self.assertRaises(OSError):p.write_exclusive(root/'failed',b'{}')
                    elif kind=='fsync':
                        with patch.object(p.os,'fsync',side_effect=OSError('fsync failed')),self.assertRaises(OSError):p.write_exclusive(root/'fsync-failed',b'{}')
                    elif kind=='readback':
                        with patch.object(p,'read_bytes',return_value=b'bad'),self.assertRaises(ValueError):p.write_exclusive(root/'readback-failed',b'{}')
            self.assertEqual(good['counts']['produced'],'unknown');self.assertEqual(good['counts']['qualified_total'],'unknown')
            source=Path(__file__).resolve().parents[1]/'scripts/vipe_benchmark/stages.py'
            self.assertIn('checks = publish_segment_row(',source.read_text())


    def test_progress_plan046_worker_authority(self):
        import copy,uuid
        from vipe_benchmark import s1_progress as p,s1_evidence as e,s1_cpu_helper as helper
        from vipe_benchmark.s1_clock import ReservationClock
        from vipe_benchmark.s1_helper_session import identity
        from vipe_benchmark.files import write_json,file_record
        from test_vipe_benchmark_s1_helper_fixtures import progress_fixture,progress_reservation
        saved=[]
        with tempfile.TemporaryDirectory() as temp:
            fixture=progress_fixture(Path(temp)/'fixture')
            for case in SUBTEST_CASES[f'{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}']:
                with self.subTest(**case):
                    root=Path(temp)/case['kind'];root.mkdir();(root/'jobs').mkdir();output=root/'output';output.mkdir()
                    reservation=progress_reservation(fixture,30);clock=ReservationClock.from_reservation(reservation)
                    reference=p.prepare_context(root,clock,fixture['request'],fixture['request']['recovery_authorization'],uuid.uuid4().hex,identity(os.getpid()),load(),owner_pid=os.getpid())
                    cache=p.RetainedProgress();sequence=[1];binding=p.process_binding(identity(os.getpid()))
                    consumer=p.Consumer(reference,cache,lambda:False,lambda producer:(binding,1 if producer=='worker' else sequence[0]))
                    publisher=None
                    try:
                        with patch.object(p.Publisher,'after_notice',side_effect=lambda:consumer.tick()):
                            publisher=p.Publisher(reference,'worker',1,clock=clock,request=fixture['request'])
                            row=fixture['rows'][0];path=output/'one-produced-row.json';write_json(path,row)
                            e.produced_row(row,fixture['request']);publisher.seal(row,file_record(path))
                            e.qualify_row(row,fixture['request'],first=True);publisher.seal(row,file_record(path),qualified=True)
                            publisher.close();trusted=cache.reference()
                            if case['kind']=='conflict':
                                changed=copy.deepcopy(row);changed['metadata']['conflict']=True;write_json(output/'two-produced-row.json',changed)
                            publisher=p.Publisher(reference,'reconcile',1,clock=clock,request=fixture['request'],trusted=trusted)
                            with patch.object(e,'produced_row',side_effect=AssertionError('sealed structural guard reused')),patch.object(e,'qualify_row',side_effect=AssertionError('sealed semantic guard reused')):
                                summary=e.reconcile_rows(output,fixture['request'],deadline=clock.work_deadline,publisher=publisher)
                            self.assertEqual(summary['counts']['produced_lower_bound'],1);self.assertEqual(summary['counts']['qualified'],1)
                            if case['kind']=='conflict':self.assertTrue(summary['verification_errors']);self.assertEqual(publisher.coverage,'conflict')
                            elif case['kind']=='forged_seal':
                                publisher.rows[0]['authority']['worker_reference']=dict(trusted['checkpoints']['worker'],sha256='f'*64)
                                with self.assertRaisesRegex(ValueError,'worker authority'):publisher.publish()
                            elif case['kind']=='resume':
                                prior=publisher.sequence;publisher.close();sequence[0]=2
                                publisher=p.Publisher(reference,'reconcile',2,trusted=cache.reference())
                                publisher.publish();self.assertEqual(publisher.sequence,prior+1)
                            elif case['kind']=='publish_adapter':
                                document=helper.summary_binding(consumer.context['session'],1,reservation)
                                directory=root/'jobs'/'S1-calibration-recovery-001';directory.mkdir()
                                path=directory/('helper-summary-'+consumer.context['session']+'-1.json')
                                ordinary=dict(counts={'produced':0},runtime={},first_result={'status':'unverified','value':None},verification_errors=[])
                                write_json(path,dict(document,summary=ordinary))
                                args=dict(local=str(root),reservation=reservation,outcome=dict(verified_progress_reference=cache.reference(),evidence_summary_record=dict(document,record=file_record(path))))
                                with patch.object(helper,'run',side_effect=lambda operation:operation['args']['outcome']):
                                    result=helper.session_operation(dict(operation='publish',args=args),consumer.context['session'],3)
                                self.assertEqual(result['evidence_summary']['counts']['produced_lower_bound'],1)
                                self.assertEqual(result['evidence_summary']['counts']['produced'],'unknown')
                            saved.append(dict(case,counts=summary['counts'],errors=summary['verification_errors'],reference=cache.reference()))
                    finally:
                        if publisher is not None:publisher.close()
                        consumer.close()
        self.control_record('plan046-worker-authority',saved)

    def test_progress_plan046_launch_deadline(self):
        from vipe_benchmark import supervisor as sup
        from test_vipe_benchmark_s1_helper_fixtures import progress_fixture,progress_reservation
        records=[]
        with tempfile.TemporaryDirectory() as temp:
            fixture=progress_fixture(Path(temp)/'fixture')
            for case in SUBTEST_CASES[f'{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}']:
                with self.subTest(**case):
                    now=[102.];started=[];outcome={};root=Path(temp)/case['kind'];root.mkdir()
                    reservation=progress_reservation(fixture,4);reservation['monotonic_start']=100.
                    class Session:
                        def admission_guard(inner):pass
                        def install_progress(inner,*args):now[0]=103.+case['offset']
                        def retire_worker(inner):pass
                        def close(inner,deadline):return True
                        def ownership(inner):return []
                    life=sup.HelperLifecycle(retain=True);life.helpers=[Session()]
                    class Ledger:
                        path=root/'ledger.jsonl';config=load();jobs={'S1-calibration-recovery-001':dict(resource='gpu')}
                        def reserve(inner,*args,**kwargs):return reservation
                        def note(inner,*args,**kwargs):pass
                        def finish(inner,*args,**kwargs):outcome.update(kwargs)
                    def monitor(*args,**kwargs):
                        if kwargs.get('phase')=='initial_sample':return self.reading
                        if kwargs.get('phase')=='prelaunch':return {'bounded':'context'}
                        raise RuntimeError('no late reconciliation fixture')
                    def popen(*args,**kwargs):started.append(now[0]);raise RuntimeError('pure Popen boundary reached')
                    with patch.object(sup,'HelperLifecycle',return_value=life),patch.object(sup,'monitored_call',side_effect=monitor),patch.object(sup.time,'monotonic',side_effect=lambda:now[0]),patch.object(sup.subprocess,'Popen',side_effect=popen):
                        with self.assertRaises(sup.SupervisionFailure):sup.supervise(Ledger(),'S1-calibration-recovery-001',['unused'],root/'output',evidence={},sample_resources=self.sampler)
                    self.assertEqual(len(started),1 if case['kind']=='before' else 0)
                    if case['kind']!='before':self.assertIn('immediately before worker launch',outcome['error'])
                    self.assertIsNone(outcome['terminal_receipt']);records.append(dict(case,started=started,outcome=outcome))
        self.control_record('plan046-launch-deadline',records)

    def test_progress_plan046_ownership(self):
        import json,hashlib,copy
        from vipe_benchmark import s1_helper_session as h
        original=json.loads(Path(os.environ['S1_OWNED_ROOT_NOTE']).read_text())
        good=h.owned_workload(os.environ['S1_OWNED_ROOT_NOTE'])
        self.assertEqual(good['total_workers'],good['B']+max(1,good['H']))
        self.assertEqual(good['measured_total']+good['reserve'],good['total_workers'])
        with tempfile.TemporaryDirectory() as temp:
            for case in SUBTEST_CASES[f'{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}']:
                with self.subTest(**case):
                    kind=case['kind'];note=copy.deepcopy(original)
                    if kind=='root_bool':note['ownership_root']['pid']=True
                    elif kind=='pid_reuse':note['ownership_root']['start_ticks']+=1
                    elif kind=='output':note['run_directory']+='-foreign'
                    elif kind=='plan':note['bindings'][0]['sha256']='a'*64
                    elif kind=='omitted_source':note['sources'].pop()
                    path=Path(temp)/kind;raw=json.dumps(note).encode();path.write_bytes(raw)
                    env={'S1_OWNED_ROOT_SHA256':'0'*64 if kind=='hash' else hashlib.sha256(raw).hexdigest()}
                    with patch.dict(os.environ,env):
                        if kind=='enumeration':
                            with patch.object(h,'census',side_effect=OSError('enumeration unavailable')),self.assertRaises(OSError):h.owned_workload(path)
                        elif kind=='overflow':
                            actual=Path.iterdir
                            def many(path):
                                values=list(actual(path))
                                return iter(values*9 if path.name=='task' else values)
                            with patch.object(Path,'iterdir',many),self.assertRaisesRegex(ValueError,'ceiling'):h.owned_workload(path)
                        elif kind=='unproven_detached':
                            with self.assertRaises(ValueError):h.owned_workload(path,extra=(original['preexisting_ancestors'][0]['pid'],))
                        else:
                            with self.assertRaises(ValueError):h.owned_workload(path)

    def test_progress_plan046_protocol(self):
        import copy
        from vipe_benchmark import s1_progress as p
        from vipe_benchmark.s1_clock import ReservationClock
        from vipe_benchmark.files import write_json,file_record
        from vipe_benchmark.s1_evidence import produced_row
        from test_vipe_benchmark_s1_helper_fixtures import progress_fixture,progress_reservation,inline_progress
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);fixture=progress_fixture(root);(root/'jobs').mkdir()
            clock=ReservationClock.from_reservation(progress_reservation(fixture,30))
            with inline_progress(root,clock,fixture['request'],load()) as (reference,cache):
                publisher=p.Publisher(reference,'worker',1,clock=clock,request=fixture['request'])
                try:
                    row=fixture['rows'][0];path=root/'row.json';write_json(path,row)
                    produced_row(row,fixture['request']);publisher.seal(row,file_record(path))
                    doc=p.read_record(publisher.previous);head=p.read_record(file_record(Path(publisher.previous['path']).parent/'head.json'))
                    notice=dict(schema='s1-progress-notice/v1',context=reference,producer='worker',binding=publisher.binding,
                        request_id=1,sequence=1,current=publisher.previous,previous=None,head=file_record(Path(publisher.previous['path']).parent/'head.json'),completed=self.time.monotonic())
                    ack=dict(schema='s1-progress-ack/v1',context=reference['sha256'],producer='worker',sequence=1,current=publisher.previous)
                    for case in SUBTEST_CASES[f'{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}']:
                        with self.subTest(**case):
                            kind=case['kind'];n=copy.deepcopy(notice);a=copy.deepcopy(ack);h=copy.deepcopy(head);d=copy.deepcopy(doc);r=copy.deepcopy(cache.reference())
                            if kind=='notice_bool_request':n['request_id']=True
                            elif kind=='notice_bool_pid':n['binding']['pid']=True
                            elif kind=='notice_bad_record':n['context']['bytes']=True
                            elif kind=='ack_bool_sequence':a['sequence']=True
                            elif kind=='ack_bad_record':a['current']['path']=1
                            elif kind=='head_schema':h['schema']='foreign'
                            elif kind=='head_bool_sequence':h['sequence']=True
                            elif kind=='head_bad_previous':h['previous']={'path':'/x','bytes':False,'sha256':'a'*64}
                            elif kind=='reference_bool_frozen':r['frozen']=1
                            elif kind=='checkpoint_bool_deadline':d['work_deadline']=True
                            elif kind=='runtime_alias':d['runtime']['partial']=file_record(path)
                            with self.assertRaises(ValueError):
                                if kind.startswith('notice'):p.validate_notice(n)
                                elif kind.startswith('ack'):p.validate_ack(a)
                                elif kind.startswith('head'):p.validate_head(h)
                                elif kind.startswith('reference'):p.recover(r)
                                elif kind=='numeric_overflow':p.number(10**1000)
                                else:p.validate_checkpoint(d,publisher.context,reference)
                finally:publisher.close()

    def test_progress_plan046_inventory(self):
        import copy
        from vipe_benchmark import s1_progress as p
        from vipe_benchmark.files import write_json
        from test_vipe_benchmark_s1_helper_fixtures import progress_fixture
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);fixture=progress_fixture(root/'fixture')
            for case in SUBTEST_CASES[f'{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}']:
                with self.subTest(**case):
                    output=root/case['kind'];output.mkdir();row=fixture['rows'][0]
                    result={'rows':[row]};write_json(output/'result.json',result)
                    write_json(output/'one-produced-row.json',row)
                    if case['kind']=='result_mismatch':
                        other=copy.deepcopy(result);other['rows'][0]['metadata']['other']=True
                        with self.assertRaisesRegex(ValueError,'snapshot mismatch'):p.candidate_inventory(output,other,None)
                        continue
                    candidates,inventory=p.candidate_inventory(output,result,None)
                    self.assertEqual(len(candidates),2);inventory.recheck()
                    kind=case['kind']
                    if kind=='result_mutation':(output/'result.json').write_text('{"rows":[]}')
                    elif kind=='membership_add':write_json(output/'extra-produced-row.json',row)
                    elif kind=='membership_remove':(output/'one-produced-row.json').unlink()
                    elif kind=='parent_replace':output.rename(output.with_suffix('.old'));output.mkdir()
                    with self.assertRaises((ValueError,FileNotFoundError)):inventory.recheck()

    def test_progress_plan046_summary(self):
        import copy
        from vipe_benchmark import s1_progress as p
        ref=dict(path='/immutable/runtime.json',bytes=2,sha256='a'*64)
        trusted=dict(integrity_status='verified',counts=p.counts([]),runtime={'final':ref},first_result=ref,
            verification_errors=['sticky'],scan_complete=False,acceptance=None)
        for case in SUBTEST_CASES[f'{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}']:
            with self.subTest(**case):
                kind=case['kind'];ordinary=dict(counts={'produced':0},runtime={'final':dict(status='verified',value=ref)},
                    first_result=dict(status='verified',value=ref),verification_errors=[])
                if kind=='first_conflict':ordinary['first_result']['value']=dict(ref,sha256='b'*64)
                elif kind=='runtime_conflict':ordinary['runtime']['final']['value']=dict(ref,sha256='b'*64)
                elif kind=='runtime_alias':ordinary['runtime']['partial']=ordinary['runtime'].pop('final')
                if kind.endswith('conflict') or kind=='runtime_alias':
                    with self.assertRaises(ValueError):p.summary_adapter(trusted,ordinary)
                else:
                    value=p.summary_adapter(trusted,None if kind=='absent' else ordinary)
                    self.assertEqual(value['counts'],trusted['counts']);self.assertEqual(value['first_result']['value'],ref)
                    self.assertEqual(value['runtime']['final']['value'],ref);self.assertEqual(value['verification_errors'],['sticky'])

    def test_progress_plan046_publication_faults(self):
        from vipe_benchmark import s1_progress as p
        from vipe_benchmark.s1_clock import ReservationClock
        from vipe_benchmark.files import write_json,file_record
        from vipe_benchmark.s1_evidence import produced_row
        from test_vipe_benchmark_s1_helper_fixtures import progress_fixture,progress_reservation,inline_progress
        evidence=[]
        with tempfile.TemporaryDirectory() as temp:
            fixture=progress_fixture(Path(temp)/'fixture')
            for case in SUBTEST_CASES[f'{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}']:
                with self.subTest(**case):
                    root=Path(temp)/case['kind'];root.mkdir();(root/'jobs').mkdir()
                    clock=ReservationClock.from_reservation(progress_reservation(fixture,30))
                    with inline_progress(root,clock,fixture['request'],load()) as (reference,cache):
                        publisher=p.Publisher(reference,'worker',1,clock=clock,request=fixture['request'])
                        try:
                            row=fixture['rows'][0];path=root/'row.json';write_json(path,row)
                            produced_row(row,fixture['request']);publisher.seal(row,file_record(path))
                            retained=cache.reference();reached=[]
                            def boundary(stage):
                                reached.append(stage)
                                if stage==case['kind']:raise OSError('actual publication boundary '+stage)
                            import contextlib,socket
                            with contextlib.ExitStack() as stack:
                                kind=case['kind']
                                if kind=='short_write':
                                    original=p.os.fdopen
                                    class Short:
                                        def __init__(inner,stream):inner.stream=stream
                                        def __enter__(inner):inner.stream.__enter__();return inner
                                        def __exit__(inner,*args):return inner.stream.__exit__(*args)
                                        def write(inner,raw):reached.append('short_write');return inner.stream.write(raw[:1])
                                        def __getattr__(inner,name):return getattr(inner.stream,name)
                                    def fdopen(fd,mode,*args,**kwargs):
                                        stream=original(fd,mode,*args,**kwargs)
                                        return Short(stream) if mode=='wb' else stream
                                    stack.enter_context(patch.object(p.os,'fdopen',side_effect=fdopen))
                                elif kind=='generation_collision':
                                    (Path(publisher.previous['path']).parent/'0002.json').write_bytes(b'{}')
                                    reached.append(kind)
                                elif kind=='notice_full':
                                    for _ in range(32):
                                        try:publisher.channel.sendto(b' '*p.CONTROL_BYTES,p.address(publisher.context))
                                        except BlockingIOError:reached.append(kind);break
                                    self.assertIn(kind,reached)
                                elif kind=='receive_truncated':
                                    publisher.channel.sendto(b' '*(p.CONTROL_BYTES+1),p.address(publisher.context));reached.append(kind)
                                elif kind in ('receive_credentials','ack_wrong'):
                                    actual=p.receive
                                    def receive(channel):
                                        value,credentials,sender=actual(channel)
                                        if kind=='receive_credentials' and value['schema']=='s1-progress-notice/v1':
                                            reached.append(kind);credentials=(credentials[0]+1,*credentials[1:])
                                        if kind=='ack_wrong' and value['schema']=='s1-progress-ack/v1':
                                            reached.append(kind);value=dict(value,sequence=True)
                                        return value,credentials,sender
                                    stack.enter_context(patch.object(p,'receive',side_effect=receive))
                                else:stack.enter_context(patch.object(p,'publication_boundary',side_effect=boundary))
                                with self.assertRaises((OSError,ValueError)):publisher.publish()
                            self.assertIn(case['kind'],reached);self.assertTrue(publisher.stopped)
                            current=cache.reference()
                            expected=2 if case['kind'] in ('ack_receipt','ack_wrong') else 1
                            self.assertEqual(p.read_record(current['checkpoints']['worker'])['sequence'],expected)
                            files=[dict(path=str(path),bytes=path.stat().st_size,raw_hex=path.read_bytes().hex()) for path in Path(reference['path']).parent.rglob('*') if path.is_file()]
                            evidence.append(dict(stage=case['kind'],reached=reached,deadline=clock.work_deadline,
                                retained=current,previous=retained,raw_files=files,usable=current['integrity_status']=='verified'))
                        finally:publisher.close()
        self.control_record('plan046-publication-faults',evidence)

    def control_record(self,name,value):
        import json
        from dataclasses import asdict,is_dataclass
        with (Path(os.environ['S1_VALIDATION_RUN_DIRECTORY'])/(name+'.json')).open('x') as stream:
            json.dump(value,stream,indent=2,default=lambda v:asdict(v) if is_dataclass(v) else list(v));stream.write('\n')

    def test_combined_duplex_and_same_turn_bounds(self):
        import socket,struct
        from vipe_benchmark.s1_helper_session import Wire,tokens,IO_SLICE
        rows=[];a,b=socket.socketpair();b.setblocking(False)
        try:
            wire=Wire(a);value=dict(data=['x'*1900]*16);wire.queue(value)
            raw=''.join(tokens(value)).encode();remaining=bytearray(struct.pack('!I',len(raw))+raw)
            outgoing=bytearray();received=None
            for _ in range(100):
                if remaining:
                    try:size=b.send(remaining);del remaining[:size]
                    except BlockingIOError:pass
                result=wire.tick()
                rows.append(dict(sent=wire.turn_sent,received=wire.turn_received,peek=wire.turn_peek))
                self.assertLessEqual(sum(rows[-1].values()),IO_SLICE)
                try:outgoing.extend(b.recv(65540))
                except BlockingIOError:pass
                if result is not None:received=result
                if received is not None and wire.encoder is None and not wire.out:break
            self.assertEqual(received,value)
            self.assertEqual(bytes(outgoing),struct.pack('!I',len(raw))+raw)
            self.assertTrue(any(r['sent'] and r['received'] for r in rows))
        finally:a.close();b.close()
        # Deterministic socket seam observes a byte in the final-send turn.
        class Duplex:
            def __init__(self):self.sent=False
            def setblocking(self,value):pass
            def send(self,value):self.sent=True;return len(value)
            def recv(self,size,flags=0):
                if self.sent:return b'x'
                raise BlockingIOError()
        wire=Wire(Duplex());wire.queue({'ok':True});request={}
        with self.assertRaisesRegex(ValueError,'premature'):wire.tick(request)
        self.assertIn('transmitted_observed',request)
        self.assertIn('early_observed',request)
        self.assertLessEqual(wire.turn_sent+wire.turn_peek,IO_SLICE)
        self.assertTrue(any(sum(row.values())==IO_SLICE for row in rows))
        # Exhaust a small explicit allowance after a previously completed frame's
        # validator, then require the trailing check on the next turn.
        a,b=socket.socketpair()
        try:
            rollover=Wire(a);b.send(struct.pack('!I',2)+b'{}')
            self.assertIsNone(rollover.tick())
            rollover.out=bytearray(b'x')
            self.assertIsNone(rollover.tick(allowance=1))
            self.assertEqual(rollover.turn_sent,1)
            self.assertIsNotNone(rollover.decoded)
            self.assertIsNone(rollover.validator)
            self.assertEqual(rollover.tick(allowance=1),{})
            self.assertIsNone(rollover.decoded)
        finally:a.close();b.close()
        self.control_record('transport-controls',dict(duplex=rows,same_turn=request,exhausted_allowance=1,validation_rollover=True))

    def test_partial_constructor_boundaries(self):
        import _thread,socket
        from vipe_benchmark import s1_helper_session as mod
        from vipe_benchmark import supervisor as sup
        records=[]
        for mode in ('capability','native_known','owner','socket1','socket2','wire1','wire2','invalid_cutoffs'):
            before=set(os.listdir('/proc/self/fd'));calls=[]
            pair=socket.socketpair;wire=mod.Wire
            def socket_factory():
                calls.append('socket')
                if mode=='socket'+str(calls.count('socket')):raise OSError('injected '+mode)
                return pair()
            def wire_factory(channel):
                calls.append('wire')
                if mode=='wire'+str(calls.count('wire')):raise ValueError('injected '+mode)
                return wire(channel)
            acquired=[]
            class Selected(mod.Session):
                def __init__(self):
                    acquired.append(self)
                    kwargs=dict(owner_factory=lambda session:(_ for _ in ()).throw(ValueError('injected owner'))) if mode=='owner' else {}
                    if mode=='invalid_cutoffs':kwargs['ready_seconds']=0
                    super().__init__(**kwargs)
            from contextlib import ExitStack
            with ExitStack() as stack:
                stack.enter_context(patch.object(socket,'socketpair',side_effect=socket_factory))
                stack.enter_context(patch.object(mod,'Wire',side_effect=wire_factory))
                if mode=='capability':
                    saved=_thread.start_joinable_thread;del _thread.start_joinable_thread
                    stack.callback(setattr,_thread,'start_joinable_thread',saved)
                else:stack.enter_context(patch.object(_thread,'start_joinable_thread',side_effect=mod.NativeNotStarted('known native pre-entry failure')))
                life=sup.HelperLifecycle(session_factory=Selected);start=self.time.monotonic()
                with tempfile.TemporaryDirectory() as temp:
                    reserves=[]
                    class Disposable:
                        config=load();jobs={'S1-calibration-recovery-001':dict(resource='gpu')}
                        def reserve(inner,*args,**kwargs):reserves.append('reserve')
                    with patch.object(sup,'HelperLifecycle',return_value=life):
                        with self.assertRaises(sup.HelperFailure) as caught:
                            sup.supervise(Disposable(),'S1-calibration-recovery-001',['unused'],Path(temp)/'out',evidence={},sample_resources=self.sampler)
                    self.assertEqual(reserves,[])
                current=acquired[0];primary=dict(current.primary)
                self.assertTrue(life.reap(start+.1));self.assertTrue(current.close(start+.1))
                self.assertEqual(current.primary,primary);self.assertEqual(current.state,'retired')
                self.assertLessEqual(self.time.monotonic(),start+.1)
                self.assertFalse(current.ownership());self.assertFalse(life.helpers)
                self.assertEqual(caught.exception.failure['error_class'],primary['error_class'])
            self.assertEqual(set(os.listdir('/proc/self/fd')),before)
            records.append(dict(mode=mode,primary=primary,calls=calls,retired=current.state,descriptor_delta=0,reserve_calls=0))
        self.control_record('construction-controls',records)

    def test_census_immutable_identity_mutations(self):
        from dataclasses import replace,FrozenInstanceError
        import types
        from vipe_benchmark.s1_helper_session import Session,Census,ProcessIdentity,GPUOwnershipError
        session=Session.__new__(Session);session.token='token';session.owner=types.SimpleNamespace(boot_id='boot')
        helper1=ProcessIdentity(1,2,1,os.getpid(),'S');helper2=ProcessIdentity(3,4,3,os.getpid(),'S');worker=ProcessIdentity(5,6,5,os.getpid(),'Z')
        session.ready={r:dict(pid=h.pid,start_ticks=h.start_ticks,pgid=h.pgid) for r,h in zip(('work','sample'),(helper1,helper2))}
        session.worker_pid=5;session.worker_generation=7;session.worker_root=worker;session.last_sample=None
        pre=Census('token','boot',1,1,7,10.,10.1,'success',(helper1,helper2),worker,(worker,),helper_rows=(helper1,helper2))
        post=replace(pre,generation=2,acquisition_start=10.4,completed=10.5)
        request=dict(id=1,dispatch=10.,deadline=11.,census_generation=2,pre=pre,final_send_entered=10.2,transmitted_observed=10.25,response_observed=10.4,
            candidate=dict(value=dict(gpu_pids=[5]),acquisition_start=10.2,acquisition_end=10.3))
        self.assertEqual(session.validate_census(post,request,10.6),post)
        session.last_sample=session.sample_authority(request,post,10.6);saved=session.last_sample
        mutations=[dict(session='other'),dict(boot_id='other'),dict(generation=1),dict(generation=True),dict(request_id=True),dict(worker_generation=True),dict(request_id=2),dict(worker_generation=8),dict(status='failed'),dict(acquisition_start=9.),dict(completed=12.),dict(completed=True),dict(completed=float('nan')),dict(worker=replace(worker,start_ticks=7)),dict(worker=replace(worker,pgid=9)),dict(worker=replace(worker,pid=9)),dict(worker=None),dict(helper_rows=()),dict(helper_rows=(replace(helper1,start_ticks=99),helper2)),dict(helpers=(replace(helper1,start_ticks=9),helper2)),dict(exit_observed=10.7)]
        for change in mutations:
            with self.assertRaises(ValueError):session.validate_census(replace(post,**change),request,10.6)
        for rows in ((),(replace(worker,start_ticks=99),),(replace(worker,pgid=99),)):
            with self.assertRaises(GPUOwnershipError):session.sample_authority(request,replace(post,rows=rows),10.6)
        new=ProcessIdentity(9,10,5,5,'S');request['candidate']['value']['gpu_pids']=[9]
        with self.assertRaises(GPUOwnershipError):session.sample_authority(request,replace(post,rows=(worker,new)),10.6)
        with self.assertRaises(FrozenInstanceError):post.generation=99
        self.assertIs(session.last_sample,saved)
        session.worker_pid=None
        with self.assertRaises(ValueError):session.validate_census(post,request,10.6)
        self.control_record('census-controls',dict(pre=pre,post=post,mutation_count=len(mutations)+5,immutable=True))

    def test_bounded_traces_counters_and_authority(self):
        from vipe_benchmark.s1_helper_session import Trace,Counter,UINT64_MAX,Session
        import types
        records=[]
        for capacity,errors in ((256,False),(128,False),(128,False),(32,True),(32,True)):
            trace=Trace(capacity,errors=errors)
            for number in range(capacity+10):trace.append(dict(message=str(number)+'x'*2000,number=number))
            self.assertEqual(len(trace),capacity);self.assertEqual(trace.total.value,capacity+10);self.assertEqual(trace.dropped.value,10)
            if errors:self.assertEqual(trace.primary['number'],0);self.assertEqual(len(trace.primary['message']),1024)
            trace.total.value=UINT64_MAX;trace.append(dict(message='saturated'))
            self.assertTrue(trace.total.saturated);self.assertEqual(trace.total.value,UINT64_MAX)
            self.assertLessEqual(trace.first,trace.last);records.append(trace.facts())
        current=Session.__new__(Session)
        # Constructor no-start seam initializes all bounded authoritative state.
        import _thread
        from vipe_benchmark.s1_helper_session import NativeNotStarted
        with patch.object(_thread,'start_joinable_thread',side_effect=NativeNotStarted('primary')):
            with self.assertRaises(NativeNotStarted):current.__init__()
        current.requests['work']={'id':7,'deadline':0.};primary=current.primary
        for _ in range(300):current.events.append({'event':'overflow'})
        self.assertEqual(current.requests['work']['id'],7);self.assertIs(current.primary,primary)
        current.poisoned=False;current.owner.cancelled=False;current.owner.errors=Trace(32,errors=True)
        current.last_tick=self.time.monotonic()
        with self.assertRaisesRegex(TimeoutError,'phase deadline'):current.tick(self.time.monotonic())
        retained=current.requests['work']
        order=[]
        class EmptyWire:
            def __init__(self,role):self.role=role
            def tick(self,request=None):order.append(self.role)
        current.requests={'work':None,'sample':None};current.wires={role:EmptyWire(role) for role in current.requests}
        current.ready={'work':{},'sample':{}}
        current.ticks.total.value=UINT64_MAX
        current.last_tick=self.time.monotonic()
        current.tick(self.time.monotonic()+.1);current.tick(self.time.monotonic()+.1)
        self.assertEqual(order[:2],list(reversed(order[2:])))
        self.assertTrue(current.ticks.total.saturated)
        current.sequences['work']=UINT64_MAX
        with self.assertRaisesRegex(ValueError,'sequence exhausted'):current.submit('work',self.operation,self.time.monotonic()+.1)
        current.census_sequence=UINT64_MAX
        with self.assertRaisesRegex(ValueError,'generation exhausted'):current.request_census({'id':1},'pre')
        self.control_record('trace-controls',dict(rings=records,primary_retained=primary,request_retained=retained,role_order=order))

    def test_control_primitive_and_frame_mutations(self):
        from vipe_benchmark.s1_helper_session import tokens,decode,Wire,MAX_FRAME
        import socket
        import struct
        valid=dict(one=[None,True,False,1,1.5,'text'])
        self.assertEqual(decode(''.join(tokens(valid)).encode()),valid)
        for raw in (b'',b'{}'*(MAX_FRAME//2+1),b'{"x":1,"x":2}',b'{"x":NaN}',b'\xff',b'[] trailing',b'['*19+b'0'+b']'*19,b'1'*21,b'1.'+b'1'*70):
            with self.assertRaises((ValueError,UnicodeError)): decode(raw)
        for value in (object(),{'x':object()},'x'*2049,[0]*4097,10**20,float('inf')):
            with self.assertRaises(ValueError): list(tokens(value))
        for length in (0,65537):
            a,b=socket.socketpair()
            try:
                wire=Wire(a); b.send(struct.pack('!I',length))
                with self.assertRaises(ValueError): wire.tick()
            finally: a.close(); b.close()
        a,b=socket.socketpair()
        try:
            wire=Wire(a); raw=b'{"x":1}'
            frame=struct.pack('!I',len(raw))+raw
            for byte in frame:
                b.send(bytes([byte])); self.assertIsNone(wire.tick())
            self.assertEqual(wire.tick(),{'x':1})
        finally: a.close(); b.close()

    def test_exact_frame_bounds_and_trailing_data(self):
        from vipe_benchmark.s1_helper_session import Wire,tokens,decode,MAX_FRAME
        import socket
        import struct
        value=dict(data=['x'*2048]*31,pad='')
        size=len(''.join(tokens(value)).encode())
        value['pad']='x'*(MAX_FRAME-size)
        raw=''.join(tokens(value)).encode()
        self.assertEqual(len(raw),MAX_FRAME)
        self.assertEqual(decode(raw),value)
        a,b=socket.socketpair();b.setblocking(False)
        try:
            wire=Wire(a);wire.queue(value);written=bytearray()
            while wire.encoder is not None or wire.out:
                wire.tick()
                try: written.extend(b.recv(65540))
                except BlockingIOError: pass
            self.assertEqual(bytes(written),struct.pack('!I',MAX_FRAME)+raw)
            value['pad']+='x';wire.queue(value)
            with self.assertRaises(ValueError):
                while True: wire.tick()
        finally:a.close();b.close()
        a,b=socket.socketpair()
        try:
            wire=Wire(a);b.send(struct.pack('!I',2)+b'{}'+struct.pack('!I',2)+b'{}')
            self.assertIsNone(wire.tick())
            with self.assertRaisesRegex(ValueError,'trailing'):wire.tick()
        finally:a.close();b.close()

    def test_resource_field_mutations(self):
        from vipe_benchmark.supervisor import validate_sample
        validate_sample(self.reading)
        for key in ('device_bytes','artifact_bytes','download_bytes'):
            for value in (None,True,'0',-1,float('nan'),float('inf')):
                bad=dict(self.reading);bad[key]=value
                with self.assertRaises(ValueError):validate_sample(bad)
        for pids in (None,True,[True],[0],[-1],[1,1],['1']):
            bad=dict(self.reading,gpu_pids=pids)
            with self.assertRaises(ValueError):validate_sample(bad)

    def test_sample_typed_timing_mutations(self):
        from vipe_benchmark.s1_helper_session import validate_acquisition
        good=dict(acquisition_start=10.,acquisition_end=10.1)
        validate_acquisition(good,10.,10.2,11.)
        for value in (None,True,'10',float('nan'),float('inf'),-1,9.,11.):
            for key in ('acquisition_start','acquisition_end'):
                bad=dict(good); bad[key]=value
                with self.assertRaises(ValueError): validate_acquisition(bad,10.,10.2,11.)
        with self.assertRaises(ValueError): validate_acquisition({},10.,10.2,11.)
        with self.assertRaises(ValueError): validate_acquisition(good,10.,11.,12.)
        with self.assertRaises(ValueError): validate_acquisition(good,10.,10.2,10.2)
        with self.assertRaises(ValueError): validate_acquisition(dict(acquisition_start=10.1,acquisition_end=10.),10.,10.2,11.)

    def test_envelope_correlation_mutations(self):
        from vipe_benchmark.s1_helper_session import Session
        import types
        session=Session.__new__(Session); session.token='a'; session.owner=types.SimpleNamespace(boot_id='b')
        good=session.envelope('sample',1,'response',{})
        self.assertEqual(session.correlate('sample',good,'response',1),{})
        for key,value in (('version',True),('version',2),('session','z'),('boot_id','z'),('role','work'),('request_id',True),('request_id',0),('request_id',2),('kind','ready')):
            bad=dict(good); bad[key]=value
            with self.assertRaises(ValueError): session.correlate('sample',bad,'response',1)
        with self.assertRaises(ValueError): session.correlate('sample',dict(good,extra=1),'response',1)

if __name__ == '__main__':
    unittest.main()
