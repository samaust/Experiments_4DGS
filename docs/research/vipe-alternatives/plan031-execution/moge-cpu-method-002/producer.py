"""Retained local MoGe CPU evidence method; root owns admission and CPU charge."""
import argparse
import gc
import importlib.metadata
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


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


def capture_child(args):
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
    require(setup.get('schema') == 'plan069-depth-setup-result/v1' and
            setup.get('candidate') == candidate and setup.get('status') == 'complete' and
            setup.get('record_kind') == 'actual', 'actual complete candidate setup required')
    require(Path(args.setup).absolute() == Path(setup['source_dir']).parent / 'result.json',
            'setup record escaped owned source parent')
    dispatch_record = record(args.setup_dispatch)
    dispatched = read(args.setup_dispatch)
    require(dispatched.get('schema') == 'plan069-depth-setup-dispatch/v1' and
            dispatched.get('status') == 'complete' and dispatched.get('result') == setup_record,
            'accepted supervised setup dispatch record required')
    review, authorization, proposal, _ = execution_authorization(candidate)
    require(setup.get('review') == review and setup.get('authorization') == authorization and
            setup.get('source_revision') == proposal['candidate_config']['code']['revision'] and
            setup.get('weight_revision') == proposal['candidate_config']['weights']['revision'],
            'setup differs from exact approved source or weights')
    request_record = record(args.setup_request)
    request = read(args.setup_request)
    require(request.get('review') == review and request.get('authorization') == authorization and
            request.get('schema') == 'plan069-depth-setup-request/v1' and
            request.get('candidate') == candidate and request.get('record_kind') == 'actual' and
            request.get('job_id') == f'plan069-{candidate}-setup-001', 'exact setup request required')
    recipe = request['runtime_environment']
    require(read(verify(request['runtime_environment_record'])['path']) == recipe,
            'setup inline environment differs from exact reviewed recipe record')
    validate_environment_request(recipe, setup['source_dir'], candidate, 'actual')
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
    import torch
    require(not torch.cuda.is_initialized(), 'CUDA already initialized')
    def forbid_cuda(*unused_args, **unused_kwargs):
        raise PermissionError('CPU qualification prohibits CUDA initialization')
    torch.cuda._lazy_init = forbid_cuda
    before_sources = local_source_records(candidate)
    for _ in range(2):
        adapter = load_adapter(candidate, setup_record, device='cpu')
        model = adapter.runtime
        require(all(p.device.type == 'cpu' for p in model.parameters()) and
                all(b.device.type == 'cpu' for b in model.buffers()), 'native model escaped CPU')
        require(candidate != 'D6' or hasattr(model, 'refiner'), 'native v3 refiner missing')
        del model, adapter
        gc.collect()
        require(not torch.cuda.is_initialized(), 'native CPU load initialized CUDA')
    require(local_source_records(candidate) == before_sources, 'reviewed worker sources changed during capture')
    require(record(args.setup) == setup_record and record(args.setup_request) == request_record,
            'setup records changed during qualification')
    write(out / 'native-cpu.json', dict(schema='plan069-moge-native-cpu-qualification/v1',
        record_kind='actual', candidate=candidate, status='passed', setup=setup_record,
        setup_dispatch=dispatch_record, setup_request=request_record, runtime_environment=runtime_record,
        python_executable=str(Path(sys.executable).absolute()), python=record(sys.executable),
        source_revision=revision, weights_revision=setup['weight_revision'], local_sources=before_sources,
        config=record(CONFIG), profile=proposal['profile'], checkpoint=setup['checkpoint'],
        flex_cache_path=str(cache), strict_cpu_loads=2, inference=False, cuda_initialized=False,
        network_guards=True, process_escape_guards=True, inventory=runtime['inventory'],
        dependency_manifest=record(out / 'installed-dependencies.json'),
        limitations=['Python audit guards are not a network namespace or native syscall sandbox.']))


def terminate(process):
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait()


def capture(args):
    started = time.monotonic()
    record, read, verify = helpers(args.root)
    require(0 < args.seconds <= 180 and args.artifact_bytes > 0, 'bounded CPU and artifact allocations required')
    setup = read(args.setup)
    runtime = read(verify(setup['runtime_environment'])['path'])
    python = runtime['python_executable']
    out = Path(args.output).absolute()
    environment = dict(os.environ, CUDA_VISIBLE_DEVICES='', PYTHONDONTWRITEBYTECODE='1',
        HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_DATASETS_OFFLINE='1',
        DIFFUSERS_OFFLINE='1', UV_OFFLINE='1', PIP_NO_INDEX='1', WANDB_MODE='disabled',
        PYTHONNOUSERSITE='1', OMP_NUM_THREADS='7', MKL_NUM_THREADS='7', MAX_JOBS='7')
    for name in ('PYTHONPATH', 'PYTHONHOME', 'FLEX_GEMM_BUILD_CUDA', 'BUILD_CUDA'):
        require(name not in os.environ, 'inherited unreviewed path/build configuration: ' + name)
    for variable in ('HF_HOME', 'TRITON_CACHE_DIR', 'TORCH_HOME', 'MPLCONFIGDIR',
                     'NUMBA_CACHE_DIR', 'XDG_CACHE_HOME', 'TMPDIR'):
        path = out / variable.lower()
        environment[variable] = str(path)
    from vipe_benchmark.moge_source_build import cache_path
    environment['FLEX_GEMM_AUTOTUNE_CACHE_PATH'] = str(cache_path(Path(runtime['inventory']['path']).parent))
    command = [python, '-I', '-B', str(Path(__file__).absolute()), 'child', '--root', args.root,
        '--candidate', args.candidate, '--setup', args.setup, '--setup-request', args.setup_request,
        '--setup-dispatch', args.setup_dispatch, '--output', str(out)]
    method = record(__file__)
    require(args.artifact_bytes >= 65536, 'artifact allocation must reserve terminal evidence headroom')
    out.mkdir(parents=True, exist_ok=False)
    process, error, returncode, native_record = None, None, None, None
    try:
        for variable in ('HF_HOME', 'TRITON_CACHE_DIR', 'TORCH_HOME', 'MPLCONFIGDIR',
                         'NUMBA_CACHE_DIR', 'XDG_CACHE_HOME', 'TMPDIR'):
            Path(environment[variable]).mkdir()
        write(out / 'method.json', dict(method=method, command=command, seconds=args.seconds,
            artifact_bytes=args.artifact_bytes, environment={k: environment[k] for k in (
                'CUDA_VISIBLE_DEVICES', 'PYTHONDONTWRITEBYTECODE', 'HF_HUB_OFFLINE',
                'TRANSFORMERS_OFFLINE', 'HF_DATASETS_OFFLINE', 'DIFFUSERS_OFFLINE', 'UV_OFFLINE',
                'PIP_NO_INDEX', 'PYTHONNOUSERSITE', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'MAX_JOBS',
                'HF_HOME', 'TRITON_CACHE_DIR', 'TORCH_HOME', 'MPLCONFIGDIR', 'NUMBA_CACHE_DIR',
                'XDG_CACHE_HOME', 'TMPDIR', 'FLEX_GEMM_AUTOTUNE_CACHE_PATH')}, root_cpu_charge_required=True))
        with (out / 'stdout.txt').open('xb') as stdout, (out / 'stderr.txt').open('xb') as stderr:
            process = subprocess.Popen(command, env=environment, stdout=stdout, stderr=stderr,
                start_new_session=True)
            while process.poll() is None:
                if time.monotonic() - started >= args.seconds:
                    raise TimeoutError('CPU qualification wall allocation exhausted')
                size = sum(p.stat().st_blocks * 512 for p in out.rglob('*') if p.is_file())
                if size > args.artifact_bytes - 32768:
                    raise ValueError('CPU qualification retained artifact allocation exhausted')
                time.sleep(.1)
            returncode = process.returncode
            require(returncode == 0, 'native CPU qualification child failed')
            require(time.monotonic() - started < args.seconds, 'CPU qualification wall allocation exhausted')
            require(sum(p.stat().st_blocks * 512 for p in out.rglob('*') if p.is_file()) <=
                    args.artifact_bytes - 32768, 'CPU qualification retained artifact allocation exhausted')
            native = read(out / 'native-cpu.json')
            require(native.get('status') == 'passed' and native.get('candidate') == args.candidate and
                    native.get('setup') == record(args.setup), 'native child result missing or mismatched')
            native_record = record(out / 'native-cpu.json')
            require(record(__file__) == method, 'retained method changed during execution')
    except BaseException as exc:
        error = type(exc).__name__ + ': ' + str(exc)
        if process is not None and process.poll() is None:
            terminate(process)
        if process is not None:
            returncode = process.returncode
    finally:
        write(out / 'capture.json', dict(schema='plan069-moge-cpu-capture/v1', candidate=args.candidate,
            status='passed' if error is None else 'failed', method=method, command=command,
            elapsed_seconds=time.monotonic() - started, timing_scope='capture launcher entry through child cleanup',
            returncode=returncode, error=error, native_cpu=native_record, cpu_charge_applied=False, ledger_modified=False,
            download_bytes=0, gpu_operations=False, cleanup_confirmed=process is not None and process.poll() is not None,
            cleanup_scope='direct child reaped; root admitted CPU wrapper must independently confirm full descendant cleanup',
            limitations=['Python guards are not a native syscall/network namespace sandbox; external metered CPU wrapper required.']))
    require(sum(p.stat().st_blocks * 512 for p in out.rglob('*') if p.is_file()) <=
            args.artifact_bytes, 'terminal evidence exceeded artifact allocation')
    require(error is None, error)


def finalize(args):
    # Root's separately metered CPU wrapper must bound this verification phase too.
    record, read, verify = helpers(args.root)
    from vipe_benchmark.depth_admission import local_source_records
    from vipe_benchmark.depth_authorization import execution_authorization
    base = Path(args.capture).absolute()
    capture_record, native_record = record(base / 'capture.json'), record(base / 'native-cpu.json')
    captured, native = read(capture_record['path']), read(native_record['path'])
    require(captured.get('status') == 'passed' and captured.get('cleanup_confirmed') is True and
            captured.get('native_cpu') == native_record and
            native.get('status') == 'passed' and native.get('candidate') == args.candidate and
            native.get('strict_cpu_loads') == 2 and native.get('inference') is False and
            native.get('cuda_initialized') is False,
            'successful exact native CPU capture required')
    require(native['local_sources'] == local_source_records(args.candidate), 'current source capture is stale')
    setup = read(verify(native['setup'])['path'])
    from vipe_benchmark.moge_setup import source_tree_records
    require(source_tree_records(setup['source_dir']) == setup.get('source_tree'),
            'extracted native source changed since setup/capture')
    verify(setup['source_archive'])
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
    original_request = read(verify(native['setup_request'])['path'])
    verify(original_request['runtime_environment_record'])
    require(reviewed.get('runtime_recipe') == original_request['runtime_environment_record'],
            'current source review differs from accepted setup recipe')
    require(reviewed.get('schema') == 'plan069-depth-source-review/v1' and
            reviewed.get('candidate') == args.candidate and reviewed.get('status') == 'passed' and
            reviewed.get('local_sources') == native['local_sources'], 'current independent source review required')
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
        setup=native['setup'], config=native['config'], profile=native['profile'], assets=assets,
        local_sources=native['local_sources'], dependency_manifest=dependency_record,
        python_executable=native['python_executable'], python=native['python'], source_review=source_review,
        native_cpu=native_record, capture=capture_record, gpu_model_load='not_performed',
        peak_gpu_memory='not_measured', qualification_scope='exact installed closure and two strict native CPU loads; no inference/CUDA; GPU numerical behavior and memory remain unmeasured')
    write(out / 'runtime-qualification.json', runtime)
    commercial = {k: assessment[k] for k in ('candidate', 'source_revision', 'weights_revision', *scopes)}
    commercial['assessment'] = assessment_record
    runtime_binding = {k: runtime[k] for k in ('candidate', 'source_revision', 'status', 'config')}
    runtime_binding['receipt'] = record(out / 'runtime-qualification.json')
    runtime_binding['python_executable'] = runtime['python_executable']
    write(out / 'qualification.json', dict(schema=f'plan069-depth-{args.candidate}-qualification/v1',
        record_kind='actual', candidate=args.candidate, status='passed', setup=native['setup'],
        assets=assets, commercial=commercial, runtime=runtime_binding, source_review=source_review))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='mode', required=True)
    for mode in ('capture', 'child', 'finalize'):
        p = sub.add_parser(mode)
        p.add_argument('--root', required=True)
        p.add_argument('--candidate', choices=('D5', 'D6'), required=True)
        p.add_argument('--output', required=True)
        if mode in ('capture', 'child'):
            p.add_argument('--setup', required=True)
            p.add_argument('--setup-request', required=True)
            p.add_argument('--setup-dispatch', required=True)
        if mode == 'capture':
            p.add_argument('--seconds', type=float, required=True)
            p.add_argument('--artifact-bytes', type=int, required=True)
        if mode == 'finalize':
            p.add_argument('--capture', required=True)
            p.add_argument('--commercial-assessment', required=True)
            p.add_argument('--source-review', required=True)
    args = parser.parse_args()
    {'capture': capture, 'child': capture_child, 'finalize': finalize}[args.mode](args)


if __name__ == '__main__':
    main()
