"""D6 qualification011 worker: method 013 rebinding the passed 010 after the D6 maps retry entry."""
import argparse
import hashlib
import gc
from contextlib import contextmanager
import importlib.metadata
import importlib.util
from types import ModuleType
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


CREATION_EXCEPTION = dict(syscall='socket', domain=1, type=524293, protocol=0)


def physical_record(path):
    """Read only literal physical files using stdlib before dependency imports."""
    path = Path(path).absolute()
    require(path == path.resolve() and 'prompts' not in path.parts and path.is_file(),
            'early source must be a literal physical file')
    code = path.read_bytes()
    return dict(path=str(path), bytes=len(code), sha256=hashlib.sha256(code).hexdigest())


def install_early_guard(request_path):
    """Bind the new authority and install reviewed startup before any helpers."""
    physical_record(request_path)
    request = json.loads(Path(request_path).read_text())
    require(request.get('record_kind') == 'actual' and
            request.get('schema') == 'plan069-D6-driver-qualification-request/v5' and
            request.get('candidate') == 'D6' and request.get('job_id') == 'plan069-D6-driver-qualification-011',
            'actual qualification011 request required before guard startup')
    for key in ('review', 'authorization'):
        require(physical_record(request[key]['path']) == request[key], 'early authority bytes changed')
    reviewed = json.loads(Path(request['review']['path']).read_text())
    approved = json.loads(Path(request['authorization']['path']).read_text())
    proposal = reviewed.get('proposal', {})
    proposal_hash = hashlib.sha256(json.dumps(proposal,sort_keys=True,separators=(',', ':'),allow_nan=False).encode()).hexdigest()
    require(reviewed.get('schema') == 'plan069-D6-driver-qualification-review/v5' and reviewed.get('status') == 'REVIEW' and
            approved.get('schema') == 'plan069-D6-driver-qualification-authorization/v5' and approved.get('status') == 'DO' and
            approved.get('review') == request['review'] and approved.get('proposal_sha256') == proposal_hash,
            'explicit qualification011 REVIEW and DO required before startup')
    for key, path in (('worker',Path(__file__)),('guard_startup',Path(__file__).with_name('startup.py')),
                      ('network_guard',Path(__file__).with_name('network_guard.py'))):
        require(physical_record(path) == request.get(key) == proposal.get(key),
                'exact early reviewed '+key+' required')
    startup = request['guard_startup']; code = Path(startup['path']).read_bytes()
    require(len(code) == startup['bytes'] and hashlib.sha256(code).hexdigest() == startup['sha256'],
            'startup changed before execution')
    module = ModuleType('method014_reviewed_startup'); module.__file__ = startup['path']
    exec(compile(code,startup['path'],'exec'),module.__dict__)
    proof = module.install_before_helpers(request['network_guard'])
    require(physical_record(startup['path']) == startup and
            physical_record(request['network_guard']['path']) == request['network_guard'],
            'early guard bytes changed during startup')
    return dict(request=request,guard_startup=startup,guard_startup_proof=proof,network_guard=request['network_guard'])


def require(condition, message):
    if not condition:
        raise ValueError(message)


def write(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def helpers(root):
    root = Path(root).absolute()
    require(root == root.resolve(), 'source checkout path contains symlink')
    sys.path.insert(0, str(root / 'scripts'))
    from vipe_benchmark.files import file_record, read_json, verify_record
    return file_record, read_json, verify_record


def validate_offline_direct_url(direct, source):
    """PEP610 archive hashes are optional; the exact verified local URI is required."""
    expected = source['record']
    require(isinstance(direct, dict) and set(direct) == {'url', 'archive_info'},
            'installed source must be an offline archive without VCS/directory/editable metadata')
    require(direct['url'] == Path(expected['path']).as_uri(),
            'installed source URL differs from exact verified local archive')
    archive = direct['archive_info']
    require(isinstance(archive, dict) and set(archive) <= {'hash', 'hashes'},
            'installed source archive metadata unsupported')
    if 'hash' in archive:
        require(archive['hash'] == 'sha256=' + expected['sha256'],
                'installed source archive hash differs')
    if 'hashes' in archive:
        hashes = archive['hashes']
        require(isinstance(hashes, dict) and set(hashes) <= {'sha256'},
                'installed source archive hashes unsupported')
        if 'sha256' in hashes:
            require(hashes['sha256'] == expected['sha256'],
                    'installed source archive SHA256 differs')


def install_guards():
    # Python audit guards are additional controls, not a network namespace.
    def audit(event, args):
        if event.startswith('socket.') and event not in ('socket.__new__',):
            raise PermissionError('CPU qualification prohibits network sockets')
        if event in ('subprocess.Popen', 'os.system', 'os.posix_spawn', 'os.exec',
                     'os.fork', 'os.forkpty'):
            raise PermissionError('CPU qualification prohibits child process escape')
        if event in ('open', 'os.listdir', 'os.scandir', 'ctypes.dlopen') and args:
            value = args[0]
            if isinstance(value, (str, bytes, os.PathLike)):
                p = Path(os.fsdecode(value))
                if 'prompts' in p.parts or 'prompts' in p.resolve().parts:
                    raise PermissionError('CPU qualification prohibits prompts access')
    sys.addaudithook(audit)


@contextmanager
def no_inference_guards(torch, triton):
    """Fail on forward, direct or autotuned benchmarks and JIT launches."""
    calls = dict(forward_calls=0, benchmark_calls=0, kernel_launches=0)
    guards = [(torch.nn.Module, '_call_impl', 'forward_calls'),
              (triton.runtime.Autotuner, '_bench', 'benchmark_calls'),
              (triton.runtime.jit.JITFunction, 'run', 'kernel_launches'),
              (triton.testing, 'do_bench', 'benchmark_calls'),
              (triton.testing, 'do_bench_cudagraph', 'benchmark_calls')]
    retained = [getattr(owner, name) for owner, name, _ in guards]
    def forbid(kind):
        def denied(*unused_args, **unused_kwargs):
            calls[kind] += 1
            raise PermissionError('Driver qualification prohibits ' + kind)
        return denied
    try:
        for owner, name, kind in guards:
            setattr(owner, name, forbid(kind))
        yield calls
    finally:
        for (owner, name, _), original in zip(guards, retained):
            setattr(owner, name, original)


SUPERVISED_TRITON = (('TRITON_HOME', 'triton-home'), ('TRITON_CACHE_DIR', 'triton-cache'),
                     ('TRITON_DUMP_DIR', 'triton-dump'), ('TRITON_OVERRIDE_DIR', 'triton-override'))


def select_triton_cache(environment, output, triton_cache):
    """Accept only the supervisor's per-attempt Triton paths, then select the bound helper cache."""
    temporary = Path(output).absolute().with_name(Path(output).name + '-temporary')
    supervised = {name: str(temporary / folder) for name, folder in SUPERVISED_TRITON}
    inherited = {name: value for name, value in environment.items() if name.startswith('TRITON_')}
    require(inherited == supervised, 'Triton environment differs from the supervised per-attempt caches')
    require(isinstance(triton_cache.get('libcuda_path'), str), 'bound libcuda directory required')
    environment['TRITON_CACHE_DIR'] = triton_cache['cache_directory']
    # Triton >= 3.3 resolves libcuda eagerly; the bound path keeps it from running ldconfig.
    environment['TRITON_LIBCUDA_PATH'] = triton_cache['libcuda_path']


def bind_triton_cache(qualification, output, environment=None):
    """Bind the prebuilt helper from the qualification request before Triton loads, so its driver hits the cache."""
    from vipe_benchmark.triton_helper_cache import validate_binding
    triton_spec = importlib.util.find_spec('triton')
    require(triton_spec is not None and triton_spec.origin is not None, 'installed Triton package required')
    triton_directory = Path(triton_spec.origin).parent
    triton_cache = validate_binding(qualification['triton_cache'], triton_directory=triton_directory)
    select_triton_cache(os.environ if environment is None else environment, output, triton_cache)
    return triton_directory, triton_cache


def driver_child(args):
    early = install_early_guard(args.request)
    record, read, verify = helpers(args.root)
    from vipe_benchmark.depth_driver_qualification_triton_cache import KIND, validate_request, reservation_evidence
    from vipe_benchmark.depth_admission import local_source_records
    from vipe_benchmark.config import load
    from vipe_benchmark.ledger import Ledger
    qualification_request_record = record(args.request)
    request, _ = validate_request(qualification_request_record, current_sources=local_source_records('D6'))
    require(request['record_kind'] == 'actual', 'fixture request cannot execute a real driver')
    ledger = Ledger(request['ledger_path'], dict(load(), new_download_gib_limit=110, new_artifact_disk_gib_limit=210))
    JOB = request['job_id']
    require(JOB == 'plan069-D6-driver-qualification-011', 'method014 serves only qualification011')
    state = ledger.states().get(JOB, {})
    require(state.get('event') == 'reserve' and state.get('command') == request['command'] and
            state.get('evidence') == reservation_evidence(qualification_request_record,request), 'active exact GPU qualification reservation required')
    require(Path(args.output).absolute() == Path(request['output']) and
            str(Path(sys.executable).absolute()) == request['interpreter_invocation'], 'request output/interpreter differs')
    args.candidate = 'D6'
    args.setup = request['setup']['path']
    args.setup_request = request['setup_request']['path']
    args.setup_dispatch = request['setup_dispatch']['path']
    Path(args.output).mkdir(parents=True, exist_ok=False)
    require(request == early['request'], 'request changed after early guard installation')
    network_guard = early['network_guard']
    # Keep the early-verified qualification request separate: `request` is re-bound to the setup request below.
    qualification = early['request']
    install_guards()
    record, read, verify = helpers(args.root)
    from vipe_benchmark.depth_authorization import execution_authorization
    from vipe_benchmark.depth_admission import local_source_records
    from vipe_benchmark.depth_environment import _validate_inventory
    from vipe_benchmark.moge_environment import validate_environment_request
    from vipe_benchmark.moge_native import load_adapter
    from vipe_benchmark.moge_source_build import verify_derivation, cache_path
    from vipe_benchmark.runtime_inventory import inventory
    from vipe_benchmark.depth_extension import CONFIG
    out = Path(args.output).absolute()
    setup_record = record(args.setup)
    setup = read(args.setup)
    candidate = args.candidate
    require(setup.get('schema') == 'plan069-depth-setup-recovery-result/v1' and
            setup.get('candidate') == candidate and setup.get('status') == 'complete' and
            setup.get('record_kind') == 'actual', 'actual complete recovered candidate setup required')
    require(Path(args.setup).absolute() == Path(setup['source_dir']).parent / 'result.json',
            'setup record escaped owned source parent')
    # The approved runtime replacement: its accepted lineage replaces the original setup dispatch.
    from vipe_benchmark.depth_moge_runtime_replacement import accepted_setup_lineage
    lineage = accepted_setup_lineage(setup_record, ledger.events(), Path(qualification['ledger_path']).parent)
    dispatch_record = record(args.setup_dispatch)
    require(dispatch_record == lineage['review'], 'exact reviewed runtime replacement REVIEW required')
    review, authorization, proposal, _ = execution_authorization(candidate)
    require(lineage['map_proposal'] == proposal and
            setup.get('source_revision') == proposal['candidate_config']['code']['revision'] and
            setup.get('weight_revision') == proposal['candidate_config']['weights']['revision'],
            'setup differs from exact approved source or weights')
    request_record = record(args.setup_request)
    request = read(args.setup_request)
    require(request_record == lineage['request'] and request.get('candidate') == candidate and
            request.get('record_kind') == 'actual', 'exact accepted runtime replacement request required')
    recipe = lineage['runtime_environment']
    runtime_record = verify(setup['runtime_environment'])
    runtime = read(runtime_record['path'])
    require(runtime.get('status') == 'complete' and runtime.get('candidate') == candidate and
            runtime.get('python_executable') == str(Path(sys.executable).absolute()) and
            runtime.get('python') == record(sys.executable), 'exact prepared invocation interpreter required')
    runtime_request = read(Path(runtime_record['path']).parent / 'request.json')
    require(runtime_request.get('setup_request') == request_record and
            all(runtime_request.get(k) == v for k, v in recipe.items() if k != 'sources'),
            'runtime differs from original immutable setup recipe')
    for key in ('dependency_lock', 'inventory'):
        verify(runtime[key])
    for row in runtime['command_receipts']:
        verify(row)
    cache = cache_path(Path(runtime_record['path']).parent)
    require(runtime.get('flex_cache_path') == str(cache), 'runtime Flex cache differs')
    sources = runtime['source_packages']
    require([(r['name'], r['revision']) for r in sources] ==
            [(r['name'], r['revision']) for r in recipe['sources']], 'offline source pins differ')
    for source in sources:
        verify(source['record'])
        if source['name'] == 'flex-gemm':
            verify_derivation(source)
    require([r['name'] for r in sources] == ['utils3d_moge', 'pipeline', 'flex-gemm'],
            'exact three dependency source packages required')
    current = inventory()
    _validate_inventory(current, recipe, str(Path(sys.executable).absolute()))
    accepted_inventory = read(runtime['inventory']['path'])
    require(current == accepted_inventory, 'installed closure differs from accepted setup inventory')
    direct_urls = []
    for source in sources:
        dist = importlib.metadata.distribution(source['name'])
        direct = json.loads(dist.read_text('direct_url.json') or '{}')
        validate_offline_direct_url(direct, source)
        direct_urls.append(dict(name=source['name'], direct_url=direct))
    revision = setup['source_revision']
    files = [f for package in current['packages'] for f in package['files']]
    write(out / 'installed-dependencies.json', dict(schema='plan069-depth-installed-dependencies/v1',
        record_kind='actual', candidate=candidate, source_revision=revision,
        setup=setup_record, inventory=runtime['inventory'], packages=current['packages'], files=files,
        source_packages=sources, direct_urls=direct_urls, model_imports=False, gpu_operations=False))
    write(out / 'license-inventory.json', dict(schema='plan069-moge-license-inventory/v1',
        candidate=candidate, status='assessment-required', dependency_manifest=record(out / 'installed-dependencies.json'),
        packages=[dict(name=p['name'], version=p['version'], license=p['license'],
            classifiers=p['classifiers'], notices=[f for f in p['files'] if
                any(word in Path(f['path']).name.lower() for word in ('license', 'notice', 'copying', 'copyright'))])
            for p in current['packages']], source_license=record(Path(setup['source_dir']) / 'LICENSE'),
        weights_license='separate pinned primary evidence required; code license is insufficient'))
    from vipe_benchmark.triton_helper_cache import validate_binding
    triton_directory, triton_cache = bind_triton_cache(qualification, out)
    import torch
    require(not torch.cuda.is_initialized(), 'CUDA already initialized before approved qualification')
    torch.cuda.init()
    require(torch.cuda.is_initialized(), 'approved driver initialization failed')
    driver_metadata = dict(name=torch.cuda.get_device_name(0), capability=list(torch.cuda.get_device_capability(0)))
    import triton
    import triton.testing
    before_sources = local_source_records(candidate)
    with no_inference_guards(torch, triton) as calls:
        for _ in range(2):
            adapter = load_adapter(candidate, setup_record, device='cpu')
            model = adapter.runtime
            require(all(p.device.type == 'cpu' for p in model.parameters()) and
                    all(b.device.type == 'cpu' for b in model.buffers()), 'native model escaped CPU')
            require(hasattr(model, 'refiner'), 'native v3 refiner missing')
            del model, adapter
            gc.collect()
            require(all(count == 0 for count in calls.values()), 'qualification executed prohibited model/kernel/benchmark work')
    require(local_source_records(candidate) == before_sources, 'reviewed worker sources changed during capture')
    require(Path(triton.__file__).parent == triton_directory and
            validate_binding(qualification['triton_cache'], triton_directory=triton_directory) == triton_cache,
            'Triton helper cache changed during qualification')
    require(record(args.setup) == setup_record and record(args.setup_request) == request_record,
            'setup records changed during qualification')
    require(torch.cuda.max_memory_allocated() == 0, 'qualification allocated GPU model/tensor memory')
    write(out / 'worker-result.json', dict(schema='plan069-D6-driver-qualification-result/v5',
        trace_path=str(out.with_suffix('.syscalls.log')),
        network_guard=network_guard, creation_exception=CREATION_EXCEPTION,
        guard_startup=early['guard_startup'],guard_startup_proof=early['guard_startup_proof'],
        bind_exception=early['request']['bind_exception'],listen_exception=early['request']['listen_exception'],
        triton_cache=qualification['triton_cache'], triton_cache_unchanged=True,
        qualification_kind=KIND, request=qualification_request_record, method=record(__file__),
        all_parameters_cpu=True, all_buffers_cpu=True, gpu_model_load='not_performed',
        driver_metadata=driver_metadata, tensor_peak_allocated_bytes=0, **calls,
        record_kind='actual', candidate=candidate, status='passed', setup=setup_record,
        setup_dispatch=dispatch_record, setup_request=request_record, runtime_environment=runtime_record,
        python_executable=str(Path(sys.executable).absolute()), python=record(sys.executable),
        source_revision=revision, weights_revision=setup['weight_revision'], local_sources=before_sources,
        config=record(CONFIG), profile=proposal['profile'], checkpoint=setup['checkpoint'],
        flex_cache_path=str(cache), strict_cpu_loads=2, inference=False, cuda_initialized=True,
        network_guards=True, process_escape_guards=True, inventory=runtime['inventory'],
        dependency_manifest=record(out / 'installed-dependencies.json'),
        limitations=['Python audit guards are not a network namespace or native syscall sandbox.']))


def finalize(args):
    # Root's separately metered CPU wrapper must bound this verification phase too.
    record, read, verify = helpers(args.root)
    from vipe_benchmark.depth_admission import local_source_records
    from vipe_benchmark.depth_authorization import execution_authorization
    base = Path(args.capture).absolute()
    capture_record, native_record = record(Path(args.finish)), record(base / 'result.json')
    native = read(native_record['path'])
    finish = read(capture_record['path'])
    from vipe_benchmark.depth_driver_qualification_triton_cache import qualification_exception, KIND
    proof = dict(request=native['request'], result=native_record, finish=capture_record,
                 ledger_path=args.ledger)
    qualification_exception(dict(driver_qualification=proof, setup=native['setup'],
        local_sources=native['local_sources'], qualification_kind=KIND))
    require(native['local_sources'] == local_source_records(args.candidate), 'current source capture is stale')
    setup = read(verify(native['setup'])['path'])
    from vipe_benchmark.moge_setup import source_tree_records
    verified_source_files = source_tree_records(setup['source_dir'])
    require(verified_source_files == setup.get('source_tree'),
            'extracted native source changed since setup/capture')
    verified_source_archive = verify(setup['source_archive'])
    retained_runtime = read(verify(native['runtime_environment'])['path'])
    require(verify(native['python']) == retained_runtime.get('python') and
            retained_runtime.get('python_executable') == native['python_executable'],
            'prepared interpreter changed since native CPU capture')
    verify(native['inventory'])
    verify(native['config'])
    dependency_record = verify(native['dependency_manifest'])
    dependencies = read(dependency_record['path'])
    for row in dependencies['files']:
        verify(row)
    assessment_record = record(args.commercial_assessment)
    assessment = read(args.commercial_assessment)
    scopes = ('code', 'weights', 'dependencies', 'inference_outputs')
    require(assessment.get('schema') == 'plan069-depth-commercial-assessment/v1' and
            assessment.get('candidate') == args.candidate and
            assessment.get('source_revision') == native['source_revision'] and
            assessment.get('weights_revision') == native['weights_revision'] and
            assessment.get('dependency_manifest') == dependency_record and
            all(assessment.get(s) == 'allowed' for s in scopes) and
            len(assessment.get('primary_sources', [])) >= 2 and
            assessment.get('independent_review', {}).get('status') == 'passed',
            'independently reviewed exact code/weights/dependency/output permission required')
    verify(assessment['permission_report'])
    source_review = record(args.source_review)
    reviewed = read(args.source_review)
    from vipe_benchmark.depth_moge_runtime_replacement import accepted_setup_lineage
    lineage = accepted_setup_lineage(native['setup'], [json.loads(line) for line in Path(args.ledger).read_text().splitlines()],
                                     Path(args.ledger).parent)
    require(verify(native['setup_request']) == lineage['request'], 'runtime replacement request lineage differs')
    original_request = read(lineage['original']['request']['path'])
    verify(original_request['runtime_environment_record'])
    require(reviewed.get('runtime_recipe') == original_request['runtime_environment_record'],
            'current source review differs from the accepted original setup recipe')
    require(reviewed.get('schema') == 'plan069-depth-source-review/v1' and
            reviewed.get('candidate') == args.candidate and reviewed.get('status') == 'passed' and
            reviewed.get('local_sources') == native['local_sources'] and
            reviewed.get('source_archive') == verified_source_archive and
            reviewed.get('source_files') == verified_source_files, 'current independent post-setup source review required')
    _, _, proposal, _ = execution_authorization(args.candidate)
    require(native['profile'] == proposal['profile'], 'approved profile changed since CPU capture')
    from vipe_benchmark.depth_admission import INVENTORY
    inventory = read(INVENTORY)['candidates'][args.candidate]['files']
    require(len(inventory) == 1 and inventory[0]['path'] == 'model.pt', 'MoGe exact model asset inventory changed')
    checkpoint = verify(setup['checkpoint'])
    require(checkpoint['bytes'] == inventory[0]['bytes'] and
            checkpoint['sha256'] == inventory[0]['lfs_sha256'], 'checkpoint differs from frozen inventory')
    assets = [dict(repository=inventory[0]['repository'], path='model.pt', record=checkpoint)]
    out = Path(args.output).absolute()
    out.mkdir(parents=True, exist_ok=False)
    runtime = dict(schema='plan069-depth-runtime-qualification/v1', record_kind='actual',
        candidate=args.candidate, status='passed', source_revision=native['source_revision'],
        setup=native['setup'], source_archive=setup['source_archive'], source_files=setup['source_tree'],
        config=native['config'], profile=native['profile'], assets=assets,
        local_sources=native['local_sources'], dependency_manifest=dependency_record,
        python_executable=native['python_executable'], python=native['python'], source_review=source_review,
        native_load=native_record, driver_qualification=proof, qualification_kind=KIND,
        gpu_model_load='not_performed', cuda_initialized=True,
        peak_gpu_memory=finish['peak']['device_bytes'], qualification_scope='GPU-aware driver import and two strict CPU model loads; no forward/inference/benchmark/kernel launch. Scientific GPU numerical behavior remains unmeasured.')
    write(out / 'runtime-qualification.json', runtime)
    commercial = {k: assessment[k] for k in ('candidate', 'source_revision', 'weights_revision', *scopes)}
    commercial['assessment'] = assessment_record
    runtime_binding = {k: runtime[k] for k in ('candidate', 'source_revision', 'status', 'config')}
    runtime_binding['receipt'] = record(out / 'runtime-qualification.json')
    runtime_binding['python_executable'] = runtime['python_executable']
    write(out / 'qualification.json', dict(schema=f'plan069-depth-{args.candidate}-qualification/v1',
        record_kind='actual', candidate=args.candidate, status='passed', setup=native['setup'],
        source_archive=setup['source_archive'], source_files=setup['source_tree'], assets=assets, commercial=commercial, runtime=runtime_binding, source_review=source_review))



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('driver-child', 'finalize'))
    parser.add_argument('--root')
    parser.add_argument('--request')
    parser.add_argument('--output', required=True)
    parser.add_argument('--candidate', default='D6', choices=('D6',))
    parser.add_argument('--capture')
    parser.add_argument('--finish')
    parser.add_argument('--ledger')
    parser.add_argument('--commercial-assessment')
    parser.add_argument('--source-review')
    args = parser.parse_args()
    if args.mode == 'driver-child':
        require(args.request is not None, 'approved qualification request required')
        physical_record(args.request)
        document = json.loads(Path(args.request).read_text())
        args.root = document['root']
        driver_child(args)
    else:
        require(all(getattr(args, name) for name in ('root', 'capture', 'finish', 'ledger', 'commercial_assessment', 'source_review')),
                'full accepted GPU qualification and commercial/source evidence required')
        finalize(args)


if __name__ == '__main__':
    main()
