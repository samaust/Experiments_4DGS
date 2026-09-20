"""Static, typed CPU execution evidence contract; never imports test modules."""
import ast
import copy
import datetime
from functools import lru_cache
import json
import math
from pathlib import Path
import re

from .config import ROOT
from .files import file_record, read_json

SUITES = ('s1_semantics', 's1_recovery', 'backends', 'contracts', 'component_recovery',
          'execution', 'budgets', 'supervisor', 'review_annotations')
STDIN = ('import runpy\nimport sys\nsys.path.insert(0, "scripts")\n'
         'runpy.run_module("vipe_benchmark.s1_validation_runner", run_name="__main__", alter_sys=True, init_globals={"STDIN_PYTHON_ARGV": tuple(sys.argv)})\n')
ARGV = ['.local/envs/stg-colmap/bin/python', '-B', '-']
THREADS = ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS')
ENVIRONMENT = {**{key: '1' for key in THREADS}, 'VIPE_CPU_VALIDATION': '1', 'S1_HELPER_DIAGNOSTIC': None,
               'S1_RECEIPT_DIAGNOSTIC': None}
RUNNER = ROOT / 'scripts/vipe_benchmark/s1_validation_runner.py'
CAPTURE = ROOT / 'scripts/vipe_benchmark/s1_validation_capture.py'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def source_paths():
    return sorted([ROOT / 'scripts/basketball_vipe_benchmark.py', ROOT / 'scripts/basketball_vipe_worker.py',
                   ROOT / 'configs/vipe-alternatives/benchmark-v1.json',
                   *(ROOT / 'scripts/vipe_benchmark').glob('*.py'),
                   *(ROOT / 'tests').glob('test_vipe_benchmark_*.py')])


def strict_record(record):
    require(type(record) is dict and set(record) == {'path', 'sha256', 'bytes'}, 'strict file record required')
    require(type(record['path']) is str and type(record['bytes']) is int and record['bytes'] >= 0
            and type(record['sha256']) is str and re.fullmatch('[0-9a-f]{64}', record['sha256']), 'strict file record fields required')
    path = Path(record['path'])
    require('prompts' not in path.parts, 'forbidden evidence path')
    require(str(path.resolve()) == record['path'] and path.is_file(), 'canonical existing file record required')
    require(file_record(path) == record, 'stale file record bytes or hash')
    return record


def identity(parameters):
    require(type(parameters) is dict and all(type(k) is str for k in parameters), 'primitive parameter dictionary required')
    result = []
    for key, value in sorted(parameters.items()):
        kind = type(value)
        require(kind in (str, bool, int, float, type(None)), 'primitive parameter value required')
        require(kind is not float or math.isfinite(value), 'finite parameter value required')
        result.append((key, kind.__name__, value))
    return json.dumps(result, ensure_ascii=True, separators=(',', ':'), allow_nan=False)


def callback_id(parent, parameters):
    return parent + '::' + identity(parameters)


def parse_suite(text, module):
    """Return isolated declarations, reusing only successful exact-source parsing."""
    return copy.deepcopy(_parse_suite_cached(text, module))


@lru_cache(maxsize=16)
def _parse_suite_cached(text, module):
    """Reject ambiguous/dynamic declarations before Python can collapse dict keys."""
    try:
        tree = ast.parse(text)
        parents = {id(child): node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id == 'SUBTEST_CASES':
                parent = parents.get(id(node))
                if isinstance(parent, (ast.Attribute, ast.AugAssign, ast.Delete)):
                    raise ValueError('dynamic declaration mutation forbidden')
                if isinstance(parent, ast.Subscript) and isinstance(parent.ctx, (ast.Store, ast.Del)):
                    raise ValueError('dynamic declaration mutation forbidden')
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ('getattr', 'setattr'):
                if len(node.args) > 1 and isinstance(node.args[1], ast.Constant) and isinstance(node.args[1].value, str):
                    require(node.args[1].value != 'subTest' and not node.args[1].value.startswith('test_'),
                            'unsupported indirect parameterization')
        assignments = [n for n in ast.walk(tree) if isinstance(n, (ast.Assign, ast.AnnAssign))
                       and any(isinstance(t, ast.Name) and t.id == 'SUBTEST_CASES'
                               for t in (n.targets if isinstance(n, ast.Assign) else [n.target]))]
        require(len(assignments) == 1 and assignments[0] in tree.body
                and isinstance(assignments[0], ast.Assign) and len(assignments[0].targets) == 1,
                'exactly one module literal SUBTEST_CASES assignment required')
        value = assignments[0].value
        require(isinstance(value, ast.Dict), 'literal declaration dictionary required')
        for node in ast.walk(value):
            if isinstance(node, ast.Dict):
                require(all(k is not None for k in node.keys), 'declaration unpacking forbidden')
                keys = [ast.literal_eval(k) for k in node.keys]
                require(all(type(k) is str for k in keys) and len(keys) == len(set(keys)), 'duplicate declaration key')
        declared = ast.literal_eval(value)
        expected, parameterized = [], set()
        seen_classes = set()
        recognized_calls = set()
        for cls in sorted((n for n in tree.body if isinstance(n, ast.ClassDef)), key=lambda n: n.name):
            require(cls.name not in seen_classes, 'duplicate collected class')
            seen_classes.add(cls.name)
            for method in sorted((n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                                  and n.name.startswith('test_')), key=lambda n: n.name):
                name = f'{module}.{cls.name}.{method.name}'
                require(name not in expected and isinstance(method, ast.FunctionDef) and not method.decorator_list,
                        'unsupported dynamic collected method')
                expected.append(name)
                calls = [n for n in ast.walk(method) if isinstance(n, ast.Attribute) and n.attr == 'subTest']
                if calls:
                    parameterized.add(name)
                    for call in calls:
                        require(isinstance(call.value, ast.Name) and call.value.id == 'self'
                                and isinstance(parents.get(id(call)), ast.Call) and parents[id(call)].func is call,
                                'unsupported indirect subTest')
                        recognized_calls.add(id(call))
        require(all(id(n) in recognized_calls for n in ast.walk(tree)
                    if isinstance(n, ast.Attribute) and n.attr == 'subTest'), 'unsupported indirect parameterization')
        require(set(declared) == parameterized, 'missing or extraneous parameter declarations')
        for name, cases in declared.items():
            require(type(cases) in (tuple, list) and bool(cases), 'nonempty declaration sequence required')
            typed = [identity(case) for case in cases]
            require(len(typed) == len(set(typed)), 'duplicate declared typed tuple')
            declared[name] = list(cases)
        return expected, declared
    except (SyntaxError, TypeError, KeyError) as exc:
        raise ValueError('invalid literal declaration') from exc


def collection():
    expected, declared = [], {}
    for suite in SUITES:
        module = 'test_vipe_benchmark_' + suite
        methods, cases = parse_suite((ROOT / 'tests' / (module + '.py')).read_text(), module)
        require(not set(declared).intersection(cases), 'duplicate declaration across suites')
        expected.extend(methods)
        declared.update(cases)
    require(bool(expected) and len(expected) == len(set(expected)), 'unique nonempty collection required')
    return expected, declared


def required_cases():
    expected, declared = collection()
    return expected, set(declared)


def receipt_totals(cases):
    return {suite: counters([case for case in cases if case['id'].startswith('test_vipe_benchmark_' + suite + '.')])
            for suite in SUITES}


def counters(cases):
    return dict(tests_run=len(cases), subtests_run=sum(len(c['subtests']) for c in cases),
                failures=sum(c['status'] == 'failed' for c in cases),
                errors=sum(c['status'] == 'error' for c in cases), skipped=sum(c['status'] == 'skipped' for c in cases))


def counts_match(value, expected):
    require(all(type(value.get(k)) is int and value[k] >= 0 and value[k] == v for k, v in expected.items()),
            'exact integer receipt accounting required')


def utc(value):
    require(type(value) is str, 'UTC timestamp required')
    try:
        parsed = datetime.datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError('UTC timestamp malformed') from exc
    require(parsed.tzinfo is not None and parsed.utcoffset() == datetime.timedelta(0), 'UTC timezone required')
    return parsed


def number(value):
    require(type(value) in (int, float) and math.isfinite(value) and value >= 0, 'finite nonnegative timing required')
    return value


def interval(value):
    start, end = value.get('start', {}), value.get('end', {})
    sm, em = number(start.get('monotonic')), number(end.get('monotonic'))
    su, eu = utc(start.get('utc')), utc(end.get('utc'))
    require(sm <= em and su <= eu and abs(number(value.get('elapsed_seconds')) - (em - sm)) <= 1e-6,
            'inconsistent timing interval')
    return sm, em, su, eu


def contained(child, parent):
    require(parent[0] <= child[0] <= child[1] <= parent[1]
            and parent[2] <= child[2] <= child[3] <= parent[3], 'timing outside enclosing interval')


def sources_check(records):
    require(type(records) is list and records == [file_record(p) for p in source_paths()], 'exact current ordered sources required')
    for record in records:
        strict_record(record)


def environment_check(value):
    require(type(value) is dict and value == ENVIRONMENT, 'exact validation environment required')


def invocation_check(value, directory):
    require(type(value) is dict and value.get('launcher_argv') == ARGV and value.get('python_argv') == ['-']
            and value.get('runpy_argv') == [str(RUNNER.resolve())], 'exact launcher argv required')
    require(value.get('cwd') == str(ROOT.resolve()) and value.get('run_directory') == directory, 'invocation cwd/run directory mismatch')
    executable = str(ROOT / ARGV[0])
    require(value.get('executable') == executable and value.get('resolved_interpreter') == str(Path(executable).resolve()),
            'exact interpreter required')
    environment_check(value.get('environment'))
    require(value.get('thread_environment') == {k: '1' for k in THREADS}, 'exact thread environment required')


def artifact(value, key, directory, filename):
    record = strict_record(value.get(key))
    require(record['path'] == str(Path(directory) / filename), 'artifact path mismatch: ' + key)
    return Path(record['path']).read_bytes()


def validate_inner(value, sources=None):
    require(type(value) is dict and value.get('schema') == 's1-cpu-aggregate/v2' and value.get('diagnostic') is False,
            'complete v2 aggregate schema required')
    require(value.get('suite_order') == list(SUITES) and value.get('discovery_errors') == [], 'exact suite collection without discovery errors required')
    expected, declared = collection()
    require(value.get('collected') == expected, 'ordered method collection mismatch')
    supplied = value.get('declarations')
    require(type(supplied) is dict and set(supplied) == set(declared), 'complete declarations required')
    for name in declared:
        require(type(supplied[name]) is list and [identity(c) for c in supplied[name]] == [identity(c) for c in declared[name]],
                'typed declaration mismatch')
    cases = value.get('cases')
    require(type(cases) is list and [c.get('id') for c in cases] == expected, 'ordered executed methods mismatch')
    for case in cases:
        require(case.get('status') == 'passed' and type(case.get('subtests')) is list, 'passing method required')
        callbacks = case['subtests']
        wanted = declared.get(case['id'], [])
        require(len(callbacks) == len(wanted), 'callback multiplicity mismatch')
        for sub, parameters in zip(callbacks, wanted):
            require(identity(sub.get('parameters')) == identity(parameters), 'typed callback parameters mismatch')
            require(sub.get('id') == callback_id(case['id'], parameters), 'canonical callback ID mismatch')
            require(sub.get('status') == 'passed', 'passing callback required')
    counts_match(value, counters(cases))
    require(all(value[k] == 0 for k in ('failures', 'errors', 'skipped')) and value.get('passed') is True
            and type(value.get('expected_exit_code')) is int and value['expected_exit_code'] == 0, 'passing aggregate required')
    sources_check(value.get('sources_before'))
    sources_check(value.get('sources_after'))
    require(value['sources_before'] == value['sources_after'] and (sources is None or sources == value['sources_before']), 'source snapshots differ')
    directory = value.get('run_directory')
    require(type(directory) is str and str(Path(directory).resolve()) == directory and Path(directory).is_dir(), 'canonical run directory required')
    require(artifact(value, 'stdin', directory, 'stdin.py') == STDIN.encode(), 'prescribed stdin bytes required')
    require(artifact(value, 'runner', directory, 'runner.py') == RUNNER.read_bytes(), 'current runner snapshot required')
    artifact(value, 'stdout', directory, 'stdout.log')
    artifact(value, 'stderr', directory, 'stderr.log')
    require(strict_record(value.get('interpreter')) == file_record(ROOT / ARGV[0]), 'interpreter file mismatch')
    invocation_check(value.get('invocation'), directory)
    require(type(value.get('boot_id')) is str and re.fullmatch('[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', value['boot_id']), 'boot identity required')
    bounds = interval(value)
    suites = value.get('suites')
    require(type(suites) is list and [s.get('suite') for s in suites] == list(SUITES), 'ordered suite receipts required')
    previous = (bounds[0], bounds[2])
    for suite in suites:
        rows = [c for c in cases if c['id'].startswith('test_vipe_benchmark_' + suite['suite'] + '.')]
        require(suite.get('collected') == [c['id'] for c in rows], 'suite collected methods mismatch')
        counts_match(suite, counters(rows))
        require(suite.get('invocation') == value['invocation'], 'suite invocation mismatch')
        child = interval(suite)
        contained(child, bounds)
        require(previous[0] <= child[0] and previous[1] <= child[2], 'suite intervals overlap')
        previous = (child[1], child[3])
    return value


def validate_execution(value, receipt_record, inner):
    require(type(value) is dict and value.get('schema') == 's1-cpu-execution/v1', 'complete execution schema required')
    require(value.get('receipt') == strict_record(receipt_record), 'execution/receipt link mismatch')
    require(type(value.get('returncode')) is int and value['returncode'] == inner['expected_exit_code'] == 0
            and value.get('timed_out') is False and value.get('wait_completed') is True, 'actual successful wait completion required')
    require(type(value.get('child_pid')) is int and value['child_pid'] > 0, 'child PID required')
    require(value.get('requested_argv') == ARGV and value.get('cwd') == str(ROOT.resolve()), 'exact outer argv/cwd required')
    environment_check(value.get('environment'))
    directory = inner['run_directory']
    require(value.get('run_directory') == directory, 'execution run directory mismatch')
    for key in ('stdin', 'runner', 'interpreter'):
        require(strict_record(value.get(key)) == inner[key], 'execution artifact mismatch: ' + key)
    require(artifact(value, 'capture', directory, 'capture.py') == CAPTURE.read_bytes(), 'current capture snapshot required')
    require(artifact(value, 'stdout', directory, 'process-stdout.log') == Path(inner['stdout']['path']).read_bytes()
            and artifact(value, 'stderr', directory, 'process-stderr.log') == Path(inner['stderr']['path']).read_bytes(), 'process/runner log bytes differ')
    sources_check(value.get('sources_before'))
    sources_check(value.get('sources_after'))
    require(value['sources_before'] == value['sources_after'] == inner['sources_before'], 'outer source snapshots differ')
    require(value.get('boot_id') == inner['boot_id'], 'execution boot mismatch')
    bounds = interval(value)
    contained(interval(inner), bounds)
    require(type(value.get('timeout_seconds')) is int and 0 < value['timeout_seconds'] <= 300
            and value['elapsed_seconds'] <= value['timeout_seconds'], 'execution invocation cap exceeded')
    return value


def validate_wrapper(value, amendment, configuration):
    require(type(value) is dict and value.get('schema') == 'plan031-s1-recovery-validation/v2'
            and value.get('status') == 'passed' and value.get('semantic_amendment') == amendment
            and value.get('configuration') == configuration, 'complete current amendment-bound source validation required')
    for key in ('semantic_amendment', 'configuration', 'plan', 'baseline', 'baseline_correction'):
        strict_record(value.get(key))
    for key in ('aggregate_passed', 'receipt_milestone_complete', 'implementation_acceptance_complete', 'ready_for_live_admission', 'objective_complete'):
        require(type(value.get(key)) is bool, 'separate acceptance flags required')
    require(value['aggregate_passed'], 'aggregate pass required')
    sources_check(value.get('sources'))
    diff = value.get('diff_check', {})
    require(type(diff.get('exit_code')) is int and diff['exit_code'] == 0 and diff.get('command') == 'git diff --check'
            and type(diff.get('stdout')) is str and type(diff.get('stderr')) is str, 'exact clean diff check required')
    require('aggregate' not in value, 'alternate aggregate document forbidden')
    tests = value.get('tests')
    require(type(tests) is list and len(tests) == 1 and type(tests[0]) is dict
            and set(tests[0]) == {'receipt', 'execution'}, 'one bound receipt/execution entry required')
    inner_record = strict_record(tests[0]['receipt'])
    outer_record = strict_record(tests[0]['execution'])
    inner = validate_inner(read_json(inner_record['path']), value['sources'])
    validate_execution(read_json(outer_record['path']), inner_record, inner)
    return value
