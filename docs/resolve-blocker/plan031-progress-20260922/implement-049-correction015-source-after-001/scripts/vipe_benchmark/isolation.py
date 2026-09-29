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


def deny_vipe(source_roots, native_helpers=None):
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
        lexical = Path(os.path.abspath(path))
        path = lexical.resolve()
        return ('prompts' in lexical.parts or 'prompts' in path.parts or
                any(path.is_relative_to(root) or lexical.is_relative_to(root) for root in roots))

    def audit(event, args):
        if event in ('open', 'os.listdir', 'os.scandir', 'ctypes.dlopen') and args and forbidden(args[0]):
            raise PermissionError('standalone worker attempted prohibited source/extension access')
        if event == 'subprocess.Popen':
            if native_helpers is None or not native_helpers.consume(args):
                raise PermissionError('standalone model worker subprocesses are prohibited')
        if event in ('os.system', 'os.posix_spawn', 'os.exec', 'os.fork', 'os.forkpty'):
            raise PermissionError('standalone worker process escape is prohibited')

    sys.addaudithook(audit)
    if native_helpers is not None:
        native_helpers.install()
    return dict(import_guard=True, source_roots=[str(p) for p in roots],
                subprocesses=False if native_helpers is None else 'confined-native-helpers',
                native_helpers=None if native_helpers is None else native_helpers.evidence,
                limitation='Python audit guard; native runtime qualification still required')
