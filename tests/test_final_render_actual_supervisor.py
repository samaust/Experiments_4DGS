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
