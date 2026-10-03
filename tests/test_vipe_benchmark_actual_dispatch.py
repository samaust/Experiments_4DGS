import tempfile
import unittest
from pathlib import Path

from vipe_benchmark.files import file_record, write_json


class ActualDispatchTests(unittest.TestCase):
    def test_native_command_has_a_registration_release_gate(self):
        from vipe_benchmark.final_render_actual_dispatch import native_command
        command = native_command({'path':'/env/bin/python'}, {'path':'/code/worker.py'},
                                 Path('/run/invocation.json'), Path('/run/release.json'))
        self.assertEqual(command, ['/env/bin/python','/code/worker.py','--invocation',
                                   '/run/invocation.json','--release-file','/run/release.json'])

    def test_fixture_envelope_cannot_construct_an_actual_dispatcher(self):
        from vipe_benchmark.final_render_actual_dispatch import ActualDispatcher
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'envelope.json'
            write_json(path, dict(schema='plan069-final-render-do/v1', record_kind='fixture', mode='DO'))
            with self.assertRaisesRegex(ValueError, 'actual DO'):
                ActualDispatcher(file_record(path), None)
            self.assertEqual(sorted(p.name for p in Path(directory).iterdir()), ['envelope.json'])

    def test_changed_envelope_is_rejected_before_ledger_or_worker_access(self):
        from vipe_benchmark.final_render_actual_dispatch import ActualDispatcher
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'envelope.json'
            write_json(path, dict(record_kind='fixture'))
            record = file_record(path)
            path.write_text('{}')
            with self.assertRaisesRegex(ValueError, 'changed file'):
                ActualDispatcher(record, None)

    def test_byte_count_is_part_of_the_immutable_envelope(self):
        from vipe_benchmark.final_render_actual_dispatch import ActualDispatcher
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'envelope.json'
            write_json(path, dict(record_kind='fixture'))
            record = file_record(path)
            record['bytes'] += 1
            with self.assertRaisesRegex(ValueError, 'exact unchanged'):
                ActualDispatcher(record, None)
