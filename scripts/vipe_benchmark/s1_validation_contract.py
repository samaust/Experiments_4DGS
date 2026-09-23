"""Static, typed CPU execution evidence contract; never imports test modules."""
import ast
import copy
import datetime
from functools import lru_cache
import json
import hashlib
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
    require(type(value) is dict and value.get('schema') in ('s1-cpu-execution/v1','s1-cpu-execution/v2'), 'complete execution schema required')
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
    if value['schema']=='s1-cpu-execution/v1':
        require('execution_mode' not in value and 'wait' not in value and 'launch_note' not in value,'legacy timed mode cannot claim no-timeout provenance')
        require(type(value.get('timeout_seconds')) is int and 0 < value['timeout_seconds'] <= 300
                and value['elapsed_seconds'] <= value['timeout_seconds'], 'execution invocation cap exceeded')
    else:
        require(value.get('execution_mode')=='no-timeout' and 'timeout_seconds' in value and value['timeout_seconds'] is None,'explicit null no-timeout mode required')
        wait=value.get('wait')
        require(type(wait) is dict and type(wait.get('pid')) is int and type(wait.get('returncode')) is int and wait.get('completed') is True,'typed successful wait evidence required')
        require(value.get('wait')==dict(method='Popen.wait',timeout_seconds=None,pid=value['child_pid'],returncode=value['returncode'],completed=True),'actual unbounded wait evidence required')
        note=no_timeout_launch(value.get('launch_note'),directory)
        validate_creation(value.get('creation'),note,value['child_pid'],value['boot_id'])

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



def _identity_record(value, *, ancestor=False):
    require(type(value) is dict,'complete process identity required')
    base=('boot_id','pid','ppid','pgid','start_ticks')
    require(set(value)==set(base)|{'threads','threads_before','threads_after','process_before','process_after'},'exact process identity fields')
    def process(item):
        require(type(item) is dict and set(item)==set(base),'exact nested process fields')
        require(type(item['boot_id']) is str and re.fullmatch('[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',item['boot_id']),'boot identity required')
        for key in ('pid','pgid','start_ticks'):require(type(item[key]) is int and item[key]>0,'positive process identity: '+key)
        require(type(item['ppid']) is int and item['ppid']>=0,'parent identity required')
    expected={key:value[key] for key in base};process(expected)
    for key in ('process_before','process_after'):process(value[key])
    require(value['process_before']==value['process_after']==expected,'stable process identity required')
    for key in ('threads','threads_before','threads_after'):
        tasks=value[key];require(type(tasks) is list and tasks,'complete thread identities required')
        tids=[]
        for task in tasks:
            require(type(task) is dict and set(task)=={'boot_id','pid','process_start_ticks','tid','start_ticks'},'exact thread identity fields')
            require(type(task['boot_id']) is str and task['boot_id']==value['boot_id'],'thread boot identity')
            for field in ('pid','process_start_ticks','tid','start_ticks'):require(type(task[field]) is int and task[field]>0,'exact positive thread identity: '+field)
            require(task['pid']==value['pid'] and task['process_start_ticks']==value['start_ticks'],'thread process binding')
            require(task['start_ticks']>=value['start_ticks'],'thread birth identity')
            tids.append(task['tid'])
        require(tids==sorted(set(tids)) and value['pid'] in tids,'unique sorted complete task census')
    if not ancestor:require(value['threads']==value['threads_before']==value['threads_after'],'stable thread identities around enumeration')
    return value


def identity_record(value):
    # Every root/owned creation, census and retirement caller stays strict.
    return _identity_record(value)


def identity_projection(root, ancestors):
    """Trusted chain role: project only actual non-root preexisting ancestors."""
    identity_record(root)
    require(type(ancestors) is list and ancestors,'terminated ancestry required')
    cursor=root['ppid'];seen={root['pid']};projected=[]
    for row in ancestors:
        _identity_record(row,ancestor=True)
        require(row['pid']==cursor and cursor not in seen and row['boot_id']==root['boot_id'] and row['start_ticks']<=root['start_ticks'],'ancestry identity/age/reuse')
        seen.add(cursor);cursor=row['ppid']
        projected.append({key:value for key,value in row.items() if key not in ('threads','threads_before','threads_after')})
    require(cursor==0,'ancestry termination')
    return dict(ownership_root=root,preexisting_ancestors=projected)


def launch_output_paths(directory,kind,index):
    run=ROOT/'docs/resolve-blocker/plan031-progress-20260922'
    prefix=run/('driver-049-'+kind+'-'+str(index).zfill(3))
    return [str(Path(directory)/name) for name in ('receipt.json','execution.json','process-stdout.log','process-stderr.log','stdout.log','stderr.log','stdin.py','runner.py','capture.py')]+[str(prefix)+ending for ending in ('-exec-start.json','-stdout.log','-stderr.log')]


def validate_creation(value,note,child_pid,boot):
    require(type(value) is dict and set(value)=={'before','after','retired','child','retirement','authority','cpu_bound'},'complete creation and retirement evidence required')
    require(value['authority']==file_record(note['admission']['path']) and value['cpu_bound']=='B+max(1,H)≤8','creation Main authority')
    root=identity_record(note['ownership_root']);child=identity_record(value['child'])
    require(child['pid']==child_pid and child['ppid']==root['pid'] and child['boot_id']==boot==root['boot_id'] and child['start_ticks']>=root['start_ticks'],'creation child full identity')
    def snapshot(item):
        require(type(item) is dict and set(item)=={'root_pid','processes','B','H','charge','complete'},'exact creation census')
        require(item['complete'] is True and type(item['root_pid']) is int and item['root_pid']==root['pid'],'complete root census')
        records=item['processes'];require(type(records) is list and records,'creation process census required')
        for row in records:identity_record(row);require(row['boot_id']==boot,'creation boot mismatch')
        ids=[row['pid'] for row in records];require(ids==sorted(set(ids)),'unique creation identities')
        require(root in records,'creation root changed')
        owned={root['pid']}
        for _ in records:owned.update(row['pid'] for row in records if row['ppid'] in owned)
        require(owned==set(ids),'unbound creation descendant')
        B=sum(len(row['threads']) for row in records)
        require(type(item['B']) is int and item['B']==B and type(item['H']) is int and item['H']==0 and type(item['charge']) is int and item['charge']==B+1<=8,'creation exact capacity')
        return records
    before=snapshot(value['before']);after=snapshot(value['after']);retired=snapshot(value['retired'])
    require(before==[root] and after==sorted([root,child],key=lambda row:row['pid']) and retired==before,'exact before/after/retired creation identity set')
    require(value['before']['B']+2<=8,'new child plus reserve before creation')
    retirement=value['retirement']
    require(type(retirement) is dict and set(retirement)=={'identity','method','returncode','completed','absent_after'},'exact retirement fields')
    identity_record(retirement['identity'])
    require(type(retirement['method']) is str and type(retirement['returncode']) is int and type(retirement['completed']) is bool and type(retirement['absent_after']) is bool,'exact retirement primitive types')
    require(value['retirement']==dict(identity=child,method='matching Popen.wait',returncode=0,completed=True,absent_after=True),'exact matching child retirement')


def session_json(path):
    """Admission evidence rejects duplicate keys and nonfinite JSON at every depth."""
    def pairs(items):
        result={}
        for key,value in items:
            require(key not in result,'duplicate session evidence key')
            result[key]=value
        return result
    def invalid(value):raise ValueError('nonfinite session evidence: '+value)
    value=json.loads(Path(path).read_text(),object_pairs_hook=pairs,parse_constant=invalid)
    def finite(item):
        if type(item) is float:require(math.isfinite(item),'finite session JSON number')
        elif type(item) is dict:
            for child in item.values():finite(child)
        elif type(item) is list:
            for child in item:finite(child)
    finite(value)
    return value


def session_proof(reference,kind,index,driver,identity_request,admission_path,reason):
    """Trusted Main transcript correlation; never cross-namespace kernel attestation."""
    import shlex
    run=ROOT/'docs/resolve-blocker/plan031-progress-20260922'
    require(kind in ('diagnostic','aggregate') and type(index) is int and index>0,'session kind/index')
    suffix=kind+'-'+str(index).zfill(3)
    proof_record=strict_record(reference)
    require(proof_record['path']==str(run/('main-session-proof-049-'+suffix+'.json')),'fixed session proof path')
    proof=session_json(proof_record['path'])
    fields={'schema','proof_mode','kind','index','session_id','driver','identity_request','admission_path','tool_events','readiness_event','readiness_line','readiness_line_sha256','user_authorization','correction','cross_namespace_kernel_verified'}
    require(type(proof) is dict and set(proof)==fields,'exact session proof fields')
    require(proof['schema']=='plan049-session-proof/v1' and proof['proof_mode']=='session-bound/v1' and proof['cross_namespace_kernel_verified'] is False,'explicit session trust model')
    require(proof['kind']==kind and type(proof['index']) is int and proof['index']==index,'proof kind/index correlation')
    handle=proof['session_id'];require(type(handle) is int and handle>0,'opaque exact session handle')
    require(strict_record(proof['driver'])==driver and strict_record(proof['identity_request'])==identity_request,'session driver/request binding')
    require(identity_request['path']==str(run/('launch-identity-049-'+suffix+'.json')),'fixed session identity path')
    require(proof['admission_path']==admission_path==str(run/('launch-admission-049-'+suffix+'.json')),'fixed session admission path')
    authorization=strict_record(proof['user_authorization']);correction=strict_record(proof['correction'])
    require(authorization['path']==str(run/'authorization-049-session-proof-001.md') and correction['path']==str(run/'plan049-correction-008.md'),'fixed session authorization/correction')
    require(authorization['sha256']=='6ee2d0f899c6ee20de96415079d9aa07900b51f2321ef37d20af5e7e171bd755' and correction['sha256']=='e68129133349fbbecc25e725025c0cda833c7ab149aaacad0ff05ead4737cf91','authorized session trust amendment bytes')
    request=session_json(identity_request['path'])
    request_fields={'schema','kind','index','driver','ownership_root','preexisting_ancestors','ancestry_terminal','retained_wrappers','output_paths'}
    require(type(request) is dict and set(request)==request_fields,'exact session identity request fields')
    require(request['schema']=='plan049-prospective-identity/v1' and request['kind']==kind and type(request['index']) is int and request['index']==index and strict_record(request['driver'])==driver,'session identity correlation')
    root=identity_record(request['ownership_root']);ancestors=request['preexisting_ancestors']
    require(type(ancestors) is list and ancestors,'session full ancestry')
    cursor=root['ppid'];seen={root['pid']}
    for row in ancestors:
        _identity_record(row,ancestor=True)
        require(row['pid']==cursor and cursor not in seen and row['boot_id']==root['boot_id'] and row['start_ticks']<=root['start_ticks'],'session ancestry chain')
        seen.add(cursor);cursor=row['ppid']
    terminal=request['ancestry_terminal']
    require(type(terminal) is dict and set(terminal)=={'pid','ppid'} and type(terminal['pid']) is int and type(terminal['ppid']) is int and terminal==dict(pid=ancestors[-1]['pid'],ppid=0) and cursor==0,'session ancestry terminal')
    require(type(request['retained_wrappers']) is list and request['retained_wrappers']==[],'session wrappers')
    require(type(request['output_paths']) is list and all(type(p) is str for p in request['output_paths']),'session output paths')
    events=proof['tool_events'];require(type(events) is list and len(events)>=3,'two mandatory live polls')
    require(type(proof['readiness_event']) is int and 0<=proof['readiness_event']<len(events)-2,'readiness precedes mandatory live polls')
    line=proof['readiness_line'];require(type(line) is str and '\n' not in line and '\r' not in line,'complete readiness line')
    require(type(proof['readiness_line_sha256']) is str and hashlib.sha256(line.encode()).hexdigest()==proof['readiness_line_sha256'],'readiness line hash')
    # Parse through the same duplicate-key rejecting parser without normalizing output.
    def unique(items):
        result={}
        for key,value in items:
            require(key not in result,'duplicate readiness key');result[key]=value
        return result
    announcement=json.loads(line,object_pairs_hook=unique)
    require(type(announcement) is dict and set(announcement)=={'awaiting_main_admission','identity_request'} and announcement['awaiting_main_admission']==admission_path and strict_record(announcement['identity_request'])==identity_request,'readiness identity correlation')
    previous=None;output='';ends=[]
    def stamp(value):
        require(type(value) is dict and set(value)=={'utc','monotonic'},'exact event stamp')
        require(type(value['utc']) is str,'event UTC text')
        try:utc=datetime.datetime.fromisoformat(value['utc'])
        except ValueError:raise ValueError('event UTC') from None
        require(utc.tzinfo is not None and utc.utcoffset()==datetime.timedelta(0),'event UTC timezone')
        mono=value['monotonic'];require(type(mono) in (int,float) and math.isfinite(mono) and mono>=0,'event finite monotonic')
        return utc,mono
    for ordinal,event_record in enumerate(events):
        strict_record(event_record)
        require(event_record['path']==str(run/('main-session-049-'+suffix+'-event-'+str(ordinal).zfill(3)+'.json')),'fixed contiguous event path')
        event=session_json(event_record['path'])
        require(type(event) is dict and set(event)=={'schema','kind','index','ordinal','role','tool','arguments','result','started','returned','output_sha256'},'exact tool event fields')
        role='start' if ordinal==0 else 'pre_admission' if ordinal==len(events)-2 else 'at_admission' if ordinal==len(events)-1 else 'readiness'
        require(event['schema']=='plan049-session-tool-event/v1' and event['kind']==kind and type(event['index']) is int and event['index']==index and type(event['ordinal']) is int and event['ordinal']==ordinal and event['role']==role,'ordered event correlation')
        start=stamp(event['started']);end=stamp(event['returned'])
        require(all(a<=b for a,b in zip(start,end)) and (previous is None or all(a<=b for a,b in zip(previous,start))),'ordered tool stamps');previous=end
        args=event['arguments'];result=event['result']
        require(type(args) is dict and type(result) is dict,'verbatim tool objects')
        require(type(result.get('session_id')) is int and result['session_id']==handle and result.get('exit_code') is None and not result.get('isError') and not result.get('error'),'affirmative live tool session')
        require(type(result.get('output')) is str and type(event['output_sha256']) is str and hashlib.sha256(result['output'].encode()).hexdigest()==event['output_sha256'],'exact tool output hash')
        require(not result.get('truncated') and not result.get('output_truncated') and 'truncated' not in result['output'].lower(),'untruncated tool output')
        if ordinal==0:
            require(event['tool']=='exec_command' and type(args.get('cmd')) is str,'session start command')
            expected_command=shlex.join(['exec',str(ROOT/ARGV[0]),'-B',driver['path'],kind,str(index),reason])
            require(args['cmd']==expected_command,'exact sole driver exec command')
            # Token equivalence cannot prove shell structure (exec followed by
            # a newline is two commands). Bind exact quoting and shell options.
            fixed_start=dict(shell='/bin/bash',login=False,workdir=str(ROOT),tty=True,
                             sandbox_permissions='require_escalated',yield_time_ms=1000,
                             justification='Run the reviewed Plan049 CPU-only '+kind+' after the exact AF_UNIX datagram socket retry succeeded.')
            require(set(args)==set(fixed_start)|{'cmd','max_output_tokens','prefix_rule'},'exact start argument fields')
            for key,expected_value in fixed_start.items():
                require(type(args[key]) is type(expected_value) and args[key]==expected_value,'exact start argument: '+key)
            require(type(args['prefix_rule']) is list and all(type(value) is str for value in args['prefix_rule']) and args['prefix_rule']==['exec',str(ROOT/ARGV[0]),'-B',driver['path']],'exact start argument: prefix_rule')
            require(type(args['max_output_tokens']) is int and args['max_output_tokens']>0,'exact positive start output budget')
        else:
            require(event['tool']=='write_stdin' and type(args.get('session_id')) is int and args['session_id']==handle and args.get('chars')=='' and type(args.get('chars')) is str,'same-session empty live poll')
        require(type(args.get('yield_time_ms')) is int and 0<args['yield_time_ms']<=60000,'responsive poll yield')
        output+=result['output'];ends.append(len(output))
    require(output==line+'\n' or output==line+'\r\n','sole complete readiness announcement; unexplained output rejected')
    complete=next((ordinal for ordinal,end in enumerate(ends) if end>=len(output)),None)
    require(complete==proof['readiness_event'],'readiness event correlation')
    return proof


def no_timeout_launch(reference,directory,*,diagnostic=False):
    """Fresh fixed Plan049 authority; the environment cannot choose a plan."""
    run=ROOT/'docs/resolve-blocker/plan031-progress-20260922'
    record=strict_record(reference);note=session_json(record['path'])
    require(note.get('schema')=='plan049-prospective-launch/v1' and note.get('execution_mode')=='no-timeout'
            and 'timeout_seconds' in note and note['timeout_seconds'] is None,'Plan049 no-timeout launch required')
    require(note.get('run_directory')==directory and note.get('kind')==('diagnostic' if diagnostic else 'aggregate'),'no-timeout launch directory/kind')
    dispatch_record=file_record(run/'implementation-dispatch-049.json');dispatch=read_json(dispatch_record['path'])
    require(dispatch.get('schema')=='plan049-implementation-dispatch/v1','fixed Plan049 dispatch schema')
    require(dispatch['authorization']['invocation_timeout'] is None and dispatch['authorization']['operational_duration_ceiling_seconds'] is None,'no-timeout authorization required')
    require(dispatch['plan']['path']==str(ROOT/'plans/plan_049.md') and file_record(ROOT/'plans/plan_049.md')['sha256']==dispatch['plan']['sha256'],'fixed Plan049 authority')
    status=strict_record(dispatch['implementation_status_snapshot']);authorization=strict_record(dispatch['authorization_note'])
    require(status['path']==str(run/'implementation-status-049.md') and authorization['path']==str(run/'authorization-049.md'),'fixed Plan049 status/authorization')
    driver=strict_record(note.get('driver'));require(driver['path']==str(run/'launch-049-exec.py'),'fixed Plan049 driver')
    bindings=note.get('bindings');require(type(bindings) is list,'launch bindings required')
    for binding in bindings:strict_record(binding)
    require(dispatch_record in bindings and status in bindings and authorization in bindings
            and file_record(ROOT/'plans/plan_049.md') in bindings,'complete fixed Plan049 launch bindings')
    sources_check(note.get('sources'))
    require(note.get('cpu_bound')=='B+max(1,H)≤8','exact owned CPU cap')
    expected=[str(ROOT/ARGV[0]),'-B','-m','vipe_benchmark.s1_validation_capture',directory,'--no-timeout']
    if diagnostic:expected.append('--diagnostic')
    require(note.get('command')==expected,'exact no-timeout capture command')
    admission_record=strict_record(note.get('admission'))
    require(admission_record in bindings,'bound main admission required')
    admission=session_json(admission_record['path'])
    require(type(admission) is dict,'Main admission dictionary')
    require(admission.get('approved') is True and admission.get('cleanup_resolved') is True,'approved resolved main admission required')
    require(admission.get('execution_mode')=='no-timeout' and 'timeout_seconds' in admission and admission['timeout_seconds'] is None,'admission no-timeout mode')
    require(admission.get('sources')==note['sources'] and admission.get('source_paths')==[r['path'] for r in note['sources']],'admission complete source binding')
    for key,note_key in [('kind','kind'),('index','attempt_index'),('reason','reason'),('counts_before','counts_before')]:
        require(admission.get(key)==note.get(note_key),'admission launch identity: '+key)
    require(type(admission.get('index')) is int and admission['index']>0 and type(admission.get('reason')) is str and admission['reason'].strip(),'positive no-ceiling attempt/reason')
    command_bindings=admission.get('bindings',{})
    require(type(command_bindings) is dict,'Main admission binding dictionary')
    require(command_bindings.get('driver')==driver and command_bindings.get('command')==expected and command_bindings.get('run_directory')==directory,'admission driver/command/output binding')
    require(command_bindings.get('plan')==file_record(ROOT/'plans/plan_049.md') and command_bindings.get('dispatch')==dispatch_record and command_bindings.get('status')==status and command_bindings.get('authorization')==authorization,'admission fixed authority binding')
    require(command_bindings.get('stdin')==dict(bytes=len(STDIN.encode()),sha256=hashlib.sha256(STDIN.encode()).hexdigest()),'admission exact stdin')
    settings={key:'1' for key in (*THREADS,'OPENCV_FOR_THREADS_NUM','VIPE_CPU_VALIDATION')}
    settings['PYTHONPATH']=str(ROOT/'scripts')
    require(command_bindings.get('environment')==note.get('environment')==settings,'exact admission/launch environment')
    require(note.get('cwd')==str(ROOT) and note.get('unset_environment')==['S1_HELPER_DIAGNOSTIC','S1_RECEIPT_DIAGNOSTIC'],'exact launch cwd/unset environment')
    require(note.get('stdin_identity')==dict(bytes=len(STDIN.encode()),sha256=hashlib.sha256(STDIN.encode()).hexdigest(),content=STDIN),'exact launch stdin identity')
    require(set(command_bindings)=={'plan','dispatch','status','authorization','ancestor_authorization','driver','command','environment','stdin','run_directory','identity_request','addenda','session_proof','ownership_root','preexisting_ancestors','ancestry_terminal','retained_wrappers','output_paths'},'exact admission binding fields')
    def typed_binding(value):
        require(type(value) is dict,'identity binding dictionary')
        identity_record(value.get('ownership_root'))
        ancestors=value.get('preexisting_ancestors')
        require(type(ancestors) is list and ancestors,'typed ancestry list')
        identity_projection(value['ownership_root'],ancestors)
        terminal=value.get('ancestry_terminal')
        require(type(terminal) is dict and set(terminal)=={'pid','ppid'} and type(terminal['pid']) is int and terminal['pid']>0 and type(terminal['ppid']) is int and terminal['ppid']==0,'typed ancestry terminal')
        require(type(value.get('retained_wrappers')) is list and value['retained_wrappers']==[],'typed retained wrapper list')
        require(type(value.get('output_paths')) is list and all(type(path) is str for path in value['output_paths']),'typed output paths')
    typed_binding(note);typed_binding(command_bindings)
    root=identity_record(note.get('ownership_root'))
    ancestors=note.get('preexisting_ancestors');require(type(ancestors) is list and ancestors,'terminated ancestry required')
    cursor=root['ppid'];seen={root['pid']}
    for row in ancestors:
        _identity_record(row,ancestor=True)
        require(row['pid']==cursor and cursor not in seen and row['boot_id']==root['boot_id'] and row['start_ticks']<=root['start_ticks'],'ancestry identity/age/reuse')
        seen.add(cursor);cursor=row['ppid']
    require(cursor==0 and note.get('ancestry_terminal')==dict(pid=ancestors[-1]['pid'],ppid=0),'ancestry termination')
    require(note.get('retained_wrappers')==[],'unvalidated retained wrapper')
    outputs=launch_output_paths(directory,note['kind'],note['attempt_index'])
    require(note.get('output_paths')==outputs,'complete exact output paths')
    for key in ('ownership_root','preexisting_ancestors','ancestry_terminal','retained_wrappers','output_paths'):
        require(command_bindings.get(key)==note.get(key),'Main prebound identity: '+key)
    identity_request=strict_record(command_bindings.get('identity_request'))
    require(identity_request in bindings,'Main prospective identity request binding')
    request=session_json(identity_request['path'])
    typed_binding(request)
    require(request==dict(schema='plan049-prospective-identity/v1',kind=note['kind'],index=note['attempt_index'],driver=driver,**{key:note[key] for key in ('ownership_root','preexisting_ancestors','ancestry_terminal','retained_wrappers','output_paths')}),'exact pre-admission identity request')
    addenda=[file_record(run/name) for name in ('plan049-correction-001.md','plan049-correction-002.md','plan049-correction-003.md','plan049-correction-004.md','plan049-correction-005.md','plan049-correction-006.md','plan049-correction-007.md','plan049-correction-008.md','plan049-correction-009.md','plan049-correction-010.md','plan049-correction-011.md','plan049-correction-012.md','plan049-correction-013.md','plan049-correction-014.md','plan049-correction-015.md')]
    require(command_bindings.get('addenda')==addenda and all(row in bindings for row in addenda),'current correction authority')
    ancestor_authorization=file_record(run/'authorization-049-ancestor-process-001.md')
    require(ancestor_authorization['sha256']=='734fc8fc67f2cc7f60ead6eba279b797abff47bbf32602cf5106e07ef540605d','fixed ancestor authorization bytes')
    require(command_bindings.get('ancestor_authorization')==ancestor_authorization and ancestor_authorization in bindings,'ancestor authorization binding')
    proof_record=strict_record(command_bindings.get('session_proof'))
    proof=session_proof(proof_record,note['kind'],note['attempt_index'],driver,identity_request,admission_record['path'],admission['reason'])
    require(proof_record in bindings and proof['user_authorization'] in bindings,'note session proof/authorization binding')
    capacity=admission.get('resource_capacity',{});B=capacity.get('B');H=capacity.get('H')
    require(type(B) is int and type(H) is int and min(B,H)>=0 and B+max(1,H)<=8 and type(capacity.get('charge')) is int and capacity['charge']==B+max(1,H),'admission exact CPU capacity')
    require(B==len(root['threads']) and H==0,'Main root thread capacity correlation')
    require(type(capacity.get('artifact_bytes')) is int and 0<=capacity['artifact_bytes']<=150*1024**3,'admission artifact capacity')
    return note
