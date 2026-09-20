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
        with patch.object(multiprocessing.process.BaseProcess, 'start', side_effect=OSError('bootstrap failed')):
            with self.assertRaises(self.sup.HelperFailure) as caught:
                self.call()
        self.assertEqual(caught.exception.failure['phase'], 'startup')
        self.assertEqual(self.life.helpers, [])
        helper = self.life.start(self.operation)
        helper.process.kill()
        limit = self.time.monotonic()+2
        try:
            with self.assertRaises(self.sup.HelperFailure) as caught:
                while self.time.monotonic() < limit:
                    helper.poll()
                    self.time.sleep(.005)
            self.assertEqual(caught.exception.failure['phase'], 'transport')
            self.assertEqual(caught.exception.failure['ownership']['pid'], helper.pid)
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
        reading = self.reading
        class Fake:
            def __init__(self, operation):
                self.pid = 987654321
                self.phase = 'fixture'
                self.value = operation['args']['value']
                self.selected = (isinstance(self.value, dict)) == (role == 'sample')
                self.calls = 0
            def poll(self):
                if self.selected and outcome == 'error':
                    raise ValueError('primary fixture error')
                if self.selected and outcome == 'timeout':
                    return False, None
                return True, self.value
            def close(self):
                self.calls += 1
                if self.selected:
                    if mode == 'false' or (mode=='false_then_reaped' and self.calls==1):
                        return False
                    if mode.endswith('exception'):
                        raise OSError(mode)
                return True
        return Fake

    def test_cleanup_matrix(self):
        from unittest.mock import patch
        for case in SUBTEST_CASES[f"{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}"]:
            with self.subTest(**case):
                self.life = self.sup.HelperLifecycle()
                start = self.time.monotonic()
                with patch.object(self.sup,'_Helper',self.fake_class(**case)):
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
                with patch.object(self.sup,'_Helper',self.fake_class(mode=case['mode'])):
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
        with patch.object(self.sup,'_Helper',self.fake_class(outcome='error',mode='close_exception')):
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
        helper = self.life.start(self.operation)
        self.assertTrue(self.life.reap(self.time.monotonic()+2))
        self.assertTrue(helper.close())
        self.assertTrue(helper.close())

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
                if kwargs['phase']=='initial_sample': return self.reading
                if kwargs['phase']=='worker_sample':
                    self.assertIsNotNone(kwargs['worker'])
                    self.reading['gpu_pids']=[kwargs['worker'].pid]
                    with patch.object(self.sup,'_Helper',self.fake_class(mode='false')):
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


if __name__ == '__main__':
    unittest.main()
