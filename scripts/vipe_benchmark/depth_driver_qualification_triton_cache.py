"""Separately approved D6 qualifications005+: local-listen guard plus a prebuilt Triton helper cache."""
from pathlib import Path

# The guard007 socket policy is unchanged from qualification004.
from .depth_driver_qualification_local_listen import BIND_EXCEPTION, CREATION_EXCEPTION, KIND, LISTEN_EXCEPTION
from .files import file_record, object_hash, read_json, verify_record

JOB = 'plan069-D6-driver-qualification-005'
FOURTH_PREDECESSOR = 'plan069-D6-driver-qualification-004'
# Each distinct attempt names its reviewed worker method, the consumed-attempt lineage it adds and,
# when the previous attempt passed but its sources were superseded, that previous terminal status.
ATTEMPTS = {
    JOB: dict(method='moge-driver-method-008', previous=FOURTH_PREDECESSOR,
              lineage=('fourth_predecessor_finish', 'fourth_predecessor_trace')),
    'plan069-D6-driver-qualification-006': dict(method='moge-driver-method-009', previous=JOB,
              lineage=('fourth_predecessor_finish', 'fourth_predecessor_trace',
                       'fifth_predecessor_finish', 'fifth_predecessor_trace')),
    'plan069-D6-driver-qualification-007': dict(method='moge-driver-method-010',
              previous='plan069-D6-driver-qualification-006', previous_status='complete',
              lineage=('fourth_predecessor_finish', 'fourth_predecessor_trace',
                       'fifth_predecessor_finish', 'fifth_predecessor_trace',
                       'sixth_predecessor_finish', 'sixth_predecessor_trace')),
    'plan069-D6-driver-qualification-008': dict(method='moge-driver-method-011',
              previous='plan069-D6-driver-qualification-007', previous_status='complete',
              lineage=('fourth_predecessor_finish', 'fourth_predecessor_trace',
                       'fifth_predecessor_finish', 'fifth_predecessor_trace',
                       'sixth_predecessor_finish', 'sixth_predecessor_trace',
                       'seventh_predecessor_finish', 'seventh_predecessor_trace')),
    # First attempt on the approved replacement runtime: the only attempt allowed to change setup.
    'plan069-D6-driver-qualification-009': dict(method='moge-driver-method-012',
              previous='plan069-D6-driver-qualification-008', previous_status='complete',
              replaced_setup_job='plan069-D6-setup-recovery-002',
              lineage=('fourth_predecessor_finish', 'fourth_predecessor_trace',
                       'fifth_predecessor_finish', 'fifth_predecessor_trace',
                       'sixth_predecessor_finish', 'sixth_predecessor_trace',
                       'seventh_predecessor_finish', 'seventh_predecessor_trace',
                       'eighth_predecessor_finish', 'eighth_predecessor_trace')),
}
BASE_LINEAGE = ('predecessor_finish', 'diagnostic_finish', 'diagnostic_result', 'diagnostic_trace',
                'second_predecessor_finish', 'second_predecessor_trace', 'third_predecessor_finish',
                'third_predecessor_trace')


def require(value, message):
    if not value:
        raise ValueError(message)


def validate_request(request_record, *, current_sources=None, completed=False):
    request = read_json(verify_record(request_record)['path'])
    reviewed = read_json(verify_record(request['review'])['path'])
    approved = read_json(verify_record(request['authorization'])['path'])
    proposal = reviewed.get('proposal', {})
    require(reviewed.get('schema') == 'plan069-D6-driver-qualification-review/v5' and
            reviewed.get('status') == 'REVIEW', 'exact driver qualification REVIEW required')
    require(approved.get('schema') == 'plan069-D6-driver-qualification-authorization/v5' and
            approved.get('status') == 'DO' and approved.get('review') == request['review'] and
            approved.get('proposal_sha256') == object_hash(proposal),
            'explicit approved driver qualification allocation required')
    job = request.get('job_id')
    require(request.get('schema') == 'plan069-D6-driver-qualification-request/v5' and
            request.get('candidate') == 'D6' and job in ATTEMPTS and
            request.get('record_kind') in ('actual', 'fixture'), 'exact D6 qualification request required')
    attempt = ATTEMPTS[job]
    require(proposal.get('candidate') == 'D6' and proposal.get('job_id') == job and
            proposal.get('qualification_kind') == KIND and type(proposal.get('max_attempts')) is int and proposal['max_attempts'] == 1 and
            proposal.get('seconds') == 180 and proposal.get('device_bytes') == 2 * 1024**3 and
            proposal.get('artifact_bytes') == 64 * 1024**2 and
            proposal.get('downloads') == 0 and proposal.get('inference') is False and
            proposal.get('benchmarks') is False and proposal.get('strict_cpu_loads') == 2 and proposal.get('cleanup_seconds') == 30 and
            proposal.get('gpu_model_load') is False and
            proposal.get('creation_exception') == CREATION_EXCEPTION and
            proposal.get('bind_exception') == BIND_EXCEPTION and
            proposal.get('listen_exception') == LISTEN_EXCEPTION and
            isinstance(proposal.get('triton_cache'), dict),
            'qualification proposal differs from bounded D6 contract')
    require(proposal.get('setup') == request.get('setup'), 'proposal setup binding differs')
    require(isinstance(request.get('worker'), dict) and proposal.get('worker') == request['worker'],
            'exact reviewed qualification worker required')
    lineage = BASE_LINEAGE + attempt['lineage']
    require(all(proposal.get(key) == request.get(key) for key in
            ('network_guard', 'strace', 'creation_exception', 'bind_exception', 'guard_startup', 'listen_exception',
             'triton_cache') + lineage), 'exact reviewed recovery lineage/guard required')
    for key in lineage + ('triton_cache', 'guard_startup'):
        verify_record(request[key])
    if not completed:
        from .triton_helper_cache import SCHEMA, SCHEMA_V2, validate_binding
        binding = validate_binding(request['triton_cache'])
        # Only the runtime-replacing attempt runs Triton >= 3.3, which needs the bound libcuda (v2).
        require(binding.get('schema') == (SCHEMA_V2 if attempt.get('replaced_setup_job') else SCHEMA),
                'Triton helper cache schema differs from the attempt runtime')
        built = read_json(verify_record(binding['build_receipt'])['path'])
        require(built.get('python') == request.get('interpreter_invocation') and built.get('gpu_operations') is False,
                'Triton helper must be built CPU-only by the qualification interpreter')
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
        method_root = Path(request['root']) / 'docs/research/vipe-alternatives/plan031-execution' / attempt['method']
        require(Path(request['worker']['path']) == method_root / 'producer.py' and
                Path(request['network_guard']['path']) == method_root / 'network_guard.py' and
                Path(request['guard_startup']['path']) == method_root / 'startup.py',
                'exact versioned attempt producer and local-listen guard required')
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
            request.get('network_guard') in source['local_sources'] and
            request.get('guard_startup') in source['local_sources'], 'reviewed worker/interpreter binding required')
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
    require(result.get('schema') == 'plan069-D6-driver-qualification-result/v5' and
            result.get('candidate') == 'D6' and result.get('status') == 'passed' and
            result.get('qualification_kind') == KIND and result.get('request') == request_record and
            result.get('network_guard') == request['network_guard'] and
            result.get('creation_exception') == CREATION_EXCEPTION and
            result.get('bind_exception') == BIND_EXCEPTION and
            result.get('listen_exception') == LISTEN_EXCEPTION and
            result.get('triton_cache') == request['triton_cache'] and result.get('triton_cache_unchanged') is True and
            result.get('guard_startup') == request['guard_startup'] and
            result.get('record_kind') == request['record_kind'] and result.get('setup') == request['setup'],
            'exact D6 driver qualification result required')
    proof = result.get('guard_startup_proof', {})
    require(isinstance(proof, dict) and set(proof) == {'socket_descriptors', 'descriptor_count',
            'single_thread', 'numeric_imports', 'unix_bind_allowed', 'unix_listen_allowed'} and
            type(proof.get('socket_descriptors')) is int and proof['socket_descriptors'] == 0 and
            type(proof.get('descriptor_count')) is int and proof['descriptor_count'] >= 0 and
            proof.get('single_thread') is True and proof.get('numeric_imports') is False and
            proof.get('unix_bind_allowed') is True and proof.get('unix_listen_allowed') is True, 'exact pre-helper descriptor proof required')
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


def qualification_exception(runtime, *, events=None, run_root=None):
    """Validate a retained completed exception without granting another attempt."""
    receipt = runtime.get('driver_qualification')
    require(isinstance(receipt, dict), 'D6 GPU-aware qualification receipt missing')
    result = read_json(verify_record(receipt['result'])['path'])
    finish = read_json(verify_record(receipt['finish'])['path'])
    from .depth_driver_qualification import retained_ledger_events
    events = retained_ledger_events(receipt, events=events, run_root=run_root)
    require(any(event == finish for event in events) and finish.get('event') == 'finish' and
            finish.get('job_id') in ATTEMPTS and finish.get('status') == 'complete' and
            finish.get('cleanup_confirmed') is True and not finish.get('cleanup_uncertain') and
            not finish.get('surviving_pids') and not finish.get('deadline_exceeded') and
            finish.get('elapsed_seconds', float('inf')) <= 180 and
            finish.get('peak', {}).get('device_bytes', float('inf')) <= 2 * 1024**3,
            'accepted driver qualification finish missing')
    request = validate_result(result, receipt['request'], cleanup_confirmed=finish['cleanup_confirmed'])
    require(request.get('ledger_path') == receipt['ledger_path'] and request['job_id'] == finish['job_id'],
            'qualification request and retained ledger path differ')
    check_predecessor(events, request)
    reserves = [event for event in events if event.get('event') == 'reserve' and event.get('job_id') == finish['job_id']]
    require(len(reserves) == 1 and reserves[0].get('evidence', {}).get('request') == receipt['request'] and
            finish.get('result') == receipt['result'] and
            result.get('record_kind') == runtime.get('record_kind', 'actual') and
            runtime.get('setup') == request['setup'] and runtime.get('local_sources') == result.get('local_sources') and
            runtime.get('qualification_kind') == KIND,
            'driver qualification lineage differs from runtime')
    return receipt


def reservation_evidence(request_record, request=None):
    return dict(request=request_record)


def check_predecessor(events, request):
    """Preserve the exact consumed previous attempt's grant, request, trace and earlier ancestry."""
    if request['job_id'] != JOB:
        return _check_previous_triton_attempt(events, request)
    from .ledger import Ledger
    from .depth_driver_qualification_local_listen import validate_request as previous_request, check_predecessor as previous_lineage
    failed = read_json(verify_record(request['fourth_predecessor_finish'])['path'])
    states = Ledger.__new__(Ledger).states(events)
    require(states.get(FOURTH_PREDECESSOR) == failed and failed.get('event') == 'finish' and
            failed.get('job_id') == FOURTH_PREDECESSOR and failed.get('status') == 'failed' and
            failed.get('cleanup_confirmed') is True and not failed.get('cleanup_uncertain') and
            not failed.get('surviving_pids') and not failed.get('deadline_exceeded'),
            'exact failed clean qualification004 predecessor required')
    grants = [row for row in events if row.get('event') == 'depth_driver_qualification_local_listen_authorized']
    reserves = [row for row in events if row.get('event') == 'reserve' and row.get('job_id') == FOURTH_PREDECESSOR]
    require(len(grants) == len(reserves) == 1 and grants[0]['sequence'] < reserves[0]['sequence'] < failed['sequence'] and
            reserves[0].get('evidence') == dict(request=grants[0]['request']),
            'exact consumed qualification004 authority required')
    retained, _ = previous_request(grants[0]['request'], completed=True)
    previous_lineage(events, retained)
    require(all(retained[key] == request[key] for key in ('setup', 'predecessor_finish',
            'diagnostic_finish', 'diagnostic_result', 'diagnostic_trace',
            'second_predecessor_finish', 'second_predecessor_trace', 'third_predecessor_finish',
            'third_predecessor_trace', 'strace')) and
            reserves[0].get('command') == retained['command'], 'qualification004 retained lineage differs')
    trace = verify_record(request['fourth_predecessor_trace'])
    require(trace['path'] == str(Path(retained['output']).with_suffix('.syscalls.log')),
            'exact retained qualification004 trace required')


def _check_previous_triton_attempt(events, request):
    """A later attempt requires the exact clean earlier Triton-cache attempt (failed, or passed then superseded)."""
    from .ledger import Ledger
    previous = ATTEMPTS[request['job_id']]['previous']
    status = ATTEMPTS[request['job_id']].get('previous_status', 'failed')
    finish_key, trace_key = ATTEMPTS[request['job_id']]['lineage'][-2:]
    failed = read_json(verify_record(request[finish_key])['path'])
    states = Ledger.__new__(Ledger).states(events)
    require(states.get(previous) == failed and failed.get('event') == 'finish' and
            failed.get('job_id') == previous and failed.get('status') == status and
            failed.get('cleanup_confirmed') is True and not failed.get('cleanup_uncertain') and
            not failed.get('surviving_pids') and not failed.get('deadline_exceeded'),
            'exact clean previous Triton-cache qualification (' + status + ') required')
    grants = [row for row in events if row.get('event') == 'depth_driver_qualification_triton_cache_authorized' and
              row.get('job_id') == previous]
    reserves = [row for row in events if row.get('event') == 'reserve' and row.get('job_id') == previous]
    require(len(grants) == len(reserves) == 1 and grants[0]['sequence'] < reserves[0]['sequence'] < failed['sequence'] and
            reserves[0].get('evidence') == dict(request=grants[0]['request']),
            'exact consumed previous Triton-cache qualification authority required')
    retained, _ = validate_request(grants[0]['request'], completed=True)
    require(retained['job_id'] == previous, 'previous Triton-cache grant names a different attempt')
    check_predecessor(events, retained)
    replaced = ATTEMPTS[request['job_id']].get('replaced_setup_job')
    if replaced is not None:
        _require_replacement_setup(request, retained, replaced, events)
    require(all(retained[key] == request[key] for key in
            (() if replaced is not None else ('setup',)) + ('strace',) + BASE_LINEAGE + ATTEMPTS[previous]['lineage']) and
            reserves[0].get('command') == retained['command'], 'previous Triton-cache retained lineage differs')
    trace = verify_record(request[trace_key])
    require(trace['path'] == str(Path(retained['output']).with_suffix('.syscalls.log')),
            'exact retained previous Triton-cache qualification trace required')


def _require_replacement_setup(request, retained, replaced_job, events):
    """The new setup is the accepted approved runtime replacement of the retained original setup."""
    from .depth_moge_runtime_replacement import accepted_setup_lineage
    root = Path(request['ledger_path']).resolve().parent
    require(Path(request['setup']['path']) == root / 'jobs' / replaced_job / 'result.json',
            'exact accepted runtime replacement setup required')
    lineage = accepted_setup_lineage(request['setup'], events, root)
    require(lineage['original']['setup'] == retained['setup'] and
            request.get('setup_request') == lineage['request'] and request.get('setup_dispatch') == lineage['review'],
            'runtime replacement does not replace the retained qualification setup')
