"""Fresh reloads of each retained Plan 026 curve using the frozen Plan 024 renderer."""
import argparse
import json
import os
from pathlib import Path

from basketball_study import ARTIFACTS, CURVE, DOCS, MANIFEST, ROOT, digest, supervise, verify_files, write_new


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--arm', choices=('stg-full', 'freetimegs-sparse'), required=True)
    p.add_argument('--seed', type=int, choices=range(3), required=True)
    a = p.parse_args()
    protocol = json.loads((ROOT / 'docs/research/basketball-sync-pivot/evaluation-protocol-v3.json').read_text())
    verify_files(protocol['files'])
    training = ARTIFACTS / f'training/{a.arm}-seed{a.seed}'
    provenance = json.loads((training / 'study-provenance.json').read_text())
    result = json.loads((training / 'worker-result.json').read_text())
    if result['iteration'] != 50000 or provenance['arm'] != a.arm or provenance['seed'] != a.seed:
        raise ValueError('training endpoint or pairing mismatch')
    if digest(training / 'study_adapter.py') != provenance['adapter_sha256']:
        raise ValueError('executed training adapter changed')
    method = 'stg-full' if a.arm == 'stg-full' else 'freetimegs'
    environment = 'stg-render' if method == 'stg-full' else 'freetimegs'
    checkout = ROOT / ('.local/SpacetimeGaussians' if method == 'stg-full' else '.local/FreeTimeGsVanilla')
    output = ARTIFACTS / f'evaluation/{a.arm}-seed{a.seed}'
    output.mkdir(parents=True, exist_ok=False)
    os.environ['TRAINING_STOP_MONOTONIC'] = 'inf'
    for step in CURVE[1:]:
        checkpoint = training / f'checkpoint-{step:06d}.pt'
        checkpoint_hash = digest(checkpoint)
        folder = output / f'{step:06d}'
        command = [str(ROOT / f'.local/envs/{environment}/bin/python'), 'scripts/evaluate-basketball-sync.py',
            'evaluate', '--method', method, '--checkout', str(checkout), '--manifest', str(MANIFEST),
            '--checkpoint', str(checkpoint), '--regions', str(ROOT / '.local/sync-pivot/basketball-evaluation-regions/regions.json'),
            '--output', str(folder)]
        segment = supervise(command, 'evaluation', ARTIFACTS / f'segments/evaluate-{a.arm}-seed{a.seed}-{step}')
        if segment['exit_code'] or segment['interrupted']:
            raise SystemExit('evaluation stopped; inspect retained segment and worker logs')
        evaluation = json.loads((folder / 'evaluation.json').read_text())
        repeated = evaluation['reload']
        if (not evaluation['complete'] or evaluation['iteration'] != step or
            evaluation['checkpoint_sha256'] != checkpoint_hash or repeated['compared'] != 13 or
            not all(repeated[k] for k in ('fresh_process', 'png_identical', 'float_identical', 'complete'))):
            raise ValueError('curve checkpoint reload validation failed')
        render = folder / 'first/render.json'
        report = json.loads(render.read_text())
        if len(report['frames']) != 350:
            raise ValueError('curve target coverage mismatch')
        record = dict(arm=a.arm, method=method, seed=a.seed, iteration=step,
            checkpoint=str(checkpoint), checkpoint_sha256=checkpoint_hash, checkpoint_bytes=checkpoint.stat().st_size,
            render=str(render), render_sha256=digest(render), reload=repeated,
            rendering_fps=report['benchmark']['fps'], peak_allocated_bytes=report['peak_allocated_bytes'],
            peak_reserved_bytes=report['peak_reserved_bytes'], charged_seconds=segment['charged_seconds'])
        write_new(output / f'record-{step:06d}.json', record)
        print(json.dumps(dict(arm=a.arm, seed=a.seed, step=step, status='rendered and reload-verified')), flush=True)


if __name__ == '__main__':
    main()
