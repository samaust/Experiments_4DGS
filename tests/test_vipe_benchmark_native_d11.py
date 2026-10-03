"""D11 processes a folder in one native call and binds frames to predictions."""

from pathlib import Path
import sys
import tempfile
import subprocess
import time
import os
import signal
import json
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.files import file_record
from vipe_benchmark.depth_source_integrity import source_manifest
from vipe_benchmark.marigold_relative import MarigoldLogStage2Adapter, SOURCE_REVISION
from vipe_benchmark.native_d11 import CachedD11Runtime, run_folder


class NativeD11Tests(unittest.TestCase):
    def test_one_native_call_and_exact_order(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            native = root / 'source/scripts/infer.py'
            native.parent.mkdir(parents=True)
            native.write_text('# pinned fixture\n')
            config = root / 'source/configs/depth.yaml'
            config.parent.mkdir()
            config.write_text('seed: 2025\n')
            archive = root / 'source.tar.gz'
            archive.write_bytes(b'fixture source')
            assets = []
            for index in range(12):
                path = root / 'assets/checkpoints' / (
                    'Marigold-V2/depth/Log-stage2/trainables.safetensors' if index == 0
                    else f'Qwen-Image-Edit-2509/transformer/file{index}.bin')
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(bytes([index]))
                assets.append(dict(record=file_record(path)))
            setup = dict(schema='plan069-depth-setup-result/v1', status='complete',
                candidate='D11', source_revision=SOURCE_REVISION,
                source_dir=str(root / 'source'), source_archive=file_record(archive),
                native_source=file_record(native), assets=assets,
                source_manifest=source_manifest(root / 'source'))
            interpreter = root / 'python'
            interpreter.write_text('# fixture\n')
            setup['runtime'] = dict(status='complete', python_executable=str(interpreter),
                                    native_qualification={'status': 'passed'})
            rgb_a = np.full((540, 960, 3), 11, np.uint8)
            rgb_b = np.full((540, 960, 3), 22, np.uint8)
            calls = []

            def run(command, **kwargs):
                calls.append((command, kwargs))
                self.assertNotIn('--width', command)
                self.assertEqual(kwargs['env']['HF_HUB_OFFLINE'], '1')
                self.assertEqual(kwargs['env']['PYTHONDONTWRITEBYTECODE'], '1')
                self.assertEqual(kwargs['env']['PATH'].split(':')[0], str(interpreter.parent))
                target = root / 'out/native/images/predictions_npy'
                target.mkdir(parents=True)
                np.save(target / 'a.npy', np.full((540, 960), .1, np.float32))
                np.save(target / 'b.npy', np.full((540, 960), .2, np.float32))

            with patch('vipe_benchmark.depth_native_packages.qualify', side_effect=ValueError('dependency qualification failed')):
                with self.assertRaisesRegex(ValueError, 'dependency qualification failed'):
                    run_folder(setup, [('a', rgb_a)], root / 'out',
                               interpreter=interpreter, timeout_seconds=100, runner=run)
                self.assertFalse((root / 'out').exists())
                self.assertEqual(calls, [])
            with patch('vipe_benchmark.depth_native_packages.qualify', return_value={'status': 'passed'}):
                config.write_text('seed: 999\n')
                with self.assertRaisesRegex(ValueError, 'source tree changed'):
                    run_folder(setup, [('a', rgb_a)], root / 'out',
                               interpreter=interpreter, timeout_seconds=100, runner=run)
                self.assertEqual(calls, [])
                config.write_text('seed: 2025\n')
                rows = run_folder(setup, [('a', rgb_a), ('b', rgb_b)], root / 'out',
                                  interpreter=interpreter, timeout_seconds=100, runner=run)
            self.assertEqual(len(calls), 1)
            adapter = MarigoldLogStage2Adapter(CachedD11Runtime(rows))
            K = np.eye(3)
            valid = np.ones((540, 960), np.bool_)
            self.assertAlmostEqual(float(adapter.predict(rgb_a, K, valid).values[0, 0]), .1)
            with self.assertRaisesRegex(ValueError, 'prediction/input mismatch'):
                adapter.predict(rgb_a, K, valid)
            self.assertAlmostEqual(float(adapter.predict(rgb_b, K, valid).values[0, 0]), .2)
            # A CPU native fixture launches the same child-process topology as upstream.
            marker = root / 'escaped-child'
            child = 'import time; from pathlib import Path; time.sleep(1.5); Path(' + repr(str(marker)) + ').touch()'
            native.write_text('import subprocess, sys, time\nsubprocess.Popen([sys.executable, "-c", ' + repr(child) + '])\ntime.sleep(60)\n')
            setup['native_source'] = file_record(native)
            setup['source_manifest'] = source_manifest(root / 'source')
            setup['runtime']['python_executable'] = sys.executable
            with patch('vipe_benchmark.depth_native_packages.qualify', return_value={'status': 'passed'}):
                with self.assertRaises(subprocess.TimeoutExpired):
                    run_folder(setup, [('a', rgb_a)], root / 'timed-out',
                               interpreter=sys.executable, timeout_seconds=.5)
            time.sleep(1.7)
            self.assertFalse(marker.exists(), 'native child survived the deadline')
            # Exercise actual-shaped worker ownership using CPU-only native fixtures.
            ownership = root / 'ownership.json'
            native.write_text('import os, json, time\nfrom pathlib import Path\nPath(' +
                              repr(str(ownership)) + ').write_text(json.dumps({"pgid": os.getpgrp()}))\ntime.sleep(60)\n')
            setup.update(record_kind='actual', native_source=file_record(native),
                         source_manifest=source_manifest(root / 'source'))
            setup_path = root / 'cpu-topology-fixture.json'
            setup_path.write_text(json.dumps(setup))
            code = ('import json, numpy as np; from pathlib import Path; '
                    'from vipe_benchmark import native_d11; '
                    'native_d11.verify_runtime=lambda *args: {"status": "passed"}; '
                    'native_d11.run_folder(json.loads(Path(' + repr(str(setup_path)) +
                    ').read_text()), [("a", np.zeros((540,960,3), np.uint8))], ' +
                    repr(str(root / 'owned-out')) + ', interpreter=' + repr(sys.executable) +
                    ', timeout_seconds=.5)')
            env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / 'scripts'))
            with subprocess.Popen([sys.executable, '-c', code], env=env,
                                  start_new_session=True, stdout=subprocess.DEVNULL,
                                  stderr=subprocess.DEVNULL) as worker:
                try:
                    self.assertEqual(worker.wait(timeout=5), -signal.SIGKILL)
                    self.assertEqual(json.loads(ownership.read_text())['pgid'], worker.pid)
                finally:
                    if worker.poll() is None:
                        os.killpg(worker.pid, signal.SIGKILL)
                        worker.wait()



if __name__ == '__main__':
    unittest.main()
