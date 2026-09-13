import copy
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


if __name__ == '__main__':
    unittest.main()
