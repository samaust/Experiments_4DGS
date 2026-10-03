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
