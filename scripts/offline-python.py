#!/usr/bin/env python3
"""Run a Python script with Linux seccomp blocking non-Unix sockets.

Install before importing Torch so new worker threads inherit the filter.
Local Unix-domain IPC and GPU device access remain allowed. This is a network
restriction for offline model validation, not a general untrusted-code sandbox.
API reference: https://github.com/seccomp/libseccomp/blob/main/include/seccomp.h.in
"""
import argparse
import ctypes
import errno
import json
import os
from pathlib import Path
import runpy
import socket
import sys


class Comparison(ctypes.Structure):
    _fields_ = [('arg', ctypes.c_uint), ('op', ctypes.c_int),
                ('datum_a', ctypes.c_uint64), ('datum_b', ctypes.c_uint64)]


def restrict_network():
    lib = ctypes.CDLL('libseccomp.so.2', use_errno=True)
    lib.seccomp_init.argtypes = [ctypes.c_uint32]
    lib.seccomp_init.restype = ctypes.c_void_p
    lib.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    lib.seccomp_syscall_resolve_name.restype = ctypes.c_int
    lib.seccomp_rule_add_array.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int,
                                         ctypes.c_uint, ctypes.POINTER(Comparison)]
    lib.seccomp_rule_add_array.restype = ctypes.c_int
    lib.seccomp_load.argtypes = [ctypes.c_void_p]
    lib.seccomp_load.restype = ctypes.c_int
    lib.seccomp_release.argtypes = [ctypes.c_void_p]
    lib.seccomp_release.restype = None
    context = lib.seccomp_init(0x7fff0000)  # SCMP_ACT_ALLOW
    if not context:
        raise RuntimeError('seccomp_init failed')

    def check(code, operation):
        if code < 0:
            raise OSError(-code, operation+': '+os.strerror(-code))

    try:
        for name in ('socket', 'socketpair'):
            number = lib.seccomp_syscall_resolve_name(name.encode())
            if number < 0:
                raise RuntimeError('unavailable syscall: '+name)
            comparison = Comparison(0, 1, socket.AF_UNIX, 0)  # SCMP_CMP_NE
            check(lib.seccomp_rule_add_array(context, 0x00050000 | errno.EPERM,
                  number, 1, ctypes.byref(comparison)), 'seccomp rule '+name)
        # io_uring can issue socket operations without a socket() syscall.
        number = lib.seccomp_syscall_resolve_name(b'io_uring_setup')
        if number < 0:
            raise RuntimeError('unavailable syscall: io_uring_setup')
        check(lib.seccomp_rule_add_array(context, 0x00050000 | errno.EPERM,
                                        number, 0, None), 'seccomp io_uring rule')
        check(lib.seccomp_load(context), 'seccomp_load')
    finally:
        lib.seccomp_release(context)
    probes = {}
    for family in (socket.AF_INET, socket.AF_INET6):
        try:
            with socket.socket(family, socket.SOCK_STREAM):
                pass
        except OSError as error:
            if error.errno != errno.EPERM:
                raise
            probes[family.name] = 'EPERM (expected offline self-test)'
        else:
            raise RuntimeError('offline socket probe unexpectedly succeeded')
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM):
        probes['AF_UNIX'] = 'allowed local IPC'
    return dict(policy='seccomp: Unix-domain sockets only; io_uring_setup denied', probes=probes)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('script', type=Path, nargs='?')
    parser.add_argument('arguments', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    report = restrict_network()
    print(json.dumps(report), flush=True)
    if args.script:
        os.environ['STG_OFFLINE_GUARD'] = json.dumps(report)
        sys.path.insert(0, str(args.script.resolve().parent))
        sys.argv = [str(args.script), *args.arguments]
        runpy.run_path(str(args.script), run_name='__main__')


if __name__ == '__main__':
    main()
