import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('training_supervisor',
    Path(__file__).resolve().parents[1]/'scripts/training_supervisor.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SupervisorTests(unittest.TestCase):
    def run_worker(self, source):
        with tempfile.TemporaryFile(mode='w+') as log:
            result = module.supervise([sys.executable, '-c', source], cwd='.', log=log,
                                     seconds=1.5, checkpoint_margin=.7, kill_margin=.3)
            log.seek(0)
            return result, log.read()

    def test_clean_worker(self):
        result, output = self.run_worker('import os; print(os.environ["TRAINING_STOP_MONOTONIC"])')
        self.assertEqual(result['exit_code'], 0)
        self.assertGreater(float(output.strip()), 0)
        self.assertFalse(result['forced_kill'])

    def test_cooperative_checkpoint_signal(self):
        result, output = self.run_worker(
            'import signal,time,sys; '
            'signal.signal(signal.SIGTERM, lambda *_: (print("checkpoint",flush=True),sys.exit(0))); '
            'time.sleep(10)')
        self.assertEqual(result['exit_code'], 0)
        self.assertTrue(result['stop_requested'])
        self.assertEqual(output.strip(), 'checkpoint')

    def test_uncooperative_worker_is_killed(self):
        result, _ = self.run_worker(
            'import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(10)')
        self.assertEqual(result['exit_code'], -9)
        self.assertTrue(result['forced_kill'])
        self.assertLess(result['wall_seconds'], 1.5)

    def test_failure_is_returned(self):
        result, _ = self.run_worker('raise SystemExit(7)')
        self.assertEqual(result['exit_code'], 7)
