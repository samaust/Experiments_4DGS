"""D11 admission retains the prepared environment invocation spelling."""
import importlib.util
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/basketball_vipe_depth_d11_dispatch.py'
spec = importlib.util.spec_from_file_location('d11_dispatch', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class D11DispatchTests(unittest.TestCase):
    def test_resolved_host_binary_cannot_replace_prepared_venv_invocation(self):
        with tempfile.TemporaryDirectory() as directory:
            venv = Path(directory) / 'venv/bin/python'
            host = Path(directory) / 'python3'
            host.write_text('synthetic interpreter')
            venv.parent.mkdir(parents=True)
            venv.symlink_to(host)
            qualification = dict(runtime=dict(python_executable=str(venv)))
            module.validate_runtime_interpreter(qualification, str(venv))
            with self.assertRaisesRegex(ValueError, 'qualified virtual environment interpreter differs'):
                module.validate_runtime_interpreter(qualification, str(venv.resolve()))

    def test_worker_name_matches_ledger_native_contract(self):
        worker = SCRIPT.with_name('basketball_vipe_depth_d11_maps.py')
        self.assertTrue(worker.is_file())
        self.assertIn(str(worker.name), SCRIPT.read_text())
