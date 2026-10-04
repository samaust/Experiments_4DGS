"""CPU-only guard differential; never imports Torch or executes CUDA."""
import argparse
import ctypes
import errno
import importlib.util
import json
from pathlib import Path
import socket
import time


def unix_only_creation():
    """Diagnostic prototype, not a complete production no-network policy."""
    class Comparison(ctypes.Structure):
        _fields_ = [('arg', ctypes.c_uint), ('op', ctypes.c_int),
                    ('a', ctypes.c_uint64), ('b', ctypes.c_uint64)]
    libc = ctypes.CDLL(None, use_errno=True)
    assert libc.prctl(38, 1, 0, 0, 0) == 0
    lib = ctypes.CDLL('libseccomp.so.2', use_errno=True)
    lib.seccomp_init.argtypes = [ctypes.c_uint32]
    lib.seccomp_init.restype = ctypes.c_void_p
    lib.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    lib.seccomp_rule_add_array.argtypes = [ctypes.c_void_p, ctypes.c_uint32,
        ctypes.c_int, ctypes.c_uint, ctypes.POINTER(Comparison)]
    lib.seccomp_load.argtypes = [ctypes.c_void_p]
    lib.seccomp_release.argtypes = [ctypes.c_void_p]
    context = lib.seccomp_init(0x7fff0000)
    assert context
    try:
        for name in ('socket', 'socketpair'):
            # SCMP_CMP_NE on domain argument0 denies every family except AF_UNIX.
            comparison = Comparison(0, 1, socket.AF_UNIX, 0)
            nr = lib.seccomp_syscall_resolve_name(name.encode())
            assert nr >= 0
            assert lib.seccomp_rule_add_array(context, 0x00050001, nr, 1,
                ctypes.byref(comparison)) == 0
        for name in ('io_uring_setup', 'io_uring_enter', 'io_uring_register'):
            nr = lib.seccomp_syscall_resolve_name(name.encode())
            assert nr >= 0
            assert lib.seccomp_rule_add_array(context, 0x00050001, nr, 0, None) == 0
        assert lib.seccomp_load(context) == 0
    finally:
        lib.seccomp_release(context)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--producer', required=True)
    parser.add_argument('--mode', choices=('old', 'unix-prototype'), required=True)
    args = parser.parse_args()
    path = Path(args.producer).resolve()
    assert 'prompts' not in path.parts
    specification = importlib.util.spec_from_file_location('retained_producer', path)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    start = time.monotonic()
    if args.mode == 'old':
        module.deny_native_network()
    else:
        unix_only_creation()
    rows = []
    for family in (socket.AF_UNIX, socket.AF_INET, socket.AF_INET6):
        try:
            stream = socket.socket(family, socket.SOCK_STREAM)
            stream.close()
            rows.append(dict(family=int(family), allowed=True))
        except OSError as error:
            assert error.errno == errno.EPERM
            rows.append(dict(family=int(family), allowed=False, errno=error.errno))
    assert [row['allowed'] for row in rows] == ([False]*3 if args.mode == 'old' else [True, False, False]), rows
    unix_exchange = False
    try:
        first, second = socket.socketpair()
        with first, second:
            first.sendall(b'local-fixture')
            unix_exchange = second.recv(32) == b'local-fixture'
    except OSError as error:
        assert args.mode == 'old' and error.errno == errno.EPERM
    assert unix_exchange == (args.mode == 'unix-prototype')
    print(json.dumps(dict(mode=args.mode, elapsed_seconds=time.monotonic()-start,
        socket_creation=rows, unix_pair_exchange=unix_exchange, gpu_used=False,
        model_loaded=False, proves_cuda_304_cause=False)))


if __name__ == '__main__':
    main()
