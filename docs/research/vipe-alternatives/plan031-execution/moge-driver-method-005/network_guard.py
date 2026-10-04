"""Proposed creation-only Unix socket exception; no execution authority."""
import ctypes
import socket

DENIED = ('socketpair', 'connect', 'bind', 'listen', 'accept', 'accept4',
          'sendto', 'sendmsg', 'sendmmsg', 'recvfrom', 'recvmsg', 'recvmmsg',
          'io_uring_setup', 'io_uring_enter', 'io_uring_register')
OBSERVED_DOMAIN = int(socket.AF_UNIX)
OBSERVED_TYPE = int(socket.SOCK_SEQPACKET | socket.SOCK_CLOEXEC)
OBSERVED_PROTOCOL = 0


def require(value, message):
    if not value:
        raise ValueError(message)


def deny_native_network():
    """Allow only socket(AF_UNIX, SOCK_SEQPACKET|SOCK_CLOEXEC, 0) creation."""
    class Comparison(ctypes.Structure):
        _fields_ = [('argument', ctypes.c_uint), ('operation', ctypes.c_int),
                    ('datum_a', ctypes.c_uint64), ('datum_b', ctypes.c_uint64)]
    libc = ctypes.CDLL(None, use_errno=True)
    require(libc.prctl(38, 1, 0, 0, 0) == 0, 'PR_SET_NO_NEW_PRIVS failed')
    lib = ctypes.CDLL('libseccomp.so.2', use_errno=True)
    lib.seccomp_init.argtypes = [ctypes.c_uint32]
    lib.seccomp_init.restype = ctypes.c_void_p
    lib.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    lib.seccomp_rule_add_array.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int,
        ctypes.c_uint, ctypes.POINTER(Comparison)]
    lib.seccomp_load.argtypes = [ctypes.c_void_p]
    lib.seccomp_release.argtypes = [ctypes.c_void_p]
    context = lib.seccomp_init(0x7fff0000)  # SCMP_ACT_ALLOW
    require(bool(context), 'seccomp_init failed')
    try:
        syscall = lib.seccomp_syscall_resolve_name(b'socket')
        require(syscall >= 0, 'unsupported socket syscall')
        # Separate deny rules form OR: any differing argument is denied. No broad allow.
        for argument, value in enumerate((OBSERVED_DOMAIN, OBSERVED_TYPE, OBSERVED_PROTOCOL)):
            comparison = Comparison(argument, 1, value, 0)  # SCMP_CMP_NE=1
            require(lib.seccomp_rule_add_array(context, 0x00050001, syscall, 1,
                ctypes.byref(comparison)) == 0, 'socket argument rule failed')
        for name in DENIED:
            syscall = lib.seccomp_syscall_resolve_name(name.encode())
            require(syscall >= 0, 'unsupported syscall: ' + name)
            require(lib.seccomp_rule_add_array(context, 0x00050001, syscall, 0, None) == 0,
                    'seccomp deny failed: ' + name)
        require(lib.seccomp_load(context) == 0, 'seccomp_load failed')
    finally:
        lib.seccomp_release(context)
