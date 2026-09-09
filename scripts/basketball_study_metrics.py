"""Evaluate matched curve cohorts in the identical pinned metric container."""
import argparse
import json
from pathlib import Path

from basketball_study import ARTIFACTS, CURVE, DOCS, ROOT, digest, supervise, verify_files, write_new
from basketball_study_baselines import finite


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--iteration', type=int, choices=CURVE[1:], required=True)
    a = p.parse_args()
    verify_files(json.loads((ROOT / 'docs/research/basketball-sync-pivot/evaluation-protocol-v3.json').read_text())['files'])
    runtime = json.loads((DOCS / 'metric-runtime.json').read_text())
    records = []
    for arm in ('stg-full', 'freetimegs-sparse'):
        for seed in range(3):
            path = ARTIFACTS / f'evaluation/{arm}-seed{seed}/record-{a.iteration:06d}.json'
            record = json.loads(path.read_text())
            if (record['arm'], record['seed'], record['iteration']) != (arm, seed, a.iteration):
                raise ValueError('curve evaluation pairing mismatch')
            if digest(record['render']) != record['render_sha256']:
                raise ValueError('curve render changed')
            records.append(record)
    inputs = ARTIFACTS / f'metric-inputs-{a.iteration:06d}.json'
    write_new(inputs, dict(runs=[dict(method=r['method'], seed=r['seed'], render=r['render']) for r in records]))
    output = ARTIFACTS / f'metrics/{a.iteration:06d}'
    command = ['docker', 'run', '--rm', '--name', f'plan026-metrics-{a.iteration}', '--network', 'none',
        '--gpus', 'all', '--user', '1000:1000', '-e', 'TRAINING_STOP_MONOTONIC=inf', '-e', 'MPLCONFIGDIR=/tmp/matplotlib',
        '--entrypoint', 'python', '-v', f'{ROOT}:{ROOT}', '-w', str(ROOT), runtime['image'],
        'scripts/basketball_reconstruction_metrics.py', '--inputs', str(inputs), '--output', str(output)]
    segment = supervise(command, 'evaluation', ARTIFACTS / f'segments/metrics-{a.iteration}')
    if segment['exit_code'] or segment['interrupted']:
        raise SystemExit('metrics stopped; inspect retained segment and worker logs')
    for record in records:
        path = output / f"{record['method']}-seed{record['seed']}.json"
        metrics = json.loads(path.read_text())
        render = json.loads(Path(record['render']).read_text())
        expected = {(r['camera'], r['frame_id']) for r in render['frames']}
        if (not metrics['complete'] or not finite(metrics) or metrics['iteration'] != a.iteration or
            metrics['render_sha256'] != record['render_sha256'] or len(metrics['frames']) != 350 or
            {(r['camera'], r['frame_id']) for r in metrics['frames']} != expected):
            raise ValueError('incomplete, nonfinite, or mismatched curve metrics')
        record['metrics'], record['metrics_sha256'] = str(path), digest(path)
    write_new(output / 'records.json', dict(schema='basketball-study-curve-metrics/v1', records=records,
        image=runtime['image'], charged_seconds=segment['charged_seconds']))


if __name__ == '__main__':
    main()
