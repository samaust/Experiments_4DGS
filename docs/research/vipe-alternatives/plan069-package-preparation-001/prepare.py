"""Prepare an immutable draft; never publish, spend allocations or choose a model."""
import argparse
import json
from pathlib import Path
import time

from vipe_benchmark.depth_anchor_previews import aggregate_request
from vipe_benchmark.depth_aggregate import CANDIDATES
from vipe_benchmark.files import file_record, read_json, verify_record


def prepare(checkout, run, output):
    started = time.monotonic()
    output.mkdir(parents=True, exist_ok=False)
    context = file_record(run / 'jobs/plan069-depth-context-003/context.json')
    inputs = file_record(run / 'prepare/inputs.json')
    receipts = {}
    slots = {}
    config = None
    for candidate in CANDIDATES:
        path = run / f'jobs/plan069-{candidate}-anchor-previews-002/result.json'
        if not path.exists():
            slots[candidate] = dict(status='missing',
                reason='Pending actual execution and revision 002 anchor previews; no terminal disposition authorized.',
                evidence={})
            continue
        record = file_record(path)
        receipt = read_json(path)
        if receipt['context'] != context or receipt['inputs'] != inputs:
            raise ValueError(f'{candidate}: accepted input/context differs')
        if config is not None and any(receipt['config'][key] != config[key]
                                      for key in ('sha256', 'bytes')):
            raise ValueError(f'{candidate}: configuration differs')
        config = receipt['config']
        verify_record(config)
        receipts[candidate] = record
        slots[candidate] = receipt['slot']
    if not receipts:
        raise ValueError('At least one actual preview receipt is required')
    charges = [json.loads(line) for line in (run / 'ledger.jsonl').read_text().splitlines()
               if 'plan069-depth-context-003-charge.json' in line]
    if len(charges) != 1 or charges[0]['event'] != 'cpu_preparation_charge':
        raise ValueError('Unique accepted context CPU ledger receipt required')
    verify_record(charges[0]['evidence'])
    ledger_path = output / 'context-ledger-receipt.json'
    ledger_path.write_text(json.dumps(charges[0], indent=2) + '\n')
    request = dict(schema='plan069-depth-aggregate-request/v1', record_kind='actual',
        id='plan069-depth-comparison-002',
        bindings=dict(context=context, inputs=inputs, config=config,
            amendment=file_record(checkout / 'docs/specs/plan031-execution/depth-comparison-extension.md'),
            source=file_record(checkout / 'scripts/vipe_benchmark/depth_aggregate.py')),
        source_provenance=dict(source_result=context,
            ledger_outcome=file_record(ledger_path), configuration=config),
        candidates=slots)
    request = aggregate_request(request, receipts)
    request_path = output / 'request.json'
    request_path.write_text(json.dumps(request, indent=2) + '\n')
    summary = dict(schema='plan069-depth-aggregate-draft/v1',
        status='draft_not_published', request=file_record(request_path),
        available=list(receipts), pending=[key for key in CANDIDATES if key not in receipts],
        rendered_frames=sum(len(request['candidates'][key]['anchors']) for key in receipts),
        verification='Matched actual revision 002 receipts; full aggregate/media admission still required.',
        elapsed_seconds=time.monotonic() - started,
        ledger_written=False, gpu_used=False, human_choice=None)
    (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('checkout', 'run', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.checkout.resolve(), args.run.resolve(), args.output.resolve())))
