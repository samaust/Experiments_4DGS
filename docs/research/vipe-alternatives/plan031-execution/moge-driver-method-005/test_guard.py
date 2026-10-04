"""CPU-only actual native guard fixture; no CUDA/model/network connection."""
import argparse
import ctypes
import errno
import importlib.util
import json
import os
from pathlib import Path
import socket
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--guard', required=True)
    parser.add_argument('--audit-guard')
    args = parser.parse_args()
    path = Path(args.guard).resolve()
    assert 'prompts' not in path.parts
    spec = importlib.util.spec_from_file_location('exact_guard', path)
    assert spec is not None and spec.loader is not None
    guard = importlib.util.module_from_spec(spec); spec.loader.exec_module(guard)
    start = time.monotonic(); guard.deny_native_network()
    if args.audit_guard:
        audit_path = Path(args.audit_guard).resolve()
        assert 'prompts' not in audit_path.parts
        audit_spec = importlib.util.spec_from_file_location('retained_audit', audit_path)
        assert audit_spec is not None and audit_spec.loader is not None
        audit = importlib.util.module_from_spec(audit_spec); audit_spec.loader.exec_module(audit)
        audit.install_guards()
    libc = ctypes.CDLL(None, use_errno=True)
    libc.socket.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
    libc.close.argtypes = [ctypes.c_int]
    domains = (socket.AF_INET, socket.AF_INET6)
    denied = []
    for family, kind, protocol in [(socket.AF_UNIX, socket.SOCK_STREAM, 0),
        (socket.AF_UNIX, socket.SOCK_DGRAM, 0), (socket.AF_UNIX, socket.SOCK_SEQPACKET, 0),
        (socket.AF_UNIX, socket.SOCK_SEQPACKET | socket.SOCK_CLOEXEC | socket.SOCK_NONBLOCK, 0),
        (socket.AF_UNIX, socket.SOCK_SEQPACKET | socket.SOCK_CLOEXEC, 1)] + [
        (family, socket.SOCK_STREAM, 0) for family in domains]:
        ctypes.set_errno(0); fd = libc.socket(int(family), int(kind), protocol)
        assert fd == -1 and ctypes.get_errno() == errno.EPERM
        denied.append([int(family), int(kind), protocol])
    fd = libc.socket(int(socket.AF_UNIX), int(socket.SOCK_SEQPACKET | socket.SOCK_CLOEXEC), 0)
    assert fd >= 0, ('observed creation denied', ctypes.get_errno())
    operations = {'connect': (fd, None, 0), 'bind': (fd, None, 0), 'listen': (fd, 0),
        'accept': (fd, None, None), 'accept4': (fd, None, None, 0),
        'sendto': (fd, None, 0, 0, None, 0), 'sendmsg': (fd, None, 0),
        'sendmmsg': (fd, None, 0, 0), 'recvfrom': (fd, None, 0, 0, None, None),
        'recvmsg': (fd, None, 0), 'recvmmsg': (fd, None, 0, 0, None)}
    for name, arguments in operations.items():
        ctypes.set_errno(0); value = getattr(libc, name)(*arguments)
        assert value == -1 and ctypes.get_errno() == errno.EPERM, (name, value, ctypes.get_errno())
    try:
        socket.socketpair()
        raise AssertionError('socketpair unexpectedly allowed')
    except OSError as error:
        assert error.errno == errno.EPERM
    libseccomp = ctypes.CDLL('libseccomp.so.2')
    libseccomp.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    for name in ('io_uring_setup', 'io_uring_enter', 'io_uring_register'):
        number = libseccomp.seccomp_syscall_resolve_name(name.encode())
        assert number >= 0
        ctypes.set_errno(0)
        assert libc.syscall(number, 0, 0, 0, 0, 0, 0) == -1 and ctypes.get_errno() == errno.EPERM
    with socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET | socket.SOCK_CLOEXEC, 0) as stream:
        if args.audit_guard:
            try:
                stream.connect('/nonexistent-local-fixture')
                raise AssertionError('Python connect unexpectedly allowed')
            except PermissionError:
                pass
    # read/write cannot create a peer for this new unconnected socket.
    try:
        os.write(fd, b'fixture')
        raise AssertionError('unconnected socket transferred bytes')
    except OSError as error:
        assert error.errno in (errno.ENOTCONN, errno.EDESTADDRREQ, errno.EPIPE)
    finally:
        libc.close(fd)
    print(json.dumps(dict(status='passed', elapsed_seconds=time.monotonic()-start,
        denied_creation=denied, blocked_operations=list(operations), socketpair_blocked=True,
        unconnected_write_blocked=True, observed_creation_allowed=True,
        io_uring_blocked=True, retained_python_audit=bool(args.audit_guard),
        cuda_initialized=False, model_loaded=False, external_connection_attempted=False)))


if __name__ == '__main__':
    main()
