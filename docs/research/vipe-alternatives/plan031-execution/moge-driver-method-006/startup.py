"""Proposed pre-helper startup hook; grants no execution authority."""
import hashlib
from pathlib import Path
from types import ModuleType


def install_before_helpers(guard_record):
    """A future reviewed producer calls this before helpers or numeric imports."""
    path = Path(__file__).absolute().with_name('network_guard.py')
    if path != path.resolve() or 'prompts' in path.parts:
        raise ValueError('guard path must be literal reviewed method006 source')
    code = path.read_bytes()
    actual = dict(path=str(path), bytes=len(code), sha256=hashlib.sha256(code).hexdigest())
    if guard_record != actual:
        raise ValueError('exact reviewed method006 guard record required')
    module = ModuleType('method006_reviewed_network_guard')
    module.__file__ = str(path)
    exec(compile(code, str(path), 'exec'), module.__dict__)
    return module.deny_native_network()
