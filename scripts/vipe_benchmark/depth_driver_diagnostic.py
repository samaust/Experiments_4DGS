"""Separate one-use D6 syscall diagnostic authority; no model qualification."""
from pathlib import Path

from .files import file_record, object_hash, read_json, verify_record

JOB = 'plan069-D6-driver-diagnostic-001'
PREDECESSOR = 'plan069-D6-driver-qualification-001'


def require(value, message):
    if not value:
        raise ValueError(message)


def validate_request(record, *, completed=False, current_sources=None):
    request = read_json(verify_record(record)['path'])
    review = read_json(verify_record(request['review'])['path'])
    approval = read_json(verify_record(request['authorization'])['path'])
    proposal = review.get('proposal', {})
    require(request.get('schema') == 'plan069-D6-driver-diagnostic-request/v1' and
            request.get('record_kind') in ('actual', 'fixture'), 'exact driver diagnostic request required')
    require(review.get('schema') == 'plan069-D6-driver-diagnostic-review/v1' and review.get('status') == 'REVIEW' and
            approval.get('schema') == 'plan069-D6-driver-diagnostic-authorization/v1' and
            approval.get('status') == 'DO' and approval.get('review') == request['review'] and
            approval.get('proposal_sha256') == object_hash(proposal), 'separate diagnostic DO required')
    expected = dict(candidate='D6', job_id=JOB, predecessor_job=PREDECESSOR, max_attempts=1,
                    seconds=60, cleanup_seconds=30, device_bytes=2*1024**3,
                    artifact_bytes=16*1024**2, downloads=0, model_load=False,
                    inference=False, benchmarks=False, preserve_network_guard=True)
    require(all(proposal.get(key) == value for key, value in expected.items()), 'diagnostic bounds changed')
    require(proposal.get('setup') == request.get('setup') and
            proposal.get('predecessor_finish') == request.get('predecessor_finish'), 'diagnostic predecessor/setup changed')
    require(all(proposal.get(key) == request.get(key) for key in ('worker', 'guard', 'strace', 'dependencies')),
            'reviewed diagnostic method/tool/runtime binding differs')
    source = read_json(verify_record(request['source_review'])['path'])
    require(source.get('candidate') == 'D6' and source.get('status') == 'passed' and source.get('reviewer'),
            'independent diagnostic source review required')
    if current_sources is not None:
        require(source.get('local_sources') == current_sources, 'diagnostic sources changed')
    cpu = read_json(verify_record(request['cpu_validation'])['path'])
    require(cpu.get('schema') == 'plan069-delta-cpu-test-capture/v1' and cpu.get('passed') is True and
            cpu.get('record_kind') == request['record_kind'] and cpu.get('within_wall_limit') is True and
            cpu.get('source_bytes_unchanged') is True and cpu.get('sources_before') == cpu.get('sources_after'),
            'passing diagnostic CPU delta required')
    qualified = {row['path']: row for row in cpu['sources_before']}
    require(all(qualified.get(row['path']) == row for row in source['local_sources']), 'diagnostic CPU source binding differs')
    setup = read_json(verify_record(request['setup'])['path'])
    require(setup.get('candidate') == 'D6' and setup.get('status') == 'complete' and
            setup.get('record_kind') == request['record_kind'] and
            setup.get('python_executable') == request.get('interpreter_invocation'), 'exact accepted D6 runtime required')
    dependencies = read_json(verify_record(request['dependencies'])['path'])
    require(dependencies.get('schema') == 'plan069-depth-installed-dependencies/v1' and
            dependencies.get('candidate') == 'D6' and dependencies.get('setup') == request['setup'] and
            dependencies.get('record_kind') == request['record_kind'] and
            (request['record_kind'] == 'fixture' or bool(dependencies.get('files'))),
            'exact retained installed runtime closure required')
    if request['record_kind'] == 'actual':
        runtime = read_json(verify_record(setup['runtime_environment'])['path'])
        inventory = read_json(verify_record(runtime['inventory'])['path'])
        require(dependencies.get('inventory') == runtime['inventory'] and
                dependencies.get('packages') == inventory['packages'] and
                dependencies.get('files') == [row for package in inventory['packages'] for row in package['files']],
                'diagnostic installed package/file closure differs from accepted inventory')
    require(source.get('source_archive') == setup.get('source_archive') and
            source.get('source_files') == setup.get('source_tree'), 'diagnostic accepted native source binding differs')
    for key in ('worker', 'guard', 'strace', 'executable'):
        if not completed:
            verify_record(request[key])
    require(request['worker'] in source['local_sources'] and request['guard'] in source['local_sources'],
            'reviewed diagnostic worker and unchanged guard required')
    if not completed:
        for row in source['local_sources']:
            verify_record(row)
    require(file_record(Path(request['interpreter_invocation']).resolve()) == request['executable'],
            'diagnostic runtime executable changed')
    output = Path(request['output'])
    require(output.absolute() == output.resolve() and output.is_relative_to(Path(request['ledger_path']).parent),
            'diagnostic output escaped run')
    trace = output.with_suffix('.syscalls.log')
    require(not trace.is_symlink() and trace.absolute() == trace.resolve(), 'diagnostic trace symlink rejected')
    expected_command = [request['strace']['path'], '-f', '-qq', '-s', '128', '-e',
        'trace=socket,socketpair,connect,bind,listen,accept,accept4,sendto,sendmsg,recvfrom,recvmsg,ioctl',
        '-e', 'raw=sendto,sendmsg,recvfrom,recvmsg,ioctl', '-o', str(output.with_suffix('.syscalls.log')),
        request['interpreter_invocation'], '-I', '-B', request['worker']['path'], '--request', record['path']]
    require(request.get('command') == expected_command, 'exact diagnostic trace command required')
    return request, proposal


def check_predecessor(events, request):
    from .ledger import Ledger
    state = Ledger.__new__(Ledger).states(events).get(PREDECESSOR, {})
    retained = read_json(verify_record(request['predecessor_finish'])['path'])
    require(retained == state and retained.get('event') == 'finish' and retained.get('status') == 'failed' and
            retained.get('cleanup_confirmed') is True, 'exact failed clean predecessor required')
    reservations = [row for row in events if row.get('event') == 'reserve' and row.get('job_id') == PREDECESSOR]
    require(len(reservations) == 1, 'exact consumed predecessor reservation required')
    predecessor = read_json(verify_record(reservations[0]['evidence']['request'])['path'])
    require(predecessor.get('setup') == request['setup'] and predecessor.get('worker') == request['guard'],
            'diagnostic runtime/guard differs from failed predecessor')
    require(request['dependencies'] == file_record(Path(predecessor['output']) / 'installed-dependencies.json'),
            'exact predecessor installed dependency manifest required')


def validate_result(result, record):
    request, _ = validate_request(record, completed=True)
    require(result.get('schema') == 'plan069-D6-driver-diagnostic-result/v1' and
            result.get('request') == record and result.get('record_kind') == request['record_kind'] and
            result.get('status') == 'captured' and result.get('model_loaded') is False and
            result.get('inference') is False and result.get('benchmarks') is False and
            result.get('tensor_peak_allocated_bytes') == 0 and
            result.get('network_guard') == request['guard'] and
            result.get('cuda_init_outcome') in ('initialized', 'error'), 'exact driver-only diagnostic result required')
    trace_path = Path(request['output']).with_suffix('.syscalls.log')
    require(result.get('trace_path') == str(trace_path) and trace_path.is_file(), 'diagnostic trace escaped output')
    return result
