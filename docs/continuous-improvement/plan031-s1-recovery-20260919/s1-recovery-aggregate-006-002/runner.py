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
from .s1_recovery import ROOT, SUITES, source_paths

STDIN = ('import runpy\nimport sys\nsys.path.insert(0, "scripts")\n'
         'runpy.run_module("vipe_benchmark.s1_validation_runner", run_name="__main__", alter_sys=True, init_globals={"STDIN_PYTHON_ARGV": tuple(sys.argv)})\n')


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
        self.current['subtests'].append(dict(id=subtest.id(), parameters=parameters, status=status))
        if err is not None:
            self.current['status'] = status
        super().addSubTest(test, subtest, err)


def ids(suite):
    result = []
    for test in suite:
        result.extend(ids(test) if isinstance(test, unittest.TestSuite) else [test.id()])
    return result


def literal_declarations():
    declarations = {}
    for name in SUITES:
        tree = ast.parse((ROOT/'tests'/f'test_vipe_benchmark_{name}.py').read_text())
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'HELPER_CASES' for t in node.targets):
                declarations.update(ast.literal_eval(node.value))
    return declarations


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
    expected = ROOT/'.local/envs/stg-colmap/bin/python'
    if Path(sys.executable).resolve() != expected.resolve():
        raise RuntimeError('wrong validation interpreter')
    if any(os.environ.get(k) != '1' for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS')):
        raise RuntimeError('thread limits must be one')
    os.environ['VIPE_CPU_VALIDATION'] = '1'
    focus = os.environ.get('S1_HELPER_DIAGNOSTIC') == '1'
    base = ROOT/'docs/continuous-improvement/plan031-s1-recovery-20260919'
    label = 'diagnostic' if focus else 'aggregate'
    for number in range(1, 1000):
        directory = base/f's1-recovery-{label}-006-{number:03d}'
        if not directory.exists():
            directory.mkdir()
            break
    (directory/'stdin.py').write_text(STDIN)
    (directory/'runner.py').write_bytes(Path(__file__).read_bytes())
    start = stamp()
    before = [file_record(p) for p in source_paths()]
    proc_argv = Path('/proc/self/cmdline').read_bytes().split(b'\0')[:-1]
    invocation = dict(launcher_argv=[v.decode() for v in proc_argv], python_argv=list(globals().get('STDIN_PYTHON_ARGV', ())),
        runpy_argv=list(sys.argv), executable=sys.executable, resolved_interpreter=str(Path(sys.executable).resolve()),
        thread_environment={k:os.environ.get(k) for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')})
    cases, collected, suites, discovery_errors = [], [], [], []
    stdout, stderr = io.StringIO(), io.StringIO()
    oldout, olderr = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = Tee(oldout, stdout), Tee(olderr, stderr)
    try:
        with patch('vipe_benchmark.supervisor.gpu_reading', side_effect=AssertionError('unexpected GPU probe')), \
             patch('vipe_benchmark.execution.gpu_reading', side_effect=AssertionError('unexpected GPU probe')):
            for name in (('supervisor',) if focus else SUITES):
                loader = unittest.TestLoader()
                suite = loader.discover(str(ROOT/'tests'), pattern=f'test_vipe_benchmark_{name}.py')
                if focus:
                    suite = unittest.TestSuite(t for group in suite for cls in group for t in cls
                        if t.__class__.__name__ == 'HelperIntegrationTests')
                discovered = ids(suite)
                collected.extend(discovered)
                discovery_errors.extend(loader.errors)
                suite_start = stamp()
                result = unittest.TextTestRunner(verbosity=2, resultclass=Result, stream=sys.stderr).run(suite)
                suite_end = stamp()
                cases.extend(result.cases)
                suites.append(dict(suite=name, start=suite_start, end=suite_end,
                    elapsed_seconds=suite_end['monotonic']-suite_start['monotonic'], invocation=invocation,
                    collected=discovered, tests_run=result.testsRun, failures=len(result.failures),
                    errors=len(result.errors), skipped=len(result.skipped),
                    subtests_run=sum(len(c['subtests']) for c in result.cases)))
    finally:
        sys.stdout, sys.stderr = oldout, olderr
        (directory/'stdout.log').write_text(stdout.getvalue())
        (directory/'stderr.log').write_text(stderr.getvalue())
    after = [file_record(p) for p in source_paths()]
    end = stamp()
    declarations = literal_declarations()
    actual = {c['id']:tuple(s['parameters'] for s in c['subtests']) for c in cases}
    declaration_checks = {key: actual.get(key) == value for key, value in declarations.items()}
    counts = {k:sum(s[k] for s in suites) for k in ('tests_run','failures','errors','skipped','subtests_run')}
    passed = (bool(cases) and not discovery_errors and before == after and all(declaration_checks.values())
              and not any(counts[k] for k in ('failures','errors','skipped'))
              and collected == [c['id'] for c in cases] and all(c['status']=='passed' for c in cases))
    receipt = dict(schema='s1-cpu-aggregate/v1', diagnostic=focus, suite_order=[s['suite'] for s in suites],
        invocation=invocation, start=start, end=end, elapsed_seconds=end['monotonic']-start['monotonic'],
        sources_before=before, sources_after=after, collected=collected, cases=cases, suites=suites,
        discovery_errors=discovery_errors, declared_helper_cases=declarations, declaration_checks=declaration_checks,
        **counts, exit_code=0 if passed else 1, passed=passed,
        stdin=file_record(directory/'stdin.py'), runner=file_record(directory/'runner.py'),
        stdout=file_record(directory/'stdout.log'), stderr=file_record(directory/'stderr.log'),
        open_acceptance_gates=['Complete nine-suite literal declarations and strict production receipt metadata guards remain open.'])
    (directory/'receipt.json').write_text(json.dumps(receipt, indent=2, allow_nan=False)+'\n')
    print('RECEIPT', directory/'receipt.json', 'PASS' if passed else 'FAIL')
    return receipt['exit_code']


if __name__ == '__main__':
    raise SystemExit(main())
