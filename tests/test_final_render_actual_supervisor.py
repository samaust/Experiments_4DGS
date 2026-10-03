"""Admission/ledger seam: fixture processes cannot become actual workers."""
from pathlib import Path
import tempfile
import unittest

from vipe_benchmark.final_render_actual_supervisor import supervise_reserved


class ActualSupervisorTests(unittest.TestCase):
    def test_fixture_reservation_rejected_before_process_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'output'
            with self.assertRaisesRegex(ValueError, 'actual reservation'):
                supervise_reserved(None, {'event':'reserve','evidence':{'record_kind':'fixture'}},
                    ['/not/a/command'], output, {}, release_path=Path(directory)/'release.json')
            self.assertFalse(output.exists())

    def test_command_mismatch_charges_reserved_attempt_without_launch(self):
        import time
        from vipe_benchmark.final_render_actual_supervisor import ActualSupervisionFailure
        reservation = dict(event='reserve',job_id='test',event_sha256='a'*64,
            command=['/approved/command'],monotonic_start=time.monotonic(),
            evidence=dict(record_kind='actual',execution_authorized=True,native_adapter_qualified=True))
        class LedgerFixture:
            def __init__(self):
                self.finished = []
            def states(self):
                return {'test':reservation}
            def finish(self, job, status, elapsed, **fields):
                self.finished.append((job,status,elapsed,fields))
                return dict(event='finish',status=status)
        ledger = LedgerFixture()
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ActualSupervisionFailure,'exact reserved command'):
                supervise_reserved(ledger,reservation,['/different/command'],
                    Path(directory)/'output',{},release_path=Path(directory)/'release')
            self.assertEqual(len(ledger.finished),1)
            self.assertEqual(ledger.finished[0][1],'failed')
            self.assertTrue(ledger.finished[0][3]['cleanup_confirmed'])
            self.assertFalse((Path(directory)/'output').exists())

    def test_uncertain_monitor_cleanup_keeps_terminal_attempt_uncertain(self):
        import os
        import sys
        import time
        import types
        from unittest.mock import patch
        from vipe_benchmark.files import file_record, write_json
        from vipe_benchmark.final_render_actual_control import ControlFailure
        from vipe_benchmark.final_render_actual_supervisor import ActualSupervisionFailure
        class LedgerFixture:
            config = {}
            def __init__(self,reservation):
                self.reservation = reservation
                self.finished = []
            def states(self):
                return {'test':self.reservation}
            def note(self,*args,**kwargs):
                pass
            def finish(self,job,status,elapsed,**fields):
                self.finished.append((status,fields))
                return dict(event='finish',status=status)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            release = root/'release.json'
            command = [sys.executable,'-c','import time; time.sleep(30)','--release-file',str(release)]
            reservation = dict(event='reserve',job_id='test',event_sha256='b'*64,
                command=command,seconds=10.,monotonic_start=time.monotonic(),
                boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                evidence=dict(record_kind='actual',execution_authorized=True,native_adapter_qualified=True))
            ledger = LedgerFixture(reservation)
            write_json(root/'request.json',{})
            write_json(root/'invocation.json',dict(request=file_record(root/'request.json'),output=str(root/'output')))
            gate = types.ModuleType('vipe_benchmark.final_render_admission')
            gate.validate_dispatch_invocation = lambda *args: None
            with patch.dict(sys.modules,{'vipe_benchmark.final_render_admission':gate}), patch(
                'vipe_benchmark.final_render_actual_supervisor.run_control',
                side_effect=ControlFailure('test monitor cleanup uncertain',cleanup_confirmed=False)):
                with self.assertRaises(ActualSupervisionFailure):
                    supervise_reserved(ledger,reservation,command,root/'output',
                        file_record(root/'invocation.json'),release_path=release)
            self.assertEqual(len(ledger.finished),1)
            status, fields = ledger.finished[0]
            self.assertEqual(status,'failed')
            self.assertFalse(fields['cleanup_confirmed'])
            self.assertTrue(fields['cleanup_uncertain'])
