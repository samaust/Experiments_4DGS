import tempfile
import unittest
from pathlib import Path

from vipe_benchmark.files import file_record, write_json


class ActualDispatchTests(unittest.TestCase):
    def test_native_command_preserves_real_symlinked_venv(self):
        import json
        import subprocess
        import sys
        import venv
        from vipe_benchmark.final_render_actual_dispatch import native_command
        from vipe_benchmark.final_render_admission import interpreter_invocation
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            environment = root/'env'
            venv.EnvBuilder(with_pip=False, symlinks=True).create(environment)
            launch = environment/'bin/python'
            self.assertTrue(launch.is_symlink())
            interpreter = file_record(launch)
            self.assertNotEqual(interpreter['path'], str(launch))
            worker = root/'worker.py'
            worker.write_text('import json, sys; print(json.dumps(sys.prefix))')
            command = native_command(interpreter, file_record(worker),
                root/'invocation.json', root/'release.json', interpreter_invocation=str(launch))
            self.assertEqual(command, [str(launch), str(worker), '--invocation',
                str(root/'invocation.json'), '--release-file', str(root/'release.json')])
            self.assertEqual(interpreter_invocation(interpreter, str(launch),
                environment_prefix=str(environment)), str(launch))
            self.assertEqual(json.loads(subprocess.check_output(command, text=True)), str(environment))
            with self.assertRaisesRegex(ValueError, 'outside bound environment'):
                interpreter_invocation(interpreter, interpreter['path'], environment_prefix=str(environment))
            other = root/'wrong-python'
            other.write_text('wrong executable bytes')
            with self.assertRaisesRegex(ValueError, 'binary differs'):
                native_command(interpreter, file_record(worker), root/'invocation.json',
                    root/'release.json', interpreter_invocation=str(other))

    def test_control_helper_preserves_bound_interpreter_invocation(self):
        from unittest.mock import patch
        from vipe_benchmark.final_render_actual_control import run_control
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binary = root/'binary'
            binary.write_text('fixture executable bytes')
            launch = root/'env/bin/python'
            launch.parent.mkdir(parents=True)
            launch.symlink_to(binary)
            invocation_path = root/'invocation.json'
            write_json(invocation_path, dict(interpreter=file_record(binary),
                interpreter_invocation=str(launch)))
            invocation = file_record(invocation_path)
            response = dict(schema='plan069-final-render-control-response/v1',
                operation='sample', invocation=invocation, cleanup_confirmed=True)
            with patch('vipe_benchmark.final_render_actual_control._run', return_value=response) as run:
                self.assertEqual(run_control('sample', invocation, root/'controls'), response)
            self.assertEqual(run.call_args.args[0][0], str(launch))

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
