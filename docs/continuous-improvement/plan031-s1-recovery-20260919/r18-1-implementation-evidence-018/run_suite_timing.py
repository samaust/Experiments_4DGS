"""Per-test elapsed timing for one vipe_benchmark suite (measurement only)."""
import datetime
import io
import json
import os
import sys
import time
import unittest
from unittest import mock

ROOT = '/home/auss/git_repos/samaust/Experiments_4DGS'
sys.path.insert(0, ROOT + '/scripts')
sys.path.insert(0, ROOT + '/tests')
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('MKL_NUM_THREADS', '1')
os.environ.setdefault('NUMEXPR_NUM_THREADS', '1')
os.environ.setdefault('VIPE_CPU_VALIDATION', '1')
os.environ.setdefault('OPENCV_FOR_THREADS_NUM', '1')
import tempfile
os.environ['S1_VALIDATION_RUN_DIRECTORY'] = tempfile.mkdtemp(prefix='s1-timing-run-')
# Official driver sets PYTHONPATH=ROOT/scripts (launch-049-exec.py:186) so child
# processes launched by tests can import the package.
os.environ['PYTHONPATH'] = ROOT + '/scripts'
try:
    os.setsid()  # official capture launches the runner in its own session (pid==pgid)
except OSError:
    pass


class TimedResult(unittest.TextTestResult):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.rows = []
        self._t0 = None

    def startTest(self, test):
        super().startTest(test)
        self._t0 = time.monotonic()

    def stopTest(self, test):
        elapsed = time.monotonic() - self._t0
        self.rows.append(dict(id=test.id(), elapsed_seconds=elapsed))
        super().stopTest(test)

    def addFailure(self, test, err):
        self.rows[-1]['outcome'] = 'failure'
        self.rows[-1]['msg'] = repr(err[1]).split('\n')[0][:200]
        super().addFailure(test, err)

    def addError(self, test, err):
        self.rows[-1]['outcome'] = 'error'
        self.rows[-1]['msg'] = repr(err[1]).split('\n')[0][:200]
        super().addError(test, err)

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)


def main():
    suite_name = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    out_path = sys.argv[3]
    start_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    t0 = time.monotonic()
    suite = unittest.TestLoader().discover(ROOT + '/tests', pattern=f'test_vipe_benchmark_{suite_name}.py')
    def flatten(s):
        for sub in s:
            if isinstance(sub, unittest.TestSuite):
                yield from flatten(sub)
            else:
                yield sub
    tests = list(flatten(suite))
    collected = len(tests)
    if limit:
        tests = tests[:limit]
    print(f'collected={collected} executed={len(tests)}', flush=True)
    stdout, stderr = io.StringIO(), io.StringIO()
    oldout, olderr = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = stdout, stderr
        with mock.patch('vipe_benchmark.supervisor.gpu_reading', side_effect=AssertionError('no gpu')), \
             mock.patch('vipe_benchmark.execution.gpu_reading', side_effect=AssertionError('no gpu')):
            result = unittest.TextTestRunner(verbosity=0, resultclass=TimedResult, stream=stderr).run(unittest.TestSuite(tests))
    finally:
        sys.stdout, sys.stderr = oldout, olderr
        open('/tmp/s1-timing/suite-stdout.log', 'w').write(stdout.getvalue()[-200000:])
        open('/tmp/s1-timing/suite-stderr.log', 'w').write(stderr.getvalue()[-200000:])
    rows = result.rows
    rows.sort(key=lambda r: -r['elapsed_seconds'])
    report = dict(suite=suite_name, collected=collected, executed=len(tests),
                  start_utc=start_utc, elapsed_seconds=time.monotonic() - t0,
                  failures=len(result.failures), errors=len(result.errors),
                  skips=len(getattr(result, 'skipped', [])), top=rows[:60],
                  all=rows)
    with open(out_path, 'w') as f:
        json.dump(report, f, indent=1)
    print(f'{suite_name}: executed={len(tests)} collected={collected} '
          f'failures={len(result.failures)} errors={len(result.errors)} '
          f'skips={len(getattr(result, 'skipped', []))} elapsed={time.monotonic()-t0:.1f}s')
    for r in rows[:25]:
        print(f"  {r['elapsed_seconds']:9.3f}s  {r['id']}  {r.get('outcome','') } {r.get('msg','')}")


if __name__ == '__main__':
    main()
