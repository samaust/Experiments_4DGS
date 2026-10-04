"""Generic notes cannot manufacture checked execution authority."""
from pathlib import Path
import tempfile
import unittest

from vipe_benchmark.config import load
from vipe_benchmark.ledger import Ledger


class ProtectedLedgerNoteTests(unittest.TestCase):
    def test_authorization_notes_are_rejected_without_changing_ledger(self):
        events = ('depth_setup_authorized','depth_attempt_authorized',
            'native_qualification_authorized','depth_driver_qualification_authorized',
            'final_render_do_authorized','setup_recovery_authorized',
            'component_recovery_authorized','reconstruction_recovery_authorized',
            'memory_diagnostic_authorized')
        for event in events:
            with self.subTest(event=event), tempfile.TemporaryDirectory() as directory:
                ledger = Ledger(Path(directory)/'fixture-ledger.jsonl',load())
                ledger.note('fixture_observation',value='retained')
                before = ledger.path.read_bytes()
                with self.assertRaisesRegex(ValueError,'checked ledger transition'):
                    ledger.note(event,job_id='fixture/never-authorized')
                self.assertEqual(ledger.path.read_bytes(),before)
                self.assertEqual(len(ledger.events()),1)

    def test_ordinary_notes_preserve_existing_history(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory)/'fixture-ledger.jsonl',load())
            first = ledger.note('fixture_observation',value='retained')
            second = ledger.note('started',job_id='fixture/lifecycle',pid=123,pgid=123)
            self.assertEqual(ledger.events(),[first,second])
            self.assertEqual(second['previous_sha256'],first['event_sha256'])
