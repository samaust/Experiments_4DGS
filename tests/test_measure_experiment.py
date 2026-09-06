"""Synthetic sampler failures must stop the measured command, not lose evidence."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class MeasurementTests(unittest.TestCase):
    def test_failed_sampler_prevents_workload_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sampler = root/'nvidia-smi'
            sampler.write_text('#!'+sys.executable+'\nprint("synthetic sampler failure")\nraise SystemExit(3)\n')
            sampler.chmod(0o755)
            marker = root/'workload-started'
            command = [sys.executable, 'scripts/measure-experiment.py', '--output', str(root/'output'),
                       '--cwd', str(root), '--', sys.executable, '-c',
                       'from pathlib import Path; Path('+repr(str(marker))+').touch()']
            env = dict(os.environ, PATH=str(root)+os.pathsep+os.environ['PATH'])
            result = subprocess.run(command, env=env, capture_output=True, text=True,
                                    cwd=Path(__file__).resolve().parents[1], timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('GPU sampler stopped', result.stderr)
            self.assertIn('synthetic sampler failure', result.stderr)
            self.assertFalse(marker.exists())
