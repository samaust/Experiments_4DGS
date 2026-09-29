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
        from test_vipe_benchmark_s1_helper_fixtures import nested_worker_code
        code = nested_worker_code(20)
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
        from vipe_benchmark.s1_helper_session import create_owned_process,register_owned,retire_owned
        from test_vipe_benchmark_s1_helper_fixtures import fixture_process_launch,retire_fixture_processes
        workers=[]
        try:
            for _ in range(2):
                process=fixture_process_launch('existing reservation race',command,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                workers.append(process)
            # Completion waits have no invocation deadline; the preserved old
            # assertion below only reads already-completed statuses.
            for process in workers:process.wait()
            self.assertEqual(sorted(p.wait(timeout=10) for p in workers), [0, 1])
        finally:
            retire_fixture_processes(workers,sys.exception())





SUBTEST_CASES = {
 'test_vipe_benchmark_supervisor.HelperSessionTests.test_progress_plan048_pure_memo': [
  {'kind': 'snapshot_member_once'},
  {'kind': 'uncached_valid_equivalence'},
  {'kind': 'uncached_invalid_equivalence'},
  {'kind': 'same_size_restored_mtime'},
  {'kind': 'inode_replacement'},
  {'kind': 'path_replacement'},
  {'kind': 'request_changed'},
  {'kind': 'context_changed'},
  {'kind': 'identity_changed'},
  {'kind': 'source_changed'},
  {'kind': 'lookup_before_w'},
  {'kind': 'lookup_equal_w'},
  {'kind': 'lookup_after_w'},
  {'kind': 'retention_cap'},
  {'kind': 'eviction'},
  {'kind': 'failure_cleanup'},
 ],

    'test_vipe_benchmark_supervisor.HelperSessionTests.test_progress_plan047_deadline_steps': [{'operation': 'checkpoint_write', 'when': 'before'},
 {'operation': 'checkpoint_write', 'when': 'equal'},
 {'operation': 'checkpoint_write', 'when': 'after'},
 {'operation': 'checkpoint_flush', 'when': 'before'},
 {'operation': 'checkpoint_flush', 'when': 'equal'},
 {'operation': 'checkpoint_flush', 'when': 'after'},
 {'operation': 'checkpoint_fsync', 'when': 'before'},
 {'operation': 'checkpoint_fsync', 'when': 'equal'},
 {'operation': 'checkpoint_fsync', 'when': 'after'},
 {'operation': 'checkpoint_close', 'when': 'before'},
 {'operation': 'checkpoint_close', 'when': 'equal'},
 {'operation': 'checkpoint_close', 'when': 'after'},
 {'operation': 'checkpoint_readback', 'when': 'before'},
 {'operation': 'checkpoint_readback', 'when': 'equal'},
 {'operation': 'checkpoint_readback', 'when': 'after'},
 {'operation': 'head_write', 'when': 'before'},
 {'operation': 'head_write', 'when': 'equal'},
 {'operation': 'head_write', 'when': 'after'},
 {'operation': 'head_flush', 'when': 'before'},
 {'operation': 'head_flush', 'when': 'equal'},
 {'operation': 'head_flush', 'when': 'after'},
 {'operation': 'head_fsync', 'when': 'before'},
 {'operation': 'head_fsync', 'when': 'equal'},
 {'operation': 'head_fsync', 'when': 'after'},
 {'operation': 'head_close', 'when': 'before'},
 {'operation': 'head_close', 'when': 'equal'},
 {'operation': 'head_close', 'when': 'after'},
 {'operation': 'head_readback', 'when': 'before'},
 {'operation': 'head_readback', 'when': 'equal'},
 {'operation': 'head_readback', 'when': 'after'},
 {'operation': 'generation_install', 'when': 'before'},
 {'operation': 'generation_install', 'when': 'equal'},
 {'operation': 'generation_install', 'when': 'after'},
 {'operation': 'generation_dir_fsync', 'when': 'before'},
 {'operation': 'generation_dir_fsync', 'when': 'equal'},
 {'operation': 'generation_dir_fsync', 'when': 'after'},
 {'operation': 'generation_reopen_hash', 'when': 'before'},
 {'operation': 'generation_reopen_hash', 'when': 'equal'},
 {'operation': 'generation_reopen_hash', 'when': 'after'},
 {'operation': 'head_install', 'when': 'before'},
 {'operation': 'head_install', 'when': 'equal'},
 {'operation': 'head_install', 'when': 'after'},
 {'operation': 'head_dir_fsync', 'when': 'before'},
 {'operation': 'head_dir_fsync', 'when': 'equal'},
 {'operation': 'head_dir_fsync', 'when': 'after'},
 {'operation': 'final_head_read', 'when': 'before'},
 {'operation': 'final_head_read', 'when': 'equal'},
 {'operation': 'final_head_read', 'when': 'after'},
 {'operation': 'final_generation_read', 'when': 'before'},
 {'operation': 'final_generation_read', 'when': 'equal'},
 {'operation': 'final_generation_read', 'when': 'after'},
 {'operation': 'notice_send', 'when': 'before'},
 {'operation': 'notice_send', 'when': 'equal'},
 {'operation': 'notice_send', 'when': 'after'},
 {'operation': 'owner_retention', 'when': 'before'},
 {'operation': 'owner_retention', 'when': 'equal'},
 {'operation': 'owner_retention', 'when': 'after'},
 {'operation': 'ack_send', 'when': 'before'},
 {'operation': 'ack_send', 'when': 'equal'},
 {'operation': 'ack_send', 'when': 'after'},
 {'operation': 'ack_receipt', 'when': 'before'},
 {'operation': 'ack_receipt', 'when': 'equal'},
 {'operation': 'ack_receipt', 'when': 'after'},
 {'operation': 'array_npy', 'when': 'before'},
 {'operation': 'array_npy', 'when': 'equal'},
 {'operation': 'array_npy', 'when': 'after'},
 {'operation': 'array_png', 'when': 'before'},
 {'operation': 'array_png', 'when': 'equal'},
 {'operation': 'array_png', 'when': 'after'},
 {'operation': 'npz_member', 'when': 'before'},
 {'operation': 'npz_member', 'when': 'equal'},
 {'operation': 'npz_member', 'when': 'after'},
 {'operation': 'npz_finalize', 'when': 'before'},
 {'operation': 'npz_finalize', 'when': 'equal'},
 {'operation': 'npz_finalize', 'when': 'after'},
 {'operation': 'array_hash', 'when': 'before'},
 {'operation': 'array_hash', 'when': 'equal'},
 {'operation': 'array_hash', 'when': 'after'},
 {'operation': 'produced_json', 'when': 'before'},
 {'operation': 'produced_json', 'when': 'equal'},
 {'operation': 'produced_json', 'when': 'after'},
 {'operation': 'produced_read', 'when': 'before'},
 {'operation': 'produced_read', 'when': 'equal'},
 {'operation': 'produced_read', 'when': 'after'},
 {'operation': 'produced_guard', 'when': 'before'},
 {'operation': 'produced_guard', 'when': 'equal'},
 {'operation': 'produced_guard', 'when': 'after'},
 {'operation': 'qualified_guard', 'when': 'before'},
 {'operation': 'qualified_guard', 'when': 'equal'},
 {'operation': 'qualified_guard', 'when': 'after'},
 {'operation': 'first_guard', 'when': 'before'},
 {'operation': 'first_guard', 'when': 'equal'},
 {'operation': 'first_guard', 'when': 'after'},
 {'operation': 'runtime_guard', 'when': 'before'},
 {'operation': 'runtime_guard', 'when': 'equal'},
 {'operation': 'runtime_guard', 'when': 'after'},
 {'operation': 'reuse_after_read', 'when': 'before'},
 {'operation': 'reuse_after_read', 'when': 'equal'},
 {'operation': 'reuse_after_read', 'when': 'after'},
 {'operation': 'cleanup_next_array', 'when': 'before'},
 {'operation': 'cleanup_next_array', 'when': 'equal'},
 {'operation': 'cleanup_next_array', 'when': 'after'},
 {'operation': 'accept_after_read', 'when': 'before'},
 {'operation': 'accept_after_read', 'when': 'equal'},
 {'operation': 'accept_after_read', 'when': 'after'},
 {'operation': 'complete_after_read', 'when': 'before'},
 {'operation': 'complete_after_read', 'when': 'equal'},
 {'operation': 'complete_after_read', 'when': 'after'},
 {'operation': 'next_input', 'when': 'before'},
 {'operation': 'next_input', 'when': 'equal'},
 {'operation': 'next_input', 'when': 'after'},
 {'operation': 'worker_popen', 'when': 'before'},
 {'operation': 'worker_popen', 'when': 'equal'},
 {'operation': 'worker_popen', 'when': 'after'}],
    'test_vipe_benchmark_supervisor.HelperSessionTests.test_progress_plan047_ownership': [{'kind': 'paired_env_runner_root'},
 {'kind': 'paired_env_foreign_output'},
 {'kind': 'stale_dispatch016'},
 {'kind': 'forged_dispatch_env'},
 {'kind': 'capture_omitted'},
 {'kind': 'stdin_inode_replaced'},
 {'kind': 'capture_argv_swapped'},
 {'kind': 'driver_log_inode_swapped'},
 {'kind': 'ancestor_empty'},
 {'kind': 'ancestor_truncated'},
 {'kind': 'ancestor_cycle'},
 {'kind': 'ancestor_terminal_changed'},
 {'kind': 'detached_grandchild'},
 {'kind': 'retained_pid_reuse'},
 {'kind': 'registry_owner_dispatch'},
 {'kind': 'registry_worker_dispatch'},
 {'kind': 'registry_direct_dispatch'},
 {'kind': 'registry_sentinel_dispatch'},
 {'kind': 'registry_missing_enumeration'},
 {'kind': 'test_glob_addition'},
 {'kind': 'test_glob_omission'},
 {'kind': 'wrapper_unproven'},
 {'kind': 'wrapper_one_thread'},
 {'kind': 'wrapper_two_threads'},
 {'kind': 'no_wrapper_reserve'}],
    'test_vipe_benchmark_supervisor.HelperSessionTests.test_progress_plan047_limits': [{'limit': 'inventory_depth', 'value': 3},
 {'limit': 'inventory_depth', 'value': 4},
 {'limit': 'inventory_depth', 'value': 5},
 {'limit': 'variants', 'value': 3},
 {'limit': 'variants', 'value': 4},
 {'limit': 'variants', 'value': 5},
 {'limit': 'identities', 'value': 509},
 {'limit': 'identities', 'value': 510},
 {'limit': 'identities', 'value': 511},
 {'limit': 'candidates', 'value': 2047},
 {'limit': 'candidates', 'value': 2048},
 {'limit': 'candidates', 'value': 2049},
 {'limit': 'inventory_sources', 'value': 2047},
 {'limit': 'inventory_sources', 'value': 2048},
 {'limit': 'inventory_sources', 'value': 2049},
 {'limit': 'directory_entries', 'value': 4095},
 {'limit': 'directory_entries', 'value': 4096},
 {'limit': 'directory_entries', 'value': 4097},
 {'limit': 'embedded_refs', 'value': 4095},
 {'limit': 'embedded_refs', 'value': 4096},
 {'limit': 'embedded_refs', 'value': 4097},
 {'limit': 'metadata_bytes', 'value': 33554431},
 {'limit': 'metadata_bytes', 'value': 33554432},
 {'limit': 'metadata_bytes', 'value': 33554433},
 {'limit': 'row_bytes', 'value': 262143},
 {'limit': 'row_bytes', 'value': 262144},
 {'limit': 'row_bytes', 'value': 262145},
 {'limit': 'path_utf8_bytes', 'value': 2047},
 {'limit': 'path_utf8_bytes', 'value': 2048},
 {'limit': 'path_utf8_bytes', 'value': 2049},
 {'limit': 'checkpoint_bytes', 'value': 1048575},
 {'limit': 'checkpoint_bytes', 'value': 1048576},
 {'limit': 'checkpoint_bytes', 'value': 1048577},
 {'limit': 'checkpoint_depth', 'value': 11},
 {'limit': 'checkpoint_depth', 'value': 12},
 {'limit': 'checkpoint_depth', 'value': 13},
 {'limit': 'checkpoint_nodes', 'value': 65535},
 {'limit': 'checkpoint_nodes', 'value': 65536},
 {'limit': 'checkpoint_nodes', 'value': 65537},
 {'limit': 'producer_generations', 'value': 1023},
 {'limit': 'producer_generations', 'value': 1024},
 {'limit': 'producer_generations', 'value': 1025},
 {'limit': 'total_generations', 'value': 2047},
 {'limit': 'total_generations', 'value': 2048},
 {'limit': 'total_generations', 'value': 2049},
 {'limit': 'committed_bytes', 'value': 2147483647},
 {'limit': 'committed_bytes', 'value': 2147483648},
 {'limit': 'committed_bytes', 'value': 2147483649},
 {'limit': 'tree_entries', 'value': 2056},
 {'limit': 'tree_entries', 'value': 2057},
 {'limit': 'tree_entries', 'value': 2058},
 {'limit': 'retained_bytes', 'value': 4194303},
 {'limit': 'retained_bytes', 'value': 4194304},
 {'limit': 'retained_bytes', 'value': 4194305},
 {'limit': 'context_bytes', 'value': 8191},
 {'limit': 'context_bytes', 'value': 8192},
 {'limit': 'context_bytes', 'value': 8193},
 {'limit': 'head_bytes', 'value': 8191},
 {'limit': 'head_bytes', 'value': 8192},
 {'limit': 'head_bytes', 'value': 8193},
 {'limit': 'reference_bytes', 'value': 8191},
 {'limit': 'reference_bytes', 'value': 8192},
 {'limit': 'reference_bytes', 'value': 8193},
 {'limit': 'control_bytes', 'value': 4095},
 {'limit': 'control_bytes', 'value': 4096},
 {'limit': 'control_bytes', 'value': 4097},
 {'limit': 'result_bytes', 'value': 33554431},
 {'limit': 'result_bytes', 'value': 33554432},
 {'limit': 'result_bytes', 'value': 33554433},
 {'limit': 'result_depth', 'value': 63},
 {'limit': 'result_depth', 'value': 64},
 {'limit': 'result_depth', 'value': 65},
 {'limit': 'result_nodes', 'value': 1048575},
 {'limit': 'result_nodes', 'value': 1048576},
 {'limit': 'result_nodes', 'value': 1048577},
 {'limit': 'error_count', 'value': 31},
 {'limit': 'error_count', 'value': 32},
 {'limit': 'error_count', 'value': 33},
 {'limit': 'error_utf8_bytes', 'value': 1023},
 {'limit': 'error_utf8_bytes', 'value': 1024},
 {'limit': 'error_utf8_bytes', 'value': 1025},
 {'limit': 'socket_address_bytes', 'value': 95},
 {'limit': 'socket_address_bytes', 'value': 96},
 {'limit': 'socket_address_bytes', 'value': 97}],
    'test_vipe_benchmark_supervisor.HelperSessionTests.test_progress_plan047_alias_inventory': [{'kind': 'leaf_symlink'},
 {'kind': 'component_symlink'},
 {'kind': 'dot_alias'},
 {'kind': 'dotdot_traversal'},
 {'kind': 'repeated_separator'},
 {'kind': 'hardlink_duplicate'},
 {'kind': 'hardlink_external'},
 {'kind': 'foreign_candidate_root'},
 {'kind': 'fifo_candidate'},
 {'kind': 'directory_candidate'},
 {'kind': 'descriptor_replacement'},
 {'kind': 'row_bytes_closure'},
 {'kind': 'result_bytes_closure'},
 {'kind': 'member_add_closure'},
 {'kind': 'member_remove_closure'},
 {'kind': 'member_rename_closure'},
 {'kind': 'parent_replace_closure'},
 {'kind': 'member_add_after_publish'},
 {'kind': 'member_remove_after_publish'},
 {'kind': 'member_rename_after_publish'},
 {'kind': 'result_replace_after_publish'},
 {'kind': 'row_replace_after_publish'}],
    'test_vipe_benchmark_supervisor.HelperSessionTests.test_progress_plan047_nested': [{'field': 'schema', 'mutation': 'missing', 'target': 'context'},
 {'field': 'schema', 'mutation': 'extra', 'target': 'context'},
 {'field': 'schema', 'mutation': 'wrong_container', 'target': 'context'},
 {'field': 'request', 'mutation': 'missing', 'target': 'context.clock'},
 {'field': 'request', 'mutation': 'extra', 'target': 'context.clock'},
 {'field': 'request', 'mutation': 'wrong_container', 'target': 'context.clock'},
 {'field': 'sha256', 'mutation': 'missing', 'target': 'context.clock.request'},
 {'field': 'sha256', 'mutation': 'extra', 'target': 'context.clock.request'},
 {'field': 'sha256', 'mutation': 'wrong_container', 'target': 'context.clock.request'},
 {'field': 'sequence', 'mutation': 'missing', 'target': 'context.clock.reservation'},
 {'field': 'sequence', 'mutation': 'extra', 'target': 'context.clock.reservation'},
 {'field': 'sequence', 'mutation': 'wrong_container', 'target': 'context.clock.reservation'},
 {'field': 'path', 'mutation': 'missing', 'target': 'context.authorization'},
 {'field': 'path', 'mutation': 'extra', 'target': 'context.authorization'},
 {'field': 'path', 'mutation': 'wrong_container', 'target': 'context.authorization'},
 {'field': 'pid', 'mutation': 'missing', 'target': 'context.work'},
 {'field': 'pid', 'mutation': 'extra', 'target': 'context.work'},
 {'field': 'pid', 'mutation': 'wrong_container', 'target': 'context.work'},
 {'field': 'guard', 'mutation': 'missing', 'target': 'context.sources'},
 {'field': 'guard', 'mutation': 'extra', 'target': 'context.sources'},
 {'field': 'guard', 'mutation': 'wrong_container', 'target': 'context.sources'},
 {'field': 'bytes', 'mutation': 'missing', 'target': 'context.sources.guard'},
 {'field': 'bytes', 'mutation': 'extra', 'target': 'context.sources.guard'},
 {'field': 'bytes', 'mutation': 'wrong_container', 'target': 'context.sources.guard'},
 {'field': 'producer', 'mutation': 'missing', 'target': 'checkpoint'},
 {'field': 'producer', 'mutation': 'extra', 'target': 'checkpoint'},
 {'field': 'producer', 'mutation': 'wrong_container', 'target': 'checkpoint'},
 {'field': 'start_ticks', 'mutation': 'missing', 'target': 'checkpoint.binding'},
 {'field': 'start_ticks', 'mutation': 'extra', 'target': 'checkpoint.binding'},
 {'field': 'start_ticks', 'mutation': 'wrong_container', 'target': 'checkpoint.binding'},
 {'field': 'path', 'mutation': 'missing', 'target': 'checkpoint.previous'},
 {'field': 'path', 'mutation': 'extra', 'target': 'checkpoint.previous'},
 {'field': 'path', 'mutation': 'wrong_container', 'target': 'checkpoint.previous'},
 {'field': 'identity', 'mutation': 'missing', 'target': 'checkpoint.rows.0'},
 {'field': 'identity', 'mutation': 'extra', 'target': 'checkpoint.rows.0'},
 {'field': 'identity', 'mutation': 'wrong_container', 'target': 'checkpoint.rows.0'},
 {'field': 'branch', 'mutation': 'missing', 'target': 'checkpoint.rows.0.identity'},
 {'field': 'branch', 'mutation': 'extra', 'target': 'checkpoint.rows.0.identity'},
 {'field': 'branch', 'mutation': 'wrong_container', 'target': 'checkpoint.rows.0.identity'},
 {'field': 'sha256', 'mutation': 'missing', 'target': 'checkpoint.rows.0.row'},
 {'field': 'sha256', 'mutation': 'extra', 'target': 'checkpoint.rows.0.row'},
 {'field': 'sha256', 'mutation': 'wrong_container', 'target': 'checkpoint.rows.0.row'},
 {'field': 'version', 'mutation': 'missing', 'target': 'checkpoint.rows.0.authority'},
 {'field': 'version', 'mutation': 'extra', 'target': 'checkpoint.rows.0.authority'},
 {'field': 'version', 'mutation': 'wrong_container', 'target': 'checkpoint.rows.0.authority'},
 {'field': 'bytes', 'mutation': 'missing', 'target': 'checkpoint.sources.0'},
 {'field': 'bytes', 'mutation': 'extra', 'target': 'checkpoint.sources.0'},
 {'field': 'bytes', 'mutation': 'wrong_container', 'target': 'checkpoint.sources.0'},
 {'field': 'dropped', 'mutation': 'missing', 'target': 'checkpoint.diagnostics'},
 {'field': 'dropped', 'mutation': 'extra', 'target': 'checkpoint.diagnostics'},
 {'field': 'dropped', 'mutation': 'wrong_container', 'target': 'checkpoint.diagnostics'},
 {'field': 'message', 'mutation': 'missing', 'target': 'checkpoint.diagnostics.first'},
 {'field': 'message', 'mutation': 'extra', 'target': 'checkpoint.diagnostics.first'},
 {'field': 'message', 'mutation': 'wrong_container', 'target': 'checkpoint.diagnostics.first'},
 {'field': 'observed', 'mutation': 'missing', 'target': 'checkpoint.diagnostics.last'},
 {'field': 'observed', 'mutation': 'extra', 'target': 'checkpoint.diagnostics.last'},
 {'field': 'observed', 'mutation': 'wrong_container', 'target': 'checkpoint.diagnostics.last'},
 {'field': 'error_class', 'mutation': 'missing', 'target': 'checkpoint.diagnostics.primary'},
 {'field': 'error_class', 'mutation': 'extra', 'target': 'checkpoint.diagnostics.primary'},
 {'field': 'error_class', 'mutation': 'wrong_container', 'target': 'checkpoint.diagnostics.primary'},
 {'field': 'qualified', 'mutation': 'missing', 'target': 'checkpoint.counts'},
 {'field': 'qualified', 'mutation': 'extra', 'target': 'checkpoint.counts'},
 {'field': 'qualified', 'mutation': 'wrong_container', 'target': 'checkpoint.counts'},
 {'field': 'path', 'mutation': 'missing', 'target': 'checkpoint.runtime.final'},
 {'field': 'path', 'mutation': 'extra', 'target': 'checkpoint.runtime.final'},
 {'field': 'path', 'mutation': 'wrong_container', 'target': 'checkpoint.runtime.final'},
 {'field': 'current', 'mutation': 'missing', 'target': 'head'},
 {'field': 'current', 'mutation': 'extra', 'target': 'head'},
 {'field': 'current', 'mutation': 'wrong_container', 'target': 'head'},
 {'field': 'sha256', 'mutation': 'missing', 'target': 'head.current'},
 {'field': 'sha256', 'mutation': 'extra', 'target': 'head.current'},
 {'field': 'sha256', 'mutation': 'wrong_container', 'target': 'head.current'},
 {'field': 'head', 'mutation': 'missing', 'target': 'notice'},
 {'field': 'head', 'mutation': 'extra', 'target': 'notice'},
 {'field': 'head', 'mutation': 'wrong_container', 'target': 'notice'},
 {'field': 'pgid', 'mutation': 'missing', 'target': 'notice.binding'},
 {'field': 'pgid', 'mutation': 'extra', 'target': 'notice.binding'},
 {'field': 'pgid', 'mutation': 'wrong_container', 'target': 'notice.binding'},
 {'field': 'bytes', 'mutation': 'missing', 'target': 'notice.head'},
 {'field': 'bytes', 'mutation': 'extra', 'target': 'notice.head'},
 {'field': 'bytes', 'mutation': 'wrong_container', 'target': 'notice.head'},
 {'field': 'sequence', 'mutation': 'missing', 'target': 'ack'},
 {'field': 'sequence', 'mutation': 'extra', 'target': 'ack'},
 {'field': 'sequence', 'mutation': 'wrong_container', 'target': 'ack'},
 {'field': 'path', 'mutation': 'missing', 'target': 'ack.current'},
 {'field': 'path', 'mutation': 'extra', 'target': 'ack.current'},
 {'field': 'path', 'mutation': 'wrong_container', 'target': 'ack.current'},
 {'field': 'provenance', 'mutation': 'missing', 'target': 'reference'},
 {'field': 'provenance', 'mutation': 'extra', 'target': 'reference'},
 {'field': 'provenance', 'mutation': 'wrong_container', 'target': 'reference'},
 {'field': 'event_sha256', 'mutation': 'missing', 'target': 'reference.reservation'},
 {'field': 'event_sha256', 'mutation': 'extra', 'target': 'reference.reservation'},
 {'field': 'event_sha256', 'mutation': 'wrong_container', 'target': 'reference.reservation'},
 {'field': 'accepted_head', 'mutation': 'missing', 'target': 'reference.provenance.worker'},
 {'field': 'accepted_head', 'mutation': 'extra', 'target': 'reference.provenance.worker'},
 {'field': 'accepted_head', 'mutation': 'wrong_container', 'target': 'reference.provenance.worker'},
 {'field': 'sha256', 'mutation': 'missing', 'target': 'reference.provenance.worker.accepted_head'},
 {'field': 'sha256', 'mutation': 'extra', 'target': 'reference.provenance.worker.accepted_head'},
 {'field': 'sha256', 'mutation': 'wrong_container', 'target': 'reference.provenance.worker.accepted_head'},
 {'field': 'previous', 'mutation': 'missing', 'target': 'reference.provenance.worker.intended_successor'},
 {'field': 'previous', 'mutation': 'extra', 'target': 'reference.provenance.worker.intended_successor'},
 {'field': 'previous', 'mutation': 'wrong_container', 'target': 'reference.provenance.worker.intended_successor'},
 {'field': 'pid', 'mutation': 'missing', 'target': 'reference.provenance.worker.intended_successor.binding'},
 {'field': 'pid', 'mutation': 'extra', 'target': 'reference.provenance.worker.intended_successor.binding'},
 {'field': 'pid', 'mutation': 'wrong_container', 'target': 'reference.provenance.worker.intended_successor.binding'},
 {'field': 'value', 'mutation': 'missing', 'target': 'summary.runtime.final'},
 {'field': 'value', 'mutation': 'extra', 'target': 'summary.runtime.final'},
 {'field': 'value', 'mutation': 'wrong_container', 'target': 'summary.runtime.final'},
 {'field': 'status', 'mutation': 'missing', 'target': 'summary.first_result'},
 {'field': 'status', 'mutation': 'extra', 'target': 'summary.first_result'},
 {'field': 'status', 'mutation': 'wrong_container', 'target': 'summary.first_result'}],
    'test_vipe_benchmark_supervisor.HelperSessionTests.test_progress_plan047_state_authority': [{'kind': 'produced_then_semantic_failure'},
 {'kind': 'first_identity_semantics'},
 {'kind': 'worker_reuse_exact'},
 {'kind': 'worker_stale_interleave'},
 {'kind': 'worker_future_reference'},
 {'kind': 'worker_self_reference'},
 {'kind': 'worker_qualified_overclaim'},
 {'kind': 'worker_sources_changed'},
 {'kind': 'worker_row_version_changed'},
 {'kind': 'worker_detached_identity'},
 {'kind': 'trusted_conflict'},
 {'kind': 'discovered_conflict'},
 {'kind': 'fallback_no_unique_version'},
 {'kind': 'fallback_invalidated'},
 {'kind': 'conflict_to_closed'},
 {'kind': 'overflow_to_closed'},
 {'kind': 'overflow_to_incomplete'},
 {'kind': 'conflict_plus_overflow'},
 {'kind': 'errors_saturation'},
 {'kind': 'diagnostics_drop_regression'},
 {'kind': 'diagnostics_primary_replaced'},
 {'kind': 'checkpoint_v1_rejected'},
 {'kind': 'qualification_regression'},
 {'kind': 'first_runtime_regression'},
 {'kind': 'acceptance_regression'},
 {'kind': 'duplicate_exact'},
 {'kind': 'duplicate_conflict'},
 {'kind': 'sequence_replay'},
 {'kind': 'sequence_jump'},
 {'kind': 'request_changed_late'}],
    'test_vipe_benchmark_supervisor.HelperSessionTests.test_progress_plan047_recovery': [{'kind': 'accepted_exact'},
 {'kind': 'optional_valid_successor'},
 {'kind': 'optional_successor_body_missing'},
 {'kind': 'optional_successor_body_truncated'},
 {'kind': 'optional_successor_head_truncated'},
 {'kind': 'head_missing_no_intent'},
 {'kind': 'head_truncated_no_intent'},
 {'kind': 'accepted_body_missing'},
 {'kind': 'accepted_body_changed'},
 {'kind': 'accepted_head_changed'},
 {'kind': 'head_regressed'},
 {'kind': 'context_changed'},
 {'kind': 'foreign_provenance'},
 {'kind': 'unacknowledged_only'},
 {'kind': 'history_tripwire'},
 {'kind': 'current_previous_retention'},
 {'kind': 'late_recovery'}],
    'test_vipe_benchmark_supervisor.HelperSessionTests.test_progress_plan047_cancellation': [{'stage': 'dequeue', 'when': 'before'},
 {'stage': 'dequeue', 'when': 'after'},
 {'stage': 'credentials', 'when': 'before'},
 {'stage': 'credentials', 'when': 'after'},
 {'stage': 'context_read', 'when': 'before'},
 {'stage': 'context_read', 'when': 'after'},
 {'stage': 'old_checkpoint_read', 'when': 'before'},
 {'stage': 'old_checkpoint_read', 'when': 'after'},
 {'stage': 'head_read', 'when': 'before'},
 {'stage': 'head_read', 'when': 'after'},
 {'stage': 'new_checkpoint_read', 'when': 'before'},
 {'stage': 'new_checkpoint_read', 'when': 'after'},
 {'stage': 'worker_authority_read', 'when': 'before'},
 {'stage': 'worker_authority_read', 'when': 'after'},
 {'stage': 'retention', 'when': 'before'},
 {'stage': 'retention', 'when': 'after'},
 {'stage': 'ack_send', 'when': 'before'},
 {'stage': 'ack_send', 'when': 'after'},
 {'stage': 'ack_receipt', 'when': 'before'},
 {'stage': 'ack_receipt', 'when': 'after'}],
    'test_vipe_benchmark_supervisor.HelperSessionTests.test_progress_plan047_result_summary': [{'kind': 'result_duplicate_top'},
 {'kind': 'result_duplicate_row'},
 {'kind': 'result_nonfinite'},
 {'kind': 'result_supplied_bool_int'},
 {'kind': 'result_full510'},
 {'kind': 'runtime_unverified_nonnull'},
 {'kind': 'runtime_verified_null'},
 {'kind': 'runtime_unknown_status'},
 {'kind': 'first_unverified_nonnull'},
 {'kind': 'runtime_final_conflict'},
 {'kind': 'runtime_alias'},
 {'kind': 'summary_unknown_totals'},
 {'kind': 'notice_bool_pid'},
 {'kind': 'notice_bool_request'},
 {'kind': 'ack_bool_sequence'},
 {'kind': 'clock_bool_start'},
 {'kind': 'clock_negative_time'},
 {'kind': 'clock_overflow_time'},
 {'kind': 'clock_nonfinite'},
 {'kind': 'reservation_bool_sequence'},
 {'kind': 'process_pid_bound'},
 {'kind': 'identity_bool_camera'},
 {'kind': 'identity_wrong_branch'},
 {'kind': 'identity_pair_nonnull'},
 {'kind': 'identity_order_duplicate'},
 {'kind': 'indices_bool'},
 {'kind': 'indices_duplicate'},
 {'kind': 'indices_out_of_range'},
 {'kind': 'context_wrong_boot'},
 {'kind': 'context_wrong_guard'},
 {'kind': 'notice_wrong_uid'},
 {'kind': 'notice_wrong_pid'},
 {'kind': 'notice_wrong_sender'},
 {'kind': 'notice_truncated'},
 {'kind': 'notice_missing_credentials'},
 {'kind': 'ack_wrong_binding'},
 {'kind': 'reference_v1_rejected'},
 {'kind': 'reference_bool_frozen'},
 {'kind': 'reference_wrong_reservation'}],
    'test_vipe_benchmark_supervisor.HelperSessionTests.test_progress_plan047_complete_final_sample': [{'kind': 'success'}, {'kind': 'final_sample_failure'}],
    'test_vipe_benchmark_supervisor.HelperSessionTests.test_progress_plan047_publication_faults': [{'kind': 'checkpoint_open'},
 {'kind': 'checkpoint_write_short'},
 {'kind': 'checkpoint_flush'},
 {'kind': 'checkpoint_fsync'},
 {'kind': 'checkpoint_close'},
 {'kind': 'checkpoint_readback'},
 {'kind': 'head_open'},
 {'kind': 'head_write_short'},
 {'kind': 'head_flush'},
 {'kind': 'head_fsync'},
 {'kind': 'head_close'},
 {'kind': 'head_readback'},
 {'kind': 'generation_collision_exact'},
 {'kind': 'generation_collision_changed'},
 {'kind': 'generation_dir_fsync'},
 {'kind': 'head_dir_fsync'},
 {'kind': 'final_generation_readback'},
 {'kind': 'final_head_readback'},
 {'kind': 'ack_send_short'},
 {'kind': 'ack_send_late'},
 {'kind': 'ack_receive_late'},
 {'kind': 'owner_retention_error'}],
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
        from vipe_benchmark.s1_helper_session import create_owned_process,register_owned,retire_owned
        from test_vipe_benchmark_s1_helper_fixtures import fixture_process_launch,retire_fixture_processes
        process=None
        try:
            process=fixture_process_launch('existing helper runner',command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)
            stdout,stderr=process.communicate()
            result=subprocess.CompletedProcess(command,process.returncode,stdout,stderr)
        finally:
            if process is not None:retire_fixture_processes([process],sys.exception())
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
        from test_vipe_benchmark_s1_helper_fixtures import fixture_process_launch,retire_fixture_processes
        process=fixture_process_launch('existing helper-test worker',[sys.executable,'-c',code],start_new_session=True)
        self.addCleanup(lambda:retire_fixture_processes([process],sys.exception(),stop=lambda value:self.sup.stop_group(value,self.time.monotonic()+1)))
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
        from test_vipe_benchmark_s1_helper_fixtures import nested_worker_code
        process = self.worker(nested_worker_code(10,parent_wait=True))
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
            observed_calls=Trace(128);timing_failures=[]
            record=dict(scenario=label,mode=mode,constructor_entry=started,action_cutoff=action_cutoff,safety_cutoff=safety_cutoff)
            try:
                session(mode,instance=current,**bounds)
                current.fixture_action_end=action_cutoff; current.fixture_safety_end=safety_cutoff
                observed_calls=Trace(128)
                timing_failures=[]
                def observe_call(name,operation):
                    def observed(*args,**kwargs):
                        deadline=args[0] if name in ('tick','close') else current.ready_deadline
                        effective=min(deadline,safety_cutoff if name=='close' else action_cutoff)
                        if name=='tick' and current.requests['sample'] is not None:
                            effective=min(effective,current.requests['sample']['deadline'])
                        entered=self.time.monotonic();result=None;error=None;ready_before=sorted(getattr(current,'ready',{}))
                        try:
                            result=operation(*args,**kwargs);return result
                        except BaseException as exc:
                            error=type(exc).__name__+': '+str(exc);raise
                        finally:
                            returned=self.time.monotonic()
                            observed_calls.append(dict(operation=name,entered=entered,deadline=effective,returned=returned,
                                confirmed=result if name=='close' else None,error=error,ready_before=ready_before,ready_after=sorted(getattr(current,'ready',{}))))
                            # Save the original pending exception before checking timing.
                            try:self.assertLessEqual(returned,effective+.1)
                            except AssertionError as violation:
                                timing_failures.append(dict(operation=name,message=str(violation),returned=returned,deadline=effective))
                    return observed
                current.tick=observe_call('tick',current.tick)
                current.close=observe_call('close',current.close)
                current.await_ready=observe_call('await_ready',current.await_ready)
                record.update(constructor_end=self.time.monotonic(),t0=current.t0,
                    ready_deadline=current.ready_deadline,setup_deadline=current.setup_deadline,setup_cleanup_deadline=current.cleanup_deadline)
                yield current
            finally:
                pending=sys.exception()
                secondary=[];cleaned=False;action_end=self.time.monotonic();ended=action_end
                def secondary_step(label,operation):
                    try:return operation()
                    except BaseException as error:
                        item=dict(operation=label,error_class=type(error).__name__,message=str(error)[:2048])
                        if len(secondary)<32:secondary.append(item)
                        else:record['secondary_overflow']=record.get('secondary_overflow',0)+1
                        if pending is not None:
                            pending.add_note(label+': '+item['error_class']+': '+item['message'])
                            pending.scenario_secondary=list(secondary)
                        return None
                def close_owned():
                    nonlocal cleaned,ended
                    owner=getattr(current,'owner',None)
                    if owner is not None:owner.released=True
                    cleaned=current.close(safety_cutoff)
                    ended=self.time.monotonic()
                secondary_step('lifecycle_close',close_owned)
                def assemble_record():
                    owner=getattr(current,'owner',None)
                    if label in ('P01','P02','P03','P04','P05','P06'):
                        final=next((event for event in reversed(list(current.events)) if event.get('event')=='progress_final_outcome'),None)
                        if final is None:
                            final=dict(event='progress_final_outcome',label=label,phase='startup_or_fixture_preparation',
                                primary=None if pending is None else dict(error_class=type(pending).__name__,message=str(pending)),
                                secondary=list(secondary),reference=None if not hasattr(current,'progress_cache') else current.progress_cache.reference(),
                                cleanup_confirmed=cleaned,observed=ended,causal_status='actual startup failure; no inferred EPERM cause')
                            current.events.append(final)
                        record['progress_final_outcome']=final
                    record.update(action_end=action_end,end=ended,execution_seconds=action_end-started,
                        cleanup_seconds=ended-action_end,cleanup_confirmed=cleaned,
                        records={} if owner is None else owner.records,errors=[] if owner is None else list(owner.errors),
                        signals=[] if owner is None else list(owner.signals),ticks=list(current.ticks),events=list(current.events),
                        trace_facts=current.events.facts(),tick_facts=current.ticks.facts(),
                        owner_error_facts=None if owner is None else owner.errors.facts(),owner_signal_facts=None if owner is None else owner.signals.facts(),
                        request_counts={role:dict(dispatch=current.dispatch_counts[role].value,response=current.response_counts[role].value) for role in current.requests},
                        census_request_count=current.census_requests.value,max_gap=current.max_gap,max_turn=current.max_turn,
                        call_observations=list(observed_calls),call_observation_facts=observed_calls.facts(),
                        timing_failures=timing_failures,
                        last_sample=current.last_sample,requests=current.requests,
                        ownership=current.ownership(),wire={role:dict(sent=w.sent_bytes,received=w.received_bytes,blocked_writes=w.blocked_writes,peek=w.peek_bytes.value,combined=w.combined_bytes.value,last_frame=w.last_frame) for role,w in current.wires.items()})
                secondary_step('record_assembly',assemble_record)
                directory=secondary_step('scenario_destination',lambda:Path(os.environ['S1_VALIDATION_RUN_DIRECTORY']))
                def persist_record():
                    record['secondary']=list(secondary)
                    with (directory/('scenario-'+label+'.json')).open('x') as stream:
                        json.dump(record,stream,indent=2,default=lambda v:asdict(v) if is_dataclass(v) else list(v));stream.write('\n')
                secondary_step('scenario_record_write',persist_record)
                def check_0():
                    self.assertTrue(cleaned,record)
                secondary_step('timing_or_cleanup_check_0',check_0)
                def check_1():
                    self.assertLessEqual(action_end-started,2)
                secondary_step('timing_or_cleanup_check_1',check_1)
                def check_2():
                    self.assertLessEqual(ended-action_end,1)
                secondary_step('timing_or_cleanup_check_2',check_2)
                def check_3():
                    self.assertLessEqual(ended-started,3)
                secondary_step('timing_or_cleanup_check_3',check_3)
                def check_4():
                    self.assertEqual(timing_failures,[],record)
                secondary_step('timing_or_cleanup_check_4',check_4)
                if secondary:
                    def persist_secondary():
                        with (directory/('scenario-'+label+'-secondary.json')).open('x') as stream:
                            json.dump(dict(primary_class=None if pending is None else type(pending).__name__,
                                primary_text=None if pending is None else str(pending),secondary=list(secondary)),stream)
                    secondary_step('scenario_secondary_write',persist_secondary)
                    # Already-authorized enclosing receipt gets in-memory evidence
                    # even if both evidence destinations failed; never recurse.
                    self.scenario_secondary=list(secondary)
                    if pending is not None:pending.scenario_secondary=list(secondary)
                    else:raise AssertionError('scenario cleanup/timing failures: '+repr(secondary))
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
            self.assertTrue(any(event['event']=='opaque_spawn_return_held' and event['mode']=='late_spawn' for event in session.events))
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
        from vipe_benchmark.s1_helper_session import census,predispatch_owned,register_owned,retire_owned,create_owned_process
        with self.scenario('L18','descendant') as session:
            session.await_ready()
            if os.environ.get('S1_OWNED_ROOT_NOTE'):predispatch_owned('L18 sentinel')
            from test_vipe_benchmark_s1_helper_fixtures import l18_sentinel_launch
            sentinel=l18_sentinel_launch()
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
                    if os.waitpid(sentinel,os.WNOHANG)[0]:retire_owned(sentinel);break
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
        from test_vipe_benchmark_s1_recovery import S1RecoveryTests
        with tempfile.TemporaryDirectory() as temp:
            fixture=S1RecoveryTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
            _,request,binding=fixture.register();command=fixture.command(binding)
            reservation=fixture.ledger.reserve('S1-calibration-recovery-001',command,binding)
            self.assertEqual(fixture.ledger.events()[-1],reservation)
            local=fixture.root;(local/'jobs'/'S1-calibration-recovery-001').mkdir(parents=True)
            with self.scenario('L24','artifact') as session:
                session.await_ready()
                session.events.append(dict(event='actual_summary_reserve',reservation=reservation,command=command))
                operation=dict(operation='constant',args=dict(value=dict(local=str(local),reservation=reservation,command=command)))
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
            calls=[];reserve_entries=[]
            with tempfile.TemporaryDirectory() as temp:
                class Disposable:
                    jobs={'S1-calibration-recovery-001':dict(resource='gpu')}
                    config=load()
                    @property
                    def reserve(inner):
                        self.assertTrue(session.accepted_initial)
                        self.assertIsNotNone(session.last_sample)
                        reserve_entries.append(dict(boundary='actual_reserve_descriptor',observed=self.time.monotonic(),deadline=session.setup_deadline))
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
                self.assertEqual(len(reserve_entries),1)
                session.events.append(dict(event='admission_predecessor',entries=reserve_entries))
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
            from vipe_benchmark.s1_helper_session import owned_workload,register_owned,create_owned_process
            if os.environ.get('S1_OWNED_ROOT_NOTE'):
                self.assertLessEqual(owned_workload(os.environ['S1_OWNED_ROOT_NOTE'])['total_workers']+1,8)
            from test_vipe_benchmark_s1_helper_fixtures import fixture_process_launch,retire_fixture_processes
            worker=fixture_process_launch('scenario sentinel',[sys.executable,'-B','-c',code],start_new_session=True,env=dict(os.environ,OPENCV_FOR_THREADS_NUM='1'))
            try:yield worker
            finally:
                pending=sys.exception();secondary=[]
                try:session.retire_worker()
                except BaseException as error:secondary.append(error)
                def stop(process):
                    self.assertEqual(sup.stop_group(worker,session.fixture_action_end),[])
                try:retire_fixture_processes([worker],pending,stop=stop)
                except BaseException as error:secondary.append(error)
                if secondary:
                    if pending is not None:
                        for error in secondary:pending.add_note('scenario worker cleanup: '+repr(error))
                        pending.s1_cleanup_errors=tuple(secondary)
                    else:raise secondary[0]
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
            code=("import sys,time\nfrom pathlib import Path\n"+f"sys.path.insert(0,{str(Path(__file__).resolve().parent)!r})\n"+"from test_vipe_benchmark_s1_helper_fixtures import fixture_process_launch,retire_fixture_processes\n"
                "p=None\ntry:\n p=fixture_process_launch('existing detached descendant',[sys.executable,'-B','-c','import time; time.sleep(10)'])\n"
                f" Path({str(marker)!r}).write_text(str(p.pid))\n end=time.monotonic()+1\n while not Path({str(release)!r}).exists() and time.monotonic()<end:time.sleep(.001)\n"
                "except BaseException as primary:\n if p is not None:retire_fixture_processes([p],primary)\n raise\n")
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
        session=Session.__new__(Session);returned=started;production=None;cleaned=False;secondary=[]
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
            pending=sys.exception()
            if production is None:
                returned=self.time.monotonic()
                production=dict(deadline=getattr(session,'cleanup_deadline',None),returned=returned,state=getattr(session,'state','not_started'),
                    primary=getattr(session,'primary',None),actually_acquired=list(acquired),
                    interrupted_by=None if pending is None else dict(error_class=type(pending).__name__,message=str(pending)))
            def final_step(name,operation):
                try:return operation()
                except BaseException as error:
                    secondary.append(dict(operation=name,error_class=type(error).__name__,message=str(error)))
                    if pending is not None:pending.add_note('L36 secondary: '+repr(secondary[-1]))
                    return None
            def retire():
                nonlocal cleaned
                if handles:
                    session.handle=handles[0]
                    if session.owner is not None:session.owner.handle=handles[0]
                cleaned=session.close(safety_end)
            final_step('retire_acquired',retire)
            ended=self.time.monotonic()
            import json
            owner=getattr(session,'owner',None)
            record=dict(scenario='L36',constructor_entry=started,action_cutoff=action_end,safety_cutoff=safety_end,
                production=production,cleanup_confirmed=cleaned,execution_seconds=returned-started,cleanup_seconds=ended-returned,end=ended,
                ownership=final_step('ownership',session.ownership),records={} if owner is None else owner.records,
                events=list(session.events),ticks=list(session.ticks),errors=[] if owner is None else list(owner.errors),secondary=secondary)
            def persist():
                with (Path(os.environ['S1_VALIDATION_RUN_DIRECTORY'])/'scenario-L36.json').open('x') as stream:json.dump(record,stream,indent=2)
            def original_checks():
                self.assertTrue(cleaned);self.assertLessEqual(ended-started,3);self.assertLessEqual(ended-returned,1)
                self.assertNotIn(session.owner,OWNERS)
            final_step('original_cleanup_assertions',original_checks)
            final_step('actual_outcome_write',persist)
            final_step('actual_outcome_presence',lambda:self.assertTrue((Path(os.environ['S1_VALIDATION_RUN_DIRECTORY'])/'scenario-L36.json').is_file()))
            if pending is None and secondary:raise AssertionError('L36 secondary failures: '+repr(secondary))

    def progress_scenario(self,label,mode,*,supervised=True):
        import json,shutil
        from vipe_benchmark import supervisor as sup,s1_progress as p
        from vipe_benchmark.files import write_json,file_record
        from vipe_benchmark.s1_clock import ReservationClock
        from test_vipe_benchmark_s1_helper_fixtures import progress_fixture,progress_reservation
        p.trace_reset()
        with self.scenario(label,mode) as session, tempfile.TemporaryDirectory() as temp:
            session.await_ready()
            root=Path(temp);fixture=progress_fixture(root/'fixture',states=label=='P04')
            write_json(root/'progress-fixture.json',fixture)
            marker=root/'sample-fail'
            life=sup.HelperLifecycle(retain=True);life.helpers=[session]
            session.resume();self.assertLessEqual(self.record_census(session)[0],8)
            pair={k:p.process_binding(v) for k,v in session.owner.records.items()}
            outcome={};caught=None;observed=[];consumer=None;reservation=None;primary_observations=[];late_parent_entries=[];cutoff_observations=[]
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
                        phase=kwargs.get('phase')
                        if label=='P01' and observed and phase in ('reconciliation','acceptance'):
                            W=observed[0]['monotonic_start']+observed[0]['seconds']-min(30.,observed[0]['seconds']/4)
                            if self.time.monotonic()>=W:
                                late_parent_entries.append(dict(phase=phase,observed=self.time.monotonic()));raise AssertionError('P01 forbidden post-W owner dispatch')
                        try:result=original(*args,**kwargs)
                        except BaseException as primary:
                            primary_observations.append(dict(error_class=type(primary).__name__,message=str(primary),phase=kwargs.get('phase'),observed=self.time.monotonic(),kind=getattr(primary,'kind',None),stop_required=getattr(primary,'stop_required',None),secondary=list(getattr(primary,'helper_cleanup_errors',[]))))
                            raise
                        if kwargs.get('worker') is not None:self.assertLessEqual(self.record_census(session,[kwargs['worker'].pid])[0],8)
                        return result
                    original_stop=sup.stop_group
                    def stop_with_cutoff(process,deadline):
                        if label=='P01' and process is not None:
                            marker=Path(fixture['root'])/'P01-cutoff-ready'
                            while not marker.exists() and self.time.monotonic()<deadline:self.time.sleep(.001)
                            cutoff_observations.append(dict(phase='owner_before_retirement',observed=self.time.monotonic(),worker_pid=process.pid,terminal_witness=marker.exists(),deadline=deadline))
                        return original_stop(process,deadline)
                    with patch.object(sup,'HelperLifecycle',return_value=life),patch.object(sup,'monitored_call',side_effect=monitored),patch.object(sup,'stop_group',side_effect=stop_with_cutoff):
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
                if supervised:
                    self.assertEqual(caught.primary_failure,outcome['primary_failure'])
                    self.assertEqual(caught.kind,caught.primary_failure['kind'])
                    self.assertEqual(type(caught.primary_exception).__name__,caught.primary_failure['error_class'])
                    self.assertEqual(str(caught.primary_exception),caught.primary_failure['message'])
                    self.assertEqual(caught.secondary_failures,outcome['secondary_failures'])
                    if label=='P01':self.assertEqual(caught.kind,'job_deadline')
                    if label=='P06':self.assertEqual(caught.primary_failure['phase'],'acceptance')
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
                child_boundaries=[]
                for trace in sorted(Path(fixture['root']).glob('child-progress-*.jsonl')):
                    raw=trace.read_bytes();events=[json.loads(line) for line in raw.splitlines()]
                    self.assertTrue(events);self.assertLessEqual(len(events),4097)
                    self.assertTrue(all(event['session']==reference['session'] for event in events))
                    self.assertTrue(all(event['overflow']==0 and event['valid'] for event in events))
                    self.assertTrue(events[-1]['terminal'],dict(label=label,last=events[-1]))
                    context=p.read_record(reference['context'],p.SMALL_BYTES)
                    self.assertTrue(all(event['reservation']==reference['reservation'] and event['request']==fixture['request_record'] for event in events))
                    self.assertTrue(all(event['work_deadline']==context['clock']['work_deadline'] and event['total_deadline']==context['clock']['total_deadline'] and event['observed']<event['total_deadline'] for event in events))
                    published=[event for event in events if event['producer'] is not None]
                    self.assertTrue(published)
                    for event in published:
                        self.assertGreaterEqual(event['request_id'],1);self.assertGreaterEqual(event['sequence'],1)
                        body=Path(context['root'])/event['producer']/(str(event['sequence']).zfill(4)+'.json')
                        if body.exists():
                            doc=p.decode(body.read_bytes(),p.CHECKPOINT_BYTES)
                            self.assertEqual(event['request_id'],doc['request_id'])
                            self.assertEqual(event['versions'],[row['version'] for row in doc['rows']])
                            self.assertEqual(event['binding'],doc['binding'])
                            self.assertEqual(event['boot_id'],context['boot_id'])
                        else:
                            self.assertFalse(event['installed'],dict(label=label,event=event,missing_body=str(body)))
                            self.assertFalse(event['head_installed']);self.assertFalse(event['acknowledged'])
                            same_generation=[v for v in events if v['producer']==event['producer'] and v['sequence']==event['sequence']]
                            self.assertTrue(any(v['terminal'] for v in same_generation),dict(label=label,missing_generation=event['sequence']))
                            self.assertFalse(any(v['installed'] or v['acknowledged'] for v in same_generation))
                    generations={}
                    for event in published:generations.setdefault((event['producer'],event['sequence']),[]).append(event)
                    required=['write','flush','file_fsync','close','close_readback','generation_install','generation_directory_fsync','generation_reopen_hash',
                        'write','flush','file_fsync','close','close_readback','head_install','head_directory_fsync','final_head_read','final_generation_read','notice_send','ack_receipt','producer_acknowledged']
                    correlation=[]
                    for (producer,sequence),events_for_generation in generations.items():
                        acknowledged=any(v['acknowledged'] for v in events_for_generation)
                        boundary=[v['phase'] for v in events_for_generation if v['state']=='boundary']
                        cursor=0
                        for phase in boundary:
                            if cursor<len(required) and phase==required[cursor]:cursor+=1
                        if acknowledged:self.assertEqual(cursor,len(required),dict(label=label,producer=producer,sequence=sequence,boundaries=boundary))
                        else:self.assertTrue(any(v['terminal'] for v in events_for_generation),dict(label=label,incomplete_generation=sequence))
                        record=reference['checkpoints'].get(producer)
                        retained=record is not None and Path(record['path']).stem==str(sequence).zfill(4)
                        if retained:
                            self.assertTrue(any(v['head_installed'] for v in events_for_generation))
                            self.assertEqual(file_record(record['path']),record)
                        correlation.append(dict(producer=producer,sequence=sequence,required=required,matched_prefix=cursor,
                            producer_acknowledged=acknowledged,owner_retained=retained,accepted=bool(recovered['acceptance']),
                            record=record if retained else None,versions=events_for_generation[-1]['versions']))

                    target=saved/trace.name;target.write_bytes(raw)
                    child_boundaries.append(dict(record=file_record(target),events=events,correlation=correlation))
                self.assertTrue(child_boundaries,label)
                if label=='P05':self.assertTrue(any(event['phase']=='P05_pre_head_replace' for trace in child_boundaries for event in trace['events']))
                owner_trace=p.trace_snapshot();self.assertTrue(owner_trace['valid'])
                for producer,checkpoint in reference['checkpoints'].items():
                    bound=[event for event in owner_trace['events'] if event.get('correlation') is not None and event['correlation']['producer']==producer and event['correlation']['current']==checkpoint]
                    phases=[event['phase'] for event in bound]
                    required_owner=['credentials:after','new_checkpoint_read:before','new_checkpoint_read:after','owner_retention','ack_send','ack_send:after']
                    cursor=0
                    for phase in phases:
                        if cursor<len(required_owner) and phase==required_owner[cursor]:cursor+=1
                    self.assertEqual(cursor,len(required_owner),dict(label=label,producer=producer,owner_trace=bound))
                    self.assertTrue(all(event['correlation']['reservation']==reference['reservation'] and event['correlation']['session']==reference['session'] for event in bound))
                if label=='P01':
                    suffixes=[event for trace in child_boundaries for event in trace['events'] if event['phase']=='P01_late_suffix']
                    self.assertEqual(len(suffixes),1)
                    event=suffixes[0];suffix=event['late_suffix']
                    self.assertTrue(event['terminal']);self.assertEqual(event['overflow'],0)
                    self.assertEqual(suffix['entered'],[]);self.assertEqual(late_parent_entries,[])
                    self.assertEqual([row['operation'] for row in suffix['attempts']],['raw','reconcile','first','runtime','accept'])
                    self.assertTrue(all(row['error_class']=='TimeoutError' and row['start']>=event['work_deadline'] and row['end']<event['total_deadline'] for row in suffix['attempts']))
                    self.assertEqual(suffix['cutoff'],event['work_deadline']);self.assertEqual(suffix['sequence'],event['sequence'])
                    self.assertEqual(suffix['versions'],event['versions']);self.assertEqual(suffix['binding'],event['binding'])
                    self.assertEqual(suffix['request'],event['request']);self.assertEqual(suffix['session'],event['session'])
                    self.assertEqual(len(cutoff_observations),1);self.assertTrue(cutoff_observations[0]['terminal_witness'])
                    self.assertEqual(cutoff_observations[0]['worker_pid'],event['binding']['pid'])
                    self.assertGreaterEqual(cutoff_observations[0]['observed'],event['observed'])
                    self.assertLess(cutoff_observations[0]['observed'],event['total_deadline'])
                    self.assertEqual(caught.primary_failure['kind'],'job_deadline')
                if label=='P05':
                    faults=[event for trace in child_boundaries for event in trace['events'] if event['phase']=='P05_pre_head_replace']
                    self.assertTrue(all(event['installed'] and not event['head_installed'] and not event['acknowledged'] for event in faults))
                    for event in faults:
                        directory=Path(context['root'])/event['producer'];temporary=directory/'head.tmp'
                        self.assertTrue(temporary.is_file());self.assertTrue(temporary.read_bytes())
                        head=p.read_record(file_record(directory/'head.json'),p.SMALL_BYTES)
                        self.assertLess(head['sequence'],event['sequence'])
                copied=[file_record(path) for path in sorted(saved.rglob('*')) if path.is_file()]
                session.events.append(dict(event='progress_outcome',label=label,reference=reference,recovered=recovered,exception=type(caught).__name__,
                    publication=outcome.get('terminal_publication_status'),primary=dict(error_class=type(caught).__name__,message=str(caught),kind=getattr(caught,'kind',None),stop_required=getattr(caught,'stop_required',None)),primary_observations=primary_observations,finish=outcome,protocol_trace=p.trace_snapshot(),fixture_scope='two-row final-sample loss, not full acceptance' if label=='P04' else label,durable_copies=copied,original_pair=pair,original_clock=observed[0] if observed else reservation,
                    child_boundaries=child_boundaries,late_parent_entries=late_parent_entries,cutoff_observations=cutoff_observations,production_return=self.time.monotonic(),owner_block_entered=getattr(session.owner,'progress_block_entered',None)))
            finally:
                pending=sys.exception();frozen=None;cleanup_errors=[];safety_steps=[]
                def safety_step(name,function):
                    observation=dict(operation=name,entered=self.time.monotonic(),action_cutoff=session.fixture_action_end,safety_cutoff=session.fixture_safety_end,completed=False);safety_steps.append(observation)
                    try:
                        value=function();observation['completed']=True;return value
                    except BaseException as secondary:
                        item=dict(operation=name,error_class=type(secondary).__name__,message=str(secondary))
                        cleanup_errors.append(item)
                        if pending is not None:pending.add_note('progress safety: '+repr(item))
                        if caught is not None:
                            caught.progress_safety_secondary=list(cleanup_errors)
                        return None
                    finally:observation['returned']=self.time.monotonic()
                def cutoff():
                    session.events.append(dict(event='plan047_production_cutoff',observed=self.time.monotonic(),reference=life.progress.reference(),ownership=life.ownership(),safety_cutoff=session.fixture_safety_end))
                frozen=safety_step('frozen_snapshot',lambda:life.progress.snapshot)
                safety_step('cutoff_record',cutoff)
                safety_step('owner_release',lambda:setattr(session.owner,'released',True))
                def reap():
                    if not life.reap(session.fixture_safety_end):raise AssertionError('progress helpers not retired')
                safety_step('lifecycle_reap',reap)
                def pointer_check():
                    self.assertIs(life.progress.snapshot,frozen)
                safety_step('frozen_pointer',pointer_check)
                def retired_record():
                    session.events.append(dict(event='plan047_safety_retirement',observed=self.time.monotonic(),ownership=life.ownership(),secondary=list(cleanup_errors)))
                safety_step('retirement_record',retired_record)
                def final_outcome():
                    session.events.append(dict(event='progress_final_outcome',label=label,
                        primary=None if caught is None else dict(error_class=type(caught).__name__,message=str(caught),kind=getattr(caught,'kind',None),
                            primary_failure=getattr(caught,'primary_failure',None),secondary_failures=getattr(caught,'secondary_failures',None)),
                        assertion_or_setup_failure=None if pending is None else dict(error_class=type(pending).__name__,message=str(pending)),
                        finish=dict(outcome),reference=life.progress.reference(),retained_snapshot_present=frozen is not None,pointer_unchanged=life.progress.snapshot is frozen,primary_observations=list(primary_observations),
                        cleanup_secondary=list(cleanup_errors),safety_steps=list(safety_steps),ownership=life.ownership(),observed=self.time.monotonic(),
                        causal_status='recorded actual outcome; no inferred EPERM cause',original_clock=observed[0] if observed else reservation))
                safety_step('final_outcome_record',final_outcome)
                if pending is None and cleanup_errors:raise AssertionError('progress safety failures: '+repr(cleanup_errors))
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
                        # D49-2: exact expired public entry, not a returned scan.
                        from contextlib import ExitStack
                        suffix=[];spies=[]
                        def forbidden(name,*args,**kwargs):
                            suffix.append(name)
                            raise AssertionError('expired reconciliation entered forbidden suffix: '+name)
                        with ExitStack() as stack:
                            for module,name in ((e,'_reconcile_rows'),(e,'input_loader'),(p,'candidate_inventory'),(e,'produced_row'),(e,'qualify_row')):
                                spy=stack.enter_context(patch.object(module,name,side_effect=lambda *args,_name=name,**kwargs:forbidden(_name,*args,**kwargs)))
                                spies.append((name,spy))
                            with self.assertRaisesRegex(TimeoutError,'^progress original work deadline$'):
                                e.reconcile_rows(output,fixture['request'],deadline=0)
                            for name,spy in spies:self.assertEqual(spy.call_count,0,name)
                            self.assertEqual(suffix,[])
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
                                publisher=p.Publisher(reference,'reconcile',2,clock=clock,trusted=cache.reference())
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

    def test_progress_plan047_nested(self):
        import copy
        from vipe_benchmark import s1_progress as p
        from test_vipe_benchmark_s1_helper_fixtures import progress_fixture,plan047_state
        evidence=[]
        with tempfile.TemporaryDirectory() as temp:
            fixture=progress_fixture(Path(temp)/'fixture')
            with plan047_state(fixture,Path(temp)/'state') as state:
                pub=state.publisher;pub.failure(ValueError('nested schema fixture'),'schema')
                pub.runtime['final']=state.row_record;pub.publish()
                checkpoint=p.read_record(pub.previous);head=p.read_record(state.cache.reference()['provenance']['worker']['accepted_head'],p.SMALL_BYTES)
                notice=dict(schema='s1-progress-notice/v1',context=state.reference,producer='worker',binding=pub.binding,request_id=1,sequence=pub.sequence,current=pub.previous,previous=checkpoint['previous'],head=state.cache.reference()['provenance']['worker']['accepted_head'],completed=checkpoint['verified_at'])
                ack=dict(schema='s1-progress-ack/v1',context=state.reference['sha256'],producer='worker',sequence=pub.sequence,current=pub.previous)
                def transient_successor(rec,limit=p.CHECKPOINT_BYTES):
                    intended=state.cache.reference()['provenance']['worker']['intended_successor']
                    self.assertEqual(rec,state.reference)
                    self.assertGreater(intended['sequence'],checkpoint['sequence'])
                    evidence.append(dict(control='credentialed_transient_successor',record=rec,intended=intended,context=state.reference,observed=self.time.monotonic()))
                    raise TimeoutError('stop after credentialed intended successor')
                with patch.object(state.consumer,'read',side_effect=transient_successor):
                    with self.assertRaises(OSError):pub.publish()
                self.assertTrue(state.consumer.cache.reference()['provenance']['worker']['intended_successor'])
                with plan047_state(fixture,Path(temp)/'ordinary-oserror') as untrusted:
                    untrusted.publisher.failure(ValueError('independent integrity control'),'schema')
                    with patch.object(untrusted.consumer,'read',side_effect=OSError('ordinary integrity failure')):
                        with self.assertRaises(OSError):untrusted.publisher.publish()
                    self.assertTrue(untrusted.cache.integrity)
                    with self.assertRaisesRegex(ValueError,'progress recovery unverified'):p.recover(untrusted.cache.reference())
                    evidence.append(dict(control='ordinary_oserror_remains_integrity',integrity=untrusted.cache.integrity,reference=untrusted.cache.reference()))
                reference=state.cache.reference()
                trusted=p.recover(reference)
                summary=dict(runtime={'final':{'status':'unverified','value':None}},first_result={'status':'unverified','value':None},verification_errors=[])
                originals=dict(context=pub.context,checkpoint=checkpoint,head=head,notice=notice,ack=ack,reference=reference,summary=summary)
                validators=dict(context=p.context_document,checkpoint=lambda v:p.validate_checkpoint(v,pub.context,state.reference),head=p.validate_head,notice=p.validate_notice,ack=p.validate_ack,reference=p.recover,summary=lambda v:p.summary_adapter(trusted,v))
                for case in SUBTEST_CASES[f'{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}']:
                    with self.subTest(**case):
                        target=case['target'].split('.');name=target.pop(0);value=copy.deepcopy(originals[name]);parent=None;key=None;node=value
                        for part in target:
                            parent=node;key=int(part) if type(node) is list else part;node=node[key]
                        if case['mutation']=='missing':del node[case['field']]
                        elif case['mutation']=='extra':node['__plan047_extra__']=None
                        elif parent is None:value=[]
                        else:parent[key]=[]
                        pointer=state.cache.snapshot
                        with self.assertRaises((ValueError,TypeError,KeyError)) as caught:validators[name](value)
                        self.assertIsInstance(caught.exception,ValueError)
                        self.assertIs(state.cache.snapshot,pointer)
                        evidence.append(dict(case,source=validators[name].__name__,observed=type(caught.exception).__name__,fixture=state.reference,pointer_unchanged=True))
        self.control_record('plan047-nested',evidence)

    def test_progress_plan047_alias_inventory(self):
        import copy,json
        from vipe_benchmark import s1_progress as p
        from vipe_benchmark.files import write_json
        from test_vipe_benchmark_s1_helper_fixtures import progress_fixture
        evidence=[]
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);fixture=progress_fixture(base/'fixture')
            for case in SUBTEST_CASES[f'{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}']:
                with self.subTest(**case):
                    kind=case['kind'];root=base/kind;root.mkdir();row=root/'one-produced-row.json';write_json(row,fixture['rows'][0]);deadline=self.time.monotonic()+20
                    foreign=base/(kind+'-external');foreign.write_bytes(row.read_bytes());action=lambda:p.candidate_inventory(root,None,deadline)
                    if kind=='leaf_symlink':row.unlink();row.symlink_to(foreign)
                    elif kind=='component_symlink':
                        link=base/(kind+'-link');link.symlink_to(root,target_is_directory=True);action=lambda:p.candidate_inventory(link,None,deadline)
                    elif kind in ('dot_alias','dotdot_traversal','repeated_separator'):
                        suffix={'dot_alias':'/./','dotdot_traversal':'/../'+root.name+'/','repeated_separator':'//'}[kind]
                        action=lambda:p.candidate_inventory(str(root)+suffix,None,deadline)
                    elif kind in ('hardlink_duplicate','hardlink_external'):
                        os.link(row,root/'two-produced-row.json' if kind=='hardlink_duplicate' else base/(kind+'-hard'))
                    elif kind=='foreign_candidate_root':
                        # Result cannot silently substitute a row outside the anchored snapshot.
                        _,closed=p.candidate_inventory(root,None,deadline)
                        with self.assertRaisesRegex(ValueError,'foreign candidate root'):
                            closed.append(p.record(foreign,foreign.read_bytes()))
                        write_json(root/'result.json',{'rows':[fixture['rows'][0]]});changed=copy.deepcopy(fixture['rows'][0]);changed['metadata']['foreign']=True
                        action=lambda:p.candidate_inventory(root,{'rows':[changed]},deadline)
                    elif kind=='fifo_candidate':row.unlink();os.mkfifo(row)
                    elif kind=='directory_candidate':row.unlink();row.mkdir()
                    elif kind=='descriptor_replacement':
                        actual=p.os.fstat;seen=[0]
                        def fstat(fd):
                            value=actual(fd)
                            if value.st_ino==row.stat().st_ino:
                                seen[0]+=1
                                if seen[0]==2:os.replace(foreign,row)
                            return value
                        action0=action
                        def action():
                            with patch.object(p.os,'fstat',side_effect=fstat):return action0()
                    else:
                        if kind.startswith('result_'):write_json(root/'result.json',{'rows':[fixture['rows'][0]]})
                        _,inventory=p.candidate_inventory(root,None,deadline)
                        if kind.startswith(('row_bytes','row_replace')):row.write_bytes(row.read_bytes()+b' ')
                        elif kind.startswith('result_'):(root/'result.json').write_bytes(b'{}')
                        elif kind.startswith('member_add'):write_json(root/'two-produced-row.json',fixture['rows'][0])
                        elif kind.startswith('member_remove'):row.unlink()
                        elif kind.startswith('member_rename'):row.rename(root/'other-produced-row.json')
                        elif kind=='parent_replace_closure':root.rename(base/(kind+'-old'));root.mkdir();write_json(row,fixture['rows'][0])
                        action=lambda:inventory.recheck(deadline)
                    with self.assertRaises((ValueError,OSError)) as caught:action()
                    actual_fallback=None
                    if kind.endswith('_after_publish'):
                        from test_vipe_benchmark_s1_helper_fixtures import invalidated_fallback
                        actual_fallback=invalidated_fallback(self,fixture,base/(kind+'-acknowledged'),kind)
                    evidence.append(dict(case,source='candidate_inventory/ClosedInventory.recheck/read_bytes',observed=type(caught.exception).__name__,fixture=fixture['request_record'],acknowledged_fallback=actual_fallback))
        self.control_record('plan047-alias-inventory',evidence)

    def test_progress_plan047_recovery(self):
        import copy,json
        from vipe_benchmark import s1_progress as p
        from test_vipe_benchmark_s1_helper_fixtures import progress_fixture,plan047_state
        evidence=[]
        with tempfile.TemporaryDirectory() as temp:
            fixture=progress_fixture(Path(temp)/'fixture')
            for case in SUBTEST_CASES[f'{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}']:
                with self.subTest(**case),plan047_state(fixture,Path(temp)/case['kind']) as state:
                    pub=state.publisher;reference=state.cache.reference();kind=case['kind'];head=Path(pub.previous['path']).parent/'head.json';body=Path(pub.previous['path']);expected_error=False
                    if kind.startswith('optional_'):
                        with patch.object(state.consumer,'read',side_effect=BlockingIOError('after credentialed successor')):
                            with self.assertRaises(OSError):pub.publish()
                        reference=state.cache.reference();new=reference['provenance']['worker']['intended_successor']['current']
                        if kind=='optional_successor_body_missing':Path(new['path']).unlink()
                        elif kind=='optional_successor_body_truncated':Path(new['path']).write_bytes(b'{')
                        elif kind=='optional_successor_head_truncated':head.write_bytes(b'{')
                    elif kind=='head_missing_no_intent':head.unlink()
                    elif kind=='head_truncated_no_intent':head.write_bytes(b'{')
                    elif kind=='accepted_body_missing':body.unlink();expected_error=True
                    elif kind=='accepted_body_changed':body.write_bytes(b'{}');expected_error=True
                    elif kind=='accepted_head_changed':
                        value=p.decode(head.read_bytes(),p.SMALL_BYTES);value['current']['sha256']='0'*64;head.write_bytes(p.encode(value,p.SMALL_BYTES));expected_error=True
                    elif kind=='head_regressed':
                        value=p.decode(head.read_bytes(),p.SMALL_BYTES);value['sequence']=1;head.write_bytes(p.encode(value,p.SMALL_BYTES));expected_error=True
                    elif kind=='context_changed':Path(state.reference['path']).write_bytes(b'{}');expected_error=True
                    elif kind=='foreign_provenance':reference['provenance']['worker']['accepted_head']['sha256']='0'*64;expected_error=True
                    elif kind=='unacknowledged_only':reference['checkpoints']={};reference['provenance']={};expected_error=True
                    elif kind=='current_previous_retention':pub.publish();reference=state.cache.reference();self.assertEqual(reference['provenance']['worker']['previous_checkpoint'],state.consumer.previous['worker'][0])
                    before=state.cache.snapshot;opened=[];actual=p.read_bytes
                    def read(path,limit):opened.append(str(path));return actual(path,limit)
                    import contextlib
                    with contextlib.ExitStack() as recovery_scope,patch.object(p,'read_bytes',side_effect=read),patch.object(Path,'iterdir',side_effect=AssertionError('history enumeration forbidden')):
                        if kind=='late_recovery':
                            recovery_scope.enter_context(patch.object(p.time,'monotonic',return_value=state.clock.work_deadline+1))
                            from vipe_benchmark import s1_evidence
                            recovery_scope.enter_context(patch.object(s1_evidence,'qualify_row',side_effect=AssertionError('late recovery raw guard')))
                            recovery_scope.enter_context(patch.object(s1_evidence,'produced_row',side_effect=AssertionError('late recovery raw guard')))
                        if expected_error:
                            with self.assertRaises((ValueError,OSError)) as caught:p.recover(reference)
                            observed=type(caught.exception).__name__
                        else:
                            result=p.recover(reference);observed=result['integrity_status'];self.assertEqual(result['counts']['produced_lower_bound'],1)
                            if kind in ('head_missing_no_intent','head_truncated_no_intent'):
                                self.assertTrue(result['stop_required']);self.assertFalse(result['scan_complete']);self.assertEqual(result['integrity_status'],'uncertain')
                            if kind.startswith('optional_'):self.assertFalse(result['scan_complete']);self.assertEqual(result['integrity_status'],'verified')
                            if kind=='late_recovery':
                                self.assertEqual(result['verified_progress_reference'],reference)
                                self.assertFalse(result['scan_complete'])
                    self.assertIs(state.cache.snapshot,before);self.assertLessEqual(len(opened),7)
                    self.assertFalse(any(name.endswith(('.npy','.npz','.png')) for name in opened))
                    evidence.append(dict(case,source='recover',observed=observed,opened=opened,reference=reference,pointer_unchanged=True))
        self.control_record('plan047-recovery',evidence)
    def test_progress_plan047_limits(self):
        import copy
        from vipe_benchmark import s1_progress as p,s1_evidence as e
        from vipe_benchmark.files import write_json
        from test_vipe_benchmark_s1_helper_fixtures import progress_fixture,plan047_state
        evidence=[]
        limits={'inventory_depth':4,'variants':4,'identities':510,'candidates':2048,'inventory_sources':2048,'directory_entries':4096,'embedded_refs':4096,'metadata_bytes':33554432,'row_bytes':262144,'path_utf8_bytes':2048,'checkpoint_bytes':1048576,'checkpoint_depth':12,'checkpoint_nodes':65536,'producer_generations':1024,'total_generations':2048,'committed_bytes':2147483648,'tree_entries':2057,'retained_bytes':4194304,'context_bytes':8192,'head_bytes':8192,'reference_bytes':8192,'control_bytes':4096,'result_bytes':33554432,'result_depth':64,'result_nodes':1048576,'error_count':32,'error_utf8_bytes':1024,'socket_address_bytes':96}
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);fixture=progress_fixture(root/'fixture')
            with plan047_state(fixture,root/'state') as state:
                original=p.read_record(state.publisher.previous)
                for index,case in enumerate(SUBTEST_CASES[f'{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}']):
                    with self.subTest(**case):
                        name=case['limit'];value=case['value'];limit=limits[name];document=copy.deepcopy(original);source='';semantic='capacity only; enclosing semantic validation remains separate'
                        directory=root/str(index);directory.mkdir()
                        if name in ('total_generations','committed_bytes','tree_entries','retained_bytes'):
                            args=dict(generations=0,committed_bytes=0,tree_entries=0,retained_bytes=0);args['generations' if name=='total_generations' else name]=value
                            action=lambda:p.publication_capacity(**args);source='publication_capacity (also reached by real fixture publication)'
                        elif name=='path_utf8_bytes':
                            path='/'+'é'*((value-1)//2)+'x'*((value-1)%2);self.assertEqual(len(path.encode()),value);action=lambda:p.canonical(path);source='canonical UTF-8'
                        elif name=='metadata_bytes':
                            row={};row_size=len(p.encode(row,256*1024));base=p.encode(dict(rows=[row]))
                            raw=base+b' '*(value-row_size-len(base));self.assertEqual(len(raw)+row_size,value)
                            self.assertLessEqual(len(raw),p.MAX_METADATA)
                            (directory/'result.json').write_bytes(raw)
                            action=lambda:p.candidate_inventory(directory,None,None);source='candidate_inventory aggregate raw-result plus canonical-row bytes'
                        elif name in ('row_bytes','result_bytes'):
                            base=p.encode(dict(rows=[])) if name=='result_bytes' else b'{}'
                            raw=base+b' '*(value-len(base));self.assertEqual(len(raw),value)
                            path=directory/('result.json' if name=='result_bytes' else 'one-produced-row.json');path.write_bytes(raw)
                            action=lambda:p.candidate_inventory(directory,None,None);source='candidate_inventory anchored '+name+' read'
                        elif name in ('context_bytes','head_bytes','checkpoint_bytes'):
                            if name=='context_bytes':doc=state.publisher.context;validator=p.context_document
                            elif name=='head_bytes':doc=p.read_record(state.cache.reference()['provenance']['worker']['accepted_head'],p.SMALL_BYTES);validator=p.validate_head
                            else:doc=document;validator=lambda doc:p.validate_checkpoint(doc,state.publisher.context,state.reference)
                            base=p.encode(doc);raw=base+b' '*(value-len(base));self.assertEqual(len(raw),value)
                            path=directory/'metadata.json';path.write_bytes(raw);record=p.record(path,raw)
                            action=lambda:validator(p.read_record(record,limit));source='anchored read_record plus enclosing '+name+' validator'
                        elif name=='reference_bytes':
                            ref=copy.deepcopy(state.cache.reference());proof=ref['provenance']['worker']
                            proof['previous_checkpoint']=copy.deepcopy(state.row_record);proof['previous_head']=copy.deepcopy(state.row_record)
                            fields=[ref['context'],ref['checkpoints']['worker'],proof['accepted_head'],proof['previous_checkpoint'],proof['previous_head']]
                            for record in fields:
                                remaining=value-len(p.encode(ref,p.MAX_METADATA))
                                if remaining<=0:break
                                record['path']+='x'*min(remaining,2048-len(record['path'].encode()))
                            self.assertEqual(len(p.encode(ref,p.MAX_METADATA)),value)
                            def action():
                                if value>limit:return p.recover(ref)
                                # The exact production reference encoder succeeds; the
                                # deliberately foreign provenance then rejects separately.
                                with self.assertRaises((ValueError,OSError)):p.recover(ref)
                            source='recover composite reference encoder before semantic provenance'
                        elif name=='control_bytes':
                            base=p.encode(dict(schema='s1-progress-ack/v1',context=state.reference['sha256'],producer='worker',sequence=state.publisher.sequence,current=state.publisher.previous),p.CONTROL_BYTES)
                            raw=base+b' '*(value-len(base));self.assertEqual(len(raw),value)
                            def action():
                                state.publisher.channel.sendto(raw,p.address(state.publisher.context))
                                result,credentials,sender=p.receive(state.consumer.channel)
                                return p.validate_ack(result)
                            source='receive existing datagram truncation/byte bound plus ack validator'
                        elif name.endswith('_depth') and name!='inventory_depth':
                            raw=b'['*value+b'0'+b']'*value
                            action=lambda:p.decode(raw,p.MAX_METADATA,max_depth=limit,max_nodes=1048576);source='decode actual lexical nesting'
                        elif name.endswith('_nodes'):
                            raw=b'['+b','.join([b'null']*(value-1))+b']'
                            action=lambda:p.decode(raw,p.MAX_METADATA,max_depth=64,max_nodes=limit);source='decode actual primitive node counter'
                        elif name=='identities':
                            document['rows']=[dict(copy.deepcopy(original['rows'][0]),identity=i) for i in p.identities(state.publisher.context)[:value]]
                            if value>510:document['rows'].append(copy.deepcopy(document['rows'][-1]))
                            document['counts']=p.counts(document['rows']);action=lambda:p.validate_checkpoint(document,state.publisher.context,state.reference);source='validate_checkpoint admitted ordered membership'
                        elif name=='embedded_refs':
                            document['sources']=[dict(state.row_record,path=str(directory/str(i))) for i in range(value)]
                            document['rows'][0]['source_indices']=list(range(value));action=lambda:p.validate_checkpoint(document,state.publisher.context,state.reference);source='validate_checkpoint source capacity'
                        elif name=='producer_generations':
                            document['sequence']=value;action=lambda:p.validate_checkpoint(document,state.publisher.context,state.reference);source='validate_checkpoint sequence'
                        elif name=='error_count':
                            pub=state.publisher;pub.errors=[];pub.diagnostics=dict(dropped=0,first=None,last=None,primary=None)
                            for _ in range(value):pub.failure(ValueError('bounded error'))
                            self.assertEqual(len(pub.errors),min(value,limit));self.assertEqual(pub.diagnostics['dropped'],max(0,value-limit));self.assertEqual(pub.diagnostics['primary'],pub.diagnostics['first'])
                            action=lambda:True;source='Publisher.failure saturation';semantic='overflow is retained as a drop, never lost';limit=value
                        elif name=='error_utf8_bytes':
                            document['errors']=['é'*(value//2)+'x'*(value%2)]
                            event=dict(error_class='ValueError',message='capacity fixture',phase='test',observed=self.time.monotonic())
                            document['diagnostics']=dict(dropped=0,first=event,last=event,primary=event)
                            action=lambda:p.validate_checkpoint(document,state.publisher.context,state.reference);source='validate_checkpoint UTF-8 error size'
                        elif name=='socket_address_bytes':
                            context=dict(state.publisher.context,session='x'*(value-len('\0s1-progress--owner')));action=lambda:p.address(context);source='address before bind'
                        elif name=='inventory_depth':
                            current=directory
                            for _ in range(value):current=current/'d';current.mkdir()
                            action=lambda:p.candidate_inventory(directory,None,None);source='candidate_inventory.walk depth'
                        elif name=='directory_entries':
                            for i in range(value):(directory/str(i)).touch()
                            action=lambda:p.candidate_inventory(directory,None,None);source='candidate_inventory.walk global entries'
                        elif name in ('candidates','inventory_sources'):
                            if name=='candidates':write_json(directory/'result.json',dict(rows=[fixture['rows'][0]]*value))
                            else:
                                for i in range(value):write_json(directory/(str(i)+'-produced-row.json'),fixture['rows'][0])
                            action=lambda:p.candidate_inventory(directory,None,None);source='candidate_inventory append/source capacity'
                        elif name=='variants':
                            for i in range(value):
                                row=copy.deepcopy(fixture['rows'][0]);row['metadata']['variant']=i;write_json(directory/(str(i)+'-produced-row.json'),row)
                            result=e.reconcile_rows(directory,fixture['request'])
                            overflow=any('overflow' in item['error'] for item in result['verification_errors'])
                            self.assertEqual(overflow,value>limit);self.assertEqual(result['counts']['qualified'],0)
                            action=lambda:True;source='reconcile_rows distinct version insertion';limit=value
                        else:raise AssertionError(name)
                        counters={};actual_counter=p.inventory_capacity
                        def counter(counter_name,observed_value,maximum):
                            counters[counter_name]=max(counters.get(counter_name,0),observed_value)
                            return actual_counter(counter_name,observed_value,maximum)
                        with patch.object(p,'inventory_capacity',side_effect=counter):
                            if value>limit:
                                with self.assertRaises((ValueError,OverflowError)) as caught:action()
                                observed=type(caught.exception).__name__
                            else:action();observed='accepted numeric endpoint'
                        if name in ('metadata_bytes','candidates','inventory_sources','inventory_depth','directory_entries'):
                            self.assertEqual(counters[name],value)
                        evidence.append(dict(case,limit=limits[name],source=source,observed=observed,counters=counters,semantic=semantic,fixture=state.reference))
        self.control_record('plan047-limits',evidence)

    def test_progress_plan047_publication_faults(self):
        import contextlib
        from vipe_benchmark import s1_progress as p
        from test_vipe_benchmark_s1_helper_fixtures import progress_fixture,plan047_state
        records=[]
        with tempfile.TemporaryDirectory() as temp:
            fixture=progress_fixture(Path(temp)/'fixture')
            for case in SUBTEST_CASES[f'{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}']:
                with self.subTest(**case),plan047_state(fixture,Path(temp)/case['kind']) as state:
                    kind=case['kind'];publisher=state.publisher;pointer=state.cache.snapshot;reached=[];prior=state.cache.reference();section=['checkpoint'];last_stage=[''];now=[self.time.monotonic()]
                    mapping={'generation_dir_fsync':'generation_directory_fsync','head_dir_fsync':'head_directory_fsync','owner_retention_error':'owner_retention','ack_send_late':'ack_send','ack_receive_late':'ack_receipt'}
                    def boundary(stage):
                        last_stage[0]=stage
                        if stage=='generation_directory_fsync':section[0]='head'
                        target=mapping.get(kind,kind.removeprefix(section[0]+'_').replace('fsync','file_fsync'))
                        if stage==target and kind not in ('checkpoint_open','checkpoint_flush','checkpoint_fsync','checkpoint_close','head_open','head_flush','head_fsync','head_close','generation_dir_fsync','head_dir_fsync','ack_send_late','ack_receive_late'):
                            reached.append(stage)
                            if kind.endswith('_late'):now[0]=state.clock.work_deadline
                            else:raise OSError('plan047 injected '+kind)
                    real_open=p.os.fdopen
                    class FaultStream:
                        def __init__(inner,stream):inner.stream=stream
                        def __getattr__(inner,name):return getattr(inner.stream,name)
                        def write(inner,raw):
                            if kind==section[0]+'_write_short':reached.append('write_short');return inner.stream.write(raw[:1])
                            return inner.stream.write(raw)
                        def flush(inner):
                            if kind==section[0]+'_flush':reached.append('flush');raise OSError('plan047 actual flush failure')
                            return inner.stream.flush()
                        def close(inner):
                            if kind==section[0]+'_close' and not inner.stream.closed:
                                reached.append('close');inner.stream.close();raise OSError('plan047 injected close')
                            return inner.stream.close()
                    def fdopen(fd,mode,*args,**kwargs):
                        stream=real_open(fd,mode,*args,**kwargs)
                        return FaultStream(stream) if mode=='wb' else stream
                    real_osopen=p.os.open;real_fsync=p.os.fsync
                    def osopen(path,*args,**kwargs):
                        if kind==section[0]+'_open' and str(path) in ('checkpoint.tmp','head.tmp'):reached.append('open');raise OSError('plan047 actual exclusive open failure')
                        return real_osopen(path,*args,**kwargs)
                    def fsync(fd):
                        if kind==section[0]+'_fsync' and last_stage[0]=='file_fsync' or kind=='generation_dir_fsync' and last_stage[0]=='generation_directory_fsync' or kind=='head_dir_fsync' and last_stage[0]=='head_directory_fsync':reached.append('fsync');raise OSError('plan047 actual fsync failure')
                        return real_fsync(fd)
                    real_read=p.read_bytes
                    def read(path,limit):
                        raw=real_read(path,limit);name=Path(path).name
                        match=(kind=='checkpoint_readback' and name=='checkpoint.tmp' or kind=='head_readback' and name=='head.tmp' or kind=='final_generation_readback' and name==str(publisher.sequence+1).zfill(4)+'.json' and section[0]=='final' or kind=='final_head_readback' and name=='head.json' and section[0]=='final')
                        if match:reached.append('readback mismatch');return b'{}'
                        return raw
                    old_boundary=boundary
                    def boundary(stage):
                        if stage=='final_readback':section[0]='final'
                        return old_boundary(stage)
                    if kind.startswith('generation_collision'):
                        real_link=p.os.link
                        def link(src,dst,*args,**kwargs):
                            directory=Path(publisher.previous['path']).parent;raw=(directory/'checkpoint.tmp').read_bytes();(directory/dst).write_bytes(raw if kind.endswith('_exact') else b'{}');reached.append(kind)
                            return real_link(src,dst,*args,**kwargs)
                    with contextlib.ExitStack() as stack:
                        stack.enter_context(patch.object(p,'publication_boundary',side_effect=boundary));stack.enter_context(patch.object(p.os,'fdopen',side_effect=fdopen));stack.enter_context(patch.object(p,'read_bytes',side_effect=read));stack.enter_context(patch.object(p.os,'open',side_effect=osopen));stack.enter_context(patch.object(p.os,'fsync',side_effect=fsync))
                        if kind.startswith('generation_collision'):stack.enter_context(patch.object(p.os,'link',side_effect=link))
                        if kind.endswith('_late'):stack.enter_context(patch.object(p.time,'monotonic',side_effect=lambda:now[0]))
                        if kind in ('ack_send_short','ack_send_late'):
                            channel=state.consumer.channel
                            class ShortChannel:
                                def __getattr__(inner,name):return getattr(channel,name)
                                def sendto(inner,raw,sender):
                                    reached.append(kind)
                                    sent=channel.sendto(raw[:-1] if kind=='ack_send_short' else raw,sender)
                                    if kind=='ack_send_late':now[0]=state.clock.work_deadline+.001
                                    return sent
                            state.consumer.channel=ShortChannel()
                        if kind=='ack_receive_late':
                            real_receive=p.receive
                            def receive(channel):
                                value=real_receive(channel)
                                if channel is publisher.channel:reached.append(kind);now[0]=state.clock.work_deadline+.001
                                return value
                            stack.enter_context(patch.object(p,'receive',side_effect=receive))
                        if kind=='generation_collision_exact':publisher.publish();self.assertIsNot(state.cache.snapshot,pointer);outcome='exact collision acknowledged'
                        else:
                            with self.assertRaises((ValueError,OSError,TimeoutError)) as caught:publisher.publish()
                            outcome=type(caught.exception).__name__
                            if kind=='ack_receive_late':self.assertIsNot(state.cache.snapshot,pointer)
                            else:self.assertIs(state.cache.snapshot,pointer)
                    self.assertTrue(reached,kind)
                    files=[dict(path=str(path),bytes=path.stat().st_size,sha256=p.record(path,path.read_bytes())['sha256']) for path in Path(state.reference['path']).parent.rglob('*') if path.is_file()]
                    records.append(dict(case,source='Publisher._publish/write_exclusive/Consumer.tick',reached=reached,observed=outcome,prior=prior,reference=state.cache.reference(),files=files))
        self.control_record('plan047-publication-faults',records)
    def test_progress_plan047_ownership(self):
        import copy,json,hashlib,contextlib
        from vipe_benchmark import s1_helper_session as h
        original_path=Path(os.environ['S1_OWNED_ROOT_NOTE']);original=json.loads(original_path.read_bytes());records=[]
        baseline=h.owned_workload(original_path)
        with tempfile.TemporaryDirectory() as temp:
            for case in SUBTEST_CASES[f'{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}']:
                with self.subTest(**case),contextlib.ExitStack() as stack:
                    kind=case['kind'];note=copy.deepcopy(original);actual_records=copy.deepcopy(h.INVOCATION.records);result=None
                    try:
                        if kind in ('wrapper_one_thread','wrapper_two_threads','no_wrapper_reserve'):
                            if kind=='wrapper_two_threads':
                                with self.assertRaises(ValueError):h.owned_charge(7,2)
                                result='9 rejected'
                            elif kind=='wrapper_one_thread':self.assertEqual(h.owned_charge(7,1),8);result='8 accepted'
                            else:
                                self.assertEqual(h.owned_charge(7,0),8)
                                with self.assertRaises(ValueError):h.owned_charge(8,0)
                                result='reserve enforced'
                        elif kind.startswith('registry_') and kind!='registry_missing_enumeration':
                            observed=h.predispatch_owned(kind);self.assertEqual(observed['registry_identity'],id(h.INVOCATION));self.assertEqual(observed['root'],baseline['root']);result='same invocation registry'
                            entry={'registry_owner_dispatch':'Owner.run work','registry_worker_dispatch':'supervisor worker','registry_direct_dispatch':'direct script','registry_sentinel_dispatch':'L18 sentinel'}[kind]
                            creation=[];gate=h.predispatch_owned
                            def reached(event):
                                value=gate(event);creation.append(dict(event=event,registry=value['registry_identity'],charge=value['total_workers']));return value
                            def syscall(*args,**kwargs):creation.append(dict(syscall='pure creation seam'));return 2147482999
                            with patch.object(h,'predispatch_owned',side_effect=reached):
                                self.assertEqual(h.create_owned_process(entry,syscall),2147482999)
                            self.assertEqual(creation[0]['event'],entry);self.assertEqual(creation[0]['registry'],id(h.INVOCATION))
                            self.assertEqual(creation[-1],{'syscall':'pure creation seam'})
                            if kind=='registry_owner_dispatch':
                                with patch.object(h,'identity',side_effect=OSError('first full identity failed')),self.assertRaises(OSError):h.register_owned(2147482999,entry)
                                unknown=[r for r in h.INVOCATION.records.values() if r['pid']==2147482999]
                                self.assertEqual(len(unknown),1);self.assertEqual(unknown[0]['state'],'unresolved')
                                with self.assertRaisesRegex(ValueError,'unresolved'):h.predispatch_owned(entry)
                                h.retire_owned(2147482999)
                            result=dict(control=result,creation=creation,entrypoint='create_owned_process used by actual '+entry)
                            from test_vipe_benchmark_s1_helper_fixtures import named_creation_controls
                            entry_root=Path(temp)/kind;entry_root.mkdir()
                            result['named_enclosing_paths']=named_creation_controls(self,kind,entry_root)
                            if kind=='registry_worker_dispatch':
                                from test_vipe_benchmark_s1_helper_fixtures import enclosing_creation_controls,scenario_secondary_controls
                                result['other_enclosing_paths']=enclosing_creation_controls(self,entry_root)
                                result['scenario_secondary_controls']=scenario_secondary_controls(self,entry_root)
                        elif kind in ('detached_grandchild','retained_pid_reuse','registry_missing_enumeration'):
                            rows=h.census();fake=2147483000;boot=original['ownership_root']['boot_id'];identity=dict(pid=fake,ppid=1,pgid=fake,start_ticks=100,state='S')
                            h.INVOCATION.records[(boot,fake,100)]=dict(identity,boot_id=boot,threads=[fake],creation_parent=os.getpid(),creation_event='pure observed identity fixture')
                            if kind=='registry_missing_enumeration':
                                with patch.object(h,'census',side_effect=OSError('unavailable census')),self.assertRaises(OSError):h.predispatch_owned(kind)
                                result='unavailable enumeration blocks dispatch'
                            else:
                                rows[fake]=dict(identity,start_ticks=101 if kind=='retained_pid_reuse' else 100);rows[fake+1]=dict(pid=fake+1,ppid=fake,pgid=fake,start_ticks=102,state='S')
                                actual_iter=Path.iterdir;actual_identity=h.identity
                                def iterdir(path):return iter([Path(str(fake if str(fake) in str(path) else fake+1))]) if str(path) in (f'/proc/{fake}/task',f'/proc/{fake+1}/task') else actual_iter(path)
                                def identify(pid):return {k:rows[pid][k] for k in ('pid','pgid','start_ticks')} if pid in (fake,fake+1) else actual_identity(pid)
                                actual_thread=h.thread_identity
                                def identify_thread(pid,tid):return dict(tid=tid,start_ticks=rows[pid]['start_ticks']) if pid in (fake,fake+1) else actual_thread(pid,tid)
                                stack.enter_context(patch.object(h,'thread_identity',side_effect=identify_thread))
                                stack.enter_context(patch.object(h,'census',return_value=rows));stack.enter_context(patch.object(Path,'iterdir',iterdir));stack.enter_context(patch.object(h,'identity',side_effect=identify))
                                if kind=='retained_pid_reuse':
                                    with self.assertRaises(ValueError):h.predispatch_owned(kind)
                                    result='PID reuse unresolved'
                                else:
                                    observed=h.owned_workload(original_path);self.assertIn(fake,observed['process_threads']);self.assertIn(fake+1,observed['process_threads']);result='detached descendant charged'
                        elif kind.startswith('test_glob_'):
                            root=Path(temp)/kind;(root/'scripts/vipe_benchmark').mkdir(parents=True);(root/'tests').mkdir()
                            contract=Path(h.__file__).with_name('s1_validation_contract.py');(root/'scripts/vipe_benchmark/s1_validation_contract.py').write_bytes(contract.read_bytes());added=root/'tests/test_vipe_benchmark_new.py';added.write_text('')
                            members=h.validation_sources(root);self.assertIn(added,members);self.assertEqual(members,sorted(members))
                            if kind=='test_glob_omission':self.assertNotEqual([str(p) for p in members if p!=added],[str(p) for p in members])
                            self.assertEqual(h.source_membership([dict(path=str(p)) for p in members],root),[str(p) for p in members])
                            if kind=='test_glob_omission':
                                with self.assertRaisesRegex(ValueError,'source membership'):h.source_membership([dict(path=str(p)) for p in members if p!=added],root)
                            result='current contract glob recomputed'
                        else:
                            if kind=='paired_env_runner_root':note['ownership_root']=next(r for r in baseline['processes'] if r['pid']==os.getpid())
                            elif kind=='paired_env_foreign_output':note['run_directory']+='-foreign'
                            elif kind=='stale_dispatch016':note['bindings'][1]['path']=str(original_path.parent/'implementation-dispatch-016.json')
                            elif kind=='forged_dispatch_env':stack.enter_context(patch.dict(os.environ,{'S1_IMPLEMENTATION_DISPATCH':'/tmp/forged-dispatch'}));note['bindings']=[]
                            elif kind=='capture_omitted':note['ownership_root']['pid']=os.getpid()
                            elif kind=='stdin_inode_replaced':note['stdin_identity']['sha256']='0'*64
                            elif kind=='capture_argv_swapped':note['command'][-1]='999'
                            elif kind=='driver_log_inode_swapped':note['output_paths'][-1]+='-swapped'
                            elif kind=='ancestor_empty':note['preexisting_ancestors']=[]
                            elif kind=='ancestor_truncated':note['preexisting_ancestors'].pop()
                            elif kind=='ancestor_cycle':note['preexisting_ancestors'].append(note['preexisting_ancestors'][0])
                            elif kind=='ancestor_terminal_changed':note['ancestry_terminal']['ppid']=1
                            elif kind=='wrapper_unproven':note['retained_wrappers']=[dict(pid=os.getpid())]
                            else:raise AssertionError(kind)
                            path=Path(temp)/kind;raw=json.dumps(note).encode();path.write_bytes(raw)
                            stack.enter_context(patch.dict(os.environ,{'S1_OWNED_ROOT_NOTE':str(path),'S1_OWNED_ROOT_SHA256':hashlib.sha256(raw).hexdigest()}))
                            with self.assertRaises(ValueError):h.owned_workload(path)
                            result='kernel anchor rejected paired caller substitution'
                            # Preserve the generic control above, then isolate the
                            # named pinned authority predicate at its actual entry.
                            with patch.dict(os.environ,{'S1_OWNED_ROOT_NOTE':str(original_path),'S1_OWNED_ROOT_SHA256':hashlib.sha256(original_path.read_bytes()).hexdigest()}):
                                self.assertEqual(h.owned_workload(original_path)['root'],original['ownership_root'])
                            reached=[];saved_anchor=copy.deepcopy(h.INVOCATION.anchor)
                            target_note=copy.deepcopy(note);target_raw=json.dumps(target_note).encode()
                            actual_read=Path.read_bytes;actual_stat=Path.stat
                            root_pid=baseline['root']['pid'];runner=h.INVOCATION.anchor['runner']
                            stdin=Path(h.INVOCATION.anchor['directory'])/'stdin.py'
                            command_path=Path('/proc',str(root_pid),'cmdline')
                            start_path=next(Path(v) for v in original['output_paths'] if v.endswith('-exec-start.json'))
                            log_path=Path(str(start_path).replace('-exec-start.json','-stdout.log'))
                            start_doc=json.loads(actual_read(start_path))
                            expected_error={'stdin_inode_replaced':'stdin descriptor identity','capture_argv_swapped':'capture argv',
                                'driver_log_inode_swapped':'log descriptor identity','ancestor_empty':'ancestry termination',
                                'ancestor_truncated':'ancestry termination','ancestor_cycle':'ancestry',
                                'ancestor_terminal_changed':'ancestry termination','wrapper_unproven':'wrapper ownership',
                                'stale_dispatch016':'dispatch/plan/status','forged_dispatch_env':'dispatch/plan/status',
                                'paired_env_runner_root':'capture root binding','capture_omitted':'capture root binding',
                                'paired_env_foreign_output':'output/command binding'}[kind]
                            kernel_case=kind in ('stdin_inode_replaced','capture_argv_swapped','driver_log_inode_swapped')
                            from vipe_benchmark import s1_validation_contract as contract
                            projected={};actual_text=Path.read_text;actual_record=contract.file_record
                            def projected_record(path):
                                key=str(path)
                                if key not in projected:return actual_record(path)
                                data=projected[key];return dict(path=key,bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
                            def store_projection(path,value):
                                projected[str(path)]=json.dumps(value).encode();return projected_record(path)
                            # Rebuild every affected graph edge at its original
                            # canonical logical path. No runtime authority file
                            # is overwritten by these read-only fixture seams.
                            if not kernel_case:
                                admitted=json.loads(actual_read(Path(original['admission']['path'])))
                                command_binding=admitted['bindings']
                                request_path=command_binding['identity_request']['path']
                                request_doc=json.loads(actual_read(Path(request_path)))
                                for field in ('ownership_root','preexisting_ancestors','ancestry_terminal','retained_wrappers','output_paths'):
                                    request_doc[field]=copy.deepcopy(target_note[field])
                                    command_binding[field]=copy.deepcopy(target_note[field])
                                request_ref=store_projection(request_path,request_doc)
                                proof_path=command_binding['session_proof']['path']
                                proof_doc=json.loads(actual_read(Path(proof_path)))
                                old_line=proof_doc['readiness_line'];old_output='';event_docs=[]
                                for event_ref in proof_doc['tool_events']:
                                    document=json.loads(actual_read(Path(event_ref['path'])));event_docs.append(document);old_output+=document['result']['output']
                                proof_doc['identity_request']=request_ref
                                proof_doc['readiness_line']=json.dumps(dict(awaiting_main_admission=proof_doc['admission_path'],identity_request=request_ref))
                                proof_doc['readiness_line_sha256']=hashlib.sha256(proof_doc['readiness_line'].encode()).hexdigest()
                                delimiter='\r\n' if old_output.endswith('\r\n') else '\n'
                                new_output=proof_doc['readiness_line']+delimiter;cursor=0;event_refs=[]
                                for ordinal,(event_ref,document) in enumerate(zip(proof_doc['tool_events'],event_docs)):
                                    count=len(document['result']['output'])
                                    text=new_output[cursor:] if ordinal==proof_doc['readiness_event'] else new_output[cursor:cursor+count] if ordinal<proof_doc['readiness_event'] else ''
                                    cursor+=len(text);document['result']['output']=text;document['output_sha256']=hashlib.sha256(text.encode()).hexdigest()
                                    event_refs.append(store_projection(event_ref['path'],document))
                                proof_doc['tool_events']=event_refs;proof_ref=store_projection(proof_path,proof_doc)
                                command_binding['identity_request']=request_ref;command_binding['session_proof']=proof_ref
                                admission_ref=store_projection(original['admission']['path'],admitted)
                                target_note['admission']=admission_ref
                                target_note['bindings']=[projected_record(row['path']) if row['path'] in projected else row for row in target_note['bindings']]
                                store_projection(original_path,target_note);target_raw=projected[str(original_path)]
                            def text_target(path,*args,**kwargs):
                                if str(path) in projected:return projected[str(path)].decode(kwargs.get('encoding') or 'utf-8')
                                return actual_text(path,*args,**kwargs)
                            if not kernel_case:
                                h.INVOCATION.anchor=dict(saved_anchor,raw=target_raw)
                                start_doc['note']=dict(path=str(original_path),bytes=len(target_raw),sha256=hashlib.sha256(target_raw).hexdigest())
                            def read_target(path):
                                if kind=='capture_argv_swapped' and path==command_path:
                                    reached.append('live_capture_cmdline');return b'\0'.join(v.encode() for v in original['command']+['foreign'])+b'\0'
                                if not kernel_case and path==original_path:reached.append('pinned_note_bytes');return target_raw
                                if str(path) in projected:return projected[str(path)]
                                if not kernel_case and path==start_path:return json.dumps(start_doc).encode()
                                return actual_read(path)
                            def stat_target(path,*args,**kwargs):
                                value=actual_stat(path,*args,**kwargs)
                                if (kind=='stdin_inode_replaced' and path==stdin) or (kind=='driver_log_inode_swapped' and path==log_path):
                                    reached.append('named_descriptor_inode');fields=list(value);fields[1]+=1;return os.stat_result(fields)
                                return value
                            try:
                                with patch.dict(os.environ,{'S1_OWNED_ROOT_NOTE':str(original_path),'S1_OWNED_ROOT_SHA256':hashlib.sha256(original_path.read_bytes() if kernel_case else target_raw).hexdigest(),'S1_VALIDATION_RUN_DIRECTORY':original['run_directory']}),patch.object(Path,'read_bytes',read_target),patch.object(Path,'read_text',text_target),patch.object(Path,'stat',stat_target),patch.object(contract,'file_record',side_effect=projected_record):
                                    with self.assertRaisesRegex(ValueError,expected_error):h.owned_workload(original_path)
                                self.assertTrue(reached,kind)
                            finally:h.INVOCATION.anchor=saved_anchor
                            result=dict(generic_control=result,target=expected_error,reached=reached)
                        records.append(dict(case,source='owned_workload/InvocationRegistry/predispatch_owned',observed=result,registry_identity=id(h.INVOCATION),baseline=baseline['root']))
                    finally:h.INVOCATION.records=actual_records
        self.control_record('plan047-ownership',records)

    def test_progress_plan047_cancellation(self):
        from vipe_benchmark import s1_progress as p
        from test_vipe_benchmark_s1_helper_fixtures import progress_fixture,plan047_state
        records=[]
        with tempfile.TemporaryDirectory() as temp:
            fixture=progress_fixture(Path(temp)/'fixture')
            for index,case in enumerate(SUBTEST_CASES[f'{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}']):
                with self.subTest(**case),plan047_state(fixture,Path(temp)/str(index)) as state:
                    publisher=state.publisher;stage=case['stage'];seen=[];reads=[];pointer=state.cache.snapshot;now=[self.time.monotonic()]
                    if stage=='worker_authority_read':
                        publisher.close();publisher=p.Publisher(state.reference,'reconcile',1,clock=state.clock,trusted=state.cache.reference());state.publisher=publisher
                        # Exact acknowledged worker version and sources, no new guard.
                        doc=state.consumer.current['worker'][1];row=doc['rows'][0]
                        publisher.rows[0]=dict(row,authority=dict(row['authority'],worker_reference=state.consumer.current['worker'][0]));publisher.sources=doc['sources']
                    actual=state.consumer.read
                    forbidden=[]
                    def read(*args,**kwargs):
                        if state.cancelled[0]:forbidden.append(dict(operation='read',record=args[0]))
                        reads.append(args[0]);return actual(*args,**kwargs)
                    acknowledge=state.cache.acknowledge
                    def retain(*args,**kwargs):
                        if state.cancelled[0]:forbidden.append(dict(operation='retain'))
                        return acknowledge(*args,**kwargs)
                    actual_send=p.socket.socket.sendto
                    def sent(channel,*args,**kwargs):
                        if state.cancelled[0]:forbidden.append(dict(operation='send'))
                        return actual_send(channel,*args,**kwargs)
                    def boundary(name):
                        seen.append(name)
                        if name==stage+':'+case['when']:
                            state.cancelled[0]=True;state.cache.freeze('injected cancellation');now[0]=state.clock.work_deadline
                    with patch.object(p.socket.socket,'sendto',sent),patch.object(p,'publication_boundary',side_effect=boundary),patch.object(state.consumer,'read',side_effect=read),patch.object(state.cache,'acknowledge',side_effect=retain),patch.object(p.time,'monotonic',side_effect=lambda:now[0]):
                        with self.assertRaises((TimeoutError,InterruptedError)):publisher.publish()
                    self.assertIn(stage+':'+case['when'],seen)
                    if stage=='ack_receipt':self.assertIsNot(state.cache.snapshot,pointer)
                    else:self.assertIs(state.cache.snapshot,pointer)
                    self.assertTrue(state.cache.frozen)
                    self.assertEqual(forbidden,[])
                    records.append(dict(case,source='Consumer.tick/Publisher._publish',events=seen,reads=reads,retained=state.cache.reference(),acknowledged_before_receipt=stage=='ack_receipt'))
                    publisher.close()
        self.control_record('plan047-cancellation',records)
    def test_progress_plan047_complete_final_sample(self):
        import shutil,uuid,copy
        from types import SimpleNamespace
        from vipe_benchmark import supervisor as sup,s1_progress as p,s1_cpu_helper as cpu,s1_helper_session as h
        from vipe_benchmark.files import file_record
        from test_vipe_benchmark_s1_helper_fixtures import plan047_full_fixture
        full=plan047_full_fixture(self);records=[];real_lifecycle=sup.HelperLifecycle
        pristine=full.output.with_name('plan047-pristine');shutil.copytree(full.output,pristine);shutil.rmtree(full.output)
        for case in SUBTEST_CASES[f'{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}']:
            with self.subTest(**case):
                kind=case['kind'];finished={};sessions=[];trace=[];docs=full.fixture.root/('docs-'+kind);docs.mkdir()
                class Facade:
                    def __init__(inner):
                        inner.token=uuid.uuid4().hex;inner.ready={'work':{},'sample':{}};inner.setup_deadline=full.clock.work_deadline;inner.cleanup_deadline=full.clock.total_deadline
                        inner.progress_cache=p.RetainedProgress();inner.consumer=None;inner.context=None;inner.requests={'work':None,'sample':None};inner.responses=[];inner.sequence=0;inner.accepted=False;inner.last_sample={'post':SimpleNamespace(rows=[])};sessions.append(inner)
                    def resume(inner):pass
                    def await_ready(inner):pass
                    def admission_guard(inner):pass
                    def set_worker(inner,worker):inner.worker=worker
                    def worker_exit(inner):return 0
                    def retire_worker(inner):inner.worker=None
                    def ownership(inner):return []
                    def install_progress(inner,reference,deadline):
                        inner.context=reference;binding=p.process_binding(h.identity(os.getpid()))
                        inner.consumer=p.Consumer(reference,inner.progress_cache,lambda:False,lambda producer:(binding,inner.sequence))
                    def submit(inner,role,operation,deadline):
                        dispatched=self.time.monotonic();inner.requests[role]=operation
                        if role=='sample':
                            if kind=='final_sample_failure' and inner.accepted:
                                trace.append(dict(event='final_sample_failure',reference=inner.progress_cache.reference(),observed=self.time.monotonic()))
                                raise RuntimeError('plan047 genuine acceptance then final sample failure')
                            value=dict(self.reading)
                        else:
                            inner.sequence+=1;operation=copy.deepcopy(operation);name=operation['operation']
                            if name in ('accept','reconcile'):
                                operation['args'].update(progress_context=inner.context,trusted_progress=inner.progress_cache.reference())
                            with patch.object(p.Publisher,'after_notice',side_effect=lambda:inner.consumer.tick()):
                                value=cpu.session_operation(operation,inner.token,inner.sequence)
                            if name=='accept':
                                inner.accepted=True;self.assertEqual(inner.progress_cache.reference()['counts']['complete'],510)
                                trace.append(dict(event='accepted',result=value,reference=inner.progress_cache.reference(),observed=self.time.monotonic()))
                        received=self.time.monotonic();inner.responses.append((role,value,received,dispatched))
                    def tick(inner,deadline):
                        responses=inner.responses;inner.responses=[]
                        for role,_,_,_ in responses:inner.requests[role]=None
                        return responses
                    def close(inner,deadline):
                        if inner.consumer is not None:inner.consumer.close();inner.consumer=None
                        return True
                class Ledger:
                    path=full.fixture.ledger.path;config=full.fixture.config;jobs=full.fixture.ledger.jobs
                    def reserve(inner,*args,**kwargs):return full.reservation
                    def note(inner,*args,**kwargs):trace.append(dict(event='supervisor_note',args=args,fields=kwargs))
                    def finish(inner,job,status,elapsed,**kwargs):finished.update(status=status,elapsed=elapsed,**kwargs)
                def popen(*args,**kwargs):
                    shutil.copytree(pristine,full.output)
                    return SimpleNamespace(pid=os.getpid(),poll=lambda:0,wait=lambda **kw:0)
                def lifecycle(**kwargs):return real_lifecycle(session_factory=Facade,**kwargs)
                # Only transport/process creation and retirement are replaced.
                with patch.object(sup,'HelperLifecycle',side_effect=lifecycle),patch.object(sup.subprocess,'Popen',side_effect=popen),patch.object(sup,'stop_group',return_value=[]),patch.object(h,'register_owned',return_value=None),patch.object(p,'prepare_context',wraps=p.prepare_context) as prepared:
                    actual=cpu.session_operation
                    def operation(value,session,sequence):
                        if value['operation']=='prelaunch':
                            ref=actual(value,session,sequence)
                            # The serial facade is the owner in this process.
                            document=p.read_record(ref,p.SMALL_BYTES);document['owner_pid']=os.getpid();raw=p.encode(document,p.SMALL_BYTES);Path(ref['path']).write_bytes(raw);return p.record(ref['path'],raw)
                        return actual(value,session,sequence)
                    with patch.object(cpu,'session_operation',side_effect=operation):
                        if kind=='final_sample_failure':
                            with self.assertRaises(sup.SupervisionFailure) as caught:sup.supervise(Ledger(),full.reservation['job_id'],full.command,full.output,evidence=full.binding,sample_resources=self.sampler,validate_result=lambda output:None,terminal_publisher=True,terminal_docs=docs)
                            self.assertIn('genuine acceptance then final sample failure',str(caught.exception));self.assertIsNone(finished['terminal_receipt']);self.assertEqual(finished['status'],'failed')
                        else:
                            sup.supervise(Ledger(),full.reservation['job_id'],full.command,full.output,evidence=full.binding,sample_resources=self.sampler,validate_result=lambda output:None,terminal_publisher=True,terminal_docs=docs)
                            self.assertEqual(finished['status'],'complete');self.assertIsNotNone(finished['terminal_receipt'])
                reference=finished['verified_progress_reference'];self.assertEqual(reference['counts']['complete'],510);self.assertEqual(reference['counts']['fit_qualified'],340);self.assertEqual(reference['counts']['selection_qualified'],170)
                recovered=p.recover(reference);self.assertEqual(recovered['acceptance'],file_record(full.output/'acceptance.json'));self.assertEqual(recovered['first_result'],full.result['first_result']);self.assertEqual(recovered['runtime']['final'],file_record(full.output/'result.json'))
                records.append(dict(case,source='supervise/monitored_call/session_operation/accept_result/accepted_progress',trace=trace,finish=finished,reservation=full.reservation,result=file_record(full.output/'result.json'),reference=reference))
                full.output.rename(full.output.with_name('plan047-finished-'+kind));full.output.with_suffix('.log').rename(full.output.with_name('plan047-log-'+kind));shutil.rmtree(full.output.with_name(full.output.name+'-temporary'))
        self.control_record('plan047-complete-final-sample',records)
    def test_progress_plan047_state_authority(self):
        import copy
        from vipe_benchmark import s1_progress as p,s1_evidence as e
        from vipe_benchmark.files import write_json
        from test_vipe_benchmark_s1_helper_fixtures import progress_fixture,plan047_state
        records=[]
        with tempfile.TemporaryDirectory() as temp:
            fixture=progress_fixture(Path(temp)/'fixture')
            for case in SUBTEST_CASES[f'{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}']:
                active_fixture=fixture
                if case['kind'] in ('produced_then_semantic_failure','first_identity_semantics'):
                    active_fixture=copy.deepcopy(fixture)
                    if case['kind']=='produced_then_semantic_failure':active_fixture['rows'][0]['metadata']['detections'][0]['class_assignment']['derived_class']='invalid'
                    else:active_fixture['rows'][0]=copy.deepcopy(fixture['rows'][1])
                with self.subTest(**case),plan047_state(active_fixture,Path(temp)/case['kind'],qualified=case['kind'] not in ('worker_qualified_overclaim','produced_then_semantic_failure','first_identity_semantics')) as state:
                    kind=case['kind'];pub=state.publisher;before=state.cache.reference();pointer=state.cache.snapshot;reached=[];observed='rejected';replacement=None
                    try:
                        if kind in ('produced_then_semantic_failure','first_identity_semantics'):
                            row=p.read_record(state.row_record,256*1024)
                            self.assertEqual(row,state.row)
                            self.assertEqual(before['counts']['produced_lower_bound'],1);self.assertEqual(before['counts']['qualified'],0)
                            with self.assertRaises(ValueError):e.qualify_row(row,fixture['request'],first=True,deadline=state.clock.work_deadline)
                            self.assertIs(state.cache.snapshot,pointer);reached=['qualify_row real semantic/first guard']
                            self.assertEqual(state.cache.reference()['counts']['qualified'],0)
                            self.assertEqual(pub.rows[next(iter(pub.rows))]['version'],p.record(state.row_record['path'],p.encode(row,256*1024))['sha256'])
                        elif kind.startswith('worker_') or kind in ('trusted_conflict','discovered_conflict','fallback_no_unique_version','fallback_invalidated','conflict_to_closed','overflow_to_closed','overflow_to_incomplete','conflict_plus_overflow'):
                            if kind=='worker_detached_identity':
                                self.assertEqual(pub.binding,state.consumer.bindings('worker')[0]);self.assertEqual(pub.context['boot_id'],state.clock.boot_id);reached=['Consumer pinned full producer binding'];observed='accepted exact registered identity'
                                from vipe_benchmark import s1_helper_session as h
                                owner=h.Owner.__new__(h.Owner);pid=pub.binding['pid']
                                previous=dict(pub.binding,ppid=os.getppid(),state='S')
                                attached=owner.lineage({pid:previous},{pid},{})
                                detached=dict(previous,ppid=1)
                                retained=owner.lineage({pid:detached},set(),attached)
                                self.assertIn(pid,retained);self.assertEqual(p.process_binding(retained[pid]),pub.binding)
                                self.assertEqual(retained[pid]['ppid'],1)
                                with self.assertRaisesRegex(ValueError,'identity changed'):
                                    owner.lineage({pid:dict(detached,start_ticks=detached['start_ticks']+1)},set(),attached)
                                binding_reads=[];current_rows={pid:previous};lineage=[attached]
                                def retained_binding(producer):
                                    lineage[0]=owner.lineage(current_rows,set(),lineage[0])
                                    binding_reads.append(dict(producer=producer,rows=copy.deepcopy(lineage[0]),boot_id=state.clock.boot_id))
                                    return p.process_binding(lineage[0][pid]),1
                                state.consumer.bindings=retained_binding
                                pub.publish();attached_ack=state.cache.reference();current_rows={pid:detached}
                                pub.publish();self.assertEqual(state.cache.reference()['counts'],before['counts'])
                                detached_ack=state.cache.reference();self.assertNotEqual(attached_ack['checkpoints'],detached_ack['checkpoints'])
                                self.assertEqual(state.consumer.current['worker'][1]['binding'],pub.binding)
                                self.assertTrue(any(item['rows'][pid]['ppid']==1 for item in binding_reads))
                                fallback=p.Publisher(state.reference,'reconcile',1,clock=state.clock,trusted=detached_ack)
                                try:
                                    fallback.publish();self.assertEqual(state.cache.reference()['counts'],before['counts'])
                                finally:fallback.close()
                                state.cache.freeze();frozen=state.cache.reference();self.assertTrue(frozen['frozen'])
                                self.assertEqual(p.recover(frozen)['counts'],before['counts'])
                                self.assertIsNone(p.recover(frozen)['acceptance'])
                                state.cache.frozen=False
                                reached.append(dict(operation='Owner.lineage/Consumer acknowledgment/reconcile/freeze/recover',attached=attached,detached=retained,binding_reads=binding_reads,attached_ack=attached_ack,detached_ack=detached_ack,frozen=frozen,accepted=False))
                            else:
                                replacement=p.Publisher(state.reference,'reconcile',1,clock=state.clock,trusted=before);doc=state.consumer.current['worker'][1];sealed=doc['rows'][0]
                                replacement.rows[0]=dict(copy.deepcopy(sealed),authority=dict(sealed['authority'],worker_reference=before['checkpoints']['worker']));replacement.sources=copy.deepcopy(doc['sources'])
                                if kind=='worker_reuse_exact':
                                    with patch.object(e,'qualify_row',side_effect=AssertionError('raw guard during reuse')),patch.object(e,'produced_row',side_effect=AssertionError('raw guard during reuse')):replacement.publish()
                                    observed='exact worker authority reused'
                                elif kind=='worker_stale_interleave':
                                    pub.publish()
                                    with self.assertRaisesRegex(ValueError,'worker authority'):replacement.publish()
                                elif kind in ('worker_future_reference','worker_self_reference'):
                                    if kind=='worker_future_reference':
                                        future=copy.deepcopy(doc);future.update(sequence=doc['sequence']+1,previous=before['checkpoints']['worker'])
                                        path=Path(before['checkpoints']['worker']['path']).with_name(str(future['sequence']).zfill(4)+'.json')
                                        p.write_exclusive(path,p.encode(future));reference=p.record(path,path.read_bytes())
                                        p.validate_checkpoint(p.read_record(reference),pub.context,state.reference)
                                    else:
                                        issued=copy.deepcopy(doc);issued.update(producer='reconcile',binding=replacement.binding,coverage='closed',sequence=1,previous=None)
                                        path=Path(state.reference['path']).parent/'reconcile'/'0001.json'
                                        issued['rows'][0]['authority'].update(producer='reconcile',worker_reference=None)
                                        p.write_exclusive(path,p.encode(issued));reference=p.record(path,path.read_bytes())
                                        p.validate_checkpoint(p.read_record(reference),pub.context,state.reference)
                                        # Keep the attempted current reconcile publication on its next
                                        # independent filename while the self-issued record stays untrusted.
                                        path.rename(path.with_name('self-issued.json'));reference=p.record(path.with_name('self-issued.json'),p.encode(issued))
                                    replacement.rows[0]['authority']['worker_reference']=reference
                                    with self.assertRaises(ValueError):replacement.publish()
                                elif kind=='worker_qualified_overclaim':
                                    replacement.rows[0]['qualified']=True
                                    with self.assertRaises(ValueError):replacement.publish()
                                elif kind=='worker_sources_changed':
                                    replacement.sources[0]=dict(replacement.sources[0],sha256='0'*64)
                                    with self.assertRaises(ValueError):replacement.publish()
                                elif kind=='worker_row_version_changed':
                                    replacement.rows[0]['row']=dict(sealed['row'],sha256='0'*64)
                                    with self.assertRaises(ValueError):replacement.publish()
                                elif kind=='trusted_conflict':
                                    replacement.rows[0]['authority'].update(producer='reconcile',worker_reference=None,version='0'*64);replacement.rows[0]['version']='0'*64;replacement.coverage='closed'
                                    with self.assertRaisesRegex(ValueError,'conflicting producer'):replacement.publish()
                                elif kind in ('discovered_conflict','fallback_no_unique_version','fallback_invalidated'):
                                    output=state.root/'inventory';output.mkdir();write_json(output/'one-produced-row.json',fixture['rows'][0]);changed=copy.deepcopy(fixture['rows'][0]);changed['metadata']['variant']=1;write_json(output/'two-produced-row.json',changed)
                                    if kind=='discovered_conflict':
                                        result=e.reconcile_rows(output,fixture['request'],deadline=state.clock.work_deadline,publisher=replacement);self.assertEqual(result['counts']['qualified'],1);self.assertEqual(replacement.coverage,'conflict')
                                    elif kind=='fallback_no_unique_version':
                                        result=e.reconcile_rows(output,fixture['request'],deadline=state.clock.work_deadline);self.assertEqual(result['counts']['produced_lower_bound'],0)
                                    else:
                                        _,inventory=p.candidate_inventory(output,None,state.clock.work_deadline);write_json(output/'three-produced-row.json',changed)
                                        with self.assertRaises(ValueError):inventory.recheck(state.clock.work_deadline)
                                        from test_vipe_benchmark_s1_helper_fixtures import invalidated_fallback
                                        reached.append(invalidated_fallback(self,fixture,state.root/'real-invalidated',kind))
                                    observed='sticky conflict or closed inventory invalidation'
                                else:
                                    old='conflict' if kind.startswith('conflict') else 'overflow';replacement.coverage=old;replacement.failure(ValueError(old));replacement.publish()
                                    recovered=p.recover(state.cache.reference());self.assertTrue(recovered['stop_required'])
                                    self.assertEqual(recovered['coverage']['reconcile'],old)
                                    self.assertEqual(recovered['diagnostics']['reconcile']['primary']['message'],old)
                                    self.assertTrue(p.summary_adapter(recovered)['stop_required'])
                                    if kind=='conflict_plus_overflow':replacement.coverage='overflow';self.assertEqual(replacement.coverage,'conflict');self.assertTrue(any('overflow' in x for x in replacement.errors));observed='both failures retained'
                                    else:
                                        new='incomplete' if kind.endswith('incomplete') else 'closed'
                                        with self.assertRaises(ValueError):replacement.coverage=new
                                reached=['Publisher.publish','Consumer.tick worker-authority/coverage/merge']
                        elif kind=='errors_saturation':
                            for i in range(35):pub.failure(ValueError(str(i)))
                            pub.publish();self.assertEqual(len(pub.errors),32);self.assertEqual(pub.diagnostics['dropped'],3);self.assertEqual(pub.diagnostics['primary']['message'],'0');reached=['Publisher.failure','validate_diagnostics'];observed='32 messages plus 3 drops'
                        elif kind.startswith('diagnostics_'):
                            pub.failure(ValueError('original'));pub.publish();pub.failure(ValueError('later'))
                            if kind=='diagnostics_drop_regression':pub.acknowledged_diagnostics['dropped']=1
                            else:pub.diagnostics['primary']=dict(pub.diagnostics['primary'],message='replacement')
                            with self.assertRaises(ValueError):pub.publish()
                            reached=['diagnostic_transition']
                        elif kind=='checkpoint_v1_rejected':
                            document=p.read_record(pub.previous);document['schema']='s1-verified-progress/v1'
                            with self.assertRaises(ValueError):p.validate_checkpoint(document,pub.context,state.reference)
                            reached=['validate_checkpoint schema']
                        elif kind=='qualification_regression':
                            pub.rows[0]['qualified']=False
                            with self.assertRaises(ValueError):pub.publish()
                            reached=['Consumer.tick row regression']
                        elif kind=='first_runtime_regression':
                            pub.first_result=state.row_record;pub.runtime['final']=state.row_record;pub.publish();pub.first_result=None;pub.runtime={}
                            with self.assertRaises(ValueError):pub.publish()
                            reached=['Consumer.tick state regression']
                        elif kind=='acceptance_regression':
                            # The transition predicate is tested independently of the
                            # full numerical acceptance covered by the paired controller.
                            old=p.read_record(pub.previous);new=copy.deepcopy(old);old['acceptance']=state.row_record
                            with self.assertRaises(ValueError):p.acceptance_transition(old,new)
                            reached=['acceptance_transition used by Consumer.tick']
                        elif kind in ('duplicate_exact','duplicate_conflict','sequence_replay','sequence_jump','request_changed_late'):
                            current=p.read_record(pub.previous);reference=state.cache.reference();notice=dict(schema='s1-progress-notice/v1',context=state.reference,producer='worker',binding=pub.binding,request_id=1,sequence=pub.sequence,current=pub.previous,previous=current['previous'],head=reference['provenance']['worker']['accepted_head'],completed=self.time.monotonic())
                            if kind=='duplicate_conflict':notice['current']=dict(notice['current'],sha256='0'*64)
                            elif kind=='sequence_replay':notice['sequence']-=1
                            elif kind=='sequence_jump':notice['sequence']+=2
                            elif kind=='request_changed_late':notice['request_id']=2
                            pub.channel.sendto(p.encode(notice,p.CONTROL_BYTES),p.address(pub.context))
                            if kind=='duplicate_exact':state.consumer.tick();self.assertEqual(state.cache.reference()['checkpoints'],reference['checkpoints']);observed='idempotent duplicate acknowledged'
                            else:
                                with self.assertRaises(ValueError):state.consumer.tick()
                            reached=['Consumer.tick credential/sequence/duplicate']
                        else:raise AssertionError(kind)
                        records.append(dict(case,source=reached,observed=observed,before=before,after=state.cache.reference()))
                    finally:
                        if replacement is not None:replacement.close()
        self.control_record('plan047-state-authority',records)
    def test_progress_plan047_result_summary(self):
        import copy,json,struct,socket
        from vipe_benchmark import s1_progress as p,s1_evidence as e
        from vipe_benchmark.files import write_json
        from test_vipe_benchmark_s1_helper_fixtures import progress_fixture,plan047_state,plan047_full_fixture
        records=[]
        with tempfile.TemporaryDirectory() as temp:
            fixture=progress_fixture(Path(temp)/'fixture')
            with plan047_state(fixture,Path(temp)/'state') as state:
                checkpoint=p.read_record(state.publisher.previous);reference=state.cache.reference();trusted=p.recover(reference)
                notice=dict(schema='s1-progress-notice/v1',context=state.reference,producer='worker',binding=state.publisher.binding,request_id=1,sequence=state.publisher.sequence,current=state.publisher.previous,previous=checkpoint['previous'],head=reference['provenance']['worker']['accepted_head'],completed=self.time.monotonic())
                ack=dict(schema='s1-progress-ack/v1',context=state.reference['sha256'],producer='worker',sequence=2,current=state.publisher.previous)
                for case in SUBTEST_CASES[f'{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}']:
                    with self.subTest(**case):
                        kind=case['kind'];doc=copy.deepcopy(checkpoint);ctx=copy.deepcopy(state.publisher.context);ref=copy.deepcopy(reference);msg=copy.deepcopy(notice);response=copy.deepcopy(ack);source='';expected_failure=True
                        if kind.startswith('result_'):
                            source='strict result decode/candidate_inventory/validate_result'
                            raw={'result_duplicate_top':b'{"rows":[],"rows":[]}', 'result_duplicate_row':b'{"rows":[{"identity":{"camera":0,"camera":0}}]}', 'result_nonfinite':b'{"rows":[],"value":NaN}'}.get(kind)
                            if raw is not None:
                                root=Path(temp)/kind;root.mkdir();(root/'result.json').write_bytes(raw)
                                action=lambda:p.candidate_inventory(root,None,state.clock.work_deadline)
                            elif kind=='result_supplied_bool_int':
                                root=Path(temp)/kind;root.mkdir();write_json(root/'result.json',dict(rows=[],count=1));action=lambda:p.candidate_inventory(root,dict(rows=[],count=True),state.clock.work_deadline)
                            else:
                                full=plan047_full_fixture(self);raw=(full.output/'result.json').read_bytes();parsed=p.decode(raw,p.MAX_METADATA,max_depth=64,max_nodes=1048576)
                                self.assertEqual(len(parsed['rows']),510);self.assertTrue(e.validate_result(parsed,full.request,full.fixture.config,clock=full.clock,deadline=full.clock.work_deadline));action=lambda:parsed;expected_failure=False
                        elif kind.startswith(('runtime_','first_','summary_')):
                            ordinary=dict(runtime={},first_result=dict(status='unverified',value=None),verification_errors=[]);target=copy.deepcopy(trusted)
                            if kind=='runtime_unverified_nonnull':ordinary['runtime']['final']=dict(status='unverified',value={})
                            elif kind=='runtime_verified_null':ordinary['runtime']['final']=dict(status='verified',value=None)
                            elif kind=='runtime_unknown_status':ordinary['runtime']['final']=dict(status='unknown',value=None)
                            elif kind=='first_unverified_nonnull':ordinary['first_result']['value']={}
                            elif kind=='runtime_final_conflict':target['runtime']['final']=state.row_record;ordinary['runtime']['final']=dict(status='verified',value=dict(state.row_record,sha256='0'*64))
                            elif kind=='runtime_alias':ordinary['runtime']['partial']=dict(status='unverified',value=None)
                            elif kind=='summary_unknown_totals':ordinary['counts']={'produced':0};expected_failure=False
                            action=lambda:p.summary_adapter(target,ordinary);source='summary_adapter exact status/null/unknown totals'
                        elif kind in ('notice_bool_pid','notice_bool_request'):
                            if kind=='notice_bool_pid':msg['binding']['pid']=True
                            else:msg['request_id']=True
                            action=lambda:p.validate_notice(msg);source='validate_notice nested typed binding'
                        elif kind=='ack_bool_sequence':response['sequence']=True;action=lambda:p.validate_ack(response);source='validate_ack'
                        elif kind.startswith('clock_'):
                            ctx['clock']['monotonic_start']={'clock_bool_start':True,'clock_negative_time':-1,'clock_overflow_time':10**400,'clock_nonfinite':float('inf')}[kind]
                            action=lambda:p.context_document(ctx);source='context_document/ReservationClock.from_mapping'
                        elif kind=='reservation_bool_sequence':ctx['clock']['reservation']['sequence']=True;action=lambda:p.context_document(ctx);source='context reservation'
                        elif kind=='process_pid_bound':ctx['work']['pid']=2**31;action=lambda:p.context_document(ctx);source='context process binding'
                        elif kind.startswith('identity_'):
                            if kind=='identity_bool_camera':doc['rows'][0]['identity']['camera']=True
                            elif kind=='identity_wrong_branch':doc['rows'][0]['identity']['branch']='reconstruction'
                            elif kind=='identity_pair_nonnull':doc['rows'][0]['identity']['pair_start']=20
                            else:doc['rows']*=2
                            action=lambda:p.validate_checkpoint(doc,ctx,state.reference);source='validate_checkpoint identity membership/order'
                        elif kind.startswith('indices_'):
                            doc['rows'][0]['source_indices']={'indices_bool':[True],'indices_duplicate':[0,0],'indices_out_of_range':[len(doc['sources'])]}[kind];action=lambda:p.validate_checkpoint(doc,ctx,state.reference);source='validate_checkpoint source indices'
                        elif kind=='context_wrong_boot':ctx['boot_id']='0'*36;action=lambda:p.context_document(ctx);source='context boot correlation'
                        elif kind=='context_wrong_guard':doc['rows'][0]['authority']['guard']='0'*64;action=lambda:p.validate_checkpoint(doc,ctx,state.reference);source='checkpoint source-bound guard'
                        elif kind in ('notice_wrong_uid','notice_wrong_pid','notice_wrong_sender'):
                            actual=p.receive
                            def receive(channel):
                                value,cred,sender=actual(channel)
                                if kind=='notice_wrong_uid':cred=(cred[0],cred[1]+1,cred[2])
                                elif kind=='notice_wrong_pid':cred=(cred[0]+1,cred[1],cred[2])
                                else:sender=b'\0foreign'
                                return value,cred,sender
                            state.publisher.channel.sendto(p.encode(msg,p.CONTROL_BYTES),p.address(ctx))
                            def action():
                                with patch.object(p,'receive',side_effect=receive):state.consumer.tick()
                            source='Consumer actual datagram credentials'
                        elif kind in ('notice_truncated','notice_missing_credentials'):
                            class Channel:
                                def recvmsg(inner,*args):return p.encode(msg,p.CONTROL_BYTES),[],socket.MSG_TRUNC if kind=='notice_truncated' else 0,b'\0address'
                            action=lambda:p.receive(Channel());source='receive MSG_TRUNC/SCM credentials'
                        elif kind=='ack_wrong_binding':
                            response['context']='0'*64
                            action=lambda:p.ack_correlation(response,ack);source='ack_correlation used by Publisher'
                        elif kind.startswith('reference_'):
                            if kind=='reference_v1_rejected':ref['schema']='s1-progress-reference/v1'
                            elif kind=='reference_bool_frozen':ref['frozen']=1
                            else:ref['reservation']['event_sha256']='0'*64
                            action=lambda:p.recover(ref);source='recover exact reference binding'
                        else:raise AssertionError(kind)
                        # A failed credential notice freezes that cache; reset only
                        # this test's owner cancellation state for independent cases.
                        if expected_failure:
                            with self.assertRaises((ValueError,TypeError,OverflowError)) as caught:action()
                            observed=type(caught.exception).__name__
                        else:
                            value=action();observed='accepted'
                            if kind=='summary_unknown_totals':self.assertEqual(value['counts']['produced'],'unknown');self.assertEqual(value['counts']['produced_lower_bound'],1)
                        records.append(dict(case,source=source,observed=observed,fixture=state.reference))
                        state.cache.frozen=False;state.cache.integrity=None
        self.control_record('plan047-result-summary',records)
    def test_progress_plan047_deadline_steps(self):
        import contextlib,copy
        import numpy as np
        from vipe_benchmark import s1_progress as p,s1_evidence as e,stages,s1_recovery as recovery,supervisor as sup
        from vipe_benchmark.files import file_record,write_json
        from test_vipe_benchmark_s1_helper_fixtures import progress_fixture,plan047_state,plan047_full_fixture
        evidence=[];full=None;before_controls={}
        publication={'checkpoint_write':'write','checkpoint_flush':'flush','checkpoint_fsync':'file_fsync','checkpoint_close':'close','checkpoint_readback':'close_readback','head_write':'write','head_flush':'flush','head_fsync':'file_fsync','head_close':'close','head_readback':'close_readback','generation_install':'generation_install','generation_dir_fsync':'generation_directory_fsync','generation_reopen_hash':'generation_reopen_hash','head_install':'head_install','head_dir_fsync':'head_directory_fsync','final_head_read':'final_head_read','final_generation_read':'final_generation_read','notice_send':'notice_send','owner_retention':'owner_retention','ack_send':'ack_send','ack_receipt':'ack_receipt'}
        with tempfile.TemporaryDirectory() as temp:
            fixture=progress_fixture(Path(temp)/'fixture',states=True)
            for index,case in enumerate(SUBTEST_CASES[f'{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}']):
                with self.subTest(**case),plan047_state(fixture,Path(temp)/str(index)) as state,contextlib.ExitStack() as stack:
                    name=case['operation'];offset={'before':-.001,'equal':0.,'after':.001}[case['when']];now=[self.time.monotonic()];deadline=state.clock.work_deadline;seen=[];phase=['checkpoint'];pointer=state.cache.snapshot;source=name;expected_late=case['when']!='before';current_stage=[''];injected=[False];injection_files=[None];injection_observations=[];witness=None
                    partial_roots=[state.root]
                    def snapshot_files():
                        result={}
                        # Test-only retrospective bytes are read through the
                        # original stream seam and never counted as production.
                        for directory in partial_roots:
                            for path in directory.rglob('*'):
                                if path.is_file():
                                    with baseline_path_open(path,'rb') as stream:result[str(path)]=stream.read()
                        return result
                    baseline_path_open=Path.open
                    def remember_predecessor(label):
                        injection_files[0]=snapshot_files()
                        injection_observations.append(dict(operation=label,entered_before=now[0],returned_at=deadline+offset))
                    if name=='runtime_guard' and case['when']=='before':
                        from test_vipe_benchmark_s1_helper_fixtures import backend_gate_controls,backend_retirement_controls,backend_interior_controls
                        seen.append(dict(stage='real_backend_cpu_constructor_seams',evidence=backend_gate_controls(self,fixture,state.root),retirement=backend_retirement_controls(self,state.root),interior=backend_interior_controls(self,state.root)))
                        from test_vipe_benchmark_s1_helper_fixtures import backend_retirement_transition_controls,publication_equality_controls
                        seen.append(dict(stage='correction006_retirement_and_exact_C',retirement=backend_retirement_transition_controls(self,state.root),publication=publication_equality_controls(self,fixture,state.root)))
                    if name in publication:
                        if name in ('notice_send','owner_retention','ack_send','ack_receipt'):now[0]=deadline-.25
                        target=publication[name]
                        current_stage=[''];injected=[False]
                        def advance(label):
                            nonlocal pointer
                            if injected[0]:return
                            if name!='ack_send':pointer=state.cache.snapshot
                            injected[0]=True
                            remember_predecessor(label)
                            seen.append(dict(stage=label,state='preceding_real_return',observed=now[0]));now[0]=deadline+offset
                        original_boundary=p.publication_boundary
                        def boundary(stage):
                            original_boundary(stage)
                            current_stage[0]=stage;seen.append(dict(stage=stage,observed=now[0]))
                            if stage=='generation_directory_fsync':phase[0]='head'
                        actual_operation=p.operation
                        def operation(function,*args,**kwargs):
                            label=getattr(function,'__name__','operation');stage=current_stage[0]
                            selected=(not name.startswith('head_') or phase[0]=='head') and (not name.startswith('checkpoint_') or phase[0]=='checkpoint')
                            value=actual_operation(function,*args,**kwargs)
                            predecessor={'checkpoint_flush':('write','write'),'head_flush':('write','write'),
                                'checkpoint_fsync':('flush','flush'),'head_fsync':('flush','flush'),
                                'checkpoint_close':('file_fsync','fsync'),'head_close':('file_fsync','fsync'),
                                'checkpoint_readback':('close','close'),'head_readback':('close','close'),
                                'generation_dir_fsync':('generation_install','unlink'),
                                'generation_reopen_hash':('generation_directory_fsync','record'),
                                'head_dir_fsync':('head_install','replace'),
                                'final_head_read':('head_directory_fsync','record'),
                                'final_generation_read':('final_head_read','read_record')}.get(name)
                            if selected and predecessor==(stage,label):advance(stage+'/'+label)
                            return value
                        fdopen=p.os.fdopen
                        def opened(fd,mode,*args,**kwargs):
                            value=fdopen(fd,mode,*args,**kwargs)
                            if mode=='wb' and name==phase[0]+'_write':advance(phase[0]+'/fdopen')
                            return value
                        exclusive=p.write_exclusive
                        def written(path,*args,**kwargs):
                            value=exclusive(path,*args,**kwargs)
                            if (name=='generation_install' and Path(path).name=='checkpoint.tmp') or (name=='head_install' and Path(path).name=='head.tmp'):advance(str(path)+'/durable_write_return')
                            return value
                        encode=p.encode
                        def encoded(value,*args,**kwargs):
                            raw=encode(value,*args,**kwargs)
                            if isinstance(value,dict) and value.get('schema')=='s1-progress-notice/v1':
                                seen.append(dict(stage='actual_notice_freshness',completed=value['completed'],publication_clock=now[0],boundary=deadline+offset,fresh_until=min(deadline,value['completed']+.5)))
                                if name in ('notice_send','owner_retention','ack_send','ack_receipt') and not expected_late:self.assertLess(deadline+offset,min(deadline,value['completed']+.5))
                            if isinstance(value,dict) and ((name=='notice_send' and value.get('schema')=='s1-progress-notice/v1') or (name=='owner_retention' and value.get('schema')=='s1-progress-ack/v1')):advance(value['schema']+'/encode')
                            return raw
                        retain=state.cache.retain
                        def retained(snapshot):
                            value=retain(snapshot)
                            if name=='ack_send':advance('RetainedProgress.retain')
                            return value
                        receive=p.receive
                        def received(channel):
                            value=receive(channel)
                            if name=='ack_receipt' and channel is state.publisher.channel:advance('matching_ack_receive')
                            return value
                        stack.enter_context(patch.object(p,'publication_boundary',side_effect=boundary))
                        stack.enter_context(patch.object(p,'operation',side_effect=operation));stack.enter_context(patch.object(p.os,'fdopen',side_effect=opened))
                        stack.enter_context(patch.object(p,'write_exclusive',side_effect=written));stack.enter_context(patch.object(p,'encode',side_effect=encoded))
                        stack.enter_context(patch.object(state.cache,'retain',side_effect=retained));stack.enter_context(patch.object(p,'receive',side_effect=received));action=state.publisher.publish
                    elif name=='worker_popen':
                        from types import SimpleNamespace
                        reservation=dict(state.clock.mapping());original=self.time.monotonic();outcome={};started=[]
                        reservation=copy.deepcopy(recovery_clock:=dict(event='reserve',job_id='S1-calibration-recovery-001',sequence=7,event_sha256='a'*64,boot_id=state.clock.boot_id,monotonic_start=original,seconds=4,evidence={'request':fixture['request_record'],'authorization':fixture['request']['recovery_authorization']}));deadline=original+3
                        class Session:
                            def admission_guard(inner):pass
                            def install_progress(inner,*args):
                                p.read_record(args[0],p.SMALL_BYTES);seen.append(dict(stage='install_progress_real_context_read_return',observed=now[0]));injected[0]=True;remember_predecessor('install_progress_real_context_read_return');now[0]=deadline+offset
                            def retire_worker(inner):pass
                            def close(inner,deadline):return True
                            def ownership(inner):return []
                        life=sup.HelperLifecycle(retain=True);life.helpers=[Session()]
                        class Ledger:
                            path=state.root/'ledger.jsonl';config=load();jobs={'S1-calibration-recovery-001':dict(resource='gpu')}
                            def reserve(inner,*args,**kwargs):return reservation
                            def note(inner,*args,**kwargs):pass
                            def finish(inner,*args,**kwargs):outcome.update(kwargs)
                        def monitor(*args,**kwargs):
                            if kwargs['phase']=='initial_sample':return self.reading
                            if kwargs['phase']=='prelaunch':return state.reference
                            raise RuntimeError('pure terminal stop')
                        def popen(*args,**kwargs):
                            started.append(now[0]);witness.target.append(dict(operation='Popen',entered=now[0],exited=now[0],completed=False,error_class='RuntimeError'))
                            self.assertLess(now[0],deadline)
                            raise RuntimeError('pure worker Popen reached')
                        stack.enter_context(patch.object(sup,'HelperLifecycle',return_value=life));stack.enter_context(patch.object(sup,'monitored_call',side_effect=monitor));stack.enter_context(patch.object(sup.subprocess,'Popen',side_effect=popen))
                        from vipe_benchmark import s1_helper_session as worker_ownership
                        def forbidden_registration(*args,**kwargs):
                            witness.successor.append(dict(operation='post_creation_registration',entered=now[0]))
                            raise AssertionError('registration after absent worker handle')
                        stack.enter_context(patch.object(worker_ownership,'register_owned',side_effect=forbidden_registration))
                        action=lambda:sup.supervise(Ledger(),'S1-calibration-recovery-001',['unused'],state.root/'worker-output',evidence={},sample_resources=self.sampler)
                    else:
                        # A real immutable metadata read is the immediate preceding
                        # operation; equality and after prohibit new expensive work.
                        raw=p.read_bytes(state.row_record['path'],256*1024);self.assertEqual(p.record(state.row_record['path'],raw),state.row_record);seen.append(dict(stage='preceding_real_metadata_read',observed=now[0]))
                        if name in ('array_npy','array_hash'):action=lambda:stages.array_file(state.root/'array.npy',np.zeros((2,2),np.int32),deadline=deadline)
                        elif name=='array_png':action=lambda:stages.png_file(state.root/'array.png',np.zeros((2,2),np.uint8),deadline=deadline)
                        elif name in ('npz_member','npz_finalize','cleanup_next_array'):action=lambda:e.numeric_file(state.root/'array.npz',{'a':np.arange(4),'b':np.arange(4)},deadline=deadline)
                        elif name in ('produced_json','produced_read'):
                            action=lambda:p.publish_segment_row(state.row,fixture['request'],e.input_loader(fixture['request']),state.clock,state.publisher,state.root/'produced.json',state.root/'qualified.json',first=True)
                        elif name=='produced_guard':action=lambda:e.produced_row(state.row,fixture['request'],deadline=deadline)
                        elif name=='qualified_guard':action=lambda:e.qualify_row(state.row,fixture['request'],first=True,deadline=deadline)
                        elif name=='runtime_guard':action=lambda:e.qualify_runtime(fixture['observed_runtime'],fixture['request'],deadline=deadline)
                        elif name in ('first_guard','reuse_after_read'):
                            from test_vipe_benchmark_s1_helper_fixtures import fixture_interpreter_adapter
                            adapter=stack.enter_context(fixture_interpreter_adapter(fixture,seen,deadline=deadline))
                            self.assertEqual(adapter(fixture['request']['runtime']['python']),fixture['interpreter_adapter']['record'])
                            alias=state.root/'untrusted-interpreter-alias';alias.symlink_to(fixture['interpreter_adapter']['target'])
                            try:
                                with self.assertRaises(OSError):adapter(alias)
                            finally:alias.unlink()
                            original_target=fixture['interpreter_adapter']['target']
                            with patch.dict(fixture['interpreter_adapter'],target=str(state.root/'substituted-target')):
                                with self.assertRaisesRegex(ValueError,'fixture original interpreter target changed'):
                                    with fixture_interpreter_adapter(fixture,seen,deadline=deadline) as altered:altered(fixture['request']['runtime']['python'])
                            self.assertEqual(fixture['interpreter_adapter']['target'],original_target)
                            checks=e.qualify_row(state.row,fixture['request'],first=True);kwargs=dict(clock=state.clock,rows=[state.row],runtime=fixture['observed_runtime'],checks=checks,raw=[state.row['diagnostics']])
                            first=e.first_record(fixture['request'],state.root,'passed',**kwargs);value=read_json(first['path'])
                            action=(lambda:e.verify_first(value,fixture['request'],clock=state.clock,deadline=deadline)) if name=='first_guard' else (lambda:e.first_record(fixture['request'],state.root,'passed',**kwargs))
                        elif name in ('accept_after_read','complete_after_read'):
                            if full is None:full=plan047_full_fixture(self)
                            deadline=full.clock.work_deadline
                            if name=='accept_after_read':action=lambda:recovery.accept_result(full.fixture.root,full.fixture.config,full.request,full.result,full.output,reservation=full.reservation)
                            else:
                                # Explicit real prerequisite; this callback cannot inherit
                                # a failed accept callback as an implicit baseline.
                                if not (full.output/'acceptance.json').exists():
                                    recovery.accept_result(full.fixture.root,full.fixture.config,full.request,full.result,full.output,reservation=full.reservation)
                                e.validate_result(full.result,full.request,full.fixture.config,clock=full.clock,deadline=deadline)
                                acceptance=file_record(full.output/'acceptance.json')
                                accepted=p.read_record(acceptance,32*1024*1024)
                                self.assertEqual(accepted['result'],file_record(full.output/'result.json'))
                                self.assertEqual(accepted['count'],510)
                                seen.append(dict(stage='real_acceptance_prerequisite',acceptance=acceptance,result=accepted['result'],fresh_validation=True,observed=now[0]))
                                action=lambda:recovery.prepare_terminal_evidence(full.fixture.root,full.reservation,dict(error=None,result=file_record(full.output/'result.json'),acceptance=acceptance),deadline,config=full.fixture.config)
                        elif name=='next_input':
                            import builtins
                            from types import SimpleNamespace
                            from test_vipe_benchmark_s1_recovery import ReservationClockTests,synthetic_row
                            from test_vipe_benchmark_s1_helper_fixtures import inline_progress
                            from vipe_benchmark.access import Identity
                            from vipe_benchmark.backends import SegmentationResult
                            admitted=ReservationClockTests();self.addCleanup(admitted.doCleanups)
                            segment_fixture,segment_request,_,segment_clock=admitted.admitted(reduced=True)
                            deadline=segment_clock.work_deadline;now[0]=segment_clock.monotonic_start+1
                            partial_roots.append(segment_fixture.root/'next-input-output')
                            native_row,native_arrays=synthetic_row(segment_fixture.root/'next-input-native',segment_request)
                            prediction=SegmentationResult(np.load(native_row['instances']['path']),native_row['semantics'],np.ones((540,960),bool),native_row['metadata'],diagnostics=native_arrays)
                            actual_load=e.load_rgb;actual_print=builtins.print;second_entries=[];native_entries=[]
                            def segment_load(loader,identity):
                                if identity.frame==62:
                                    second_entries.append(now[0]);self.assertLess(now[0],deadline)
                                    event=dict(operation='load_rgb(frame62)',entered=now[0],completed=False);witness.target.append(event)
                                    value=actual_load(loader,identity);event.update(exited=now[0],completed=True)
                                    load_context[0]='second_input_validation'
                                    return value
                                return actual_load(loader,identity)
                            def predicted(*args,**kwargs):
                                if injected[0]:
                                    witness.successor.append(dict(operation='frame62_native',entered=now[0]));raise AssertionError('frame62 native successor')
                                native_entries.append(now[0]);return [prediction]
                            def preceding_print(*args,**kwargs):
                                value=actual_print(*args,**kwargs)
                                first_reference=inline_cache.reference();first_recovered=p.recover(first_reference)
                                self.assertIsNotNone(first_recovered['first_result'])
                                self.assertEqual(first_reference['counts']['produced_lower_bound'],1)
                                self.assertEqual(first_reference['counts']['qualified'],1)
                                first_value=read_json(first_recovered['first_result']['path'])
                                self.assertTrue(e.verify_first(first_value,segment_request,clock=segment_clock))
                                seen.append(dict(stage='frame50_first_acknowledged_and_reverified',reference=first_reference,first=first_recovered['first_result']))
                                advance('segment_frame50_print_return_before_frame62')
                                return value
                            inline_reference,inline_cache=stack.enter_context(inline_progress(segment_fixture.root,segment_clock,segment_request,segment_fixture.config))
                            actual_array=e.load_array;actual_publish=p.publish_segment_row;load_context=['native_work'];load_calls=[]
                            actual_preserve=e.preserve_failure;intended_valid=e.input_loader(segment_request).row(Identity('calibration',0,62))['valid']
                            def valid_array(*args,**kwargs):
                                event=dict(context=load_context[0],record=copy.deepcopy(args[0]),entered=now[0],completed=False);load_calls.append(event)
                                try:
                                    if injected[0] and load_context[0]=='second_input_validation':
                                        self.assertEqual(args[0],intended_valid)
                                        witness.successor.append(dict(operation='frame62_valid_array',entered=now[0],record=copy.deepcopy(args[0]),context=load_context[0]))
                                        self.assertLess(now[0],deadline)
                                        raise RuntimeError('plan049 actual frame62 deliberate stop')
                                    value=actual_array(*args,**kwargs);event['completed']=True;return value
                                except BaseException as error:event.update(error_class=type(error).__name__,message=str(error));raise
                                finally:event['exited']=now[0]
                            def preserving(request,output,identity,error,*args,**kwargs):
                                previous=load_context[0];load_context[0]='failure_preservation'
                                seen.append(dict(stage='actual_failure_preservation',identity=identity.record(),failure_stage=kwargs.get('stage'),error_class=type(error).__name__,entered=now[0]))
                                try:return actual_preserve(request,output,identity,error,*args,**kwargs)
                                finally:load_context[0]=previous

                            def raw_row(row,*args,**kwargs):
                                if row['identity']['frame']==62:
                                    witness.successor.append(dict(operation='frame62_raw',entered=now[0]));raise AssertionError('frame62 raw successor')
                                return actual_publish(row,*args,**kwargs)
                            stack.enter_context(patch.object(e,'load_array',valid_array));stack.enter_context(patch.object(e,'preserve_failure',preserving));stack.enter_context(patch.object(p,'publish_segment_row',raw_row))
                            stack.enter_context(patch.dict(sys.modules,{'torch':SimpleNamespace(cuda=SimpleNamespace(synchronize=lambda:None,max_memory_allocated=lambda:0,max_memory_reserved=lambda:0))}))
                            stack.enter_context(patch.object(stages,'_model_runtime',return_value=copy.deepcopy(segment_fixture.observed)))
                            stack.enter_context(patch('vipe_benchmark.backends.build_backend',return_value=SimpleNamespace(segment=predicted)))
                            stack.enter_context(patch.object(p,'loaded_runtime',return_value=segment_fixture.observed['loaded_files']))
                            stack.enter_context(patch.object(stages,'output_identities',return_value=[Identity('calibration',0,50),Identity('calibration',0,62)]))
                            stack.enter_context(patch.object(e,'load_rgb',side_effect=segment_load))
                            stack.enter_context(patch.object(builtins,'print',side_effect=preceding_print))
                            def action():
                                try:stages.segment(segment_request,segment_fixture.root/'next-input-output',segment_fixture.config,clock=segment_clock)
                                except RuntimeError as error:
                                    if str(error)!='plan049 actual frame62 deliberate stop':raise
                                    self.assertEqual(second_entries,[deadline+offset])
                                finally:
                                    seen.append(dict(stage='complete_load_call_ledger',calls=load_calls))
                                    self.control_record('plan049-next-input-load-'+case['when'],dict(calls=load_calls,second_entries=second_entries,native_entries=native_entries,work_deadline=deadline))
                                    self.assertEqual(len(native_entries),1)
                                    self.assertEqual(len(second_entries),0 if expected_late else 1)
                                    seen.append(dict(stage='actual_segment_frame62',target_entries=second_entries,native_entries=native_entries,forbidden_successor='frame62 valid/native/raw'))

                        else:raise AssertionError(name)
                        injected=[False]
                        def advance(label):
                            nonlocal pointer
                            if injected[0]:return
                            pointer=state.cache.snapshot;injected[0]=True
                            remember_predecessor(label)
                            seen.append(dict(stage=label,state='preceding_real_return',observed=now[0]));now[0]=deadline+offset
                        def after(module,attribute,label,predicate=lambda *a,**k:True):
                            original=getattr(module,attribute)
                            def completed(*args,**kwargs):
                                value=original(*args,**kwargs)
                                if predicate(*args,**kwargs):advance(label)
                                return value
                            completed.__name__=attribute
                            stack.enter_context(patch.object(module,attribute,completed))
                        if name=='array_npy':
                            original_open=Path.open
                            def opened(path,*args,**kwargs):
                                value=original_open(path,*args,**kwargs)
                                if path==state.root/'array.npy':advance('array_unbuffered_open_return')
                                return value
                            stack.enter_context(patch.object(Path,'open',opened))
                        elif name=='array_png':
                            original_exists=Path.exists
                            def exists(path):
                                value=original_exists(path)
                                if path==state.root/'array.png':advance('png_destination_stat_return')
                                return value
                            stack.enter_context(patch.object(Path,'exists',exists))
                        elif name=='array_hash':pass  # Actual stream.close return advances below, immediately before hashing.
                        elif name in ('npz_member','npz_finalize','cleanup_next_array'):
                            import zipfile
                            closed=[0];original_close=zipfile._ZipWriteFile.close
                            def member_closed(member):
                                was_closed=member.closed;value=original_close(member)
                                if not was_closed:
                                    closed[0]+=1
                                    if name!='npz_member' and closed[0]==(2 if name=='npz_finalize' else 1):advance('npz_member_'+str(closed[0])+'_close_return')
                                return value
                            stack.enter_context(patch.object(zipfile._ZipWriteFile,'close',member_closed))
                            if name=='npz_member':
                                converted=[0];array_conversion=np.asanyarray
                                def conversion(value,*args,**kwargs):
                                    result=array_conversion(value,*args,**kwargs);converted[0]+=1
                                    if converted[0]==2:advance('second_npz_array_conversion_return_before_member_open')
                                    return result
                                conversion.__name__='asanyarray'
                                stack.enter_context(patch.object(np,'asanyarray',conversion))
                            if name=='cleanup_next_array':
                                primary=RuntimeError('original cleanup primary');primary.s1_evidence={'arrays':{'a':np.arange(4),'b':np.arange(4)}}
                                action=lambda:e.preserve_failure(fixture['request'],state.root,None,primary,clock=state.clock)
                        elif name=='produced_json':
                            after(e,'input_loader','input_manifest_read_and_parse_return')
                        elif name=='produced_read':after(p,'write_exclusive','produced_row_durable_write_return',lambda path,*a,**k:Path(path).name=='produced.json')
                        elif name in ('produced_guard','qualified_guard'):
                            action=lambda:p.publish_segment_row(state.row,fixture['request'],e.input_loader(fixture['request']),state.clock,state.publisher,state.root/'produced.json',state.root/'qualified.json',first=True)
                            if name=='produced_guard':after(p,'read_record','produced_row_read_hash_parse_return',lambda rec,*a,**k:Path(rec['path']).name=='produced.json')
                            else:after(state.publisher,'seal','produced_guard_seal_ack_return')
                        elif name in ('first_guard','reuse_after_read'):
                            if name=='first_guard':action=lambda:p.operation(e.verify_first,p.operation(e.read_json,first['path'],deadline=deadline),fixture['request'],clock=state.clock,deadline=deadline)
                            after(e,'read_json','first_metadata_read_parse_return',lambda path:Path(path).name=='first-result-qualification.json')
                        elif name=='runtime_guard':
                            path=state.root/'runtime.json';write_json(path,fixture['observed_runtime'])
                            action=lambda:p.operation(e.qualify_runtime,p.operation(e.read_json,path,deadline=deadline),fixture['request'],deadline=deadline)
                            after(e,'read_json','runtime_metadata_read_parse_return',lambda path:Path(path).name=='runtime.json')
                        elif name=='accept_after_read':
                            ready=[False];captured=recovery.captured_clock
                            def captured_return(*args,**kwargs):
                                value=captured(*args,**kwargs);ready[0]=True;return value
                            stack.enter_context(patch.object(recovery,'captured_clock',side_effect=captured_return))
                            after(p,'checked_read_json','accepted_request_read_parse_return',lambda path:ready[0] and str(path)==full.clock.request_path)
                        elif name=='complete_after_read':after(p,'checked_read_json','acceptance_metadata_read_parse_return',lambda path:Path(path).name=='acceptance.json')
                    from test_vipe_benchmark_s1_helper_fixtures import named_deadline_witness
                    witness=named_deadline_witness(self,name,state,stack,lambda:now[0],lambda:deadline,lambda:injected[0],lambda:current_stage[0],lambda:phase[0])
                    actual_operation_observer=p.operation;operation_observations=[];descriptor_observations=[];retiring=[False];fd_paths={};write_observations=[]
                    def observe_operation(function,*args,**kwargs):
                        label=getattr(function,'__name__',type(function).__name__)
                        def actual_entry(*values,**named):
                            if not observing[0]:return function(*values,**named)
                            operation_observations.append(dict(operation=label,state='actual_entry',observed=now[0],after_injection=injected[0] if name!='worker_popen' else bool(started)))
                            if now[0]>=deadline:
                                raise AssertionError('forbidden successor entered at/after W: '+label)
                            if hasattr(witness,'primitive'):value=witness.primitive(function,values,named,lambda:function(*values,**named))
                            else:value=function(*values,**named)
                            operation_observations.append(dict(operation=label,state='actual_exit',observed=now[0]))
                            return value
                        actual_entry.__name__=label
                        return actual_operation_observer(actual_entry,*args,**kwargs)
                    actual_open=p.os.open;actual_close=p.os.close;actual_retire=p.retire
                    def observed_open(*args,**kwargs):
                        descriptor=actual_open(*args,**kwargs)
                        path=Path(args[0]);parent=kwargs.get('dir_fd')
                        if not path.is_absolute() and parent in fd_paths:path=Path(fd_paths[parent])/path
                        fd_paths[descriptor]=str(path)
                        descriptor_observations.append(dict(operation='acquire',fd=descriptor,observed=now[0],path=str(path)))
                        return descriptor
                    def observed_close(descriptor):
                        item=dict(operation='retirement' if retiring[0] else 'normal_close',fd=descriptor,observed=now[0],completed=False)
                        descriptor_observations.append(item)
                        try:value=actual_close(descriptor)
                        except BaseException as error:item.update(error_class=type(error).__name__,message=str(error));raise
                        item['completed']=True;return value
                    def observed_retire(function,*args,**kwargs):
                        previous=retiring[0];retiring[0]=True
                        try:return actual_retire(function,*args,**kwargs)
                        finally:retiring[0]=previous
                    observed_close.__name__='close'
                    actual_path_open=Path.open;actual_fdopen=p.os.fdopen;observing=[True]
                    class ObservedStream:
                        def __init__(inner,stream,closefd):inner.stream=stream;inner.closefd=closefd;inner.descriptor=stream.fileno()
                        def __getattr__(inner,attribute):return getattr(inner.stream,attribute)
                        def __iter__(inner):return inner
                        def __next__(inner):return next(inner.stream)
                        def write(inner,data):
                            offset=inner.stream.tell();value=inner.stream.write(data)
                            if observing[0]:write_observations.append(dict(path=fd_paths.get(inner.descriptor),offset=offset,bytes=value,content_hex=bytes(data[:value]).hex(),observed=now[0]))
                            return value
                        def __enter__(inner):return inner
                        def __exit__(inner,kind,error,tb):
                            previous=retiring[0];retiring[0]=error is not None
                            try:inner.close()
                            finally:retiring[0]=previous
                        def close(inner):
                            if inner.stream.closed:return
                            item=dict(operation='retirement' if retiring[0] else 'normal_close',fd=inner.descriptor,observed=now[0],completed=False,stream_close=True,owns_descriptor=inner.closefd)
                            if observing[0]:descriptor_observations.append(item)
                            try:value=inner.stream.close()
                            except BaseException as error:item.update(error_class=type(error).__name__,message=str(error));raise
                            item['completed']=True
                            if name=='array_hash' and not retiring[0] and fd_paths.get(inner.descriptor)==str(state.root/'array.npy'):advance('array_normal_close_return_before_hash')
                            return value
                    def path_open(path,*args,**kwargs):
                        stream=actual_path_open(path,*args,**kwargs)
                        if not observing[0]:return stream
                        fd_paths[stream.fileno()]=str(path)
                        descriptor_observations.append(dict(operation='acquire',fd=stream.fileno(),observed=now[0],path=str(path),source='Path.open'))
                        return ObservedStream(stream,True)
                    def descriptor_stream(fd,*args,**kwargs):
                        stream=actual_fdopen(fd,*args,**kwargs)
                        return ObservedStream(stream,kwargs.get('closefd',True)) if observing[0] else stream
                    stack.enter_context(patch.object(Path,'open',path_open));stack.enter_context(patch.object(p.os,'fdopen',side_effect=descriptor_stream))
                    stack.enter_context(patch.object(p,'operation',side_effect=observe_operation));stack.enter_context(patch.object(e,'operation',side_effect=observe_operation))
                    stack.enter_context(patch.object(p.os,'open',side_effect=observed_open));stack.enter_context(patch.object(p.os,'close',side_effect=observed_close));stack.enter_context(patch.object(p,'retire',side_effect=observed_retire))
                    stack.enter_context(patch.object(p.time,'monotonic',side_effect=lambda:now[0]))
                    initial_files=snapshot_files();primary_observation=None
                    if name=='worker_popen':
                        with self.assertRaises(sup.SupervisionFailure) as worker_failure:action()
                        self.assertEqual(len(started),0 if expected_late else 1);observed=outcome['error']
                        self.assertEqual(witness.successor,[],case)
                        self.assertIsInstance(worker_failure.exception.primary_exception,TimeoutError if expected_late else RuntimeError)
                        primary_observation=dict(error_class=type(worker_failure.exception.primary_exception).__name__,message=str(worker_failure.exception.primary_exception),secondary=list(worker_failure.exception.secondary_failures))
                    elif expected_late:
                        with self.assertRaises(TimeoutError) as caught:action()
                        observed=str(caught.exception);primary_observation=dict(error_class=type(caught.exception).__name__,message=str(caught.exception),secondary=list(getattr(caught.exception,'__notes__',())))
                        if name!='ack_receipt':self.assertIs(state.cache.snapshot,pointer)
                    else:action();observed='real operation completed before W'
                    if name!='worker_popen':self.assertTrue(injected[0],name)
                    if name=='array_npy':
                        observing[0]=False
                        # Same typed callback also exposes trace-return W edges
                        # and the acquired-new/failed-old-close ownership edge.
                        probe_now=[deadline-1];entries=[]
                        def trace_return(phase,status):
                            if status=='start':probe_now[0]=deadline+offset
                        with patch.object(p.time,'monotonic',side_effect=lambda:probe_now[0]),patch.object(p,'trace_event',side_effect=trace_return):
                            if expected_late:
                                with self.assertRaises(TimeoutError):p.operation(lambda:entries.append('target'),deadline=deadline)
                            else:p.operation(lambda:entries.append('target'),deadline=deadline)
                        self.assertEqual(entries,[] if expected_late else ['target'])
                        trace_primary=RuntimeError('plan049 trace primary')
                        with patch.object(p.time,'monotonic',return_value=deadline-1),patch.object(p,'trace_event',side_effect=trace_primary):
                            with self.assertRaises(RuntimeError) as trace_error:p.operation(lambda:entries.append('forbidden'),deadline=deadline)
                        self.assertIs(trace_error.exception,trace_primary);self.assertNotIn('forbidden',entries)
                        acquired=[];closed=[];close_primary=OSError('plan049 old descriptor close failed')
                        real_open=actual_open;real_close=actual_close
                        def acquire_fd(*args,**kwargs):
                            fd=real_open(*args,**kwargs);acquired.append(fd);return fd
                        def close_fd(fd):
                            closed.append(fd);result=real_close(fd)
                            if len(closed)==1:raise close_primary
                            return result
                        with patch.object(p.time,'monotonic',return_value=deadline-1),patch.object(p.os,'open',side_effect=acquire_fd),patch.object(p.os,'close',side_effect=close_fd):
                            with self.assertRaises(OSError) as close_error:p.open_parent(state.root/'ownership-edge')
                        self.assertIs(close_error.exception,close_primary)
                        self.assertEqual(len(acquired),2);self.assertEqual(closed,acquired)
                        self.assertEqual(close_primary.s1_uncertain_descriptors,(acquired[0],))
                        for descriptor in acquired:
                            with self.assertRaises(OSError):os.fstat(descriptor)
                        seen.append(dict(stage='trace_and_open_parent_edges',trace_target_entries=entries,acquired=acquired,close_order=closed,uncertain=list(close_primary.s1_uncertain_descriptors),same_primary=True))
                    observing[0]=False
                    self.assertEqual(len(injection_observations),1,name)
                    self.assertEqual(injection_observations[0]['returned_at'],deadline+offset)
                    self.assertLess(injection_observations[0]['entered_before'],deadline)
                    forbidden=[row for row in operation_observations if row['state']=='actual_entry' and row['observed']>=deadline]
                    self.assertEqual(forbidden,[],name)
                    self.assertTrue(witness.spec['target']);self.assertTrue(witness.spec['successor'])
                    if expected_late:
                        self.assertIn(name,before_controls)
                        self.assertEqual(witness.target,[],dict(case=case,target=witness.spec['target']))
                        self.assertEqual(witness.successor,[],dict(case=case,successor=witness.spec['successor']))
                        self.assertEqual(witness.spec,before_controls[name]['spec'])
                        self.assertEqual(snapshot_files(),injection_files[0],dict(case=case,reason='exact partial bytes unchanged after predecessor'))
                        if name!='worker_popen':self.assertEqual(primary_observation['error_class'],'TimeoutError')
                    else:
                        self.assertTrue(witness.target,dict(case=case,spec=witness.spec,events=seen))
                        self.assertTrue(all(row['entered']<deadline and row.get('exited',deadline)<deadline for row in witness.target))
                        if name!='worker_popen':self.assertTrue(all(row['completed'] for row in witness.target))
                        if name!='worker_popen':self.assertTrue(witness.successor,dict(case=case,spec=witness.spec))
                        if name=='next_input':self.assertEqual([row['operation'] for row in witness.successor],['frame62_valid_array'])
                        before_controls[name]=dict(spec=witness.spec,target=witness.target,successor=witness.successor,predecessor=injection_observations[0])
                    owned_descriptors={}
                    for item in descriptor_observations:
                        if item['operation']=='acquire':
                            self.assertNotIn(item['fd'],owned_descriptors,dict(case=case,descriptor=item))
                            owned_descriptors[item['fd']]=item
                        elif item.get('completed') and (not item.get('stream_close') or item.get('owns_descriptor')):
                            owned_descriptors.pop(item['fd'],None)
                    self.assertEqual(owned_descriptors,{},dict(case=case,reason='all acquired FDs/streams retired'))
                    self.assertFalse(any(item.get('error_class') for item in descriptor_observations),case)
                    final_files=snapshot_files()
                    for path,content in final_files.items():
                        writes=[row for row in write_observations if row['path']==path]
                        if not writes:continue
                        expected=bytearray(initial_files.get(path,b''))
                        for write in writes:
                            chunk=bytes.fromhex(write['content_hex']);self.assertEqual(len(chunk),write['bytes'])
                            end=write['offset']+len(chunk)
                            if end>len(expected):expected.extend(b'\0'*(end-len(expected)))
                            expected[write['offset']:end]=chunk
                        self.assertEqual(content,bytes(expected),dict(case=case,path=path,reason='exact accepted write bytes'))
                        self.assertEqual(__import__('hashlib').sha256(content).hexdigest(),__import__('hashlib').sha256(expected).hexdigest())
                    partial=[dict(path=str(path),bytes=path.stat().st_size,sha256=__import__('hashlib').sha256(path.read_bytes()).hexdigest(),content_hex=path.read_bytes().hex()) for path in state.root.rglob('*') if path.is_file()]
                    evidence.append(dict(case,source=source,events=seen,named_target=witness.target,named_successor=witness.successor,named_spec=witness.spec,real_predecessor=injection_observations,write_observations=write_observations,primary=primary_observation,retirement_complete=not owned_descriptors,deadline=deadline,work_deadline=deadline,total_deadline=segment_clock.total_deadline if name=='next_input' else state.clock.total_deadline,exact_injected_time=deadline+offset,observed=observed,actual_operations=operation_observations,descriptor_observations=descriptor_observations,forbidden_successor_entries=[v for v in operation_observations if v['state']=='actual_entry' and v['observed']>=deadline],reference=state.cache.reference(),partial_files=partial,fixture=fixture['request_record']))
        self.control_record('plan047-deadline-steps',evidence)

    def test_progress_plan048_pure_memo(self):
        import contextlib,copy,hashlib,io,json
        import numpy as np
        from vipe_benchmark import s1_evidence as e,s1_progress as p
        from vipe_benchmark.files import file_record,write_json
        from test_vipe_benchmark_s1_helper_fixtures import progress_fixture,plan047_state
        records=[]
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);fixture=progress_fixture(root/'fixture');row=fixture['rows'][0];request=fixture['request']
            baseline=e.qualify_row(row,request,first=True)
            for case in SUBTEST_CASES[f'{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}']:
                with self.subTest(**case),contextlib.ExitStack() as stack:
                    kind=case['kind'];memo=e.PureMemo();events=[];counts={'decode':0,'preprocess':0};deadline=self.time.monotonic()+60
                    actual_load=e.np.load;actual_processed=e.processed_rgb
                    def load(*args,**kwargs):
                        if isinstance(args[0],io.BytesIO) and args[0].getbuffer()[:2]==b'PK':counts['decode']+=1;events.append('archive_open')
                        return actual_load(*args,**kwargs)
                    def processed(rgb):counts['preprocess']+=1;events.append('processed_rgb');return actual_processed(rgb)
                    stack.enter_context(patch.object(e.np,'load',side_effect=load));stack.enter_context(patch.object(e,'processed_rgb',side_effect=processed))
                    self.assertEqual(e.qualify_row(row,request,first=True,memo=memo,deadline=deadline),baseline)
                    self.assertIsNotNone(memo.entry);retained=memo.retained_bytes;control=dict(counts)
                    if kind=='snapshot_member_once':
                        raw=p.verified_bytes(row['diagnostics']);member_counts={}
                        with actual_load(io.BytesIO(raw),allow_pickle=False) as archive:
                            class Counted:
                                files=archive.files
                                def __getitem__(inner,key):member_counts[key]=member_counts.get(key,0)+1;return archive[key]
                            snapshot=e.BoundedArrays(Counted())
                            for key in archive.files:
                                first=snapshot[key];self.assertIs(snapshot[key],first);self.assertFalse(first.flags.writeable);self.assertFalse(first.dtype.hasobject)
                            self.assertEqual(member_counts,{key:1 for key in archive.files});snapshot.clear();self.assertEqual(snapshot.bytes,0)
                        events.append(dict(member_counts=member_counts))
                    elif kind=='uncached_valid_equivalence':
                        fresh=e.qualify_row(row,request,first=True,deadline=deadline)
                        cached=e.qualify_row(row,request,first=True,memo=memo,deadline=deadline)
                        self.assertEqual(cached,fresh);self.assertEqual(cached,baseline);self.assertEqual(memo.hits,1)
                        self.assertEqual(counts,{'decode':2,'preprocess':2})
                    elif kind in ('uncached_invalid_equivalence','failure_cleanup'):
                        invalid=copy.deepcopy(row)
                        if kind=='uncached_invalid_equivalence':
                            with actual_load(io.BytesIO(p.verified_bytes(row['diagnostics'])),allow_pickle=False) as archive:
                                invalid_arrays={key:archive[key] for key in archive.files}
                            invalid_arrays['detector_raw_token_logits']=invalid_arrays['detector_raw_token_logits'].copy()
                            invalid_arrays['detector_raw_token_logits'][0,0]+=1
                            invalid['diagnostics']=e.numeric_file(root/(kind+'.npz'),invalid_arrays)
                            events.append(dict(numerical_fault='logit/probability disagreement',record=invalid['diagnostics']))
                        else:invalid['metadata']['detections'][0]['class_assignment']['derived_class']='invalid'
                        failures=[]
                        for active in (None,memo):
                            with self.assertRaises(ValueError) as caught:e.qualify_row(invalid,request,memo=active,deadline=deadline)
                            failures.append((type(caught.exception).__name__,str(caught.exception)))
                        self.assertEqual(failures[0],failures[1]);self.assertIsNone(memo.entry);self.assertEqual(memo.retained_bytes,0)
                        if kind=='failure_cleanup':
                            self.assertEqual(e.qualify_row(row,request,memo=memo,deadline=deadline),baseline)
                            self.assertEqual(memo.misses,2);memo.clear();self.assertIsNone(memo.entry)
                        events.append(dict(failures=failures))
                    elif kind in ('same_size_restored_mtime','inode_replacement','path_replacement'):
                        path=Path(row['diagnostics']['path']);raw=path.read_bytes();old=path.stat();replacement=path.with_name('replacement.npz')
                        try:
                            if kind=='same_size_restored_mtime':
                                changed=bytearray(raw);changed[len(changed)//2]^=1;path.write_bytes(changed);os.utime(path,ns=(old.st_atime_ns,old.st_mtime_ns))
                                self.assertEqual(path.stat().st_size,old.st_size);self.assertEqual(path.stat().st_mtime_ns,old.st_mtime_ns)
                                with self.assertRaises(ValueError):e.qualify_row(row,request,memo=memo,deadline=deadline)
                                self.assertIsNone(memo.entry)
                            elif kind=='inode_replacement':
                                replacement.write_bytes(raw);os.replace(replacement,path);self.assertNotEqual(path.stat().st_ino,old.st_ino)
                                actual=p.read_bytes
                                def read(path_value,limit):events.append(dict(fresh_read=str(path_value)));return actual(path_value,limit)
                                with patch.object(p,'read_bytes',side_effect=read):self.assertEqual(e.qualify_row(row,request,memo=memo,deadline=deadline),baseline)
                                self.assertTrue(any(isinstance(v,dict) and v.get('fresh_read')==str(path) for v in events));self.assertEqual(memo.hits,1)
                            else:
                                replacement.write_bytes(raw);actual=p.os.fstat;seen=[0]
                                def fstat(fd):
                                    value=actual(fd)
                                    if value.st_ino==old.st_ino:
                                        seen[0]+=1
                                        if seen[0]==2:os.replace(replacement,path);events.append('named_path_replaced_after_read')
                                    return value
                                with patch.object(p.os,'fstat',side_effect=fstat),self.assertRaisesRegex(ValueError,'descriptor replacement'):
                                    e.qualify_row(row,request,memo=memo,deadline=deadline)
                                self.assertIn('named_path_replaced_after_read',events);self.assertIsNone(memo.entry)
                            events.append(dict(before_inode=old.st_ino,after_inode=path.stat().st_ino,original_hash=hashlib.sha256(raw).hexdigest(),observed_hash=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=len(raw)))
                        finally:path.write_bytes(raw);os.utime(path,ns=(old.st_atime_ns,old.st_mtime_ns))
                    elif kind in ('request_changed','identity_changed'):
                        changed=copy.deepcopy(row);req=copy.deepcopy(request)
                        if kind=='request_changed':req['job_id']='other'
                        else:changed['identity']['camera']=99
                        with self.assertRaises(ValueError):e.qualify_row(changed,req,memo=memo,deadline=deadline)
                        self.assertIsNone(memo.entry);events.append('real_row_request_or_identity_rejected')
                    elif kind in ('context_changed','source_changed'):
                        with plan047_state(fixture,root/kind) as state:
                            state.publisher.close();context_path=Path(state.reference['path']);context_raw=context_path.read_bytes();reference=state.reference
                            if kind=='context_changed':context_path.write_bytes(context_raw+b' ')
                            else:
                                doc=p.decode(context_raw,p.SMALL_BYTES);source=root/'guard-copy.py';source.write_bytes(Path(doc['sources']['guard']['path']).read_bytes());doc['sources']['guard']=file_record(source)
                                raw=p.encode(doc,p.SMALL_BYTES);context_path.write_bytes(raw);reference=p.record(context_path,raw)
                                control_publisher=p.Publisher(reference,'worker',1,clock=state.clock,request=request);control_publisher.close()
                                source.write_bytes(source.read_bytes()+b'\n')
                            with self.assertRaisesRegex(ValueError,'metadata changed|source changed'):p.Publisher(reference,'worker',1,clock=state.clock,request=request)
                            self.assertEqual(memo.retained_bytes,retained);events.append('fresh_publisher_authority_rejected_before_memo')
                            # The same previously warmed numerical memo is passed
                            # through the production qualification/context path.
                            before_counts=dict(counts);lookups=memo.lookup;lookup_calls=[]
                            def lookup(key):lookup_calls.append(key);return lookups(key)
                            with patch.object(memo,'lookup',side_effect=lookup),self.assertRaisesRegex(ValueError,'metadata changed|source changed'):
                                e.qualify_row(row,request,first=True,memo=memo,progress_context=reference,deadline=deadline)
                            self.assertEqual(lookup_calls,[]);self.assertEqual(counts,before_counts)
                            self.assertIsNone(memo.entry);self.assertEqual(memo.retained_bytes,0)
                            events.append(dict(pipeline='qualify_row with same warm memo and current progress_context',authority_rejected=True,numerical_successor_entries=0))
                    elif kind.startswith('lookup_'):
                        now=[self.time.monotonic()];deadline=now[0]+10;offset={'lookup_before_w':-.001,'lookup_equal_w':0.,'lookup_after_w':.001}[kind]
                        lookup=memo.lookup;forbidden=[];member=e.BoundedArrays.__getitem__
                        def completed_lookup(key):
                            value=lookup(key);events.append('real_lookup_return');now[0]=deadline+offset;return value
                        def getitem(inner,key):
                            if now[0]>=deadline:forbidden.append(key);raise AssertionError('member access after lookup reached W')
                            events.append('member:'+key);return member(inner,key)
                        with patch.object(memo,'lookup',side_effect=completed_lookup),patch.object(e.BoundedArrays,'__getitem__',getitem),patch.object(p.time,'monotonic',side_effect=lambda:now[0]):
                            if kind=='lookup_before_w':self.assertEqual(e.qualify_row(row,request,memo=memo,deadline=deadline),baseline)
                            else:
                                with self.assertRaises(TimeoutError) as caught:e.qualify_row(row,request,memo=memo,deadline=deadline)
                                self.assertEqual(str(caught.exception),'progress original work deadline');self.assertIsNone(memo.entry)
                        self.assertIn('real_lookup_return',events);self.assertEqual(forbidden,[])
                        self.assertEqual(any(isinstance(v,str) and v.startswith('member:') for v in events),kind=='lookup_before_w')
                    elif kind=='retention_cap':
                        self.assertEqual(e.PURE_MEMO_BYTES,64*1024*1024)
                        self.assertLessEqual(memo.retained_bytes,e.PURE_MEMO_BYTES)
                        payload=b'x'*e.PURE_MEMO_BYTES
                        self.assertTrue(memo.retain((payload,),{},None));self.assertEqual(memo.retained_bytes,e.PURE_MEMO_BYTES)
                        self.assertFalse(memo.retain((payload,b'y'),{},None));self.assertIsNone(memo.entry);self.assertEqual(memo.retained_bytes,0)
                        del payload
                        self.assertEqual(e.qualify_row(row,request,memo=memo,deadline=deadline),baseline)
                        events.append('exact_cap_then_uncached_guard')
                        oversized=copy.deepcopy(row)
                        with actual_load(io.BytesIO(p.verified_bytes(row['diagnostics'])),allow_pickle=False) as archive:
                            oversized_arrays={key:archive[key] for key in archive.files}
                        oversized_arrays['retention_accounting_padding']=np.zeros(e.PURE_MEMO_BYTES,np.uint8)
                        oversized['diagnostics']=e.numeric_file(root/'oversized-real-pair.npz',oversized_arrays)
                        del oversized_arrays
                        for repetition in range(2):
                            before_decode=counts['decode']
                            self.assertEqual(e.qualify_row(oversized,request,memo=memo,deadline=deadline),baseline)
                            self.assertEqual(counts['decode'],before_decode+1)
                            self.assertIsNone(memo.entry);self.assertEqual(memo.retained_bytes,0)
                        events.append(dict(real_oversized_record=oversized['diagnostics'],uncached_repetitions=2))
                    elif kind=='eviction':
                        old=memo.entry[0];new=(b'new-pair',)
                        self.assertIsNone(memo.lookup(new));self.assertIsNone(memo.entry);self.assertEqual(memo.evictions,1)
                        self.assertTrue(memo.retain(new,{},None));self.assertEqual(memo.entry[0],new);self.assertNotEqual(memo.entry[0],old)
                        self.assertIsNone(memo.lookup(old));self.assertEqual(memo.evictions,2);self.assertIsNone(memo.entry)
                        events.append('one_pair_evicted_exact_key_and_buffers')
                        self.assertEqual(e.qualify_row(row,request,memo=memo,deadline=deadline),baseline)
                        first_key=memo.entry[0];old_evictions=memo.evictions
                        second=copy.deepcopy(row)
                        with actual_load(io.BytesIO(p.verified_bytes(row['diagnostics'])),allow_pickle=False) as archive:
                            second_arrays={key:archive[key] for key in archive.files}
                        second_arrays['second_pair_numeric_marker']=np.array([1],np.uint8)
                        second['diagnostics']=e.numeric_file(root/'second-real-pair.npz',second_arrays)
                        self.assertEqual(e.qualify_row(second,request,memo=memo,deadline=deadline),baseline)
                        self.assertNotEqual(memo.entry[0],first_key);self.assertEqual(memo.evictions,old_evictions+1)
                        self.assertEqual(e.qualify_row(row,request,memo=memo,deadline=deadline),baseline)
                        self.assertEqual(memo.entry[0],first_key);self.assertEqual(memo.evictions,old_evictions+2)
                        events.append(dict(real_first=row['diagnostics'],real_second=second['diagnostics']))
                    else:raise AssertionError(kind)
                    records.append(dict(case,source='qualify_row/numerical_snapshot/PureMemo/BoundedArrays',positive_control=control,counts=counts,events=events,work_deadline=deadline,retained_bytes=memo.retained_bytes,hits=memo.hits,misses=memo.misses,fixture=fixture['request_record'],archive=row['diagnostics']))
                    memo.clear();self.assertIsNone(memo.entry);self.assertEqual(memo.retained_bytes,0)
        self.control_record('plan048-pure-memo',records)

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
        # Exercise the actual acquisition/readiness prefix with pure existing
        # lifecycle seams; submit rejection stays in the real Session method.
        import ast,inspect,textwrap
        from unittest.mock import Mock
        from vipe_benchmark import supervisor as sup
        monitored=ast.parse(textwrap.dedent(inspect.getsource(sup.monitored_call))).body[0]
        prefix=next(node for node in monitored.body if isinstance(node,ast.Try)).body[:4]
        readiness=[]
        for ready in ({},{'work':{}},{'sample':{}},{'work':{},'sample':{}}):
            events=[]
            selected=types.SimpleNamespace(ready=ready,resume=Mock(side_effect=lambda:events.append('resume')),await_ready=Mock(side_effect=lambda:events.append('await_ready')),set_worker=Mock(side_effect=lambda worker:events.append('set_worker')))
            life=types.SimpleNamespace(acquire=Mock(return_value=selected))
            exec(compile(ast.Module(body=prefix,type_ignores=[]),'<actual-monitored-readiness>','exec'),dict(lifecycle=life,worker=None))
            self.assertEqual(selected.await_ready.call_count,0 if ready.keys()=={'work','sample'} else 1)
            self.assertEqual(events,(['resume'] if ready else [])+([] if ready.keys()=={'work','sample'} else ['await_ready'])+['set_worker'])
            readiness.append(dict(ready=list(ready),events=events))
        current.sequences['work']=0;current.requests['work']=None
        for fault in ('poisoned','cancelled','deadline'):
            current.poisoned=fault=='poisoned';current.owner.cancelled=fault=='cancelled'
            with self.assertRaisesRegex(TimeoutError if fault=='deadline' else ValueError,'S1 work dispatch deadline' if fault=='deadline' else 'helper session unavailable'):
                current.submit('work',self.operation,self.time.monotonic() if fault=='deadline' else self.time.monotonic()+.1)
        self.control_record('plan049-ready-reuse',readiness)
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
