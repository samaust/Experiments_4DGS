"""Admission/ledger seam: fixture processes cannot become actual workers."""
from pathlib import Path
import tempfile
import unittest

from vipe_benchmark.final_render_qualification_supervisor import supervise_reserved


class QualificationSupervisorTests(unittest.TestCase):
    def test_fixture_reservation_rejected_before_process_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'output'
            with self.assertRaisesRegex(ValueError, 'qualification reservation'):
                supervise_reserved(None, {'event':'reserve','evidence':{'record_kind':'fixture'}},
                    ['/not/a/command'], output, {}, release_path=Path(directory)/'release.json')
            self.assertFalse(output.exists())

    def test_production_do_reservation_cannot_enter_qualification(self):
        with tempfile.TemporaryDirectory() as directory:
            evidence = dict(record_kind='actual',execution_authorized=True,
                            native_adapter_qualified=True,
                            schema='plan069-final-render-reservation-binding/v1')
            with self.assertRaisesRegex(ValueError, 'qualification reservation'):
                supervise_reserved(None,dict(event='reserve',evidence=evidence),
                    ['/production/command'],Path(directory)/'output',{},
                    release_path=Path(directory)/'release')
            self.assertFalse((Path(directory)/'output').exists())

    def test_command_mismatch_charges_reserved_attempt_without_launch(self):
        import time
        from vipe_benchmark.final_render_qualification_supervisor import QualificationSupervisionFailure
        reservation = dict(event='reserve',job_id='test',event_sha256='a'*64,
            command=['/approved/command'],monotonic_start=time.monotonic(),
            evidence=dict(record_kind='actual',execution_authorized=True,native_adapter_qualified=False,role='native-qualification',schema='plan069-final-render-qualification-reservation-binding/v1'))
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
            with self.assertRaisesRegex(QualificationSupervisionFailure,'exact reserved command'):
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
        from vipe_benchmark.final_render_qualification_control import ControlFailure
        from vipe_benchmark.final_render_qualification_supervisor import QualificationSupervisionFailure
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
                evidence=dict(record_kind='actual',execution_authorized=True,native_adapter_qualified=False,role='native-qualification',schema='plan069-final-render-qualification-reservation-binding/v1'))
            ledger = LedgerFixture(reservation)
            write_json(root/'request.json',{})
            write_json(root/'invocation.json',dict(request=file_record(root/'request.json'),output=str(root/'output')))
            gate = types.ModuleType('vipe_benchmark.final_render_qualification')
            gate.validate_dispatch_invocation = lambda *args: None
            with patch.dict(sys.modules,{'vipe_benchmark.final_render_qualification':gate}), patch(
                'vipe_benchmark.final_render_qualification_supervisor.run_control',
                side_effect=ControlFailure('test monitor cleanup uncertain',cleanup_confirmed=False)):
                with self.assertRaises(QualificationSupervisionFailure):
                    supervise_reserved(ledger,reservation,command,root/'output',
                        file_record(root/'invocation.json'),release_path=release)
            self.assertEqual(len(ledger.finished),1)
            status, fields = ledger.finished[0]
            self.assertEqual(status,'failed')
            self.assertFalse(fields['cleanup_confirmed'])
            self.assertTrue(fields['cleanup_uncertain'])

    def test_foreign_gpu_process_prevents_worker_launch_and_consumes_reservation(self):
        import sys
        import time
        import types
        from unittest.mock import patch
        from vipe_benchmark.files import file_record, write_json
        from vipe_benchmark.final_render_qualification_supervisor import QualificationSupervisionFailure
        class LedgerFixture:
            config = dict(gpu_peak_device_gib_limit=20,cpu_max_workers=8,
                new_artifact_disk_gib_limit=210,new_download_gib_limit=110)
            def __init__(self,reservation):
                self.reservation = reservation
                self.finished = []
            def states(self): return {'test':self.reservation}
            def note(self,*args,**kwargs): pass
            def finish(self,job,status,elapsed,**fields):
                self.finished.append((status,fields))
                return dict(event='finish',status=status)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            release = root/'release.json'
            command = ['/never/launch','--release-file',str(release)]
            reservation = dict(event='reserve',job_id='test',event_sha256='c'*64,
                command=command,seconds=10.,monotonic_start=time.monotonic(),
                boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                evidence=dict(schema='plan069-final-render-qualification-reservation-binding/v1',record_kind='actual',
                    role='native-qualification',execution_authorized=True,native_adapter_qualified=False))
            ledger = LedgerFixture(reservation)
            write_json(root/'request.json',dict(device_bytes_limit=20*2**30,
                cpu_workers_limit=8,artifact_bytes_limit=2**30))
            write_json(root/'invocation.json',dict(request=file_record(root/'request.json'),output=str(root/'output')))
            gate = types.ModuleType('vipe_benchmark.final_render_qualification')
            gate.validate_dispatch_invocation = lambda *args: None
            sample = dict(artifact_bytes=0,download_bytes=0,device_bytes=0,cpu_workers_used=0,
                free_disk_bytes=2**30,phase_artifact_bytes=0,gpu_pids=[12345],owned_pids=[])
            with patch.dict(sys.modules,{'vipe_benchmark.final_render_qualification':gate}), patch(
                'vipe_benchmark.final_render_qualification_supervisor.run_control',return_value=sample):
                with self.assertRaisesRegex(QualificationSupervisionFailure,'foreign GPU'):
                    supervise_reserved(ledger,reservation,command,root/'output',
                        file_record(root/'invocation.json'),release_path=release)
            self.assertEqual(len(ledger.finished),1)
            self.assertEqual(ledger.finished[0][0],'failed')
            self.assertTrue(ledger.finished[0][1]['cleanup_confirmed'])
            self.assertFalse(release.exists())

    def test_terminal_publication_rejects_time_or_storage_overrun(self):
        import sys
        import time
        import types
        from unittest.mock import patch
        from vipe_benchmark.files import file_record, write_json,read_json
        from vipe_benchmark.final_render_qualification_supervisor import QualificationSupervisionFailure
        for append_delay,phase_bytes in ((4.2,0),(0.,2**30-1)):
            with self.subTest(append_delay=append_delay,phase_bytes=phase_bytes):
                class LedgerFixture:
                    config = dict(gpu_peak_device_gib_limit=20,cpu_max_workers=8,
                        new_artifact_disk_gib_limit=210,new_download_gib_limit=110)
                    def __init__(self,reservation): self.reservation = reservation
                    def states(self): return {'test':self.reservation}
                    def note(self,*args,**kwargs): pass
                    def finish(self,job,status,elapsed,**fields):
                        time.sleep(append_delay)
                        return dict(event='finish',status=status)
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    release = root/'release.json'
                    command = [sys.executable,'-c','pass','--release-file',str(release)]
                    reservation = dict(event='reserve',job_id='test',event_sha256='d'*64,
                        command=command,seconds=4.,monotonic_start=time.monotonic(),
                        boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                        evidence=dict(schema='plan069-final-render-qualification-reservation-binding/v1',record_kind='actual',
                            role='native-qualification',execution_authorized=True,native_adapter_qualified=False))
                    ledger = LedgerFixture(reservation)
                    write_json(root/'request.json',dict(device_bytes_limit=20*2**30,
                        cpu_workers_limit=8,artifact_bytes_limit=2**30))
                    write_json(root/'invocation.json',dict(request=file_record(root/'request.json'),output=str(root/'output')))
                    write_json(root/'phase.json',dict(record_kind='fixture'))
                    gate = types.ModuleType('vipe_benchmark.final_render_qualification')
                    gate.validate_dispatch_invocation = lambda *args: None
                    sample = dict(artifact_bytes=0,download_bytes=0,device_bytes=0,cpu_workers_used=0,
                        free_disk_bytes=2**30,phase_artifact_bytes=phase_bytes,gpu_pids=[],owned_pids=[])
                    def control(operation,*args,**kwargs):
                        return dict(result=file_record(root/'phase.json')) if operation == 'accept' else sample
                    with patch.dict(sys.modules,{'vipe_benchmark.final_render_qualification':gate}), patch(
                        'vipe_benchmark.final_render_qualification_supervisor.run_control',side_effect=control):
                        with self.assertRaises(QualificationSupervisionFailure):
                            supervise_reserved(ledger,reservation,command,root/'output',
                                file_record(root/'invocation.json'),release_path=release)
                    if append_delay:
                        marker = read_json(root/'output-controls'/'terminal-publication-failure.json')
                        self.assertFalse(marker['execution_authorized'])
                        self.assertFalse(marker['native_adapter_qualified'])
                        self.assertGreater(marker['elapsed_seconds'],4.)
                    else:
                        receipt = read_json(root/'output-controls'/'supervision.json')
                        self.assertEqual(receipt['status'],'failed')
                        self.assertIn('publication storage reserve',receipt['error'])
