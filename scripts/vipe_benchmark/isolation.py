"""Fail closed on ViPE imports/source access in a standalone worker process."""
import importlib.abc
import os
from pathlib import Path
import sys


class NoViPE(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('vipe', 'vipe_ext'):
            raise ImportError('standalone benchmark workers may not import ViPE')
        return None


def deny_vipe(source_roots):
    if any(name.split('.')[0] in ('vipe', 'vipe_ext') for name in sys.modules):
        raise ValueError('ViPE already loaded before standalone isolation')
    roots = [Path(p).resolve() for p in source_roots]
    sys.meta_path.insert(0, NoViPE())

    def forbidden(value):
        if not isinstance(value, (str, bytes, os.PathLike)):
            return False
        path = Path(os.fsdecode(value))
        # Resolve symlinks as well as lexical paths. stat/readlink do not invoke
        # this hook's open/scandir cases.
        path = Path(os.path.abspath(path)).resolve()
        return 'prompts' in path.parts or any(path.is_relative_to(root) for root in roots)

    def audit(event, args):
        if event in ('open', 'os.listdir', 'os.scandir', 'ctypes.dlopen') and args and forbidden(args[0]):
            raise PermissionError('standalone worker attempted prohibited source/extension access')
        if event == 'subprocess.Popen':
            # Standalone adapters do not spawn helpers whose filesystem access
            # could escape the Python import/source guard.
            raise PermissionError('standalone model worker subprocesses are prohibited')

    sys.addaudithook(audit)
    return dict(import_guard=True, source_roots=[str(p) for p in roots], subprocesses=False,
                limitation='Python audit guard; native runtime qualification still required')
