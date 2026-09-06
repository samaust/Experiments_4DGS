"""Linux process-group deadline enforcement for plan-004 training workers.

Workers receive TRAINING_STOP_MONOTONIC and must checkpoint at an iteration
boundary by then. SIGTERM requests shutdown at that time; SIGKILL terminates
the process group before the allocation ends if graceful shutdown fails.
"""
import ctypes
import os
import signal
import subprocess
import time


def supervise(command, *, cwd, log, seconds, checkpoint_margin=30., kill_margin=2.):
    if not 0 < kill_margin < checkpoint_margin < seconds:
        raise ValueError('require 0 < kill margin < checkpoint margin < duration')
    started = time.monotonic()
    stop_at = started+seconds-checkpoint_margin
    kill_at = started+seconds-kill_margin
    env = os.environ.copy()
    env['TRAINING_STOP_MONOTONIC'] = repr(stop_at)
    parent_pid = os.getpid()
    libc = ctypes.CDLL(None, use_errno=True)

    def child_setup():
        # Linux PR_SET_PDEATHSIG: do not leave a training worker running if
        # the supervisor is killed. Run supervisor single-threaded.
        if libc.prctl(1, signal.SIGKILL, 0, 0, 0) != 0:
            os._exit(125)
        if os.getppid() != parent_pid:
            os._exit(125)

    process = subprocess.Popen(command, cwd=cwd, env=env, stdout=log,
                               stderr=subprocess.STDOUT, start_new_session=True,
                               preexec_fn=child_setup)
    requested = False
    killed = False

    def signal_group(sig):
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            pass

    try:
        while process.poll() is None:
            now = time.monotonic()
            if now >= kill_at:
                killed = True
                signal_group(signal.SIGKILL)
                break
            if now >= stop_at and not requested:
                requested = True
                signal_group(signal.SIGTERM)
            time.sleep(min(.05, max(0., kill_at-now)))
        process.wait(timeout=kill_margin)
    finally:
        # Also terminate surviving descendants if the leader exits early.
        signal_group(signal.SIGKILL)
        if process.poll() is None:
            process.wait(timeout=kill_margin)
    return dict(exit_code=process.returncode, stop_requested=requested, forced_kill=killed,
                wall_seconds=time.monotonic()-started)
