"""Bounded CPU process seam; fixtures cannot issue native authority."""
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest

from vipe_benchmark.final_render_qualification_control import ControlFailure, run_fixture_control


class QualificationControlTests(unittest.TestCase):
    def test_hung_operation_is_terminated_and_partial_evidence_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            command = [sys.executable, '-c', "import pathlib,time; pathlib.Path('partial').write_text('kept'); time.sleep(30)"]
            started = time.monotonic()
            with self.assertRaises(ControlFailure) as caught:
                run_fixture_control(command, root, seconds=.4)
            self.assertLess(time.monotonic()-started, 4)
            self.assertEqual((root/'partial').read_text(), 'kept')
            evidence = json.loads((root/'control-failure.json').read_text())
            self.assertTrue(evidence['cleanup_confirmed'])
            self.assertIn('deadline', str(caught.exception))
            self.assertFalse(evidence['execution_authorized'])

    def test_fixture_receipt_cannot_claim_native_authority(self):
        with tempfile.TemporaryDirectory() as directory:
            command = [sys.executable, '-c', "import json; json.dump({'execution_authorized':True,'record_kind':'actual'},open('response.json','w'))"]
            value = run_fixture_control(command, Path(directory), seconds=2)
            self.assertEqual(value['record_kind'], 'fixture')
            self.assertFalse(value['execution_authorized'])

    def test_descendant_outliving_successful_parent_is_cleaned(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            command = [sys.executable, '-c', "import subprocess,sys,json; p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']); json.dump({'child':p.pid},open('response.json','w'))"]
            started = time.monotonic()
            value = run_fixture_control(command, root, seconds=2)
            self.assertLess(time.monotonic()-started, 4)
            stat = Path('/proc',str(value['child']),'stat')
            if stat.exists():
                self.assertEqual(stat.read_text().rsplit(')',1)[1].split()[0], 'Z')

    def test_oversized_response_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            command = [sys.executable, '-c', "open('response.json','w').write(' '*1048577)"]
            with self.assertRaisesRegex(ValueError, 'bounded transport'):
                run_fixture_control(command, Path(directory), seconds=2)

    def test_cleanup_past_operation_deadline_cannot_publish_success(self):
        with tempfile.TemporaryDirectory() as directory:
            command = [sys.executable, '-c', "import subprocess,sys,json,time; subprocess.Popen([sys.executable,'-c','import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(30)']); time.sleep(.1); json.dump({},open('response.json','w'))"]
            with self.assertRaisesRegex(ControlFailure,'deadline') as caught:
                run_fixture_control(command, Path(directory), seconds=.5)
            self.assertTrue(caught.exception.cleanup_confirmed)

    def test_phase_artifact_measurement_includes_monitoring_caches(self):
        from vipe_benchmark.final_render_qualification_control import phase_artifact_bytes
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root/'phase'
            output.mkdir()
            (output/'tiny-result').write_bytes(b'x')
            cache = root/'phase-controls'/'kernel-cache'
            cache.mkdir(parents=True)
            (cache/'large').write_bytes(b'x'*2048)
            self.assertGreaterEqual(phase_artifact_bytes(output),2049)
            (cache/'large').unlink()
            self.assertLess(phase_artifact_bytes(output),2049*2)
