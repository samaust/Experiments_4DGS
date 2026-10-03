"""Harmless orchestration fixtures; no installed runtime or model execution."""
import argparse
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys

spec = importlib.util.spec_from_file_location('moge_cpu_producer', Path(__file__).with_name('producer.py'))
producer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(producer)
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))


class Orchestration(unittest.TestCase):
    def run_fixture(self, returncode, artifact_bytes=2**20, seconds=1, timed_out=False):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            out = base / 'capture'
            args = argparse.Namespace(root=str(base), candidate='D5', setup=str(base / 'setup.json'),
                setup_request=str(base / 'request.json'), setup_dispatch=str(base / 'dispatch.json'),
                output=str(out), seconds=seconds, artifact_bytes=artifact_bytes)
            setup = dict(runtime_environment=dict(path='runtime'))
            runtime = dict(python_executable='/fixture/python', inventory=dict(path=str(base / 'runtime/inventory.json')))
            def read(path):
                if str(path) == args.setup:
                    return setup
                if str(path) == 'runtime':
                    return runtime
                return json.loads(Path(path).read_text())
            def record(path):
                return dict(path=str(path), sha256='fixture', bytes=1)
            class Process:
                pid = 123456789
                def __init__(self):
                    self.returncode = returncode
                def poll(self):
                    return None if timed_out and self.returncode is None else self.returncode
                def wait(self):
                    return self.returncode
            process = Process()
            def launch(*unused_args, **unused_kwargs):
                if artifact_bytes == 65536:
                    (out / 'oversized-fixture.bin').write_bytes(b'x' * 70000)
                return process
            def kill(process):
                process.returncode = -9
            with patch.object(producer, 'helpers', return_value=(record, read, lambda x: x)), \
                 patch.object(producer.subprocess, 'Popen', side_effect=launch), \
                 patch.object(producer, 'terminate', side_effect=kill), \
                 patch.dict(producer.os.environ, {}, clear=True), \
                 patch('vipe_benchmark.moge_source_build.cache_path', return_value=base / 'runtime/cache.json'), \
                 patch.object(producer.time, 'monotonic', side_effect=[0, 2, 3, 4, 5, 6]):
                with self.assertRaises((ValueError, TimeoutError)):
                    producer.capture(args)
            receipt = json.loads((out / 'capture.json').read_text())
            self.assertEqual(receipt['status'], 'failed')
            self.assertFalse(receipt['cpu_charge_applied'])
            self.assertFalse(receipt['ledger_modified'])
            self.assertEqual(receipt['download_bytes'], 0)
            return receipt

    def test_child_failure_retains_terminal_receipt(self):
        self.assertIn('child failed', self.run_fixture(3, seconds=10)['error'])

    def test_timeout_terminates_and_preserves_failed_receipt(self):
        receipt = self.run_fixture(None, timed_out=True)
        self.assertIn('wall allocation', receipt['error'])
        self.assertEqual(receipt['returncode'], -9)

    def test_fast_child_still_checks_final_artifact_size(self):
        self.assertIn('artifact allocation', self.run_fixture(0, artifact_bytes=65536, seconds=10)['error'])

    def test_zero_exit_without_native_result_cannot_pass(self):
        self.assertIn('FileNotFoundError', self.run_fixture(0, seconds=10)['error'])


if __name__ == '__main__':
    unittest.main()
