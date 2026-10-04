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
            def events(self): return []
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
            def events(self): return []
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

    def test_consumed_or_started_reservation_replay_never_launches_or_writes(self):
        import time
        from unittest.mock import patch
        from vipe_benchmark.ledger import Ledger
        from vipe_benchmark.config import load
        for terminal in (True,False):
            with self.subTest(terminal=terminal), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                ledger = Ledger(root/'fixture-ledger.jsonl',load())
                with ledger.locked() as (stream,events):
                    reservation = ledger._append(stream,events,dict(event='reserve',job_id='fixture/native-probe',
                        resource='cpu',seconds=60,command=['fixture-never-launched'],monotonic_start=time.monotonic(),
                        evidence=dict(record_kind='actual',execution_authorized=True,native_adapter_qualified=True)))
                if terminal:
                    ledger.finish(reservation['job_id'],'failed',1.,cleanup_confirmed=True,cleanup_uncertain=False)
                else:
                    ledger.note('started',job_id=reservation['job_id'],pid=123,pgid=123)
                before = ledger.path.read_bytes()
                with patch('vipe_benchmark.final_render_actual_supervisor._supervise_reserved') as execute:
                    with self.assertRaisesRegex(ValueError,'current active unstarted reservation'):
                        supervise_reserved(ledger,reservation,reservation['command'],root/'output',{},
                            release_path=root/'release.json')
                    execute.assert_not_called()
                from vipe_benchmark.final_render_admission import validate_dispatch_invocation
                with patch('vipe_benchmark.final_render_admission.invocation_binding') as binding:
                    with self.assertRaisesRegex(ValueError,'current active unstarted reservation'):
                        validate_dispatch_invocation({},ledger,reservation)
                    binding.assert_not_called()
                self.assertEqual(ledger.path.read_bytes(),before)
                self.assertFalse((root/'output').exists())
                self.assertFalse((root/'output-controls').exists())

    def test_missing_acceptance_fails_and_finishes_cleaned_reservation(self):
        import sys
        import time
        import types
        from unittest.mock import patch
        from vipe_benchmark.files import file_record, write_json, read_json
        from vipe_benchmark.final_render_actual_supervisor import ActualSupervisionFailure
        class LedgerFixture:
            config = dict(gpu_peak_device_gib_limit=20,cpu_max_workers=8,
                new_artifact_disk_gib_limit=210,new_download_gib_limit=110)
            def __init__(self,reservation):
                self.reservation = reservation
                self.finished = []
            def events(self): return []
            def states(self): return {'test':self.reservation}
            def note(self,*args,**kwargs): pass
            def finish(self,job,status,elapsed,**fields):
                self.finished.append((status,fields))
                self.reservation = dict(event='finish',status=status)
                return self.reservation
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            release = root/'release.json'
            command = [sys.executable,'-c','pass','--release-file',str(release)]
            reservation = dict(event='reserve',job_id='test',event_sha256='e'*64,
                command=command,seconds=10.,monotonic_start=time.monotonic(),
                boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                evidence=dict(schema='plan069-final-render-reservation-binding/v1',record_kind='actual',
                    execution_authorized=True,native_adapter_qualified=True))
            ledger = LedgerFixture(reservation)
            write_json(root/'request.json',dict(device_bytes_limit=20*2**30,
                cpu_workers_limit=8,artifact_bytes_limit=2**30))
            write_json(root/'invocation.json',dict(request=file_record(root/'request.json'),output=str(root/'output')))
            gate = types.ModuleType('vipe_benchmark.final_render_admission')
            gate.validate_dispatch_invocation = lambda *args: None
            sample = dict(artifact_bytes=0,download_bytes=0,device_bytes=0,cpu_workers_used=0,
                free_disk_bytes=2**30,phase_artifact_bytes=0,gpu_pids=[],owned_pids=[])
            def control(operation,*args,**kwargs):
                return None if operation == 'accept' else sample
            with patch.dict(sys.modules,{'vipe_benchmark.final_render_admission':gate}), patch(
                'vipe_benchmark.final_render_actual_supervisor.run_control',side_effect=control):
                with self.assertRaisesRegex(ActualSupervisionFailure,'acceptance result missing') as caught:
                    supervise_reserved(ledger,reservation,command,root/'output',
                        file_record(root/'invocation.json'),release_path=release)
            self.assertIsInstance(caught.exception.__cause__,RuntimeError)
            self.assertEqual(len(ledger.finished),1)
            status, fields = ledger.finished[0]
            self.assertEqual(status,'failed')
            self.assertTrue(fields['cleanup_confirmed'])
            self.assertFalse(fields['cleanup_uncertain'])
            self.assertIsNone(fields['result'])
            self.assertEqual(ledger.states()['test']['event'],'finish')
            receipt = read_json(root/'output-controls'/'supervision.json')
            self.assertEqual(receipt['status'],'failed')
            self.assertIn('acceptance result missing',receipt['error'])
            self.assertFalse(receipt['execution_authorized'])
