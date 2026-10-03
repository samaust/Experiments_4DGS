"""D7 admission retains the virtual environment path through interpreter symlinks."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from basketball_vipe_depth_d7_dispatch import validate_runtime_interpreter


class D7RuntimeIdentityTests(unittest.TestCase):
    def test_qualified_environment_invocation_preserves_symlink_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base = root / 'base-python'
            base.write_bytes(b'fixture interpreter')
            python = root / 'environment/bin/python'
            python.parent.mkdir(parents=True)
            python.symlink_to(base)
            qualification = dict(runtime=dict(python_executable=str(python.absolute())))
            validate_runtime_interpreter(qualification, str(python))
            with self.assertRaisesRegex(ValueError, 'virtual environment interpreter differs'):
                validate_runtime_interpreter(qualification, str(base))
            other = root / 'other-environment/bin/python'
            other.parent.mkdir(parents=True)
            other.symlink_to(base)
            with self.assertRaisesRegex(ValueError, 'virtual environment interpreter differs'):
                validate_runtime_interpreter(qualification, str(other))
            with self.assertRaisesRegex(ValueError, 'virtual environment interpreter differs'):
                validate_runtime_interpreter({}, str(python))
