"""Plan 031 preparation/admission controller; preserve every historical artifact."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import re
import subprocess
import sys

from vipe_benchmark.config import PLAN, PROTOCOL, ROOT, SOURCE_HASHES, counts, jobs, load
from vipe_benchmark.files import digest, file_record, read_json, verify_record, write_json
from vipe_benchmark.ledger import Ledger

CONFIG = ROOT / 'configs/vipe-alternatives/benchmark-v1.json'


def paths(run_id):
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,95}', run_id):
        raise ValueError('invalid run ID')
    return (ROOT / '.local/vipe-alternatives' / run_id,
            ROOT / 'docs/research/vipe-alternatives' / run_id)


def init_run(args, config):
    from vipe_benchmark.prepare import exposure_history
    local, docs = paths(args.run_id)
    if local.exists() or docs.exists():
        raise ValueError('run ID already exists; never overwrite a previous run')
    local.mkdir(parents=True)
    docs.mkdir(parents=True)
    authorization = dict(schema='vipe-benchmark-authorization/v1', run_id=args.run_id,
        created_utc=datetime.now(timezone.utc).isoformat(), request='Implement plans/plan_031.md.',
        basis='Explicit user implementation request; AGENTS.md standing approval for plan-specific allocations and local commits.',
        continuous_improvement_loop=False, plan=file_record(PLAN), protocol=file_record(PROTOCOL),
        source_hashes=SOURCE_HASHES, configuration=file_record(CONFIG),
        repository_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        limits=config, expected_counts=counts(config), inherited_ledger_reset=False)
    write_json(docs / 'authorization.json', authorization)
    write_json(docs / 'exposure-history.json', exposure_history())
    write_json(docs / 'components.json', dict(schema='vipe-benchmark-qualification/v1',
        specification=file_record(ROOT / 'configs/vipe-alternatives/components-v1.json'),
        candidates={k: dict(status='unverified', reason='exact assets, permissions and runtime have not been qualified')
                    for k in [f'S{i}' for i in range(5)] + [f'D{i}' for i in range(5)]},
        new_environment_builds=0, model_inference_jobs=0))
    Ledger(local / 'ledger.jsonl', config).note('authorized', authorization=file_record(docs / 'authorization.json'))
    print(str(docs / 'authorization.json'))


def check_run(args, config):
    local, docs = paths(args.run_id)
    authorization = read_json(docs / 'authorization.json')
    for field in ('plan', 'protocol', 'configuration'):
        verify_record(authorization[field])
    if authorization['limits'] != config or authorization['source_hashes'] != SOURCE_HASHES:
        raise ValueError('run allocation or source specification changed')
    return local, docs, Ledger(local / 'ledger.jsonl', config)


def cpu_stage(args, config):
    from vipe_benchmark.supervisor import directory_bytes, supervise
    local, docs, ledger = check_run(args, config)
    operation = args.command
    request = dict(configuration=file_record(CONFIG), exposure=file_record(docs / 'exposure-history.json'))
    if operation == 'annotations':
        request.update(inputs=file_record(local / 'prepare/inputs.json'), annotations=file_record(args.bundle))
    request_path = local / f'{operation}-request.json'
    write_json(request_path, request)
    command = [str(Path(sys.executable)), str(ROOT / 'scripts/basketball_vipe_worker.py'),
               '--operation', operation, '--config', str(CONFIG), '--request', str(request_path),
               '--output', str(local / operation)]
    def validate(output):
        result = read_json(output / 'result.json')
        if result.get('status') != 'complete':
            raise ValueError('incomplete worker result')
        verify_record(result['inputs' if operation == 'prepare' else 'annotations'])
        if operation == 'prepare' and (result['counts'] != counts(config) or result['annotation_images'] != 232):
            raise ValueError('preparation count mismatch')
    result = supervise(ledger, operation, command, local / operation,
                       evidence=dict(request=file_record(request_path), worker=file_record(ROOT / 'scripts/basketball_vipe_worker.py')),
                       sample_resources=lambda: dict(artifact_bytes=directory_bytes(local)), validate_result=validate,
                       poll_seconds=1.)
    write_json(docs / (operation + '.json'), result)
    print(f'{operation}: complete')


def auto_annotations(args, config):
    from vipe_benchmark.auto_annotations import check_policy, validate
    from vipe_benchmark.supervisor import directory_bytes, supervise
    local, docs, ledger = check_run(args, config)
    policy_record = file_record(args.policy)
    policy = check_policy(policy_record)
    checkpoint = read_json(args.checkpoint_receipt)['asset']
    verify_record(checkpoint)
    request = dict(configuration=file_record(CONFIG), inputs=file_record(local / 'prepare/inputs.json'),
                   policy=policy_record, checkpoint=checkpoint)
    request_path = local / 'auto-annotations-request.json'
    write_json(request_path, request)
    command = [sys.executable, str(ROOT / 'scripts/basketball_vipe_worker.py'),
               '--operation', 'auto-annotations', '--config', str(CONFIG),
               '--request', str(request_path), '--output', str(local / 'annotations')]
    def validate_result(output):
        result = read_json(output / 'result.json')
        if result.get('status') != 'complete':
            raise ValueError('annotation worker incomplete')
        verify_record(result['annotations'])
        validate(read_json(result['annotations']['path']), read_json(request['inputs']['path']), config)
    downloads = sum(read_json(p)['bytes_received'] for p in (local / 'assets').glob('*.transfer-*.json'))
    result = supervise(ledger, 'annotations', command, local / 'annotations',
        evidence=dict(request=file_record(request_path), policy=policy_record),
        sample_resources=lambda: dict(artifact_bytes=directory_bytes(local), download_bytes=downloads),
        validate_result=validate_result, poll_seconds=2., seconds_limit=policy['limits']['annotation_seconds'])
    write_json(docs / 'annotations-002.json', result)
    print('Automated annotations: reviewed proxy bundle complete')


def admission(args, config):
    from vipe_benchmark.execution import common_admission
    local, docs, _ = check_run(args, config)
    record = common_admission(local, docs, config, args.validation)
    print(record['status'] + (': ' + '; '.join(record['reasons']) if record['reasons'] else ''))
    return 2 if record['status'] == 'blocked' else 0


def status(args, config):
    local, docs, ledger = check_run(args, config)
    import json
    admissions = [r for r in ledger.events() if r['event'] == 'admission']
    latest = read_json(verify_record(admissions[-1]['evidence'])['path']) if admissions else (
        read_json(docs / 'admission.json') if (docs / 'admission.json').exists() else 'pending')
    print(json.dumps(dict(run_id=args.run_id, consumption=ledger.totals(),
                          jobs={k: r.get('status', 'reserved') for k, r in ledger.states().items()},
                          admission=latest), indent=2))


def execute(args, config):
    from vipe_benchmark.execution import (aggregate_request, dispatch, execute_matrix,
                                         make_request, qualify_existing, supplement_existing_inventory)
    local, docs, ledger = check_run(args, config)
    if args.command == 'qualify':
        qualify_existing(local, docs, config)
    elif args.command == 'inventory-existing':
        supplement_existing_inventory(local, docs, config)
    elif args.command == 'setup':
        if args.environment:
            from vipe_benchmark.setup_recipes import request as setup_request
            request = setup_request(local, args.environment)
        else:
            request = read_json(args.request)
        if request['job_id'] != request['environment'] + '-setup':
            raise ValueError('setup request/job identity mismatch')
        dispatch(local, docs, config, request, operation='setup')
    elif args.command == 'setup-recovery':
        from vipe_benchmark.setup_recipes import recovery_request
        authorization = file_record(args.authorization)
        recovery_id = read_json(args.authorization)['job_id']
        registered = [event for event in ledger.events() if event['event'] == 'setup_recovery_authorized'
                      and event['job_id'] == recovery_id]
        if not registered:
            ledger.authorize_setup_recovery(authorization)
        elif len(registered) != 1 or registered[0]['authorization'] != authorization:
            raise ValueError('a different recovery authorization is already registered')
        dispatch(local, docs, config, recovery_request(local, authorization), operation='setup')
    elif args.command == 'execute':
        execute_matrix(local, docs, config, args.validation)
    elif args.command == 'stage':
        from vipe_benchmark.execution import common_admission, require_stage_order
        require_stage_order(local, args.job, config)
        record = common_admission(local, docs, config, args.validation)
        if record['status'] != 'admitted':
            raise ValueError('; '.join(record['reasons']))
        request, reasons = make_request(local, args.job, config)
        if reasons:
            ledger.account(args.job, 'skipped' if args.job.startswith('R-') else 'blocked', '; '.join(reasons))
            print('; '.join(reasons))
        else:
            operation = 'geometry' if args.job.startswith(('G-', 'C')) or args.job == 'R-G' else 'component'
            dispatch(local, docs, config, request, operation=operation)
    print(args.command + ': complete')


def resume(args, config):
    _, _, ledger = check_run(args, config)
    ledger.resume_unstarted(args.jobs, args.authorization)
    print('Recorded explicit resume for unstarted slots only; no jobs launched.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('init')
    sub.add_parser('prepare')
    sub.add_parser('status')
    p = sub.add_parser('annotations')
    p.add_argument('--bundle', type=Path, required=True)
    p = sub.add_parser('auto-annotations')
    p.add_argument('--policy', type=Path, required=True)
    p.add_argument('--checkpoint-receipt', type=Path, required=True)
    p = sub.add_parser('admit')
    p.add_argument('--validation', type=Path)
    sub.add_parser('qualify')
    sub.add_parser('inventory-existing')
    p = sub.add_parser('setup')
    choice = p.add_mutually_exclusive_group(required=True)
    choice.add_argument('--request', type=Path)
    choice.add_argument('--environment', choices=[f'E{i}' for i in range(1, 8)])
    p = sub.add_parser('setup-recovery')
    p.add_argument('--authorization', type=Path, required=True)
    p = sub.add_parser('execute')
    p.add_argument('--validation', type=Path, required=True)
    p = sub.add_parser('stage')
    p.add_argument('--job', required=True)
    p.add_argument('--validation', type=Path, required=True)
    p = sub.add_parser('resume')
    p.add_argument('--authorization', required=True, help='Exact explicit user resume instruction')
    p.add_argument('--jobs', nargs='+', required=True)
    args = parser.parse_args()
    config = load()
    if args.command == 'init':
        return init_run(args, config)
    if args.command in ('prepare', 'annotations'):
        return cpu_stage(args, config)
    if args.command == 'auto-annotations':
        return auto_annotations(args, config)
    if args.command == 'admit':
        return admission(args, config)
    if args.command in ('qualify', 'inventory-existing', 'setup', 'setup-recovery', 'execute', 'stage'):
        return execute(args, config)
    if args.command == 'resume':
        return resume(args, config)
    return status(args, config)


if __name__ == '__main__':
    raise SystemExit(main())
