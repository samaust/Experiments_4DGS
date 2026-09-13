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


def admission(args, config):
    local, docs, ledger = check_run(args, config)
    reasons = []
    evidence = {}
    for name, path in [('inputs', local / 'prepare/inputs.json'),
                       ('annotations', local / 'annotations/annotations.json')]:
        if not path.exists():
            reasons.append(f'{name}: missing completed, hash-bound evidence')
        else:
            evidence[name] = file_record(path)
            if name == 'annotations' and read_json(path).get('status') != 'reviewed':
                reasons.append('annotations: not fully reviewed')
    # These are implementation gaps, not candidate runtime failures. Do not
    # dispatch an unimplemented backend merely to consume an experiment attempt.
    reasons += ['pinned model adapters and the complete diagnostic geometry worker are not yet qualified/connected',
                'per-candidate source/weight/dependency/license inventories and E0–E8 runtime qualification are incomplete',
                'staged end-to-end aggregation/reporting has not been qualified']
    if args.validation:
        evidence['implementation_checks'] = file_record(args.validation)
    else:
        reasons.append('saved implementation validation is missing')
    record = dict(status='blocked', reasons=reasons, evidence=evidence, source_hashes=SOURCE_HASHES,
                  authorization=file_record(docs / 'authorization.json'), consumption=ledger.totals(),
                  independent_truth='232 reviewed/adjudicated images; external primary annotator and independent reviewer required')
    write_json(docs / 'admission.json', record)
    print('\n'.join(reasons))
    return 2


def status(args, config):
    local, docs, ledger = check_run(args, config)
    import json
    print(json.dumps(dict(run_id=args.run_id, consumption=ledger.totals(),
                          jobs={k: r.get('status', 'reserved') for k, r in ledger.states().items()},
                          admission=read_json(docs / 'admission.json') if (docs / 'admission.json').exists() else 'pending'), indent=2))


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
    p = sub.add_parser('admit')
    p.add_argument('--validation', type=Path)
    p = sub.add_parser('resume')
    p.add_argument('--authorization', required=True, help='Exact explicit user resume instruction')
    p.add_argument('--jobs', nargs='+', required=True)
    args = parser.parse_args()
    config = load()
    if args.command == 'init':
        return init_run(args, config)
    if args.command in ('prepare', 'annotations'):
        return cpu_stage(args, config)
    if args.command == 'admit':
        return admission(args, config)
    if args.command == 'resume':
        return resume(args, config)
    return status(args, config)


if __name__ == '__main__':
    raise SystemExit(main())
