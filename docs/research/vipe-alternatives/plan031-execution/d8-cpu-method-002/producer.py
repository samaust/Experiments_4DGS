"""Retained local D8 CPU evidence method; root owns admission and CPU charge."""
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


def source_files(setup, record, verify):
    """Convert verified relative manifest entries into absolute file records."""
    from vipe_benchmark.depth_source_integrity import verify_source
    root = Path(setup['source_dir'])
    require(root.is_absolute() and root == root.resolve(), 'absolute immutable source directory required')
    entries = setup.get('source_manifest', {}).get('files')
    require(isinstance(entries, list) and bool(entries), 'nonempty source manifest required')
    result = []
    for entry in entries:
        relative = Path(entry['path'])
        require(not relative.is_absolute() and '..' not in relative.parts and
                'prompts' not in relative.parts and relative.parts,
                'unsafe native source manifest entry')
        path = root / relative
        require(path == path.resolve() and path.is_file(), 'source file escaped immutable tree')
        expected = dict(path=str(path), sha256=entry['sha256'], bytes=entry['bytes'])
        require(record(path) == verify(expected), 'native source manifest bytes changed')
        result.append(expected)
    require(len({row['path'] for row in result}) == len(result), 'duplicate native source manifest entries')
    verify_source(setup)
    return result


def forbid_cuda_initialization(torch):
    require(not torch.cuda.is_initialized(), 'CUDA already initialized')
    def forbid_cuda(*args, **kwargs):
        raise PermissionError('CPU qualification prohibits CUDA initialization')
    torch.cuda._lazy_init = forbid_cuda


def strict_cpu_loads(setup, torch, model_class):
    """Same bundled constructor and strict state loading as native_d8; no infer."""
    forbid_cuda_initialization(torch)
    asset = setup['assets'][0]['record']
    counts = []
    for _ in range(2):
        checkpoint = torch.load(asset['path'], map_location='cpu', weights_only=True)
        require(isinstance(checkpoint, dict) and isinstance(checkpoint.get('model_config'), dict) and
                isinstance(checkpoint.get('model'), dict), 'D8 checkpoint structure differs')
        model = model_class(**checkpoint['model_config'])
        model.load_state_dict(checkpoint['model'], strict=True)
        model = model.to('cpu').eval()
        require(not model.training and all(p.device.type == 'cpu' for p in model.parameters()) and
                all(b.device.type == 'cpu' for b in model.buffers()), 'native model escaped CPU/eval')
        counts.append(dict(parameters=sum(p.numel() for p in model.parameters()),
                           buffers=sum(b.numel() for b in model.buffers())))
        del model, checkpoint
        gc.collect()
        require(not torch.cuda.is_initialized(), 'native CPU load initialized CUDA')
    require(counts[0] == counts[1], 'two strict CPU loads differ')
    return counts


def bind_accepted_setup(args, record, read, run, review, authorization, proposal):
    """Bind the accepted D8 setup: the original setup-001 or its accepted recovery.

    Returns (setup, setup request record, setup dispatch record or None, runtime request).
    A consumed failed setup never qualifies; a recovery qualifies only through the
    recovery core's accepted lineage (clean protected completion, exact request).
    """
    from vipe_benchmark.config import load
    from vipe_benchmark.depth_native_runtime import recipe
    from vipe_benchmark.ledger import Ledger
    from vipe_benchmark.native_d8 import SOURCE_REVISION
    from vipe_benchmark.setup_recovery_core import accepted_setup
    setup_record = record(args.setup)
    events = Ledger(run / 'ledger.jsonl', dict(load(), new_download_gib_limit=110,
                    new_artifact_disk_gib_limit=210)).events()
    setup, job = accepted_setup('D8', setup_record, events, run)
    recovered = job != 'plan069-D8-setup-001'
    require(setup.get('candidate') == 'D8' and setup.get('status') == 'complete' and
            setup.get('record_kind') == 'actual' and setup.get('job_id') == job and
            setup.get('schema') == ('plan069-depth-setup-recovery-result/v1' if recovered
                                    else 'plan069-depth-setup-result/v1') and
            setup.get('source_revision') == SOURCE_REVISION ==
            proposal['candidate_config']['code']['revision'] and
            setup.get('weight_revision') == proposal['candidate_config']['weights']['revision'],
            'exact actual completed D8 setup required')
    request_record = record(args.setup_request)
    request = read(args.setup_request)
    if recovered:
        require(args.setup_dispatch is None and setup.get('request') == request_record and
                request.get('schema') == 'plan069-depth-setup-recovery-request/v1' and
                request.get('job_id') == job and request.get('runtime_environment') == recipe('D8', run),
                'exact accepted recovery request and amended recipe required')
        dispatch_record = None
    else:
        dispatch_record = record(args.setup_dispatch)
        dispatched = read(args.setup_dispatch)
        require(dispatched.get('schema') == 'plan069-depth-setup-dispatch/v1' and
                dispatched.get('status') == 'complete' and dispatched.get('result') == setup_record and
                setup.get('review') == review and setup.get('authorization') == authorization,
                'accepted supervised setup dispatch required')
        require(request.get('schema') == 'plan069-depth-setup-request/v1' and
                request.get('candidate') == 'D8' and request.get('job_id') == job and
                request.get('record_kind') == 'actual' and request.get('review') == review and
                request.get('authorization') == authorization and
                request.get('environment') == recipe('D8', run),
                'exact original setup recipe/approval required')
        reserve = [e for e in events if e.get('event') == 'reserve' and e.get('job_id') == job]
        require(len(reserve) == 1 and reserve[0].get('evidence', {}).get('request') == request_record,
                'exact original setup reservation request required')
    runtime_request = read(run / 'jobs' / job / 'runtime/request.json')
    return setup, request_record, dispatch_record, runtime_request


def capture_child(args):
    install_guards()
    sys.dont_write_bytecode = True
    record, read, verify = helpers(args.root)
    from vipe_benchmark.depth_authorization import execution_authorization
    from vipe_benchmark.depth_admission import local_source_records
    from vipe_benchmark.depth_native_runtime import recipe, verify_runtime
    from vipe_benchmark.depth_environment import _validate_inventory
    from vipe_benchmark.runtime_inventory import inventory
    from vipe_benchmark.depth_extension import CONFIG
    from vipe_benchmark.native_d8 import SOURCE_REVISION, WEIGHT_SHA256
    out = Path(args.output).absolute()
    setup_record = record(args.setup)
    run = Path(args.setup).absolute().parents[2]
    review, authorization, proposal, _ = execution_authorization('D8')
    setup, request_record, dispatch_record, runtime_request = bind_accepted_setup(
        args, record, read, run, review, authorization, proposal)
    expected_recipe = recipe('D8', run)
    files = source_files(setup, record, verify)
    runtime = setup['runtime']
    package_qualification = verify_runtime(setup)
    require(runtime_request.get('setup_request') == request_record and
            all(runtime_request.get(k) == v for k,v in expected_recipe.items() if k not in
                ('sources', 'requirement_sources', 'constraints')) and
            set(expected_recipe['constraints']) <= set(runtime_request.get('constraints', [])) and
            all('==' in pin for pin in runtime_request.get('constraints', [])),
            'installed runtime differs from the approved recipe')
    current = inventory()
    _validate_inventory(current, runtime_request, str(Path(sys.executable).absolute()))
    require(current == read(verify(runtime['inventory'])['path']), 'installed closure changed since setup')
    sources = runtime['source_packages']
    require(len(sources) == 1 and sources[0]['name'] == 'utils3d', 'exact pinned utils3d source required')
    validate_offline_direct_url(json.loads(importlib.metadata.distribution('utils3d').read_text('direct_url.json') or '{}'), sources[0])
    verify(sources[0]['record'])
    dependencies = [f for package in current['packages'] for f in package['files']]
    write(out / 'installed-dependencies.json', dict(schema='plan069-depth-installed-dependencies/v1',
        record_kind='actual', candidate='D8', source_revision=SOURCE_REVISION, setup=setup_record,
        inventory=runtime['inventory'], packages=current['packages'], files=dependencies,
        source_packages=sources, model_imports=False, gpu_operations=False))
    before = local_source_records('D8')
    assets = setup['assets']
    require(len(assets) == 1 and assets[0]['repository'] == 'metricanything' and
            assets[0]['path'] == 'student_pointmap.pt' and
            verify(assets[0]['record'])['sha256'] == WEIGHT_SHA256, 'exact PointMap checkpoint required')
    source = Path(setup['source_dir']) / 'models/student_pointmap'
    require(setup.get('native_source') == record(source / 'moge/model/v2.py'), 'bundled model entry changed')
    require(not any(name == 'moge' or name.startswith('moge.') for name in sys.modules),
            'different MoGe implementation preloaded')
    sys.path.insert(0,str(source))
    import torch
    forbid_cuda_initialization(torch)
    from moge.model.v2 import MoGeModel
    location = getattr(sys.modules[MoGeModel.__module__], '__file__', None)
    if not isinstance(location, str) or not Path(location).resolve().is_relative_to(source):
        raise ValueError('different MoGe implementation imported')
    counts = strict_cpu_loads(setup, torch, MoGeModel)
    for asset in assets:
        verify(asset['record'])
    require(source_files(setup, record, verify) == files and local_source_records('D8') == before and
            record(args.setup) == setup_record and record(args.setup_request) == request_record,
            'setup/source changed during capture')
    write(out / 'native-cpu.json', dict(schema='plan069-D8-native-cpu-qualification/v1',
        record_kind='actual', candidate='D8', status='passed', setup=setup_record,
        setup_dispatch=dispatch_record, setup_request=request_record,
        python_executable=str(Path(sys.executable).absolute()), python=record(sys.executable),
        source_revision=SOURCE_REVISION, weights_revision=setup['weight_revision'],
        source_archive=setup['source_archive'], source_files=files, local_sources=before,
        config=record(CONFIG), profile=proposal['profile'], assets=assets, strict_cpu_loads=2,
        load_counts=counts, inference=False, cuda_initialized=False,
        inventory=runtime['inventory'], dependency_manifest=record(out / 'installed-dependencies.json'),
        native_package_qualification=package_qualification,
        limitations=['Python audit guards are not a native syscall/network namespace sandbox.']))


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
    runtime = setup['runtime']
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
    command = [python, '-I', '-B', str(Path(__file__).absolute()), 'child', '--root', args.root,
        '--candidate', args.candidate, '--setup', args.setup, '--setup-request', args.setup_request,
        *(['--setup-dispatch', args.setup_dispatch] if args.setup_dispatch else []), '--output', str(out)]
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
                'XDG_CACHE_HOME', 'TMPDIR')}, root_cpu_charge_required=True))
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
        write(out / 'capture.json', dict(schema='plan069-D8-cpu-capture/v1', candidate=args.candidate,
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
    install_guards()
    record, read, verify = helpers(args.root)
    from vipe_benchmark.depth_admission import local_source_records
    from vipe_benchmark.depth_authorization import execution_authorization
    base = Path(args.capture).absolute()
    captured, native = read(base / 'capture.json'), read(base / 'native-cpu.json')
    native_record = record(base / 'native-cpu.json')
    require(captured.get('status') == 'passed' and captured.get('cleanup_confirmed') is True and
            captured.get('native_cpu') == native_record and native.get('status') == 'passed' and
            native.get('candidate') == 'D8' and native.get('strict_cpu_loads') == 2 and
            native.get('inference') is False and native.get('cuda_initialized') is False,
            'successful exact CPU capture required')
    require(native['local_sources'] == local_source_records('D8'), 'current source capture stale')
    setup = read(verify(native['setup'])['path'])
    files = source_files(setup, record, verify)
    archive = verify(setup['source_archive'])
    require(native.get('source_files') == files and native.get('source_archive') == archive and
            native.get('assets') == setup.get('assets'), 'native source/assets capture changed')
    runtime = setup['runtime']
    verify(native['setup_request'])
    if native.get('setup_dispatch') is not None:
        verify(native['setup_dispatch'])
    for row in runtime.get('command_receipts', []):
        verify(row)
    if 'dependency_lock' in runtime:
        verify(runtime['dependency_lock'])
    require(verify(native['python']) == runtime.get('python') and
            runtime.get('python_executable') == native['python_executable'], 'prepared interpreter changed')
    for key in ('inventory','config'):
        verify(native[key])
    dependency_record = verify(native['dependency_manifest'])
    dependencies = read(dependency_record['path'])
    require(dependencies.get('candidate') == 'D8' and dependencies.get('setup') == native['setup'] and
            dependencies.get('source_revision') == native['source_revision'] and
            dependencies.get('files'), 'exact installed dependency manifest required')
    for row in dependencies['files']:
        verify(row)
    assessment_record = record(args.commercial_assessment)
    assessment = read(args.commercial_assessment)
    scopes = ('code','weights','dependencies','inference_outputs')
    require(assessment.get('schema') == 'plan069-depth-commercial-assessment/v1' and
            assessment.get('candidate') == 'D8' and
            assessment.get('source_revision') == native['source_revision'] and
            assessment.get('weights_revision') == native['weights_revision'] and
            assessment.get('dependency_manifest') == dependency_record and
            all(assessment.get(key) == 'allowed' for key in scopes) and
            len(assessment.get('primary_sources',[])) >= 2 and
            assessment.get('independent_review',{}).get('status') == 'passed',
            'independently reviewed exact commercial permissions required')
    verify(assessment['permission_report'])
    source_record = record(args.source_review)
    source_review = read(args.source_review)
    require(source_review.get('schema') == 'plan069-depth-source-review/v1' and
            source_review.get('candidate') == 'D8' and source_review.get('status') == 'passed' and
            source_review.get('reviewer') and source_review.get('source_revision') == native['source_revision'] and
            source_review.get('local_sources') == native['local_sources'] and
            source_review.get('source_archive') == archive and source_review.get('source_files') == files,
            'fresh postsetup source review must bind identical archive and absolute source files')
    _, _, proposal, _ = execution_authorization('D8')
    require(native['profile'] == proposal['profile'] and
            source_review.get('profile_inventory') == proposal['profile_inventory'], 'exact approved profile required')
    from vipe_benchmark.depth_setup_other import _asset_identity
    expected = read(verify(proposal['required_assets'])['path'])['candidates']['D8']['files']
    require(len(expected) == len(native['assets']) == 1, 'exact single checkpoint inventory required')
    for asset, row in zip(native['assets'], expected):
        require((asset['repository'],asset['path']) == (row['repository'],row['path']), 'checkpoint identity differs')
        _asset_identity(verify(asset['record']),row)
    out = Path(args.output).absolute()
    out.mkdir(parents=True,exist_ok=False)
    runtime_doc = dict(schema='plan069-depth-runtime-qualification/v1',record_kind='actual',
        candidate='D8',status='passed',source_revision=native['source_revision'],
        setup=native['setup'],config=native['config'],profile=native['profile'],assets=native['assets'],
        source_archive=archive,source_files=files,local_sources=native['local_sources'],
        dependency_manifest=dependency_record,python_executable=native['python_executable'],python=native['python'],
        source_review=source_record,native_cpu=native_record,capture=record(base/'capture.json'),
        gpu_model_load='not_performed',peak_gpu_memory='not_measured',
        qualification_scope='exact installed closure and two strict native CPU loads; no inference/CUDA')
    write(out/'runtime-qualification.json',runtime_doc)
    commercial = {key:assessment[key] for key in ('candidate','source_revision','weights_revision',*scopes)}
    commercial['assessment'] = assessment_record
    binding = {key:runtime_doc[key] for key in ('candidate','source_revision','status','config','python_executable')}
    binding['receipt'] = record(out/'runtime-qualification.json')
    write(out/'qualification.json',dict(schema='plan069-depth-D8-qualification/v1',record_kind='actual',
        candidate='D8',status='passed',setup=native['setup'],assets=native['assets'],commercial=commercial,
        runtime=binding,source_review=source_record,source_archive=archive,source_files=files))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='mode', required=True)
    for mode in ('capture', 'child', 'finalize'):
        p = sub.add_parser(mode)
        p.add_argument('--root', required=True)
        p.add_argument('--candidate', choices=('D8',), required=True)
        p.add_argument('--output', required=True)
        if mode in ('capture', 'child'):
            p.add_argument('--setup', required=True)
            p.add_argument('--setup-request', required=True)
            p.add_argument('--setup-dispatch', help='Original setup dispatch (omitted for an accepted recovery)')
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
