"""Separately approved D6 qualification002 with the creation-only guard."""
from pathlib import Path

from .files import file_record, object_hash, read_json, verify_record

JOB = 'plan069-D6-driver-qualification-002'
KIND = 'gpu_aware_import_cpu_weights'
CREATION_EXCEPTION = dict(syscall='socket', domain=1, type=524293, protocol=0)
PREDECESSOR = 'plan069-D6-driver-qualification-001'
DIAGNOSTIC = 'plan069-D6-driver-diagnostic-001'


def require(value, message):
    if not value:
        raise ValueError(message)


def validate_request(request_record, *, current_sources=None, completed=False):
    request = read_json(verify_record(request_record)['path'])
    reviewed = read_json(verify_record(request['review'])['path'])
    approved = read_json(verify_record(request['authorization'])['path'])
    proposal = reviewed.get('proposal', {})
    require(reviewed.get('schema') == 'plan069-D6-driver-qualification-review/v2' and
            reviewed.get('status') == 'REVIEW', 'exact driver qualification REVIEW required')
    require(approved.get('schema') == 'plan069-D6-driver-qualification-authorization/v2' and
            approved.get('status') == 'DO' and approved.get('review') == request['review'] and
            approved.get('proposal_sha256') == object_hash(proposal),
            'explicit approved driver qualification allocation required')
    require(request.get('schema') == 'plan069-D6-driver-qualification-request/v2' and
            request.get('candidate') == 'D6' and request.get('job_id') == JOB and
            request.get('record_kind') in ('actual', 'fixture'), 'exact D6 qualification request required')
    require(proposal.get('candidate') == 'D6' and proposal.get('job_id') == JOB and
            proposal.get('qualification_kind') == KIND and proposal.get('max_attempts') == 1 and
            proposal.get('seconds') == 180 and proposal.get('device_bytes') == 2 * 1024**3 and
            proposal.get('artifact_bytes') == 64 * 1024**2 and
            proposal.get('downloads') == 0 and proposal.get('inference') is False and
            proposal.get('benchmarks') is False and proposal.get('strict_cpu_loads') == 2 and proposal.get('cleanup_seconds') == 30 and
            proposal.get('gpu_model_load') is False and
            proposal.get('creation_exception') == CREATION_EXCEPTION,
            'qualification proposal differs from bounded D6 contract')
    require(proposal.get('setup') == request.get('setup'), 'proposal setup binding differs')
    require(all(proposal.get(key) == request.get(key) for key in
            ('network_guard', 'strace', 'predecessor_finish', 'diagnostic_finish', 'diagnostic_result', 'diagnostic_trace',
             'creation_exception')), 'exact reviewed recovery lineage/guard required')
    for key in ('predecessor_finish', 'diagnostic_finish', 'diagnostic_result', 'diagnostic_trace'):
        verify_record(request[key])
    source = read_json(verify_record(request['source_review'])['path'])
    require(source.get('schema') == 'plan069-depth-source-review/v1' and source.get('candidate') == 'D6' and
            source.get('status') == 'passed' and bool(source.get('reviewer')),
            'independent current D6 source review required')
    if current_sources is not None:
        require(source.get('local_sources') == current_sources, 'driver qualification sources changed')
    if not completed:
        for item in source['local_sources']:
            verify_record(item)
    cpu = read_json(verify_record(request['cpu_validation'])['path'])
    require(cpu.get('schema') in ('plan069-delta-cpu-test-capture/v1',
                                 'plan069-integrated-cpu-test-capture/v1') and cpu.get('passed') is True and
            cpu.get('record_kind') == request['record_kind'] and cpu.get('within_wall_limit') is True and
            cpu.get('source_bytes_unchanged') is True and cpu.get('sources_before') == cpu.get('sources_after'),
            'passing combined CPU qualification required')
    if cpu['schema'] == 'plan069-integrated-cpu-test-capture/v1':
        packet = read_json(verify_record(cpu['review_request'])['path'])
        head = cpu.get('head')
        require(packet.get('schema') == 'plan069-final-full-cpu-review/v1' and
                packet.get('status') == 'REVIEW' and isinstance(head, str) and
                len(head) == 40 and all(character in '0123456789abcdef' for character in head) and
                head == packet.get('base_head') == cpu.get('head_after') and
                cpu.get('head_unchanged') is True and
                cpu.get('checkout') == packet.get('checkout') == request.get('root') and
                cpu.get('max_seconds') == packet.get('max_seconds') and
                0 <= cpu.get('elapsed_seconds', -1) <= cpu['max_seconds'],
                'integrated CPU qualification checkout/head/time binding differs')
        environment = cpu.get('environment', {})
        expected = dict(CUDA_VISIBLE_DEVICES='', VIPE_CPU_VALIDATION='1',
                        PYTHONDONTWRITEBYTECODE='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',
                        OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
                        NUMEXPR_NUM_THREADS='1', MPLBACKEND='Agg',
                        PYTHONPATH=f"{packet.get('overlay')}:{packet.get('checkout')}/scripts:{packet.get('checkout')}/tests",
                        S1_VALIDATION_RUN_DIRECTORY=str(Path(packet.get('output', '')) / 'disposable-results'),
                        MPLCONFIGDIR=str(Path(packet.get('output', '')) / 'matplotlib'))
        require(cpu.get('record_kind') == 'actual' and cpu.get('environment_bytes_unchanged') is True and
                all(environment.get(key) == value for key, value in expected.items()),
                'integrated CPU qualification environment binding differs')
        commands = cpu.get('commands', [])
        require([row.get('name') for row in commands] == ['pytest', 'unittest'] and
                all(row.get('returncode') == 0 and row.get('timed_out') is False and
                    row.get('cleanup', {}).get('confirmed_no_surviving_observed_processes') is True and
                    row.get('cleanup', {}).get('surviving_observed_owned_processes') == []
                    for row in commands), 'integrated CPU qualification commands or cleanup failed')
    if request['record_kind'] == 'actual':
        commands = cpu.get('commands', [])
        require(bool(commands) and all(row.get('returncode') == 0 and
                row.get('timed_out') is False and
                row.get('cleanup', {}).get('confirmed_no_surviving_observed_processes') is True and
                row.get('cleanup', {}).get('surviving_observed_owned_processes') == []
                for row in commands), 'CPU qualification cleanup evidence required')
        method_root = Path(request['root']) / 'docs/research/vipe-alternatives/plan031-execution/moge-driver-method-005'
        require(Path(request['worker']['path']) == method_root / 'producer.py' and
                Path(request['network_guard']['path']) == method_root / 'network_guard.py',
                'exact versioned005 producer and creation-only guard required')
    qualified_sources = {item['path']: item for item in cpu.get('sources_before', [])}
    require(all(qualified_sources.get(item['path']) == item for item in source['local_sources']),
            'CPU qualification does not bind reviewed driver sources')
    setup = read_json(verify_record(request['setup'])['path'])
    require(setup.get('candidate') == 'D6' and setup.get('status') == 'complete' and
            setup.get('record_kind') == request['record_kind'], 'accepted exact D6 setup required')
    require(source.get('source_archive') == setup.get('source_archive') and
            source.get('source_files') == setup.get('source_tree'), 'accepted archive/tree review required')
    require(request.get('interpreter_invocation') == setup.get('python_executable') and
            request.get('worker') in source['local_sources'] and
            request.get('network_guard') in source['local_sources'], 'reviewed worker/interpreter binding required')
    for key in ('executable', 'setup_request', 'setup_dispatch'):
        verify_record(request[key])
    if not completed:
        verify_record(request['worker'])
        verify_record(request['network_guard'])
        verify_record(request['strace'])
    trace = Path(request['output']).with_suffix('.syscalls.log')
    require(not trace.is_symlink() and trace.absolute() == trace.resolve(),
            'qualification trace symlink rejected')
    command = request.get('command')
    require(isinstance(command, list) and command == [request['strace']['path'], '-f', '-qq', '-s', '128', '-e',
            'trace=socket,socketpair,connect,bind,listen,accept,accept4,sendto,sendmsg,recvfrom,recvmsg,ioctl',
            '-e', 'raw=sendto,sendmsg,recvfrom,recvmsg,ioctl', '-o', str(trace),
            request['interpreter_invocation'], '-I', '-B', request['worker']['path'],
            'driver-child', '--request', request_record['path'], '--output', request['output']],
            'exact traced qualification command binding required')
    require(file_record(Path(request['interpreter_invocation']).resolve()) == request['executable'],
            'qualification interpreter changed')
    require(request.get('ledger_path') and Path(request['output']).absolute() == Path(request['output']).resolve(),
            'qualification output or ledger binding invalid')
    return request, proposal


def validate_result(result, request_record, *, cleanup_confirmed):
    request, proposal = validate_request(request_record, completed=True)
    require(result.get('schema') == 'plan069-D6-driver-qualification-result/v2' and
            result.get('candidate') == 'D6' and result.get('status') == 'passed' and
            result.get('qualification_kind') == KIND and result.get('request') == request_record and
            result.get('network_guard') == request['network_guard'] and
            result.get('creation_exception') == CREATION_EXCEPTION and
            result.get('record_kind') == request['record_kind'] and result.get('setup') == request['setup'],
            'exact D6 driver qualification result required')
    trace = verify_record(result['trace'])
    worker_result = verify_record(result['worker_result'])
    require(trace['path'] == str(Path(request['output']).with_suffix('.syscalls.log')) and
            result.get('trace_path') == trace['path'] and
            worker_result['path'] == str(Path(request['output']) / 'worker-result.json') and
            {key: value for key, value in result.items() if key not in ('trace', 'worker_result')} ==
            read_json(worker_result['path']), 'exact stable trace and worker-result envelope required')
    source = read_json(request['source_review']['path'])
    require(result.get('local_sources') == source['local_sources'] and result.get('method') == request['worker'] and
            result.get('python_executable') == request['interpreter_invocation'] and
            result.get('python') == file_record(request['interpreter_invocation']),
            'driver qualification result source/method/interpreter lineage differs')
    dependency = verify_record(result['dependency_manifest'])
    require(Path(dependency['path']) == Path(request['output']) / 'installed-dependencies.json',
            'driver qualification dependency manifest escaped output')
    dependencies = read_json(dependency['path'])
    require(dependencies.get('schema') == 'plan069-depth-installed-dependencies/v1' and
            dependencies.get('candidate') == 'D6' and dependencies.get('setup') == request['setup'],
            'driver qualification installed closure differs')
    if request['record_kind'] == 'actual':
        setup = read_json(verify_record(request['setup'])['path'])
        runtime = read_json(verify_record(setup['runtime_environment'])['path'])
        inventory = read_json(verify_record(runtime['inventory'])['path'])
        require(dependencies.get('record_kind') == 'actual' and
                dependencies.get('inventory') == runtime['inventory'] and
                dependencies.get('packages') == inventory['packages'] and
                dependencies.get('files') == [row for package in inventory['packages'] for row in package['files']] and
                result.get('runtime_environment') == setup['runtime_environment'] and
                result.get('setup_request') == request['setup_request'] and
                result.get('setup_dispatch') == request['setup_dispatch'],
                'exact retained runtime installed closure required')
    require(result.get('strict_cpu_loads') == 2 and result.get('all_parameters_cpu') is True and
            result.get('all_buffers_cpu') is True and result.get('cuda_initialized') is True and
            result.get('inference') is False and result.get('forward_calls') == 0 and
            result.get('benchmark_calls') == 0 and result.get('kernel_launches') == 0 and
            result.get('gpu_model_load') == 'not_performed' and cleanup_confirmed is True,
            'driver qualification exceeded import and CPU weight-loading scope')
    require(result.get('tensor_peak_allocated_bytes') == 0,
            'driver qualification allocated GPU tensors/models')
    return request


def qualification_exception(runtime):
    """Validate a retained completed exception without granting another attempt."""
    receipt = runtime.get('driver_qualification')
    require(isinstance(receipt, dict), 'D6 GPU-aware qualification receipt missing')
    result = read_json(verify_record(receipt['result'])['path'])
    finish = read_json(verify_record(receipt['finish'])['path'])
    from .ledger import Ledger
    from .config import load
    ledger = Ledger(receipt['ledger_path'], dict(load(), new_download_gib_limit=110,
                                              new_artifact_disk_gib_limit=210))
    events = ledger.events()
    require(any(event == finish for event in events) and finish.get('event') == 'finish' and
            finish.get('job_id') == JOB and finish.get('status') == 'complete' and
            finish.get('cleanup_confirmed') is True and not finish.get('cleanup_uncertain') and
            not finish.get('surviving_pids') and not finish.get('deadline_exceeded') and
            finish.get('elapsed_seconds', float('inf')) <= 180 and
            finish.get('peak', {}).get('device_bytes', float('inf')) <= 2 * 1024**3,
            'accepted driver qualification finish missing')
    request = validate_result(result, receipt['request'], cleanup_confirmed=finish['cleanup_confirmed'])
    check_predecessor(events, request)
    reserves = [event for event in events if event.get('event') == 'reserve' and event.get('job_id') == JOB]
    require(len(reserves) == 1 and reserves[0].get('evidence', {}).get('request') == receipt['request'] and
            finish.get('result') == receipt['result'] and
            result.get('record_kind') == runtime.get('record_kind', 'actual') and
            runtime.get('setup') == request['setup'] and runtime.get('local_sources') == result.get('local_sources') and
            runtime.get('qualification_kind') == KIND,
            'driver qualification lineage differs from runtime')
    return receipt


def check_predecessor(events, request):
    """Require the preserved failed001 and completed diagnostic, without resetting either."""
    from .ledger import Ledger
    from .depth_driver_diagnostic import validate_result as diagnostic_result
    states = Ledger.__new__(Ledger).states(events)
    failed = read_json(verify_record(request['predecessor_finish'])['path'])
    diagnostic = read_json(verify_record(request['diagnostic_finish'])['path'])
    require(states.get(PREDECESSOR) == failed and failed.get('event') == 'finish' and
            failed.get('status') == 'failed' and failed.get('cleanup_confirmed') is True and
            not failed.get('cleanup_uncertain') and not failed.get('surviving_pids'),
            'exact failed clean qualification001 predecessor required')
    require(states.get(DIAGNOSTIC) == diagnostic and diagnostic.get('event') == 'finish' and
            diagnostic.get('status') == 'complete' and diagnostic.get('cleanup_confirmed') is True and
            not diagnostic.get('cleanup_uncertain') and not diagnostic.get('surviving_pids') and
            diagnostic.get('deadline_exceeded') is not True and
            diagnostic.get('elapsed_seconds', float('inf')) <= 60 and
            diagnostic.get('peak', {}).get('device_bytes', float('inf')) <= 2 * 1024**3 and
            diagnostic.get('result') == request['diagnostic_result'],
            'exact completed clean diagnostic001 required')
    reserves = [row for row in events if row.get('event') == 'reserve' and row.get('job_id') == DIAGNOSTIC]
    require(len(reserves) == 1, 'exact consumed diagnostic reservation required')
    diagnostic_request = reserves[0].get('evidence', {}).get('request')
    result = read_json(verify_record(request['diagnostic_result'])['path'])
    diagnostic_result(result, diagnostic_request)
    require(request['diagnostic_trace'] == file_record(result['trace_path']),
            'exact retained diagnostic trace required')
    retained = read_json(verify_record(diagnostic_request)['path'])
    require(retained.get('setup') == request['setup'] and
            retained.get('predecessor_finish') == request['predecessor_finish'] and
            retained.get('strace') == request['strace'],
            'diagnostic setup/predecessor lineage differs')
    # The diagnostic's own checker ties its unchanged004 guard, runtime and dependency manifest
    # to the original consumed001 reservation; the new005 guard grants no historical authority.
    from .depth_driver_diagnostic import check_predecessor as diagnostic_predecessor
    diagnostic_predecessor(events, retained)
