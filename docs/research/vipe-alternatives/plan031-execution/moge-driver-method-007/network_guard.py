"""REVIEW candidate: Unix bind/listen after a fail-closed descriptor provenance check."""
import ctypes
import os
import signal
import stat
import sys

CREATION = (1, 524293, 0)
DENIED = ('socketpair', 'connect', 'accept', 'accept4',
          'sendto', 'sendmsg', 'sendmmsg', 'recvfrom', 'recvmsg', 'recvmmsg',
          'pidfd_getfd', 'io_uring_setup', 'io_uring_enter', 'io_uring_register')
NUMERIC_MODULES = ('numpy', 'scipy', 'torch', 'triton', 'cv2')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def policy_rules():
    """Bind/listen rely on descriptor provenance, not socket-pointer inspection."""
    return (tuple(('socket', argument, 'not_equal', value)
                  for argument, value in enumerate(CREATION)) +
            tuple((name, None, 'always', None) for name in DENIED))


def _identity(fd):
    value = os.fstat(fd)
    return (value.st_dev, value.st_ino, value.st_mode, value.st_rdev)


def own_process_snapshot():
    """Inspect only this process; keep scandir's descriptor live during fstat."""
    require(not any(name.split('.')[0] in NUMERIC_MODULES for name in sys.modules),
            'guard must precede numeric imports')
    tasks_before = tuple(sorted(os.listdir('/proc/self/task')))
    require(tasks_before == (str(os.getpid()),), 'guard requires one main thread')
    own_directory = os.stat('/proc/self/fd')
    descriptors = {}
    with os.scandir('/proc/self/fd') as entries:
        for entry in entries:
            require(entry.name.isdecimal(), 'unexpected own-proc descriptor name')
            fd = int(entry.name)
            identity = _identity(fd)  # disappearance is fatal, never ignored
            require(not stat.S_ISSOCK(identity[2]), 'inherited socket descriptor')
            # Inspection directory descriptors cannot provide a socket endpoint.
            if (identity[:2] == (own_directory.st_dev, own_directory.st_ino)
                    and stat.S_ISDIR(identity[2])):
                continue
            descriptors[fd] = identity
        require(all(_identity(fd) == identity for fd, identity in descriptors.items()),
                'descriptor replaced during inspection')
    require(tuple(sorted(os.listdir('/proc/self/task'))) == tasks_before,
            'thread set changed during inspection')
    return descriptors


def establish_and_install(snapshot, install):
    """Fake seams exercise startup ordering without socket/filter execution."""
    before = snapshot()
    require(snapshot() == before, 'descriptor inventory changed before filter')
    install(policy_rules())
    require(snapshot() == before, 'descriptor inventory changed during filter')
    return dict(socket_descriptors=0, descriptor_count=len(before),
                single_thread=True, numeric_imports=False, unix_bind_allowed=True,
                unix_listen_allowed=True)


def _install_rules(rules):
    class Comparison(ctypes.Structure):
        _fields_ = [('argument', ctypes.c_uint), ('operation', ctypes.c_int),
                    ('datum_a', ctypes.c_uint64), ('datum_b', ctypes.c_uint64)]
    libc = ctypes.CDLL(None, use_errno=True)
    require(libc.prctl(38, 1, 0, 0, 0) == 0, 'PR_SET_NO_NEW_PRIVS failed')
    lib = ctypes.CDLL('libseccomp.so.2', use_errno=True)
    lib.seccomp_init.argtypes = [ctypes.c_uint32]
    lib.seccomp_init.restype = ctypes.c_void_p
    lib.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    lib.seccomp_rule_add_array.argtypes = [ctypes.c_void_p, ctypes.c_uint32,
        ctypes.c_int, ctypes.c_uint, ctypes.POINTER(Comparison)]
    lib.seccomp_load.argtypes = [ctypes.c_void_p]
    lib.seccomp_release.argtypes = [ctypes.c_void_p]
    context = lib.seccomp_init(0x7fff0000)
    require(bool(context), 'seccomp_init failed')
    try:
        for name, argument, operation, value in rules:
            syscall = lib.seccomp_syscall_resolve_name(name.encode())
            require(syscall >= 0, 'unsupported syscall: ' + name)
            comparison = Comparison(argument or 0, 1, value or 0, 0)
            count = int(operation == 'not_equal')
            require(lib.seccomp_rule_add_array(context, 0x00050001, syscall,
                count, ctypes.byref(comparison) if count else None) == 0,
                'seccomp deny failed: ' + name)
        require(lib.seccomp_load(context) == 0, 'seccomp_load failed')
    finally:
        lib.seccomp_release(context)


def deny_native_network():
    """Use only in a fresh exec worker before helpers/numeric/native imports."""
    blocked = signal.valid_signals() - {signal.SIGKILL, signal.SIGSTOP}
    previous = signal.pthread_sigmask(signal.SIG_BLOCK, blocked)
    try:
        return establish_and_install(own_process_snapshot, _install_rules)
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, previous)
