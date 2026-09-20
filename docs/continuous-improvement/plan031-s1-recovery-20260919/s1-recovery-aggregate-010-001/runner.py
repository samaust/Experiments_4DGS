"""Fixed serial CPU validation runner; safe to import during spawn bootstrap."""
import ast
import datetime
import io
import json
import os
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

from .files import file_record
from .s1_validation_contract import (ROOT, SUITES, source_paths, STDIN, RUNNER, THREADS,
    ENVIRONMENT, collection, callback_id, validate_inner, counters)


def stamp():
    return dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), monotonic=time.monotonic())


class Tee:
    def __init__(self, original, capture):
        self.original, self.capture = original, capture
    def write(self, value):
        self.original.write(value)
        return self.capture.write(value)
    def flush(self):
        self.original.flush()
        self.capture.flush()


class Result(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cases = []
    def startTest(self, test):
        super().startTest(test)
        self.current = dict(id=test.id(), status='passed', subtests=[])
        self.cases.append(self.current)
    def addFailure(self, test, err):
        self.current['status'] = 'failed'
        super().addFailure(test, err)
    def addError(self, test, err):
        self.current['status'] = 'error'
        super().addError(test, err)
    def addSkip(self, test, reason):
        self.current['status'] = 'skipped'
        super().addSkip(test, reason)
    def addSubTest(self, test, subtest, err):
        parameters = dict(subtest.params)
        # JSON serialization preserves primitive type distinctions, including bool/int.
        json.dumps(parameters, allow_nan=False)
        status = 'passed' if err is None else ('failed' if issubclass(err[0], test.failureException) else 'error')
        self.current['subtests'].append(dict(id=callback_id(test.id(), parameters), display_id=subtest.id(), parameters=parameters, status=status))
        if err is not None:
            self.current['status'] = status
        super().addSubTest(test, subtest, err)


def ids(suite):
    result = []
    for test in suite:
        result.extend(ids(test) if isinstance(test, unittest.TestSuite) else [test.id()])
    return result


def literal_declarations():
    return collection()[1]


def helper_probe():
    from .supervisor import monitored_call, HelperLifecycle
    from .config import load
    life = HelperLifecycle()
    value = monitored_call(dict(operation='constant', args=dict(value=37)), time.monotonic()+3,
        dict(operation='constant', args=dict(value=dict(device_bytes=0, artifact_bytes=0, download_bytes=0, gpu_pids=[]))),
        load(), {}, lifecycle=life, phase='bootstrap_probe')
    assert value == 37 and not life.helpers
    print('helper probe: 37; reaped')


def main():
    if '--helper-probe' in sys.argv:
        helper_probe()
        return 0
    expected = ROOT / '.local/envs/stg-colmap/bin/python'
    if Path(sys.executable).resolve() != expected.resolve():
        raise RuntimeError('wrong validation interpreter')
    if any(os.environ.get(k) != '1' for k in THREADS) or os.environ.get('VIPE_CPU_VALIDATION') != '1':
        raise RuntimeError('thread and CPU validation limits must be one')
    focus = os.environ.get('S1_RECEIPT_DIAGNOSTIC') == '1'
    directory = Path(os.environ['S1_VALIDATION_RUN_DIRECTORY']).resolve()
    start = stamp()
    before = [file_record(p) for p in source_paths()]
    proc_argv = Path('/proc/self/cmdline').read_bytes().split(b'\0')[:-1]
    invocation = dict(launcher_argv=[v.decode() for v in proc_argv], python_argv=list(globals().get('STDIN_PYTHON_ARGV', ())),
        runpy_argv=list(sys.argv), executable=sys.executable, resolved_interpreter=str(Path(sys.executable).resolve()),
        thread_environment={k: os.environ.get(k) for k in THREADS},
        environment={k: os.environ.get(k) for k in ENVIRONMENT}, cwd=str(Path.cwd()), run_directory=str(directory))
    cases, collected, suites, discovery_errors = [], [], [], []
    stdout, stderr = io.StringIO(), io.StringIO()
    oldout, olderr = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = Tee(oldout, stdout), Tee(olderr, stderr)
    try:
        with patch('vipe_benchmark.supervisor.gpu_reading', side_effect=AssertionError('unexpected GPU probe')), \
             patch('vipe_benchmark.execution.gpu_reading', side_effect=AssertionError('unexpected GPU probe')):
            for name in (('s1_recovery',) if focus else SUITES):
                loader = unittest.TestLoader()
                suite = loader.discover(str(ROOT/'tests'), pattern=f'test_vipe_benchmark_{name}.py')
                if focus:
                    suite = unittest.TestSuite(t for group in suite for cls in group for t in cls
                        if t.__class__.__name__ == 'NumericalEnvelopeTests')
                discovered = ids(suite)
                collected.extend(discovered)
                discovery_errors.extend(loader.errors)
                suite_start = stamp()
                result = unittest.TextTestRunner(verbosity=2, resultclass=Result, stream=sys.stderr).run(suite)
                suite_end = stamp()
                cases.extend(result.cases)
                suites.append(dict(suite=name, start=suite_start, end=suite_end,
                    elapsed_seconds=suite_end['monotonic']-suite_start['monotonic'], invocation=invocation,
                    collected=discovered, **counters(result.cases)))
    finally:
        sys.stdout, sys.stderr = oldout, olderr
        (directory/'stdout.log').write_text(stdout.getvalue())
        (directory/'stderr.log').write_text(stderr.getvalue())
    after = [file_record(p) for p in source_paths()]
    end = stamp()
    counts = counters(cases)
    passed = bool(cases) and not discovery_errors and before == after and not any(counts[k] for k in ('failures','errors','skipped'))
    receipt = dict(schema='s1-cpu-aggregate/v2', diagnostic=focus, suite_order=[s['suite'] for s in suites],
        invocation=invocation, start=start, end=end, elapsed_seconds=end['monotonic']-start['monotonic'],
        sources_before=before, sources_after=after, collected=collected, cases=cases, suites=suites,
        discovery_errors=discovery_errors, declarations=literal_declarations(),
        **counts, expected_exit_code=0 if passed else 1, passed=passed, run_directory=str(directory),
        boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(), interpreter=file_record(sys.executable),
        stdin=file_record(directory/'stdin.py'), runner=file_record(directory/'runner.py'),
        stdout=file_record(directory/'stdout.log'), stderr=file_record(directory/'stderr.log'))
    if not focus:
        try:
            validate_inner(receipt)
        except (ValueError, KeyError, TypeError, OSError) as exc:
            receipt.update(passed=False, expected_exit_code=1, contract_error=str(exc))
    (directory/'receipt.json').write_text(json.dumps(receipt, indent=2, allow_nan=False)+'\n')
    return receipt['expected_exit_code']


if __name__ == '__main__':
    raise SystemExit(main())
