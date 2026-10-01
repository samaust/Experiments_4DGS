"""The shared context supervisor must release its process group on failure."""

import os
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from basketball_vipe_depth_context import _stop_worker


class DepthContextSupervisorTests(unittest.TestCase):
    def test_stop_worker_reaps_process_group(self):
        process = subprocess.Popen([sys.executable, '-c',
            'import time; time.sleep(30)'], start_new_session=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            _stop_worker(process)
            self.assertIsNotNone(process.returncode)
            with self.assertRaises(ProcessLookupError):
                os.killpg(process.pid, 0)
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()


if __name__ == '__main__':
    unittest.main()
